#!/usr/bin/python3
from game import Game
from extraction import ExtractedFile
from sys import argv

f = open(argv[1], "r")
ex = ExtractedFile(f)
g = Game(ex)

print(g.player_room.look_text())
