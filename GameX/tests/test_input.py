"""Headless regression tests for GameView input routing."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window

from gamex.widgets import GameView
from gamex.entities import Actor, Bullet


class FakeTouch:
    def __init__(self, uid, x, y, profile=()):
        self.uid = uid
        self.x, self.y = x, y
        self.profile = list(profile)
        self.button = None
        self.is_mouse_scrolling = False
        self.grab_current = None

    @property
    def pos(self):
        return self.x, self.y

    def grab(self, widget, exclusive=False):
        self.grab_current = widget

    def ungrab(self, widget):
        if self.grab_current is widget:
            self.grab_current = None


class InputTests(unittest.TestCase):
    def setUp(self):
        self.root = FloatLayout(size=(960, 600))
        self.game = GameView(size=(960, 600))
        self.root.add_widget(self.game)
        hud = Label(text="HUD", size=(960, 38), pos=(0, 562), disabled=True)
        self.root.add_widget(hud)
        self.game._event.cancel()

    def tearDown(self):
        Window.unbind(mouse_pos=self.game._mouse_moved,
                      on_mouse_down=self.game._on_window_mouse_down,
                      on_mouse_up=self.game._on_window_mouse_up)
        if self.game._keyboard:
            self.game._keyboard.unbind(on_key_down=self.game._key_down, on_key_up=self.game._key_up)

    def test_keyboard_moves_player(self):
        before = self.game.world.player.x
        self.game._key_down(None, (100, "d"), "d", [])
        self.game._tick(0.05)
        self.assertGreater(self.game.world.player.x, before)
        self.game._key_up(None, (100, "d"))
        self.assertNotIn("d", self.game.keys)

    def test_mouse_button_and_motion_aim_and_fire(self):
        Window.mouse_pos = (820, 300)
        self.assertNotEqual(self.game.world.aim, None)
        self.assertGreater(self.game.world.facing[0], 0)
        Window.dispatch("on_mouse_down", 800, 300, "left", [])
        self.assertIn("left", self.game.mouse_buttons)
        self.game._tick(0.05)
        self.assertTrue(self.game.world.bullets)
        bullet = self.game.world.bullets[0]
        self.assertGreater(bullet.vx, 0)
        Window.dispatch("on_mouse_up", 820, 300, "left", [])
        self.assertNotIn("left", self.game.mouse_buttons)
        self.assertFalse(self.game.world.firing)

    def test_mouse_hud_overlay_does_not_block_window_mouse_dispatch(self):
        overlay = Label(text="HUD", size=self.game.size, pos=self.game.pos, disabled=True)
        self.root.add_widget(overlay)
        Window.dispatch("on_mouse_down", 700, 320, "left", [])
        self.assertTrue(self.game.world.firing)
        Window.dispatch("on_mouse_up", 700, 320, "left", [])
        self.assertFalse(self.game.world.firing)

    def test_input_state_clears_on_screen_change(self):
        self.game.keys.add("w")
        self.game.mouse_buttons.add("left")
        self.game.move_vector = (1, 0)
        self.game.world.set_firing(True)
        self.game.clear_input_state()
        self.assertFalse(self.game.keys)
        self.assertFalse(self.game.mouse_buttons)
        self.assertEqual(self.game.move_vector, (0.0, 0.0))
        self.assertFalse(self.game.world.firing)

    def test_touch_joystick_moves_and_release_clears(self):
        cx, cy = self.game.joystick_center
        touch = FakeTouch(1, cx + 40, cy)
        self.assertTrue(self.game.on_touch_down(touch))
        self.assertIs(touch.grab_current, self.game)
        before = self.game.world.player.x
        self.game._tick(0.05)
        self.assertGreater(self.game.world.player.x, before)
        self.assertTrue(self.game.on_touch_up(touch))
        self.assertEqual(self.game.move_vector, (0.0, 0.0))
        self.assertIsNone(self.game.move_touch)

    def test_touch_fire_button_fires_and_release_clears(self):
        cx, cy = self.game.fire_center
        touch = FakeTouch(2, cx, cy)
        self.assertTrue(self.game.on_touch_down(touch))
        self.game._tick(0.05)
        self.assertTrue(self.game.world.bullets)
        self.assertTrue(self.game.on_touch_up(touch))
        self.assertFalse(self.game.world.firing)
        self.assertIsNone(self.game.world.aim)

    def test_unowned_touches_propagate_and_mouse_emulation_uses_mouse_input(self):
        outside_left = FakeTouch(3, 10, 300)
        self.assertFalse(self.game.on_touch_down(outside_left))
        mouse_touch = FakeTouch(4, 700, 300, profile=("button",))
        mouse_touch.button = "left"
        self.assertTrue(self.game.on_touch_down(mouse_touch))
        self.assertIn("left", self.game.mouse_buttons)
        self.assertTrue(self.game.world.firing)
        self.assertTrue(self.game.on_touch_up(mouse_touch))
        self.assertFalse(self.game.world.firing)

    def test_restart_clears_controls_and_fire_can_start_again(self):
        self.game.world.game_over = True
        self.game.keys.add("w")
        self.game.mouse_buttons.add("left")
        self.game.reset_game()
        self.assertFalse(self.game.world.game_over)
        self.assertFalse(self.game.keys)
        self.assertFalse(self.game.mouse_buttons)
        self.assertFalse(self.game.world.firing)
        self.game.world.set_aim(800, 300)
        self.game.world.set_firing(True)
        self.game.world.update(0.05, (0, 0))
        self.assertTrue(self.game.world.bullets)

    def test_game_over_restart_button_responds_to_mouse_and_touch(self):
        self.game.world.game_over = True
        panel_w, panel_h = min(420, self.game.width * .82), min(250, self.game.height * .72)
        px = self.game.x + (self.game.width - panel_w) / 2
        py = self.game.y + (self.game.height - panel_h) / 2
        bx, by = px + panel_w / 2, py + 60
        self.assertTrue(self.game.on_mouse_down(bx, by, "left", []))
        self.assertFalse(self.game.world.game_over)
        self.game.world.game_over = True
        touch = FakeTouch(5, bx, by)
        self.assertTrue(self.game.on_touch_down(touch))
        self.assertFalse(self.game.world.game_over)

    def test_renderer_draws_and_world_creates_timed_combat_effects(self):
        world = self.game.world
        world.set_aim(world.player.x + 100, world.player.y)
        world.set_firing(True)
        world.update(0.016, (0, 0))
        self.assertEqual(world.effects[0].kind, "muzzle")
        self.assertEqual(world.ammo, world.max_ammo - 1)
        enemy_x = world.player.x + 45
        world.enemies = [Actor(enemy_x, world.player.y + 20, 16)]
        world.bullets = [Bullet(enemy_x, world.player.y + 20, 0, 0, 5)]
        world.update(0.016, (0, 0), firing=False)
        self.assertEqual(world.score, 12)
        self.assertTrue(any(effect.kind == "hit" for effect in world.effects))
        self.game._redraw()

    def test_controls_scale_and_wave_counter_advances(self):
        self.game.size = (640, 360)
        self.game._layout()
        self.assertLessEqual(self.game.joystick_radius, 43.2)
        self.game.world.wave_timer = 19.99
        self.game.world.update(0.05, (0, 0), firing=False)
        self.assertEqual(self.game.world.wave, 2)

    def test_weapon_keyboard_and_touch_switching(self):
        self.game._key_down(None, (50, "2"), "2", [])
        self.assertEqual(self.game.world.weapon.spec.name, "Assault Rifle")
        rect = self.game.weapon_button_rects[2]
        touch = FakeTouch(6, rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
        self.assertTrue(self.game.on_touch_down(touch))
        self.assertEqual(self.game.world.weapon.spec.name, "Shotgun")
        self.assertIn(touch.uid, self.game.ui_touches)
        self.game.on_touch_up(touch)
        self.assertNotIn(touch.uid, self.game.ui_touches)

    def test_pistol_unlimited_reserve_and_damage(self):
        world = self.game.world
        self.assertEqual(world.weapon.spec.name, "Pistol")
        self.assertIsNone(world.reserve_ammo)
        self.assertTrue(world.shoot_toward(world.player.x + 100, world.player.y))
        self.assertEqual(world.bullets[-1].damage, 24)
        self.assertEqual(world.ammo, 11)

    def test_rifle_limited_reserve_and_timed_reload(self):
        world = self.game.world
        world.select_weapon(1)
        for _ in range(world.ammo):
            self.assertTrue(world.shoot_toward(world.player.x + 100, world.player.y))
        self.assertEqual(world.ammo, 0)
        self.assertEqual(world.reserve_ammo, 150)
        self.assertGreater(world.reload_timer, 0)
        for _ in range(30):
            world.update(.05, (0, 0), firing=False)
        self.assertEqual(world.ammo, 30)
        self.assertEqual(world.reserve_ammo, 120)

    def test_shotgun_fires_multiple_spread_pellets(self):
        world = self.game.world
        world.select_weapon(2)
        self.assertTrue(world.shoot_toward(world.player.x + 100, world.player.y))
        self.assertEqual(len(world.bullets), 6)
        self.assertTrue(all(bullet.damage == 12 for bullet in world.bullets))
        self.assertEqual(world.ammo, 5)
        self.assertGreater(len({round(bullet.vy, 2) for bullet in world.bullets}), 1)

    def test_manual_reload_button_and_key(self):
        world = self.game.world
        world.select_weapon(1)
        world.ammo = 12
        self.game._key_down(None, (114, "r"), "r", [])
        self.assertGreater(world.reload_timer, 0)
        world.reload_timer = 0
        world.ammo = 10
        rect = self.game.reload_button_rect
        touch = FakeTouch(7, rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
        self.assertTrue(self.game.on_touch_down(touch))
        self.assertGreater(world.reload_timer, 0)

    def test_enemy_variants_boss_difficulty_and_attack_damage(self):
        world = self.game.world
        with patch("gamex.world.choice", return_value="normal"):
            world._spawn_enemy()
        normal = world.enemies[-1]
        self.assertEqual(normal.kind, "normal")
        world.wave = 3
        with patch("gamex.world.choice", return_value="fast"):
            world._spawn_enemy()
        fast = world.enemies[-1]
        self.assertLess(fast.health, normal.health)
        self.assertGreater(fast.speed, normal.speed)
        world.wave = 5
        world.wave_target = 5
        world.wave_spawned = 4
        world.boss_spawned = False
        world._spawn_enemy()
        self.assertEqual(world.enemies[-1].kind, "boss")
        self.assertTrue(world.enemies[-1].boss)

        world.enemies = [Actor(world.player.x, world.player.y, 22, health=120,
                               kind="heavy", speed=42, damage=2, reward=16)]
        health = world.player.health
        world.update(.05, (0, 0), firing=False)
        self.assertEqual(world.player.health, health - 2)

    def test_enemy_reward_coins_score_and_wave_scaling(self):
        world = self.game.world
        enemy_x, enemy_y = world.player.x + 80, world.player.y + 30
        world.enemies = [Actor(enemy_x, enemy_y, 13, health=1,
                               kind="fast", reward=8)]
        world.bullets = [Bullet(enemy_x, enemy_y, 0, 0, 5, damage=15)]
        world.update(.01, (0, 0), firing=False)
        self.assertEqual(world.coins, 8)
        self.assertEqual(world.score, 26)
        world.wave_timer = 19.99
        world.update(.05, (0, 0), firing=False)
        self.assertEqual(world.wave, 2)
        self.assertEqual(world.wave_target, 7)
        self.assertEqual(world.announcement, "WAVE 2")

    def test_restart_resets_weapons_rewards_and_wave_state(self):
        world = self.game.world
        world.select_weapon(2)
        world.coins = 90
        world.wave = 7
        world.weapon.magazine = 1
        self.game.reset_game()
        self.assertEqual(world.weapon.spec.name, "Pistol")
        self.assertEqual(world.ammo, 12)
        self.assertEqual(world.coins, 0)
        self.assertEqual(world.wave, 1)


if __name__ == "__main__":
    unittest.main()
