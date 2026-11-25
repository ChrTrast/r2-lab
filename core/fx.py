"""Η γιορτή όταν το παιδί τα καταφέρνει: χαρτοπόλεμος και πινακίδα «Μπράβο!»."""
import math
import random

import pygame

from . import ui


class Confetti:
    COLORS = [(240, 70, 70), (250, 200, 50), (70, 180, 90), (70, 130, 230), (190, 100, 220), (255, 140, 40)]

    def __init__(self):
        self.parts = []

    def clear(self):
        self.parts = []

    def burst(self, width, n=170):
        for _ in range(n):
            self.parts.append({"x": random.uniform(0, width), "y": random.uniform(-260, -10),
                               "vx": random.uniform(-60, 60), "vy": random.uniform(40, 160),
                               "rot": random.uniform(0, 6.3), "spin": random.uniform(-8, 8),
                               "size": random.uniform(5, 9), "phase": random.uniform(0, 6.3),
                               "color": random.choice(self.COLORS)})

    def update(self, dt, time, bottom):
        for c in self.parts:
            c["vy"] += 260 * dt
            c["vx"] *= 0.99
            c["x"] += c["vx"] * dt + math.sin(time * 3 + c["phase"]) * 30 * dt
            c["y"] += c["vy"] * dt
            c["rot"] += c["spin"] * dt
        self.parts = [c for c in self.parts if c["y"] < bottom + 30]

    def draw(self, surf):
        for c in self.parts:
            s = c["size"]
            ca, sa = math.cos(c["rot"]), math.sin(c["rot"])
            pts = [(c["x"] + dx * ca - dy * sa, c["y"] + dx * sa + dy * ca)
                   for dx, dy in ((-s, -s * 0.5), (s, -s * 0.5), (s, s * 0.5), (-s, s * 0.5))]
            ui.fill_poly(surf, c["color"], pts)


class Banner:
    """Πινακίδα που «σκάει» στη μέση και σβήνει μετά από λίγα δευτερόλεπτα."""

    def __init__(self, title, subtitle, stay=3.8, icon=None):
        """icon: προαιρετική ζωγραφιά στη θέση των τριών αστεριών, icon(εικόνα, κέντρο)."""
        self.stay = stay
        self.start = None
        self.img = pygame.Surface((500, 180), pygame.SRCALPHA)
        ui.panel(self.img, (6, 6, 488, 162), (255, 252, 240), radius=28, border=(250, 190, 50), shadow=False)
        if icon:
            icon(self.img, (250, 40))
        else:
            for i, dx in enumerate((-70, 0, 70)):
                ui.star(self.img, (250 + dx, 44 - (8 if i == 1 else 0)), 24 if i == 1 else 19, (252, 204, 60))
        ui.text(self.img, title, (250, 102), 56, (236, 118, 30), shadow=(250, 214, 150))
        ui.text(self.img, subtitle, (250, 146), 24, (70, 80, 110))

    def show(self, time):
        self.start = time

    def hide(self):
        self.start = None

    def visible(self, time):
        return self.start is not None and time - self.start <= self.stay + 0.7

    def contains(self, pos, time, center):
        """Αν η πινακίδα φαίνεται και το pos είναι πάνω της (κλικ στο «Μπράβο»)."""
        if not self.visible(time):
            return False
        return self.img.get_rect(center=center).collidepoint(pos)

    def draw(self, surf, time, center):
        if not self.visible(time):
            return
        age = time - self.start
        alpha = 255 if age < self.stay else int(255 * (self.stay + 0.7 - age) / 0.7)
        pop = min(1.0, age / 0.25)
        scale = 0.6 + 0.4 * (1 - (1 - pop) ** 3)
        img = self.img
        if scale != 1.0:
            img = pygame.transform.smoothscale(img, (int(500 * scale), int(180 * scale)))
        else:
            img = img.copy()
        img.set_alpha(alpha)
        surf.blit(img, img.get_rect(center=center))
