"""Η οθόνη του δασκάλου (και του προβολέα).

- Οργάνωση: η τάξη (θυμάται ως πού έφτασε), η πίστα, η αίθουσα με 25 θέσεις σε Π (ο δάσκαλος κάτω). Ο δάσκαλος
  σέρνει κάθε υπολογιστή στη θέση του. Οι διπλανές θέσεις γίνονται ένα «ποτάμι» (ομάδα).
- Μάθημα: όλο το δάσος (ή ζουμ σε ένα ποτάμι), τα ονόματα με την κατάσταση κάθε οικοπέδου (τελείωσε,
  οδηγεί, κόλλησε...), Πάγωμα, Παύση, Ξανά, Επόμενη. Κόκκινο «!» δίπλα σε όποιο R2 χρειάζεται βοήθεια.
- Βοήθεια (κλικ σε όνομα ή οικόπεδο): το οικόπεδο από κοντά, το πρόγραμμα που έγραψαν οδηγώντας, τι γίνεται,
  και τα βήματα: Υπόδειξη, Δρόμος, Επόμενη κίνηση, Λύση (το R2 το κάνει μόνο του), Μήνυμα, Ξανά.
Η πρόοδος κάθε τάξης και οι θέσεις των υπολογιστών φυλάγονται στο rescue_forest.json (στον φάκελο δεδομένων).
"""
import json
import math
import os

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.program import code
from . import art, net, view as V, world as W

STORE_FILE = "rescue_forest.json"
ROOM = pygame.Rect(436, 104, 830, 604)
MAP = pygame.Rect(14, 144, 1252, 418)
MAP_BIG = pygame.Rect(14, 104, 1252, 604)
CHIPS = pygame.Rect(14, 570, 1252, 138)
HELP = pygame.Rect(54, 40, 1172, 650)
INK, GREY, LIGHT = art.INK, art.GREY, art.LIGHT


class Store:
    def __init__(self, folder):
        self.path = os.path.join(folder, STORE_FILE) if folder else None
        self.data = {"classes": {}, "order": [], "seats": {}, "settings": {}}
        if self.path and os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except (OSError, ValueError):
                pass
        if not self.data["order"]:
            self.data["order"] = ["Δ1", "Ε1", "ΣΤ1"]
            for c in self.data["order"]:
                self.data["classes"].setdefault(c, {"done": {}, "last": None})

    def save(self):
        if not self.path:
            return
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def klass(self, name):
        return self.data["classes"].setdefault(name, {"done": {}, "last": None})

    def add_class(self, name):
        name = name.strip()[:6]
        if name and name not in self.data["order"]:
            self.data["order"].append(name)
            self.klass(name)
            self.save()
        return name

    def setting(self, key, default):
        return self.data["settings"].get(key, default)

    def set(self, key, value):
        self.data["settings"][key] = value
        self.save()


# ================================================================ θέσεις της αίθουσας (σχήμα Π, δάσκαλος κάτω)
def seat_rects():
    """Οι 25 θέσεις με τη σειρά τους: αριστερά 9 (από κάτω προς τα πάνω), πάνω 7 (από αριστερά προς τα δεξιά),
    δεξιά 9 (από πάνω προς τα κάτω). Κάτω, στο ανοιχτό μέρος, ο δάσκαλος."""
    R = ROOM
    sw, sh = 104, 46
    top_y = R.y + 58
    left_x, right_x = R.x + 18, R.right - 18 - sw
    col_top, col_bot = top_y + 66, R.bottom - 16
    step = (col_bot - col_top - sh) / 8
    seats = [pygame.Rect(left_x, round(col_bot - sh - i * step), sw, sh) for i in range(9)]
    inner_l, inner_r = left_x + sw + 14, right_x - 14
    tw = (inner_r - inner_l - 6 * 8) / 7
    seats += [pygame.Rect(round(inner_l + i * (tw + 8)), top_y, round(tw), sh + 10) for i in range(7)]
    seats += [pygame.Rect(right_x, round(col_top + i * step), sw, sh) for i in range(9)]
    return seats


SEATS = seat_rects()


def team_layout(n_order, bots):
    """Ποιο ποτάμι και ποιο οικόπεδο παίρνει κάθε θέση με τη σειρά (για την προεπισκόπηση στην αίθουσα)."""
    n = max(W.MIN_PCS, min(W.MAX_PCS, n_order + bots))
    out = []
    for t, size in enumerate(W.team_sizes(n)):
        for j in range(size):
            out.append((t, j))
    return out


class TeacherScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.pressed = None
        self.room = art.room()
        self.store = Store(app.data_dir)
        order = self.store.data["order"]
        self.klass = self.store.setting("class", order[0] if order else "Δ1")
        if self.klass not in order:
            self.klass = order[0]
        self.selected = self._resume_level()
        self.error = None
        try:
            self.host = net.Host(self.klass)
        except OSError as e:
            self.host = None
            self.error = f"Δεν άνοιξε το δίκτυο ({e})."
        if self.host:
            self.host.bots = self.store.setting("bots", 0)
            self.host.plan_seconds = self.store.setting("plan", 180)
            self.host.completed = self._completed
        self.page = "setup"
        self.drag = None              # σύρσιμο υπολογιστή στην αίθουσα: {"pc", "grab"}
        self.typing = None            # νέα τάξη: το κείμενο
        self.big = False              # Tab: μόνο το δάσος, για τον προβολέα
        self.view_key = "all"
        self.views = {}
        self.tr = None
        self.help_k = None
        self.help_view = None
        self.msg_menu = False
        self.sent = {}                # (οικόπεδο, βοήθεια) -> πότε στάλθηκε
        self.confirm = None
        self.confetti = fx.Confetti()
        self.celebrated = False
        self.event_seen = 0
        self.codeview = None
        self._forest_seen = None
        self._blame_cache = {}
        self._make_buttons()

    # ------------------------------------------------------------ κουμπιά
    def _make_buttons(self):
        T, B = art.TextButton, ui.Button
        self.btn_back = B((14, 8, 112, 76), "Πίσω", ui.icon_prev, art.BLUE, self.leave, label_size=15)
        self.btn_sound = B((1190, 8, 80, 76), "Ήχος",
                           lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           art.PURPLE, self.app.sounds.toggle)
        self.btn_start = B((30, 608, 378, 84), "Ξεκινάμε", ui.icon_play, art.OK, self.start, label_size=20)
        self.btn_home = B((14, 8, 112, 76), "Οργάνωση", ui.icon_prev, art.BLUE, self.ask_home, label_size=15)
        self.btn_freeze = B((850, 8, 96, 76), "Πάγωμα", art.icon_snow, (90, 170, 230), self.freeze, label_size=15)
        self.btn_pause = B((956, 8, 90, 76), "Παύση", art.icon_pause, (120, 130, 150), self.pause, label_size=15)
        self.btn_restart = B((1056, 8, 96, 76), "Ξανά", ui.icon_again, art.ORANGE, self.restart_level, label_size=15)
        self.btn_next = B((1162, 8, 104, 76), "Επόμενη", ui.icon_next, art.BLUE, self.next_level, label_size=15)
        self.btn_run = B((842, 8, 112, 76), "Εκτέλεση!", ui.icon_play, art.OK, self.run_now, label_size=15)
        self.btn_round = B((842, 8, 112, 76), "Γύρος 2", ui.icon_next, art.BLUE, self.next_round, label_size=15)
        self.btn_time = B((964, 8, 96, 76), "+1 λεπτό", art.icon_timer, art.ORANGE, self.add_time, label_size=15)
        self.btn_plan_minus = T((0, 0, 34, 34), "−", (236, 240, 246), lambda: self.set_plan(-1), 20, fg=INK)
        self.btn_plan_plus = T((0, 0, 34, 34), "+", (236, 240, 246), lambda: self.set_plan(1), 20, fg=INK)
        self.btn_bot_minus = T((0, 0, 34, 34), "−", (236, 240, 246), lambda: self.set_bots(-1), 20, fg=INK)
        self.btn_bot_plus = T((0, 0, 34, 34), "+", (236, 240, 246), lambda: self.set_bots(1), 20, fg=INK)
        self.btn_yes = T((WIDTH // 2 - 190, 410, 180, 60), "Ναι", art.STUCK, self.confirm_yes, 19)
        self.btn_no = T((WIDTH // 2 + 10, 410, 180, 60), "Όχι", (120, 130, 150), self.confirm_no, 19)
        self.btn_done_next = T((0, 0, 250, 60), "Επόμενη πίστα", art.OK, self.next_level, 20, icon=art.icon_back)
        self.btn_done_next.icon = lambda s, c, z, col: ui.icon_next(s, c, z, col)
        self.btn_done_again = T((0, 0, 170, 60), "Ξανά", art.ORANGE, self.restart_level, 19)
        self.btn_done_end = T((0, 0, 250, 60), "Τέλος", art.TEAL, self.finish_game, 20)
        # βοήθεια
        hx, hy = HELP.x + 20, HELP.bottom - 116
        self.help_btns = [
            ("hint", B((hx, hy, 138, 86), "Υπόδειξη", art.icon_bulb, (236, 170, 40), lambda: self.help("hint"),
                       label_size=15)),
            ("route", B((hx + 150, hy, 138, 86), "Δρόμος", art.icon_route, art.TEAL, lambda: self.help("route"),
                        label_size=15)),
            ("next", B((hx + 300, hy, 138, 86), "Επόμενη κίνηση", art.icon_arrow_key, art.ORANGE,
                       lambda: self.help("next"), label_size=14)),
            ("auto", B((hx + 450, hy, 138, 86), "Λύση", art.icon_check, art.OK, lambda: self.help("auto"),
                       label_size=15)),
        ]
        self.btn_msg = B((HELP.x + 660, hy, 154, 86), "Μήνυμα", art.icon_msg, art.PURPLE, self.toggle_msgs,
                         label_size=15)
        self.btn_reset = B((HELP.x + 826, hy, 154, 86), "Ξανά", ui.icon_again, art.ORANGE, self.reset_plot,
                           label_size=15)
        self.btn_close = B((HELP.right - 70, HELP.y + 16, 54, 54), "", ui.icon_close, (150, 158, 172), self.close_help)
        self.msg_btns = [T((0, 0, 300, 44), m, art.PURPLE, (lambda m=m: self.help("msg", m)), 16)
                         for m in net.TEACHER_MSGS]

    # ------------------------------------------------------------ ενέργειες
    def leave(self):
        if self.host:
            self.host.close()
        from .scene import StartScene
        self.app.switch(StartScene(self.app))

    def ask_home(self):
        self.confirm = ("home", "Πίσω στην οργάνωση; Η πίστα σταματά.")

    def confirm_yes(self):
        kind, _ = self.confirm
        self.confirm = None
        if kind == "home":
            self.host.to_lobby()
            self.page = "setup"
            self.help_k = None

    def confirm_no(self):
        self.confirm = None

    def set_plan(self, d):
        steps = [0, 60, 90, 120, 180, 240, 300, 420, 600]
        cur = self.host.plan_seconds
        i = min(range(len(steps)), key=lambda j: abs(steps[j] - cur))
        self.host.plan_seconds = steps[max(0, min(len(steps) - 1, i + d))]
        self.store.set("plan", self.host.plan_seconds)

    def run_now(self):
        self.host.run_now()

    def next_round(self):
        self.host.next_round()

    def add_time(self):
        self.host.add_time(60)

    def set_bots(self, d):
        if not self.host:
            return
        self.host.bots = max(0, min(W.MAX_PCS - len(self.host.order()), self.host.bots + d))
        self.store.set("bots", self.host.bots)

    def start(self):
        if not self.host:
            return
        self.host.title = self.klass
        self.host.start_level(self.selected)
        self.store.klass(self.klass)["last"] = self.selected
        self.store.set("class", self.klass)
        self.page = "lesson"
        self.help_k = None
        self.views = {}
        self.view_key = "all"
        self.tr = V.Tracker(self.host.forest)
        self._forest_seen = self.host.forest
        self.event_seen = self.host.forest.event_id
        self.celebrated = False
        self.confetti.clear()
        self.app.sounds.play("swoosh", 0.7)

    def pause(self):
        self.host.pause()

    def freeze(self):
        self.host.freeze()

    def restart_level(self):
        self.selected = self.host.level_id
        self.start()

    def next_level(self):
        nxt = W.next_level(self.host.level_id)
        if nxt:
            self.selected = nxt
            self.start()

    def finish_game(self):
        """Η τελευταία πίστα πέτυχε: τέλος του παιχνιδιού, πίσω στην οργάνωση (χωρίς ερώτηση)."""
        self.host.to_lobby()
        self.page = "setup"
        self.help_k = None

    def _completed(self, level_id):
        k = self.store.klass(self.klass)
        k["done"][level_id] = k["done"].get(level_id, 0) + 1
        k["last"] = W.next_level(level_id) or level_id
        self.store.save()

    def _resume_level(self):
        k = self.store.klass(self.klass)
        last = k.get("last")
        if last in W.BY_ID:
            return last
        return W.LEVELS[0]["id"]

    # ------------------------------------------------------------ βοήθεια
    def open_help(self, k):
        f = self.host.forest
        if k not in f.plots:
            return
        self.help_k = k
        self.msg_menu = False
        p = f.plots[k]
        box = (max(0, p["x0"] - 1), max(0, p["y0"] - 1), min(f.W, p["x0"] + W.PLOT + 1), min(f.H, p["y0"] + W.PLOT + 1))
        names = {kk: self.host.name_of(kk) for kk in f.plots}
        rect = pygame.Rect(HELP.x + 20, HELP.y + 84, 600, 420)
        self.help_view = V.ForestView(f, rect, box=box, me=k, names=names, decor=False)
        self.codeview = code.CodeView((HELP.x + 648, HELP.y + 124, 496, 170))
        self.app.sounds.play("select", 0.5)

    def close_help(self):
        self.help_k = None
        self.msg_menu = False

    def help(self, kind, data=None):
        k = self.help_k
        if k is None:
            return
        if kind == "auto" and self.host.mode != "drive":
            self.host.help(k, "solution")
        elif kind == "auto":
            self.host.set_auto(k, True)
        else:
            self.host.help(k, kind, data)
        self.sent[(k, kind)] = self.time
        self.msg_menu = False

    def toggle_msgs(self):
        self.msg_menu = not self.msg_menu

    def reset_plot(self):
        if self.help_k is None:
            return
        if self.host.mode != "drive":
            self.host.set_auto(self.help_k)
        else:
            self.host.reset_plot(self.help_k)
        self.sent[(self.help_k, "reset")] = self.time

    # ------------------------------------------------------------ γεγονότα
    def buttons(self):
        if self.confirm:
            return [self.btn_yes, self.btn_no]
        if self.page == "setup":
            out = [self.btn_back, self.btn_sound, self.btn_start, self.btn_bot_minus, self.btn_bot_plus,
                   self.btn_plan_minus, self.btn_plan_plus]
            self.btn_start.enabled = self.host is not None
            self.btn_start.label = f"Ξεκινάμε: πίστα {W.level(self.selected)['no']}"
            return out
        if self.help_k is not None:
            out = [b for _, b in self.help_btns] + [self.btn_msg, self.btn_reset, self.btn_close]
            auto = self.host.forest.auto.get(self.help_k)
            prog = self.host.mode != "drive"
            b3, b4 = self.help_btns[2][1], self.help_btns[3][1]
            if prog:
                b3.label, b3.icon = "Λάθος μπλοκ", art.icon_puzzle
                b4.label, b4.icon = "Λύση", art.icon_check
                self.btn_reset.label = "Σειρά τους" if auto else "Αυτόματο R2"
                self.btn_reset.icon = art.icon_hand if auto else art.icon_robot
            else:
                b3.label, b3.icon = "Επόμενη κίνηση", art.icon_arrow_key
                b4.label = "Σειρά τους" if auto else "Λύση"
                b4.icon = art.icon_hand if auto else art.icon_check
                self.btn_reset.label, self.btn_reset.icon = "Ξανά", ui.icon_again
            if self.msg_menu:
                out += self.msg_btns
            return out
        h = self.host
        if h.mode != "drive":
            # χρόνος, Εκτέλεση! (ή ο επόμενος γύρος), +1 λεπτό, Πάγωμα, Παύση
            self.btn_pause.rect.topleft = (1176, 8)
            self.btn_freeze.rect.topleft = (1070, 8)
            out = [self.btn_home, self.btn_freeze, self.btn_pause]
            if h.phase == "result":
                self.btn_round.label = f"Γύρος {h.round + 1}"
                out.append(self.btn_round)
            elif h.phase in ("plan", "run"):
                self.btn_run.enabled = h.phase == "plan"
                out.append(self.btn_run)
            if h.phase == "plan" and h.plan_seconds > 0:
                out.append(self.btn_time)
        else:
            self.btn_pause.rect.topleft = (956, 8)
            self.btn_freeze.rect.topleft = (850, 8)
            out = [self.btn_home, self.btn_freeze, self.btn_pause, self.btn_restart]
            if W.next_level(h.level_id) is not None:            # στην τελευταία πίστα: όχι «Επόμενη»
                out.append(self.btn_next)
        self.btn_pause.label = "Συνέχεια" if h.paused else "Παύση"
        self.btn_freeze.label = "Ξεπάγωμα" if h.frozen else "Πάγωμα"
        self.btn_next.enabled = W.next_level(h.level_id) is not None
        if h.forest and (h.forest.done if h.mode == "drive" else h.phase == "done"):
            card = self._done_card()
            last = W.next_level(h.level_id) is None
            done_next = self.btn_done_end if last else self.btn_done_next
            done_next.rect.topleft = (card.centerx + 10, card.bottom - 68)
            self.btn_done_again.rect.topright = (card.centerx - 10, card.bottom - 68)
            out += [done_next, self.btn_done_again]
        return out

    def _done_card(self):
        last = self.host.level_id is not None and W.next_level(self.host.level_id) is None
        card = pygame.Rect(0, 0, 640, 204 if last else 170)
        card.midtop = (self.map_rect().centerx, self.map_rect().y + 12)
        return card

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
            if self.confirm:
                return
            if self.page == "setup":
                self._setup_down(e.pos)
            else:
                self._lesson_down(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            b, self.pressed = self.pressed, None
            if b:
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
                return
            if self.drag:
                self._drop_pc(e.pos)
        elif e.type == pygame.TEXTINPUT and self.typing is not None:
            self.typing = (self.typing + "".join(ch for ch in e.text if ch.isalnum()))[:6].upper()
        elif e.type == pygame.KEYDOWN:
            self._key(e)

    def _key(self, e):
        if self.typing is not None:
            if e.key == pygame.K_BACKSPACE:
                self.typing = self.typing[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                name = self.store.add_class(self.typing) if self.typing else None
                self.typing = None
                if name:
                    self._pick_class(name)
            elif e.key == pygame.K_ESCAPE:
                self.typing = None
            return
        if e.key == pygame.K_ESCAPE:
            if self.confirm:
                self.confirm = None
            elif self.help_k is not None:
                self.close_help()
            elif self.page == "lesson":
                self.ask_home()
            else:
                self.leave()
        elif self.page == "lesson" and self.help_k is None:
            if e.key == pygame.K_SPACE:
                self.pause()
            elif e.key == pygame.K_f:
                self.freeze()
            elif e.key == pygame.K_TAB:
                self.big = not self.big
                self.views = {}

    def _pick_class(self, name):
        self.klass = name
        self.store.set("class", name)
        self.selected = self._resume_level()
        if self.host:
            self.host.title = name

    def _setup_regions(self):
        regions = []
        x = 34
        for name in self.store.data["order"] + ["+ Νέα"]:
            w = ui.font(16).size(name)[0] + 30
            regions.append(("class", name, pygame.Rect(x, 150, w, 36)))
            x += w + 8
        y = 250
        no = 1
        for ch in W.CHAPTERS:
            ids = ch.get("levels") or [None] * ch.get("soon", 0)
            for i, lid in enumerate(ids):
                regions.append(("level", lid, pygame.Rect(174 + i * 42 - 17, y - 17, 34, 34)))
                no += 1
            y += 42
        return regions

    def _setup_down(self, pos):
        for kind, val, r in self._setup_regions():
            if r.collidepoint(pos):
                if kind == "class":
                    if val.startswith("+"):
                        self.typing = ""
                    else:
                        self._pick_class(val)
                elif kind == "level" and val:
                    self.selected = val
                self.app.sounds.play("select", 0.5)
                return
        if not self.host:
            return
        for i, r in enumerate(SEATS):
            if r.collidepoint(pos):
                p = next((p for p in self.host.pcs.values() if p["seat"] == i), None)
                if p:
                    self.drag = {"pc": p["pc"], "grab": (pos[0] - r.x, pos[1] - r.y)}
                return

    def _drop_pc(self, pos):
        d, self.drag = self.drag, None
        for i, r in enumerate(SEATS):
            if r.collidepoint(pos):
                self.host.seat(d["pc"], i)
                self._save_seats()
                self.app.sounds.play("place", 0.6)
                return

    def _save_seats(self):
        seats = self.store.data.setdefault("seats", {})
        for p in self.host.pcs.values():
            if p["host"] and p["seat"] is not None:
                seats[p["host"]] = p["seat"]
        self.store.save()

    def _apply_saved_seats(self):
        """Οι υπολογιστές που ξέρουμε πάνε μόνοι τους στη θέση τους (με το όνομα του υπολογιστή)."""
        seats = self.store.data.get("seats", {})
        if self.host.state != "lobby":
            return
        for p in list(self.host.pcs.values()):
            want = seats.get(p["host"])
            if want is not None and p["seat"] != want and not p.get("_placed"):
                self.host.seat(p["pc"], want)
            p["_placed"] = True

    def map_rect(self):
        return MAP_BIG if self.big else MAP

    def view(self):
        key = (self.view_key, self.big)
        if key not in self.views:
            f = self.host.forest
            names = {k: self.host.name_of(k) for k in f.plots}
            box = None if self.view_key == "all" else f.data["teams"][self.view_key]["box"]
            scale = 0.85 if self.view_key == "all" and f.data["n"] > 6 else 1.0
            self.views[key] = V.ForestView(f, self.map_rect(), box=box, names=names, tag_scale=scale)
        return self.views[key]

    def _tabs(self):
        f = self.host.forest
        out = []
        x = 14
        labels = [("all", "Όλο το δάσος")] + [(i, t["name"]) for i, t in enumerate(f.data["teams"])]
        if len(labels) == 2:
            labels = labels[:1]
        for key, text in labels:
            w = ui.font(15).size(text)[0] + 28
            out.append((key, text, pygame.Rect(x, 102, w, 31)))
            x += w + 8
        return out

    def _chip_rects(self):
        """(οικόπεδο, ορθογώνιο) για τα ονόματα στο κάτω πάνελ, ανά ποτάμι."""
        f = self.host.forest
        teams = f.data["teams"]
        n = len(teams)
        gw = (CHIPS.w - 24 - (n - 1) * 14) / n
        out, heads = [], []
        for i, t in enumerate(teams):
            gx = CHIPS.x + 12 + i * (gw + 14)
            heads.append((i, gx, gw))
            cols = 2 if gw > 200 else 1
            rows = math.ceil(len(t["plots"]) / cols)
            ch = min(42, (CHIPS.h - 42) / rows - 5)
            cw = (gw - 8 * (cols - 1)) / cols
            for j, k in enumerate(t["plots"]):
                r = pygame.Rect(round(gx + (j % cols) * (cw + 8)), round(CHIPS.y + 34 + (j // cols) * (ch + 5)),
                                round(cw), round(ch))
                out.append((k, r))
        return out, heads

    def _lesson_down(self, pos):
        if self.help_k is not None:
            if self.msg_menu:
                self.msg_menu = False
            elif not HELP.collidepoint(pos):
                self.close_help()
            return
        f = self.host.forest
        if not self.big:
            for key, text, r in self._tabs():
                if r.collidepoint(pos):
                    self.view_key = key
                    self.app.sounds.play("select", 0.4)
                    return
            for k, r in self._chip_rects()[0]:
                if r.collidepoint(pos):
                    self.open_help(k)
                    return
        if self.map_rect().collidepoint(pos) and not f.done:
            k = self.view().plot_at(pos)
            if k:
                self.open_help(k)

    # ------------------------------------------------------------ χρόνος
    def update(self, dt):
        self.time += dt
        h = self.host
        if h:
            h.tick(dt)
            self._apply_saved_seats()
            if self.page == "lesson" and h.forest is not None:
                f = h.forest
                if f is not self._forest_seen:
                    self._forest_seen = f
                    self.tr = V.Tracker(f)
                    self.views = {}
                    self.event_seen = 0
                    self._blame_cache = {}
                    if self.help_k is not None:
                        k = self.help_k
                        self.open_help(k)
                for e in list(f.events):
                    if e[0] <= self.event_seen:
                        continue
                    self.event_seen = e[0]
                    kind = e[2]
                    if kind == "fire_out":
                        self.app.sounds.play("complete", 0.7)
                    elif kind == "saved":
                        self.app.sounds.play("hop", 0.3)
                    elif kind == "bump":
                        self.tr.bump(e[3], self.time)
                self.tr.sync(self.time)
                if (f.done if h.mode == "drive" else h.phase == "done") and not self.celebrated:
                    self.celebrated = True
                    self.confetti.burst(WIDTH, 180)
                    if W.next_level(h.level_id) is None:          # το τέλος του παιχνιδιού: διπλή γιορτή
                        self.confetti.burst(WIDTH, 260)
                    self.app.sounds.play("win")
        self.confetti.update(dt, self.time, HEIGHT)
        hover = False
        for b in self.buttons():
            b.hover = b.enabled and b.contains(self.mouse)
            hover = hover or b.hover
        if self.page == "setup":
            hover = hover or any(r.collidepoint(self.mouse) for kind, v, r in self._setup_regions()
                                 if kind == "class" or v)
        want = pygame.SYSTEM_CURSOR_HAND if hover or self.drag else pygame.SYSTEM_CURSOR_ARROW
        if want != self.cursor:
            try:
                pygame.mouse.set_cursor(want)
            except (pygame.error, TypeError):
                pass
            self.cursor = want

    # ------------------------------------------------------------ ζωγραφική
    def draw(self, screen):
        screen.blit(self.room, (0, 0))
        if self.page == "setup" or not self.host or self.host.forest is None:
            self._draw_setup(screen)
        else:
            self._draw_lesson(screen)
            if self.help_k is not None:
                self._draw_help(screen)
        self.confetti.draw(screen)
        if self.confirm:
            self._draw_confirm(screen)

    def _top(self, s, chip, chip_col, title):
        art.top_bar(s)
        x0 = 136
        xr = min((b.rect.x for b in self.buttons() if b.rect.y < 20 and b.rect.x > 600), default=WIDTH - 14) - 10
        cx = (x0 + xr) / 2
        art.mode_title(s, cx, 46, chip, title, chip_col=chip_col)

    # ---- οργάνωση
    def _draw_setup(self, s):
        self._top(s, "Δάσκαλος", art.TEAL, "Αποστολές Διάσωσης: οργάνωση μαθήματος")
        L = pygame.Rect(14, 104, 410, 604)
        art.panel(s, L)
        ui.text(s, "Τάξη", (L.x + 20, L.y + 26), 20, INK, anchor="midleft")
        done = self.store.klass(self.klass)["done"]
        for kind, val, r in self._setup_regions():
            if kind == "class":
                if val.startswith("+"):
                    pygame.draw.rect(s, art.WHITE, r, border_radius=18)
                    pygame.draw.rect(s, (190, 198, 212), r, width=2, border_radius=18)
                    label = (self.typing + "|") if self.typing is not None else val
                    ui.text(s, label, r.center, 16, INK if self.typing is not None else GREY)
                else:
                    on = val == self.klass
                    pygame.draw.rect(s, art.TEAL if on else (240, 243, 248), r, border_radius=18)
                    ui.text(s, val, r.center, 16, art.WHITE if on else INK)
        ui.text(s, "Πίστα", (L.x + 20, L.y + 112), 20, INK, anchor="midleft")
        ui.text(s, f"κίτρινο: την έχει περάσει η {self.klass}", (L.right - 20, L.y + 113), 13, LIGHT,
                anchor="midright", bold=False)
        y = 250
        no = 1
        for ch in W.CHAPTERS:
            name, col = art.MODE[ch["mode"]]
            ui.text(s, name, (L.x + 20, y), 16, col, anchor="midleft")
            ids = ch.get("levels") or [None] * ch.get("soon", 0)
            for i, lid in enumerate(ids):
                cx = 174 + i * 42
                if lid and lid == self.selected:
                    ui.circle(s, col, (cx, y), 17)
                    ui.text(s, str(no), (cx, y), 16, art.WHITE)
                    pygame.draw.circle(s, (250, 200, 60), (cx, y), 21, 3)
                elif lid and lid in done:
                    ui.circle(s, (250, 200, 60), (cx, y), 15, ui.shade((250, 200, 60), 0.7))
                    ui.text(s, str(no), (cx, y), 14, art.WHITE)
                else:
                    ui.circle(s, ui.mix(col, art.WHITE, 0.5 if lid else 0.75), (cx, y), 15)
                    ui.circle(s, (246, 248, 252), (cx, y), 12)
                    ui.text(s, str(no), (cx, y), 14, ui.shade(col, 0.8) if lid else ui.mix(col, art.WHITE, 0.5))
                no += 1
            if not ch.get("levels"):
                ui.text(s, "σύντομα", (174 + len(ids) * 42 - 6, y), 12, LIGHT, anchor="midleft", bold=False)
            y += 42
        lv = W.level(self.selected)
        box = pygame.Rect(L.x + 16, L.y + 318, L.w - 32, 92)
        pygame.draw.rect(s, (238, 246, 252), box, border_radius=14)
        pygame.draw.rect(s, (190, 212, 236), box, width=2, border_radius=14)
        ui.text(s, f"{lv['no']} · {lv['title']}", (box.x + 14, box.y + 20), 17, INK, anchor="midleft")
        for i, t in enumerate(lv["about"]):
            ui.text(s, t, (box.x + 14, box.y + 46 + i * 22), 14, GREY, anchor="midleft", bold=False)
        if W.level(self.selected).get("mode", "drive") != "drive":
            ui.text(s, "Χρόνος για το πρόγραμμα", (L.x + 20, L.y + 436), 16, INK, anchor="midleft")
            self.btn_plan_minus.rect.center = (L.x + 250, L.y + 436)
            self.btn_plan_plus.rect.center = (L.x + 360, L.y + 436)
            ps = self.host.plan_seconds if self.host else 180
            ui.text(s, "χωρίς" if ps == 0 else f"{ps // 60}:{ps % 60:02d}", (L.x + 305, L.y + 436), 20, INK)
        else:
            self.btn_plan_minus.rect.topleft = (-200, -200)
            self.btn_plan_plus.rect.topleft = (-200, -200)
        ui.text(s, "Αυτόματα R2 (επίδειξη)", (L.x + 20, L.y + 476), 16, INK, anchor="midleft")
        self.btn_bot_minus.rect.center = (L.x + 250, L.y + 476)
        self.btn_bot_plus.rect.center = (L.x + 360, L.y + 476)
        ui.text(s, str(self.host.bots if self.host else 0), (L.x + 305, L.y + 476), 20, INK)
        n_pc = len(self.host.order()) if self.host else 0
        n = max(W.MIN_PCS, n_pc + (self.host.bots if self.host else 0))
        sizes = W.team_sizes(n)
        rivers = " + ".join(str(x) for x in sizes)
        ui.text(s, f"Συνδεδεμένοι: {n_pc} · ποτάμια: {len(sizes)} ({rivers})", (L.x + 20, L.y + 512), 14, GREY,
                anchor="midleft", bold=False)
        if n_pc < 2:
            ui.text(s, "Με λιγότερους από 2, μπαίνουν αυτόματα R2.", (L.x + 20, L.y + 534), 13, LIGHT,
                    anchor="midleft", bold=False)
        if self.error:
            ui.text(s, self.error, (L.centerx, L.bottom - 110), 14, art.STUCK)
        self._draw_room(s)
        for b in self.buttons():
            b.draw(s, self.time)

    def _draw_room(self, s):
        R = ROOM
        art.panel(s, R, "Η αίθουσα")
        h = self.host
        if h:
            ui.text(s, f"διεύθυνση: {h.ip}", (R.right - 20, R.y + 25), 15, art.TEAL, anchor="midright")
        ui.text(s, "Σύρε τους υπολογιστές στις θέσεις τους · αριθμός = οικόπεδο στο ποτάμι", (R.right - 20, R.y + 48),
                13, LIGHT, anchor="midright", bold=False)
        layout = team_layout(len(h.order()) if h else 0, h.bots if h else 0)
        by_seat = {p["seat"]: p for p in h.pcs.values()} if h else {}
        order = h.order() if h else []
        pos_of = {pc: i for i, pc in enumerate(order)}
        firsts = {}
        for i, r in enumerate(SEATS):
            p = by_seat.get(i)
            if p and self.drag and self.drag["pc"] == p["pc"]:
                self._seat(s, r, None, i)
                continue
            if p:
                idx = pos_of.get(p["pc"])
                t, j = layout[idx] if idx is not None and idx < len(layout) else (0, 0)
                self._seat(s, r, p, i, t, j)
                firsts.setdefault(t, r)
            else:
                self._seat(s, r, None, i)
        for t, r in firsts.items():
            if r.x < R.x + 200:
                art.pill(s, (r.right + 10, r.centery), f"Ποτάμι {W.TEAM_NAMES[t]}", V.TEAM_COLS[t % 7], art.WHITE, 14,
                         anchor="midleft")
            else:
                art.pill(s, (r.centerx, r.bottom + 6), f"Ποτάμι {W.TEAM_NAMES[t]}", V.TEAM_COLS[t % 7], art.WHITE, 13,
                         anchor="midtop")
        desk = pygame.Rect(0, 0, 220, 54)
        desk.midbottom = (R.centerx, R.bottom - 18)
        pygame.draw.rect(s, (236, 240, 246), desk, border_radius=12)
        pygame.draw.rect(s, (190, 198, 212), desk, width=2, border_radius=12)
        pygame.draw.rect(s, (60, 70, 90), (desk.x + 14, desk.y + 12, 34, 24), border_radius=3)
        ui.text(s, "Δάσκαλος", (desk.x + 60, desk.centery - 8), 16, INK, anchor="midleft")
        ui.text(s, "και προβολέας", (desk.x + 60, desk.centery + 12), 13, GREY, anchor="midleft", bold=False)
        if not by_seat:
            for i, t in enumerate(("Οι μαθητές ανοίγουν «Αποστολές Διάσωσης → Μαθητές»",
                                   "και γράφουν το όνομά τους.")):
                ui.text(s, t, (R.centerx, R.y + 300 + i * 26), 16, GREY, bold=False)
        else:
            for i, t in enumerate(("Οι διπλανοί στην αίθουσα είναι διπλανοί και στο δάσος:",
                                   "μιλάνε μεταξύ τους χωρίς να σηκωθούν.")):
                ui.text(s, t, (R.centerx, R.y + 330 + i * 22), 14, GREY, bold=False)
        if self.drag:
            p = h.pcs.get(self.drag["pc"])
            if p:
                r = pygame.Rect(self.mouse[0] - self.drag["grab"][0], self.mouse[1] - self.drag["grab"][1], 104, 46)
                self._seat(s, r, p, None, 0, 0, lifted=True)

    def _seat(self, s, r, p, num, team=0, plot=0, lifted=False):
        if p is None:
            pygame.draw.rect(s, (248, 250, 253), r, border_radius=10)
            for x in range(r.x + 8, r.right - 8, 10):
                pygame.draw.line(s, (200, 206, 218), (x, r.y), (x + 5, r.y))
                pygame.draw.line(s, (200, 206, 218), (x, r.bottom - 1), (x + 5, r.bottom - 1))
            for y in range(r.y + 6, r.bottom - 6, 10):
                pygame.draw.line(s, (200, 206, 218), (r.x, y), (r.x, y + 5))
                pygame.draw.line(s, (200, 206, 218), (r.right - 1, y), (r.right - 1, y + 5))
            if num is not None:
                ui.text(s, str(num + 1), r.center, 14, (190, 196, 208))
            return
        col = V.TEAM_COLS[team % 7]
        if lifted:
            ui.glow(s, r.inflate(10, 10), (255, 214, 60), 140, radius=12)
        pygame.draw.rect(s, ui.mix(col, art.WHITE, 0.86), r, border_radius=10)
        pygame.draw.rect(s, col, r, width=2, border_radius=10)
        narrow = r.w < 90
        on = p.get("on", True)
        mon = pygame.Rect(r.x + 7, r.y + 8, 18, 13)
        pygame.draw.rect(s, (60, 70, 90) if on else (170, 176, 188), mon, border_radius=2)
        pygame.draw.rect(s, (60, 70, 90), (mon.centerx - 2, mon.bottom, 4, 4))
        name = p["name"]
        if narrow:
            ui.text(s, name[:9], (r.centerx, r.y + 37), 13, INK)
        else:
            ui.text(s, name[:11], (r.x + 30, r.y + 15), 14, INK, anchor="midleft")
            ui.text(s, (p["host"] or "")[:14], (r.x + 8, r.bottom - 11), 11, GREY, anchor="midleft", bold=False)
        c = (r.right - 12, r.bottom - 12) if not narrow else (r.right - 12, r.y + 14)
        ui.circle(s, V.PLOT_COLS[plot % 5], c, 9)
        ui.text(s, str(plot + 1), c, 12, art.WHITE)

    # ---- μάθημα
    def _draw_lesson(self, s):
        h = self.host
        f = h.forest
        lv = W.level(h.level_id)
        v = self.view()
        v.draw(s, self.time, self.tr)
        rect = self.map_rect()
        # κόκκινο «!» δίπλα σε όποιο R2 χρειάζεται βοήθεια
        statuses = {k: h.status(k) for k in f.plots}
        for k, st in statuses.items():
            X, Y, _ = self.tr.robot(k, self.time)
            if not v.in_box((int(X), int(Y))):
                continue
            if st in ("stuck", "idle"):
                art.alert(s, v.pt(X - 0.55, Y, 45))
            elif h.mode != "drive" and h.phase in ("result", "done") and k in h.results:
                art.mark(s, v.pt(X - 0.55, Y, 45), h.results[k][0] == "ok", 12)
        if f.paused:
            art.pill(s, (rect.x + 16, rect.y + 14), "Παύση", (120, 130, 150), art.WHITE)
        art.map_frame(s, rect)
        if not self.big:
            for key, text, r in self._tabs():
                on = key == self.view_key
                pygame.draw.rect(s, art.TEAL if on else art.WHITE, r, border_radius=r.h // 2)
                if not on:
                    pygame.draw.rect(s, art.LINE, r, width=2, border_radius=r.h // 2)
                ui.text(s, text, r.center, 15, art.WHITE if on else INK)
            saved, total, out, fires = f.counts()
            txt = f"Ζώα στο λιβάδι {saved}/{total}" + (f" · Φωτιές σβηστές {out}/{fires}" if fires else "")
            if h.mode != "drive":
                hum = h.humans()
                if h.phase == "plan":
                    txt = f"Γύρος {h.round} · Έτοιμοι {sum(1 for k in hum if h.ready.get(k))} από {len(hum)}"
                elif h.phase == "run":
                    txt = "Εκτέλεση: όλα τα R2 μαζί · " + txt
                elif h.phase == "result":
                    left = max(0, int(h.result_at + net.RESULT_TIME - h.clock))
                    txt = f"Γύρος {h.round}: " + txt + f" · γύρος {h.round + 1} σε {left}"
            pr = art.pill(s, (WIDTH - 14, 102), txt, art.WHITE, INK, 15, anchor="topright")
            tabs = self._tabs()
            if tabs[-1][2].right < 600 and pr.x > 960:
                ui.text(s, "κλικ σε όνομα ή οικόπεδο: βοήθεια · Tab: μόνο το δάσος", (WIDTH // 2 + 140, 118), 13, LIGHT,
                        bold=False)
            self._draw_chips(s, statuses)
        title = f"Πίστα {lv['no']}: {lv['title']}"
        self._top(s, lv.get("pill", lv.get("mode", "drive")), None, title)
        for b in self.buttons():
            if b.rect.y < 20 and b not in (self.btn_done_next, self.btn_done_again):
                b.draw(s, self.time)
        if h.mode != "drive" and h.phase == "plan" and h.plan_seconds > 0:
            r = pygame.Rect(0, 0, 124, 60)
            r.topright = (self.btn_run.rect.x - 10, 16)
            pygame.draw.rect(s, art.WHITE, r, border_radius=18)
            pygame.draw.rect(s, art.LINE, r, width=2, border_radius=18)
            art.icon_timer(s, (r.x + 28, r.centery), 32, GREY)
            left = int(h.left)
            ui.text(s, f"{left // 60}:{left % 60:02d}", (r.x + 80, r.centery), 28, INK)
        if f.done if h.mode == "drive" else h.phase == "done":
            self._draw_done(s)

    def _draw_chips(self, s, statuses):
        h = self.host
        f = h.forest
        art.panel(s, CHIPS)
        chips, heads = self._chip_rects()
        for i, gx, gw in heads:
            t = f.data["teams"][i]
            saved, total, out, fires = f.counts(i)
            ui.text(s, t["name"], (gx + 6, CHIPS.y + 18), 17, V.TEAM_COLS[i % 7], anchor="midleft")
            sub = f"{saved}/{total} ζώα" + (" · φωτιά σβηστή" if fires and out == fires else "")
            ui.text(s, sub, (gx + gw - 4, CHIPS.y + 18), 13, GREY, anchor="midright", bold=False)
            if i:
                pygame.draw.line(s, (230, 234, 240), (gx - 7, CHIPS.y + 12), (gx - 7, CHIPS.bottom - 12), 2)
        for k, r in chips:
            st = statuses[k]
            text, col = art.ST_TEXT[st]
            if st == "stuck":
                last = f.stats[k]["last"]
                if f.stats[k]["first"] is not None and f.clock - last > 20:
                    m = int(f.clock - last)
                    text = f"κόλλησε {m // 60}:{m % 60:02d}"
            elif st == "idle":
                m = int(f.clock)
                text = f"δεν κουνήθηκε {m // 60}:{m % 60:02d}"
            if st == "write":
                from games.program import logic as PL
                n = PL.count(h.programs.get(k) or [])
                text = f"γράφουν · {n} εντολ{'ή' if n == 1 else 'ές'}" if n else "δεν έγραψαν ακόμα"
            elif st == "fail":
                text = art.result_text(h.results.get(k))
            hot = st in ("stuck", "idle", "fail")
            hov = r.collidepoint(self.mouse)
            pygame.draw.rect(s, (255, 238, 236) if hot else ((238, 244, 252) if hov else (246, 248, 252)), r,
                             border_radius=12)
            pygame.draw.rect(s, art.STUCK if hot else (224, 228, 236), r, width=2, border_radius=12)
            pygame.draw.rect(s, V.robot_color(f, k), (r.x + 7, r.y + 7, 7, r.h - 14), border_radius=3)
            big = r.h >= 38
            ui.text(s, h.name_of(k)[:12], (r.x + 22, r.y + (13 if big else r.h // 2 - 6)), 15 if big else 13, INK,
                    anchor="midleft")
            ui.circle(s, col, (r.x + 26, r.y + r.h - (12 if big else 7)), 4)
            ui.text(s, text, (r.x + 35, r.y + r.h - (12 if big else 7)), 13 if big else 11, col, anchor="midleft")

    def _draw_done(self, s):
        h = self.host
        f = h.forest
        card = self._done_card()
        ui.panel(s, card, (255, 252, 240), radius=26, border=(250, 190, 50))
        for i, dx in enumerate((-270, -225, -180)):
            ui.star(s, (card.centerx + dx, card.y + 42 - (6 if i == 1 else 0)), 20 if i == 1 else 16, (252, 204, 60))
        ui.text(s, "Μπράβο, τάξη!", (card.centerx + 40, card.y + 40), 38, art.TITLE, shadow=(250, 214, 150))
        saved, total, out, fires = f.counts()
        line = f"Σώθηκαν {saved} από {total} ζώα" + (f" · έσβησαν {out} από {fires} φωτιές" if fires else "")
        ui.text(s, line, (card.centerx, card.y + 82), 19, INK)
        if W.next_level(h.level_id) is None:
            ui.text(s, "Τέλος του παιχνιδιού! Σώσατε το δάσος σε όλες τις αποστολές.", (card.centerx, card.y + 114), 18, art.OK)
            self.btn_done_end.draw(s, self.time)
        else:
            self.btn_done_next.draw(s, self.time)
        self.btn_done_again.draw(s, self.time)

    # ---- βοήθεια
    def _draw_help(self, s):
        h = self.host
        f = h.forest
        k = self.help_k
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 30, 50, 150))
        s.blit(veil, (0, 0))
        ui.panel(s, HELP, art.WHITE, radius=26, border=art.LINE)
        pygame.draw.rect(s, V.robot_color(f, k), (HELP.x + 22, HELP.y + 22, 10, 44), border_radius=5)
        ui.text(s, h.name_of(k), (HELP.x + 44, HELP.y + 34), 26, INK, anchor="midleft")
        p = f.plots[k]
        t = f.data["teams"][p["team"]]
        pc = h.assign.get(k)
        host = h.pcs.get(pc, {}).get("host", "") if pc else "αυτόματο R2"
        ui.text(s, f"οικόπεδο {t['plots'].index(k) + 1} · {t['name']} · {host}", (HELP.x + 44, HELP.y + 60), 14, GREY,
                anchor="midleft", bold=False)
        st = h.status(k)
        text, col = art.ST_TEXT[st]
        art.pill(s, (HELP.x + 340, HELP.y + 26), text, col, art.WHITE, 15)
        self.help_view.draw(s, self.time, self.tr)
        pygame.draw.rect(s, art.LINE, self.help_view.rect, width=2, border_radius=20)
        art.pill(s, (self.help_view.rect.x + 12, self.help_view.rect.y + 10), "Τώρα, ζωντανά", art.WHITE, INK, 14)
        P = pygame.Rect(HELP.x + 640, HELP.y + 84, 512, 220)
        pygame.draw.rect(s, (248, 249, 252), P, border_radius=18)
        pygame.draw.rect(s, (224, 228, 236), P, width=2, border_radius=18)
        if h.mode != "drive":
            ui.text(s, "Το πρόγραμμά τους", (P.x + 16, P.y + 22), 17, INK, anchor="midleft")
            ui.text(s, "ζωντανά, όπως το γράφουν", (P.right - 16, P.y + 23), 13, LIGHT, anchor="midright", bold=False)
            prog = h.programs.get(k) or []
            res = h.test_result(k)
            self.codeview.set_program(prog)
            self.codeview.draw(s, error=tuple(res[2]) if res[0] != "ok" and res[2] else None)
            if not prog:
                ui.text(s, "Δεν έχουν γράψει ακόμα εντολές.", (P.centerx, P.centery + 10), 16, LIGHT, bold=False)
        else:
            ui.text(s, "Το πρόγραμμα που έγραψαν οδηγώντας", (P.x + 16, P.y + 22), 17, INK, anchor="midleft")
            rec = f.rec.get(k, [])
            self.codeview.set_program(rec)
            self.codeview.draw(s)
            if not rec:
                ui.text(s, "Δεν έχουν κουνήσει ακόμα το R2.", (P.centerx, P.centery + 10), 16, LIGHT, bold=False)
        Hb = pygame.Rect(HELP.x + 640, HELP.y + 316, 512, 188)
        pygame.draw.rect(s, (255, 250, 228), Hb, border_radius=18)
        pygame.draw.rect(s, (246, 214, 120), Hb, width=2, border_radius=18)
        art.icon_bulb(s, (Hb.x + 30, Hb.y + 30), 34, (230, 170, 30))
        ui.text(s, "Τι γίνεται", (Hb.x + 52, Hb.y + 30), 17, INK, anchor="midleft")
        stt = f.stats[k]
        facts = f"Κινήσεις: {stt['moves']} · χτυπήματα: {stt['bumps']}"
        if h.mode != "drive":
            hist = h.history.get(k, [])
            facts = "Γύροι: " + (" ".join("✓" if r[0] == "ok" else "✗" for r in hist) or "κανένας ακόμα")
            facts = facts.replace("✓", "πέτυχε").replace("✗", "όχι")
        ui.text(s, facts, (Hb.x + 20, Hb.y + 62), 15, GREY, anchor="midleft", bold=False)
        hint = h.suggest_hint(k)
        for i, ln in enumerate(art.wrap("Υπόδειξη: «" + hint + "»", 15, Hb.w - 40)[:4]):
            ui.text(s, ln, (Hb.x + 20, Hb.y + 92 + i * 22), 15, INK, anchor="midleft")
        ui.text(s, "Βοήθεια βήμα βήμα (φαίνεται στην οθόνη τους)", (HELP.x + 24, HELP.bottom - 130), 15, GREY,
                anchor="midleft", bold=False)
        ui.text(s, "Για το οικόπεδο", (HELP.x + 664, HELP.bottom - 130), 15, GREY, anchor="midleft", bold=False)
        for i, (kind, b) in enumerate(self.help_btns):
            b.draw(s, self.time)
            ui.circle(s, art.WHITE, (b.rect.x + 16, b.rect.y + 16), 12, ui.shade(b.color, 0.7))
            ui.text(s, str(i + 1), (b.rect.x + 16, b.rect.y + 16), 14, ui.shade(b.color, 0.6))
            sent = self.sent.get((k, kind))
            if sent is not None and self.time - sent < 6:
                art.mark(s, (b.rect.right - 8, b.rect.y + 4), True, 11)
        self.btn_msg.draw(s, self.time)
        self.btn_reset.draw(s, self.time)
        sent = self.sent.get((k, "reset"))
        if sent is not None and self.time - sent < 4:
            art.mark(s, (self.btn_reset.rect.right - 8, self.btn_reset.rect.y + 4), True, 11)
        self.btn_close.draw(s, self.time)
        if self.msg_menu:
            x, y = self.btn_msg.rect.x - 80, self.btn_msg.rect.y - 8 - len(self.msg_btns) * 50
            box = pygame.Rect(x - 10, y - 10, 320, len(self.msg_btns) * 50 + 14)
            ui.panel(s, box, art.WHITE, radius=16, border=art.LINE)
            for i, b in enumerate(self.msg_btns):
                b.rect.topleft = (x, y + i * 50)
                b.draw(s, self.time)

    def _draw_confirm(self, s):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 30, 50, 160))
        s.blit(veil, (0, 0))
        card = pygame.Rect(WIDTH // 2 - 320, 260, 640, 230)
        ui.panel(s, card, art.WHITE, radius=22)
        ui.text(s, self.confirm[1], (card.centerx, card.y + 70), 22, INK)
        self.btn_yes.rect.topright = (card.centerx - 10, card.bottom - 90)
        self.btn_no.rect.topleft = (card.centerx + 10, card.bottom - 90)
        self.btn_yes.draw(s, self.time)
        self.btn_no.draw(s, self.time)
