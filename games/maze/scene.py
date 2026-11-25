"""Λαβύρινθος: οδήγησε το R2 στον φορτιστή.

Χειριστήριο με 4 κουμπιά στη θέση των βελών του πληκτρολογίου:
↑ μπροστά, ↓ πίσω, ← στρίψε αριστερά, → στρίψε δεξιά. Όταν το παιδί πατά ένα βελάκι,
πατιέται μόνο του και το αντίστοιχο κουμπί, για να συνδέσει το πλήκτρο με την εντολή.

Όσο το παιδί οδηγεί, το πρόγραμμα γράφεται μόνο του με τα μπλοκ του R2 στο Mind+ (core/blocks.py).
Στους πρώτους λαβύρινθους (SIDE_LEVELS) η οθόνη χωρίζεται στα δύο: αριστερά ο λαβύρινθος, δεξιά πάνω
το χειριστήριο και από κάτω το πρόγραμμα. Στο τέλος, το «Εκτέλεση εντολών» (η πράσινη σημαία) γυρίζει
το R2 στην ΑΡΧΗ και εκτελεί όλο το πρόγραμμα, φωτίζοντας το μπλοκ που τρέχει. Κάθε μπλοκ κρατά όσα
δευτερόλεπτα γράφει. Στους μεγάλους λαβύρινθους το πρόγραμμα είναι μια λωρίδα κάτω, με την τελευταία
εντολή, χωρίς σημαία (τα προγράμματα εκεί είναι πολύ μεγάλα για να ξανατρέξουν).
"""
import math

import pygame

from core import blocks, fx, ui
from core.app import HEIGHT, WIDTH, Scene
from . import GAME_ID, LEVEL_COUNT, art, levels, logic

TOP_H = 92
CENTER_X = 653
MOVE_TIME = 0.30          # πόσο κρατά η κίνηση ενός τετραγώνου
TURN_TIME = 0.26          # πόσο κρατά μια στροφή
BUMP_TIME = 0.34          # πόσο κρατά το «χτύπημα» στον τοίχο
MAX_WAITING = 3           # πόσες εντολές περιμένουν τη σειρά τους όσο κινείται το R2
CELEBRATE_AFTER = 0.7     # πότε αρχίζει η γιορτή, αφού φτάσει στον φορτιστή
SIDE_LEVELS = 6           # οι λαβύρινθοι 1-6: πρόγραμμα στο πλάι και «Εκτέλεση εντολών»
PROGRAM_ROWS = 11         # πόσες γραμμές φαίνονται στο πλάι: το R2 starts και 10 εντολές
RUN_PAUSE = 0.6           # το R2 περιμένει λίγο στην ΑΡΧΗ πριν εκτελέσει το πρόγραμμα
FRESH_TIME = 0.8          # πόσο λάμπει το μπλοκ που μόλις γράφτηκε
KEYS = {pygame.K_UP: "forward", pygame.K_DOWN: "back", pygame.K_LEFT: "left", pygame.K_RIGHT: "right"}

MSG = {
    "start": "Οδήγησε το R2 στον φορτιστή!",
    "bump": "Ωχ! Εκεί έχει τοίχο.",
    "done": "Μπράβο! Το R2 φορτίζει!",
    "run": "Το R2 εκτελεί τις εντολές σου!",
}


def _clamp(t):
    return max(0.0, min(1.0, t))


def ease(t):
    t = _clamp(t)
    return t * t * (3 - 2 * t)


def ease_in(t):
    """Ξεκινά αργά και φτάνει σε σταθερή ταχύτητα (για το πρώτο τετράγωνο ενός μεγάλου μπλοκ)."""
    t = _clamp(t)
    return 2 * t * t - t ** 3


def ease_out(t):
    return 1 - ease_in(1 - t)


EASES = {"both": ease, "in": ease_in, "out": ease_out, "none": _clamp}


class Layout:
    """Πού μπαίνει τι στην οθόνη.

    "side":  λαβύρινθοι 1-6. Η οθόνη στα δύο: αριστερά ο λαβύρινθος, δεξιά πάνω το χειριστήριο
             (οριζόντιο) και από κάτω το πρόγραμμα. Στο τέλος και «Εκτέλεση εντολών».
    "strip": λαβύρινθοι 7-20. Ο λαβύρινθος και το χειριστήριο (κάθετο) λίγο πιο κοντά, και από κάτω,
             σε όλο το πλάτος, λωρίδα με την τελευταία εντολή.
    """

    def __init__(self, mode):
        self.mode = mode
        self.run_rect = None
        if mode == "side":
            self.board = pygame.Rect(14, 104, 600, 604)
            self.panel = pygame.Rect(628, 104, 638, 188)
            self.code = pygame.Rect(628, self.panel.bottom + 12, 638, 708 - self.panel.bottom - 12)
            self.canvas = pygame.Rect(self.code.x + 12, self.code.y + 40, self.code.w - 24, self.code.h - 52)
            self.rows = PROGRAM_ROWS
            self.avatar, self.avatar_size, self.avatar_r = (self.panel.x + 92, self.panel.y + 60), 84, 50
            bw, bh, gap = 132, 78, 8
            x0, y0 = self.panel.x + 186, self.panel.y + 12
            row = y0 + bh + gap
            # «Μπράβο» και από κάτω «Εκτέλεση εντολών» και «Επόμενο», όλα πάνω στον λαβύρινθο,
            # ώστε το πρόγραμμα να φαίνεται ολόκληρο δίπλα τους.
            top = self.board.centery - (180 + 18 + 150) // 2
            self.banner_center = (self.board.centerx, top + 90)
            self.run_rect = pygame.Rect(self.board.centerx - 200, top + 198, 190, 150)
            self.go_rect = pygame.Rect(self.board.centerx + 10, top + 198, 150, 150)
        else:
            self.board = pygame.Rect(14, 104, 902, 504)
            self.panel = pygame.Rect(932, 104, 334, 504)
            self.code = pygame.Rect(14, 620, 1252, 88)
            self.canvas = pygame.Rect(self.code.x + 196, self.code.y + 12, self.code.w - 208, self.code.h - 24)
            self.rows = 1
            self.avatar, self.avatar_size, self.avatar_r = (self.panel.centerx, self.panel.y + 66), 92, 54
            bw, bh, gap = 94, 124, 10
            x0 = self.panel.centerx - (3 * bw + 2 * gap) // 2
            y0 = self.panel.y + 156
            row = y0 + bh + 16
            # Το «Μπράβο» (500 πλάτος) και δίπλα του το μεγάλο κουμπί «Επόμενο», μαζί στη μέση του λαβύρινθου.
            left = self.board.centerx - (500 + 24 + 150) // 2
            self.banner_center = (left + 250, self.board.centery)
            self.go_rect = pygame.Rect(left + 524, self.board.centery - 75, 150, 150)
        self.controls = {
            "forward": pygame.Rect(x0 + bw + gap, y0, bw, bh),
            "left": pygame.Rect(x0, row, bw, bh),
            "back": pygame.Rect(x0 + bw + gap, row, bw, bh),
            "right": pygame.Rect(x0 + 2 * (bw + gap), row, bw, bh),
        }
        self.controls_area = self.controls["left"].unionall(list(self.controls.values())).inflate(16, 22)

    def room(self):
        """Το φόντο με τα πάνελ (ζωγραφίζεται μία φορά)."""
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(surf, ui.mix((234, 242, 252), (212, 226, 244), y / HEIGHT), (0, y), (WIDTH, y))
        p, c = self.panel, self.code
        dark, grey, light = (44, 54, 76), (90, 100, 120), (110, 120, 140)
        ui.panel(surf, p, (255, 255, 255), radius=20, border=(206, 214, 228))
        pygame.draw.circle(surf, (232, 240, 252), self.avatar, self.avatar_r)
        ui.panel(surf, c, (255, 255, 255), radius=20, border=(206, 214, 228))
        if self.mode == "strip":
            ui.text(surf, "Χειριστήριο", (p.centerx, p.y + 138), 19, dark)
            ui.text(surf, "Πάτα τα κουμπιά", (p.centerx, p.bottom - 46), 17, grey, bold=False)
            ui.text(surf, "ή τα βελάκια του πληκτρολογίου", (p.centerx, p.bottom - 24), 17, grey, bold=False)
            ui.text(surf, "Το πρόγραμμα", (c.x + 22, c.y + 32), 21, dark, anchor="midleft")
            ui.text(surf, "η τελευταία εντολή", (c.x + 22, c.y + 58), 15, light, anchor="midleft", bold=False)
            return surf
        x = self.avatar[0]
        ui.text(surf, "Χειριστήριο", (x, p.y + 128), 19, dark)
        ui.text(surf, "Πάτα τα κουμπιά", (x, p.y + 152), 15, grey, bold=False)
        ui.text(surf, "ή τα βελάκια", (x, p.y + 170), 15, grey, bold=False)
        ui.text(surf, "Το πρόγραμμα", (c.x + 22, c.y + 21), 21, dark, anchor="midleft")
        ui.text(surf, "κάθε κουμπί γράφει μια εντολή, όπως στο Mind+", (c.right - 22, c.y + 22), 15,
                light, anchor="midright", bold=False)
        return surf


class ControlButton:
    """Κουμπί του χειριστηρίου. Φαίνεται πατημένο όσο το κρατά το ποντίκι ή το βελάκι,
    και λίγο ακόμα μετά από ένα γρήγορο πάτημα, για να το προλάβει το μάτι."""

    def __init__(self, name, rect, color, icon, lines, key_dir, compact=False):
        self.name = name
        self.rect = pygame.Rect(rect)
        self.color = color
        self.icon = icon
        self.lines = lines
        self.key_dir = key_dir
        self.compact = compact
        self.held_mouse = False
        self.held_key = False
        self.flash_until = -1.0
        self.hover = False

    def contains(self, pos):
        return self.rect.collidepoint(pos)

    def pressed(self, time):
        return self.held_mouse or self.held_key or time < self.flash_until

    def draw(self, surf, time):
        art.ctrl_button(surf, self.rect, self.color, self.icon, self.lines, self.key_dir,
                        self.pressed(time), self.hover, self.compact)


class MazeScene(Scene):
    def __init__(self, app, index=0):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.held_control = None
        self.confetti = fx.Confetti()
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 215))
        self.layouts = {mode: Layout(mode) for mode in ("side", "strip")}
        self.views = {mode: blocks.StackView(L.canvas, L.rows) for mode, L in self.layouts.items()}
        self.rooms = {}
        self.layout = None
        self.dots_xy = [(CENTER_X - (LEVEL_COUNT - 1) * 16 + i * 32, 30) for i in range(LEVEL_COUNT)]
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((116, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        self.buttons = [self.btn_again, self.btn_next, self.btn_sound, self.btn_menu]
        # Εμφανίζονται με το «Μπράβο» όταν το R2 φτάσει στον φορτιστή.
        self.btn_go = B((0, 0, 150, 150), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level, label_size=24)
        self.btn_go.pulse = True
        self.btn_run = blocks.RunButton((0, 0, 190, 150), self.run_program)
        self.load(index)

    # ------------------------------------------------------------- setup
    def _use_layout(self, layout):
        if layout is self.layout:
            return
        self.layout = layout
        self.btn_go.rect = pygame.Rect(layout.go_rect)
        if layout.run_rect:
            self.btn_run.rect = pygame.Rect(layout.run_rect)
        r, C, small = layout.controls, ControlButton, layout.mode == "side"
        self.controls = {
            "forward": C("forward", r["forward"], art.TEAL, art.arrow_up, ["Μπροστά"], logic.UP, small),
            "left": C("left", r["left"], art.ORANGE, art.turn_left, ["Στρίψε", "αριστερά"], logic.LEFT, small),
            "back": C("back", r["back"], art.TEAL, art.arrow_down, ["Πίσω"], logic.DOWN, small),
            "right": C("right", r["right"], art.ORANGE, art.turn_right, ["Στρίψε", "δεξιά"], logic.RIGHT, small),
        }
        self.held_control = None
        self.view = self.views[layout.mode]
        if layout.mode not in self.rooms:
            room = layout.room()
            self.view.draw_background(room)
            self.rooms[layout.mode] = room

    def load(self, index):
        self.index = index % LEVEL_COUNT
        self._use_layout(self.layouts["side" if self.index < SIDE_LEVELS else "strip"])
        self.maze = logic.Maze(levels.LEVELS[self.index])
        self.robot = logic.Robot(self.maze)
        self.board = art.Board(self.maze, self.layout.board)
        self.base = self.rooms[self.layout.mode].copy()
        self.board.draw_floor(self.base)
        self.anim = None
        self.queue = []                       # εντολές που περιμένουν να τελειώσει η κίνηση
        self.angle = self.robot.facing * 90.0
        self.pos = self.board.center(self.robot.cell)
        self.red_until = -1.0
        self.bumps = []                       # (θέση, πότε) για τα αστεράκια του χτυπήματος
        self.done_time = None
        self.celebrated = False
        # το πρόγραμμα και η εκτέλεσή του (η εκτέλεση μόνο στους πρώτους λαβύρινθους)
        self.program = logic.Program()
        self.steps = None                     # τα βήματα που μένουν, όσο εκτελείται το πρόγραμμα
        self.run_at = 0.0
        self.running = None                   # το μπλοκ που τρέχει
        self.fresh = None                     # (μπλοκ, πότε) για το μπλοκ που μόλις γράφτηκε
        self.view.set_blocks([])
        self.view.target = 0
        self.view.jump()
        last = self.index == LEVEL_COUNT - 1
        # Το «Μπράβο» μένει στην οθόνη ώσπου το παιδί να πατήσει «Επόμενο».
        self.banner = fx.Banner("Μπράβο!", "Τελείωσες όλους τους λαβυρίνθους!" if last
                                else "Το R2 βρήκε τον φορτιστή!", stay=math.inf)
        self.confetti.clear()
        self.message = MSG["start"]

    # ------------------------------------------------------------ actions
    def restart(self):
        self.load(self.index)

    def next_level(self):
        self.app.sounds.play("swoosh", 0.7)
        self.load(self.index + 1)

    def to_menu(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    @property
    def replaying(self):
        return self.steps is not None

    def command(self, name):
        """Μια εντολή από κουμπί ή βελάκι. Αν το R2 κινείται ακόμα, η εντολή περιμένει τη σειρά της,
        ώστε να γίνεται κάθε πάτημα (ως MAX_WAITING, για να μη μαζεύονται πολλές)."""
        if self.robot.done or self.replaying:
            return
        if self.anim is not None:
            if len(self.queue) < MAX_WAITING:
                self.queue.append(name)
            return
        self._run(name)

    def _run(self, name, dur=None, how="both"):
        """Εκτελεί μία εντολή. dur: πόσο κρατά (στην εκτέλεση του προγράμματος, όσο γράφει το μπλοκ)."""
        replay = dur is not None
        for ev in self.robot.command(name):
            kind = ev[0]
            if kind == "move":
                self.anim = {"kind": "move", "start": self.time, "dur": dur or MOVE_TIME, "ease": how,
                             "a": self.board.center(ev[1]), "b": self.board.center(ev[2])}
                self.app.sounds.play("motor", 0.6)
                if self.message == MSG["bump"]:
                    self.message = MSG["start"]
            elif kind == "turn":
                delta = 90 if name == "right" else -90
                self.anim = {"kind": "turn", "start": self.time, "dur": dur or TURN_TIME, "ease": how,
                             "a": self.angle, "b": self.angle + delta}
                self.app.sounds.play("turn", 0.6)
            elif kind == "bump":
                d = ev[2]
                self.anim = {"kind": "bump", "start": self.time, "dur": BUMP_TIME, "d": d}
                self.red_until = self.time + 0.9
                cx, cy = self.board.center(ev[1])
                dx, dy = logic.STEP[d]
                half = self.board.cell * 0.5
                self.bumps.append(((cx + dx * half, cy + dy * half), self.time + BUMP_TIME * 0.4))
                self.app.sounds.play("bump", 0.7)
                self.message = MSG["bump"]
                self.queue.clear()        # όπως το αληθινό ρομπότ: μετά από χτύπημα σταματά
            if kind in ("move", "turn") and not replay:
                self._write(name)

    def _write(self, name):
        """Γράφει την εντολή στο πρόγραμμα (ή μεγαλώνει το τελευταίο μπλοκ) και την κάνει να λάμψει."""
        i = self.program.add(name)
        self.view.set_blocks(self.block_parts())
        self.view.show(i)
        self.fresh = (i, self.time)

    def block_parts(self):
        """Τα μπλοκ του προγράμματος, όπως στο Mind+."""
        out = []
        for i, (name, _n) in enumerate(self.program.blocks):
            sec = self.program.seconds(i)
            out.append(blocks.move(name, sec) if name in ("forward", "back") else blocks.turn(name, sec))
        return out

    def run_program(self):
        """Η πράσινη σημαία: το R2 γυρίζει στην ΑΡΧΗ και εκτελεί όλο το πρόγραμμα, μπλοκ μπλοκ."""
        if not self.program or not self.layout.run_rect:
            return
        self.robot = logic.Robot(self.maze)
        self.angle = self.robot.facing * 90.0
        self.pos = self.board.center(self.robot.cell)
        self.anim = None
        self.queue = []
        self.bumps = []
        self.done_time = None
        self.celebrated = False
        self.banner.hide()
        self.confetti.clear()
        self.steps = self.program.steps()
        self.run_at = self.time + RUN_PAUSE
        self.running = None
        self.fresh = None
        self.message = MSG["run"]
        self.view.target = 0                  # από την αρχή, με το R2 starts

    def _next_step(self):
        if not self.steps:
            self.steps = None
            self.running = None
            if self.robot.done:
                self._arrive()
            else:
                self.message = MSG["start"]
            return
        i, name, first, last = self.steps.pop(0)
        self.running = i
        self.view.show(i, below=2)
        how = "both" if first and last else ("in" if first else ("out" if last else "none"))
        self._run(name, dur=float(logic.SECONDS), how=how)

    def _arrive(self):
        self.done_time = self.time
        self.message = MSG["done"]
        self.app.progress.mark(GAME_ID, self.index + 1)
        self.app.sounds.play("charge", 0.7)

    # -------------------------------------------------------------- input
    def active_buttons(self):
        """Τα κουμπιά της πάνω μπάρας, και όσα βγαίνουν με το «Μπράβο» όταν φαίνεται."""
        if not self.celebrated:
            return self.buttons
        return self.buttons + ([self.btn_run] if self.layout.run_rect and self.program else []) + [self.btn_go]

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
            for b in self.active_buttons():
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed_button = b
                    return
            if not self.replaying:
                for c in self.controls.values():
                    if c.contains(e.pos):
                        c.held_mouse = True
                        self.held_control = c
                        self.command(c.name)
                        return
            dot = self.dot_at(e.pos)
            if dot is not None:
                self.app.sounds.play("swoosh", 0.7)
                self.load(dot)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.held_control:
                self.held_control.held_mouse = False
                self.held_control.flash_until = self.time + 0.12
                self.held_control = None
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.MOUSEWHEEL:
            if self.layout.canvas.collidepoint(self.mouse):
                self.view.scroll_by(-e.y)
        elif e.type == pygame.KEYDOWN:
            if e.key in KEYS:
                if self.replaying:
                    return
                c = self.controls[KEYS[e.key]]
                c.held_key = True
                c.flash_until = self.time + 0.15
                self.command(c.name)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.celebrated:
                self.app.sounds.play("button")
                self.next_level()
            elif e.key == pygame.K_ESCAPE:
                self.to_menu()
            elif e.key == pygame.K_n:
                self.next_level()
            elif e.key == pygame.K_r:
                self.restart()
            elif e.key == pygame.K_m:
                self.app.sounds.toggle()
        elif e.type == pygame.KEYUP and e.key in KEYS:
            self.controls[KEYS[e.key]].held_key = False

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        a = self.anim
        if a and self.time >= a["start"] + a["dur"]:
            self.anim = None
            if a["kind"] == "move":
                self.pos = a["b"]
            elif a["kind"] == "turn":
                self.angle = a["b"] % 360
            if self.replaying:
                self._next_step()
            elif self.robot.done and self.done_time is None:
                self._arrive()
            elif self.queue:
                self._run(self.queue.pop(0))
        if self.replaying and self.anim is None and self.time >= self.run_at:
            self._next_step()
        if self.done_time is not None and not self.celebrated and self.time >= self.done_time + CELEBRATE_AFTER:
            self.celebrated = True
            self.app.sounds.play("win", 0.9)
            self.confetti.burst(WIDTH)
            self.banner.show(self.time)
        self.bumps = [(p, t) for p, t in self.bumps if self.time - t < 0.8]
        self.btn_next.pulse = self.done_time is not None
        for b in self.active_buttons():
            b.hover = b.contains(self.mouse)
        for c in self.controls.values():
            c.hover = c.contains(self.mouse) and not self.replaying
        self.view.update(dt)
        self.confetti.update(dt, self.time, HEIGHT)
        self._update_cursor()

    def _update_cursor(self):
        pos = self.mouse
        hand = (any(b.enabled and b.contains(pos) for b in self.active_buttons())
                or (not self.replaying and any(c.contains(pos) for c in self.controls.values()))
                or self.dot_at(pos) is not None)
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # --------------------------------------------------------------- draw
    def robot_state(self):
        """Πού είναι και προς τα πού κοιτάει το R2 αυτή τη στιγμή (μαζί με την κίνηση)."""
        pos, angle = self.pos, self.angle
        a = self.anim
        if a:
            t = (self.time - a["start"]) / a["dur"]
            if a["kind"] == "move":
                k = EASES[a["ease"]](t)
                pos = (a["a"][0] + (a["b"][0] - a["a"][0]) * k, a["a"][1] + (a["b"][1] - a["a"][1]) * k)
            elif a["kind"] == "turn":
                angle = a["a"] + (a["b"] - a["a"]) * EASES[a["ease"]](t)
            else:
                dx, dy = logic.STEP[a["d"]]
                push = math.sin(math.pi * max(0.0, min(1.0, t))) * self.board.cell * 0.16
                pos = (pos[0] + dx * push, pos[1] + dy * push)
        return pos, angle

    def led(self):
        if self.done_time is not None:
            return art.LED_GREEN
        if self.time < self.red_until:
            return art.LED_RED
        return art.LED_BLUE

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

    def _draw_program(self, screen):
        fresh, alpha = None, 0
        if self.fresh is not None:
            i, t = self.fresh
            age = self.time - t
            if age < FRESH_TIME:
                fresh, alpha = i, 255 * (1 - age / FRESH_TIME)
        self.view.draw(screen, running=self.running, fresh=fresh, fresh_alpha=alpha)

    def draw(self, screen):
        screen.blit(self.base, (0, 0))
        board = self.board
        charging = self.done_time is not None
        art.charger(screen, board.cell_rect(self.maze.goal), self.time, charging)
        pos, angle = self.robot_state()
        moving = self.anim is not None and self.anim["kind"] == "move"
        trail = [board.center(c) for c in self.robot.trail[:-1]]
        trail.append(pos if moving else board.center(self.robot.cell))
        board.trail(screen, trail)
        screen.blit(board.walls(), board.frame)
        led = self.led()
        if charging:
            art.charge_rings(screen, pos, self.time, board.robot_size)
        art.draw_robot(screen, pos, board.robot_size, angle, led)
        for p, t in self.bumps:
            art.bump_stars(screen, p, self.time - t, board.cell)
        art.draw_robot(screen, self.layout.avatar, self.layout.avatar_size, 0, led)
        for c in self.controls.values():
            c.draw(screen, self.time)
        if self.replaying:
            # όσο εκτελείται το πρόγραμμα, το χειριστήριο ξεθωριάζει: τώρα «οδηγεί» το πρόγραμμα
            veil = pygame.Surface(self.layout.controls_area.size, pygame.SRCALPHA)
            veil.fill((255, 255, 255, 150))
            screen.blit(veil, self.layout.controls_area)
        self._draw_program(screen)
        self._draw_top(screen)
        self.confetti.draw(screen)
        self.banner.draw(screen, self.time, self.layout.banner_center)
        if self.celebrated:
            if self.btn_run in self.active_buttons():
                self.btn_run.draw(screen, self.time)
            self.btn_go.draw(screen, self.time)
