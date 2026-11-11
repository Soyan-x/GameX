"""Input adapter and lightweight Kivy widget for the GameX battlefield."""

from math import atan2, cos, hypot, sin

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line
from kivy.uix.widget import Widget

from .renderer import GameRenderer
from .world import GameWorld


class GameView(Widget):
    JOYSTICK_RADIUS = 56
    FIRE_RADIUS = 54

    def __init__(self, world=None, **kwargs):
        super().__init__(**kwargs)
        self.world = world or GameWorld()
        self.renderer = GameRenderer(self)
        self.move_vector = (0.0, 0.0)
        self.move_touch = self.fire_touch = None
        self.ui_touches: set[int] = set()
        self._active_touches = {}
        self.paused = False
        self.input_enabled = True
        self.pause_callback = None
        self.restart_callback = None
        self.game_over_callback = None
        self.audio_manager = None
        self.keys: set[str] = set()
        self.mouse_buttons: set[str] = set()
        self.mouse_aim: tuple[float, float] | None = None
        self.mouse_sensitivity = 1.0
        self.touch_sensitivity = 1.0
        self.graphics_quality = "medium"
        self.screen_shake_enabled = True
        self.renderer.configure(self.graphics_quality, self.screen_shake_enabled)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self, "text")
        if self._keyboard:
            self._keyboard.bind(on_key_down=self._key_down, on_key_up=self._key_up)
        Window.bind(mouse_pos=self._mouse_moved,
                    on_mouse_down=self._on_window_mouse_down,
                    on_mouse_up=self._on_window_mouse_up)
        self.bind(size=self._layout, pos=self._layout)
        self._event = Clock.schedule_interval(self._tick, 1 / 60)

    @property
    def joystick_center(self):
        return self.x + self.width * .15, self.y + self.height * .19

    @property
    def joystick_radius(self):
        return max(38, min(self.JOYSTICK_RADIUS, min(self.width, self.height) * .12))

    @property
    def fire_center(self):
        return self.x + self.width * .86, self.y + self.height * .19

    @property
    def fire_radius(self):
        return max(38, min(self.FIRE_RADIUS, min(self.width, self.height) * .12))

    @property
    def weapon_button_rects(self):
        button_w = min(78, self.width * .105)
        button_h = min(38, self.height * .11)
        y = self.y + self.height * .09
        return [(self.x + self.width * (.40 + i * .11) - button_w / 2,
                 y - button_h / 2, button_w, button_h) for i in range(3)]

    @property
    def reload_button_rect(self):
        button_w = min(70, self.width * .095)
        button_h = min(38, self.height * .11)
        cx, cy = self.x + self.width * .73, self.y + self.height * .19
        return cx - button_w / 2, cy - button_h / 2, button_w, button_h

    @property
    def pause_button_rect(self):
        size = min(42, self.width * .08)
        return self.x + self.width - size - 14, self.y + self.height - size - 12, size, size

    def _layout(self, *_):
        self.world.resize(self.width, self.height)
        self.canvas.ask_update()

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._key_down, on_key_up=self._key_up)
            self._keyboard = None
        self.keys.clear()

    def _key_down(self, _keyboard, keycode, _text, _modifiers):
        if not self.input_enabled or self.paused:
            return False
        key = keycode[1].lower()
        if key in ("escape", "p") and self.pause_callback and not self.world.game_over:
            self.pause_callback()
            return True
        if key in ("w", "a", "s", "d", "up", "down", "left", "right"):
            self.keys.add(key)
            return True
        if key in ("1", "2", "3"):
            self.world.select_weapon(int(key) - 1)
            return True
        if key == "r":
            self.world.reload()
            return True
        if key in ("enter", "spacebar") and self.world.game_over:
            self.restart_callback() if self.restart_callback else self.reset_game()
            return True
        return False

    def _key_up(self, _keyboard, keycode):
        self.keys.discard(keycode[1].lower())
        return True

    def _mouse_moved(self, _window, pos):
        if not self.input_enabled or self.paused or self.parent is None:
            return
        if not self.collide_point(*pos):
            if "left" in self.mouse_buttons:
                self.mouse_buttons.discard("left")
                self.world.set_firing(False)
            return
        self.mouse_aim = self._sensitive_aim(pos[0] - self.x, pos[1] - self.y,
                                            self.mouse_sensitivity)
        self.world.set_aim(*self.mouse_aim)

    def _on_window_mouse_down(self, _window, x, y, button, modifiers):
        if not self.input_enabled or self.paused or self.parent is None:
            return False
        if button == "left" and self._mouse_touch_target(x, y):
            # Let Kivy's mouse provider convert this UI click to a touch so
            # buttons are activated only in the screen that received the press.
            return False
        return self.on_mouse_down(x, y, button, modifiers)

    def _on_window_mouse_up(self, _window, x, y, button, modifiers):
        if button == "left" and not self.input_enabled:
            self.clear_input_state()
            return False
        return self.on_mouse_up(x, y, button, modifiers)

    def _sensitive_aim(self, x, y, sensitivity):
        px, py = self.world.player.x, self.world.player.y
        dx, dy = x - px, y - py
        target_angle = atan2(dy, dx)
        current_angle = atan2(self.world.facing[1], self.world.facing[0])
        difference = atan2(sin(target_angle - current_angle), cos(target_angle - current_angle))
        angle = current_angle + difference * max(.25, min(3, sensitivity))
        return px + cos(angle) * 300, py + sin(angle) * 300

    def on_mouse_down(self, x, y, button, modifiers):
        if not self.input_enabled or self.paused or self.parent is None:
            return False
        if (button == "left" and not self.world.game_over
                and self._inside_rect(x, y, self.pause_button_rect) and self.pause_callback):
            self.pause_callback()
            return True
        if not self.collide_point(x, y):
            return False
        if button == "left":
            if self.world.game_over:
                if self._in_restart_button(x, y):
                    self.restart_callback() if self.restart_callback else self.reset_game()
                return True
            self.mouse_buttons.add(button)
            self._mouse_moved(Window, (x, y))
            self.world.set_firing(True)
            return True
        return False

    def on_mouse_up(self, x, y, button, modifiers):
        if button == "left" and button in self.mouse_buttons:
            self.mouse_buttons.discard(button)
            self.world.set_firing(False)
            return True
        return False

    def on_touch_down(self, touch):
        if not self.input_enabled or self.paused or self.parent is None:
            return super().on_touch_down(touch)
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if getattr(touch, "is_mouse_scrolling", False) or getattr(touch, "button", None) in (
            "scrollup", "scrolldown", "scrollleft", "scrollright"
        ):
            return super().on_touch_down(touch)
        if (not self.world.game_over and self._inside_rect(*touch.pos, self.pause_button_rect)
                and self.pause_callback):
            self.pause_callback()
            return True
        if self.world.game_over:
            if self._in_restart_button(*touch.pos):
                self.restart_callback() if self.restart_callback else self.reset_game()
                return True
            return super().on_touch_down(touch)
        for index, rect in enumerate(self.weapon_button_rects):
            if self._inside_rect(*touch.pos, rect):
                self.world.select_weapon(index)
                self._grab_touch(touch)
                self.ui_touches.add(touch.uid)
                return True
        if self._inside_rect(*touch.pos, self.reload_button_rect):
            self.world.reload()
            self._grab_touch(touch)
            self.ui_touches.add(touch.uid)
            return True
        if "button" in getattr(touch, "profile", ()):
            if getattr(touch, "button", None) == "left":
                if "left" not in self.mouse_buttons:
                    self.mouse_buttons.add("left")
                    self._mouse_moved(Window, touch.pos)
                    self.world.set_firing(True)
                return True
            return super().on_touch_down(touch)
        if self._near(*touch.pos, self.joystick_center, self.joystick_radius * 1.8):
            if self.move_touch is not None:
                return False
            self.move_touch = touch.uid
            self._grab_touch(touch)
            self._set_move(*touch.pos)
            return True
        if self._near(*touch.pos, self.fire_center, self.fire_radius * 1.8):
            if self.fire_touch is not None:
                return False
            self.fire_touch = touch.uid
            self._grab_touch(touch)
            self.world.set_aim(self.world.player.x + self.world.facing[0] * 250,
                               self.world.player.y + self.world.facing[1] * 250)
            self.world.set_firing(True)
            return True
        local_x, local_y = touch.x - self.x, touch.y - self.y
        if local_x >= self.width * .5:
            self.fire_touch = touch.uid
            self._grab_touch(touch)
            self.world.set_aim(*self._sensitive_aim(local_x, local_y, self.touch_sensitivity))
            self.world.set_firing(True)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.input_enabled or self.paused:
            return super().on_touch_move(touch)
        if touch.grab_current is not self:
            if "button" in getattr(touch, "profile", ()) and "left" in self.mouse_buttons:
                self._mouse_moved(Window, touch.pos)
                return True
            return super().on_touch_move(touch)
        if touch.uid == self.move_touch:
            self._set_move(*touch.pos)
        elif touch.uid == self.fire_touch:
            tx, ty = touch.x - self.x, touch.y - self.y
            self.world.set_aim(*self._sensitive_aim(tx, ty, self.touch_sensitivity))
        return True

    def on_touch_up(self, touch):
        if "button" in getattr(touch, "profile", ()) and getattr(touch, "button", None) == "left":
            self.mouse_buttons.discard("left")
            self.world.set_firing(False)
            return True
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        self._active_touches.pop(touch.uid, None)
        if touch.uid in self.ui_touches:
            self.ui_touches.discard(touch.uid)
            return True
        if touch.uid == self.move_touch:
            self.move_touch = None
            self.move_vector = (0.0, 0.0)
        if touch.uid == self.fire_touch:
            self.fire_touch = None
            self.world.set_firing(False)
            self.world.clear_aim()
        return True

    def on_touch_cancel(self, touch, *args):
        self.ui_touches.discard(touch.uid)
        if touch.uid == self.move_touch:
            self.move_touch = None
            self.move_vector = (0.0, 0.0)
        if touch.uid == self.fire_touch:
            self.fire_touch = None
            self.world.set_firing(False)
            self.world.clear_aim()
        if touch.grab_current is self:
            touch.ungrab(self)
            self._active_touches.pop(touch.uid, None)
            return True
        return super().on_touch_cancel(touch, *args)

    @staticmethod
    def _near(point_x, point_y, center, radius):
        return hypot(point_x - center[0], point_y - center[1]) <= radius

    @staticmethod
    def _inside_rect(x, y, rect):
        rx, ry, width, height = rect
        return rx <= x <= rx + width and ry <= y <= ry + height

    def _mouse_touch_target(self, x, y):
        if not self.collide_point(x, y):
            return False
        if self._inside_rect(x, y, self.pause_button_rect):
            return True
        if self.world.game_over and self._in_restart_button(x, y):
            return True
        return any(self._inside_rect(x, y, rect) for rect in self.weapon_button_rects) \
            or self._inside_rect(x, y, self.reload_button_rect)

    def _grab_touch(self, touch):
        touch.grab(self)
        self._active_touches[touch.uid] = touch

    def _set_move(self, x, y):
        cx, cy = self.joystick_center
        dx, dy = x - cx, y - cy
        radius = self.joystick_radius
        distance = hypot(dx, dy)
        if distance > radius:
            dx, dy = dx * radius / distance, dy * radius / distance
        self.move_vector = (dx / radius, dy / radius)

    def _tick(self, dt):
        if self.paused or not self.input_enabled:
            return
        move = list(self.move_vector)
        for key, axis, amount in (("left", 0, -1), ("a", 0, -1), ("right", 0, 1), ("d", 0, 1),
                                  ("down", 1, -1), ("s", 1, -1), ("up", 1, 1), ("w", 1, 1)):
            if key in self.keys:
                move[axis] += amount
        was_over = self.world.game_over
        self.world.update(dt, tuple(move), aim=self.mouse_aim if "left" in self.mouse_buttons else None)
        if self.audio_manager:
            self.audio_manager.consume(self.world.audio_events)
            self.world.audio_events.clear()
        if not was_over and self.world.game_over and self.game_over_callback:
            self.game_over_callback()
        self._redraw(dt)

    def reset_game(self):
        upgrades = self.world.upgrades
        self.world.reset()
        self.world.apply_upgrades(upgrades)
        self.move_vector = (0.0, 0.0)
        self.move_touch = self.fire_touch = None
        self.ui_touches.clear()
        self.keys.clear()
        self.mouse_buttons.clear()
        self.world.set_firing(False)
        self.world.clear_aim()
        self.mouse_aim = None
        self.renderer.clear_effects()

    def clear_input_state(self):
        for touch in tuple(self._active_touches.values()):
            if touch.grab_current is self:
                touch.ungrab(self)
        self._active_touches.clear()
        self.keys.clear()
        self.mouse_buttons.clear()
        self.move_vector = (0.0, 0.0)
        self.move_touch = self.fire_touch = None
        self.ui_touches.clear()
        self.world.set_firing(False)
        self.world.clear_aim()
        self.mouse_aim = None

    def _redraw(self, dt=0):
        self.renderer.draw(dt)

    @staticmethod
    def _circle(x, y, radius, outline=False):
        if outline:
            Line(circle=(x, y, radius), width=1.5)
        else:
            Ellipse(pos=(x - radius, y - radius), size=(radius * 2, radius * 2))

    def _in_restart_button(self, x, y):
        panel_w, panel_h = min(420, self.width * .82), min(250, self.height * .72)
        panel_x = self.x + (self.width - panel_w) / 2
        panel_y = self.y + (self.height - panel_h) / 2
        bx, by = panel_x + panel_w * .2, panel_y + 36
        bw, bh = panel_w * .6, 54
        return bx <= x <= bx + bw and by <= y <= by + bh
