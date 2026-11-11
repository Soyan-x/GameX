"""Validated, offline JSON persistence for GameX profile data."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from .weapons import WEAPONS


UPGRADE_COSTS = {
    "damage": (40, 80, 140),
    "reload": (35, 75, 130),
    "magazine": (30, 70, 120),
}


def default_save() -> dict:
    return {
        "version": 1,
        "profile": {"high_score": 0, "total_coins": 0, "best_wave": 0,
                    "games_played": 0, "kills": 0},
        "settings": {"master_volume": .8, "music_volume": .35, "effects_volume": .8,
                     "mouse_sensitivity": 1.0, "touch_sensitivity": 1.0,
                     "graphics_quality": "medium", "screen_shake": True,
                     "tutorial_seen": False},
        "upgrades": {weapon.name: {kind: 0 for kind in UPGRADE_COSTS} for weapon in WEAPONS},
    }


class SaveStore:
    """Store a sanitized profile in a writable app-specific directory."""

    def __init__(self, directory: str | os.PathLike):
        self.directory = Path(directory)
        self.path = self.directory / "gamex_save.json"
        self.data = default_save()

    def load(self) -> dict:
        try:
            with self.path.open("r", encoding="utf-8") as save_file:
                self.data = self._sanitize(json.load(save_file))
        except FileNotFoundError:
            self.data = default_save()
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self._preserve_corrupt_file()
            self.data = default_save()
        return self.data

    def _preserve_corrupt_file(self) -> None:
        if not self.path.exists():
            return
        backup = self.path.with_suffix(".json.corrupt")
        try:
            if backup.exists():
                backup = self.path.with_name(f"gamex_save.corrupt.{os.getpid()}.json")
            shutil.copy2(self.path, backup)
        except OSError:
            # Keep the original in place; callers can still continue with a clean session.
            pass

    @staticmethod
    def _integer(value, fallback=0, maximum=2_000_000_000):
        if isinstance(value, bool) or not isinstance(value, int):
            return fallback
        return max(0, min(maximum, value))

    @staticmethod
    def _number(value, fallback, minimum, maximum):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return fallback
        return max(minimum, min(maximum, float(value)))

    @classmethod
    def _sanitize(cls, raw) -> dict:
        clean = default_save()
        if not isinstance(raw, dict):
            return clean
        profile = raw.get("profile", {})
        if isinstance(profile, dict):
            for key in clean["profile"]:
                clean["profile"][key] = cls._integer(profile.get(key), clean["profile"][key])
        settings = raw.get("settings", {})
        if isinstance(settings, dict):
            for key in ("master_volume", "music_volume", "effects_volume"):
                clean["settings"][key] = cls._number(settings.get(key), clean["settings"][key], 0, 1)
            for key in ("mouse_sensitivity", "touch_sensitivity"):
                clean["settings"][key] = cls._number(settings.get(key), clean["settings"][key], .25, 3)
            clean["settings"]["tutorial_seen"] = settings.get("tutorial_seen") is True
            quality = settings.get("graphics_quality")
            clean["settings"]["graphics_quality"] = quality if quality in ("low", "medium", "high") else "medium"
            clean["settings"]["screen_shake"] = settings.get("screen_shake") is not False
        upgrades = raw.get("upgrades", {})
        if isinstance(upgrades, dict):
            for weapon in WEAPONS:
                values = upgrades.get(weapon.name, {})
                if isinstance(values, dict):
                    for kind in UPGRADE_COSTS:
                        clean["upgrades"][weapon.name][kind] = cls._integer(values.get(kind), 0, 3)
        return clean

    def save(self) -> None:
        self.data = self._sanitize(self.data)
        self.directory.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.directory,
                                   prefix="gamex_save_", suffix=".tmp", delete=False) as temp:
                temp_path = Path(temp.name)
                json.dump(self.data, temp, indent=2, sort_keys=True)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def update_settings(self, **values) -> None:
        self.data["settings"].update(values)
        self.data = self._sanitize(self.data)
        self.save()

    def finish_run(self, score: int, wave: int, coins: int, kills: int) -> None:
        profile = self.data["profile"]
        profile["high_score"] = max(profile["high_score"], self._integer(score))
        profile["best_wave"] = max(profile["best_wave"], self._integer(wave))
        profile["total_coins"] += self._integer(coins)
        profile["games_played"] += 1
        profile["kills"] += self._integer(kills)
        self.save()

    def purchase_upgrade(self, weapon_name: str, upgrade: str) -> tuple[bool, int]:
        if weapon_name not in self.data["upgrades"] or upgrade not in UPGRADE_COSTS:
            return False, 0
        level = self.data["upgrades"][weapon_name][upgrade]
        if level >= len(UPGRADE_COSTS[upgrade]):
            return False, 0
        price = UPGRADE_COSTS[upgrade][level]
        profile = self.data["profile"]
        if profile["total_coins"] < price:
            return False, price
        profile["total_coins"] -= price
        self.data["upgrades"][weapon_name][upgrade] = level + 1
        self.save()
        return True, price
