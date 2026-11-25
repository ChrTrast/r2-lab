"""Το κεντρικό μενού: μια κάρτα για κάθε παιχνίδι της λίστας GAMES (games/__init__.py)."""
import importlib
import math
import random

import pygame

from core import ui
from core.app import HEIGHT, WIDTH, Scene
from games import GAMES
from games.maze import art as r2
from games.line_follow import art

CARD_W, CARD_H = 330, 220      # μέγεθος κάρτας όταν χωράει ολόκληρη
GAP = 30
PER_PAGE = 8
AREA = pygame.Rect(90, 146, 1100, 482)   # ο χώρος για τις κάρτες
LINE_Y, LINE_AMP, LINE_WAVE = 681, 8, 420   # η μαύρη γραμμή του line follower στο κάτω μέρος
ROBOT_SIZE, ROBOT_SPEED = 56, 80            # pixels, pixels/δευτερόλεπτο
PALETTE = [(62, 140, 226), (238, 146, 46), (84, 172, 96), (220, 88, 120), (156, 108, 210),
           (52, 172, 176), (230, 110, 70), (120, 130, 220), (200, 160, 40), (90, 160, 200)]


# ------------------------------------------------------------ card icons
def _icon_line_follow(surf, c):
    """Ακολούθησε: το R2 πάνω στη μαύρη γραμμή."""
    g0 = art.Geo(0, 0, tw=84, shift=40, th=66)

    def draw(s, g):
        for x in (0, 1):
            art.piece_tile(s, g, 6, x, 0)
        art.draw_robot(s, g, 1.0, 0.5, 1.0, 0.0)

    img = art.render(g0, 2 * 84 + 40 + 40, 66 + 110, (60, 92), draw)
    surf.blit(img, img.get_rect(center=(c[0] + 6, c[1] - 6)))


def _icon_maze(surf, c):
    r = pygame.Rect(0, 0, 120, 120)
    r.center = c
    pygame.draw.rect(surf, (250, 250, 240), r, border_radius=12)
    col, w = (60, 120, 70), 7
    for a, b in (((0, 0), (4, 0)), ((0, 0), (0, 4)), ((4, 0), (4, 4)), ((1, 4), (4, 4)), ((1, 1), (3, 1)),
                 ((1, 1), (1, 3)), ((2, 2), (4, 2)), ((2, 3), (3, 3)), ((2, 2), (2, 3))):
        p = (r.x + 12 + a[0] * 24, r.y + 12 + a[1] * 24)
        q = (r.x + 12 + b[0] * 24, r.y + 12 + b[1] * 24)
        pygame.draw.line(surf, col, p, q, w)
    ui.circle(surf, (236, 84, 70), (r.x + 12 + 0.5 * 24, r.y + 12 + 3.5 * 24), 8)
    ui.star(surf, (r.x + 12 + 3.5 * 24, r.y + 12 + 0.5 * 24), 10, (250, 204, 60))


def _icon_connect(surf, c):
    x, y = c
    pts = [(x - 56, y + 40), (x - 56, y - 6), (x, y - 50), (x + 56, y - 6), (x + 56, y + 40)]
    pygame.draw.lines(surf, (52, 150, 156), False, pts[:4], 5)
    for i, (px, py) in enumerate(pts):
        ui.circle(surf, (255, 255, 255), (px, py), 13, (40, 110, 120))
        ui.text(surf, str(i + 1), (px, py), 15, (40, 110, 120))


def _icon_letter(surf, c, game):
    """Για παιχνίδια χωρίς δικό τους εικονίδιο: το πρώτο γράμμα του τίτλου."""
    col = game["color"]
    ui.circle(surf, col, c, 56, ui.shade(col, 0.7))
    ui.circle(surf, ui.mix(col, (255, 255, 255), 0.25), (c[0] - 14, c[1] - 16), 18)
    ui.text(surf, game["title"][:1].upper(), (c[0], c[1] + 2), 74, (255, 255, 255), shadow=ui.shade(col, 0.6))


ICONS = {"line_follow": _icon_line_follow, "maze": _icon_maze, "connect": _icon_connect}


def card_rects(n):
    """Θέσεις για n κάρτες: μεγάλες όταν είναι λίγες, μικρότερες όταν είναι πολλές."""
    if n <= 0:
        return []
    cols = n if n <= 3 else (2 if n == 4 else (3 if n <= 6 else 4))
    rows = math.ceil(n / cols)
    s = min(1.0, (AREA.w - (cols - 1) * GAP) / cols / CARD_W, (AREA.h - (rows - 1) * GAP) / rows / CARD_H)
    w, h = round(CARD_W * s), round(CARD_H * s)
    y0 = AREA.y + (AREA.h - (rows * h + (rows - 1) * GAP)) // 2
    rects = []
    for r in range(rows):
        in_row = min(cols, n - r * cols)
        x0 = (WIDTH - (in_row * w + (in_row - 1) * GAP)) // 2
        rects += [pygame.Rect(x0 + c * (w + GAP), y0 + r * (h + GAP), w, h) for c in range(in_row)]
    return rects


def line_y(x):
    """Το ύψος της μαύρης γραμμής στο x: απαλά κύματα, για να στρίβει λίγο το R2."""
    return LINE_Y + LINE_AMP * math.sin(2 * math.pi * x / LINE_WAVE)


def line_angle(x):
    """Η κατεύθυνση του R2 στο x, σε μοίρες δεξιόστροφα από το «πάνω» (90 = δεξιά)."""
    slope = LINE_AMP * 2 * math.pi / LINE_WAVE * math.cos(2 * math.pi * x / LINE_WAVE)
    return 90 + math.degrees(math.atan(slope))


def _build_background():
    big = pygame.Surface((WIDTH * art.SS, HEIGHT * art.SS))
    top, low = (110, 178, 236), (206, 232, 250)
    for y in range(HEIGHT * art.SS):
        pygame.draw.line(big, ui.mix(top, low, y / (HEIGHT * art.SS)), (0, y), (WIDTH * art.SS, y))
    rng = random.Random(5)
    for _ in range(7):
        x, y, s = rng.uniform(0, WIDTH), rng.uniform(20, 560), rng.uniform(0.7, 1.4)
        for dx, dy, r in ((-30, 4, 22), (0, -6, 30), (32, 4, 22), (12, 10, 20)):
            pygame.draw.circle(big, (255, 255, 255), ((x + dx * s) * art.SS, (y + dy * s) * art.SS), r * s * art.SS)
    pygame.draw.rect(big, art.GRASS, (0, 640 * art.SS, WIDTH * art.SS, 80 * art.SS))
    k = art.SS
    # λευκή πίστα πάνω στο γρασίδι και η μαύρη γραμμή που ακολουθεί το R2
    pygame.draw.rect(big, (226, 222, 210), (0, 651 * k, WIDTH * k, 64 * k))
    pygame.draw.rect(big, (248, 246, 238), (0, 649 * k, WIDTH * k, 63 * k))
    for x in range(-10, WIDTH + 10, 2):
        pygame.draw.circle(big, (28, 28, 32), (x * k, line_y(x) * k), 6 * k)
    return pygame.transform.smoothscale(big, (WIDTH, HEIGHT))


class MenuScene(Scene):
    def __init__(self, app, games=None):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.bg = _build_background()
        self.games = []
        for i, entry in enumerate(GAMES if games is None else games):
            game = dict(entry)
            game.setdefault("color", PALETTE[i % len(PALETTE)])
            game["play"] = importlib.import_module(game["module"]) if game.get("module") else None
            self.games.append(game)
        self.pages = max(1, math.ceil(len(self.games) / PER_PAGE))
        self.exit_btn = ui.Button((1184, 14, 82, 70), "Έξοδος", ui.icon_close, (224, 84, 84), app.quit)
        self.prev_btn = ui.Button((14, 346, 62, 76), "", ui.icon_prev, (62, 132, 222), lambda: self.show_page(-1))
        self.next_btn = ui.Button((1204, 346, 62, 76), "", ui.icon_next, (62, 132, 222), lambda: self.show_page(1))
        self.pressed_button = None
        self.page = 0
        self.cards = []
        self.show_page(0)
        self.robot_x = -ROBOT_SIZE
        self.cursor = None

    def buttons(self):
        return [self.exit_btn] + ([self.prev_btn, self.next_btn] if self.pages > 1 else [])

    def show_page(self, step):
        self.page = (self.page + step) % self.pages
        shown = self.games[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]
        self.cards = [{"game": g, "rect": r, "img": self._card_image(g, r.size), "shake": -10.0}
                      for g, r in zip(shown, card_rects(len(shown)))]

    def _card_image(self, game, size):
        img = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        ready = game["play"] is not None
        col = game["color"] if ready else ui.mix(game["color"], (200, 204, 212), 0.55)
        ui.panel(img, (0, 0, CARD_W, CARD_H - 6), col, radius=26, shadow=False)
        pygame.draw.rect(img, (255, 255, 255), (12, 12, CARD_W - 24, 150), border_radius=18)
        icon = getattr(game["play"], "draw_icon", None) or ICONS.get(game["id"])
        if icon:
            icon(img, (CARD_W // 2, 87))
        else:
            _icon_letter(img, (CARD_W // 2, 87), game)
        ui.text(img, game["title"], (CARD_W // 2, 188), 30, (255, 255, 255), shadow=ui.shade(col, 0.6))
        if not ready:
            veil = pygame.Surface((CARD_W - 24, 150), pygame.SRCALPHA)
            veil.fill((255, 255, 255, 120))
            img.blit(veil, (12, 12))
            badge = pygame.Rect(CARD_W - 136, 20, 116, 34)
            pygame.draw.rect(img, (250, 204, 60), badge, border_radius=17)
            ui.text(img, "Σύντομα!", badge.center, 19, (120, 80, 20))
        elif getattr(game["play"], "LEVEL_COUNT", None):
            done = len(self.app.progress.completed(getattr(game["play"], "GAME_ID", game["id"])))
            pill = pygame.Rect(22, 22, 100, 30)
            pygame.draw.rect(img, (255, 255, 255), pill, border_radius=15)
            pygame.draw.rect(img, (250, 190, 50), pill, 2, border_radius=15)
            ui.star(img, (pill.x + 18, pill.centery), 10, (252, 204, 60))
            ui.text(img, f"{done}/{game['play'].LEVEL_COUNT}", (pill.x + 60, pill.centery), 18, (120, 90, 30))
        if size != (CARD_W, CARD_H):
            img = pygame.transform.smoothscale(img, size)
        return img

    def _card_at(self, pos):
        for card in self.cards:
            if card["rect"].collidepoint(pos):
                return card
        return None

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons():
                if b.contains(e.pos):
                    b.pressed = True
                    self.pressed_button = b
                    return
            card = self._card_at(e.pos)
            if card:
                self._open(card)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos):
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.app.quit()
            elif e.key == pygame.K_LEFT and self.pages > 1:
                self.show_page(-1)
            elif e.key == pygame.K_RIGHT and self.pages > 1:
                self.show_page(1)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                ready = [c for c in self.cards if c["game"]["play"]]
                if ready:
                    self._open(ready[0])

    def _open(self, card):
        game = card["game"]
        if game["play"] is None:
            card["shake"] = self.time
            self.app.sounds.play("deny", 0.6)
            return
        self.app.sounds.play("button")
        self.app.switch(game["play"].open_game(self.app))

    def update(self, dt):
        self.time += dt
        for b in self.buttons():
            b.hover = b.contains(self.mouse)
        self.robot_x += ROBOT_SPEED * dt
        if self.robot_x > WIDTH + ROBOT_SIZE:
            self.robot_x = -ROBOT_SIZE
        hand = self._card_at(self.mouse) is not None or any(b.contains(self.mouse) for b in self.buttons())
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        ui.text(screen, "Ας παίξουμε!", (WIDTH // 2, 58), 56, (255, 255, 255), shadow=(60, 110, 170))
        ui.text(screen, "Διάλεξε ένα παιχνίδι", (WIDTH // 2, 112), 26, (40, 70, 120))
        for card in self.cards:
            rect = card["rect"]
            ready = card["game"]["play"] is not None
            hover = rect.collidepoint(self.mouse)
            dx = 0
            age = self.time - card["shake"]
            if age < 0.45:
                dx = math.sin(age * 40) * 10 * (1 - age / 0.45)
            r = rect.move(dx, -6 if hover and ready else 0)
            if hover and ready:
                ui.glow(screen, r.inflate(14, 14), (255, 230, 120), 150, radius=32)
            sh = pygame.Surface((r.w, r.h - 6), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 50), sh.get_rect(), border_radius=26)
            screen.blit(sh, r.move(0, 8))
            screen.blit(card["img"], r)
        for b in self.buttons():
            b.draw(screen, self.time)
        if self.pages > 1:
            x0 = WIDTH // 2 - (self.pages - 1) * 11
            for i in range(self.pages):
                on = i == self.page
                ui.circle(screen, (62, 132, 222) if on else (255, 255, 255), (x0 + i * 22, 633), 7 if on else 5,
                          (40, 90, 160))
        x = self.robot_x
        r2.draw_robot(screen, (x, line_y(x)), ROBOT_SIZE, line_angle(x), r2.LED_GREEN)


def window_icon():
    """Το R2 (από πάνω, με πράσινο LED) για το εικονίδιο του παραθύρου."""
    return r2.robot(64, r2.LED_GREEN).copy()
