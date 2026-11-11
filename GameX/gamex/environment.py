"""Deterministic, asset-free battlefield floor cached between resizes."""

from random import Random

from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle, Translate
from kivy.metrics import dp


class BattlefieldRenderer:
    """Build a decorative non-colliding battlefield once per layout/quality."""

    TILE_SIZES = {"low": 128, "medium": 96, "high": 78}

    def __init__(self, view):
        self.view = view
        self.quality = "medium"
        self.shake = None
        self._signature = None

    def set_quality(self, quality):
        quality = quality.lower()
        if quality != self.quality:
            self.quality = quality
            self._signature = None

    def set_shake(self, instruction, x, y):
        if instruction is not None:
            instruction.x, instruction.y = x, y

    def rebuild(self):
        view = self.view
        signature = (view.x, view.y, view.width, view.height, self.quality)
        if signature == self._signature:
            return
        self._signature = signature
        canvas = view.canvas.before
        canvas.clear()
        x0, y0, width, height = view.x, view.y, view.width, view.height
        tile = dp(self.TILE_SIZES[self.quality])
        rand = Random(7319)
        with canvas:
            PushMatrix()
            self.shake = Translate(0, 0)
            Color(.075, .105, .092, 1)
            Rectangle(pos=(x0, y0), size=(width, height))
            columns = int(width // tile) + 1
            rows = int(height // tile) + 1
            palettes = (
                (.11, .15, .12, 1), (.14, .16, .14, 1), (.18, .16, .12, 1),
                (.17, .19, .17, 1), (.12, .17, .14, 1), (.19, .18, .14, 1),
            )
            for col in range(columns):
                for row in range(rows):
                    color = palettes[rand.randrange(len(palettes))]
                    inset = dp(1.2)
                    Color(*color)
                    Rectangle(pos=(x0 + col * tile + inset, y0 + row * tile + inset),
                              size=(tile - inset * 2, tile - inset * 2))
                    if self.quality != "low":
                        detail = rand.randrange(4)
                        px = x0 + col * tile + rand.uniform(tile * .12, tile * .72)
                        py = y0 + row * tile + rand.uniform(tile * .12, tile * .78)
                        Color(.23, .25, .19, .22)
                        if detail == 0:
                            Line(points=[px, py, px + tile * .18, py + tile * .04,
                                         px + tile * .27, py - tile * .06], width=1)
                        elif detail == 1:
                            Ellipse(pos=(px, py), size=(tile * .08, tile * .035))
                        elif detail == 2:
                            Rectangle(pos=(px, py), size=(tile * .1, tile * .035))
                    elif (col * 3 + row * 5) % 7 == 0:
                        Color(.2, .23, .16, .22)
                        Ellipse(pos=(x0 + col * tile + tile * .3,
                                     y0 + row * tile + tile * .35), size=(tile * .08, tile * .04))

            self._road(x0, y0, width, height)
            self._edge_terrain(x0, y0, width, height, tile)
            self._obstacles(x0, y0, width, height, tile, rand)
            if self.quality == "high":
                self._ambient_lighting(x0, y0, width, height)
            PopMatrix()

    def _road(self, x, y, width, height):
        road_y, road_h = y + height * .48, dp(82)
        Color(.105, .12, .12, 1)
        Rectangle(pos=(x, road_y - road_h / 2), size=(width, road_h))
        Color(.21, .22, .18, .7)
        Line(points=[x, road_y - road_h / 2, x + width, road_y - road_h / 2], width=1)
        Line(points=[x, road_y + road_h / 2, x + width, road_y + road_h / 2], width=1)
        Color(.72, .61, .34, .38)
        dash, gap = dp(34), dp(27)
        cursor = x + dp(18)
        while cursor < x + width:
            Rectangle(pos=(cursor, road_y - dp(2)), size=(dash, dp(4)))
            cursor += dash + gap
        if self.quality != "low":
            Color(.025, .035, .035, .58)
            for offset in (width * .22, width * .76):
                Line(points=[x + offset, road_y + road_h * .35,
                             x + offset + dp(13), road_y + road_h * .1,
                             x + offset + dp(7), road_y - road_h * .08], width=1.5)

    @staticmethod
    def _edge_terrain(x, y, width, height, tile):
        # Worn grass bands and boundary chevrons help communicate the arena edge.
        Color(.11, .19, .12, .76)
        Rectangle(pos=(x, y), size=(width, tile * .23))
        Rectangle(pos=(x, y + height - tile * .2), size=(width, tile * .2))
        Color(.62, .52, .28, .7)
        for px in range(int(x + dp(15)), int(x + width - dp(18)), int(dp(46))):
            Line(points=[px, y + tile * .2, px + dp(13), y + tile * .2], width=1.4)
            Line(points=[px, y + height - tile * .17, px + dp(13), y + height - tile * .17], width=1.4)

    def _obstacles(self, x, y, width, height, tile, rand):
        count = max(4, min(18, int(width * height / (dp(440) ** 2))))
        candidates = []
        for index in range(count * 5):
            px = x + rand.uniform(dp(42), max(dp(43), width - dp(48)))
            py = y + rand.uniform(dp(52), max(dp(53), height - dp(52)))
            # Keep cover away from player spawn and leave the central road legible.
            if abs(py - (y + height * .48)) < dp(68):
                continue
            if (px - (x + width / 2)) ** 2 + (py - (y + height / 2)) ** 2 < dp(105) ** 2:
                continue
            candidates.append((px, py))
            if len(candidates) >= count:
                break
        types = ("crate", "barrel", "sandbag", "fence", "barricade", "wreck", "debris")
        for index, (px, py) in enumerate(candidates):
            kind = types[(index + rand.randrange(len(types))) % len(types)]
            self._obstacle(kind, px, py, tile)

    def _obstacle(self, kind, x, y, tile):
        scale = tile / dp(96)
        if kind == "crate":
            size = dp(34) * scale
            Color(.025, .035, .03, .42)
            RoundedRectangle(pos=(x - size * .43, y - size * .55), size=(size, size), radius=[dp(3)])
            Color(.34, .29, .18, 1)
            RoundedRectangle(pos=(x - size / 2, y - size / 2), size=(size, size), radius=[dp(3)])
            Color(.58, .47, .28, .9)
            Line(rectangle=(x - size / 2, y - size / 2, size, size), width=1.2)
            Line(points=[x - size * .35, y - size * .35, x + size * .35, y + size * .35], width=1)
            Line(points=[x - size * .35, y + size * .35, x + size * .35, y - size * .35], width=1)
        elif kind == "barrel":
            radius = dp(15) * scale
            Color(.02, .03, .02, .42)
            Ellipse(pos=(x - radius * .8, y - radius * 1.05), size=(radius * 2, radius * 2))
            Color(.34, .25, .12, 1)
            Ellipse(pos=(x - radius, y - radius), size=(radius * 2, radius * 2))
            Color(.71, .55, .27, 1)
            Line(circle=(x, y, radius * .82), width=1.3)
            Line(points=[x - radius, y, x + radius, y], width=1)
        elif kind == "sandbag":
            Color(.035, .04, .028, .4)
            RoundedRectangle(pos=(x - dp(25) * scale, y - dp(13) * scale),
                             size=(dp(50) * scale, dp(24) * scale), radius=[dp(8)])
            Color(.43, .4, .27, 1)
            for bag in range(3):
                Ellipse(pos=(x - dp(24) * scale + bag * dp(16) * scale,
                             y - dp(9) * scale), size=(dp(20) * scale, dp(17) * scale))
        elif kind in ("fence", "barricade"):
            length = dp(62 if kind == "fence" else 48) * scale
            Color(.03, .04, .03, .4)
            Rectangle(pos=(x - length / 2, y - dp(10) * scale),
                      size=(length, dp(8) * scale))
            Color(.42, .37, .24, 1) if kind == "fence" else Color(.53, .32, .18, 1)
            Rectangle(pos=(x - length / 2, y - dp(7) * scale), size=(length, dp(5) * scale))
            for post in (-.4, 0, .4):
                Rectangle(pos=(x + length * post, y - dp(16) * scale),
                          size=(dp(4) * scale, dp(28) * scale))
            if kind == "barricade":
                Color(.82, .66, .3, .9)
                Line(points=[x - length * .35, y - dp(2), x - length * .15, y + dp(3)], width=2)
                Line(points=[x + length * .05, y - dp(2), x + length * .25, y + dp(3)], width=2)
        elif kind == "wreck":
            length, breadth = dp(72) * scale, dp(34) * scale
            Color(.02, .025, .022, .5)
            RoundedRectangle(pos=(x - length / 2, y - breadth / 2 - dp(5)),
                             size=(length, breadth), radius=[dp(9)])
            Color(.2, .24, .2, 1)
            RoundedRectangle(pos=(x - length / 2, y - breadth / 2),
                             size=(length, breadth), radius=[dp(9)])
            Color(.1, .15, .15, 1)
            RoundedRectangle(pos=(x - length * .18, y - breadth * .36),
                             size=(length * .37, breadth * .72), radius=[dp(6)])
            Color(.48, .31, .14, .9)
            Line(points=[x - length * .42, y + breadth * .38,
                         x - length * .24, y + breadth * .54,
                         x + length * .31, y + breadth * .48], width=2)
        else:
            Color(.4, .37, .27, .8)
            for bit in range(4):
                px = x + (bit - 1.5) * dp(7) * scale
                py = y + ((bit % 2) - .5) * dp(8) * scale
                Line(points=[px - dp(6) * scale, py, px + dp(7) * scale, py + dp(3) * scale], width=2)

    @staticmethod
    def _ambient_lighting(x, y, width, height):
        Color(.48, .38, .19, .035)
        Ellipse(pos=(x + width * .04, y + height * .62), size=(width * .24, height * .31))
        Color(.14, .31, .28, .04)
        Ellipse(pos=(x + width * .68, y + height * .08), size=(width * .26, height * .32))
