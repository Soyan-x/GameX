"""Responsive, touch-friendly GameX menu and overlay builders."""

from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch

from .save_system import UPGRADE_COSTS
from .weapons import WEAPONS


class MenuFactory:
    def __init__(self, app):
        self.app = app

    def _panel(self, title, subtitle=""):
        root = FloatLayout()
        with root.canvas.before:
            Color(.025, .045, .05, 1)
            background = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda widget, pos: setattr(background, "pos", pos),
                  size=lambda widget, size: setattr(background, "size", size))
        panel = BoxLayout(orientation="vertical", spacing=dp(10), padding=(dp(22), dp(18)),
                          size_hint=(.82, .9), pos_hint={"center_x": .5, "center_y": .5})
        root.add_widget(panel)
        panel.add_widget(Label(text=title, font_size="32sp", bold=True,
                               color=(.76, .88, .72, 1), size_hint_y=None, height=dp(48)))
        if subtitle:
            panel.add_widget(Label(text=subtitle, font_size="15sp", color=(.68, .76, .72, 1),
                                   size_hint_y=None, height=dp(38)))
        return root, panel

    @staticmethod
    def _button(text, callback, height=48):
        button = Button(text=text, font_size="17sp", bold=True,
                        color=(.91, .96, .89, 1), background_normal="",
                        background_color=(.12, .28, .23, 1),
                        size_hint_y=None, height=dp(height))
        button.bind(on_release=lambda *_: callback())
        return button

    @staticmethod
    def _backdrop(root):
        with root.canvas.before:
            Color(.025, .045, .05, 1)
            rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda widget, pos: setattr(rect, "pos", pos),
                  size=lambda widget, size: setattr(rect, "size", size))

    def main_menu(self):
        profile = self.app.save_store.data["profile"]
        root, panel = self._panel("GAMEX", "OFFLINE ZOMBIE SURVIVAL")
        panel.add_widget(Label(text=f"HIGH SCORE  {profile['high_score']}     BEST WAVE  {profile['best_wave']}\n"
                                    f"COINS  {profile['total_coins']}     RUNS  {profile['games_played']}",
                               font_size="15sp", color=(.83, .85, .74, 1), size_hint_y=None, height=dp(54)))
        panel.add_widget(self._button("PLAY", self.app.play_from_menu, 54))
        panel.add_widget(self._button("SETTINGS", self.app.open_settings))
        panel.add_widget(self._button("WEAPON SHOP", self.app.open_shop))
        panel.add_widget(self._button("EXIT", self.app.stop))
        return root

    def pause_menu(self):
        root, panel = self._panel("PAUSED", "The battlefield is on hold.")
        panel.add_widget(self._button("RESUME", self.app.resume_game, 54))
        panel.add_widget(self._button("RESTART RUN", self.app.confirm_restart_screen))
        panel.add_widget(self._button("MAIN MENU", self.app.return_to_menu))
        return root

    def restart_confirmation(self):
        root, panel = self._panel("RESTART RUN?", "This ends the current run and saves its rewards.")
        panel.add_widget(self._button("CONFIRM RESTART", self.app.confirm_restart, 54))
        panel.add_widget(self._button("CANCEL", self.app.pause_game))
        return root

    def tutorial(self):
        root, panel = self._panel("FIELD GUIDE", "Quick controls briefing")
        for line in (
            "MOVE  ·  WASD / ARROWS or drag the left joystick",
            "AIM  ·  Move the mouse or touch the right side",
            "FIRE  ·  Hold left mouse or the right fire button",
            "RELOAD  ·  Press R or tap RELOAD; empty magazines reload",
            "WEAPONS  ·  Press 1 / 2 / 3 or use weapon buttons",
            "Survive waves, earn coins, and upgrade weapons in the shop.",
        ):
            panel.add_widget(Label(text=line, font_size="15sp", color=(.82, .87, .81, 1),
                                   size_hint_y=None, height=dp(36)))
        panel.add_widget(self._button("START GAME", self.app.finish_tutorial, 52))
        panel.add_widget(self._button("SKIP TUTORIAL", self.app.finish_tutorial))
        return root

    def settings(self):
        root, panel = self._panel("SETTINGS", "Changes are stored on this device.")
        settings = self.app.save_store.data["settings"]
        self.sliders = {}
        self.value_labels = {}
        rows = (
            ("Master volume", "master_volume", 0, 1, "audio"),
            ("Music volume", "music_volume", 0, 1, "audio"),
            ("Effects volume", "effects_volume", 0, 1, "audio"),
            ("Mouse sensitivity", "mouse_sensitivity", .25, 3, "input"),
            ("Touch sensitivity", "touch_sensitivity", .25, 3, "input"),
        )
        for title, key, minimum, maximum, _group in rows:
            row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(42))
            row.add_widget(Label(text=title, font_size="14sp", color=(.8, .87, .82, 1), size_hint_x=.38))
            slider = Slider(min=minimum, max=maximum, value=settings[key], step=.01)
            value_label = Label(text=f"{settings[key]:.2f}", font_size="13sp", color=(.9, .84, .56, 1), size_hint_x=.13)
            slider.bind(value=lambda _slider, value, k=key, label=value_label: self._setting_changed(k, value, label))
            row.add_widget(slider)
            row.add_widget(value_label)
            panel.add_widget(row)
            self.sliders[key] = slider
            self.value_labels[key] = value_label
        quality_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(42))
        quality_row.add_widget(Label(text="Graphics quality", font_size="14sp",
                                     color=(.8, .87, .82, 1), size_hint_x=.38))
        self.quality_spinner = Spinner(text=settings["graphics_quality"].title(),
                                       values=("Low", "Medium", "High"),
                                       size_hint_x=.62, height=dp(38))
        self.quality_spinner.bind(text=self._quality_changed)
        quality_row.add_widget(self.quality_spinner)
        panel.add_widget(quality_row)
        shake_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(42))
        shake_row.add_widget(Label(text="Screen shake", font_size="14sp",
                                   color=(.8, .87, .82, 1), size_hint_x=.7))
        self.shake_switch = Switch(active=settings["screen_shake"], size_hint_x=.3)
        self.shake_switch.bind(active=lambda _switch, value: self._setting_changed("screen_shake", value, None))
        shake_row.add_widget(self.shake_switch)
        panel.add_widget(shake_row)
        panel.add_widget(self._button("SAVE AND BACK", self.app.close_settings))
        return root

    def _setting_changed(self, key, value, label):
        self.app.save_store.data["settings"][key] = value
        if label is not None:
            label.text = f"{value:.2f}"
        self.app.apply_settings()

    def _quality_changed(self, _spinner, value):
        self.app.save_store.data["settings"]["graphics_quality"] = value.lower()
        self.app.apply_settings()

    def shop(self):
        root, panel = self._panel("WEAPON SHOP", "Spend run-earned coins on permanent upgrades.")
        coins = self.app.save_store.data["profile"]["total_coins"]
        panel.add_widget(Label(text=f"AVAILABLE COINS  {coins}", font_size="17sp",
                               color=(.96, .79, .35, 1), size_hint_y=None, height=dp(30)))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        rows = BoxLayout(orientation="vertical", spacing=dp(5), size_hint_y=None)
        rows.bind(minimum_height=rows.setter("height"))
        for weapon in WEAPONS:
            levels = self.app.save_store.data["upgrades"][weapon.name]
            rows.add_widget(Label(text=f"{weapon.name.upper()}  ·  DAMAGE {levels['damage']}  "
                                       f"RELOAD {levels['reload']}  MAG {levels['magazine']}",
                                  font_size="13sp", color=(.74, .84, .77, 1),
                                  size_hint_y=None, height=dp(25)))
            row = BoxLayout(orientation="horizontal", spacing=dp(5), size_hint_y=None, height=dp(38))
            for upgrade in UPGRADE_COSTS:
                level = levels[upgrade]
                suffix = "MAX" if level >= len(UPGRADE_COSTS[upgrade]) else f"{UPGRADE_COSTS[upgrade][level]} COINS"
                text = f"{upgrade.title()} {suffix}"
                button = self._button(text, lambda w=weapon.name, u=upgrade: self.app.buy_upgrade(w, u), 36)
                button.font_size = "11sp"
                row.add_widget(button)
            rows.add_widget(row)
        scroll.add_widget(rows)
        panel.add_widget(scroll)
        panel.add_widget(self._button("BACK", self.app.return_to_menu))
        return root
