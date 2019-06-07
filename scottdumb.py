#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv
from random import seed

seed()

f = open(argv[1], "r")
ex = ExtractedFile(f)
g = Game(ex)

if len(argv)>=3:
        g.load_game(argv[2])

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

