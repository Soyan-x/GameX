"""Simple simulation entities independent of Kivy widgets."""

from dataclasses import dataclass
from math import hypot


@dataclass
class Actor:
    x: float
    y: float
    radius: float
    health: int = 1
    kind: str = "normal"
    speed: float = 78.0
    damage: int = 1
    reward: int = 1
    boss: bool = False
    attack_timer: float = 0.0
    max_health: int | None = None
    facing: tuple[float, float] = (1.0, 0.0)
    anim_phase: float = 0.0
    walk_strength: float = 0.0
    hit_flash_timer: float = 0.0
    attack_flash_timer: float = 0.0
    dust_timer: float = 0.0


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    trail: list[tuple[float, float]] | None = None
    damage: int = 1

    def update(self, dt: float) -> None:
        if self.trail is None:
            self.trail = []
        self.trail.append((self.x, self.y))
        if len(self.trail) > 4:
            del self.trail[0]
        self.x += self.vx * dt
        self.y += self.vy * dt


@dataclass
class VisualEffect:
    x: float
    y: float
    kind: str
    ttl: float
    duration: float
    radius: float

    def update(self, dt: float) -> None:
        self.ttl = max(0.0, self.ttl - dt)

    @property
    def progress(self) -> float:
        return 1.0 - self.ttl / self.duration if self.duration else 1.0


def overlaps(a: Actor | Bullet, b: Actor | Bullet) -> bool:
    return hypot(a.x - b.x, a.y - b.y) <= a.radius + b.radius
