#!/usr/bin/python3
import asyncio

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFrame,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import QTimer
from game import Game
from extraction import ExtractedFile
from wordytextview import WordyTextView
from gui.filedialog import file_dialog_open, file_dialog_save
from gui.mainloop import run

from sys import argv
from random import seed


GAME_FILTERS = ["Games (*.dat)", "All Files (*)"]
SAVE_FILTERS = ["Saved Games (*.sav)", "All Files (*)"]


async def get_game_path():
    return await file_dialog_open(None, "Open Game", GAME_FILTERS)


class GuiGame(Game):
    """This game subclass uses file chooser dialogs to prompt for save or load file names."""

    def __init__(self, extracted_game, window):
        Game.__init__(self, extracted_game)
        self.window = window

    def flush_output(self):
        self.window.flush_output()
        self.window.update_room_view()

    async def get_save_game_path(self):
        return await file_dialog_save(self.window, "Save Game", SAVE_FILTERS)

    async def get_load_game_path(self):
        return await file_dialog_open(self.window, "Load Game", SAVE_FILTERS)


class GameWindow(QMainWindow):
    """
    This window displays the game output in two sections; a top section shows
    the room description, and the lower shows the transcript as you go. An text
    entry area allows command input, and a toolbar lets you load and save your game.
    """

    def __init__(self, game_file):
        super().__init__()
        self.setWindowTitle("Scott Dumb")

        with open(game_file, "r") as f:
            self.game = GuiGame(ExtractedFile(f), self)

        # Toolbar with Load / Save
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        load_action = toolbar.addAction("&Load")
        load_action.triggered.connect(self.on_load_game)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(spacer)

        save_action = toolbar.addAction("&Save")
        save_action.triggered.connect(self.on_save_game)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Room view (auto-sizes to content, no scrolling)
        self.room_view = WordyTextView(
            self.game, self.queue_command, auto_height=True
        )
        main_layout.addWidget(self.room_view)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(sep1)

        # Middle area: script transcript + inventory
        mid_layout = QHBoxLayout()

        self.script_view = WordyTextView(self.game, self.queue_command)
        mid_layout.addWidget(self.script_view, stretch=1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        mid_layout.addWidget(sep2)

        self.inventory_view = WordyTextView(
            self.game, self.queue_command, width_request=300
        )
        mid_layout.addWidget(self.inventory_view)

        main_layout.addLayout(mid_layout, stretch=1)

        # Command entry area
        self.command_widget = QWidget()
        cmd_layout = QHBoxLayout(self.command_widget)
        cmd_layout.setContentsMargins(5, 5, 5, 5)

        cmd_label = QLabel(">")
        cmd_layout.addWidget(cmd_label)

        self.command_entry = QLineEdit()
        self.command_entry.returnPressed.connect(self.on_command_activate)
        cmd_layout.addWidget(self.command_entry, stretch=1)

        score_button = QPushButton("&Score")
        score_button.clicked.connect(self.on_score)
        cmd_layout.addWidget(score_button)

        main_layout.addWidget(self.command_widget)

        self.resize(900, 500)

        self.running_task = None
        self.pending_command = None
        self.start_task(self.before_turn())

    def closeEvent(self, event):
        asyncio.get_running_loop().stop()
        event.accept()

    def start_task(self, coro):
        task = asyncio.get_running_loop().create_task(coro)

        def done(*_args):
            if self.running_task == task:
                self.running_task = None

            if (
                self.running_task is None
                and self.pending_command is not None
                and self.pending_command == self.command_entry.text()
            ):
                cmd = self.pending_command
                self.pending_command = None
                self.queue_command(cmd)

        task.add_done_callback(done)
        self.running_task = task

    def flush_output(self):
        """
        Displays any pending output. Each output is displayed in its own
        text-view, so this will implicitly place a line break after the output.
        """
        words = self.game.extract_output()

        if len(words) > 0:
            self.script_view.append_line()
            self.script_view.append_words(words)
            self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Scrolls the output window as far down as possible."""

        def do_scroll():
            scrollbar = self.script_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        do_scroll()
        # Scrolling may fail because the widgets are not laid out yet;
        # so this will try to do it again a little later.
        QTimer.singleShot(0, do_scroll)

    def update_room_view(self):
        """
        Generate the room description text afresh and displays it. The previous
        room description is removed.
        """
        game = self.game
        if game.wants_room_update or game.needs_room_update:
            words = game.player_room.get_look_words()
            self.room_view.clear()
            self.room_view.append_words(words)
            game.needs_room_update = False
            game.wants_room_update = False

        self.command_widget.setEnabled(not game.game_over)
        self.update_inventory_view()

    def update_inventory_view(self):
        words = self.game.get_inventory_words()
        self.inventory_view.clear()
        self.inventory_view.append_words(words)

    async def before_turn(self):
        """
        Performs game logic that should happen before user commands are accepted.
        This flushes output and updates the room view.
        """
        game = self.game

        if not game.game_over:
            await game.perform_occurances()
            self.command_entry.setFocus()

        self.flush_output()
        self.update_room_view()

        async def scroll():
            await asyncio.sleep(0)
            self.scroll_to_bottom()

        asyncio.create_task(scroll())

    def on_load_game(self):
        """Handles the load game button."""
        asyncio.get_running_loop().create_task(self.do_on_load_game())

    async def do_on_load_game(self):
        game = self.game
        if await game.load_game():
            self.pending_command = None
            self.running_task = None
            game.extract_output()
            self.script_view.clear()
            game.output_line("Game loaded.")
            self.flush_output()
            self.update_room_view()
            self.command_entry.setFocus()

    def on_save_game(self):
        """Handles the save game button."""
        if self.running_task is not None:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText("You cannot save now.")
            msg.setInformativeText(
                "You cannot save the game while game actions are happening."
            )
            msg.addButton(QMessageBox.StandardButton.Ok)
            msg.open()
            return

        asyncio.get_running_loop().create_task(self.game.save_game())

    # Command handling

    def queue_command(self, cmd):
        """Runs a command. A command may not complete immediately,
        and if so it will be running after this returns. If called while
        another command is running, this will queue the new command to run
        after the old completes."""
        if self.running_task is None:
            self.start_task(self.do_command(cmd))
        else:
            self.pending_command = cmd
            self.command_entry.setText(cmd)

    def cancel_commands(self):
        """This terminates all running and pending command
        activity. This interrupts a running command, if any,
        and is done before loading save."""
        self.running_task = None
        self.pending_command = None

    async def do_command(self, cmd):
        """This handles a user command; it parses it and
        echos it to the output, then starts it executing."""
        game = self.game
        try:
            self.command_entry.setText("")
            verb, noun = game.parse_command(cmd)
            game.output_line("> " + cmd)
            self.flush_output()
            await game.perform_command(verb, noun)
        except Exception as e:
            game.output(str(e))
            self.flush_output()

        await self.before_turn()

    def on_command_activate(self):
        """Handles a user-entered command when the user hits enter."""
        if not self.game.game_over:
            cmd = self.command_entry.text()
            self.queue_command(cmd)

    def on_score(self):
        """Generates the score command"""
        if not self.game.game_over:
            self.queue_command("SCORE")


async def start_game():
    if len(argv) >= 2:
        game_path = argv[1]
    else:
        game_path = await get_game_path()

    if game_path:
        seed()
        win = GameWindow(game_path)
        win.show()
    else:
        asyncio.get_running_loop().stop()


run(start_game())
