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

class GuiGame(Game):
        def __init__(self, file, save_game_path):
                Game.__init__(self, file)
                self.save_game_path = save_game_path

        def get_save_game_path(self):
                return self.save_game_path

        def get_load_game_path(self):
                return self.save_game_path

class GameWindow(Gtk.Window):
    def __init__(self, game):
        Gtk.Window.__init__(self, title="Scott Dumb")
        self.game = game
        self.room_buffer = Gtk.TextBuffer()
        self.room_view = Gtk.TextView(buffer=self.room_buffer, editable=False)

        self.script_buffer = Gtk.TextBuffer()
        self.script_view = Gtk.TextView(buffer=self.script_buffer, editable=False)

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
        self.scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.script_view)
        vBox.pack_end(self.scroller, True, True, 0)

        self.add(vBox)

        self.set_default_size(900, 300)
        self.before_turn()

    def print(self, text, end="\n"):
        iter = self.script_buffer.get_end_iter()
        self.script_buffer.insert(iter, text+end)
        GLib.idle_add(self.scroll_to_bottom)

    def scroll_to_bottom(self):
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_upper())

    def update_room_view(self):
        game = self.game
        if game.wants_room_update or game.needs_room_update:
            text = game.player_room.get_look_text()
            self.room_buffer.set_text(text)
            game.needs_room_update = False
            game.wants_room_update = False

        self.command_entry.set_sensitive(not game.game_over)

    def before_turn(self):
        game = self.game

        self.update_room_view()

        if not game.game_over:
            game.perform_occurances()
            self.print(game.extract_output(), end = "")
            self.command_entry.grab_focus()

    def on_command_activate(self, data):
        game = self.game
        if not game.game_over:
            try:
                cmd = self.command_entry.get_text()
                self.command_entry.set_text("")
                verb, noun = game.parse_command(cmd)
   
                self.print("> " + cmd)             
                game.perform_command(verb, noun)
                self.print(game.extract_output(), end = "")
            except Exception as e:
                self.print(str(e))

        self.before_turn()
            
seed()

with open(argv[1], "r") as f:
        ex = ExtractedFile(f)

if len(argv) >= 3:
        g = GuiGame(ex, argv[2])
        try: game.load_game()
        except FileNotFoundError: pass
else:
        g = Game(ex)



win = GameWindow(g)
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()

