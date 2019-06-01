class Game():
        def __init__(self, extracted):
                self.rooms = [Room(x.description) for x in extracted.rooms]
                self.player_room = self.rooms[extracted.starting_room]

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

class Room():
        def __init__(self, description):
                self.description = description
                self.north = None
                self.south = None
                self.east = None
                self.west = None
                self.up = None
                self.down = None

        def __repr__(self):
                return self.description[:32]

        def look_text(self):
                text = self.description
                if text.startswith("*"):
                        text = text[1:]
                else:
                        text = "I'm in a " + text

                exits = ""
                if self.north: exits += " North"
                if self.south: exits += " South"
                if self.east: exits += " East"
                if self.west: exits += " West"
                if self.up: exits += " Up"
                if self.down: exits += " Down"

                return text + "\n\nObvious exits:" + exits
