def read_num(file):
        line = file.readline()
        return int(line)

def read_string_plus(file):
        buffer = []
        extra = ""
        while True:
                line = file.readline()
                if line == "": break
                
                if len(buffer) == 0:
                        if line[0] == "\"": # remove opening quote
                                line = line[1:]
                        else: # did not start with opening quote?
                                raise ValueError(f"'{line}' is not a string.")

                endquotepos = line.rfind("\"")
                if endquotepos < 0:
                        buffer.append(line)
                else:
                        buffer.append(line[:endquotepos])
                        extra = line[endquotepos+1:]                
                        break

        return ("".join(buffer), extra)

def read_string(file):
        return read_string_plus(file)[0]

def split_number(number, multiplier):
        low = int(number % multiplier)
        high = int(number / multiplier)
        return (high, low)

def group_words(words):
        grouped = []
        buffer = []
        for word in words:
                if word not in (".", "*."): # This must be the padding, I think
                        if word[0] == "*": buffer.append(word[1:])
                        elif len(buffer) == 0: buffer.append(word)
                        else:
                                grouped.append(buffer)
                                buffer = [word]

        if len(buffer) > 0:
                grouped.append(buffer)

        return grouped

class ExtractedFile():
        def __init__(self, file):
                read_num(file) # unknown value
                self.max_item_index = read_num(file)
                self.max_action_index = read_num(file)
                self.max_word_index = read_num(file)
                self.max_room_index = read_num(file)
                self.max_carried = read_num(file)
                self.starting_room = read_num(file)
                self.treasure_count = read_num(file)
                self.word_length = read_num(file)
                self.light_duration = read_num(file)
                self.max_message_index = read_num(file)
                self.treasure_room = read_num(file)

                self.actions = []
                for i in range(0, self.max_action_index+1):
                        self.actions.append(ExtractedAction(file))

                raw_verbs = []
                raw_nouns = []
                for i in range(0, self.max_word_index+1):
                        raw_verbs.append(read_string(file))
                        raw_nouns.append(read_string(file))
                self.verbs = group_words(raw_verbs)
                self.nouns = group_words(raw_nouns)

                self.rooms = []
                for i in range(0, self.max_room_index+1):
                        self.rooms.append(ExtractedRoom(file))

                self.messages = []
                for i in range(0, self.max_message_index+1):
                        self.messages.append(read_string(file))

                self.items = []
                for i in range(0, self.max_item_index+1):
                        self.items.append(ExtractedItem(file))

                for a in self.actions:
                        a.comment = read_string(file).strip()
        
class ExtractedAction():
        def __init__(self, file):
                input_num = read_num(file)
                self.verb, self.noun = split_number(input_num, 150)
                condition_nums = [
                        read_num(file),
                        read_num(file),
                        read_num(file),
                        read_num(file),
                        read_num(file)
                ]
                self.conditions = [split_number(c, 20) for c in condition_nums]

                action_nums = [
                        read_num(file),
                        read_num(file)
                ]
                self.actions = [s for a in action_nums for s in split_number(a, 150)]

class ExtractedRoom():
        def __init__(self, file):
                self.north = read_num(file)
                self.south = read_num(file)
                self.east = read_num(file)
                self.west = read_num(file)
                self.up = read_num(file)
                self.down = read_num(file)
                self.description = read_string(file)

class ExtractedItem():
        def __init__(self, file):
                self.name, extra = read_string_plus(file)
                self.room = int(extra)
                self.word = None

                if self.name.endswith("/"):
                        wordstart = self.name.rfind("/", 0, len(self.name) - 1)
                        self.word = self.name[wordstart + 1:len(self.name) - 1]
                        self.name = self.name[:wordstart]

