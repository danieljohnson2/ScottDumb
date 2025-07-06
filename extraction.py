class ExtractedFile:
    """Contiains all the data from file which it reads when constructed.

    max_carried - max # of items carried
    starting_room - room # when player starts
    treasure_count - # of treasures
    word_length - # of character in vocabulary words
    light_duration - # of turns the lamp (item 9) will run
    treasure_room - room # where treasure must be placed

    actions - list of ExtractedActions
    nouns - the nouns in index order
    verbs- the verbs in index order
    grouped_nouns - groups of synonyms (a list of lists)
    grouped_verbs - groups of synonyms (a list of lists)
    rooms - list of ExtractedRooms
    messages - list of messages
    items - list of ExractedItems
    """

    def __init__(self, file):
        read_num(file)  # unknown value
        max_item_index = read_num(file)
        max_action_index = read_num(file)
        max_word_index = read_num(file)
        max_room_index = read_num(file)
        self.max_carried = read_num(file)
        self.starting_room = read_num(file)
        self.treasure_count = read_num(file)
        self.word_length = read_num(file)
        self.light_duration = read_num(file)
        max_message_index = read_num(file)
        self.treasure_room = read_num(file)

        self.actions = []
        for i in range(0, max_action_index + 1):
            self.actions.append(ExtractedAction(file))

        self.verbs = []
        self.nouns = []
        for i in range(0, max_word_index + 1):
            self.verbs.append(read_string(file))
            self.nouns.append(read_string(file))
        self.grouped_verbs = group_words(self.verbs)
        self.grouped_nouns = group_words(self.nouns)

        self.rooms = []
        for i in range(0, max_room_index + 1):
            self.rooms.append(ExtractedRoom(file))

        self.messages = []
        for i in range(0, max_message_index + 1):
            self.messages.append(read_string(file))

        self.items = []
        for i in range(0, max_item_index + 1):
            self.items.append(ExtractedItem(file))

        for a in self.actions:
            a.comment = read_string(file).strip()


class ExtractedAction:
    """Contains the bytecode for a unit of game logic.

    verb - verb number the player must enter, or 0 for 'occurances'
    noun - noun number the player must enter, 0 if none. If
       verb is 0, this is a % chance to execute each turn.

    conditions - list of tuples (condition-op, value)
    actions = list of action bytecodes
    """

    def __init__(self, file):
        input_num = read_num(file)
        self.verb, self.noun = split_number(input_num, 150)
        condition_nums = [
            read_num(file),
            read_num(file),
            read_num(file),
            read_num(file),
            read_num(file),
        ]
        self.conditions = [split_number(c, 20) for c in condition_nums]

        action_nums = [read_num(file), read_num(file)]
        self.actions = [s for a in action_nums for s in split_number(a, 150)]


class ExtractedRoom:
    """Contains the data for a room.

    description - room text
    north - room # north of this one, 0 for no exit.
    south - room # south of this one.
    east - room # east of this one.
    west - room # west of this one.
    up - room # up of this one.
    down - room # down of this one.
    """

    def __init__(self, file):
        self.north = read_num(file)
        self.south = read_num(file)
        self.east = read_num(file)
        self.west = read_num(file)
        self.up = read_num(file)
        self.down = read_num(file)
        self.description = read_string(file)


class ExtractedItem:
    """Contains the data for an item.

    description - item description, displayed in 'look' text.
    starting_room - room where item starts.
    carry_word - word used to refer to this item when getting or
                 dropping it; if None item can't be carried.
    """

    def __init__(self, file):
        self.description, extra = read_string_plus(file)
        self.starting_room = int(extra)
        self.carry_word = None

        if self.description.endswith("/"):
            wordstart = self.description.rfind("/", 0, len(self.description) - 1)
            self.carry_word = self.description[
                wordstart + 1 : len(self.description) - 1
            ]
            self.description = self.description[:wordstart]


# Utility Functions


def read_num(file):
    """Reads a line from 'file', converting it to an integer."""
    line = file.readline()
    return int(line)


def read_string_plus(file):
    """Reads a string from 'file', which can be a multi-line string. It must be
    quoted with double-quotes, and may not contain them.

    The first line must start with a double quote, but there can be extra text
    after the closing quote.

    this function returns a tuple of the content text and this extra text.
    """

    buffer = []
    extra = ""
    while True:
        line = file.readline()
        if line == "":
            break

        if len(buffer) == 0:
            if line[0] == '"':  # remove opening quote
                line = line[1:]
            else:  # did not start with opening quote?
                raise ValueError(f"'{line}' is not a string.")

        endquotepos = line.rfind('"')
        if endquotepos < 0:
            buffer.append(line)
        else:
            buffer.append(line[:endquotepos])
            extra = line[endquotepos + 1 :]
            break

    return ("".join(buffer), extra)


def read_string(file):
    """Reads a string from the file, discarding any extra text after it on its last line."""
    return read_string_plus(file)[0]


def split_number(number, multiplier):
    """Decodes a number into two. The number = high * multiplier + low, and
    This method returns the tuple (high, low).
    """

    low = int(number % multiplier)
    high = int(number / multiplier)
    return (high, low)


def group_words(words):
    """Takes a list of words, and groups them, returning a list-of-lists.

    The idea is that each word starting with '*' is a synonym for the previous word,
    and we group these synonyms together with their base word.

    The word '.' is padding, and we discard it if found.
    """

    grouped = []
    buffer = []
    for word in words:
        if word not in (".", "*."):  # This must be the padding, I think
            if word == "":
                pass
            elif word[0] == "*":
                buffer.append(word[1:])
            elif len(buffer) == 0:
                buffer.append(word)
            else:
                grouped.append(buffer)
                buffer = [word]

    if len(buffer) > 0:
        grouped.append(buffer)

    return grouped
