"""Data-driven weapon definitions used by GameWorld and the HUD."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    magazine_size: int
    reserve_ammo: int | None
    damage: int
    fire_interval: float
    reload_time: float
    pellets: int = 1
    spread_degrees: float = 0.0


WEAPONS = (
    WeaponSpec("Pistol", 12, None, 24, 0.32, 1.0),
    WeaponSpec("Assault Rifle", 30, 150, 15, 0.105, 1.35),
    WeaponSpec("Shotgun", 6, 36, 12, 0.68, 1.65, pellets=6, spread_degrees=24),
)


@dataclass
class WeaponState:
    spec: WeaponSpec
    magazine: int
    reserve: int | None

    @classmethod
    def create(cls, spec: WeaponSpec) -> "WeaponState":
        return cls(spec, spec.magazine_size, spec.reserve_ammo)

    def reload(self) -> int:
        if self.magazine >= self.spec.magazine_size:
            return 0
        if self.reserve is None:
            amount = self.spec.magazine_size - self.magazine
        else:
            amount = min(self.spec.magazine_size - self.magazine, self.reserve)
            self.reserve -= amount
        self.magazine += amount
        return amount
