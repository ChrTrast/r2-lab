"""Οι ζωγραφιές των αντικειμένων του Εργοστασίου, φτιαγμένες με κώδικα.

Κάθε ζωγραφιά είναι μια συνάρτηση που ζωγραφίζει σε μονάδες 0-100 (ένα τετράγωνο 100 x 100),
πάνω σε επιφάνεια 3 φορές μεγαλύτερη για λεία περιγράμματα (Pen). Σε ποιο κουτί πάει το καθένα
λέει το catalog.py. Τα προγράμματα είναι εικονίδια σαν αυτά της οθόνης, χωρίς αληθινά σήματα εταιρειών.
"""
import math

import pygame

from core import ui

INK = (24, 26, 34)
WHITE = (255, 255, 255)
OL = 2.4          # το πάχος του μαύρου περιγράμματος


class Pen:
    """Ζωγραφίζει σε μονάδες 0-100. ol = χρώμα περιγράμματος (None: χωρίς), bw = πάχος του."""

    def __init__(self, size, ss=3):
        self.k = size * ss / 100
        self.s = pygame.Surface((round(size * ss), round(size * ss)), pygame.SRCALPHA)
        self.size = (round(size), round(size))

    def _r(self, x, y, w, h):
        k = self.k
        return pygame.Rect(round(x * k), round(y * k), round(w * k), round(h * k))

    def rr(self, col, x, y, w, h, rad=0, ol=INK, bw=OL):
        k = self.k
        if ol:
            pygame.draw.rect(self.s, ol, self._r(x - bw, y - bw, w + 2 * bw, h + 2 * bw),
                             border_radius=round((rad + bw) * k) if rad else 0)
        pygame.draw.rect(self.s, col, self._r(x, y, w, h), border_radius=round(rad * k))

    def circ(self, col, x, y, r, ol=INK, bw=OL):
        k = self.k
        if ol:
            pygame.draw.circle(self.s, ol, (x * k, y * k), (r + bw) * k)
        pygame.draw.circle(self.s, col, (x * k, y * k), r * k)

    def ell(self, col, cx, cy, rx, ry, ol=INK, bw=OL):
        if ol:
            pygame.draw.ellipse(self.s, ol, self._r(cx - rx - bw, cy - ry - bw, 2 * (rx + bw), 2 * (ry + bw)))
        pygame.draw.ellipse(self.s, col, self._r(cx - rx, cy - ry, 2 * rx, 2 * ry))

    def poly(self, col, pts, ol=INK, bw=OL):
        k = self.k
        q = [(x * k, y * k) for x, y in pts]
        if ol:
            w = bw * k * 2
            pygame.draw.lines(self.s, ol, True, q, max(1, round(w)))
            for p in q:
                pygame.draw.circle(self.s, ol, p, w / 2)
        pygame.draw.polygon(self.s, col, q)

    def line(self, col, pts, w):
        k = self.k
        q = [(x * k, y * k) for x, y in pts]
        pygame.draw.lines(self.s, col, False, q, max(1, round(w * k)))
        for p in (q[0], q[-1]):
            pygame.draw.circle(self.s, col, p, w * k / 2)

    def arc(self, col, cx, cy, r, a0, a1, w, ol=INK, bw=OL, steps=30):
        """Χοντρό τόξο. Γωνίες σε μοίρες (0 = δεξιά, 90 = πάνω)."""
        def pts(rad):
            return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
                     cy - rad * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]
        self.poly(col, pts(r + w / 2) + pts(r - w / 2)[::-1], ol, bw)

    def text(self, s, x, y, size, col, bold=True):
        img = ui.font(size * self.k, bold).render(s, True, col)
        self.s.blit(img, img.get_rect(center=(round(x * self.k), round(y * self.k))))

    def done(self):
        return pygame.transform.smoothscale(self.s, self.size)


def bez(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def ellipse_pts(cx, cy, rx, ry, n=40, a0=0, a1=360):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy - ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# ================================================================ ΥΛΙΚΟ: συσκευές
def keyboard(p):
    p.line(INK, bez((50, 30), (47, 16), (64, 8)), 2.6)
    p.rr((206, 210, 220), 4, 30, 92, 46, 8)
    p.rr((226, 230, 238), 7, 32, 86, 6, 3, None)
    dark = (64, 68, 82)
    for r in range(3):
        for c in range(10):
            p.rr(dark, 8.5 + c * 8.5, 39 + r * 8.6, 6.4, 6.4, 1.6, None)
    for x in (8.5, 17, 25.5):
        p.rr(dark, x, 64.8, 6.4, 6.4, 1.6, None)
    p.rr(dark, 34, 64.8, 32.6, 6.4, 1.6, None)
    for x in (68.8, 77.3, 85.8):
        p.rr(dark, x, 64.8, 6.4, 6.4, 1.6, None)


def mouse(p):
    p.line(INK, bez((50, 26), (50, 10), (70, 6)), 2.6)
    p.ell((238, 240, 246), 50, 60, 23, 32)
    p.line((150, 156, 170), [(50, 29), (50, 55)], 1.6)
    p.line((150, 156, 170), bez((27.5, 52), (50, 60), (72.5, 52)), 1.6)
    p.rr((62, 132, 222), 46, 34, 8, 14, 4, INK, 1.6)
    p.ell((214, 218, 228), 50, 76, 14, 8, None)


def monitor(p):
    p.rr((76, 80, 94), 28, 84, 44, 8, 4)
    p.rr((110, 114, 128), 44, 66, 12, 20, 2)
    p.rr((44, 46, 56), 5, 10, 90, 60, 6)
    p.rr((88, 160, 238), 11, 16, 78, 46, 3, None)
    p.poly((140, 196, 250), [(11, 46), (40, 16), (58, 16), (24, 62), (11, 62)], None)
    p.circ((80, 220, 120), 84, 66, 1.6, None)


def printer(p):
    p.rr(WHITE, 24, 6, 52, 30, 2)
    for i in range(3):
        p.rr((200, 206, 218), 30, 13 + i * 6, 40 - i * 10, 2.4, 1, None)
    p.rr((210, 214, 224), 5, 32, 90, 44, 9)
    p.rr((172, 178, 190), 10, 37, 80, 9, 4, None)
    p.circ((240, 90, 80), 72, 56, 2.8, INK, 1.4)
    p.circ((80, 220, 120), 82, 56, 2.8, INK, 1.4)
    p.rr((60, 64, 76), 16, 64, 68, 6, 2, None)
    p.rr(WHITE, 22, 66, 56, 26, 2)
    for i, col in enumerate(((236, 80, 80), (250, 196, 50), (70, 170, 230))):
        p.rr(col, 29, 72 + i * 6, 42, 3.2, 1.2, None)


def speakers(p):
    for x in (6, 54):
        p.rr((54, 58, 72), x, 16, 40, 74, 8)
        p.circ((92, 98, 114), x + 20, 66, 13)
        p.circ((40, 42, 52), x + 20, 66, 5.4, None)
        p.circ((120, 126, 142), x + 20, 33, 6.6)
        p.circ((60, 64, 78), x + 20, 33, 2.6, None)


def headphones(p):
    p.arc((70, 74, 88), 50, 58, 35, 180, 0, 7.5)
    for x, inner in ((6, 25), (76, 69)):
        p.rr((62, 132, 222), x, 46, 18, 36, 8)
        p.rr((44, 48, 60), inner, 50, 6, 28, 3, None)


def microphone(p):
    p.ell((60, 64, 78), 50, 89, 25, 6)
    p.rr((150, 156, 170), 46, 60, 8, 28, 3)
    p.arc((110, 116, 130), 50, 42, 22, 200, 340, 4.4)
    p.rr((176, 182, 196), 34, 6, 32, 50, 16)
    for i in range(5):
        p.line((120, 126, 142), [(38, 14 + i * 6), (62, 14 + i * 6)], 1.4)
    p.rr((60, 64, 78), 34, 40, 32, 6, 0, None)


def webcam(p):
    p.poly((60, 64, 78), [(34, 80), (66, 80), (72, 92), (28, 92)])
    p.rr((110, 116, 130), 45, 60, 10, 22, 2)
    p.ell((238, 240, 246), 50, 42, 36, 27)
    p.circ((44, 46, 56), 50, 42, 15)
    p.circ((50, 70, 120), 50, 42, 11, None)
    p.circ((96, 146, 226), 50, 42, 6.4, None)
    p.circ(WHITE, 46, 38, 2.4, None)
    p.circ((80, 220, 120), 77, 32, 2.6, INK, 1.2)


def scanner(p):
    p.poly((188, 194, 208), [(10, 54), (90, 54), (82, 16), (18, 16)])
    p.poly((150, 158, 176), [(16, 50), (84, 50), (78, 22), (22, 22)], None)
    p.rr((214, 218, 228), 4, 52, 92, 30, 7)
    p.rr((110, 190, 226), 10, 55, 80, 7, 2, None)
    p.rr((140, 255, 200), 30, 55, 5, 7, 1, None)
    p.circ((80, 220, 120), 84, 72, 2.6, INK, 1.2)
    p.rr((170, 176, 190), 12, 70, 34, 4, 2, None)


def tower(p):
    p.rr((52, 56, 70), 24, 5, 52, 88, 6)
    p.rr((74, 78, 94), 30, 11, 40, 76, 4, None)
    p.rr((30, 32, 40), 34, 18, 32, 4.4, 1.4, None)
    p.circ((30, 32, 40), 50, 37, 7, None)
    p.circ((90, 170, 255), 50, 37, 4.6, None)
    p.arc(WHITE, 50, 37, 2.6, 120, 420, 1.2, None)
    p.line(WHITE, [(50, 33), (50, 37)], 1.2)
    for i in range(5):
        p.rr((40, 42, 52), 36, 55 + i * 6, 28, 2.8, 1.2, None)
    for x in (28, 64):
        p.rr(INK, x, 92, 8, 4, 1, None)


def laptop(p):
    p.rr((44, 46, 56), 15, 12, 70, 48, 5)
    p.rr((88, 160, 238), 20, 17, 60, 38, 2, None)
    p.poly((140, 196, 250), [(20, 44), (44, 17), (58, 17), (30, 55), (20, 55)], None)
    p.poly((200, 204, 216), [(10, 62), (90, 62), (99, 80), (1, 80)])
    for r in range(2):
        for c in range(9):
            p.rr((90, 94, 108), 15 + c * 7.8 - r * 1.4, 65 + r * 5, 5.4, 3.2, 1, None)
    p.rr((170, 176, 190), 40, 75, 20, 3.6, 1.4, None)


def usb(p):
    p.rr((196, 200, 210), 40, 6, 20, 24, 2)
    for x in (44, 52):
        p.rr((90, 96, 110), x, 12, 4, 4, 0.6, None)
    p.rr((62, 132, 222), 33, 28, 34, 64, 9)
    p.rr((120, 176, 240), 38, 34, 24, 34, 5, None)
    p.circ((44, 100, 190), 50, 82, 4, None)


# ============================================================ ΛΟΓΙΣΜΙΚΟ: εικονίδια προγραμμάτων
def _tile(p, col):
    p.rr(ui.shade(col, 0.7), 8, 12, 84, 84, 20, None)
    p.rr(col, 8, 8, 84, 84, 20)
    p.rr(ui.mix(col, WHITE, 0.25), 15, 12, 70, 9, 5, None)


def app_paint(p):
    _tile(p, (246, 140, 44))
    p.circ(WHITE, 46, 54, 27, INK, 1.8)
    p.circ((246, 140, 44), 54, 68, 6, INK, 1.4)
    for (x, y), c in zip(((33, 44), (46, 37), (59, 42), (32, 59)),
                         ((236, 70, 70), (250, 206, 50), (70, 180, 90), (60, 130, 230))):
        p.circ(c, x, y, 5, None)
    p.line((150, 96, 50), [(60, 80), (82, 40)], 5)
    p.line((196, 200, 210), [(82, 40), (85, 34)], 5)
    p.poly((60, 130, 230), [(83, 34), (88, 34), (90, 22), (86, 24)], None)


def app_text(p):
    _tile(p, (62, 132, 222))
    p.poly(WHITE, [(26, 18), (64, 18), (76, 30), (76, 84), (26, 84)], INK, 1.6)
    p.poly((200, 214, 236), [(64, 18), (64, 30), (76, 30)], INK, 1.2)
    p.text("Α", 40, 38, 22, (62, 132, 222))
    for i, w in enumerate((40, 40, 34, 40, 26)):
        p.rr((170, 180, 200), 32, 52 + i * 6.4, w, 2.6, 1, None)
    p.rr((170, 180, 200), 52, 34, 18, 2.6, 1, None)
    p.rr((170, 180, 200), 52, 41, 14, 2.6, 1, None)


def app_game(p):
    _tile(p, (150, 104, 206))
    p.rr((120, 196, 250), 18, 20, 64, 62, 8, INK, 1.6)
    p.rr((90, 190, 100), 18, 66, 64, 16, 0, None)
    p.rr((90, 190, 100), 18, 66, 64, 16, 8, INK, 1.6)
    p.rr((120, 196, 250), 19.6, 64, 60.8, 4, 0, None)
    p.line((90, 190, 100), [(19.6, 66), (80.4, 66)], 1.6)
    p.rr((236, 120, 50), 56, 54, 12, 12, 2, INK, 1.4)
    p.circ((236, 70, 70), 34, 46, 7, INK, 1.4)
    p.circ(WHITE, 36, 44, 2, None)
    for i in range(4):
        p.circ(WHITE, 40 + i * 6, 40 - i * 2.2, 1.2, None)
    ui.star(p.s, (66 * p.k, 34 * p.k), 6 * p.k, (252, 214, 60), INK)


def app_music(p):
    _tile(p, (226, 78, 140))
    p.poly(WHITE, [(40, 30), (72, 22), (72, 30), (40, 38)], None)
    p.rr(WHITE, 37, 30, 5, 38, 0, None)
    p.rr(WHITE, 69, 22, 5, 38, 0, None)
    p.ell(WHITE, 33, 70, 9, 7, None)
    p.ell(WHITE, 65, 62, 9, 7, None)


def app_photos(p):
    _tile(p, (250, 186, 46))
    p.rr(WHITE, 18, 22, 64, 56, 5, INK, 1.6)
    p.rr((130, 200, 250), 23, 27, 54, 46, 2, None)
    p.circ((255, 220, 70), 64, 40, 7, None)
    p.poly((90, 180, 90), [(23, 73), (23, 60), (40, 44), (56, 62), (64, 54), (77, 66), (77, 73)], None)


def app_video(p):
    _tile(p, (226, 64, 60))
    p.rr((40, 42, 52), 16, 26, 68, 50, 6, None)
    for i in range(6):
        p.rr(WHITE, 20 + i * 11, 29, 6, 5, 1, None)
        p.rr(WHITE, 20 + i * 11, 67, 6, 5, 1, None)
    p.rr(WHITE, 20, 37, 60, 28, 3, None)
    p.poly((226, 64, 60), [(44, 42), (60, 51), (44, 60)], None)


def app_web(p):
    _tile(p, (34, 166, 170))
    c = (34, 166, 170)
    p.circ(WHITE, 50, 52, 30, INK, 1.6)
    p.ell(WHITE, 50, 52, 13, 30, c, 2.4)
    p.line(c, [(20, 52), (80, 52)], 3)
    p.line(c, bez((26, 36), (50, 44), (74, 36)), 3)
    p.line(c, bez((26, 68), (50, 60), (74, 68)), 3)
    p.line(c, [(50, 22), (50, 82)], 3)


def app_code(p):
    _tile(p, (66, 176, 92))
    for i, (col, w) in enumerate((((252, 190, 40), 54), ((76, 140, 240), 46), ((168, 100, 220), 50))):
        y = 22 + i * 20
        p.rr(col, 20, y, w, 16, 3, INK, 1.4)
        p.rr(col, 28, y + 14, 10, 6, 1, None)
    p.poly(WHITE, [(26, 26), (34, 30), (26, 34)], None)


# ============================================================== ΚΑΔΟΣ: άσχετα με τον υπολογιστή
def umbrella(p):
    p.line(INK, [(50, 30), (50, 80)], 4.6)
    p.line((150, 96, 50), [(50, 30), (50, 80)], 2.4)
    p.arc((150, 96, 50), 58, 80, 8, 180, 360, 3.4, INK, 1.4)
    pts = ellipse_pts(50, 52, 44, 42, 40, 0, 180)
    for i in range(4):
        pts += ellipse_pts(17 + i * 22, 52, 11, 7, 8, 180, 0)
    p.poly((236, 70, 70), pts)
    for x in (28, 72):
        p.poly(WHITE, [(50, 11), (x - 4, 46), (x + 4, 46)], None)
    for x in (28, 50, 72):
        p.line((170, 40, 40), [(50, 11), (x, 45)], 1.4)
    p.circ(INK, 50, 9, 2.4, None)


def unicorn(p):
    head = [(30, 94), (28, 62), (34, 40), (48, 26), (64, 26), (78, 38), (90, 52), (90, 60), (82, 64),
            (66, 60), (58, 66), (58, 94)]
    p.poly(WHITE, head)
    p.poly(WHITE, [(46, 30), (48, 12), (58, 27)])
    p.poly((255, 200, 220), [(49, 26), (50, 18), (54, 26)], None)
    p.poly((252, 206, 54), [(60, 26), (74, 2), (68, 30)])
    for y in (10, 15, 20):
        p.line((200, 150, 30), [(66 + (20 - y) * 0.15, y + 2), (71 - (20 - y) * 0.05, y)], 1.2)
    for (x, y), col in zip(((40, 30), (31, 40), (25, 52), (23, 65), (24, 78), (27, 90)),
                           ((240, 100, 160), (250, 170, 60), (250, 220, 70), (90, 200, 120), (80, 160, 240),
                            (170, 110, 230))):
        p.circ(col, x, y, 7.5)
    p.circ(INK, 66, 42, 3.4, None)
    p.circ(WHITE, 67, 41, 1.1, None)
    p.circ((255, 170, 190), 80, 54, 4, None)
    p.circ(INK, 86, 53, 1.3, None)


def scooter(p):
    p.line(INK, [(70, 74), (62, 14)], 7)
    p.line((236, 70, 70), [(70, 74), (62, 14)], 4)
    p.line(INK, [(50, 14), (74, 14)], 6)
    p.line((70, 74, 88), [(50, 14), (74, 14)], 3.4)
    p.rr((236, 70, 70), 14, 70, 62, 8, 4)
    for x in (20, 76):
        p.circ((60, 64, 78), x, 84, 10)
        p.circ((196, 200, 210), x, 84, 4, None)


def ball(p):
    p.circ(WHITE, 50, 52, 38)
    for a0, col in ((-60, (236, 70, 70)), (0, (250, 206, 50)), (60, (60, 130, 230))):
        pts = []
        for i in range(21):
            t = -1 + i / 10
            y = 52 + 38 * t
            hw = 38 * math.sqrt(max(0.0, 1 - t * t))
            pts.append((50 + a0 / 60 * hw * 0.62 - hw * 0.22, y))
        for i in range(21):
            t = 1 - i / 10
            y = 52 + 38 * t
            hw = 38 * math.sqrt(max(0.0, 1 - t * t))
            pts.append((50 + a0 / 60 * hw * 0.62 + hw * 0.22, y))
        p.poly(col, pts, None)
    p.circ(WHITE, 36, 34, 5, None)


def shoe(p):
    p.poly((236, 70, 70), [(8, 72), (10, 40), (30, 38), (40, 48), (72, 58), (90, 64), (92, 74)])
    p.rr(WHITE, 6, 70, 88, 12, 6)
    p.poly(WHITE, [(10, 40), (30, 38), (26, 30), (12, 32)])
    for i in range(3):
        x = 36 + i * 9
        p.line(WHITE, [(x, 46 + i * 2), (x + 6, 54 + i * 2)], 3)
    p.rr((250, 206, 50), 10, 58, 16, 6, 3, None)


def apple(p):
    p.line((120, 80, 40), bez((50, 30), (48, 18), (56, 10)), 4)
    p.poly((80, 180, 80), [(52, 20), (66, 8), (78, 14), (64, 24)])
    p.circ((226, 50, 50), 36, 56, 26, None)
    p.circ((226, 50, 50), 64, 56, 26, None)
    pts = ellipse_pts(36, 56, 26, 26, 30, 70, 280) + ellipse_pts(64, 56, 26, 26, 30, -100, 110)
    p.poly((226, 50, 50), pts)
    p.ell((255, 140, 130), 34, 46, 6, 9, None)


def icecream(p):
    p.poly((226, 170, 100), [(28, 50), (72, 50), (50, 96)])
    for i in range(4):
        p.line((180, 120, 60), [(32 + i * 10, 50), (50 + i * 4, 90 - i * 4)], 1.4)
        p.line((180, 120, 60), [(68 - i * 10, 50), (50 - i * 4, 90 - i * 4)], 1.4)
    p.circ((120, 74, 50), 40, 44, 15)
    p.circ((255, 170, 200), 58, 42, 16)
    p.circ((250, 240, 220), 50, 26, 15)
    p.circ((226, 40, 60), 54, 10, 5)


def teddy(p):
    brown, light = (176, 116, 66), (226, 180, 130)
    for x in (30, 70):
        p.circ(brown, x, 14, 9)
        p.circ(light, x, 14, 4.6, None)
    p.circ(brown, 34, 76, 9)
    p.circ(brown, 66, 76, 9)
    p.circ(brown, 50, 72, 20)
    p.circ(light, 50, 74, 11, None)
    for x in (24, 76):
        p.circ(brown, x, 64, 8)
    p.circ(brown, 50, 32, 21)
    p.ell(light, 50, 40, 10, 8, None)
    p.circ(INK, 50, 36, 3, None)
    for x in (42, 58):
        p.circ(INK, x, 27, 2.6, None)
    p.line(INK, bez((45, 43), (50, 47), (55, 43)), 1.4)


def flower(p):
    p.line((70, 160, 70), [(50, 50), (50, 92)], 4)
    p.poly((90, 190, 90), [(50, 80), (30, 66), (24, 72), (46, 86)])
    p.poly((90, 190, 90), [(50, 70), (70, 58), (76, 64), (54, 76)])
    for i in range(8):
        a = math.radians(i * 45)
        p.circ((255, 140, 190), 50 + 17 * math.cos(a), 34 + 17 * math.sin(a), 10)
    for i in range(8):
        a = math.radians(i * 45)
        p.circ((255, 140, 190), 50 + 17 * math.cos(a), 34 + 17 * math.sin(a), 10, None)
    p.circ((252, 206, 54), 50, 34, 10)


def hat(p):
    p.ell((240, 200, 110), 50, 70, 46, 13)
    p.poly((240, 200, 110), [(26, 70), (30, 36), (50, 28), (70, 36), (74, 70)])
    p.ell((240, 200, 110), 50, 70, 46, 13, None)
    p.poly((240, 200, 110), [(26, 70), (30, 36), (50, 28), (70, 36), (74, 70)], None)
    p.line(INK, bez((26, 70), (50, 80), (74, 70)), 2)
    p.poly((60, 130, 230), [(28, 56), (72, 56), (73, 65), (27, 65)], None)
    p.circ((236, 70, 70), 64, 56, 5)


def bucket(p):
    p.arc((70, 74, 88), 50, 34, 26, 180, 0, 3.4, INK, 1.4)
    p.poly((60, 150, 236), [(22, 34), (78, 34), (70, 90), (30, 90)])
    p.rr((120, 190, 250), 20, 30, 60, 8, 4)
    p.rr((250, 206, 50), 34, 58, 32, 10, 5, None)
    p.line(INK, [(84, 20), (78, 66)], 5)
    p.line((236, 70, 70), [(84, 20), (78, 66)], 3)
    p.poly((236, 70, 70), [(72, 64), (86, 66), (84, 84), (72, 80)])


def carrot(p):
    for a in (-30, 0, 30):
        x = 50 + 18 * math.sin(math.radians(a))
        p.poly((80, 180, 80), [(46, 26), (x - 4, 4), (x + 4, 4), (54, 26)])
    p.poly((246, 140, 40), [(32, 24), (68, 24), (52, 96), (48, 96)])
    for y, s in ((40, -1), (56, 1), (70, -1)):
        x0 = 50 - 10 if s < 0 else 50 + 2
        p.line((200, 100, 30), [(x0, y), (x0 + 8, y)], 2)


# ------------------------------------------------------------------ όλες
DRAW = {
    "keyboard": keyboard, "mouse": mouse, "monitor": monitor, "printer": printer, "speakers": speakers,
    "headphones": headphones, "microphone": microphone, "webcam": webcam, "scanner": scanner, "tower": tower,
    "laptop": laptop, "usb": usb,
    "app_paint": app_paint, "app_text": app_text, "app_game": app_game, "app_music": app_music,
    "app_photos": app_photos, "app_video": app_video, "app_web": app_web, "app_code": app_code,
    "umbrella": umbrella, "unicorn": unicorn, "scooter": scooter, "ball": ball, "shoe": shoe, "apple": apple,
    "icecream": icecream, "teddy": teddy, "flower": flower, "hat": hat, "bucket": bucket, "carrot": carrot,
}
_cache = {}


def image(key, size):
    """Η ζωγραφιά σε τετράγωνο size x size pixels (με διάφανο φόντο)."""
    size = max(8, round(size))
    if (key, size) not in _cache:
        if len(_cache) > 400:
            _cache.clear()
        p = Pen(size)
        DRAW[key](p)
        _cache[key, size] = p.done()
    return _cache[key, size]
