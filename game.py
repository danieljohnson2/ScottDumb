from execution import Occurance, Command

class Game():
        """This is the root object containing the game state.

        word_length - the length of Word object text
        rooms - list of Rooms (but not 'inventory')
        inventory - a Room holding the player's inventory
        player_room - the room the player is in
        items - list of all Items
        messages - list of messages
        flags - list of 32 Flags
        logics - list of all game logics

        dark_flag - the flag (#15) that is set when it is dark
        lamp_item - the lamp (#9)

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
        """

        def __init__(self, extracted):
                self.word_length = extracted.word_length
                self.rooms = [Room(self, x) for x in extracted.rooms]
                self.inventory = Room(self, description = "Inventory")
                self.player_room = self.rooms[extracted.starting_room]
                self.needs_room_update = True
                self.wants_room_update = True
                self.game_over = False

                self.flags = [Flag() for n in range(0, 32)]
                self.dark_flag = self.flags[15]

                self.nouns = dict()
                for i, g in enumerate(extracted.grouped_nouns):
                        word = Word(g)
                        for text in g:
                                self.nouns[self.normalize_word(text)] = word

                self.north_word = self.get_noun("NOR")
                self.south_word = self.get_noun("SOU")
                self.east_word = self.get_noun("EAS")
                self.west_word = self.get_noun("WES")
                self.up_word = self.get_noun("UP")
                self.down_word = self.get_noun("DOW")
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
                        if ei.starting_room == -1: item.starting_room = inventory
                        else: item.starting_room = self.rooms[ei.starting_room]
                        item.room = item.starting_room
                        self.items.append(item)
                self.lamp_item = self.items[9]

                self.messages = extracted.messages

                self.logics = []
                for ea in extracted.actions:
                        if ea.verb == 0:
                                self.logics.append(Occurance(self, ea))
                        else:
                                self.logics.append(Command(self, extracted, ea))

                self.output_text = ""

        def output(self, text):
                """Adds text to the output buffer, with no newline."""
                self.output_text += text

        def output_line(self, line = ""):
                """Adds text to the output buffer, followed by a newline."""
                self.output_text += line + "\n"

        def extract_output(self):
                """Returns the output buffer, but also resets it."""
                out = self.output_text
                self.output_text = ""
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

                for l in self.logics:
                        if l.check_occurance():
                                l.execute()

        def perform_command(self, verb, noun):
                """Executes a command given. Either verb or noun can be None.
       
                This returns the text to be displayed to the user. It also
                updates the game state, and it can raise exceptions for errors.
                """

                for l in self.logics:
                        if l.check_command(verb, noun):
                                return l.execute()

                if verb is None or verb == self.go_word:
                        next = self.player_room.get_move(noun)
                        if next is None: raise WordError(noun, f"I can't go there!")
                        self.move_player(next)
                elif verb == self.get_word:
                        item = self.get_carry_item(noun)
                        if item is None: raise WordError(noun, "I can't pick that up.")
                        self.get_item(item)
                elif verb == self.drop_word:
                        item = self.get_carry_item(noun)
                        self.drop_item(item)
                else:
                        raise ValueError("I don't understand.")

        def get_score_text(self):
                return "Score not supported yet!"

        def get_inventory_text(self):
                """Returns the text to display when the user takes inventory."""
                text = "I am carrying the following:\n"
                items = [i.description for i in self.inventory.get_items()]
                if len(items) > 0:
                        text += " ".join(items)
                else:
                        text += " Nothing at all!"
                return text

        def move_player(self, new_room):
                """Moves the player to a new room."""
                self.player_room = new_room
                self.needs_room_update = True

        def get_item(self, item, as_user = True):
                """Cause an item to enter the player inventory.

                If as_user is true, tihs checks that the item is available,
                and generates output too. If not, the 'get' is unchecked and silent.
                """
                if as_user and item.room != self.player_room:
                        raise ValueError("That isn't here.")
                item.room = self.inventory
                self.wants_room_update = True
                if as_user: self.output_line("Taken.")

        def drop_item(self, item, as_user = True):
                """Cause an item to enter the room the player is in.

                If as_user is true, tihs checks that the item is carried,
                and generates output too. If not, the 'drop' is unchecked and silent.
                """
                if as_user and (item is None or item.room != self.inventory):
                        raise ValueError("I'm not carrying that.")
                item.room = self.player_room
                self.wants_room_update = True
                if as_user: self.output_line("Dropped.")

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

        north, south, east, west, up, down - refernces to neighboring rooms
        """

        def __init__(self, game, extracted_room = None, description = None):
                if description is None and extracted_room is not None:
                        description = extracted_room.description
                        if description.startswith("*"):
                                description = description[1:]
                        else:
                                description = "I'm in a " + description

                GameObject.__init__(self, game, description)
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

        def get_look_text(self):
                """The text to describe the room and everything in it."""

                if self.game.dark_flag.state and self.game.lamp_item.room != self.game.inventory:
                        return "It is too dark to see!"

                text = self.description                

                items = []
                for item in self.get_items():
                        items.append(item.description + ".")

                if len(items) > 0:
                        text += "\n\nVisible items: " + " ".join(items)

                exits = []
                if self.north: exits.append("North")
                if self.south: exits.append("South")
                if self.east: exits.append("East")
                if self.west: exits.append("West")
                if self.up: exits.append("Up")
                if self.down: exits.append("Down")

                if len(exits) > 0:
                        text += "\n\nObvious exits: " + " ".join(exits)

                return text

class Item(GameObject):
        """Represents an item that can be moved from room to room.

        room - the room the item is in.
        starting_room - the room the item started in
        carry_word - word used to get or drop the item;
                     None if the item can't be taken.
        """

        def __init__(self, game, extracted_item):
                GameObject.__init__(self, game, extracted_item.description)
                self.carry_word = game.get_noun(extracted_item.carry_word)
                self.room = None

class Flag():
        def __init__(self):
                self.state = False
