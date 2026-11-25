"""Τα κοινά κομμάτια των οθονών των «Αποστολών Διάσωσης» (στο ύφος του «Προγραμμάτισε»): χρώματα,
κουμπιά, εικονίδια, ταμπελίτσες, οι τελείες των πιστών, η λωρίδα με τους στόχους και το εικονίδιο του μενού.
Ο χάρτης ζωγραφίζεται στο view.py.
"""
import math

import pygame

from core import ui
from games.line_follow import art as lf
from games.program import art as A
from . import fire as FI
from . import world as W

INK = (44, 54, 76)
GREY = (90, 100, 120)
LIGHT = (130, 140, 158)
TITLE = (236, 118, 30)
WHITE = (255, 255, 255)
LINE = (206, 214, 228)
OK = (52, 160, 80)
WORK = (236, 168, 28)
STUCK = (222, 70, 58)
OFF = (150, 158, 172)
BLUE = (62, 132, 222)
PURPLE = (150, 104, 206)
ORANGE = (238, 146, 46)
TEAL = (0, 150, 160)
RUN = (226, 96, 52)
TOP_H = 92
MODE = {"drive": ("Χειριστήριο", BLUE), "fix": ("Διόρθωσε", ORANGE), "write": ("Γράψε", OK),
        "sense": ("Αισθητήρες", PURPLE)}
ST_TEXT = {"done": ("τελείωσε", OK), "drive": ("οδηγεί", BLUE), "stuck": ("κόλλησε", STUCK),
           "idle": ("δεν κουνήθηκε", STUCK), "auto": ("αυτόματο R2", OFF), "off": ("αποσυνδέθηκε · αυτόματο", OFF),
           "bot": ("αυτόματο R2", OFF), "ready": ("έτοιμοι", OK), "write": ("γράφουν", OFF), "ok": ("πέτυχε", OK),
           "fail": ("δεν πέτυχε", STUCK), "run": ("εκτελεί", BLUE)}
WHY_SHORT = {"tree": "χτύπησε σε δέντρο", "rock": "χτύπησε σε βράχο", "water": "πήγε στο νερό",
             "fence": "χτύπησε στον φράχτη", "stone": "η πέτρα δεν τραβιέται", "animal": "ένα ζώο στον δρόμο",
             "branch": "το κλαδί ήταν κάτω", "fire": "πήγε στη φωτιά", "bridge": "πέτρα στο γεφυράκι",
             "heavy": "μόνο του στον βράχο", "time": "περίμενε πολύ", "noline": "δεν βρήκε τη γραμμή"}


def result_text(res):
    if not res:
        return ""
    status, why, path = res
    if status == "ok" and why == "partner":
        return "σωστό · ο γείτονας δεν ήρθε"
    if status == "ok" and why == "chain":
        return "σωστό · η μπάρα δεν άνοιξε"
    if status == "ok":
        return "πέτυχε"
    if status == "bump":
        return WHY_SHORT.get(why, "χτύπησε")
    if status == "empty":
        return "χωρίς πρόγραμμα"
    return "σταμάτησε νωρίς"


# ================================================================ μικρά βοηθητικά
def room(w=1280, h=720):
    s = pygame.Surface((w, h))
    for y in range(h):
        pygame.draw.line(s, ui.mix((234, 242, 252), (212, 226, 244), y / h), (0, y), (w, y))
    return s


def chip(s, text, pos, fg=WHITE, bg=BLUE, size=15, anchor="midleft", pad=12, h=None, border=None, icon=None):
    f = ui.font(size)
    tw = f.size(text)[0]
    ih = h or size + 14
    iw = tw + 2 * pad + (ih - 6 if icon else 0)
    r = pygame.Rect(0, 0, iw, ih)
    setattr(r, anchor, (round(pos[0]), round(pos[1])))
    pygame.draw.rect(s, bg, r, border_radius=ih // 2)
    if border:
        pygame.draw.rect(s, border, r, width=2, border_radius=ih // 2)
    x = r.x + pad
    if icon:
        icon(s, (x + (ih - 10) / 2, r.centery), ih - 12, fg)
        x += ih - 6
    ui.text(s, text, (x, r.centery), size, fg, anchor="midleft")
    return r


def pill(s, pos, text, col=WHITE, fg=INK, size=16, anchor="topleft", alpha=236):
    f = ui.font(size)
    r = pygame.Rect(0, 0, f.size(text)[0] + 28, size + 16)
    setattr(r, anchor, (round(pos[0]), round(pos[1])))
    sh = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(sh, (*col, alpha), sh.get_rect(), border_radius=r.h // 2)
    s.blit(sh, r)
    ui.text(s, text, r.center, size, fg)
    return r


def badge(s, center, num, color, r=13, size=15):
    ui.circle(s, color, center, r)
    ui.text(s, str(num), center, size, WHITE)


def mark(s, pos, ok, r=13):
    """Πράσινο ✓ ή κόκκινο ✗ σε κυκλάκι."""
    x, y = round(pos[0]), round(pos[1])
    col = OK if ok else STUCK
    pygame.draw.circle(s, ui.shade(col, 0.7), (x, y + 2), r)
    pygame.draw.circle(s, col, (x, y), r)
    pygame.draw.circle(s, WHITE, (x, y), r, 2)
    if ok:
        pygame.draw.lines(s, WHITE, False, [(x - r * 0.45, y), (x - r * 0.1, y + r * 0.38), (x + r * 0.5, y - r * 0.38)], 3)
    else:
        d = r * 0.38
        pygame.draw.line(s, WHITE, (x - d, y - d), (x + d, y + d), 3)
        pygame.draw.line(s, WHITE, (x - d, y + d), (x + d, y - d), 3)


def alert(s, pos, r=12):
    x, y = round(pos[0]), round(pos[1])
    pygame.draw.circle(s, ui.shade(STUCK, 0.7), (x, y + 2), r)
    pygame.draw.circle(s, STUCK, (x, y), r)
    pygame.draw.circle(s, WHITE, (x, y), r, 2)
    ui.text(s, "!", (x, y), round(r * 1.4), WHITE)


def check_mark(s, c, sz, col, w=None):
    x, y = c
    w = w or max(2, round(sz * 0.16))
    pts = [(x - sz * 0.38, y + sz * 0.02), (x - sz * 0.1, y + sz * 0.3), (x + sz * 0.4, y - sz * 0.3)]
    pygame.draw.lines(s, col, False, pts, w)
    for p in pts:
        pygame.draw.circle(s, col, p, w / 2)


def wrap(text, size, width, bold=True):
    """Σπάει ένα κείμενο σε γραμμές που χωράνε στο πλάτος."""
    f = ui.font(size, bold)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if f.size(trial)[0] <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# ================================================================ εικονίδια (surf, κέντρο, μέγεθος, χρώμα)
def icon_eye(s, c, sz, col):
    x, y = c
    pts = [(x - sz * 0.45 + sz * 0.9 * t / 20, y - sz * 0.3 * math.sin(math.pi * t / 20)) for t in range(21)]
    pts += [(x + sz * 0.45 - sz * 0.9 * t / 20, y + sz * 0.3 * math.sin(math.pi * t / 20)) for t in range(21)]
    pygame.draw.polygon(s, col, pts, max(2, round(sz * 0.09)))
    ui.circle(s, col, (x, y), sz * 0.15)


def icon_bulb(s, c, sz, col):
    x, y = c
    ui.circle(s, col, (x, y - sz * 0.1), sz * 0.27)
    pygame.draw.rect(s, col, (x - sz * 0.13, y + sz * 0.12, sz * 0.26, sz * 0.2), border_radius=2)
    pygame.draw.line(s, col, (x - sz * 0.12, y + sz * 0.38), (x + sz * 0.12, y + sz * 0.38), max(2, round(sz * 0.07)))


def icon_check(s, c, sz, col):
    check_mark(s, c, sz * 0.9, col)


def icon_robot(s, c, sz, col):
    from games.maze import art as r2art
    img = r2art.robot(max(8, int(sz * 0.95)), r2art.LED_GREEN)
    s.blit(img, img.get_rect(center=(round(c[0]), round(c[1]))))


def icon_msg(s, c, sz, col):
    x, y = c
    r = pygame.Rect(0, 0, sz * 0.8, sz * 0.55)
    r.center = (x, y - sz * 0.06)
    pygame.draw.rect(s, col, r, border_radius=round(sz * 0.14))
    ui.fill_poly(s, col, [(x - sz * 0.2, r.bottom - 2), (x - sz * 0.28, y + sz * 0.38), (x + sz * 0.02, r.bottom - 2)])


def icon_pause(s, c, sz, col):
    x, y = c
    w, h = sz * 0.17, sz * 0.6
    pygame.draw.rect(s, col, (x - sz * 0.22, y - h / 2, w, h), border_radius=2)
    pygame.draw.rect(s, col, (x + sz * 0.05, y - h / 2, w, h), border_radius=2)


def icon_snow(s, c, sz, col):
    x, y = c
    lw = max(2, round(sz * 0.08))
    for k in range(3):
        a = k * math.pi / 3
        dx, dy = math.cos(a) * sz * 0.36, math.sin(a) * sz * 0.36
        pygame.draw.line(s, col, (x - dx, y - dy), (x + dx, y + dy), lw)


def icon_route(s, c, sz, col):
    x, y = c
    for i in range(5):
        t = i / 4
        ui.circle(s, col, (x - sz * 0.38 + sz * 0.5 * t, y + sz * 0.28 - sz * 0.25 * math.sin(t * math.pi)), sz * 0.05)
    ui.circle(s, col, (x + sz * 0.22, y - sz * 0.12), sz * 0.18)
    ui.fill_poly(s, col, [(x + sz * 0.08, y - sz * 0.04), (x + sz * 0.36, y - sz * 0.04), (x + sz * 0.22, y + sz * 0.26)])


def icon_arrow_key(s, c, sz, col):
    """Ένα πλήκτρο με βελάκι (η βοήθεια «Επόμενη κίνηση»)."""
    x, y = c
    r = pygame.Rect(0, 0, sz * 0.7, sz * 0.62)
    r.center = (x, y)
    pygame.draw.rect(s, col, r, width=max(2, round(sz * 0.08)), border_radius=round(sz * 0.12))
    ui.fill_poly(s, col, [(x, y - sz * 0.2), (x + sz * 0.16, y + sz * 0.02), (x - sz * 0.16, y + sz * 0.02)])
    pygame.draw.rect(s, col, (x - sz * 0.05, y, sz * 0.1, sz * 0.16))


def icon_puzzle(s, c, sz, col):
    x, y = c
    r = pygame.Rect(0, 0, sz * 0.56, sz * 0.56)
    r.center = (x - sz * 0.04, y + sz * 0.06)
    pygame.draw.rect(s, col, r, border_radius=3)
    ui.circle(s, col, (r.centerx, r.y), sz * 0.11)
    ui.circle(s, col, (r.right, r.centery), sz * 0.11)


def icon_timer(s, c, sz, col):
    x, y = c
    lw = max(2, round(sz * 0.08))
    pygame.draw.circle(s, col, (x, y + sz * 0.05), sz * 0.32, lw)
    pygame.draw.line(s, col, (x, y + sz * 0.05), (x, y - sz * 0.15), lw)
    pygame.draw.line(s, col, (x, y + sz * 0.05), (x + sz * 0.13, y + sz * 0.12), lw)
    pygame.draw.rect(s, col, (x - sz * 0.1, y - sz * 0.42, sz * 0.2, sz * 0.09), border_radius=2)


def icon_hand(s, c, sz, col):
    x, y = c
    ui.circle(s, col, (x - sz * 0.12, y - sz * 0.2), sz * 0.14)
    pygame.draw.rect(s, col, (x - sz * 0.3, y - sz * 0.02, sz * 0.36, sz * 0.36), border_radius=round(sz * 0.12))
    pygame.draw.line(s, col, (x + sz * 0.05, y + sz * 0.02), (x + sz * 0.3, y - sz * 0.32), max(3, round(sz * 0.12)))
    ui.circle(s, col, (x + sz * 0.3, y - sz * 0.34), sz * 0.08)


def icon_back(s, c, sz, col):
    ui.icon_prev(s, c, sz, col)


def icon_forest(s, c, z, col):
    """Διπλωμένος χάρτης με ένα σημάδι («Όλο το δάσος»)."""
    x, y = c
    a = z * 0.42
    pts = [(x - a, y - a * 0.62), (x - a / 3, y - a * 0.86), (x + a / 3, y - a * 0.62), (x + a, y - a * 0.86),
           (x + a, y + a * 0.62), (x + a / 3, y + a * 0.86), (x - a / 3, y + a * 0.62), (x - a, y + a * 0.86)]
    ui.fill_poly(s, col, pts)
    for u in (-a / 3, a / 3):
        pygame.draw.line(s, (0, 120, 130), (x + u, y - a * 0.74), (x + u, y + a * 0.74), 2)
    pygame.draw.line(s, (90, 170, 230), (x - a * 0.8, y + a * 0.1), (x + a * 0.8, y - a * 0.2), 3)
    ui.circle(s, (232, 84, 84), (x + a * 0.45, y - a * 0.25), a * 0.2)


def icon_flame(s, c, sz, col=None, time=0.0):
    """Μια μικρή φλόγα από pixel (για τίτλους και κουμπιά)."""
    px = max(2, round(sz / 20))
    img = FI.flame_sprite(5 * 10 + FI.frame(time, 5), 12, 20, px, 0.85)
    s.blit(img, img.get_rect(center=(round(c[0]), round(c[1]))))


# ================================================================ πάνω μπάρα, στόχοι, τελείες
def top_bar(s):
    bar = pygame.Surface((s.get_width(), TOP_H), pygame.SRCALPHA)
    bar.fill((255, 255, 255, 232))
    s.blit(bar, (0, 0))
    pygame.draw.line(s, (196, 206, 218), (0, TOP_H), (s.get_width(), TOP_H), 2)


def level_dots(s, cx, y, current, done=()):
    """Οι πίστες σε τελείες (με το χρώμα του κεφαλαίου). current: ο αριθμός της πίστας που παίζεται."""
    dots = []
    for ch in W.CHAPTERS:
        col = MODE[ch["mode"]][1]
        n = len(ch.get("levels", [])) or ch.get("soon", 0)
        for i in range(n):
            dots.append((col, ch.get("levels") is not None))
    total = len(dots)
    for i, (col, real) in enumerate(dots):
        x = cx - (total - 1) * 16 + i * 32
        no = i + 1
        if no == current:
            ui.circle(s, col, (x, y), 15)
            ui.text(s, str(no), (x, y), 15, WHITE)
        elif no in done:
            ui.circle(s, (250, 200, 60), (x, y), 12, ui.shade((250, 200, 60), 0.7))
            ui.text(s, str(no), (x, y), 13, WHITE)
        else:
            ui.circle(s, ui.mix(col, WHITE, 0.5 if real else 0.72), (x, y), 12)
            ui.circle(s, (246, 248, 252), (x, y), 9.5)
            ui.text(s, str(no), (x, y), 13, ui.shade(col, 0.8) if real else ui.mix(col, WHITE, 0.45))


def level_dot_at(pos, cx, y):
    """Ο αριθμός της πίστας (1, 2, ...) στις τελείες της level_dots κάτω από το pos, ή None (μόνο πίστες που
    υπάρχουν, όχι «σύντομα»)."""
    real = [ch.get("levels") is not None for ch in W.CHAPTERS for _ in (ch.get("levels") or [None] * ch.get("soon", 0))]
    total = len(real)
    for i, ok in enumerate(real):
        x = cx - (total - 1) * 16 + i * 32
        if ok and (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 15 ** 2:
            return i + 1
    return None


def mode_title(s, cx, y, mode, title, chip_col=None, maxw=720):
    name, col = MODE.get(mode, (mode, BLUE))
    if chip_col:
        col = chip_col
    cw = ui.font(16).size(name)[0] + 24
    size = 20
    tw = ui.font(size).size(title)[0]
    while cw + 10 + tw > maxw and size > 14:
        size -= 1
        tw = ui.font(size).size(title)[0]
    x0 = cx - (cw + 10 + tw) / 2
    c = pygame.Rect(round(x0), y - 13, cw, 26)
    pygame.draw.rect(s, col, c, border_radius=13)
    ui.text(s, name, c.center, 16, WHITE)
    ui.text(s, title, (c.right + 10, y), size, INK, anchor="midleft")


def goals(s, rect, items):
    """Η λωρίδα με τα αστέρια κάτω στον χάρτη, όπως στο «Προγραμμάτισε». items: [(πέτυχε, κείμενο)]."""
    strip = pygame.Rect(rect.x + 14, rect.bottom - 58, rect.w - 28, 44)
    sh = pygame.Surface(strip.size, pygame.SRCALPHA)
    pygame.draw.rect(sh, (255, 255, 255, 232), sh.get_rect(), border_radius=22)
    s.blit(sh, strip)
    w = strip.w / len(items)
    for i, (on, label) in enumerate(items):
        x = strip.x + w * i + 24
        ui.star(s, (x, strip.centery), 13, (252, 204, 60) if on else (214, 220, 230),
                (170, 120, 20) if on else (170, 178, 192))
        size = 16 if ui.font(16).size(label)[0] < w - 50 else 14
        ui.text(s, label, (x + 20, strip.centery), size, INK if on else GREY, anchor="midleft")
        if i:
            pygame.draw.line(s, (226, 230, 238), (strip.x + w * i, strip.y + 8), (strip.x + w * i, strip.bottom - 8), 2)


def map_frame(s, rect):
    pygame.draw.rect(s, LINE, rect, width=3, border_radius=20)


def panel(s, rect, title=None, hint=None):
    ui.panel(s, rect, WHITE, radius=20, border=LINE)
    if title:
        ui.text(s, title, (rect.x + 20, rect.y + 24), 21, INK, anchor="midleft")
    if hint:
        ui.text(s, hint, (rect.right - 20, rect.y + 25), 14, LIGHT, anchor="midright", bold=False)


# ================================================================ το εικονίδιο του μενού
def menu_icon(surf, c):
    """Η κάρτα του μενού: ένα νησάκι από κυβάκια με το R2, μια πέτρα, νερό και φωτιά."""
    g = lf.Geo(c[0] - 64, c[1] - 30, 46, 21, 34)
    for y in range(2):
        for x in range(4):
            if (x, y) == (1, 1):
                A.cube(surf, g, x, y, -A.CUBE, -16, "water", 3, n=4)
            else:
                A.cube(surf, g, x, y, -A.CUBE, 0, "grass", 3, n=4)
    A.cube(surf, g, 3, 0, 0, A.CUBE, "leaf", 4, 0.1, 0.9, 0.1, 0.9, n=4)
    A.cube(surf, g, 2, 1, 0, A.CUBE * 0.5, (196, 192, 184), 3, 0.15, 0.85, 0.15, 0.85, n=4)
    lf.draw_robot(surf, g, 0.6, 1.5, 1, 0, led=(62, 132, 222), z=0)
    for i, (fx, fy) in enumerate(((3.5, 1.5), (3.2, 0.4))):
        x, y = g.pt(fx, fy, 0 if i == 0 else A.CUBE)
        img = FI.flame_sprite(70 + i * 10, 12, 20, 3, 0.85)
        surf.blit(img, img.get_rect(midbottom=(round(x), round(y))))


class TextButton(ui.Button):
    """Κουμπί με κείμενο στη μέση (και προαιρετικά ένα εικονίδιο αριστερά του)."""

    def __init__(self, rect, label, color, action, size=18, icon=None, fg=WHITE):
        super().__init__(rect, label, icon, color, action)
        self.size, self.fg = size, fg

    def draw(self, surf, time=0.0):
        r = self.rect
        col = self.color if self.enabled else (186, 190, 198)
        if self.enabled and self.hover and not self.pressed:
            col = ui.mix(col, (255, 255, 255), 0.14)
        if self.enabled and self.pulse:
            p = 0.5 + 0.5 * math.sin(time * 6)
            ui.glow(surf, r.inflate(12 + 8 * p, 12 + 8 * p), (255, 214, 60), 90 + 110 * p)
        depth = 5 if r.h >= 40 else 3
        face = r.move(0, depth if self.pressed else 0)
        pygame.draw.rect(surf, ui.shade(col, 0.68), r.move(0, depth), border_radius=min(14, r.h // 3))
        pygame.draw.rect(surf, col, face, border_radius=min(14, r.h // 3))
        if r.h >= 40:
            pygame.draw.rect(surf, ui.mix(col, (255, 255, 255), 0.22), (face.x + 8, face.y + 5, face.w - 16, 5),
                             border_radius=3)
        fg = self.fg if self.enabled else (240, 240, 244)
        f = ui.font(self.size)
        tw = f.size(self.label)[0] if self.label else 0
        isz = (face.h * (0.5 if face.w >= 140 else 0.36)) if self.icon else 0
        total = tw + (isz + (10 if self.label else 0) if self.icon else 0)
        x = face.centerx - total / 2
        if self.icon:
            self.icon(surf, (x + isz / 2, face.centery), isz, fg)
            x += isz + 10
        if self.label:
            ui.text(surf, self.label, (x, face.centery), self.size, fg, anchor="midleft")
