"""Ακολούθησε: φτιάξε τη μαύρη γραμμή ώστε το R2 να φτάσει στον φορτιστή.

Οι κανόνες είναι στο logic.py και τα επίπεδα στο levels.py.
"""
import math
import random

import pygame
import pygame.gfxdraw

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.maze import art as r2
from . import GAME_ID, art, logic
from .levels import LEVELS

AUTO_START = 0.5            # δευτερόλεπτα από το πράσινο φανάρι ως το ξεκίνημα του R2
BOARD_ORIGIN = (480, 152)
TOP_H = 92
TRAY_RECT = pygame.Rect(110, 548, 1060, 162)
SLOT_W, SLOT_GAP = 160, 15
CENTER_X = 720

MSG = {
    "build0": "Φτιάξε τη μαύρη γραμμή από το R2 ως τον φορτιστή!",
    "build1": "Φτιάξε τη γραμμή. Πάτα «Ξεκίνα» όποτε θες να δοκιμάσεις!",
    "ready": "Η γραμμή είναι έτοιμη! Πάτα «Ξεκίνα»!",
    "run": "Το R2 ακολουθεί τη μαύρη γραμμή...",
    "turn": "Ωχ! Η γραμμή τελειώνει. Το R2 γυρίζει πίσω.",
    "home": "Το R2 γύρισε. Διόρθωσε τη γραμμή και ξαναδοκίμασε!",
    "arrived": "Μπράβο! Το R2 έφτασε στον φορτιστή!",
    "gears": "Η γραμμή φτάνει, αλλά δεν περνά από όλα τα γρανάζια!",
    "barrier": "Η μπάρα είναι κλειστή: λείπουν γρανάζια! Το R2 γυρίζει πίσω.",
}
GEAR_Z = art.PIECE_Z + 32       # πόσο ψηλά αιωρούνται τα γρανάζια
GEAR_R = 18
COLLECT_TIME = 0.6             # πόσο κρατά το εφέ όταν το R2 μαζεύει ένα γρανάζι
BARRIER_TIME = 0.5             # πόσο κάνει η μπάρα να ανοίξει


class LineFollowScene(Scene):
    def __init__(self, app, level=0):
        super().__init__(app)
        self.geo = art.Geo(*BOARD_ORIGIN)
        self.assets = art.get_assets(self.geo, (WIDTH, HEIGHT))
        self.time = 0.0
        self.mouse = (0, 0)
        self.confetti = fx.Confetti()
        self.banner = fx.Banner("Μπράβο!", "Το R2 έφτασε στον φορτιστή!")
        self.robot_pos = None
        self.pressed_button = None
        self.cursor = None
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 215))
        self.slots = [pygame.Rect(TRAY_RECT.x + 12 + i * (SLOT_W + SLOT_GAP), TRAY_RECT.y + 14, SLOT_W, TRAY_RECT.h - 26)
                      for i in range(len(logic.PIECE_TYPES))]
        self.dots = [(CENTER_X - (len(LEVELS) - 1) * 16 + i * 32, 30) for i in range(len(LEVELS))]
        self._make_buttons()
        self.load_level(level)

    # ------------------------------------------------------------- setup
    def _make_buttons(self):
        B = ui.Button
        self.btn_go = B((14, 8, 124, 76), "Ξεκίνα", ui.icon_play, (60, 172, 84), self.start_robot)
        self.btn_again = B((148, 8, 92, 76), "Ξανά", ui.icon_again, (238, 146, 46), self.restart)
        self.btn_next = B((250, 8, 100, 76), "Επόμενο", ui.icon_next, (62, 132, 222), self.next_level)
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.toggle_sound)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού",
                          lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84)),
                          (224, 84, 84), self.to_menu)
        self.buttons = [self.btn_go, self.btn_again, self.btn_next, self.btn_sound, self.btn_menu]

    def load_level(self, index):
        self.level_index = index % len(LEVELS)
        self.level = level = LEVELS[self.level_index]
        self.mode = level.mode
        self.board = level.board()
        self.counts = dict(zip(logic.PIECE_TYPES, level.pieces))
        self.robot = logic.Robot()
        self.selected = None
        self.hold = None
        self.complete = False
        self.locked = False
        self.arrived = False
        self.auto_timer = None
        self.motor_timer = 0.0
        self.win_timer = None
        self.wheel_spin = [0.0, 0.0]        # πόσο έχει γυρίσει η αριστερή και η δεξιά ρόδα (ακτίνια)
        self.last_pose = self.robot.pose()
        self.banner.hide()
        self.confetti.clear()
        if level.kinds:
            self.scenery = dict(zip(level.blocked, level.kinds))
        else:
            rng = random.Random(self.level_index * 31 + 5)
            self.scenery = {cell: rng.choice(art.BLOCK_KINDS) for cell in sorted(level.blocked)}
        self.river = art.get_river(self.geo, (WIDTH, HEIGHT), level.water) if level.water else None
        self.ripple_cells = [cell for cell in level.water if cell not in self.board.fixed]
        self.gear_fx = {}          # γρανάζι -> πότε το μάζεψε το R2 (για το εφέ)
        self.gear_back = {}        # γρανάζι -> πότε ξαναμπήκε στη θέση του
        self.barrier_open = 0.0
        self.build_msg = level.hint or MSG["build0" if self.mode == 0 else "build1"]
        self.message = self.build_msg
        self.layer = None

    # ------------------------------------------------------------ actions
    def go_enabled(self):
        return self.robot.state == "idle" and not self.arrived and (self.mode == 1 or self.complete)

    def start_robot(self):
        if not self.go_enabled():
            return
        self._drop_hold_to_tray()
        self.robot.start()
        self.auto_timer = None
        self.motor_timer = 0.34
        self.message = MSG["run"]
        self.app.sounds.play("motor", 0.8)

    def restart(self):
        self.load_level(self.level_index)

    def next_level(self):
        self.load_level(self.level_index + 1)

    def toggle_sound(self):
        self.app.sounds.toggle()

    def to_menu(self):
        from games.menu import MenuScene
        self._set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        self.app.switch(MenuScene(self.app))

    def check_path(self):
        was = self.complete
        reached, visited = self.board.trace()
        self.complete = reached and not self.board.missing_gears(visited)
        if self.robot.state != "idle" or self.arrived:
            return
        if self.complete:
            self.auto_timer = AUTO_START
            if self.mode == 0 and not self.locked:
                self.locked = True
                self.selected = None
                self.app.sounds.play("complete", 0.8)
            if not was or self.message in (MSG["home"], MSG["gears"], self.build_msg):
                self.message = MSG["ready"]
        else:
            self.auto_timer = None
            if reached:
                self.message = MSG["gears"]
            elif self.message in (MSG["ready"], MSG["gears"]):
                self.message = self.build_msg

    def can_place(self, cell):
        return (self.board.free(cell) and not self.locked
                and not self.arrived and cell not in self.robot.occupied())

    def place(self, cell, ptype):
        old = self.board.pieces.get(cell)
        if old:
            self.counts[old] += 1
        self.board.place(cell, ptype)
        self.counts[ptype] -= 1
        if self.counts[ptype] == 0 and self.selected == ptype:
            self.selected = None
        self.app.sounds.play("place")
        self.layer = None
        self.check_path()

    def _drop_hold_to_tray(self):
        if self.hold and self.hold["src"] == "board":
            self.counts[self.hold["type"]] += 1
            self.layer = None
        self.hold = None

    # -------------------------------------------------------------- input
    def cell_at(self, pos):
        X, Y = self.geo.world_at(pos[0], pos[1], 13)
        return (math.floor(X), math.floor(Y))

    def slot_at(self, pos):
        for i, r in enumerate(self.slots):
            if r.collidepoint(pos):
                return logic.PIECE_TYPES[i]
        return None

    def dot_at(self, pos):
        for i, (x, y) in enumerate(self.dots):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 15 ** 2:
                return i
        return None

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
            cell = self.cell_at(e.pos)
            if cell in self.board.pieces and self.can_place(cell):
                self.counts[self.board.remove(cell)] += 1
                self.app.sounds.play("remove")
                self.layer = None
                self.check_path()
            else:
                self.selected = None
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.to_menu()
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.start_robot()
            elif e.key == pygame.K_r:
                self.restart()
            elif e.key == pygame.K_n:
                self.next_level()
            elif e.key == pygame.K_m:
                self.toggle_sound()

    def _mouse_down(self, pos):
        if self.auto_timer is not None:
            self.auto_timer = AUTO_START
        for b in self.buttons:
            if b.enabled and b.contains(pos):
                b.pressed = True
                self.pressed_button = b
                return
        dot = self.dot_at(pos)
        if dot is not None:
            self.app.sounds.play("button")
            self.load_level(dot)
            return
        ptype = self.slot_at(pos)
        if ptype is not None:
            if self.locked or self.arrived or self.counts[ptype] == 0:
                self.app.sounds.play("deny", 0.6)
                return
            if self.selected != ptype:
                self.app.sounds.play("select")
            self.selected = ptype
            self.hold = {"src": "tray", "type": ptype, "start": pos, "active": False}
            return
        cell = self.cell_at(pos)
        if not logic.Board.on_board(cell):
            if not TRAY_RECT.collidepoint(pos):
                self.selected = None   # κλικ στο γρασίδι: αφήνω το κομμάτι
            return
        if not self.can_place(cell):
            if not self.board.free(cell) or self.locked or cell in self.board.pieces:
                self.app.sounds.play("deny", 0.6)
            return
        if cell in self.board.pieces:
            ptype = self.board.remove(cell)
            self.layer = None
            self.hold = {"src": "board", "type": ptype, "from": cell, "start": pos, "active": False}
            self.app.sounds.play("select", 0.6)
        elif self.selected and self.counts[self.selected] > 0:
            self.place(cell, self.selected)

    def _mouse_up(self, pos):
        b = self.pressed_button
        if b:
            b.pressed = False
            self.pressed_button = None
            if b.contains(pos) and b.enabled:
                self.app.sounds.play("button")
                b.action()
            return
        hold, self.hold = self.hold, None
        if not hold:
            return
        cell = self.cell_at(pos)
        ptype = hold["type"]
        if hold["src"] == "tray":
            if hold["active"] and self.can_place(cell) and self.counts[ptype] > 0:
                self.place(cell, ptype)
            return
        # κομμάτι που σηκώθηκε από το ταμπλό
        origin = hold["from"]
        if not hold["active"]:
            sel = self.selected
            if sel and sel != ptype and self.counts[sel] > 0:
                self.counts[ptype] += 1
                self.place(origin, sel)
            else:
                self.counts[ptype] += 1
                self.app.sounds.play("remove")
        elif self.can_place(cell):
            self.counts[ptype] += 1
            self.place(cell, ptype)
        else:
            self.counts[ptype] += 1
            self.app.sounds.play("remove")
        self.layer = None
        self.check_path()

    # ------------------------------------------------------------- update
    def _on_robot_event(self, ev):
        if ev == "turn":
            self.message = MSG["turn"]
            self.app.sounds.play("turn", 0.8)
        elif ev == "barrier":
            self.message = MSG["barrier"]
            self.app.sounds.play("bump", 0.7)
        elif ev == "gear":
            self.gear_fx[self.robot.cell] = self.time
            self.gear_back.pop(self.robot.cell, None)
            self.app.sounds.play("gear", 0.8)
        elif ev == "home":
            self.app.sounds.play("remove", 0.7)
            # τα γρανάζια ξαναμπαίνουν στη θέση τους για την επόμενη δοκιμή
            for cell in self.gear_fx:
                self.gear_back[cell] = self.time
            self.gear_fx = {}
            self.message = MSG["home"]
            self.check_path()
        elif ev == "arrived":
            self.arrived = True
            self.selected = None
            self.message = MSG["arrived"]
            self.app.sounds.play("charge", 0.8)
            self.win_timer = 0.6
            self.app.progress.mark(GAME_ID, self.level_index + 1)
            self.banner.show(self.time)
            self.confetti.burst(WIDTH)

    def update(self, dt):
        self.time += dt
        self.btn_go.enabled = self.go_enabled()
        self.btn_go.pulse = self.btn_go.enabled and self.complete
        self.btn_next.pulse = self.arrived
        for b in self.buttons:
            b.hover = b.contains(self.mouse)

        if self.auto_timer is not None and self.robot.state == "idle" and not self.hold:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                self.auto_timer = None
                self.start_robot()

        for ev in self.robot.update(dt, self.board):
            self._on_robot_event(ev)
        self._turn_wheels()
        if self.board.gears:
            # η μπάρα ανοίγει μόλις το R2 έχει όλα τα γρανάζια και κλείνει όταν τα αφήσει πίσω
            want = 1.0 if self.board.gears <= self.robot.collected or self.arrived else 0.0
            if want and self.barrier_open == 0.0:
                self.app.sounds.play("barrier", 0.7)
            step = dt / BARRIER_TIME
            self.barrier_open = min(want, self.barrier_open + step) if want else max(0.0, self.barrier_open - step)
        if self.robot.moving:
            # η γραμμή μπορεί να αλλάξει όσο κινείται το R2 (στο mode 1)
            self.complete = self.board.follow()[0]

        if self.robot.state == "running":
            # το μοτέρ του R2 βουίζει όσο κινείται
            self.motor_timer -= dt * max(0.35, self.robot.speed / logic.Robot.MAX_SPEED)
            if self.motor_timer <= 0:
                self.motor_timer = 0.34
                self.app.sounds.play("motor", 0.2)
        if self.win_timer is not None:
            self.win_timer -= dt
            if self.win_timer <= 0:
                self.win_timer = None
                self.app.sounds.play("win", 0.8)

        self.confetti.update(dt, self.time, HEIGHT)

        self._update_cursor()

    def _turn_wheels(self):
        """Γυρίζει τις ρόδες όσο κινήθηκε το R2: μπροστά και οι δύο, ή αντίθετα στη στροφή επί τόπου."""
        X, Y, hx, hy = pose = self.robot.pose()
        lx, ly, lhx, lhy = self.last_pose
        self.last_pose = pose
        dist = math.hypot(X - lx, Y - ly)
        turn = (math.atan2(hy, hx) - math.atan2(lhy, lhx) + math.pi) % (2 * math.pi) - math.pi
        if dist > 0.5:          # άλμα (νέα πίστα): όχι κύλισμα
            return
        side = turn * art.WHEEL_HALF_TRACK
        self.wheel_spin[0] += (dist + side) / art.WHEEL_R
        self.wheel_spin[1] += (dist - side) / art.WHEEL_R

    def _set_cursor(self, cursor):
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    def _update_cursor(self):
        pos = self.mouse
        hand = any(b.enabled and b.contains(pos) for b in self.buttons) or self.dot_at(pos) is not None
        if not hand:
            ptype = self.slot_at(pos)
            hand = ptype is not None and self.counts[ptype] > 0 and not self.locked and not self.arrived
        if not hand:
            cell = self.cell_at(pos)
            hand = self.can_place(cell) and (cell in self.board.pieces or self.selected is not None)
        self._set_cursor(pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW)

    # --------------------------------------------------------------- draw
    def _board_layer(self):
        if self.layer is None:
            layer = self.assets.background.copy()
            if self.river:
                layer.blit(self.river, (0, 0))
            ax, ay = self.assets.tile_anchor
            water = set(self.level.water)
            for r in range(logic.ROWS):
                for c in range(logic.COLS):
                    cell = (c, r)
                    x, y = self.geo.pt(c, r)
                    if cell in self.scenery:
                        layer.blit(self.assets.grass, (x - ax, y - ay))
                    elif cell in self.board.fixed:
                        ptype = self.board.fixed[cell]
                        img = self.assets.bridges[ptype] if cell in water else self.assets.fixed[ptype]
                        layer.blit(img, (x - ax, y - ay))
                    elif cell in self.board.pieces:
                        layer.blit(self.assets.pieces[self.board.pieces[cell]], (x - ax, y - ay))
            self.layer = layer
        return self.layer

    def _cell_poly(self, cell, z=art.PIECE_Z, m=0.03):
        c, r = cell
        g = self.geo
        return [g.pt(c + m, r + m, z), g.pt(c + 1 - m, r + m, z), g.pt(c + 1 - m, r + 1 - m, z), g.pt(c + m, r + 1 - m, z)]

    def _draw_hover(self, screen):
        if self.hold and not self.hold["active"]:
            return
        cell = self.cell_at(self.mouse)
        if not self.can_place(cell):
            return
        current = self.board.pieces.get(cell)
        ptype = self.hold["type"] if self.hold else self.selected
        if ptype and (self.hold or self.counts[ptype] > 0) and current != ptype:
            x, y = self.geo.pt(*cell)
            ax, ay = self.assets.tile_anchor
            screen.blit(self.assets.ghosts[ptype], (x - ax, y - ay))
            ui.fill_poly(screen, (255, 236, 110, 70), self._cell_poly(cell), (255, 200, 40))
        elif current:
            ui.fill_poly(screen, (255, 255, 255, 60), self._cell_poly(cell), (255, 255, 255))

    def _draw_world(self, screen):
        g = self.geo
        ox, oy = self.assets.obj_anchor
        items = []
        for cell, kind in self.scenery.items():
            x, y = g.pt(*cell)
            items.append((g.depth(cell[0] + 0.5, cell[1] + 0.6), self.assets.objects[kind], (x - ox, y - oy)))
            if kind == "windmill":
                sails = lambda s, cell=cell: art.windmill_sails(s, g, cell, self.time * 1.3)
                items.append((g.depth(cell[0] + 0.5, cell[1] + 0.6) + 0.001, sails, None))
        sc = art.SIGNAL_CELL
        x, y = g.pt(*sc)
        items.append((g.depth(sc[0] + art.SIGNAL_POS[0], sc[1] + art.SIGNAL_POS[1]),
                      self.assets.signal[self.complete], (x - ox, y - oy)))
        for cell in self.board.gears:
            items.append((g.depth(cell[0] + 0.5, cell[1] + 0.5), lambda s, cell=cell: self._draw_gear(s, cell), None))
        if self.board.gears:
            got = len(self.robot.collected & self.board.gears)
            if self.arrived:
                got = len(self.board.gears)
            draw = lambda s: art.barrier(s, g, self.barrier_open, got, len(self.board.gears), self.time)
            items.append((g.depth(*art.BARRIER_POST), draw, None))
            items.append((g.depth(*art.BARRIER_REST), lambda s: art.barrier_rest(s, g, self.barrier_open), None))
        X, Y, hx, hy = self.robot.pose()
        items.append((g.depth(X, Y), None, (X, Y, hx, hy)))
        for _, img, where in sorted(items, key=lambda it: it[0]):
            if img is None:
                self.robot_pos = art.draw_robot(screen, g, *where, led=self._led(), spin=self.wheel_spin)
                if self.arrived:
                    r2.charge_rings(screen, self.robot_pos, self.time, art.ROBOT_SIZE * g.tw)
            elif callable(img):
                img(screen)
            else:
                screen.blit(img, where)

    def _draw_gear(self, screen, cell):
        """Ένα γρανάζι που αιωρείται και γυρίζει. Όταν το μαζέψει το R2, πετά ψηλά και σβήνει."""
        g = self.geo
        phase = cell[0] * 1.7 + cell[1] * 2.3
        bob = 4 * math.sin(self.time * 3 + phase)
        angle = self.time * 1.6 + phase
        scale, alpha, lift = 1.0, 255, 0.0
        if cell in self.gear_fx:
            p = (self.time - self.gear_fx[cell]) / COLLECT_TIME
            if p >= 1:
                return
            lift, scale, alpha = 70 * p, 1 + 0.5 * p, round(255 * (1 - p) ** 1.5)
            angle += 10 * p
        elif cell in self.gear_back:
            p = min(1.0, (self.time - self.gear_back[cell]) / 0.35)
            scale = p * (1 + 0.3 * math.sin(p * math.pi))
        if scale <= 0.02:
            return
        sx, sy = g.pt(cell[0] + 0.5, cell[1] + 0.5, art.PIECE_Z)
        if cell not in self.gear_fx:
            w = 15 * g.k * scale * (1 - bob / 30)
            pygame.gfxdraw.filled_ellipse(screen, round(sx), round(sy), max(1, round(w)), max(1, round(w * 0.36)),
                                          (40, 40, 30, 50))
        x, y = g.pt(cell[0] + 0.5, cell[1] + 0.5, GEAR_Z + bob + lift)
        r = GEAR_R * g.k * scale
        if alpha >= 255:
            art.gear(screen, (x, y), r, angle)
            return
        size = math.ceil(r * 2.6) + 4
        tmp = pygame.Surface((size, size), pygame.SRCALPHA)
        art.gear(tmp, (size / 2, size / 2), r, angle)
        tmp.set_alpha(alpha)
        screen.blit(tmp, (x - size / 2, y - size / 2))
        # αστεράκια που φεύγουν προς τα έξω
        p = (self.time - self.gear_fx[cell]) / COLLECT_TIME
        for i in range(6):
            a = i * math.pi / 3 + p * 2
            d = (10 + 46 * p) * g.k
            ui.star(screen, (x + d * math.cos(a), y + d * math.sin(a) * 0.8), 6 * g.k * (1 - p) + 1,
                    (255, 236, 120), (200, 150, 30))

    def _draw_water(self, screen):
        if self.ripple_cells:
            art.ripples(screen, self.geo, self.ripple_cells, self.time)

    def _led(self):
        """Το χρώμα του LED: πράσινο όταν φορτίζει, κόκκινο όταν γυρίζει πίσω, αλλιώς μπλε."""
        if self.arrived:
            return r2.LED_GREEN
        if self.robot.state == "turning":
            return r2.LED_RED
        return r2.LED_BLUE

    def _draw_top(self, screen):
        screen.blit(self.top_bar, (0, 0))
        pygame.draw.line(screen, (196, 206, 218), (0, TOP_H), (WIDTH, TOP_H), 2)
        for b in self.buttons:
            b.draw(screen, self.time)
        done = self.app.progress.completed(GAME_ID)
        for i, (x, y) in enumerate(self.dots):
            current = i == self.level_index
            r = 15 if current else 12
            if current:
                ui.circle(screen, (62, 132, 222), (x, y), r + 3)
                ui.circle(screen, (255, 255, 255), (x, y), r + 1)
            fill = (250, 200, 60) if (i + 1) in done else ((62, 132, 222) if current else (226, 230, 238))
            ui.circle(screen, fill, (x, y), r, ui.shade(fill, 0.7))
            fg = (255, 255, 255) if current or (i + 1) in done else (110, 118, 132)
            ui.text(screen, str(i + 1), (x, y), 16 if current else 14, fg)
        ui.text(screen, self.message, (CENTER_X, 69), 21, (44, 54, 76))

    def _draw_tray(self, screen):
        ui.panel(screen, TRAY_RECT, (198, 152, 100), radius=22, border=(150, 106, 64))
        dim = self.locked or self.arrived
        for i, ptype in enumerate(logic.PIECE_TYPES):
            slot = self.slots[i]
            n = self.counts[ptype]
            sel = self.selected == ptype and not dim
            hover = slot.collidepoint(self.mouse) and n > 0 and not dim
            r = slot.move(0, -6 if sel else (-2 if hover else 0))
            pygame.draw.rect(screen, (255, 238, 160) if sel else (228, 194, 146), r, border_radius=16)
            pygame.draw.rect(screen, (255, 186, 40) if sel else (176, 132, 86), r, 4 if sel else 2, border_radius=16)
            cx, cy = r.centerx - 6, r.centery + 8
            if n == 0 or dim:
                img = self.assets.tray_dim[ptype]
                screen.blit(img, img.get_rect(center=(cx, cy)))
            else:
                img = self.assets.tray[ptype]
                for j in reversed(range(min(n, 3))):
                    screen.blit(img, img.get_rect(center=(cx + 5 * j, cy - 5 * j)))
            bx, by = r.right - 22, r.y + 22
            ui.circle(screen, (255, 255, 255) if n and not dim else (220, 214, 204), (bx, by), 17, (120, 90, 60))
            ui.text(screen, str(n), (bx, by), 21, (60, 50, 40) if n and not dim else (160, 150, 140))
        if self.selected and not dim:
            r = self.slots[logic.PIECE_TYPES.index(self.selected)]
            cx = r.centerx
            tip = r.y - 8 + 5 * math.sin(self.time * 6)
            pts = [(cx - 7, tip - 40), (cx + 7, tip - 40), (cx + 7, tip - 18), (cx + 17, tip - 18), (cx, tip),
                   (cx - 17, tip - 18), (cx - 7, tip - 18)]
            ui.fill_poly(screen, (232, 44, 44), pts, (120, 20, 20))

    def _draw_hold(self, screen):
        if not (self.hold and self.hold["active"]):
            return
        img = self.assets.pieces[self.hold["type"]]
        ax, ay = self.assets.tile_anchor
        g = self.geo
        # το κέντρο του κομματιού ακολουθεί το ποντίκι
        cx = ax + 0.5 * g.tw - 0.5 * g.shift
        cy = ay + 0.5 * g.th - art.PIECE_Z
        screen.blit(img, (self.mouse[0] - cx, self.mouse[1] - cy))

    def _draw_celebration(self, screen):
        self.confetti.draw(screen)
        self.banner.draw(screen, self.time, (640, 318))

    def draw(self, screen):
        screen.blit(self._board_layer(), (0, 0))
        self._draw_water(screen)
        self._draw_hover(screen)
        self._draw_world(screen)
        self._draw_top(screen)
        self._draw_tray(screen)
        self._draw_hold(screen)
        self._draw_celebration(screen)
