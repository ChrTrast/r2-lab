"""Οι εικόνες του «Ένωσε», ζωγραφισμένες με κώδικα.

Κάθε εικόνα έχει:
  groups:  τις τελείες, σε ομάδες (σημεία, κλείσιμο) — δες logic.DotGame
  sketch:  όσα φαίνονται από την αρχή (μάτια, πόρτα…), με απλές γραμμές
  final:   την έγχρωμη εικόνα του τέλους, που κινείται (t = δευτερόλεπτα από την ολοκλήρωση)
Όλα σχεδιάζονται σε «καμβά» 960x576 (x δεξιά, y κάτω).
"""
import math
import random

import pygame

from core import ui

CANVAS = (960, 576)
OUTLINE = (52, 52, 72)
LIGHT_LINE = (200, 214, 255)
TWO_PI = 2 * math.pi


# --------------------------------------------------------------- helpers
def make_tf(ox=0.0, oy=0.0, dx=0.0, dy=0.0, angle=0.0, sx=1.0, sy=1.0, center=(480, 288)):
    """Μετατροπή σημείων: κλίμακα και περιστροφή γύρω από το center, μετά μετακίνηση."""
    ca, sa = math.cos(angle), math.sin(angle)
    cx, cy = center

    def tf(p):
        x, y = (p[0] - cx) * sx, (p[1] - cy) * sy
        return (ox + cx + dx + x * ca - y * sa, oy + cy + dy + x * sa + y * ca)
    return tf


def chain(outer, inner):
    return lambda p: outer(inner(p))


def lines(surf, color, pts, width=4, closed=False):
    if len(pts) < 2:
        return
    pygame.draw.lines(surf, color, closed, pts, width)
    if width > 2:
        for p in pts:
            pygame.draw.circle(surf, color, p, width / 2)


def shape(surf, tf, pts, fill=None, line=OUTLINE, width=4, closed=True):
    sp = [tf(p) for p in pts]
    if fill is not None:
        ui.fill_poly(surf, fill, sp)
    if line is not None:
        lines(surf, line, sp, width, closed)


def oval_pts(cx, cy, rx, ry, n=28):
    return [(cx + rx * math.cos(TWO_PI * i / n), cy + ry * math.sin(TWO_PI * i / n)) for i in range(n)]


def arc_pts(cx, cy, rx, ry, a0, a1, n=12):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


def oval(surf, tf, cx, cy, rx, ry, fill=None, line=OUTLINE, width=3):
    shape(surf, tf, oval_pts(cx, cy, rx, ry), fill, line, width)


def twinkle(surf, x, y, size, color):
    """Μικρό αστεράκι με 4 ακτίνες."""
    s, k = size, size * 0.3
    ui.fill_poly(surf, color, [(x, y - s), (x + k, y - k), (x + s, y), (x + k, y + k),
                               (x, y + s), (x - k, y + k), (x - s, y), (x - k, y - k)])


def gradient(top, bottom, rect=None, surf=None):
    surf = surf or pygame.Surface(CANVAS)
    rect = pygame.Rect(rect or (0, 0, *CANVAS))
    for y in range(rect.height):
        pygame.draw.line(surf, ui.mix(top, bottom, y / max(1, rect.height - 1)),
                         (rect.x, rect.y + y), (rect.right, rect.y + y))
    return surf


def night_sky(seed, top=(14, 20, 58), bottom=(48, 40, 104), count=140):
    surf = gradient(top, bottom)
    rng = random.Random(seed)
    for _ in range(count):
        x, y = rng.uniform(0, 960), rng.uniform(0, 576)
        c = rng.choice(((255, 255, 255), (220, 230, 255), (255, 240, 200)))
        pygame.draw.circle(surf, ui.mix(c, top, rng.uniform(0.2, 0.7)), (x, y), rng.choice((1, 1, 1.5, 2)))
    return surf


def cloud(surf, x, y, s=1.0, color=(255, 255, 255)):
    for dx, dy, r in ((-34, 6, 24), (0, -8, 32), (36, 6, 24), (14, 14, 22)):
        pygame.draw.circle(surf, color, (x + dx * s, y + dy * s), r * s)


def sun(surf, x, y, t, r=38):
    for i in range(12):
        a = t * 0.6 + i * math.pi / 6
        pygame.draw.line(surf, (255, 200, 50), (x + math.cos(a) * r * 1.25, y + math.sin(a) * r * 1.25),
                         (x + math.cos(a) * r * 1.7, y + math.sin(a) * r * 1.7), 6)
    ui.circle(surf, (255, 214, 60), (x, y), r, (230, 160, 40))


# ------------------------------------------------------------- pictures
class Picture:
    name = ""
    title = ""
    dark = False            # σκούρο χαρτί (νυχτερινός ουρανός)
    home = None             # η γωνία του R2 και του φορτιστή: "left", "right" ή None (διαλέγει μόνη της)
    groups = []
    group_names = None

    def sketch(self, surf, tf, color):
        pass

    def backdrop(self):
        return gradient((150, 205, 245), (218, 238, 252))

    def final(self, surf, t):
        pass


class Star(Picture):
    name, title = "Αστέρι", "Ένα χαρούμενο αστέρι!"

    def __init__(self):
        self.points = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            r = 235 if k % 2 == 0 else 98
            self.points.append((480 + r * math.cos(a), 300 + r * math.sin(a)))
        self.groups = [(self.points, 0)]
        rng = random.Random(3)
        self.sparks = [(rng.uniform(40, 920), rng.uniform(30, 540)) for _ in range(14)]

    def face(self, surf, tf, color, cheeks=False):
        if cheeks:
            for x in (418, 542):
                oval(surf, tf, x, 322, 15, 11, fill=(255, 150, 150), line=None)
        for x in (445, 515):
            oval(surf, tf, x, 286, 9, 13, fill=color, line=None)
        lines(surf, color, [tf(p) for p in arc_pts(480, 316, 36, 24, 0.15 * math.pi, 0.85 * math.pi)], 5)

    def sketch(self, surf, tf, color):
        self.face(surf, tf, color)

    def backdrop(self):
        return night_sky(11)

    def final(self, surf, t):
        for i, (x, y) in enumerate(self.sparks):
            twinkle(surf, x, y, 5 + 4 * abs(math.sin(2 * t + i)), (255, 246, 190))
        pulse = 1 + 0.04 * math.sin(3 * t)
        tf = make_tf(angle=0.12 * math.sin(1.5 * t), sx=pulse, sy=pulse, center=(480, 300))
        glow = make_tf(angle=0.12 * math.sin(1.5 * t), sx=pulse * 1.12, sy=pulse * 1.12, center=(480, 300))
        shape(surf, glow, self.points, fill=(255, 236, 140, 70), line=None)
        shape(surf, tf, self.points, fill=(255, 214, 60), line=(226, 140, 30), width=6)
        self.face(surf, tf, OUTLINE, cheeks=True)


class House(Picture):
    name, title = "Σπιτάκι", "Ένα σπιτάκι!"
    PTS = [(320, 480), (320, 270), (270, 270), (480, 110), (570, 179), (570, 120), (610, 120), (610, 209),
           (690, 270), (640, 270), (640, 480)]

    def __init__(self):
        self.groups = [(self.PTS, 0)]

    def sketch(self, surf, tf, color):
        shape(surf, tf, [(445, 480), (445, 395), (515, 395), (515, 480)], line=color, width=3, closed=False)
        oval(surf, tf, 503, 440, 4, 4, fill=color, line=None)
        for x0 in (355, 535):
            shape(surf, tf, [(x0, 320), (x0 + 70, 320), (x0 + 70, 375), (x0, 375)], line=color, width=3)
            shape(surf, tf, [(x0 + 35, 320), (x0 + 35, 375)], line=color, width=3, closed=False)
            shape(surf, tf, [(x0, 347), (x0 + 70, 347)], line=color, width=3, closed=False)
        shape(surf, tf, [(200, 480), (760, 480)], line=color, width=3, closed=False)

    def backdrop(self):
        surf = gradient((150, 205, 245), (218, 238, 252))
        pygame.draw.rect(surf, (120, 190, 90), (0, 480, 960, 96))
        cloud(surf, 300, 90, 1.0)
        cloud(surf, 800, 140, 0.8)
        return surf

    def final(self, surf, t):
        sun(surf, 120, 105, t)
        for k in range(3):
            phase = (t * 0.45 + k / 3) % 1
            x, y = 590 + 18 * math.sin(phase * 6 + k), 110 - phase * 110
            ui.circle(surf, (235, 235, 240, int(220 * (1 - phase))), (x, y), 12 + 22 * phase)
        tf = make_tf()
        shape(surf, tf, [(570, 179), (570, 120), (610, 120), (610, 209)], fill=(176, 92, 70))
        shape(surf, tf, [(320, 480), (320, 270), (640, 270), (640, 480)], fill=(250, 232, 190))
        shape(surf, tf, [(270, 270), (480, 110), (570, 179), (610, 209), (690, 270)], fill=(214, 70, 60))
        shape(surf, tf, [(445, 480), (445, 395), (515, 395), (515, 480)], fill=(150, 92, 56))
        oval(surf, tf, 503, 440, 5, 5, fill=(250, 210, 80), line=None)
        for x0 in (355, 535):
            shape(surf, tf, [(x0, 320), (x0 + 70, 320), (x0 + 70, 375), (x0, 375)], fill=(190, 226, 250))
            shape(surf, tf, [(x0 + 35, 320), (x0 + 35, 375)], line=(255, 255, 255), width=4, closed=False)
            shape(surf, tf, [(x0, 347), (x0 + 70, 347)], line=(255, 255, 255), width=4, closed=False)
        shape(surf, tf, self.PTS, line=OUTLINE, width=5)
        for i, x in enumerate(range(240, 740, 46)):
            if 300 < x < 660:
                continue
            sway = 3 * math.sin(2 * t + i)
            pygame.draw.line(surf, (60, 150, 70), (x, 500), (x + sway, 474), 3)
            ui.circle(surf, ((240, 90, 120), (250, 200, 60), (160, 110, 220))[i % 3], (x + sway, 472), 8)


class Boat(Picture):
    name, title = "Καραβάκι", "Ένα καραβάκι στη θάλασσα!"
    HULL = [(240, 370), (720, 370), (690, 420), (650, 470), (330, 470), (280, 420)]
    SAIL1 = [(495, 350), (495, 110), (680, 350)]
    SAIL2 = [(465, 350), (465, 150), (300, 350)]

    def __init__(self):
        self.groups = [(self.HULL, 0), (self.SAIL1, 0), (self.SAIL2, 0)]

    @staticmethod
    def waves(y, phase=0.0):
        return [(x, y + 8 * math.sin(x / 30 + phase)) for x in range(100, 870, 10)]

    def sketch(self, surf, tf, color):
        shape(surf, tf, [(480, 370), (480, 92)], line=color, width=4, closed=False)
        shape(surf, tf, [(480, 92), (535, 105), (480, 118)], line=color, width=3)
        shape(surf, tf, self.waves(505), line=color, width=3, closed=False)
        shape(surf, tf, self.waves(540, 2), line=color, width=3, closed=False)

    def backdrop(self):
        surf = gradient((140, 200, 245), (214, 236, 252))
        gradient((70, 150, 215), (24, 84, 160), (0, 430, 960, 146), surf)
        cloud(surf, 200, 90, 0.9)
        cloud(surf, 760, 70, 1.1)
        return surf

    def final(self, surf, t):
        sun(surf, 860, 90, t, 32)
        gx = (t * 70) % 1100 - 80
        gy = 150 + 12 * math.sin(t * 2)
        flap = 10 * math.sin(t * 8)
        lines(surf, OUTLINE, [(gx - 22, gy - flap), (gx, gy), (gx + 22, gy - flap)], 3)
        tf = make_tf(dy=7 * math.sin(2 * t), angle=0.035 * math.sin(1.6 * t), center=(480, 430))
        shape(surf, tf, [(480, 372), (480, 92)], line=(120, 80, 50), width=6, closed=False)
        shape(surf, tf, [(480, 92), (535, 105 + 6 * math.sin(6 * t)), (480, 118)], fill=(230, 60, 60))
        shape(surf, tf, self.SAIL1, fill=(255, 252, 240))
        shape(surf, tf, self.SAIL2, fill=(255, 232, 140))
        shape(surf, tf, self.HULL, fill=(214, 60, 60), width=5)
        shape(surf, tf, [(262, 396), (703, 396)], line=(255, 255, 255), width=7, closed=False)
        for x in (390, 480, 570):
            oval(surf, tf, x, 434, 12, 12, fill=(220, 240, 255))
        sea = [(x, 452 + 7 * math.sin(x / 40 + 2.2 * t)) for x in range(0, 961, 20)]
        ui.fill_poly(surf, (44, 120, 200), sea + [(960, 576), (0, 576)])
        lines(surf, (190, 225, 250), sea, 4)
        for k, y in enumerate((490, 525, 555)):
            lines(surf, (120, 180, 235), [(x, y + 6 * math.sin(x / 35 + 2 * t + k)) for x in range(0, 961, 20)], 3)


class Rocket(Picture):
    name, title = "Πύραυλος", "Ένας πύραυλος για το διάστημα!"
    home = "right"          # αριστερά κάτω είναι το φεγγάρι
    PTS = [(480, 70), (530, 140), (540, 380), (610, 460), (545, 450), (530, 480), (430, 480), (415, 450),
           (350, 460), (420, 380), (430, 140)]

    def __init__(self):
        self.groups = [(self.PTS, 0)]
        rng = random.Random(7)
        self.stars = [(rng.uniform(0, 960), rng.uniform(0, 576), rng.uniform(0.5, 1.6)) for _ in range(70)]

    def sketch(self, surf, tf, color):
        oval(surf, tf, 480, 230, 34, 34, line=color)
        oval(surf, tf, 480, 230, 24, 24, line=color)
        shape(surf, tf, [(424, 300), (536, 300)], line=color, width=3, closed=False)
        shape(surf, tf, [(430, 140), (530, 140)], line=color, width=3, closed=False)

    def backdrop(self):
        surf = gradient((8, 12, 40), (34, 26, 76))
        ui.circle(surf, (230, 150, 90), (820, 120), 54, (190, 110, 70))
        pygame.draw.ellipse(surf, (250, 210, 160), (740, 104, 160, 32), 5)
        ui.circle(surf, (210, 210, 220), (130, 470), 40, (170, 170, 180))
        return surf

    def final(self, surf, t):
        for x, y, speed in self.stars:
            yy = (y + t * 160 * speed) % 576
            pygame.draw.line(surf, (230, 235, 255), (x, yy), (x, yy - 6 * speed), max(1, int(speed * 1.5)))
        tf = make_tf(dx=1.5 * math.sin(41 * t), dy=-12 * math.sin(1.8 * t), center=(480, 300))
        flame = 70 + 18 * math.sin(25 * t) + 8 * math.sin(13 * t)
        shape(surf, tf, [(438, 478), (522, 478), (480, 478 + flame)], fill=(255, 140, 40), line=None)
        shape(surf, tf, [(455, 478), (505, 478), (480, 478 + flame * 0.6)], fill=(255, 230, 90), line=None)
        shape(surf, tf, self.PTS, fill=(236, 236, 244), width=5)
        shape(surf, tf, [(480, 70), (530, 140), (430, 140)], fill=(220, 60, 60))
        shape(surf, tf, [(421, 372), (350, 460), (415, 450), (428, 476)], fill=(220, 60, 60))
        shape(surf, tf, [(539, 372), (610, 460), (545, 450), (532, 476)], fill=(220, 60, 60))
        shape(surf, tf, [(424, 300), (536, 300)], line=(220, 60, 60), width=8, closed=False)
        oval(surf, tf, 480, 230, 34, 34, fill=(90, 150, 220), width=4)
        oval(surf, tf, 470, 220, 9, 9, fill=(220, 240, 255), line=None)


class Cat(Picture):
    name, title = "Γατούλα", "Μια γατούλα!"
    PTS = [(480, 470), (360, 440), (300, 360), (300, 260), (330, 190), (310, 90), (410, 160), (480, 150),
           (550, 160), (650, 90), (630, 190), (660, 260), (660, 360), (600, 440)]

    def __init__(self):
        self.groups = [(self.PTS, 0)]

    def face(self, surf, tf, color, t=None):
        wiggle = 0 if t is None else 6 * math.sin(4 * t)
        for x in (410, 550):
            if t is None:
                oval(surf, tf, x, 280, 34, 22, line=color)
                oval(surf, tf, x, 280, 6, 17, fill=color, line=None)
            elif t % 3.5 < 0.18:
                oval(surf, tf, x, 280, 36, 24, fill=(246, 166, 80), line=None)
                shape(surf, tf, arc_pts(x, 278, 34, 10, 0, math.pi), line=color, width=4, closed=False)
            else:
                oval(surf, tf, x, 280, 34, 22, fill=(150, 220, 90), line=color)
                oval(surf, tf, x, 280, 7, 18, fill=color, line=None)
                oval(surf, tf, x - 10, 272, 5, 5, fill=(255, 255, 255), line=None)
        shape(surf, tf, [(465, 330), (495, 330), (480, 348)], fill=(255, 140, 160) if t is not None else None,
              line=color, width=3)
        shape(surf, tf, [(480, 348), (480, 360)], line=color, width=3, closed=False)
        shape(surf, tf, arc_pts(463, 360, 17, 14, 0, math.pi), line=color, width=3, closed=False)
        shape(surf, tf, arc_pts(497, 360, 17, 14, 0, math.pi), line=color, width=3, closed=False)
        for side in (-1, 1):
            for y0, y1 in ((345, 325), (358, 365)):
                shape(surf, tf, [(480 + side * 50, y0), (480 + side * 160, y1 + side * wiggle)],
                      line=color, width=3, closed=False)

    def sketch(self, surf, tf, color):
        self.face(surf, tf, color)

    def backdrop(self):
        surf = gradient((255, 238, 205), (250, 216, 172))
        for x in range(30, 960, 80):
            for y in range(30, 576, 80):
                pygame.draw.circle(surf, (255, 228, 190), (x + (y // 80 % 2) * 40, y), 10)
        return surf

    def final(self, surf, t):
        tf = make_tf(angle=0.05 * math.sin(1.3 * t), center=(480, 330))
        shape(surf, tf, self.PTS, fill=(246, 166, 80), width=5)
        shape(surf, tf, [(334, 186), (320, 112), (398, 160)], fill=(255, 170, 180), line=None)
        shape(surf, tf, [(626, 186), (640, 112), (562, 160)], fill=(255, 170, 180), line=None)
        for x0, x1 in ((460, 466), (480, 480), (500, 494)):
            shape(surf, tf, [(x0, 168), (x1, 204)], line=(214, 120, 50), width=6, closed=False)
        for x in (378, 582):
            oval(surf, tf, x, 352, 20, 13, fill=(255, 150, 140, 150), line=None)
        self.face(surf, tf, OUTLINE, t)


class Fish(Picture):
    name, title = "Ψαράκι", "Ένα ψαράκι!"

    @staticmethod
    def body(deg):
        a = math.radians(deg)
        return (440 + 230 * math.cos(a), 290 - 130 * math.sin(a))

    def __init__(self):
        upper = [self.body(d) for d in (160, 135, 110, 90, 70, 50, 30)]
        tail = [(760, 165), (700, 290), (760, 415)]
        lower = [self.body(d) for d in (-30, -50, -70, -90, -110, -135, -160)]
        self.PTS = upper + tail + lower + [(250, 292)]
        self.groups = [(self.PTS, 0)]

    def details(self, surf, tf, color, fill=False):
        oval(surf, tf, 300, 255, 20, 20, fill=(255, 255, 255) if fill else None, line=color)
        oval(surf, tf, 304, 257, 8, 8, fill=color, line=None)
        shape(surf, tf, arc_pts(300, 290, 70, 85, -0.4 * math.pi, 0.4 * math.pi), line=color, width=3, closed=False)

    def sketch(self, surf, tf, color):
        self.details(surf, tf, color)
        shape(surf, tf, [(390, 163), (450, 100), (540, 175)], line=color, width=3, closed=False)
        shape(surf, tf, [(430, 418), (470, 470), (520, 413)], line=color, width=3, closed=False)

    def backdrop(self):
        surf = gradient((110, 200, 235), (28, 96, 168))
        sand = [(x, 535 + 10 * math.sin(x / 70)) for x in range(0, 961, 20)]
        ui.fill_poly(surf, (232, 212, 150), sand + [(960, 576), (0, 576)])
        return surf

    def final(self, surf, t):
        for k, x0 in enumerate((90, 150, 810, 870)):
            pts = [(x0 + 16 * math.sin(t * 1.5 + j * 0.6 + k), 576 - j * 26) for j in range(9)]
            lines(surf, (60, 160, 90), pts, 10)
        for i in range(7):
            y = 576 - ((t * 60 + i * 97) % 640)
            x = 120 + i * 120 + 10 * math.sin(t + i)
            pygame.draw.circle(surf, (220, 240, 255), (x, y), 6 + i % 3, 2)
        tf = make_tf(dx=35 * math.sin(1.1 * t), dy=12 * math.sin(2.2 * t), angle=0.05 * math.sin(1.1 * t + 1),
                     center=(480, 290))
        shape(surf, tf, [(390, 168), (450, 100), (540, 178)], fill=(236, 112, 36))
        shape(surf, tf, [(430, 412), (470, 470), (520, 408)], fill=(236, 112, 36))
        shape(surf, tf, self.PTS, fill=(255, 160, 60), width=5)

        def edge(x):
            k = max(0.0, 1 - ((x - 440) / 230) ** 2) ** 0.5
            return 290 - 130 * k + 6, 290 + 130 * k - 6
        for x0 in (380, 520):
            (t0, b0), (t1, b1) = edge(x0), edge(x0 + 26)
            shape(surf, tf, [(x0, t0), (x0 + 26, t1), (x0 + 26, b1), (x0, b0)], fill=(255, 236, 210), line=None)
        self.details(surf, tf, OUTLINE, fill=True)
        for i in range(3):
            phase = (t * 0.8 + i / 3) % 1
            p = tf((236 - 30 * phase, 280 - 90 * phase))
            pygame.draw.circle(surf, (230, 245, 255), p, 4 + 6 * phase, 2)


class Butterfly(Picture):
    name, title = "Πεταλούδα", "Μια πεταλούδα!"
    LEFT = [(455, 265), (430, 180), (360, 120), (270, 110), (220, 170), (250, 240), (320, 285), (250, 330),
            (240, 410), (300, 450), (380, 420), (450, 330)]
    RIGHT = [(960 - x, y) for x, y in LEFT]
    SPOTS = [((330, 190), 32, (255, 220, 80)), ((300, 385), 26, (255, 220, 80)), ((405, 250), 14, (255, 255, 255))]

    def __init__(self):
        self.groups = [(self.LEFT, 0), (self.RIGHT, 0)]

    def body(self, surf, tf, color, fill=None):
        oval(surf, tf, 480, 300, 14, 105, fill=fill, line=color)
        oval(surf, tf, 480, 180, 22, 22, fill=fill, line=color)
        for side in (-1, 1):
            shape(surf, tf, [(480 + side * 8, 162), (480 + side * 25, 130), (480 + side * 40, 100)],
                  line=color, width=3, closed=False)
            oval(surf, tf, 480 + side * 40, 98, 6, 6, fill=color, line=None)

    def sketch(self, surf, tf, color):
        self.body(surf, tf, color)

    def backdrop(self):
        surf = gradient((160, 214, 248), (225, 242, 252))
        hills = [(x, 430 - 40 * math.sin(x / 160)) for x in range(0, 961, 20)]
        ui.fill_poly(surf, (126, 196, 96), hills + [(960, 576), (0, 576)])
        rng = random.Random(5)
        for _ in range(40):
            x, y = rng.uniform(0, 960), rng.uniform(470, 570)
            pygame.draw.circle(surf, rng.choice(((255, 255, 255), (255, 210, 80), (240, 120, 160))), (x, y), 5)
        return surf

    def final(self, surf, t):
        flap = 0.55 + 0.45 * abs(math.cos(5 * t))
        body_tf = make_tf(dy=14 * math.sin(1.6 * t), center=(480, 300))
        wing_tf = chain(body_tf, make_tf(sx=flap, center=(480, 300)))
        for wing, mirror in ((self.LEFT, False), (self.RIGHT, True)):
            shape(surf, wing_tf, wing, fill=(255, 140, 60), width=4)
            for (x, y), r, col in self.SPOTS:
                oval(surf, wing_tf, 960 - x if mirror else x, y, r, r, fill=col, line=None)
        self.body(surf, body_tf, OUTLINE, fill=(96, 64, 52))
        for side in (-1, 1):
            oval(surf, body_tf, 480 + side * 8, 176, 4, 4, fill=(255, 255, 255), line=None)


class Constellations(Picture):
    name, title, dark = "Αστερισμοί", "Αστερισμοί στον ουρανό!", True
    BIG = [(110, 170), (185, 150), (245, 165), (305, 195), (320, 265), (415, 275), (425, 195)]
    LITTLE = [(560, 80), (600, 115), (630, 150), (650, 195), (740, 215), (730, 265), (660, 250)]
    CASS = [(700, 390), (760, 345), (815, 390), (870, 335), (930, 365)]
    ORION = [(190, 330), (330, 320), (300, 420), (350, 520), (205, 515), (240, 435)]
    group_names = ["Μεγάλη Άρκτος", "Μικρή Άρκτος", "Κασσιόπη", "Ωρίων"]
    NAME_POS = [(270, 112), (660, 300), (815, 440), (440, 470)]

    def __init__(self):
        self.groups = [(self.BIG, 3), (self.LITTLE, 3), (self.CASS, None), (self.ORION, 0)]

    def sketch(self, surf, tf, color):
        x, y = tf((270, 428))
        twinkle(surf, x, y, 7, color)

    def backdrop(self):
        return night_sky(19, count=220)

    def final(self, surf, t):
        for g, (pts, close_to) in enumerate(self.groups):
            path = list(pts) + ([pts[close_to]] if close_to is not None else [])
            lines(surf, (90, 120, 200), path, 9)
            lines(surf, (170, 205, 255), path, 3)
        lines(surf, (170, 205, 255), [(240, 435), (270, 428), (300, 420)], 3)
        i = 0
        for pts, _ in self.groups:
            for x, y in pts:
                twinkle(surf, x, y, 9 + 3 * math.sin(3 * t + i), (255, 248, 200))
                i += 1
        twinkle(surf, 270, 428, 8, (255, 248, 200))
        for k, (name, pos) in enumerate(zip(self.group_names, self.NAME_POS)):
            alpha = max(0.0, min(1.0, (t - 0.5 * k) * 2))
            if alpha > 0:
                img = ui.font(24).render(name, True, (255, 236, 150))
                img.set_alpha(int(255 * alpha))
                surf.blit(img, img.get_rect(center=pos))
        p = (t % 4.0) / 1.2
        if p < 1:
            x, y = 80 + 760 * p, 40 + 140 * p
            pygame.draw.line(surf, (255, 255, 255), (x, y), (x - 90, y - 17), 3)
            ui.circle(surf, (255, 255, 230), (x, y), 4)


class Flower(Picture):
    name, title = "Λουλούδι", "Ένα λουλούδι στη γλάστρα!"
    POT = [(370, 400), (590, 400), (590, 432), (558, 432), (540, 520), (420, 520), (402, 432), (370, 432)]
    LEAF = [(477, 360), (422, 338), (372, 356), (426, 380)]

    def __init__(self):
        self.PETALS = []
        for k in range(20):
            a = -math.pi / 2 + k * TWO_PI / 20
            r = 70 + 55 * abs(math.cos(2.5 * (a + math.pi / 2)))
            self.PETALS.append((480 + r * math.cos(a), 200 + r * math.sin(a)))
        self.groups = [(self.POT, 0), (self.LEAF, 0), (self.PETALS, 0)]

    def sketch(self, surf, tf, color):
        shape(surf, tf, [(480, 400), (478, 340), (482, 300), (480, 270)], line=color, width=3, closed=False)
        oval(surf, tf, 480, 200, 32, 32, line=color)
        shape(surf, tf, [(300, 520), (660, 520)], line=color, width=3, closed=False)

    def backdrop(self):
        surf = gradient((250, 244, 228), (240, 228, 206))
        pygame.draw.rect(surf, (200, 222, 240), (680, 60, 200, 240))
        pygame.draw.rect(surf, (255, 255, 255), (680, 60, 200, 240), 10)
        pygame.draw.line(surf, (255, 255, 255), (780, 60), (780, 300), 8)
        pygame.draw.rect(surf, (196, 146, 96), (0, 520, 960, 56))
        pygame.draw.line(surf, (160, 112, 70), (0, 520), (960, 520), 4)
        return surf

    def final(self, surf, t):
        tf = make_tf()
        plant = make_tf(angle=0.07 * math.sin(1.4 * t), center=(480, 400))
        shape(surf, plant, [(480, 400), (478, 340), (482, 300), (480, 268)], line=(70, 160, 80), width=9, closed=False)
        shape(surf, plant, self.LEAF, fill=(96, 184, 90))
        shape(surf, plant, self.PETALS, fill=(240, 110, 170), width=4)
        oval(surf, plant, 480, 200, 32, 32, fill=(255, 210, 60))
        for k in range(6):
            a = k * TWO_PI / 6
            oval(surf, plant, 480 + 14 * math.cos(a), 200 + 14 * math.sin(a), 3, 3, fill=(200, 140, 40), line=None)
        shape(surf, tf, self.POT, fill=(205, 105, 65), width=5)
        shape(surf, tf, [(370, 400), (590, 400), (590, 432), (370, 432)], fill=(180, 86, 52), width=4)
        bx, by = 480 + 230 * math.cos(0.9 * t), 210 + 90 * math.sin(1.8 * t)
        wing = 8 + 5 * abs(math.sin(20 * t))
        ui.circle(surf, (255, 255, 255, 180), (bx - 4, by - 12), wing)
        ui.circle(surf, (255, 255, 255, 180), (bx + 6, by - 12), wing)
        pygame.draw.ellipse(surf, (250, 200, 40), (bx - 14, by - 9, 28, 18))
        for dx in (-5, 3):
            pygame.draw.line(surf, OUTLINE, (bx + dx, by - 8), (bx + dx, by + 8), 3)
        pygame.draw.ellipse(surf, OUTLINE, (bx - 14, by - 9, 28, 18), 2)


PICTURES = [Star(), House(), Boat(), Rocket(), Cat(), Fish(), Butterfly(), Constellations(), Flower()]
