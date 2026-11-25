"""Οι ζωγραφιές των Λέξεων, φτιαγμένες με κώδικα.

Κάθε ζωγραφιά σχεδιάζεται σε τετράγωνο 0-100 (x δεξιά, y κάτω), 3 φορές μεγαλύτερο,
και μετά μικραίνει για λεία περιγράμματα. picture(name, size) τη δίνει έτοιμη (και τη θυμάται).
"""
import math

import pygame

OUT = (52, 52, 72)
_cache = {}


class _Pen:
    def __init__(self, size):
        self.u = size * 3 / 100
        self.size = size
        self.s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        self.lw = max(2, round(2.6 * self.u))

    def P(self, x, y):
        return (x * self.u, y * self.u)

    def circle(self, x, y, r, col, outline=True):
        if outline:
            pygame.draw.circle(self.s, OUT, self.P(x, y), r * self.u)
            pygame.draw.circle(self.s, col, self.P(x, y), r * self.u - self.lw)
        else:
            pygame.draw.circle(self.s, col, self.P(x, y), r * self.u)

    def poly(self, pts, col, outline=True):
        p = [self.P(x, y) for x, y in pts]
        pygame.draw.polygon(self.s, col, p)
        if outline:
            pygame.draw.polygon(self.s, OUT, p, self.lw)
            for q in p:
                pygame.draw.circle(self.s, OUT, q, self.lw / 2)

    def ellipse(self, x, y, rx, ry, col, angle=0.0, outline=True, n=40):
        a = math.radians(angle)
        pts = []
        for i in range(n):
            t = i * 2 * math.pi / n
            ex, ey = rx * math.cos(t), ry * math.sin(t)
            pts.append((x + ex * math.cos(a) - ey * math.sin(a), y + ex * math.sin(a) + ey * math.cos(a)))
        p = [self.P(*q) for q in pts]
        pygame.draw.polygon(self.s, col, p)
        if outline:
            pygame.draw.polygon(self.s, OUT, p, self.lw)

    def rect(self, x, y, w, h, col, rad=0, outline=True):
        r = pygame.Rect(round(x * self.u), round(y * self.u), round(w * self.u), round(h * self.u))
        pygame.draw.rect(self.s, col, r, border_radius=round(rad * self.u))
        if outline:
            pygame.draw.rect(self.s, OUT, r, width=self.lw, border_radius=round(rad * self.u))

    def line(self, pts, col, w=2.6):
        p = [self.P(x, y) for x, y in pts]
        pygame.draw.lines(self.s, col, False, p, max(1, round(w * self.u)))
        for q in (p[0], p[-1]):
            pygame.draw.circle(self.s, col, q, w * self.u / 2)

    def done(self):
        return pygame.transform.smoothscale(self.s, (self.size, self.size))


# ------------------------------------------------------------ οι ζωγραφιές
def apple(p):
    for x in (38, 62):
        p.circle(x, 60, 28, OUT, outline=False)
    for x in (38, 62):
        p.circle(x, 60, 28 - 2.6, (226, 60, 56), outline=False)
    p.ellipse(32, 50, 6, 9, (250, 150, 140), angle=20, outline=False)
    p.line([(50, 36), (54, 14)], (120, 76, 40), 4.5)
    p.ellipse(66, 18, 13, 6, (96, 184, 80), angle=-25)


def cat(p):
    orange, pink = (244, 162, 70), (250, 170, 180)
    for s in (1, -1):
        p.poly([(50 - s * 28, 42), (50 - s * 25, 8), (50 - s * 4, 28)], orange)
        p.poly([(50 - s * 24, 36), (50 - s * 23, 16), (50 - s * 10, 29)], pink, outline=False)
    p.ellipse(50, 58, 37, 31, orange)
    for x in (44, 50, 56):
        p.line([(x, 30), (x, 38)], (214, 120, 40), 2.6)
    for s in (1, -1):
        p.ellipse(50 - s * 13, 54, 6.5, 8.5, (120, 196, 96))
        p.ellipse(50 - s * 13, 54, 2.2, 6.5, OUT, outline=False)
        p.circle(50 - s * 13 - 2, 50, 1.6, (255, 255, 255), outline=False)
        p.line([(50 - s * 12, 67), (50 - s * 40, 63)], OUT, 1.8)
        p.line([(50 - s * 12, 71), (50 - s * 40, 74)], OUT, 1.8)
    p.poly([(45, 64), (55, 64), (50, 70)], pink)
    p.line([(50, 70), (50, 74), (44, 78)], OUT, 2)
    p.line([(50, 74), (56, 78)], OUT, 2)


def house(p):
    p.rect(64, 14, 11, 26, (180, 80, 60))
    p.rect(20, 44, 60, 46, (250, 214, 120))
    p.poly([(10, 48), (50, 12), (90, 48)], (222, 72, 60))
    p.rect(43, 62, 15, 28, (150, 92, 52), rad=2)
    p.circle(54, 77, 1.8, (250, 214, 120), outline=False)
    for x in (25, 63):
        p.rect(x, 54, 13, 13, (150, 206, 250))
        p.line([(x + 6.5, 54), (x + 6.5, 67)], OUT, 1.8)
        p.line([(x, 60.5), (x + 13, 60.5)], OUT, 1.8)


def boat(p):
    p.poly([(0, 80), (12, 76), (25, 80), (38, 76), (50, 80), (62, 76), (75, 80), (88, 76), (100, 80),
            (100, 100), (0, 100)], (96, 172, 232), outline=False)
    p.line([(50, 12), (50, 64)], (120, 76, 40), 3.2)
    p.poly([(50, 8), (63, 11), (50, 15)], (226, 60, 56))
    p.poly([(54, 18), (54, 58), (82, 58)], (255, 255, 255))
    p.poly([(46, 24), (46, 58), (24, 58)], (252, 232, 180))
    p.poly([(12, 62), (88, 62), (75, 82), (25, 82)], (176, 104, 52))
    p.line([(18, 70), (82, 70)], (230, 200, 120), 3)


def tree(p):
    p.ellipse(50, 91, 32, 5, (150, 210, 120), outline=False)
    p.poly([(43, 91), (57, 91), (55, 56), (45, 56)], (150, 92, 52))
    blobs = [(50, 34, 25), (29, 50, 18), (71, 50, 18), (50, 54, 18)]
    for x, y, r in blobs:
        p.circle(x, y, r, OUT, outline=False)
    for x, y, r in blobs:
        p.circle(x, y, r - 2.6, (84, 172, 82), outline=False)
    for x, y in ((38, 38), (62, 32), (58, 56), (32, 56), (70, 48)):
        p.circle(x, y, 4, (226, 60, 56))


def turtle(p):
    green, shell = (120, 196, 96), (66, 150, 84)
    for x in (28, 64):
        p.ellipse(x, 76, 8, 8, green)
    p.poly([(12, 66), (2, 72), (14, 72)], green)
    p.circle(84, 58, 11, green)
    p.circle(88, 55, 2.4, OUT, outline=False)
    pts = [(48 + 36 * math.cos(t), 68 - 32 * math.sin(t)) for t in (i * math.pi / 24 for i in range(25))]
    p.poly(pts, shell)
    for a, b in (((30, 46), (40, 38)), ((40, 38), (56, 38)), ((56, 38), (66, 46)), ((30, 46), (30, 64)),
                 ((66, 46), (66, 64)), ((40, 38), (40, 52)), ((56, 38), (56, 52)), ((40, 52), (56, 52)),
                 ((30, 58), (40, 52)), ((66, 58), (56, 52))):
        p.line([a, b], (40, 110, 60), 2)
    p.rect(11, 64, 74, 7, (200, 220, 110), rad=3)


def moon(p):
    p.circle(46, 52, 32, (250, 206, 60))
    pygame.draw.circle(p.s, (0, 0, 0, 0), p.P(64, 38), 28 * p.u)
    for x, y, r in ((80, 66, 7), (70, 84, 4.5), (86, 30, 5)):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        p.poly(pts, (250, 214, 90))


def shoe(p):
    p.poly([(14, 72), (16, 40), (34, 36), (46, 50), (70, 54), (86, 60), (92, 72)], (222, 72, 60))
    p.poly([(16, 40), (34, 36), (38, 42), (20, 46)], (250, 140, 120))
    p.poly([(8, 72), (94, 72), (94, 80), (88, 85), (12, 85), (8, 80)], (255, 255, 255))
    p.line([(10, 79), (92, 79)], (200, 206, 220), 2)
    for k in range(3):
        x = 40 + k * 8
        p.line([(x, 49 + k), (x + 7, 43 + k)], (255, 255, 255), 2.8)
    p.poly([(24, 60), (60, 58), (78, 66), (40, 66)], (250, 214, 90))


def bicycle(p):
    for x in (24, 76):
        pygame.draw.circle(p.s, OUT, p.P(x, 66), 19 * p.u, round(4.5 * p.u))
        pygame.draw.circle(p.s, (120, 126, 140), p.P(x, 66), 14.8 * p.u, max(1, round(1.2 * p.u)))
        for k in range(6):
            a = k * math.pi / 3
            p.line([(x, 66), (x + 14 * math.cos(a), 66 + 14 * math.sin(a))], (150, 156, 170), 1.2)
        p.circle(x, 66, 3, (150, 156, 170))
    red = (62, 132, 222)
    for a, b in (((24, 66), (44, 42)), ((44, 42), (68, 42)), ((68, 42), (76, 66)), ((44, 42), (50, 66)),
                 ((50, 66), (24, 66)), ((50, 66), (68, 42))):
        p.line([a, b], red, 3.6)
    p.line([(44, 42), (42, 32)], OUT, 3)
    p.rect(34, 28, 16, 6, OUT, rad=3, outline=False)
    p.line([(68, 42), (66, 28), (76, 26)], OUT, 3)
    p.circle(50, 66, 5, (250, 206, 60))


def flower(p):
    p.line([(50, 56), (50, 95)], (70, 150, 70), 4.5)
    p.ellipse(62, 80, 12, 5.5, (96, 184, 80), angle=-30)
    p.ellipse(38, 74, 10, 5, (96, 184, 80), angle=30)
    petals = [(50 + 17 * math.cos(k * math.pi / 3), 36 + 17 * math.sin(k * math.pi / 3)) for k in range(6)]
    for x, y in petals:
        p.circle(x, y, 13, OUT, outline=False)
    for x, y in petals:
        p.circle(x, y, 13 - 2.6, (240, 120, 170), outline=False)
    p.circle(50, 36, 11, (250, 206, 60))


def butterfly(p):
    for s in (1, -1):
        p.ellipse(50 - s * 20, 36, 20, 16, (250, 150, 60), angle=s * 25)
        p.ellipse(50 - s * 17, 66, 14, 12, (170, 110, 220), angle=-s * 20)
        p.circle(50 - s * 22, 34, 5, (255, 255, 255))
        p.circle(50 - s * 17, 68, 3.5, (255, 255, 255))
    p.ellipse(50, 52, 5, 25, OUT, outline=False)
    p.line([(49, 30), (41, 13)], OUT, 2)
    p.line([(51, 30), (59, 13)], OUT, 2)
    p.circle(41, 13, 2.6, OUT, outline=False)
    p.circle(59, 13, 2.6, OUT, outline=False)


def airplane(p):
    blue = (70, 130, 220)
    p.poly([(46, 46), (58, 46), (44, 24), (36, 24)], (50, 96, 180))
    p.poly([(10, 44), (22, 44), (17, 20), (9, 20)], blue)
    p.rect(8, 40, 84, 20, (236, 240, 250), rad=10)
    p.poly([(80, 44), (88, 46), (90, 50), (80, 50)], (60, 90, 160), outline=False)
    for k in range(5):
        p.circle(30 + k * 9, 48, 2.6, (120, 180, 240), outline=False)
    p.poly([(42, 54), (60, 54), (46, 80), (34, 80)], blue)


DRAW = {"apple": apple, "cat": cat, "house": house, "boat": boat, "tree": tree, "turtle": turtle,
        "moon": moon, "shoe": shoe, "bicycle": bicycle, "flower": flower, "butterfly": butterfly,
        "airplane": airplane}


def picture(name, size):
    key = (name, size)
    if key not in _cache:
        pen = _Pen(size)
        DRAW[name](pen)
        _cache[key] = pen.done()
    return _cache[key]


def draw(surf, rect, name):
    rect = pygame.Rect(rect)
    img = picture(name, min(rect.w, rect.h))
    surf.blit(img, img.get_rect(center=rect.center))


def preview(names=None, size=150):
    """Όλες οι ζωγραφιές σε μια εικόνα (για έλεγχο με το μάτι)."""
    names = names or list(DRAW)
    sheet = pygame.Surface((len(names) * (size + 10) + 10, size + 20))
    sheet.fill((240, 244, 252))
    for i, n in enumerate(names):
        sheet.blit(picture(n, size), (10 + i * (size + 10), 10))
    return sheet
