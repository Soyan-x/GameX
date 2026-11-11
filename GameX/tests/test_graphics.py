"""Graphics quality, cache, and bounded-particle regression tests."""

import tempfile
import unittest

from gamex.environment import BattlefieldRenderer
from gamex.particles import ParticlePool
from gamex.save_system import SaveStore
from gamex.widgets import GameView


class GraphicsTests(unittest.TestCase):
    def setUp(self):
        self.game = GameView(size=(960, 600))
        self.game._event.cancel()

    def tearDown(self):
        from kivy.core.window import Window
        Window.unbind(mouse_pos=self.game._mouse_moved,
                      on_mouse_down=self.game._on_window_mouse_down,
                      on_mouse_up=self.game._on_window_mouse_up)
        if self.game._keyboard:
            self.game._keyboard.unbind(on_key_down=self.game._key_down, on_key_up=self.game._key_up)

    def test_quality_settings_are_validated_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SaveStore(directory)
            store.load()
            store.update_settings(graphics_quality="high", screen_shake=False)
            loaded = SaveStore(directory)
            settings = loaded.load()["settings"]
            self.assertEqual(settings["graphics_quality"], "high")
            self.assertFalse(settings["screen_shake"])
            settings = SaveStore._sanitize({"settings": {"graphics_quality": "ultra"}})["settings"]
            self.assertEqual(settings["graphics_quality"], "medium")

    def test_particle_pool_is_bounded_and_effects_expire(self):
        pool = ParticlePool("low")
        capacity = len(pool.particles)
        for _ in range(100):
            pool.emit(10, 20, "explosion", 2)
        self.assertEqual(len(pool.particles), capacity)
        self.assertLessEqual(sum(p.active for p in pool.particles), capacity)
        pool.update(20)
        pool.update(20)
        self.assertEqual(sum(p.active for p in pool.particles), 0)
        pool.set_quality("high")
        self.assertEqual(len(pool.particles), ParticlePool.CAPS["high"])

    def test_environment_cache_and_quality_rebuild(self):
        env = BattlefieldRenderer(self.game)
        env.rebuild()
        first_shake = env.shake
        env.rebuild()
        self.assertIs(env.shake, first_shake)
        env.set_quality("high")
        env.rebuild()
        self.assertIsNot(env.shake, first_shake)

    def test_renderer_smoke_draws_entities_and_quality_modes(self):
        from gamex.entities import Actor
        self.game.world.enemies = [Actor(160, 180, 20, 50, "boss", 20, 2, 20, True, max_health=50)]
        for quality in ("low", "medium", "high"):
            self.game.renderer.configure(quality, shake=False)
            self.game._redraw(.016)
            self.assertEqual(self.game.renderer.quality, quality)
            self.assertEqual(self.game.renderer.particles.CAPS[quality],
                             len(self.game.renderer.particles.particles))


if __name__ == "__main__":
    unittest.main()
