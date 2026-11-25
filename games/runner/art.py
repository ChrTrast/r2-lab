"""Τα γραφικά του τρεξίματος (Αριθμοί, Λέξεις, Πράξεις), ζωγραφισμένα με κώδικα.

Το R2 φαίνεται από το πλάι και κοιτάει δεξιά, με τα χρώματα του πραγματικού ρομπότ: μαύρο σασί,
θήκη μπαταριών, λευκή πλακέτα polytech με χρωματιστές υποδοχές και το RGB LED, διάφανο καπάκι
σε χρυσές κολόνες, μπροστά ο αισθητήρας απόστασης («τα μάτια»). Όπως στο πραγματικό, η μεγάλη μαύρη
ρόδα είναι πίσω και ο σφαιρικός τροχός μπροστά, κάτω από τον αισθητήρα γραμμής.
Ο κόσμος μετριέται σε κουτάκια (TILE). Το έδαφος έχει πάνω του τη γραμμή y = ground.
"""
import math
import random

import pygame
import pygame.gfxdraw

from core import ui

TILE = 64
LED_BLUE, LED_RED, LED_GREEN = (90, 170, 255), (240, 60, 60), (70, 220, 110)
INK = (24, 26, 34)
WHITE = (255, 255, 255)
YELLOW, YELLOW_DARK = (252, 206, 54), (196, 140, 22)
ORANGE = (240, 126, 40)

# Τα χρώματα κάθε πίστας: ουρανός (πάνω, κάτω), έδαφος, εμπόδια, γραμμές
THEMES = [
    {"sky": ((52, 104, 214), (120, 176, 248)), "ground": (30, 62, 156), "block": (20, 38, 106), "line": (206, 228, 255)},
    {"sky": ((96, 62, 196), (176, 136, 244)), "ground": (66, 38, 140), "block": (42, 22, 98), "line": (234, 216, 255)},
    {"sky": ((14, 128, 124), (92, 206, 184)), "ground": (10, 88, 84), "block": (6, 56, 56), "line": (204, 250, 236)},
    {"sky": ((222, 96, 40), (252, 178, 92)), "ground": (148, 50, 18), "block": (96, 30, 10), "line": (255, 228, 192)},
    {"sky": ((194, 54, 136), (246, 140, 198)), "ground": (118, 26, 84), "block": (80, 12, 54), "line": (255, 214, 238)},
    {"sky": ((20, 20, 66), (70, 56, 150)), "ground": (16, 16, 44), "block": (8, 8, 28), "line": (176, 186, 255)},
]

PORTAL_COLORS = {
    "gravity_up": (70, 168, 255),     # το R2 τρέχει ανάποδα, στο ταβάνι
    "gravity_down": YELLOW,           # πίσω στο πάτωμα
    "rocket": (240, 86, 176),         # γίνεται πύραυλος
    "run": (80, 206, 108),            # πίσω στις ρόδες
}

_cache = {}


def _cached(key, make):
    if key not in _cache:
        if len(_cache) > 300:
            _cache.clear()
        _cache[key] = make()
    return _cache[key]


def _bezier(p0, p1, p2, n=18):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


class _Pen:
    """Ζωγραφίζει σε μονάδες 0-100 πάνω σε επιφάνεια 3 φορές μεγαλύτερη (για λεία περιγράμματα)."""

    def __init__(self, w, h=None, unit=None):
        h = w if h is None else h
        self.u = unit if unit is not None else w * 3 / 100
        self.s = pygame.Surface((round(w * 3), round(h * 3)), pygame.SRCALPHA)
        self.size = (round(w), round(h))

    def R(self, x, y, w, h):
        u = self.u
        return pygame.Rect(round(x * u), round(y * u), round(w * u), round(h * u))

    def rr(self, col, x, y, w, h, rad, border=None, bw=1.6):
        pygame.draw.rect(self.s, col, self.R(x, y, w, h), border_radius=round(rad * self.u))
        if border:
            pygame.draw.rect(self.s, border, self.R(x, y, w, h), width=max(1, round(bw * self.u)),
                             border_radius=round(rad * self.u))

    def circ(self, col, x, y, r):
        pygame.draw.circle(self.s, col, (x * self.u, y * self.u), r * self.u)

    def poly(self, col, pts):
        pygame.draw.polygon(self.s, col, [(x * self.u, y * self.u) for x, y in pts])

    def line(self, col, pts, w):
        pygame.draw.lines(self.s, col, False, [(x * self.u, y * self.u) for x, y in pts], max(1, round(w * self.u)))

    def done(self):
        return pygame.transform.smoothscale(self.s, self.size)


# ------------------------------------------------------------------ R2
WHEEL_AT = (0.27, 0.78)      # το κέντρο της ρόδας μέσα στο κουτί του R2 (κλάσματα του μεγέθους): πίσω


def _eye(p, x, y, r):
    p.circ(INK, x, y, r + 1)
    p.circ((210, 216, 228), x, y, r)
    p.circ((156, 164, 180), x, y, r * 0.74)
    p.circ((62, 66, 78), x, y, r * 0.52)
    p.circ(WHITE, x - r * 0.28, y - r * 0.3, r * 0.2)


def _paint_body(size, led):
    """Το R2 χωρίς τη ρόδα (η ρόδα γυρίζει, γι' αυτό ζωγραφίζεται χωριστά), με τα χρώματα του πραγματικού."""
    p = _Pen(size)
    # μπροστά, κάτω από το σασί: ο αισθητήρας γραμμής (λευκή πλακέτα, το «μάτι» του από κάτω) και κάτω
    # από αυτόν ο σφαιρικός τροχός: λευκή θήκη με ατσάλινη μπίλια που ακουμπά στο έδαφος
    p.rr((238, 240, 236), 62, 61.5, 30, 3, 1, (150, 156, 164), 0.8)
    p.rr((36, 38, 44), 84.5, 64, 5, 2.6, 0.6)
    p.rr((222, 225, 230), 65.5, 64, 12, 25, 2.5, (140, 146, 156), 0.9)
    p.circ(INK, 71.5, 92.6, 7.2)
    p.circ((150, 154, 166), 71.5, 92.6, 5.9)
    p.circ((214, 218, 226), 69.9, 90.9, 1.9)
    # πίσω, κάτω από το σασί: το κίτρινο μοτέρ της ρόδας (το κρύβει σχεδόν όλο η ρόδα) και το ασημένιο
    # μοτεράκι του, που ξεπροβάλλει μπροστά από τη ρόδα
    p.rr((250, 200, 40), 11, 60, 28, 12, 2, (190, 140, 20), 1)
    p.rr((186, 190, 198), 38, 61.5, 15, 9, 2, (120, 124, 136), 0.8)
    # μαύρο ακρυλικό σασί
    p.rr((34, 35, 40), 5, 56, 80, 6, 2, INK, 1.2)
    # μπλε πλακέ καλώδιο: από τον αισθητήρα κάνει καμπύλη ψηλά και κατεβαίνει στην πλακέτα
    p.line((36, 84, 210), _bezier((73, 34), (62, -8), (40, 27)), 2.8)
    # χρυσές κολόνες: από το σασί στην πλακέτα και από την πλακέτα στο καπάκι
    for x in (10, 63):
        p.rr((214, 172, 76), x, 21, 3.2, 35, 1, (160, 120, 40), 0.8)
    # θήκη μπαταριών πίσω, πάνω στο σασί
    p.rr((24, 25, 30), 8, 44, 34, 12, 2, INK, 1.2)
    for i in range(3):
        p.rr((70, 72, 80), 11 + i * 10.3, 46.5, 8.5, 5, 1.5)
    # λευκή πλακέτα polytech: οι χρωματιστές υποδοχές πάνω της, το LED μπροστά
    p.rr((240, 242, 238), 6, 37, 66, 4.5, 1.5, (150, 156, 164), 1)
    for i, (top, low) in enumerate((((250, 214, 40), (226, 52, 52)), ((52, 160, 76), (52, 160, 76)),
                                    ((250, 214, 40), (226, 52, 52)), ((70, 170, 230), (250, 214, 40)))):
        x = 9 + i * 11.5
        p.rr((36, 38, 44), x, 29, 9.5, 8.5, 1)
        p.rr(top, x + 0.8, 29.8, 3.8, 3.2, 0.6)
        p.rr(low, x + 4.9, 29.8, 3.8, 3.2, 0.6)
    p.circ(WHITE, 61, 33, 4.6)
    p.circ(led, 61, 33, 3.4)
    p.circ(WHITE, 60, 31.8, 1.1)
    # διάφανο ακρυλικό καπάκι (στον αέρα, οπότε το μισοδιάφανο απλώς δείχνει τι είναι πίσω)
    p.rr((220, 236, 255, 90), 4, 19, 70, 3.5, 1.2, (255, 255, 255, 230), 0.8)
    for x in (11.6, 64.6):
        p.circ((196, 200, 210), x, 18.6, 1.6)
    # μπροστά: γκρι μεταλλική βάση και πάνω της ο μπλε αισθητήρας με τα «μάτια» (το μακρινό λίγο πιο πίσω)
    p.rr((196, 200, 208), 73, 26, 4, 30, 1, (130, 134, 144), 0.8)
    p.rr((44, 104, 196), 77, 33, 9, 30, 2.5, INK)
    _eye(p, 91, 42, 7.5)
    _eye(p, 87, 54, 9.5)
    return p.done()


def _paint_wheel(size):
    """Η ρόδα σε τετράγωνο 0.44 x μέγεθος: μαύρο λάστιχο με αυλακώσεις, γκρι ζάντα με τρύπες."""
    side = size * 0.44
    p = _Pen(side, unit=size * 3 / 100)
    c = 22
    p.circ(INK, c, c, 21.6)
    p.circ((40, 42, 48), c, c, 20.4)
    for k in range(14):
        a = k * 2 * math.pi / 14
        p.line((72, 74, 84), [(c + 16 * math.cos(a), c + 16 * math.sin(a)),
                              (c + 19.6 * math.cos(a), c + 19.6 * math.sin(a))], 2.2)
    p.circ((70, 74, 84), c, c, 12.4)
    p.circ((116, 120, 132), c, c, 11.4)
    for k in range(3):
        a = k * 2 * math.pi / 3
        p.circ((34, 36, 42), c + 6.6 * math.cos(a), c + 6.6 * math.sin(a), 2.6)
    p.circ((176, 180, 192), c, c, 3.2)
    return p.done()


def body(size, led=LED_BLUE):
    return _cached(("body", size, tuple(led)), lambda: _paint_body(size, led))


def wheel(size):
    return _cached(("wheel", size), lambda: _paint_wheel(size))


def _blit_rotated(surf, img, center, angle):
    if abs(angle) > 0.3:
        img = pygame.transform.rotozoom(img, angle, 1.0)
    surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def draw_r2(surf, center, size, tilt=0.0, spin=0.0, led=LED_BLUE, upside_down=False):
    """Το R2 που τρέχει. tilt: μοίρες (θετικές = η μύτη πάνω). spin: πόσο έχει γυρίσει η ρόδα."""
    canvas = body(size, led).copy()
    w = pygame.transform.rotozoom(wheel(size), -spin, 1.0)
    canvas.blit(w, w.get_rect(center=(size * WHEEL_AT[0], size * WHEEL_AT[1])))
    if upside_down:
        canvas = pygame.transform.flip(canvas, False, True)
        tilt = -tilt
    _blit_rotated(surf, canvas, center, tilt)


def _paint_rocket(size, led, flame):
    """Ο πύραυλος με το R2 καβάλα. Το κουτί είναι 1.5 x 1.15 το μέγεθος του R2."""
    k = size / 100
    p = _Pen(size * 1.5, size * 1.15, unit=size * 3 / 100)
    # φλόγα πίσω
    L = 22 + flame * 10
    p.poly((255, 140, 40), [(18, 70), (18 - L, 79), (18, 88)])
    p.poly((255, 226, 90), [(18, 73), (18 - L * 0.6, 79), (18, 85)])
    # πίσω πτερύγιο (όρθιο) και ακροφύσιο
    p.poly((214, 52, 52), [(24, 66), (12, 44), (24, 44), (40, 64)])
    p.rr((120, 126, 140), 14, 69, 13, 20, 3, INK)
    # το R2 κάθεται πάνω: μόνο το σώμα του, τα κάτω τα κρύβει ο πύραυλος
    rb = pygame.transform.smoothscale(body(size, led), (round(size * 0.72 * 3), round(size * 0.72 * 3)))
    p.s.blit(rb, (round(44 * k * 3), round(16 * k * 3)))
    # σώμα και μύτη
    p.rr((240, 242, 248), 22, 64, 86, 32, 16, INK, 2)
    p.poly(INK, [(104, 63), (124, 68), (141, 80), (124, 92), (104, 97)])
    p.poly((230, 64, 60), [(106, 65.5), (123, 70), (137.5, 80), (123, 90), (106, 94.5)])
    p.rr((230, 64, 60), 30, 76, 74, 7, 3)
    p.circ(INK, 92, 80, 6.6)
    p.circ((90, 170, 255), 92, 80, 5.4)
    p.circ(WHITE, 90.4, 78.2, 1.7)
    # κάτω πτερύγιο
    p.poly((214, 52, 52), [(26, 92), (14, 112), (30, 112), (46, 94)])
    return p.done()


def draw_rocket(surf, center, size, tilt=0.0, time=0.0, led=LED_BLUE):
    """Το R2 στον πύραυλο. center = το κέντρο του κουτιού του R2 (το ίδιο σημείο με το draw_r2)."""
    flame = round((math.sin(time * 34) * 0.5 + 0.5) * 3) / 3
    img = _cached(("rocket", size, tuple(led), flame), lambda: _paint_rocket(size, led, flame))
    # το κουτί του πυραύλου ξεκινά λίγο πιο αριστερά από το κουτί του R2
    off = (size * 1.5 / 2 - size * 0.72, size * 1.15 / 2 - size * 0.62)
    ca, sa = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    c = (center[0] + off[0] * ca + off[1] * sa, center[1] - off[0] * sa + off[1] * ca)
    _blit_rotated(surf, img, c, tilt)


def charge_rings(surf, center, time, size):
    """Πράσινοι κύκλοι που απλώνουν γύρω από το R2 όσο φορτίζει."""
    x, y = round(center[0]), round(center[1])
    for k in range(2):
        t = (time * 1.2 + k * 0.5) % 1.0
        r = size * (0.45 + 0.5 * t)
        color = (70, 220, 110, int(170 * (1 - t)))
        for dr in (-1, 0, 1):
            pygame.gfxdraw.aacircle(surf, x, y, max(1, round(r + dr)), color)


def crash(surf, center, age, size, seed=7):
    """Το R2 χτύπησε: κομματάκια και αστεράκια που πετάγονται και σβήνουν (age σε δευτερόλεπτα)."""
    if age < 0 or age > 0.9:
        return
    rng = random.Random(seed)
    fade = 1 - age / 0.9
    cols = [(240, 242, 238), (250, 200, 40), (34, 35, 40), (214, 172, 76), (44, 104, 196)]
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi)
        v = rng.uniform(140, 380)
        x = center[0] + math.cos(a) * v * age
        y = center[1] + math.sin(a) * v * age + 500 * age * age
        s = rng.uniform(0.07, 0.16) * size
        rot = rng.uniform(-9, 9) * age
        ca, sn = math.cos(rot), math.sin(rot)
        pts = [(x + dx * ca - dy * sn, y + dx * sn + dy * ca) for dx, dy in ((-s, -s), (s, -s), (s, s), (-s, s))]
        col = cols[i % len(cols)]
        ui.fill_poly(surf, (*col, int(255 * fade)), pts)
    r = size * (0.3 + 0.5 * min(1.0, age / 0.3))
    for i in range(5):
        a = age * 4 + i * 2 * math.pi / 5
        ui.star(surf, (center[0] + r * math.cos(a), center[1] + r * math.sin(a)), size * 0.13,
                (255, 214, 60, int(255 * fade)), (200, 140, 20, int(255 * fade)))


# ------------------------------------------------------------ σκηνικό
def sky(theme, size):
    def make():
        w, h = size
        s = pygame.Surface(size)
        top, low = theme["sky"]
        for y in range(h):
            pygame.draw.line(s, ui.mix(top, low, y / h), (0, y), (w, y))
        return s
    return _cached(("sky", id(theme), size), make)


def gear(surf, center, r, teeth, angle, color):
    pts = []
    for i in range(teeth * 4):
        a = angle + i * math.pi * 2 / (teeth * 4)
        rr = r if (i % 4) in (1, 2) else r * 0.8
        pts.append((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a)))
    ui.fill_poly(surf, color, pts)
    hole = r * 0.32
    ui.circle(surf, color, center, hole * 1.5)


_GEARS = [(120, 210, 90, 12), (420, 150, 60, 10), (700, 260, 120, 14), (980, 170, 70, 10), (1180, 300, 100, 12),
          (300, 380, 50, 8), (860, 420, 56, 9)]


def background(surf, theme, cam_x, time, area):
    """Ουρανός με αχνά γρανάζια που γυρίζουν και κινούνται πιο αργά από το έδαφος (βάθος)."""
    area = pygame.Rect(area)
    surf.blit(sky(theme, area.size), area)
    span = area.w + 300
    for i, (x, y, r, teeth) in enumerate(_GEARS):
        gx = (x - cam_x * 0.15) % span - 150
        spin = time * (0.25 if i % 2 else -0.3) * 60 / r
        gear(surf, (area.x + gx, area.y + y), r, teeth, spin, (255, 255, 255, 34))


def menu_icon(surf, c, label, kind="bubble"):
    """Το εικονίδιο της κάρτας στο μενού: το R2 πηδά πάνω από αγκάθι προς μια φούσκα (ή πόρτα)."""
    x, y = c
    th = THEMES[0]
    pygame.draw.rect(surf, th["ground"], (x - 120, y + 50, 240, 12), border_radius=4)
    pygame.draw.line(surf, th["sky"][0], (x - 118, y + 50), (x + 118, y + 50), 3)
    spike(surf, x - 20, y + 50, th, h=42)
    draw_r2(surf, (x - 60, y + 2), 78, tilt=18, spin=20)
    if kind == "door":
        door(surf, (x + 36, y - 56, 64, 76), label)
        return
    bx, by = x + 66, y - 22
    ui.circle(surf, ui.shade(ORANGE, 0.75), (bx, by), 28)
    ui.circle(surf, ORANGE, (bx, by), 26)
    ui.circle(surf, WHITE, (bx, by), 21)
    ui.text(surf, label, (bx, by + 1), 26 if len(label) < 3 else 20, (36, 38, 52))


def ground(surf, theme, cam_x, top, bottom, width, ceiling=False):
    """Το πάτωμα (ή το ταβάνι, αν ceiling) με κουτάκια που κυλούν μαζί με τον κόσμο."""
    g = theme["ground"]
    rect = pygame.Rect(0, top, width, bottom - top)
    pygame.draw.rect(surf, g, rect)
    dark = ui.shade(g, 0.8)
    x0 = -(cam_x % TILE)
    edge = bottom if ceiling else top
    inner = top if ceiling else bottom
    for i in range(int(width / TILE) + 2):
        x = round(x0 + i * TILE)
        pygame.draw.line(surf, dark, (x, top), (x, bottom), 2)
    step = 1 if inner > edge else -1
    for k in range(10):
        y = edge + step * k
        pygame.draw.line(surf, ui.mix(g, theme["line"], 0.35 * (1 - k / 10)), (0, y), (width, y))
    pygame.draw.line(surf, theme["line"], (0, edge), (width, edge), 4)


def _shrink(pts, d):
    """Μικραίνει ένα κυρτό πολύγωνο προς το κέντρο του κατά d pixels (περίπου)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        n = math.hypot(dx, dy) or 1
        out.append((x - dx / n * d * 1.6, y - dy / n * d * 1.6))
    return out


def spike(surf, x, y, theme, down=False, h=None):
    """Αγκάθι πάνω στο πάτωμα: x = αριστερή άκρη του κουτιού, y = η γραμμή του πατώματος.
    Με down=True κρέμεται από ταβάνι (y = η κάτω γραμμή του ταβανιού)."""
    h = TILE * 0.9 if h is None else h
    s = -1 if down else 1
    pts = [(x + 4, y), (x + TILE / 2, y - s * h), (x + TILE - 4, y)]
    ui.fill_poly(surf, theme["line"], pts)
    ui.fill_poly(surf, theme["block"], _shrink(pts, 3.2))
    hi = [(x + TILE / 2, y - s * (h - 14)), (x + TILE / 2 + 7, y - s * (h * 0.42)), (x + TILE / 2 - 1, y - s * h * 0.36)]
    ui.fill_poly(surf, (*theme["line"], 70), hi)


def block(surf, rect, theme):
    """Κουτί (ένα ή πολλά στη σειρά): σκούρο με φωτεινό περίγραμμα και αχνές γραμμές ανά κουτάκι."""
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, theme["line"], r, border_radius=6)
    inner = r.inflate(-6, -6)
    pygame.draw.rect(surf, theme["block"], inner, border_radius=4)
    faint = ui.mix(theme["block"], theme["line"], 0.22)
    for x in range(r.x + TILE, r.right - 2, TILE):
        pygame.draw.line(surf, faint, (x, inner.y + 4), (x, inner.bottom - 5), 2)
    for y in range(r.y + TILE, r.bottom - 2, TILE):
        pygame.draw.line(surf, faint, (inner.x + 4, y), (inner.right - 5, y), 2)
    pygame.draw.rect(surf, faint, inner.inflate(-14, -14), width=2, border_radius=3)


def pad(surf, x, y, time=0.0, down=False):
    """Τραμπολίνο: κίτρινο μαξιλαράκι στο πάτωμα (x = αριστερή άκρη του κουτιού)."""
    s = -1 if down else 1
    cx = x + TILE / 2
    for k in range(2):
        t = (time * 1.6 + k * 0.5) % 1.0
        yy = y - s * (16 + t * 46)
        a = int(170 * (1 - t))
        ui.fill_poly(surf, (*YELLOW, a), [(cx - 16, yy + s * 9), (cx, yy - s * 5), (cx + 16, yy + s * 9),
                                          (cx + 16, yy + s * 15), (cx, yy + s * 1), (cx - 16, yy + s * 15)])
    pts = [(cx + 30 * math.cos(a), y - s * 20 * math.sin(a)) for a in (i * math.pi / 16 for i in range(17))]
    ui.fill_poly(surf, YELLOW_DARK, pts)
    ui.fill_poly(surf, YELLOW, _shrink(pts, 2))
    pygame.draw.line(surf, (255, 240, 170), (cx - 16, y - s * 11), (cx + 6, y - s * 14), 3)


def ring(surf, center, time=0.0, used=False):
    """Δαχτυλίδι άλματος: όταν το R2 περνά από μέσα και πατάς, πηδάει ξανά στον αέρα."""
    x, y = center
    pulse = 0.5 + 0.5 * math.sin(time * 6)
    col = (190, 190, 200) if used else YELLOW
    for dr in (0, 1, 2):
        pygame.gfxdraw.aacircle(surf, round(x), round(y), round(31 + pulse * 5 + dr), (*col, 150 - dr * 40))
    ui.circle(surf, YELLOW_DARK if not used else (130, 130, 140), center, 23)
    ui.circle(surf, col, center, 20)
    ui.circle(surf, (255, 246, 190) if not used else (226, 226, 232), center, 11)
    ui.circle(surf, WHITE, (x - 6, y - 7), 4)


def _portal_icon(surf, kind, c, s):
    x, y = c
    if kind in ("gravity_up", "gravity_down"):
        d = -1 if kind == "gravity_up" else 1
        ui.fill_poly(surf, WHITE, [(x - s * 0.36, y - d * s * 0.02), (x, y + d * s * 0.38), (x + s * 0.36, y - d * s * 0.02),
                                   (x + s * 0.14, y - d * s * 0.02), (x + s * 0.14, y - d * s * 0.38),
                                   (x - s * 0.14, y - d * s * 0.38), (x - s * 0.14, y - d * s * 0.02)])
    elif kind == "rocket":
        ui.fill_poly(surf, WHITE, [(x - s * 0.34, y - s * 0.12), (x + s * 0.18, y - s * 0.12), (x + s * 0.4, y),
                                   (x + s * 0.18, y + s * 0.12), (x - s * 0.34, y + s * 0.12)])
        ui.fill_poly(surf, WHITE, [(x - s * 0.3, y - s * 0.1), (x - s * 0.42, y - s * 0.34), (x - s * 0.16, y - s * 0.1)])
        ui.fill_poly(surf, WHITE, [(x - s * 0.3, y + s * 0.1), (x - s * 0.42, y + s * 0.34), (x - s * 0.16, y + s * 0.1)])
    else:
        ui.circle(surf, WHITE, c, s * 0.36)
        ui.circle(surf, PORTAL_COLORS["run"], c, s * 0.2)
        ui.circle(surf, WHITE, c, s * 0.08)


def portal(surf, center, kind, time=0.0, h=TILE * 3):
    """Πύλη (ψηλό οβάλ δαχτυλίδι). Αλλάζει τη βαρύτητα ή κάνει το R2 πύραυλο / ξανά ρόδες."""
    col = PORTAL_COLORS[kind]
    x, y = center
    w = 54
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (round(x), round(y))
    glow = pygame.Surface((w + 40, h + 40), pygame.SRCALPHA)
    a = 0.75 + 0.25 * math.sin(time * 5)
    light = ui.mix(col, WHITE, 0.5)
    for k, alpha in ((18, 50), (12, 90), (6, 140)):
        pygame.draw.ellipse(glow, (*light, int(alpha * a)), rect.inflate(2 * k, 2 * k).move(20 - rect.x, 20 - rect.y), 4)
    surf.blit(glow, glow.get_rect(center=rect.center))
    pygame.draw.ellipse(surf, ui.shade(col, 0.6), rect.inflate(6, 6))
    pygame.draw.ellipse(surf, col, rect)
    hole = pygame.Surface(rect.inflate(-22, -26).size, pygame.SRCALPHA)
    pygame.draw.ellipse(hole, (*ui.mix(col, WHITE, 0.6), 150), hole.get_rect())
    surf.blit(hole, hole.get_rect(center=rect.center))
    pygame.draw.ellipse(surf, ui.mix(col, WHITE, 0.45), rect.inflate(-8, -10), 3)
    rng = random.Random(int(x) // 7)
    for i in range(6):
        t = (time * 0.8 + rng.random()) % 1.0
        px = x + (rng.random() - 0.5) * 30
        py = y + (rng.random() - 0.5) * h * 0.8 * (1 - t)
        ui.circle(surf, (*WHITE, int(220 * (1 - t))), (px, py), 3)
    badge = (x, rect.y - 8)
    ui.circle(surf, ui.shade(col, 0.6), badge, 24)
    ui.circle(surf, col, badge, 21)
    _portal_icon(surf, kind, badge, 30)


def speed(surf, center, n=2, time=0.0):
    """Πύλη ταχύτητας: βελάκια ». Από εδώ και πέρα το R2 τρέχει πιο γρήγορα."""
    x, y = center
    col = (90, 230, 120) if n == 2 else (250, 140, 40)
    total = n * 26
    for i in range(n):
        cx = x - total / 2 + 13 + i * 26 + 4 * math.sin(time * 8 - i)
        pts = [(cx - 16, y - 40), (cx - 2, y - 40), (cx + 22, y), (cx - 2, y + 40), (cx - 16, y + 40), (cx + 8, y)]
        ui.fill_poly(surf, ui.shade(col, 0.6), [(px + 3, py + 3) for px, py in pts])
        ui.fill_poly(surf, col, pts)


def finish(surf, x, y, time=0.0, charging=False):
    """Το τέρμα: ο φορτιστής του R2 (x = αριστερή άκρη, y = η γραμμή του πατώματος)."""
    for i in range(4):
        for j in range(2):
            col = WHITE if (i + j) % 2 == 0 else INK
            pygame.draw.rect(surf, col, (x - 150 + i * 32, y - 2 + j * 0, 32, 6))
    base = pygame.Rect(x, y - 214, 96, 214)
    a = (150 if charging else 70) + 60 * math.sin(time * (8 if charging else 3))
    ui.glow(surf, base.inflate(30, 30), (120, 230, 150), a, radius=30)
    pygame.draw.rect(surf, (40, 140, 80), base.move(0, 4), border_radius=18)
    pygame.draw.rect(surf, (84, 200, 124), base, border_radius=18)
    scr = pygame.Rect(base.x + 14, base.y + 18, base.w - 28, 110)
    pygame.draw.rect(surf, (118, 220, 152), scr, border_radius=12)
    bolt = [(0.60, 0.10), (0.28, 0.56), (0.47, 0.56), (0.38, 0.90), (0.74, 0.40), (0.54, 0.40), (0.66, 0.10)]
    bc = (255, 248, 140) if charging and math.sin(time * 8) > 0 else WHITE
    ui.fill_poly(surf, bc, [(scr.x + scr.w * bx, scr.y + scr.h * by) for bx, by in bolt], (40, 140, 80))
    for i in range(3):
        on = charging or int(time * 3) % 3 == i
        ui.circle(surf, (255, 255, 200) if on else (60, 150, 90), (base.x + 26 + i * 22, base.y + 150), 7)
    pygame.draw.rect(surf, (52, 160, 96), (base.x + 18, base.y + 176, base.w - 36, 22), border_radius=8)


# ------------------------------------------------------------ τα μαθήματα
RED, GREEN, GREY = (226, 64, 60), (60, 182, 96), (178, 184, 198)


def bubble(surf, center, label, time=0.0, style="normal"):
    """Φούσκα με αριθμό ή γράμμα που μαζεύει το R2.
    style: normal, wrong (κόκκινη, κουνιέται), right (πράσινη, πάλλεται), faded (γκρι, μικρή)."""
    x, y = center
    bob = math.sin(time * 3 + x * 0.01) * 4
    r = 31
    color = ORANGE
    if style == "wrong":
        color = RED
        x += math.sin(time * 40) * 4
        bob = 0
    elif style == "right":
        color = GREEN
        r = 31 + 3 * math.sin(time * 8)
    elif style == "faded":
        color = GREY
        r = 24
    c = (x, y + bob)
    if style != "faded":
        g = pygame.Surface((96, 96), pygame.SRCALPHA)
        glow = (255, 255, 255) if style == "normal" else ui.mix(color, WHITE, 0.4)
        pygame.draw.circle(g, (*glow, 70 + int(30 * math.sin(time * 4))), (48, 48), r + 15)
        surf.blit(g, g.get_rect(center=(round(c[0]), round(c[1]))))
    ui.circle(surf, ui.shade(color, 0.75), c, r + 2)
    ui.circle(surf, color, c, r)
    ui.circle(surf, WHITE, c, r - 6)
    size = (34 if len(label) < 3 else 26) * r / 31
    ui.text(surf, label, (c[0], c[1] + 1), size, (36, 38, 52) if style != "faded" else (140, 146, 160))


def pop(surf, center, age, color=GREEN):
    """Η φούσκα «σκάει» όταν την πιάνει το R2: κύκλος που ανοίγει και αστεράκια."""
    if age < 0 or age > 0.5:
        return
    k = age / 0.5
    a = int(255 * (1 - k))
    x, y = center
    r = 30 + 40 * k
    for dr in (0, 1, 2, 3):
        pygame.gfxdraw.aacircle(surf, round(x), round(y), round(r + dr), (*color, a))
    for i in range(6):
        ang = i * math.pi / 3 + 0.4
        d = 26 + 60 * k
        ui.star(surf, (x + d * math.cos(ang), y + d * math.sin(ang)), 9 * (1 - k * 0.5),
                (255, 214, 60, a), (200, 140, 20, a))


def door(surf, rect, label, time=0.0, style="normal"):
    """Πόρτα με αριθμό για τις Πράξεις: το R2 περνά από μέσα της.
    style: normal (κίτρινη), wrong (κόκκινη, κουνιέται), right (πράσινη, πάλλεται), faded (γκρι)."""
    r = pygame.Rect(rect)
    frame, dark = YELLOW, YELLOW_DARK
    if style == "wrong":
        frame, dark = RED, ui.shade(RED, 0.7)
        r.x += round(math.sin(time * 40) * 4)
    elif style == "right":
        frame, dark = GREEN, ui.shade(GREEN, 0.7)
        r.inflate_ip(round(4 + 4 * math.sin(time * 8)), round(4 + 4 * math.sin(time * 8)))
    elif style == "faded":
        frame, dark = GREY, ui.shade(GREY, 0.8)
    shine = pygame.Surface(r.size, pygame.SRCALPHA)
    alpha = 30 if style == "faded" else 60 + int(25 * math.sin(time * 4))
    pygame.draw.rect(shine, (*ui.mix(frame, WHITE, 0.7), alpha), shine.get_rect(), border_radius=14)
    surf.blit(shine, r)
    pygame.draw.rect(surf, dark, r.move(0, 3), width=10, border_radius=14)
    pygame.draw.rect(surf, frame, r, width=9, border_radius=14)
    c = r.center
    rad = min(32, r.h // 2 - 12)
    ui.circle(surf, dark, c, rad + 3)
    ui.circle(surf, WHITE, c, rad)
    size = (34 if len(label) < 3 else 27) * rad / 32
    ui.text(surf, label, (c[0], c[1] + 1), size, (36, 38, 52) if style != "faded" else (150, 156, 170))


def _turtle(surf, c, s):
    x, y = c
    green, shell, dark = (120, 196, 96), (66, 150, 84), (36, 96, 52)
    for dx in (-0.2, 0.16):
        ui.circle(surf, green, (x + dx * s, y + 0.2 * s), 0.1 * s, dark)
    ui.circle(surf, green, (x + 0.36 * s, y + 0.04 * s), 0.13 * s, dark)
    ui.circle(surf, INK, (x + 0.41 * s, y + 0.01 * s), max(1.5, 0.03 * s))
    ui.fill_poly(surf, green, [(x - 0.4 * s, y + 0.12 * s), (x - 0.52 * s, y + 0.2 * s), (x - 0.36 * s, y + 0.2 * s)], dark)
    pts = [(x - 0.02 * s + 0.36 * s * math.cos(t), y + 0.2 * s - 0.36 * s * math.sin(t))
           for t in (i * math.pi / 20 for i in range(21))]
    ui.fill_poly(surf, shell, pts, dark)
    for dx, dy in ((-0.14, 0.04), (0.1, 0.04), (-0.02, -0.06)):
        ui.circle(surf, ui.mix(shell, (255, 255, 255), 0.3), (x + dx * s, y + dy * s), 0.06 * s)
    pygame.draw.line(surf, (200, 220, 110), (x - 0.38 * s, y + 0.2 * s), (x + 0.34 * s, y + 0.2 * s),
                     max(2, round(0.05 * s)))


def speed_icon(surf, c, s, level, time=0.0):
    """Το εικονίδιο της ταχύτητας: 0 χελώνα (αργά), 1 το R2 (κανονικά), 2 πύραυλος (γρήγορα)."""
    if level == 0:
        _turtle(surf, c, s * 1.1)
    elif level == 1:
        draw_r2(surf, (c[0], c[1] + s * 0.04), max(8, round(s * 0.95)))
    else:
        draw_rocket(surf, (c[0] + s * 0.06, c[1] + s * 0.06), max(8, round(s * 0.72)), tilt=12, time=time)


def progress(surf, rect, frac, color):
    """Η μπάρα που δείχνει πόσο έχει προχωρήσει η πίστα, με το ποσοστό."""
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, (214, 220, 232), r, border_radius=r.h // 2)
    if frac > 0:
        f = r.copy()
        f.w = max(r.h, round(r.w * min(1.0, frac)))
        pygame.draw.rect(surf, color, f, border_radius=r.h // 2)
        pygame.draw.rect(surf, ui.mix(color, WHITE, 0.35), (f.x + 8, f.y + 4, f.w - 16, 4), border_radius=2)
    pygame.draw.rect(surf, (170, 180, 198), r, width=2, border_radius=r.h // 2)
    ui.text(surf, f"{round(frac * 100)}%", (r.right + 34, r.centery), 20, (44, 54, 76))


def numbers_panel(surf, center, label, seq, got, time=0.0):
    """Ο κανόνας (π.χ. «Ανά 2:») και τα κυκλάκια: πράσινα όσα μαζεύτηκαν, πορτοκαλί «?» ο επόμενος."""
    img = ui.font(24).render(label, True, (44, 54, 76))
    step = 52
    rect = pygame.Rect(0, 0, img.get_width() + 44 + step * len(seq), 66)
    rect.center = center
    ui.panel(surf, rect, WHITE, radius=18)
    surf.blit(img, img.get_rect(midleft=(rect.x + 20, rect.centery)))
    x0 = rect.x + img.get_width() + 34
    for i, n in enumerate(seq):
        c = (x0 + i * step + step / 2 - 4, rect.centery)
        r = 22
        if i < got:
            ui.circle(surf, (70, 190, 104), c, r, (46, 140, 74))
            ui.text(surf, str(n), c, 19 if n < 100 else 15, WHITE)
        elif i == got:
            p = 2 * math.sin(time * 6)
            ui.circle(surf, ORANGE, c, r + 3 + p)
            ui.circle(surf, WHITE, c, r - 1 + p)
            ui.text(surf, "?", c, 20, ORANGE)
        else:
            ui.circle(surf, (232, 236, 244), c, r)


def word_panel(surf, center, word, got, picture, time=0.0):
    """Η ζωγραφιά της λέξης και τα κουτάκια των γραμμάτων: γραμμένα όσα μαζεύτηκαν.
    picture(surf, rect) ζωγραφίζει τη ζωγραφιά μέσα στο rect."""
    bw = 50 if len(word) <= 10 else 44
    rect = pygame.Rect(0, 0, 112 + len(word) * (bw + 8), 96)
    rect.center = center
    x, y = rect.topleft
    ui.panel(surf, rect, WHITE, radius=18)
    pic = pygame.Rect(x + 12, y + 10, 76, 76)
    pygame.draw.rect(surf, (240, 244, 252), pic, border_radius=14)
    picture(surf, pic.inflate(-4, -4))
    for i, ch in enumerate(word):
        r = pygame.Rect(x + 100 + i * (bw + 8), y + 18, bw, 60)
        if i < got:
            pygame.draw.rect(surf, (226, 246, 232), r, border_radius=10)
            pygame.draw.rect(surf, (70, 190, 104), r, width=3, border_radius=10)
            ui.text(surf, ch, r.center, 34, (36, 110, 64))
        elif i == got:
            pygame.draw.rect(surf, (255, 244, 230), r, border_radius=10)
            pygame.draw.rect(surf, ORANGE, r, width=4, border_radius=10)
            ui.text(surf, "?", r.center, 32, ORANGE)
        else:
            pygame.draw.rect(surf, (236, 240, 246), r, border_radius=10)
            pygame.draw.line(surf, (170, 178, 194), (r.x + 12, r.bottom - 14), (r.right - 12, r.bottom - 14), 3)


def math_panel(surf, center, question, got, total, solved=False, time=0.0):
    """Η πράξη με μεγάλα γράμματα (π.χ. «3 + 4 = ?») και κυκλάκια για όσες λύθηκαν.
    solved: η πράξη μόλις λύθηκε και γράφεται ολόκληρη, πράσινη (π.χ. «3 + 4 = 7»)."""
    if solved:
        parts = [(question, (46, 140, 74))]
    else:
        left, _, right = question.partition("?")
        parts = [(left, (36, 38, 52)), ("?", ORANGE), (right, (36, 38, 52))]
    imgs = [ui.font(46).render(t, True, col) for t, col in parts if t]
    tw = sum(i.get_width() for i in imgs)
    dots = total * 24
    rect = pygame.Rect(0, 0, max(300, tw) + dots + 90, 76)
    rect.center = center
    ui.panel(surf, rect, WHITE, radius=18)
    x = rect.x + 28 + (max(300, tw) - tw) // 2
    for img in imgs:
        surf.blit(img, img.get_rect(midleft=(x, rect.centery)))
        x += img.get_width()
    x0 = rect.right - 34 - (total - 1) * 24
    pygame.draw.line(surf, (226, 230, 238), (x0 - 30, rect.y + 14), (x0 - 30, rect.bottom - 14), 2)
    for i in range(total):
        c = (x0 + i * 24, rect.centery)
        if i < got:
            ui.circle(surf, (70, 190, 104), c, 9, (46, 140, 74))
        elif i == got:
            ui.circle(surf, ORANGE, c, 10 + math.sin(time * 6))
            ui.circle(surf, WHITE, c, 6)
        else:
            ui.circle(surf, (226, 230, 238), c, 8)
