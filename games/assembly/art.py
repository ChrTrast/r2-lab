"""Τα δισδιάστατα γραφικά της Συναρμολόγησης: φόντο, ταπέτο εργασίας, κάρτες του κουτιού, συννεφάκι,
εικονίδια των κουμπιών, «μαγνήτης», «κλικ!» και το εικονίδιο του μενού."""
import math

import pygame

from core import ui
from . import eng3d as E
from . import parts as P

INK = (40, 48, 70)
ORANGE = (238, 132, 40)
GREEN = (60, 170, 90)
RED = (220, 64, 60)
BLUE = (40, 120, 200)
MAGNET = (90, 200, 255)
MAT = (56, 140, 104)
MAT_LINE = (88, 168, 132)
MAT_TEXT = (226, 248, 236)
MAT_RECT = (-170, 170, -130, 260)       # x0, x1, y0, y1 σε χιλιοστά


# ----------------------------------------------------------------- φόντο και ταπέτο
_bg = None


def background(w, h):
    global _bg
    if _bg is None or _bg.get_size() != (w, h):
        _bg = pygame.Surface((w, h))
        for y in range(h):
            pygame.draw.line(_bg, ui.mix((222, 232, 244), (192, 206, 226), y / h), (0, y), (w, y))
    return _bg


def mat(surf, cam):
    """Το πράσινο ταπέτο κοπής με το πλέγμα και τις λέξεις ΜΠΡΟΣΤΑ, ΠΙΣΩ, ΑΡΙΣΤΕΡΑ, ΔΕΞΙΑ."""
    x0, x1, y0, y1 = MAT_RECT
    corners = [cam.proj((x, y, 0)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    under = [cam.proj((x, y, -4)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    # το πάχος του ταπέτου: οι πλευρές που φαίνονται
    for i in range(4):
        a, b = i, (i + 1) % 4
        quad = [corners[a], corners[b], under[b], under[a]]
        if (quad[1][0] - quad[0][0]) * (quad[3][1] - quad[0][1]) - (quad[1][1] - quad[0][1]) * (quad[3][0] - quad[0][0]) > 0:
            ui.fill_poly(surf, (34, 96, 70), quad)
    ui.fill_poly(surf, MAT, corners)
    for k in range(x0 + 20, x1, 20):
        a, b = cam.proj((k, y0, 0)), cam.proj((k, y1, 0))
        pygame.draw.aaline(surf, MAT_LINE, a, b)
    for k in range(y0 + 20, y1, 20):
        a, b = cam.proj((x0, k, 0)), cam.proj((x1, k, 0))
        pygame.draw.aaline(surf, MAT_LINE, a, b)
    pygame.draw.aalines(surf, (120, 196, 160), True, corners)
    for (x, y), word, size in (((0, 232), "ΜΠΡΟΣΤΑ", 3.2), ((0, -104), "ΠΙΣΩ", 3.2),
                               ((-128, 40), "ΑΡΙΣΤΕΡΑ", 2.5), ((128, 40), "ΔΕΞΙΑ", 2.5)):
        _mat_word(surf, cam, (x, y, 0), word, size)
    tip = [cam.proj(p) for p in ((-11, 196, 0), (11, 196, 0), (0, 212, 0))]
    ui.fill_poly(surf, MAT_TEXT, tip)


_word_cache = {}


def _mat_word(surf, cam, c, word, size):
    key = (word, round(cam.scale * size * 5.2))
    if key not in _word_cache:
        _word_cache[key] = ui.font(max(8, key[1])).render(word, True, MAT_TEXT)
    img = _word_cache[key]
    p0 = cam.proj(c)
    pu = cam.proj((c[0] + 1, c[1], 0))
    pv = cam.proj((c[0], c[1] + 1, 0))
    fx = math.hypot(pu[0] - p0[0], pu[1] - p0[1]) / cam.scale
    fy = math.hypot(pv[0] - p0[0], pv[1] - p0[1]) / cam.scale
    if fy < 0.15:
        return
    w, h = img.get_size()
    img = pygame.transform.smoothscale(img, (max(1, round(w * fx)), max(1, round(h * fy))))
    img = pygame.transform.rotate(img, math.degrees(math.atan2(-(pu[1] - p0[1]), pu[0] - p0[0])))
    img.set_alpha(220)
    surf.blit(img, img.get_rect(center=(round(p0[0]), round(p0[1]))))


def shadow(surf, cam, lift=0.0):
    """Απαλή σκιά κάτω από το ρομπότ (πιο αχνή όταν σηκώνεται)."""
    pts = [cam.proj((x, y, 0)) for x, y in ((-72, -20), (72, -20), (72, 136), (-72, 136))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    r = pygame.Rect(min(xs) - 30, min(ys) - 30, max(xs) - min(xs) + 60, max(ys) - min(ys) + 60)
    if r.w <= 0 or r.h <= 0:
        return
    small = pygame.Surface((max(1, r.w // 6), max(1, r.h // 6)), pygame.SRCALPHA)
    a = max(0, int(80 * (1 - min(1.0, lift / 120))))
    pygame.draw.polygon(small, (10, 40, 26, a), [((x - r.x) / 6, (y - r.y) / 6) for x, y in pts])
    surf.blit(pygame.transform.smoothscale(small, r.size), r.topleft)


# ----------------------------------------------------------------- επάνω μπάρα
def progress(surf, x0, task, done, words=None, y=23):
    """Οι 7 εργασίες του οδηγού: πράσινο τικ όσες τελείωσαν, πορτοκαλί η τωρινή.

    words: για κάθε εργασία [(λέξη, είναι το τωρινό βήμα)], π.χ. «Ρόδες» / «υπέρηχοι» για την Εργασία 2.
    """
    for i in range(6):
        x = x0 + i * 88
        pygame.draw.line(surf, GREEN if (i + 1) in done else (210, 216, 228), (x + 14, y), (x + 74, y), 4)
    for i in range(7):
        x, n = x0 + i * 88, i + 1
        if n in done:
            ui.circle(surf, GREEN, (x, y), 15)
            pygame.draw.lines(surf, (255, 255, 255), False, [(x - 7, y), (x - 2, y + 5), (x + 7, y - 6)], 4)
        elif n == task:
            ui.circle(surf, (255, 214, 120), (x, y), 19)
            ui.circle(surf, ORANGE, (x, y), 15)
            ui.text(surf, str(n), (x, y), 19, (255, 255, 255))
        else:
            ui.circle(surf, (226, 230, 238), (x, y), 15)
            ui.text(surf, str(n), (x, y), 18, (150, 156, 172))
        if words:
            for k, (w, now) in enumerate(words[i]):
                col = ORANGE if (now and n == task) else (INK if n == task else (130, 138, 156))
                fit_text(surf, w, (x, y + 24 + k * 14), 13, col, 86, bold=n == task)


# ----------------------------------------------------------------- κείμενα
def wrap(s, size, max_w, bold=True):
    words, lines, cur = s.split(), [], ""
    f = ui.font(size, bold)
    for w in words:
        test = (cur + " " + w).strip()
        if f.size(test)[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(surf, s, pos, size, color, max_w, anchor="center", bold=True):
    w = ui.font(size, bold).size(s)[0]
    if w > max_w:
        size = max(11, int(size * max_w / w))
    return ui.text(surf, s, pos, size, color, anchor=anchor, bold=bold)


def instruction(surf, rect, small, big, small_col=ORANGE):
    ui.panel(surf, rect, (255, 255, 255), radius=18, border=(214, 222, 236))
    bx, by = rect.x + 16, rect.y + rect.h // 2 - 23
    pygame.draw.rect(surf, (90, 140, 220), (bx, by, 40, 46), border_radius=6)
    pygame.draw.rect(surf, (255, 255, 255), (bx + 6, by + 6, 28, 34), border_radius=3)
    for k in range(4):
        pygame.draw.line(surf, (160, 180, 210), (bx + 10, by + 13 + k * 7), (bx + 30, by + 13 + k * 7), 2)
    tx = rect.x + 70
    max_w = rect.right - tx - 14
    ui.text(surf, small, (tx, rect.y + 20), 17, small_col, anchor="midleft")
    lines = wrap(big, 23, max_w)
    if len(lines) == 1:
        fit_text(surf, big, (tx, rect.y + 50), 25, INK, max_w, anchor="midleft")
    else:
        size = 20 if len(lines) == 2 else 17
        lines = wrap(big, size, max_w)[:3]
        for i, line in enumerate(lines):
            ui.text(surf, line, (tx, rect.y + 44 + i * (size + 3)), size, INK, anchor="midleft", bold=False)


def bubble(surf, rect, line1, line2, color1=BLUE):
    """Το R2 μιλάει: λευκό συννεφάκι με μύτη προς τα δεξιά (εκεί στέκεται το R2)."""
    ui.panel(surf, rect, (255, 255, 255), radius=22, border=(214, 222, 236))
    tail = [(rect.right - 3, rect.y + 30), (rect.right + 30, rect.y + 52), (rect.right - 3, rect.y + 64)]
    ui.fill_poly(surf, (255, 255, 255), tail)
    pygame.draw.lines(surf, (214, 222, 236), False, tail, 3)
    fit_text(surf, line1, (rect.centerx, rect.y + 30), 24, color1, rect.w - 30)
    if line2:
        fit_text(surf, line2, (rect.centerx, rect.y + 64), 19, INK, rect.w - 30)


# ----------------------------------------------------------------- κουτί υλικών
def parts_box(surf, rect, title):
    ui.panel(surf, rect, (226, 196, 150), radius=16, border=(176, 140, 92))
    pygame.draw.rect(surf, (212, 178, 128), (rect.x + 10, rect.y + 44, rect.w - 20, rect.h - 54), border_radius=10)
    ui.text(surf, title, (rect.centerx, rect.y + 23), 22, (92, 62, 30))


def card(surf, r, img, name, left, total, state, hover=False, small=False):
    """Μία κάρτα κομματιού. state: "ready", "hand" (στο χέρι), "done" (μπήκαν όλα), "next" (λάμπει)."""
    if state == "next":
        ui.glow(surf, r.inflate(12, 12), (255, 214, 60), 150, 18)
    face = r.move(0, -3) if (hover and state == "ready") else r
    col = (255, 255, 255) if state != "done" else (236, 240, 236)
    border = {"ready": (214, 222, 236), "hand": ORANGE, "done": (190, 210, 196), "next": (252, 196, 60)}[state]
    ui.panel(surf, face, col, radius=12, border=border, shadow=state not in ("done",))
    if img is not None:
        pic = img
        if state in ("hand", "done"):
            pic = img.copy()
            pic.set_alpha(80 if state == "done" else 60)
        surf.blit(pic, pic.get_rect(center=(face.centerx, face.y + (30 if small else 56))))
    size = 13 if small else 16
    lines = name.split("\n")
    base = face.bottom - (len(lines) * (size + 2)) - (5 if small else 8)
    for k, line in enumerate(lines):
        fit_text(surf, line, (face.centerx, base + k * (size + 2) + size // 2 + 1), size,
                 INK if state != "done" else (130, 140, 150), face.w - 10)
    if total > 1 and state != "done":
        b = pygame.Rect(face.right - (32 if small else 38), face.y + 6, 28 if small else 32, 20 if small else 24)
        pygame.draw.rect(surf, (90, 140, 220), b, border_radius=b.h // 2)
        ui.text(surf, f"×{left}", b.center, 13 if small else 16, (255, 255, 255))
    if state == "done":
        c = (face.right - 16, face.y + 16)
        ui.circle(surf, GREEN, c, 11)
        pygame.draw.lines(surf, (255, 255, 255), False, [(c[0] - 5, c[1]), (c[0] - 1, c[1] + 4), (c[0] + 6, c[1] - 4)], 3)
    if state == "hand":
        ui.text(surf, "στο χέρι", (face.centerx, face.y + (30 if small else 56)), 13 if small else 17, ORANGE)


# ----------------------------------------------------------------- εικονίδια κουμπιών
def icon_rotate(surf, c, z, col, direction):
    r = z * 0.32
    ui.thick_arc(surf, col, c, r, math.radians(-30), math.radians(210), z * 0.12)
    a = math.radians(210 if direction < 0 else -30)
    px, py = c[0] + r * math.cos(a), c[1] - r * math.sin(a)
    h = z * 0.19
    ui.fill_poly(surf, col, [(px - h, py - h * 0.2), (px + h, py - h * 0.2), (px, py + h)])


def icon_flip(surf, c, z, col):
    x, y = c
    pygame.draw.rect(surf, col, (round(x - z * 0.36), round(y - z * 0.2), round(z * 0.62), round(z * 0.13)),
                     border_radius=3)
    ui.circle(surf, col, (x - z * 0.22, y + z * 0.02), z * 0.1)
    ui.circle(surf, col, (x + z * 0.14, y + z * 0.02), z * 0.1)
    ui.thick_arc(surf, col, (x + z * 0.34, y - z * 0.08), z * 0.2, math.radians(110), math.radians(-100), z * 0.08)
    a = math.radians(-100)
    px, py = x + z * 0.34 + z * 0.2 * math.cos(a), y - z * 0.08 - z * 0.2 * math.sin(a)
    ui.fill_poly(surf, col, [(px + z * 0.12, py - z * 0.04), (px - z * 0.08, py - z * 0.1), (px - z * 0.02, py + z * 0.1)])


def icon_drive(surf, c, z, col):
    x, y = c
    pygame.draw.rect(surf, col, (round(x - z * 0.3), round(y - z * 0.22), round(z * 0.6), round(z * 0.26)),
                     border_radius=4)
    for dx in (-0.2, 0.2):
        ui.circle(surf, col, (x + dx * z, y + z * 0.14), z * 0.13)
    for k in range(3):
        pygame.draw.line(surf, col, (x - z * 0.52, y - z * 0.16 + k * z * 0.11), (x - z * 0.36, y - z * 0.16 + k * z * 0.11), 3)


# ----------------------------------------------------------------- εφέ
def magnet_arcs(surf, a, b, time, color=MAGNET):
    """Διακεκομμένες γραμμές «μαγνήτη» ανάμεσα στο κομμάτι και στη θέση του (κυλάνε προς τη θέση)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L < 6:
        return
    nx, ny = -dy / L, dx / L
    for k in (-1, 0, 1):
        bend = k * min(26, L * 0.35)
        pts = []
        for i in range(25):
            t = i / 24
            off = bend * math.sin(math.pi * t)
            pts.append((ax + dx * t + nx * off, ay + dy * t + ny * off))
        shift = int(time * 24) % 4
        for i in range(shift, 24, 4):
            pygame.draw.line(surf, color, pts[i], pts[min(24, i + 2)], 3)


def target_ring(surf, c, r, time, color=MAGNET):
    p = 0.5 + 0.5 * math.sin(time * 5)
    g = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
    for k in range(5, 0, -1):
        pygame.draw.circle(g, (*color, int((14 + 8 * p) * k)), (r * 2, r * 2), int(r + k * 4))
    surf.blit(g, (c[0] - r * 2, c[1] - r * 2))
    pygame.draw.circle(surf, (255, 255, 255), (round(c[0]), round(c[1])), int(r * (0.9 + 0.1 * p)), 3)


def plug_halo(surf, c, time, color=(255, 214, 60)):
    p = 0.5 + 0.5 * math.sin(time * 6)
    r = 15 + 4 * p
    g = pygame.Surface((60, 60), pygame.SRCALPHA)
    pygame.draw.circle(g, (*color, int(70 + 60 * p)), (30, 30), int(r))
    surf.blit(g, (c[0] - 30, c[1] - 30))
    pygame.draw.circle(surf, (255, 255, 255), (round(c[0]), round(c[1])), int(r), 2)


def pop(surf, c, age, word="κλικ!", color=(236, 118, 30)):
    if age > 0.8:
        return
    k = age / 0.8
    for i in range(8):
        a = 2 * math.pi * i / 8
        r0, r1 = 16 + 26 * k, 26 + 30 * k
        col = ui.mix((255, 210, 60), (255, 255, 255), k)
        pygame.draw.line(surf, col, (c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a)),
                         (c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)), max(1, int(4 * (1 - k)) + 1))
    img = ui.font(30).render(word, True, color)
    img.set_alpha(int(255 * (1 - k ** 2)))
    surf.blit(img, img.get_rect(center=(c[0], c[1] - 44 - 20 * k)))


def spin_mark(surf, c, time):
    """Βελάκι που γυρίζει: μια βίδα βιδώνεται εκεί που δεν φαίνεται (π.χ. κάτω από τη βάση)."""
    r = 13
    a0 = time * 9
    for w, col in ((8, (255, 255, 255)), (4, ORANGE)):
        ui.thick_arc(surf, col, c, r, a0, a0 + 4.6, w, 18)
    a = a0 + 4.6
    px, py = c[0] + r * math.cos(a), c[1] - r * math.sin(a)
    tx, ty = -math.sin(a), -math.cos(a)
    nx, ny = math.cos(a), -math.sin(a)
    ui.fill_poly(surf, ORANGE, [(px + nx * 7, py + ny * 7), (px - nx * 7, py - ny * 7),
                                (px + tx * 9, py + ty * 9)])


def cross(surf, c, age):
    """Κόκκινο Χ εκεί που άφησε το παιδί ένα κομμάτι σε λάθος θέση."""
    if age > 0.9:
        return
    a = int(255 * (1 - age / 0.9))
    s = pygame.Surface((70, 70), pygame.SRCALPHA)
    pygame.draw.circle(s, (*RED, a // 3), (35, 35), 32)
    pygame.draw.line(s, (*RED, a), (20, 20), (50, 50), 8)
    pygame.draw.line(s, (*RED, a), (20, 50), (50, 20), 8)
    surf.blit(s, (c[0] - 35, c[1] - 35))


def label_tip(surf, pos, s, color=GREEN):
    img = ui.font(20).render(s, True, ui.shade(color, 0.7))
    r = img.get_rect()
    box = r.inflate(22, 12)
    box.midbottom = (round(pos[0]), round(pos[1]) - 18)
    ui.panel(surf, box, (255, 255, 255), radius=10, border=color, shadow=False)
    surf.blit(img, img.get_rect(center=box.center))


# ----------------------------------------------------------------- εικονίδιο μενού
_menu_img = None


def menu_icon(surf, c):
    """Το R2 μισοτελειωμένο και ο ελεγκτής από πάνω, έτοιμος να κολλήσει σαν μαγνήτης."""
    global _menu_img
    if _menu_img is None:
        base = [P.chassis(), P.motor(-1), P.motor(1), P.wheel(-1), P.wheel(1), P.ultrasonic(), P.lego(), P.battery()]
        base += [P.standoff(x, y, P.DECK_Z, P.BOARD_Z) for x, y in P.STANDOFFS]
        flying = P.board().mapped(lambda p: (p[0], p[1], p[2] + 34), lambda n: n)
        cam = E.fit_camera(base + [flying], -30, 30, (220, 140), pad=4)
        img, _ = E.render(base + [flying], cam, pygame.Rect(0, 0, 220, 140))
        a = cam.proj((0, 50, P.BOARD_Z + 30))
        b = cam.proj((0, 50, P.BOARD_Z + 2))
        for dx in (-34, 0, 34):
            pa = cam.proj((dx, 50, P.BOARD_Z + 30))
            pb = cam.proj((dx, 50, P.BOARD_Z + 4))
            for i in range(0, 8, 2):
                t0, t1 = i / 8, (i + 1) / 8
                pygame.draw.line(img, MAGNET, (pa[0] + (pb[0] - pa[0]) * t0, pa[1] + (pb[1] - pa[1]) * t0),
                                 (pa[0] + (pb[0] - pa[0]) * t1, pa[1] + (pb[1] - pa[1]) * t1), 3)
        del a, b
        _menu_img = img
    surf.blit(_menu_img, _menu_img.get_rect(center=(c[0], c[1] + 2)))
