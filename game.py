from execution import Occurance, Command, CommandContinuation
from time import sleep

class Game():
    """This is the root object containing the game state.

    word_length - the length of Word object text
    rooms - list of Rooms (but not 'inventory')
    inventory - a Room holding the player's inventory
    player_room - the room the player is in
    items - list of all Items
    messages - list of messages
    flags - list of 32 Flags
    counters - list of 16 counters
    logics - list of all game logics

    saved_player_room - a room the player was in
    saved_player_rooms - a list of more rooms the player was in

    dark_flag - the flag (#15) that is set when it is dark
    lamp_exhausted_flag - the flag (#16) set when lamp runs out
    lamp_item - the lamp (#9)
    light_duration - the initial light_remaining
    light_remaining - number of turns of lamp use left
    max_carried - number of items the player can carry
    treasure_count - total number of treasures
    treasure_room - room where treasure must be placed

    north_word, south_word,
    east_word, west_word,
    up_word, down_word,
    go_word, get_word, drop_word - predefined Word objects
    directions - a list of all direction words above

    needs_room_update - set when the room look text needs to be reshown;
                        you clear this once you have done so.
    wants_room_update - set when the room has changed, but immediate
                        redisplay is not needed. Again, clear this yourself.
    game_over - set when the game is over and should exit

    continuing_commands - set to continue executing actions, but only 'continuing' ones
    """

    def __init__(self, extracted):
        self.word_length = extracted.word_length
        self.rooms = [Room(self, i, x) for i, x in enumerate(extracted.rooms)]
        self.inventory = Room(self, -1, description = "Inventory")
        self.player_room = self.rooms[extracted.starting_room]
        self.saved_player_room = self.player_room
        self.saved_player_rooms = [self.player_room for n in range(0, 16)]
        self.needs_room_update = True
        self.wants_room_update = True
        self.game_over = False

        self.counter = Counter()
        self.counters = [Counter() for n in range(0, 16)]
        
        self.flags = [Flag() for n in range(0, 32)]
        self.dark_flag = self.flags[15]
        self.lamp_exhausted_flag = self.flags[16]

        self.nouns = dict()
        for i, g in enumerate(extracted.grouped_nouns):
            word = Word(g)
            for text in g:
                self.nouns[self.normalize_word(text)] = word

        self.north_word = self.get_noun("NORTH")
        self.south_word = self.get_noun("SOUTH")
        self.east_word = self.get_noun("EAST")
        self.west_word = self.get_noun("WEST")
        self.up_word = self.get_noun("UP")
        self.down_word = self.get_noun("DOWN")
        self.directions = [
            self.north_word, self.south_word,
            self.east_word, self.west_word,
            self.up_word, self.down_word
        ]

        # Hardcoded direction aliases
        self.nouns["N"] = self.north_word
        self.nouns["S"] = self.south_word
        self.nouns["E"] = self.east_word
        self.nouns["W"] = self.west_word
        self.nouns["U"] = self.up_word
        self.nouns["D"] = self.down_word

        self.verbs = dict()
        for i, g in enumerate(extracted.grouped_verbs):
            word = Word(g)
            for text in g:
                self.verbs[self.normalize_word(text)] = word

        self.go_word = self.get_verb("GO")
        self.get_word = self.get_verb("GET")
        self.drop_word = self.get_verb("DROP")

        for i, r in enumerate(self.rooms):
            src = extracted.rooms[i]

            def resolve_room(index):
                return None if index <= 0 else self.rooms[index]

            r.north = resolve_room(src.north)
            r.south = resolve_room(src.south)
            r.east = resolve_room(src.east)
            r.west = resolve_room(src.west)
            r.up = resolve_room(src.up)
            r.down = resolve_room(src.down)

        self.items = []
        for ei in extracted.items:
            item = Item(self, ei)
            if ei.starting_room == -1: item.starting_room = self.inventory
            elif ei.starting_room == 0: item.starting_room = None
            else: item.starting_room = self.rooms[ei.starting_room]
            item.room = item.starting_room
            self.items.append(item)
        self.lamp_item = self.items[9]
        self.light_duration = extracted.light_duration
        self.light_remaining = self.light_duration
        self.max_carried = extracted.max_carried

        self.treasure_room = self.rooms[extracted.treasure_room]
        self.treasure_count = extracted.treasure_count

        self.messages = extracted.messages

        self.occurances = []
        self.commands = []
        for ea in extracted.actions:
            if ea.verb == 0:
                if ea.noun == 0: self.commands.append(CommandContinuation(self, ea))
                else: self.occurances.append(Occurance(self, ea))
            else:
                self.commands.append(Command(self, extracted, ea))

        # try to assign command-words where we can find 'em, so items
        # you can't carry can still be clicked.
        carry_words = {item.carry_word for item in self.items 
                                       if item.carry_word is not None}
        
        for n in self.nouns.values():
            if n not in self.directions and n not in carry_words:
                for nm in self.items:
                    if nm.get_candidate_name(n) is not None:
                        nm.command_words.add(n)
                   
        # We will reuse the carry words, but only if that's the only
        # word available for the item.     
        for n in carry_words:
            if n not in self.directions:
                for nm in self.items:
                    if len(nm.command_words) == 0 and nm.get_candidate_name(n) is not None:
                        nm.command_words.add(n)
        
        self.output_words = []

    def output(self, text):
        """Adds text to the output buffer, with no newline."""
        for part in text.split():
            self.output_word(OutputWord(part))

    def output_line(self, line = ""):
        """Adds text to the output buffer, followed by a newline."""
        self.output(line)
        self.output_word(OutputWord("\n"))

    def output_word(self, word):
        """Adds a single OutputWord to the output buffer."""
        self.output_words.append(word)

    def extract_output(self):
        """Returns the output buffer, but also resets it."""
        out = self.output_words
        self.output_words = []
        return out

    def get_carry_item(self, word):
        """Looks up the item that can be picked up via "GET <word>"
        
        Returns None if no such item can be found. Only carriable items
        can be returned. The names can be ambiguous, so we prefer the item
        that is present.
        """

        if word is not None:
            for i in self.items:
                if (i.room == self.player_room or i.room == self.inventory) and i.carry_word == word:
                    return i

            for i in self.items:
                if i.carry_word == word:
                    return i
        return None
        
    def get_command_item(self, word):
        """Looks up the item that can be referred to by a word
        
        Returns None if no such item can be found. Words can be ambiguous, so we prefer the item
        that is present.
        """

        if word is not None:
            for i in self.items:
                if (i.room == self.player_room or i.room == self.inventory) and i.command_word == word:
                    return i

            for i in self.items:
                if i.command_word == word:
                    return i
        return None
        
    def normalize_word(self, word):
        """Converts the word to the the right length, and uppercase."""
        return word[:self.word_length].upper()

    def get_noun(self, text):
        """Returns the Word for the text given; this will normalize text
        and accounts for aliases. Returns None if text is None, but
        raises ValueError if it is not a known noun, even if it is a verb.
        """

        if text is None: return None
        try: return self.nouns[self.normalize_word(text)]
        except KeyError: raise ValueError(f"I don't know what '{text}' means.")

    def get_verb(self, text):
        """Returns the Word for the text given; this will normalize text
        and accounts for aliases. Returns None if text is None, but
        raises ValueError if it is not a known verb, even if it is a noun.
        """

        if text is None: return None
        try: return self.verbs[self.normalize_word(text)]
        except KeyError: raise ValueError(f"I don't know what '{text}' means.")

    def parse_command(self, command):
        """Parses a two-word command into a verb Word and a noun Word.
        This returns a tuple (verb, noun); if one or the other word is missing
        it is None in the tuple- we don't return a shorter tuple.

        Raises ValueError if the comamnd is too long. If it is empty, returns
        (None, None).
        """

        parts = command.split()
        if len(parts) > 2:
            raise ValueError("No more than two words!")
        
        self.parsed_verb = parts[0] if len(parts) > 0 else None
        self.parsed_noun = parts[1] if len(parts) > 1 else None
        verb = None
        noun = None

        if self.parsed_verb is not None:
            try: verb = self.get_verb(self.parsed_verb)
            except ValueError:
                noun = self.get_noun(self.parsed_verb)
                return (None, noun)

        if self.parsed_noun is not None:
            noun = self.get_noun(self.parsed_noun)

        return (verb, noun)
            
    def perform_occurances(self):
        """This must be called before taking user input, and runs 'occurance'
        logic that handles events other that carrying out commands.

        This returns text to be displayed to the user before accepting input.
        """

        if self.lamp_item.room == self.inventory and self.light_remaining > 0:
            self.light_remaining -= 1
            if self.light_remaining <= 0:
                self.lamp_exhausted_flag.state = True

        self.execute_logic(self.occurances, lambda l: l.check_occurance(), halt_after_first=False)

    def perform_command(self, verb, noun):
        """Executes a command given. Either verb or noun can be None.

        This returns the text to be displayed to the user. It also
        updates the game state, and it can raise exceptions for errors.
        """

        halted = self.execute_logic(self.commands, lambda l: l.check_command(verb, noun))
        if halted: return

        if verb is None or verb == self.go_word:
            next = self.player_room.get_move(noun)
            if next is None: raise WordError(noun, f"I can't go there!")
            self.move_player(next)
        elif verb == self.get_word:
            item = self.get_carry_item(noun)
            if item is None: raise WordError(noun, "I can't pick that up.")
            if item.room == self.inventory: raise ValueError("I already have it.")
            if item.room != self.player_room: raise ValueError("I don't see it here!")

            self.get_item(item)
            self.output_line("OK")
        elif verb == self.drop_word:
            item = self.get_carry_item(noun)
            if (item is None or item.room != self.inventory):
                raise ValueError("I'm not carrying it!")
    
            self.drop_item(item)
            self.output_line("OK")
        else:
            raise ValueError("I don't understand.")

    def execute_logic(self, logics, checker, halt_after_first=True):
        """
        This executes a list of logics, as permitted by its conditions. Logics
        can only run if the 'checker' function given returns treu for it.
        If half_after_first is true, this method halts after the first action.

        This method returns true if it executes any action, and False if it found
        none to execute.
        """
        self.continuing_commands = False
        executed_any = False

        for l in logics:
            if self.continuing_commands:
                if l.is_continuation():
                    if l.is_available(): l.execute()
                else:
                    break
            elif checker(l):
                executed_any = True
                l.execute()
                if halt_after_first and not self.continuing_commands: break

        return executed_any

    def check_score(self):
        treasures_found = sum(1 for t in self.treasure_room.get_items() if t.is_treasure())
        score = int(treasures_found * 100 / self.treasure_count)
        self.output_line(f"I stored {treasures_found} treasures.")
        self.output_line(f"On a scale of 0-100, that's: {score}")
        if score == 100 and self.player_room == self.treasure_room:
            self.game_over = True

    def get_inventory_words(self):
        """Returns the text to display when the user takes inventory."""
        words = [OutputWord(s) for s in "I am carrying the following:".split()]
        items = self.inventory.get_items()
        if len(items) > 0:
            words.append(OutputWord("\n"))
            for item in items:
                words.append(item.inventory_word)
        else:
            words.append(OutputWord("Nothing at all!"))
        return words
        
    def output_inventory_text(self):
        for word in self.get_inventory_words():
            self.output_word(word)
        self.output_line()
            
    def move_player(self, new_room):
        """Moves the player to a new room."""
        self.player_room = new_room
        self.needs_room_update = True

    def get_item(self, item, force = False):
        """Cause an item to enter the player inventory.

        If force is true, this will work even if the player inventory is full.
        """

        if not force and len(self.inventory.get_items()) >= self.max_carried:
            raise ValueError("I've too much to carry!")

        item.room = self.inventory
        self.wants_room_update = True
            
    def drop_item(self, item):
        """Cause an item to enter the room the player is in."""
        item.room = self.player_room
        self.wants_room_update = True

    def move_item(self, item, room):
        """Moves an item to a particular room. The room may be None."""
        item.room = room
        self.wants_room_update = True

    def swap_items(self, item1, item2):
        """Swaps two items, so each winds up ine the room the other was in."""
        tmp = item1.room
        item1.room = item2.room
        item2.room = tmp
        self.wants_room_update = True

    def save_game(self):
        """Saves the game to the file named using the ScottFree format."""
        def get_room_index(r):
            return 0 if r is None else r.index

        path = self.get_save_game_path()
        if path is None: return

        with open(path, "w") as file:
            # counters (and saved rooms, which we don't support yet.)
            for n in range(0, 16):
                file.write(f"{self.counters[n].value} 0\n")

            bitflags = 0
            for f in reversed(self.flags):
                bitflags = bitflags << 1
                if f.state: bitflags = bitflags | 1
            dark = 1 if self.dark_flag.state else 0
            player_room_index = get_room_index(self.player_room)

            file.write(f"{bitflags} {dark} {player_room_index} {self.counter.value} 0 {self.light_remaining}\n")

            for item in self.items:
                file.write(f"{get_room_index(item.room)}\n")

    def get_save_game_path(self):
        """Provides the path to the file when saving the game; can return None to cancel."""
        return "scott.sav"

    def load_game(self):
        """
        Loads the game from the file named, which is in the ScottFree format.
        Returns True if the game was loaded, and False if this was cancelled.
        """
        def find_room(index):
            if index == -1: return self.inventory
            elif index == 0: return None
            else: return self.rooms[index]

        path = self.get_load_game_path()
        if path is None: return False

        with open(path, "r") as file:
            # counters and saved rooms, which we don't support yet.
            for n in range(0, 16):
                line = file.readline().split()
                self.counters[n].value = int(line[0])
                
            state = file.readline().split()
            bitflags = int(state[0])
            for f in self.flags:
                f.state = (bitflags & 1) != 0
                bitflags = bitflags >> 1

            self.player_room = find_room(int(state[2]))
            self.counter.value = int(state[3])
            self.light_remaining = int(state[5])

            for item in self.items:
                item.room = find_room(int(file.readline()))

        self.game_over = False
        self.needs_room_update = True
        return True
                    
    def get_load_game_path(self):
        """Provides the path to the file when loading the game; can return None to cancel."""
        return "scott.sav"

    def sleep(self, seconds):
        """This method waits for a number of seconds; you can override this to keep your GUI alive."""
        sleep(2)
       
class Word():
    """Represents a word in the vocabulary; these are interned, so duplicate
    word objects do not exist.

    text - the word's text, abbreviated to the games word length.
    aliases - all variations of the word (including 'text'), abbreviated.
    """

    def __init__(self, aliases):
        self.text = aliases[0]
        self.aliases = aliases

    def __str__(self): return self.text
    def __repr__(self): return self.text

class WordError(Exception):
    """An error raised when a word is not valid, in lieu of KeyError, which
    cocks up the message."""
    def __init__(self, word, message):
        self.word = word
        self.message = message

    def __str__(self): return self.message

class GameObject():
    """A base class for things in the game that you can see.

    game - the game this object is part of
    description - the text displayed for this object
    """

    def __init__(self, game, description):
        self.game = game
        self.description = description
        
class Room(GameObject):
    """Represents a room in the game, with references to its neighboring rooms.
    Rooms do not change during gameplay.

    index - room number, used to save game
    north, south, east, west, up, down - refernces to neighboring rooms
    """

    def __init__(self, game, index, extracted_room = None, description = None):
        if description is None and extracted_room is not None:
            description = extracted_room.description
            if description.startswith("*"):
                description = description[1:]
            else:
                description = "I'm in a " + description

        GameObject.__init__(self, game, description)
        self.index = index
        self.north = None
        self.south = None
        self.east = None
        self.west = None
        self.up = None
        self.down = None

    def __repr__(self):
        return self.description[:32]

    def get_items(self):
        """Returns a list of items that are in this room."""
        return [i for i in self.game.items if i.room == self]

    def get_move(self, word):
        """Returns the neighboring room in the direction indicated by the Word given.

        Raises WordError if the word is invalid, but None if there's no neighbor that way.
        """

        choices = {
            self.game.north_word: self.north,
            self.game.south_word: self.south,
            self.game.east_word: self.east,
            self.game.west_word: self.west,
            self.game.up_word: self.up,
            self.game.down_word: self.down
        }

        try: return choices[word]
        except KeyError: raise WordError(word, f"'{word}' is not a direction.")

    def get_look_words(self):
        """The text to describe the room and everything in it."""

        if self.game.dark_flag.state and self.game.lamp_item.room != self.game.inventory:
            return [OutputWord("It is too dark to see!")]

        words = [OutputWord(self.description)]

        items = self.get_items()
        if len(items) > 0:
            words.append(OutputWord("\n"))
            words.append(OutputWord("\n"))
            words.append(OutputWord("Visible items:"))

            for item in items:
                words.append(item.room_word)

        exits = []
        if self.north: exits.append(OutputWord("North", direction=self.north))
        if self.south: exits.append(OutputWord("South", direction=self.south))
        if self.east: exits.append(OutputWord("East", direction=self.east))
        if self.west: exits.append(OutputWord("West", direction=self.west))
        if self.up: exits.append(OutputWord("Up", direction=self.up))
        if self.down: exits.append(OutputWord("Down", direction=self.down))

        if len(exits) > 0:
            words.append(OutputWord("\n"))
            words.append(OutputWord("\n"))
            words.append(OutputWord("Obvious exits:"))

            for exit in exits:
                words.append(exit)

        return words

class Item(GameObject):
    """Represents an item that can be moved from room to room.

    room - the room the item is in.
    starting_room - the room the item started in
    carry_word - word used to get or drop the item;
                 None if the item can't be taken.
    command_words - word used to refer to this item by commands
    room_word - ouput word output for the room description
    inventory_word - output word output for the inventory
    """

    def __init__(self, game, extracted_item):
        GameObject.__init__(self, game, extracted_item.description)
        self.carry_word = game.get_noun(extracted_item.carry_word)
        self.command_words = {self.carry_word} if self.carry_word is not None else set()
        self.room = None
        output_word = OutputWord(self.description, item=self)
        self.room_word = output_word
        self.inventory_word = output_word

    def is_treasure(self): return self.description.startswith("*")

    def get_command_name(self, word):
        """Picks a name to include in a command referring to this item.
        This is a word from the description that starts with the command_word."""
        name = self.get_candidate_name(word)
        return name if name is not None else str(word).upper()
        
    def get_candidate_name(self, word):
        """Picks a name for this item that resembles the word given."""
        if word is None: return None
        short_name = str(word).upper()
        for w in self.description.upper().split():
            s = w.strip("*!:;.?$#@")
            if s[0:len(short_name)] == short_name and "'" not in s:
                return s
        return None
        
class Flag():
    def __init__(self):
        self.state = False

class Counter():
    def __init__(self):
        self.value = 0

    def swap(self, game):
        tmp = game.counter.value
        game.counter.value = self.value
        self.value = tmp

class OutputWord():
    def __init__(self, text, item = None, direction = None):
        self.text = text
        self.item = item
        self.direction = direction
        self.tags = {}

    def is_plain(self, game): return len(self.active_commands(game)) == 0
    
    def active_commands(self, game):
        """
        Returns a list of commands this word can trigger, which
        may be empty for a 'plain' word.
        """
        if self.item is not None:
            commands = []
            for command_word in self.item.command_words:
                command_name = self.item.get_command_name(command_word)
                
                if self.item.carry_word is not None:
                    if self.item.room == game.inventory:
                        commands.append("DROP " + command_name)
                    else:
                        commands.append("GET " + command_name)
                    
                for cmd in game.commands:
                    if cmd.check_available_command(command_word):
                        command = str(cmd.verb) + " " + command_name
                        if command not in commands:
                            commands.append(command)
                    
            return commands
        elif self.direction is not None:
            return [str(self)]
        else:
            return []
        
    def is_newline(self): return self.text == "\n"

    def __str__(self):
        return self.text
