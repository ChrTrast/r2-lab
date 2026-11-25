"""Προγραμμάτισε: η οθόνη του παιχνιδιού.

Αριστερά το νησάκι με το R2, δεξιά πάνω οι Εντολές (ή το χειριστήριο στις πίστες «Δες») και από κάτω
ο χώρος προγράμματος με το «Πάμε!». Το παιδί σέρνει εντολές κάτω από το «R2 starts» (ή τις πατά),
αλλάζει ▾, αριθμούς και χρώματα όπως στο Mind+, και πατά «Πάμε!». Το R2 εκτελεί το πρόγραμμα βήμα βήμα
και φωτίζεται κίτρινο το μπλοκ που τρέχει. Αν κάτι πάει στραβά, το R2 σταματά και το μπλοκ γίνεται κόκκινο,
με ένα συννεφάκι που λέει τι έγινε. Στο τέλος: τρία αστέρια (φορτιστής, κρύσταλλοι, λίγες εντολές).
"""
import math
from collections import deque

import pygame

from core import blocks, fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.line_follow import art as lf
from games.maze import art as r2art
from . import GAME_ID, LEVEL_COUNT, art, code, levels, logic

TOP_H = 92
CENTER_X = 653
WORLD = pygame.Rect(14, 104, 684, 604)
RIGHT_X, RIGHT_W = 712, 554
STEP_TIME = 0.5            # πόσο κρατά στην οθόνη 1 δευτερόλεπτο του R2 (1 κουτάκι, ¼ στροφής)
DRIVE_TIME = 0.32          # στις πίστες «Δες», όταν οδηγείς με τα κουμπιά
QUICK = 0.3                # μπλοκ που δεν παίρνουν χρόνο (LED, Σταμάτησε, Κινήσου χωρίς τέλος)
HEAD = 0.25                # το κεφάλι ενός «επανάλαβε» / «εάν» πριν μπει μέσα
BUMP_TIME = 0.6
DOCK_TIME = 1.1
NEXT_MAP_TIME = 1.6        # «Μπράβο! Και τώρα σε άλλον χάρτη»
FRESH_TIME = 0.8
DRAG_START = 6             # pixel: πόσο πρέπει να κουνηθεί το ποντίκι για να αρχίσει το σύρσιμο
MAX_WAITING = 3            # «Δες»: πόσα πατήματα περιμένουν όσο κινείται το R2
UNDO_MAX = 60
IDLE_HINT = 2.5            # δευτερόλεπτα χωρίς αλλαγή: το «Πάμε!» λάμπει, για να το πατήσουν
MODES = {"see": ("Δες", (62, 132, 222)), "fix": ("Διόρθωσε", (238, 146, 46)), "write": ("Γράψε", (52, 160, 80))}
DARK, GREY, LIGHT = (44, 54, 76), (90, 100, 120), (120, 130, 150)
RED = (232, 60, 60)
BLUE = (62, 132, 222)
WHY = {
    "stone": ["Εδώ το R2 χτύπησε", "σε πέτρα!"],
    "tree": ["Εδώ το R2 χτύπησε", "σε δέντρο!"],
    "water": ["Ωχ! Νερό!", "Το R2 δεν κολυμπάει."],
    "edge": ["Στοπ! Εδώ τελειώνει", "το νησί."],
    "door": ["Η πόρτα είναι κλειστή!", "Τι χρώμα έχει το LED;"],
    "bug": ["Πρόσεξε!", "Η πασχαλίτσα!"],
    "bridge": ["Η γέφυρα βούλιαξε!", "Περίμενε να ανέβει."],
    "box": ["Εδώ το R2 χτύπησε", "στην εργαλειοθήκη!"],
    "noline": ["Το R2 δεν είναι", "πάνω στη μαύρη γραμμή!"],
    "end": ["Το πρόγραμμα τελείωσε,", "αλλά το R2 δεν έφτασε", "στον φορτιστή."],
    "time": ["Το R2 έψαξε πολλή ώρα", "και κουράστηκε."],
    "stuck": ["Το «για πάντα» δεν κάνει", "τίποτα που να κινεί το R2."],
}
# Μια μικρή ερώτηση κάτω από το «τι έγινε», για την εντολή που θέλει διόρθωση (χωρίς να λέει την απάντηση).
HINTS = {("turn", "dir"): "Μήπως στρίβει από την άλλη;", ("move", "dir"): "Μπροστά ή πίσω;",
         ("go", "dir"): "Μπροστά ή πίσω;", ("move", "n"): "Μήπως θέλει άλλον αριθμό;",
         ("turn", "n"): "Μήπως θέλει άλλον αριθμό;", ("wait", "n"): "Πόσα δευτερόλεπτα να περιμένει;",
         ("repeat", "n"): "Πόσες φορές χρειάζονται;", ("led", "color"): "Τι χρώμα θέλει το LED;",
         ("until", "cm"): "Μήπως θέλει άλλον αριθμό;", ("if", "cm"): "Μήπως θέλει άλλον αριθμό;",
         ("line", "mode"): "Ενεργοποίηση ή απενεργοποίηση;"}
DRIVE_WHY = {"stone": "Ωχ! Εκεί έχει πέτρα.", "tree": "Ωχ! Εκεί έχει δέντρο.", "water": "Ωχ! Νερό!",
             "edge": "Στοπ! Εκεί τελειώνει το νησί.", "door": "Η πόρτα είναι κλειστή!", "bug": "Πρόσεξε την πασχαλίτσα!"}
ARROWS = {pygame.K_UP: "up_arrow", pygame.K_DOWN: "down_arrow", pygame.K_RIGHT: "right_arrow",
          pygame.K_LEFT: "left_arrow"}         # το τηλεκοντρόλ: τα βελάκια του πληκτρολογίου
CONTROL_ARROW = {"forward": "up_arrow", "back": "down_arrow", "left": "left_arrow", "right": "right_arrow"}
ARROW_CONTROL = {a: name for name, a in CONTROL_ARROW.items()}
OFF_BUTTON = (178, 184, 196)          # κουμπί του χειριστηρίου χωρίς πρόγραμμα (τηλεκοντρόλ)
SEE_NODES = {"forward": ("move", "forward"), "back": ("move", "back"), "left": ("turn", "left"),
             "right": ("turn", "right")}


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def cell_center(c):
    return c[0] + 0.5, c[1] + 0.5


def depth_key(c):
    return c[1], c[0]


def bubble(surf, lines, anchor, side="left", border=RED, size=18):
    """Συννεφάκι με μύτη που δείχνει το anchor. side: πού είναι το συννεφάκι ως προς το anchor."""
    f = ui.font(size)
    w = max(f.size(t)[0] for t in lines) + 32
    h = len(lines) * (size + 8) + 18
    ax, ay = round(anchor[0]), round(anchor[1])
    if side == "up" and ay - 18 - h < TOP_H + 6:
        side, ay = "down", ay + 70
    if side == "left":
        r = pygame.Rect(ax - 18 - w, ay - h // 2, w, h)
        tip = [(r.right - 2, ay - 10), (ax, ay), (r.right - 2, ay + 10)]
    elif side == "up":
        r = pygame.Rect(ax - w // 2, ay - 18 - h, w, h)
        tip = [(ax - 12, r.bottom - 2), (ax, ay), (ax + 12, r.bottom - 2)]
    elif side == "down":
        r = pygame.Rect(ax - w // 2, ay + 18, w, h)
        tip = [(ax - 12, r.y + 2), (ax, ay), (ax + 12, r.y + 2)]
    else:
        r = pygame.Rect(ax + 18, ay - h // 2, w, h)
        tip = [(r.x + 2, ay - 10), (ax, ay), (r.x + 2, ay + 10)]
    shift_x = max(8 - r.x, 0) - max(r.right - (WIDTH - 8), 0)
    if side in ("up", "down") and shift_x:
        r.x += shift_x
    sh = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 50), sh.get_rect(), border_radius=16)
    surf.blit(sh, r.move(0, 4))
    pygame.draw.rect(surf, (255, 255, 255), r, border_radius=16)
    ui.fill_poly(surf, (255, 255, 255), tip)
    pygame.draw.rect(surf, border, r, width=3, border_radius=16)
    pygame.draw.lines(surf, border, False, tip, 3)
    if side in ("up", "down"):
        dy = 2 if side == "up" else -2
        pygame.draw.line(surf, (255, 255, 255), (tip[0][0] + 2, tip[0][1] + dy), (tip[2][0] - 2, tip[2][1] + dy), 3)
    else:
        pygame.draw.line(surf, (255, 255, 255), (tip[0][0], tip[0][1] + 3), (tip[2][0], tip[2][1] - 3), 3)
    for i, t in enumerate(lines):
        ui.text(surf, t, (r.centerx, r.y + 9 + (size + 8) * i + (size + 8) // 2), size, DARK)
    return r


class FlagButton(ui.Button):
    """Το «Πάμε!» με την πράσινη σημαία, πάνω από το πρόγραμμα όπως στο Scratch: μεγάλο, γεμάτο πράσινο.
    Όσο τρέχει το πρόγραμμα γίνεται κόκκινο «Σταμάτα»."""

    def __init__(self, rect, action):
        super().__init__(rect, "Πάμε!", None, (255, 255, 255), action)
        self.stop = False

    def draw(self, surf, time=0.0):
        r = self.rect
        if self.enabled and self.pulse and not self.stop:
            p = 0.5 + 0.5 * math.sin(time * 6)
            ui.glow(surf, r.inflate(14 + 10 * p, 14 + 10 * p), (255, 214, 60), 110 + 120 * p, radius=24)
        if not self.enabled:
            col, base = (196, 200, 208), (168, 172, 182)
        elif self.stop:
            col, base = (232, 76, 76), (176, 44, 44)
        else:
            col, base = blocks.FLAG, blocks.FLAG_EDGE
        if self.hover and not self.pressed and self.enabled:
            col = ui.mix(col, (255, 255, 255), 0.14)
        face = r.move(0, 6 if self.pressed else 0)
        pygame.draw.rect(surf, ui.shade(base, 0.85), r.move(0, 6), border_radius=18)
        pygame.draw.rect(surf, col, face, border_radius=18)
        pygame.draw.rect(surf, ui.mix(col, (255, 255, 255), 0.3), (face.x + 12, face.y + 6, face.w - 24, 6),
                         border_radius=3)
        disc = (face.x + face.h // 2 + 4, face.centery)
        pygame.draw.circle(surf, (255, 255, 255), disc, face.h * 0.38)
        if self.stop:
            cx, cy, R = disc[0], disc[1], face.h * 0.25
            pts = [(cx + R * math.cos(math.pi / 8 + i * math.pi / 4), cy + R * math.sin(math.pi / 8 + i * math.pi / 4))
                   for i in range(8)]
            ui.fill_poly(surf, (236, 86, 86), pts, (180, 40, 40))
            ui.text(surf, "Σταμάτα", (disc[0] + face.h * 0.5, face.centery), 30, (255, 255, 255), anchor="midleft")
            return
        blocks.green_flag(surf, (disc[0] + 2, disc[1]), face.h * 0.56)
        ui.text(surf, self.label, (disc[0] + face.h * 0.5, face.centery), 32, (255, 255, 255), anchor="midleft")


class Control:
    """Ένα κουμπί του χειριστηρίου (πίστες «Δες»). Πατιέται μόνο με το ποντίκι, όχι με τα βελάκια.
    Στο τηλεκοντρόλ είναι γκρι (enabled=False) όσο δεν υπάρχει πρόγραμμα για το βελάκι του."""

    def __init__(self, name, rect, color, icon, label):
        self.name, self.rect, self.color, self.icon, self.label = name, pygame.Rect(rect), color, icon, label
        self.held = False
        self.flash_until = -1.0
        self.hover = False
        self.enabled = True

    def draw(self, surf, time):
        on = self.enabled
        r2art.ctrl_button(surf, self.rect, self.color if on else OFF_BUTTON, self.icon, [self.label], None,
                          on and (self.held or time < self.flash_until), on and self.hover, compact=True)


class ProgramScene(Scene):
    def __init__(self, app, index=0):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.confetti = fx.Confetti()
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 228))
        self.room = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(self.room, ui.mix((234, 242, 252), (212, 226, 244), y / HEIGHT), (0, y), (WIDTH, y))
        self.dots_xy = [(CENTER_X - (LEVEL_COUNT - 1) * 16 + i * 32, 30) for i in range(LEVEL_COUNT)]
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((116, 8, 100, 76), "Επόμενο", ui.icon_next, BLUE, self.next_level)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        self.btn_undo = B((0, 0, 86, 56), "Αναίρεση", ui.icon_undo, (120, 130, 150), self.undo, label_size=14)
        self.btn_trash = B((0, 0, 86, 56), "Σβήσ' τα", ui.icon_trash, (120, 130, 150), self.clear, label_size=14)
        self.btn_run = FlagButton((0, 0, 236, 64), self.run_or_stop)
        self.btn_go = B((0, 0, 170, 84), "Επόμενο", ui.icon_next, BLUE, self.next_level, label_size=20)
        self.btn_go.pulse = True
        self.btn_retry = B((0, 0, 150, 84), "Ξανά", ui.icon_again, (238, 146, 46), self.close_banner, label_size=18)
        self._culprit_key, self._culprit = None, None
        self.load(index)

    # ================================================================ πίστα
    def load(self, index):
        self.index = index % LEVEL_COUNT
        self.level = lv = levels.LEVELS[self.index]
        self.mode = lv["mode"]
        self.worlds = logic.level_worlds(lv)
        self.boards = [None] * len(self.worlds)
        self.variant = 0
        self.program = logic.clone(lv.get("program") or [])
        self.history = []
        self._layout_panels()
        self.view.set_program(self.program)
        self.view.target = self.view.scroll = 0
        self.popup = None
        self.drag = None              # {"chunk", "grab", "from"}
        self.press = None             # πάτημα που ίσως γίνει σύρσιμο
        self.preview = None
        self.fresh = None
        self.queue = deque()          # «Δες»: πατήματα που περιμένουν
        self.message = None           # (γραμμές, πότε, χρώμα): συννεφάκι πάνω από το R2
        self.celebrated = False
        self.stars = None
        self.confetti.clear()
        self.live = logic.Run(self.world) if self.mode == "see" or self.remote else None
        if self.remote:
            self.live.max_time = 10 ** 6      # το παιδί οδηγεί όσο θέλει
        self.drove_home = False
        self.round = []               # οι χάρτες που μένουν σε αυτό το «Πάμε»
        self.round_crystals = True
        self.map_pace = 1.0           # οι επόμενοι χάρτες ενός «Πάμε» τρέχουν πιο γρήγορα
        self.next_map_at = None
        self.pending_variant = None   # μετά από λάθος, το επόμενο «Πάμε» αλλάζει χάρτη
        self.empty_flash = -9.0
        self.edited_at = self.time    # πότε άλλαξε τελευταία φορά το πρόγραμμα
        self.ran_since_edit = False   # πατήθηκε το «Πάμε!» μετά την τελευταία αλλαγή;
        self._reset_robot()
        self._sync_buttons()
        if self.remote:
            self.message = (["Πάτα «Μπροστά»!", "Τα γκρι κουμπιά", "θέλουν πρόγραμμα."], self.time, BLUE)

    @property
    def world(self):
        return self.worlds[self.variant]

    @property
    def board(self):
        if self.boards[self.variant] is None:
            self.boards[self.variant] = art.Board(self.world, WORLD)
        return self.boards[self.variant]

    def _make_controls(self, panel, bh, gap):
        """Τα 4 κουμπιά του χειριστηρίου μέσα στο panel (όπως τα βελάκια του πληκτρολογίου)."""
        bw = 156
        x0, y0 = panel.centerx - (3 * bw + 2 * gap) // 2, panel.y + 44
        spec = {"forward": ((0, 166, 186), r2art.arrow_up, "Μπροστά", (x0 + bw + gap, y0)),
                "back": ((0, 166, 186), r2art.arrow_down, "Πίσω", (x0 + bw + gap, y0 + bh + gap)),
                "left": ((238, 128, 40), r2art.turn_left, "Στρίψε αριστερά", (x0, y0 + bh + gap)),
                "right": ((238, 128, 40), r2art.turn_right, "Στρίψε δεξιά", (x0 + 2 * (bw + gap), y0 + bh + gap))}
        return {k: Control(k, (x, y, bw, bh), col, icon, label) for k, (col, icon, label, (x, y)) in spec.items()}

    def _layout_panels(self):
        self.pal_rect = None                  # το τηλεκοντρόλ έχει τις Εντολές σε δικό τους πλαίσιο
        if self.mode == "see":
            self.palette = None
            self.panel = pygame.Rect(RIGHT_X, 104, RIGHT_W, 170)
            self.controls = self._make_controls(self.panel, 56, 8)
        elif self.remote:
            # πάνω το χειριστήριο, από κάτω οι Εντολές, πιο κάτω το πρόγραμμα (χωρίς «Πάμε!»)
            self.panel = pygame.Rect(RIGHT_X, 104, RIGHT_W, 142)
            self.controls = self._make_controls(self.panel, 42, 6)
            top = self.panel.bottom + 8
            self.palette = code.Palette(self.level["palette"], RIGHT_X + 18, top + 42, RIGHT_W - 36, 0.55,
                                        lang=self.lang)
            self.pal_rect = pygame.Rect(RIGHT_X, top, RIGHT_W, round(self.palette.height) + 52)
        elif self.locked:
            # εύκολη «Διόρθωσε»: χωρίς Εντολές, το παιδί αλλάζει μόνο ▾ και αριθμούς στο πρόγραμμα
            self.controls = {}
            self.palette = None
            self.panel = pygame.Rect(RIGHT_X, 104, RIGHT_W, 96)
        else:
            self.controls = {}
            self.palette = code.Palette(self.level["palette"], RIGHT_X + 18, 104 + 48, RIGHT_W - 36, lang=self.lang)
            if self.palette.height > 180:          # πολλές εντολές: λίγο πιο μικρές
                self.palette = code.Palette(self.level["palette"], RIGHT_X + 18, 104 + 48, RIGHT_W - 36, 0.62,
                                            lang=self.lang)
            self.panel = pygame.Rect(RIGHT_X, 104, RIGHT_W, max(120, round(self.palette.height) + 66))
        above = self.pal_rect or self.panel
        gap = 8 if self.remote else 12
        self.code_rect = pygame.Rect(RIGHT_X, above.bottom + gap, RIGHT_W, 708 - above.bottom - gap)
        c = self.code_rect
        # το «Πάμε!» πάνω από το πρόγραμμα (όπως η σημαία στο Scratch), η Αναίρεση και ο κάδος από κάτω
        if self.remote:                       # το τηλεκοντρόλ δεν έχει «Πάμε!»: τα κουμπιά τρέχουν τα προγράμματα
            self.btn_run.rect.topleft = (-2000, -2000)
            top = 40
        else:
            self.btn_run.rect.topleft = (c.x + 14, c.y + 12)
            top = self.btn_run.rect.bottom + 14 - c.y
        bottom = (68 if self.remote else 76) if self.mode != "see" else 12
        self.view = code.CodeView((c.x + 12, c.y + top, c.w - 24, c.h - top - bottom), lang=self.lang,
                                  starts=not self.remote)
        if self.remote:                     # 4 μικρά προγράμματα: να χωράνε όλα χωρίς κύλιση
            self.view.TALL = 0.5
        bar_y = self.view.rect.bottom + 6
        self.btn_undo.rect.topleft = (c.x + 14, bar_y)
        self.btn_trash.rect.topleft = (c.x + 110, bar_y)

    def _reset_robot(self):
        """Το R2 στην αρχή, όπως πριν από ένα «Πάμε»."""
        w = self.world
        self.rx, self.ry = cell_center(w.start)
        self.angle = w.face * 90.0 - 90.0
        self.cell = w.start
        self.tile = w.start
        self.spin = 0.0
        self.led = None
        self.taken = set()
        self.sim_t = 0.0
        self.anim = None
        self.source = None            # τα γεγονότα που μένουν (γεννήτρια ή λίστα)
        self.runner = None            # το logic.Run που εκτελείται
        self.running = None           # το μπλοκ που φωτίζεται
        self.badges = {}
        self.answer = None            # (μπλοκ, ΝΑΙ/ΟΧΙ) στο «εάν»
        self.failure = None           # (μπλοκ, γιατί, κουτάκι)
        self.bump = None              # (θέση στην οθόνη, πότε)
        self.sparkles = []
        self.charging = False
        self.docked = False

    # ============================================================== κουμπιά
    def restart(self):
        if self.remote and not self.celebrated:   # τηλεκοντρόλ: το R2 πίσω στην αρχή, το πρόγραμμα μένει
            program, history = self.program, self.history
            self.load(self.index)
            self.program, self.history = program, history
            self._changed()
            return
        self.load(self.index)

    def next_level(self):
        self.app.sounds.play("swoosh", 0.7)
        self.load(self.index + 1)

    def to_menu(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def close_banner(self):
        """«Ξανά» στο «Μπράβο»: το πρόγραμμα μένει, για να γίνει καλύτερο (στις πίστες «Δες» όλα από την αρχή)."""
        if self.mode == "see":
            self.restart()
            return
        self.celebrated = False
        self.confetti.clear()
        self._reset_robot()

    @property
    def remote(self):
        """Η πίστα «τηλεκοντρόλ»: προγράμματα «όταν πατηθεί πλήκτρο» και το R2 οδηγείται με τα βελάκια."""
        return bool(self.level.get("keys"))

    @property
    def lang(self):
        return code.REMOTE if self.remote else code.PROGRAM

    @property
    def locked(self):
        """Πίστα «Διόρθωσε» χωρίς Εντολές: τα μπλοκ μένουν στη θέση τους (δεν σέρνονται, δεν σβήνονται)
        και διορθώνονται μόνο τα ▾, οι αριθμοί και τα χρώματα."""
        return self.mode == "fix" and not self.level.get("palette")

    @property
    def culprit(self):
        """Μετά από λάθος: (θέση, πεδίο) της εντολής που θέλει διόρθωση, ή None. Αυτή γίνεται κόκκινη,
        όχι απαραίτητα εκείνη όπου σταμάτησε το R2 (η λάθος στροφή φαίνεται στην κίνηση που ακολουθεί)."""
        if not self.failure or self.remote:     # τηλεκοντρόλ: το λάθος μπορεί να είναι στο πάτημα, όχι στο πρόγραμμα
            return None
        key = (self.failure, repr(self.program))
        if key != self._culprit_key:
            self._culprit_key = key
            self._culprit = logic.blame(self.worlds, self.program, self.failure[0], self.level.get("solution"))
        return self._culprit

    def red_block(self):
        """Ποιο μπλοκ γίνεται κόκκινο μετά από λάθος."""
        if not self.failure:
            return None
        found = self.culprit
        return found[0] if found else self.failure[0]

    @property
    def busy(self):
        """Το R2 εκτελεί πρόγραμμα (όχι απλώς οδήγηση με κουμπιά)."""
        return self.runner is not None

    def active_buttons(self):
        out = [self.btn_again, self.btn_next, self.btn_sound, self.btn_menu]
        if self.celebrated:
            return out + [self.btn_go, self.btn_retry]
        if not self.remote:
            out.append(self.btn_run)
        if self.mode != "see":
            out += [self.btn_undo] if self.locked else [self.btn_undo, self.btn_trash]
        return out

    def has_script(self, name):
        """Τηλεκοντρόλ: υπάρχει «όταν πατηθεί πλήκτρο» για το βελάκι αυτού του κουμπιού, με εντολή από κάτω;"""
        return any(node["op"] == "key" and node["key"] == CONTROL_ARROW[name] and node["body"]
                   for node in self.program)

    def _sync_buttons(self):
        if self.remote:                       # τηλεκοντρόλ: γκρι τα κουμπιά χωρίς πρόγραμμα
            for name, ctl in self.controls.items():
                ctl.enabled = self.has_script(name)
        editable = not self.busy and not self.celebrated
        self.btn_undo.enabled = editable and bool(self.history)
        self.btn_trash.enabled = editable and bool(self.program)
        self.btn_run.stop = self.busy or self.next_map_at is not None
        self.btn_run.enabled = self.btn_run.stop or self.anim is None
        waiting = (self.mode != "see" and bool(self.program) and not self.ran_since_edit and not self.drag
                   and not self.popup and self.time - self.edited_at > IDLE_HINT)
        self.btn_run.pulse = not self.busy and ((self.mode == "see" and self.drove_home) or
                                                self.failure is not None or waiting)

    # ========================================================= αλλαγές προγράμματος
    def _remember(self):
        self.history.append(logic.clone(self.program))
        del self.history[:-UNDO_MAX]

    def _changed(self):
        self.view.set_program(self.program)
        self.edited_at, self.ran_since_edit = self.time, False
        if self.failure or self.docked:
            self.failure = None
            self.badges = {}
            self.answer = None

    def undo(self):
        if self.history and not self.busy and not self.celebrated:
            self.program = self.history.pop()
            self._changed()
            self.app.sounds.play("remove", 0.6)

    def clear(self):
        if self.program and not self.busy and not self.celebrated:
            self._remember()
            self.program = []
            self._changed()
            self.app.sounds.play("remove", 0.7)

    def append(self, template):
        """Κλικ σε μια εντολή: μπαίνει στο τέλος του προγράμματος."""
        where, index = logic.append_spot(self.program)
        if template["op"] == "key":            # νέο πρόγραμμα «όταν πατηθεί πλήκτρο», στο τέλος
            where, index = (), len(self.program)
        chunk = [logic.clone(template)]
        if not logic.can_insert(self.program, where, index, chunk, scripts=self.remote):
            self.app.sounds.play("deny", 0.6)
            return
        self._remember()
        logic.insert(self.program, where, index, chunk)
        self._changed()
        path = where + (index,)
        self.fresh = (path, self.time)
        self.view.show(path)
        self.app.sounds.play("place", 0.7)

    def set_field(self, path, field, value):
        node = logic.get(self.program, path)
        if node.get(field) == value:
            return
        self._remember()
        node[field] = value
        self._changed()
        self.fresh = (path, self.time)
        self.app.sounds.play("select", 0.7)

    def open_field(self, item, field, rect):
        node = item.node
        options = logic.choices(node, field)
        # χρώματα: τα 4 χρώματα· αριθμοί: το αριθμητικό· λέξεις (κατεύθυνση, βελάκι, ενεργοποίηση…): λίστα
        if field == "color":
            kind = "colors"
        elif all(isinstance(o, (int, float)) for o in options):
            kind = "pad"
        else:
            kind = "menu"
        self.popup = code.Popup(kind, rect, options, node[field], item.path, field, item.cat)
        self.app.sounds.play("button", 0.6)

    # ============================================================= «Δες»
    def command(self, name):
        """Ένα κουμπί του χειριστηρίου: το R2 κάνει την εντολή αμέσως και γράφεται στο πρόγραμμα.
        Στο τηλεκοντρόλ το κουμπί τρέχει το πρόγραμμα «όταν πατηθεί πλήκτρο» του βελακιού του."""
        if self.remote:
            if self.celebrated:
                return
            if not self.has_script(name):
                self.app.sounds.play("deny", 0.6)
                self.message = (["Αυτό το κουμπί δεν έχει", "πρόγραμμα ακόμα!"], self.time, RED)
                return
            if len(self.queue) < MAX_WAITING:
                self.queue.append(name)
            if self.anim is None and self.source is None:
                self._remote_next()
                self._advance()
            return
        if self.mode != "see" or self.busy or self.celebrated or self.drove_home:
            return
        if len(self.queue) >= MAX_WAITING:
            return
        self.queue.append(name)
        if self.anim is None:
            self._drive_next()

    def _drive_next(self):
        if not self.queue or self.drove_home:
            self.queue.clear()
            return
        name = self.queue.popleft()
        op, d = SEE_NODES[name]
        node = logic.move(d, 1) if op == "move" else logic.turn(d, 1)
        self.failure = None
        events = self.live.do(node)
        if self.live.failure:
            self.live.failure = None
        else:
            self._write(node)
        self.source = iter(events)
        self._advance()

    def _write(self, node):
        """Γράφει την εντολή στο πρόγραμμα. Ίδια εντολή με την προηγούμενη: μεγαλώνει ο αριθμός της."""
        last = self.program[-1] if self.program else None
        if last and last["op"] == node["op"] and last["dir"] == node["dir"] and last["n"] < 9:
            last["n"] += 1
        else:
            self.program.append(node)
        self.view.set_program(self.program)
        path = (len(self.program) - 1,)
        self.fresh = (path, self.time)
        self.view.show(path)

    def _back_to_live(self):
        """Πίστες «Δες»: μετά από ένα «Πάμε» το R2 είναι εκεί που το είχε φέρει το παιδί οδηγώντας."""
        self.live = logic.Run(self.world)
        for node in self.program:
            self.live.do(node)
        self.live.failure = None
        lv = self.live
        self.rx, self.ry = cell_center(lv.pos)
        self.cell = self.tile = lv.pos
        self.angle = lv.facing * 90.0 - 90.0
        self.taken = set(lv.taken)
        self.charging = self.docked = self.drove_home = lv.docked

    # ============================================================== εκτέλεση
    def run_or_stop(self):
        if self.remote:                       # το τηλεκοντρόλ δεν έχει «Πάμε!»
            return
        if self.busy or self.next_map_at is not None:
            self._reset_robot()
            self.round, self.next_map_at, self.message = [], None, None
            if self.mode == "see":
                self._back_to_live()
            return
        if not self.program:
            self.app.sounds.play("deny", 0.6)
            self.empty_flash = self.time
            return
        self.popup = None
        self.ran_since_edit = True
        n = len(self.worlds)
        first = self.variant if self.pending_variant is None else self.pending_variant
        self.pending_variant = None
        self.round = [(first + k) % n for k in range(n)]
        self.round_crystals = True
        self.map_pace = 1.0
        self.message = None
        self._start_round_map()

    def _start_round_map(self):
        self.variant = self.round[0]
        self._reset_robot()
        self.runner = logic.Run(self.world)
        self.failure = None
        self.view.set_program(self.program)
        self.source = self.runner.events(logic.clone(self.program))
        self._advance()

    def press_arrow(self, k):
        """Βελάκι του πληκτρολογίου στο τηλεκοντρόλ: όπως το κουμπί του χειριστηρίου."""
        name = ARROW_CONTROL[k]
        self.controls[name].flash_until = self.time + 0.15
        self.command(name)

    def _remote_next(self):
        """Τηλεκοντρόλ: το επόμενο πάτημα (ή το βελάκι που μένει πατημένο) τρέχει το πρόγραμμά του,
        από εκεί που είναι τώρα το R2 (όπως στις πίστες «Δες»)."""
        name = self.queue.popleft() if self.queue else None
        if name is None:
            held = pygame.key.get_pressed()
            name = next((ARROW_CONTROL[a] for key, a in ARROWS.items() if held[key]), None)
        if name is None or self.celebrated or not self.has_script(name):
            return
        self.live.failure = None
        self.source = self.live.press(logic.clone(self.program), CONTROL_ARROW[name])

    def _advance(self):
        """Παίρνει το επόμενο γεγονός και ξεκινά την κίνησή του."""
        while self.source is not None:
            try:
                e = next(self.source)
            except StopIteration:
                self.source = None
                self.anim = None
                self.running = None if self.busy else self.running
                if self.mode == "see" and not self.busy:
                    self._drive_next()
                if self.remote and not self.busy:
                    self.running = None
                    self._remote_next()
                    if self.source is not None:
                        continue
                return
            if self._start(e):
                return

    def _anim(self, kind, dur, **kw):
        if self.busy:                    # τα μεγάλα προγράμματα επιταχύνουν σιγά σιγά
            dur *= self.map_pace * (1.0 if self.sim_t < 8 else (0.75 if self.sim_t < 20 else 0.55))
        self.anim = dict(kind=kind, start=self.time, dur=dur, **kw)

    def _node_at(self, path):
        try:
            return logic.get(self.program, path) if path else None
        except (IndexError, KeyError):
            return None

    def _start(self, e):
        """Ξεκινά την κίνηση ενός γεγονότος. Επιστρέφει False αν δεν θέλει χρόνο (πάμε στο επόμενο)."""
        k = e.kind
        step = STEP_TIME if self.busy else DRIVE_TIME
        if k == "block":
            if self.busy or self.remote:
                self.running = e.path
                self.view.show(e.path)
                node = self._node_at(e.path)
                if node and node["op"] in ("go", "stop", "until"):
                    self._anim("pause", QUICK)
                    return True
            return False
        if k == "loop":
            self.running = e.path
            self.badges[e.path] = f"{e.a}η φορά"
            self._anim("pause", HEAD if e.a <= 2 else HEAD * 0.4)
            return True
        if k == "branch":
            self.running = e.path
            self.answer = (e.path, "ΝΑΙ" if e.a == 0 else "ΟΧΙ")
            self._anim("pause", HEAD * 1.6, sensor=True)
            return True
        if k == "led":
            self.led = e.a
            self.app.sounds.play("select", 0.5)
            self._anim("pause", QUICK)
            return True
        if k == "move":
            self.sim_t = e.t
            self.cell = e.b
            self.tile = max(e.a, e.b, key=depth_key)
            self._anim("move", step, a=e.a, b=e.b, t=e.t)
            self.app.sounds.play("motor", 0.5)
            return True
        if k == "turn":
            self.sim_t = e.t
            way = 1 if (e.b - e.a) % 4 == 1 else -1
            self._anim("turn", step, a0=self.angle, a1=self.angle + 90 * way, t=e.t, way=way)
            self.app.sounds.play("turn", 0.5)
            return True
        if k == "wait":
            self.sim_t = e.t
            self._anim("wait", step, t=e.t)
            return True
        if k == "crystal":
            self.taken.add(e.a)
            x, y = self.board.pt(e.a[0] + 0.5, e.a[1] + 0.5, 42)
            self.sparkles.append(((x, y), self.time))
            self.app.sounds.play("pick", 0.7)
            return False
        if k == "dock":
            self.docked = True
            self.charging = True
            self.app.sounds.play("charge", 0.7)
            self._anim("dock", DOCK_TIME)
            return True
        if k == "fail":
            return self._failed(e)
        return False

    def _failed(self, e):
        why, cell = e.a, e.b
        if not self.busy:                     # «Δες»: χτύπησε οδηγώντας: απλώς ένα μήνυμα
            self.message = ([DRIVE_WHY.get(why, "Ωχ!")], self.time, RED)
            self.app.sounds.play("bump", 0.7)
            self._bump_anim(cell)
            return True
        self.failure = (e.path, why, cell)
        self.running = None
        if why == "bridge":                     # η γέφυρα βουλιάζει μπροστά του (ή κάτω του)
            self.app.sounds.play("bump", 0.7)
            self._bump_anim(cell, BUMP_TIME * 1.6)
            self.anim["t"] = e.t                # ο χρόνος προχωρά 1 δευτερόλεπτο: φαίνεται να βουλιάζει
        elif why in ("stone", "tree", "water", "edge", "door", "bug", "box"):
            self.app.sounds.play("bump", 0.7)
            self._bump_anim(cell)
        else:
            self.app.sounds.play("deny", 0.6)
            self._anim("pause", 0.2)
        if e.path:
            self.view.show(e.path)
        return True

    def _bump_anim(self, cell, dur=BUMP_TIME):
        a = (self.cell[0] + 0.5, self.cell[1] + 0.5)
        b = (cell[0] + 0.5, cell[1] + 0.5)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self.bump = (self.board.pt(mid[0], mid[1], 40), self.time)
        self._anim("bump", dur, dx=(b[0] - a[0]) * 0.22, dy=(b[1] - a[1]) * 0.22)

    def _finish(self, a):
        """Τέλος μιας κίνησης: το R2 στη θέση του."""
        k = a["kind"]
        if k == "move":
            (x0, y0), (x1, y1) = cell_center(a["a"]), cell_center(a["b"])
            r = math.radians(self.angle)
            self.spin += (-1 if (x1 - x0) * math.cos(r) + (y1 - y0) * math.sin(r) < 0 else 1) / lf.WHEEL_R
            self.rx, self.ry = x1, y1
            self.tile = a["b"]
            self.sim_t = a["t"] + 1
        elif k == "turn":
            self.angle = a["a1"]
            self.sim_t = a["t"] + 1
        elif k == "wait":
            self.sim_t = a["t"] + 1
        elif k == "dock":
            self.charging = False
            if self.busy:
                self._map_done()
                return
            if self.remote:                   # τηλεκοντρόλ: έφτασε οδηγώντας με τα προγράμματά του
                self.anim = None
                self.source = None
                self.running = None
                self.queue.clear()
                self.round_crystals = self.live.taken == self.world.crystals
                self._complete()
                return
            # «Δες»: έφτασε οδηγώντας
            self.drove_home = True
            self.queue.clear()
            self.message = (["Τέλεια! Τώρα πάτα «Πάμε!»:", "το R2 θα κάνει μόνο του", "όλο το πρόγραμμα."],
                            self.time, BLUE)
            self.charging = True
        elif k == "bump" and self.busy and self.failure:
            self._run_stopped()
            return
        self.anim = None
        if self.busy and self.failure and k == "pause":
            self._run_stopped()
            return
        self._advance()

    def _run_stopped(self):
        """Το πρόγραμμα σταμάτησε με λάθος: το R2 μένει εκεί και το μπλοκ γίνεται κόκκινο.
        Αν η πίστα έχει πολλούς χάρτες, το επόμενο «Πάμε» είναι σε άλλον."""
        self.anim = None
        self.source = None
        self.runner = None
        self.badges = {}
        self.round = []
        if self.red_block():
            self.view.show(self.red_block())    # να φαίνεται η εντολή που θέλει διόρθωση
        if len(self.worlds) > 1:
            self.pending_variant = (self.variant + 1) % len(self.worlds)
        if self.mode == "see":
            failure = self.failure
            self._back_to_live()
            self.failure = failure

    def _map_done(self):
        """Έφτασε στον φορτιστή σε αυτόν τον χάρτη."""
        run = self.runner
        self.round_crystals = self.round_crystals and run.taken == self.world.crystals
        self.round.pop(0)
        self.anim = None
        self.source = None
        self.runner = None
        self.running = None
        self.badges = {}
        if self.round:
            self.map_pace = 0.6
            self.message = (["Μπράβο! Και τώρα", "σε άλλον χάρτη..."], self.time, BLUE)
            self.next_map_at = self.time + NEXT_MAP_TIME
            self.charging = True
            return
        self._complete()

    def _complete(self):
        n = logic.count(self.program)
        total = len(self.world.crystals)
        self.stars = [True, self.round_crystals, n <= self.level["limit"]]
        lines = ["Το R2 έφτασε στον φορτιστή" + (" παντού" if len(self.worlds) > 1 else "")]
        if not any(w.crystals for w in self.worlds):
            lines.append("Δεν είχε κρυστάλλους")
        elif self.round_crystals:
            lines.append("Μάζεψε όλους τους κρυστάλλους" if total != 1 else "Μάζεψε τον κρύσταλλο")
        else:
            lines.append("Έμειναν κρύσταλλοι")
        lines.append(f"Το πρόγραμμα έχει {n} εντολ{'ή' if n == 1 else 'ές'}" if self.stars[2]
                     else f"Δοκίμασε με {self.level['limit']} εντολές ή λιγότερες")
        self.star_lines = lines
        self.celebrated = True
        self.charging = True
        self.app.progress.mark(GAME_ID, self.index + 1)
        self.confetti.burst(WIDTH)
        self.app.sounds.play("win", 0.8)

    # ============================================================ ποντίκι
    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots_xy):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 14 ** 2:
                return i
        return None

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self._motion(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self._down(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self._up(e.pos)
        elif e.type == pygame.MOUSEWHEEL:
            if self.view.rect.collidepoint(self.mouse):
                self.view.scroll_by(-e.y * 40)
        elif e.type == pygame.KEYDOWN:
            self._key(e)

    def _key(self, e):
        # τα βελάκια δεν κάνουν τίποτα: στις πίστες «Δες» το R2 οδηγείται μόνο με τα κουμπιά (ποντίκι).
        # Μόνο στο τηλεκοντρόλ οδηγούν το R2, με το πρόγραμμα που έφτιαξε το παιδί.
        if e.key in ARROWS and self.remote:
            self.press_arrow(ARROWS[e.key])
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.celebrated:
                self.next_level()
            elif not self.drag:
                self.run_or_stop()
        elif e.key == pygame.K_z and e.mod & pygame.KMOD_CTRL:
            self.undo()
        elif e.key == pygame.K_ESCAPE:
            if self.popup:
                self.popup = None
            else:
                self.to_menu()

    def _down(self, pos):
        if self.popup:
            choice = self.popup.at(pos)
            p = self.popup
            self.popup = None
            if choice is not None:
                self.set_field(p.path, p.field, choice)
            return
        for b in self.active_buttons():
            if b.enabled and b.contains(pos):
                b.pressed = True
                self.pressed_button = b
                return
        dot = self.dot_at(pos)
        if dot is not None:
            self.app.sounds.play("swoosh", 0.7)
            self.load(dot)
            return
        if self.celebrated:
            return
        for c in self.controls.values():
            if c.rect.collidepoint(pos):
                c.held = True
                c.flash_until = self.time + 0.12
                self.command(c.name)
                return
        if self.mode == "see" or self.busy:
            return
        hit = self.palette.at(pos) if self.palette else None
        if hit:
            node, rect = hit
            self.press = {"pos": pos, "template": node, "rect": rect}
            return
        field = self.view.field_at(pos)
        if field:
            self.open_field(*field)
            return
        if self.locked:                         # τα μπλοκ δεν σέρνονται σε αυτές τις πίστες
            return
        item = self.view.block_at(pos)
        if item:
            box = self.view.screen_rect(item.path)
            self.press = {"pos": pos, "path": item.path, "rect": box}

    def _motion(self, pos):
        if self.popup:
            self.popup.hover = self.popup.at(pos)
        if self.press and not self.drag:
            if math.hypot(pos[0] - self.press["pos"][0], pos[1] - self.press["pos"][1]) >= DRAG_START:
                self._start_drag()
        if self.drag:
            self._update_preview()

    def _start_drag(self):
        p = self.press
        grab = (p["pos"][0] - p["rect"].x, p["pos"][1] - p["rect"].y)
        if "template" in p:
            chunk, origin = [logic.clone(p["template"])], "palette"
        else:
            self._remember()
            chunk, origin = logic.take(self.program, p["path"]), "program"
            self._changed()
        self.drag = {"chunk": chunk, "grab": grab, "from": origin}
        self.press = None
        self.app.sounds.play("pick", 0.5)
        self._update_preview()

    def _drag_topleft(self):
        g = self.drag["grab"]
        return self.mouse[0] - g[0], self.mouse[1] - g[1]

    def _update_preview(self):
        chunk = self.drag["chunk"]
        if self.view.rect.collidepoint(self.mouse):
            self.view.set_program(self.program, extra=chunk)
            spot = self.view.nearest_spot(self.program, chunk, self._drag_topleft())
        else:
            spot = None
        if spot != self.preview:
            self.preview = spot
            if spot:
                trial = logic.clone(self.program)
                logic.insert(trial, spot[0], spot[1], chunk)
                self.view.set_program(trial)
            else:
                self.view.set_program(self.program)

    def _up(self, pos):
        for c in self.controls.values():
            if c.held:
                c.held = False
                c.flash_until = self.time + 0.12
        b, self.pressed_button = self.pressed_button, None
        if b:
            b.pressed = False
            if b.contains(pos) and b.enabled:
                self.app.sounds.play("button")
                b.action()
            return
        if self.press:                         # κλικ χωρίς σύρσιμο
            p, self.press = self.press, None
            if "template" in p:
                self.append(p["template"])
            return
        if self.drag:
            self._drop()

    def _drop(self):
        d, self.drag = self.drag, None
        spot, self.preview = self.preview, None
        chunk = d["chunk"]
        if spot and logic.can_insert(self.program, spot[0], spot[1], chunk, scripts=self.remote):
            if d["from"] == "palette":
                self._remember()                   # (από το πρόγραμμα: κρατήθηκε όταν σηκώθηκε)
            logic.insert(self.program, spot[0], spot[1], chunk)
            self._changed()
            path = spot[0] + (spot[1],)
            self.fresh = (path, self.time)
            self.app.sounds.play("place", 0.7)
            return
        if d["from"] == "program":
            self.app.sounds.play("remove", 0.7)    # αφέθηκε έξω: σβήνεται (όπως στο Mind+)
        self._changed()

    # ============================================================== χρόνος
    def update(self, dt):
        self.time += dt
        self.view.update(dt)
        a = self.anim
        if a:
            if self.busy and (a["kind"] in ("move", "turn", "wait") or (a["kind"] == "bump" and "t" in a)):
                self.sim_t = a["t"] + min(1.0, (self.time - a["start"]) / a["dur"])
            if self.time >= a["start"] + a["dur"]:
                self._finish(a)
        if self.next_map_at is not None and self.time >= self.next_map_at:
            self.next_map_at = None
            self.message = None
            self._start_round_map()
        self.confetti.update(dt, self.time, HEIGHT)
        self.sparkles = [(p, t) for p, t in self.sparkles if self.time - t < 0.8]
        self._sync_buttons()
        self._update_cursor()

    def _update_cursor(self):
        pos = self.mouse
        hand = (any(b.enabled and b.contains(pos) for b in self.active_buttons()) or self.dot_at(pos) is not None
                or any(c.rect.collidepoint(pos) for c in self.controls.values()))
        if not hand and not self.busy and not self.celebrated and self.palette is not None:
            hand = bool(self.palette.at(pos) or self.view.block_at(pos)) or self.drag is not None
        elif not hand and not self.busy and not self.celebrated and self.locked:
            hand = self.view.field_at(pos) is not None
        for b in self.active_buttons():
            b.hover = b.enabled and b.contains(pos)
        for c in self.controls.values():
            c.hover = c.rect.collidepoint(pos)
        want = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if want != self.cursor:
            self.cursor = want
            try:
                pygame.mouse.set_cursor(want)
            except (pygame.error, TypeError):
                pass

    # ========================================================== τι δείχνει
    def robot_pose(self):
        """(X, Y, hx, hy, κουτάκι για το βάθος, σπιν ροδών) του R2 αυτή τη στιγμή."""
        X, Y, ang, spin = self.rx, self.ry, self.angle, self.spin
        a = self.anim
        if a:
            t = ease((self.time - a["start"]) / a["dur"])
            if a["kind"] == "move":
                (x0, y0), (x1, y1) = cell_center(a["a"]), cell_center(a["b"])
                X, Y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                back = (x1 - x0) * math.cos(math.radians(ang)) + (y1 - y0) * math.sin(math.radians(ang)) < 0
                spin = self.spin + (t / lf.WHEEL_R) * (-1 if back else 1)
            elif a["kind"] == "turn":
                ang = a["a0"] + (a["a1"] - a["a0"]) * t
            elif a["kind"] == "bump":
                k = math.sin(min(1.0, (self.time - a["start"]) / a["dur"]) * math.pi)
                X, Y = X + a["dx"] * k, Y + a["dy"] * k
        r = math.radians(ang)
        return X, Y, math.cos(r), math.sin(r), self.tile, spin

    def bug_pose(self):
        w = self.world
        if not w.bug:
            return None
        t = self.sim_t
        k = math.floor(t)
        p0, p1 = w.bug_at(k), w.bug_at(k + 1)
        f = ease(t - k)
        (x0, y0), (x1, y1) = cell_center(p0), cell_center(p1)
        hx, hy = (x1 - x0, y1 - y0) if p0 != p1 else (0, 1)
        if p0 == p1 and k > 0:
            q = w.bug_at(k - 1)
            hx, hy = p0[0] - q[0], p0[1] - q[1]
        return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, hx, hy, max(p0, p1, key=depth_key), t * 2

    def box_pose(self):
        """(X, Y, κουτάκι για το βάθος, γύρισμα ροδών) της εργαλειοθήκης που κινείται, ή None."""
        w = self.world
        if not w.mover:
            return None
        t = self.sim_t
        k = math.floor(t)
        p0, p1 = w.mover_at(k), w.mover_at(k + 1)
        f = ease(t - k)
        (x0, y0), (x1, y1) = cell_center(p0), cell_center(p1)
        return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, max(p0, p1, key=depth_key), t if p0 != p1 else k

    def sensor_on(self):
        """Ο αισθητήρας απόστασης δουλεύει τώρα (περίμενε ώσπου / εάν);"""
        if not self.busy or self.running is None:
            return False
        node = self._node_at(self.running)
        return bool(node) and node["op"] in ("until", "if")

    # ============================================================== ζωγραφική
    def draw(self, screen):
        screen.blit(self.room, (0, 0))
        pose = self.robot_pose()
        led = self.led
        if self.failure and self.anim and self.anim["kind"] == "bump":
            led = "red"
        sensing = self.sensor_on()
        self.board.draw(screen, self.time, pose, led, self.bug_pose(), self.taken,
                        self.time * 1.4 if sensing else None, self.charging,
                        bridge=art.bridge_height(self.world, self.sim_t), box=self.box_pose())
        if self.bump:
            p, t = self.bump
            r2art.bump_stars(screen, p, self.time - t, self.board.g.tw * 0.9)
        for p, t in self.sparkles:
            art.sparkle(screen, p, (self.time - t) / 0.8)
        if sensing:
            cm = self.world.distance(self.cell, self._facing(), self.led, math.floor(self.sim_t))
            text = "απόσταση: " + ("πολύ μακριά" if cm >= logic.FAR_CM else f"{cm} cm")
            bubble(screen, [text], self.board.robot_top(pose[0], pose[1]), side="up", border=BLUE, size=17)
        self._draw_goals(screen)
        self._draw_panels(screen)
        self._draw_top(screen)
        self._draw_messages(screen, pose)
        if self.drag:
            code.draw_chunk(screen, self.view.st, self.drag["chunk"], self._drag_topleft(), lang=self.lang)
        if self.popup:
            self.popup.draw(screen)
        self.confetti.draw(screen)
        if self.celebrated:
            self._draw_banner(screen)

    def _facing(self):
        return round((self.angle + 90) / 90) % 4

    def _draw_goals(self, s):
        strip = pygame.Rect(WORLD.x + 14, WORLD.bottom - 58, WORLD.w - 28, 44)
        sh = pygame.Surface(strip.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (255, 255, 255, 228), sh.get_rect(), border_radius=22)
        s.blit(sh, strip)
        total = len(self.world.crystals)
        n = logic.count(self.program)
        limit = self.level["limit"]
        items = [(self.docked or self.celebrated, "Φορτιστής"),
                 (len(self.taken) == total and total > 0, f"Κρύσταλλοι {len(self.taken)}/{total}"),
                 (0 < n <= limit, f"Ως {limit} εντολ{'ή' if limit == 1 else 'ές'}")]
        if total == 0:
            items[1] = (True, "Χωρίς κρυστάλλους")
        w = strip.w / 3
        for i, (on, label) in enumerate(items):
            cx = strip.x + w * i + 26
            ui.star(s, (cx, strip.centery), 14, (252, 204, 60) if on else (214, 220, 230),
                    (170, 120, 20) if on else (170, 178, 192))
            ui.text(s, label, (cx + 22, strip.centery), 17, DARK if on else GREY, anchor="midleft")
            if i:
                pygame.draw.line(s, (226, 230, 238), (strip.x + w * i, strip.y + 8), (strip.x + w * i, strip.bottom - 8),
                                 2)

    def _draw_panels(self, s):
        p, c = self.panel, self.code_rect
        ui.panel(s, p, (255, 255, 255), radius=20, border=(206, 214, 228))
        if self.remote:
            ui.text(s, "Χειριστήριο", (p.x + 20, p.y + 24), 21, DARK, anchor="midleft")
            ui.text(s, "γκρι κουμπί: θέλει πρόγραμμα", (p.right - 20, p.y + 25), 15, LIGHT, anchor="midright",
                    bold=False)
            for ctl in self.controls.values():
                ctl.draw(s, self.time)
            q = self.pal_rect
            ui.panel(s, q, (255, 255, 255), radius=20, border=(206, 214, 228))
            ui.text(s, "Εντολές", (q.x + 20, q.y + 24), 21, DARK, anchor="midleft")
            ui.text(s, "σύρε μια εντολή στο πρόγραμμα", (q.right - 20, q.y + 25), 15, LIGHT, anchor="midright",
                    bold=False)
            self.palette.draw(s, dim=self.celebrated)
        elif self.mode == "see":
            ui.text(s, "Χειριστήριο", (p.x + 20, p.y + 24), 21, DARK, anchor="midleft")
            for ctl in self.controls.values():
                ctl.draw(s, self.time)
            if self.busy or self.drove_home or self.celebrated:
                veil = pygame.Surface((p.w - 8, p.h - 48), pygame.SRCALPHA)
                veil.fill((255, 255, 255, 150))
                s.blit(veil, (p.x + 4, p.y + 42))
        elif self.palette is None:
            ui.text(s, "Διόρθωσε το πρόγραμμα", (p.x + 20, p.y + 24), 21, DARK, anchor="midleft")
            ui.text(s, "Δεν χρειάζονται νέες εντολές. Πάτα σε μια λέξη (π.χ. «δεξιά»),", (p.x + 20, p.y + 54), 17,
                    GREY, anchor="midleft", bold=False)
            ui.text(s, "σε έναν αριθμό ή σε ένα χρώμα στο πρόγραμμα και άλλαξέ τα.", (p.x + 20, p.y + 76), 17, GREY,
                    anchor="midleft", bold=False)
        else:
            ui.text(s, "Εντολές", (p.x + 20, p.y + 24), 21, DARK, anchor="midleft")
            ui.text(s, "σύρε μια εντολή στο πρόγραμμα", (p.right - 20, p.y + 25), 15, LIGHT, anchor="midright",
                    bold=False)
            self.palette.draw(s, dim=self.busy or self.celebrated)
        ui.panel(s, c, (255, 255, 255), radius=20, border=(206, 214, 228))
        n = logic.count(self.program)
        count_text = f"{n} εντολ{'ή' if n == 1 else 'ές'}"
        count_col = RED if n > self.level["limit"] else GREY
        if self.remote:                       # χωρίς «Πάμε!»: τίτλος και πλήθος σε μία γραμμή
            ui.text(s, "Το πρόγραμμα", (c.x + 20, c.y + 24), 21, DARK, anchor="midleft")
            ui.text(s, count_text, (c.right - 20, c.y + 25), 18, count_col, anchor="midright")
        else:
            head_y = self.btn_run.rect.centery
            ui.text(s, "Το πρόγραμμα", (c.right - 20, head_y - 13), 21, DARK, anchor="midright")
            ui.text(s, count_text, (c.right - 20, head_y + 15), 18, count_col, anchor="midright")
        fresh, alpha = None, 0
        if self.fresh:
            path, t = self.fresh
            if self.time - t < FRESH_TIME:
                fresh, alpha = path, 255 * (1 - (self.time - t) / FRESH_TIME)
        ghosts = {id(n) for chunk in ([self.drag["chunk"]] if self.drag and self.preview else [])
                  for _, n in logic.walk(chunk)}
        error = self.red_block()
        self.view.draw(s, self.running, error, fresh, alpha, ghosts, self.badges)
        if self.answer and self.busy:
            path, word = self.answer
            box = self.view.screen_rect(path)
            if box and self.running == path:
                chip = pygame.Rect(box.right + 6, box.centery - 12, 58, 24)
                col = (52, 160, 80) if word == "ΝΑΙ" else (200, 80, 80)
                pygame.draw.rect(s, col, chip, border_radius=12)
                ui.text(s, word, chip.center, 15, (255, 255, 255))
        if not self.program and not self.drag:
            r = self.view.rect
            lines = (["Οδήγησε το R2 με τα κουμπιά:", "εδώ θα γραφτούν οι εντολές."] if self.mode == "see" else
                     ["Σύρε εδώ το «όταν πατηθεί πλήκτρο»", "και βάλε από κάτω του μια εντολή."] if self.remote else
                     ["Σύρε εντολές εδώ, κάτω από το «R2 starts»,", "ή πάτα τες στις Εντολές."])
            flash = self.time - self.empty_flash < 1.5
            for i, t in enumerate(lines):
                ui.text(s, t, (r.centerx, r.centery + 10 + i * 24), 19 if flash else 17, BLUE if flash else LIGHT,
                        bold=flash)
        if self.mode != "see":
            self.btn_undo.draw(s, self.time)
            if not self.locked:
                self.btn_trash.draw(s, self.time)
        if not self.celebrated and not self.remote:
            self.btn_run.draw(s, self.time)

    def _draw_top(self, s):
        s.blit(self.top_bar, (0, 0))
        pygame.draw.line(s, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)
        done = self.app.progress.completed(GAME_ID)
        for i, (x, y) in enumerate(self.dots_xy):
            col = MODES[levels.LEVELS[i]["mode"]][1]
            if i == self.index:
                ui.circle(s, col, (x, y), 15)
                ui.text(s, str(i + 1), (x, y), 15, (255, 255, 255))
            elif (i + 1) in done:
                ui.circle(s, (250, 200, 60), (x, y), 12, ui.shade((250, 200, 60), 0.7))
                ui.text(s, str(i + 1), (x, y), 13, (255, 255, 255))
            else:
                ui.circle(s, ui.mix(col, (255, 255, 255), 0.5), (x, y), 12)
                ui.circle(s, (246, 248, 252), (x, y), 9.5)
                ui.text(s, str(i + 1), (x, y), 13, ui.shade(col, 0.8))
        name, col = MODES[self.mode]
        text = self.level["title"]
        chip_w = ui.font(16).size(name)[0] + 24
        tw = ui.font(20).size(text)[0]
        x0 = CENTER_X - (chip_w + 10 + tw) / 2
        chip = pygame.Rect(round(x0), 58, chip_w, 26)
        pygame.draw.rect(s, col, chip, border_radius=13)
        ui.text(s, name, chip.center, 16, (255, 255, 255))
        ui.text(s, text, (chip.right + 10, 71), 20, DARK, anchor="midleft")
        for b in (self.btn_again, self.btn_next, self.btn_sound, self.btn_menu):
            b.draw(s, self.time)

    def _draw_messages(self, s, pose):
        if self.failure and not self.busy and not self.celebrated:
            why = self.failure[1]
            path = self.red_block()
            lines = list(WHY[why])
            found = self.culprit
            if found and not (why == "door" and found[1] == "color"):
                lines.append(HINTS.get((logic.get(self.program, found[0])["op"], found[1]), ""))
            box = self.view.screen_rect(path) if path else None
            r = self.view.rect
            if box and r.colliderect(box):
                anchor = (box.x + 8, box.centery + 2)
            else:                                   # χωρίς μπλοκ: στο τέλος του προγράμματος
                anchor = (r.x + 16, min(r.bottom - 20, max(r.y + 24, self.view.end_y())))
            bubble(s, [t for t in lines if t], anchor, side="left", size=18)
        if self.message:
            lines, t, col = self.message
            if self.time - t < (6 if col == BLUE else 2.2) or (self.drove_home and not self.busy):
                bubble(s, lines, self.board.robot_top(pose[0], pose[1]), side="up", border=col, size=18)
            else:
                self.message = None

    def _draw_banner(self, s):
        card = pygame.Rect(0, 0, 540, 330)
        card.center = (WORLD.centerx, WORLD.centery - 40)
        ui.panel(s, card, (255, 252, 240), radius=28, border=(250, 190, 50))
        got = sum(self.stars)
        for i, dx in enumerate((-80, 0, 80)):
            on = i < got
            ui.star(s, (card.centerx + dx, card.y + 52 - (10 if i == 1 else 0)), 30 if i == 1 else 24,
                    (252, 204, 60) if on else (222, 226, 234), (170, 120, 20) if on else (180, 186, 198))
        ui.text(s, "Μπράβο!", (card.centerx, card.y + 120), 56, (236, 118, 30), shadow=(250, 214, 150))
        for i, (on, line) in enumerate(zip(self.stars, self.star_lines)):
            y = card.y + 178 + i * 36
            ui.star(s, (card.x + 62, y), 13, (252, 204, 60) if on else (214, 220, 230),
                    (170, 120, 20) if on else (170, 178, 192))
            ui.text(s, line, (card.x + 86, y), 21, DARK if on else GREY, anchor="midleft")
        self.btn_retry.rect.topleft = (card.centerx - 170, card.bottom + 18)
        self.btn_go.rect.topleft = (card.centerx, card.bottom + 18)
        self.btn_retry.draw(s, self.time)
        self.btn_go.draw(s, self.time)
