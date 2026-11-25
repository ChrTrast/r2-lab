"""Τα γραφικά των Κύβων, ζωγραφισμένα με κώδικα: κύβοι, τοίχος, ράγα με το R2, τετράδιο."""
import math

import pygame

from core import ui
from games.runner import art as side       # το R2 από το πλάι, όπως στους Αριθμούς
from . import logic

COLORS = {logic.BLUE: (66, 112, 230), logic.RED: (232, 66, 66),
          logic.GREEN: (76, 186, 84), logic.YELLOW: (250, 206, 58)}
EDGE = (36, 38, 56)
AIR_EDGE = (110, 120, 145)


def _light(c):
    return ui.mix(c, (255, 255, 255), 0.3)


def _dark(c):
    return ui.shade(c, 0.68)


def _dashed(surf, color, p, q, width=1, dash=5, gap=4):
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    if length == 0:
        return
    ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
    d = 0.0
    while d < length:
        e = min(length, d + dash)
        pygame.draw.line(surf, color, (p[0] + ux * d, p[1] + uy * d), (p[0] + ux * e, p[1] + uy * e), width)
        d = e + gap


def _face(surf, color, pts, alpha):
    if alpha < 255:
        color = (*color[:3], alpha)
    ui.fill_poly(surf, color, pts)


def draw_cube(surf, ctype, x, bottom, size, alpha=255, outline=True, air_fill=True):
    """Κύβος με την μπροστινή κάτω-αριστερή γωνία στο (x, bottom).

    size: πλάτος της μπροστινής πλευράς. Ο μισός κύβος έχει το μισό ύψος.
    air_fill=False: ο διάφανος κύβος μόνο με γραμμές (για επιφάνειες με διαφάνεια, π.χ. το τετράδιο).
    """
    cube = logic.CUBES[ctype]
    d = size * 0.35
    h = size if cube.halves == 2 else size / 2
    top = bottom - h
    TL, TR, BR, BL = (x, top), (x + size, top), (x + size, bottom), (x, bottom)
    T1, T2 = (x + d, top - d), (x + size + d, top - d)
    R2 = (x + size + d, bottom - d)
    width = max(1, round(size / 22))

    if cube.kind == "air":
        if air_fill:
            fill = (255, 255, 255, min(alpha, 70))
            ui.fill_poly(surf, fill, [TL, TR, BR, BL])
            ui.fill_poly(surf, fill, [TL, T1, T2, TR])
            ui.fill_poly(surf, fill, [TR, T2, R2, BR])
        edge = AIR_EDGE if alpha >= 255 else (*AIR_EDGE, alpha)
        back = (x + d, bottom - d)
        for p, q in ((TL, TR), (TR, BR), (BR, BL), (BL, TL), (TL, T1), (T1, T2), (T2, TR), (T2, R2), (R2, BR),
                     (T1, back), (back, R2), (back, BL)):
            _dashed(surf, edge, p, q, width)
        return

    c = [COLORS[k] for k in cube.colors]
    if cube.kind == "solid":
        _face(surf, c[0], [TL, TR, BR, BL], alpha)
        _face(surf, _light(c[0]), [TL, T1, T2, TR], alpha)
        _face(surf, _dark(c[0]), [TR, T2, R2, BR], alpha)
    elif cube.kind == "diag_up":        # διαγώνιος από κάτω-αριστερά προς πάνω-δεξιά
        _face(surf, c[0], [TL, TR, BL], alpha)
        _face(surf, c[1], [TR, BR, BL], alpha)
        _face(surf, _light(c[0]), [TL, T1, T2, TR], alpha)
        _face(surf, _dark(c[1]), [TR, T2, R2, BR], alpha)
    elif cube.kind == "diag_down":      # διαγώνιος από πάνω-αριστερά προς κάτω-δεξιά
        _face(surf, c[0], [TL, TR, BR], alpha)
        _face(surf, c[1], [TL, BR, BL], alpha)
        _face(surf, _light(c[0]), [TL, T1, T2, TR], alpha)
        _face(surf, _dark(c[0]), [TR, T2, R2, BR], alpha)
    else:                               # split: αριστερό και δεξί μισό
        mx = x + size / 2
        _face(surf, c[0], [TL, (mx, top), (mx, bottom), BL], alpha)
        _face(surf, c[1], [(mx, top), TR, BR, (mx, bottom)], alpha)
        _face(surf, _light(c[0]), [TL, T1, (mx + d, top - d), (mx, top)], alpha)
        _face(surf, _light(c[1]), [(mx, top), (mx + d, top - d), T2, TR], alpha)
        _face(surf, _dark(c[1]), [TR, T2, R2, BR], alpha)
    if outline:
        edge = EDGE if alpha >= 255 else (*EDGE, alpha)
        if cube.kind == "diag_up":
            pygame.draw.line(surf, edge, BL, TR, width)
        elif cube.kind == "diag_down":
            pygame.draw.line(surf, edge, TL, BR, width)
        elif cube.kind == "split":
            pygame.draw.line(surf, edge, (x + size / 2, top), (x + size / 2, bottom), width)
        pygame.draw.lines(surf, edge, True, [BL, TL, T1, T2, R2, BR], width)
        pygame.draw.lines(surf, edge, False, [TL, TR, BR], width)
        pygame.draw.line(surf, edge, TR, T2, width)


def draw_columns(surf, columns, x, bottom, size, air_fill=True):
    """Ζωγραφίζει στήλες κύβων (από αριστερά προς τα δεξιά, από κάτω προς τα πάνω)."""
    for i, column in enumerate(columns):
        y = bottom
        for ctype in column:
            draw_cube(surf, ctype, x + i * size, y, size, air_fill=air_fill)
            y -= size * logic.CUBES[ctype].halves / 2


# ------------------------------------------------------------------ wall
def _motif(surf, kind, center, r, color):
    x, y = center
    w = 6
    if kind == "sun":
        pygame.draw.circle(surf, color, (x, y), int(r * 0.45), w)
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.line(surf, color, (x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6),
                             (x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9), w)
    elif kind == "star":
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r * 0.9 if i % 2 == 0 else r * 0.38
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        pygame.draw.lines(surf, color, True, pts, w)
    elif kind == "flower":
        for i in range(6):
            a = i * math.pi / 3
            pygame.draw.circle(surf, color, (x + math.cos(a) * r * 0.42, y + math.sin(a) * r * 0.42), int(r * 0.3), w)
        pygame.draw.circle(surf, color, (x, y), int(r * 0.18), w)
    elif kind == "moon":
        pygame.draw.arc(surf, color, (x - r * 0.7, y - r * 0.7, r * 1.4, r * 1.4), math.pi * 0.35, math.pi * 1.65, w)
        pygame.draw.arc(surf, color, (x - r * 0.3, y - r * 0.6, r * 1.1, r * 1.2), math.pi * 0.45, math.pi * 1.55, w)
    else:  # boat
        pygame.draw.lines(surf, color, False, [(x - r * 0.8, y + r * 0.3), (x - r * 0.5, y + r * 0.65),
                                               (x + r * 0.5, y + r * 0.65), (x + r * 0.8, y + r * 0.3)], w)
        pygame.draw.line(surf, color, (x - r * 0.8, y + r * 0.3), (x + r * 0.8, y + r * 0.3), w)
        pygame.draw.line(surf, color, (x, y + r * 0.3), (x, y - r * 0.8), w)
        pygame.draw.lines(surf, color, False, [(x, y - r * 0.8), (x + r * 0.6, y + r * 0.15), (x, y + r * 0.15)], w)


MOTIFS = ("sun", "flower", "star", "boat", "moon")


def build_room(size, wall_rect, cube, motif):
    """Το φόντο: δωμάτιο, ο τοίχος με το πλέγμα και το ράφι από κάτω."""
    W, H = size
    surf = pygame.Surface(size)
    for y in range(H):
        pygame.draw.line(surf, ui.mix((255, 244, 222), (246, 228, 200), y / H), (0, y), (W, y))
    for x in range(0, W, 46):
        pygame.draw.line(surf, (250, 236, 210), (x, 0), (x, H), 14)
    wr = pygame.Rect(wall_rect)
    frame = wr.inflate(28, 28)
    frame.height -= 12
    ui.panel(surf, frame, (214, 226, 244), radius=18, border=(170, 186, 214))
    pygame.draw.rect(surf, (232, 240, 252), wr)
    _motif(surf, motif, wr.center, wr.width * 0.36, (214, 226, 244))
    for i in range(logic.COLS + 1):
        pygame.draw.line(surf, (214, 224, 242), (wr.x + i * cube, wr.y), (wr.x + i * cube, wr.bottom), 1)
    for j in range(logic.MAX_HALVES // 2 + 1):
        pygame.draw.line(surf, (214, 224, 242), (wr.x, wr.bottom - j * cube), (wr.right, wr.bottom - j * cube), 1)
    # ράφι
    d = cube * 0.35
    left, right, y = wr.x - 22, wr.right + d + 22, wr.bottom
    ui.fill_poly(surf, (222, 178, 124), [(left, y), (left + d, y - d), (right, y - d), (right - d, y)])
    pygame.draw.rect(surf, (178, 132, 84), (left, y, right - d - left, 16))
    pygame.draw.line(surf, (150, 108, 66), (left, y + 16), (right - d, y + 16), 2)
    return surf


# ------------------------------------------------------------------ R2
RAIL_DARK, RAIL, RAIL_LIGHT = (96, 102, 118), (150, 158, 174), (206, 212, 224)
ARM_COLOR = (128, 134, 150)


def draw_rail(surf, left, right, y, brace_to):
    """Η ράγα του R2 πάνω από τον τοίχο (y = η πάνω πλευρά της, εκεί πατάει η ρόδα).
    brace_to: το σημείο του πλαισίου όπου στηρίζεται η αριστερή άκρη, που κρέμεται στον αέρα."""
    bx, by = brace_to
    pygame.draw.line(surf, RAIL_DARK, (left + 66, y + 6), (bx, by), 9)
    pygame.draw.line(surf, RAIL, (left + 66, y + 6), (bx, by), 5)
    ui.circle(surf, RAIL_LIGHT, (bx, by), 5, RAIL_DARK)
    beam = pygame.Rect(left, y, right - left, 10)
    pygame.draw.rect(surf, RAIL, beam, border_radius=3)
    pygame.draw.line(surf, RAIL_LIGHT, (left + 3, y + 1), (right - 4, y + 1), 2)
    pygame.draw.line(surf, RAIL_DARK, (left + 3, y + 8), (right - 4, y + 8), 2)
    pygame.draw.rect(surf, (70, 76, 92), beam, 1, border_radius=3)
    for x in range(left + 20, right - 10, 40):
        ui.circle(surf, RAIL_DARK, (x, y + 5), 2)
    for x in (left, right - 7):                    # τα τέρματα, για να μη φύγει το R2
        pygame.draw.rect(surf, (226, 84, 70), (x, y - 9, 7, 19), border_radius=2)
        pygame.draw.rect(surf, (150, 50, 40), (x, y - 9, 7, 19), 1, border_radius=2)


def draw_carrier(surf, x, rail_y, size, arm, hang_top, cube, ctype=None, push=0.0, push_dist=10,
                 spin=0.0, led=None, cube_scale=1.0):
    """Το R2 στη ράγα, από το πλάι, με το χέρι-βεντούζα μπροστά του.

    x: το κέντρο του R2. arm: πόσο μπροστά από το κέντρο αρχίζει ο κύβος που κρατά.
    hang_top: πού είναι η πάνω μπροστινή ακμή του κύβου. push: 0..1 πόσο τον έχει σπρώξει κάτω.
    """
    side.draw_r2(surf, (x, rail_y - size / 2), size, spin=spin, led=led or side.LED_BLUE)
    d = cube * 0.35
    rod_x = x + arm + cube * 0.5 + d / 2           # πάνω από τη μέση της πάνω πλευράς του κύβου
    face_y = hang_top - d / 2
    lid = rail_y - size + size * 0.19
    bar_y = min(lid - 3, hang_top - d - 7)
    servo = pygame.Rect(0, 0, round(size * 0.24), round(lid - bar_y + 3))
    servo.midbottom = (round(x + size * 0.2), round(lid + 1))
    pygame.draw.rect(surf, (52, 56, 68), servo, border_radius=3)
    pygame.draw.rect(surf, EDGE, servo, 1, border_radius=3)
    pygame.draw.line(surf, EDGE, (servo.centerx, bar_y), (rod_x + 3, bar_y), 7)
    pygame.draw.line(surf, ARM_COLOR, (servo.centerx, bar_y), (rod_x + 2, bar_y), 4)
    down = push * push_dist
    if ctype is not None and cube_scale > 0.05:
        s = cube * cube_scale
        h = s if logic.CUBES[ctype].halves == 2 else s / 2
        draw_cube(surf, ctype, rod_x - 0.675 * s, face_y + 0.175 * s + down + h, s)
    plate_y = face_y - 1 + down
    pygame.draw.line(surf, EDGE, (rod_x, bar_y), (rod_x, plate_y), 5)
    pygame.draw.line(surf, ARM_COLOR, (rod_x, bar_y), (rod_x, plate_y), 3)
    plate = pygame.Rect(0, 0, 18, 6)
    plate.midtop = (round(rod_x), round(plate_y - 2))
    pygame.draw.rect(surf, (60, 64, 78), plate, border_radius=3)
    pygame.draw.rect(surf, EDGE, plate, 1, border_radius=3)
    ui.circle(surf, (190, 196, 210), (servo.centerx, bar_y), 3, EDGE)


# --------------------------------------------------------------- notebook
def build_notebook(rect, pattern, title):
    """Το τετράδιο με το σχέδιο που πρέπει να φτιάξει το παιδί."""
    rect = pygame.Rect(rect)
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    ui.panel(surf, (0, 0, rect.w, rect.h - 6), (255, 253, 244), radius=16, shadow=False)
    for y in range(78, rect.h - 20, 26):
        pygame.draw.line(surf, (200, 222, 244), (36, y), (rect.w - 14, y), 1)
    pygame.draw.line(surf, (244, 170, 170), (54, 10), (54, rect.h - 16), 2)
    for y in range(22, rect.h - 20, 30):
        ui.circle(surf, (230, 226, 216), (20, y), 6, (180, 176, 168))
        pygame.draw.arc(surf, (110, 110, 120), (2, y - 9, 22, 18), math.pi * 0.5, math.pi * 1.5, 3)
    ui.text(surf, title, (rect.w // 2 + 16, 38), 26, (60, 70, 130))
    if pattern is None:
        for i, line in enumerate(("Φτιάξε ό,τι θέλεις!", "", "Χτίσε στον τοίχο", "με όποιους κύβους", "σου αρέσουν.")):
            ui.text(surf, line, (rect.w // 2 + 16, 110 + i * 32), 22, (90, 96, 130), bold=(i == 0))
        draw_cube(surf, 1, rect.w // 2 - 34, rect.h - 70, 40)
        draw_cube(surf, 4, rect.w // 2 + 8, rect.h - 70, 40)
        draw_cube(surf, 6, rect.w // 2 - 13, rect.h - 110, 40)
        return surf
    cols = pattern.columns
    tallest = max(sum(logic.CUBES[t].halves for t in c) for c in cols) / 2
    area_w, area_h = rect.w - 90, rect.h - 160
    size = int(min(38, area_w / (len(cols) + 0.35), area_h / (tallest + 0.35)))
    width = len(cols) * size + size * 0.35
    x = 54 + (rect.w - 54 - width) / 2
    bottom = rect.h - 84
    pygame.draw.line(surf, (150, 160, 190), (x - 10, bottom + 1), (x + width + 6, bottom + 1), 2)
    draw_columns(surf, cols, x, bottom, size, air_fill=False)
    if any(logic.CUBES[t].kind == "air" for c in cols for t in c):
        draw_cube(surf, 5, 70, rect.h - 22, 26, air_fill=False)
        ui.text(surf, "= κενός χώρος", (110, rect.h - 32), 19, (90, 96, 130), anchor="midleft")
    return surf


def draw_icon(surf, center):
    """Το εικονίδιο του παιχνιδιού στο μενού."""
    x, y = center
    s = 44
    bottom = y + 52
    draw_cube(surf, 3, x - 1.5 * s, bottom, s)
    draw_cube(surf, 2, x - 0.5 * s, bottom, s)
    draw_cube(surf, 4, x + 0.5 * s, bottom, s)
    draw_cube(surf, 1, x - 0.5 * s, bottom - s, s)
    draw_cube(surf, 6, x + 0.5 * s, bottom - s, s)
    draw_cube(surf, 11, x - 0.5 * s, bottom - 2 * s, s)
