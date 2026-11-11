"""Compact responsive battlefield HUD, controls, and overlays."""

from collections import OrderedDict

from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle


class HUDRenderer:
    def __init__(self, view):
        self.view = view
        self.text_cache = OrderedDict()

    def draw(self):
        self.controls()
        self.panel()
        self.pause_button()
        if self.view.world.game_over:
            self.game_over()

    def controls(self):
        v = self.view
        jc, fc = v.joystick_center, v.fire_center
        Color(.12, .32, .35, .28)
        Ellipse(pos=(jc[0] - v.joystick_radius, jc[1] - v.joystick_radius),
                size=(v.joystick_radius * 2, v.joystick_radius * 2))
        Color(.29, .68, .7, .7)
        Line(circle=(*jc, v.joystick_radius), width=1.4)
        knob = v.joystick_radius * .3
        self._circle(jc[0] + v.move_vector[0] * v.joystick_radius * .56,
                     jc[1] + v.move_vector[1] * v.joystick_radius * .56, knob, (.26, .67, .7, .65))
        Color(.52, .1, .08, .52 if v.world.firing else .34)
        Ellipse(pos=(fc[0] - v.fire_radius, fc[1] - v.fire_radius),
                size=(v.fire_radius * 2, v.fire_radius * 2))
        Color(.95, .57, .42, .9)
        Line(circle=(*fc, v.fire_radius), width=2)
        self._text("FIRE", fc[0] - 12, fc[1] - 5, 10, (1, .87, .78, 1))
        if v.world.reload_timer > 0:
            progress = 1 - v.world.reload_timer / max(.01, v.world.weapon.spec.reload_time)
            Color(.96, .69, .27, .9)
            Line(circle=(*fc, v.fire_radius + 5), width=2.5, end_angle=360 * progress)
        labels = ("1 PISTOL", "2 RIFLE", "3 SHOTGUN")
        for index, (bx, by, bw, bh) in enumerate(v.weapon_button_rects):
            selected = index == v.world.weapon_index
            Color(.13, .43, .32, .94) if selected else Color(.055, .09, .09, .9)
            RoundedRectangle(pos=(bx, by), size=(bw, bh), radius=[7])
            Color(.5, .82, .59, .92) if selected else Color(.31, .44, .4, .8)
            Line(rounded_rectangle=(bx, by, bw, bh, 7), width=1)
            self._text(labels[index], bx + 4, by + bh * .32, 9,
                       (.93, 1, .91, 1) if selected else (.71, .8, .75, 1))
        rx, ry, rw, rh = v.reload_button_rect
        Color(.07, .16, .17, .94)
        RoundedRectangle(pos=(rx, ry), size=(rw, rh), radius=[7])
        Color(.35, .69, .75, .9)
        Line(rounded_rectangle=(rx, ry, rw, rh, 7), width=1)
        self._text("RELOAD", rx + 5, ry + rh * .32, 9, (.84, .97, 1, 1))

    def panel(self):
        v, w = self.view, self.view.world
        x, y, width, height = v.x, v.y, v.width, v.height
        panel_w = min(width - 24, 470)
        Color(.018, .035, .036, .88)
        RoundedRectangle(pos=(x + 12, y + height - 65), size=(panel_w, 52), radius=[8])
        Color(.26, .39, .32, .72)
        Line(rounded_rectangle=(x + 12, y + height - 65, panel_w, 52, 8), width=1)
        self._text("VITALS", x + 23, y + height - 29, 9, (.72, .82, .72, 1))
        bar_x, bar_y, bar_w, bar_h = x + 22, y + height - 53, min(130, width * .2), 11
        Color(.08, .12, .11, 1)
        RoundedRectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h), radius=[5])
        ratio = max(0, min(1, w.player.health / 5))
        Color(.23, .82, .48, 1) if ratio > .35 else Color(.95, .28, .19, 1)
        if ratio:
            RoundedRectangle(pos=(bar_x, bar_y), size=(bar_w * ratio, bar_h), radius=[5])
        self._text(f"{w.player.health}/5", bar_x + bar_w + 7, bar_y, 10)
        self._text(f"WAVE {w.wave:02d}", bar_x + bar_w + 48, y + height - 29, 11, (.45, .79, .84, 1))
        self._text(f"SCORE {w.score}", x + width - 206, y + height - 28, 11, (.95, .8, .43, 1))
        self._text(f"COINS {w.coins}", x + width - 112, y + height - 28, 10, (.96, .72, .35, 1))
        ammo_y = y + height - 52
        reserve = "INF" if w.reserve_ammo is None else str(w.reserve_ammo)
        self._text(f"{w.weapon.spec.name.upper()}  {w.ammo:02d}/{reserve}",
                   x + width - 205, ammo_y, 11, (.88, .92, .84, 1))
        if w.reload_timer > 0:
            self._text("RELOADING", x + width - 102, ammo_y, 9, (1, .69, .3, 1))
        bosses = [enemy for enemy in w.enemies if enemy.boss or enemy.kind == "boss"]
        if bosses:
            boss = bosses[0]
            bw, bh = min(width * .5, 360), 14
            bx, by = x + (width - bw) / 2, y + height - 92
            Color(.02, .025, .025, .9)
            RoundedRectangle(pos=(bx, by), size=(bw, bh), radius=[5])
            Color(.72, .12, .16, 1)
            RoundedRectangle(pos=(bx + 2, by + 2), size=((bw - 4) * max(0, boss.health / max(1, boss.max_health or 1)), bh - 4), radius=[4])
            self._text("HOSTILE: BOSS", bx, by + 17, 10, (1, .55, .46, 1))
        if w.announcement_timer > 0:
            alpha = min(1, w.announcement_timer)
            self._text(w.announcement, x + width * .39, y + height * .73, 22,
                       (1, .84, .47, alpha))
        if getattr(w, "reward_notice_timer", 0) > 0:
            self._text(getattr(w, "reward_notice", ""), x + width * .43, y + height * .67,
                       15, (.98, .77, .34, min(1, w.reward_notice_timer)))

    def pause_button(self):
        x, y, width, height = self.view.pause_button_rect
        Color(.04, .09, .09, .84)
        RoundedRectangle(pos=(x, y), size=(width, height), radius=[8])
        Color(.66, .82, .76, .95)
        Line(rounded_rectangle=(x, y, width, height, 8), width=1)
        Color(.82, .93, .86, 1)
        Rectangle(pos=(x + width * .36, y + height * .27), size=(4, height * .46))
        Rectangle(pos=(x + width * .6, y + height * .27), size=(4, height * .46))

    def game_over(self):
        v, w = self.view, self.view.world
        x, y, width, height = v.x, v.y, v.width, v.height
        Color(.008, .015, .018, .78)
        Rectangle(pos=(x, y), size=(width, height))
        panel_w, panel_h = min(420, width * .82), min(250, height * .72)
        px, py = x + (width - panel_w) / 2, y + (height - panel_h) / 2
        Color(.07, .11, .11, .98)
        RoundedRectangle(pos=(px, py), size=(panel_w, panel_h), radius=[18])
        Color(.9, .25, .18, 1)
        RoundedRectangle(pos=(px + 24, py + panel_h - 22), size=(panel_w - 48, 4), radius=[2])
        self._text("GAME OVER", px + panel_w * .3, py + panel_h - 82, 25, (1, .38, .27, 1))
        self._text(f"FINAL SCORE  {w.score}     COINS {w.coins}", px + panel_w * .22,
                   py + panel_h - 119, 14)
        bx, by, bw, bh = px + panel_w * .2, py + 36, panel_w * .6, 54
        Color(.16, .57, .39, 1)
        RoundedRectangle(pos=(bx, by), size=(bw, bh), radius=[12])
        Color(.63, .95, .71, .95)
        Line(rounded_rectangle=(bx, by, bw, bh, 12), width=1.2)
        self._text("PLAY AGAIN", bx + bw * .31, by + bh * .32, 17, (.92, 1, .92, 1))

    @staticmethod
    def _circle(x, y, radius, color):
        Color(*color)
        Ellipse(pos=(x - radius, y - radius), size=(radius * 2, radius * 2))

    def _text(self, text, x, y, font_size, color=(.84, .9, .84, 1)):
        key = (text, font_size, color)
        label = self.text_cache.get(key)
        if label is None:
            label = CoreLabel(text=text, font_size=font_size, color=color)
            label.refresh()
            self.text_cache[key] = label
            if len(self.text_cache) > 160:
                self.text_cache.popitem(last=False)
        else:
            self.text_cache.move_to_end(key)
        Color(1, 1, 1, 1)
        Rectangle(texture=label.texture, pos=(x, y), size=label.texture.size)

