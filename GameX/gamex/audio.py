"""Offline procedural audio and local Kivy playback."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from kivy.core.audio import SoundLoader


SAMPLE_RATE = 22050


def _write_wave(path: Path, samples) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))


def _tone(duration, start_hz, end_hz=None, volume=.35, harmonics=1):
    count = int(SAMPLE_RATE * duration)
    end_hz = start_hz if end_hz is None else end_hz
    result = []
    phase = 0.0
    for i in range(count):
        t = i / SAMPLE_RATE
        progress = i / max(1, count - 1)
        frequency = start_hz + (end_hz - start_hz) * progress
        phase += 2 * math.pi * frequency / SAMPLE_RATE
        envelope = min(1, t * 60) * max(0, 1 - progress) ** .7
        sample = sum(math.sin(phase * harmonic) / harmonic for harmonic in range(1, harmonics + 1))
        result.append(volume * envelope * sample * .75)
    return result


def generate_audio_assets(directory: str | Path) -> dict[str, Path]:
    """Generate original synth cues and a short looping music bed as WAV files."""
    directory = Path(directory)
    paths = {name: directory / f"{name}.wav" for name in
             ("music", "shoot", "reload", "hit", "death", "boss")}
    if all(path.exists() for path in paths.values()):
        return paths
    duration = 8.0
    music = [0.0] * int(SAMPLE_RATE * duration)
    notes = (110, 164.81, 220, 164.81, 130.81, 196, 261.63, 196)
    beat = .5
    for index in range(int(duration / beat)):
        tone = _tone(beat * .88, notes[index % len(notes)], volume=.095, harmonics=2)
        offset = int(index * beat * SAMPLE_RATE)
        for sample_index, sample in enumerate(tone):
            music[offset + sample_index] += sample
    _write_wave(paths["music"], music)
    _write_wave(paths["shoot"], _tone(.075, 520, 180, .32, 3))
    _write_wave(paths["reload"], _tone(.18, 260, 110, .23, 2) + _tone(.12, 390, 170, .18, 2))
    _write_wave(paths["hit"], _tone(.09, 180, 70, .26, 3))
    _write_wave(paths["death"], _tone(.28, 115, 38, .34, 4))
    _write_wave(paths["boss"], _tone(.35, 190, 90, .3, 2) + _tone(.3, 140, 65, .28, 2))
    return paths


class AudioManager:
    """Playback manager using only generated local WAVs and Kivy's audio API."""

    def __init__(self, directory: str | Path, settings: dict | None = None, enabled=True):
        self.directory = Path(directory)
        self.settings = settings or {}
        self.enabled = enabled
        self.sounds = {}
        self.music = None
        if enabled:
            try:
                paths = generate_audio_assets(self.directory)
                self.sounds = {key: SoundLoader.load(str(path)) for key, path in paths.items()}
                self.music = self.sounds.pop("music", None)
                if self.music:
                    self.music.loop = True
                    self._volume(self.music, "music")
            except (OSError, RuntimeError, ValueError):
                self.enabled = False

    def _volume(self, sound, channel):
        if sound:
            master = float(self.settings.get("master_volume", .8))
            level = float(self.settings.get(f"{channel}_volume", .8))
            sound.volume = max(0, min(1, master * level))

    def set_settings(self, settings):
        self.settings = settings
        self._volume(self.music, "music")

    def play_music(self):
        if self.enabled and self.music and self.music.state != "play":
            self._volume(self.music, "music")
            self.music.play()

    def pause_music(self):
        if self.music and self.music.state == "play":
            self.music.stop()

    def play(self, event: str):
        if not self.enabled:
            return
        sound = self.sounds.get(event)
        if sound:
            self._volume(sound, "effects")
            sound.stop()
            sound.play()

    def consume(self, events):
        for event in events:
            self.play(event)

