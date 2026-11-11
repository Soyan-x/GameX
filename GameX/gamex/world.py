"""Offline game simulation: movement, weapons, typed enemies, waves, and rewards."""

from math import atan2, cos, hypot, radians, sin
from random import choice, uniform
from dataclasses import replace

from .config import ENEMY_TYPES, ENEMY_SPAWN_INTERVAL, PLAYER_MAX_HEALTH, PLAYER_RADIUS, PLAYER_SPEED
from .entities import Actor, Bullet, VisualEffect, overlaps
from .weapons import WEAPONS, WeaponState


class GameWorld:
    def __init__(self, upgrades: dict | None = None) -> None:
        self.width, self.height = 960.0, 600.0
        self.upgrades = upgrades or {}
        self.reset()

    def reset(self) -> None:
        self.player = Actor(self.width / 2, self.height / 2, PLAYER_RADIUS, PLAYER_MAX_HEALTH)
        self.enemies: list[Actor] = []
        self.bullets: list[Bullet] = []
        self.effects: list[VisualEffect] = []
        self.score = self.coins = 0
        self.wave = 1
        self.wave_timer = 0.0
        self.announcement_timer = 2.5
        self.announcement = "WAVE 1"
        self.wave_spawned = 0
        self.wave_target = 5
        self.boss_spawned = False
        self.spawn_timer = 0.5
        self.fire_timer = 0.0
        self.game_over = False
        self.aim: tuple[float, float] | None = None
        self.firing = False
        self.facing = (1.0, 0.0)
        self.weapon_states = [WeaponState.create(spec) for spec in WEAPONS]
        self.upgrade_specs = list(WEAPONS)
        self.apply_upgrades(self.upgrades)
        self.weapon_index = 0
        self.reload_timer = 0.0
        self.kills = 0
        self.audio_events: list[str] = []
        self.visual_events: list[dict] = []
        self.reward_notice = ""
        self.reward_notice_timer = 0.0

    def apply_upgrades(self, upgrades: dict | None) -> None:
        """Apply persistent shop levels to this run's weapon definitions."""
        self.upgrades = upgrades or {}
        states = []
        specs = []
        for base in WEAPONS:
            levels = self.upgrades.get(base.name, {})
            damage_level = int(levels.get("damage", 0))
            reload_level = int(levels.get("reload", 0))
            magazine_level = int(levels.get("magazine", 0))
            capacity = base.magazine_size + magazine_level * 2
            spec = replace(base, damage=base.damage + damage_level * 4,
                           reload_time=base.reload_time * max(.55, 1 - reload_level * .12),
                           magazine_size=capacity)
            reserve = None if base.reserve_ammo is None else base.reserve_ammo + magazine_level * base.magazine_size
            spec = replace(spec, reserve_ammo=reserve)
            specs.append(spec)
            states.append(WeaponState.create(spec))
        self.upgrade_specs = specs
        self.weapon_states = states

    @property
    def weapon(self) -> WeaponState:
        return self.weapon_states[self.weapon_index]

    @property
    def ammo(self) -> int:
        return self.weapon.magazine

    @ammo.setter
    def ammo(self, amount: int) -> None:
        self.weapon.magazine = max(0, min(self.weapon.spec.magazine_size, amount))

    @property
    def max_ammo(self) -> int:
        return self.weapon.spec.magazine_size

    @property
    def reserve_ammo(self) -> int | None:
        return self.weapon.reserve

    def resize(self, width: float, height: float) -> None:
        self.width, self.height = max(1, width), max(1, height)
        self.player.x = min(max(self.player.x, PLAYER_RADIUS), self.width - PLAYER_RADIUS)
        self.player.y = min(max(self.player.y, PLAYER_RADIUS), self.height - PLAYER_RADIUS)

    def select_weapon(self, index: int) -> bool:
        if not 0 <= index < len(self.weapon_states):
            return False
        self.weapon_index = index
        self.reload_timer = 0.0
        self.fire_timer = 0.0
        return True

    def reload(self) -> bool:
        state = self.weapon
        if self.reload_timer > 0 or state.magazine >= state.spec.magazine_size:
            return False
        if state.reserve is not None and state.reserve <= 0:
            return False
        self.reload_timer = state.spec.reload_time
        self.audio_events.append("reload")
        return True

    def shoot_toward(self, x: float, y: float) -> bool:
        state = self.weapon
        if state.magazine <= 0 or self.reload_timer > 0:
            return False
        dx, dy = x - self.player.x, y - self.player.y
        base_angle = atan2(dy, dx)
        distance = hypot(dx, dy) or 1.0
        self.facing = (dx / distance, dy / distance)
        spec = state.spec
        for pellet in range(spec.pellets):
            spread = uniform(-spec.spread_degrees / 2, spec.spread_degrees / 2) if spec.pellets > 1 else 0
            angle = base_angle + radians(spread)
            self.bullets.append(Bullet(self.player.x, self.player.y,
                                       cos(angle) * 520, sin(angle) * 520, 5,
                                       damage=spec.damage))
        muzzle_x = self.player.x + dx / distance * (self.player.radius + 5)
        muzzle_y = self.player.y + dy / distance * (self.player.radius + 5)
        self.effects.append(VisualEffect(muzzle_x, muzzle_y, "muzzle", .09, .09, 18))
        self.visual_events.append({"kind": "muzzle", "x": muzzle_x, "y": muzzle_y, "scale": 1})
        self.audio_events.append("shoot")
        state.magazine -= 1
        if state.magazine == 0:
            self.reload()
        return True

    def set_aim(self, x: float, y: float) -> None:
        self.aim = (x, y)
        dx, dy = x - self.player.x, y - self.player.y
        distance = hypot(dx, dy)
        if distance:
            self.facing = (dx / distance, dy / distance)

    def clear_aim(self) -> None:
        self.aim = None

    def set_firing(self, firing: bool) -> None:
        self.firing = firing

    def _finish_reload(self) -> None:
        state = self.weapon
        if state.reserve is None:
            state.magazine = state.spec.magazine_size
        else:
            amount = min(state.spec.magazine_size - state.magazine, state.reserve)
            state.magazine += amount
            state.reserve -= amount
        self.reload_timer = 0.0

    def update(self, dt: float, movement: tuple[float, float], aim: tuple[float, float] | None = None,
               firing: bool | None = None) -> None:
        if self.game_over:
            return
        dt = min(dt, .05)
        self.player.anim_phase += dt
        self.player.walk_strength += (min(1.0, hypot(*movement)) - self.player.walk_strength) * min(1, dt * 12)
        self.player.attack_flash_timer = max(0, self.player.attack_flash_timer - dt)
        self.reward_notice_timer = max(0, self.reward_notice_timer - dt)
        mx, my = movement
        length = hypot(mx, my)
        if length > 1:
            mx, my = mx / length, my / length
        self.player.x = min(max(self.player.x + mx * PLAYER_SPEED * dt, PLAYER_RADIUS), self.width - PLAYER_RADIUS)
        self.player.y = min(max(self.player.y + my * PLAYER_SPEED * dt, PLAYER_RADIUS), self.height - PLAYER_RADIUS)

        self.wave_timer += dt
        if self.wave_timer >= 20:
            self.wave_timer -= 20
            self.wave += 1
            self.wave_spawned = 0
            self.wave_target = 5 + (self.wave - 1) * 2
            self.boss_spawned = False
            self.announcement = f"WAVE {self.wave}"
            self.announcement_timer = 2.5
        self.announcement_timer = max(0, self.announcement_timer - dt)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            if self.wave_spawned < self.wave_target:
                self._spawn_enemy()
            self.spawn_timer = max(.28, ENEMY_SPAWN_INTERVAL - (self.wave - 1) * .055)

        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self._finish_reload()
        self.fire_timer -= dt
        active_aim = aim if aim is not None else self.aim
        active_firing = self.firing if firing is None else firing
        if active_firing and active_aim is not None and self.fire_timer <= 0:
            if self.weapon.magazine > 0 and self.reload_timer <= 0:
                self.shoot_toward(*active_aim)
                self.fire_timer = self.weapon.spec.fire_interval
            elif self.weapon.magazine == 0 and self.reload_timer <= 0:
                self.reload()

        for enemy in self.enemies:
            enemy.anim_phase += dt * (1.4 if enemy.kind == "fast" else .85 if enemy.kind == "heavy" else 1)
            enemy.hit_flash_timer = max(0, enemy.hit_flash_timer - dt)
            enemy.attack_flash_timer = max(0, enemy.attack_flash_timer - dt)
            dx, dy = self.player.x - enemy.x, self.player.y - enemy.y
            distance = hypot(dx, dy) or 1.0
            enemy.facing = (dx / distance, dy / distance)
            if distance > enemy.radius + self.player.radius:
                enemy.x += dx / distance * enemy.speed * dt
                enemy.y += dy / distance * enemy.speed * dt
                enemy.walk_strength = min(1, enemy.walk_strength + dt * 2.5)
                enemy.dust_timer -= dt
                if enemy.dust_timer <= 0 and self.upgrades is not None:
                    enemy.dust_timer = .42
                    if enemy.kind in ("heavy", "boss"):
                        self.visual_events.append({"kind": "dust", "x": enemy.x, "y": enemy.y, "scale": 1.2})
            else:
                enemy.walk_strength = max(0, enemy.walk_strength - dt * 4)
                enemy.attack_timer -= dt
                if enemy.attack_timer <= 0:
                    self.player.health -= enemy.damage
                    self.player.attack_flash_timer = .08
                    enemy.attack_timer = 0.8 if enemy.kind != "boss" else .65
                    self.effects.append(VisualEffect(enemy.x, enemy.y, "explosion", .32, .32, 27))
                    self.visual_events.append({"kind": "explosion", "x": enemy.x, "y": enemy.y,
                                               "scale": 1.4 if enemy.boss else 1})
                    if enemy.boss:
                        self.visual_events.append({"kind": "boss", "x": enemy.x, "y": enemy.y, "scale": 1.4})
                    self.audio_events.append("hit")
                    if self.player.health <= 0:
                        self.player.health = 0
                        self.game_over = True
                        self.audio_events.append("death")

        for bullet in self.bullets:
            bullet.update(dt)
            for enemy in self.enemies:
                if enemy.health > 0 and overlaps(bullet, enemy):
                    enemy.health -= bullet.damage
                    enemy.hit_flash_timer = .12
                    self.visual_events.append({"kind": "impact", "x": enemy.x, "y": enemy.y,
                                               "scale": 1.5 if enemy.boss else 1})
                    bullet.radius = 0
                    if enemy.health <= 0:
                        self.score += 10 + enemy.reward * 2
                        self.coins += enemy.reward
                        self.kills += 1
                        self.reward_notice = f"+{enemy.reward} COINS"
                        self.reward_notice_timer = 1.2
                        self.audio_events.append("death")
                        self.effects.append(VisualEffect(enemy.x, enemy.y, "hit", .28, .28,
                                                         42 if enemy.boss else 20))
                        self.visual_events.append({"kind": "boss" if enemy.boss else "death",
                                                   "x": enemy.x, "y": enemy.y,
                                                   "scale": 1.8 if enemy.boss else 1.1})
                    else:
                        self.audio_events.append("hit")
                        self.effects.append(VisualEffect(enemy.x, enemy.y, "hit", .16, .16, 12))
                    break
        self.enemies = [enemy for enemy in self.enemies if enemy.health > 0]
        self.bullets = [bullet for bullet in self.bullets if bullet.radius > 0 and
                        -10 < bullet.x < self.width + 10 and -10 < bullet.y < self.height + 10]
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.ttl > 0]

    def _spawn_enemy(self) -> None:
        boss = self.wave % 5 == 0 and not self.boss_spawned and self.wave_spawned == self.wave_target - 1
        if boss:
            kind = "boss"
            self.boss_spawned = True
            self.announcement = "BOSS APPROACHING"
            self.announcement_timer = 2.5
            self.audio_events.append("boss")
        else:
            choices = ["normal"]
            if self.wave >= 2:
                choices.append("fast")
            if self.wave >= 3:
                choices.append("heavy")
            kind = choice(choices)
        stats = ENEMY_TYPES[kind]
        radius = stats["radius"]
        side = int(uniform(0, 4))
        if side == 0:
            x, y = uniform(0, self.width), -radius
        elif side == 1:
            x, y = self.width + radius, uniform(0, self.height)
        elif side == 2:
            x, y = uniform(0, self.width), self.height + radius
        else:
            x, y = -radius, uniform(0, self.height)
        difficulty = 1 + .08 * (self.wave - 1)
        max_health = int(stats["health"] * difficulty)
        self.enemies.append(Actor(x, y, radius, max_health, kind,
                                  stats["speed"] * (1 + .025 * (self.wave - 1)),
                                  stats["damage"], stats["reward"], boss, max_health=max_health))
        if boss:
            self.visual_events.append({"kind": "boss", "x": x, "y": y, "scale": 1.8})
        self.wave_spawned += 1
