#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv

f = open(argv[1], "r")
ex = ExtractedFile(f)
g = Game(ex)

print(g.player_room.get_look_text())

while True:
        try:
                cmd = input("What should I do? ")
                verb, noun = g.parse_command(cmd)
                print(verb, noun)

                response = g.perform_command(verb, noun)
                if response != "": print(response)
        except Exception as e:
                print(str(e))

