"""Η οθόνη των μαθητών (και της Εξάσκησης), στο ύφος του «Προγραμμάτισε».

Αριστερά ο χάρτης με όλη την ομάδα (το ποτάμι): το δικό τους οικόπεδο με κίτρινο περίγραμμα και τα R2 όλων
να κινούνται. Δεξιά:
- Χειριστήριο (κεφάλαιο 1): Μπροστά, Πίσω, Στρίψε αριστερά/δεξιά (ή τα βελάκια) και το πρόγραμμα που
  γράφεται μόνο του όσο οδηγούν. Πάνω: «Ξανά» (το οικόπεδο από την αρχή).
- Διόρθωσε / Γράψε: οι Εντολές και το πρόγραμμα, «Δοκιμή» (μόνο το δικό τους R2, εδώ) και «Έτοιμοι!». Όταν
  είναι όλοι έτοιμοι, όλα τα R2 τρέχουν μαζί· μετά τα αποτελέσματα και, αν χρειάζεται, νέος γύρος.
Πάνω δεξιά: «Όλο το δάσος».
"""
import math

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.maze import art as r2art
from games.program import code, logic as PL
from games.program.scene import FlagButton, bubble
from . import art, editor as E, net, sim as S, view as V, world as W

MAP = pygame.Rect(14, 104, 780, 604)
FULL = pygame.Rect(14, 104, 1252, 604)
RX, RW = 806, 460
KEYS = {pygame.K_UP: "forward", pygame.K_DOWN: "back", pygame.K_LEFT: "left", pygame.K_RIGHT: "right"}
WHY = {"tree": ["Ωχ! Δέντρο."], "rock": ["Ωχ! Βράχος."], "water": ["Ωχ! Νερό!"],
       "fence": ["Ο φράχτης!", "Μένεις στο οικόπεδό σου."], "stone": ["Το R2 σπρώχνει", "μόνο προς τα μπροστά."],
       "animal": ["Περνάει κάποιος!", "Περίμενε λίγο."], "branch": ["Το κλαδί είναι κάτω!", "Περίμενε τον γείτονα."],
       "fire": ["Φωτιά! Μην πλησιάζεις."], "bridge": ["Πέτρα στο γεφυράκι;", "Όχι!"],
       "heavy": ["Ο βράχος είναι βαρύς!", "Χρειάζεται και ο γείτονας."], "time": ["Το R2 περίμενε πολύ."],
       "noline": ["Δεν βρίσκω", "τη μαύρη γραμμή!"]}
DARK = art.INK


class Control:
    """Ένα κουμπί του χειριστηρίου."""

    def __init__(self, name, rect, color, icon, label, key):
        self.name, self.rect, self.color, self.icon, self.label, self.key = name, pygame.Rect(rect), color, icon, label, key
        self.flash = -9.0
        self.hover = False

    def draw(self, surf, time, enabled=True, blink=False):
        col = self.color if enabled else (178, 184, 196)
        pressed = enabled and time - self.flash < 0.18
        if blink and enabled:
            p = 0.5 + 0.5 * math.sin(time * 7)
            ui.glow(surf, self.rect.inflate(16 + 10 * p, 16 + 10 * p), (255, 214, 60), 120 + 120 * p, radius=22)
        r2art.ctrl_button(surf, self.rect, col, self.icon, [self.label], None, pressed, enabled and self.hover,
                          compact=True)


class ReadyButton(ui.Button):
    """Το «Έτοιμοι!»: μπλε, κίτρινο όταν είναι πατημένο, γκρι όταν δεν πατιέται."""

    def __init__(self, rect, action):
        super().__init__(rect, "Έτοιμοι!", None, art.BLUE, action)
        self.on = False

    def draw(self, s, time=0.0):
        r = self.rect
        if not self.enabled:
            col, base = (196, 200, 208), (168, 172, 182)
        elif self.on:
            col, base = (250, 196, 50), (196, 146, 20)
        else:
            col, base = art.BLUE, (40, 96, 170)
        if self.enabled and self.pulse and not self.on:
            p = 0.5 + 0.5 * math.sin(time * 6)
            ui.glow(s, r.inflate(14 + 10 * p, 14 + 10 * p), (255, 214, 60), 110 + 120 * p, radius=24)
        if self.hover and self.enabled:
            col = ui.mix(col, (255, 255, 255), 0.12)
        face = r.move(0, 6 if self.pressed else 0)
        pygame.draw.rect(s, ui.shade(base, 0.85), r.move(0, 6), border_radius=18)
        pygame.draw.rect(s, col, face, border_radius=18)
        pygame.draw.rect(s, ui.mix(col, (255, 255, 255), 0.3), (face.x + 12, face.y + 6, face.w - 24, 6), border_radius=3)
        d = (face.x + face.h // 2 + 4, face.centery)
        pygame.draw.circle(s, (255, 255, 255), d, face.h * 0.36)
        pygame.draw.lines(s, col, False, [(d[0] - 10, d[1] + 1), (d[0] - 3, d[1] + 8), (d[0] + 11, d[1] - 8)], 5)
        ui.text(s, "Έτοιμοι!", (d[0] + face.h * 0.48, face.centery), 28, (255, 255, 255), anchor="midleft")


class StudentScene(Scene):
    def __init__(self, app, link):
        super().__init__(app)
        self.link = link
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.room = art.room()
        self.confetti = fx.Confetti()
        self.level_no = None
        self.view = self.full = self.tr = None
        self.show_full = False
        self.message = None           # (γραμμές, πότε, χρώμα, πόσο κρατά)
        self.banner = None            # (κείμενο, πότε): μήνυμα του δασκάλου
        self.blink = None             # (κίνηση, ως πότε): βοήθεια «Επόμενη κίνηση»
        self.route_until = 0.0
        self.bump = None              # (θέση, πότε)
        self.last_pose = None
        self.confirm_exit = False
        self.pressed_btn = None
        self.done_seen = False
        B = ui.Button
        self.btn_again = B((14, 8, 92, 76), "Ξανά", ui.icon_again, art.ORANGE, self.reset)
        self.btn_forest = B((1056, 8, 124, 76), "Όλο το δάσος", art.icon_forest, art.TEAL, self.toggle_full,
                            label_size=15)
        self.btn_sound = B((1190, 8, 80, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.btn_yes = art.TextButton((WIDTH // 2 - 190, 400, 180, 64), "Ναι", art.STUCK, self.leave, 20)
        self.btn_no = art.TextButton((WIDTH // 2 + 10, 400, 180, 64), "Όχι", (120, 130, 150), self.close_confirm, 20)
        self.btn_next = art.TextButton((0, 0, 230, 60), "Επόμενη πίστα", art.BLUE, self.practice_next, 19,
                                       icon=lambda s, c, z, col: ui.icon_next(s, c, z, col))
        self.btn_retry = art.TextButton((0, 0, 170, 60), "Ξανά", art.ORANGE, self.practice_retry, 19)
        bw, bh, gap = 136, 56, 8
        x0, y0 = RX + RW // 2 - (3 * bw + 2 * gap) // 2, 104 + 44
        self.controls = [
            Control("forward", (x0 + bw + gap, y0, bw, bh), (0, 166, 186), r2art.arrow_up, "Μπροστά", pygame.K_UP),
            Control("back", (x0 + bw + gap, y0 + bh + gap, bw, bh), (0, 166, 186), r2art.arrow_down, "Πίσω",
                    pygame.K_DOWN),
            Control("left", (x0, y0 + bh + gap, bw, bh), (238, 128, 40), r2art.turn_left, "Στρίψε αριστερά",
                    pygame.K_LEFT),
            Control("right", (x0 + 2 * (bw + gap), y0 + bh + gap, bw, bh), (238, 128, 40), r2art.turn_right,
                    "Στρίψε δεξιά", pygame.K_RIGHT)]
        self.code_rect = pygame.Rect(RX, 286, RW, 708 - 286)
        self.codeview = code.CodeView((RX + 12, 286 + 46, RW - 24, self.code_rect.h - 96))
        self._rec_shown = None
        # κεφάλαια με πρόγραμμα
        self.editor = None
        self.ready = False
        self.test = None              # η «Δοκιμή»: ένα δάσος μόνο για εδώ
        self.test_tr = None
        self.test_view = None
        self.test_until = 0.0
        self.sent = None
        self.result_round = None
        self.run_prog = []
        self.btn_test = FlagButton((0, 0, 204, 62), self.do_test)
        self.btn_test.label = "Δοκιμή"
        self.btn_ready = ReadyButton((0, 0, 204, 62), self.toggle_ready)

    # ================================================================ βοηθητικά
    @property
    def practice(self):
        return isinstance(self.link, net.Practice)

    def forest(self):
        return self.link.forest

    def my_team(self):
        f = self.forest()
        return f.plots[self.link.k]["team"] if f and self.link.k in f.plots else None

    def editable(self):
        f = self.forest()
        return (f is not None and self.link.state == "level" and not self.link.frozen and not f.paused
                and not f.auto.get(self.link.k) and not f.done)

    @property
    def programming(self):
        return self.link.state == "level" and self.link.mode != "drive" and self.editor is not None

    def can_edit(self):
        L = self.link
        return (self.programming and L.phase == "plan" and not L.frozen and not L.paused and self.test is None
                and not (L.forest and L.forest.auto.get(L.k)))

    def buttons(self):
        if self.confirm_exit:
            return [self.btn_yes, self.btn_no]
        out = [self.btn_sound]
        if self.link.state == "level":
            if self.programming:
                out = [self.btn_forest, self.btn_sound]
                if not self.show_full:
                    out += [self.btn_test, self.btn_ready] + self.editor.buttons()
            else:
                out = [self.btn_again, self.btn_forest, self.btn_sound]
            if self.practice and self.link.done:
                out += [self.btn_next, self.btn_retry]
        return out

    def do_test(self):
        """«Δοκιμή»: τρέχει μόνο το δικό μας R2, εδώ, χωρίς να το δουν οι άλλοι."""
        if not self.can_edit():
            return
        L = self.link
        self.editor.cancel()
        self.editor.error = None
        self.test = S.Forest(L.data)
        self.test.start_run({L.k: PL.clone(self.editor.program)}, test=True)
        self.test_tr = V.Tracker(self.test)
        team = L.data["teams"][self.test.plots[L.k]["team"]]
        names = {k: L.names.get(k, "R2") for k in self.test.plots}
        self.test_view = V.ForestView(self.test, MAP, box=team["box"], me=L.k, names=names)
        self.test_view.ground = self.view.ground
        self.test_view._static = self.view._static if self.view.ground is not None else None
        if self.test_view._static is None:
            self.test_view.ground = None
        kind = L.data.get("kind")
        p = self.test.plots[L.k]
        if kind == "bars" and p.get("arm"):
            self.message = (["Στη Δοκιμή η μπάρα", "ανοίγει μόνη της."], self.time, art.BLUE, 3.5)
        elif kind == "rock" and p.get("rock"):
            self.message = (["Στη Δοκιμή ο γείτονας", "σπρώχνει μαζί σου."], self.time, art.BLUE, 3.5)
        self.app.sounds.play("swoosh", 0.4)

    def toggle_ready(self):
        if not self.can_edit():
            return
        if not self.editor.program:
            self.message = (["Πρώτα γράψτε", "το πρόγραμμα!"], self.time, art.STUCK, 2.5)
            self.app.sounds.play("deny", 0.6)
            return
        self.ready = not self.ready
        self.app.sounds.play("select" if self.ready else "remove", 0.6)

    def _send(self):
        if not self.programming:
            return
        prog = self.editor.program
        key = (repr(prog), self.ready)
        if key != self.sent:
            self.sent = key
            self.link.send_program(PL.clone(prog), self.ready)

    # ================================================================ κουμπιά
    def reset(self):
        if self.editable() or (self.forest() and not self.forest().done and not self.link.frozen):
            self.link.reset()
            self.app.sounds.play("swoosh", 0.5)

    def toggle_full(self):
        self.show_full = not self.show_full
        self.btn_forest.label = "Πίσω" if self.show_full else "Όλο το δάσος"
        self.btn_forest.icon = art.icon_back if self.show_full else art.icon_forest

    def leave(self):
        self.link.close()
        from .scene import StartScene
        self.app.switch(StartScene(self.app))

    def close_confirm(self):
        self.confirm_exit = False

    def practice_next(self):
        nxt = W.next_level(self.link.level_id)
        if nxt is None:                          # η τελευταία πίστα: τέλος, πίσω στην αρχή
            self.leave()
            return
        self.link.start(nxt)

    def practice_retry(self):
        self.link.start(self.link.level_id)

    def press(self, action):
        if not self.editable():
            return
        for c in self.controls:
            if c.name == action:
                c.flash = self.time
        self.link.act(action)

    # ================================================================ γεγονότα
    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            if self.programming:
                self.editor.motion(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            for b in self.buttons():
                if b.enabled and b.contains(e.pos):
                    b.pressed = True
                    self.pressed_btn = b
                    return
            if self.confirm_exit or self.show_full:
                return
            lid = self._level_at(e.pos)
            if lid is not None and not (self.programming and self.editor.busy()):
                self.app.sounds.play("button")
                self.link.start(lid)                 # Εξάσκηση: κλικ στον αριθμό = αυτή η πίστα
                return
            if self.programming:
                before = PL.clone(self.editor.program)
                self.editor.down(e.pos)
                self._after_edit(before)
                return
            for c in self.controls:
                if c.rect.collidepoint(e.pos):
                    self.press(c.name)
                    return
        elif e.type == pygame.MOUSEWHEEL and self.programming:
            self.editor.wheel(e.y)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed_btn = self.pressed_btn, None
            if b:
                before = PL.clone(self.editor.program) if self.programming else None
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
                if self.programming:
                    self._after_edit(before)
            elif self.programming:
                before = PL.clone(self.editor.program)
                self.editor.up(e.pos)
                self._after_edit(before)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.confirm_exit = not self.confirm_exit
            elif self.confirm_exit:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.leave()
            elif self.programming:
                if e.key == pygame.K_SPACE:
                    self.do_test()
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.toggle_ready()
                elif e.key == pygame.K_z and e.mod & pygame.KMOD_CTRL:
                    before = PL.clone(self.editor.program)
                    self.editor.undo()
                    self._after_edit(before)
            elif e.key in KEYS:
                self.press(KEYS[e.key])

    def _after_edit(self, before):
        """Όταν αλλάζει το πρόγραμμα, το «Έτοιμοι!» σβήνει (πρέπει να το ξαναπατήσουν)."""
        if before is not None and self.editor.program != before:
            self.ready = False
            self.test_view = None

    # ================================================================ χρόνος
    def _load_level(self):
        L = self.link
        f = L.forest
        self.level_no = L.level_no
        self.tr = V.Tracker(f)
        team = f.data["teams"][f.plots[L.k]["team"]]
        names = {k: L.names.get(k, "R2") for k in f.plots}
        self.view = V.ForestView(f, MAP, box=team["box"], me=L.k, names=names)
        self.full = None
        self.show_full = False
        self.btn_forest.label, self.btn_forest.icon = "Όλο το δάσος", art.icon_forest
        self.message = (["Οδήγησε το R2 με τα κουμπιά", "ή με τα βελάκια!"], self.time, art.BLUE, 6)
        self.banner = None
        self.blink = None
        self.done_seen = False
        self.confetti.clear()
        r = f.robots[L.k]
        self.last_pose = (r["pos"], r["face"])
        self._rec_shown = None
        self.editor = None
        self.test = self.test_view = None
        self.ready = False
        self.sent = None
        self.result_round = None
        if L.mode != "drive":
            fix = L.mode == "fix"
            palette = f.data.get("palette") or []
            if fix:
                top = 104 + 96 + 12
                pal = None
            else:
                ed_probe = E.Editor((RX, 104, RW, 100), (0, 0, 10, 10), palette)
                top = 104 + round(ed_probe.palette.height) + 66 + 12
                pal = (RX, 104, RW, top - 12 - 104)
            c = pygame.Rect(RX, top, RW, 708 - top)
            self.code_rect = c
            self.editor = E.Editor(pal, (c.x + 12, c.y + 90, c.w - 24, c.h - 90 - 74), palette, fix, self.app.sounds)
            self.editor.btn_undo.rect.topleft = (c.x + 14, c.bottom - 68)
            self.editor.btn_trash.rect.topleft = (c.x + 110, c.bottom - 68)
            self.btn_test.rect.topleft = (c.x + 14, c.y + 12)
            self.btn_ready.rect.topright = (c.right - 14, c.y + 12)
            self.editor.set_program(L.start_prog)
            if fix:
                self.message = (["Ένα μπλοκ έχει λάθος.", "Πάτα «Δοκιμή»!"], self.time, art.ORANGE, 6)
            else:
                self.message = (["Γράψε το πρόγραμμα", "και πάτα «Δοκιμή»!"], self.time, art.OK, 6)
            self._send()

    def update(self, dt):
        self.time += dt
        L = self.link
        L.tick(dt)
        if L.state == "closed":
            from .scene import MessageScene
            self.app.switch(MessageScene(self.app, L.error or "Τέλος μαθήματος."))
            return
        if L.state == "level" and L.forest is not None and L.level_no != self.level_no:
            self._load_level()
        f = L.forest
        if L.state == "level" and f is not None and self.tr is not None:
            while L.events:
                self._event(*L.events.popleft())
            while L.helps:
                self._help(*L.helps.popleft())
            self.tr.sync(self.time)
            r = f.robots[L.k]
            pose = (r["pos"], r["face"])
            if pose != self.last_pose and self.last_pose is not None:
                self.app.sounds.play("motor" if pose[0] != self.last_pose[0] else "turn", 0.35)
            self.last_pose = pose
            if L.rec != self._rec_shown:
                self._rec_shown = [dict(n) for n in L.rec]
                self.codeview.set_program(L.rec)
            if L.done and not self.done_seen:
                self.done_seen = True
                self.confetti.burst(WIDTH, 160)
                if W.next_level(L.level_id) is None:      # το τέλος του παιχνιδιού: διπλή γιορτή
                    self.confetti.burst(WIDTH, 240)
                self.app.sounds.play("win")
            if self.time > self.route_until and self.view.route:
                self.view.route = None
            if self.programming:
                self._update_program(dt)
        else:
            while L.events:
                L.events.popleft()
        self.confetti.update(dt, self.time, HEIGHT)
        for c in self.controls:
            c.hover = c.rect.collidepoint(self.mouse) and self.editable()
        for b in self.buttons():
            b.hover = b.enabled and b.contains(self.mouse)
        want = pygame.SYSTEM_CURSOR_HAND if (any(b.hover for b in self.buttons()) or self._level_at(self.mouse) or
                                             any(c.hover for c in self.controls)) else pygame.SYSTEM_CURSOR_ARROW
        if want != self.cursor:
            try:
                pygame.mouse.set_cursor(want)
            except (pygame.error, TypeError):
                pass
            self.cursor = want
        self.btn_again.enabled = self.editable()

    def _update_program(self, dt):
        L = self.link
        ed = self.editor
        ed.update(dt)
        ed.locked = not self.can_edit()
        if L.phase != "plan":
            self.ready = False
        # η «Δοκιμή»
        if self.test is not None:
            self.test.tick(dt)
            self.test_tr.sync(self.time)
            st = self.test.run.get(L.k) if self.test.run else None
            ed.running = tuple(st["path"]) if st and st["path"] and self.test.run_phase == "robots" else None
            if self.test.run_phase == "end":
                res = self.test.run_results().get(L.k, ["empty", None, None])
                self._show_result(res, test=True)
                self.test = None
                self.test_until = self.time + 2.5
        elif L.phase == "run":
            rv = L.forest.run_view.get(L.k)
            ed.running = tuple(rv[0]) if rv and rv[0] and rv[1] == "run" else None
        else:
            ed.running = None
        if L.phase == "plan":
            self.run_prog = PL.clone(ed.program)
        # τα αποτελέσματα του γύρου
        if L.results and L.phase in ("result", "done") and self.result_round != L.round:
            self.result_round = L.round
            res = L.results.get(L.k)
            if res:
                self._show_result(res, test=False)
        self.btn_ready.on = self.ready
        self.btn_ready.enabled = self.can_edit()
        self.btn_test.enabled = self.can_edit()
        self.btn_ready.pulse = (self.can_edit() and not self.ready and bool(ed.program)
                                and self.time - ed.changed_at > 6)
        self._send()

    def _show_result(self, res, test):
        status, why, path = res
        ed = self.editor
        if status == "ok" and why in ("partner", "chain"):
            ed.error = None
            second = "Ο γείτονας δεν ήρθε στον βράχο." if why == "partner" else "Η μπάρα δεν άνοιξε."
            self.message = (["Το πρόγραμμά σας είναι σωστό!", second], self.time, art.ORANGE, 6)
        elif status == "ok":
            ed.error = None
            if test:
                self.message = (["Πέτυχε!", "Τώρα πατήστε «Έτοιμοι!»."], self.time, art.OK, 5)
            else:
                self.message = (["Πέτυχε!"], self.time, art.OK, 4)
            self.app.sounds.play("complete", 0.6)
        else:
            prog = ed.program if test else self.run_prog
            fix = net.program_fix(self.link.data, self.link.k, prog) if status != "empty" else None
            if fix:                              # η πιο μικρή αλλαγή που διορθώνει το πρόγραμμα
                ed.error = tuple(fix[1])
                text = fix[2]
            else:
                ed.error = tuple(path) if path else None
                text = net.program_hint(res, self.link.data.get("kind"))
            self.message = (art.wrap(text, 17, 300), self.time, art.STUCK, 8)
            self.app.sounds.play("deny", 0.5)

    def _event(self, eid, t, kind, k, data):
        me = self.link.k
        f = self.forest()
        team = self.my_team()
        snd = self.app.sounds
        if kind == "bump" and k == me:
            self.tr.bump(k, self.time)
            snd.play("bump", 0.6)
            text = WHY.get(data, ["Ωχ!"])
            if data == "branch" and f.data.get("kind") == "bars":
                text = ["Η μπάρα είναι κλειστή!", "Περίμενε να ανοίξει."]
            self.message = (text, self.time, art.STUCK, 2.2)
            self.bump = (self.time,)
        elif kind == "splash" and k == me:
            snd.play("swoosh", 0.6)
            self.message = (["Πέρασμα για τα ζώα!"], self.time, art.OK, 2.5)
        elif kind == "dam" and k == me:
            snd.play("thud", 0.7)
            self.message = (["Το αυλάκι έκλεισε!", "Το νερό πάει από αλλού."], self.time, art.OK, 3)
        elif kind == "push" and k == me:
            snd.play("place", 0.4)
        elif kind == "heavy" and k == me:
            snd.play("thud", 0.5)
            self.message = (["Ο βράχος είναι βαρύς!", "Σπρώχνω και περιμένω τον γείτονα."], self.time, art.BLUE, 3)
        elif kind == "arm" and f.data.get("kind") == "bars":
            if data and any(s["to"] == k == s["from"] == me for s in f.seesaws):
                snd.play("barrier", 0.5)
                self.message = (["Το φράγμα άνοιξε!", "Το νερό πάει στη φωτιά."], self.time, art.OK, 3.5)
            elif data and k == me:
                snd.play("barrier", 0.5)
                self.message = (["Η μπάρα άνοιξε!"], self.time, art.OK, 2.5)
            elif data and any(s["to"] == k and s["from"] == me for s in f.seesaws):
                snd.play("barrier", 0.4)
                self.message = (["Άνοιξες τη μπάρα", "του γείτονα!"], self.time, art.BLUE, 3)
        elif kind == "arm":
            s = next((s for s in f.seesaws if s["to"] == k), None)
            if s and data:
                if k == me:
                    snd.play("barrier", 0.5)
                    self.message = (["Το κλαδί σηκώθηκε!", "Πέρνα από κάτω."], self.time, art.OK, 3)
                elif s["from"] == me:
                    snd.play("barrier", 0.4)
                    self.message = (["Μείνε στο πεντάλ", "ώσπου να περάσει!"], self.time, art.BLUE, 4)
        elif kind == "saved" and f.plots.get(k, {}).get("team") == team:
            snd.play("hop", 0.5)
        elif kind == "fire_out" and data == team:
            snd.play("complete", 0.7)
            self.banner = ("Η φωτιά έσβησε!", self.time)
        elif kind == "reset" and k == me:
            self.message = (["Ξανά από την αρχή!"], self.time, art.BLUE, 2)

    def _help(self, kind, data):
        if kind == "phase":
            if data == "plan":
                self.ready = False
                self.sent = None
                if self.editor:
                    self.editor.running = None
            elif data == "run":
                self.test = None
                self.test_view = None
                if self.editor:
                    self.editor.cancel()
                    self.editor.error = None
                self.message = (["Όλα τα R2 μαζί!"], self.time, art.BLUE, 2.5)
            return
        if kind == "blame" and self.editor:
            if data:
                self.editor.error = tuple(data)
                self.message = (["Ο δάσκαλος σας δείχνει", "το μπλοκ με το λάθος."], self.time, art.STUCK, 6)
            else:
                self.message = (["Το πρόγραμμα", "είναι σωστό!"], self.time, art.OK, 4)
            return
        if kind == "solution" and self.editor and data is not None:
            self.editor.set_program(data, remember=True)
            self.ready = False
            self.message = (["Ο δάσκαλος σας έδωσε", "το σωστό πρόγραμμα."], self.time, art.BLUE, 6)
            return
        if kind == "hint" and data:
            self.message = (art.wrap(str(data), 17, 300), self.time, (236, 170, 40), 9)
            self.app.sounds.play("select", 0.6)
        elif kind == "route" and data:
            self.view.route = [tuple(c) for c in data]
            self.route_until = self.time + 14
            self.message = (["Ακολούθησε τις κίτρινες", "τελίτσες!"], self.time, (236, 170, 40), 5)
        elif kind == "next" and data:
            self.blink = (data, self.time + 6)
        elif kind == "auto":
            if data:
                self.message = (["Το R2 κινείται", "μόνο του!"], self.time, art.OFF, 5)
            else:
                self.message = (["Σειρά σας ξανά!"], self.time, art.BLUE, 3)
        elif kind == "msg" and data:
            self.banner = (str(data), self.time)
            self.app.sounds.play("select", 0.6)

    # ================================================================ ζωγραφική
    def draw(self, screen):
        screen.blit(self.room, (0, 0))
        L = self.link
        if L.state != "level" or L.forest is None or self.view is None:
            self._draw_lobby(screen)
        elif self.show_full:
            self._draw_full(screen)
        else:
            self._draw_level(screen)
        self.confetti.draw(screen)
        if L.frozen:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((20, 40, 70, 170))
            screen.blit(veil, (0, 0))
            art.icon_snow(screen, (WIDTH // 2, HEIGHT // 2 - 70), 90, art.WHITE)
            ui.text(screen, "Κοιτάξτε τον πίνακα!", (WIDTH // 2, HEIGHT // 2 + 20), 44, art.WHITE)
        if self.confirm_exit:
            self._draw_confirm(screen)

    def _top(self, s):
        art.top_bar(s)
        L = self.link
        f = L.forest
        x = 14
        if L.state == "level" and not self.programming:
            self.btn_again.draw(s, self.time)
            x = 116
        card = pygame.Rect(x, 12, 186, 68)
        ui.panel(s, card, art.WHITE, radius=16, border=art.LINE, shadow=False)
        name = L.names.get(L.k) if L.state == "level" else L.name_typed
        team = self.my_team()
        if f is not None and team is not None:
            t = f.data["teams"][team]
            col = V.robot_color(f, L.k)
            sub = f"οικόπεδο {t['plots'].index(L.k) + 1} · {t['name']}"
        else:
            col, sub = art.BLUE, L.title and f"μάθημα: {L.title}" or ""
        pygame.draw.rect(s, col, (card.x + 10, card.y + 12, 10, card.h - 24), border_radius=5)
        ui.text(s, name or "", (card.x + 30, card.y + 24), 20, DARK, anchor="midleft")
        ui.text(s, sub, (card.x + 30, card.y + 48), 14, art.GREY, anchor="midleft", bold=False)
        if f is not None and L.state == "level":
            lv = W.level(f.data["level"])
            art.level_dots(s, 653, 30, lv["no"])
            art.mode_title(s, 653, 71, lv.get("pill", lv.get("mode", "drive")), lv["goal"])
        else:
            ui.text(s, "Αποστολές Διάσωσης", (653, 46), 24, art.TITLE)
        for b in self.buttons():
            if b in (self.btn_forest, self.btn_sound):
                b.draw(s, self.time)

    def _goal_items(self):
        f = self.forest()
        k = self.link.k
        team = self.my_team()
        kind = f.data["kind"]
        saved, total, out, fires = f.counts(team)
        csaved, ctotal, _, _ = f.counts()
        p = f.plots[k]
        stone_done = f.plot_done_stones(k)
        if kind == "cross":
            return [(stone_done, "Η πέτρα στο ποτάμι"), (saved == total, f"Ζώα στο λιβάδι {saved}/{total}"),
                    (csaved == ctotal, f"Όλη η τάξη {csaved}/{ctotal}")]
        if kind == "dam":
            return [(stone_done, "Το αυλάκι κλειστό"), (out == fires and fires > 0, "Το νερό στη φωτιά"),
                    (saved == total, f"Ζώα στο λιβάδι {saved}/{total}")]
        if kind == "bars":
            on = p.get("pedal") is not None and f.robots[k]["pos"] == tuple(p["pedal"])
            return [(on, "Πάτα το πεντάλ"), (out == fires and fires > 0, "Το νερό στη φωτιά"),
                    (saved == total, f"Ζώα στο λιβάδι {saved}/{total}")]
        if kind == "rock":
            label = "Ο βράχος στο ποτάμι" if p.get("rock") else "Η πέτρα στο ποτάμι"
            return [(stone_done, label), (saved == total, f"Ζώα στο λιβάδι {saved}/{total}"),
                    (csaved == ctotal, f"Όλη η τάξη {csaved}/{ctotal}")]
        middle = (p.get("pedal") and f.plot_done(k)) if p.get("pedal") else (out == fires and fires > 0)
        label = "Το κλαδί για τον γείτονα" if p.get("pedal") else "Το νερό στη φωτιά"
        return [(stone_done, "Το αυλάκι κλειστό"), (bool(middle), label), (saved == total, f"Ζώα {saved}/{total}")]

    def _draw_level(self, s):
        L = self.link
        f = L.forest
        testing = self.programming and (self.test is not None or (self.test_view is not None and self.time < self.test_until))
        if testing:
            self.test_view.draw(s, self.time, self.test_tr)
        else:
            self.view.draw(s, self.time, self.tr)
        if self.bump and self.time - self.bump[0] < 0.7:
            pos = self.view.robot_top(L.k, self.tr, self.time, 60)
            V.bump_stars(s, pos, self.time - self.bump[0], self.view.g.tw * 0.9)
        art.goals(s, MAP, self._goal_items())
        if f.paused or (self.programming and L.paused):
            art.pill(s, (MAP.x + 16, MAP.y + 14), "Παύση", (120, 130, 150), art.WHITE)
        elif self.programming:
            self._draw_phase_pills(s, testing)
        if f.auto.get(L.k):
            art.pill(s, (MAP.right - 16, MAP.y + 14), "Αυτόματο R2", art.OFF, art.WHITE, anchor="topright")
        self._draw_sensor(s, testing)
        art.map_frame(s, MAP)
        if self.programming:
            self._draw_editor(s)
        else:
            self._draw_controls(s)
            self._draw_program(s)
        self._top(s)
        self._draw_messages(s, testing)
        if self.programming:
            self.editor.draw_top(s)
        if L.done:
            self._draw_done(s)

    def _draw_sensor(self, s, testing):
        """Πάνω από το R2: «10 cm» όσο τρέχει το «περίμενε ώσπου» (για να βλέπουν τι μετρά ο αισθητήρας)."""
        ed = self.editor
        if not self.programming or not ed.running:
            return
        try:
            node = PL.get(self.run_prog if not testing else ed.program, ed.running)
        except (IndexError, KeyError, TypeError):
            return
        if not isinstance(node, dict) or node.get("op") != "until":
            return
        f, view, tr = (self.test, self.test_view, self.test_tr) if testing and self.test else (self.link.forest, self.view, self.tr)
        if f is None or self.link.k not in f.robots:
            return
        cm = f.distance(self.link.k)
        x, y = view.robot_top(self.link.k, tr, self.time, 0)     # κάτω από το R2 (πάνω είναι τα μηνύματα)
        txt = f"απόσταση {cm} cm" if cm < W.CM_FAR else "απόσταση: μακριά"
        art.pill(s, (round(x), round(y) + 14), txt, art.PURPLE, art.WHITE, size=15, anchor="midtop")

    def _goal_items_program(self):
        return self._goal_items()

    def _draw_full(self, s):
        L = self.link
        f = L.forest
        if self.full is None:
            names = {k: L.names.get(k, "R2") for k in f.plots}
            self.full = V.ForestView(f, FULL, me=L.k, names=names, tag_scale=0.8)
        self.full.draw(s, self.time, self.tr)
        for t in f.data["teams"]:
            x0, y0, x1, y1 = t["box"]
            x, y = self.full.pt((x0 + x1) / 2, y1, 0)
            saved, total, out, fires = f.counts(f.data["teams"].index(t))
            txt = f"{t['name']} · ζώα {saved}/{total}"
            art.pill(s, (x, min(FULL.bottom - 50, y + 26)), txt, V.TEAM_COLS[f.data["teams"].index(t) % 7],
                     art.WHITE, 14, anchor="midtop")
        art.map_frame(s, FULL)
        art.top_bar(s)
        self.btn_forest.draw(s, self.time)
        self.btn_sound.draw(s, self.time)
        csaved, ctotal, out, fires = f.counts()
        art.mode_title(s, 600, 46, "drive", f"Όλη η τάξη: ζώα {csaved}/{ctotal}" +
                       (f" · φωτιές {out}/{fires}" if fires else ""), chip_col=art.TEAL)

    def _draw_controls(self, s):
        p = pygame.Rect(RX, 104, RW, 170)
        art.panel(s, p, "Χειριστήριο", "ή με τα βελάκια")
        ok = self.editable()
        blink = self.blink[0] if self.blink and self.time < self.blink[1] else None
        for c in self.controls:
            c.draw(s, self.time, ok, blink == c.name)

    def _draw_program(self, s):
        c = self.code_rect
        art.panel(s, c, "Το πρόγραμμα")
        n = PL.count(self.link.rec)
        ui.text(s, f"{n} εντολ{'ή' if n == 1 else 'ές'}", (c.right - 20, c.y + 25), 18, art.GREY, anchor="midright")
        fresh = (len(self.link.rec) - 1,) if self.link.rec else None
        self.codeview.draw(s, fresh=fresh, fresh_alpha=140)
        if not self.link.rec:
            r = self.codeview.rect
            for i, t in enumerate(("Οδήγησε το R2 με τα κουμπιά:", "εδώ θα γραφτούν οι εντολές.")):
                ui.text(s, t, (r.centerx, r.centery + 10 + i * 24), 17, art.LIGHT, bold=False)
        ui.text(s, "Οδηγείς το R2 και οι εντολές γράφονται μόνες τους.", (c.centerx, c.bottom - 26), 15, art.LIGHT,
                bold=False)

    def _draw_phase_pills(self, s, testing):
        L = self.link
        x = MAP.x + 16
        if testing:
            art.pill(s, (x, MAP.y + 14), "Δοκιμή: μόνο το δικό σας R2", (236, 170, 40), art.WHITE)
            return
        if L.phase == "plan":
            if L.timed:
                left = int(L.time_left())
                r = art.pill(s, (x, MAP.y + 14), f"Χρόνος {left // 60}:{left % 60:02d}")
                x = r.right + 8
            if L.allready_at is not None:
                import time as _t
                n = max(0, math.ceil(L.allready_at - _t.monotonic()))
                art.pill(s, (x, MAP.y + 14), f"Όλοι έτοιμοι! Ξεκινάμε σε {n}…", art.OK, art.WHITE)
            elif self.ready:
                art.pill(s, (x, MAP.y + 14), "Περιμένουμε και τους άλλους…", art.BLUE, art.WHITE)
            art.pill(s, (MAP.right - 16, MAP.y + 14), f"Γύρος {L.round}", art.WHITE, DARK, anchor="topright")
        elif L.phase == "run":
            art.pill(s, (x, MAP.y + 14), "Εκτέλεση: όλα τα R2 μαζί!", art.RUN, art.WHITE)
        elif L.phase == "result" and L.results is not None:
            c = getattr(L, "last_counts", None)
            txt = f"Γύρος {L.round}: σώθηκαν {c[0]} από {c[1]} ζώα" if c else f"Γύρος {L.round}"
            r = art.pill(s, (x, MAP.y + 14), txt, (255, 252, 240), DARK)
            art.pill(s, (r.right + 8, MAP.y + 14), "Διορθώστε και ξαναπάμε!", art.ORANGE, art.WHITE)

    def _draw_editor(self, s):
        L = self.link
        ed = self.editor
        if ed.palette is not None:
            p = ed.palette_rect
            art.panel(s, p, "Εντολές", "σύρε μια εντολή στο πρόγραμμα")
            ed.draw_palette(s)
        else:
            p = pygame.Rect(RX, 104, RW, 96)
            art.panel(s, p, "Διόρθωσε το πρόγραμμα")
            first = ("Πάτα στο σύμβολο (< ή >) ή σε έναν αριθμό" if PL.count(ed.program) and
                     any(n.get("op") == "until" for n in ed.program) else "Πάτα σε έναν αριθμό ή σε μια λέξη (π.χ. «δεξιά»)")
            ui.text(s, first, (p.x + 20, p.y + 54), 15, art.GREY, anchor="midleft", bold=False)
            ui.text(s, "και άλλαξέ τα. Η «Δοκιμή» δείχνει πού είναι το λάθος.", (p.x + 20, p.y + 76), 15, art.GREY,
                    anchor="midleft", bold=False)
        c = self.code_rect
        art.panel(s, c)
        ed.draw_code(s)
        if not ed.program:
            r = ed.view.rect
            for i, t in enumerate(("Σύρε εντολές εδώ, κάτω από το «R2 starts»,", "ή πάτα τες στις Εντολές.")):
                ui.text(s, t, (r.centerx, r.centery + 10 + i * 24), 16, art.LIGHT, bold=False)
        self.btn_test.draw(s, self.time)
        self.btn_ready.draw(s, self.time)
        for b in ed.buttons():
            b.draw(s, self.time)
        n = PL.count(ed.program)
        ui.text(s, f"{n} εντολ{'ή' if n == 1 else 'ές'}", (c.right - 22, c.bottom - 40), 18, art.GREY, anchor="midright")

    def _draw_messages(self, s, testing=False):
        L = self.link
        f = L.forest
        waiting = any(a["wait"] == L.k for a in f.animals if not a["safe"])
        if testing:
            anchor = self.test_view.robot_top(L.k, self.test_tr, self.time)
        else:
            anchor = self.view.robot_top(L.k, self.tr, self.time)
        if self.message and self.time - self.message[1] < self.message[3]:
            lines, t, col, _ = self.message
            bubble(s, lines, anchor, side="up", border=col, size=17)
        elif waiting and not f.done:
            bubble(s, ["Κάνε στην άκρη,", "να περάσουν τα ζώα!"], anchor, side="up", border=art.ORANGE, size=17)
        elif self._pedal_hint():
            lines, col = self._pedal_hint()
            bubble(s, lines, anchor, side="up", border=col, size=17)
        if self.banner and self.time - self.banner[1] < 6:
            txt = self.banner[0]
            art.pill(s, (MAP.centerx, MAP.y + 54), txt, (255, 252, 240), DARK, 20, anchor="midtop")

    def _pedal_hint(self):
        """Πίστα με κλαδί: το R2 πρέπει να μείνει στο πεντάλ ώσπου να περάσει ο γείτονας."""
        L = self.link
        f = L.forest
        if self.programming or f is None or f.done or L.k not in f.plots:
            return None
        p = f.plots[L.k]
        if not p.get("pedal") or f.next_of(L.k) is None or not f.plot_done_stones(L.k) or f.neighbour_passed(L.k):
            return None
        if f.robots[L.k]["pos"] == tuple(p["pedal"]):
            return ["Μείνε στο πεντάλ", "ώσπου να περάσει ο γείτονας!"], art.BLUE
        return ["Πήγαινε στο κίτρινο πεντάλ:", "ο γείτονας περιμένει!"], art.ORANGE

    def _level_at(self, pos):
        """Εξάσκηση: η πίστα κάτω από το ποντίκι στις τελείες πάνω (ή None)."""
        if not self.practice or self.link.state != "level" or self.confirm_exit:
            return None
        ids = [lid for ch in W.CHAPTERS for lid in ch.get("levels", [])]
        no = art.level_dot_at(pos, 653, 30)
        return ids[no - 1] if no and no <= len(ids) else None

    def _draw_done(self, s):
        card = pygame.Rect(0, 0, 600, 150)
        card.midtop = (MAP.centerx, MAP.y + 10)
        ui.panel(s, card, (255, 252, 240), radius=26, border=(250, 190, 50))
        for i, dx in enumerate((-250, -205, -160)):
            ui.star(s, (card.centerx + dx, card.y + 44 - (6 if i == 1 else 0)), 20 if i == 1 else 16, (252, 204, 60))
        ui.text(s, "Μπράβο, τάξη!" if not self.practice else "Μπράβο!", (card.centerx + 40, card.y + 42), 38,
                art.TITLE, shadow=(250, 214, 150))
        saved, total, fires = self.link.done
        line = f"Σώθηκαν {saved} από {total} ζώα" + (f" · έσβησαν {fires} από {fires} φωτιές" if fires else "")
        ui.text(s, line, (card.centerx, card.y + 88), 19, DARK)
        last = W.next_level(self.link.level_id) is None
        if self.practice:
            self.btn_next.label = "Τέλος" if last else "Επόμενη πίστα"
            self.btn_next.icon = None if last else (lambda s, c, z, col: ui.icon_next(s, c, z, col))
            self.btn_next.rect.topleft = (card.centerx + 10, card.bottom + 14)
            self.btn_retry.rect.topright = (card.centerx - 10, card.bottom + 14)
            self.btn_next.draw(s, self.time)
            self.btn_retry.draw(s, self.time)
        if last:
            ui.text(s, "Τέλος του παιχνιδιού! Σώσατε το δάσος σε όλες τις αποστολές.", (card.centerx, card.y + 120), 16, art.OK)
        elif self.practice:
            ui.text(s, "Το δάσος ξαναπρασινίζει!", (card.centerx, card.y + 120), 16, art.OK)
        else:
            ui.text(s, "Το δάσος ξαναπρασινίζει!  Ο δάσκαλος θα ανοίξει την επόμενη πίστα.",
                    (card.centerx, card.y + 120), 16, art.OK)

    def _draw_lobby(self, s):
        self._top(s)
        L = self.link
        card = pygame.Rect(WIDTH // 2 - 380, 200, 760, 300)
        ui.panel(s, card, art.WHITE, radius=24, border=art.LINE)
        art.icon_flame(s, (card.centerx, card.y + 70), 60, None, self.time)
        if L.late:
            lines = ["Το μάθημα έχει ήδη ξεκινήσει.", "Θα μπείτε μόλις ο δάσκαλος ανοίξει πίστα."]
        else:
            lines = ["Περιμένουμε τον δάσκαλο να ξεκινήσει…",
                     f"Στο μάθημα: {L.lobby_n} υπολογιστ{'ής' if L.lobby_n == 1 else 'ές'}" if L.lobby_n else ""]
        for i, t in enumerate(lines):
            ui.text(s, t, (card.centerx, card.y + 150 + i * 40), 26 if i == 0 else 20, DARK if i == 0 else art.GREY)
        for i in range(3):
            ui.circle(s, art.BLUE, (card.centerx - 30 + i * 30, card.bottom - 40 + math.sin(self.time * 3 + i) * 6), 8)

    def _draw_confirm(self, s):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 30, 50, 160))
        s.blit(veil, (0, 0))
        card = pygame.Rect(WIDTH // 2 - 300, 250, 600, 240)
        ui.panel(s, card, art.WHITE, radius=22)
        ui.text(s, "Να βγείτε από το μάθημα;", (card.centerx, card.y + 60), 28, DARK)
        ui.text(s, "Το οικόπεδό σας θα συνεχίσει με αυτόματο R2.", (card.centerx, card.y + 100), 17, art.GREY,
                bold=False)
        self.btn_yes.rect.topright = (card.centerx - 10, card.bottom - 90)
        self.btn_no.rect.topleft = (card.centerx + 10, card.bottom - 90)
        self.btn_yes.draw(s, self.time)
        self.btn_no.draw(s, self.time)
