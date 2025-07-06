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
        Gtk.TextView.__init__(
            self, buffer=self.buffer, editable=False, cursor_visible=False, **kwargs
        )
        self.set_wrap_mode(Gtk.WrapMode.WORD)

        click_gesture = Gtk.GestureClick(button=0)
        click_gesture.connect("pressed", self.on_pressed)
        self.add_controller(click_gesture)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self.on_motion)
        self.add_controller(motion_controller)

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

        tag_table = self.buffer.get_tag_table()

        for tag in self.words_by_tag:
            del self.words_by_tag[tag].tags[self.buffer]
        self.words_by_tag = {}

        tag_table.foreach(lambda tag: tag_table.remove(tag))

    def on_motion(self, controller, mouse_x, mouse_y):
        x, y = self.window_to_buffer_coords(Gtk.TextWindowType.TEXT, mouse_x, mouse_y)
        found, i = self.get_iter_at_location(x, y)
        if found and len(i.get_tags()) > 0:
            cursor_name = "pointer"
        else:
            cursor_name = "text"
        cursor = Gdk.Cursor.new_from_name(cursor_name, None)
        self.set_cursor(cursor)

    def on_pressed(self, click, count, click_x, click_y):
        click.set_state(Gtk.EventSequenceState.CLAIMED)

        if count != 1:
            return

        def on_menu_item_clicked(m, c):
            self.perform_command(c)
            menu.popdown()

        def create_menu(commands):
            menu = Gtk.Popover()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_spacing(3)
            menu.set_parent(self)
            menu.set_child(vbox)
            for cmd in commands:
                item = Gtk.Button(label=cmd)
                item.add_css_class("flat")
                item.add_css_class("menu-button")                
                vbox.append(item)
                item.connect("clicked", on_menu_item_clicked, cmd)
            return menu

        x, y = self.window_to_buffer_coords(Gtk.TextWindowType.TEXT, click_x, click_y)
        found, i = self.get_iter_at_location(x, y)
        if found:
            for t in i.get_tags():
                word = self.words_by_tag[t]
                commands = word.active_commands(self.game)
                if len(commands) > 0:
                    start = i.copy()
                    if not start.starts_word():
                        start.backward_word_start()
                    start_where = self.get_iter_location(start)
                    end = i.copy()
                    if not end.ends_word():
                        end.forward_word_end()
                    end_where = self.get_iter_location(end)
                    menu = create_menu(commands)
                    where = Gdk.Rectangle.union(start_where, end_where)
                    menu.set_pointing_to(where)
                    menu.popup()
                    # click.stop_emission_by_name("pressed")
