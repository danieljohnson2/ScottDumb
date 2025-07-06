import asyncio
from random import randint


class Logic:
    """This class contains the actual opcodes to execute for the game.

    Subclasses override methods to control when this can execute, but the
    actual execution is all here.
    """

    def __init__(self, game, extracted_action):
        self.game = game
        self.conditions = []
        args = []
        for val, op in extracted_action.conditions:
            if op == 0:
                args.append(val)
            else:
                self.conditions.append(self.create_condition(op, val))

        def get_arg():
            val = args[0]
            del args[0]
            return val

        self.actions = []
        for op in extracted_action.actions:
            self.actions.append(self.create_action(op, get_arg))

    @property
    def is_available(self):
        """Runs conditions for the logic; returns true if this logic can execute."""
        for c in self.conditions:
            if not c():
                return False
        return True

    def check_occurance(self):
        """True if this is an occurance that should run now.

        This rolls the dice for the chance of the occurance, so repeated
        calls don't always agree. Also checks availability.
        """
        return False

    def check_command(self, verb, noun):
        """True if this is a command to handle the user command indicated
        by verb and noun. Also checks availability."""
        return False

    def check_available_command(self, noun):
        """True if this is a command to handle the user command indicated
        by noun only. Also checks availability."""
        return False

    @property
    def is_continuation(self):
        """True if this is a continuation action; is_available must be checked separately."""
        return False

    async def execute(self):
        """Runs the action. This applies changes to self.game. If any of the actions are co-routines,
        this will await them."""
        for a in self.actions:
            t = a()
            if asyncio.iscoroutine(t):
                await t
            else:
                await asyncio.sleep(0.0)

    def create_condition(self, op, val):
        """Returns a function (no arguments, returns a boolean) that
        implements a condition, given its opcode and value.

        This does not handle opcode 0, the 'argument carrier' for action opcodes-
        that is a special case.
        """

        def undefined():
            raise ValueError(f"Undefined condition op: {op}")

        game = self.game

        if op == 1:
            return lambda: game.items[val].room == game.inventory
        if op == 2:
            return lambda: game.items[val].room == game.player_room
        if op == 3:
            return lambda: game.items[val].room in [game.player_room, game.inventory]
        if op == 4:
            return lambda: game.player_room == game.rooms[val]
        if op == 5:
            return lambda: game.items[val].room != game.player_room
        if op == 6:
            return lambda: game.items[val].room != game.inventory
        if op == 7:
            return lambda: game.player_room != game.rooms[val]
        if op == 8:
            return lambda: game.flags[val].state
        if op == 9:
            return lambda: not game.flags[val].state
        if op == 10:
            return lambda: len(game.inventory.get_items()) > 0
        if op == 11:
            return lambda: len(game.inventory.get_items()) == 0
        if op == 12:
            return lambda: game.items[val].room not in [
                game.player_room,
                game.inventory,
            ]
        if op == 13:
            return lambda: game.items[val].room is not None
        if op == 14:
            return lambda: game.items[val].room is None
        if op == 15:
            return lambda: game.counter.value <= val
        if op == 16:
            return lambda: game.counter.value > val
        if op == 17:
            return lambda: game.items[val].room == game.items[val].starting_room
        if op == 18:
            return lambda: game.items[val].room != game.items[val].starting_room
        if op == 19:
            return lambda: game.counter.value == val
        return undefined()

    def create_action(self, op, value_source):
        """Returns a function (no arguments, returns nothing) that implements
        an action opcode.

        value_source is not an opcode argument, but a function that extracts the
        next one from the argument carries (which are among the conditions of all
        things.) It can be called repeatedly for multiple arguments.
        """

        game = self.game

        def clear_screen():
            pass  # we don't do this

        def get_item():
            game.get_item(item)

        def superget_item():
            game.get_item(item, force=True)

        def drop_item():
            game.drop_item(item)

        def move_item():
            game.move_item(item, room)

        def remove_item():
            game.move_item(item, None)

        def swap_items():
            game.swap_items(item1, item2)

        def put_item_with():
            game.move_item(item1, item2.room)

        def move_player():
            game.move_player(room)

        def swap_loc():
            saved_player_room = game.saved_player_room
            game.saved_player_room = game.player_room
            game.move_player(saved_player_room)

        def set_counter():
            game.counter.value = counter_value

        def swap_counter():
            counter.swap(game)

        def add_counter():
            game.counter.value += counter_value

        def subtract_counter():
            game.counter.value -= counter_value

        def decrement_counter():
            game.counter.value -= 1

        def print_counter():
            game.output(f"{game.counter.value} ")

        def set_flag():
            flag.state = True

        def reset_flag():
            flag.state = False

        def die():
            game.move_player(game.rooms[len(game.rooms) - 1])
            game.dark_flag.state = False

        def game_over():
            game.game_over = True

        def check_score():
            game.check_score()

        def save_game():
            game.save_game()

        def describe_room():
            game.needs_room_update = True

        def refill_lamp():
            game.light_remaining = game.light_duration
            game.move_item(game.lamp_item, game.inventory)

        def swap_specific_loc():
            saved_player_room = game.saved_player_rooms[saved_room_value]
            game.saved_player_rooms[saved_room_value] = game.player_room
            game.move_player(saved_player_room)

        def continue_actions():
            game.continuing_commands = True

        def undefined():
            raise ValueError(f"Undefined action op: {op}")

        if op == 0:
            return lambda: None
        if op <= 51:
            return lambda: game.output_line(game.messages[op])
        if op == 52:
            item = game.items[value_source()]
            return get_item
        if op == 53:
            item = game.items[value_source()]
            return drop_item
        if op == 54:
            room = game.rooms[value_source()]
            return move_player
        if op == 55 or op == 59:
            item = game.items[value_source()]
            return remove_item
        if op == 56:
            flag = game.dark_flag
            return set_flag
        if op == 57:
            flag = game.dark_flag
            return reset_flag
        if op == 58:
            flag = game.flags[value_source()]
            return set_flag
        if op == 60:
            flag = game.flags[value_source()]
            return reset_flag
        if op == 61:
            return die
        if op == 62:
            item = game.items[value_source()]
            room = game.rooms[value_source()]
            return move_item
        if op == 63:
            return game_over
        if op == 64 or op == 76:
            return describe_room
        if op == 65:
            return check_score
        if op == 66:
            return lambda: game.output_inventory_text()
        if op == 67:
            flag = game.flags[0]
            return set_flag
        if op == 68:
            flag = game.flags[0]
            return reset_flag
        if op == 69:
            return refill_lamp
        if op == 70:
            return clear_screen
        if op == 71:
            return save_game
        if op == 72:
            item1 = game.items[value_source()]
            item2 = game.items[value_source()]
            return swap_items
        if op == 73:
            return continue_actions
        if op == 74:
            item = game.items[value_source()]
            return superget_item
        if op == 75:
            item1 = game.items[value_source()]
            item2 = game.items[value_source()]
            return put_item_with
        if op == 77:
            return decrement_counter
        if op == 78:
            return print_counter
        if op == 79:
            counter_value = value_source()
            return set_counter
        if op == 80:
            return swap_loc
        if op == 81:
            counter = game.counters[value_source()]
            return swap_counter
        if op == 82:
            counter_value = value_source()
            return add_counter
        if op == 83:
            counter_value = value_source()
            return subtract_counter
        if op == 84:
            return lambda: game.output(game.parsed_noun)
        if op == 85:
            return lambda: game.output_line(game.parsed_noun)
        if op == 86:
            return lambda: game.output_line()
        if op == 87:
            saved_room_value = value_source()
            return swap_specific_loc
        if op == 88:

            async def wait():
                game.flush_output()
                await asyncio.sleep(2.0)

            return wait
        if op >= 102:
            return lambda: game.output_line(game.messages[op - 50])
        return undefined()


class Occurance(Logic):
    """These logics run before user input, and let the game take actions
    not commanded by the user. These can have a chance-to-run, so they only
    run now and again.
    """

    def __init__(self, game, extracted_action):
        Logic.__init__(self, game, extracted_action)
        self.chance = extracted_action.noun

    def check_occurance(self):
        return self.is_available and randint(1, 100) <= self.chance


class Command(Logic):
    """These logics handle specific user commands."""

    def __init__(self, game, extracted, extracted_action):
        Logic.__init__(self, game, extracted_action)
        verb_index = extracted_action.verb
        noun_index = extracted_action.noun
        self.verb = game.get_verb(extracted.verbs[verb_index])
        self.noun = (
            game.get_noun(extracted.nouns[noun_index]) if noun_index > 0 else None
        )

    def check_command(self, verb, noun):
        if self.verb == verb:
            if self.noun is None or self.noun == noun:
                return self.is_available
        return False

    def check_available_command(self, noun):
        return self.noun == noun and self.is_available


class Continuation(Logic):
    """These logics are weird. They are continuations of commands or occurances
    which they follow. They run if a command executes the continue opcode, and
    if their condition is also met."""

    def __init__(self, game, extracted_action):
        Logic.__init__(self, game, extracted_action)

    @property
    def is_continuation(self):
        return True
