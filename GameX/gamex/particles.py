"""Bounded reusable combat particle pool for the Kivy renderer."""

from dataclasses import dataclass
from math import cos, sin
from random import Random

from kivy.graphics import Color, Ellipse, Line


@dataclass
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0
    duration: float = 1.0
    size: float = 2.0
    kind: str = "dust"
    pending: bool = False

    @property
    def active(self):
        return self.life > 0


class ParticlePool:
    """Fixed-capacity pool; events reuse dead particles instead of growing lists."""

    CAPS = {"low": 28, "medium": 72, "high": 144}
    QUALITY_COUNTS = {"low": 2, "medium": 5, "high": 9}

    def __init__(self, quality="medium", seed=993):
        self.rng = Random(seed)
        self.quality = "medium"
        self.particles = []
        self._cursor = 0
        self.set_quality(quality)

    def set_quality(self, quality):
        quality = quality if quality in self.CAPS else "medium"
        if quality == self.quality and self.particles:
            return
        active = [p for p in self.particles if p.active]
        capacity = self.CAPS[quality]
        self.particles = active[:capacity]
        self.particles.extend(Particle() for _ in range(capacity - len(self.particles)))
        self._cursor = 0
        self.quality = quality

    def emit(self, x, y, kind="impact", scale=1.0):
        count = self.QUALITY_COUNTS[self.quality]
        if kind in ("boss", "explosion", "death"):
            count = min(self.CAPS[self.quality], count * (3 if self.quality == "high" else 2))
        for index in range(count):
            particle = None
            for _ in range(len(self.particles)):
                candidate = self.particles[self._cursor]
                self._cursor = (self._cursor + 1) % len(self.particles)
                if not candidate.active and not candidate.pending:
                    particle = candidate
                    break
            if particle is None:
                return
            particle.pending = True
            angle = self.rng.random() * 6.283185307
            speed = self.rng.uniform(18, 95) * scale
            particle.x, particle.y = x, y
            particle.vx = cos(angle) * speed
            particle.vy = sin(angle) * speed
            particle.duration = self.rng.uniform(.16, .5) * (1.4 if kind in ("explosion", "boss") else 1)
            particle.life = particle.duration
            particle.size = self.rng.uniform(1.5, 4.5) * scale
            particle.kind = kind

    def consume(self, events):
        for event in events:
            self.emit(event["x"], event["y"], event["kind"], event.get("scale", 1.0))
        events.clear()

    def update(self, dt):
        dt = max(dt, 0)
        for p in self.particles:
            if p.pending:
                p.pending = False
            elif p.active:
                p.life = max(0, p.life - dt)
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx *= .94
                p.vy *= .94

    def draw(self, ox=0, oy=0):
        for p in self.particles:
            if not p.active:
                continue
            fade = p.life / p.duration
            if p.kind in ("explosion", "boss", "death"):
                Color(1, .34 if p.kind != "boss" else .14, .08, fade * .8)
            elif p.kind in ("muzzle", "tracer"):
                Color(1, .78, .28, fade * .9)
            elif p.kind == "impact":
                Color(1, .82, .52, fade)
            else:
                Color(.58, .56, .42, fade * .45)
            radius = p.size * (.65 + .55 * (1 - fade))
            Ellipse(pos=(ox + p.x - radius, oy + p.y - radius), size=(radius * 2, radius * 2))

