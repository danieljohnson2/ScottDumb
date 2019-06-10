#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv
from random import seed

class CliGame(Game):
        def __init__(self, file, save_game_path):
                Game.__init__(self, file)
                self.save_game_path = save_game_path

        def get_save_game_path(self):
                return self.save_game_path

        def get_load_game_path(self):
                return self.save_game_path

seed()

with open(argv[1], "r") as f:
        ex = ExtractedFile(f)

if len(argv) >= 3:
        g = CliGame(ex, argv[2])
        try: g.load_game()
        except FileNotFoundError: pass
else:
        g = Game(ex)

while not g.game_over:
        try:
                if g.needs_room_update:
                        print(g.player_room.get_look_text())
                        g.needs_room_update = False
                        g.wants_room_update = False

                g.perform_occurances()
                print(g.extract_output(), end = "")

                if g.game_over: break

                if g.needs_room_update:
                        print(g.player_room.get_look_text())
                        g.needs_room_update = False
                        g.wants_room_update = False
                
                cmd = input("What should I do? ")
                verb, noun = g.parse_command(cmd)
                
                g.perform_command(verb, noun)
                print(g.extract_output(), end = "")
        except EOFError:
                exit()
        except Exception as e:
                print(str(e))

