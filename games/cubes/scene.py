"""Κύβοι: χτίσε στον τοίχο το σχέδιο του τετραδίου. Το παιδί διαλέγει κύβο και στήλη,
και το R2, που κινείται σε μια ράγα πάνω από τον τοίχο, πηγαίνει τον κύβο εκεί και τον σπρώχνει μέσα."""
import math

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.maze import art as r2art           # ο φορτιστής και τα χρώματα του LED
from . import GAME_ID, art, logic, patterns
from .robot import Carrier

CUBE = 40                       # μέγεθος κύβου στον τοίχο
WALL = pygame.Rect(632, 166, logic.COLS * CUBE, logic.MAX_HALVES // 2 * CUBE)
NOTE = pygame.Rect(36, 106, 360, 476)
TRAY = pygame.Rect(430, 596, 836, 116)
SLOT_W, TRAY_CUBE = 76, 46
TOP_H = 92
CENTER_X = 714
GRAVITY = 2600

R2_SIZE = 64
RAIL_Y = WALL.y - 14            # η πάνω πλευρά της ράγας: εκεί πατάει η ρόδα του R2
ARM = 34                        # από το κέντρο του R2 ως τον κύβο που κρατά μπροστά του
HANG_TOP = RAIL_Y - 30          # η πάνω μπροστινή ακμή του κύβου που κρατά
PUSH_DIST = 10                  # πόσο σπρώχνει τον κύβο κάτω πριν τον αφήσει
PUSH_SPEED = 180                # με τι ταχύτητα φεύγει ο κύβος όταν τον αφήνει
DOCK_X = WALL.x - ARM - 76      # το R2 στον φορτιστή, στην αριστερή άκρη της ράγας
CHARGER = pygame.Rect(0, 0, 50, 50)
CHARGER.bottomright = (round(DOCK_X - R2_SIZE * 0.45) - 3, RAIL_Y)
RAIL_LEFT, RAIL_RIGHT = CHARGER.x - 12, WALL.right + 34
CELEBRATE_AFTER = 0.4           # πότε αρχίζει η γιορτή, αφού φτάσει το R2 στον φορτιστή
RED_TIME = 0.7                  # πόσο μένει κόκκινο το LED όταν η στήλη είναι γεμάτη

MSG = {
    "build": "Διάλεξε κύβο και πάτα στήλη: το R2 θα τον πάει εκεί!",
    "free": "Ελεύθερο παιχνίδι: φτιάξε ό,τι θέλεις!",
    "full": "Αυτή η στήλη γέμισε!",
    "win": "Μπράβο! Το σχέδιο είναι ίδιο!",
}


def pop(t):
    """Από 0 σε 1 με ένα μικρό «φούσκωμα» στο τέλος."""
    t = max(0.0, min(1.0, t)) - 1
    return 1 + 2.7 * t ** 3 + 1.7 * t ** 2


def banner_charger(surf, c):
    r2art.charger(surf, (c[0] - 32, c[1] - 32, 64, 64))


def stop_x(col):
    """Πού σταματά το R2 για να είναι ο κύβος που κρατά ακριβώς πάνω από τη στήλη col."""
    return WALL.x + col * CUBE - ARM


class CubesScene(Scene):
    def __init__(self, app, index=0):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed_button = None
        self.confetti = fx.Confetti()
        self.banner = fx.Banner("Μπράβο!", "Το σχέδιο είναι ίδιο!", icon=banner_charger)
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 215))
        self.rooms = {}
        self.carrier = Carrier(DOCK_X, wheel_r=R2_SIZE * 0.22)
        self._make_buttons()
        self.load(index)

    # ------------------------------------------------------------- setup
    def _make_buttons(self):
        B = ui.Button
        self.btn_undo = B((14, 8, 100, 76), "Αναίρεση", ui.icon_undo, (238, 146, 46), self.undo)
        self.btn_clear = B((124, 8, 104, 76), "Καθάρισε", ui.icon_close, (226, 96, 96), self.clear)
        self.btn_next = B((238, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_pattern)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        self.btn_free = B((NOTE.centerx - 56, 600, 112, 88), "Ελεύθερο", ui.icon_star, (84, 172, 96),
                          lambda: self.load(None))
        self.btn_cubes = B((TRAY.right - 112, TRAY.y + 10, 100, TRAY.h - 22), "Άλλοι", self._icon_more,
                           (150, 104, 206), self.other_cubes)
        self.buttons = [self.btn_undo, self.btn_clear, self.btn_next, self.btn_sound, self.btn_menu,
                        self.btn_free, self.btn_cubes]

    @staticmethod
    def _icon_more(surf, c, s, col):
        art.draw_cube(surf, 1, c[0] - s * 0.46, c[1] + s * 0.32, s * 0.42)
        art.draw_cube(surf, 13, c[0] - s * 0.02, c[1] + s * 0.32, s * 0.42)
        art.draw_cube(surf, 9, c[0] - s * 0.24, c[1] - s * 0.1, s * 0.42)

    def load(self, index):
        """Ανοίγει ένα σχέδιο του τετραδίου (index) ή ελεύθερο παιχνίδι (None)."""
        all_patterns = patterns.BUILT_IN
        self.free = index is None
        self.index = None if self.free else index % len(all_patterns)
        self.pattern = None if self.free else all_patterns[self.index]
        self.wall = logic.Wall()
        self.falling = {}
        self.selected = None
        self.hold = None
        self.matched = False
        self.carrier.place(DOCK_X)
        self.charge_time = None         # πότε έφτασε το R2 στον φορτιστή
        self.celebrated = False
        self.bump_time = -9.0           # πότε πατήθηκε γεμάτη στήλη (κόκκινο LED, το R2 κουνιέται)
        self.grip_type = None           # ο κύβος που φαίνεται στη βεντούζα του R2
        self.grip_time = 0.0
        if self.free:
            first = list(logic.FULL_CUBES)
        else:
            first = patterns.cubes_for(self.pattern, self.index + 1)
        self.sets = [first] + [list(s) for s in (logic.FULL_CUBES, logic.HALF_CUBES) if list(s) != first]
        self.set_index = 0
        self.motif = art.MOTIFS[(self.index or 0) % len(art.MOTIFS)] if not self.free else "star"
        self.note = self._notebook()
        self.message = MSG["free" if self.free else "build"]
        self.confetti.clear()
        self.banner.hide()

    def _notebook(self):
        title = "Ελεύθερο παιχνίδι" if self.free else "Φτιάξε αυτό!"
        return art.build_notebook(NOTE, self.pattern, title)

    def _room(self):
        if self.motif not in self.rooms:
            room = art.build_room((WIDTH, HEIGHT), WALL, CUBE, self.motif)
            art.draw_rail(room, RAIL_LEFT, RAIL_RIGHT, RAIL_Y, (WALL.x - 14, WALL.y + 44))
            self.rooms[self.motif] = room
        return self.rooms[self.motif]

    @property
    def palette(self):
        return self.sets[self.set_index]

    def slot_rects(self):
        n = len(self.palette)
        area_w = self.btn_cubes.rect.x - TRAY.x - 16
        x0 = TRAY.x + 10 + (area_w - n * SLOT_W) // 2
        return [pygame.Rect(x0 + i * SLOT_W, TRAY.y + 10, SLOT_W - 8, TRAY.h - 22) for i in range(n)]

    # ------------------------------------------------------------ actions
    def drop(self, col, ctype):
        """Ο κύβος γράφεται αμέσως στον τοίχο, αλλά φαίνεται εκεί μόνο όταν τον αφήσει το R2."""
        if not self.wall.drop(col, ctype):
            self.app.sounds.play("deny", 0.6)
            self.message = MSG["full"]
            self.bump_time = self.time
            return
        self.carrier.carry(stop_x(col), col, len(self.wall.columns[col]) - 1, ctype)
        self.carrier.park_x = None          # αν φόρτιζε, φεύγει από τον φορτιστή
        self.charge_time = None
        self._after_change()

    def _removed(self, col):
        """Ο πάνω κύβος της στήλης col μόλις βγήκε: σταμάτα την πτώση του ή πάρ' τον από το R2."""
        n = len(self.wall.columns[col])
        self.falling.pop((col, n), None)
        self.carrier.cancel(col, n)

    def undo(self):
        done = self.wall.undo()
        if not done:
            self.app.sounds.play("deny", 0.6)
            return
        self._removed(done[0])
        self.app.sounds.play("pick")
        self._after_change()

    def take_top(self, col):
        ctype = self.wall.take_top(col)
        if ctype is None:
            return None
        self._removed(col)
        self.app.sounds.play("pick")
        self._after_change()
        return ctype

    def clear(self):
        if self.wall.empty:
            return
        self.wall.clear()
        self.falling.clear()
        self.carrier.clear()
        self.app.sounds.play("swoosh", 0.7)
        self._after_change()

    def next_pattern(self):
        self.app.sounds.play("swoosh", 0.7)
        self.load(0 if self.free else self.index + 1)

    def other_cubes(self):
        self.set_index = (self.set_index + 1) % len(self.sets)
        if self.selected not in self.palette:
            self.selected = None

    def to_menu(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def _after_change(self):
        """Μετά από κάθε αλλαγή στον τοίχο: ταιριάζει πια με το σχέδιο;
        Περιμένει ώσπου το R2 να αφήσει όλους τους κύβους και να πέσουν."""
        if self.falling or self.carrier.busy:
            return
        now = not self.free and logic.matches(self.wall.columns, self.pattern.columns)
        if now and not self.matched:
            self.message = MSG["win"]
            self.celebrated = False
            self.app.progress.mark(GAME_ID, self.index + 1)
        elif not now and self.message in (MSG["win"], MSG["full"]):
            self.message = MSG["free" if self.free else "build"]
        if not now:
            self.charge_time = None
        self.matched = now
        self.carrier.park_x = DOCK_X if now else None    # μόλις ταιριάξει, το R2 πάει να φορτίσει

    def _land(self, job):
        """Το R2 άφησε τον κύβο: από εδώ και πέρα πέφτει μόνος του."""
        col, n, ctype = job["col"], job["n"], job["ctype"]
        below = sum(logic.CUBES[t].halves for t in self.wall.columns[col][:n])
        final_bottom = WALL.bottom - below * CUBE / 2
        released = HANG_TOP + PUSH_DIST + logic.CUBES[ctype].halves * CUBE / 2
        self.falling[(col, n)] = [max(0.0, final_bottom - released), PUSH_SPEED]
        self.grip_time = self.time          # ο επόμενος κύβος «σκάει» στη βεντούζα

    # -------------------------------------------------------------- input
    def column_at(self, pos):
        x, y = pos
        if WALL.x <= x < WALL.right and HANG_TOP - 20 <= y <= WALL.bottom + 6:
            return int((x - WALL.x) // CUBE)
        return None

    def top_cube_rect(self, col):
        column = self.wall.columns[col]
        if not column:
            return None
        h = self.wall.height(col)
        size = logic.CUBES[column[-1]].halves * CUBE / 2
        return pygame.Rect(WALL.x + col * CUBE, WALL.bottom - h * CUBE / 2 - CUBE * 0.35,
                           CUBE * 1.35, size + CUBE * 0.35)

    def slot_at(self, pos):
        for ctype, r in zip(self.palette, self.slot_rects()):
            if r.collidepoint(pos):
                return ctype
        return None

    def dots(self):
        n = len(patterns.BUILT_IN)
        step = min(30, 640 / max(1, n))
        x0 = CENTER_X - (n - 1) * step / 2
        return [(x0 + i * step, 30) for i in range(n)]

    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots()):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 14 ** 2:
                return i
        return None

    def visible_buttons(self):
        hidden = set()
        if len(self.sets) < 2:
            hidden.add(self.btn_cubes)
        return [b for b in self.buttons if b not in hidden]

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            if self.hold and not self.hold["active"]:
                sx, sy = self.hold["start"]
                if (e.pos[0] - sx) ** 2 + (e.pos[1] - sy) ** 2 > 64:
                    self.hold["active"] = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self._mouse_down(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse = e.pos
            self._mouse_up(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            col = self.column_at(e.pos)
            if col is not None and self.wall.columns[col]:
                self.take_top(col)
            else:
                self.selected = None
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.to_menu()
            elif e.key == pygame.K_BACKSPACE or (e.key == pygame.K_z and e.mod & pygame.KMOD_CTRL):
                self.undo()
            elif e.key == pygame.K_n:
                self.next_pattern()
            elif e.key == pygame.K_m:
                self.app.sounds.toggle()
            elif pygame.K_1 <= e.key <= pygame.K_9 and e.key - pygame.K_1 < len(self.palette):
                self.selected = self.palette[e.key - pygame.K_1]
                self.app.sounds.play("select")

    def _mouse_down(self, pos):
        for b in self.visible_buttons():
            if b.enabled and b.contains(pos):
                b.pressed = True
                self.pressed_button = b
                return
        dot = self.dot_at(pos)
        if dot is not None:
            self.app.sounds.play("swoosh", 0.7)
            self.load(dot)
            return
        ctype = self.slot_at(pos)
        if ctype is not None:
            if self.selected != ctype:
                self.app.sounds.play("select")
            self.selected = ctype
            self.hold = {"type": ctype, "start": pos, "active": False}
            return
        col = self.column_at(pos)
        if col is not None:
            if self.selected is not None:
                self.drop(col, self.selected)
            else:
                rect = self.top_cube_rect(col)
                if rect and rect.collidepoint(pos):
                    self.selected = self.take_top(col)
            return
        if not TRAY.collidepoint(pos):
            self.selected = None

    def _mouse_up(self, pos):
        b, self.pressed_button = self.pressed_button, None
        if b:
            b.pressed = False
            if b.contains(pos) and b.enabled:
                self.app.sounds.play("button")
                b.action()
            return
        hold, self.hold = self.hold, None
        if hold and hold["active"]:
            col = self.column_at(pos)
            if col is not None:
                self.drop(col, hold["type"])

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        self.btn_undo.enabled = not self.wall.empty
        self.btn_clear.enabled = not self.wall.empty
        self.btn_next.pulse = self.matched and not self.free
        for b in self.buttons:
            b.hover = b.contains(self.mouse)
        for ev in self.carrier.update(dt):
            if ev[0] == "drive":
                self.app.sounds.play("motor", 0.3)
            elif ev[0] == "drop":
                self._land(ev[1])
            elif ev[0] == "park" and self.matched:
                self.charge_time = self.time
                self.app.sounds.play("charge", 0.7)
        landed = False
        for key, fall in list(self.falling.items()):
            fall[1] += GRAVITY * dt
            fall[0] -= fall[1] * dt
            if fall[0] <= 0:
                del self.falling[key]
                landed = True
        if landed:
            self.app.sounds.play("thud", 0.6)
            self._after_change()
        if self.charge_time is not None and not self.celebrated and self.time >= self.charge_time + CELEBRATE_AFTER:
            self.celebrated = True
            self.app.sounds.play("win", 0.9)
            self.confetti.burst(WIDTH)
            self.banner.show(self.time)
        grip = self._grip_type()
        if grip != self.grip_type:
            self.grip_type = grip
            self.grip_time = self.time
        self.confetti.update(dt, self.time, HEIGHT)
        self._update_cursor()

    def _update_cursor(self):
        pos = self.mouse
        hand = (any(b.enabled and b.contains(pos) for b in self.visible_buttons())
                or self.dot_at(pos) is not None or self.slot_at(pos) is not None)
        col = self.column_at(pos)
        if not hand and col is not None:
            rect = self.top_cube_rect(col)
            hand = self.selected is not None or bool(rect and rect.collidepoint(pos))
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # --------------------------------------------------------------- draw
    def _draw_wall(self, screen):
        waiting = {(job["col"], job["n"]) for job in self.carrier.jobs}
        for col, column in enumerate(self.wall.columns):
            bottom = WALL.bottom
            for i, ctype in enumerate(column):
                if (col, i) in waiting:                   # το κρατάει ακόμα το R2
                    break
                offset = self.falling.get((col, i), (0.0,))[0]
                art.draw_cube(screen, ctype, WALL.x + col * CUBE, bottom - offset, CUBE)
                bottom -= logic.CUBES[ctype].halves * CUBE / 2

    def _held_type(self):
        if self.hold and self.hold["active"]:
            return self.hold["type"]
        return self.selected

    def _grip_type(self):
        """Ποιος κύβος φαίνεται στη βεντούζα: αυτός που πηγαίνει τώρα, αλλιώς ο διαλεγμένος."""
        job = self.carrier.carrying
        if job:
            return job["ctype"]
        if self.hold and self.hold["active"]:
            return None                                   # τον σέρνει το παιδί με το ποντίκι
        return self.selected

    def _led(self):
        if self.charge_time is not None and self.carrier.parked:
            return r2art.LED_GREEN
        if self.time < self.bump_time + RED_TIME:
            return r2art.LED_RED
        return r2art.LED_BLUE

    def _draw_r2(self, screen):
        charging = self.charge_time is not None and self.carrier.parked
        r2art.charger(screen, CHARGER, self.time, charging)
        x = self.carrier.x
        age = self.time - self.bump_time
        if age < 0.45:                                    # «όχι»: κουνιέται πέρα-δώθε
            x += 3 * math.sin(age * 45) * (1 - age / 0.45)
        if charging:
            r2art.charge_rings(screen, (x, RAIL_Y - R2_SIZE / 2), self.time, R2_SIZE)
        art.draw_carrier(screen, x, RAIL_Y, R2_SIZE, ARM, HANG_TOP, CUBE, ctype=self.grip_type,
                         push=self.carrier.push, push_dist=PUSH_DIST, spin=self.carrier.spin,
                         led=self._led(), cube_scale=pop((self.time - self.grip_time) / 0.2))

    def _draw_held(self, screen):
        ctype = self._held_type()
        if ctype is None:
            return
        col = self.column_at(self.mouse)
        if col is not None:
            x = WALL.x + col * CUBE
            if self.wall.fits(col, ctype):
                landing = WALL.bottom - self.wall.height(col) * CUBE / 2
                art.draw_cube(screen, ctype, x, landing, CUBE, alpha=90, outline=False)
                pygame.draw.line(screen, (255, 190, 40), (x + CUBE / 2, WALL.y + 2), (x + CUBE / 2, landing - 4), 1)
            if self.hold and self.hold["active"]:
                art.draw_cube(screen, ctype, self.mouse[0] + 14, self.mouse[1] + 40, 30)
        elif self.hold and self.hold["active"] or not TRAY.collidepoint(self.mouse):
            art.draw_cube(screen, ctype, self.mouse[0] + 14, self.mouse[1] + 40, 30)

    def _draw_top(self, screen):
        screen.blit(self.top_bar, (0, 0))
        pygame.draw.line(screen, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)
        done = self.app.progress.completed(GAME_ID)
        for i, (x, y) in enumerate(self.dots()):
            current = i == self.index
            r = 14 if current else 11
            if current:
                ui.circle(screen, (62, 132, 222), (x, y), r + 3)
                ui.circle(screen, (255, 255, 255), (x, y), r + 1)
            if i + 1 in done:
                fill = (250, 200, 60)
            else:
                fill = (62, 132, 222) if current else (226, 230, 238)
            ui.circle(screen, fill, (x, y), r, ui.shade(fill, 0.7))
            fg = (110, 118, 132) if fill == (226, 230, 238) else (255, 255, 255)
            ui.text(screen, str(i + 1), (x, y), 15 if current else 13, fg)
        ui.text(screen, self.message, (CENTER_X, 69), 21, (44, 54, 76))

    def _draw_tray(self, screen):
        ui.panel(screen, TRAY, (198, 152, 100), radius=22, border=(150, 106, 64))
        held = self._held_type()
        for i, (ctype, r) in enumerate(zip(self.palette, self.slot_rects())):
            sel = ctype == held
            hover = r.collidepoint(self.mouse)
            rr = r.move(0, -6 if sel else (-2 if hover else 0))
            pygame.draw.rect(screen, (255, 238, 160) if sel else (228, 194, 146), rr, border_radius=14)
            pygame.draw.rect(screen, (255, 186, 40) if sel else (176, 132, 86), rr, 4 if sel else 2, border_radius=14)
            h = logic.CUBES[ctype].halves * TRAY_CUBE / 2
            x = rr.centerx - TRAY_CUBE * 0.68
            bottom = rr.centery + h / 2 + TRAY_CUBE * 0.17
            art.draw_cube(screen, ctype, x, bottom, TRAY_CUBE)
            if i < 9:
                ui.text(screen, str(i + 1), (rr.x + 11, rr.y + 12), 13, (150, 110, 70))

    def draw(self, screen):
        screen.blit(self._room(), (0, 0))
        screen.blit(self.note, NOTE)
        if self.matched:
            ui.star(screen, (NOTE.right - 38, NOTE.y + 44), 30 + 3 * math.sin(self.time * 4), (252, 204, 60))
        self._draw_wall(screen)
        self._draw_r2(screen)
        self._draw_tray(screen)
        self._draw_top(screen)
        for b in self.visible_buttons():
            b.draw(screen, self.time)
        self._draw_held(screen)
        self.confetti.draw(screen)
        self.banner.draw(screen, self.time, (WALL.centerx, WALL.centery - 40))
