#!/usr/bin/python3
from extraction import ExtractedFile
from sys import argv

f = open(argv[1], "r")
ex = ExtractedFile(f)

for m in ex.items:
        print(vars(m))
