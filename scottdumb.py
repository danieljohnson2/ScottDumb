#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv

f = open(argv[1], "r")
ex = ExtractedFile(f)
g = Game(ex)

print(g.player_room.look_text())

while True:
        try:
                cmd = input("What should I do? ")
                verb, noun = g.parse_command(cmd)
                print(verb, noun)

                if (verb is None or verb == g.go_word) and g.is_direction(noun):
                        next = g.player_room.get_move(noun)
                        if next is None: raise ValueError(f"I can't go there!")
                        g.player_room = next
                        print(g.player_room.look_text())
                else:
                        raise ValueError("I don't understand.")
        except Exception as e:
                print(e)

