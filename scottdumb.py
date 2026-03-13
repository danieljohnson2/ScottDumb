#!/usr/bin/python3
import gi
import asyncio

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk, Gio
from game import Game
from extraction import ExtractedFile
from wordytextview import WordyTextView

from sys import argv
from random import seed


def make_filter(name, pattern):
    """Builds a GTK file-filter conveniently."""
    f = Gtk.FileFilter()
    f.set_name(name)
    f.add_pattern(pattern)
    return f


def make_filter_list(*filters):
    """Builds a Gio.ListStore of file filters for Gtk.FileDialog."""
    store = Gio.ListStore.new(Gtk.FileFilter)
    for f in filters:
        store.append(f)
    return store


GAME_FILTERS = make_filter_list(
    make_filter("Games", "*.dat"),
    make_filter("All Files", "*"),
)

SAVE_FILTERS = make_filter_list(
    make_filter("Saved Games", "*.sav"),
    make_filter("All Files", "*"),
)


async def file_dialog_open(parent, title, filters):
    """Opens a file dialog for selecting a file to open. Returns the path, or None if cancelled."""
    dialog = Gtk.FileDialog()
    dialog.set_title(title)
    dialog.set_filters(filters)
    future = loop.create_future()

    def callback(dialog, result):
        try:
            file = dialog.open_finish(result)
            future.set_result(file.get_path())
        except GLib.Error:
            future.set_result(None)

    dialog.open(parent, None, callback)
    return await future


async def file_dialog_save(parent, title, filters):
    """Opens a file dialog for selecting a file to save. Returns the path, or None if cancelled."""
    dialog = Gtk.FileDialog()
    dialog.set_title(title)
    dialog.set_filters(filters)
    future = loop.create_future()

    def callback(dialog, result):
        try:
            file = dialog.save_finish(result)
            future.set_result(file.get_path())
        except GLib.Error:
            future.set_result(None)

    dialog.save(parent, None, callback)
    return await future


async def get_game_path():
    return await file_dialog_open(None, "Game", GAME_FILTERS)


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


class GameWindow(Gtk.ApplicationWindow):
    """
    This window displays the game output in two sections; a top section shows
    the room description, and the lower shows the transcript as you go. A text
    entry area allows command input, and a header bar lets you load and save your game.
    """

    def __init__(self, app, game_file):
        Gtk.ApplicationWindow.__init__(self, application=app)

        with open(game_file, "r") as f:
            self.game = GuiGame(ExtractedFile(f), self)

        self.header_bar = Gtk.HeaderBar()
        self.set_title("Scott Dumb")
        self.set_titlebar(self.header_bar)

        self.load_button = Gtk.Button(label="_Load", use_underline=True)
        self.load_button.connect("clicked", self.on_load_game)
        self.header_bar.pack_start(self.load_button)

        self.save_button = Gtk.Button(label="_Save", use_underline=True)
        self.save_button.connect("clicked", self.on_save_game)
        self.header_bar.pack_end(self.save_button)

        self.room_view = WordyTextView(self.game, self.queue_command)

        self.script_view = WordyTextView(self.game, self.queue_command)

        self.inventory_view = WordyTextView(
            self.game, self.queue_command, width_request=300
        )

        vBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vBox.append(self.room_view)
        vBox.append(Gtk.Separator())

        self.command_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        command_label = Gtk.Label(label=">")
        command_label.set_margin_start(5)
        self.command_entry = Gtk.Entry()
        self.command_entry.set_hexpand(True)
        self.command_entry.connect("activate", self.on_command_activate)

        score_button = Gtk.Button(label="_Score", use_underline=True)
        score_button.connect("clicked", self.on_score)
        score_button.set_margin_end(5)

        self.command_box.append(command_label)
        self.command_box.append(self.command_entry)
        self.command_box.append(score_button)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_child(self.script_view)
        self.scroller.set_hexpand(True)

        hBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hBox.set_vexpand(True)
        hBox.append(self.scroller)
        hBox.append(Gtk.Separator())
        hBox.append(self.inventory_view)
        vBox.append(hBox)

        vBox.append(self.command_box)

        self.set_child(vBox)

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
        # Scrolling may fail because the widgets are not laid out yet;
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

    def on_load_game(self, data):
        """Handles the load game button."""
        self.start_task(self.do_load_game())

    async def do_load_game(self):
        game = self.game
        if await game.load_game():
            self.pending_command = None
            self.running_task = None
            game.extract_output()
            self.script_view.clear()
            game.output_line("Game loaded.")
            self.flush_output()
            self.update_room_view()
            self.command_entry.grab_focus()

    def on_save_game(self, data):
        """Handles the save game button."""
        if self.running_task is not None:
            dialog = Gtk.AlertDialog()
            dialog.set_message("You cannot save now.")
            dialog.set_detail(
                "You cannot save the game while game actions are happening."
            )
            dialog.set_buttons(["OK"])
            dialog.show(self)
            return

        self.start_task(self.game.save_game())

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

    def on_command_activate(self, data):
        """Handles a user-entered command when the user hits enter."""
        if not self.game.game_over:
            cmd = self.command_entry.get_text()
            self.queue_command(cmd)

    def on_score(self, data):
        """Generates the score command"""
        if not self.game.game_over:
            self.queue_command("SCORE")


def on_activate(app):
    if len(argv) >= 2:
        game_path = argv[1]
        seed()
        win = GameWindow(app, game_path)
        win.connect("close-request", lambda *x: loop.stop())
        win.present()
    else:
        loop.create_task(open_game_then_start(app))


async def open_game_then_start(app):
    game_path = await get_game_path()
    if game_path:
        seed()
        win = GameWindow(app, game_path)
        win.connect("close-request", lambda *x: loop.stop())
        win.present()
    else:
        loop.stop()


async def start():
    app = Gtk.Application(application_id="org.scottdumb.app")
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
