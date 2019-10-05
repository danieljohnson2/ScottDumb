#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile

from sys import argv
from random import seed

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango

def make_filter(name, pattern):
    """Builds a GTK file-filter conveniently."""
    f = Gtk.FileFilter()
    f.set_name(name)
    f.add_pattern(pattern)
    return f

class GuiGame(Game):
    """This game subclass uses file chooser dialogs to prompt for save or load file names."""
    def __init__(self, extracted_game, window):
        Game.__init__(self, extracted_game)
        self.window = window

    def get_save_game_path(self):
        dlg = Gtk.FileChooserDialog(title="Save Game",
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.add_filter(make_filter("Saved Games", "*.sav"))
        dlg.add_filter(make_filter("All Files", "*"))
        try:
            if (dlg.run() == Gtk.ResponseType.OK):
                return dlg.get_filename()
            else:
                return None
        finally:
            dlg.destroy()

    def get_load_game_path(self):
        dlg = Gtk.FileChooserDialog(title="Load Game",
            parent=self.window,
            action=Gtk.FileChooserAction.OPEN)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.add_filter(make_filter("Saved Games", "*.sav"))
        dlg.add_filter(make_filter("All Files", "*"))
        try:
            if (dlg.run() == Gtk.ResponseType.OK):
                return dlg.get_filename()
            else:
                return None
        finally:
            dlg.destroy()

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

        self.underline_tag = Gtk.TextTag()
        self.underline_tag.set_property("underline", Pango.Underline.SINGLE)
        
        self.room_buffer = Gtk.TextBuffer()
        self.room_view = Gtk.TextView(buffer=self.room_buffer, editable=False)
        self.room_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.room_view.connect("size-allocate", self.on_room_view_size_allocate)

        self.script_buffer = Gtk.TextBuffer()
        self.script_buffer.get_tag_table().add(self.underline_tag)
        self.script_view = Gtk.TextView(buffer=self.script_buffer, editable=False)
        self.script_view.set_wrap_mode(Gtk.WrapMode.WORD)

        vBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vBox.pack_start(self.room_view, False, False, 0)
        vBox.pack_start(Gtk.Separator(), False, False, 0)
       
        cmdBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        command_label = Gtk.Label(label=">")
        command_label.set_margin_start(5)
        self.command_entry = Gtk.Entry()
        self.command_entry.connect("activate", self.on_command_activate)
        self.command_entry.set_margin_end(5)
        cmdBox.pack_start(command_label, False, False, 0)
        cmdBox.pack_end(self.command_entry, True, True, 0)

        vBox.pack_end(cmdBox, False, False, 5)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.script_view)
        vBox.pack_end(self.scroller, True, True, 0)

        self.add(vBox)

        self.set_default_size(900, 500)
        self.before_turn()

    def flush_output(self):
        """
        Displays any pending output, if any. Each output is displayed in its own
        text-view, so this will implicitly place a line break after the output.
        """
        buffer = self.game.extract_output()

        if len(buffer) > 0:
            iter = self.script_buffer.get_end_iter()
            if self.script_buffer.get_char_count() > 0:
                self.script_buffer.insert(iter, "\n")

            while len(buffer) > 0 and buffer[0].is_newline():
                del buffer[0]

            while len(buffer) > 0 and buffer[-1].is_newline():
                del buffer[-1]

            word_index = 0
            for word in buffer:
                if word_index > 0: self.script_buffer.insert(iter, " ")

                if word.is_underlined:
                    self.script_buffer.insert_with_tags(iter, str(word), self.underline_tag)
                else:
                    self.script_buffer.insert(iter, str(word))

                if word.is_newline(): word_index = 0
                else: word_index += 1

            self.scroll_to_bottom()

    def clear_output(self):
        """Clears the output in the window, and clears the output buffer."""
        self.game.extract_output()
        start = self.script_buffer.get_start_iter()
        end = self.script_buffer.get_end_iter()
        self.script_buffer.delete(start, end)

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
            text = game.player_room.get_look_text()
            self.room_buffer.set_text(text)
            game.needs_room_update = False
            game.wants_room_update = False

        self.command_entry.set_sensitive(not game.game_over)

    def before_turn(self):
        """
        Performs game logic that should happen before user commands are accepted.
        This flushes output and updates the room view.
        """        
        game = self.game

        if not game.game_over:
            game.perform_occurances()
            self.command_entry.grab_focus()

        self.flush_output()
        self.update_room_view()

    def on_room_view_size_allocate(self, allocation, data):
        self.scroll_to_bottom()

    def on_load_game(self, data):
        """Handles the load game button."""
        game = self.game
        if game.load_game():
            self.clear_output()
            game.output_line("Game loaded.")
            self.flush_output()
            self.update_room_view()
            self.command_entry.grab_focus()

    def on_save_game(self, data):
        """Handles the save game button."""
        self.game.save_game()

    def on_command_activate(self, data):
        """Handles a user-enterd command when the user hits enter."""
        game = self.game
        if not game.game_over:
            try:
                cmd = self.command_entry.get_text()
                self.command_entry.set_text("")

                verb, noun = game.parse_command(cmd)
   
                game.output_line("> " + cmd + "\n")
                self.flush_output()
                game.perform_command(verb, noun)
                self.flush_output()
            except Exception as e:
                game.output(str(e))
                self.flush_output()

        self.before_turn()
            
seed()
win = GameWindow(argv[1])
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()

