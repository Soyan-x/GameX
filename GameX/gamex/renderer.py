"""Modular, asset-free renderer for static terrain and animated combat."""

from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Translate

from .characters import CharacterRenderer
from .environment import BattlefieldRenderer
from .hud import HUDRenderer
from .particles import ParticlePool


class GameRenderer:
    """Coordinate environment, characters, particles, and HUD renderers."""

    def __init__(self, view):
        self.view = view
        self.quality = "medium"
        self.shake_enabled = True
        self.shake_time = 0.0
        self.shake_amount = 0.0
        self.environment = BattlefieldRenderer(view)
        self.characters = CharacterRenderer()
        self.particles = ParticlePool(self.quality)
        self.hud = HUDRenderer(view)
        self._shake = Translate(0, 0)

    def configure(self, quality="medium", shake=True):
        quality = quality if quality in ("low", "medium", "high") else "medium"
        self.quality = quality
        self.shake_enabled = bool(shake)
        self.environment.set_quality(quality)
        self.particles.set_quality(quality)
        if not self.shake_enabled:
            self.shake_time = self.shake_amount = 0
            self._shake.x = self._shake.y = 0

    def clear_effects(self):
        for p in self.particles.particles:
            p.life = 0
        self.shake_time = self.shake_amount = 0
        self.view.world.visual_events.clear()

    def draw(self, dt=0):
        view, world = self.view, self.view.world
        x0, y0, width, height = view.x, view.y, view.width, view.height
        self.environment.rebuild()
        if self.environment.shake is not None:
            self.environment.set_shake(self.environment.shake, 0, 0)

        events = getattr(world, "visual_events", [])
        for event in events:
            kind = event["kind"]
            if kind in ("explosion", "boss") and self.shake_enabled and self.quality != "low":
                self.shake_time = .12 if kind == "explosion" else .2
                self.shake_amount = 3 if kind == "explosion" else 5
        self.particles.consume(events)
        self.particles.update(dt)
        if self.shake_time > 0 and self.shake_enabled:
            self.shake_time = max(0, self.shake_time - dt)
            import math
            import random
            amount = self.shake_amount * self.shake_time / .2
            sx, sy = random.uniform(-amount, amount), random.uniform(-amount, amount)
            if self.environment.shake is not None:
                self.environment.set_shake(self.environment.shake, sx, sy)
        else:
            sx = sy = 0

        with view.canvas:
            view.canvas.clear()
            PushMatrix()
            self._shake = Translate(sx, sy)
            for bullet in world.bullets:
                self._bullet(x0, y0, bullet)
            for effect in world.effects:
                self._effect(x0, y0, effect)
            for enemy in world.enemies:
                self.characters.enemy(x0 + enemy.x, y0 + enemy.y, enemy)
            player = world.player
            self.characters.player(x0 + player.x, y0 + player.y, player.radius,
                                   world.facing, player.anim_phase, player.walk_strength,
                                   max(player.attack_flash_timer, 0))
            self.particles.draw(x0, y0)
            PopMatrix()
            self.hud.draw()

    @staticmethod
    def _bullet(x0, y0, bullet):
        colors = {24: (1, .88, .51), 15: (1, .58, .18), 12: (.62, .83, 1)}
        color = colors.get(bullet.damage, (1, .75, .3))
        trail = bullet.trail or []
        if len(trail) > 1:
            Color(*color, .32)
            points = []
            for tx, ty in trail[-4:]:
                points.extend((x0 + tx, y0 + ty))
            Line(points=points, width=max(1.2, bullet.radius * .34))
        for index, (tx, ty) in enumerate(trail):
            alpha = .1 + .12 * index
            radius = bullet.radius * (.55 + .1 * index)
            Color(*color, alpha)
            Ellipse(pos=(x0 + tx - radius, y0 + ty - radius), size=(radius * 2, radius * 2))
        Color(*color, 1)
        Ellipse(pos=(x0 + bullet.x - bullet.radius, y0 + bullet.y - bullet.radius),
                size=(bullet.radius * 2, bullet.radius * 2))

    def _effect(self, x0, y0, effect):
        progress = effect.progress
        radius = effect.radius * (.35 + progress * .8)
        alpha = max(0, 1 - progress)
        x, y = x0 + effect.x, y0 + effect.y
        if effect.kind == "muzzle":
            if self.quality == "high":
                Color(1, .55, .12, alpha * .12)
                Ellipse(pos=(x - radius * 2.4, y - radius * 2.4), size=(radius * 4.8, radius * 4.8))
            Color(1, .78, .27, alpha)
            Ellipse(pos=(x - radius * .55, y - radius * .55), size=(radius * 1.1, radius * 1.1))
            Color(1, .4, .1, alpha * .8)
            Line(circle=(x, y, radius), width=2)
            return
        if effect.kind == "explosion":
            Color(.24, .22, .19, alpha * .25)
            Line(circle=(x, y, radius * 1.2), width=3 + progress * 3)
            Color(1, .35, .1, alpha * .75)
        else:
            Color(1, .48, .12, alpha * .8)
        Line(circle=(x, y, radius), width=2.2)
        Color(1, .83, .42, alpha)
        Ellipse(pos=(x - radius * .25, y - radius * .25), size=(radius * .5, radius * .5))
