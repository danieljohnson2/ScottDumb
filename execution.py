from random import randint

class Logic():
        def __init__(self, game, extracted_action):
                self.game = game
                self.conditions = []
                args = []
                for val, op in extracted_action.conditions:
                        if op == 0: args.append(val)
                        else: self.conditions.append(self.create_condition(op, val))

                def get_arg():
                        val = args[0]
                        del args[0]
                        return val

                self.actions = []
                for op in extracted_action.actions:
                        self.actions.append(self.create_action(op, get_arg))
                
        def is_available(self):
                for c in self.conditions:
                        if not c():
                                return False
                return True

        def check_occurance(self): return False

        def check_command(self, verb, noun): return False

        def check_continuation(self): return False

        def execute(self):
                text = []
                for a in self.actions:
                        msg = a()
                        if msg is not None: text.append(msg)

                return " ".join(text)

        def create_condition(self, op, val):
                def undefined(): raise ValueError(f"Undefined condition op: {op}")

                if op == 1: return lambda: self.game.items[val].room == self.game.inventory
                if op == 2: return lambda: self.game.items[val].room == self.game.player_room
                if op == 3: return lambda: self.game.items[val].room in [self.game.player_room, self.game.inventory]
                if op == 4: return lambda: self.game.player_room == self.game.rooms[val]
                if op == 5: return lambda: self.game.items[val].room != self.game.player_room
                if op == 6: return lambda: self.game.items[val].room != self.game.inventory
                if op == 7: return lambda: self.game.player_room != self.game.rooms[val]
                if op == 8: return lambda: self.game.flags[val].state
                if op == 9: return lambda: not self.game.flags[val].state
                if op == 10: return lambda: len(self.game.inventory.get_items()) > 0
                if op == 11: return lambda: len(self.game.inventory.get_items()) == 0
                if op == 12:
                        return lambda: self.game.items[val].room not in [self.game.player_room, self.game.inventory]
                if op == 13: return lambda: self.game.items[val].room == None
                if op == 14: return lambda: self.game.items[val].room != None
                if op == 17: return lambda: self.game.items[val].room == self.game.items[val].starting_room
                if op == 18: return lambda: self.game.items[val].room != self.game.items[val].starting_room
                return undefined

        def create_action(self, op, value_source):
                def get_item(): self.game.get_item(self.game.items[item_index])
                def superget_item(): self.game.get_item(self.game.items[item_index], force = True)
                def drop_item(): self.game.drop_item(self.game.items[item_index])
                def move_player(): self.game.move_player(self.game.rooms[room_index])
                def remove_item(): self.game.move_item(self.game.items[item_index], None)
                def set_flag(): self.game.flags[flag_index].state = True
                def reset_flag(): self.game.flags[flag_index].state = False
                def die():
                        self.game.move_player(self.game.rooms[len(self.game.rooms) - 1])
                        self.game.flags[15].state = False # darkness flag
                def game_over(): self.game.game_over = True
                def check_score() : self.game.check_score()
                def move_item(): self.game.move_item(self.game.items[item_index], self.game.rooms[room_index])
                def describe_room(): self.game.needs_room_update = True
                def clear_screen(): pass # we don't do this
                def save_game(): self.game.save_game("scott.sav")
                def continue_actions(): self.game.continuing_commands = True
                def swap_items(): self.game.swap_items(self.game.items[item1_index], self.game.items[item2_index])
                def refill_lamp():
                        self.game.light_remaining = self.game.light_duration
                        self.game.move_item(self.game.lamp_item, self.game.inventory)
                def undefined(): raise ValueError(f"Undefined action op: {op}")

                if op == 0: return lambda: None
                if op <= 51: return lambda: self.game.output_line(self.game.messages[op])
                if op == 52:
                        item_index = value_source()
                        return get_item
                if op == 53:
                        item_index = value_source()
                        return drop_item
                if op == 54:
                        room_index = value_source()
                        return move_player
                if op == 55 or op == 59:
                        item_index = value_source()
                        return remove_item
                if op == 56:
                        flag_index = 15 # darkness flag
                        return set_flag
                if op == 57:
                        flag_index = 15 # darkness flag
                        return reset_flag
                if op == 58:
                        flag_index = value_source()
                        return set_flag
                if op == 60:
                        flag_index = value_source()
                        return reset_flag
                if op == 61: return die
                if op == 62:
                        item_index = value_source()
                        room_index = value_source()
                        return move_item
                if op == 63: return game_over
                if op == 64 or op == 76: return describe_room
                if op == 65: return check_score
                if op == 66: return lambda: self.game.output_line(self.game.get_inventory_text())
                if op == 67:
                        flag_index = 0
                        return set_flag
                if op == 68:
                        flag_index = 0
                        return reset_flag
                if op == 69: return refill_lamp
                if op == 70: return clear_screen
                if op == 71: return save_game
                if op == 72:
                        item1_index = value_source()
                        item2_index = value_source()
                        return swap_items
                if op == 73: return continue_actions
                if op == 74:
                        item_index = value_source()
                        return superget_item
                if op == 84: return lambda: self.game.output(self.game.parsed_noun)
                if op == 85: return lambda: self.game.output_line(self.game.parsed_noun)
                if op == 86: return lambda: self.game.output_line()
                if op >= 102: return lambda: self.game.output_line(self.game.messages[op - 50])
                return undefined

class Occurance(Logic):
        def __init__(self, game, extracted_action):
                Logic.__init__(self, game, extracted_action)
                self.chance = extracted_action.noun
        
        def check_occurance(self):
                return self.is_available() and randint(0, 100) <= self.chance

class Command(Logic):
        def __init__(self, game, extracted, extracted_action):
                Logic.__init__(self, game, extracted_action)
                verb_index = extracted_action.verb
                noun_index = extracted_action.noun
                self.verb = game.get_verb(extracted.verbs[verb_index])
                self.noun = game.get_noun(extracted.nouns[noun_index]) if noun_index > 0 else None
        
        def check_command(self, verb, noun):
                if self.verb == verb:
                        if self.noun is None or self.noun == noun:
                                return self.is_available()
                return False

class CommandContinuation(Logic):
        def __init__(self, game, extracted_action):
                Logic.__init__(self, game, extracted_action)
        
        def check_continuation(self):
                return self.is_available()

