"""Η οθόνη του Εργοστασίου.

Η πίστα ξεκινά με κλικ σε μία από τις τρεις ταχύτητες της κάρτας (όπως στα παιχνίδια τρεξίματος,
και η ταχύτητα είναι κοινή με αυτά). Τα αντικείμενα έρχονται πάνω στην ταινία και το παιδί:
  - σέρνει με το ποντίκι (ή το δάχτυλο στον διαδραστικό πίνακα) όποιο θέλει μέσα σε ένα κουτί, ή
  - πατά ← ↓ → (ή κλικ πάνω σε ένα κουτί) και φεύγει εκείνο με το κίτρινο βελάκι από πάνω του:
    το πιο κοντινό στο τέλος, ή όποιο διάλεξε με ένα κλικ πάνω του.
Λάθος κουτί: χάνεται μια καρδιά, η ταινία σταματά, το R2 λέει γιατί και το αντικείμενο πάει μόνο
του στο σωστό κουτί. Αν ένα αντικείμενο φτάσει στο τέλος της ταινίας, πέφτει (χάνεται μια καρδιά).
Οι κανόνες (καρδιές, σερί, αστέρια) είναι στο logic.py.
"""
import math
import random

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.runner import art as rart
from games.runner.scene import SPEED_KEYS, SPEEDS
from . import art, logic
from .catalog import HW, ITEMS, OTHER, SW, lost_text, wrong_text

TOP_H = art.TOP_H
LAYOUT = {2: ((250, 330), (720, 330)), 3: ((170, 270), (495, 280), (830, 270))}   # (κέντρο, πλάτος) των κουτιών
ZONE_TOP = art.BELT_Y + 60         # κάτω από εδώ, η στήλη κάθε κουτιού δέχεται αντικείμενα
ZONE_RIGHT = 960                   # δεξιά από εδώ (κόκκινο κουτί, R2) δεν είναι κανένα κουτί
KEY_BOX = {pygame.K_LEFT: HW, pygame.K_DOWN: SW, pygame.K_RIGHT: OTHER}
FLY_TIME = 0.42                    # πόσο κρατά το πέταγμα στο κουτί
SINK_TIME = 0.22                   # και το «βούτηγμα» μέσα του
WRONG_FREEZE = 3.4                 # πόσο σταματά η ταινία μετά από λάθος κουτί
SKIP_AFTER = 1.2                   # μετά από τόσο, ένα κλικ ή πλήκτρο ξεκινά πάλι την ταινία
LOST_MSG = 2.4                     # πόσο μένει το μήνυμα όταν κάτι πέσει
OVER_AFTER = 1.4                   # πότε βγαίνει η κάρτα «Τέλος βάρδιας» μετά την τελευταία καρδιά
CELEBRATE_AFTER = 0.7              # πότε αρχίζει η γιορτή, αφού μπει και το τελευταίο αντικείμενο
DRAG_MIN = 12                      # pixels: πιο λίγο από αυτό είναι κλικ (διαλέγει), όχι σύρσιμο
WARN_DIST = 200                    # τόσο πριν από το τέλος της ταινίας αρχίζει η προειδοποίηση
INTRO_CARD = pygame.Rect(WIDTH // 2 - 460, 140, 920, 430)
SPEED_RECTS = [pygame.Rect(INTRO_CARD.centerx - 277 + i * 192, INTRO_CARD.y + 66, 170, 112) for i in range(3)]
OVER_CARD = pygame.Rect(WIDTH // 2 - 400, 130, 800, 440)
BANNER_CENTER = (560, 330)
GO_RECT = pygame.Rect(860, 270, 170, 120)
INK = art.TEXT


class Flight:
    """Ένα αντικείμενο που πετάει σε τόξο από p0 σε p1 (ξεκινά τη στιγμή start)."""

    def __init__(self, key, p0, p1, start, dur=FLY_TIME, arc=110, s0=1.0, s1=0.85, spin=0.0, land=None):
        self.key, self.p0, self.p1 = key, p0, p1
        self.start, self.dur, self.arc = start, dur, arc
        self.s0, self.s1, self.spin = s0, s1, spin
        self.land = land

    def at(self, time):
        k = max(0.0, min(1.0, (time - self.start) / self.dur))
        x = self.p0[0] + (self.p1[0] - self.p0[0]) * k
        y = self.p0[1] + (self.p1[1] - self.p0[1]) * k - self.arc * math.sin(math.pi * k)
        return (x, y), self.s0 + (self.s1 - self.s0) * k, self.spin * k

    def done(self, time):
        return time >= self.start + self.dur


class FactoryScene(Scene):
    def __init__(self, app, game_id, levels, index=0):
        super().__init__(app)
        self.game_id = game_id
        self.levels = levels
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.rng = random.Random()
        self.confetti = fx.Confetti()
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 225))
        n = len(levels)
        self.dots_xy = [(WIDTH // 2 - (n - 1) * 17 + i * 34, 24) for i in range(n)]
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((116, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        home = lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84))   # noqa: E731
        self.btn_menu = B((1184, 8, 86, 76), "Μενού", home, (224, 84, 84), self.to_menu)
        # η ταχύτητα κρατιέται όσο είναι ανοιχτό το πρόγραμμα, κοινή με τα παιχνίδια τρεξίματος
        self.speed_i = getattr(app, "runner_speed", 0)
        self.btn_speed = B((996, 8, 86, 76), SPEEDS[self.speed_i][1],
                           lambda s, c, z, col: rart.speed_icon(s, (c[0], c[1] + 2), z * 0.95, self.speed_i, self.time),
                           (96, 184, 150), self.cycle_speed)
        self.buttons = [self.btn_again, self.btn_next, self.btn_speed, self.btn_sound, self.btn_menu]
        self.btn_go = B(GO_RECT, "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level, label_size=22)
        self.btn_go.pulse = True
        self.btn_retry = B((OVER_CARD.centerx - 200, OVER_CARD.y + 310, 180, 100), "Ξανά", ui.icon_again,
                           (238, 146, 46), self.restart, label_size=20)
        self.btn_retry.pulse = True
        self.btn_quit = B((OVER_CARD.centerx + 20, OVER_CARD.y + 310, 180, 100), "Μενού", home, (224, 84, 84),
                          self.to_menu, label_size=20)
        self.speed_rects = SPEED_RECTS
        self.load(index)

    # ------------------------------------------------------------- setup
    def load(self, index):
        self.index = index % len(self.levels)
        self.level = self.levels[self.index]
        kinds = self.level["boxes"]
        self.boxes = [art.Box(k, cx, w) for k, (cx, w) in zip(kinds, LAYOUT[len(kinds)])]
        self.box_of = {b.kind: b for b in self.boxes}
        last = self.index == len(self.levels) - 1
        self.banner = fx.Banner("Μπράβο!", "Τελείωσες όλες τις πίστες!" if last else "", stay=math.inf,
                                icon=self._banner_stars)
        self.new_shift(wait=True)

    def new_shift(self, wait=False):
        """Από την αρχή της πίστας. wait: με την κάρτα και τις ταχύτητες, αλλιώς ξεκινά αμέσως."""
        self.shift = logic.Shift(self.level, self.rng)
        self.state = "ready" if wait else "run"
        self.flights = []
        self.falls = []
        self.sinks = []
        self.pops = []
        self.poofs = []
        self.held = None
        self.chosen = None
        self.peek = {HW: [], SW: [], OTHER: []}   # τι μπήκε σε κάθε κουτί (τα τελευταία φαίνονται)
        self.pile = []                            # ό,τι έπεσε στο κόκκινο κουτί
        self.flash = {}                           # κουτί -> (χρώμα, ως πότε λάμπει)
        self.bumped = {}                          # κουτί -> πότε δέχτηκε αντικείμενο (αναπηδά)
        self.shaken = {}                          # κουτί -> πότε μπήκε κάτι λάθος (κουνιέται)
        self.freeze_until = None
        self.freeze_at = 0.0
        self.message = None                       # (γραμμή 1, γραμμή 2, ως πότε)
        self.led = None                           # (χρώμα, ως πότε)
        self.hop = (0.0, 0.0, 0.3)                # (πότε, πόσο ψηλά, πόσο κρατά)
        self.super_at = None
        self.heart_at = None
        self.end_at = None
        self.celebrated = False
        self.confetti.clear()
        self.banner.hide()

    def _banner_stars(self, img, c):
        """Στη θέση των αστεριών του «Μπράβο»: τόσα χρυσά αστέρια όσες καρδιές έμειναν."""
        n = max(1, self.shift.hearts) if hasattr(self, "shift") else 3
        for i, dx in enumerate((-70, 0, 70)):
            on = i < n
            ui.star(img, (c[0] + dx, c[1] - (8 if i == 1 else 0)), 24 if i == 1 else 19,
                    (252, 204, 60) if on else (220, 224, 232), (150, 100, 20) if on else (170, 176, 190))

    # ------------------------------------------------------------ actions
    def restart(self):
        self.new_shift(wait=self.state == "ready")

    def next_level(self):
        self.app.sounds.play("swoosh", 0.7)
        self.load(self.index + 1)

    def to_menu(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def set_speed(self, i):
        self.speed_i = i % len(SPEEDS)
        self.app.runner_speed = self.speed_i
        self.btn_speed.label = SPEEDS[self.speed_i][1]

    def cycle_speed(self):
        self.set_speed(self.speed_i + 1)

    def start(self):
        self.state = "run"
        self.app.sounds.play("swoosh", 0.5)

    # ------------------------------------------------------------ helpers
    @property
    def frozen(self):
        return self.freeze_until is not None

    def playing(self):
        """Το παιδί μπορεί να πιάσει αντικείμενα (η ταινία κυλά)."""
        return self.state == "run" and not self.frozen and not self.shift.finished

    def target(self):
        """Το αντικείμενο που στέλνουν τα βελάκια: όποιο διάλεξε το παιδί, αλλιώς το πιο κοντινό στο τέλος."""
        return (self.shift.find(self.chosen) if self.chosen is not None else None) or self.shift.front()

    def thing_at(self, pos):
        for t in sorted(self.shift.things, key=lambda t: -t.x):
            if abs(pos[0] - t.x) <= art.ITEM * 0.5 and abs(pos[1] - art.ITEM_Y) <= art.ITEM * 0.55:
                return t
        return None

    def zone_at(self, pos):
        """Σε ποιο κουτί πέφτει ένα αντικείμενο που αφήνεται στο pos (όλη η στήλη κάτω από την ταινία)."""
        if pos[1] < ZONE_TOP or not 0 <= pos[0] < ZONE_RIGHT:
            return None
        xs = [b.cx for b in self.boxes]
        for i, b in enumerate(self.boxes):
            right = (xs[i] + xs[i + 1]) / 2 if i + 1 < len(xs) else ZONE_RIGHT
            if pos[0] < right:
                return b.kind
        return None

    def warn(self):
        """0..1: πόσο κοντά στο τέλος είναι το πιο μπροστινό αντικείμενο."""
        front = self.shift.front()
        if front is None or self.state != "run":
            return 0.0
        return max(0.0, min(1.0, (front.x - (logic.BELT_END - WARN_DIST)) / WARN_DIST))

    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots_xy):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 15 ** 2:
                return i
        return None

    def active_buttons(self):
        extra = []
        if self.state == "done" and self.celebrated:
            extra = [self.btn_go]
        elif self.state == "over":
            extra = [self.btn_retry, self.btn_quit]
        return self.buttons + extra

    # ------------------------------------------------------------ sorting
    def send(self, kind):
        """Βελάκι ή κλικ σε κουτί: το αντικείμενο με το κίτρινο βελάκι πετάει σε αυτό το κουτί."""
        thing = self.target()
        if thing is None or kind not in self.box_of:
            return
        self.app.sounds.play("swoosh", 0.35)
        self.sort(thing, kind, (thing.x, art.ITEM_Y))

    def sort(self, thing, kind, start_pos, s0=1.0):
        result = self.shift.sort(thing, kind)
        if self.chosen == thing.id:
            self.chosen = None
        box = self.box_of[kind]
        if result["right"]:
            self.flights.append(Flight(thing.key, start_pos, box.mouth(), self.time, s0=s0,
                                       land=lambda: self._land_right(thing.key, kind, result)))
            if self.shift.done:
                self.end_at = self.time + FLY_TIME + CELEBRATE_AFTER
                self.app.progress.mark(self.game_id, self.index + 1)
            return
        # λάθος κουτί: σταματά η ταινία, το R2 εξηγεί, και το αντικείμενο πάει μόνο του στο σωστό
        self.app.sounds.play("deny", 0.8)
        self.freeze_at = self.time
        self.freeze_until = self.time + WRONG_FREEZE
        self.message = (*wrong_text(thing.key, kind), self.freeze_until)
        self.led = (rart.LED_RED, self.freeze_until)
        right = self.box_of.get(thing.kind)
        wrong_mouth = box.mouth()
        wrong_mouth = (wrong_mouth[0], wrong_mouth[1] - 30)
        self.flights.append(Flight(thing.key, start_pos, wrong_mouth, self.time, s0=s0, s1=0.9,
                                   land=lambda: self._land_wrong(kind)))
        if right is not None:
            self.flights.append(Flight(thing.key, wrong_mouth, right.mouth(), self.time + FLY_TIME + 0.45, dur=0.75,
                                       arc=150, s0=0.9, s1=0.85, land=lambda: self._land_fixed(thing.key, right.kind)))
        if self.shift.over:
            self.end_at = self.time + FLY_TIME + 0.45 + 0.75 + OVER_AFTER

    def _receive(self, key, kind):
        """Το αντικείμενο μπαίνει στο κουτί: βουτάει μέσα, το κουτί αναπηδά."""
        box = self.box_of[kind]
        self.sinks.append((key, kind, box.mouth(), self.time))
        self.bumped[kind] = self.time
        peek = self.peek[kind]
        if kind == SW:
            if key in peek:
                peek.remove(key)
            peek.append(key)
        else:
            peek.append(key)
            del peek[:-3]

    def _land_right(self, key, kind, result):
        self._receive(key, kind)
        self.flash[kind] = (art.GREEN_GLOW, self.time + 0.5)
        mouth = self.box_of[kind].mouth()
        self.pops.append((f"+{result['stars']}", (mouth[0], mouth[1] - 50), self.time))
        self.app.sounds.play(f"note{min(max(self.shift.streak, 1) - 1, 7)}", 0.7)
        self.app.sounds.play("place", 0.35)
        if not self.frozen and (self.led is None or self.led[1] < self.time):
            self.led = (rart.LED_GREEN, self.time + 0.6)
        if result["super"]:
            self.super_at = self.time
            self.app.sounds.play("complete", 0.7)
            self.hop = (self.time, 34, 0.5)
            if result["heart_back"]:
                self.heart_at = self.time
        else:
            self.hop = (self.time, 12, 0.3)

    def _land_wrong(self, kind):
        self.shaken[kind] = self.time
        self.flash[kind] = (art.RED_GLOW, self.time + 0.9)

    def _land_fixed(self, key, kind):
        self._receive(key, kind)
        self.flash[kind] = (art.GREEN_GLOW, self.time + 1.0)
        self.app.sounds.play("place", 0.5)

    def _lost(self, thing):
        if self.chosen == thing.id:
            self.chosen = None
        start = (logic.BELT_END + 10, art.ITEM_Y)
        self.falls.append(Flight(thing.key, start, art.lost_mouth(), self.time, dur=0.55, arc=40, s1=0.8, spin=-150,
                                 land=lambda: self._land_lost(thing.key)))
        if not self.frozen:
            self.message = (*lost_text(thing.key), self.time + LOST_MSG)
            self.led = (rart.LED_RED, self.time + 1.5)
        self.app.sounds.play("remove", 0.6)
        if self.shift.over:
            self.end_at = self.time + 0.55 + OVER_AFTER

    def _land_lost(self, key):
        self.pile.append(key)
        del self.pile[:-3]
        self.app.sounds.play("bump", 0.7)

    def _unfreeze(self):
        self.freeze_until = None
        if self.message and not self.shift.finished:
            self.message = None
        if self.led and self.led[0] == rart.LED_RED:
            self.led = None

    # -------------------------------------------------------------- input
    def grab(self, thing, pos):
        self.shift.take(thing)
        self.held = {"thing": thing, "start": pos, "pos": pos, "dx": thing.x - pos[0],
                     "dy": art.ITEM_Y - pos[1], "moved": False}
        self.app.sounds.play("pick", 0.5)

    def release(self, pos):
        h, self.held = self.held, None
        thing = h["thing"]
        if not self.playing():
            return
        if not h["moved"]:
            # ένα κλικ πάνω του: μένει στην ταινία και το διαλέγει για τα βελάκια
            self.shift.put_back(thing)
            self.chosen = thing.id
            self.app.sounds.play("select", 0.4)
            return
        kind = self.zone_at(pos)
        here = (pos[0] + h["dx"], pos[1] + h["dy"])
        if kind is not None:
            self.sort(thing, kind, here, s0=1.12)
        else:
            self.flights.append(Flight(thing.key, here, (thing.x, art.ITEM_Y), self.time, dur=0.3, arc=30,
                                       s0=1.12, s1=1.0, land=lambda: self.shift.put_back(thing)))

    def _skip_freeze(self):
        if self.frozen and self.time - self.freeze_at >= SKIP_AFTER and not self.shift.finished:
            self._unfreeze()
            return True
        return False

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            if self.held:
                self.held["pos"] = e.pos
                sx, sy = self.held["start"]
                if (e.pos[0] - sx) ** 2 + (e.pos[1] - sy) ** 2 > DRAG_MIN ** 2:
                    self.held["moved"] = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            for b in self.active_buttons():
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed_button = b
                    return
            dot = self.dot_at(e.pos)
            if dot is not None:
                self.app.sounds.play("swoosh", 0.7)
                self.load(dot)
                return
            if self.state == "ready":
                for i, r in enumerate(self.speed_rects):
                    if r.collidepoint(e.pos):
                        self.app.sounds.play("select", 0.6)
                        self.set_speed(i)
                        self.start()
                        return
                return
            if self._skip_freeze() or not self.playing() or self.held:
                return
            thing = self.thing_at(e.pos)
            if thing is not None:
                self.grab(thing, e.pos)
            else:
                kind = self.zone_at(e.pos)
                if kind is not None:
                    self.send(kind)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.held:
                self.release(e.pos)
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.KEYDOWN:
            if e.key in KEY_BOX:
                if not self._skip_freeze() and self.playing() and not self.held:
                    self.send(KEY_BOX[e.key])
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                if self.state == "done" and self.celebrated:
                    self.next_level()
                elif self.state == "over":
                    self.restart()
                else:
                    self._skip_freeze()
            elif e.key == pygame.K_ESCAPE:
                self.to_menu()
            elif e.key == pygame.K_n:
                self.next_level()
            elif e.key == pygame.K_r:
                self.restart()
            elif e.key == pygame.K_m:
                self.app.sounds.toggle()
            elif e.key in SPEED_KEYS:
                self.set_speed(SPEED_KEYS[e.key])

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        if self.frozen and self.time >= self.freeze_until and not self.shift.finished:
            self._unfreeze()
        if self.state == "run" and not self.frozen:
            for kind, thing in self.shift.update(dt * SPEEDS[self.speed_i][0]):
                if kind == "lost":
                    self._lost(thing)
        for group in (self.flights, self.falls):
            for f in [f for f in group if f.done(self.time)]:
                group.remove(f)
                if f.land:
                    f.land()
        self.sinks = [s for s in self.sinks if self.time - s[3] < SINK_TIME]
        self.pops = [p for p in self.pops if self.time - p[2] < 0.9]
        self.poofs = [p for p in self.poofs if self.time - p[1] < 0.5]
        if self.message and self.time >= self.message[2] and not self.frozen:
            self.message = None
        if self.state == "run" and self.end_at is not None and self.time >= self.end_at:
            self._finish()
        if self.held and not self.playing():
            self.held = None                      # η βάρδια τελείωσε όσο το κρατούσε
        for b in self.active_buttons():
            b.hover = b.contains(self.mouse)
        self.confetti.update(dt, self.time, HEIGHT)
        self._update_cursor()

    def _finish(self):
        self.end_at = None
        self.freeze_until = None
        if self.shift.done:
            self.state = "done"
            self.message = None
            for th in self.shift.things:              # ό,τι έμεινε στην ταινία εξαφανίζεται με αστεράκια
                self.poofs.append(((th.x, art.ITEM_Y), self.time))
            self.shift.things.clear()
            self.celebrated = True
            self.app.sounds.play("win", 0.9)
            self.confetti.burst(WIDTH)
            self.banner = fx.Banner("Μπράβο!", self.banner_text(), stay=math.inf, icon=self._banner_stars)
            self.banner.show(self.time)
        else:
            self.state = "over"
            self.message = None
            self.app.sounds.play("thud", 0.6)

    def banner_text(self):
        if self.index == len(self.levels) - 1:
            return "Τελείωσες όλες τις πίστες!"
        return f"Τακτοποίησες {self.shift.goal} αντικείμενα!"

    def _update_cursor(self):
        pos = self.mouse
        hand = (any(b.enabled and b.contains(pos) for b in self.active_buttons()) or self.dot_at(pos) is not None
                or (self.state == "ready" and any(r.collidepoint(pos) for r in self.speed_rects))
                or self.held is not None
                or (self.playing() and (self.thing_at(pos) is not None or self.zone_at(pos) is not None)))
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # --------------------------------------------------------------- draw
    def r2_led(self, warn):
        if self.state == "done":
            return rart.LED_GREEN
        if self.state == "over":
            return rart.LED_RED
        if self.led and self.time < self.led[1]:
            return self.led[0]
        if warn > 0.3 and math.sin(self.time * 14) > 0:
            return art.LED_ORANGE
        return rart.LED_BLUE

    def r2_hop(self):
        if self.state == "done":
            return abs(math.sin(self.time * 5)) * 18
        at, amp, dur = self.hop
        k = (self.time - at) / dur
        return amp * math.sin(math.pi * k) if 0 <= k < 1 else 0.0

    def draw(self, screen):
        t = self.time
        warn = self.warn()
        art.background(screen, t)
        art.hatch_back(screen)
        art.belt(screen, self.shift.distance, warn)
        self._draw_belt_items(screen, warn)
        art.hatch_front(screen)
        for f in self.falls:
            pos, scale, angle = f.at(t)
            art.item(screen, f.key, pos, scale, angle)
        art.lost_bin(screen, self.pile, warn)
        art.r2_stand(screen)
        art.r2(screen, self.r2_led(warn), self.r2_hop(), -6 if self.state == "over" else 0,
               rings=self.state == "done", time=t)
        self._draw_boxes(screen)
        for f in self.flights:
            if t < f.start:
                continue                          # περιμένει μέσα στο λάθος κουτί πριν πεταχτεί στο σωστό
            pos, scale, angle = f.at(t)
            art.item(screen, f.key, pos, scale, angle)
        if self.held:
            h = self.held
            p = (h["pos"][0] + h["dx"], h["pos"][1] + h["dy"])
            sh = pygame.Surface((96, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 50), sh.get_rect())
            screen.blit(sh, sh.get_rect(center=(round(p[0]), round(p[1] + 66))))
            art.item(screen, h["thing"].key, p, 1.12, -6)
        self._draw_pops(screen)
        if self.message:
            art.bubble(screen, self.message[0], self.message[1])
        self._draw_top(screen)
        if self.state == "ready":
            self._draw_intro(screen)
        elif self.state == "over":
            self._draw_over(screen)
        self.confetti.draw(screen)
        if self.state == "done":
            self.banner.draw(screen, t, BANNER_CENTER)
            if self.celebrated:
                self.btn_go.draw(screen, t)

    def _draw_belt_items(self, screen, warn):
        target = self.target() if self.playing() or self.state == "ready" else None
        for th in self.shift.things:
            if th is target:
                near = th.x > logic.BELT_END - WARN_DIST
                color = art.RED_GLOW if near else art.YELLOW_GLOW
                art.halo(screen, (th.x, art.ITEM_Y), art.ITEM // 2 + 20, color, 110 + 60 * math.sin(self.time * 6))
            art.item(screen, th.key, (th.x, art.ITEM_Y), shadow_y=art.BELT_Y + 2)
        if target is not None:
            art.marker(screen, target.x, self.time)

    def _box_glow(self, kind):
        if self.held and self.held["moved"] and self.zone_at(self.held["pos"]) == kind:
            return art.YELLOW_GLOW, 170
        f = self.flash.get(kind)
        if f and self.time < f[1]:
            return f[0], 180
        return None, 0

    def _draw_boxes(self, screen):
        t = self.time
        for box in self.boxes:
            k = box.kind
            dx = dy = 0
            age = t - self.shaken.get(k, -9)
            if age < 0.5:
                dx = math.sin(age * 40) * 8 * (1 - age / 0.5)
            age = t - self.bumped.get(k, -9)
            if age < 0.25:
                dy = -8 * math.sin(math.pi * age / 0.25)
            glow, alpha = self._box_glow(k)
            box.draw_lid(screen, dx, dy)
            box.draw_back(screen, self.peek[k], dx, dy)
            sinking = [s for s in self.sinks if s[1] == k]
            if k != SW:
                for key, _, mouth, at in sinking:
                    q = (t - at) / SINK_TIME
                    art.item(screen, key, (mouth[0] + dx, mouth[1] + dy + 50 * q), 0.85 * (1 - 0.4 * q))
            flash = 0.0
            if k == SW and sinking:
                flash = 1 - (t - sinking[-1][3]) / SINK_TIME
            box.draw(screen, glow, alpha, dx, dy, apps=self.peek[SW], flash=max(0.0, flash))
            if k == SW:
                for key, _, mouth, at in sinking:
                    q = (t - at) / SINK_TIME
                    art.item(screen, key, mouth, 0.85 * (1 - 0.7 * q), alpha=int(255 * (1 - q)))

    def _draw_pops(self, screen):
        t = self.time
        for pos, at in self.poofs:
            rart.pop(screen, pos, t - at, (252, 204, 60))
        for text, (x, y), at in self.pops:
            k = (t - at) / 0.9
            a = int(255 * min(1.0, 2 * (1 - k)))
            yy = y - 50 * k
            img = ui.font(32).render(text, True, (60, 170, 90))
            img.set_alpha(a)
            screen.blit(img, img.get_rect(midright=(round(x + 4), round(yy))))
            ui.star(screen, (x + 22, yy), 15, (252, 204, 60, a), (150, 100, 20, a))
        if self.super_at is not None and t - self.super_at < 1.8:
            k = (t - self.super_at) / 1.8
            pop = min(1.0, (t - self.super_at) / 0.2)
            size = round(58 * (0.6 + 0.4 * pop))
            y = 210 - 20 * k
            alpha = int(255 * min(1.0, 4 * (1 - k)))
            for text, sz, col, dy in (("Σούπερ!", size, (246, 120, 40), 0),
                                      (f"{logic.STREAK} στη σειρά: διπλά αστέρια!", round(size * 0.45), INK, 50)):
                img = ui.font(sz).render(text, True, col)
                sh = ui.font(sz).render(text, True, (255, 255, 255))
                for im in (sh, img):
                    im.set_alpha(alpha)
                c = (500, y + dy)
                screen.blit(sh, sh.get_rect(center=(c[0] + 2, c[1] + 2)))
                screen.blit(img, img.get_rect(center=c))
            if self.heart_at is not None and t - self.heart_at < 1.8:
                art.heart(screen, (680, y + 4), 20 * (0.6 + 0.4 * pop))

    def _draw_top(self, screen):
        screen.blit(self.top_bar, (0, 0))
        pygame.draw.line(screen, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)
        done = self.app.progress.completed(self.game_id)
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
        sh = self.shift
        glow = 0.0
        if self.heart_at is not None and self.time - self.heart_at < 1.5:
            glow = 1 - (self.time - self.heart_at) / 1.5
        for i in range(logic.HEARTS):
            back = glow if i == sh.hearts - 1 else 0.0
            art.heart(screen, (262 + i * 42, 52), 17, full=i < sh.hearts, glow=back)
        art.progress(screen, (520, 50, 240, 22), sh.got, sh.goal)
        ui.star(screen, (820, 61), 15, (252, 204, 60))
        ui.text(screen, str(sh.stars), (842, 62), 24, INK, anchor="midleft")
        if sh.streak >= 2:
            big = sh.double
            art.flame(screen, (920, 60), 17 if big else 13)
            ui.text(screen, f"x{sh.streak}", (940, 62), 24 if big else 21, (220, 100, 30), anchor="midleft")
        for b in self.buttons:
            b.draw(screen, self.time)

    def _draw_intro(self, screen):
        """Η κάρτα στην αρχή της πίστας: πάνω οι τρεις ταχύτητες, κάτω με μικρά γράμματα τι κάνεις
        και παραδείγματα για κάθε κουτί."""
        card = INTRO_CARD
        ui.panel(screen, card, (255, 255, 255), radius=24, border=(214, 222, 236))
        cx = card.centerx
        ui.text(screen, f"Πίστα {self.index + 1}", (cx, card.y + 34), 34, (236, 118, 30))
        blink = (62, 132, 222) if math.sin(self.time * 5) > -0.3 else (130, 170, 230)
        ui.text(screen, "Διάλεξε ταχύτητα για να ξεκινήσεις!", (cx, card.y + 206), 22, blink)
        pygame.draw.line(screen, (226, 230, 238), (card.x + 40, card.y + 234), (card.right - 40, card.y + 234), 2)
        art.fit_text(screen, self.level["goal_text"], (cx, card.y + 258), 19, INK, card.w - 40)
        kinds = self.level["boxes"]
        n = len(kinds)
        gw = (card.w - 40 - (n - 1) * 20) // n
        for i, kind in enumerate(kinds):
            box = pygame.Rect(card.x + 20 + i * (gw + 20), card.y + 278, gw, 100)
            pygame.draw.rect(screen, (246, 248, 252), box, border_radius=16)
            pygame.draw.rect(screen, ui.mix(art.BOX_COLORS[kind], (255, 255, 255), 0.5), box, 2, border_radius=16)
            art.label(screen, kind, (box.centerx, box.y + 20), None, key=True, size=16)
            keys = self.level["examples"][kind]
            step = gw / len(keys)
            for j, key in enumerate(keys):
                art.item(screen, key, (box.x + step * (j + 0.5), box.y + 68), 52 / art.ITEM)
        art.fit_text(screen, self.level["tip"], (cx, card.y + 398), 16, (90, 100, 120), card.w - 40)
        for i, ((_, name), r) in enumerate(zip(SPEEDS, self.speed_rects)):
            last = i == self.speed_i
            hover = r.collidepoint(self.mouse)
            face = r.move(0, -4) if hover else r
            pygame.draw.rect(screen, (196, 206, 222), r.move(0, 4), border_radius=18)
            pygame.draw.rect(screen, (236, 250, 242) if hover else (244, 246, 250), face, border_radius=18)
            border = (60, 170, 120) if hover else ((140, 206, 170) if last else (206, 214, 228))
            pygame.draw.rect(screen, border, face, width=4 if hover else 2, border_radius=18)
            rart.speed_icon(screen, (face.centerx, face.y + 44), 64, i, self.time)
            ui.text(screen, name, (face.centerx, face.bottom - 20), 22, (40, 130, 90) if hover else (90, 100, 120))

    def _draw_over(self, screen):
        """«Τέλος βάρδιας»: πόσα έβαλε σωστά, και ποια ήταν λάθος με το σωστό τους κουτί."""
        card = OVER_CARD
        ui.panel(screen, card, (255, 255, 255), radius=24, border=(214, 222, 236))
        cx = card.centerx
        sh = self.shift
        ui.text(screen, "Τέλος βάρδιας!", (cx, card.y + 46), 44, (236, 118, 30))
        ui.text(screen, f"Έβαλες σωστά {sh.got} από τα {sh.goal} αντικείμενα.", (cx, card.y + 100), 26, INK)
        lessons = sh.lessons()
        if lessons:
            ui.text(screen, "Θυμήσου:", (cx, card.y + 146), 22, (90, 100, 120))
            step = 250
            x0 = cx - step * (len(lessons) - 1) / 2
            for i, key in enumerate(lessons):
                x = x0 + i * step
                art.item(screen, key, (x - 30, card.y + 210), 76 / art.ITEM)
                ui.fill_poly(screen, (150, 156, 170), [(x + 14, card.y + 200), (x + 34, card.y + 210),
                                                       (x + 14, card.y + 220)])
                art.label(screen, ITEMS[key].kind, (x + 30, card.y + 262), None, key=False, size=20)
        self.btn_retry.draw(screen, self.time)
        self.btn_quit.draw(screen, self.time)
