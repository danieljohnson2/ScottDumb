#!/usr/bin/python3
import gi
import asyncio

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import GLib, Gtk, Gio
from game import Game
from extraction import ExtractedFile
from wordytextview import WordyTextView
from contextlib import contextmanager

from sys import argv
from random import seed


def make_filter(name, pattern):
    """Builds a GTK file-filter conveniently."""
    f = Gtk.FileFilter()
    f.set_name(name)
    f.add_pattern(pattern)
    return f


@contextmanager
def filechooser(window, title, action):
    dlg = Gtk.FileChooserDialog(title="Game", action=action, transient_for=window)
    try:
        yield dlg
    finally:
        dlg.destroy()


@contextmanager
def error_alert(window, text):
    dlg = Gtk.MessageDialog(
        transient_for=window,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CANCEL,
        text=text,
    )
    try:
        yield dlg
    finally:
        dlg.destroy()


def get_game_path():
    with filechooser(None, "Game", Gtk.FileChooserAction.OPEN) as dlg:
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.add_filter(make_filter("Games", "*.dat"))
        dlg.add_filter(make_filter("All Files", "*"))

        if dlg.run() == Gtk.ResponseType.OK:
            return dlg.get_filename()
        else:
            return None


class GuiGame(Game):
    """This game subclass uses file chooser dialogs to prompt for save or load file names."""

    def __init__(self, extracted_game, window):
        Game.__init__(self, extracted_game)
        self.window = window

    def flush_output(self):
        self.window.flush_output()
        self.window.update_room_view()

    def get_save_game_path(self):
        with filechooser(self.window, "Save Game", Gtk.FileChooserAction.SAVE) as dlg:
            dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            dlg.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            dlg.set_default_response(Gtk.ResponseType.OK)
            dlg.add_filter(make_filter("Saved Games", "*.sav"))
            dlg.add_filter(make_filter("All Files", "*"))

            if dlg.run() == Gtk.ResponseType.OK:
                return dlg.get_filename()
            else:
                return None

    def get_load_game_path(self):
        with filechooser(self.window, "Load Game", Gtk.FileChooserAction.OPEN) as dlg:
            dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
            dlg.set_default_response(Gtk.ResponseType.OK)
            dlg.add_filter(make_filter("Saved Games", "*.sav"))
            dlg.add_filter(make_filter("All Files", "*"))

            if dlg.run() == Gtk.ResponseType.OK:
                return dlg.get_filename()
            else:
                return None


class GameWindow(Gtk.Window):
    """
    This window displays the game output in two sections; a top section shows
    the room description, and the lower shows the transcript as you go. An text
    entry area allows command input, and a header bar lets you load and save your game.
    """

    def __init__(self, game_file):
        Gtk.Window.__init__(self)

        with open(game_file, "r") as f:
            self.game = GuiGame(ExtractedFile(f), self)

        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_title("Scott Dumb")
        self.header_bar.set_show_close_button(True)

        self.load_button = Gtk.Button(label="_Load", use_underline=True)
        self.load_button.connect("clicked", self.on_load_game)
        self.header_bar.pack_start(self.load_button)

        self.save_button = Gtk.Button(label="_Save", use_underline=True)
        self.save_button.connect("clicked", self.on_save_game)
        self.header_bar.pack_end(self.save_button)

        self.set_titlebar(self.header_bar)

        self.room_view = WordyTextView(self.game, self.queue_command)
        self.room_view.connect("size-allocate", self.on_room_view_size_allocate)

        self.script_view = WordyTextView(self.game, self.queue_command)

        self.inventory_view = WordyTextView(
            self.game, self.queue_command, width_request=300
        )

        vBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vBox.pack_start(self.room_view, False, False, 0)
        vBox.pack_start(Gtk.Separator(), False, False, 0)

        self.command_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        command_label = Gtk.Label(label=">")
        command_label.set_margin_start(5)
        self.command_entry = Gtk.Entry()
        self.command_entry.connect("activate", self.on_command_activate)

        score_button = Gtk.Button(label="_Score", use_underline=True)
        score_button.connect("clicked", self.on_score)
        score_button.set_margin_end(5)
        self.command_box.pack_end(score_button, False, False, 0)

        self.command_box.pack_start(command_label, False, False, 0)
        self.command_box.pack_end(self.command_entry, True, True, 0)

        vBox.pack_end(self.command_box, False, False, 5)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.script_view)

        hBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hBox.pack_start(self.scroller, True, True, 0)
        hBox.pack_start(Gtk.Separator(), False, False, 0)
        hBox.pack_start(self.inventory_view, False, False, 0)
        vBox.pack_end(hBox, True, True, 0)

        self.add(vBox)

        self.set_default_size(900, 500)

        self.running_task = None
        self.start_task(self.before_turn())
        self.pending_command = None

    def start_task(self, coro):
        task = loop.create_task(coro)

        def done(*_args):
            if self.running_task == task:
                self.running_task = None

            if (
                self.running_task is None
                and self.pending_command is not None
                and self.pending_command == self.command_entry.get_text()
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
            adj = self.scroller.get_vadjustment()
            adj.set_value(adj.get_upper())

        do_scroll()
        # Scrolling may fail because the wigdets are not laid out yet;
        # so this will try to do it again a little later.
        GLib.idle_add(do_scroll)

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

        self.command_box.set_sensitive(not game.game_over)
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
            self.command_entry.grab_focus()

        self.flush_output()
        self.update_room_view()

    def on_room_view_size_allocate(self, allocation, data):
        self.scroll_to_bottom()

    def on_load_game(self, data):
        """Handles the load game button."""
        game = self.game
        if game.load_game():
            self.pending_command = None
            self.running_task = None
            game.extract_output()
            self.script_view.clear()
            game.output_line("Game loaded.")
            self.flush_output()
            self.update_room_view()
            self.command_entry.grab_focus()

    def on_save_game(self, data):
        if self.running_task is not None:
            with error_alert(self, "You cannot save now.") as dlg:
                dlg.format_secondary_text(
                    "You cannot save the game while game actions are happening."
                )
            return

        """Handles the save game button."""
        self.game.save_game()

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
            self.command_entry.set_text(cmd)

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
            self.command_entry.set_text("")
            verb, noun = game.parse_command(cmd)
            game.output_line("> " + cmd)
            self.flush_output()
            await game.perform_command(verb, noun)
        except Exception as e:
            game.output(str(e))
            self.flush_output()

        await self.before_turn()

    def run_next_command1(self):
        """Executes the next step of running_iter, or
        if that runs out, it starts pending_command and does
        the first stop of that.

        This loops and runs as much as possible of the commands,
        but if a delay occurs it queues intself to run again after
        the delay. In this way the UI can be responsive while a pause
        opcode is running."""
        if self.running_task is not None:
            try:
                while True:
                    next(self.running_task)
            except StopIteration:
                self.running_task = None

                if (
                    self.pending_command is not None
                    and self.pending_command == self.command_entry.get_text()
                ):
                    cmd = self.pending_command
                    self.pending_command = None
                    self.queue_command(cmd)
            except Exception as e:
                self.game.output(str(e))
        self.flush_output()
        self.update_room_view()
        False  # do not repeat

    def on_command_activate(self, data):
        """Handles a user-entered command when the user hits enter."""
        if not self.game.game_over:
            cmd = self.command_entry.get_text()
            self.queue_command(cmd)

    def on_score(self, data):
        """Generates the score command"""
        if not self.game.game_over:
            self.queue_command("SCORE")


def on_activate(*args):
    if len(argv) >= 2:
        game_path = argv[1]
    else:
        game_path = get_game_path()

    if game_path:
        seed()
        win = GameWindow(game_path)
        win.connect("delete-event", lambda *x: asyncio.get_running_loop().stop())
        win.show_all()
    else:
        loop.stop()


async def start():
    app = Gio.Application()
    app.connect("activate", on_activate)
    app.register()
    app.activate()


def repeated_iteration():
    while main_context.pending():
        main_context.iteration(False)
    loop.call_later(0.01, repeated_iteration)


loop = asyncio.new_event_loop()
main_context = GLib.MainContext.default()
loop.create_task(start())
repeated_iteration()
loop.run_forever()
