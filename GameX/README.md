# GameX

GameX is an offline 2D top-down zombie shooter made with Python and Kivy. It uses local procedural graphics and audio and makes no network requests.

## Windows setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Controls

- Move: **WASD** or arrow keys.
- Aim: move the mouse; on touch, hold on the right half of the battlefield.
- Fire: hold left mouse button or the large right-side touch control.
- Select Pistol / Assault Rifle / Shotgun: **1 / 2 / 3** or the on-screen buttons.
- Reload: **R** or the on-screen reload button. Empty weapons reload automatically.
- Pause: **P**, **Escape**, or the pause icon. Resume, confirm a restart, or return to the menu.

On Android, drag the lower-left joystick to move. Weapon and reload buttons sit near the bottom center. The controls and menus use responsive Kivy layouts and require no permissions.

Play, menus, and gameplay transition inside the same Kivy window. Mouse aim follows the pointer; hold and release the left mouse button to start and stop firing.

## Gameplay systems

The Pistol has unlimited reserve ammo; the Assault Rifle and Shotgun have limited reserves. Each has a different magazine, damage, firing rate, pellet spread, and reload duration. Normal, fast, and heavy zombies have different speed, health, and contact damage. Every fifth wave includes a boss. Waves grow in size and difficulty; defeated enemies grant score and coins.

The main menu includes a first-run skippable tutorial, settings, and weapon shop. The shop offers three levels each of damage, reload-speed, and magazine upgrades. Purchases require saved coins. Settings persist master/music/effects volume, mouse/touch aiming sensitivity, graphics quality (Low, Medium, High), and the screen-shake toggle.

The battlefield uses cached procedural terrain, roads, cracks, cover props and layered military-style floor details. Animated character drawings distinguish the four enemy types and soldier. Combat uses a bounded reusable particle pool for impacts, dust, muzzle flashes, deaths, and boss/explosion feedback. Low quality reduces terrain detail and particles; High adds lighting and more effects. Decorative environment props do not change movement or collision rules.

The pause menu stops the simulation. Restart asks for confirmation and banks the current run first. High score, total coins, best wave, games played, kills, settings, tutorial completion, and upgrades are stored in `gamex_save.json` in Kivy's writable application data directory. Android uses the app-specific writable directory. Saves are atomic; malformed JSON is copied to a `.corrupt` file before defaults are used.

Music and effects are original tones synthesized into WAV files on first launch and stored in the same writable local data area. Kivy plays these local files; no copyrighted or third-party audio is bundled.

## Tests

```powershell
python -m compileall -q main.py gamex tests
python -m unittest discover -s tests -v
```

## Android packaging

Buildozer packaging is generally run from Linux or WSL:

```sh
buildozer android debug
```

The Android settings are in `buildozer.spec`. Set `package.domain` to a domain you control before publishing. Android packaging and device touch/audio behavior still need on-device verification.
