"""Τα γραφικά του Εργοστασίου: ο τοίχος, η ταινία, τα κουτιά, το κόκκινο κουτί για ό,τι πέφτει
και το R2 πάνω στη βάση του (το ίδιο R2 από το πλάι με τα παιχνίδια τρεξίματος, γυρισμένο αριστερά).
"""
import math

import pygame

from core import ui
from core.app import HEIGHT, WIDTH
from games.runner import art as rart
from . import items, logic
from .catalog import BOX_NAMES, HW, OTHER, SW

TOP_H = 92
FLOOR_Y = 662
BELT_Y = 300                 # η πάνω επιφάνεια της ταινίας
BELT_LEFT = 40
BELT_END = logic.BELT_END
ITEM = 104                   # το μέγεθος ενός αντικειμένου πάνω στην ταινία
ITEM_Y = BELT_Y - ITEM // 2 + 4
LOST_BIN = pygame.Rect(BELT_END - 10, 560, 150, FLOOR_Y - 560)
R2_SIZE = 150
R2_POS = (1192, BELT_Y - R2_SIZE * 0.49)
HATCH = pygame.Rect(-20, 150, 96, BELT_Y - 150 + 4)
INK = (24, 26, 34)
TEXT = (44, 54, 76)
WHITE = (255, 255, 255)
LED_ORANGE = (255, 160, 40)
BOX_COLORS = {HW: (62, 132, 222), SW: (150, 104, 206), OTHER: (70, 166, 90)}
KEY_DIR = {HW: "left", SW: "down", OTHER: "right"}
YELLOW_GLOW, GREEN_GLOW, RED_GLOW = (255, 214, 60), (80, 220, 120), (240, 70, 60)


# ------------------------------------------------------------ τοίχος
_bg = {}


def _paint_wall():
    s = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        k = max(0.0, min(1.0, (y - TOP_H) / (FLOOR_Y - TOP_H)))
        pygame.draw.line(s, ui.mix((222, 230, 240), (196, 208, 224), k), (0, y), (WIDTH, y))
    for x in range(0, WIDTH, 160):
        pygame.draw.line(s, (206, 216, 230), (x, 0), (x, FLOOR_Y), 2)
    for x in range(150, WIDTH, 320):
        r = pygame.Rect(x, 112, 180, 92)
        pygame.draw.rect(s, (176, 190, 210), r.inflate(12, 12), border_radius=8)
        pygame.draw.rect(s, (236, 246, 255), r, border_radius=4)
        pygame.draw.line(s, (176, 190, 210), (r.centerx, r.y), (r.centerx, r.bottom), 6)
        pygame.draw.line(s, (176, 190, 210), (r.x, r.centery), (r.right, r.centery), 6)
    pygame.draw.rect(s, (160, 172, 192), (0, 96, WIDTH, 10))
    for x in range(40, WIDTH, 200):
        pygame.draw.rect(s, (140, 152, 172), (x, 93, 14, 16), border_radius=3)
    # το πάτωμα με την κίτρινη-μαύρη γραμμή ασφαλείας
    pygame.draw.rect(s, (96, 104, 120), (0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))
    pygame.draw.rect(s, (120, 128, 146), (0, FLOOR_Y, WIDTH, 6))
    for x in range(-40, WIDTH, 56):
        y0, y1 = FLOOR_Y + 6, FLOOR_Y + 16
        ui.fill_poly(s, (252, 206, 54), [(x, y0), (x + 28, y0), (x + 18, y1), (x - 10, y1)])
        ui.fill_poly(s, (30, 32, 40), [(x + 28, y0), (x + 56, y0), (x + 46, y1), (x + 18, y1)])
    for x in range(30, WIDTH, 90):
        pygame.draw.line(s, (88, 96, 112), (x, FLOOR_Y + 22), (x - 30, HEIGHT), 2)
    return s


_GEARS = ((90, 430, 70, 12), (1210, 140, 54, 10), (640, 520, 90, 14), (360, 230, 44, 9), (1090, 470, 60, 11))


def background(s, time=0.0):
    if "wall" not in _bg:
        _bg["wall"] = _paint_wall()
    s.blit(_bg["wall"], (0, 0))
    for i, (x, y, r, teeth) in enumerate(_GEARS):
        rart.gear(s, (x, y), r, teeth, time * (0.3 if i % 2 else -0.3), (255, 255, 255, 60))


def hazard(s, rect, w=22):
    """Κίτρινες-μαύρες λωρίδες."""
    rect = pygame.Rect(rect)
    clip = s.get_clip()
    s.set_clip(rect.clip(clip) if clip else rect)
    s.fill((252, 206, 54), rect)
    for x in range(rect.x - rect.h, rect.right + rect.h, w * 2):
        ui.fill_poly(s, (30, 32, 40), [(x, rect.bottom), (x + w, rect.bottom), (x + w + rect.h, rect.y),
                                       (x + rect.h, rect.y)])
    s.set_clip(clip)


# ------------------------------------------------------------- ταινία
def hatch_back(s):
    """Το άνοιγμα στον τοίχο απ' όπου έρχονται τα αντικείμενα."""
    hazard(s, HATCH.inflate(20, 20).move(0, -6))
    pygame.draw.rect(s, (40, 44, 56), HATCH, border_radius=8)


def hatch_front(s):
    """Η κουρτίνα από πλαστικές λωρίδες μπροστά στο άνοιγμα (τα αντικείμενα περνούν από μέσα)."""
    strips = pygame.Surface(HATCH.size, pygame.SRCALPHA)
    for i in range(6):
        pygame.draw.rect(strips, (120, 150, 190, 150), (4 + i * 15, 0, 12, HATCH.h - 4), border_radius=3)
        pygame.draw.rect(strips, (190, 214, 240, 160), (6 + i * 15, 0, 3, HATCH.h - 8))
    s.blit(strips, HATCH)
    pygame.draw.rect(s, (60, 66, 82), (HATCH.x, HATCH.y, HATCH.w, 10))


def belt(s, distance=0.0, warn=0.0):
    """Τα πόδια, ο σκελετός με τους κυλίνδρους και η λαστιχένια ταινία. distance: πόσο έχει κυλήσει.
    warn 0..1: πόσο κόκκινο ανάβει στο τέλος της ταινίας (κάτι πλησιάζει να πέσει)."""
    for x in (150, 520, 880):
        pygame.draw.rect(s, (110, 120, 140), (x, BELT_Y + 40, 18, FLOOR_Y - BELT_Y - 40))
        pygame.draw.rect(s, (90, 98, 116), (x - 10, FLOOR_Y - 8, 38, 8), border_radius=3)
    frame = pygame.Rect(BELT_LEFT, BELT_Y + 14, BELT_END - BELT_LEFT, 34)
    pygame.draw.rect(s, (96, 108, 130), frame.move(0, 4), border_radius=10)
    pygame.draw.rect(s, (130, 144, 168), frame, border_radius=10)
    turn = distance / 11
    for x in range(70, BELT_END, 64):
        c = (x, frame.centery)
        ui.circle(s, (70, 78, 96), c, 11)
        for k in range(3):
            a = turn + k * 2 * math.pi / 3
            pygame.draw.line(s, (120, 130, 150), c, (x + 9 * math.cos(a), c[1] + 9 * math.sin(a)), 2)
        ui.circle(s, (170, 180, 200), c, 4)
    band = pygame.Rect(BELT_LEFT, BELT_Y, BELT_END - BELT_LEFT, 16)
    pygame.draw.rect(s, (52, 56, 68), band, border_radius=8)
    off = distance % 48
    for x in range(BELT_LEFT - 48, BELT_END, 48):
        xx = x + off
        if BELT_LEFT + 10 < xx < BELT_END - 20:
            pygame.draw.lines(s, (88, 94, 112), False, [(xx, band.y + 3), (xx + 7, band.centery), (xx, band.bottom - 3)], 3)
    end = (BELT_END, BELT_Y + 22)
    if warn > 0:
        g = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(g, (*RED_GLOW, int(150 * warn)), (60, 60), 56)
        s.blit(g, g.get_rect(center=end))
    ui.circle(s, (40, 44, 56), end, 24)
    for k in range(3):
        a = turn * 0.45 + k * 2 * math.pi / 3
        pygame.draw.line(s, (90, 98, 116), end, (end[0] + 19 * math.cos(a), end[1] + 19 * math.sin(a)), 4)
    ui.circle(s, (150, 160, 180), end, 8)


def item(s, key, center, scale=1.0, angle=0.0, alpha=255, shadow_y=None):
    """Ένα αντικείμενο με κέντρο center. shadow_y: σκιά από κάτω (πάνω στην ταινία)."""
    size = round(ITEM * scale)
    if shadow_y is not None:
        sh = pygame.Surface((size, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect())
        s.blit(sh, sh.get_rect(center=(round(center[0]), round(shadow_y))))
    img = items.image(key, size)
    if angle:
        img = pygame.transform.rotozoom(img, angle, 1.0)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(max(0, alpha))
    s.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def halo(s, center, r, color, alpha):
    g = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
    pygame.draw.circle(g, (*color, max(0, min(255, int(alpha)))), (r + 2, r + 2), r)
    s.blit(g, g.get_rect(center=(round(center[0]), round(center[1]))))


def marker(s, x, time, color=(252, 196, 40)):
    """Το βελάκι πάνω από το αντικείμενο που θα στείλουν τα βελάκια του πληκτρολογίου."""
    y = BELT_Y - ITEM - 22 + 6 * math.sin(time * 6)
    ui.fill_poly(s, color, [(x - 17, y - 17), (x + 17, y - 17), (x, y + 4)], INK)


# --------------------------------------------------------- τα κουτιά
def keycap(s, center, d, size=1.0):
    """Μικρό πλήκτρο με βελάκι: ποιο βελάκι του πληκτρολογίου στέλνει σε αυτό το κουτί."""
    r = pygame.Rect(0, 0, round(36 * size), round(32 * size))
    r.center = (round(center[0]), round(center[1]))
    pygame.draw.rect(s, (150, 156, 170), r.move(0, 4), border_radius=7)
    pygame.draw.rect(s, WHITE, r, border_radius=7)
    pygame.draw.rect(s, (150, 156, 170), r, width=1, border_radius=7)
    x, y = r.center
    dx, dy = {"left": (-1, 0), "right": (1, 0), "down": (0, 1)}[d]
    px, py, k = -dy, dx, size
    pygame.draw.line(s, (60, 66, 84), (x - dx * 9 * k, y - dy * 9 * k), (x + dx * 2 * k, y + dy * 2 * k), max(2, round(3 * k)))
    ui.fill_poly(s, (60, 66, 84), [(x + dx * 10 * k, y + dy * 10 * k), (x + px * 7 * k + dx, y + py * 7 * k + dy),
                                   (x - px * 7 * k + dx, y - py * 7 * k + dy)])


def label(s, kind, center, w=None, key=True, size=30):
    """Η χρωματιστή ταμπέλα με το όνομα του κουτιού (και το πλήκτρο του, αν key)."""
    name, col = BOX_NAMES[kind], BOX_COLORS[kind]
    img = ui.font(size).render(name, True, WHITE)
    room = 52 if key else 0
    if w and img.get_width() + room + 24 > w:
        size = int(size * (w - room - 24) / img.get_width())
        img = ui.font(size).render(name, True, WHITE)
    w = w or img.get_width() + 40 + room
    r = pygame.Rect(0, 0, w, size + 22)
    r.center = (round(center[0]), round(center[1]))
    pygame.draw.rect(s, ui.shade(col, 0.7), r.move(0, 4), border_radius=14)
    pygame.draw.rect(s, col, r, border_radius=14)
    pygame.draw.rect(s, ui.mix(col, WHITE, 0.25), (r.x + 8, r.y + 4, r.w - 16, 5), border_radius=3)
    s.blit(img, img.get_rect(center=(r.centerx + room // 2, r.centery + 1)))
    if key:
        keycap(s, (r.x + 26, r.centery), KEY_DIR[kind], 0.85)
    return r


class Box:
    """Ένα από τα κουτιά κάτω από την ταινία. cx: το κέντρο του, w: το πλάτος του."""

    def __init__(self, kind, cx, w):
        self.kind = kind
        self.cx = cx
        self.w = w

    def mouth(self):
        """Πού πέφτουν μέσα τα αντικείμενα."""
        if self.kind == HW:
            return self.cx, FLOOR_Y - 4 - 168 + 10
        if self.kind == SW:
            return self.cx, FLOOR_Y - 70 - 75
        return self.cx, FLOOR_Y - 18 - 176 + 4

    def outline(self):
        """Το σχήμα του κουτιού (για τη λάμψη γύρω του)."""
        if self.kind == HW:
            return pygame.Rect(self.cx - self.w / 2 - 5, FLOOR_Y - 4 - 168 - 50, self.w + 10, 168 + 60)
        if self.kind == SW:
            return pygame.Rect(self.cx - self.w / 2 - 5, FLOOR_Y - 70 - 160, self.w + 10, 170)
        top = self.w * 0.86
        return pygame.Rect(self.cx - top / 2, FLOOR_Y - 18 - 176 - 40, top, 176 + 50)

    def draw_back(self, s, peek=(), dx=0, dy=0):
        """Ό,τι φαίνεται πίσω/μέσα στο κουτί (τα τελευταία αντικείμενα που μπήκαν)."""
        cx = self.cx + dx
        if self.kind == HW:
            top = FLOOR_Y - 4 - 168 + dy
            for i, key in enumerate(peek[-2:]):
                img = pygame.transform.rotate(items.image(key, 86), (-12, 14)[i % 2])
                s.blit(img, img.get_rect(midbottom=(cx - self.w * 0.17 + self.w * 0.34 * i, top + 30)))
        elif self.kind == OTHER and peek:
            top = FLOOR_Y - 18 - 176 + dy
            img = pygame.transform.rotate(items.image(peek[-1], 80), 10)
            s.blit(img, img.get_rect(midbottom=(cx, top + 30)))

    def draw(self, s, glow=None, glow_alpha=170, dx=0, dy=0, apps=(), flash=0.0):
        cx = self.cx + dx
        if glow:
            ui.glow(s, self.outline().move(dx, dy).inflate(30, 30), glow, glow_alpha, radius=26)
        if self.kind == HW:
            self._crate(s, cx, dy)
        elif self.kind == SW:
            self._computer(s, cx, dy, apps, flash)
        else:
            self._bin(s, cx, dy)

    def _crate(self, s, cx, dy):
        w, h = self.w, 168
        body = pygame.Rect(0, 0, w, h)
        body.midbottom = (cx, FLOOR_Y - 4 + dy)
        brown, dark, flap = (214, 160, 100), (172, 120, 70), (196, 142, 84)
        ui.fill_poly(s, flap, [(body.x, body.y), (body.x - 34, body.y - 46), (body.x + w * 0.3, body.y - 50),
                               (body.x + w * 0.4, body.y)], INK)
        ui.fill_poly(s, flap, [(body.right, body.y), (body.right + 34, body.y - 46), (body.right - w * 0.3, body.y - 50),
                               (body.right - w * 0.4, body.y)], INK)
        pygame.draw.rect(s, dark, body.move(0, 4), border_radius=6)
        pygame.draw.rect(s, brown, body, border_radius=6)
        pygame.draw.rect(s, INK, body, 3, border_radius=6)
        pygame.draw.rect(s, (230, 196, 140), (body.centerx - 26, body.y + 2, 52, 48))
        label(s, HW, (body.centerx, body.y + 98), w - 50)

    def _computer(self, s, cx, dy, apps, flash):
        w = self.w
        scr = pygame.Rect(0, 0, w, 150)
        scr.midbottom = (cx, FLOOR_Y - 70 + dy)
        base = pygame.Rect(0, 0, 150, 14)
        base.midbottom = (cx, FLOOR_Y - 4)
        neck = pygame.Rect(cx - 16, scr.bottom, 32, base.y - scr.bottom)
        pygame.draw.rect(s, (110, 116, 132), neck)
        pygame.draw.rect(s, INK, neck, 2)
        pygame.draw.rect(s, (76, 80, 94), base, border_radius=6)
        pygame.draw.rect(s, INK, base, 2, border_radius=6)
        pygame.draw.rect(s, (44, 46, 56), scr, border_radius=14)
        pygame.draw.rect(s, INK, scr, 3, border_radius=14)
        inner = scr.inflate(-22, -22)
        pygame.draw.rect(s, ui.mix((70, 140, 226), (150, 220, 255), flash), inner, border_radius=6)
        # τα προγράμματα που έχουν ήδη μπει στον υπολογιστή, σαν εικονίδια στην οθόνη του
        per_row = max(1, (inner.w - 8) // 62)
        size = 52
        for i, key in enumerate(apps[-2 * per_row:]):
            r, c = divmod(i, per_row)
            s.blit(items.image(key, size), (inner.x + 8 + c * 62, inner.y + 6 + r * 58))
        label(s, SW, (cx, scr.bottom + 34), w - 40)

    def _bin(self, s, cx, dy):
        w, h = self.w, 176
        top_w, bot_w = w * 0.86, w * 0.7
        y0, y1 = FLOOR_Y - 18 - h + dy, FLOOR_Y - 18 + dy
        green, dark = BOX_COLORS[OTHER], (46, 120, 62)
        for x in (cx - bot_w / 2 + 14, cx + bot_w / 2 - 14):
            ui.circle(s, INK, (x, FLOOR_Y - 14), 14)
            ui.circle(s, (120, 126, 140), (x, FLOOR_Y - 14), 6)
        ui.fill_poly(s, green, [(cx - top_w / 2, y0 + 10), (cx + top_w / 2, y0 + 10), (cx + bot_w / 2, y1),
                                (cx - bot_w / 2, y1)], INK)
        rim = pygame.Rect(cx - top_w / 2 - 6, y0 + 4, top_w + 12, 18)
        pygame.draw.rect(s, dark, rim, border_radius=6)
        pygame.draw.rect(s, INK, rim, 2, border_radius=6)
        for k in (-0.22, 0, 0.22):
            pygame.draw.line(s, dark, (cx + k * top_w, y0 + 36), (cx + k * bot_w * 1.1, y1 - 70), 5)
        label(s, OTHER, (cx, y1 - 38), bot_w - 4)

    def draw_lid(self, s, dx=0, dy=0):
        """Το καπάκι του κάδου, ανοιχτό προς τα πίσω (ζωγραφίζεται πριν από ό,τι πέφτει μέσα)."""
        if self.kind != OTHER:
            return
        cx = self.cx + dx
        top_w = self.w * 0.86
        y0 = FLOOR_Y - 18 - 176 + dy
        ui.fill_poly(s, (46, 120, 62), [(cx - top_w / 2 - 6, y0), (cx + top_w / 2 + 6, y0),
                                        (cx + top_w / 2 - 4, y0 - 34), (cx - top_w / 2 + 4, y0 - 34)], INK)
        ui.fill_poly(s, (30, 70, 40), [(cx - top_w / 2 + 6, y0 + 2), (cx + top_w / 2 - 6, y0 + 2),
                                       (cx + top_w / 2 - 10, y0 + 14), (cx - top_w / 2 + 10, y0 + 14)])


def lost_bin(s, pile=(), warn=0.0):
    """Το κόκκινο κουτί κάτω από το τέλος της ταινίας: εκεί πέφτει ό,τι δεν πρόλαβε το παιδί."""
    r = LOST_BIN
    for i, key in enumerate(pile[-3:]):
        img = pygame.transform.rotozoom(items.image(key, 80), (-25, 15, -8)[i % 3], 1.0)
        s.blit(img, img.get_rect(center=(r.x + 40 + i * 36, r.y - 6 + (i % 2) * 8)))
    if warn > 0:
        ui.glow(s, r.inflate(24, 24), RED_GLOW, 140 * warn, radius=18)
    pygame.draw.rect(s, (150, 40, 40), r.move(0, 4), border_radius=10)
    pygame.draw.rect(s, (214, 64, 60), r, border_radius=10)
    pygame.draw.rect(s, (236, 110, 100), (r.x + 8, r.y + 6, r.w - 16, 6), border_radius=3)
    c = (r.centerx, r.centery + 6)
    ui.fill_poly(s, (255, 236, 120) if warn > 0.5 else WHITE,
                 [(c[0], c[1] - 30), (c[0] + 32, c[1] + 24), (c[0] - 32, c[1] + 24)], INK)
    ui.text(s, "!", (c[0], c[1] + 6), 34, INK)


def lost_mouth():
    return LOST_BIN.centerx, LOST_BIN.y + 6


# ----------------------------------------------------------------- R2
def r2_stand(s):
    pillar = pygame.Rect(1158, BELT_Y + 14, 70, FLOOR_Y - BELT_Y - 14)
    pygame.draw.rect(s, (110, 120, 140), pillar)
    pygame.draw.rect(s, (90, 98, 116), (pillar.x - 14, FLOOR_Y - 8, pillar.w + 28, 8), border_radius=3)
    top = pygame.Rect(1124, BELT_Y, 140, 22)
    hazard(s, top)
    pygame.draw.rect(s, INK, top, 2)


def r2(s, led=rart.LED_BLUE, hop=0.0, tilt=0.0, rings=False, time=0.0):
    """Το R2 πάνω στη βάση του, γυρισμένο προς την ταινία (αριστερά)."""
    c = (R2_POS[0], R2_POS[1] - hop)
    if rings:
        rart.charge_rings(s, c, time, R2_SIZE)
    canvas = rart.body(R2_SIZE, led).copy()
    wheel = rart.wheel(R2_SIZE)
    canvas.blit(wheel, wheel.get_rect(center=(R2_SIZE * rart.WHEEL_AT[0], R2_SIZE * rart.WHEEL_AT[1])))
    canvas = pygame.transform.flip(canvas, True, False)
    if abs(tilt) > 0.3:
        canvas = pygame.transform.rotozoom(canvas, tilt, 1.0)
    s.blit(canvas, canvas.get_rect(center=(round(c[0]), round(c[1]))))


def bubble(s, line1, line2, color1=rart.RED, right=1100, y=102, w=850):
    """Το R2 μιλάει: λευκό συννεφάκι με μύτη προς το R2 (δεξιά)."""
    rect = pygame.Rect(right - w, y, w, 92)
    ui.panel(s, rect, WHITE, radius=24, border=(214, 222, 236))
    tail = [(rect.right - 3, rect.y + 34), (rect.right + 46, rect.y + 70), (rect.right - 3, rect.y + 62)]
    ui.fill_poly(s, WHITE, tail)
    pygame.draw.lines(s, (214, 222, 236), False, tail, 3)
    fit_text(s, line1, (rect.centerx, rect.y + 28), 30, color1, w - 40)
    fit_text(s, line2, (rect.centerx, rect.y + 66), 26, TEXT, w - 40)


def fit_text(s, text, pos, size, color, max_w):
    """Κείμενο που μικραίνει αν δεν χωράει στο πλάτος max_w."""
    w = ui.font(size).size(text)[0]
    if w > max_w:
        size = max(12, int(size * max_w / w))
    return ui.text(s, text, pos, size, color)


# --------------------------------------------------------- πάνω μπάρα
def heart(s, c, r, full=True, glow=0.0):
    x, y = c
    col = (236, 64, 80) if full else (214, 220, 232)
    pts = []
    for i in range(41):
        a = i / 40 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((x + hx * r / 17, y + hy * r / 17))
    if glow > 0:
        halo(s, c, round(r * 1.6), (255, 214, 60), 200 * glow)
    ui.fill_poly(s, col, pts, ui.shade(col, 0.7))
    if full:
        ui.circle(s, ui.mix(col, WHITE, 0.5), (x - r * 0.4, y - r * 0.3), r * 0.18)


def flame(s, c, r):
    x, y = c
    ui.fill_poly(s, (246, 120, 40), [(x, y - r), (x + r * 0.7, y + r * 0.1), (x + r * 0.55, y + r * 0.7), (x, y + r),
                                     (x - r * 0.55, y + r * 0.7), (x - r * 0.7, y + r * 0.1), (x - r * 0.25, y - r * 0.2)],
                 (190, 80, 20))
    ui.fill_poly(s, (252, 214, 60), [(x, y - r * 0.2), (x + r * 0.35, y + r * 0.4), (x, y + r * 0.85),
                                     (x - r * 0.35, y + r * 0.4)])


def progress(s, rect, got, goal):
    r = pygame.Rect(rect)
    pygame.draw.rect(s, (214, 220, 232), r, border_radius=r.h // 2)
    if got > 0:
        f = r.copy()
        f.w = max(r.h, round(r.w * min(1.0, got / goal)))
        pygame.draw.rect(s, (70, 190, 104), f, border_radius=r.h // 2)
        pygame.draw.rect(s, (140, 220, 160), (f.x + 8, f.y + 4, f.w - 16, 4), border_radius=2)
    pygame.draw.rect(s, (170, 180, 198), r, 2, border_radius=r.h // 2)
    ui.text(s, f"{got}/{goal}", (r.x - 40, r.centery), 22, TEXT)


# ------------------------------------------------------------- μενού
def menu_icon(surf, c):
    """Το εικονίδιο της κάρτας στο μενού: η ταινία με τρία αντικείμενα."""
    x0, y = c[0] - 120, c[1] + 36
    pygame.draw.rect(surf, (130, 144, 168), (x0, y + 8, 250, 20), border_radius=8)
    for x in range(x0 + 18, x0 + 250, 38):
        ui.circle(surf, (70, 78, 96), (x, y + 18), 6)
    pygame.draw.rect(surf, (52, 56, 68), (x0, y, 250, 10), border_radius=5)
    for k, (key, dx) in enumerate((("monitor", 40), ("umbrella", 125), ("app_music", 210))):
        img = items.image(key, 64)
        surf.blit(img, img.get_rect(midbottom=(x0 + dx, y + 2)))
    ui.fill_poly(surf, (252, 196, 40), [(x0 + 198, y - 82), (x0 + 222, y - 82), (x0 + 210, y - 68)], INK)
