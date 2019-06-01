class Game():
        def __init__(self, extracted):
                self.word_length = extracted.word_length
                self.rooms = [Room(self, x.description) for x in extracted.rooms]
                self.inventory = Room(self, "Inventory")
                self.player_room = self.rooms[extracted.starting_room]

                self.nouns = dict()
                for i, g in enumerate(extracted.nouns):
                        word = Word(g)
                        for text in g:
                                self.nouns[normalize_word(text)] = word

                self.north_word = self.get_noun(extracted.nouns[1][0])
                self.south_word = self.get_noun(extracted.nouns[2][0])
                self.east_word = self.get_noun(extracted.nouns[3][0])
                self.west_word = self.get_noun(extracted.nouns[4][0])
                self.up_word = self.get_noun(extracted.nouns[5][0])
                self.down_word = self.get_noun(extracted.nouns[6][0])
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
                for i, g in enumerate(extracted.verbs):
                        word = Word(g)
                        for text in g:
                                self.verbs[normalize_word(text)] = word

                self.go_word = self.get_verb(extracted.verbs[1][0])
                self.get_word = self.get_verb(extracted.verbs[10][0])
                self.drop_word = self.get_verb(extracted.verbs[18][0])

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
                        item = Item(self, ei.name, self.get_noun(ei.carry_word))
                        if ei.starting_room == -1: item.room = inventory
                        else: item.room = self.rooms[ei.starting_room]
                        self.items.append(item)

        def is_direction(self, word):
                return word in self.directions

        def get_noun(self, text):
                if text is None: return None
                try: return self.nouns[normalize_word(text)]
                except KeyError: raise KeyError(f"I don't know what '{text}' means.")

        def get_verb(self, text):
                if text is None: return None
                try: return self.verbs[normalize_word(text)]
                except KeyError: raise KeyError(f"I don't know what '{text}' means.")

        def parse_command(self, command):
                parts = command.split()
                if len(parts) > 2:
                        raise ValueError("No more than two words!")
                
                verb = None
                noun = None

                if len(parts) >= 1:
                        try: verb = self.get_verb(parts[0])
                        except KeyError:
                                noun = self.get_noun(parts[0])
                                return (None, noun)

                if len(parts) >= 2:
                        noun = self.get_noun(parts[1])

                return (verb, noun)
                
        def perform_command(self, verb, noun):
                if (verb is None or verb == self.go_word) and self.is_direction(noun):
                        next = self.player_room.get_move(noun)
                        if next is None: raise ValueError(f"I can't go there!")
                        self.player_room = next
                        return self.player_room.look_text()
                else:
                        raise ValueError("I don't understand.")

class Word():
        def __init__(self, aliases):
                self.text = aliases[0]
                self.aliases = aliases

        def __str__(self): return self.text

class Room():        
        def __init__(self, game, description):
                self.game = game
                self.description = description
                self.north = None
                self.south = None
                self.east = None
                self.west = None
                self.up = None
                self.down = None

        def __repr__(self):
                return self.description[:32]

        def get_items(self):
                return [i for i in self.game.items if i.room == self]

        def get_move(self, word):
                choices = {
                        self.game.north_word: self.north,
                        self.game.south_word: self.south,
                        self.game.east_word: self.east,
                        self.game.west_word: self.west,
                        self.game.up_word: self.up,
                        self.game.down_word: self.down
                }
                return choices[word]

        def look_text(self):
                text = self.description
                if text.startswith("*"):
                        text = text[1:]
                else:
                        text = "I'm in a " + text

                items = []
                for item in self.get_items():
                        items.append(item.name + ".")

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

class Item():
        def __init__(self, game, name, carry_word):
                self.game = game       
                self.name = name         
                self.carry_word = carry_word
                self.room = None

def normalize_word(word):
        return word[:3].upper()
