"""Η αρχή των «Αποστολών Διάσωσης»: ποιος είσαι (Δάσκαλος, Μαθητές, Εξάσκηση), η είσοδος των μαθητών στο
μάθημα (ονόματα και αναζήτηση του υπολογιστή του δασκάλου) και η επιλογή πίστας στην Εξάσκηση."""
import math

import pygame

from core import ui
from core.app import HEIGHT, WIDTH, Scene
from games.line_follow import art as lf
from games.program import art as A
from . import art, net
from . import world as W

TOP = 60
INK, GREY, LIGHT = art.INK, art.GREY, art.LIGHT


def _cursor(hand, state):
    want = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
    if want != state:
        try:
            pygame.mouse.set_cursor(want)
        except (pygame.error, TypeError):
            pass
    return want


class _Page(Scene):
    """Κοινά: φόντο, πάνω μπάρα, κουμπιά με πάτημα/άφημα."""
    title = "Αποστολές Διάσωσης"
    sub = None

    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed = None
        self.room = art.room()
        self.btn_back = art.TextButton((WIDTH - 150, 8, 136, 44), "Πίσω", (120, 130, 150), self.back, 17,
                                       icon=art.icon_back)

    def back(self):
        from games.menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def buttons(self):
        return [self.btn_back]

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            for b in self.buttons():
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed = b
                    return
            self.click(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed = self.pressed, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.back()
        else:
            self.other(e)

    def click(self, pos):
        pass

    def other(self, e):
        pass

    def update(self, dt):
        self.time += dt
        for b in self.buttons():
            b.hover = b.enabled and b.contains(self.mouse)
        self.cursor = _cursor(any(b.hover for b in self.buttons()) or self.hand(), self.cursor)

    def hand(self):
        return False

    def draw_base(self, s):
        s.blit(self.room, (0, 0))
        pygame.draw.rect(s, art.WHITE, (0, 0, WIDTH, TOP))
        pygame.draw.line(s, art.LINE, (0, TOP), (WIDTH, TOP), 2)
        art.icon_flame(s, (34, TOP // 2), 34, None, self.time)
        r = ui.text(s, self.title, (60, TOP // 2), 25, art.TITLE, anchor="midleft")
        if self.sub:
            ui.text(s, self.sub, (r.right + 14, TOP // 2 + 2), 17, GREY, anchor="midleft", bold=False)
        for b in self.buttons():
            b.draw(s, self.time)


# ================================================================ αρχή
class StartScene(_Page):
    sub = "συνεργατικό παιχνίδι για όλη την τάξη"

    def __init__(self, app):
        super().__init__(app)
        w, h, gap = 360, 330, 30
        x0 = WIDTH // 2 - (3 * w + 2 * gap) // 2
        self.cards = [
            ("teacher", pygame.Rect(x0, 200, w, h), "Δάσκαλος", ["Φτιάχνω το μάθημα", "στον προβολέα"], art.TITLE),
            ("student", pygame.Rect(x0 + w + gap, 200, w, h), "Μαθητές", ["Μπαίνουμε στο μάθημα", "του δασκάλου"],
             art.BLUE),
            ("practice", pygame.Rect(x0 + 2 * (w + gap), 200, w, h), "Εξάσκηση", ["Παίζουμε μόνοι μας", "σε έναν υπολογιστή"],
             art.OK),
        ]

    def hand(self):
        return any(r.collidepoint(self.mouse) for _, r, *_ in self.cards)

    def click(self, pos):
        for key, r, *_ in self.cards:
            if r.collidepoint(pos):
                self.app.sounds.play("button")
                if key == "teacher":
                    from .teacher import TeacherScene
                    self.app.switch(TeacherScene(self.app))
                elif key == "student":
                    self.app.switch(JoinScene(self.app))
                else:
                    self.app.switch(PracticeScene(self.app))
                return

    def draw(self, s):
        self.draw_base(s)
        ui.text(s, "Ποιος παίζει σε αυτόν τον υπολογιστή;", (WIDTH // 2, 140), 30, INK)
        for key, r, title, lines, col in self.cards:
            hover = r.collidepoint(self.mouse)
            rr = r.move(0, -4 if hover else 0)
            ui.panel(s, rr, col, radius=24)
            inner = pygame.Rect(rr.x + 14, rr.y + 14, rr.w - 28, 170)
            pygame.draw.rect(s, art.WHITE, inner, border_radius=18)
            c = inner.center
            if key == "teacher":
                scr = pygame.Rect(0, 0, 220, 124)
                scr.center = (c[0], c[1] - 8)
                pygame.draw.rect(s, (60, 70, 86), scr, border_radius=8)
                inner2 = scr.inflate(-14, -14)
                pygame.draw.rect(s, (150, 206, 248), inner2, border_radius=4)
                old = s.get_clip()
                s.set_clip(inner2)
                _island(s, (inner2.x + 4, inner2.y + 18), 24, 7, 3, self.time)
                s.set_clip(old)
                pygame.draw.rect(s, (60, 70, 86), (c[0] - 40, scr.bottom + 6, 80, 8), border_radius=3)
            elif key == "student":
                _island(s, (c[0] - 118, c[1] - 52), 44, 4, 2, self.time, robots=2)
            else:
                _island(s, (c[0] - 100, c[1] - 52), 46, 3, 2, self.time, robots=1)
            ui.text(s, title, (rr.centerx, rr.y + 218), 32, art.WHITE, shadow=ui.shade(col, 0.6))
            for i, ln in enumerate(lines):
                ui.text(s, ln, (rr.centerx, rr.y + 262 + i * 26), 18, art.WHITE, bold=False)


# ================================================================ ονόματα (κοινό)
class _Names:
    """Το κουτάκι για το όνομα (αν κάθονται δύο παιδιά, γράφουν και τα δύο ονόματα εδώ)."""

    def __init__(self, x, y, w):
        self.boxes = [pygame.Rect(x, y, w, 52)]
        self.values = [""]
        self.focus = 0

    def click(self, pos):
        for i, b in enumerate(self.boxes):
            if b.collidepoint(pos):
                self.focus = i
                return True
        return False

    def event(self, e):
        if e.type == pygame.TEXTINPUT:
            extra = "".join(ch for ch in e.text if ch.isalnum() or ch in " -'")
            v = (self.values[self.focus] + extra).lstrip()[:net.NAME_MAX]
            self.values[self.focus] = v[:1].upper() + v[1:]
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.values[self.focus] = self.values[self.focus][:-1]
                return True
        return False

    def names(self):
        return [net.clean_name(v) for v in self.values if net.clean_name(v)]

    def name(self):
        n = self.names()
        return n[0] if n else ""

    def hand(self, pos):
        return any(b.collidepoint(pos) for b in self.boxes)

    def draw(self, s, t):
        labels = ("Το όνομά σας (αν είστε δύο, γράψτε και τα δύο)",)
        for i, (b, lab) in enumerate(zip(self.boxes, labels)):
            ui.text(s, lab, (b.x + 4, b.y - 16), 15, GREY, anchor="midleft")
            on = i == self.focus
            pygame.draw.rect(s, art.WHITE, b, border_radius=12)
            pygame.draw.rect(s, art.BLUE if on else (206, 212, 222), b, width=3 if on else 2, border_radius=12)
            r = ui.text(s, self.values[i], (b.x + 16, b.centery), 22, INK, anchor="midleft")
            if on and int(t * 2) % 2 == 0:
                x = r.right + 3 if self.values[i] else b.x + 16
                pygame.draw.line(s, INK, (x, b.y + 12), (x, b.bottom - 12), 2)


# ================================================================ μαθητές: είσοδος στο μάθημα
class JoinScene(_Page):
    sub = "Μαθητές: μπαίνουμε στο μάθημα"
    ROWS = 5

    def __init__(self, app):
        super().__init__(app)
        self.names = _Names(80, 178, 420)
        try:
            self.finder = net.Finder(port=net.DISC_PORT)
        except OSError:
            self.finder = None
        self.joining = None
        self.message = None
        self.addr_open = False
        self.addr_text = ""
        self.row_btns = [art.TextButton((0, 0, 170, 48), "Μπαίνουμε", art.OK, None, 18) for _ in range(self.ROWS)]
        self.btn_addr = art.TextButton((560, 600, 250, 48), "Με διεύθυνση…", (120, 130, 150), self.open_addr, 17)
        self.btn_go = art.TextButton((0, 0, 150, 48), "Σύνδεση", art.OK, self.join_addr, 18)
        self.btn_cancel = art.TextButton((0, 0, 130, 48), "Άκυρο", (120, 130, 150), self.close_addr, 17)
        self.lessons = []

    def back(self):
        if self.finder:
            self.finder.close()
        if self.joining:
            self.joining.close()
        self.app.switch(StartScene(self.app))

    def buttons(self):
        if self.joining:
            return [self.btn_back]
        if self.addr_open:
            return [self.btn_back, self.btn_go, self.btn_cancel]
        return [self.btn_back, self.btn_addr] + [b for b in self.row_btns if b.action]

    def open_addr(self):
        self.addr_open = True

    def close_addr(self):
        self.addr_open = False

    def join_addr(self):
        if net.valid_ip(self.addr_text):
            self.join({"addr": self.addr_text.strip(), "port": net.GAME_PORT, "name": self.addr_text})
            self.addr_open = False
        else:
            self.message = ("Γράψτε διεύθυνση σαν 192.168.1.10", self.time)

    def join(self, lesson):
        names = self.names.names()
        if not names:
            self.message = ("Γράψτε πρώτα το όνομά σας!", self.time)
            self.names.focus = 0
            self.app.sounds.play("deny", 0.6)
            return
        self.joining = net.Client(self.names.name(), lesson["addr"], lesson["port"])
        self.message = None

    def click(self, pos):
        if not self.addr_open:
            self.names.click(pos)

    def other(self, e):
        if self.joining:
            return
        if self.addr_open:
            if e.type == pygame.TEXTINPUT:
                extra = "".join(ch for ch in e.text if ch.isdigit() or ch in ".,")
                self.addr_text = (self.addr_text + extra.replace(",", "."))[:15]
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_BACKSPACE:
                self.addr_text = self.addr_text[:-1]
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.join_addr()
            return
        if self.names.event(e):
            return
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and len(self.lessons) == 1:
            self.join(self.lessons[0])

    def hand(self):
        return self.names.hand(self.mouse) and not self.addr_open

    def update(self, dt):
        if self.finder:
            self.finder.poll()
            self.lessons = [f for f in self.finder.fields() if f.get("game") == "rescue2"]
        if self.joining:
            self.joining.poll()
            if self.joining.state in ("lobby", "level"):
                link, self.joining = self.joining, None
                if self.finder:
                    self.finder.close()
                from .student import StudentScene
                self.app.switch(StudentScene(self.app, link))
                return
            if self.joining.state == "closed":
                self.message = (self.joining.error or "Δεν μπόρεσα να μπω στο μάθημα.", self.time)
                self.joining = None
                self.app.sounds.play("deny", 0.6)
        for i, b in enumerate(self.row_btns):
            if i < len(self.lessons):
                lesson = self.lessons[i]
                b.action = (lambda f=lesson: self.join(f))
                b.rect.topleft = (1060, 168 + i * 78)
                b.enabled = lesson.get("v") == net.VERSION
            else:
                b.action = None
        super().update(dt)

    def draw(self, s):
        self.draw_base(s)
        left = pygame.Rect(40, 84, 500, 320)
        ui.panel(s, left, art.WHITE, radius=18)
        ui.text(s, "Ποιοι είστε;", (left.x + 24, left.y + 28), 22, INK, anchor="midleft")
        self.names.draw(s, self.time)
        tip = pygame.Rect(40, 420, 500, 160)
        ui.panel(s, tip, (248, 250, 253), radius=18, border=art.LINE, shadow=False)
        for i, ln in enumerate(("Κάθε υπολογιστής έχει ένα οικόπεδο στο δάσος.", "Οι διπλανοί σας στην αίθουσα",
                                "είναι διπλανοί σας και στο δάσος:", "βοηθήστε ο ένας τον άλλο!")):
            ui.text(s, ln, (tip.x + 22, tip.y + 30 + i * 30), 16, GREY if i else INK, anchor="midleft", bold=i == 0)
        right = pygame.Rect(560, 84, 690, 500)
        ui.panel(s, right, art.WHITE, radius=18)
        ui.text(s, "Τα μαθήματα στο δίκτυο", (right.x + 24, right.y + 28), 22, INK, anchor="midleft")
        if not self.lessons:
            ui.text(s, "Ψάχνουμε τον υπολογιστή του δασκάλου…", (right.centerx, right.y + 200), 20, GREY)
            for i in range(3):
                ui.circle(s, art.BLUE, (right.centerx - 30 + i * 30, right.y + 250 + math.sin(self.time * 3 + i) * 6), 8)
            ui.text(s, "Ο δάσκαλος ανοίγει «Αποστολές Διάσωσης → Δάσκαλος».", (right.centerx, right.y + 310), 16,
                    LIGHT, bold=False)
        for i, f in enumerate(self.lessons[:self.ROWS]):
            row = pygame.Rect(right.x + 16, right.y + 60 + i * 78, right.w - 32, 66)
            pygame.draw.rect(s, (244, 247, 252), row, border_radius=14)
            art.icon_flame(s, (row.x + 34, row.centery), 30, None, self.time + i)
            ui.text(s, f"Μάθημα: {f.get('name', '')}", (row.x + 64, row.centery - 10), 21, INK, anchor="midleft")
            n = f.get("n", [0])[0]
            sub = f"{n} υπολογιστές μέσα" if f.get("v") == net.VERSION else f"άλλη έκδοση ({f.get('v')})"
            ui.text(s, sub, (row.x + 64, row.centery + 14), 15, GREY, anchor="midleft", bold=False)
        for b in self.buttons():
            b.draw(s, self.time)
        if self.addr_open:
            self._draw_addr(s)
        if self.joining:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((20, 30, 50, 150))
            s.blit(veil, (0, 0))
            ui.text(s, "Συνδεόμαστε…", (WIDTH // 2, HEIGHT // 2), 34, art.WHITE)
        if self.message and self.time - self.message[1] < 6:
            art.chip(s, self.message[0], (WIDTH // 2, 676), bg=art.STUCK, size=17, anchor="center")

    def _draw_addr(self, s):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 30, 50, 150))
        s.blit(veil, (0, 0))
        card = pygame.Rect(WIDTH // 2 - 280, 220, 560, 260)
        ui.panel(s, card, art.WHITE, radius=20)
        ui.text(s, "Η διεύθυνση του υπολογιστή του δασκάλου", (card.centerx, card.y + 40), 20, INK)
        box = pygame.Rect(card.x + 60, card.y + 80, card.w - 120, 56)
        pygame.draw.rect(s, art.WHITE, box, border_radius=12)
        pygame.draw.rect(s, art.BLUE, box, width=3, border_radius=12)
        ui.text(s, self.addr_text or "π.χ. 192.168.1.10", box.center, 26, INK if self.addr_text else LIGHT)
        self.btn_go.rect.topleft = (card.centerx + 10, card.bottom - 76)
        self.btn_cancel.rect.topright = (card.centerx - 10, card.bottom - 76)
        self.btn_go.draw(s, self.time)
        self.btn_cancel.draw(s, self.time)


# ================================================================ εξάσκηση
class PracticeScene(_Page):
    sub = "Εξάσκηση σε έναν υπολογιστή"

    def __init__(self, app):
        super().__init__(app)
        self.names = _Names(80, 178, 400)
        self.cells = []
        y = 150
        no = 1
        for ch in W.CHAPTERS:
            ids = ch.get("levels") or [None] * ch.get("soon", 0)
            for i, lid in enumerate(ids):
                self.cells.append((ch, lid, no, pygame.Rect(800 + i * 64, y - 26, 54, 54)))
                no += 1
            y += 100

    def back(self):
        self.app.switch(StartScene(self.app))

    def hand(self):
        return self.names.hand(self.mouse) or any(lid and r.collidepoint(self.mouse) for _, lid, _, r in self.cells)

    def click(self, pos):
        if self.names.click(pos):
            return
        for ch, lid, no, r in self.cells:
            if lid and r.collidepoint(pos):
                link = net.Practice(self.names.name() or "Ομάδα")
                link.start(lid)
                from .student import StudentScene
                self.app.sounds.play("button")
                self.app.switch(StudentScene(self.app, link))
                return

    def other(self, e):
        self.names.event(e)

    def draw(self, s):
        self.draw_base(s)
        left = pygame.Rect(40, 84, 480, 320)
        ui.panel(s, left, art.WHITE, radius=18)
        ui.text(s, "Ποιος παίζει;", (left.x + 24, left.y + 28), 22, INK, anchor="midleft")
        self.names.draw(s, self.time)
        tip = pygame.Rect(40, 420, 480, 200)
        ui.panel(s, tip, (248, 250, 253), radius=18, border=art.LINE, shadow=False)
        for i, ln in enumerate(("Στην Εξάσκηση έχετε ένα οικόπεδο.", "Τα άλλα οικόπεδα έχουν αυτόματα R2,",
                                "σαν να παίζετε με την τάξη.", "Οδηγήστε με τα κουμπιά ή τα βελάκια.")):
            ui.text(s, ln, (tip.x + 22, tip.y + 30 + i * 32), 17, INK if i == 0 else GREY, anchor="midleft",
                    bold=i == 0)
        right = pygame.Rect(540, 84, 710, 470)
        ui.panel(s, right, art.WHITE, radius=18)
        ui.text(s, "Διάλεξε πίστα", (right.x + 24, right.y + 28), 22, INK, anchor="midleft")
        y = 150
        for ch in W.CHAPTERS:
            name, col = art.MODE[ch["mode"]]
            ui.text(s, name, (right.x + 30, y), 19, col, anchor="midleft")
            if not ch.get("levels"):
                ui.text(s, "σύντομα", (right.x + 30, y + 24), 13, LIGHT, anchor="midleft", bold=False)
            y += 100
        for ch, lid, no, r in self.cells:
            name, col = art.MODE[ch["mode"]]
            if lid:
                hover = r.collidepoint(self.mouse)
                pygame.draw.rect(s, ui.mix(col, art.WHITE, 0.15 if hover else 0), r, border_radius=14)
                ui.text(s, str(no), r.center, 20, art.WHITE)
            else:
                pygame.draw.rect(s, (236, 238, 242), r, border_radius=14)
                ui.text(s, str(no), r.center, 16, LIGHT)


def _island(s, origin, tw, cols, rows, time, robots=0):
    """Ένα νησάκι από κυβάκια για τις κάρτες της αρχής: νερό, πέτρα, φωτιά και R2."""
    from . import fire as FI
    g = lf.Geo(origin[0] + rows * tw * 0.46, origin[1] + tw, tw, tw * 0.46, tw * 0.8)
    for y in range(rows):
        for x in range(cols):
            if x == cols // 2 and y == rows - 1 and cols > 3:
                A.cube(s, g, x, y, -A.CUBE, -16, "water", 3, n=4)
            else:
                A.cube(s, g, x, y, -A.CUBE, 0, "grass", 3, n=4)
    A.tree(s, g, cols - 1, 0)
    A.cube(s, g, 1, 0, 0, A.CUBE * 0.5, (196, 192, 184), 3, 0.15, 0.85, 0.15, 0.85, n=4)
    if robots >= 1:
        lf.draw_robot(s, g, 0.5, rows - 0.5, 1, 0, led=(62, 132, 222), z=0)
    if robots >= 2:
        lf.draw_robot(s, g, cols - 0.5, rows - 0.5, -1, 0, led=(238, 146, 46), z=0)
    x, y = g.pt(cols - 0.5, 0.5, A.CUBE * 1.6)
    img = FI.flame_sprite(60 + FI.frame(time, 3), 12, 20, max(2, round(tw / 14)), 0.85)
    s.blit(img, img.get_rect(midbottom=(round(x), round(y))))


# ================================================================ μήνυμα (π.χ. τέλος σύνδεσης)
class MessageScene(_Page):
    def __init__(self, app, text):
        super().__init__(app)
        self.text = text

    def back(self):
        self.app.switch(StartScene(self.app))

    def draw(self, s):
        self.draw_base(s)
        card = pygame.Rect(WIDTH // 2 - 360, 230, 720, 220)
        ui.panel(s, card, art.WHITE, radius=20)
        for i, ln in enumerate(art.wrap(self.text, 22, card.w - 80)):
            ui.text(s, ln, (card.centerx, card.y + 70 + i * 34), 22, INK)
        ui.text(s, "Πατήστε «Πίσω» για να συνεχίσετε.", (card.centerx, card.bottom - 40), 16, GREY, bold=False)
