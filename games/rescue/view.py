"""Η ζωγραφική του δάσους: κυβάκια όπως στο «Προγραμμάτισε» (games/program/art.py), με την ίδια πλάγια
προβολή (Geo) και το ίδιο R2.

- ForestView: ένα «παράθυρο» στο δάσος (όλο το δάσος, ένα ποτάμι ή ένα οικόπεδο) μέσα σε ένα ορθογώνιο.
  Ό,τι δεν κουνιέται (ουρανός, έδαφος, νερό, αυλάκια, γεφυράκια, πεντάλ) ζωγραφίζεται μία φορά σε μια
  εικόνα. Δέντρα, φράχτες, πέτρες, ζώα, R2, φωτιές και κλαδιά μπαίνουν σε κάθε καρέ με τη σειρά βάθους.
- Tracker: η ομαλή κίνηση. Το δάσος (sim.Forest) αλλάζει κουτάκι-κουτάκι· ο Tracker κάνει τα R2, τα ζώα,
  τις πέτρες και τα κλαδιά να γλιστρούν από το ένα κουτάκι στο άλλο.
Οι εικόνες (sprites) φτιάχνονται μία φορά για κάθε μέγεθος κύβου και φυλάγονται.
"""
import math
import random

import pygame

from core import ui
from games.line_follow import art as lf
from games.maze import art as r2art
from games.program import art as A
from . import fire as FI
from . import sim as S
from . import world as W

cube, CUBE = A.cube, A.CUBE
PLOT_COLS = [(232, 84, 84), (62, 132, 222), (238, 146, 46), (150, 104, 206), (40, 170, 120)]
TEAM_COLS = [(0, 150, 160), (88, 96, 200), (176, 110, 60), (200, 76, 140), (96, 140, 40), (120, 110, 130),
             (40, 120, 200)]
FENCE_POST, FENCE_RAIL = (120, 86, 54), (196, 150, 92)
STONE_COL, STONE_TOP = (196, 192, 184), (214, 210, 202)
WATER = (66, 146, 232)


def robot_color(forest, k):
    p = forest.plots[k]
    team = forest.data["teams"][p["team"]]
    return PLOT_COLS[team["plots"].index(k) % len(PLOT_COLS)]


def fit_box(rect, box, top=2.2, bottom=2.4, strip=0, maxtw=104.0, margin=40):
    """Μια Geo ώστε τα κουτάκια box = (x0, y0, x1, y1) να χωρούν όσο πιο μεγάλα στο rect."""
    r = pygame.Rect(rect)
    x0, y0, x1, y1 = box
    cols, rows = x1 - x0, y1 - y0
    avail = r.h - strip - 16
    tw = min(maxtw, (r.w - margin) / (cols + rows * 0.46))
    while True:
        k = tw / 104
        h = top * CUBE * k + rows * tw * 0.8 + bottom * CUBE * k
        if h <= avail or tw < 6:
            break
        tw -= 0.5
    k = tw / 104
    w = cols * tw + rows * tw * 0.46
    ox = r.centerx - w / 2 + rows * tw * 0.46
    oy = r.y + 8 + (avail - h) / 2 + top * CUBE * k
    shift, th = tw * 0.46, tw * 0.8
    return lf.Geo(ox - x0 * tw + y0 * shift, oy - y0 * th, tw, shift, th)


# ================================================================ ζώα (από κουτάκια)
def _box(s, g, cx, cy, ax, ay, z0, z1, col, n=2):
    cube(s, g, 0, 0, z0, z1, col, 1, cx - ax, cx + ax, cy - ay, cy + ay, n=n)


def _vox(s, g, X, Y, hx, hy, parts, scale=1.0):
    items = []
    for fwd, side, L, Wd, z0, z1, col in parts:
        fwd, side, L, Wd = fwd * scale, side * scale, L * scale, Wd * scale
        wx, wy = X + hx * fwd - hy * side, Y + hy * fwd + hx * side
        ax, ay = (L, Wd) if hx else (Wd, L)
        items.append((z0 * scale, wx * 0.46 + wy, (wx, wy, ax, ay, z0 * scale, z1 * scale, col)))
    items.sort(key=lambda it: (round(it[0] / 6), it[1]))
    for _, _, p in items:
        _box(s, g, *p)


def _shadow(s, g, X, Y, r):
    x, y = g.pt(X, Y, 0)
    lf._shadow(s, x, y, r * g.tw, r * g.tw * 0.42, 55)


def draw_animal(s, g, kind, X, Y, hx, hy):
    if kind in ("rabbit",):
        sc = 1.35
        _shadow(s, g, X, Y, 0.2 * sc)
        c, d, w = (226, 214, 196), (188, 172, 150), (250, 250, 248)
        _vox(s, g, X, Y, hx, hy, [
            (0.09, 0.06, 0.03, 0.025, 0, 6, d), (0.09, -0.06, 0.03, 0.025, 0, 6, d),
            (-0.08, 0.07, 0.05, 0.03, 0, 6, d), (-0.08, -0.07, 0.05, 0.03, 0, 6, d),
            (0, 0, 0.15, 0.11, 4, 22, c), (-0.16, 0, 0.04, 0.04, 10, 18, w),
            (0.15, 0, 0.08, 0.08, 14, 32, c),
            (0.13, 0.045, 0.02, 0.025, 32, 50, c), (0.13, -0.045, 0.02, 0.025, 32, 50, c)], sc)
    elif kind in ("deer", "fawn"):
        sc = 1.0 if kind == "deer" else 0.72
        _shadow(s, g, X, Y, 0.3 * sc)
        b, d, w, k = (182, 118, 64), (124, 80, 46), (246, 240, 228), (40, 30, 26)
        parts = [(0.17, 0.07, 0.03, 0.03, 0, 28, d), (0.17, -0.07, 0.03, 0.03, 0, 28, d),
                 (-0.17, 0.07, 0.03, 0.03, 0, 28, d), (-0.17, -0.07, 0.03, 0.03, 0, 28, d),
                 (0, 0, 0.25, 0.1, 28, 48, b), (-0.26, 0, 0.03, 0.035, 40, 48, w),
                 (0.05, 0.04, 0.025, 0.025, 48, 50, w), (-0.1, -0.03, 0.025, 0.025, 48, 50, w),
                 (0.21, 0, 0.06, 0.05, 44, 64, b), (0.29, 0, 0.09, 0.06, 58, 72, b), (0.38, 0, 0.02, 0.03, 60, 66, k),
                 (0.25, 0.065, 0.02, 0.03, 70, 78, b), (0.25, -0.065, 0.02, 0.03, 70, 78, b)]
        if kind == "deer":
            parts += [(0.27, 0.04, 0.012, 0.012, 72, 92, d), (0.27, -0.04, 0.012, 0.012, 72, 92, d),
                      (0.27, 0.075, 0.012, 0.035, 88, 92, d), (0.27, -0.075, 0.012, 0.035, 88, 92, d),
                      (0.31, 0.04, 0.03, 0.012, 82, 86, d), (0.31, -0.04, 0.03, 0.012, 82, 86, d)]
        _vox(s, g, X, Y, hx, hy, parts, sc)
    else:
        sc = 1.15 if kind == "fox" else 0.8
        _shadow(s, g, X, Y, 0.25 * sc)
        o, d, w, k = (236, 124, 38), (196, 92, 26), (250, 246, 238), (44, 36, 34)
        _vox(s, g, X, Y, hx, hy, [
            (0.12, 0.06, 0.025, 0.025, 0, 14, k), (0.12, -0.06, 0.025, 0.025, 0, 14, k),
            (-0.12, 0.06, 0.025, 0.025, 0, 14, k), (-0.12, -0.06, 0.025, 0.025, 0, 14, k),
            (0, 0, 0.18, 0.08, 14, 30, o), (-0.27, 0, 0.1, 0.05, 18, 28, o), (-0.39, 0, 0.03, 0.05, 18, 28, w),
            (0.22, 0, 0.08, 0.07, 22, 38, o), (0.31, 0, 0.03, 0.04, 23, 30, w),
            (0.21, 0.045, 0.02, 0.02, 38, 47, d), (0.21, -0.045, 0.02, 0.02, 38, 47, d)], sc)


def heart(s, center, r, col=(240, 72, 96)):
    x, y = center
    pygame.draw.circle(s, col, (round(x - r * 0.5), round(y - r * 0.2)), max(1, round(r * 0.55)))
    pygame.draw.circle(s, col, (round(x + r * 0.5), round(y - r * 0.2)), max(1, round(r * 0.55)))
    ui.fill_poly(s, col, [(x - r * 1.02, y - r * 0.05), (x + r * 1.02, y - r * 0.05), (x, y + r * 1.05)])


# ================================================================ αντικείμενα του χάρτη
def _stone(s, g, x, y):
    cube(s, g, x, y, 0, CUBE * 0.42, STONE_COL, 3, 0.14, 0.86, 0.14, 0.86, n=5)
    cube(s, g, x, y, CUBE * 0.42, CUBE * 0.62, STONE_TOP, 4, 0.24, 0.76, 0.24, 0.76, n=4)


def _crossing(s, g, x, y):
    cube(s, g, x, y, -16, -2, STONE_COL, 3, 0.1, 0.9, 0.12, 0.88, n=5)


def _dam(s, g, x, y):
    cube(s, g, x, y, -2, CUBE * 0.42, STONE_COL, 3, 0.17, 0.83, 0.17, 0.83, n=4)
    cube(s, g, x, y, CUBE * 0.42, CUBE * 0.56, STONE_TOP, 4, 0.27, 0.73, 0.27, 0.73, n=3)


def _big_half(s, g, d):
    """Το μισό του μεγάλου βράχου: φτάνει ως την άκρη του κουτακιού προς τη μεριά d (εκεί είναι το άλλο μισό)."""
    u0, u1, v0, v1 = 0.06, 0.94, 0.1, 0.9
    if d == W.RIGHT:
        u1 = 1.0
    elif d == W.LEFT:
        u0 = 0.0
    elif d == W.DOWN:
        v1 = 1.0
    else:
        v0 = 0.0
    cube(s, g, 0, 0, 0, CUBE * 0.92, "stone", 21, u0, u1, v0, v1, n=6)
    a0, a1, b0, b1 = u0 + 0.1, u1 - 0.1, v0 + 0.1, v1 - 0.1
    if d == W.RIGHT:
        a1 = 1.0
    elif d == W.LEFT:
        a0 = 0.0
    elif d == W.DOWN:
        b1 = 1.0
    else:
        b0 = 0.0
    cube(s, g, 0, 0, CUBE * 0.92, CUBE * 1.18, "stone", 23, a0, a1, b0, b1, n=4)


def _black_line(s, g, line, w=0.12):
    """Η μαύρη γραμμή στο έδαφος (για τον αισθητήρα γραμμής), από κέντρο σε κέντρο."""
    col, edge = (36, 36, 44), (70, 70, 80)
    pts = [(c[0] + 0.5, c[1] + 0.5) for c in line]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        x0, x1 = min(ax, bx) - w, max(ax, bx) + w
        y0, y1 = min(ay, by) - w, max(ay, by) + w
        pygame.draw.polygon(s, edge, _quad(g, x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02, 1))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        x0, x1 = min(ax, bx) - w, max(ax, bx) + w
        y0, y1 = min(ay, by) - w, max(ay, by) + w
        pygame.draw.polygon(s, col, _quad(g, x0, y0, x1, y1, 1))


def _bush(s, g, v):
    """Χαμηλός θάμνος (στη λωρίδα δάσους μπροστά από ένα οικόπεδο, για να φαίνεται η κάτω σειρά του)."""
    cube(s, g, 0, 0, 0, CUBE * 0.42, "leaf", v * 5 + 3, 0.1, 0.9, 0.1, 0.9, n=5)
    cube(s, g, 0, 0, CUBE * 0.42, CUBE * 0.62, "leaf", v * 5 + 4, 0.26, 0.74, 0.26, 0.74, n=3)


def _rock(s, g, x, y):
    cube(s, g, x, y, 0, CUBE, "stone", 5 + x)


def _spring(s, g, x, y):
    cube(s, g, x, y, 0, CUBE * 1.35, "stone", 12)
    cube(s, g, x, y, CUBE * 1.35, CUBE * 1.5, "grass", 12, 0.1, 0.9, 0.1, 0.9, n=4)


def _sign(s, g, x, y):
    cube(s, g, 0, 0, 0, 50, FENCE_POST, 3, x + 0.46, x + 0.54, y + 0.46, y + 0.54, n=2)
    cube(s, g, 0, 0, 30, 62, (214, 176, 116), 3, x + 0.16, x + 0.84, y + 0.5, y + 0.56, n=3)
    heart(s, g.pt(x + 0.5, y + 0.56, 46), max(3, g.tw * 0.11))


def _fence_v(s, g, X, y):
    for z0, z1 in ((13, 19), (24, 29)):
        cube(s, g, 0, 0, z0, z1, FENCE_RAIL, 4, X - 0.025, X + 0.025, y, y + 1, n=2)
    for v in (0.08, 0.5, 0.92):
        cube(s, g, 0, 0, 0, 34, FENCE_POST, 5, X - 0.04, X + 0.04, y + v - 0.04, y + v + 0.04, n=2)


def _fence_h(s, g, x, Y):
    for z0, z1 in ((13, 19), (24, 29)):
        cube(s, g, 0, 0, z0, z1, FENCE_RAIL, 4, x, x + 1, Y - 0.025, Y + 0.025, n=2)
    for u in (0.08, 0.5, 0.92):
        cube(s, g, 0, 0, 0, 34, FENCE_POST, 5, x + u - 0.04, x + u + 0.04, Y - 0.04, Y + 0.04, n=2)


def _stump(s, g, X, Y):
    cube(s, g, 0, 0, 0, 12, "stone", 7, X - 0.2, X + 0.2, Y - 0.2, Y + 0.2, n=3)
    cube(s, g, 0, 0, 0, 26, (110, 82, 54), 6, X - 0.13, X + 0.13, Y - 0.13, Y + 0.13, n=3)


def beam(s, g, a, za, b, zb, w=0.14, t=15, axis="x"):
    """Το κλαδί από το σημείο a (ύψος za) ως το b (ύψος zb). axis: κατά μήκος ποιου άξονα."""
    (ax, ay), (bx, by) = a, b
    if axis == "x":
        if ax > bx:
            (ax, ay, za), (bx, by, zb) = (bx, by, zb), (ax, ay, za)
        top = [g.pt(ax, ay - w, za + t), g.pt(bx, by - w, zb + t), g.pt(bx, by + w, zb + t), g.pt(ax, ay + w, za + t)]
        front = [g.pt(ax, ay + w, za + t), g.pt(bx, by + w, zb + t), g.pt(bx, by + w, zb), g.pt(ax, ay + w, za)]
        end = [g.pt(bx, by - w, zb + t), g.pt(bx, by + w, zb + t), g.pt(bx, by + w, zb), g.pt(bx, by - w, zb)]
    else:
        if ay > by:
            (ax, ay, za), (bx, by, zb) = (bx, by, zb), (ax, ay, za)
        top = [g.pt(ax - w, ay, za + t), g.pt(ax + w, ay, za + t), g.pt(bx + w, by, zb + t), g.pt(bx - w, by, zb + t)]
        front = [g.pt(bx - w, by, zb + t), g.pt(bx + w, by, zb + t), g.pt(bx + w, by, zb), g.pt(bx - w, by, zb)]
        end = [g.pt(ax + w, ay, za + t), g.pt(bx + w, by, zb + t), g.pt(bx + w, by, zb), g.pt(ax + w, ay, za)]
    ui.fill_poly(s, (108, 78, 50), front, (60, 44, 30))
    ui.fill_poly(s, (92, 66, 42), end, (60, 44, 30))
    ui.fill_poly(s, (156, 116, 74), top, (60, 44, 30))


class Sprites:
    """Οι εικόνες για ένα μέγεθος κύβου (tw). Κάθε εικόνα: (εικόνα, μετατόπιση από τη γωνία του κουτακιού)."""
    _all = {}

    @classmethod
    def get(cls, tw):
        key = round(tw, 1)
        if key not in cls._all:
            cls._all[key] = Sprites(key)
        return cls._all[key]

    def __init__(self, tw):
        self.tw = tw
        self.cache = {}

    def _make(self, draw, wide=4.0, tall=7.0):
        tw = self.tw
        g = lf.Geo(tw * 1.6 + 20, tw * 4.8 + 30, tw, tw * 0.46, tw * 0.8)
        surf = pygame.Surface((int(tw * wide) + 60, int(tw * tall) + 60), pygame.SRCALPHA)
        draw(surf, g)
        box = surf.get_bounding_rect()
        if not box.w or not box.h:
            return pygame.Surface((1, 1), pygame.SRCALPHA), (0, 0)
        ox, oy = g.pt(0, 0, 0)
        return surf.subsurface(box).copy(), (box.x - ox, box.y - oy)

    def item(self, key, draw, **kw):
        if key not in self.cache:
            self.cache[key] = self._make(draw, **kw)
        return self.cache[key]

    def tree(self, v):
        return self.item(("tree", v), lambda s, g: A.tree(s, g, 0, 0) if v == 0 else _tree_var(s, g, v))

    def rock(self, v):
        return self.item(("rock", v), lambda s, g: cube(s, g, 0, 0, 0, CUBE, "stone", 5 + v))

    def robot(self, angle, led):
        a = round(angle / 10) * 10 % 360
        key = ("r2", a, led)

        def draw(s, g):
            rad = math.radians(a)
            lf.draw_robot(s, g, 0.5, 0.5, math.cos(rad), math.sin(rad), led=led, z=0)
        return self.item(key, draw)

    def animal(self, kind, face):
        hx, hy = W.DX[face], W.DY[face]
        return self.item(("an", kind, face), lambda s, g: draw_animal(s, g, kind, 0.5, 0.5, hx, hy))


def _tree_var(s, g, v):
    """Λίγο διαφορετικά δέντρα (για να μη μοιάζουν όλα ίδια)."""
    seed = v * 7
    h = (0.95, 1.05, 0.88, 1.12)[v % 4]
    cube(s, g, 0, 0, 0, CUBE * 0.95 * h, "bark", seed, 0.38, 0.62, 0.38, 0.62, n=4)
    cube(s, g, 0, 0, CUBE * 0.7 * h, CUBE * 1.55 * h, "leaf", seed, 0.06, 0.94, 0.06, 0.94, n=8)
    cube(s, g, 0, 0, CUBE * 1.55 * h, CUBE * 1.95 * h, "leaf", seed + 1, 0.26, 0.74, 0.26, 0.74, n=4)


# ================================================================ ομαλή κίνηση
class Tracker:
    def __init__(self, forest):
        self.f = forest
        self.rob = {}
        self.stone = {}
        self.ani = {}
        self.arm = {}
        self.fire_out = {}
        self.bumps = {}
        self.splash = []
        self.sync(0.0, first=True)

    @staticmethod
    def _ang(face):
        return face * 90.0 - 90.0

    def sync(self, now, first=False):
        f = self.f
        for k, r in f.robots.items():
            tgt = (r["pos"][0] + 0.5, r["pos"][1] + 0.5, self._ang(r["face"]))
            cur = self.rob.get(k)
            if first or cur is None:
                self.rob[k] = {"from": tgt, "to": tgt, "t0": now, "dur": 0.0}
            elif cur["to"] != tgt:
                pose = self.robot(k, now)
                to = list(tgt)
                d = (to[2] - pose[2] + 180) % 360 - 180
                to[2] = pose[2] + d
                moved = (round(to[0] - pose[0], 3), round(to[1] - pose[1], 3)) != (0, 0)
                self.rob[k] = {"from": pose, "to": tuple(to), "t0": now, "dur": S.STEP if moved else S.TURN,
                               "key": tgt}
                if abs(to[0] - pose[0]) + abs(to[1] - pose[1]) > 1.6:
                    self.rob[k]["dur"] = 0.0              # «Ξανά»: πηδά στην αρχή
            if self.rob[k].get("key") is None:
                self.rob[k]["key"] = tgt
            if self.rob[k]["key"] != tgt:
                self.rob[k]["key"] = tgt
        for i, s in enumerate(f.stones):
            tgt = (s["pos"][0] + 0.5, s["pos"][1] + 0.5)
            cur = self.stone.get(i)
            if first or cur is None or abs(tgt[0] - cur["to"][0]) + abs(tgt[1] - cur["to"][1]) > 1.5:
                self.stone[i] = {"from": tgt, "to": tgt, "t0": now}
            elif cur["to"] != tgt:
                self.stone[i] = {"from": self.stone_pos(i, now), "to": tgt, "t0": now}
        for i, a in enumerate(f.animals):
            tgt = (a["pos"][0] + 0.5, a["pos"][1] + 0.5)
            cur = self.ani.get(i)
            if first or cur is None:
                self.ani[i] = {"from": tgt, "to": tgt, "t0": now, "face": a["face"]}
            elif cur["to"] != tgt:
                self.ani[i] = {"from": self.animal_pos(i, now)[:2], "to": tgt, "t0": now, "face": a["face"]}
            else:
                cur["face"] = a["face"]
        for i, s in enumerate(f.seesaws):
            cur = self.arm.get(i)
            v = 1.0 if s["up"] else 0.0
            if first or cur is None:
                self.arm[i] = {"from": v, "to": v, "t0": now}
            elif cur["to"] != v:
                self.arm[i] = {"from": self.arm_pos(i, now), "to": v, "t0": now}
        for i, fi in enumerate(f.fires):
            if fi["out"] and i not in self.fire_out:
                self.fire_out[i] = -99.0 if first else now

    def robot(self, k, now):
        a = self.rob[k]
        if a["dur"] <= 0:
            t = 1.0
        else:
            t = max(0.0, min(1.0, (now - a["t0"]) / a["dur"]))
        x = a["from"][0] + (a["to"][0] - a["from"][0]) * t
        y = a["from"][1] + (a["to"][1] - a["from"][1]) * t
        ang = a["from"][2] + (a["to"][2] - a["from"][2]) * t
        b = self.bumps.get(k)
        if b is not None and now - b < 0.45:
            k_ = math.sin((now - b) / 0.45 * math.pi * 3) * 0.06 * (1 - (now - b) / 0.45)
            rad = math.radians(ang)
            x += math.cos(rad) * k_
            y += math.sin(rad) * k_
        return (x, y, ang)

    def moving(self, k, now):
        a = self.rob[k]
        return a["dur"] > 0 and now - a["t0"] < a["dur"]

    def stone_pos(self, i, now):
        a = self.stone[i]
        t = max(0.0, min(1.0, (now - a["t0"]) / S.STEP))
        return (a["from"][0] + (a["to"][0] - a["from"][0]) * t, a["from"][1] + (a["to"][1] - a["from"][1]) * t)

    def animal_pos(self, i, now):
        a = self.ani[i]
        dur = S.ANIMAL_STEP * 0.85
        t = max(0.0, min(1.0, (now - a["t0"]) / dur))
        x = a["from"][0] + (a["to"][0] - a["from"][0]) * t
        y = a["from"][1] + (a["to"][1] - a["from"][1]) * t
        hop = abs(math.sin(t * math.pi)) * 10 if t < 1 else 0
        return (x, y, hop)

    def arm_pos(self, i, now):
        a = self.arm[i]
        t = max(0.0, min(1.0, (now - a["t0"]) / 0.45))
        return a["from"] + (a["to"] - a["from"]) * t

    def bump(self, k, now):
        self.bumps[k] = now


# ================================================================ το «παράθυρο» στο δάσος
class ForestView:
    def __init__(self, forest, rect, box=None, me=None, names=None, tags=True, tag_scale=1.0, decor=True,
                 radius=20, top=2.2, bottom=2.4):
        self.f = forest
        self.rect = pygame.Rect(rect)
        self.box = tuple(box) if box else (0, 0, forest.W, forest.H)
        self.me = me
        self.names = names or {}
        self.tags = tags
        self.tag_scale = tag_scale
        self.decor = decor
        self.radius = radius
        self.g = fit_box(self.rect, self.box, top=top, bottom=bottom)
        self.sp = Sprites.get(self.g.tw)
        self.ground = None
        self._static = None
        self.route = None             # η βοήθεια «Δρόμος»: κουτάκια με τη σειρά

    # ------------------------------------------------------------ βοηθητικά
    def pt(self, X, Y, z=0.0):
        return self.g.pt(X, Y, z)

    def in_box(self, c):
        x0, y0, x1, y1 = self.box
        return x0 <= c[0] < x1 and y0 <= c[1] < y1

    def cell_at(self, pos):
        X, Y = self.g.world_at(pos[0], pos[1], 0)
        c = (math.floor(X), math.floor(Y))
        return c if self.in_box(c) else None

    def plot_at(self, pos):
        c = self.cell_at(pos)
        return self.f.owner_of(c) if c else 0

    def links(self, c):
        """Από πού και πού πάει το αυλάκι στο κουτάκι c (για να ζωγραφιστεί σωστά)."""
        f = self.f
        out = []
        for d in range(4):
            n = W.add(c, d)
            if n in f.chan_next.get(c, []) or c in f.chan_next.get(n, []):
                out.append(d)
            elif f.cell(n) == "S" and c in f.sources:
                out.append(d)
            elif f.cell(n) == "F" and any(fi["end"] == c for fi in f.fires):
                out.append(d)
        return out

    # ------------------------------------------------------------ μία φορά: το έδαφος
    def build(self):
        f, r = self.f, self.rect
        g = lf.Geo(self.g.ox - r.x, self.g.oy - r.y, self.g.tw, self.g.shift, self.g.th)
        img = pygame.Surface(r.size)
        img.fill((200, 232, 252))
        for y in range(r.h):
            pygame.draw.line(img, ui.mix((110, 182, 246), (200, 232, 252), y / r.h), (0, y), (r.w, y))
        if self.decor:
            A.Board._sky_decor(None, img)
        tw = self.g.tw
        n = 8 if tw > 50 else 6 if tw > 30 else 4 if tw > 18 else 2
        nu = max(1, n // 2)
        x0, y0, x1, y1 = self.box
        cells = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
        rng = random.Random(7)
        for x, y in cells:
            edge = min(x - x0, y - y0, x1 - 1 - x, y1 - 1 - y)
            if edge >= 1 and rng.random() < 0.45:
                cube(img, g, x, y, -3 * CUBE, -2 * CUBE, "dirt", 2, n=nu)
        for x, y in cells:
            edge = min(x - x0, y - y0, x1 - 1 - x, y1 - 1 - y)
            if edge >= 1 or rng.random() < 0.55:
                cube(img, g, x, y, -2 * CUBE, -CUBE, "dirt", 1, n=nu)
        for x, y in cells:
            c = (x, y)
            ch = f.cell(c)
            if ch == "w":
                cube(img, g, x, y, -CUBE, -16, "water", 3, n=n)
            elif ch == "m":
                cube(img, g, x, y, -CUBE, 0, "grass", 3, n=n, top=(132, 206, 92))
            else:
                cube(img, g, x, y, -CUBE, 0, "grass", 3, n=n)
            if ch in "cB":
                self._groove(img, g, c, self.links(c))
                if ch == "B":
                    lk = self.links(c)
                    along_x = any(d in (W.LEFT, W.RIGHT) for d in lk)
                    if along_x:
                        cube(img, g, x, y, 0, 8, "plank", 3, 0.3, 0.7, 0.12, 0.88, n=4)
                    else:
                        cube(img, g, x, y, 0, 8, "plank", 3, 0.12, 0.88, 0.3, 0.7, n=4)
            elif ch == "p":
                pts = [g.pt(x + u, y + v, 1) for u, v in ((0.16, 0.16), (0.84, 0.16), (0.84, 0.84), (0.16, 0.84))]
                ui.fill_poly(img, (250, 206, 50), pts, (200, 150, 30))
            elif ch == "m":
                _flowers(img, g, x, y, 5)
            elif ch in ".a" and tw > 16:
                A.flowers(img, g, x, y)
        # οι καταρράκτες στην άκρη του νησιού (όπου το ποτάμι βγαίνει έξω)
        for x, y in cells:
            if f.cell((x, y)) == "w":
                for d in range(4):
                    nx, ny = x + W.DX[d], y + W.DY[d]
                    if not (x0 <= nx < x1 and y0 <= ny < y1) and d in (W.RIGHT, W.DOWN):
                        self._fall(img, g, x, y, d)
        # το οικόπεδο του μαθητή: κίτρινο περίγραμμα
        if self.me and self.me in f.plots:
            p = f.plots[self.me]
            px, py = p["x0"], p["y0"]
            over = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            pts = [g.pt(px + 0.03, py + 0.03, 1), g.pt(px + W.PLOT - 0.03, py + 0.03, 1),
                   g.pt(px + W.PLOT - 0.03, py + W.PLOT - 0.03, 1), g.pt(px + 0.03, py + W.PLOT - 0.03, 1)]
            pygame.draw.polygon(over, (255, 236, 120, 46), pts)
            img.blit(over, (0, 0))
            pygame.draw.lines(img, (250, 204, 40), True, pts, max(2, round(tw * 0.09)))
        # οι μαύρες γραμμές (αισθητήρας γραμμής), πάνω από το κίτρινο του οικοπέδου
        for k, line in f.lines.items():
            if len(line) > 1 and any(self.in_box(c) for c in line):
                _black_line(img, g, line)
        if self.radius:
            out = pygame.Surface(r.size, pygame.SRCALPHA)
            out.blit(img, (0, 0))
            mask = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=self.radius)
            out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            img = out
        self.ground = img
        self._static = self._static_items()

    def _groove(self, s, g, c, dirs):
        x, y = c
        for w, col in ((0.22, (104, 76, 50)), (0.16, (164, 124, 82))):
            for r in _groove_rects(x, y, dirs, w):
                pygame.draw.polygon(s, col, _quad(g, *r))

    def _fall(self, s, g, x, y, d):
        if d == W.RIGHT:
            a, b = (x + 1, y + 0.36), (x + 1, y + 0.64)
        else:
            a, b = (x + 0.36, y + 1), (x + 0.64, y + 1)
        pts = [g.pt(a[0], a[1], -2), g.pt(b[0], b[1], -2), g.pt(b[0], b[1], -3.2 * CUBE), g.pt(a[0], a[1], -3.2 * CUBE)]
        pygame.draw.polygon(s, (78, 156, 238), pts)
        for i in range(4):
            u = (i + 0.5) / 4
            p = g.pt(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, -CUBE * (0.5 + i * 0.6))
            pygame.draw.line(s, (196, 228, 255), p, (p[0], p[1] + g.tw * 0.25), 2)

    def _static_items(self):
        """Δέντρα, βράχοι, πηγές, πινακίδες, φράχτες, στηρίγματα: (βάθος, εικόνα, θέση)."""
        f, sp = self.f, self.sp
        items = []
        x0, y0, x1, y1 = self.box
        signs = set()
        for t, cells in f.meadows.items():
            if cells:
                signs.add(max(cells, key=lambda c: (c[1], c[0])))
        pivots = set()
        for s in f.seesaws:
            pivots.add(frozenset((s["pedal"], s["arm"][0])))
            if s["from"] == s["to"] and self.in_box(s["pedal"]):      # το φράγμα: στήριγμα ανάμεσα
                a, b = s["pedal"], s["arm"][0]
                X, Y = (a[0] + b[0]) / 2 + 0.5, (a[1] + b[1]) / 2 + 0.5
                items.append(self._place(X * 0.46 + Y, sp.item(("stump_in", round(X % 1, 1), round(Y % 1, 1)),
                                                               lambda ss, gg, u=X % 1, v=Y % 1: _stump(ss, gg, u, v)),
                                         int(X), int(Y)))
        rock_pairs = set()
        for st in f.stones:
            if st.get("big") is not None:
                rock_pairs.add(frozenset((st["start"], f.stones[st["big"]]["start"])))
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = (x, y)
                ch = f.cell(c)
                v = (x * 7 + y * 13) % 4
                low = not f.owner_of(c) and (f.owner_of((x, y - 1)) or f.owner_of((x, y - 2)))   # μπροστά από οικόπεδο
                if ch == "T" and low:
                    items.append(self._place((x + 0.5) * 0.46 + y + 0.5, sp.item(("bush", v), lambda ss, gg, v=v: _bush(ss, gg, v)), x, y))
                elif ch == "T":
                    items.append(self._place((x + 0.5) * 0.46 + y + 0.5, sp.tree(v), x, y))
                elif ch == "R":
                    items.append(self._place((x + 0.5) * 0.46 + y + 0.5, sp.rock(v), x, y))
                elif ch == "S":
                    items.append(self._place((x + 0.5) * 0.46 + y + 0.5, sp.item("spring", lambda s, g: _spring(s, g, 0, 0)), x, y))
                if c in signs:
                    items.append(self._place((x + 0.5) * 0.46 + y + 0.6, sp.item("sign", lambda s, g: _sign(s, g, 0, 0)), x, y))
                # φράχτες προς τα δεξιά και προς τα κάτω
                k = f.owner_of(c)
                for d in (W.RIGHT, W.DOWN):
                    nb = W.add(c, d)
                    k2 = f.owner_of(nb)
                    if not (x0 <= nb[0] < x1 and y0 <= nb[1] < y1) or k == k2 or not k or not k2:
                        continue
                    if frozenset((c, nb)) in f.gap_pairs or frozenset((c, nb)) in rock_pairs:
                        continue
                    if f.cell(c) in "wcBS" and f.cell(nb) in "wcBS":
                        continue
                    if frozenset((c, nb)) in pivots:
                        if d == W.RIGHT:
                            items.append(self._place((x + 1) * 0.46 + y + 0.5,
                                                     sp.item("stump", lambda s, g: _stump(s, g, 0, 0.5)), x + 1, y))
                        else:
                            items.append(self._place((x + 0.5) * 0.46 + y + 1,
                                                     sp.item("stump", lambda s, g: _stump(s, g, 0.5, 0)), x, y + 1))
                        continue
                    if d == W.RIGHT:
                        items.append(self._place((x + 1) * 0.46 + y + 0.5, sp.item("fv", lambda s, g: _fence_v(s, g, 0, 0)),
                                                 x + 1, y))
                    else:
                        items.append(self._place((x + 0.5) * 0.46 + y + 1, sp.item("fh", lambda s, g: _fence_h(s, g, 0, 0)),
                                                 x, y + 1))
        return items

    def _place(self, depth, sprite, x, y):
        img, (ox, oy) = sprite
        px, py = self.g.pt(x, y, 0)
        return (depth, img, (round(px + ox), round(py + oy)))

    # ------------------------------------------------------------ κάθε καρέ
    def draw(self, surf, time, tr, labels=True):
        if self.ground is None:
            self.build()
        f, g, sp = self.f, self.g, self.sp
        surf.blit(self.ground, self.rect)
        old = surf.get_clip()
        surf.set_clip(self.rect.inflate(-4, -4))
        x0, y0, x1, y1 = self.box
        # νερό στα αυλάκια, καμένο έδαφος
        for c in f.wet:
            if self.in_box(c):
                lk = [d for d in self.links(c) if W.add(c, d) in f.wet or f.cell(W.add(c, d)) in "wSF"
                      or W.add(c, d) in f.chan_next.get(c, [])]
                self._water(surf, g, c, lk, time)
        for i, fi in enumerate(f.fires):
            for j, c in enumerate(fi["cells"]):
                if not self.in_box(c):
                    continue
                pts = _quad(g, c[0] + 0.02, c[1] + 0.02, c[0] + 0.98, c[1] + 0.98, 0.5)
                if fi["out"]:
                    pygame.draw.polygon(surf, (92, 96, 66), pts)
                else:
                    pygame.draw.polygon(surf, (70, 54, 42), pts)
                    FI.ground_glow(surf, g, c[0] + 0.5, c[1] + 0.5, 1.0, 0.9)
                    FI.scorched(surf, g, c[0], c[1], 60 + j, time)
        if self.route:
            for a, b in zip(self.route, self.route[1:]):
                for t in range(4):
                    u = t / 4
                    p = g.pt(a[0] + 0.5 + (b[0] - a[0]) * u, a[1] + 0.5 + (b[1] - a[1]) * u, 1)
                    ui.circle(surf, (255, 255, 255), p, max(3, g.tw * 0.07) + 1.5)
                    ui.circle(surf, (250, 190, 30), p, max(3, g.tw * 0.07))
        items = list(self._static)
        # πέτρες
        for i, s in enumerate(f.stones):
            X, Y = tr.stone_pos(i, time)
            if not (x0 - 1 <= X < x1 + 1 and y0 - 1 <= Y < y1 + 1):
                continue
            key = {".": "stone", "x": "crossing", "d": "dam"}[s["state"]]
            draw = {".": _stone, "x": _crossing, "d": _dam}[s["state"]]
            if s.get("big") is not None and s["state"] == ".":
                side = W.dir_of(s["pos"], f.stones[s["big"]]["pos"])
                side = side if side is not None else W.dir_of(s["start"], f.stones[s["big"]]["start"])
                spr = sp.item(("big", side), lambda ss, gg, side=side: _big_half(ss, gg, side))
            else:
                spr = sp.item(key, lambda ss, gg, draw=draw: draw(ss, gg, 0, 0))
            depth = X * 0.46 + Y - (0.3 if s["state"] == "x" else 0)
            items.append(self._place_f(depth, spr, X - 0.5, Y - 0.5))
        # φωτιές
        for i, fi in enumerate(f.fires):
            for j, c in enumerate(fi["cells"]):
                if not self.in_box(c):
                    continue
                tree_cell = (c[0] + c[1]) % 2 == 0
                depth = (c[0] + 0.5) * 0.46 + c[1] + 0.5
                if fi["out"]:
                    if tree_cell:
                        items.append(self._place(depth, sp.item(("burnt", j % 3), lambda s, g, j=j: FI.burnt_tree(s, g, 0, 0, 20 + j)),
                                                 c[0], c[1]))
                    else:
                        items.append(self._place(depth, sp.item(("sprouts", j % 3), lambda s, g, j=j: FI.sprouts(s, g, 0, 0, 40 + j)),
                                                 c[0], c[1]))
                elif tree_cell:
                    items.append(self._place(depth, sp.item(("charred", j % 3), lambda s, g, j=j: FI.charred_tree(s, g, 0, 0, 20 + j)),
                                             c[0], c[1]))
                    items.append((depth + 0.01, ("flames_tree", c, 20 + j * 5), None))
                else:
                    items.append((depth + 0.01, ("flames_ground", c, 40 + j * 7), None))
        # ζώα
        for i, a in enumerate(f.animals):
            X, Y, hop = tr.animal_pos(i, time)
            if not (x0 - 1 <= X < x1 + 1 and y0 - 1 <= Y < y1 + 1):
                continue
            if a["safe"]:
                hop = abs(math.sin(time * 3 + i)) * 6
            img, (ox, oy) = sp.animal(a["kind"], a["face"])
            px, py = g.pt(X - 0.5, Y - 0.5, hop)
            items.append((X * 0.46 + Y, img, (round(px + ox), round(py + oy))))
        # R2
        for k in f.robots:
            X, Y, ang = tr.robot(k, time)
            if not (x0 - 1 <= X < x1 + 1 and y0 - 1 <= Y < y1 + 1):
                continue
            img, (ox, oy) = sp.robot(ang, robot_color(f, k))
            px, py = g.pt(X - 0.5, Y - 0.5, 0)
            items.append((X * 0.46 + Y + 0.02, img, (round(px + ox), round(py + oy))))
        # κλαδιά
        for i, s in enumerate(f.seesaws):
            if not (self.in_box(s["pedal"]) or self.in_box(s["arm"][0])):
                continue
            up = tr.arm_pos(i, time)
            items.extend(self._seesaw_items(s, up))
        items.sort(key=lambda it: it[0])
        for depth, img, pos in items:
            if pos is None:
                kind = img[0]
                if kind == "flames_tree":
                    FI.tree_flames(surf, g, img[1][0], img[1][1], img[2], time)
                elif kind == "flames_ground":
                    FI.ground_flames(surf, g, img[1][0], img[1][1], img[2], time)
                elif kind == "beam":
                    beam(surf, g, *img[1:])
            else:
                surf.blit(img, pos)
        # πάνω από όλα: λάμψη και καπνός της φωτιάς, ατμός, καρδιές, ονόματα
        for i, fi in enumerate(f.fires):
            out_t = tr.fire_out.get(i)
            for j, c in enumerate(fi["cells"]):
                if not self.in_box(c):
                    continue
                tree_cell = (c[0] + c[1]) % 2 == 0
                if not fi["out"]:
                    FI.air_glow(surf, g, c[0] + 0.5, c[1] + 0.5, CUBE * (1.6 if tree_cell else 0.5),
                                1.3 if tree_cell else 0.9, 0.55 if tree_cell else 0.45)
                    if tree_cell:
                        FI.smoke(surf, g, c[0] + 0.5, c[1] + 0.5, CUBE * 2.1, 80 + j, time)
                elif out_t is not None and time - out_t < 5:
                    FI.smoke(surf, g, c[0] + 0.5, c[1] + 0.5, CUBE * 0.8, 90 + j, time, 1 - (time - out_t) / 5, True)
        for i, a in enumerate(f.animals):
            if a["safe"]:
                X, Y, _ = tr.animal_pos(i, time)
                if self.in_box((int(X), int(Y))):
                    heart(surf, g.pt(X, Y, 90 + 8 * math.sin(time * 3 + i)), max(3, g.tw * 0.12))
        if labels and self.tags:
            for k in f.robots:
                X, Y, _ = tr.robot(k, time)
                if not (x0 <= X < x1 and y0 <= Y < y1):
                    continue
                name = self.names.get(k)
                if name is None:
                    continue
                if f.auto.get(k):
                    name = f"{name} · αυτόματο"
                self.name_tag(surf, g.pt(X, Y, 118), name, robot_color(f, k), k == self.me)
        surf.set_clip(old)

    def _place_f(self, depth, sprite, x, y):
        img, (ox, oy) = sprite
        px, py = self.g.pt(x, y, 0)
        return (depth, img, (round(px + ox), round(py + oy)))

    def _water(self, s, g, c, dirs, time):
        x, y = c
        for r in _groove_rects(x, y, dirs or [], 0.16):
            pygame.draw.polygon(s, WATER, _quad(g, *r))
        if g.tw > 18:
            k = (time * 1.5 + x * 0.3 + y * 0.7) % 1.0
            a = g.pt(x + 0.42 + 0.1 * k, y + 0.5, 0.6)
            b = g.pt(x + 0.5 + 0.1 * k, y + 0.5, 0.6)
            pygame.draw.line(s, (170, 214, 252), a, b, 2)

    def _seesaw_items(self, s, up):
        """Το κλαδί σε δύο κομμάτια: την άκρη που πατά το R2 (πριν από το R2) και το μακρύ χέρι πάνω από
        το μονοπάτι του γείτονα (μετά από ό,τι περνά από κάτω)."""
        pedal, arm = s["pedal"], s["arm"]
        d = W.dir_of(pedal, arm[0])
        a0 = arm[0]
        piv = ((pedal[0] + a0[0]) / 2 + 0.5, (pedal[1] + a0[1]) / 2 + 0.5)
        zp = 26
        z3 = 48 + (4 - 48) * up
        z4 = 2 + ((240 if len(arm) <= 3 else 150) - 2) * up
        pedal_end = (pedal[0] + 0.5 - W.DX[d] * 0.45, pedal[1] + 0.5 - W.DY[d] * 0.45)
        arm_end = (arm[-1][0] + 0.5 + W.DX[d] * 0.45, arm[-1][1] + 0.5 + W.DY[d] * 0.45)
        axis = "x" if d in (W.LEFT, W.RIGHT) else "y"
        dp = (pedal[0] + 0.5) * 0.46 + pedal[1] + 0.5 - 0.05
        da = max((c[0] + 0.5) * 0.46 + c[1] + 0.5 for c in arm) + 0.05
        return [(dp, ("beam", piv, zp, pedal_end, z3, 0.14, 15, axis), None),
                (da, ("beam", piv, zp, arm_end, z4, 0.14, 15, axis), None)]

    def name_tag(self, s, pos, text, color, own=False):
        sc = self.tag_scale
        size = round((14 if own else 13) * sc)
        f = ui.font(size)
        w = f.size(text)[0] + round(30 * sc)
        r = pygame.Rect(0, 0, w, size + round(11 * sc))
        r.midbottom = (round(pos[0]), round(pos[1]))
        fill = (252, 210, 60) if own else (255, 255, 255)
        pygame.draw.rect(s, ui.shade(fill, 0.75), r.move(0, 2), border_radius=r.h // 2)
        pygame.draw.rect(s, fill, r, border_radius=r.h // 2)
        pygame.draw.circle(s, color, (r.x + round(12 * sc), r.centery), max(3, round(5 * sc)))
        ui.text(s, text, (r.x + round(21 * sc), r.centery), size, (60, 50, 20) if own else (50, 60, 80), anchor="midleft")
        pygame.draw.polygon(s, fill, [(r.centerx - 5, r.bottom - 1), (r.centerx + 5, r.bottom - 1),
                                      (r.centerx, r.bottom + 5)])

    def robot_top(self, k, tr, now, z=150):
        X, Y, _ = tr.robot(k, now)
        return self.g.pt(X, Y, z)

    def plot_outline(self, k, inset=0.03):
        p = self.f.plots[k]
        px, py = p["x0"], p["y0"]
        return [self.g.pt(px + inset, py + inset, 1), self.g.pt(px + W.PLOT - inset, py + inset, 1),
                self.g.pt(px + W.PLOT - inset, py + W.PLOT - inset, 1), self.g.pt(px + inset, py + W.PLOT - inset, 1)]


def _quad(g, x0, y0, x1, y1, z=0.5):
    return [g.pt(x0, y0, z), g.pt(x1, y0, z), g.pt(x1, y1, z), g.pt(x0, y1, z)]


def _groove_rects(X, Y, dirs, w):
    rs = [(X + 0.5 - w, Y + 0.5 - w, X + 0.5 + w, Y + 0.5 + w)]
    for d in dirs:
        if d == W.RIGHT:
            rs.append((X + 0.5, Y + 0.5 - w, X + 1, Y + 0.5 + w))
        elif d == W.LEFT:
            rs.append((X, Y + 0.5 - w, X + 0.5, Y + 0.5 + w))
        elif d == W.DOWN:
            rs.append((X + 0.5 - w, Y + 0.5, X + 0.5 + w, Y + 1))
        elif d == W.UP:
            rs.append((X + 0.5 - w, Y, X + 0.5 + w, Y + 0.5))
    return rs


def _flowers(s, g, x, y, n=5):
    rng = random.Random(x * 17 + y * 5)
    for _ in range(n):
        px, py = g.pt(x + rng.uniform(0.12, 0.88), y + rng.uniform(0.12, 0.88), 0)
        col = rng.choice([(240, 70, 70), (250, 214, 60), (255, 255, 255), (200, 120, 230), (255, 150, 190)])
        r = max(2, round(4 * g.k))
        pygame.draw.rect(s, (60, 130, 50), (px - 1, py - r, 2, r))
        pygame.draw.rect(s, col, (px - r // 2 - 1, py - r - r // 2 - 2, r + 1, r + 1))


def bump_stars(s, pos, age, size):
    r2art.bump_stars(s, pos, age, size)
