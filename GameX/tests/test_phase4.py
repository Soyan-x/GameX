"""Regression checks for menus, pause, settings, upgrades, saves, and audio."""

import json
import tempfile
import unittest
import wave
from pathlib import Path

from kivy.uix.button import Button

from gamex.app import GameXApp
from gamex.audio import generate_audio_assets
from gamex.save_system import SaveStore


def descendants(widget):
    yield widget
    for child in getattr(widget, "children", ()):
        yield from descendants(child)


class Phase4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = GameXApp()
        self.app.data_dir_override = self.temp.name
        self.app.audio_enabled = False
        self.app.root = self.app.build()
        self.game = self.app.game_view
        self.game._event.cancel()

    def tearDown(self):
        from kivy.core.window import Window
        Window.unbind(mouse_pos=self.game._mouse_moved,
                      on_mouse_down=self.game._on_window_mouse_down,
                      on_mouse_up=self.game._on_window_mouse_up)
        if self.game._keyboard:
            self.game._keyboard.unbind(on_key_down=self.game._key_down, on_key_up=self.game._key_up)
        self.temp.cleanup()

    def test_main_menu_buttons_are_functional_and_tutorial_is_first_run(self):
        self.assertTrue(self.game.paused)
        labels = {widget.text for widget in descendants(self.app.root) if isinstance(widget, Button)}
        self.assertTrue({"PLAY", "SETTINGS", "WEAPON SHOP", "EXIT"}.issubset(labels))
        play = next(widget for widget in descendants(self.app.root)
                    if isinstance(widget, Button) and widget.text == "PLAY")
        play.trigger_action(duration=0)
        self.assertEqual(self.app.screen, "tutorial")
        self.app.finish_tutorial()
        self.assertEqual(self.app.screen, "game")
        self.assertTrue(self.app.save_store.data["settings"]["tutorial_seen"])

    def test_play_reuses_same_app_window_and_game_view(self):
        from kivy.core.window import Window
        self.app.save_store.data["settings"]["tutorial_seen"] = True
        app_identity = id(self.app)
        window_identity = id(Window)
        manager_identity = id(self.app.root)
        game_identity = id(self.game)
        self.assertIs(self.app.build(), self.app.root)
        self.assertEqual(id(self.app.game_view), game_identity)
        play = next(widget for widget in descendants(self.app.root)
                    if isinstance(widget, Button) and widget.text == "PLAY")
        play.trigger_action(duration=0)
        self.assertEqual(self.app.screen, "game")
        self.assertEqual(id(self.app), app_identity)
        self.assertEqual(id(Window), window_identity)
        self.assertEqual(id(self.app.root), manager_identity)
        self.assertEqual(id(self.game), game_identity)
        self.assertIs(self.app.screen_manager.current_screen.children[0], self.game)

    def test_pause_freezes_world_and_resume_continues(self):
        self.app.start_game()
        self.game.world.player.x = 200
        self.app.pause_game()
        self.assertTrue(self.game.paused)
        self.assertEqual(self.app.screen, "pause")
        before = (self.game.world.player.x, self.game.world.wave_timer, self.game.world.spawn_timer)
        self.game._tick(.05)
        self.assertEqual(before, (self.game.world.player.x, self.game.world.wave_timer,
                                  self.game.world.spawn_timer))
        self.app.resume_game()
        self.assertFalse(self.game.paused)

    def test_pause_button_and_gameover_restart_preserve_rewards(self):
        self.app.start_game()
        px, py, width, height = self.game.pause_button_rect
        touch = type("Touch", (), {"pos": (px + width / 2, py + height / 2),
                                   "profile": (), "uid": 808,
                                   "is_mouse_scrolling": False})()
        self.assertTrue(self.game.on_touch_down(touch))
        self.assertEqual(self.app.screen, "pause")
        self.app.resume_game()
        self.game.world.coins = 11
        self.game.world.score = 55
        self.game.world.game_over = True
        self.app._finalize_run()
        panel_w, panel_h = min(420, self.game.width * .82), min(250, self.game.height * .72)
        button_x = (self.game.width - panel_w) / 2 + panel_w / 2
        button_y = (self.game.height - panel_h) / 2 + 60
        self.game.on_mouse_down(button_x, button_y, "left", [])
        self.assertEqual(self.app.screen, "game")
        self.assertFalse(self.game.world.game_over)
        self.assertEqual(self.app.save_store.data["profile"]["total_coins"], 11)

    def test_hud_overlay_does_not_intercept_window_mouse_input(self):
        from kivy.core.window import Window
        from kivy.uix.label import Label
        self.app.start_game()
        screen = self.app.screen_manager.current_screen
        screen.add_widget(Label(text="HUD", size_hint=(1, 1), disabled=True))
        x = self.game.x + self.game.width / 2
        y = self.game.y + self.game.height / 2
        Window.dispatch("on_mouse_down", x, y, "left", [])
        self.assertTrue(self.game.world.firing)
        Window.dispatch("on_mouse_up", x, y, "left", [])
        self.assertFalse(self.game.world.firing)

    def test_restart_confirmation_saves_run_coins_and_keeps_permanent_profile(self):
        self.app.start_game()
        self.game.world.coins = 23
        self.game.world.score = 140
        self.game.world.wave = 4
        self.app.pause_game()
        self.app.confirm_restart_screen()
        self.assertEqual(self.app.screen, "restart_confirmation")
        self.app.confirm_restart()
        profile = self.app.save_store.data["profile"]
        self.assertEqual(profile["total_coins"], 23)
        self.assertEqual(profile["high_score"], 140)
        self.assertEqual(profile["best_wave"], 4)
        self.assertEqual(self.game.world.coins, 0)
        self.assertEqual(self.game.world.score, 0)
        self.assertTrue(self.app.run_active)

    def test_settings_sliders_persist_and_apply_sensitivities(self):
        self.app.open_settings()
        self.app.menu_factory.sliders["music_volume"].value = .63
        self.app.menu_factory.sliders["mouse_sensitivity"].value = 1.7
        self.app.menu_factory.sliders["touch_sensitivity"].value = .8
        self.app.menu_factory.quality_spinner.text = "High"
        self.app.menu_factory.shake_switch.active = False
        self.app.close_settings()
        reopened = SaveStore(self.temp.name)
        reopened.load()
        settings = reopened.data["settings"]
        self.assertAlmostEqual(settings["music_volume"], .63, places=2)
        self.assertAlmostEqual(settings["mouse_sensitivity"], 1.7, places=2)
        self.assertAlmostEqual(self.game.touch_sensitivity, .8, places=2)
        self.assertEqual(settings["graphics_quality"], "high")
        self.assertFalse(settings["screen_shake"])
        self.assertEqual(self.game.renderer.quality, "high")
        self.assertFalse(self.game.renderer.shake_enabled)

    def test_shop_purchase_cost_and_insufficient_balance(self):
        self.app.save_store.data["profile"]["total_coins"] = 100
        self.app.open_shop()
        self.assertTrue(self.app.buy_upgrade("Pistol", "damage"))
        self.assertEqual(self.app.save_store.data["profile"]["total_coins"], 60)
        self.assertEqual(self.game.world.weapon_states[0].spec.damage, 28)
        persisted = SaveStore(self.temp.name)
        persisted.load()
        self.assertEqual(persisted.data["upgrades"]["Pistol"]["damage"], 1)
        self.assertEqual(persisted.data["profile"]["total_coins"], 60)
        self.app.save_store.data["profile"]["total_coins"] = 0
        self.assertFalse(self.app.buy_upgrade("Pistol", "reload"))
        self.assertEqual(self.app.save_store.data["upgrades"]["Pistol"]["reload"], 0)

    def test_save_load_clamps_data_and_preserves_corrupt_file(self):
        path = Path(self.temp.name) / "gamex_save.json"
        store = SaveStore(self.temp.name)
        store.load()
        store.data["profile"]["total_coins"] = 900
        store.data["settings"]["music_volume"] = 3
        store.save()
        loaded = SaveStore(self.temp.name)
        loaded.load()
        self.assertEqual(loaded.data["profile"]["total_coins"], 900)
        self.assertEqual(loaded.data["settings"]["music_volume"], 1)
        path.write_text("{broken", encoding="utf-8")
        corrupt = SaveStore(self.temp.name)
        corrupt.load()
        self.assertEqual(corrupt.data["profile"]["total_coins"], 0)
        self.assertTrue(path.with_suffix(".json.corrupt").exists())
        self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_audio_assets_are_original_local_wav_files(self):
        paths = generate_audio_assets(Path(self.temp.name) / "audio")
        self.assertEqual(set(paths), {"music", "shoot", "reload", "hit", "death", "boss"})
        for path in paths.values():
            self.assertTrue(path.is_file())
            with wave.open(str(path), "rb") as sound:
                self.assertEqual(sound.getframerate(), 22050)
                self.assertGreater(sound.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
