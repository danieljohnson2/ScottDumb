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

class WordyTextView(Gtk.TextView):
    def __init__(self, game, perform_command, **kwargs):
        self.game = game
        self.perform_command = perform_command
        self.words_by_tag = { }
        self.buffer = Gtk.TextBuffer()
        Gtk.TextView.__init__(self, buffer=self.buffer, editable=False, **kwargs)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.connect("button-press-event", self.on_button_press_event)
        self.connect("motion-notify-event", self.on_motion_notify_event)

    def append_line(self):
        iter = self.buffer.get_end_iter()
        if self.buffer.get_char_count() > 0:
            self.buffer.insert(iter, "\n")

    def append_words(self, words):
        words = list(words)
        while len(words) > 0 and words[0].is_newline():
            del words[0]

        while len(words) > 0 and words[-1].is_newline():
            del words[-1]

        iter = self.buffer.get_end_iter()
        word_index = 0
        for word in words:
            if word_index > 0: self.buffer.insert(iter, " ")
            tag = self.get_tag(word)
            if tag is None:
                self.buffer.insert(iter, str(word))
            else:
                self.buffer.insert_with_tags(iter, str(word), tag)
            
            if word.is_newline(): word_index = 0
            else: word_index += 1

    def get_tag(self, word):
        if word.is_plain(self.game): return None

        if self.buffer in word.tags:
            return word.tags[self.buffer]
        else:
            tag = Gtk.TextTag()
            tag.set_property("underline", Pango.Underline.SINGLE)
            self.buffer.get_tag_table().add(tag)
            self.words_by_tag[tag] = word
            word.tags[self.buffer] = tag
            return tag;

    def clear_buffer(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.delete(start, end)

    def on_motion_notify_event(self, text_view, event):
        x, y = self.window_to_buffer_coords(Gtk.TextWindowType.TEXT, event.x, event.y)
        found, i = self.get_iter_at_location(x, y)
        if found and len(i.get_tags()) > 0:
            cursor_name = "pointer"
        else:
            cursor_name = "text"

        w = self.get_window(Gtk.TextWindowType.TEXT)
        cursor = Gdk.Cursor.new_from_name(w.get_display(), cursor_name)
        w.set_cursor(cursor)
            
    def on_button_press_event(self, text_view, event):
        x, y = self.window_to_buffer_coords(Gtk.TextWindowType.TEXT, event.x, event.y)
        found, i = self.get_iter_at_location(x, y)
        if found:
            for t in i.get_tags():
                word = self.words_by_tag[t]
                commands = word.active_commands(self.game)
                if len(commands) > 0:
                    menu = Gtk.Menu()
                    menu.attach_to_widget(text_view)
                    for cmd in commands:
                        item = Gtk.MenuItem(label=cmd)
                        menu.append(item)
                    
                        def on_menu_item_activate(m, c):
                            self.perform_command(c)
                        item.connect("activate", on_menu_item_activate, cmd)
                    menu.show_all()
                    menu.popup_at_pointer(event)
                    self.stop_emission_by_name("button-press-event")

