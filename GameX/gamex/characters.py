"""Asset-free animated character artwork for actors in the top-down arena."""

from math import atan2, pi, sin

from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, Rotate, RoundedRectangle


class CharacterRenderer:
    ENEMY_COLORS = {
        "normal": ((.33, .12, .1), (.65, .23, .17), (.89, .48, .24)),
        "fast": ((.06, .2, .17), (.13, .55, .38), (.48, .9, .48)),
        "heavy": ((.26, .21, .1), (.49, .4, .2), (.9, .7, .3)),
        "boss": ((.22, .08, .17), (.48, .13, .29), (.98, .3, .3)),
    }

    @staticmethod
    def player(x, y, radius, facing, phase=0, movement=0, flash=0):
        angle = atan2(facing[1], facing[0]) * 180 / pi
        bob = sin(phase * 2) * 1.1 * movement
        shadow = radius * 1.12
        Color(.015, .02, .018, .46)
        Ellipse(pos=(x - shadow, y - shadow * .62), size=(shadow * 2, shadow * 1.15))
        PushMatrix()
        Rotate(angle=angle, origin=(x, y))
        # Backpack and shoulder harness establish a clear soldier silhouette.
        Color(.12, .18, .13, 1)
        RoundedRectangle(pos=(x - radius * .95, y - radius * .67 + bob),
                         size=(radius * 1.9, radius * 1.34), radius=[radius * .28])
        Color(.28, .34, .21, 1)
        RoundedRectangle(pos=(x - radius * .54, y - radius * .9 + bob),
                         size=(radius * 1.08, radius * 1.58), radius=[radius * .38])
        # Limb details animate subtly with forward motion.
        Color(.17, .22, .16, 1)
        for side in (-1, 1):
            stride = sin(phase * 5 + side * pi) * radius * .12 * movement
            RoundedRectangle(pos=(x + side * radius * .37 - radius * .16 + stride,
                                  y - radius * .95 + bob),
                             size=(radius * .33, radius * .3), radius=[radius * .1])
        Color(.4, .48, .3, 1)
        RoundedRectangle(pos=(x - radius * .65, y - radius * .18 + bob),
                         size=(radius * 1.3, radius * 1.05), radius=[radius * .28])
        Color(.62, .54, .35, 1)
        Rectangle(pos=(x - radius * .55, y - radius * .16 + bob), size=(radius * 1.1, radius * .13))
        # Helmet, visor, and ear protection.
        Color(.12, .17, .13, 1)
        Ellipse(pos=(x - radius * .43, y + radius * .36 + bob), size=(radius * .86, radius * .7))
        Color(.43, .5, .31, 1)
        Ellipse(pos=(x - radius * .33, y + radius * .44 + bob), size=(radius * .66, radius * .52))
        Color(.08, .14, .14, 1)
        RoundedRectangle(pos=(x - radius * .3, y + radius * .45 + bob),
                         size=(radius * .6, radius * .16), radius=[radius * .05])
        for side in (-1, 1):
            Color(.68, .58, .3, 1)
            Ellipse(pos=(x + side * radius * .34 - radius * .08, y + radius * .47 + bob),
                    size=(radius * .16, radius * .19))
        # Rifle, oriented with the upper body aim vector.
        Color(.09, .11, .09, 1)
        RoundedRectangle(pos=(x + radius * .16, y + radius * .05 + bob),
                         size=(radius * 1.18, radius * .19), radius=[radius * .06])
        Color(.38, .39, .28, 1)
        Rectangle(pos=(x + radius * .4, y + radius * .08 + bob), size=(radius * .42, radius * .12))
        Color(.08, .1, .09, 1)
        Rectangle(pos=(x + radius * 1.18, y + radius * .105 + bob), size=(radius * .43, radius * .07))
        PopMatrix()
        if flash > 0:
            Color(1, .7, .22, min(1, flash * 9))
            Ellipse(pos=(x + facing[0] * radius * 1.6 - radius * .28,
                         y + facing[1] * radius * 1.6 - radius * .28),
                    size=(radius * .56, radius * .56))

    @classmethod
    def enemy(cls, x, y, actor):
        kind = actor.kind if actor.kind in cls.ENEMY_COLORS else "normal"
        shadow_color, shell_color, accent = cls.ENEMY_COLORS[kind]
        scale = 1.55 if kind == "boss" or actor.boss else (1.18 if kind == "heavy" else .94)
        radius = actor.radius * scale
        phase = actor.anim_phase
        stride = sin(phase * 5) * radius * .12 * actor.walk_strength
        hit = actor.hit_flash_timer > 0
        Color(.015, .018, .015, .48)
        Ellipse(pos=(x - radius * 1.05, y - radius * .78), size=(radius * 2.1, radius * 1.15))
        PushMatrix()
        Rotate(angle=atan2(actor.facing[1], actor.facing[0]) * 180 / pi, origin=(x, y))
        Color(.84, .82, .68, .92) if hit else Color(*shadow_color, 1)
        # Reaching arms and uneven legs animate independently of world simulation.
        limb = radius * (.29 if kind != "boss" else .37)
        for side in (-1, 1):
            Color(.78, .75, .64, .95) if hit else Color(*shell_color, 1)
            Ellipse(pos=(x + side * radius * .72 - limb * .35,
                         y + stride * side - limb * .35), size=(limb * .7, limb * .7))
            leg_y = y - radius * .66 + stride * side
            Line(points=[x + side * radius * .27, leg_y, x + side * radius * .32, leg_y - limb],
                 width=max(1.3, radius * .12))
        Color(.81, .82, .68, .95) if hit else Color(*shell_color, 1)
        if kind == "fast":
            # Narrow runner torso with hooked shoulders.
            Ellipse(pos=(x - radius * .52, y - radius * .72), size=(radius * 1.04, radius * 1.48))
            Color(*accent, 1)
            Line(points=[x - radius * .42, y + radius * .32, x, y + radius * .7,
                         x + radius * .42, y + radius * .32], width=max(1.2, radius * .13))
        elif kind == "heavy":
            RoundedRectangle(pos=(x - radius * .86, y - radius * .84),
                             size=(radius * 1.72, radius * 1.66), radius=[radius * .32])
            Color(*accent, 1)
            Line(points=[x - radius * .58, y - radius * .05, x + radius * .58, y - radius * .05],
                 width=max(2, radius * .15))
        else:
            Ellipse(pos=(x - radius * .67, y - radius * .72), size=(radius * 1.34, radius * 1.55))
        Color(.17, .08, .07, 1)
        Ellipse(pos=(x - radius * .4, y + radius * .25), size=(radius * .8, radius * .58))
        Color(*accent, 1)
        for eye_x in (-.19, .19):
            Ellipse(pos=(x + radius * eye_x - radius * .07, y + radius * .42),
                    size=(radius * .14, radius * .11))
        if kind == "boss":
            Color(.91, .22, .22, .82)
            Line(circle=(x, y, radius * 1.17), width=max(1.5, radius * .08))
        PopMatrix()
        if kind in ("heavy", "boss"):
            width = radius * 1.7
            Color(.025, .03, .025, .85)
            RoundedRectangle(pos=(x - width / 2, y + radius + 4), size=(width, 4), radius=[2])
            max_health = actor.max_health or (500 if kind == "boss" else max(actor.health, 1))
            Color(.91, .2, .2, 1)
            RoundedRectangle(pos=(x - width / 2, y + radius + 4),
                             size=(width * max(0, min(1, actor.health / max_health)), 4), radius=[2])

