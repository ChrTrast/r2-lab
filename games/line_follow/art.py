"""Τα γραφικά του «Ακολούθησε»: η μαύρη γραμμή, το R2, ο φορτιστής, το τοπίο.

Όλα ζωγραφίζονται με κώδικα, χωρίς αρχεία εικόνων.

Οι στατικές εικόνες ζωγραφίζονται σε διπλό μέγεθος και μικραίνουν, για λείες γραμμές.
"""
import math
import random

import pygame
import pygame.gfxdraw

from core.ui import circle, fill_poly, font, mix, shade
from games.maze import art as r2
from . import logic

SS = 2

SKY_TOP = (126, 190, 240)
SKY_LOW = (214, 236, 250)
GRASS = (126, 192, 92)
GRASS_DARK = (104, 168, 74)
GRASS_LIGHT = (156, 210, 112)
WOOD_TOP = (214, 174, 120)
WOOD_FRONT = (172, 130, 84)
WOOD_SIDE = (144, 106, 68)
HOLE = (92, 152, 78)
TILE_TOP = (248, 246, 238)
TILE_FIXED = (226, 222, 210)
LINE = (28, 28, 32)
LINE_HALF = 0.07      # μισό πλάτος της μαύρης γραμμής, σε κελιά
WINDOW = (196, 228, 250)

PIECE_Z = 16          # ύψος της επιφάνειας των κομματιών
BOARD_Z = 10          # ύψος του ξύλινου ταμπλό
SIGNAL_CELL = (logic.COLS, logic.START_ROW - 1)
SIGNAL_POS = (0.16, 0.86)

BLOCK_KINDS = ("tree", "pine", "house", "block_red", "block_blue", "block_yellow")
NEW_KINDS = ("rocks", "windmill")      # μόνο όπου η πίστα λέει τι μπαίνει πού (kinds), ποτέ τυχαία

FIXED_PLATE = (212, 218, 228)          # τα βιδωμένα κομμάτια
GEAR = (250, 194, 46)
GEAR_DARK = (178, 120, 18)
GEAR_LIGHT = (255, 228, 128)
WATER = (78, 158, 226)
WATER_DEEP = (58, 128, 204)
WATER_LIGHT = (176, 222, 250)
BANK = (232, 216, 170)
DECK = (206, 160, 100)


class Geo:
    """Μετατρέπει θέσεις του ταμπλό (στήλη X, σειρά Y, ύψος z) σε pixels.

    Το ταμπλό είναι πλάγιο: κάθε σειρά πιο κάτω μετακινείται λίγο αριστερά.
    """

    def __init__(self, ox, oy, tw=104, shift=50, th=84):
        self.ox, self.oy, self.tw, self.shift, self.th = ox, oy, tw, shift, th
        self.k = tw / 104.0

    def pt(self, X, Y, z=0.0):
        return (self.ox + X * self.tw - Y * self.shift, self.oy + Y * self.th - z * self.k)

    def scaled(self, f, ox, oy):
        return Geo(ox, oy, self.tw * f, self.shift * f, self.th * f)

    def world_at(self, sx, sy, z=0.0):
        Y = (sy + z * self.k - self.oy) / self.th
        X = (sx - self.ox + Y * self.shift) / self.tw
        return X, Y

    def depth(self, X, Y):
        """Όσο μεγαλύτερο, τόσο πιο κοντά μας (ζωγραφίζεται αργότερα)."""
        return X * self.shift / self.tw + Y


def render(geo, w, h, anchor, draw, scale=1.0):
    """Ζωγραφίζει σε διπλό μέγεθος και μικραίνει. Το σημείο (0, 0) πέφτει στο anchor."""
    ax, ay = anchor
    big = pygame.Surface((round(w * SS), round(h * SS)), pygame.SRCALPHA)
    draw(big, geo.scaled(SS, ax * SS, ay * SS))
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return pygame.transform.smoothscale(big, size)


# ------------------------------------------------------------ basic shapes
def slab(surf, g, X0, Y0, X1, Y1, z0, z1, top, front=None, side=None, line=None):
    """Πλάκα/κουτί: πάνω επιφάνεια, μπροστινή και δεξιά πλευρά."""
    front = front or shade(top, 0.8)
    side = side or shade(top, 0.66)
    A, B, C, D = g.pt(X0, Y0, z1), g.pt(X1, Y0, z1), g.pt(X1, Y1, z1), g.pt(X0, Y1, z1)
    B0, C0, D0 = g.pt(X1, Y0, z0), g.pt(X1, Y1, z0), g.pt(X0, Y1, z0)
    fill_poly(surf, side, [B, C, C0, B0])
    fill_poly(surf, front, [D, C, C0, D0])
    fill_poly(surf, top, [A, B, C, D])
    if line:
        pygame.draw.lines(surf, line, True, [A, B, C, D], max(1, round(g.k)))


def hole(surf, g, c, r):
    """Άδειο κελί: μια πράσινη 'θήκη' στο ταμπλό."""
    m = 0.06
    A, B = g.pt(c + m, r + m, BOARD_Z), g.pt(c + 1 - m, r + m, BOARD_Z)
    C, D = g.pt(c + 1 - m, r + 1 - m, BOARD_Z), g.pt(c + m, r + 1 - m, BOARD_Z)
    fill_poly(surf, HOLE, [A, B, C, D])
    w = max(2, round(3 * g.k))
    pygame.draw.line(surf, shade(HOLE, 0.7), A, B, w)
    pygame.draw.line(surf, shade(HOLE, 0.7), A, D, w)
    pygame.draw.line(surf, shade(HOLE, 1.2), D, C, w)
    pygame.draw.line(surf, shade(HOLE, 1.2), B, C, w)


def _frame(a, b, t):
    (u, v), (du, dv) = logic.point_on_piece(a, b, t)
    n = math.hypot(du, dv) or 1.0
    return u, v, du / n, dv / n


def line_piece(surf, g, X, Y, a, b, z=PIECE_Z):
    """Η μαύρη γραμμή για ένα κομμάτι που ενώνει τις πλευρές a και b."""
    steps = 6 if logic.is_straight(a, b) else 20
    P = lambda u, v: g.pt(X + u, Y + v, z)
    mid = [_frame(a, b, i / steps) for i in range(steps + 1)]
    left = [P(u - dv * LINE_HALF, v + du * LINE_HALF) for u, v, du, dv in mid]
    right = [P(u + dv * LINE_HALF, v - du * LINE_HALF) for u, v, du, dv in mid]
    fill_poly(surf, LINE, left + right[::-1])


def piece_tile(surf, g, ptype, X=0, Y=0, fixed=False):
    slab(surf, g, X + 0.03, Y + 0.03, X + 0.97, Y + 0.97, BOARD_Z, PIECE_Z,
         TILE_FIXED if fixed else TILE_TOP, line=shade(TILE_TOP, 0.75))
    a, b = logic.PIECES[ptype]
    line_piece(surf, g, X, Y, a, b)


def _screw(surf, g, X, Y, z):
    x, y = g.pt(X, Y, z)
    r = 3.4 * g.k
    circle(surf, (186, 192, 204), (x, y), r, (104, 110, 124))
    w = max(1, round(1.2 * g.k))
    pygame.draw.line(surf, (104, 110, 124), (x - r * 0.62, y + r * 0.34), (x + r * 0.62, y - r * 0.34), w)


def fixed_tile(surf, g, ptype):
    """Σταθερό κομμάτι: γκρι μεταλλική πλάκα βιδωμένη στο ταμπλό (δεν βγαίνει). Το 7 είναι διασταύρωση."""
    slab(surf, g, 0.03, 0.03, 0.97, 0.97, BOARD_Z, PIECE_Z, FIXED_PLATE, line=shade(FIXED_PLATE, 0.68))
    if ptype == logic.CROSS:
        line_piece(surf, g, 0, 0, logic.W, logic.E)
        line_piece(surf, g, 0, 0, logic.N, logic.S)
    else:
        line_piece(surf, g, 0, 0, *logic.PIECES[ptype])
    for u, v in ((0.12, 0.12), (0.88, 0.12), (0.88, 0.88), (0.12, 0.88)):
        _screw(surf, g, u, v, PIECE_Z)


def bridge_tile(surf, g, ptype):
    """Ξύλινη γέφυρα πάνω από το ποτάμι, με τη μαύρη γραμμή στις σανίδες (σταθερή)."""
    across = ptype == 6                 # η γέφυρα πάει από αριστερά προς τα δεξιά
    X0, X1, Y0, Y1 = (-0.03, 1.03, 0.08, 0.92) if across else (0.08, 0.92, -0.03, 1.03)
    # δοκάρια κάτω από τις σανίδες
    for t in (0.2, 0.8):
        if across:
            Ym = Y0 + (Y1 - Y0) * t
            slab(surf, g, X0, Ym - 0.03, X1, Ym + 0.03, 2, BOARD_Z + 2, shade(DECK, 0.6))
        else:
            Xm = X0 + (X1 - X0) * t
            slab(surf, g, Xm - 0.03, Y0, Xm + 0.03, Y1, 2, BOARD_Z + 2, shade(DECK, 0.6))
    slab(surf, g, X0, Y0, X1, Y1, BOARD_Z + 2, PIECE_Z, DECK, shade(DECK, 0.78), shade(DECK, 0.64))
    n = 10
    for i in range(1, n):
        t = i / n
        if across:
            a, b = g.pt(X0 + (X1 - X0) * t, Y0, PIECE_Z), g.pt(X0 + (X1 - X0) * t, Y1, PIECE_Z)
        else:
            a, b = g.pt(X0, Y0 + (Y1 - Y0) * t, PIECE_Z), g.pt(X1, Y0 + (Y1 - Y0) * t, PIECE_Z)
        pygame.draw.line(surf, shade(DECK, 0.72), a, b, max(1, round(g.k)))
    for i in range(0, n, 3):           # μερικά καρφιά
        t = (i + 0.5) / n
        for v in (0.18, 0.82):
            u = X0 + (X1 - X0) * (t if across else v)
            w = Y0 + (Y1 - Y0) * (v if across else t)
            circle(surf, shade(DECK, 0.55), g.pt(u, w, PIECE_Z), 1.3 * g.k)
    line_piece(surf, g, 0, 0, *logic.PIECES[ptype])
    # χαμηλά κάγκελα με κολονάκια στις δύο πλευρές
    rail = (122, 84, 52)
    for side in (0, 1):
        if across:
            Y = Y0 + 0.02 if side == 0 else Y1 - 0.05
            for X in (X0 + 0.02, 0.5 - 0.015, X1 - 0.05):
                slab(surf, g, X, Y, X + 0.04, Y + 0.03, PIECE_Z, PIECE_Z + 9, rail)
            slab(surf, g, X0 + 0.02, Y, X1 - 0.01, Y + 0.03, PIECE_Z + 7, PIECE_Z + 9, shade(rail, 1.15))
        else:
            X = X0 + 0.02 if side == 0 else X1 - 0.05
            for Y in (Y0 + 0.02, 0.5 - 0.015, Y1 - 0.05):
                slab(surf, g, X, Y, X + 0.03, Y + 0.04, PIECE_Z, PIECE_Z + 9, rail)
            slab(surf, g, X, Y0 + 0.02, X + 0.03, Y1 - 0.01, PIECE_Z + 7, PIECE_Z + 9, shade(rail, 1.15))


def river(surf, g, water):
    """Το ποτάμι μιας πίστας (σε συντεταγμένες της οθόνης): νερό, όχθες και ένας μικρός καταρράκτης
    στην μπροστινή πλευρά του ταμπλό, από όπου συνεχίζει σαν ρυάκι στο γρασίδι."""
    water = set(water)
    rng = random.Random(7)
    z = BOARD_Z
    k = g.k
    for c, r in sorted(water):
        Y0 = -0.1 if r == 0 else r
        Y1 = logic.ROWS + 0.1 if r == logic.ROWS - 1 else r + 1
        X0 = c if (c - 1, r) in water else c + 0.02
        X1 = c + 1 if (c + 1, r) in water else c + 0.98
        fill_poly(surf, WATER, [g.pt(X0, Y0, z), g.pt(X1, Y0, z), g.pt(X1, Y1, z), g.pt(X0, Y1, z)])
        # πιο βαθύ στη μέση
        fill_poly(surf, WATER_DEEP, [g.pt(X0 + 0.3, Y0, z), g.pt(X1 - 0.3, Y0, z),
                                     g.pt(X1 - 0.3, Y1, z), g.pt(X0 + 0.3, Y1, z)])
        # όχθες με βότσαλα
        for side, edge in ((-1, X0), (1, X1)):
            if (c + side, r) in water:
                continue
            inner = edge - side * 0.09
            lo, hi = min(edge, inner), max(edge, inner)
            fill_poly(surf, BANK, [g.pt(lo, Y0, z), g.pt(hi, Y0, z), g.pt(hi, Y1, z), g.pt(lo, Y1, z)])
            for _ in range(7):
                u = edge - side * rng.uniform(0.02, 0.08)
                v = rng.uniform(Y0 + 0.04, Y1 - 0.04)
                col = rng.choice(((168, 160, 150), (196, 188, 176), (140, 134, 128)))
                x, y = g.pt(u, v, z)
                pygame.gfxdraw.filled_ellipse(surf, round(x), round(y), max(1, round(3 * k)), max(1, round(2 * k)), col)
        # κυματάκια
        for _ in range(5):
            u = rng.uniform(X0 + 0.2, X1 - 0.3)
            v = rng.uniform(Y0 + 0.1, Y1 - 0.15)
            pts = [g.pt(u, v, z), g.pt(u + 0.08, v - 0.05, z), g.pt(u + 0.16, v, z)]
            pygame.draw.lines(surf, WATER_LIGHT, False, pts, max(1, round(2 * k)))
        if r == logic.ROWS - 1:
            # καταρράκτης στο μπροστινό ξύλο του ταμπλό και ρυάκι στο γρασίδι
            Yf = logic.ROWS + 0.1
            fill_poly(surf, WATER_DEEP, [g.pt(X0, Yf, z), g.pt(X1, Yf, z), g.pt(X1, Yf, 0), g.pt(X0, Yf, 0)])
            for i in range(6):
                u = X0 + (X1 - X0) * (i + 0.5) / 6
                pygame.draw.line(surf, WATER_LIGHT, g.pt(u, Yf, z - 1), g.pt(u, Yf, 2), max(1, round(1.5 * k)))
            left, right = [], []
            for i in range(9):
                v = Yf + i * 0.16
                wob = 0.08 * math.sin(i * 1.3)
                left.append(g.pt(X0 + 0.1 + wob + i * 0.02, v, 0))
                right.append(g.pt(X1 - 0.1 + wob - i * 0.02, v, 0))
            fill_poly(surf, GRASS_DARK, [(x - 4 * k, y) for x, y in left] + [(x + 4 * k, y) for x, y in right[::-1]])
            fill_poly(surf, WATER, left + right[::-1])
            for i in range(4):          # αφρός στη βάση του καταρράκτη
                x, y = g.pt(X0 + (X1 - X0) * (0.2 + 0.2 * i), Yf + 0.04, 0)
                circle(surf, (236, 248, 255), (x, y), 4.5 * k)
        if r == 0:
            # πέτρες εκεί που μπαίνει το νερό στο ταμπλό
            for u, rad in ((X0 + 0.04, 6), (X1 - 0.06, 7), (X0 + 0.5, 4)):
                x, y = g.pt(u, -0.08, z)
                circle(surf, (150, 146, 140), (x, y), rad * k, (110, 106, 100))
                circle(surf, (186, 182, 176), (x - rad * 0.3 * k, y - rad * 0.3 * k), rad * 0.45 * k)


def river_layer(geo, size, water):
    """Το ποτάμι σε μια διάφανη εικόνα όσο η οθόνη (ζωγραφίζεται μία φορά για κάθε πίστα)."""
    return render(geo, size[0], size[1], (geo.ox, geo.oy), lambda s, g: river(s, g, water))


def ripples(surf, g, cells, time):
    """Κινούμενες ανταύγειες στο νερό (κάθε καρέ). Το νερό τρέχει προς τα μπροστά."""
    k = g.k
    for c, r in cells:
        for i in range(3):
            phase = (time * 0.35 + i / 3 + c * 0.17 + r * 0.31) % 1.0
            u = c + 0.24 + 0.52 * ((i * 0.37 + c * 0.13 + r * 0.29) % 1.0)
            v = r + 0.08 + 0.84 * phase
            fade = min(phase, 1 - phase) * 2
            x, y = g.pt(u, v, BOARD_Z)
            w = 9 * k * (0.6 + 0.4 * fade)
            col = (*WATER_LIGHT, round(210 * fade))
            pygame.gfxdraw.filled_ellipse(surf, round(x), round(y), max(1, round(w)), max(1, round(1.6 * k)), col)


def grass_tile(surf, g):
    slab(surf, g, 0.03, 0.03, 0.97, 0.97, BOARD_Z, PIECE_Z, GRASS, line=GRASS_DARK)
    rng = random.Random(2)
    for _ in range(14):
        u, v = rng.uniform(0.12, 0.88), rng.uniform(0.12, 0.88)
        x, y = g.pt(u, v, PIECE_Z)
        pygame.draw.line(surf, GRASS_DARK, (x, y), (x - 2 * g.k, y - 5 * g.k), max(1, round(g.k)))
        pygame.draw.line(surf, GRASS_DARK, (x, y), (x + 2 * g.k, y - 5 * g.k), max(1, round(g.k)))


# ---------------------------------------------------------------- scenery
def _shadow(surf, x, y, rx, ry, alpha=45):
    pygame.gfxdraw.filled_ellipse(surf, round(x), round(y), max(1, round(rx)), max(1, round(ry)), (0, 0, 0, alpha))


def tree(surf, g, X, Y, z=0, size=1.0):
    k = g.k * size
    x, y = g.pt(X, Y, z)
    _shadow(surf, x + 6 * k, y, 26 * k, 9 * k)
    fill_poly(surf, (122, 80, 46), [(x - 4 * k, y), (x + 4 * k, y), (x + 3 * k, y - 36 * k), (x - 3 * k, y - 36 * k)],
              (84, 54, 32))
    blobs = [(0, -58, 24), (-18, -44, 18), (18, -44, 18), (-8, -74, 16), (11, -71, 15)]
    for dx, dy, r in blobs:
        circle(surf, (48, 122, 50), (x + (dx + 2) * k, y + (dy + 3) * k), r * k)
    for dx, dy, r in blobs:
        circle(surf, (78, 166, 68), (x + dx * k, y + dy * k), r * k)
    for dx, dy, r in blobs[:3] + blobs[3:4]:
        circle(surf, (122, 198, 94), (x + (dx - r * 0.3) * k, y + (dy - r * 0.35) * k), r * 0.42 * k)


def pine(surf, g, X, Y, z=0, size=1.0):
    k = g.k * size
    x, y = g.pt(X, Y, z)
    _shadow(surf, x + 5 * k, y, 22 * k, 8 * k)
    pygame.draw.rect(surf, (112, 74, 44), (x - 3 * k, y - 14 * k, 6 * k, 14 * k))
    for w, top, bottom in ((26, -46, -10), (21, -68, -34), (15, -88, -56)):
        fill_poly(surf, (42, 118, 70), [(x - w * k, y + bottom * k), (x + w * k, y + bottom * k), (x, y + top * k)],
                  (28, 86, 50))
        fill_poly(surf, (70, 150, 92), [(x, y + top * k), (x - w * k, y + bottom * k), (x - w * 0.25 * k, y + bottom * k)])


def bush(surf, g, X, Y, z=0, size=1.0):
    k = g.k * size
    x, y = g.pt(X, Y, z)
    _shadow(surf, x + 3 * k, y, 18 * k, 6 * k)
    for dx, dy, r in ((-9, -8, 10), (8, -8, 10), (0, -14, 11)):
        circle(surf, (66, 150, 66), (x + dx * k, y + dy * k), r * k, (50, 120, 52))
    circle(surf, (230, 90, 110), (x - 6 * k, y - 15 * k), 2.4 * k)
    circle(surf, (250, 230, 100), (x + 7 * k, y - 12 * k), 2.4 * k)


def _quad_on_front(g, X0, X1, Y, z0, z1):
    return [g.pt(X0, Y, z0), g.pt(X1, Y, z0), g.pt(X1, Y, z1), g.pt(X0, Y, z1)]


def _quad_on_side(g, X, Y0, Y1, z0, z1):
    return [g.pt(X, Y0, z0), g.pt(X, Y1, z0), g.pt(X, Y1, z1), g.pt(X, Y0, z1)]


def gable_roof(surf, g, X0, Y0, X1, Y1, z, ridge, color, wall):
    o = 0.06
    Ym = (Y0 + Y1) / 2
    zr = z + ridge
    fill_poly(surf, shade(wall, 0.72), [g.pt(X1, Y0, z), g.pt(X1, Y1, z), g.pt(X1, Ym, zr)])
    fill_poly(surf, shade(color, 0.78), [g.pt(X0 - o, Y0 - o, z), g.pt(X1 + o, Y0 - o, z),
                                         g.pt(X1 + o, Ym, zr), g.pt(X0 - o, Ym, zr)], shade(color, 0.5))
    fill_poly(surf, color, [g.pt(X0 - o, Ym, zr), g.pt(X1 + o, Ym, zr),
                            g.pt(X1 + o, Y1 + o, z), g.pt(X0 - o, Y1 + o, z)], shade(color, 0.5))


def house(surf, g, X0, Y0, X1, Y1, z, h, wall, roof):
    slab(surf, g, X0, Y0, X1, Y1, z, z + h, wall, shade(wall, 0.95), shade(wall, 0.75))
    for wx in (X0 + (X1 - X0) * 0.18, X0 + (X1 - X0) * 0.62):
        fill_poly(surf, WINDOW, _quad_on_front(g, wx, wx + (X1 - X0) * 0.2, Y1, z + h * 0.45, z + h * 0.8),
                  (90, 90, 110))
    fill_poly(surf, (150, 92, 60), _quad_on_front(g, X0 + (X1 - X0) * 0.42, X0 + (X1 - X0) * 0.56, Y1, z, z + h * 0.62))
    fill_poly(surf, shade(WINDOW, 0.85), _quad_on_side(g, X1, Y0 + 0.12, Y0 + 0.24, z + h * 0.45, z + h * 0.8),
              (90, 90, 110))
    gable_roof(surf, g, X0, Y0, X1, Y1, z + h, 20, roof, wall)


def apartment(surf, g, X0, Y0, X1, Y1, z, h, color):
    slab(surf, g, X0, Y0, X1, Y1, z, z + h, shade(color, 1.1), color, shade(color, 0.75))
    slab(surf, g, X0, Y0, X1, Y1, z + h, z + h + 4, shade(color, 0.7))
    rows, cols = 4, 3
    for i in range(cols):
        for j in range(rows):
            x0 = X0 + (X1 - X0) * (i + 0.22) / cols
            x1 = X0 + (X1 - X0) * (i + 0.78) / cols
            z0 = z + h * (j + 0.3) / rows
            z1 = z + h * (j + 0.78) / rows
            lit = (i * 7 + j * 3) % 5 == 0
            fill_poly(surf, (255, 236, 140) if lit else WINDOW, _quad_on_front(g, x0, x1, Y1, z0, z1), (70, 70, 90))
    for j in range(rows):
        z0 = z + h * (j + 0.3) / rows
        z1 = z + h * (j + 0.78) / rows
        fill_poly(surf, shade(WINDOW, 0.8), _quad_on_side(g, X1, Y0 + 0.1, Y0 + 0.24, z0, z1), (70, 70, 90))


def block_object(surf, g, kind):
    """Ό,τι κλείνει ένα κελί: δέντρο ή σπίτι (σε συντεταγμένες του κελιού)."""
    if kind == "tree":
        tree(surf, g, 0.52, 0.6, PIECE_Z)
        bush(surf, g, 0.25, 0.85, PIECE_Z, 0.6)
    elif kind == "pine":
        pine(surf, g, 0.4, 0.5, PIECE_Z, 0.95)
        pine(surf, g, 0.72, 0.78, PIECE_Z, 0.7)
    elif kind == "house":
        house(surf, g, 0.2, 0.28, 0.78, 0.7, PIECE_Z, 32, (250, 236, 200), (200, 70, 56))
        bush(surf, g, 0.82, 0.86, PIECE_Z, 0.6)
    elif kind == "rocks":
        rocks(surf, g)
    elif kind == "windmill":
        windmill(surf, g)
    else:
        color = {"block_red": (214, 76, 66), "block_blue": (70, 100, 200), "block_yellow": (226, 190, 70)}[kind]
        apartment(surf, g, 0.26, 0.3, 0.74, 0.72, PIECE_Z, 74, color)


def boulder(surf, g, X, Y, z, size, seed):
    """Ένας βράχος: ακανόνιστο σχήμα με φωτεινή κορυφή και σκούρα βάση."""
    rng = random.Random(seed)
    k = g.k * size
    x, y = g.pt(X, Y, z)
    _shadow(surf, x + 5 * k, y + 2 * k, 24 * k, 8 * k, 55)
    n = 9
    pts = []
    for i in range(n):
        a = math.pi + math.pi * i / (n - 1)          # το πάνω μισό
        rr = rng.uniform(0.82, 1.08)
        pts.append((x + 22 * k * rr * math.cos(a), y - 4 * k + 20 * k * rr * math.sin(a)))
    pts += [(x + 20 * k, y + 2 * k), (x - 20 * k, y + 2 * k)]
    fill_poly(surf, (132, 134, 140), pts, (84, 86, 94))
    top = [(px * 0.62 + (x - 4 * k) * 0.38, py * 0.62 + (y - 14 * k) * 0.38) for px, py in pts[1:n - 1]]
    fill_poly(surf, (172, 174, 180), top)
    fill_poly(surf, (198, 200, 206), [(px * 0.4 + (x - 7 * k) * 0.6, py * 0.4 + (y - 18 * k) * 0.6)
                                      for px, py in pts[2:n - 3]])
    for _ in range(3):                                # βρύα
        u, v = rng.uniform(-14, 10), rng.uniform(-6, 0)
        circle(surf, (96, 150, 70), (x + u * k, y + v * k), 2.6 * k)


def rocks(surf, g):
    boulder(surf, g, 0.36, 0.42, PIECE_Z, 1.05, 3)
    boulder(surf, g, 0.7, 0.62, PIECE_Z, 0.8, 8)
    boulder(surf, g, 0.32, 0.82, PIECE_Z, 0.55, 5)
    bush(surf, g, 0.82, 0.9, PIECE_Z, 0.5)


WINDMILL_HUB = (0.5, 0.66, PIECE_Z + 66)   # πού γυρίζουν τα φτερά του ανεμόμυλου, μέσα στο κελί


def windmill(surf, g):
    """Πέτρινος ανεμόμυλος με κόκκινη στέγη. Τα φτερά ζωγραφίζονται κάθε καρέ (windmill_sails)."""
    k = g.k
    bx, by = g.pt(0.5, 0.55, PIECE_Z)
    _shadow(surf, bx + 10 * k, by + 4 * k, 32 * k, 11 * k, 55)
    h = 60
    wb, wt = 27, 18                      # μισό πλάτος κάτω και πάνω
    wall = (228, 214, 186)
    front = [(bx - wb * k, by), (bx + wb * k, by), (bx + wt * k, by - h * k), (bx - wt * k, by - h * k)]
    side = [(bx + wb * k, by), (bx + (wb + 9) * k, by - 7 * k), (bx + (wt + 7) * k, by - (h + 5) * k),
            (bx + wt * k, by - h * k)]
    fill_poly(surf, shade(wall, 0.74), side, shade(wall, 0.5))
    fill_poly(surf, wall, front, shade(wall, 0.6))
    for i in range(4):                   # γραμμές από πέτρες
        yy = by - (10 + i * 12) * k
        f = (10 + i * 12) / h
        half = (wb + (wt - wb) * f) * k
        pygame.draw.line(surf, shade(wall, 0.86), (bx - half, yy), (bx + half, yy), max(1, round(k)))
    # πόρτα και παράθυρο
    fill_poly(surf, (140, 88, 52), [(bx - 6 * k, by), (bx + 6 * k, by), (bx + 6 * k, by - 16 * k),
                                     (bx - 6 * k, by - 16 * k)], (96, 60, 36))
    circle(surf, (140, 88, 52), (bx, by - 16 * k), 6 * k)
    circle(surf, WINDOW, (bx, by - 36 * k), 5 * k, (90, 90, 110))
    # κωνική στέγη
    roof = [(bx - (wt + 5) * k, by - (h - 2) * k), (bx + (wt + 9) * k, by - (h + 2) * k), (bx + 2 * k, by - (h + 30) * k)]
    fill_poly(surf, (206, 72, 58), roof, (140, 44, 36))
    fill_poly(surf, (232, 104, 84), [roof[0], (bx - 1 * k, by - (h - 1) * k), roof[2]])
    hx, hy = g.pt(*WINDMILL_HUB)
    pygame.draw.line(surf, (90, 70, 50), (bx + 2 * k, by - (h - 6) * k), (hx, hy), max(2, round(4 * k)))


def windmill_sails(surf, g, cell, angle):
    """Τα τέσσερα φτερά του ανεμόμυλου, γυρισμένα κατά angle (κάθε καρέ)."""
    u, v, z = WINDMILL_HUB
    hx, hy = g.pt(cell[0] + u, cell[1] + v, z)
    k = g.k
    L, w0, w1 = 42 * k, 3 * k, 12 * k
    for i in range(4):
        a = angle + i * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca
        pygame.draw.line(surf, (110, 80, 52), (hx, hy), (hx + ca * L, hy + sa * L), max(2, round(2.6 * k)))
        sail = [(hx + ca * L * 0.25 + px * w0, hy + sa * L * 0.25 + py * w0),
                (hx + ca * L + px * w1, hy + sa * L + py * w1),
                (hx + ca * L + px * 1.5 * k, hy + sa * L + py * 1.5 * k),
                (hx + ca * L * 0.25 + px * 1.5 * k, hy + sa * L * 0.25 + py * 1.5 * k)]
        fill_poly(surf, (255, 255, 252), sail, (120, 96, 72))
        for t in (0.45, 0.65, 0.85):     # το ξύλινο πλέγμα του πανιού
            a0 = (hx + ca * L * t + px * 1.5 * k, hy + sa * L * t + py * 1.5 * k)
            wt = w0 + (w1 - w0) * (t - 0.25) / 0.75
            a1 = (hx + ca * L * t + px * wt, hy + sa * L * t + py * wt)
            pygame.draw.aaline(surf, (170, 150, 128), a0, a1)
    circle(surf, (90, 70, 50), (hx, hy), 4.5 * k, (60, 44, 30))


# ----------------------------------------------------------- γρανάζια, μπάρα
def gear(surf, center, r, angle, color=GEAR, teeth=8):
    """Χρυσό γρανάζι που στέκεται όρθιο και κοιτάει προς εμάς."""
    cx, cy = center
    step = 2 * math.pi / teeth
    pts = []
    for t in range(teeth):
        for f, rr in ((0.0, 0.74), (0.14, 1.0), (0.44, 1.0), (0.58, 0.74), (0.79, 0.74)):
            a = angle + (t + f) * step
            pts.append((cx + r * rr * math.cos(a), cy + r * rr * math.sin(a)))
    dark = shade(color, 0.62)
    off = max(1.5, r * 0.14)
    fill_poly(surf, dark, [(x + off, y + off * 0.6) for x, y in pts], shade(color, 0.45))   # πάχος
    fill_poly(surf, color, pts, shade(color, 0.55))
    circle(surf, mix(color, (255, 255, 255), 0.45), (cx - r * 0.06, cy - r * 0.06), r * 0.52)
    circle(surf, color, (cx, cy), r * 0.42)
    circle(surf, dark, (cx, cy), r * 0.2, shade(color, 0.45))


def gear_icon(surf, center, r):
    gear(surf, center, r, 0.2)


BARRIER_POST = (-0.62, 1.9)        # η κολόνα της μπάρας, μπροστά από τη γραμμή, πριν από τον φορτιστή
BARRIER_REST = (-0.62, 1.07)       # το στήριγμα όπου ακουμπά η μπάρα όταν είναι κλειστή, πίσω από τη γραμμή
BARRIER_PIVOT_Z = PIECE_Z + 26
BARRIER_LEN = 0.86


def _barrier_angle(opened):
    ease = opened * opened * (3 - 2 * opened)
    return math.radians(84) * ease


def barrier_rest(surf, g, opened):
    """Η σκιά της μπάρας στο έδαφος και το στήριγμα πίσω από τη γραμμή (ζωγραφίζονται πριν από το R2)."""
    k = g.k
    PX, PY = BARRIER_POST
    RX, RY = BARRIER_REST
    a = _barrier_angle(opened)
    end = PY - 0.02 - BARRIER_LEN * math.cos(a)
    shadow = [g.pt(PX - 0.03, PY, PIECE_Z), g.pt(PX + 0.03, PY, PIECE_Z), g.pt(PX + 0.03, end, PIECE_Z),
              g.pt(PX - 0.03, end, PIECE_Z)]
    fill_poly(surf, (30, 30, 40, 60), shadow)
    zr = BARRIER_PIVOT_Z - 4
    slab(surf, g, RX - 0.05, RY - 0.04, RX + 0.05, RY + 0.04, PIECE_Z, PIECE_Z + 3, (120, 124, 134))
    slab(surf, g, RX - 0.022, RY - 0.02, RX + 0.022, RY + 0.02, PIECE_Z + 3, zr, (70, 74, 84))
    for dy in (-0.035, 0.035):           # το «δίχαλο» όπου κάθεται η μπάρα
        slab(surf, g, RX - 0.03, RY + dy - 0.012, RX + 0.03, RY + dy + 0.012, zr - 2, zr + 7, (250, 200, 40))


def barrier(surf, g, opened, got, total, time):
    """Η μπάρα του φορτιστή: ανοίγει (opened 0 -> 1) όταν το R2 μαζέψει όλα τα γρανάζια.

    Δίπλα της μια ταμπέλα δείχνει πόσα γρανάζια έχει το R2 (got/total).
    """
    k = g.k
    PX, PY = BARRIER_POST
    zp = BARRIER_PIVOT_Z
    # βάση και κουτί με το μοτέρ (κίτρινο με μαύρες ρίγες)
    slab(surf, g, PX - 0.08, PY - 0.06, PX + 0.08, PY + 0.06, PIECE_Z, PIECE_Z + 3, (120, 124, 134))
    slab(surf, g, PX - 0.06, PY - 0.045, PX + 0.06, PY + 0.045, PIECE_Z + 3, zp + 6, (250, 200, 40),
         (236, 186, 30), (196, 150, 20))
    for zz in (PIECE_Z + 8, PIECE_Z + 18):
        a, b = g.pt(PX - 0.06, PY + 0.045, zz), g.pt(PX + 0.06, PY + 0.045, zz + 5)
        pygame.draw.line(surf, (40, 40, 44), a, b, max(2, round(3 * k)))
    # ο βραχίονας: κλειστός πάει προς τα πίσω πάνω από τη γραμμή, ανοιχτός στέκεται όρθιος
    a = _barrier_angle(opened)
    L = BARRIER_LEN
    seg = 8
    pts = [g.pt(PX, PY - 0.02 - L * math.cos(a) * i / seg, zp + L * 62 * math.sin(a) * i / seg)
           for i in range(seg + 1)]
    w = max(3, round(7 * k))
    pygame.draw.lines(surf, (60, 30, 30), False, pts, w + 2)
    for i in range(seg):
        col = (226, 52, 46) if i % 2 == 0 else (255, 255, 255)
        pygame.draw.line(surf, col, pts[i], pts[i + 1], w)
    circle(surf, (226, 52, 46), pts[-1], w * 0.55, (60, 30, 30))
    circle(surf, (70, 72, 80), pts[0], 4 * k, (30, 30, 34))
    # λαμπάκι: κόκκινο όσο είναι κλειστή, πράσινο όταν ανοίξει
    lx, ly = g.pt(PX, PY, zp + 11)
    on = (90, 240, 120) if opened >= 1 else (255, 70, 60)
    if opened < 1 and int(time * 2.5) % 2:
        on = (150, 50, 46)
    pygame.gfxdraw.filled_circle(surf, round(lx), round(ly), round(9 * k), (*on, 70))
    circle(surf, on, (lx, ly), 4.2 * k, (40, 30, 30))
    # ταμπέλα με τα γρανάζια, αριστερά από την κολόνα (ώστε να μην την κρύβει ποτέ η μπάρα)
    sx, sy = g.pt(PX, PY, zp - 6)
    label = font(round(17 * k)).render(f"{got}/{total}", True, (60, 48, 20))
    bw, bh = label.get_width() + round(34 * k), round(28 * k)
    rect = pygame.Rect(0, 0, bw, bh)
    rect.midright = (round(sx - 14 * k), round(sy))
    pygame.draw.line(surf, (80, 84, 96), (rect.right - 2, sy), (sx - 4 * k, sy), max(2, round(3 * k)))
    done = got >= total
    pygame.draw.rect(surf, (226, 250, 228) if done else (255, 250, 232), rect, border_radius=round(8 * k))
    pygame.draw.rect(surf, (52, 160, 76) if done else (196, 150, 40), rect, max(2, round(2 * k)),
                     border_radius=round(8 * k))
    gear_icon(surf, (rect.x + 15 * k, rect.centery), 9 * k)
    surf.blit(label, label.get_rect(midleft=(rect.x + 27 * k, rect.centery + 1)))


def _bolt(surf, to_screen, color, outline):
    """Ο κεραυνός του φορτιστή. to_screen: (x, y) από 0 ως 1 -> σημείο στην οθόνη."""
    bolt = [(0.60, 0.10), (0.28, 0.56), (0.47, 0.56), (0.38, 0.90), (0.74, 0.40), (0.54, 0.40), (0.66, 0.10)]
    fill_poly(surf, color, [to_screen(x, y) for x, y in bolt], outline)


def charger_dock(surf, g):
    """Ο φορτιστής: το κουτί πίσω από τη γραμμή, με ταμπέλα και καλώδιο."""
    zf = 15
    slab(surf, g, -2.04, 0.08, -0.3, 0.94, 0, zf, (210, 200, 184))
    X0, X1, Y0, Y1, h = -1.95, -1.05, 0.22, 0.6, 58
    slab(surf, g, X0, Y0, X1, Y1, zf, zf + h, (238, 242, 246), (226, 232, 238), (186, 194, 206))
    # πράσινη οθόνη με κεραυνό στην μπροστινή πλευρά
    fill_poly(surf, (60, 170, 100), _quad_on_front(g, X0 + 0.16, X1 - 0.16, Y1, zf + 6, zf + 38), (36, 120, 70))

    def front(x, y):
        return g.pt(X0 + 0.22 + (X1 - X0 - 0.44) * x, Y1, zf + 35 - 26 * y)
    _bolt(surf, front, (255, 255, 255), (36, 120, 70))
    # ταμπέλα
    fill_poly(surf, (255, 255, 255), _quad_on_front(g, X0 + 0.04, X1 - 0.04, Y1, zf + 42, zf + 54), (40, 120, 70))
    lx, ly = g.pt((X0 + X1) / 2, Y1, zf + 48)
    label = font(round(10 * g.k)).render("ΦΟΡΤΙΣΤΗΣ", True, (30, 120, 70))
    surf.blit(label, label.get_rect(center=(lx, ly)))
    slab(surf, g, X0 - 0.03, Y0 - 0.03, X1 + 0.03, Y1 + 0.03, zf + h, zf + h + 5, (60, 170, 100))
    # καλώδιο ως τη βάση φόρτισης
    pts = [g.pt(-1.2, Y1, zf + 4), g.pt(-1.05, 0.8, zf + 1), g.pt(-1.05, 0.98, BOARD_Z + 2)]
    pygame.draw.lines(surf, (40, 44, 52), False, pts, max(2, round(4 * g.k)))
    # φανοστάτης
    slab(surf, g, -0.56, 0.7, -0.53, 0.73, zf, zf + 46, (60, 60, 70))
    x, y = g.pt(-0.545, 0.715, zf + 50)
    circle(surf, (255, 236, 140), (x, y), 5 * g.k, (120, 100, 40))


def charger_pad(surf, g):
    """Η βάση φόρτισης πάνω στη γραμμή: εδώ σταματά το R2 στο τέλος."""
    c, r = logic.CHARGER
    z = PIECE_Z
    slab(surf, g, c + 0.08, r + 0.08, c + 0.92, r + 0.92, z, z + 3, (84, 200, 124), (44, 150, 86), (36, 128, 72))
    fill_poly(surf, (118, 220, 152), [g.pt(c + 0.18, r + 0.18, z + 3), g.pt(c + 0.82, r + 0.18, z + 3),
                                      g.pt(c + 0.82, r + 0.82, z + 3), g.pt(c + 0.18, r + 0.82, z + 3)])
    _bolt(surf, lambda x, y: g.pt(c + 0.2 + 0.6 * x, r + 0.2 + 0.6 * y, z + 3), (255, 255, 255), (40, 140, 80))


def start_pad(surf, g):
    """Γαλάζιο πλακάκι στην αφετηρία, όπως η «ΑΡΧΗ» στον Λαβύρινθο."""
    c, r = logic.HOME
    z = PIECE_Z
    fill_poly(surf, (210, 230, 252), [g.pt(c + 0.08, r + 0.08, z), g.pt(c + 0.92, r + 0.08, z),
                                      g.pt(c + 0.92, r + 0.92, z), g.pt(c + 0.08, r + 0.92, z)], (150, 190, 236))
    line_piece(surf, g, c, r, logic.W, logic.E)
    lx, ly = g.pt(c + 0.62, r + 0.84, z)
    label = font(round(11 * g.k)).render("ΑΡΧΗ", True, (110, 150, 200))
    surf.blit(label, label.get_rect(center=(lx, ly)))


def signal(surf, g, green):
    X, Y = SIGNAL_POS
    slab(surf, g, X - 0.02, Y - 0.02, X + 0.02, Y + 0.02, 0, 64, (80, 80, 92))
    slab(surf, g, X - 0.08, Y - 0.03, X + 0.08, Y + 0.03, 58, 96, (44, 44, 52))
    for zz, on_col, off_col, on in ((86, (255, 70, 60), (110, 40, 40), not green),
                                    (69, (90, 255, 120), (40, 96, 54), green)):
        x, y = g.pt(X, Y + 0.03, zz)
        if on:
            pygame.gfxdraw.filled_circle(surf, round(x), round(y), round(11 * g.k), (*on_col, 80))
        circle(surf, on_col if on else off_col, (x, y), 5.5 * g.k, (20, 20, 20))


# ---------------------------------------------------------------------- R2
ROBOT_SIZE = 0.8      # το μήκος του R2, σε κελιά
Z_PER_CELL = 90       # pixels ύψους που αντιστοιχούν σε ένα κελί, για σωστές αναλογίες
WHEEL_R = 24 * ROBOT_SIZE / 100        # η ακτίνα της ρόδας, σε κελιά
WHEEL_HALF_TRACK = 36 * ROBOT_SIZE / 100   # από το κέντρο του R2 ως το κέντρο κάθε ρόδας, σε κελιά

# τα χρώματα του πραγματικού R2: μαύρο σασί, κίτρινα μοτέρ, λευκή πλακέτα polytech, διάφανο καπάκι
R2_TIRE, R2_GROOVE = (44, 46, 52), (26, 27, 32)
R2_RIM, R2_HOLE = (92, 96, 106), (30, 32, 38)
R2_CHASSIS = (34, 35, 40)
R2_MOTOR = (250, 200, 40)
R2_BATTERY = (30, 31, 36)
R2_BRASS = (214, 172, 76)
R2_PCB = (240, 242, 238)
R2_SOCKET = (36, 38, 44)
R2_BRACKET = (196, 200, 208)
R2_SENSOR = (44, 104, 196)
R2_EYE = (206, 210, 220)
R2_CABLE = (36, 84, 210)
R2_YELLOW, R2_RED, R2_GREEN, R2_BLUE = (250, 214, 40), (226, 52, 52), (52, 160, 76), (70, 170, 230)
# οι υποδοχές της πλακέτας: πίσω σειρά (προς τον αισθητήρα) και μπροστινή σειρά, (πάνω, κάτω) χρώμα
_PORTS_BACK = ((R2_YELLOW, R2_RED), (R2_GREEN, R2_GREEN), (R2_YELLOW, R2_RED), (R2_YELLOW, R2_RED))
_PORTS_FRONT = ((R2_BLUE, R2_YELLOW), (R2_BLUE, R2_YELLOW), (R2_BLUE, R2_YELLOW), (R2_BLUE, R2_YELLOW))


class _R2Model:
    """Το R2 ως μικρά τρισδιάστατα σχήματα (κουτιά και κύλινδροι) πάνω στο πλάγιο ταμπλό.

    Μονάδες 0-100: x από αριστερά προς τα δεξιά, y από μπροστά (0, ο αισθητήρας) προς τα πίσω (100),
    z προς τα πάνω. Κάθε σχήμα είναι κυρτό, οπότε φτάνει να ζωγραφιστούν οι πλευρές του που κοιτάνε
    προς εμάς. Τα σχήματα μπαίνουν από το πιο μακρινό στο πιο κοντινό.
    """

    def __init__(self, surf, g, X, Y, hx, hy, z):
        n = math.hypot(hx, hy) or 1.0
        self.fx, self.fy = hx / n, hy / n           # μπροστά
        self.sx, self.sy = -self.fy, self.fx        # δεξιά
        self.surf, self.g, self.X, self.Y, self.z = surf, g, X, Y, z
        self.u = ROBOT_SIZE / 100
        # η κατεύθυνση προς τον θεατή: όσο πιο θετικό το γινόμενο, τόσο πιο πολύ μας κοιτάει μια πλευρά
        self.view = (g.shift / g.tw, 1.0, g.th / (Z_PER_CELL * g.k))

    def facing(self, dx, dy, dz):
        a, b = -dy, dx
        wx, wy = self.fx * a + self.sx * b, self.fy * a + self.sy * b
        return wx * self.view[0] + wy * self.view[1] + dz * self.view[2]

    def P(self, x, y, z):
        a, b = (50 - y) * self.u, (x - 50) * self.u
        return self.g.pt(self.X + self.fx * a + self.sx * b, self.Y + self.fy * a + self.sy * b,
                         self.z + z * self.u * Z_PER_CELL)

    def face(self, col, pts, normal, outline=True):
        """Επίπεδη πλευρά: μόνο αν μας κοιτάει. Οι πλαϊνές σκουραίνουν όσο γυρίζουν μακριά."""
        f = self.facing(*normal)
        if f <= 0.002:
            return False
        light = 1.06 if normal[2] > 0.9 else 0.6 + 0.32 * min(1.0, f)
        pts = [self.P(*q) for q in pts]
        # γέμισμα χωρίς εξομάλυνση, για να μη μένουν χαραμάδες ανάμεσα σε γειτονικές πλευρές
        # (η εξομάλυνση γίνεται όταν μικραίνει η εικόνα στη draw_robot)
        pygame.draw.polygon(self.surf, shade(col, light), pts)
        if outline:
            pygame.draw.aalines(self.surf, shade(col, 0.42 if sum(col) > 150 else 0.3), True, pts)
        return True

    def box(self, col, x0, x1, y0, y1, z0, z1, top=None):
        self.face(col, [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0))
        self.face(col, [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0))
        self.face(col, [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0))
        self.face(col, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0))
        self.face(top or col, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1))

    @staticmethod
    def _at(axis, t, p, q):
        return (t, p, q) if axis == "x" else ((p, t, q) if axis == "y" else (p, q, t))

    def disc(self, axis, t, cp, cq, r, col, sign, outline=True, n=20):
        normal = self._at(axis, sign, 0, 0)
        pts = [self._at(axis, t, cp + r * math.cos(2 * math.pi * i / n), cq + r * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        return self.face(col, pts, normal, outline)

    def cylinder(self, axis, t0, t1, cp, cq, r, col, groove=None, n=22, phase=0.0):
        """Κύλινδρος κατά μήκος του άξονα. Επιστρέφει (θέση, πρόσημο) της βάσης που φαίνεται.

        phase: πόσο έχει γυρίσει (σε ακτίνια). Με groove, οι λωρίδες εναλλάσσονται και γυρίζουν μαζί του.
        """
        for i in range(n):
            a0, a1 = phase + 2 * math.pi * i / n, phase + 2 * math.pi * (i + 1) / n
            am = (a0 + a1) / 2
            quad = [self._at(axis, t, cp + r * math.cos(a), cq + r * math.sin(a))
                    for t, a in ((t0, a0), (t0, a1), (t1, a1), (t1, a0))]
            self.face(groove if groove and i % 2 else col, quad, self._at(axis, 0, math.cos(am), math.sin(am)),
                      outline=False)
        sign = 1 if self.facing(*self._at(axis, 1, 0, 0)) > 0 else -1
        end = t1 if sign > 0 else t0
        self.disc(axis, end, cp, cq, r, col, sign)
        return end, sign

    # ------------------------------------------------------------ κομμάτια
    def wheel(self, x0, x1, spin):
        """Μαύρη ρόδα. spin: πόσο έχει γυρίσει (ακτίνια, θετικά = κύλισμα προς τα μπροστά)."""
        end, sign = self.cylinder("x", x0, x1, 50, 24, 24, R2_TIRE, R2_GROOVE, n=24, phase=spin)
        self.disc("x", end, 50, 24, 15, R2_RIM, sign)
        for k in range(3):
            a = spin + k * 2 * math.pi / 3
            self.disc("x", end, 50 + 8.5 * math.cos(a), 24 + 8.5 * math.sin(a), 3.4, R2_HOLE, sign,
                      outline=False, n=10)
        self.disc("x", end, 50, 24, 3.6, (150, 154, 166), sign, n=10)

    def chassis(self):
        # κίτρινα μοτέρ κάτω από το σασί, δίπλα στις ρόδες
        for x0, x1 in ((21, 33), (67, 79)):
            self.box(R2_MOTOR, x0, x1, 36, 62, 6, 15)
        self.box(R2_CHASSIS, 18, 82, 8, 96, 15, 18)
        # θήκη μπαταριών πίσω, ανοιχτή από πάνω με τα ελατήρια
        self.box(R2_BATTERY, 30, 70, 64, 96, 18, 28, top=(52, 54, 62))
        for x in (36, 45.3, 54.6, 64):
            self.box((70, 72, 80), x - 2.8, x + 2.8, 67, 93, 28, 28.5)
            self.disc("z", 28.6, x, 92, 1.6, (200, 204, 214), 1, outline=False, n=8)

    def standoffs(self, z0, z1):
        for x, y in ((23, 21), (77, 21), (23, 61), (77, 61)):
            self.cylinder("z", z0, z1, x, y, 1.9, R2_BRASS, n=10)

    def board(self, led):
        """Η λευκή πλακέτα polytech με τις χρωματιστές υποδοχές, το USB, το LED."""
        self.standoffs(18, 32)
        self.box(R2_PCB, 20, 80, 17, 65, 32, 34)
        for row, y0 in ((_PORTS_BACK, 20), (_PORTS_FRONT, 53)):
            for i, (top, low) in enumerate(row):
                x0 = 23 + i * 11.5
                self.box(R2_SOCKET, x0, x0 + 9.5, y0, y0 + 9, 34, 40)
                self.box(top, x0 + 0.5, x0 + 9, y0 + 0.5, y0 + 4.5, 40, 40.6)
                self.box(low, x0 + 0.5, x0 + 9, y0 + 4.5, y0 + 8.5, 40, 40.6)
        self.box((206, 210, 218), 70, 78, 52, 63, 34, 39)          # USB
        self.box((48, 48, 56), 44, 54, 37, 45, 34, 35.5)           # τσιπ
        self.cylinder("z", 34, 38, 32, 43, 3.6, (40, 40, 46), n=12)  # βομβητής
        self.disc("z", 35, 68, 41, 4.6, (255, 255, 255), 1, n=14)
        self.cylinder("z", 34, 39, 68, 41, 3.4, led, n=14)
        self.disc("z", 39, 67, 40, 1.1, (255, 255, 255), 1, outline=False, n=8)

    def cover(self):
        """Το διάφανο ακρυλικό καπάκι πάνω από την πλακέτα, με τις χρυσές κολόνες και τις βίδες."""
        self.standoffs(34, 46)
        pts = [self.P(x, y, 46) for x, y in ((18, 15), (82, 15), (82, 67), (18, 67))]
        # σε δικό του στρώμα, για να ανακατευτεί με ό,τι είναι από κάτω (το blit κάνει ανάμειξη)
        glass = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(glass, (220, 236, 255, 46), pts)
        pygame.draw.aalines(glass, (255, 255, 255, 220), True, pts)
        self.surf.blit(glass, (0, 0))
        for x, y in ((23, 21), (77, 21), (23, 61), (77, 61)):
            self.disc("z", 46.2, x, y, 1.8, (196, 200, 210), 1, outline=False, n=8)

    def cable(self):
        """Το μπλε πλακέ καλώδιο: από τον αισθητήρα κάνει καμπύλη ψηλά και κατεβαίνει στην πλακέτα."""
        pts = []
        for k in range(17):
            t = k / 16
            y = (1 - t) ** 3 * 11 + 3 * (1 - t) ** 2 * t * 16 + 3 * (1 - t) * t * t * 30 + t ** 3 * 25
            z = (1 - t) ** 3 * 38 + 3 * (1 - t) ** 2 * t * 78 + 3 * (1 - t) * t * t * 74 + t ** 3 * 41
            pts.append(self.P(49 + 4 * t, y, z))
        pygame.draw.lines(self.surf, R2_CABLE, False, pts, max(2, round(3.4 * self.g.k)))

    def sensor(self, front_near):
        """Μπροστά: γκρι μεταλλική βάση και πάνω της ο αισθητήρας απόστασης με τα δύο «μάτια»."""
        eyes = sorted((38, 62), key=lambda x: self.facing(1, 0, 0) * x)
        bracket = lambda: (self.box(R2_BRACKET, 26, 74, 6, 9, 15, 46),
                           self.box((40, 42, 48), 45, 55, 9, 13, 30, 38, top=R2_YELLOW))
        if not front_near:
            for ex in eyes:
                self.cylinder("y", -6, 1, ex, 31, 8.6, R2_EYE)
            self.box(R2_SENSOR, 27, 73, 1, 6, 20, 42)
            bracket()
            return
        bracket()
        self.box(R2_SENSOR, 27, 73, 1, 6, 20, 42)
        for ex in eyes:
            self.cylinder("y", -6, 1, ex, 31, 8.6, R2_EYE)
            self.disc("y", -6, ex, 31, 7.4, (214, 220, 232), -1, outline=False)
            self.disc("y", -6, ex, 31, 5.6, (150, 158, 176), -1, outline=False)
            self.disc("y", -6, ex, 31, 3.8, (60, 64, 76), -1, outline=False, n=14)
            self.disc("y", -6, ex - 2.4, 33.6, 1.4, (255, 255, 255), -1, outline=False, n=8)

    def draw(self, led, spin):
        shadow = [self.P(50 + 50 * math.cos(a), 51 + 50 * math.sin(a), 0)
                  for a in (2 * math.pi * i / 24 for i in range(24))]
        fill_poly(self.surf, (20, 30, 50, 45), shadow)
        front_near = self.facing(0, -1, 0) > 0
        wheels = [(5, 19, spin[0]), (81, 95, spin[1])]
        if self.facing(1, 0, 0) <= 0:
            wheels.reverse()                       # πρώτα η ρόδα που είναι πιο μακριά
        self.wheel(*wheels[0])
        if not front_near:
            self.sensor(False)
        self.chassis()
        self.board(led)
        self.cover()
        if not front_near:
            self.cable()
        self.wheel(*wheels[1])
        if front_near:
            self.cable()
            self.sensor(True)


def draw_robot(surf, g, X, Y, hx, hy, led=r2.LED_BLUE, z=PIECE_Z, spin=(0.0, 0.0)):
    """Το R2 στη θέση (X, Y) του ταμπλό, να κοιτάει προς (hx, hy). Επιστρέφει το κέντρο του στην οθόνη.

    spin: πόσο έχει γυρίσει η αριστερή και η δεξιά ρόδα (ακτίνια).
    Ζωγραφίζεται σε διπλό μέγεθος σε μια μικρή εικόνα και μικραίνει, για λεία περιγράμματα.
    """
    cx, cy = g.pt(X, Y, z + 0.2 * Z_PER_CELL * ROBOT_SIZE)
    half = math.ceil(g.tw * 0.72)
    size = 2 * half
    tmp = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
    ox, oy = round(cx) - half, round(cy) - half
    big = Geo(0, 0, g.tw, g.shift, g.th).scaled(SS, (g.ox - ox) * SS, (g.oy - oy) * SS)
    _R2Model(tmp, big, X, Y, hx, hy, z).draw(led, spin)
    surf.blit(pygame.transform.smoothscale(tmp, (size, size)), (ox, oy))
    return cx, cy


# -------------------------------------------------------------- background
DECOR = (
    ("tree", -1.1, -0.6, 0.9), ("pine", 0.9, -0.62, 1.0), ("tree", 2.4, -0.72, 1.1),
    ("pine", 3.7, -0.55, 0.9), ("bush", 4.6, -0.3, 1.0), ("tree", 5.6, -0.42, 1.0),
    ("pine", 7.1, 0.45, 1.1), ("tree", 8.1, 1.6, 1.0), ("bush", 7.9, 2.9, 1.1),
    ("tree", -2.9, 2.7, 1.1), ("pine", -1.7, 3.5, 0.9), ("bush", -3.3, 0.9, 1.0),
    ("tree", 7.4, 4.45, 1.0), ("bush", 0.2, 4.7, 1.0), ("bush", 3.6, 4.75, 0.9),
)
_DECOR_FN = {"tree": tree, "pine": pine, "bush": bush}


def build_background(geo, size):
    W, H = size
    big = pygame.Surface((W * SS, H * SS))
    g = geo.scaled(SS, geo.ox * SS, geo.oy * SS)
    horizon = 132 * SS
    for y in range(horizon):
        pygame.draw.line(big, mix(SKY_TOP, SKY_LOW, y / horizon), (0, y), (W * SS, y))
    for col, base, amp, per, ph in (((164, 212, 132), 118, 16, 420, 0.5), ((140, 200, 108), 132, 10, 270, 2.0)):
        pts = [(x * SS, (base + amp * math.sin(x / per * 2 * math.pi + ph)) * SS) for x in range(0, W + 21, 20)]
        pygame.draw.polygon(big, col, pts + [(W * SS, H * SS), (0, H * SS)])
    pygame.draw.rect(big, GRASS, (0, 142 * SS, W * SS, H * SS))
    rng = random.Random(11)
    for _ in range(1500):
        x, y = rng.uniform(0, W), rng.uniform(146, H)
        c = GRASS_DARK if rng.random() < 0.6 else GRASS_LIGHT
        pygame.draw.line(big, c, (x * SS, y * SS), ((x + rng.uniform(-2, 2)) * SS, (y - rng.uniform(3, 6)) * SS), SS)
    for _ in range(80):
        x, y = rng.uniform(0, W), rng.uniform(150, H)
        c = rng.choice(((255, 255, 255), (250, 210, 230), (255, 230, 120), (200, 190, 255)))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            pygame.draw.circle(big, c, ((x + dx) * SS, (y + dy) * SS), 2 * SS)
        pygame.draw.circle(big, (250, 200, 60), (x * SS, y * SS), 1.5 * SS)

    behind = [d for d in DECOR if d[2] < 1]
    front = [d for d in DECOR if d[2] >= 1]
    for kind, X, Y, s in sorted(behind, key=lambda d: d[2]):
        _DECOR_FN[kind](big, g, X, Y, 0, s)
    charger_dock(big, g)
    # σταθερές γραμμές: προς τον φορτιστή (αριστερά) και η αφετηρία (δεξιά)
    sr, er = logic.START_ROW, logic.END_ROW
    slab(big, g, -2.06, er - 0.06, -0.1, er + 1.06, 0, BOARD_Z, WOOD_TOP, WOOD_FRONT, WOOD_SIDE)
    slab(big, g, -0.1, -0.1, logic.COLS + 0.1, logic.ROWS + 0.1, 0, BOARD_Z, WOOD_TOP, WOOD_FRONT, WOOD_SIDE)
    slab(big, g, logic.COLS + 0.1, sr - 0.06, logic.COLS + 2.06, sr + 1.06, 0, BOARD_Z, WOOD_TOP, WOOD_FRONT, WOOD_SIDE)
    for c in range(logic.COLS):
        for r in range(logic.ROWS):
            hole(big, g, c, r)
    for cell in sorted(logic.FIXED_LINE):
        piece_tile(big, g, 6, cell[0], cell[1], fixed=True)
    charger_pad(big, g)
    start_pad(big, g)
    for kind, X, Y, s in sorted(front, key=lambda d: d[2]):
        _DECOR_FN[kind](big, g, X, Y, 0, s)
    return pygame.transform.smoothscale(big, size)


class LineAssets:
    """Όλες οι έτοιμες εικόνες του παιχνιδιού, φτιαγμένες μία φορά."""

    def __init__(self, geo, size):
        self.geo = geo
        self.background = build_background(geo, size)
        pad = 14
        self.tile_anchor = (geo.shift + pad, pad + PIECE_Z)
        tw, th = geo.tw + geo.shift + 2 * pad, geo.th + PIECE_Z + 2 * pad
        self.pieces = {}
        self.ghosts = {}
        self.tray = {}
        self.tray_dim = {}
        for t in logic.PIECE_TYPES:
            draw = lambda s, g, t=t: piece_tile(s, g, t)
            self.pieces[t] = render(geo, tw, th, self.tile_anchor, draw)
            ghost = self.pieces[t].copy()
            ghost.set_alpha(150)
            self.ghosts[t] = ghost
            self.tray[t] = render(geo, tw, th, self.tile_anchor, draw, scale=0.78)
            dim = self.tray[t].copy()
            dim.set_alpha(55)
            self.tray_dim[t] = dim
        self.grass = render(geo, tw, th, self.tile_anchor, grass_tile)
        self.obj_anchor = (geo.shift + 40, 130)
        ow, oh = geo.tw + geo.shift + 80, 130 + geo.th + 30
        self.objects = {kind: render(geo, ow, oh, self.obj_anchor, lambda s, g, kind=kind: block_object(s, g, kind))
                        for kind in BLOCK_KINDS + NEW_KINDS}
        # σταθερά κομμάτια (το 7 είναι η διασταύρωση) και γέφυρες
        self.fixed = {t: render(geo, tw, th, self.tile_anchor, lambda s, g, t=t: fixed_tile(s, g, t))
                      for t in logic.PIECE_TYPES + (logic.CROSS,)}
        self.bridges = {t: render(geo, tw, th, self.tile_anchor, lambda s, g, t=t: bridge_tile(s, g, t))
                        for t in (5, 6)}
        self.signal = {state: render(geo, ow, oh, self.obj_anchor, lambda s, g, state=state: signal(s, g, state))
                       for state in (False, True)}


_cache = {}


def get_assets(geo, size):
    key = (geo.ox, geo.oy, geo.tw, geo.shift, geo.th, size)
    if key not in _cache:
        _cache[key] = LineAssets(geo, size)
    return _cache[key]


def get_river(geo, size, water):
    key = ("river", geo.ox, geo.oy, geo.tw, geo.shift, geo.th, size, tuple(sorted(water)))
    if key not in _cache:
        _cache[key] = river_layer(geo, size, water)
    return _cache[key]
