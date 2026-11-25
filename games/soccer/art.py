"""Τα γραφικά του Ποδοσφαίρου, ζωγραφισμένα με κώδικα: το γήπεδο ρομποτικής από πάνω, τα R2 με το
χρώμα της ομάδας τους, η μπάλα, τα ονόματα, ο πίνακας του σκορ και τα μικρά εικονίδια.

Γήπεδο: πράσινη μοκέτα με άσπρες γραμμές, μαύρος τοίχος γύρω γύρω με κομμένες γωνίες,
μπλε τέρμα αριστερά και κίτρινο δεξιά (όπως στο ρομποτικό ποδόσφαιρο), πορτοκαλί μπάλα.
"""
import math
import random

import pygame
import pygame.gfxdraw

from core import ui
from core.app import HEIGHT, WIDTH
from games.maze import art as r2art
from . import logic as L

TOP_H = 92
INK = (40, 44, 60)
GREY = (110, 118, 134)
TITLE = (236, 118, 30)
TITLE_SHADOW = (250, 214, 150)
BLUE = (52, 118, 226)
YELLOW = (246, 194, 30)
TEAM = {L.BLUE: BLUE, L.YELLOW: YELLOW}
TEAM_FG = {L.BLUE: (255, 255, 255), L.YELLOW: INK}
TEAM_NAME = {L.BLUE: "ΜΠΛΕ", L.YELLOW: "ΚΙΤΡΙΝΗ"}
LED = {L.BLUE: (70, 150, 255), L.YELLOW: (255, 210, 40)}
GREEN_BTN = (52, 160, 80)
ORANGE_BTN = (238, 146, 46)
BLUE_BTN = (62, 132, 222)
RED_BTN = (224, 84, 84)
WALLC = (32, 34, 40)
WALL_EDGE = (78, 82, 94)
LINE = (246, 248, 244)

WALL = 16
CARPET = pygame.Rect(78, 122, L.FW, L.FH)
ARENA = CARPET.inflate(2 * WALL, 2 * WALL)
CY = CARPET.y + L.FH // 2
LGOAL = pygame.Rect(CARPET.x - L.GOAL_D, round(CARPET.y + L.GOAL_TOP), L.GOAL_D, L.GOAL_W)
RGOAL = pygame.Rect(CARPET.right, round(CARPET.y + L.GOAL_TOP), L.GOAL_D, L.GOAL_W)


def to_screen(x, y):
    return CARPET.x + x, CARPET.y + y


def screen_angle(a):
    """Η γωνία του κόσμου (0 = δεξιά, ακτίνια) σε μοίρες για το draw_robot (0 = πάνω, δεξιόστροφα)."""
    return math.degrees(a) + 90


# ------------------------------------------------------------- βοηθητικά
def room(size=(WIDTH, HEIGHT)):
    s = pygame.Surface(size)
    w, h = size
    for y in range(h):
        pygame.draw.line(s, ui.mix((234, 242, 252), (212, 226, 244), y / h), (0, y), (w, y))
    return s


def ring(s, col, c, r, w):
    x, y = round(c[0]), round(c[1])
    r = round(r)
    pygame.draw.circle(s, col, (x, y), r, w)
    pygame.gfxdraw.aacircle(s, x, y, r, col)
    pygame.gfxdraw.aacircle(s, x, y, r - w + 1, col)


def dim(s, alpha=165):
    d = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    d.fill((236, 242, 250, alpha))
    s.blit(d, (0, 0))


def card(s, rect):
    ui.panel(s, rect, (255, 255, 255), radius=24, border=(214, 222, 236))


def fit_text(s, text, pos, size, color, max_w, anchor="center", bold=True):
    while size > 11 and ui.font(size, bold).size(text)[0] > max_w:
        size -= 1
    return ui.text(s, text, pos, size, color, anchor=anchor, bold=bold)


def monitor(s, c, w, col=(90, 100, 120), screen=(70, 170, 110), lines=True):
    """Μικρή οθόνη υπολογιστή (με ένα γηπεδάκι πάνω της)."""
    x, y = c
    h = w * 0.66
    r = pygame.Rect(0, 0, round(w), round(h))
    r.center = (round(x), round(y - h * 0.12))
    pygame.draw.rect(s, col, r, border_radius=max(2, int(w * 0.1)))
    inner = r.inflate(-round(w * 0.14), -round(w * 0.14))
    pygame.draw.rect(s, screen, inner, border_radius=2)
    if lines:
        g = max(2, inner.w // 14)
        pygame.draw.line(s, LINE, inner.midtop, (inner.centerx, inner.bottom - 1), max(1, round(w / 40)))
        pygame.draw.rect(s, BLUE, (inner.x, inner.centery - inner.h // 5, g, inner.h // 2.5))
        pygame.draw.rect(s, YELLOW, (inner.right - g, inner.centery - inner.h // 5, g, inner.h // 2.5))
    pygame.draw.rect(s, col, (round(x - w * 0.06), r.bottom, round(w * 0.12), round(h * 0.2)))
    pygame.draw.rect(s, col, (round(x - w * 0.24), r.bottom + round(h * 0.2), round(w * 0.48), round(h * 0.09)),
                     border_radius=2)


def icon_net(s, c, sz, col):
    x, y = c
    pts = [(x, y - sz * 0.22), (x - sz * 0.32, y + sz * 0.2), (x + sz * 0.32, y + sz * 0.2)]
    for i in range(3):
        pygame.draw.line(s, col, pts[i], pts[(i + 1) % 3], max(2, round(sz * 0.05)))
    for p in pts:
        monitor(s, p, sz * 0.34, col, (255, 255, 255), lines=False)


def icon_whistle(s, c, sz, col):
    x, y = c
    ui.circle(s, col, (x - sz * 0.06, y + sz * 0.08), sz * 0.26)
    ui.fill_poly(s, col, [(x - sz * 0.06, y - sz * 0.18), (x + sz * 0.44, y - sz * 0.18),
                          (x + sz * 0.44, y - sz * 0.02), (x + sz * 0.12, y - sz * 0.02)])
    pygame.draw.circle(s, col, (round(x - sz * 0.38), round(y - sz * 0.22)), round(sz * 0.1), max(2, round(sz * 0.05)))


def icon_swap(s, c, sz, col):
    x, y = c
    ui.icon_next(s, (x, y - sz * 0.17), sz * 0.72, col)
    ui.icon_prev(s, (x, y + sz * 0.17), sz * 0.72, col)


def icon_robot(s, c, sz, col):
    """Το R2 (για κουμπιά)."""
    r2art.draw_robot(s, c, round(sz * 0.8), 0, LED[L.BLUE])


def trophy(s, c, sz, col):
    x, y = c
    edge = ui.shade(col, 0.7)
    ui.thick_arc(s, edge, (x - sz * 0.3, y - sz * 0.2), sz * 0.14, math.pi / 2, 3 * math.pi / 2, sz * 0.07)
    ui.thick_arc(s, edge, (x + sz * 0.3, y - sz * 0.2), sz * 0.14, -math.pi / 2, math.pi / 2, sz * 0.07)
    cup = [(x - sz * 0.34, y - sz * 0.42), (x + sz * 0.34, y - sz * 0.42)]
    for i in range(13):
        a = i / 12 * math.pi
        cup.append((x + sz * 0.34 * math.cos(a), y - sz * 0.1 + sz * 0.26 * math.sin(a)))
    ui.fill_poly(s, col, cup, edge)
    pygame.draw.rect(s, edge, (round(x - sz * 0.06), round(y + sz * 0.15), round(sz * 0.12), round(sz * 0.16)))
    pygame.draw.rect(s, col, (round(x - sz * 0.26), round(y + sz * 0.3), round(sz * 0.52), round(sz * 0.14)),
                     border_radius=4)
    ui.star(s, (x, y - sz * 0.16), sz * 0.14, (255, 255, 255), (255, 255, 255))


def handshake(s, c, sz):
    """Ισοπαλία: μπλε και κίτρινο χέρι."""
    x, y = c
    ui.circle(s, BLUE, (x - sz * 0.18, y), sz * 0.3, ui.shade(BLUE, 0.7))
    ui.circle(s, YELLOW, (x + sz * 0.18, y), sz * 0.3, ui.shade(YELLOW, 0.7))
    ui.text(s, "=", (x, y), round(sz * 0.5), (255, 255, 255), shadow=INK)


def keycap(s, center, label=None, arrow=None, w=46, h=42, tint=None, size=18, pressed=False):
    r = pygame.Rect(0, 0, w, h)
    r.center = (round(center[0]), round(center[1]))
    pygame.draw.rect(s, (150, 156, 170), r.move(0, 4), border_radius=9)
    face_r = r.move(0, 3) if pressed else r
    face = ui.mix(tint, (255, 255, 255), 0.72) if tint else (255, 255, 255)
    if pressed:
        face = ui.mix(face, (255, 214, 60), 0.5)
    pygame.draw.rect(s, face, face_r, border_radius=9)
    pygame.draw.rect(s, (150, 156, 170), face_r, 1, border_radius=9)
    x, y = face_r.center
    col = (60, 66, 84)
    if arrow:
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[arrow]
        px, py = -dy, dx
        k = h / 42
        pygame.draw.line(s, col, (x - dx * 9 * k, y - dy * 9 * k), (x + dx * 2 * k, y + dy * 2 * k),
                         max(2, round(3 * k)))
        ui.fill_poly(s, col, [(x + dx * 10 * k, y + dy * 10 * k), (x + (px * 7 + dx) * k, y + (py * 7 + dy) * k),
                              (x + (-px * 7 + dx) * k, y + (-py * 7 + dy) * k)])
    else:
        ui.text(s, label, (x, y), size, col)
    return r


def key_cluster(s, c, letters, tint, k=36):
    """Τα τέσσερα πλήκτρα οδήγησης σε σχήμα ανάποδου Τ: W A S D ή τα βελάκια (letters=None)."""
    x, y = c
    if letters:
        keycap(s, (x, y - 20), letters[0], w=k, h=34, tint=tint)
        for i, ch in enumerate(letters[1:]):
            keycap(s, (x + (i - 1) * (k + 4), y + 20), ch, w=k, h=34, tint=tint)
    else:
        keycap(s, (x, y - 20), arrow="up", w=k, h=34, tint=tint)
        for i, a in enumerate(("left", "down", "right")):
            keycap(s, (x + (i - 1) * (k + 4), y + 20), arrow=a, w=k, h=34, tint=tint)


def ball(s, pos, r=L.BALL_R, trail=None):
    x, y = pos
    if trail:
        for i, (tx, ty) in enumerate(trail):
            g = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 170, 80, 40 + 30 * i), (r + 1, r + 1), round(r * (0.55 + 0.12 * i)))
            s.blit(g, g.get_rect(center=(round(tx), round(ty))))
    sh = pygame.Surface((r * 3, r * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
    s.blit(sh, sh.get_rect(center=(round(x + r * 0.3), round(y + r * 0.55))))
    ui.circle(s, (250, 128, 30), (x, y), r, (186, 78, 10))
    for ax, ay in ((0.35, 0.3), (-0.3, 0.42), (0.05, -0.05), (0.45, -0.25), (-0.4, -0.05)):
        ui.circle(s, (226, 104, 22), (x + ax * r, y + ay * r), max(1.2, r * 0.12))
    ui.circle(s, (255, 196, 140), (x - r * 0.36, y - r * 0.38), r * 0.28)


_tags = {}


def name_tag(s, pos, team, name, me=False, bot=False, show_me=False, tag="ΕΣΥ"):
    """Το ταμπελάκι πάνω από κάθε R2: το όνομα, και ένα συννεφάκι για το δικό σου:
    «ΕΣΥ», ή τα πλήκτρα του, όταν παίζουν δύο στον ίδιο υπολογιστή."""
    x, y = pos
    col = TEAM[team]
    fg = TEAM_FG[team]
    key = (name, team)
    if key not in _tags:
        if len(_tags) > 64:
            _tags.clear()
        _tags[key] = ui.font(15).render(name, True, fg)
    img = _tags[key]
    icon_w = 22 if bot else 0
    r = pygame.Rect(0, 0, img.get_width() + 20 + icon_w, 24)
    r.center = (round(x), round(y))
    pygame.draw.rect(s, ui.shade(col, 0.7), r.move(0, 2), border_radius=12)
    pygame.draw.rect(s, col, r, border_radius=12)
    if me:
        pygame.draw.rect(s, (255, 255, 255), r.inflate(4, 4), 3, border_radius=14)
    tx = r.x + 10
    if bot:
        monitor(s, (tx + 8, r.centery + 1), 16, fg, col, lines=False)
        tx += icon_w
    s.blit(img, img.get_rect(midleft=(tx, r.centery)))
    if me and show_me:
        t = pygame.Rect(0, 0, max(52, ui.font(14).size(tag)[0] + 18), 22)
        t.midbottom = (r.centerx, r.y - 9)
        pygame.draw.rect(s, (255, 255, 255), t, border_radius=8)
        pygame.draw.rect(s, (255, 214, 60), t, 2, border_radius=8)
        ui.fill_poly(s, (255, 214, 60), [(t.centerx - 7, t.bottom), (t.centerx + 7, t.bottom),
                                         (t.centerx, t.bottom + 7)])
        ui.text(s, tag, t.center, 14, TITLE)


_rings = {}


def _team_ring(team, size):
    key = (team, size)
    if key not in _rings:
        col = TEAM[team]
        n = round(size * 1.9)
        g = pygame.Surface((n, n), pygame.SRCALPHA)
        r = round(size * 0.68)
        pygame.draw.circle(g, (*ui.mix(col, (255, 255, 255), 0.3), 70), (n // 2, n // 2), r)
        pygame.draw.circle(g, (*col, 255), (n // 2, n // 2), r, 4)
        _rings[key] = g
    return _rings[key]


def kicker(s, pos, angle_deg, size=L.ROBOT_SIZE):
    """Η πλάκα της κλωτσιάς, βγαλμένη μπροστά από το R2, με δύο ράβδους και γραμμούλες ταχύτητας."""
    x, y = pos
    k = size / L.ROBOT_SIZE
    a = math.radians(angle_deg)
    dx, dy = math.sin(a), -math.cos(a)              # μπροστά
    px, py = -dy, dx                                # πλάι
    base, out = (L.HALF_LEN - 6) * k, (L.HALF_LEN + L.KICK_REACH - 4) * k

    def at(f, side):
        return x + dx * f + px * side, y + dy * f + py * side

    for side in (-13 * k, 13 * k):
        pygame.draw.line(s, (70, 76, 90), at(base, side), at(out, side), max(3, round(5 * k)))
    half, th = 25 * k, 4 * k
    plate = [at(out - th, -half), at(out - th, half), at(out + th, half), at(out + th, -half)]
    ui.fill_poly(s, (232, 236, 244), plate, (70, 76, 90))
    for side in (-16 * k, 0, 16 * k):
        p0 = at(out + 12 * k, side)
        p1 = at(out + (24 if side else 30) * k, side)
        pygame.draw.line(s, (255, 255, 255), p0, p1, max(2, round(3 * k)))


def robot(s, pos, angle_deg, team, me=False, kick=False, size=L.ROBOT_SIZE, time=0.0):
    """Ένα R2 με το χρώμα της ομάδας του. angle_deg: όπως στο draw_robot (0 = πάνω, δεξιόστροφα).
    kick: η πλάκα της κλωτσιάς είναι έξω."""
    x, y = pos
    g = _team_ring(team, size)
    s.blit(g, g.get_rect(center=(round(x), round(y))))
    if me:
        ring(s, (255, 214, 60), (x, y), size * 0.78, 4)
    if kick:
        kicker(s, pos, angle_deg, size)
    r2art.draw_robot(s, (x, y), size, angle_deg, LED[team])


# ------------------------------------------------------------- το γήπεδο
_field = None


def field():
    """Όλη η οθόνη με το γήπεδο (χωρίς R2 και μπάλα). Φτιάχνεται μία φορά."""
    global _field
    if _field is not None:
        return _field
    s = room()
    sh = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for r in (ARENA, LGOAL.inflate(2 * WALL, 2 * WALL), RGOAL.inflate(2 * WALL, 2 * WALL)):
        pygame.draw.rect(sh, (20, 30, 50, 55), r.move(0, 8), border_radius=18)
    s.blit(sh, (0, 0))
    for g in (LGOAL, RGOAL):
        pygame.draw.rect(s, WALLC, g.inflate(2 * WALL, 2 * WALL), border_radius=10)
        pygame.draw.rect(s, WALL_EDGE, g.inflate(2 * WALL - 4, 2 * WALL - 4), 2, border_radius=9)
    pygame.draw.rect(s, WALLC, ARENA, border_radius=16)
    pygame.draw.rect(s, WALL_EDGE, ARENA.inflate(-4, -4), 2, border_radius=14)
    carpet = pygame.Surface(CARPET.size)
    base = (54, 148, 80)
    n = 14
    step = CARPET.w / n
    for i in range(n):
        pygame.draw.rect(carpet, ui.shade(base, 1.035 if i % 2 else 0.975),
                         (round(i * step), 0, math.ceil(step) + 1, CARPET.h))
    rng = random.Random(7)
    for _ in range(14000):
        x, y = rng.randrange(CARPET.w), rng.randrange(CARPET.h)
        carpet.set_at((x, y), ui.shade(carpet.get_at((x, y)), rng.choice((0.9, 1.08))))
    shade = pygame.Surface(CARPET.size, pygame.SRCALPHA)
    for i in range(10):
        pygame.draw.rect(shade, (0, 0, 0, round(46 - i * 4.5)), shade.get_rect().inflate(-2 * i, -2 * i), 1)
    carpet.blit(shade, (0, 0))
    s.blit(carpet, CARPET.topleft)
    lines = CARPET.inflate(-44, -44)
    pygame.draw.rect(s, LINE, lines, 4, border_radius=6)
    cx = CARPET.centerx
    pygame.draw.line(s, LINE, (cx - 1, lines.y), (cx - 1, lines.bottom - 2), 4)
    ring(s, LINE, (cx, CY), 80, 4)
    ui.circle(s, LINE, (cx, CY), 6)
    for side in (-1, 1):
        pw, ph = 124, 300
        r = pygame.Rect(lines.x if side < 0 else lines.right - pw, CY - ph // 2, pw, ph)
        pygame.draw.rect(s, LINE, r, 4, border_radius=6)
    for nx, ny in L.NEUTRAL[1:]:
        ui.circle(s, (34, 90, 50), to_screen(nx, ny), 5)
    k = L.CORNER
    for x0, y0, sx, sy in ((CARPET.x, CARPET.y, 1, 1), (CARPET.right, CARPET.y, -1, 1),
                           (CARPET.x, CARPET.bottom, 1, -1), (CARPET.right, CARPET.bottom, -1, -1)):
        ui.fill_poly(s, WALLC, [(x0, y0), (x0 + sx * k, y0), (x0, y0 + sy * k)])
        pygame.draw.line(s, WALL_EDGE, (x0 + sx * k, y0), (x0, y0 + sy * k), 2)
    for g, col, left in ((LGOAL, BLUE, True), (RGOAL, YELLOW, False)):
        pygame.draw.rect(s, ui.mix(col, (255, 255, 255), 0.55), g)
        net = ui.mix(col, (255, 255, 255), 0.3)
        for xx in range(g.x + 6, g.right, 8):
            pygame.draw.line(s, net, (xx, g.y), (xx, g.bottom - 1), 1)
        for yy in range(g.y + 6, g.bottom, 8):
            pygame.draw.line(s, net, (g.x, yy), (g.right - 1, yy), 1)
        pygame.draw.rect(s, col, (g.x, g.y, 8, g.h) if left else (g.right - 8, g.y, 8, g.h))
        pygame.draw.rect(s, col, (g.x, g.y, g.w, 8))
        pygame.draw.rect(s, col, (g.x, g.bottom - 8, g.w, 8))
        mouth = g.right if left else g.x
        pygame.draw.line(s, LINE, (mouth, g.y + 8), (mouth, g.bottom - 9), 3)
    _field = s
    return s


def goal_glow(s, team, strength):
    """Το τέρμα όπου μπήκε η μπάλα λάμπει. team: η ομάδα που σκόραρε."""
    g = RGOAL if team == L.BLUE else LGOAL
    r = g.inflate(40, 40)
    gl = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(gl, (255, 236, 120, round(150 * strength)), gl.get_rect(), border_radius=20)
    s.blit(gl, r)


def mini_field(s, r):
    pygame.draw.rect(s, WALLC, r.inflate(6, 6), border_radius=8)
    pygame.draw.rect(s, (54, 148, 80), r, border_radius=6)
    pygame.draw.line(s, LINE, r.midtop, (r.centerx, r.bottom - 1), 2)
    ring(s, LINE, r.center, max(3, r.h // 5), 2)
    gh = r.h // 2.6
    pygame.draw.rect(s, BLUE, (r.x - 3, r.centery - gh / 2, 6, gh))
    pygame.draw.rect(s, YELLOW, (r.right - 3, r.centery - gh / 2, 6, gh))


# ------------------------------------------------------------- πάνω μπάρα
_bar = None


def top_bar(s):
    global _bar
    if _bar is None:
        _bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        _bar.fill((255, 255, 255, 232))
    s.blit(_bar, (0, 0))
    pygame.draw.line(s, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)


def clock_text(seconds):
    seconds = max(0, math.ceil(seconds - 1e-6))
    return f"{seconds // 60}:{seconds % 60:02d}"


def scoreboard(s, sb, sy, clock, flash=None, flash_t=0.0):
    """Το σκορ στη μέση της πάνω μπάρας και ο χρόνος από κάτω. flash: η ομάδα που μόλις σκόραρε."""
    cx = 640
    for team, score, right in ((L.BLUE, sb, False), (L.YELLOW, sy, True)):
        col = TEAM[team]
        r = pygame.Rect(0, 0, 196, 54)
        if right:
            r.midleft = (cx + 24, 36)
        else:
            r.midright = (cx - 24, 36)
        if flash == team:
            ui.glow(s, r.inflate(14, 14), (255, 214, 60), 120 + 100 * math.sin(flash_t * 8) ** 2, radius=20)
        pygame.draw.rect(s, ui.shade(col, 0.7), r.move(0, 4), border_radius=14)
        pygame.draw.rect(s, col, r, border_radius=14)
        box = pygame.Rect(0, 0, 54, 44)
        if right:
            box.midleft = (r.x + 5, r.centery)
            name_x = (box.right + r.right) / 2
        else:
            box.midright = (r.right - 5, r.centery)
            name_x = (r.x + box.x) / 2
        pygame.draw.rect(s, (255, 255, 255), box, border_radius=10)
        ui.text(s, str(score), box.center, 34, INK)
        ui.text(s, TEAM_NAME[team], (name_x, r.centery), 21, TEAM_FG[team])
    ui.text(s, ":", (cx, 33), 36, INK)
    c = pygame.Rect(0, 0, 88, 24)
    c.center = (cx, 78)
    low = clock <= 10 and clock > 0
    pygame.draw.rect(s, (214, 70, 60) if low else (44, 54, 76), c, border_radius=12)
    ui.text(s, clock_text(clock), c.center, 18, (255, 255, 255))


def chip(s, rect, text, selected, enabled=True, hover=False, size=20):
    """Κουμπάκι επιλογής (π.χ. «3 λεπτά»): πράσινο περίγραμμα όταν είναι διαλεγμένο."""
    face = rect.move(0, -3) if hover and enabled and not selected else rect
    pygame.draw.rect(s, (196, 206, 222), rect.move(0, 4), border_radius=16)
    fill = (236, 250, 242) if selected else (244, 246, 250)
    pygame.draw.rect(s, fill, face, border_radius=16)
    border = (60, 170, 120) if selected else ((150, 200, 170) if hover and enabled else (206, 214, 228))
    pygame.draw.rect(s, border, face, 4 if selected else 2, border_radius=16)
    col = (40, 130, 90) if selected else (GREY if enabled else (176, 182, 194))
    ui.text(s, text, face.center, size, col)


def tile(s, r, hover):
    face = r.move(0, -4) if hover else r
    pygame.draw.rect(s, (196, 206, 222), r.move(0, 4), border_radius=20)
    pygame.draw.rect(s, (236, 250, 242) if hover else (244, 246, 250), face, border_radius=20)
    pygame.draw.rect(s, (60, 170, 120) if hover else (206, 214, 228), face, 4 if hover else 2, border_radius=20)
    return face


def text_box(s, rect, text, focused, placeholder, time, warn=0.0):
    pygame.draw.rect(s, (255, 255, 255), rect, border_radius=10)
    border = (226, 70, 60) if warn > 0 else ((62, 132, 222) if focused else (196, 204, 218))
    pygame.draw.rect(s, border, rect, 3, border_radius=10)
    if text:
        r = ui.text(s, text, (rect.x + 14, rect.centery), 22, INK, anchor="midleft")
        right = r.right
    else:
        ui.text(s, placeholder, (rect.x + 14, rect.centery), 18, (160, 166, 180), anchor="midleft", bold=False)
        right = rect.x + 12
    if focused and (time * 2) % 2 < 1.3:
        pygame.draw.line(s, INK, (right + 3, rect.y + 9), (right + 3, rect.bottom - 9), 2)


# ------------------------------------------------------------- μενού
def menu_icon(surf, c):
    """Η κάρτα του μενού: γηπεδάκι με ένα R2 και τη μπάλα."""
    x, y = c
    r = pygame.Rect(0, 0, 210, 118)
    r.center = (x, y)
    pygame.draw.rect(surf, WALLC, r.inflate(14, 14), border_radius=12)
    pygame.draw.rect(surf, (54, 148, 80), r, border_radius=6)
    pygame.draw.line(surf, LINE, (x, r.y + 8), (x, r.bottom - 9), 3)
    ring(surf, LINE, (x, y), 24, 3)
    gh = 50
    pygame.draw.rect(surf, BLUE, (r.x - 7, y - gh // 2, 8, gh))
    pygame.draw.rect(surf, YELLOW, (r.right - 1, y - gh // 2, 8, gh))
    surf.blit(_team_ring(L.BLUE, 52), _team_ring(L.BLUE, 52).get_rect(center=(x + 18, y + 6)))
    r2art.draw_robot(surf, (x + 18, y + 6), 52, 90, LED[L.BLUE])
    ball(surf, (x + 66, y + 4), 11)
