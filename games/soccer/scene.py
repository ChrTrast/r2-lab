"""Οι οθόνες του Ποδοσφαίρου.

Αρχή («Με ποιον θα παίξεις;») -> Με τον υπολογιστή / Δύο παίκτες εδώ (ρυθμίσεις -> αγώνας)
                               -> Στο δίκτυο: «Γήπεδα στο εργαστήριο» -> «Αλλαγή ομάδων» -> αγώνας
Μετά τον αγώνα: «Ξανά» (ίδιες ομάδες), «Αλλαγή ομάδων» (στο δίκτυο) ή «Πίσω» (στις ρυθμίσεις).
Στο δίκτυο αποφασίζει όποιος έφτιαξε το γήπεδο: αυτός ξεκινά τον αγώνα και διαλέγει τι γίνεται μετά.

Οδήγηση: ↑ μπροστά, ↓ πίσω, ← → στροφή, Space κλωτσιά (και W A S D).
Δύο παίκτες στο ίδιο πληκτρολόγιο (εδώ ή στο δίκτυο): ο ένας με W A S D και Space,
ο άλλος με τα βελάκια και Enter.
Τα πλήκτρα διαβάζονται από τη θέση τους στο πληκτρολόγιο (scancode), ώστε το W A S D να
δουλεύει και όταν το πληκτρολόγιο γράφει ελληνικά.
"""
import math
import time

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from . import art as A, logic as L, net

# ------------------------------------------------------------- πλήκτρα (SDL scancodes)
SC_A, SC_D, SC_S, SC_W = 4, 7, 22, 26
SC_RETURN, SC_TAB, SC_SPACE = 40, 43, 44
SC_RIGHT, SC_LEFT, SC_DOWN, SC_UP = 79, 80, 81, 82
SC_KP_ENTER, SC_KP2, SC_KP4, SC_KP6, SC_KP8, SC_KP0 = 88, 90, 92, 94, 96, 98
SC_LCTRL, SC_LSHIFT, SC_RCTRL, SC_RSHIFT = 224, 225, 228, 229
KEY_TO_SC = {pygame.K_UP: SC_UP, pygame.K_DOWN: SC_DOWN, pygame.K_LEFT: SC_LEFT, pygame.K_RIGHT: SC_RIGHT,
             pygame.K_SPACE: SC_SPACE, pygame.K_RETURN: SC_RETURN, pygame.K_KP_ENTER: SC_KP_ENTER,
             pygame.K_LSHIFT: SC_LSHIFT, pygame.K_RSHIFT: SC_RSHIFT, pygame.K_LCTRL: SC_LCTRL,
             pygame.K_RCTRL: SC_RCTRL, pygame.K_TAB: SC_TAB}
ONE = ({SC_UP, SC_W, SC_KP8}, {SC_DOWN, SC_S, SC_KP2}, {SC_LEFT, SC_A, SC_KP4}, {SC_RIGHT, SC_D, SC_KP6},
       {SC_SPACE, SC_LSHIFT, SC_RSHIFT, SC_RETURN, SC_KP_ENTER, SC_LCTRL, SC_RCTRL, SC_KP0})
LEFT_KEYS = ({SC_W}, {SC_S}, {SC_A}, {SC_D}, {SC_SPACE, SC_LSHIFT, SC_LCTRL, SC_TAB})
RIGHT_KEYS = ({SC_UP, SC_KP8}, {SC_DOWN, SC_KP2}, {SC_LEFT, SC_KP4}, {SC_RIGHT, SC_KP6},
              {SC_RETURN, SC_KP_ENTER, SC_RSHIFT, SC_RCTRL, SC_KP0})
# ένας παίκτης σε αυτόν τον υπολογιστή: όλα τα πλήκτρα. Δύο: αριστερό και δεξί χέρι του πληκτρολογίου.
KEYMAPS = {"one": ONE, "left": LEFT_KEYS, "right": RIGHT_KEYS}


def keys_input(keys, mapping, kicks=0):
    up, down, left, right, _ = mapping
    fwd = (1 if keys & up else 0) - (1 if keys & down else 0)
    turn = (1 if keys & right else 0) - (1 if keys & left else 0)
    return L.Input(fwd, turn, kicks)


LEVEL_NAMES = {"easy": "εύκολο", "hard": "δύσκολο"}
END_AFTER = 1.2           # πότε βγαίνει η κάρτα «Τέλος αγώνα»
HOME = lambda s, c, z, col: ui.icon_home(s, c, z, col, door=A.RED_BTN)   # noqa: E731


def B(rect, label, icon, color, action, size=16):
    return ui.Button(rect, label, icon, color, action, label_size=size)


# ------------------------------------------------------------- παιχνίδι σε αυτόν τον υπολογιστή
class LocalSession:
    """Με τον υπολογιστή (1 εναντίον 1) ή δύο παίκτες στο ίδιο πληκτρολόγιο."""
    role = "local"

    def __init__(self, mode, level, minutes, name=""):
        self.mode, self.level, self.minutes = mode, level, minutes
        self.name = net.clean_name(name)
        self.match_no = 0
        self.mine = {1} if mode == "pc" else set()
        self.start()

    def start(self):
        if self.mode == "pc":
            players = [{"id": 1, "name": self.name or "ΕΣΥ", "team": L.BLUE, "bot": None},
                       {"id": 2, "name": "ΥΠΟΛΟΓΙΣΤΗΣ", "team": L.YELLOW, "bot": self.level}]
        else:
            players = [{"id": 1, "name": "W A S D", "team": L.BLUE, "bot": None},
                       {"id": 2, "name": "ΒΕΛΑΚΙΑ", "team": L.YELLOW, "bot": None}]
        self.match = L.Match(players, self.minutes)
        self.match_no += 1

    again = start

    @property
    def state(self):
        return "end" if self.match.phase == "end" else "match"

    def update(self, dt, scene):
        if self.mode == "pc":
            inputs = {1: scene.pad("one")}
        else:
            inputs = {1: scene.pad("left"), 2: scene.pad("right")}
        return self.match.update(dt, inputs)

    def view(self, now=None):
        return self.match.snapshot()

    def roster(self):
        return {p["id"]: p for p in self.match.roster()}

    def close(self):
        pass


# ------------------------------------------------------------- η σκηνή
class SoccerScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.pressed_button = None
        self.cursor = None
        self.keys = set()
        self.kicks = {name: 0 for name in KEYMAPS}      # πόσες φορές πατήθηκε η κλωτσιά, για κάθε χέρι
        self.prefs = getattr(app, "soccer_prefs", None) or {"name": "", "level": "easy", "minutes": 3}
        app.soccer_prefs = self.prefs
        self.btn_sound = B((1090, 8, 84, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_menu = B((1184, 8, 86, 76), "Μενού", HOME, A.RED_BTN, lambda: self.page.menu())
        self.btn_back = B((14, 8, 92, 76), "Πίσω", ui.icon_prev, A.BLUE_BTN, lambda: self.page.back())
        self.page = StartPage(self)

    # ---------------------------------------------------------- σελίδες
    def go(self, page):
        self.page = page
        self.pressed_button = None

    def to_menu(self):
        self.page.leave()
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def top_buttons(self):
        return [self.btn_back, self.btn_sound, self.btn_menu] if self.page.has_back else [self.btn_sound, self.btn_menu]

    def all_buttons(self):
        if self.page.modal():
            return self.page.buttons()
        return self.page.buttons() + self.top_buttons()

    def draw_top(self, screen):
        A.top_bar(screen)
        for b in self.top_buttons():
            b.draw(screen, self.time)

    # ---------------------------------------------------------- γεγονότα
    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            for b in self.all_buttons():
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed_button = b
                    return
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed_button = self.pressed_button, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
                return
        elif e.type == pygame.KEYDOWN:
            codes = {sc for sc in (getattr(e, "scancode", None), KEY_TO_SC.get(e.key)) if sc}
            fresh = codes - self.keys            # όχι η αυτόματη επανάληψη ενός πλήκτρου που μένει πατημένο
            self.keys |= codes
            for name, mapping in KEYMAPS.items():
                if fresh & mapping[4]:
                    self.kicks[name] = (self.kicks[name] + 1) % L.KICK_WRAP
        elif e.type == pygame.KEYUP:
            for sc in (getattr(e, "scancode", None), KEY_TO_SC.get(e.key)):
                self.keys.discard(sc)
        elif e.type in (getattr(pygame, "WINDOWFOCUSLOST", -1), getattr(pygame, "ACTIVEEVENT", -2)):
            self.keys.clear()
        self.page.handle_event(e)

    def pad(self, name):
        """Τι πατάει τώρα ένα χέρι του πληκτρολογίου: "one" (όλα), "left" (W A S D) ή "right" (βελάκια)."""
        return keys_input(self.keys, KEYMAPS[name], self.kicks[name])

    def update(self, dt):
        self.time += dt
        self.page.update(dt)
        hand = False
        for b in self.all_buttons():
            b.hover = b.enabled and b.contains(self.mouse)
            hand = hand or b.hover
        hand = hand or self.page.hand(self.mouse)
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    def draw(self, screen):
        self.page.draw(screen)


class Page:
    has_back = False

    def __init__(self, scene):
        self.scene = scene
        self.app = scene.app

    def buttons(self):
        return []

    def modal(self):
        return False

    def hand(self, pos):
        return False

    def handle_event(self, e):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def leave(self):
        """Η σελίδα κλείνει (π.χ. πάμε στο μενού): κλείνει και ό,τι έχει ανοιχτό στο δίκτυο."""

    def back(self):
        self.scene.go(StartPage(self.scene))

    def menu(self):
        self.scene.to_menu()

    def play(self, name, vol=1.0):
        self.app.sounds.play(name, vol)


def _decor(dim=165, players=True):
    """Το γήπεδο με τα R2 στη σέντρα, θολό πίσω από τις κάρτες."""
    s = A.field().copy()
    if players:
        for (fx_, fy), team in (((0.36, 0.5), L.BLUE), ((0.16, 0.24), L.BLUE), ((0.64, 0.5), L.YELLOW),
                                ((0.86, 0.72), L.YELLOW)):
            A.robot(s, A.to_screen(fx_ * L.FW, fy * L.FH), 90 if team == L.BLUE else 270, team)
        A.ball(s, A.to_screen(L.FW / 2, L.FH / 2))
    A.dim(s, dim)
    return s


# ------------------------------------------------------------- 1. αρχή
class StartPage(Page):
    CARD = pygame.Rect(150, 114, 980, 588)

    def __init__(self, scene):
        super().__init__(scene)
        self.bg = _decor()
        c = self.CARD
        tw, th, gap = 290, 300, 30
        x0 = c.centerx - (3 * tw + 2 * gap) // 2
        self.tiles = [pygame.Rect(x0 + i * (tw + gap), c.y + 132, tw, th) for i in range(3)]

    def hand(self, pos):
        return any(t.collidepoint(pos) for t in self.tiles)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, t in enumerate(self.tiles):
                if t.collidepoint(e.pos):
                    self.choose(i)
                    return
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.scene.to_menu()
            elif e.key in (pygame.K_1, pygame.K_KP1):
                self.choose(0)
            elif e.key in (pygame.K_2, pygame.K_KP2):
                self.choose(1)
            elif e.key in (pygame.K_3, pygame.K_KP3):
                self.choose(2)

    def choose(self, i):
        self.play("select", 0.7)
        if i == 2:
            self.scene.go(NetListPage(self.scene))
        else:
            self.scene.go(SetupPage(self.scene, "pc" if i == 0 else "two"))

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        self.scene.draw_top(s)
        c = self.CARD
        A.card(s, c)
        ui.text(s, "Ποδόσφαιρο", (c.centerx, c.y + 48), 46, A.TITLE, shadow=A.TITLE_SHADOW)
        ui.text(s, "Με ποιον θα παίξεις;", (c.centerx, c.y + 98), 24, A.GREY)
        info = (("Με τον υπολογιστή", ["1 εναντίον 1", "εύκολο ή δύσκολο"], self._vs_pc),
                ("Δύο παίκτες εδώ", ["στο ίδιο πληκτρολόγιο", "μπλε: W A S D, κίτρινη: βελάκια"], self._two),
                ("Στο δίκτυο", ["με τους άλλους υπολογιστές", "του εργαστηρίου"], self._net))
        for t, (title, sub, draw) in zip(self.tiles, info):
            hover = t.collidepoint(self.scene.mouse)
            face = A.tile(s, t, hover)
            draw(s, (face.centerx, face.y + 112))
            ui.text(s, title, (face.centerx, face.y + 214), 25, (40, 130, 90) if hover else A.INK)
            for j, line in enumerate(sub):
                ui.text(s, line, (face.centerx, face.y + 248 + j * 22), 16, A.GREY, bold=False)
        drive_hint(s, c.x + 56, c.y + 520, c)

    @staticmethod
    def _vs_pc(s, p):
        x, y = p
        A.robot(s, (x - 78, y + 6), 90, L.BLUE)
        A.robot(s, (x + 78, y + 6), 270, L.YELLOW)
        A.ball(s, (x, y + 6), 13)
        A.monitor(s, (x + 78, y - 64), 40)

    @staticmethod
    def _two(s, p):
        x, y = p
        for cx, team, letters in ((x - 68, L.BLUE, "WASD"), (x + 68, L.YELLOW, None)):
            A.key_cluster(s, (cx, y), letters, A.TEAM[team])
            A.r2art.draw_robot(s, (cx, y - 76), 44, 0, A.LED[team])

    @staticmethod
    def _net(s, p):
        x, y = p
        pts = [(x, y - 52), (x - 84, y + 34), (x + 84, y + 34)]
        for i in range(3):
            pygame.draw.line(s, (120, 130, 150), pts[i], pts[(i + 1) % 3], 4)
        for q in pts:
            A.monitor(s, q, 78)


def drive_hint(s, x, y, c):
    """«Οδήγηση: ↑ μπροστά ↓ πίσω ← → στρίψε Space κλωτσιά»."""
    pygame.draw.line(s, (226, 230, 238), (c.x + 40, y - 46), (c.right - 40, y - 46), 2)
    r = ui.text(s, "Οδήγηση:", (x, y), 20, A.INK, anchor="midleft")
    x = r.right + 30
    for keys, label in ((["up"], "μπροστά"), (["down"], "πίσω"), (["left", "right"], "στρίψε"),
                        (["Space"], "κλωτσιά")):
        for k in keys:
            if k == "Space":
                kr = A.keycap(s, (x + 50, y), "Space", w=100, size=16)
            else:
                kr = A.keycap(s, (x + 23, y), arrow=k)
            x = kr.right + 6
        r = ui.text(s, label, (x + 4, y), 18, A.GREY, anchor="midleft", bold=False)
        x = r.right + 30
    A.ball(s, (x - 8, y), 11)


# ------------------------------------------------------------- 2. ρυθμίσεις (σε αυτόν τον υπολογιστή)
class SetupPage(Page):
    has_back = True
    CARD = pygame.Rect(220, 114, 840, 588)

    def __init__(self, scene, mode):
        super().__init__(scene)
        self.mode = mode
        self.bg = _decor()
        c = self.CARD
        self.btn_go = B((c.centerx - 190, c.y + 462, 380, 100), "Ξεκίνα τον αγώνα!", A.icon_whistle,
                        A.GREEN_BTN, self.start, size=22)
        self.btn_go.pulse = True
        y_min = c.y + 360 if mode == "pc" else c.y + 380
        self.min_rects = [pygame.Rect(c.centerx - 70 + (i - 1) * 140 + 40, y_min - 28, 120, 56) for i in range(3)]
        self.level_rects = [pygame.Rect(c.centerx - 250 + i * 270 + 40, c.y + 160, 220, 120) for i in range(2)]

    def buttons(self):
        return [self.btn_go]

    def hand(self, pos):
        rects = self.min_rects + (self.level_rects if self.mode == "pc" else [])
        return any(r.collidepoint(pos) for r in rects)

    def handle_event(self, e):
        p = self.scene.prefs
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for m, r in zip(L.MINUTES, self.min_rects):
                if r.collidepoint(e.pos):
                    p["minutes"] = m
                    self.play("select", 0.6)
            if self.mode == "pc":
                for lv, r in zip(("easy", "hard"), self.level_rects):
                    if r.collidepoint(e.pos):
                        p["level"] = lv
                        self.play("select", 0.6)
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start()
            elif e.key == pygame.K_ESCAPE:
                self.back()

    def start(self):
        p = self.scene.prefs
        session = LocalSession(self.mode, p["level"], p["minutes"], p.get("name", ""))
        self.play("whistle", 0.8)
        self.scene.go(MatchPage(self.scene, session))

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        self.scene.draw_top(s)
        c = self.CARD
        A.card(s, c)
        p = self.scene.prefs
        mouse = self.scene.mouse
        if self.mode == "pc":
            ui.text(s, "Με τον υπολογιστή", (c.centerx, c.y + 46), 40, A.TITLE, shadow=A.TITLE_SHADOW)
            ui.text(s, "Εσύ είσαι η Μπλε ομάδα. Βάλε γκολ στο κίτρινο τέρμα!", (c.centerx, c.y + 94), 19, A.GREY)
            ui.text(s, "Αντίπαλος:", (c.x + 50, c.y + 220), 21, A.INK, anchor="midleft")
            for lv, r in zip(("easy", "hard"), self.level_rects):
                sel = p["level"] == lv
                hover = r.collidepoint(mouse)
                A.chip(s, r, "", sel, hover=hover)
                face = r.move(0, -3) if hover and not sel else r
                A.robot(s, (face.x + 58, face.centery), 270, L.YELLOW, size=56)
                ui.text(s, "Εύκολο" if lv == "easy" else "Δύσκολο", (face.x + 152, face.centery - 12), 24,
                        (40, 130, 90) if sel else A.INK)
                for k in range(1 if lv == "easy" else 3):
                    ui.star(s, (face.x + 124 + k * 26, face.centery + 22), 10, (252, 204, 60))
            y = c.y + 360
        else:
            ui.text(s, "Δύο παίκτες εδώ", (c.centerx, c.y + 46), 40, A.TITLE, shadow=A.TITLE_SHADOW)
            ui.text(s, "Δύο παιδιά στο ίδιο πληκτρολόγιο: ένα για κάθε ομάδα.", (c.centerx, c.y + 94), 19, A.GREY)
            for i, (team, letters, kick) in enumerate(((L.BLUE, "WASD", "Space"), (L.YELLOW, None, "Enter"))):
                box = pygame.Rect(c.x + 50 + i * 380, c.y + 130, 360, 190)
                pygame.draw.rect(s, ui.mix(A.TEAM[team], (255, 255, 255), 0.85), box, border_radius=18)
                pygame.draw.rect(s, A.TEAM[team], box, 3, border_radius=18)
                head = pygame.Rect(box.x, box.y, box.w, 40)
                pygame.draw.rect(s, A.TEAM[team], head, border_top_left_radius=18, border_top_right_radius=18)
                ui.text(s, "ΜΠΛΕ ΟΜΑΔΑ" if team == L.BLUE else "ΚΙΤΡΙΝΗ ΟΜΑΔΑ", head.center, 20, A.TEAM_FG[team])
                A.r2art.draw_robot(s, (box.x + 62, box.y + 112), 64, 90 if team == L.BLUE else 270, A.LED[team])
                A.key_cluster(s, (box.x + 196, box.y + 98), letters, A.TEAM[team])
                A.keycap(s, (box.x + 196, box.y + 156), kick, w=96, h=34, size=15, tint=A.TEAM[team])
                ui.text(s, "κλωτσιά", (box.x + 254, box.y + 156), 15, A.GREY, anchor="midleft", bold=False)
            y = c.y + 380
        ui.text(s, "Διάρκεια:", (c.x + 50, y), 21, A.INK, anchor="midleft")
        for m, r in zip(L.MINUTES, self.min_rects):
            A.chip(s, r, f"{m} λεπτά", p["minutes"] == m, hover=r.collidepoint(mouse))
        self.btn_go.draw(s, self.scene.time)


# ------------------------------------------------------------- 3. γήπεδα στο δίκτυο
class NetListPage(Page):
    has_back = True
    CARD = pygame.Rect(140, 112, 1000, 590)
    NAME_BOX = pygame.Rect(130, 38, 260, 42)
    ROWS = 4

    def __init__(self, scene, message=None):
        super().__init__(scene)
        self.bg = _decor(200, players=False)
        self.finder = net.Finder()
        self.joining = None
        self.join_name = ""
        self.message = (message, scene.time) if message else None
        self.warn = 0.0
        self.scroll = 0
        self.addr_open = False
        self.addr_text = ""
        c = self.CARD
        self.row_btns = [B((0, 0, 150, 62), "Μπες", ui.icon_next, A.GREEN_BTN, None, size=18)
                         for _ in range(self.ROWS)]
        self.btn_make = B((c.centerx - 220, c.y + 462, 440, 100), "Φτιάξε δικό σου γήπεδο", ui.icon_plus,
                          A.ORANGE_BTN, self.make, size=24)
        self.btn_addr = B((c.right - 196, c.y + 480, 166, 70), "Με διεύθυνση", A.icon_net, (120, 130, 150),
                          self.open_addr, size=15)
        P = self.ADDR_CARD
        self.btn_find = B((P.centerx - 190, P.bottom - 96, 180, 74), "Βρες το", ui.icon_next, A.GREEN_BTN,
                          self.find_addr, size=18)
        self.btn_cancel = B((P.centerx + 10, P.bottom - 96, 180, 74), "Άκυρο", ui.icon_close, (150, 156, 170),
                            self.close_addr, size=18)

    ADDR_CARD = pygame.Rect(WIDTH // 2 - 300, 220, 600, 330)

    # ---------------------------------------------------------- ενέργειες
    @property
    def name(self):
        return self.scene.prefs.get("name", "")

    def need_name(self):
        if net.clean_name(self.name):
            return False
        self.warn = 1.2
        self.message = ("Γράψε πρώτα το όνομά σου, πάνω αριστερά.", self.scene.time)
        self.play("deny", 0.6)
        return True

    def make(self):
        if self.need_name():
            return
        try:
            host = net.Host(self.name, self.scene.prefs.get("minutes", 3))
        except OSError:
            self.message = ("Δεν μπόρεσα να φτιάξω γήπεδο σε αυτόν τον υπολογιστή.", self.scene.time)
            return
        self.finder.close()
        self.scene.go(LobbyPage(self.scene, host))

    def join(self, field):
        if self.need_name() or self.joining:
            return
        self.joining = net.Client(self.name, field["addr"], field["port"])
        self.join_name = field.get("name", "")

    def open_addr(self):
        self.addr_open = True

    def close_addr(self):
        self.addr_open = False

    def find_addr(self):
        if net.valid_ip(self.addr_text):
            self.finder.add_manual(self.addr_text)
            self.message = (f"Ψάχνω γήπεδο στη διεύθυνση {self.addr_text.strip()}…", self.scene.time)
            self.addr_open = False
        else:
            self.play("deny", 0.6)

    def leave(self):
        self.finder.close()
        if self.joining:
            self.joining.close()
            self.joining = None

    def back(self):
        self.leave()
        self.scene.go(StartPage(self.scene))

    # ---------------------------------------------------------- σελίδα
    def modal(self):
        return self.addr_open or self.joining is not None

    def buttons(self):
        if self.addr_open:
            return [self.btn_find, self.btn_cancel]
        if self.joining:
            return []
        return [b for b in self.row_btns if b.action] + [self.btn_make, self.btn_addr]

    def hand(self, pos):
        return self.NAME_BOX.collidepoint(pos) and not self.modal()

    def handle_event(self, e):
        p = self.scene.prefs
        if e.type == pygame.TEXTINPUT:
            if self.addr_open:
                extra = "".join(ch for ch in e.text if ch.isdigit() or ch in ".,")
                self.addr_text = (self.addr_text + extra.replace(",", "."))[:15]
            elif not self.joining:
                p["name"] = net.typed_name(p.get("name", "") + e.text)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                if self.addr_open:
                    self.addr_text = self.addr_text[:-1]
                elif not self.joining:
                    p["name"] = p.get("name", "")[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.addr_open:
                    self.find_addr()
                else:
                    open_fields = [f for f in self.finder.fields() if self._joinable(f)]
                    if len(open_fields) == 1:
                        self.join(open_fields[0])
            elif e.key == pygame.K_ESCAPE:
                if self.addr_open:
                    self.addr_open = False
                elif self.joining:
                    self.joining.close()
                    self.joining = None
                else:
                    self.back()
        elif e.type == pygame.MOUSEWHEEL and not self.modal():
            self.scroll = max(0, self.scroll - e.y)

    @staticmethod
    def _joinable(f):
        n = f.get("n", [0, 0])
        return f.get("state") == "lobby" and f.get("v") == net.VERSION and sum(n) < 2 * f.get("max", L.MAX_TEAM)

    def update(self, dt):
        self.finder.poll()
        self.warn = max(0.0, self.warn - dt)
        if self.joining:
            self.joining.poll()
            if self.joining.state == "lobby":
                client, self.joining = self.joining, None
                self.finder.close()
                self.scene.go(LobbyPage(self.scene, client))
                return
            if self.joining.state == "closed":
                self.message = (self.joining.error or "Δεν μπόρεσα να μπω στο γήπεδο.", self.scene.time)
                self.joining = None
                self.play("deny", 0.6)
        fields = self.finder.fields()
        self.scroll = max(0, min(self.scroll, len(fields) - self.ROWS))
        y0 = self._rows_y()
        for i, b in enumerate(self.row_btns):
            k = self.scroll + i
            if k >= len(fields) or i >= self._rows_fit():
                b.action = None
                continue
            f = fields[k]
            row = pygame.Rect(self.CARD.x + 30, y0 + i * 84, self.CARD.w - 60, 76)
            b.rect = pygame.Rect(row.right - 168, row.y + 7, 150, 62)
            ok = self._joinable(f)
            b.enabled = ok
            if f.get("v") != net.VERSION:
                b.label = "Άλλη έκδοση"
            elif f.get("state") != "lobby":
                b.label = "Παίζουν"
            elif not ok:
                b.label = "Γεμάτο"
            else:
                b.label = "Μπες"
            b.label_size = 18 if ok else 15
            b.action = (lambda f=f: self.join(f))

    def _rows_y(self):
        return self.CARD.y + 86 + (52 if self._msg_visible() else 0)

    def _rows_fit(self):
        return self.ROWS - (1 if self._msg_visible() else 0)

    def _msg_visible(self):
        return self.message is not None and self.scene.time - self.message[1] < 7.0

    def draw(self, s):
        t = self.scene.time
        s.blit(self.bg, (0, 0))
        self.scene.draw_top(s)
        ui.text(s, "Το όνομά σου", (self.NAME_BOX.x, 24), 15, A.GREY, anchor="midleft", bold=False)
        A.text_box(s, self.NAME_BOX, self.name, not self.modal(), "γράψε το όνομά σου", t, self.warn)
        ui.text(s, "Στο δίκτυο", (WIDTH // 2 + 40, 46), 30, A.INK)
        c = self.CARD
        A.card(s, c)
        ui.text(s, "Γήπεδα στο εργαστήριο", (c.x + 40, c.y + 42), 32, A.TITLE, anchor="midleft")
        r = ui.text(s, "ψάχνω για γήπεδα", (c.right - 84, c.y + 44), 17, A.GREY, anchor="midright", bold=False)
        for i in range(3):
            k = (math.sin(t * 4 - i * 0.8) + 1) / 2
            ui.circle(s, ui.mix(A.GREY, (230, 232, 238), 1 - k), (r.right + 16 + i * 14, c.y + 46), 4)
        if self._msg_visible():
            box = pygame.Rect(c.x + 30, c.y + 78, c.w - 60, 44)
            pygame.draw.rect(s, (255, 240, 222), box, border_radius=12)
            pygame.draw.rect(s, (240, 170, 100), box, 2, border_radius=12)
            A.fit_text(s, self.message[0], box.center, 18, (170, 80, 20), box.w - 30)
        fields = self.finder.fields()
        y0 = self._rows_y()
        if not fields:
            ui.text(s, "Δεν βρέθηκε ακόμα κανένα γήπεδο.", (c.centerx, y0 + 110), 22, A.GREY)
            ui.text(s, "Φτιάξε ένα, ή περίμενε να φτιάξει κάποιος άλλος.", (c.centerx, y0 + 146), 18, A.GREY,
                    bold=False)
        for i in range(min(self._rows_fit(), len(fields) - self.scroll)):
            f = fields[self.scroll + i]
            row = pygame.Rect(c.x + 30, y0 + i * 84, c.w - 60, 76)
            ok = self._joinable(f)
            pygame.draw.rect(s, (246, 248, 252), row, border_radius=16)
            pygame.draw.rect(s, (222, 228, 238), row, 2, border_radius=16)
            A.mini_field(s, pygame.Rect(row.x + 22, row.centery - 24, 80, 48))
            ui.text(s, f.get("name", "?"), (row.x + 128, row.y + 28), 26, A.INK if ok else A.GREY, anchor="midleft")
            if f.get("v") != net.VERSION:
                status, col = f"άλλη έκδοση ({f.get('v')})", (200, 120, 50)
            elif f.get("state") == "lobby":
                status, col = "περιμένει παίκτες", A.GREEN_BTN
            else:
                sc = f.get("sc", [0, 0])
                status, col = f"παίζουν τώρα · {sc[0]} – {sc[1]}", (200, 120, 50)
            ui.text(s, status, (row.x + 128, row.y + 56), 16, col, anchor="midleft", bold=False)
            n = f.get("n", [0, 0])
            slots(s, row.x + 470, row.y + 30, n[0], n[1], f.get("max", L.MAX_TEAM))
            ui.text(s, f"{sum(n)} / {2 * f.get('max', L.MAX_TEAM)} παίκτες", (row.x + 550, row.y + 60), 14,
                    A.GREY, bold=False)
        extra = len(fields) - self.scroll - self._rows_fit()
        if extra > 0:
            ui.text(s, f"▼ {extra} ακόμα (ρόδα του ποντικιού)", (c.centerx, y0 + self._rows_fit() * 84 + 2), 15,
                    A.GREY, bold=False)
        for b in self.row_btns:
            if b.action:
                b.draw(s, t)
        pygame.draw.line(s, (226, 230, 238), (c.x + 40, c.y + 438), (c.right - 40, c.y + 438), 2)
        self.btn_make.draw(s, t)
        self.btn_addr.draw(s, t)
        if self.joining:
            A.dim(s, 140)
            P = pygame.Rect(WIDTH // 2 - 280, 290, 560, 150)
            A.card(s, P)
            ui.text(s, f"Μπαίνω στο γήπεδο {self.join_name}…", (P.centerx, P.y + 60), 26, A.INK)
            for i in range(3):
                k = (math.sin(t * 5 - i * 0.8) + 1) / 2
                ui.circle(s, ui.mix(A.GREEN_BTN, (230, 236, 230), 1 - k), (P.centerx - 20 + i * 20, P.y + 106), 6)
        if self.addr_open:
            A.dim(s, 140)
            P = self.ADDR_CARD
            A.card(s, P)
            ui.text(s, "Η διεύθυνση του γηπέδου", (P.centerx, P.y + 44), 28, A.TITLE)
            A.fit_text(s, "Τη βλέπεις στην «Αλλαγή ομάδων», στον υπολογιστή με το γήπεδο.",
                       (P.centerx, P.y + 84), 17, A.GREY, P.w - 40, bold=False)
            box = pygame.Rect(P.centerx - 170, P.y + 112, 340, 54)
            A.text_box(s, box, self.addr_text, True, "π.χ. 192.168.1.23", t)
            self.btn_find.enabled = net.valid_ip(self.addr_text)
            self.btn_find.draw(s, t)
            self.btn_cancel.draw(s, t)


def slots(s, x, y, nb, ny, per_team):
    for team, n, x0 in ((L.BLUE, nb, x), (L.YELLOW, ny, x + 112)):
        for i in range(per_team):
            p = (x0 + i * 32, y)
            if i < n:
                ui.circle(s, A.TEAM[team], p, 13, ui.shade(A.TEAM[team], 0.7))
                A.r2art.draw_robot(s, p, 22, 90 if team == L.BLUE else 270, A.LED[team])
            else:
                A.ring(s, (200, 206, 218), p, 13, 2)


# ------------------------------------------------------------- 4. αλλαγή ομάδων
class LobbyPage(Page):
    """«Αλλαγή ομάδων». Οι παίκτες αυτού του υπολογιστή (ένας ή δύο) έχουν κίτρινο περίγραμμα και
    κουμπί «άλλαξε» στη γραμμή τους. Με «Δεύτερος παίκτης εδώ» μπαίνει και δεύτερο παιδί στο ίδιο
    πληκτρολόγιο: ο πρώτος παίζει με W A S D και Space, ο δεύτερος με τα βελάκια και Enter."""
    has_back = True
    CARD = pygame.Rect(90, 112, 1100, 590)
    COL_W = 450
    SECOND_CARD = pygame.Rect(WIDTH // 2 - 340, 160, 680, 430)

    def __init__(self, scene, session):
        super().__init__(scene)
        self.session = session
        self.host = session.role == "host"
        self.bg = _decor(200, players=False)
        c = self.CARD
        self.col_x = {L.BLUE: c.x + 50, L.YELLOW: c.right - 50 - self.COL_W}
        self.slot_btns = {}
        self.swap_btns = {}
        for team in L.TEAMS:
            for i in range(L.MAX_TEAM):
                row = self.row_rect(team, i)
                add = B((row.right - 158, row.y + 9, 146, 48), "", lambda *a: None, (120, 130, 150), None)
                rem = B((row.right - 50, row.y + 13, 40, 40), "", ui.icon_close, (200, 206, 218), None)
                self.slot_btns[(team, i)] = (add, rem)
                self.swap_btns[(team, i)] = B((row.right - 132, row.y + 9, 120, 48), "", lambda *a: None,
                                              A.BLUE_BTN, None)
        self.btn_second = B((c.centerx - 165, c.y + 372, 330, 68), "", lambda *a: None, A.ORANGE_BTN, None)
        self.btn_start = B((c.right - 50 - 330, c.y + 476, 330, 100), "Ξεκίνα τον αγώνα!", A.icon_whistle,
                           A.GREEN_BTN, self.start, size=22)
        y = c.y + 526
        self.min_rects = [pygame.Rect(c.x + 236 + i * 126, y - 28, 112, 56) for i in range(3)]
        self.second_open = False
        self.second_name = ""
        self.warn = 0.0
        P = self.SECOND_CARD
        self.btn_in = B((P.centerx - 190, P.bottom - 98, 180, 76), "Μπες", ui.icon_next, A.GREEN_BTN,
                        self.add_second, size=18)
        self.btn_no = B((P.centerx + 10, P.bottom - 98, 180, 76), "Άκυρο", ui.icon_close, (150, 156, 170),
                        self.close_second, size=18)

    def row_rect(self, team, i):
        return pygame.Rect(self.col_x[team], self.CARD.y + 134 + i * 78, self.COL_W, 66)

    # ---------------------------------------------------------- ενέργειες
    def start(self):
        if self.host and self.session.can_start():
            self.session.start()
            self.play("whistle", 0.8)
            self.scene.go(MatchPage(self.scene, self.session))

    def open_second(self):
        self.second_open = True
        self.second_name = self.scene.prefs.get("name2", "")
        self.warn = 0.0

    def close_second(self):
        self.second_open = False

    def add_second(self):
        name = net.clean_name(self.second_name)
        if not name:
            self.warn = 1.2
            self.play("deny", 0.6)
            return
        self.scene.prefs["name2"] = name
        self.session.add_local(name)
        self.second_open = False

    def leave(self):
        self.session.close()

    def back(self):
        self.leave()
        self.scene.go(NetListPage(self.scene))

    def players(self):
        return self.session.players

    def team_list(self, team):
        return [p for p in self.players() if p["team"] == team]

    def first_name(self):
        mine = self.session.mine()
        p = next((p for p in self.players() if mine and p["id"] == mine[0]), None)
        return p["name"] if p else self.scene.prefs.get("name", "")

    # ---------------------------------------------------------- σελίδα
    def modal(self):
        return self.second_open

    def buttons(self):
        if self.second_open:
            return [self.btn_in, self.btn_no]
        out = [b for b in self.swap_btns.values() if b.action]
        if self.btn_second.action:
            out.append(self.btn_second)
        if self.host:
            out.append(self.btn_start)
        for add, rem in self.slot_btns.values():
            out += [b for b in (add, rem) if b.action]
        return out

    def hand(self, pos):
        return self.host and not self.second_open and any(r.collidepoint(pos) for r in self.min_rects)

    def handle_event(self, e):
        if self.second_open:
            if e.type == pygame.TEXTINPUT:
                self.second_name = net.typed_name(self.second_name + e.text)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.second_name = self.second_name[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.add_second()
                elif e.key == pygame.K_ESCAPE:
                    self.close_second()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.host:
            for m, r in zip(L.MINUTES, self.min_rects):
                if r.collidepoint(e.pos):
                    self.session.set_minutes(m)
                    self.scene.prefs["minutes"] = m
                    self.play("select", 0.6)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.back()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.host:
                self.start()

    def update(self, dt):
        s = self.session
        self.warn = max(0.0, self.warn - dt)
        if self.host:
            s.poll()
        else:
            s.update(dt, {})
            if s.state == "match":
                self.play("whistle", 0.8)
                self.scene.go(MatchPage(self.scene, s))
                return
            if s.state == "closed":
                self.scene.go(NetListPage(self.scene, s.error))
                return
        mine = s.mine()
        self.btn_second.action = self.open_second if len(mine) == 1 else None
        self.btn_second.enabled = len(self.players()) < 2 * L.MAX_TEAM
        if self.host:
            self.btn_start.enabled = s.can_start()
            self.btn_start.pulse = self.btn_start.enabled
        for team in L.TEAMS:
            ps = self.team_list(team)
            room = len(self.team_list(L.other(team))) < L.MAX_TEAM
            for i in range(L.MAX_TEAM):
                add, rem = self.slot_btns[(team, i)]
                swp = self.swap_btns[(team, i)]
                p = ps[i] if i < len(ps) else None
                local = p is not None and p["id"] in mine
                add.action = (lambda t=team: s.add_bot(t)) if self.host and p is None and i == len(ps) else None
                if p is not None and p.get("bot") and self.host:
                    rem.action = lambda pid=p["id"]: s.remove(pid)
                elif local and len(mine) == 2 and p["id"] == mine[1]:
                    rem.action = lambda pid=p["id"]: s.drop_local(pid)
                else:
                    rem.action = None
                swp.action = (lambda pid=p["id"]: s.swap(pid)) if local else None
                swp.enabled = room
                swp.rect.x = self.row_rect(team, i).right - (178 if rem.action else 132)

    def draw(self, s):
        t = self.scene.time
        ses = self.session
        s.blit(self.bg, (0, 0))
        self.scene.draw_top(s)
        ui.text(s, "Αλλαγή ομάδων", (WIDTH // 2, 34), 30, A.INK)
        host_name = ses.name if self.host else ses.host_name
        ip = ses.ip if self.host else ses.host_ip
        ui.text(s, f"Γήπεδο {host_name}  ·  διεύθυνση {ip}", (WIDTH // 2, 70), 17, A.GREY, bold=False)
        c = self.CARD
        A.card(s, c)
        ui.text(s, "εναντίον", (c.centerx, c.y + 58), 18, A.GREY, bold=False)
        mine = ses.mine()
        for team in L.TEAMS:
            x = self.col_x[team]
            col = A.TEAM[team]
            head = pygame.Rect(x, c.y + 30, self.COL_W, 56)
            pygame.draw.rect(s, ui.shade(col, 0.7), head.move(0, 4), border_radius=16)
            pygame.draw.rect(s, col, head, border_radius=16)
            ui.text(s, "ΜΠΛΕ ΟΜΑΔΑ" if team == L.BLUE else "ΚΙΤΡΙΝΗ ΟΜΑΔΑ", head.center, 24, A.TEAM_FG[team])
            ui.text(s, "φυλάει το μπλε τέρμα" if team == L.BLUE else "φυλάει το κίτρινο τέρμα",
                    (head.centerx, head.bottom + 22), 15, A.GREY, bold=False)
            ps = self.team_list(team)
            for i in range(L.MAX_TEAM):
                row = self.row_rect(team, i)
                p = ps[i] if i < len(ps) else None
                if p is None:
                    self._empty_row(s, row, team, i, t, first=i == len(ps))
                elif p["id"] in mine:
                    self._my_row(s, row, team, i, p, mine, t)
                else:
                    self._player_row(s, row, team, i, p, t)
        if self.btn_second.action:
            self._second_button(s, t)
        pygame.draw.line(s, (226, 230, 238), (c.x + 40, c.y + 458), (c.right - 40, c.y + 458), 2)
        ui.text(s, "Διάρκεια αγώνα:", (c.x + 50, c.y + 526), 21, A.INK, anchor="midleft")
        mins = ses.minutes
        for m, r in zip(L.MINUTES, self.min_rects):
            A.chip(s, r, f"{m} λεπτά", mins == m, enabled=self.host, hover=self.host and r.collidepoint(self.scene.mouse))
        if self.host:
            self.btn_start.draw(s, t)
            if not self.btn_start.enabled:
                A.fit_text(s, "Χρειάζεται ένα R2 σε κάθε ομάδα (πρόσθεσε ρομπότ).",
                           (self.btn_start.rect.centerx, c.y + 466), 14, (200, 100, 40), 360)
        else:
            box = pygame.Rect(c.right - 50 - 330, c.y + 480, 330, 92)
            pygame.draw.rect(s, (236, 246, 238), box, border_radius=18)
            pygame.draw.rect(s, (160, 210, 175), box, 2, border_radius=18)
            A.icon_whistle(s, (box.x + 44, box.centery), 52, A.GREEN_BTN)
            ui.text(s, "Τον αγώνα τον ξεκινάει:", (box.x + 84, box.y + 30), 16, A.GREY, anchor="midleft", bold=False)
            A.fit_text(s, ses.host_name, (box.x + 84, box.y + 62), 24, A.INK, box.w - 100, anchor="midleft")
        if self.second_open:
            self._draw_second(s, t)

    def _empty_row(self, s, row, team, i, t, first):
        pygame.draw.rect(s, (250, 251, 253), row, border_radius=14)
        dash = (200, 206, 218)
        for k in range(0, row.w, 18):
            pygame.draw.line(s, dash, (row.x + k, row.y), (row.x + min(k + 9, row.w), row.y), 2)
            pygame.draw.line(s, dash, (row.x + k, row.bottom - 1), (row.x + min(k + 9, row.w), row.bottom - 1), 2)
        pygame.draw.line(s, dash, row.topleft, row.bottomleft, 2)
        pygame.draw.line(s, dash, (row.right - 1, row.y), (row.right - 1, row.bottom), 2)
        ui.text(s, "κενή θέση", (row.x + 26, row.centery), 19, (160, 166, 180), anchor="midleft", bold=False)
        add, _ = self.slot_btns[(team, i)]
        if self.host and first and add.action:
            add.draw(s, t)
            face = add.rect.move(0, 5 if add.pressed else 0)
            ui.icon_plus(s, (face.x + 30, face.centery), 30, (255, 255, 255))
            ui.text(s, "ρομπότ", (face.x + 50, face.centery), 18, (255, 255, 255), anchor="midleft")

    @staticmethod
    def _avatar(s, row, team, faded=False):
        img = pygame.Surface((70, 70), pygame.SRCALPHA)
        ui.circle(img, ui.mix(A.TEAM[team], (255, 255, 255), 0.5), (35, 35), 28)
        A.r2art.draw_robot(img, (35, 35), 48, 0, A.LED[team])
        if faded:
            img.set_alpha(150)
        s.blit(img, img.get_rect(center=(row.x + 40, row.centery)))

    def _my_row(self, s, row, team, i, p, mine, t):
        """Παίκτης αυτού του υπολογιστή: όνομα, ποια πλήκτρα (αν είναι δύο), «άλλαξε» και (ο δεύτερος) ✕."""
        pygame.draw.rect(s, (255, 251, 232), row, border_radius=14)
        pygame.draw.rect(s, (255, 214, 60), row, 3, border_radius=14)
        self._avatar(s, row, team)
        swp = self.swap_btns[(team, i)]
        _, rem = self.slot_btns[(team, i)]
        max_w = swp.rect.x - 12 - (row.x + 82)
        A.fit_text(s, p["name"], (row.x + 82, row.centery - 10), 24, A.INK, max_w, anchor="midleft")
        if len(mine) < 2:
            sub = "εσύ"
        else:
            sub = "W A S D και Space" if p["id"] == mine[0] else "βελάκια και Enter"
        A.fit_text(s, sub, (row.x + 82, row.centery + 16), 15, A.TITLE, max_w, anchor="midleft")
        swp.draw(s, t)
        face = swp.rect.move(0, 5 if swp.pressed else 0)
        A.icon_swap(s, (face.x + 26, face.centery), 32, (255, 255, 255))
        ui.text(s, "άλλαξε", (face.x + 46, face.centery), 17, (255, 255, 255), anchor="midleft")
        if rem.action:
            rem.draw(s, t)

    def _player_row(self, s, row, team, i, p, t):
        bot = bool(p.get("bot"))
        pygame.draw.rect(s, (246, 248, 252), row, border_radius=14)
        pygame.draw.rect(s, (222, 228, 238), row, 2, border_radius=14)
        self._avatar(s, row, team, faded=bot)
        r = A.fit_text(s, p["name"], (row.x + 82, row.centery), 24, A.GREY if bot else A.INK, 190, anchor="midleft")
        if p.get("host"):
            pill = pygame.Rect(row.right - 196, row.centery - 15, 184, 30)
            pygame.draw.rect(s, (236, 246, 238), pill, border_radius=15)
            A.icon_whistle(s, (pill.x + 20, pill.centery + 1), 26, A.GREEN_BTN)
            ui.text(s, "έφτιαξε το γήπεδο", (pill.x + 38, pill.centery), 15, A.GREEN_BTN, anchor="midleft")
        if bot:
            A.monitor(s, (r.right + 22, row.centery + 2), 26)
            ui.text(s, "παίζει ο υπολογιστής", (r.right + 44, row.centery + 1), 15, A.GREY, anchor="midleft",
                    bold=False)
            _, rem = self.slot_btns[(team, i)]
            if rem.action:
                rem.draw(s, t)

    def _second_button(self, s, t):
        b = self.btn_second
        b.draw(s, t)
        face = b.rect.move(0, 5 if b.pressed else 0)
        fg = (255, 255, 255)
        ui.icon_plus(s, (face.x + 36, face.centery), 34, fg)
        ui.text(s, "Δεύτερος παίκτης εδώ", (face.x + 64, face.centery - 10), 20, fg, anchor="midleft")
        sub = "στο ίδιο πληκτρολόγιο" if b.enabled else "το γήπεδο είναι γεμάτο"
        ui.text(s, sub, (face.x + 64, face.centery + 15), 15, fg, anchor="midleft", bold=False)

    def _draw_second(self, s, t):
        """Το παράθυρο του δεύτερου παίκτη: ποιος παίζει με ποια πλήκτρα, και το όνομα του δεύτερου."""
        A.dim(s, 150)
        P = self.SECOND_CARD
        A.card(s, P)
        ui.text(s, "Δεύτερος παίκτης εδώ", (P.centerx, P.y + 44), 30, A.TITLE, shadow=A.TITLE_SHADOW)
        ui.text(s, "Δύο παιδιά σε αυτόν τον υπολογιστή, στο ίδιο πληκτρολόγιο.", (P.centerx, P.y + 86), 17,
                A.GREY, bold=False)
        tint = (120, 130, 150)
        for k, (letters, kick) in enumerate((("WASD", "Space"), (None, "Enter"))):
            box = pygame.Rect(P.x + 30 + k * 320, P.y + 112, 300, 196)
            pygame.draw.rect(s, (246, 248, 252), box, border_radius=18)
            pygame.draw.rect(s, (222, 228, 238), box, 2, border_radius=18)
            top = pygame.Rect(box.x + 20, box.y + 14, box.w - 40, 46)
            if k == 0:
                A.fit_text(s, self.first_name(), top.center, 24, A.INK, top.w)
            else:
                A.text_box(s, top, self.second_name, True, "το όνομα του δεύτερου", t, self.warn)
            A.key_cluster(s, (box.x + 88, box.y + 122), letters, tint)
            A.keycap(s, (box.x + 222, box.y + 112), kick, w=96, h=34, size=15, tint=tint)
            ui.text(s, "κλωτσιά", (box.x + 222, box.y + 146), 15, A.GREY, bold=False)
            ui.text(s, "οδήγηση", (box.x + 88, box.y + 176), 15, A.GREY, bold=False)
        self.btn_in.enabled = bool(net.clean_name(self.second_name))
        self.btn_in.draw(s, t)
        self.btn_no.draw(s, t)


# ------------------------------------------------------------- 5. ο αγώνας
class MatchPage(Page):
    END_CARD = pygame.Rect(300, 116, 680, 588)
    ASK_CARD = pygame.Rect(WIDTH // 2 - 320, 240, 640, 300)

    def __init__(self, scene, session):
        super().__init__(scene)
        self.session = session
        self.role = session.role
        self.confetti = fx.Confetti()
        self.ask = None             # None, "pause" (εδώ) ή "leave" (δίκτυο)
        self.view = None
        self._reset()
        c = self.END_CARD
        mid_label = "Αλλαγή ομάδων" if self.role == "host" else "Πίσω"
        self.btn_again = B((c.centerx - 285, c.y + 462, 170, 100), "Ξανά", ui.icon_again, A.ORANGE_BTN, self.again,
                           size=20)
        self.btn_again.pulse = True
        self.btn_mid = B((c.centerx - 85, c.y + 462, 170, 100), mid_label,
                         A.icon_swap if self.role == "host" else ui.icon_prev, A.BLUE_BTN, self.middle,
                         size=17 if self.role == "host" else 20)
        self.btn_quit = B((c.centerx + 115, c.y + 462, 170, 100), "Μενού", HOME, A.RED_BTN, self.menu, size=20)
        if self.role == "client":
            self.btn_quit.rect.centerx = c.centerx
        P = self.ASK_CARD
        self.btn_stay = B((P.centerx - 200, P.bottom - 120, 180, 96), "Συνέχεια", ui.icon_play,
                          A.GREEN_BTN, self.stay, size=18)
        self.btn_go = B((P.centerx + 20, P.bottom - 120, 180, 96), "Φεύγω", HOME, A.RED_BTN, self.scene.to_menu,
                        size=18)

    def _reset(self):
        self.match_no = self.session.match_no
        self.seen_goals = 0
        self.banner = None
        self.end_t = None
        self.spot_t = -9.0
        self.trail = []
        self.flash = None
        self.flash_t = -9.0
        self.last_sound = {}
        self.confetti.clear()

    # ---------------------------------------------------------- ενέργειες
    def again(self):
        self.session.again()
        self.play("whistle", 0.8)
        self._reset()

    def middle(self):
        if self.role == "host":
            self.session.to_lobby()
            self.scene.go(LobbyPage(self.scene, self.session))
        else:
            p = self.scene.prefs
            self.scene.go(SetupPage(self.scene, self.session.mode))
            p["level"] = getattr(self.session, "level", p["level"])

    def menu(self):
        if self.role == "local":
            self.scene.to_menu()
        else:
            self.ask = "leave"

    def stay(self):
        self.ask = None

    def leave(self):
        self.session.close()

    # ---------------------------------------------------------- σελίδα
    def modal(self):
        return self.ask is not None

    def end_visible(self):
        return self.end_t is not None and self.scene.time - self.end_t >= END_AFTER

    def buttons(self):
        if self.ask:
            return [self.btn_stay, self.btn_go]
        if self.end_visible():
            if self.role == "client":
                return [self.btn_quit]
            return [self.btn_again, self.btn_mid, self.btn_quit]
        return []

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            if self.ask:
                self.ask = None
            else:
                self.ask = "pause" if self.role == "local" else "leave"
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.end_visible():
            if self.role != "client" and not self.ask:
                self.again()

    def my_inputs(self):
        """{id: Input} για τους παίκτες αυτού του υπολογιστή: ένας με όλα τα πλήκτρα,
        ή δύο (ο πρώτος με W A S D και Space, ο δεύτερος με τα βελάκια και Enter)."""
        ids = self.session.mine()
        sc = self.scene
        if len(ids) >= 2:
            out = {ids[0]: sc.pad("left"), ids[1]: sc.pad("right")}
        else:
            out = {pid: sc.pad("one") for pid in ids}
        if self.ask:
            out = {pid: inp.still() for pid, inp in out.items()}
        return out

    def update(self, dt):
        ses = self.session
        if self.role == "local":
            events = [] if self.ask == "pause" else ses.update(dt, self.scene)
        else:
            events = ses.update(dt, self.my_inputs())
        if self.role == "client":
            if ses.state == "closed":
                self.scene.go(NetListPage(self.scene, ses.error))
                return
            if ses.state == "lobby":
                self.scene.go(LobbyPage(self.scene, ses))
                return
        if ses.match_no != self.match_no:
            self._reset()
        self._sounds(events)
        view = ses.view()
        if view is None:
            return
        self.view = view
        goals = view.get("goals", [])
        if len(goals) > self.seen_goals:
            self.seen_goals = len(goals)
            self._goal(goals[-1], view["sc"])
        if view["ph"] == "end" and self.end_t is None:
            self.end_t = self.scene.time
        bx, by = A.to_screen(*view["ball"])
        self.trail = (self.trail + [(bx, by)])[-5:]
        self.confetti.update(dt, self.scene.time, HEIGHT)

    def _sounds(self, events):
        now = self.scene.time
        for name, k in events:
            if name in ("kick", "wall"):
                if now - self.last_sound.get(name, -1) < 0.09:
                    continue
                self.last_sound[name] = now
                if name == "kick":
                    self.play("kick", 0.25 + 0.75 * k)
                else:
                    self.play("thud", 0.15 + 0.4 * k)
            elif name == "shoot":
                self.play("shoot", 0.6)
            elif name == "count":
                self.play("beep", 0.6)
            elif name == "go":
                self.play("whistle", 0.8)
            elif name == "goal":
                self.play("goal", 0.9)
            elif name == "end":
                self.play("whistle_end", 0.9)
            elif name == "spot":
                self.spot_t = now
                self.play("pick", 0.6)

    def _goal(self, goal, score):
        team, name, own = goal
        tname = "Μπλε" if team == L.BLUE else "Κίτρινη"
        who = "Αυτογκόλ" if own else (name or tname)
        self.banner = fx.Banner("ΓΚΟΛ!", f"{who} · Μπλε {score[0]} – {score[1]} Κίτρινη", stay=2.2,
                                icon=lambda img, p: A.ball(img, (p[0], p[1] + 2), 22))
        self.banner.show(self.scene.time)
        self.confetti.COLORS = ([A.BLUE, (255, 255, 255), (120, 180, 255), (30, 80, 180)] if team == L.BLUE
                                else [A.YELLOW, (255, 255, 255), (255, 226, 120), (220, 150, 20)])
        self.confetti.burst(WIDTH, 150)
        self.flash, self.flash_t = team, self.scene.time

    # ---------------------------------------------------------- ζωγραφική
    def draw(self, s):
        t = self.scene.time
        s.blit(A.field(), (0, 0))
        v = self.view
        if v is None:
            self.scene.draw_top(s)
            ui.text(s, "Περιμένω τον αγώνα…", (WIDTH // 2, HEIGHT // 2), 30, (255, 255, 255), shadow=A.INK)
            return
        roster = self.session.roster()
        tags = {}                   # τι γράφει το συννεφάκι πάνω από το δικό σου R2 (αλλιώς «ΕΣΥ»)
        if self.role == "local":
            mine = self.session.mine
        else:
            ids = self.session.mine()
            mine = set(ids)
            if len(ids) >= 2:
                tags = {ids[0]: "W A S D", ids[1]: "ΒΕΛΑΚΙΑ"}
        ph, pt = v["ph"], v["pt"]
        if ph == "goal" and v.get("goals"):
            A.goal_glow(s, v["goals"][-1][0], 0.6 + 0.4 * math.sin(t * 8) ** 2)
        robots = sorted(v["r"], key=lambda r: r[2])
        for r in robots:
            p = roster.get(r[0])
            if p is None:
                continue
            A.robot(s, A.to_screen(r[1], r[2]), A.screen_angle(r[3]), p["team"], me=r[0] in mine,
                    kick=bool(r[4]), time=t)
        bx, by = A.to_screen(*v["ball"])
        fast = len(self.trail) >= 2 and math.hypot(self.trail[-1][0] - self.trail[-2][0],
                                                   self.trail[-1][1] - self.trail[-2][1]) > 6
        A.ball(s, (bx, by), trail=self.trail[:-1] if fast else None)
        show_me = ph == "count" or (ph == "play" and pt < 3.0)
        for r in robots:
            p = roster.get(r[0])
            if p is None:
                continue
            x, y = A.to_screen(r[1], r[2])
            A.name_tag(s, (x, y - L.ROBOT_SIZE * 0.95), p["team"], p["name"], me=r[0] in mine,
                       bot=bool(p.get("bot")), show_me=show_me and p["name"] != "ΕΣΥ", tag=tags.get(r[0], "ΕΣΥ"))
        self._draw_top(s, v, t)
        if ph == "count":
            n = max(1, math.ceil(L.COUNT_TIME - pt))
            frac = (L.COUNT_TIME - pt) - (n - 1)
            self._big(s, str(n), 0.75 + 0.35 * frac)
        elif ph == "play" and pt < 0.8:
            self._big(s, "Πάμε!", 1.0, wide=True)
        if self.banner:
            self.banner.draw(s, t, (WIDTH // 2, 370))
        self.confetti.draw(s)
        if t - self.spot_t < 2.6:
            box = pygame.Rect(0, 0, 520, 46)
            box.center = (WIDTH // 2, A.CARPET.bottom - 40)
            pygame.draw.rect(s, (255, 255, 255), box, border_radius=14)
            pygame.draw.rect(s, (240, 170, 100), box, 2, border_radius=14)
            ui.text(s, "Η μπάλα κόλλησε: πάει σε ουδέτερο σημείο.", box.center, 18, (170, 80, 20))
        if self.end_visible():
            self._draw_end(s, v, t)
        if self.ask:
            self._draw_ask(s, t)

    def _draw_top(self, s, v, t):
        A.top_bar(s)
        ses = self.session
        if self.role == "local":
            if ses.mode == "pc":
                A.r2art.draw_robot(s, (50, 46), 50, 90, A.LED[L.BLUE])
                ui.text(s, "Με τον υπολογιστή", (90, 36), 22, A.INK, anchor="midleft")
                ui.text(s, f"αντίπαλος: {LEVEL_NAMES.get(ses.level, '')}", (90, 62), 15, A.GREY, anchor="midleft",
                        bold=False)
            else:
                A.r2art.draw_robot(s, (36, 46), 40, 90, A.LED[L.BLUE])
                A.r2art.draw_robot(s, (72, 46), 40, 270, A.LED[L.YELLOW])
                ui.text(s, "Δύο παίκτες εδώ", (104, 36), 22, A.INK, anchor="midleft")
                ui.text(s, "W A S D και βελάκια", (104, 62), 15, A.GREY, anchor="midleft", bold=False)
        else:
            A.icon_net(s, (52, 46), 70, (90, 100, 120))
            name = ses.name if self.role == "host" else ses.host_name
            ui.text(s, f"Γήπεδο {name}", (98, 36), 22, A.INK, anchor="midleft")
            n = ses.humans()
            ui.text(s, f"{n} {'παιδί' if n == 1 else 'παιδιά'} στο δίκτυο", (98, 62), 15, A.GREY,
                    anchor="midleft", bold=False)
        flash = self.flash if t - self.flash_t < 2.5 else None
        A.scoreboard(s, v["sc"][0], v["sc"][1], v["clk"], flash, t)
        for b in self.scene.top_buttons():
            b.draw(s, t)

    @staticmethod
    def _big(s, text, scale, wide=False):
        size = round(110 * scale)
        img = ui.font(size).render(text, True, (255, 255, 255))
        sh = ui.font(size).render(text, True, (30, 60, 40))
        c = A.CARPET.center
        w = max(img.get_width() + 60, 170)
        bg = pygame.Surface((w, img.get_height() + 30), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 40, 30, 120), bg.get_rect(), border_radius=40)
        s.blit(bg, bg.get_rect(center=c))
        s.blit(sh, sh.get_rect(center=(c[0] + 4, c[1] + 5)))
        s.blit(img, img.get_rect(center=c))

    def _draw_end(self, s, v, t):
        A.dim(s, 150)
        c = self.END_CARD
        A.card(s, c)
        cx = c.centerx
        sb, sy = v["sc"]
        winner = L.BLUE if sb > sy else (L.YELLOW if sy > sb else None)
        if winner:
            A.trophy(s, (cx, c.y + 70), 96, A.TEAM[winner])
        else:
            A.handshake(s, (cx, c.y + 70), 90)
        ui.text(s, "Τέλος αγώνα!", (cx, c.y + 150), 44, A.TITLE, shadow=A.TITLE_SHADOW)
        if self.role == "local" and self.session.mode == "pc":
            line = ("Μπράβο, νίκησες!" if winner == L.BLUE else
                    ("Νίκησε ο υπολογιστής. Πάμε ξανά;" if winner else "Ισοπαλία!"))
        else:
            line = ("Νίκησε η Μπλε ομάδα!" if winner == L.BLUE else
                    ("Νίκησε η Κίτρινη ομάδα!" if winner else "Ισοπαλία!"))
        ui.text(s, line, (cx, c.y + 198), 28, A.TEAM[winner] if winner == L.BLUE else (
            ui.shade(A.YELLOW, 0.75) if winner else A.INK))
        for team, score, x in ((L.BLUE, sb, cx - 90), (L.YELLOW, sy, cx + 90)):
            r = pygame.Rect(0, 0, 120, 82)
            r.center = (x, c.y + 274)
            pygame.draw.rect(s, ui.shade(A.TEAM[team], 0.7), r.move(0, 5), border_radius=18)
            pygame.draw.rect(s, A.TEAM[team], r, border_radius=18)
            ui.text(s, str(score), r.center, 54, A.TEAM_FG[team])
        ui.text(s, "–", (cx, c.y + 272), 44, A.INK)
        goals = v.get("goals", [])
        if goals:
            ui.text(s, "Γκολ", (cx, c.y + 336), 18, A.GREY, bold=False)
        for team, x in ((L.BLUE, cx - 150), (L.YELLOW, cx + 150)):
            counts = {}
            for g_team, name, own in goals:
                if g_team == team:
                    key = "αυτογκόλ" if own else (name or "?")
                    counts[key] = counts.get(key, 0) + 1
            for i, (name, n) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1])[:3]):
                y = c.y + 370 + i * 30
                A.fit_text(s, name, (x - 20, y), 20, A.INK, 150, anchor="midright")
                for k in range(min(n, 5)):
                    A.ball(s, (x + 2 + k * 26, y), 10)
                if n > 5:
                    ui.text(s, f"x{n}", (x + 2 + 5 * 26, y), 16, A.GREY, anchor="midleft")
        if self.role == "client":
            A.fit_text(s, f"Τι θα γίνει μετά το διαλέγει όποιος έφτιαξε το γήπεδο ({self.session.host_name}).",
                       (cx, c.y + 448), 17, A.GREY, c.w - 50, bold=False)
            self.btn_quit.rect.y = c.y + 470
            self.btn_quit.draw(s, t)
        else:
            for b in (self.btn_again, self.btn_mid, self.btn_quit):
                b.draw(s, t)

    def _draw_ask(self, s, t):
        A.dim(s, 160)
        P = self.ASK_CARD
        A.card(s, P)
        if self.ask == "pause":
            ui.text(s, "Παύση", (P.centerx, P.y + 56), 40, A.TITLE, shadow=A.TITLE_SHADOW)
            ui.text(s, "Ο αγώνας περιμένει.", (P.centerx, P.y + 112), 20, A.GREY)
            self.btn_stay.label, self.btn_go.label = "Συνέχεια", "Μενού"
        else:
            ui.text(s, "Φεύγεις;", (P.centerx, P.y + 56), 40, A.TITLE, shadow=A.TITLE_SHADOW)
            text = ("Αν φύγεις, το γήπεδο κλείνει για όλους." if self.role == "host"
                    else "Αν φύγεις, το R2 σου βγαίνει από τον αγώνα.")
            ui.text(s, text, (P.centerx, P.y + 112), 20, A.GREY)
            self.btn_stay.label, self.btn_go.label = "Μένω", "Φεύγω"
        self.btn_stay.draw(s, t)
        self.btn_go.draw(s, t)
