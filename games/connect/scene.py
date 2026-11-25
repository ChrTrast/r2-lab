"""Ένωσε: πάτα τις τελείες με τη σειρά 1, 2, 3… και το R2 τις ενώνει ζωγραφίζοντας.

Το R2 περιμένει σε μια κάτω γωνία του χαρτιού. Με κάθε σωστό κλικ στρίβει προς την τελεία
και πηγαίνει εκεί με κατεβασμένο μαρκαδόρο, αφήνοντας τη γραμμή πίσω του. Στο τέλος
εμφανίζεται ο φορτιστής, το R2 πηγαίνει να φορτίσει, και ένα κλικ στη ζωγραφιά φέρνει την επόμενη.
"""
import math

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.maze import art as r2art
from . import GAME_ID, logic, pictures

BOARD = pygame.Rect(160, 106, *pictures.CANVAS)
TOP_H = 92
CENTER_X = 652
R2_SIZE = 60
CHARGER_SIZE = 84
DRIVE_SPEED = 330       # pixels το δευτερόλεπτο
DRIVE_MIN, DRIVE_MAX = 0.22, 0.85
TURN_SPEED = 420        # μοίρες το δευτερόλεπτο
TURN_MAX = 0.35
HOME_FASTER = 1.5       # πόσο πιο γρήγορα πηγαίνει στον φορτιστή
WAIT_BEFORE_HOME = 0.35
REVEAL_AFTER = 0.6      # πότε αρχίζει να φαίνεται η έγχρωμη εικόνα, αφού τελειώσει η ζωγραφιά
FADE_TIME = 1.0
CELEBRATE_AFTER = 0.5   # πότε αρχίζει η γιορτή, αφού φτάσει το R2 στον φορτιστή
NEXT_HINT_AFTER = 3.0   # πότε λέει «Πάτα τη ζωγραφιά…», αφού φτάσει στον φορτιστή
NOTES = 8

MSG = {
    "start": "Πάτα τις τελείες με τη σειρά 1, 2, 3… και το R2 τις ενώνει!",
    "find": "Ψάξε το {n}!",
    "group": "Μπράβο! {name}!",
    "done": "Μπράβο! {title}",
    "next": "Πάτα τη ζωγραφιά για την επόμενη!",
}


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pop(t):
    """Από 0 σε 1 με ένα μικρό «φούσκωμα» στο τέλος."""
    t = max(0.0, min(1.0, t)) - 1
    return 1 + 2.7 * t ** 3 + 1.7 * t ** 2


def banner_charger(surf, c):
    r2art.charger(surf, (c[0] - 32, c[1] - 32, 64, 64))


class Painter:
    """Το R2 με τον μαρκαδόρο. Κάνει τις κινήσεις με τη σειρά που του δίνονται:
    πρώτα στρίβει προς τον στόχο και μετά προχωρά. Με κατεβασμένο μαρκαδόρο αφήνει γραμμή.
    Θέσεις σε σημεία του καμβά. Όσο περισσότερες κινήσεις περιμένουν, τόσο πιο γρήγορα πηγαίνει."""

    def __init__(self, pos):
        self.pos = tuple(pos)
        self.angle = 0.0                     # μοίρες δεξιόστροφα από το «πάνω»
        self.moves = []
        self.anim = None
        self.ink = []                        # οι γραμμές που ζωγράφισε
        self.end = self.pos                  # πού θα είναι όταν τελειώσουν όλες οι κινήσεις

    @property
    def busy(self):
        return self.anim is not None or bool(self.moves)

    def go(self, target, pen, faster=1.0):
        self.moves.append({"to": tuple(target), "pen": pen, "faster": faster, "wait": 0.0})
        self.end = tuple(target)

    def wait(self, seconds):
        self.moves.append({"to": self.end, "pen": False, "faster": 1.0, "wait": seconds})

    def _begin(self, now):
        m = self.moves.pop(0)
        hurry = 1 + 0.6 * len(self.moves)
        (ax, ay), (bx, by) = self.pos, m["to"]
        dist = math.hypot(bx - ax, by - ay)
        delta = 0.0
        if dist > 0.5:
            heading = math.degrees(math.atan2(bx - ax, -(by - ay)))
            delta = (heading - self.angle + 180) % 360 - 180
        turn = min(TURN_MAX, abs(delta) / TURN_SPEED) / hurry if abs(delta) > 2 else 0.0
        drive = 0.0
        if dist > 0.5:
            drive = max(DRIVE_MIN, min(DRIVE_MAX, dist / DRIVE_SPEED)) / (hurry * m["faster"])
        drive = max(drive, m["wait"])
        self.anim = {"start": now, "turn": turn, "drive": drive, "end": now + turn + drive,
                     "a": self.pos, "b": m["to"], "a_angle": self.angle, "b_angle": self.angle + delta,
                     "pen": m["pen"] and dist > 0.5, "rolling": False, "moves": dist > 0.5}

    def update(self, now):
        """Προχωρά την κίνηση. Επιστρέφει ("drive",) όταν ξεκινά να προχωρά και ("arrive",) όταν φτάνει."""
        events = []
        a = self.anim
        if a and now >= a["end"]:
            self.pos, self.angle = a["b"], a["b_angle"] % 360
            if a["pen"]:
                self.ink.append((a["a"], a["b"]))
            self.anim = None
            events.append(("arrive",))
        if self.anim is None and self.moves:
            self._begin(a["end"] if a else now)
        a = self.anim
        if a and a["moves"] and not a["rolling"] and now >= a["start"] + a["turn"]:
            a["rolling"] = True
            events.append(("drive",))
        return events

    def state(self, now):
        """(θέση, γωνία, πού φτάνει η γραμμή που ζωγραφίζει τώρα ή None)."""
        a = self.anim
        if a is None:
            return self.pos, self.angle, None
        t = now - a["start"]
        if t < a["turn"]:
            k = ease(t / a["turn"])
            return a["a"], a["a_angle"] + (a["b_angle"] - a["a_angle"]) * k, None
        k = ease((t - a["turn"]) / a["drive"]) if a["drive"] > 0 else 1.0
        pos = (a["a"][0] + (a["b"][0] - a["a"][0]) * k, a["a"][1] + (a["b"][1] - a["a"][1]) * k)
        return pos, a["b_angle"], (pos if a["pen"] else None)


class ConnectScene(Scene):
    def __init__(self, app, index=0):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.confetti = fx.Confetti()
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 215))
        self.room = self._room()
        self.final_surf = pygame.Surface(pictures.CANVAS)
        self.dots_xy = [(CENTER_X - (len(pictures.PICTURES) - 1) * 16 + i * 32, 30)
                        for i in range(len(pictures.PICTURES))]
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((116, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_picture)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        self.buttons = [self.btn_again, self.btn_next, self.btn_sound, self.btn_menu]
        self.load(index)

    # ------------------------------------------------------------- setup
    @staticmethod
    def _room():
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(surf, ui.mix((236, 246, 236), (214, 234, 220), y / HEIGHT), (0, y), (WIDTH, y))
        frame = BOARD.inflate(28, 28)
        ui.panel(surf, frame, (196, 150, 100), radius=16, border=(150, 106, 64))
        # μολύβια δεξιά και αριστερά, για στολίδι
        for i, col in enumerate(((230, 70, 70), (250, 190, 50), (70, 150, 230), (90, 180, 90))):
            x = 40 + i * 24 if i < 2 else WIDTH - 136 + i * 24
            y0, y1 = 230 + (i % 2) * 40, 560 + (i % 2) * 40
            pygame.draw.rect(surf, col, (x, y0, 16, y1 - y0), border_radius=3)
            ui.fill_poly(surf, (240, 210, 160), [(x, y1), (x + 16, y1), (x + 8, y1 + 22)])
            ui.fill_poly(surf, (60, 60, 70), [(x + 5, y1 + 14), (x + 11, y1 + 14), (x + 8, y1 + 22)])
        return surf

    def load(self, index):
        self.index = index % len(pictures.PICTURES)
        self.pic = pictures.PICTURES[self.index]
        self.game = logic.DotGame(self.pic.groups)
        self.home = logic.home_position(self.pic.groups, pictures.CANVAS, side=self.pic.home)
        self.painter = Painter(self.home)
        self.drawn_time = None                # πότε τελείωσε το R2 τη ζωγραφιά
        self.charge_time = None               # πότε έφτασε στον φορτιστή
        self.celebrated = False
        self.hint_until = -1.0
        self.red_until = -1.0
        self.marks = []                       # σημάδια από λάθος κλικ
        self.labels = logic.label_positions(self.pic.groups)
        self.paper = self._paper()
        self.backdrop = self.pic.backdrop()
        self.banner = fx.Banner("Μπράβο!", self.pic.title, icon=banner_charger)
        self.confetti.clear()
        self.message = MSG["start"]

    def _paper(self):
        if self.pic.dark:
            surf = self.pic.backdrop()
        else:
            surf = pygame.Surface(pictures.CANVAS)
            surf.fill((255, 253, 244))
            for y in range(24, pictures.CANVAS[1], 32):
                pygame.draw.line(surf, (232, 238, 248), (0, y), (pictures.CANVAS[0], y), 1)
        self.pic.sketch(surf, pictures.make_tf(), self.ink)
        return surf

    @property
    def ink(self):
        return pictures.LIGHT_LINE if self.pic.dark else pictures.OUTLINE

    @property
    def can_go_next(self):
        """Μετά τη ζωγραφιά, ένα κλικ πάνω της φέρνει την επόμενη (λίγο αργότερα, για να μη γίνει κατά λάθος)."""
        return self.drawn_time is not None and self.time >= self.drawn_time + REVEAL_AFTER

    # ------------------------------------------------------------ actions
    def restart(self):
        self.load(self.index)

    def next_picture(self):
        self.app.sounds.play("swoosh", 0.7)
        self.load(self.index + 1)

    def to_menu(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def click(self, pos):
        canvas = (pos[0] - BOARD.x, pos[1] - BOARD.y)
        dots = self.game.dots
        for ev in self.game.click(canvas):
            kind = ev[0]
            if kind == "dot":
                self.app.sounds.play(f"note{ev[1] % NOTES}", 0.8)
                self.hint_until = -1.0
                if self.message.startswith("Ψάξε"):
                    self.message = MSG["start"]
                if ev[1] in self.game.starts:
                    # αρχή ομάδας: το R2 πηγαίνει εκεί με σηκωμένο μαρκαδόρο
                    self.painter.go(dots[ev[1]], pen=False)
            elif kind == "line":
                a, b = ev[1], ev[2]
                if self.painter.end != dots[a]:
                    self.painter.go(dots[a], pen=False)
                self.painter.go(dots[b], pen=True)
            elif kind == "group":
                if self.pic.group_names and not self.game.done:
                    self.message = MSG["group"].format(name=self.pic.group_names[ev[1]])
                    self.app.sounds.play("complete", 0.6)
            elif kind in ("wrong", "miss"):
                self.app.sounds.play("deny", 0.45)
                self.hint_until = self.time + 2.0
                self.red_until = self.time + 0.9
                self.marks.append((canvas, self.time))
                self.message = MSG["find"].format(n=self.game.next + 1)

    def _drawn(self):
        """Το R2 τελείωσε τη ζωγραφιά: εμφανίζεται ο φορτιστής και πηγαίνει να φορτίσει."""
        self.drawn_time = self.time
        self.message = MSG["done"].format(title=self.pic.title)
        self.app.progress.mark(GAME_ID, self.index + 1)
        self.app.sounds.play("pick", 0.6)
        self.painter.wait(WAIT_BEFORE_HOME)
        self.painter.go(self.home, pen=False, faster=HOME_FASTER)

    def _charge(self):
        self.charge_time = self.time
        self.app.sounds.play("charge", 0.7)

    # -------------------------------------------------------------- input
    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots_xy):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 14 ** 2:
                return i
        return None

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            for b in self.buttons:
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed_button = b
                    return
            dot = self.dot_at(e.pos)
            if dot is not None:
                self.app.sounds.play("swoosh", 0.7)
                self.load(dot)
                return
            if BOARD.collidepoint(e.pos):
                if not self.game.done:
                    self.click(e.pos)
                elif self.can_go_next:
                    self.next_picture()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.to_menu()
            elif e.key == pygame.K_n:
                self.next_picture()
            elif e.key == pygame.K_r:
                self.restart()
            elif e.key == pygame.K_m:
                self.app.sounds.toggle()

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        for ev in self.painter.update(self.time):
            if ev[0] == "drive":
                self.app.sounds.play("motor", 0.35)
            elif ev[0] == "arrive" and self.drawn_time is not None and not self.painter.busy \
                    and self.charge_time is None:
                self._charge()
        if self.game.done and self.drawn_time is None and not self.painter.busy:
            self._drawn()
        if self.charge_time is not None:
            if not self.celebrated and self.time >= self.charge_time + CELEBRATE_AFTER:
                self.celebrated = True
                self.app.sounds.play("win", 0.9)
                self.confetti.burst(WIDTH)
                self.banner.show(self.time)
            if self.time >= self.charge_time + NEXT_HINT_AFTER:
                self.message = MSG["next"]
        self.btn_next.pulse = self.drawn_time is not None
        for b in self.buttons:
            b.hover = b.contains(self.mouse)
        self.marks = [(p, t) for p, t in self.marks if self.time - t < 0.6]
        self.confetti.update(dt, self.time, HEIGHT)
        self._update_cursor()

    def _update_cursor(self):
        pos = self.mouse
        if any(b.enabled and b.contains(pos) for b in self.buttons) or self.dot_at(pos) is not None:
            cursor = pygame.SYSTEM_CURSOR_HAND
        elif BOARD.collidepoint(pos) and not self.game.done:
            cursor = pygame.SYSTEM_CURSOR_CROSSHAIR
        elif BOARD.collidepoint(pos) and self.can_go_next:
            cursor = pygame.SYSTEM_CURSOR_HAND
        else:
            cursor = pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # --------------------------------------------------------------- draw
    def _to_screen(self, p):
        return (BOARD.x + p[0], BOARD.y + p[1])

    def _draw_lines(self, screen):
        ink = self.ink
        for a, b in self.painter.ink:
            pictures.lines(screen, ink, [self._to_screen(a), self._to_screen(b)], 5)
        _, _, tip = self.painter.state(self.time)
        if tip is not None:
            pictures.lines(screen, ink, [self._to_screen(self.painter.anim["a"]), self._to_screen(tip)], 5)

    def _draw_done_dots(self, screen):
        """Οι τελείες που πατήθηκαν: μπαίνουν κάτω από το R2."""
        light = self.pic.dark
        for i in range(min(self.game.next, len(self.game.dots))):
            ui.circle(screen, self.ink, self._to_screen(self.game.dots[i]), 5)
            ui.text(screen, str(i + 1), self._to_screen(self.labels[i]), 15,
                    (150, 160, 190) if light else (170, 170, 180))

    def _draw_open_dots(self, screen):
        """Οι τελείες που μένουν: μπαίνουν πάνω από το R2, για να φαίνεται πάντα ο επόμενος αριθμός."""
        light = self.pic.dark
        nxt = self.game.next
        for i in range(nxt, len(self.game.dots)):
            sx, sy = self._to_screen(self.game.dots[i])
            lx, ly = self._to_screen(self.labels[i])
            if i == nxt:
                pulse = 0.5 + 0.5 * math.sin(self.time * 5)
                ring = 13 + 4 * pulse
                if self.time < self.hint_until:
                    ring = 20 + 12 * abs(math.sin(self.time * 8))
                ui.circle(screen, (255, 160, 40, 90), (sx, sy), ring)
                ui.circle(screen, (255, 140, 30), (sx, sy), 9, (180, 80, 10))
                ui.text(screen, str(i + 1), (lx, ly), 22, (255, 200, 90) if light else (220, 100, 20))
            else:
                ui.circle(screen, (255, 244, 200) if light else (60, 60, 80), (sx, sy), 6)
                ui.text(screen, str(i + 1), (lx, ly), 17, (220, 230, 255) if light else (70, 70, 90))

    def _draw_marks(self, screen):
        for (x, y), t in self.marks:
            sx, sy = self._to_screen((x, y))
            a = int(255 * (1 - (self.time - t) / 0.6))
            s = 8
            pygame.draw.line(screen, (230, 60, 60), (sx - s, sy - s), (sx + s, sy + s), 3)
            pygame.draw.line(screen, (230, 60, 60), (sx - s, sy + s), (sx + s, sy - s), 3)
            ui.circle(screen, (230, 60, 60, max(0, a // 3)), (sx, sy), 14)

    def _draw_final(self, screen):
        t = self.time - self.drawn_time - REVEAL_AFTER
        self.final_surf.blit(self.backdrop, (0, 0))
        self.pic.final(self.final_surf, max(0.0, t))
        self.final_surf.set_alpha(int(255 * max(0.0, min(1.0, t / FADE_TIME))))
        screen.blit(self.final_surf, BOARD)

    def _draw_charger(self, screen):
        size = CHARGER_SIZE * pop((self.time - self.drawn_time) / 0.35)
        if size < 12:
            return
        rect = pygame.Rect(0, 0, round(size), round(size))
        rect.center = self._to_screen(self.home)
        r2art.charger(screen, rect, self.time, self.charge_time is not None)

    def _led(self):
        if self.charge_time is not None:
            return r2art.LED_GREEN
        if self.time < self.red_until:
            return r2art.LED_RED
        return r2art.LED_BLUE

    def _draw_r2(self, screen):
        pos, angle, _ = self.painter.state(self.time)
        center = self._to_screen(pos)
        if self.charge_time is not None:
            r2art.charge_rings(screen, center, self.time, R2_SIZE)
        r2art.draw_robot(screen, center, R2_SIZE, angle, self._led())

    def _draw_top(self, screen):
        screen.blit(self.top_bar, (0, 0))
        pygame.draw.line(screen, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)
        done = self.app.progress.completed(GAME_ID)
        for i, (x, y) in enumerate(self.dots_xy):
            current = i == self.index
            r = 15 if current else 12
            if current:
                ui.circle(screen, (62, 132, 222), (x, y), r + 3)
                ui.circle(screen, (255, 255, 255), (x, y), r + 1)
            fill = (250, 200, 60) if (i + 1) in done else ((62, 132, 222) if current else (226, 230, 238))
            ui.circle(screen, fill, (x, y), r, ui.shade(fill, 0.7))
            fg = (110, 118, 132) if fill == (226, 230, 238) else (255, 255, 255)
            ui.text(screen, str(i + 1), (x, y), 16 if current else 14, fg)
        ui.text(screen, self.message, (CENTER_X, 69), 21, (44, 54, 76))
        for b in self.buttons:
            b.draw(screen, self.time)

    def draw(self, screen):
        screen.blit(self.room, (0, 0))
        screen.blit(self.paper, BOARD)
        screen.set_clip(BOARD)
        revealed = self.drawn_time is not None and self.time >= self.drawn_time + REVEAL_AFTER
        fade_done = revealed and self.time >= self.drawn_time + REVEAL_AFTER + FADE_TIME
        if not fade_done:
            self._draw_lines(screen)
            self._draw_done_dots(screen)
        if revealed:
            self._draw_final(screen)
        if self.drawn_time is not None:
            self._draw_charger(screen)
        self._draw_r2(screen)
        self._draw_open_dots(screen)
        self._draw_marks(screen)
        screen.set_clip(None)
        self._draw_top(screen)
        self.confetti.draw(screen)
        self.banner.draw(screen, self.time, (BOARD.centerx, BOARD.centery))
