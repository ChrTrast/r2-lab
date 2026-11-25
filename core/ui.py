"""Κοινά εργαλεία για όλες τις οθόνες: γραμματοσειρές, χρώματα, κουμπιά, εικονίδια."""
import math

import pygame
import pygame.gfxdraw

FONT_NAMES = "segoeui,arial,dejavusans,freesans"
_fonts = {}


def font(size, bold=True):
    key = (int(size), bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(FONT_NAMES, int(size), bold=bold)
    return _fonts[key]


def mix(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1[:3], c2[:3]))


def shade(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c[:3])


def fill_poly(surf, color, pts, outline=None):
    p = [(round(x), round(y)) for x, y in pts]
    if len(p) < 3:
        return
    pygame.gfxdraw.filled_polygon(surf, p, color)
    pygame.gfxdraw.aapolygon(surf, p, outline if outline is not None else color)


def circle(surf, color, center, r, outline=None):
    x, y, r = round(center[0]), round(center[1]), max(1, round(r))
    pygame.gfxdraw.filled_circle(surf, x, y, r, color)
    pygame.gfxdraw.aacircle(surf, x, y, r, outline if outline is not None else color)


def text(surf, s, pos, size=24, color=(40, 40, 60), anchor="center", bold=True, shadow=None):
    img = font(size, bold).render(s, True, color)
    rect = img.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    if shadow:
        surf.blit(font(size, bold).render(s, True, shadow), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def panel(surf, rect, color, radius=18, border=None, shadow=True):
    rect = pygame.Rect(rect)
    if shadow:
        sh = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 55), sh.get_rect(), border_radius=radius)
        surf.blit(sh, rect.move(0, 5))
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width=3, border_radius=radius)


def glow(surf, rect, color, alpha, radius=22):
    rect = pygame.Rect(rect)
    g = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(g, (*color[:3], max(0, min(255, int(alpha)))), g.get_rect(), border_radius=radius)
    surf.blit(g, rect)


def star(surf, center, r, color, outline=(150, 100, 20)):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a)))
    fill_poly(surf, color, pts, outline)


# ------------------------------------------------------------------ icons
def thick_arc(surf, color, c, r, a0, a1, w, steps=28):
    outer, inner = [], []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        outer.append((c[0] + (r + w / 2) * math.cos(a), c[1] - (r + w / 2) * math.sin(a)))
        inner.append((c[0] + (r - w / 2) * math.cos(a), c[1] - (r - w / 2) * math.sin(a)))
    fill_poly(surf, color, outer + inner[::-1])


def icon_play(surf, c, s, col):
    x, y = c
    fill_poly(surf, col, [(x - s * 0.3, y - s * 0.4), (x + s * 0.42, y), (x - s * 0.3, y + s * 0.4)])


def icon_again(surf, c, s, col):
    r, w = s * 0.3, s * 0.13
    a0, a1 = math.radians(-60), math.radians(200)
    thick_arc(surf, col, c, r, a0, a1, w)
    # μύτη βέλους στο τέλος του τόξου, προς την κατεύθυνση της κίνησης
    px, py = c[0] + r * math.cos(a1), c[1] - r * math.sin(a1)
    tx, ty = -math.sin(a1), -math.cos(a1)
    nx, ny = math.cos(a1), -math.sin(a1)
    h = s * 0.2
    fill_poly(surf, col, [(px + nx * h, py + ny * h), (px - nx * h, py - ny * h),
                          (px + tx * h * 1.3, py + ty * h * 1.3)])


def icon_next(surf, c, s, col):
    x, y = c
    pts = [(x - s * 0.38, y - s * 0.1), (x + s * 0.05, y - s * 0.1), (x + s * 0.05, y - s * 0.3),
           (x + s * 0.42, y), (x + s * 0.05, y + s * 0.3), (x + s * 0.05, y + s * 0.1),
           (x - s * 0.38, y + s * 0.1)]
    fill_poly(surf, col, pts)


def icon_undo(surf, c, s, col):
    x, y = c
    w = s * 0.13
    cx, cy, r = x + s * 0.1, y + s * 0.04, s * 0.24
    thick_arc(surf, col, (cx, cy), r, -math.pi / 2, math.pi / 2, w, 16)
    fill_poly(surf, col, [(x - s * 0.2, cy - r - w / 2), (cx, cy - r - w / 2), (cx, cy - r + w / 2),
                          (x - s * 0.2, cy - r + w / 2)])
    fill_poly(surf, col, [(cx, cy + r - w / 2), (x - s * 0.12, cy + r - w / 2), (x - s * 0.12, cy + r + w / 2),
                          (cx, cy + r + w / 2)])
    fill_poly(surf, col, [(x - s * 0.44, cy - r), (x - s * 0.18, cy - r - s * 0.2), (x - s * 0.18, cy - r + s * 0.2)])


def icon_trash(surf, c, s, col):
    x, y = c
    fill_poly(surf, col, [(x - s * 0.34, y - s * 0.3), (x + s * 0.34, y - s * 0.3),
                          (x + s * 0.34, y - s * 0.21), (x - s * 0.34, y - s * 0.21)])
    fill_poly(surf, col, [(x - s * 0.1, y - s * 0.38), (x + s * 0.1, y - s * 0.38),
                          (x + s * 0.1, y - s * 0.3), (x - s * 0.1, y - s * 0.3)])
    fill_poly(surf, col, [(x - s * 0.27, y - s * 0.16), (x + s * 0.27, y - s * 0.16),
                          (x + s * 0.21, y + s * 0.38), (x - s * 0.21, y + s * 0.38)])


def icon_plus(surf, c, s, col):
    x, y = c
    a, b = s * 0.36, s * 0.09
    fill_poly(surf, col, [(x - a, y - b), (x + a, y - b), (x + a, y + b), (x - a, y + b)])
    fill_poly(surf, col, [(x - b, y - a), (x + b, y - a), (x + b, y + a), (x - b, y + a)])


def icon_star(surf, c, s, col):
    star(surf, c, s * 0.44, col, col)


def icon_prev(surf, c, s, col):
    icon_next(surf, c, -s, col)


def icon_home(surf, c, s, col, door=(0, 0, 0)):
    x, y = c
    fill_poly(surf, col, [(x - s * 0.42, y - s * 0.02), (x, y - s * 0.4), (x + s * 0.42, y - s * 0.02)])
    pygame.draw.rect(surf, col, (round(x - s * 0.28), round(y - s * 0.05), round(s * 0.56), round(s * 0.42)))
    pygame.draw.rect(surf, door, (round(x - s * 0.08), round(y + s * 0.12), round(s * 0.16), round(s * 0.25)))


def icon_sound(surf, c, s, col, on=True):
    x, y = c
    fill_poly(surf, col, [(x - s * 0.38, y - s * 0.12), (x - s * 0.2, y - s * 0.12), (x + s * 0.02, y - s * 0.34),
                          (x + s * 0.02, y + s * 0.34), (x - s * 0.2, y + s * 0.12), (x - s * 0.38, y + s * 0.12)])
    if on:
        for r in (0.2, 0.36):
            thick_arc(surf, col, (x + s * 0.02, y), s * r, -0.8, 0.8, s * 0.07, 10)
    else:
        w = max(2, round(s * 0.09))
        pygame.draw.line(surf, col, (x + s * 0.12, y - s * 0.16), (x + s * 0.42, y + s * 0.16), w)
        pygame.draw.line(surf, col, (x + s * 0.12, y + s * 0.16), (x + s * 0.42, y - s * 0.16), w)


def icon_close(surf, c, s, col):
    x, y = c
    w = max(3, round(s * 0.14))
    pygame.draw.line(surf, col, (x - s * 0.28, y - s * 0.28), (x + s * 0.28, y + s * 0.28), w)
    pygame.draw.line(surf, col, (x - s * 0.28, y + s * 0.28), (x + s * 0.28, y - s * 0.28), w)


class Button:
    """Μεγάλο, φιλικό κουμπί με εικονίδιο και μικρή λεζάντα."""

    def __init__(self, rect, label, icon, color, action, label_size=16):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.label_size = label_size
        self.icon = icon
        self.color = color
        self.action = action
        self.enabled = True
        self.pressed = False
        self.hover = False
        self.pulse = False

    def contains(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, surf, time=0.0):
        r = self.rect
        col = self.color if self.enabled else (182, 186, 194)
        if self.enabled and self.hover and not self.pressed:
            col = mix(col, (255, 255, 255), 0.14)
        if self.enabled and self.pulse:
            p = 0.5 + 0.5 * math.sin(time * 6)
            glow(surf, r.inflate(12 + 8 * p, 12 + 8 * p), (255, 214, 60), 90 + 110 * p)
        depth = 5
        face = r.move(0, depth if self.pressed else 0)
        pygame.draw.rect(surf, shade(col, 0.68), r.move(0, depth), border_radius=16)
        pygame.draw.rect(surf, col, face, border_radius=16)
        pygame.draw.rect(surf, mix(col, (255, 255, 255), 0.22),
                         (face.x + 8, face.y + 5, face.w - 16, 6), border_radius=3)
        fg = (255, 255, 255) if self.enabled else (240, 240, 244)
        cy = face.y + face.h * 0.40 if self.label else face.centery
        self.icon(surf, (face.centerx, cy), min(face.w, face.h) * 0.52, fg)
        if self.label:
            text(surf, self.label, (face.centerx, face.bottom - round(self.label_size * 0.9)), self.label_size, fg)
