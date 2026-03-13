#!/usr/bin/python3

from gi.repository import Pango
from gi.repository import Gdk
from gi.repository import Gtk


class WordyTextView(Gtk.TextView):
    def __init__(self, game, perform_command, **kwargs):
        self.game = game
        self.perform_command = perform_command
        self.words_by_tag = {}
        self.buffer = Gtk.TextBuffer()
        Gtk.TextView.__init__(self, buffer=self.buffer, editable=False, **kwargs)
        self.set_wrap_mode(Gtk.WrapMode.WORD)

        click = Gtk.GestureClick()
        click.connect("pressed", self.on_button_pressed)
        self.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        self.add_controller(motion)

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
        while len(words) > 0 and words[0].is_newline:
            del words[0]

        while len(words) > 0 and words[-1].is_newline:
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

            if word.is_newline:
                word_index = 0
            else:
                word_index += 1

    def clear(self):
        """Clears the text from this view."""

        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.delete(start, end)

        for tag in self.words_by_tag:
            del self.words_by_tag[tag].tags[self.buffer]
        self.words_by_tag = {}

        tag_table = self.buffer.get_tag_table()
        tag_table.foreach(lambda tag: tag_table.remove(tag))

    def on_motion(self, controller, x, y):
        bx, by = self.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y)
        )
        found, i = self.get_iter_at_location(bx, by)
        if found and len(i.get_tags()) > 0:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
        else:
            cursor = Gdk.Cursor.new_from_name("text", None)
        self.set_cursor(cursor)

    def on_button_pressed(self, gesture, n_press, x, y):
        bx, by = self.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y)
        )
        found, i = self.get_iter_at_location(bx, by)
        if found:
            for t in i.get_tags():
                word = self.words_by_tag[t]
                commands = word.active_commands(self.game)
                if len(commands) > 0:
                    gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                    self.show_command_popover(commands, x, y)

    def show_command_popover(self, commands, x, y):
        popover = Gtk.Popover()
        popover.set_parent(self)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for cmd in commands:
            btn = Gtk.Button(label=cmd)
            btn.add_css_class("flat")
            btn.connect(
                "clicked",
                lambda b, c=cmd, p=popover: (p.popdown(), self.perform_command(c)),
            )
            box.append(btn)

        popover.set_child(box)
        popover.connect("closed", lambda p: p.unparent())
        popover.popup()

    def on_menu_item_activate(self, m, c):
        self.perform_command(c)
