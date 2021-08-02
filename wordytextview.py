#!/usr/bin/python3
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gtk
from game import Game
from extraction import ExtractedFile

from sys import argv
from random import seed

import gi
gi.require_version('Gtk', '3.0')


class WordyTextView(Gtk.TextView):
    def __init__(self, game, perform_command, **kwargs):
        self.game = game
        self.perform_command = perform_command
        self.words_by_tag = {}
        self.buffer = Gtk.TextBuffer()
        Gtk.TextView.__init__(self, buffer=self.buffer,
                              editable=False, **kwargs)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.connect("button-press-event", self.on_button_press_event)
        self.connect("motion-notify-event", self.on_motion_notify_event)

    def append_line(self):
        """Adds a line break to the view. If it is now empty, this does nothing."""
        iter = self.buffer.get_end_iter()
        if self.buffer.get_char_count() > 0:
            self.buffer.insert(iter, "\n")

    def append_words(self, words):
        """
        Appends a sequence of words to the view. If there are any
        active commands on any words, this will record takes for them and
        underline them so they can be handled.
        """

        def get_tag(word):
            if word.is_plain(self.game):
                return None

            if self.buffer in word.tags:
                return word.tags[self.buffer]
            else:
                tag = Gtk.TextTag()
                tag.set_property("underline", Pango.Underline.SINGLE)
                self.buffer.get_tag_table().add(tag)
                self.words_by_tag[tag] = word
                word.tags[self.buffer] = tag
                return tag

        words = list(words)
        while len(words) > 0 and words[0].is_newline():
            del words[0]

        while len(words) > 0 and words[-1].is_newline():
            del words[-1]

        iter = self.buffer.get_end_iter()
        word_index = 0
        for word in words:
            if word_index > 0:
                self.buffer.insert(iter, " ")
            tag = get_tag(word)
            if tag is None:
                self.buffer.insert(iter, str(word))
            else:
                self.buffer.insert_with_tags(iter, str(word), tag)

            if word.is_newline():
                word_index = 0
            else:
                word_index += 1

    def clear(self):
        """Clears the text from this view."""

        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.delete(start, end)

        tag_table = self.buffer.get_tag_table()

        for tag in self.words_by_tag:
            del self.words_by_tag[tag].tags[self.buffer]
        self.words_by_tag = {}

        tag_table.foreach(lambda tag: tag_table.remove(tag))

    def on_motion_notify_event(self, text_view, event):
        x, y = self.window_to_buffer_coords(
            Gtk.TextWindowType.TEXT, event.x, event.y)
        found, i = self.get_iter_at_location(x, y)
        if found and len(i.get_tags()) > 0:
            cursor_name = "pointer"
        else:
            cursor_name = "text"

        w = self.get_window(Gtk.TextWindowType.TEXT)
        cursor = Gdk.Cursor.new_from_name(w.get_display(), cursor_name)
        w.set_cursor(cursor)

    def on_button_press_event(self, text_view, event):

        def create_menu(commands):
            menu = Gtk.Menu()
            menu.attach_to_widget(self)
            for cmd in commands:
                item = Gtk.MenuItem(label=cmd)
                menu.append(item)
                item.connect("activate", self.on_menu_item_activate, cmd)
            return menu

        x, y = self.window_to_buffer_coords(
            Gtk.TextWindowType.TEXT, event.x, event.y)
        found, i = self.get_iter_at_location(x, y)
        if found:
            for t in i.get_tags():
                word = self.words_by_tag[t]
                commands = word.active_commands(self.game)
                if len(commands) > 0:
                    menu = create_menu(commands)
                    menu.show_all()
                    menu.popup_at_pointer(event)
                    self.stop_emission_by_name("button-press-event")

    def on_menu_item_activate(self, m, c):
        self.perform_command(c)
