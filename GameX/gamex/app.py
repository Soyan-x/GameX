"""Application flow, persistent profile, audio, and screen transitions."""

from pathlib import Path

from kivy.app import App
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager

from .audio import AudioManager
from .menus import MenuFactory
from .save_system import SaveStore
from .widgets import GameView
from .world import GameWorld


class GameXApp(App):
    title = "GameX"

    def build(self):
        if hasattr(self, "screen_manager"):
            return self.screen_manager
        data_dir_override = getattr(self, "data_dir_override", None)
        data_dir = Path(data_dir_override if data_dir_override is not None else self.user_data_dir)
        self.save_store = SaveStore(data_dir)
        self.save_store.load()
        self.audio_manager = AudioManager(data_dir / "audio",
                                         self.save_store.data["settings"],
                                         enabled=getattr(self, "audio_enabled", True))
        self.menu_factory = MenuFactory(self)
        self.screen_manager = ScreenManager(transition=FadeTransition(duration=.16))
        self.screens = {}
        self.game_view = GameView(world=GameWorld(self.save_store.data["upgrades"]),
                                  size_hint=(1, 1))
        self.game_view.audio_manager = self.audio_manager
        self.game_view.pause_callback = self.pause_game
        self.game_view.restart_callback = self.start_game
        self.game_view.game_over_callback = self._finalize_run
        self.game_view.paused = True
        self.screen = "menu"
        self.run_active = False
        self.run_finalized = False
        self.apply_settings()
        self._show("menu", self.menu_factory.main_menu())
        self.audio_manager.play_music()
        return self.screen_manager

    def _show(self, name, widget):
        if name != "game":
            self.game_view.clear_input_state()
        self.screen = name
        screen = self.screens.get(name)
        if screen is None:
            screen = Screen(name=name)
            self.screens[name] = screen
            self.screen_manager.add_widget(screen)
        else:
            screen.clear_widgets()
        screen.add_widget(widget)
        self.game_view.input_enabled = name == "game" and not self.game_view.paused
        self.screen_manager.current = name

    def play_from_menu(self):
        if not self.save_store.data["settings"]["tutorial_seen"]:
            self._show("tutorial", self.menu_factory.tutorial())
        else:
            self.start_game()

    def finish_tutorial(self):
        self.save_store.data["settings"]["tutorial_seen"] = True
        self.save_store.save()
        self.start_game()

    def start_game(self):
        self.game_view.clear_input_state()
        self.game_view.reset_game()
        self.game_view.world.apply_upgrades(self.save_store.data["upgrades"])
        self.game_view.paused = False
        self.run_active = True
        self.run_finalized = False
        self.audio_manager.play_music()
        self._show("game", self.game_view)

    def pause_game(self):
        if self.screen == "restart_confirmation":
            self._show("pause", self.menu_factory.pause_menu())
            return
        if self.screen != "game" or self.game_view.world.game_over:
            return
        self.game_view.paused = True
        self.game_view.clear_input_state()
        self.audio_manager.pause_music()
        self._show("pause", self.menu_factory.pause_menu())

    def resume_game(self):
        self.game_view.paused = False
        self.audio_manager.play_music()
        self._show("game", self.game_view)

    def confirm_restart_screen(self):
        self._show("restart_confirmation", self.menu_factory.restart_confirmation())

    def confirm_restart(self):
        self._finalize_run()
        self.game_view.clear_input_state()
        self.game_view.reset_game()
        self.game_view.world.apply_upgrades(self.save_store.data["upgrades"])
        self.game_view.paused = False
        self.run_active = True
        self.run_finalized = False
        self._show("game", self.game_view)
        self.audio_manager.play_music()

    def return_to_menu(self):
        self._finalize_run()
        self.game_view.paused = True
        self.game_view.clear_input_state()
        self.audio_manager.play_music()
        self._show("menu", self.menu_factory.main_menu())

    def open_settings(self):
        self._show("settings", self.menu_factory.settings())

    def close_settings(self):
        self.save_store.save()
        self.apply_settings()
        self._show("menu", self.menu_factory.main_menu())

    def apply_settings(self):
        if not hasattr(self, "save_store"):
            return
        settings = self.save_store.data["settings"]
        if hasattr(self, "game_view"):
            self.game_view.mouse_sensitivity = settings["mouse_sensitivity"]
            self.game_view.touch_sensitivity = settings["touch_sensitivity"]
            self.game_view.graphics_quality = settings["graphics_quality"]
            self.game_view.screen_shake_enabled = settings["screen_shake"]
            self.game_view.renderer.configure(settings["graphics_quality"], settings["screen_shake"])
        if hasattr(self, "audio_manager"):
            self.audio_manager.set_settings(settings)

    def open_shop(self):
        self._show("shop", self.menu_factory.shop())

    def buy_upgrade(self, weapon, upgrade):
        purchased, _price = self.save_store.purchase_upgrade(weapon, upgrade)
        if purchased:
            self.game_view.world.apply_upgrades(self.save_store.data["upgrades"])
        self._show("shop", self.menu_factory.shop())
        return purchased

    def _finalize_run(self):
        if not self.run_active or self.run_finalized:
            return
        world = self.game_view.world
        self.save_store.finish_run(world.score, world.wave, world.coins, world.kills)
        self.run_finalized = True
        self.run_active = False

    def on_pause(self):
        if self.screen == "game":
            self.pause_game()
        self.audio_manager.pause_music()
        return True

    def on_stop(self):
        self._finalize_run()
        if hasattr(self, "save_store"):
            self.save_store.save()
        if hasattr(self, "audio_manager"):
            self.audio_manager.pause_music()
