from PySide6.QtWidgets import QTextEdit, QMenu, QSizePolicy
from PySide6.QtGui import QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtCore import Qt

WORD_ID_PROPERTY = QTextFormat.Property.UserProperty + 1


class WordyTextView(QTextEdit):
    def __init__(self, game, perform_command, auto_height=False, parent=None, **kwargs):
        super().__init__(parent)
        self.game = game
        self.perform_command = perform_command
        self.words_by_id = {}
        self.next_word_id = 1

        self.setReadOnly(True)
        self.setMouseTracking(True)

        if "width_request" in kwargs:
            self.setFixedWidth(kwargs["width_request"])

        self.auto_height_mode = auto_height
        if auto_height:
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
            self.document().documentLayout().documentSizeChanged.connect(
                self._adjust_height
            )

    def _adjust_height(self, size):
        h = int(size.height()) + self.frameWidth() * 2 + 2
        self.setFixedHeight(max(h, 20))

    def append_line(self):
        """Adds a line break to the view. If it is now empty, this does nothing."""
        if self.document().characterCount() > 1:
            cursor = QTextCursor(self.document())
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n")

    def append_words(self, words):
        """
        Appends a sequence of words to the view. If there are any
        active commands on any words, this will record tags for them and
        underline them so they can be handled.
        """
        words = list(words)
        while words and words[0].is_newline:
            del words[0]
        while words and words[-1].is_newline:
            del words[-1]

        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)

        word_index = 0
        for word in words:
            if word_index > 0:
                cursor.insertText(" ")

            fmt = self._get_format(word)
            if fmt is None:
                cursor.insertText(str(word))
            else:
                cursor.insertText(str(word), fmt)

            if word.is_newline:
                word_index = 0
            else:
                word_index += 1

    def _get_format(self, word):
        if word.is_plain(self.game):
            return None

        doc = self.document()
        if doc in word.tags:
            word_id = word.tags[doc]
        else:
            word_id = self.next_word_id
            self.next_word_id += 1
            self.words_by_id[word_id] = word
            word.tags[doc] = word_id

        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        fmt.setProperty(WORD_ID_PROPERTY, word_id)
        return fmt

    def clear(self):
        """Clears the text from this view."""
        doc = self.document()
        for word in self.words_by_id.values():
            word.tags.pop(doc, None)
        self.words_by_id = {}
        self.next_word_id = 1
        super().clear()

    def _word_at_position(self, pos):
        cursor = self.cursorForPosition(pos)
        fmt = cursor.charFormat()
        word_id = fmt.intProperty(WORD_ID_PROPERTY)
        if word_id and word_id in self.words_by_id:
            return self.words_by_id[word_id]
        return None

    def mouseMoveEvent(self, event):
        word = self._word_at_position(event.position().toPoint())
        if word and not self.game.game_over:
            commands = word.active_commands(self.game)
            if commands:
                self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                return
        self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.game.game_over:
            super().mousePressEvent(event)
            return

        word = self._word_at_position(event.position().toPoint())
        if word:
            commands = word.active_commands(self.game)
            if commands:
                menu = QMenu(self)
                for cmd in commands:
                    action = menu.addAction(cmd)
                    action.triggered.connect(
                        lambda checked, c=cmd: self.perform_command(c)
                    )
                menu.popup(event.globalPosition().toPoint())
                return

        super().mousePressEvent(event)
