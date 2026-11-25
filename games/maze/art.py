"""Τα γραφικά του Λαβύρινθου, ζωγραφισμένα με κώδικα: το R2, ο λαβύρινθος, ο φορτιστής, τα κουμπιά.

Το R2 φαίνεται από πάνω, με τα χρώματα του πραγματικού ρομπότ: μαύρο σασί και ρόδες, κίτρινα μοτέρ,
θήκη μπαταριών πίσω, λευκή πλακέτα polytech με χρωματιστές υποδοχές και το RGB LED,
διάφανο καπάκι και μπροστά ο αισθητήρας απόστασης («τα μάτια»).
"""
import math

import pygame
import pygame.gfxdraw

from core import ui
from . import logic

TEAL, ORANGE = (0, 164, 182), (240, 126, 40)          # κίνηση / στροφή
LED_BLUE, LED_RED, LED_GREEN = (90, 170, 255), (240, 60, 60), (70, 220, 110)
INK = (24, 26, 34)
MAX_CELL = 150        # οι μικροί λαβύρινθοι δεν μεγαλώνουν πιο πολύ από αυτό

_robots = {}


# ------------------------------------------------------------------ R2
def _bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def _paint_robot(size, led):
    """Το R2 να κοιτάει πάνω, με τα χρώματα του πραγματικού ρομπότ.

    Ζωγραφίζεται 3 φορές μεγαλύτερο και μικραίνει, για λεία περιγράμματα.
    """
    S = size * 3
    u = S / 100
    s = pygame.Surface((S, S), pygame.SRCALPHA)

    def R(x, y, w, h):
        return pygame.Rect(round(x * u), round(y * u), round(w * u), round(h * u))

    def rr(col, x, y, w, h, rad, border=None, bw=1.6, surf=s):
        pygame.draw.rect(surf, col, R(x, y, w, h), border_radius=round(rad * u))
        if border:
            pygame.draw.rect(surf, border, R(x, y, w, h), width=max(1, round(bw * u)), border_radius=round(rad * u))

    def circ(col, x, y, r):
        pygame.draw.circle(s, col, (x * u, y * u), r * u)

    # ρόδες: μαύρα λάστιχα με αυλακώσεις, γκρι ζάντα στην έξω πλευρά
    for x in (7, 79):
        rr((40, 42, 48), x, 26, 14, 48, 4, INK)
        for k in range(8):
            yy = 30 + k * 5.6
            pygame.draw.line(s, (70, 72, 82), ((x + 2.5) * u, yy * u), ((x + 11.5) * u, yy * u),
                             max(1, round(1.5 * u)))
        rr((120, 124, 136), x + (0.5 if x < 50 else 10.5), 33, 3, 34, 1.5)
    # κίτρινα μοτέρ που φαίνονται δίπλα στο σασί
    for x in (20.5, 74.5):
        rr((250, 200, 40), x, 34, 5, 32, 1.5, (190, 140, 20), bw=1)
    # μαύρο ακρυλικό σασί (ο σφαιρικός τροχός είναι από κάτω, μπροστά, και δεν φαίνεται από πάνω)
    rr((34, 35, 40), 24, 8, 52, 87, 6, INK, 1.4)
    # θήκη μπαταριών πίσω, με τις μπαταρίες
    rr((24, 25, 30), 30, 66, 40, 27, 3, INK, 1.2)
    for i in range(4):
        rr((70, 72, 80), 33 + i * 9, 68.5, 7, 22, 2)
        circ((200, 204, 214), 36.5 + i * 9, 89, 1.3)
    # γκρι μεταλλική βάση μπροστά, ο μπλε αισθητήρας και τα δύο ασημένια «μάτια» του
    rr((196, 200, 208), 27, 9, 46, 4, 1, (130, 134, 144), bw=1)
    rr((44, 104, 196), 28, 5, 44, 4.5, 1, (26, 64, 140), bw=1)
    for ex in (31, 55):
        rr((206, 210, 220), ex, 0.5, 14, 5.5, 2.5, (110, 116, 130), bw=1)
        rr((236, 240, 246), ex + 2, 1.3, 10, 1.6, 0.8)
    # λευκή πλακέτα polytech
    rr((240, 242, 238), 21, 17, 58, 48, 2.5, (176, 182, 188), bw=1.2)
    ports_back = (((250, 214, 40), (226, 52, 52)), ((52, 160, 76), (52, 160, 76)),
                  ((250, 214, 40), (226, 52, 52)), ((250, 214, 40), (226, 52, 52)))
    ports_front = (((70, 170, 230), (250, 214, 40)),) * 4
    for row, y0 in ((ports_back, 20), (ports_front, 53)):
        for i, (top, low) in enumerate(row):
            x0 = 24 + i * 11.5
            rr((36, 38, 44), x0, y0, 9.5, 9, 1)
            rr(top, x0 + 1, y0 + 1, 7.5, 3.5, 0.6)
            rr(low, x0 + 1, y0 + 4.5, 7.5, 3.5, 0.6)
    rr((206, 210, 218), 70.5, 52, 7, 10, 1, (150, 154, 166), bw=0.8)   # USB
    rr((48, 48, 56), 44, 37, 10, 8, 1)                                  # τσιπ
    circ((40, 40, 46), 32, 43, 3.8)                                     # βομβητής
    circ((255, 255, 255), 66, 41, 5)
    circ(led, 66, 41, 3.6)
    circ((255, 255, 255), 65, 39.8, 1.1)
    # χρυσές κολόνες με βίδες
    for x, y in ((24, 21), (76, 21), (24, 61), (76, 61)):
        circ((214, 172, 76), x, y, 2.6)
        circ((196, 200, 210), x, y, 1.4)
    # μπλε πλακέ καλώδιο από τον αισθητήρα ως την πλακέτα
    pts = [(x * u, y * u) for x, y in _bezier((50, 12), (76, 13), (49, 25))]
    pygame.draw.lines(s, (36, 84, 210), False, pts, max(2, round(2.8 * u)))
    # διάφανο ακρυλικό καπάκι (σε δικό του στρώμα, για να ανακατευτεί με την πλακέτα)
    glass = pygame.Surface((S, S), pygame.SRCALPHA)
    rr((220, 236, 255, 40), 19, 15, 62, 52, 2.5, (255, 255, 255, 200), bw=1.2, surf=glass)
    s.blit(glass, (0, 0))
    return pygame.transform.smoothscale(s, (size, size))


def robot(size, led=LED_BLUE, turns=0):
    """Το R2 σε μέγεθος size, γυρισμένο turns φορές 90° δεξιά (0 = κοιτάει πάνω)."""
    key = (size, tuple(led), turns % 4)
    if key not in _robots:
        img = _paint_robot(size, led) if turns % 4 == 0 else pygame.transform.rotate(robot(size, led), -90 * (turns % 4))
        if len(_robots) > 160:
            _robots.clear()
        _robots[key] = img
    return _robots[key]


def draw_robot(surf, center, size, angle, led=LED_BLUE):
    """angle: μοίρες δεξιόστροφα από το «πάνω» (0 πάνω, 90 δεξιά, 180 κάτω, 270 αριστερά)."""
    a = angle % 360
    k = round(a / 90)
    if abs(a - k * 90) < 0.5:
        img = robot(size, led, k)
    else:
        img = pygame.transform.rotozoom(robot(size, led), -a, 1.0)
    shadow = pygame.mask.from_surface(img, 100).to_surface(setcolor=(30, 40, 60, 60), unsetcolor=(0, 0, 0, 0))
    off = max(2, size // 22)
    surf.blit(shadow, shadow.get_rect(center=(center[0] + off, center[1] + off * 1.6)))
    surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


def bump_stars(surf, pos, age, size):
    """Αστεράκια εκεί που χτύπησε το R2. age: δευτερόλεπτα από το χτύπημα."""
    if age < 0 or age > 0.7:
        return
    fade = 1 - age / 0.7
    r = size * (0.18 + 0.25 * min(1.0, age / 0.25))
    for i in range(3):
        a = age * 5 + i * 2 * math.pi / 3
        p = (pos[0] + r * math.cos(a), pos[1] + r * math.sin(a) * 0.6)
        ui.star(surf, p, max(4, size * 0.11), (255, 210, 50, int(255 * fade)), (200, 140, 20, int(255 * fade)))


# ------------------------------------------------------------- στόχος
def charger(surf, rect, time=0.0, charging=False):
    """Ο φορτιστής: πράσινη βάση με κεραυνό. Όταν φορτίζει, λάμπει πιο δυνατά."""
    rect = pygame.Rect(rect)
    r = rect.inflate(-rect.w * 0.14, -rect.h * 0.14)
    if charging:
        alpha = 150 + 100 * math.sin(time * 8)
    else:
        alpha = 70 + 40 * math.sin(time * 3)
    ui.glow(surf, r.inflate(r.w * 0.14, r.h * 0.14), (120, 230, 150), alpha, radius=int(r.w * 0.28))
    pygame.draw.rect(surf, (44, 150, 86), r.move(0, max(2, r.h // 18)), border_radius=int(r.w * 0.2))
    pygame.draw.rect(surf, (84, 200, 124), r, border_radius=int(r.w * 0.2))
    inner = r.inflate(-r.w * 0.16, -r.h * 0.16)
    pygame.draw.rect(surf, (118, 220, 152), inner, border_radius=int(r.w * 0.14))
    bolt = [(0.60, 0.10), (0.28, 0.56), (0.47, 0.56), (0.38, 0.90), (0.74, 0.40), (0.54, 0.40), (0.66, 0.10)]
    color = (255, 248, 140) if charging and math.sin(time * 8) > 0 else (255, 255, 255)
    ui.fill_poly(surf, color, [(r.x + r.w * x, r.y + r.h * y) for x, y in bolt], (40, 140, 80))


def charge_rings(surf, center, time, size):
    """Πράσινοι κύκλοι που απλώνουν γύρω από το R2 όσο φορτίζει."""
    x, y = round(center[0]), round(center[1])
    for k in range(2):
        t = (time * 1.2 + k * 0.5) % 1.0
        r = size * (0.45 + 0.5 * t)
        color = (70, 220, 110, int(170 * (1 - t)))
        for dr in (-1, 0, 1):
            pygame.gfxdraw.aacircle(surf, x, y, max(1, round(r + dr)), color)


# ------------------------------------------------------------ λαβύρινθος
class Board:
    """Πού και σε τι μέγεθος μπαίνει ένας λαβύρινθος μέσα στο area, και η ζωγραφική του."""

    def __init__(self, maze, area):
        self.maze = maze
        area = pygame.Rect(area)
        self.cell = min((area.w - 36) // maze.cols, (area.h - 36) // maze.rows, MAX_CELL)
        w, h = self.cell * maze.cols, self.cell * maze.rows
        self.floor = pygame.Rect(area.centerx - w // 2, area.centery - h // 2, w, h)
        self.frame = self.floor.inflate(32, 32)
        self.wall_w = max(7, round(self.cell * 0.13))
        self.robot_size = int(self.cell * 0.84)
        self._walls = None

    def center(self, cell):
        return (self.floor.x + (cell[0] + 0.5) * self.cell, self.floor.y + (cell[1] + 0.5) * self.cell)

    def cell_rect(self, cell):
        return pygame.Rect(self.floor.x + cell[0] * self.cell, self.floor.y + cell[1] * self.cell, self.cell, self.cell)

    def draw_floor(self, surf):
        """Ξύλινο πλαίσιο, πάτωμα με πλακάκια και η αφετηρία (ζωγραφίζονται μία φορά)."""
        ui.panel(surf, self.frame, (150, 112, 76), radius=16, border=(116, 82, 52))
        pygame.draw.rect(surf, (252, 250, 242), self.floor)
        for c, r in self.maze.cells():
            if (c + r) % 2:
                pygame.draw.rect(surf, (246, 243, 232), self.cell_rect((c, r)))
        f, cs = self.floor, self.cell
        for c in range(self.maze.cols + 1):
            pygame.draw.line(surf, (232, 228, 214), (f.x + c * cs, f.y), (f.x + c * cs, f.bottom))
        for r in range(self.maze.rows + 1):
            pygame.draw.line(surf, (232, 228, 214), (f.x, f.y + r * cs), (f.right, f.y + r * cs))
        sr = self.cell_rect(self.maze.start).inflate(-cs * 0.16, -cs * 0.16)
        pygame.draw.rect(surf, (210, 230, 252), sr, border_radius=int(cs * 0.16))
        pygame.draw.rect(surf, (150, 190, 236), sr, width=max(2, cs // 30), border_radius=int(cs * 0.16))
        if cs >= 70:
            ui.text(surf, "ΑΡΧΗ", (sr.centerx, sr.bottom - cs * 0.13), max(11, int(cs * 0.14)), (110, 150, 200))

    def _segments(self):
        t, cs, m = self.wall_w, self.cell, self.maze
        segs = []
        for c, r in m.cells():
            x, y = self.floor.x + c * cs, self.floor.y + r * cs
            if not m.is_open((c, r), logic.UP):
                segs.append(pygame.Rect(x - t // 2, y - t // 2, cs + t, t))
            if not m.is_open((c, r), logic.LEFT):
                segs.append(pygame.Rect(x - t // 2, y - t // 2, t, cs + t))
            if c == m.cols - 1 and not m.is_open((c, r), logic.RIGHT):
                segs.append(pygame.Rect(x + cs - t // 2, y - t // 2, t, cs + t))
            if r == m.rows - 1 and not m.is_open((c, r), logic.DOWN):
                segs.append(pygame.Rect(x - t // 2, y + cs - t // 2, cs + t, t))
        return segs

    def walls(self):
        """Οι τοίχοι σε διάφανη εικόνα στο μέγεθος του πλαισίου (μπαίνουν πάνω από τη διαδρομή)."""
        if self._walls is None:
            t = self.wall_w
            layer = pygame.Surface(self.frame.size, pygame.SRCALPHA)
            segs = [s.move(-self.frame.x, -self.frame.y) for s in self._segments()]
            for s in segs:
                pygame.draw.rect(layer, (60, 40, 20, 60), s.move(2, 4), border_radius=t // 2)
            for s in segs:
                pygame.draw.rect(layer, (128, 88, 56), s, border_radius=t // 2)
            for s in segs:
                pygame.draw.rect(layer, (196, 146, 96), s.inflate(-4, -4), border_radius=t // 2)
            for s in segs:
                hl = s.inflate(-t * 0.5, -t * 0.5)
                if hl.w > 0 and hl.h > 0:
                    pygame.draw.rect(layer, (216, 174, 124), hl, border_radius=t // 3)
            self._walls = layer
        return self._walls

    def trail(self, surf, points):
        """Ο δρόμος που έκανε το R2: κίτρινες τελίτσες σε ίσες αποστάσεις, όπως στο lazblocks."""
        step = max(8.0, self.cell * 0.12)
        radius = max(2.5, self.cell * 0.035)
        left = 0.0
        for a, b in zip(points, points[1:]):
            dist = math.hypot(b[0] - a[0], b[1] - a[1])
            d = left
            while d < dist:
                t = d / dist
                ui.circle(surf, (246, 190, 40), (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), radius,
                          (200, 140, 20))
                d += step
            left = d - dist


# ------------------------------------------------------------- κουμπιά R2
def arrow_up(surf, c, s, col):
    x, y = c
    ui.fill_poly(surf, col, [(x - s * 0.13, y + s * 0.38), (x - s * 0.13, y - s * 0.02), (x - s * 0.34, y - s * 0.02),
                             (x, y - s * 0.4), (x + s * 0.34, y - s * 0.02), (x + s * 0.13, y - s * 0.02),
                             (x + s * 0.13, y + s * 0.38)])


def _flipped(draw, surf, c, s, col, fx, fy):
    tmp = pygame.Surface((int(s * 2), int(s * 2)), pygame.SRCALPHA)
    draw(tmp, (s, s), s, col)
    tmp = pygame.transform.flip(tmp, fx, fy)
    surf.blit(tmp, tmp.get_rect(center=(round(c[0]), round(c[1]))))


def arrow_down(surf, c, s, col):
    _flipped(arrow_up, surf, c, s, col, False, True)


def turn_left(surf, c, s, col):
    x, y = c
    w, r = s * 0.24, s * 0.24
    ac = (x - s * 0.02, y + s * 0.06)
    ui.thick_arc(surf, col, ac, r, 0, math.pi / 2, w, 18)
    ui.fill_poly(surf, col, [(ac[0] + r - w / 2, ac[1]), (ac[0] + r + w / 2, ac[1]),
                             (ac[0] + r + w / 2, y + s * 0.42), (ac[0] + r - w / 2, y + s * 0.42)])
    tip_y = ac[1] - r
    ui.fill_poly(surf, col, [(ac[0] - s * 0.4, tip_y), (ac[0] + 1, tip_y - s * 0.26), (ac[0] + 1, tip_y + s * 0.26)])


def turn_right(surf, c, s, col):
    _flipped(turn_left, surf, c, s, col, True, False)


def keycap(surf, center, d, pressed=False):
    """Μικρό πλήκτρο με βελάκι στη γωνία του κουμπιού: δείχνει ποιο βελάκι του πληκτρολογίου το πατάει."""
    r = pygame.Rect(0, 0, 30, 26)
    r.center = (round(center[0]), round(center[1]))
    pygame.draw.rect(surf, (150, 156, 170), r.move(0, 3), border_radius=6)
    face = r.move(0, 3 if pressed else 0)
    pygame.draw.rect(surf, (255, 255, 255), face, border_radius=6)
    pygame.draw.rect(surf, (150, 156, 170), face, width=1, border_radius=6)
    x, y = face.center
    dx, dy = logic.STEP[d]
    px, py = -dy, dx
    pygame.draw.line(surf, (60, 66, 84), (x - dx * 8, y - dy * 8), (x + dx * 2, y + dy * 2), 3)
    ui.fill_poly(surf, (60, 66, 84), [(x + dx * 8, y + dy * 8), (x + px * 6 + dx, y + py * 6 + dy),
                                      (x - px * 6 + dx, y - py * 6 + dy)])


def ctrl_button(surf, rect, color, icon, lines, key, pressed=False, hover=False, compact=False):
    """Μεγάλο κουμπί του χειριστηρίου. Πατημένο: κατεβαίνει, ανοίγει χρώμα και λάμπει κίτρινο.
    compact: χαμηλό και φαρδύ κουμπί, με τη λεζάντα σε μία γραμμή (χειριστήριο πάνω από το πρόγραμμα).
    key=None: χωρίς το πλήκτρο με το βελάκι στη γωνία (κουμπί που πατιέται μόνο με το ποντίκι)."""
    rect = pygame.Rect(rect)
    depth = 6 if compact else 7
    if pressed:
        ui.glow(surf, rect.inflate(18, 18).move(0, depth), (255, 214, 60), 190, radius=24)
    face = rect.move(0, depth if pressed else 0)
    col = ui.mix(color, (255, 255, 255), 0.2 if pressed else (0.1 if hover else 0.0))
    pygame.draw.rect(surf, ui.shade(color, 0.64), rect.move(0, depth), border_radius=18)
    pygame.draw.rect(surf, col, face, border_radius=18)
    pygame.draw.rect(surf, ui.mix(col, (255, 255, 255), 0.25), (face.x + 10, face.y + 6, face.w - 20, 6),
                     border_radius=3)
    if compact:
        icon(surf, (face.centerx, face.y + face.h * 0.40), face.h * 0.56, (255, 255, 255))
        ui.text(surf, " ".join(lines), (face.centerx, face.bottom - 13), 15, (255, 255, 255))
        if key is not None:
            keycap(surf, (face.right - 19, face.y + 18), key, pressed)
        return
    icon(surf, (face.centerx, face.y + face.h * 0.38), face.w * 0.62, (255, 255, 255))
    for i, line in enumerate(lines):
        ui.text(surf, line, (face.centerx, face.bottom - 16 - (len(lines) - 1 - i) * 17), 15, (255, 255, 255))
    if key is not None:
        keycap(surf, (face.right - 20, face.y + 19), key, pressed)


# ------------------------------------------------------------- μενού
_ICON_MAZE = """
    #######
    #S  # #
    ### # #
    #    G#
    #######
"""


def menu_icon(surf, c):
    maze = logic.Maze(_ICON_MAZE)
    # λίγο δεξιά και κάτω, για να μην το σκεπάζει το «0/15» της κάρτας
    board = Board(maze, pygame.Rect(c[0] - 115 + 42, c[1] - 62 + 6, 230, 124))
    board.draw_floor(surf)
    charger(surf, board.cell_rect(maze.goal))
    board.trail(surf, [board.center((0, 0)), board.center((1, 0))])
    surf.blit(board.walls(), board.frame)
    draw_robot(surf, board.center((1, 0)), board.robot_size, 180)
