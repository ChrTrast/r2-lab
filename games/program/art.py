"""Τα γραφικά του «Προγραμμάτισε»: ένα νησάκι από κυβάκια που αιωρείται στον ουρανό.

Όλα ζωγραφίζονται με κώδικα, με «pixel» υφές (χορτάρι, χώμα, πέτρα, νερό, ξύλο), στην ίδια πλάγια
προβολή με το «Ακολούθησε» (art.Geo). Το R2 είναι το τρισδιάστατο R2 του «Ακολούθησε».

Ό,τι δεν κινείται (ουρανός, νησί, αφετηρία, φορτιστής) ζωγραφίζεται μία φορά σε μια εικόνα.
Πέτρες, δέντρα και πόρτες γίνονται μικρές εικόνες (sprites) και μπαίνουν με τη σειρά βάθους
μαζί με το R2 και την πασχαλίτσα, ώστε ό,τι είναι πιο μπροστά να σκεπάζει ό,τι είναι πιο πίσω.
"""
import math
import random
import zlib

import pygame
import pygame.gfxdraw

from core import ui
from core.ui import fill_poly, mix, shade
from games.line_follow import art as lf
from games.maze import art as r2art
from . import logic

CUBE = 78                # το ύψος ενός κύβου (μονάδες z της Geo)
LED_RGB = {"red": (230, 56, 56), "green": (60, 190, 90), "blue": (52, 116, 240), "yellow": (250, 206, 40)}
LED_OFF = (70, 74, 84)

PAL = {
    "grass": [(106, 184, 70), (96, 172, 62), (120, 198, 82), (88, 160, 56)],
    "dirt": [(140, 100, 64), (124, 88, 56), (154, 112, 72), (110, 78, 50)],
    "stone": [(136, 138, 144), (120, 122, 128), (152, 154, 160), (104, 106, 112)],
    "sand": [(236, 216, 152), (224, 204, 138), (244, 228, 170), (214, 192, 128)],
    "water": [(62, 140, 230), (52, 126, 214), (80, 158, 240)],
    "plank": [(190, 140, 82), (176, 128, 72), (202, 152, 94)],
    "leaf": [(66, 152, 60), (54, 134, 52), (84, 172, 72), (44, 116, 44)],
    "bark": [(116, 84, 54), (100, 72, 46), (130, 96, 62)],
    "black": [(30, 30, 34), (40, 40, 46), (24, 24, 28)],
}


# ================================================================ υφές
def _tex(kind, face, rng, n):
    """Τι χρώμα έχει κάθε «pixel» (i, j) μιας πλευράς."""
    p = PAL
    if kind == "grass":
        if face == "top":
            return lambda i, j: rng.choice(p["grass"]) if rng.random() < 0.9 else (140, 210, 96)
        drip = [rng.random() < 0.55 for _ in range(n)]
        return lambda i, j: (rng.choice(p["grass"]) if j == 0 or (j == 1 and drip[i]) else rng.choice(p["dirt"]))
    if kind == "stone":
        moss = face == "top"
        return lambda i, j: ((88, 150, 70) if moss and rng.random() < 0.12 else
                             (rng.choice(p["stone"]) if rng.random() < 0.92 else (92, 94, 100)))
    if kind == "plank":
        if face == "top":
            return lambda i, j: shade(p["plank"][(i // 2) % 3], 0.8 if i % 2 and j % 4 == 0 else 1.0)
        return lambda i, j: shade(p["plank"][(j // 2) % 3], 0.78 if j % 2 and rng.random() < 0.3 else 1.0)
    if kind == "water":
        if face == "top":
            return lambda i, j: (150, 204, 252) if rng.random() < 0.08 else rng.choice(p["water"])
        return lambda i, j: shade(rng.choice(p["water"]), 0.9)
    if kind == "bark":
        if face == "top":
            return lambda i, j: (186, 146, 96) if (i + j) % 3 else (150, 112, 70)
        return lambda i, j: p["bark"][(i + j // 3) % 3] if rng.random() < 0.85 else (84, 60, 38)
    if isinstance(kind, tuple):                       # ένα χρώμα με λίγη «φασαρία» (πόρτες)
        pal = [shade(kind, 0.92), kind, shade(kind, 1.06)]
        return lambda i, j: rng.choice(pal)
    return lambda i, j: rng.choice(p[kind])


def _face(surf, corner, n, color_at, light):
    """Μια πλευρά κύβου από n x n «pixel». corner(u, v): σημείο της πλευράς -> οθόνη."""
    for i in range(n):
        for j in range(n):
            pts = [corner(i / n, j / n), corner((i + 1) / n, j / n),
                   corner((i + 1) / n, (j + 1) / n), corner(i / n, (j + 1) / n)]
            pygame.draw.polygon(surf, shade(color_at(i, j), light), pts)
    pygame.draw.lines(surf, (40, 40, 40), True, [corner(0, 0), corner(1, 0), corner(1, 1), corner(0, 1)], 1)


def cube(surf, g, X, Y, z0, z1, kind, seed=0, x0=0.0, x1=1.0, y0=0.0, y1=1.0, n=8, top=None, side=None):
    """Ένας κύβος (ή κομμάτι κύβου) στο κουτάκι (X, Y): δεξιά, μπροστά και πάνω πλευρά."""
    rng = random.Random(zlib.crc32(repr((X, Y, round(z0), kind, seed)).encode()))
    k = side or kind
    _face(surf, lambda u, v: g.pt(X + x1, Y + y0 + (y1 - y0) * u, z1 - (z1 - z0) * v), n, _tex(k, "side", rng, n), 0.64)
    _face(surf, lambda u, v: g.pt(X + x0 + (x1 - x0) * u, Y + y1, z1 - (z1 - z0) * v), n, _tex(k, "front", rng, n), 0.8)
    _face(surf, lambda u, v: g.pt(X + x0 + (x1 - x0) * u, Y + y0 + (y1 - y0) * v, z1), n,
          _tex(top or kind, "top", rng, n), 1.0)


def bolt(surf, to_screen, color, outline):
    pts = [(0.60, 0.10), (0.28, 0.56), (0.47, 0.56), (0.38, 0.90), (0.74, 0.40), (0.54, 0.40), (0.66, 0.10)]
    fill_poly(surf, color, [to_screen(x, y) for x, y in pts], outline)


# ============================================================ αντικείμενα
def charger(surf, g, X, Y):
    def P(u, v, z=6):
        return g.pt(X + u, Y + v, z)
    col = (60, 170, 100)
    A, B, C, D = P(0.1, 0.1), P(0.9, 0.1), P(0.9, 0.9), P(0.1, 0.9)
    B0, C0, D0 = P(0.9, 0.1, 0), P(0.9, 0.9, 0), P(0.1, 0.9, 0)
    fill_poly(surf, shade(col, 0.66), [B, C, C0, B0])
    fill_poly(surf, shade(col, 0.8), [D, C, C0, D0])
    fill_poly(surf, (92, 206, 132), [A, B, C, D], (40, 140, 80))
    fill_poly(surf, (126, 224, 160), [P(0.2, 0.2), P(0.8, 0.2), P(0.8, 0.8), P(0.2, 0.8)])
    bolt(surf, lambda x, y: P(0.22 + 0.56 * x, 0.22 + 0.56 * y), (255, 255, 255), (40, 140, 80))


def start_mark(surf, g, X, Y):
    pts = [g.pt(X + u, Y + v, 0) for u, v in ((0.08, 0.08), (0.92, 0.08), (0.92, 0.92), (0.08, 0.92))]
    s = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    fill_poly(s, (220, 238, 255, 200), pts, (150, 190, 236))
    surf.blit(s, (0, 0))
    lx, ly = g.pt(X + 0.62, Y + 0.84, 0)
    lab = ui.font(max(9, round(12 * g.k))).render("ΑΡΧΗ", True, (90, 130, 190))
    surf.blit(lab, lab.get_rect(center=(lx, ly)))


def flowers(surf, g, X, Y):
    rng = random.Random(X * 7 + Y * 31)
    for _ in range(rng.randint(0, 3)):
        x, y = g.pt(X + rng.uniform(0.15, 0.85), Y + rng.uniform(0.15, 0.85), 0)
        col = rng.choice([(240, 70, 70), (250, 214, 60), (255, 255, 255), (200, 120, 230)])
        s = max(3, round(5 * g.k))
        pygame.draw.rect(surf, (60, 130, 50), (x - 1, y - s, 2, s))
        pygame.draw.rect(surf, col, (x - s // 2, y - s - s // 2 - 2, s, s))


def tree(surf, g, X, Y):
    seed = X + Y
    cube(surf, g, X, Y, 0, CUBE * 0.95, "bark", seed, 0.38, 0.62, 0.38, 0.62, n=4)
    cube(surf, g, X, Y, CUBE * 0.7, CUBE * 1.55, "leaf", seed, 0.06, 0.94, 0.06, 0.94, n=8)
    cube(surf, g, X, Y, CUBE * 1.55, CUBE * 1.95, "leaf", seed + 1, 0.26, 0.74, 0.26, 0.74, n=4)


def door_parts(surf, g, X, Y, col, opened, along_x, part):
    """Πόρτα: δύο κολόνες και δοκάρι στο χρώμα της, και χρωματιστό τζάμι που χαμηλώνει όταν ανοίγει.
    along_x: το R2 περνά οριζόντια. part: "back" (η πίσω κολόνα) ή "front" (τζάμι, μπροστινή κολόνα, δοκάρι)."""
    H = CUBE * 1.05
    frame = shade(col, 0.72)

    def box(a0, a1, b0, b1, z0, z1, n=3):
        if along_x:
            cube(surf, g, X, Y, z0, z1, frame, 11, a0, a1, b0, b1, n=n)
        else:
            cube(surf, g, X, Y, z0, z1, frame, 11, b0, b1, a0, a1, n=n)

    if part == "back":
        box(0.36, 0.64, 0.0, 0.18, 0, H)
        return
    zt = 8 if opened else H
    rng = random.Random(X * 5 + Y)
    pal = [col, shade(col, 0.86), mix(col, (255, 255, 255), 0.3)]
    if along_x:
        corner = lambda u, v: g.pt(X + 0.5, Y + 0.18 + 0.64 * u, zt - zt * v)      # noqa: E731
    else:
        corner = lambda u, v: g.pt(X + 0.18 + 0.64 * u, Y + 0.5, zt - zt * v)      # noqa: E731
    glass = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    _face(glass, corner, 6, lambda i, j: (255, 255, 255) if (i + j) % 5 == 0 and j < 3 else rng.choice(pal), 1.0)
    glass.set_alpha(235)
    surf.blit(glass, (0, 0))
    box(0.36, 0.64, 0.82, 1.0, 0, H)
    box(0.34, 0.66, 0.0, 1.0, H, H + 16, n=4)
    lx, ly = g.pt(X + 0.5, Y + 0.5, H + 24)
    if opened:
        halo = pygame.Surface((90, 90), pygame.SRCALPHA)
        for r in range(40, 0, -4):
            pygame.draw.circle(halo, (*col, int(90 * (1 - r / 40))), (45, 45), r)
        surf.blit(halo, halo.get_rect(center=(round(lx), round(ly))))
    ui.circle(surf, col if opened else shade(col, 0.55), (lx, ly), 7 * g.k, (40, 40, 40))


def bubbles(surf, g, X, Y, time, strength):
    """Φυσαλίδες στο νερό, πάνω από μια γέφυρα που έχει βουλιάξει."""
    for i in range(4):
        u = 0.22 + 0.19 * i
        k = (time * 0.9 + i * 0.37) % 1.0
        x, y = g.pt(X + u, Y + 0.3 + 0.12 * ((i * 7) % 3), -14 + 10 * k)
        r = max(1.5, g.tw * 0.035 * (0.6 + k))
        a = int(200 * strength * (1 - k))
        if a > 10:
            pygame.gfxdraw.aacircle(surf, int(x), int(y), int(r), (255, 255, 255, a))


def bridge_height(world, t):
    """Πόσο πάνω είναι οι γέφυρες τη στιγμή t (δεκαδική): κατεβαίνουν ή ανεβαίνουν στο τελευταίο μισό
    δευτερόλεπτο πριν αλλάξουν, ώστε στα ακέραια δευτερόλεπτα να είναι όπως λένε οι κανόνες."""
    if not world.sink:
        return 1.0
    k = math.floor(t)
    now, nxt = world.bridges_up(k), world.bridges_up(k + 1)
    if now == nxt:
        return 1.0 if now else 0.0
    s = max(0.0, min(1.0, (t - k - 0.5) / 0.5))
    return 1.0 - s if now else s


def crystal(surf, g, X, Y, time=0.0):
    bob = math.sin(time * 2.4 + X * 1.3 + Y) * 5
    cx, cy = g.pt(X + 0.5, Y + 0.5, 0)
    lf._shadow(surf, cx, cy, 16 * g.k, 7 * g.k, 50)
    x, y = g.pt(X + 0.5, Y + 0.5, 42 + bob)
    s = 20 * g.k
    halo = _halo(round(s))
    surf.blit(halo, halo.get_rect(center=(round(x), round(y))))
    top, right, bot, left = (x, y - s * 1.25), (x + s * 0.72, y - s * 0.2), (x, y + s * 1.05), (x - s * 0.72, y - s * 0.2)
    mid = (x, y - s * 0.2)
    fill_poly(surf, (190, 250, 255), [top, mid, left])
    fill_poly(surf, (120, 228, 250), [top, right, mid])
    fill_poly(surf, (60, 186, 230), [left, mid, bot])
    fill_poly(surf, (30, 140, 200), [mid, right, bot])
    pygame.draw.aalines(surf, (20, 100, 160), True, [top, right, bot, left])
    tw = (math.sin(time * 5 + X) + 1) / 2
    if tw > 0.6:
        sx, sy, r = x - s * 0.3, y - s * 0.75, s * 0.35 * (tw - 0.6) / 0.4
        pygame.draw.line(surf, (255, 255, 255), (sx - r, sy), (sx + r, sy), 2)
        pygame.draw.line(surf, (255, 255, 255), (sx, sy - r), (sx, sy + r), 2)


_halos = {}


def _halo(s):
    if s not in _halos:
        img = pygame.Surface((s * 5, s * 5), pygame.SRCALPHA)
        for r in range(int(s * 2.4), 0, -3):
            a = int(70 * (1 - r / (s * 2.4)) ** 1.6)
            pygame.draw.circle(img, (120, 240, 255, a), (img.get_width() // 2, img.get_height() // 2), r)
        _halos[s] = img
    return _halos[s]


def sparkle(surf, center, t, color=(120, 240, 255)):
    """Αστεράκια που πετάγονται όταν το R2 παίρνει έναν κρύσταλλο (t από 0 ως 1)."""
    x, y = center
    for i in range(8):
        a = i * math.pi / 4
        r = 10 + 34 * t
        ui.circle(surf, color, (x + r * math.cos(a), y + r * math.sin(a) - 20 * t), max(1.5, 5 * (1 - t)))


def ladybug(surf, g, X, Y, hx, hy, step=0.0):
    """Πασχαλίτσα από κυβάκια (κόκκινο σώμα με μαύρες βούλες, μαύρο κεφάλι). (X, Y): το κέντρο της."""
    cx, cy = g.pt(X, Y, 0)
    lf._shadow(surf, cx, cy, 30 * g.k, 12 * g.k, 50)
    lift = abs(math.sin(step * math.pi)) * 4
    dots = {(1, 1), (4, 1), (2, 3), (5, 3), (1, 5), (4, 5)}
    x0, y0, s = X - 0.32, Y - 0.32, 0.64

    def top(i, j):
        return (24, 24, 28) if (i, j) in dots else ((226, 44, 40) if (i + j) % 3 else (206, 36, 34))
    _face(surf, lambda u, v: g.pt(x0 + s, y0 + s * u, 34 + lift - 30 * v), 6, lambda i, j: (190, 34, 32), 0.64)
    _face(surf, lambda u, v: g.pt(x0 + s * u, y0 + s, 34 + lift - 30 * v), 6, lambda i, j: (190, 34, 32), 0.8)
    _face(surf, lambda u, v: g.pt(x0 + s * u, y0 + s * v, 34 + lift), 7, top, 1.0)
    pygame.draw.line(surf, (24, 24, 28), g.pt(X - 0.3 * hx, Y - 0.3 * hy, 34.5 + lift),
                     g.pt(X + 0.3 * hx, Y + 0.3 * hy, 34.5 + lift), max(2, round(3 * g.k)))
    hx0, hy0 = X + hx * 0.32 - 0.14, Y + hy * 0.32 - 0.14
    cube(surf, g, 0, 0, 4 + lift, 26 + lift, "black", 3, hx0, hx0 + 0.28, hy0, hy0 + 0.28, n=2)
    for side in (-1, 1):
        ex, ey = X + hx * 0.42 + side * 0.07 * hy, Y + hy * 0.42 - side * 0.07 * hx
        ui.circle(surf, (255, 255, 255), g.pt(ex, ey, 22 + lift), 3.2 * g.k)


def toolbox(surf, g, X, Y, roll=0.0):
    """Μεγάλη κόκκινη εργαλειοθήκη με ροδάκια, από κυβάκια. (X, Y): το κέντρο της. roll: γύρισμα των ροδών."""
    cx, cy = g.pt(X, Y, 0)
    lf._shadow(surf, cx, cy, 40 * g.k, 17 * g.k, 60)
    red, dark, metal = (204, 52, 42), (168, 38, 32), (196, 200, 208)
    for wx in (-0.34, 0.26):                         # τα ροδάκια (φαίνονται τα μπροστινά)
        cube(surf, g, 0, 0, 0, 10, "black", 21, X + wx, X + wx + 0.08, Y + 0.18, Y + 0.3, n=2)
        ui.circle(surf, (120, 124, 132), g.pt(X + wx + 0.04, Y + 0.3, 5 + math.sin(roll * 6) * 2), 1.6 * g.k)
    cube(surf, g, 0, 0, 8, 46, red, 22, X - 0.42, X + 0.42, Y - 0.3, Y + 0.3, n=6)
    cube(surf, g, 0, 0, 46, 54, dark, 23, X - 0.44, X + 0.44, Y - 0.32, Y + 0.32, n=6)
    for lx in (-0.3, 0.2):                           # τα κουμπώματα μπροστά
        cube(surf, g, 0, 0, 36, 48, metal, 24, X + lx, X + lx + 0.1, Y + 0.3, Y + 0.34, n=2)
    for hx in (-0.22, 0.16):                         # το χερούλι
        cube(surf, g, 0, 0, 54, 64, "black", 25, X + hx, X + hx + 0.06, Y - 0.04, Y + 0.04, n=2)
    cube(surf, g, 0, 0, 64, 70, "black", 26, X - 0.22, X + 0.22, Y - 0.04, Y + 0.04, n=3)


def sensor_waves(surf, g, X, Y, hx, hy, t=0.0):
    """Οι «υπέρηχοι» του αισθητήρα απόστασης: λευκά τόξα μπροστά από το R2."""
    s = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    sx, sy = -hy, hx
    for k in range(3):
        d = 0.42 + 0.22 * k + 0.22 * (t % 1.0)
        pts = []
        for i in range(13):
            a = -0.55 + 1.1 * i / 12
            pts.append(g.pt(X + hx * d * math.cos(a) + sx * d * math.sin(a),
                            Y + hy * d * math.cos(a) + sy * d * math.sin(a), 30))
        pygame.draw.lines(s, (255, 255, 255, int(230 * (1 - k / 3))), False, pts, max(2, round(4 * g.k)))
    surf.blit(s, (0, 0))


def led_glow(surf, g, X, Y, col):
    """Το φως του LED στο χορτάρι κάτω από το R2."""
    x, y = g.pt(X, Y, 0)
    w = round(260 * g.k)
    glow = pygame.Surface((w, w // 2), pygame.SRCALPHA)
    for r in range(10, 0, -1):
        pygame.draw.ellipse(glow, (*col, 16), pygame.Rect(w / 2 - w * 0.05 * r, w / 4 - w * 0.027 * r,
                                                         w * 0.1 * r, w * 0.054 * r))
    surf.blit(glow, glow.get_rect(center=(round(x), round(y))))


# ================================================================ ο χάρτης
class Board:
    """Πού μπαίνει ο χάρτης μέσα στο ορθογώνιο rect (όσο πιο μεγάλος χωράει) και η ζωγραφική του.

    bottom: πόσο χώρο αφήνει κάτω (για τη λωρίδα με τα αστέρια)."""

    def __init__(self, world, rect, bottom=64):
        self.world = world
        self.rect = pygame.Rect(rect)
        r = self.rect
        cols, rows = world.cols, world.rows
        avail = r.h - bottom - 16
        tw = min(104.0, (r.w - 70) / (cols + rows * 0.46))
        while True:
            k = tw / 104
            h = 1.9 * CUBE * k + rows * tw * 0.8 + 2.6 * CUBE * k
            if h <= avail or tw < 30:
                break
            tw -= 2
        k = tw / 104
        w = cols * tw + rows * tw * 0.46
        ox = r.centerx - w / 2 + rows * tw * 0.46
        oy = r.y + 8 + (avail - h) / 2 + 1.9 * CUBE * k
        self.g = lf.Geo(ox, oy, tw, tw * 0.46, tw * 0.8)
        self.ground = None
        self._sprites = {}

    def pt(self, X, Y, z=0.0):
        return self.g.pt(X, Y, z)

    # -------------------------------------------------------- μία φορά
    def build(self):
        """Ο ουρανός και το νησί, σε μια εικόνα στο μέγεθος του rect (με στρογγυλές γωνίες)."""
        r = self.rect
        g = lf.Geo(self.g.ox - r.x, self.g.oy - r.y, self.g.tw, self.g.shift, self.g.th)
        img = pygame.Surface(r.size, pygame.SRCALPHA)
        for y in range(r.h):
            pygame.draw.line(img, mix((110, 182, 246), (200, 232, 252), y / r.h), (0, y), (r.w, y))
        self._sky_decor(img)
        w = self.world
        rng = random.Random(7)
        # το κάτω μέρος του νησιού (πρώτα το πιο χαμηλό), μετά το έδαφος
        under3, under2 = [], []
        for y in range(w.rows):
            for x in range(w.cols):
                edge = min(x, y, w.cols - 1 - x, w.rows - 1 - y)
                if edge >= 1 or rng.random() < 0.45:
                    under2.append((x, y))
                if edge >= 1 and rng.random() < 0.45:
                    under3.append((x, y))
        for x, y in under3:
            cube(img, g, x, y, -3 * CUBE, -2 * CUBE, "dirt", 2)
        for x, y in under2:
            cube(img, g, x, y, -2 * CUBE, -CUBE, "dirt", 1)
        for y in range(w.rows):
            for x in range(w.cols):
                ch = w.cells[(x, y)]
                if ch == "~":
                    cube(img, g, x, y, -CUBE, -16, "water", 3)
                elif ch == "=":
                    cube(img, g, x, y, -CUBE, -16, "water", 3)
                    if not w.sink:                  # γέφυρες που βουλιάζουν: ζωγραφίζονται σε κάθε καρέ
                        cube(img, g, x, y, -16, -6, "plank", 3, 0.0, 1.0, 0.1, 0.9)
                elif ch == "s":
                    cube(img, g, x, y, -CUBE, 0, "sand", 3)
                else:
                    cube(img, g, x, y, -CUBE, 0, "grass", 3)
                if ch == ".":
                    flowers(img, g, x, y)
                elif ch == "S":
                    start_mark(img, g, x, y)
                elif ch == "G":
                    charger(img, g, x, y)
        if w.line:                                   # η μαύρη γραμμή, πάνω σε λευκή ταινία
            pts = [g.pt(x + 0.5, y + 0.5, 0.5) for x, y in w.line]
            for color, width in (((236, 236, 228), 0.4), ((30, 30, 34), 0.13)):
                wpx = max(3, round(g.tw * width))
                if len(pts) > 1:
                    pygame.draw.lines(img, color, False, pts, wpx)
                for pt in pts:
                    pygame.draw.circle(img, color, pt, wpx / 2)
            if w.goal in w.line_index:               # ο φορτιστής πάνω από τη γραμμή
                charger(img, g, *w.goal)
        mask = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=20)
        img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.ground = img
        return img

    def _sky_decor(self, img):
        w, h = img.get_size()
        rng = random.Random(4)
        for fx, fy, n in ((0.13, 0.12, 5), (0.76, 0.08, 6), (0.88, 0.5, 4), (0.08, 0.63, 4), (0.58, 0.93, 5)):
            cx, cy = fx * w, fy * h
            for i in range(n):
                bw = rng.randint(3, 6) * 12
                pygame.draw.rect(img, (255, 255, 255), (cx + i * 22 - 20, cy - (i % 2) * 12, bw, 24))
            pygame.draw.rect(img, (236, 246, 255), (cx - 20, cy + 18, n * 22 + 30, 8))
        for fx, fy, n in ((0.06, 0.35, 3), (0.86, 0.26, 2), (0.84, 0.82, 2)):
            gg = lf.Geo(fx * w, fy * h, 30, 14, 24)
            for i in range(n):
                cube(img, gg, i, 0, -CUBE, 0, "grass", 9, n=4)
            cube(img, gg, n // 2, 0, -2 * CUBE, -CUBE, "dirt", 9, n=4)

    def _sprite(self, key, draw):
        """Ζωγραφίζει ένα αντικείμενο σε διάφανη εικόνα και κρατά μόνο το κομμάτι που έχει κάτι."""
        if key not in self._sprites:
            r = self.rect
            big = pygame.Surface((r.w, r.h + 200), pygame.SRCALPHA)
            g = lf.Geo(self.g.ox - r.x, self.g.oy - r.y + 200, self.g.tw, self.g.shift, self.g.th)
            draw(big, g)
            box = big.get_bounding_rect()
            img = big.subsurface(box).copy() if box.w and box.h else pygame.Surface((1, 1), pygame.SRCALPHA)
            self._sprites[key] = (img, (box.x + r.x, box.y + r.y - 200))
        return self._sprites[key]

    def objects(self, cell, led):
        """Οι εικόνες του κουτακιού: (πίσω, μπροστά). Το R2 ζωγραφίζεται ανάμεσά τους."""
        ch = self.world.cells[cell]
        x, y = cell
        if ch == "#":
            return [self._sprite(("stone", cell), lambda s, g: cube(s, g, x, y, 0, CUBE, "stone", 5))], []
        if ch == "T":
            return [self._sprite(("tree", cell), lambda s, g: tree(s, g, x, y))], []
        if ch in logic.DOORS:
            color = logic.DOORS[ch]
            opened = led == color
            w = self.world
            along_x = w.at((x - 1, y)) not in (None, "#", "T", "~") or w.at((x + 1, y)) not in (None, "#", "T", "~")
            col = LED_RGB[color]
            back = self._sprite(("door", cell, "back"),
                                lambda s, g: door_parts(s, g, x, y, col, False, along_x, "back"))
            front = self._sprite(("door", cell, opened),
                                 lambda s, g: door_parts(s, g, x, y, col, opened, along_x, "front"))
            return [back], [front]
        return [], []

    def plank(self, cell, level):
        """Η σανίδα μιας γέφυρας που βουλιάζει. level: 1 πάνω, 0 κάτω από το νερό (φαίνεται αχνά)."""
        step = round(max(0.0, min(1.0, level)) * 10)
        x, y = cell
        top = -6 - (10 - step) * 0.9                # η σανίδα χαμηλώνει ως την επιφάνεια του νερού (-16)
        cover = (10 - step) * 20                    # και το νερό τη σκεπάζει όλο και πιο πολύ

        def draw(s, g):
            cube(s, g, x, y, -16, top, "plank", 3, 0.0, 1.0, 0.1, 0.9)
            if cover:
                film = pygame.Surface(s.get_size(), pygame.SRCALPHA)
                quad = [g.pt(x + u, y + v, -14) for u, v in ((0, 0.1), (1, 0.1), (1, 0.9), (0, 0.9))]
                pygame.draw.polygon(film, PAL["water"][0] + (cover,), quad)
                s.blit(film, (0, 0))
        return self._sprite(("plank", cell, step), draw)

    # ----------------------------------------------------------- κάθε καρέ
    def draw(self, surf, time, robot=None, led=None, bug=None, taken=(), waves=None, charging=False, bridge=1.0,
             box=None):
        """robot: (X, Y, hx, hy, κουτάκι, σπιν ροδών). bug: (X, Y, hx, hy, κουτάκι, βήμα).
        box: (X, Y, κουτάκι, γύρισμα ροδών) της εργαλειοθήκης που κινείται.
        bridge: πόσο πάνω είναι οι γέφυρες που βουλιάζουν (1 πάνω, 0 κάτω από το νερό)."""
        if self.ground is None:
            self.build()
        surf.blit(self.ground, self.rect)
        old = surf.get_clip()
        surf.set_clip(self.rect.inflate(-4, -4))
        w, g = self.world, self.g
        if w.sink:
            for cell, ch in w.cells.items():
                if ch == "=":
                    img, pos = self.plank(cell, bridge)
                    surf.blit(img, pos)
                    if bridge < 1:                  # φυσαλίδες όσο η γέφυρα είναι κάτω
                        bubbles(surf, g, cell[0], cell[1], time, 1 - bridge)
        for y in range(w.rows):
            for x in range(w.cols):
                cell = (x, y)
                back, front = self.objects(cell, led)
                for img, pos in back:
                    surf.blit(img, pos)
                if cell in w.crystals and cell not in taken:
                    crystal(surf, g, x, y, time)
                if bug and bug[4] == cell:
                    ladybug(surf, g, bug[0], bug[1], bug[2], bug[3], bug[5])
                if box and box[2] == cell:
                    toolbox(surf, g, box[0], box[1], box[3])
                if robot and robot[4] == cell:
                    self._robot(surf, robot, led, waves, charging, time)
                for img, pos in front:
                    surf.blit(img, pos)
        surf.set_clip(old)
        pygame.draw.rect(surf, (206, 214, 228), self.rect, width=3, border_radius=20)

    def _robot(self, surf, robot, led, waves, charging, time):
        X, Y, hx, hy, _, spin = robot
        g = self.g
        if led:
            led_glow(surf, g, X, Y, LED_RGB[led])
        if charging:
            r2art.charge_rings(surf, g.pt(X, Y, 10), time, g.tw * 0.8)
        lf.draw_robot(surf, g, X, Y, hx, hy, led=LED_RGB[led] if led else LED_OFF, z=0, spin=(spin, spin))
        if waves is not None:
            sensor_waves(surf, g, X + hx * 0.2, Y + hy * 0.2, hx, hy, waves)

    def robot_top(self, X, Y):
        """Πάνω από το κεφάλι του R2 (για τα συννεφάκια)."""
        return self.g.pt(X, Y, 90)


# ================================================================ μενού
def menu_icon(surf, c):
    """Το εικονίδιο της κάρτας: ένα νησάκι 3x2 με το R2, μια πέτρα, έναν κρύσταλλο και τον φορτιστή."""
    g = lf.Geo(c[0] - 56, c[1] - 42, 54, 25, 38)
    for y in range(2):
        for x in range(3):
            cube(surf, g, x, y, -CUBE, 0, "grass", 3, n=6)
    cube(surf, g, 2, 0, 0, CUBE, "stone", 5, n=6)
    charger(surf, g, 2, 1)
    crystal(surf, g, 1, 0, 0.3)
    lf.draw_robot(surf, g, 0.6, 1.5, 1, 0, led=LED_RGB["green"], z=0)
