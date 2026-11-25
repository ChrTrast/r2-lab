"""Η φωτιά: φλόγες από «pixel», όπως οι υφές των κύβων του «Προγραμμάτισε».

Κάθε φλόγα φτιάχνεται με τον κλασικό αλγόριθμο φωτιάς: η θερμότητα ανεβαίνει από κάτω, κουνιέται λίγο
δεξιά-αριστερά και κρυώνει τυχαία, οπότε βγαίνουν «γλώσσες». Μετά παίρνει σχήμα σταγόνας (φαρδιά κάτω,
στενή πάνω), λειαίνεται και χρωματίζεται: κίτρινη-άσπρη καρδιά, πορτοκαλί, κόκκινες άκρες.
Για να τρεμοπαίζει, κάθε φλόγα έχει FRAMES εικόνες (άλλος σπόρος) που αλλάζουν μερικές φορές το δευτερόλεπτο.
Όλες οι εικόνες φυλάγονται (cache): φτιάχνονται μία φορά για κάθε μέγεθος.
"""
import random

import pygame

from games.program import art as A

cube, CUBE = A.cube, A.CUBE
MAXH = 36
FRAMES = 4
FPS = 7
STOPS = [(0.16, (190, 38, 22)), (0.30, (228, 72, 26)), (0.46, (246, 122, 32)), (0.62, (252, 170, 42)),
         (0.76, (255, 210, 70)), (0.88, (255, 236, 140)), (0.97, (255, 250, 214))]
_flames = {}
_glows = {}
_puffs = {}


def _heat(w, h, seed, reach=0.8, wide=1.0):
    rng = random.Random(seed)
    heat = [[0.0] * w for _ in range(h)]
    c = (w - 1) / 2
    for x in range(w):
        d = abs(x - c) / (w / 2 * wide)
        heat[h - 1][x] = MAXH * max(0.0, 1 - d ** 1.7)
    decay = MAXH / (h * reach)
    for _ in range(h * 3):
        for y in range(h - 1):
            row, below = heat[y], heat[y + 1]
            for x in range(w):
                src = below[min(w - 1, max(0, x + rng.choice((-1, 0, 0, 0, 1))))]
                row[x] = max(0.0, src - rng.random() * decay * 2.0)
    for y in range(h):
        t = 1 - y / (h - 1)
        half = (w / 2) * (1 - 0.82 * t ** 1.15) * wide
        for x in range(w):
            env = max(0.0, 1 - (abs(x - c) / max(0.6, half)) ** 2)
            heat[y][x] = heat[y][x] * env + MAXH * 0.42 * env * (1 - t) ** 1.4
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            tot, n = heat[y][x] * 2, 2
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + dx < w and 0 <= y + dy < h:
                    tot += heat[y + dy][x + dx]
                    n += 1
            out[y][x] = tot / n
    return out


def _color(v):
    col = None
    for stop, c in STOPS:
        if v >= stop:
            col = c
    return col


def flame_sprite(seed, w=12, h=20, px=3, reach=0.8):
    key = (seed, w, h, px, reach)
    if key not in _flames:
        heat = _heat(w, h, seed, reach)
        img = pygame.Surface((w * px, h * px), pygame.SRCALPHA)
        cols = [[_color(min(1.0, heat[y][x] / MAXH)) for x in range(w)] for y in range(h)]
        for y in range(h):
            for x in range(w):
                col = cols[y][x]
                if not col:
                    continue
                near = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                           if 0 <= x + dx < w and 0 <= y + dy < h and cols[y + dy][x + dx])
                if near >= 2:
                    img.fill(col, (x * px, y * px, px, px))
        _flames[key] = img
    return _flames[key]


def pixel(g, size=1.0):
    return max(2, round(g.tw / 14 * size))


def frame(time, seed):
    return int(time * FPS + seed * 0.37) % FRAMES


def flame(s, g, X, Y, z=0.0, size=1.0, seed=0, w=12, h=20, reach=0.8, time=0.0):
    """Μία φλόγα με τη βάση της στο (X, Y, z) του χάρτη."""
    img = flame_sprite(seed * 10 + frame(time, seed), w, h, pixel(g, size), reach)
    x, y = g.pt(X, Y, z)
    s.blit(img, img.get_rect(midbottom=(round(x), round(y) + img.get_height() // 12)))


def embers(s, g, X, Y, z, seed=0, n=6, spread=0.45, height=150, time=0.0):
    rng = random.Random(seed * 7 + int(time * 4))
    p = pixel(g, 0.8)
    for _ in range(n):
        x, y = g.pt(X + rng.uniform(-spread, spread), Y + rng.uniform(-spread * 0.6, spread * 0.6),
                    z + rng.uniform(40, height))
        col = rng.choice([(255, 214, 80), (255, 160, 40), (255, 236, 150), (240, 96, 30)])
        s.fill(col, (round(x), round(y), p, p))


def _glow_img(rx, ry, strength):
    key = (rx, ry, round(strength, 2))
    if key not in _glows:
        img = pygame.Surface((rx * 2, ry * 2))
        img.fill((0, 0, 0))
        steps = 12
        for i in range(steps, 0, -1):
            k = i / steps
            a = (1 - k) ** 1.5 * strength
            col = (min(255, int(200 * a)), min(255, int(92 * a)), min(255, int(20 * a)))
            r = pygame.Rect(0, 0, round(rx * 2 * k), round(ry * 2 * k))
            r.center = (rx, ry)
            pygame.draw.ellipse(img, col, r)
        _glows[key] = img
    return _glows[key]


def ground_glow(s, g, X, Y, size=1.0, strength=0.9):
    x, y = g.pt(X, Y, 0)
    rx = max(4, round(g.tw * 1.25 * size))
    img = _glow_img(rx, max(3, round(rx * 0.5)), strength)
    s.blit(img, img.get_rect(center=(round(x), round(y))), special_flags=pygame.BLEND_RGB_ADD)


def air_glow(s, g, X, Y, z, size=1.0, strength=0.55):
    x, y = g.pt(X, Y, z)
    r = max(4, round(g.tw * 1.0 * size))
    img = _glow_img(r, r, strength)
    s.blit(img, img.get_rect(center=(round(x), round(y))), special_flags=pygame.BLEND_RGB_ADD)


def _puff(size, shade, alpha):
    key = (size, shade, alpha)
    if key not in _puffs:
        img = pygame.Surface((size, size), pygame.SRCALPHA)
        img.fill((shade, shade - 4, shade - 8, alpha))
        _puffs[key] = img
    return _puffs[key]


def smoke(s, g, X, Y, z=120, seed=0, time=0.0, strength=1.0, light=False):
    """Καπνός από «pixel» τετράγωνα που ανεβαίνουν (light: ο λευκός ατμός όταν σβήνει η φωτιά)."""
    rng = random.Random(seed)
    p = pixel(g, 1.0)
    for i in range(8):
        k = (i / 8 + time * 0.25 + rng.random() * 0.05) % 1.0
        x, y = g.pt(X + rng.uniform(-0.18, 0.18) + k * 0.55, Y - k * 0.2, z + 30 + 240 * k)
        size = max(2, round(p * (2.5 + 4.5 * k)))
        a = int(150 * strength * (1 - k) ** 0.8) // 16 * 16
        if a <= 0:
            continue
        shade = 220 + int(25 * k) if light else int(64 + 90 * k) // 8 * 8
        img = _puff(size, min(255, shade), a)
        for dx, dy in ((0, 0), (size * 0.55, -size * 0.3), (-size * 0.5, -size * 0.2)):
            s.blit(img, (round(x + dx - size / 2), round(y + dy - size / 2)))


def scorched(s, g, x, y, seed=0, time=0.0):
    """Κάρβουνα που λάμπουν στο καμένο έδαφος."""
    rng = random.Random(seed)
    p = pixel(g, 0.9)
    blink = int(time * 3) % 3
    for i in range(7):
        px_, py_ = g.pt(x + rng.uniform(0.1, 0.9), y + rng.uniform(0.1, 0.9), 0.5)
        col = rng.choice([(255, 120, 30), (230, 70, 24), (255, 180, 60)])
        if (i + blink) % 3 == 0:
            col = (255, 210, 110)
        s.fill(col, (round(px_), round(py_), p, p))


def charred_tree(s, g, x, y, seed):
    """Το δέντρο που καίγεται, χωρίς τις φλόγες (μπαίνει σε cache): σκούρα, καψαλισμένα φύλλα."""
    cube(s, g, x, y, 0, CUBE * 0.95, (70, 52, 36), seed, 0.38, 0.62, 0.38, 0.62, n=4)
    cube(s, g, x, y, CUBE * 0.7, CUBE * 1.42, (84, 74, 40), seed, 0.08, 0.92, 0.08, 0.92, n=8)
    cube(s, g, x, y, CUBE * 1.42, CUBE * 1.72, (74, 62, 34), seed + 1, 0.28, 0.72, 0.28, 0.72, n=4)
    rng = random.Random(seed * 3 + 1)
    p = pixel(g, 0.8)
    for _ in range(9):
        u, v = rng.uniform(0.12, 0.88), rng.uniform(0.12, 0.88)
        if rng.random() < 0.5:
            px_, py_ = g.pt(x + u, y + 0.92, CUBE * (0.72 + 0.68 * v))
        else:
            px_, py_ = g.pt(x + 0.92, y + u, CUBE * (0.72 + 0.68 * v))
        s.fill(rng.choice([(255, 140, 40), (232, 84, 28), (255, 196, 70)]), (round(px_), round(py_), p, p))


def tree_flames(s, g, x, y, seed, time):
    """Οι φλόγες ενός δέντρου που καίγεται (κάθε καρέ)."""
    flame(s, g, x + 0.28, y + 0.66, CUBE * 1.15, 0.62, seed + 3, 10, 16, 0.8, time)
    flame(s, g, x + 0.5, y + 0.5, CUBE * 1.66, 0.95, seed + 1, 12, 20, 0.85, time)
    flame(s, g, x + 0.8, y + 0.42, CUBE * 1.25, 0.68, seed + 2, 10, 16, 0.8, time)
    embers(s, g, x + 0.5, y + 0.5, CUBE * 1.9, seed, 5, 0.5, 110, time)


def ground_flames(s, g, x, y, seed, time):
    rng = random.Random(seed)
    flame(s, g, x + 0.58 + rng.uniform(-0.08, 0.08), y + 0.38, 0, 0.82, seed, 12, 18, 0.85, time)
    flame(s, g, x + 0.28 + rng.uniform(-0.05, 0.05), y + 0.72, 0, 0.58, seed + 7, 10, 15, 0.8, time)
    embers(s, g, x + 0.5, y + 0.5, 30, seed, 4, 0.45, 100, time)


def burnt_tree(s, g, x, y, seed):
    """Μετά τη φωτιά: μαύρος κορμός με καινούργια πράσινα φυλλαράκια (το δάσος ξαναπρασινίζει)."""
    cube(s, g, x, y, 0, CUBE * 0.9, (58, 50, 46), seed, 0.4, 0.6, 0.4, 0.6, n=3)
    cube(s, g, x, y, CUBE * 0.55, CUBE * 0.62, (58, 50, 46), seed, 0.6, 0.8, 0.46, 0.54, n=2)
    for dx, dy, z in ((0.62, 0.42, 0.72), (0.3, 0.55, 0.9), (0.5, 0.36, 0.95)):
        cube(s, g, 0, 0, CUBE * z, CUBE * z + 12, (110, 196, 80), seed, x + dx, x + dx + 0.12, y + dy, y + dy + 0.12,
             n=2)


def sprouts(s, g, x, y, seed):
    rng = random.Random(seed)
    for _ in range(9):
        u, v = rng.uniform(0.12, 0.8), rng.uniform(0.12, 0.8)
        cube(s, g, 0, 0, 0, rng.uniform(10, 20), (104, 190, 74), seed, x + u, x + u + 0.09, y + v, y + v + 0.09, n=1)
