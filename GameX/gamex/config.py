"""Shared game tuning values."""

from kivy.utils import platform

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 600
PLAYER_SPEED = 250.0
PLAYER_RADIUS = 18.0
PLAYER_MAX_HEALTH = 5
BULLET_SPEED = 520.0
BULLET_RADIUS = 5.0
ENEMY_SPEED = 78.0
ENEMY_RADIUS = 16.0
ENEMY_SPAWN_INTERVAL = 1.25
PLAYER_FIRE_INTERVAL = 0.22
ENEMY_TYPES = {
    "normal": {"health": 45, "speed": 78.0, "damage": 1, "reward": 5, "radius": 16.0},
    "fast": {"health": 24, "speed": 142.0, "damage": 1, "reward": 8, "radius": 13.0},
    "heavy": {"health": 120, "speed": 42.0, "damage": 2, "reward": 16, "radius": 22.0},
    "boss": {"health": 500, "speed": 52.0, "damage": 3, "reward": 100, "radius": 34.0},
}
if platform == "android":
    WINDOW_WIDTH, WINDOW_HEIGHT = 960, 600
