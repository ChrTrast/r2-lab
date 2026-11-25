"""Ήχοι φτιαγμένοι με κώδικα (δεν χρειάζονται αρχεία WAV)."""
import array
import math
import random

import pygame

TWO_PI = 2 * math.pi


class SoundBank:
    def __init__(self):
        self.enabled = True
        self.sounds = {}
        try:
            init = pygame.mixer.get_init()
        except pygame.error:
            init = None
        if not init:
            return
        self.rate, fmt, self.channels = init
        if abs(fmt) == 16:
            self.code, self.scale = "h", 32000
        elif abs(fmt) == 32:
            self.code, self.scale = "f", 1.0
        else:
            return
        self._rng = random.Random(4)
        try:
            self._build()
        except (pygame.error, ValueError, MemoryError):
            self.sounds = {}

    # ---------------------------------------------------------------- play
    def play(self, name, volume=1.0):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.set_volume(volume)
            sound.play()

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled and pygame.mixer.get_init():
            pygame.mixer.stop()

    # ---------------------------------------------------------- synthesis
    def _tone(self, dur, freq, vol, wave="sine", attack=0.004, release=0.03,
              decay=0.0, freq_end=None, vib=0.0, vib_depth=0.0):
        rate = self.rate
        n = int(rate * dur)
        out = [0.0] * n
        phase = 0.0
        for i in range(n):
            t = i / rate
            f = freq if freq_end is None else freq + (freq_end - freq) * i / n
            if vib:
                f *= 1 + vib_depth * math.sin(TWO_PI * vib * t)
            phase += TWO_PI * f / rate
            s = math.sin(phase)
            if wave == "square":
                s = math.tanh(3 * s)
            elif wave == "tri":
                s = 2 / math.pi * math.asin(s)
            env = min(1.0, t / attack) if attack > 0 else 1.0
            if decay:
                env *= math.exp(-decay * t)
            tail = (dur - t) / release if release > 0 else 1.0
            if tail < 1.0:
                env *= max(0.0, tail)
            out[i] = s * env * vol
        return out

    def _noise(self, dur, vol, cutoff=0.3, attack=0.003, release=0.05, decay=0.0, highpass=False):
        rate = self.rate
        n = int(rate * dur)
        out = [0.0] * n
        low = 0.0
        rnd = self._rng.uniform
        for i in range(n):
            t = i / rate
            x = rnd(-1.0, 1.0)
            low += cutoff * (x - low)
            s = x - low if highpass else low
            env = min(1.0, t / attack) if attack > 0 else 1.0
            if decay:
                env *= math.exp(-decay * t)
            tail = (dur - t) / release if release > 0 else 1.0
            if tail < 1.0:
                env *= max(0.0, tail)
            out[i] = s * env * vol
        return out

    def _mix(self, *parts):
        """parts: (πότε ξεκινά σε δευτερόλεπτα, δείγματα)"""
        length = max(int(at * self.rate) + len(s) for at, s in parts)
        out = [0.0] * length
        for at, samples in parts:
            start = int(at * self.rate)
            for i, v in enumerate(samples):
                out[start + i] += v
        return out

    def _make(self, samples):
        clip = [max(-1.0, min(1.0, v)) for v in samples]
        if self.channels == 2:
            clip = [v for v in clip for _ in (0, 1)]
        if self.code == "h":
            data = array.array("h", (int(v * self.scale) for v in clip))
        else:
            data = array.array("f", clip)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _bell(self, dur, freq, vol, decay=6.0):
        return self._mix((0, self._tone(dur, freq, vol, decay=decay)),
                         (0, self._tone(dur, freq * 2, vol * 0.3, decay=decay * 1.6)))

    def _build(self):
        S = self.sounds
        S["button"] = self._make(self._tone(0.07, 900, 0.3, decay=35, freq_end=700))
        S["select"] = self._make(self._mix(
            (0, self._tone(0.2, 880, 0.32, decay=16)),
            (0, self._tone(0.12, 1320, 0.1, decay=30))))
        S["place"] = self._make(self._mix(
            (0, self._tone(0.22, 523, 0.38, decay=13)),
            (0, self._tone(0.15, 1046, 0.12, decay=22)),
            (0, self._noise(0.05, 0.3, cutoff=0.08, decay=60))))
        S["remove"] = self._make(self._tone(0.16, 640, 0.3, freq_end=320, decay=8))
        S["deny"] = self._make(self._mix(
            (0, self._tone(0.1, 185, 0.22, wave="square")),
            (0.14, self._tone(0.12, 165, 0.22, wave="square"))))
        S["complete"] = self._make(self._mix(
            *[(i * 0.09, self._bell(0.45, f, 0.22, decay=7))
              for i, f in enumerate((523, 659, 784, 1047))]))
        S["thud"] = self._make(self._mix(
            (0, self._tone(0.14, 150, 0.45, freq_end=80, decay=28)),
            (0, self._noise(0.07, 0.35, cutoff=0.12, decay=50))))
        S["pick"] = self._make(self._tone(0.13, 520, 0.28, freq_end=900, decay=12))
        S["swoosh"] = self._make(self._noise(0.4, 0.3, cutoff=0.6, attack=0.12, release=0.2, highpass=True))
        notes = [(i * 0.1, self._bell(0.5, f, 0.2, decay=5)) for i, f in enumerate((523, 659, 784, 1047, 1319))]
        sparkle = [(0.55 + i * 0.07, self._tone(0.08, f, 0.06, decay=30))
                   for i, f in enumerate((2093, 2637, 3136, 2637, 3136))]
        S["win"] = self._make(self._mix(*notes, (0.5, self._bell(0.9, 1047, 0.18, decay=2.5)), *sparkle))
        # νότες που ανεβαίνουν με κάθε σωστή τελεία στο «Ένωσε» (πεντατονική κλίμακα)
        for i, f in enumerate((523, 587, 659, 784, 880, 1047, 1175, 1319)):
            S[f"note{i}"] = self._make(self._bell(0.35, f, 0.26, decay=9))
        # Λαβύρινθος: το μοτέρ του R2, η στροφή, το χτύπημα στον τοίχο, η φόρτιση
        S["motor"] = self._make(self._mix(
            (0, self._tone(0.34, 110, 0.13, wave="square", attack=0.03, release=0.08, freq_end=135,
                           vib=28, vib_depth=0.05)),
            (0, self._tone(0.34, 220, 0.06, attack=0.03, release=0.08, freq_end=270))))
        S["turn"] = self._make(self._mix(
            (0, self._tone(0.26, 330, 0.1, wave="square", attack=0.02, release=0.06, freq_end=440,
                           vib=40, vib_depth=0.04)),
            (0, self._noise(0.26, 0.05, cutoff=0.5, attack=0.02, release=0.08, highpass=True))))
        S["bump"] = self._make(self._mix(
            (0, self._tone(0.12, 160, 0.4, freq_end=90, decay=25)),
            (0, self._noise(0.06, 0.3, cutoff=0.12, decay=50)),
            (0.05, self._tone(0.3, 520, 0.16, wave="tri", freq_end=300, decay=9, vib=18, vib_depth=0.06))))
        # τρέξιμο (Αριθμοί, Λέξεις, Πράξεις): άλμα και τραμπολίνο
        S["hop"] = self._make(self._tone(0.1, 380, 0.2, wave="tri", freq_end=620, decay=14))
        S["boing"] = self._make(self._tone(0.42, 180, 0.3, wave="tri", freq_end=720, decay=5,
                                           vib=16, vib_depth=0.08))
        S["charge"] = self._make(self._mix(
            (0, self._tone(0.55, 300, 0.14, wave="tri", attack=0.02, release=0.1, freq_end=1200)),
            (0.5, self._bell(0.6, 1319, 0.18, decay=6))))
        # Ποδόσφαιρο: σφυρίχτρα, κλωτσιά, γκολ, αντίστροφη μέτρηση
        S["whistle"] = self._make(self._mix(
            (0, self._tone(0.42, 2750, 0.16, attack=0.01, release=0.06, vib=34, vib_depth=0.035)),
            (0, self._noise(0.42, 0.05, cutoff=0.6, attack=0.01, release=0.06, highpass=True))))
        S["whistle_end"] = self._make(self._mix(
            *[(at, self._tone(dur, 2750, 0.16, attack=0.01, release=0.05, vib=34, vib_depth=0.035))
              for at, dur in ((0, 0.22), (0.3, 0.22), (0.6, 0.75))]))
        S["kick"] = self._make(self._mix(
            (0, self._tone(0.08, 240, 0.45, freq_end=110, decay=40)),
            (0, self._noise(0.04, 0.3, cutoff=0.25, decay=70))))
        S["shoot"] = self._make(self._mix(            # η πλάκα της κλωτσιάς βγαίνει: «τσακ»
            (0, self._noise(0.05, 0.3, cutoff=0.7, decay=70, highpass=True)),
            (0, self._tone(0.06, 1300, 0.16, wave="square", freq_end=480, decay=55))))
        S["goal"] = self._make(self._mix(
            (0, self._noise(1.5, 0.32, cutoff=0.12, attack=0.12, release=0.6)),
            *[(0.05 + i * 0.11, self._bell(0.5, f, 0.2, decay=5)) for i, f in enumerate((523, 659, 784, 1047))]))
        S["beep"] = self._make(self._tone(0.13, 660, 0.22, wave="tri", decay=10))
        # Ακολούθησε: το R2 μαζεύει γρανάζι, η μπάρα του φορτιστή ανοίγει
        S["gear"] = self._make(self._mix(
            (0, self._noise(0.03, 0.2, cutoff=0.7, decay=90, highpass=True)),
            (0, self._bell(0.25, 1568, 0.18, decay=11)),
            (0.07, self._bell(0.4, 2093, 0.16, decay=8))))
        # Συναρμολόγηση: το κομμάτι κολλάει σαν μαγνήτης («κλικ»), η βίδα μπαίνει μόνη της
        S["snap"] = self._make(self._mix(
            (0, self._noise(0.025, 0.42, cutoff=0.8, decay=110, highpass=True)),
            (0, self._tone(0.07, 1900, 0.2, wave="square", freq_end=1200, decay=60)),
            (0.03, self._tone(0.12, 620, 0.22, decay=30))))
        S["screw"] = self._make(self._mix(
            (0, self._tone(0.26, 210, 0.1, wave="square", attack=0.01, release=0.05, freq_end=330,
                           vib=55, vib_depth=0.12)),
            (0, self._noise(0.26, 0.06, cutoff=0.5, attack=0.01, release=0.05, highpass=True)),
            (0.24, self._tone(0.05, 1400, 0.12, decay=60))))
        S["barrier"] = self._make(self._mix(
            (0, self._tone(0.5, 170, 0.1, wave="square", attack=0.03, release=0.08, freq_end=250,
                           vib=30, vib_depth=0.05)),
            (0.48, self._tone(0.06, 900, 0.16, decay=40)),
            (0.48, self._noise(0.04, 0.2, cutoff=0.2, decay=70))))
