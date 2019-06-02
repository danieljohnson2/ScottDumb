#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv

f = open(argv[1], "r")
ex = ExtractedFile(f)
g = Game(ex)


while True:
        try:
                if g.needs_room_update:
                        print(g.player_room.get_look_text())
                        g.needs_room_update = False
                        g.wants_room_update = False

                occ = g.perform_occurances()
                if occ != "": print(occ)

                cmd = input("What should I do? ")
                verb, noun = g.parse_command(cmd)
                print(verb, noun)

                response = g.perform_command(verb, noun)
                if response != "": print(response)
        except Exception as e:
                print(str(e))

