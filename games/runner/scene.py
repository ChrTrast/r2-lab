"""Η οθόνη του τρεξίματος, κοινή για τους Αριθμούς, τις Λέξεις και τις Πράξεις.

Η πίστα ξεκινά με κλικ σε μία από τις τρεις ταχύτητες της κάρτας στην αρχή (μετά από χτύπημα
ξαναξεκινά μόνη της). Το R2 τρέχει μόνο του. Κλικ, Space ή ↑ = άλμα (κρατώντας πατημένο πηδάει ξανά
και ξανά).
Η ταχύτητα (Αργά / Κανονικά / Γρήγορα) είναι σαν αργή κίνηση: όλα (τρέξιμο, άλμα, πτώση) γίνονται
πιο αργά μαζί, οπότε η διαδρομή του R2 είναι ίδια και οι πίστες βγαίνουν σε κάθε ταχύτητα.
Σε κάθε επιλογή υπάρχουν δύο φούσκες: ψηλά (θέλει άλμα) και χαμηλά. Αν χτυπήσει σε εμπόδιο
ή πάρει τη λάθος φούσκα, η πίστα ξεκινά από την αρχή (και μετράει μια προσπάθεια ακόμα).
Στο τέλος, κλικ πάνω στο «Μπράβο» πάει στην επόμενη πίστα, όπως και το κουμπί «Επόμενο».

Το κάθε παιχνίδι δίνει τις πίστες του ως λίστα από dict με:
    rows, speed, fast (προαιρετικό): η διαδρομή (δες logic.py και chunks.py)
    lesson: το «μάθημα», με
        goal, done_text              τι πρέπει να κάνει / τι λέει η πινακίδα στο τέλος
        pairs(rng)                   (σωστό, λάθος) για κάθε επιλογή, νέα σε κάθε προσπάθεια
        wrong_text(i, label)         δύο γραμμές όταν πάρει λάθος
        draw_panel(surf, center, got, time, since)   το πάνελ κάτω (since: πόσο πριν πήρε το τελευταίο σωστό)
        sound_after(got) (προαιρετικό)  ήχος μετά από σωστή επιλογή, π.χ. όταν τελειώνει μια λέξη
        item = "door" (προαιρετικό)     πόρτες αντί για φούσκες (Πράξεις)
"""
import math
import random

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from . import art, logic
from .logic import HIT, TILE

TOP_H = 92
PANEL_Y = (logic.GROUND + HEIGHT) // 2 + 2
R2_SIZE = 84
SCREEN_X = 300               # πού τρέχει το R2 στην οθόνη
CHARGER = 2 * TILE           # ο φορτιστής είναι τόσο μετά από τη γραμμή του τέρματος
JUMP_KEYS = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
RESTART_PAUSE = 0.7          # μετά από χτύπημα, πόσο περιμένει στην αφετηρία πριν ξεκινήσει
CRASH_TIME = 1.0
WRONG_TIME = 3.0
CELEBRATE_AFTER = 0.8
SPEEDS = [(0.6, "Αργά"), (0.8, "Κανονικά"), (1.0, "Γρήγορα")]   # πόσο γρήγορα κυλά ο χρόνος του παιχνιδιού
SPEED_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
BANNER_POS = (WIDTH // 2, 330)   # το «Μπράβο»: κλικ πάνω του = επόμενη πίστα (όπως το «Επόμενο»)
INTRO_CARD = pygame.Rect(WIDTH // 2 - 450, 340 - 173, 900, 346)     # η κάρτα στην αρχή της πίστας
SPEED_RECTS = [pygame.Rect(INTRO_CARD.centerx - 277 + i * 192, INTRO_CARD.y + 162, 170, 112) for i in range(3)]

TIPS = [
    "Πήδα πάνω από τα αγκάθια και τα κουτιά!",
    "Νέο: τραμπολίνο! Σε πετάει ψηλά μόνο του.",
    "Νέο: δαχτυλίδι! Μέσα στον αέρα, πάτα ξανά.",
    "Νέο: μπλε πύλη! Το R2 τρέχει ανάποδα, στο ταβάνι.",
    "Νέο: πύραυλος! Κράτα πατημένο για να ανεβαίνει.",
    "Όλα μαζί, και πιο γρήγορα!",
]
INK = (44, 54, 76)


class RunnerScene(Scene):
    def __init__(self, app, game_id, levels, index=0):
        super().__init__(app)
        self.game_id = game_id
        self.levels = levels
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.mouse_held = False
        self.key_held = False
        self.hold_block = False      # το πάτημα που ξεκίνησε την πίστα δεν μετράει για άλμα
        self.press = False
        self.rng = random.Random()
        self.confetti = fx.Confetti()
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 215))
        n = len(levels)
        self.dots_xy = [(WIDTH // 2 - (n - 1) * 17 + i * 34, 24) for i in range(n)]
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((116, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        # η ταχύτητα κρατιέται όσο είναι ανοιχτό το πρόγραμμα, κοινή για τα τρία παιχνίδια τρεξίματος
        self.speed_i = getattr(app, "runner_speed", 0)
        self.btn_speed = B((996, 8, 86, 76), SPEEDS[self.speed_i][1],
                           lambda s, c, z, col: art.speed_icon(s, (c[0], c[1] + 2), z * 0.95, self.speed_i, self.time),
                           (96, 184, 150), self.cycle_speed)
        self.buttons = [self.btn_again, self.btn_next, self.btn_speed, self.btn_sound, self.btn_menu]
        self.speed_rects = SPEED_RECTS
        self.load(index)

    # ------------------------------------------------------------- setup
    def load(self, index):
        self.index = index % len(self.levels)
        lv = self.levels[self.index]
        self.track = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
        self.lesson = lv["lesson"]
        self.doors = [(self._door_rect(c["x"], c["ya"]), self._door_rect(c["x"], c["yb"]))
                      for c in self.track.choices] if getattr(self.lesson, "item", "") == "door" else None
        self.theme = art.THEMES[self.index % len(art.THEMES)]
        self.accent = self.theme["sky"][0]
        self.attempt = 0
        last = self.index == len(self.levels) - 1
        # Το «Μπράβο» μένει στην οθόνη ώσπου το παιδί να το πατήσει (ή το «Επόμενο»).
        self.banner = fx.Banner("Μπράβο!", "Τελείωσες όλες τις πίστες!" if last else self.lesson.done_text,
                                stay=math.inf)
        self.confetti.clear()
        self.new_attempt(wait=True)

    def _door_rect(self, x, y, w=92, h=100):
        """Η πόρτα γύρω από το (x, y), χωρίς να μπαίνει μέσα σε κουτιά ή στο πάτωμα (σε συντεταγμένες κόσμου)."""
        lo, hi = logic.TOP, logic.GROUND
        for b in self.track.blocks:
            if b[0] < x + w / 2 and b[0] + b[2] > x - w / 2:
                if b[1] + b[3] <= y:
                    lo = max(lo, b[1] + b[3])
                elif b[1] >= y:
                    hi = min(hi, b[1])
        h = min(h, hi - lo - 6)
        top = max(lo + 3, min(y - h / 2, hi - 3 - h))
        return pygame.Rect(round(x - w / 2), round(top), w, round(h))

    def new_attempt(self, wait=False):
        """Από την αρχή της πίστας. wait: περιμένει πάτημα (πρώτη φορά), αλλιώς ξεκινά μόνο του."""
        self.attempt += 1
        self.runner = logic.Runner(self.track)
        self.cam_x = self.runner.x - SCREEN_X
        self.state = "ready"
        self.state_at = self.time
        self.wait_press = wait
        self.items = []
        for right, wrong in self.lesson.pairs(self.rng):
            up = self.rng.random() < 0.5
            self.items.append({"A": right if up else wrong, "B": wrong if up else right,
                               "right": "A" if up else "B", "picked": None})
        self.got = 0
        self.got_at = -9.0
        self.pops = []
        self.wrong = None
        self.wrong_index = None
        self.crash_pos = None
        self.tilt = 0.0
        self.acc = 0.0
        self.press = False
        self.finished_at = None
        self.charging_at = None
        self.celebrated = False
        self.banner.hide()

    # ------------------------------------------------------------ actions
    def restart(self):
        if self.finished_at is not None:
            self.load(self.index)
        else:
            self.new_attempt(wait=False)

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

    def _start(self):
        self.state = "run"
        self.state_at = self.time
        self.acc = 0.0

    def _press(self):
        if self.state == "ready":
            # στην πρώτη προσπάθεια ξεκινά μόνο με κλικ σε ταχύτητα (δες handle_event)
            if not self.wait_press and self.time - self.state_at > 0.15:
                self._start()
                self.hold_block = True
        elif self.state == "run":
            self.press = True
        elif self.state == "wrong" and self.time - self.state_at > 1.4:
            self.new_attempt(wait=False)
            self.hold_block = True

    # -------------------------------------------------------------- input
    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots_xy):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 15 ** 2:
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
            if self.banner.contains(e.pos, self.time, BANNER_POS):
                self.next_level()
                return
            if self.state == "ready" and self.wait_press:
                for i, r in enumerate(self.speed_rects):
                    if r.collidepoint(e.pos):
                        self.app.sounds.play("select", 0.6)
                        self.set_speed(i)
                        self._start()
                        return
            dot = self.dot_at(e.pos)
            if dot is not None:
                self.app.sounds.play("swoosh", 0.7)
                self.load(dot)
            elif e.pos[1] > TOP_H:
                self.mouse_held = True
                self._press()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_held = False
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.KEYDOWN:
            if e.key in JUMP_KEYS:
                if not self.key_held:
                    self.key_held = True
                    self._press()
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
        elif e.type == pygame.KEYUP and e.key in JUMP_KEYS:
            self.key_held = False

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        held = self.mouse_held or self.key_held
        if not held:
            self.hold_block = False
        if self.state == "ready" and not self.wait_press and self.time - self.state_at >= RESTART_PAUSE:
            self._start()
        if self.state == "run":
            self.acc = min(self.acc + dt * SPEEDS[self.speed_i][0], 0.1)
            while self.acc >= logic.STEP and self.state == "run":
                self.acc -= logic.STEP
                events = self.runner.step(held and not self.hold_block, self.press)
                self.press = False
                for ev in events:
                    self._event(ev)
            if self.state == "run":
                self.cam_x = self.runner.x - SCREEN_X
        elif self.state == "crash" and self.time - self.state_at >= CRASH_TIME:
            self.new_attempt(wait=False)
        elif self.state == "wrong" and self.time - self.state_at >= WRONG_TIME:
            self.new_attempt(wait=False)
        elif self.state == "finish":
            self._drive(dt)
        self._update_tilt(dt)
        if self.charging_at is not None and not self.celebrated and self.time >= self.charging_at + CELEBRATE_AFTER:
            self.celebrated = True
            self.app.sounds.play("win", 0.9)
            self.confetti.burst(WIDTH)
            self.banner.show(self.time)
        self.pops = [(p, t) for p, t in self.pops if self.time - t < 0.6]
        self.btn_next.pulse = self.finished_at is not None
        for b in self.buttons:
            b.hover = b.contains(self.mouse)
        self.confetti.update(dt, self.time, HEIGHT)
        self._update_cursor()

    def _event(self, ev):
        kind = ev[0]
        sounds = self.app.sounds
        if kind == "jump":
            sounds.play("hop", 0.45)
        elif kind == "pad":
            sounds.play("boing", 0.7)
        elif kind == "ring":
            sounds.play("select", 0.6)
        elif kind == "portal":
            sounds.play("swoosh", 0.6)
        elif kind == "pick":
            self._pick(ev[1], ev[2])
        elif kind == "crash":
            self.state = "crash"
            self.state_at = self.time
            self.crash_pos = self.runner.center()
            sounds.play("bump", 0.8)
        elif kind == "finish":
            self.state = "finish"
            self.state_at = self.time
            self.finished_at = self.time
            self.runner.mode = "run"
            self.runner.g = 1
            self.app.progress.mark(self.game_id, self.index + 1)

    def _pick(self, i, side):
        item = self.items[i]
        item["picked"] = side
        ch = self.track.choices[i]
        if side == item["right"]:
            self.got += 1
            self.got_at = self.time
            self.pops.append(((ch["x"], ch["ya"] if side == "A" else ch["yb"]), self.time))
            self.app.sounds.play(f"note{min(self.got - 1, 7)}", 0.8)
            extra = getattr(self.lesson, "sound_after", None)
            name = extra(self.got) if extra else None
            if name:
                self.app.sounds.play(name, 0.7)
        else:
            self.state = "wrong"
            self.state_at = self.time
            self.runner.dead = True
            self.wrong_index = i
            self.wrong = self.lesson.wrong_text(i, item[side])
            self.app.sounds.play("deny", 0.8)

    def _drive(self, dt):
        """Μετά το τέρμα: το R2 προσγειώνεται, πάει ως τον φορτιστή και σταματά."""
        r = self.runner
        stop = self.track.finish_x + CHARGER + 10 - HIT
        left = stop - r.x
        if left > 0:
            r.x += min(left, max(70.0, self.track.speed * min(1.0, left / 120)) * dt)
            r.distance += self.track.speed * min(1.0, left / 120) * dt
        r.vy = min(r.vy + logic.GRAVITY * dt, logic.MAX_FALL)
        r.y = min(r.y + r.vy * dt, logic.GROUND - HIT)
        if r.y >= logic.GROUND - HIT:
            r.vy = 0.0
        if left <= 0.5 and r.y >= logic.GROUND - HIT and self.charging_at is None:
            self.charging_at = self.time
            self.app.sounds.play("charge", 0.7)

    def _update_tilt(self, dt):
        r = self.runner
        if r.mode == "rocket":
            target = max(-26.0, min(26.0, -r.vy * 0.045))
        elif r.grounded or self.state not in ("run", "finish"):
            target = 0.0
        else:
            target = max(-22.0, min(22.0, -r.vy * r.g * 0.02))
        self.tilt += (target - self.tilt) * min(1.0, dt * 14)

    def _update_cursor(self):
        pos = self.mouse
        hand = (any(b.enabled and b.contains(pos) for b in self.buttons) or self.dot_at(pos) is not None
                or self.banner.contains(pos, self.time, BANNER_POS)
                or (self.state == "ready" and self.wait_press and any(r.collidepoint(pos) for r in self.speed_rects)))
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # --------------------------------------------------------------- draw
    def led(self):
        if self.charging_at is not None:
            return art.LED_GREEN
        if self.state in ("crash", "wrong"):
            return art.LED_RED
        return art.LED_BLUE

    def draw(self, screen):
        cam = self.cam_x
        t = self.track
        th = self.theme
        art.background(screen, th, cam, self.time, (0, 0, WIDTH, HEIGHT))
        art.ground(screen, th, cam, logic.GROUND, HEIGHT, WIDTH)
        x0, x1 = cam - 3 * TILE, cam + WIDTH + 3 * TILE
        ui.text(screen, f"Προσπάθεια {self.attempt}", (t.start_x + 330 - cam, 300), 44, (255, 255, 255),
                shadow=ui.shade(th["sky"][0], 0.7))
        for b in t.blocks:
            if b[0] < x1 and b[0] + b[2] > x0:
                rect = pygame.Rect(round(b[0] - cam), round(b[1]), b[2], b[3])
                if b[1] <= logic.TOP:
                    rect.top, rect.h = TOP_H - 8, rect.bottom - (TOP_H - 8)
                art.block(screen, rect, th)
        for s in t.spikes:
            if x0 < s["x"] < x1:
                art.spike(screen, s["x"] - cam, s["y"], th, down=s["down"])
        for p in t.pads:
            if x0 < p["x"] < x1:
                art.pad(screen, p["x"] - cam, p["y"], self.time)
        for i, (rx, ry) in enumerate(t.rings):
            if x0 < rx < x1:
                art.ring(screen, (rx - cam, ry), self.time, used=("ring", i) in self.runner.used)
        for p in t.portals:
            if x0 < p["x"] < x1:
                if p["kind"] == "speed":
                    art.speed(screen, (p["x"] - cam, p["y"]), 2, self.time)
                else:
                    art.portal(screen, (p["x"] - cam, p["y"]), p["kind"], self.time)
        fx_ = t.finish_x + CHARGER
        if x0 < fx_ < x1:
            art.finish(screen, fx_ - cam, logic.GROUND, self.time, self.charging_at is not None)
        self._draw_items(screen, cam)
        self._draw_r2(screen, cam)
        for (px, py), at in self.pops:
            art.pop(screen, (px - cam, py), self.time - at)
        if self.state == "crash" and self.crash_pos:
            art.crash(screen, (self.crash_pos[0] - cam, self.crash_pos[1]), self.time - self.state_at, R2_SIZE,
                      seed=self.attempt)
        self._draw_top(screen)
        self.lesson.draw_panel(screen, (WIDTH // 2, PANEL_Y), self.got, self.time, self.time - self.got_at)
        if self.state == "ready" and self.wait_press:
            self._draw_intro(screen)
        elif self.state == "wrong" and self.wrong:
            self._draw_wrong(screen)
        self.confetti.draw(screen)
        self.banner.draw(screen, self.time, BANNER_POS)

    def _draw_items(self, screen, cam):
        for i, ch in enumerate(self.track.choices):
            x = ch["x"] - cam
            if not -80 < x < WIDTH + 80:
                continue
            it = self.items[i]
            for k, (side, y) in enumerate((("A", ch["ya"]), ("B", ch["yb"]))):
                if it["picked"] is None:
                    style = "normal"
                elif self.wrong_index == i:
                    style = "wrong" if side == it["picked"] else "right"
                elif side == it["picked"]:
                    continue                      # την έπιασε: έσκασε
                else:
                    style = "faded"
                if self.doors:
                    art.door(screen, self.doors[i][k].move(-round(cam), 0), it[side], self.time, style)
                else:
                    art.bubble(screen, (x, y), it[side], self.time, style)

    def _draw_r2(self, screen, cam):
        if self.state == "crash":
            return
        r = self.runner
        cx = r.x - cam + HIT / 2
        spin = math.degrees(r.distance / (0.21 * R2_SIZE))
        if r.mode == "rocket":
            c = (cx, r.y + HIT / 2 - R2_SIZE * 0.1)
            art.draw_rocket(screen, c, round(R2_SIZE * 0.86), self.tilt, self.time, self.led())
            return
        if r.g == 1:
            cy = r.y + HIT - R2_SIZE * 0.49
        else:
            cy = r.y + R2_SIZE * 0.49
        if self.charging_at is not None:
            art.charge_rings(screen, (cx, cy), self.time, R2_SIZE)
        art.draw_r2(screen, (cx, cy), R2_SIZE, self.tilt, spin, self.led(), upside_down=r.g == -1)

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
        art.progress(screen, (500, 52, 280, 22), self.runner.progress(), self.accent)
        ui.text(screen, f"Προσπάθεια {self.attempt}", (360, 63), 21, INK)
        for b in self.buttons:
            b.draw(screen, self.time)

    def _card(self, screen, lines, center, width):
        """Λευκή κάρτα με γραμμές (κείμενο, μέγεθος, χρώμα)."""
        h = sum(size + 18 for _, size, _ in lines) + 34
        rect = pygame.Rect(0, 0, width, h)
        rect.center = center
        ui.panel(screen, rect, (255, 255, 255), radius=24, border=(214, 222, 236))
        y = rect.y + 26
        for text, size, color in lines:
            ui.text(screen, text, (rect.centerx, y + size // 2), size, color)
            y += size + 18

    def _draw_intro(self, screen):
        """Η κάρτα στην αρχή της πίστας: τι μαθαίνει, τι νέο εμπόδιο έχει, και οι τρεις ταχύτητες.
        Το κλικ σε μια ταχύτητα ξεκινά την πίστα."""
        card = INTRO_CARD
        ui.panel(screen, card, (255, 255, 255), radius=24, border=(214, 222, 236))
        cx = card.centerx
        ui.text(screen, f"Πίστα {self.index + 1}", (cx, card.y + 40), 38, (236, 118, 30))
        ui.text(screen, self.lesson.goal, (cx, card.y + 90), 26, INK)
        ui.text(screen, TIPS[self.index % len(TIPS)], (cx, card.y + 128), 22, (90, 100, 120))
        for i, ((_, name), r) in enumerate(zip(SPEEDS, self.speed_rects)):
            last = i == self.speed_i                       # αυτή που διάλεξε την προηγούμενη φορά
            hover = r.collidepoint(self.mouse)
            face = r.move(0, -4) if hover else r
            pygame.draw.rect(screen, (196, 206, 222), r.move(0, 4), border_radius=18)
            pygame.draw.rect(screen, (236, 250, 242) if hover else (244, 246, 250), face, border_radius=18)
            border = (60, 170, 120) if hover else ((140, 206, 170) if last else (206, 214, 228))
            pygame.draw.rect(screen, border, face, width=4 if hover else 2, border_radius=18)
            art.speed_icon(screen, (face.centerx, face.y + 44), 64, i, self.time)
            ui.text(screen, name, (face.centerx, face.bottom - 20), 22, (40, 130, 90) if hover else (90, 100, 120))
        blink = (62, 132, 222) if math.sin(self.time * 5) > -0.3 else (130, 170, 230)
        ui.text(screen, "Διάλεξε ταχύτητα για να ξεκινήσεις!", (cx, card.bottom - 34), 24, blink)

    def _draw_wrong(self, screen):
        line1, line2 = self.wrong
        self._card(screen, [(line1, 34, art.RED), (line2, 28, INK)], (WIDTH // 2, 250), 820)
