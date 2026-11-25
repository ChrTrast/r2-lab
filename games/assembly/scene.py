"""Η οθόνη της Συναρμολόγησης.

Αριστερά ο πάγκος: το R2 σε 3D πάνω στο πράσινο ταπέτο. Δεξιά το «Κουτί υλικών». Το παιδί σέρνει ένα
κομμάτι από το κουτί· όταν το φέρει κοντά στη θέση του, το κομμάτι τραβιέται σαν μαγνήτης, κολλάει
(«κλικ!») και οι βίδες του μπαίνουν και γυρίζουν μόνες τους. Τα βύσματα (μπαταρία, κινητήρες,
καλώδια RJ11) σέρνονται στις υποδοχές του ελεγκτή. Λάθος θέση: το κομμάτι γυρίζει στο κουτί και το R2
εξηγεί. Η κάμερα γυρίζει μόνη της στο κάθε βήμα (στο «Μόνος μου» όταν πιάνεις ένα κομμάτι) και με τα
κουμπιά ⟲ ⟳ «Ανάποδα». Στο τέλος ο διακόπτης ON ανάβει το R2 και μπορεί να κάνει μια βόλτα.
Οι κανόνες είναι στο logic.py, τα βήματα στο steps.py, τα σχήματα στο parts.py.
"""
import math

import pygame

from core import fx, ui
from core.app import HEIGHT, WIDTH, Scene
from games.runner import art as rart
from . import art, logic
from . import eng3d as E
from . import parts as P
from .steps import PARTS, PLUGS, SLOTS, STEP_INDEX, STEPS, TASK_WORDS

GAME_ID = "assembly"
TOP_H = 74
BENCH_W = 920
TRAY = pygame.Rect(932, 84, 336, 624)
ROBOT_AT = (462, 378)            # πού πέφτει το κέντρο του ρομπότ στην οθόνη
BASE_SCALE = 2.9                 # pixels ανά χιλιοστό
INSTR = pygame.Rect(16, 84, 610, 86)
BUBBLE = pygame.Rect(242, 612, 560, 96)
R2_AT, R2_SIZE = (866, 652), 92
SNAP_R = {logic.HELP: 95, logic.GUIDE: 78, logic.SOLO: 70}   # pixels: από εδώ αρχίζει ο μαγνήτης
DROP_R = 64                      # μέσα σε τόσα pixels από μια λάθος θέση, το R2 εξηγεί
PLUG_R = 26                      # πόσο κοντά στο βύσμα πρέπει να πατήσεις για να το πιάσεις
SOCKET_R = 38                    # ο μαγνήτης των υποδοχών
PLUG_Z = P.BOARD_TOP + 9         # το ύψος όπου «πετάει» το βύσμα που σέρνεις
SCREW_T = 0.3                    # δευτερόλεπτα για κάθε βίδα
MSG_T = 5.0                      # πόσο μένει ένα μήνυμα λάθους
ZC = 40                          # γύρω από αυτό το ύψος αναποδογυρίζει το ρομπότ
ANY_SIDE = ("motor_left", "motor_right", "wheel", "ultrasonic")   # φαίνονται και με το ρομπότ ανάποδα
MODE_INFO = {
    logic.HELP: ("Με βοήθεια", "Φαίνεται πού πάει", "κάθε κομμάτι", art.GREEN),
    logic.GUIDE: ("Με τον οδηγό", "Διαβάζεις το βήμα,", "βρίσκεις τη θέση", (62, 140, 226)),
    logic.SOLO: ("Μόνος μου", "Όλα τα κομμάτια στο κουτί:", "ποιο μπαίνει τώρα;", (226, 96, 52)),
}
START_CARD = pygame.Rect(WIDTH // 2 - 480, 108, 960, 520)
MODE_RECTS = {m: pygame.Rect(START_CARD.x + 36 + i * 300, START_CARD.y + 120, 280, 250)
              for i, m in enumerate(logic.MODES)}
TASK_CHIPS = [pygame.Rect(START_CARD.x + 210 + i * 94, START_CARD.y + 398, 86, 64) for i in range(7)]
BANNER = pygame.Rect(36, 84, 430, 150)
DRIVE_T = (1.2, 2.0, 1.2, 1.4)   # μπροστά, γύρος, πίσω, κούνημα
GHOST, GHOST_ALPHA = (150, 225, 255), 175    # το «φάντασμα» που δείχνει πού πάει ένα κομμάτι
THUMB_VIEW = {"ultrasonic": (150, 18), "line_sensor": (-30, 40), "lego": (-30, 40)}   # γωνία για τις κάρτες


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Flight:
    """Μια εικόνα κομματιού που πετάει από ένα σημείο σε άλλο (στη θέση της ή πίσω στο κουτί)."""

    def __init__(self, img, off, p0, p1, start, dur, arc=0.0, land=None):
        self.img, self.off, self.p0, self.p1 = img, off, p0, p1
        self.start, self.dur, self.arc, self.land = start, dur, arc, land

    def pos(self, time):
        k = ease((time - self.start) / self.dur)
        return (self.p0[0] + (self.p1[0] - self.p0[0]) * k,
                self.p0[1] + (self.p1[1] - self.p0[1]) * k - self.arc * math.sin(math.pi * k))

    def done(self, time):
        return time >= self.start + self.dur


class AssemblyScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.mouse = (0, 0)
        self.cursor = None
        self.confetti = fx.Confetti()
        self.start_task = 1
        self.mode = logic.HELP
        self.top_bar = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
        self.top_bar.fill((255, 255, 255, 232))
        B = ui.Button
        home = lambda s, c, z, col: ui.icon_home(s, c, z, col, door=(224, 84, 84))   # noqa: E731
        self.btn_menu = B((10, 13, 60, 48), "", home, (224, 84, 84), self.to_menu)
        self.btn_sound = B((1220, 13, 50, 48), "", lambda s, c, z, col: ui.icon_sound(s, c, z, col, self.app.sounds.enabled),
                           (150, 104, 206), self.app.sounds.toggle)
        self.mode_chip = pygame.Rect(1048, 19, 160, 36)
        self.btn_left = B((14, 640, 64, 62), "", lambda s, c, z, col: art.icon_rotate(s, c, z, col, -1),
                          (120, 132, 160), lambda: self.rotate(-45))
        self.btn_right = B((84, 640, 64, 62), "", lambda s, c, z, col: art.icon_rotate(s, c, z, col, 1),
                           (120, 132, 160), lambda: self.rotate(45))
        self.btn_flip = B((154, 640, 80, 62), "Ανάποδα", art.icon_flip, (120, 132, 160), self.toggle_flip,
                          label_size=13)
        self.btn_drive = B((970, 150, 270, 104), "Βόλτα!", art.icon_drive, art.GREEN, self.start_drive, label_size=22)
        self.btn_drive.pulse = True
        self.btn_again = B((970, 280, 270, 104), "Ξανά", ui.icon_again, (90, 140, 220), self.show_start, label_size=22)
        self.btn_quit = B((970, 410, 270, 104), "Μενού", home, (120, 130, 150), self.to_menu, label_size=22)
        self.pressed = None
        # το ρομπότ τελειωμένο, πίσω από την αρχική κάρτα
        self.build = logic.Build(logic.HELP, start_task=8)
        self._reset_model()
        self.state = "start"
        self.yaw, self.pitch, self.flip, self.zoom = -32.0, 30.0, 0.0, 1.0
        self.t_yaw, self.t_pitch, self.t_flip, self.t_zoom = self.yaw, self.pitch, self.flip, self.zoom
        self.flip_h = self._top_height()

    # ------------------------------------------------------------ ξεκίνημα
    def _reset_model(self):
        self.version = 0
        self.hidden = set()                   # κομμάτια που ακόμα πετάνε προς τη θέση τους
        self.screws = {sid: [1.0] * len(SLOTS[sid].screws) for sid in self.build.placed}
        self.selfk = {sid: 1.0 for sid in self.build.placed}
        self.anims = []                       # (θέση, βίδα ή None για «το ίδιο το κομμάτι»)
        self.anim = None                      # (θέση, βίδα, πότε ξεκίνησε)
        self.flights, self.pops, self.crosses = [], [], []
        self.drag = None
        self.plug_back = None                 # βύσμα που γυρίζει στη θέση του μετά από λάθος
        self.message = None                   # (γραμμή 1, γραμμή 2, χρώμα, ως πότε)
        self.led = rart.LED_BLUE
        self.led_until = None
        self.spin = (0.0, 0.0)
        self.drive_pose = None
        self.view_pending = None
        self.shown_step = self.build.step_i
        self.elapsed = 0.0
        self.switched_at = None
        self.tape = False
        self._model_key = self._world_key = self._img_key = self._bg_key = None
        self._ghost_key = self._drag_key = self._plug_key = None
        self._thumbs = {}

    def show_start(self):
        self.state = "start"
        self.confetti.clear()
        self.drive_pose = None
        self.app.sounds.play("swoosh", 0.5)

    def begin(self, mode):
        self.mode = mode
        self.build = logic.Build(mode, self.start_task)
        self._reset_model()
        self.state = "play"
        self.flip = 0.0
        self.flip_h = self._top_height()
        self.set_view(self.build.step, instant=False)
        self.app.sounds.play("select")

    def to_menu(self):
        from games.menu import MenuScene
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except pygame.error:
            pass
        self.app.switch(MenuScene(self.app))

    # ------------------------------------------------------------ κάμερα
    def set_view(self, step, instant=False):
        if step is None:
            return
        yaw, pitch, flip, zoom = step.view
        self.t_yaw, self.t_pitch, self.t_zoom = yaw, pitch, zoom
        self._set_flip(1.0 if flip else 0.0)
        if instant:
            self.yaw, self.pitch, self.zoom, self.flip = yaw, pitch, zoom, self.t_flip

    def _set_flip(self, target):
        if target != self.t_flip and self.flip < 0.01:
            self.flip_h = self._top_height()
        self.t_flip = target

    def rotate(self, d):
        self.t_yaw += d
        self.app.sounds.play("button", 0.6)

    def toggle_flip(self):
        self._set_flip(0.0 if self.t_flip > 0.5 else 1.0)
        self.app.sounds.play("swoosh", 0.5)

    def camera(self):
        return E.Camera(self.yaw, self.pitch, BASE_SCALE * self.zoom).looking_at(P.CENTER, ROBOT_AT)

    def cam_key(self):
        return (round(self.yaw, 2), round(self.pitch, 2), round(self.flip, 4), round(self.zoom, 4))

    def _update_camera(self, dt):
        k = 1 - math.exp(-dt * 6.5)
        d = (self.t_yaw - self.yaw + 180) % 360 - 180
        self.yaw = self.t_yaw - d * (1 - k) if abs(d) > 0.05 else self.t_yaw
        for name in ("pitch", "zoom"):
            cur, tgt = getattr(self, name), getattr(self, "t_" + name)
            setattr(self, name, tgt if abs(tgt - cur) < 0.002 else cur + (tgt - cur) * k)
        if self.flip != self.t_flip:
            step = dt / 0.9
            self.flip = min(self.t_flip, self.flip + step) if self.t_flip > self.flip else max(self.t_flip, self.flip - step)

    # ------------------------------------------------------------ ο κόσμος: ανάποδα και βόλτα
    def world(self, p):
        x, y, z = p
        if self.flip > 0:
            phi = math.pi * ease(self.flip)
            c, s = math.cos(phi), math.sin(phi)
            dz = z - ZC
            x, z = x * c - dz * s, ZC + x * s + dz * c + (self.flip_h - 2 * ZC) * (1 - c) / 2 + 45 * s
        if self.drive_pose:
            psi, d = self.drive_pose
            c, s = math.cos(psi), math.sin(psi)
            ry = y - P.CENTER[1]
            x, y = x * c - ry * s, P.CENTER[1] + d + x * s + ry * c
        return (x, y, z)

    def world_n(self, n):
        x, y, z = n
        if self.flip > 0:
            phi = math.pi * ease(self.flip)
            c, s = math.cos(phi), math.sin(phi)
            x, z = x * c - z * s, x * s + z * c
        if self.drive_pose:
            c, s = math.cos(self.drive_pose[0]), math.sin(self.drive_pose[0])
            x, y = x * c - y * s, x * s + y * c
        return (x, y, z)

    def _to_world(self, meshes):
        if self.flip <= 0 and not self.drive_pose:
            return meshes
        return [m.mapped(self.world, self.world_n) for m in meshes]

    def _top_height(self):
        top = 0.0
        for m in self._static_meshes(plugs=False):
            for f in m.faces:
                if f.n is not None:
                    top = max(top, max(p[2] for p in f.pts))
        return top

    # ------------------------------------------------------------ το μοντέλο
    def _static_meshes(self, plugs=True):
        out = [P.chassis()]
        for s in self._ordered_slots():
            sid = s.id
            if sid not in self.build.placed or sid in self.hidden:
                continue
            if sid == "board":
                out.append(P.board(self.led if self.build.switched else rart.LED_BLUE, self.build.switched))
            elif s.kind == "wheel" and self.spin != (0.0, 0.0):
                out.append(P.wheel(-1 if sid == "wheel_l" else 1, self.spin[0 if sid == "wheel_l" else 1]))
            else:
                out.append(s.mesh(self.selfk.get(sid, 1.0)))
            for spec, k in zip(s.screws, self.screws.get(sid, [])):
                if k is not None:
                    out.append(P.screw(spec, k))
        if self.tape:
            out.append(P.tape())
        if plugs:
            for pid, plug in PLUGS.items():
                # το καλώδιο φαίνεται μόλις μπει το κομμάτι του (π.χ. ο κινητήρας), ακόμα κι αν δεν
                # μπορεί να συνδεθεί ακόμα (χρειάζεται και τον ελεγκτή)
                own = plug.requires[0]
                if own not in self.build.placed or own in self.hidden:
                    continue
                if self.drag and self.drag.get("pid") == pid or self.plug_back and self.plug_back["pid"] == pid:
                    continue
                if pid in self.build.connected:
                    pt, d = P.SOCKETS[plug.target]
                else:
                    pt, d = P.PLUG_REST[pid]
                out.append(P.plug_mesh(pid, pt, d))
        return out

    @staticmethod
    def _ordered_slots():
        return SLOTS.values()

    def _robot(self):
        """Η εικόνα του ρομπότ (ξαναζωγραφίζεται μόνο όταν αλλάζει κάτι)."""
        key = (self.version, self.cam_key(), self.drive_pose)
        if key != self._img_key:
            if self._model_key != self.version:
                self._model = self._static_meshes()
                self._model_key = self.version
                self._world_key = None
            wkey = (self.version, round(self.flip, 4), self.drive_pose)
            if wkey != self._world_key:
                self._world = self._to_world(self._model)
                self._world_key = wkey
            self._robot_img, self._robot_rect = E.render(self._world, self.camera())
            self._img_key = key
        return self._robot_img, self._robot_rect

    def bump(self):
        self.version += 1

    # ------------------------------------------------------------ θέσεις στην οθόνη
    def screen(self, p3, cam=None):
        return (cam or self.camera()).proj(self.world(p3))

    def slot_visible(self, slot):
        if self.flip > 0.5:
            return slot.under or slot.kind in ANY_SIDE
        return not slot.under

    def _nearest_slot(self, pos, ids, radius):
        cam = self.camera()
        best, best_d = None, radius
        for sid in ids:
            slot = SLOTS[sid]
            if not self.slot_visible(slot):
                continue
            sx, sy = self.screen(slot.anchor, cam)
            d = math.hypot(sx - pos[0], sy - pos[1])
            if d < best_d:
                best, best_d = sid, d
        return best

    def _card_rects(self):
        """[(είδος, πόσα μένουν, ορθογώνιο)] για τις κάρτες του κουτιού."""
        items = self.build.tray()
        if not items:
            return []
        small = self.mode == logic.SOLO
        cols, (cw, ch), gap = (3, (102, 88), 6) if small else (2, (154, 148), 8)
        out = []
        for i, (kind, left) in enumerate(items):
            x = TRAY.x + 12 + (i % cols) * (cw + gap)
            y = TRAY.y + 52 + (i // cols) * (ch + gap)
            out.append((kind, left, pygame.Rect(x, y, cw, ch)))
        return out

    def _card_at(self, pos):
        for kind, left, r in self._card_rects():
            if r.collidepoint(pos):
                return kind, left, r
        return None

    def _thumb(self, kind, size):
        key = (kind, size)
        if key not in self._thumbs:
            # ο αισθητήρας υπερήχων από μπροστά, για να φαίνονται και τα δύο «μάτια» του
            yaw, pitch = THUMB_VIEW.get(kind, (-30, 28))
            self._thumbs[key] = E.thumbnail(_kind_meshes(kind), size, yaw, pitch)
        return self._thumbs[key]

    def _plug_point(self, pid):
        return P.PLUG_REST[pid][0]

    def _active_plug_at(self, pos):
        if self.flip > 0.01:
            return None
        cam = self.camera()
        for pid in PLUGS:
            if self.build.plug_active(pid) and not any(r in self.hidden for r in PLUGS[pid].requires):
                sx, sy = self.screen(self._plug_point(pid), cam)
                if math.hypot(sx - pos[0], sy - pos[1]) < PLUG_R:
                    return pid
        return None

    def _switch_hit(self, pos):
        step = self.build.step
        if not step or not step.switch or self.flip > 0.01:
            return False
        sx, sy = self.screen(P.SWITCH)
        return math.hypot(sx - pos[0], sy - pos[1]) < 34

    # ------------------------------------------------------------ σύρσιμο κομματιών
    def _hand(self, kind):
        """Το κομμάτι στο χέρι: εικόνα και πού είναι μέσα της το σημείο που ακολουθεί το ποντίκι."""
        key = (kind, self.cam_key(), self.drag.get("target") if self.drag else None, self.drag_slot(kind))
        if key == self._drag_key:
            return self._drag_img
        cam = self.camera()
        sid = self.drag_slot(kind)
        if sid:
            meshes = self._to_world(_hand_meshes(kind, sid))
            anchor = self.world(SLOTS[sid].anchor)
        else:
            meshes = _kind_meshes(kind)
            b = _mesh_center(meshes)
            anchor = b
        img, rect = E.render(meshes, cam)
        ax, ay = cam.proj(anchor)
        self._drag_img = (img, (ax - rect.x, ay - rect.y))
        self._drag_key = key
        return self._drag_img

    def drag_slot(self, kind):
        """Ποια θέση «δείχνει» το κομμάτι στο χέρι (για να έχει τον σωστό προσανατολισμό)."""
        if self.drag and self.drag.get("target"):
            return self.drag["target"]
        if PARTS[kind].extra or kind == "rj11":
            return None
        wanted = self.build.wanted(kind)
        if wanted:
            return wanted[0]
        free = [s.id for s in SLOTS.values() if s.kind == kind and s.id not in self.build.placed]
        return free[0] if free else None

    def grab(self, kind, card):
        self.drag = {"type": "part", "kind": kind, "card": card.center, "target": None, "pos": self.mouse}
        self.app.sounds.play("pick", 0.6)
        if self.mode == logic.SOLO and not PARTS[kind].extra:
            sid = self.drag_slot(kind)
            if sid:
                step = STEPS[STEP_INDEX[SLOTS[sid].step]]
                yaw, pitch, flip, zoom = step.view
                if (abs((yaw - self.t_yaw + 180) % 360 - 180) > 1 or flip != (self.t_flip > 0.5)
                        or abs(pitch - self.t_pitch) > 1):
                    self.set_view(step)

    def _drag_part_update(self):
        d = self.drag
        kind = d["kind"]
        target = None
        if not PARTS[kind].extra and self.mouse[0] < BENCH_W:
            target = self._nearest_slot(self.mouse, self.build.wanted(kind), SNAP_R[self.mode])
        if target != d["target"]:
            if target:
                self.app.sounds.play("pick", 0.25)
            d["target"] = target
            tape = target == "battery"
            if tape != self.tape:
                self.tape = tape
                self.bump()
        pos = self.mouse
        if target:
            tx, ty = self.screen(SLOTS[target].anchor)
            dist = math.hypot(tx - pos[0], ty - pos[1])
            pull = 1.0 if dist < 18 else 0.55
            pos = (pos[0] + (tx - pos[0]) * pull, pos[1] + (ty - pos[1]) * pull)
        d["pos"] = pos

    def release_part(self):
        d = self.drag
        kind, pos = d["kind"], d["pos"]
        img, off = self._hand(kind)
        self.drag = None
        self._drag_key = None
        if self.tape and d["target"] != "battery":
            self.tape = False
            self.bump()
        if self.mouse[0] >= BENCH_W:
            self._fly_back(img, off, pos, d["card"], quiet=True)
            return
        sid = d["target"]
        if sid is None:
            free = [s.id for s in SLOTS.values() if s.id not in self.build.placed]
            sid = self._nearest_slot(self.mouse, free, DROP_R)
            if sid is None and (PARTS[kind].extra or kind == "rj11"):
                rect = self._robot_rect if hasattr(self, "_robot_rect") else pygame.Rect(0, 0, 0, 0)
                if rect.collidepoint(self.mouse):
                    sid = next(iter(SLOTS))
        if sid is None:
            rect = getattr(self, "_robot_rect", pygame.Rect(0, 0, 0, 0))
            if rect.collidepoint(self.mouse):
                self.say("Δεν κολλάει εκεί.", "Φέρε το κομμάτι πιο κοντά στη θέση του.", art.ORANGE, 3.0)
            self._fly_back(img, off, pos, d["card"], quiet=True)
            return
        res = self.build.drop(kind, sid)
        if res.ok:
            self.hidden.add(sid)
            to = self.screen(SLOTS[sid].anchor)
            self.flights.append(Flight(img, off, pos, to, self.time, 0.14, 0, lambda s=sid: self._landed(s)))
            return
        if res.kind == "miss":
            self._fly_back(img, off, pos, d["card"], quiet=True)
            return
        self._mistake(res, self.mouse)
        self._fly_back(img, off, pos, d["card"], quiet=False)

    def _fly_back(self, img, off, pos, card, quiet):
        self.flights.append(Flight(img, off, pos, card, self.time, 0.38, 70))
        if quiet:
            self.app.sounds.play("remove", 0.4)

    def _landed(self, sid):
        self.hidden.discard(sid)
        slot = SLOTS[sid]
        self.screws[sid] = [None] * len(slot.screws)
        if slot.self_screw:
            self.selfk[sid] = 0.0
            self.anims.append((sid, None))
        self.anims += [(sid, i) for i in range(len(slot.screws))]
        self.tape = False
        self.bump()
        self.app.sounds.play("snap")
        self.pops.append((self.screen(slot.anchor), self.time, "κλακ!" if slot.kind == "wheel" else "κλικ!"))
        self.led = rart.LED_GREEN
        self.led_until = self.time + 0.8
        if sid == "battery":
            self.say("Η ταινία διπλής όψης μπήκε μόνη της!", "Η θήκη μπαταρίας κόλλησε στη βάση.", art.GREEN, 3.5)
        elif sid == "lego":
            self.say("Η βάση για τουβλάκια μένει εδώ.", "Πάνω της θα στήνουμε κατασκευές!", art.GREEN, 3.0)
        self._after_success()

    # ------------------------------------------------------------ βύσματα
    def grab_plug(self, pid):
        pt, _ = P.PLUG_REST[pid]
        self.drag = {"type": "plug", "pid": pid, "end": pt, "dir": (0, 0, 1), "socket": None}
        self.bump()
        self.app.sounds.play("pick", 0.6)

    def _drag_plug_update(self):
        d = self.drag
        cam = self.camera()
        kind = P.PLUG_KIND[d["pid"]]
        names = P.RJ_SOCKETS if kind == "rj" else ("MA", "MB", "DCIN")
        used = {PLUGS[p].target for p in self.build.connected}
        best, best_d = None, SOCKET_R
        for name in names:
            if name in used:
                continue
            sx, sy = cam.proj(P.SOCKETS[name][0])
            dist = math.hypot(sx - self.mouse[0], sy - self.mouse[1])
            if dist < best_d:
                best, best_d = name, dist
        if best != d["socket"] and best:
            self.app.sounds.play("pick", 0.25)
        d["socket"] = best
        if best:
            d["end"], d["dir"] = P.SOCKETS[best]
        else:
            d["end"], d["dir"] = cam.unproject(self.mouse[0], self.mouse[1], PLUG_Z), (0, 0, 1)

    def release_plug(self):
        d = self.drag
        pid = d["pid"]
        self.drag = None
        res = self.build.drop_plug(pid, d["socket"])
        if res.ok:
            self.bump()
            self.app.sounds.play("snap")
            self.pops.append((self.camera().proj(P.SOCKETS[d["socket"]][0]), self.time, "κλικ!"))
            self.led, self.led_until = rart.LED_GREEN, self.time + 0.8
            self._after_success()
            return
        if res.kind != "miss":
            self._mistake(res, self.mouse)
        else:
            self.app.sounds.play("remove", 0.4)
        self.plug_back = {"pid": pid, "from": d["end"], "start": self.time}
        self.bump()

    def _plug_overlay_mesh(self):
        if self.drag and self.drag["type"] == "plug":
            d = self.drag
            return P.plug_mesh(d["pid"], d["end"], d["dir"])
        if self.plug_back:
            b = self.plug_back
            k = ease((self.time - b["start"]) / 0.35)
            rest, rd = P.PLUG_REST[b["pid"]]
            end = tuple(b["from"][i] + (rest[i] - b["from"][i]) * k for i in range(3))
            return P.plug_mesh(b["pid"], end, rd)
        return None

    # ------------------------------------------------------------ διακόπτης
    def press_switch(self):
        if not self.build.press_switch().ok:
            return
        self.led = rart.LED_GREEN
        self.bump()
        self.app.sounds.play("charge")
        self.switched_at = self.time
        self.say("Το R2 άναψε!", "Μπράβο, το συναρμολόγησες!", art.GREEN, 4.0)

    def _finish(self):
        self.state = "done"
        self.app.progress.mark(GAME_ID, logic.MODES.index(self.mode) + 1)
        self.confetti.burst(WIDTH)
        self.app.sounds.play("win")

    # ------------------------------------------------------------ βόλτα
    def start_drive(self):
        self.state = "drive"
        self.drive_t = 0.0
        self.t_zoom = 0.78
        self.t_yaw, self.t_pitch = -36.0, 30.0
        self.app.sounds.play("motor")

    def _drive_update(self, dt):
        self.drive_t += dt
        t = self.drive_t
        a, b, c, e = DRIVE_T
        track, r = 61.0, 30.0
        if t < a:
            s = ease(t / a)
            d, psi = 60 * s, 0.0
            sl = sr = d / r
        elif t < a + b:
            s = ease((t - a) / b)
            d, psi = 60.0, 2 * math.pi * s
            sl, sr = 60 / r - psi * track / r, 60 / r + psi * track / r
        elif t < a + b + c:
            s = ease((t - a - b) / c)
            d, psi = 60 * (1 - s), 0.0
            sl = sr = (60 + 60 * s) / r
            sl, sr = sl - 2 * math.pi * track / r, sr + 2 * math.pi * track / r
        elif t < a + b + c + e:
            s = (t - a - b - c) / e
            d, psi = 0.0, 0.45 * math.sin(2 * math.pi * s) * (1 - s)
            base = 120 / r
            sl, sr = base - (2 * math.pi + psi) * track / r, base + (2 * math.pi + psi) * track / r
        else:
            self.drive_pose = None
            self.spin = (0.0, 0.0)
            self.led = rart.LED_GREEN
            self.state = "done"
            self.t_zoom = 1.0
            self.bump()
            return
        prev = self.drive_t - dt
        for start in (0.0, a, a + b, a + b + c):
            if prev < start <= t and start > 0:
                self.app.sounds.play("motor" if start != a + b + c else "beep")
        self.drive_pose = (psi, d)
        self.spin = (sl, sr)
        cols = (rart.LED_GREEN, rart.LED_BLUE, (250, 200, 60), (240, 90, 200))
        self.led = cols[int(t * 4) % len(cols)]
        self.bump()

    # ------------------------------------------------------------ μηνύματα και βήματα
    def say(self, line1, line2, color, dur=MSG_T):
        self.message = (line1, line2, color, self.time + dur)

    def _mistake(self, res, pos):
        msg = res.msg or ("Όχι εκεί!", "")
        self.say(msg[0], msg[1], art.RED)
        self.crosses.append((pos, self.time))
        self.app.sounds.play("deny")
        self.led, self.led_until = rart.LED_RED, self.time + 1.5

    def _after_success(self):
        b = self.build
        if b.step_i != self.shown_step:
            old = STEPS[self.shown_step] if self.shown_step < len(STEPS) else None
            self.shown_step = b.step_i
            if old and old.task <= 7 and b.task_done(old.task) and (b.step is None or b.step.task != old.task):
                self.say(f"Μπράβο! Τέλειωσε η Εργασία {old.task}.", "", art.GREEN, 2.6)
                self.app.sounds.play("complete", 0.7)
            if self.mode != logic.SOLO or (b.step and b.step.switch) or (b.step and old and old.view[2]
                                                                          and not b.step.view[2]):
                self.view_pending = b.step

    # ------------------------------------------------------------ γεγονότα
    def _buttons(self):
        if self.state == "start":
            return [self.btn_menu, self.btn_sound]
        out = [self.btn_menu, self.btn_sound]
        if self.state == "play":
            out += [self.btn_left, self.btn_right, self.btn_flip]
        if self.state == "done":
            out += [self.btn_drive, self.btn_again, self.btn_quit]
        return out

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            for b in self._buttons():
                b.hover = b.contains(e.pos)
            if self.drag:
                (self._drag_part_update if self.drag["type"] == "part" else self._drag_plug_update)()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self._press(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse = e.pos
            if self.pressed:
                b, self.pressed = self.pressed, None
                b.pressed = False
                if b.contains(e.pos) and b.enabled:
                    self.app.sounds.play("button")
                    b.action()
                return
            if self.drag:
                (self.release_part if self.drag["type"] == "part" else self.release_plug)()
        elif e.type == pygame.KEYDOWN and self.state == "play":
            if e.key == pygame.K_LEFT:
                self.rotate(-45)
            elif e.key == pygame.K_RIGHT:
                self.rotate(45)
            elif e.key in (pygame.K_UP, pygame.K_DOWN):
                self.toggle_flip()

    def _press(self, pos):
        for b in self._buttons():
            if b.contains(pos) and b.enabled:
                self.pressed = b
                b.pressed = True
                return
        if self.state == "start":
            for m, r in MODE_RECTS.items():
                if r.collidepoint(pos):
                    self.begin(m)
                    return
            for i, r in enumerate(TASK_CHIPS):
                if r.collidepoint(pos):
                    self.start_task = i + 1
                    self.app.sounds.play("button")
            return
        if self.mode_chip.collidepoint(pos) and self.state in ("play", "done"):
            self.show_start()
            return
        if self.state != "play" or self.drag:
            return
        if self._switch_hit(pos):
            self.press_switch()
            return
        pid = self._active_plug_at(pos)
        if pid:
            self.grab_plug(pid)
            self._drag_plug_update()
            return
        hit = self._card_at(pos)
        if hit and hit[1] > 0:
            self.grab(hit[0], hit[2])
            self._drag_part_update()

    # ------------------------------------------------------------ χρόνος
    def update(self, dt):
        self.time += dt
        self._update_camera(dt)
        if self.state == "play":
            if not self.build.finished:
                self.elapsed += dt
            self._update_anims()
            if self.view_pending is not None and not self.anims and self.anim is None and not self.flights:
                self.set_view(self.view_pending)
                self.view_pending = None
            if self.switched_at is not None and self.time - self.switched_at > 1.4:
                self.switched_at = None
                self._finish()
        elif self.state == "drive":
            self._drive_update(dt)
        for f in list(self.flights):
            if f.done(self.time):
                self.flights.remove(f)
                if f.land:
                    f.land()
        if self.plug_back and self.time - self.plug_back["start"] > 0.35:
            self.plug_back = None
            self.bump()
        if self.led_until and self.time > self.led_until and not self.build.switched:
            self.led, self.led_until = rart.LED_BLUE, None
        self.pops = [p for p in self.pops if self.time - p[1] < 0.8]
        self.crosses = [c for c in self.crosses if self.time - c[1] < 0.9]
        self.confetti.update(dt, self.time, HEIGHT)
        if self.drag:
            (self._drag_part_update if self.drag["type"] == "part" else self._drag_plug_update)()
        self._update_cursor()

    def _update_anims(self):
        if self.anim is None and self.anims:
            sid, i = self.anims.pop(0)
            self.anim = (sid, i, self.time)
            self.app.sounds.play("screw", 0.7)
        if self.anim is None:
            return
        sid, i, t0 = self.anim
        k = min(1.0, (self.time - t0) / SCREW_T)
        if i is None:
            self.selfk[sid] = k
        else:
            self.screws[sid][i] = k
        self.bump()
        if k >= 1.0:
            self.anim = None

    def _update_cursor(self):
        pos = self.mouse
        hand = any(b.enabled and b.contains(pos) for b in self._buttons()) or self.drag is not None
        if self.state == "start":
            hand = hand or any(r.collidepoint(pos) for r in list(MODE_RECTS.values()) + TASK_CHIPS)
        elif self.state == "play":
            hit = self._card_at(pos)
            hand = (hand or (hit is not None and hit[1] > 0) or self._active_plug_at(pos) is not None
                    or self._switch_hit(pos) or self.mode_chip.collidepoint(pos))
        cursor = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != self.cursor:
            self.cursor = cursor
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass

    # ------------------------------------------------------------ ζωγράφισμα
    def draw(self, screen):
        cam = self.camera()
        key = self.cam_key()
        if key != self._bg_key:
            self._bg = art.background(WIDTH, HEIGHT).copy()
            art.mat(self._bg, cam)
            lift = 0.0
            if self.flip > 0:
                lift = 45 * math.sin(math.pi * ease(self.flip))
            art.shadow(self._bg, cam, lift)
            self._bg_key = key
        screen.blit(self._bg, (0, 0))
        img, rect = self._robot()
        screen.blit(img, rect)
        if self.state == "play":
            self._draw_hints(screen, cam)
        overlay = self._plug_overlay_mesh()
        if overlay is not None:
            okey = (id(self.drag), self.drag and self.drag.get("end"), self.plug_back and self.time, self.cam_key())
            if okey != self._plug_key:
                self._plug_img = E.render([overlay], cam)
                self._plug_key = okey
            screen.blit(*self._plug_img)
        self._draw_ui(screen)
        if self.state in ("play", "done", "drive"):
            self._draw_moving(screen, cam)
        if self.state == "done":
            self._draw_done(screen)
        self.confetti.draw(screen)
        if self.state == "start":
            self._draw_start(screen)

    def _draw_hints(self, screen, cam):
        b = self.build
        step = b.step
        if step is None:
            return
        show_ghost = self.mode == logic.HELP or (self.mode == logic.GUIDE and b.misses_here >= 2)
        if show_ghost and not self.flights and self.anim is None:
            if self.drag and self.drag["type"] == "part":
                ids = [] if PARTS[self.drag["kind"]].extra else b.wanted(self.drag["kind"])
            elif self.drag:
                ids = []
            else:
                ids = [sid for sid in step.slots if b.ready(sid)]
            ids = [sid for sid in ids if self.slot_visible(SLOTS[sid])]
            gkey = (tuple(ids), self.version, self.cam_key())
            if gkey != self._ghost_key:
                meshes = [SLOTS[sid].mesh(1.0).tinted(GHOST, GHOST_ALPHA) for sid in ids
                          if SLOTS[sid].kind != "rj11"]
                meshes = self._to_world([m for m in meshes if m.faces])
                self._ghost = E.render(meshes, cam) if meshes else None
                self._ghost_key = gkey
            if self._ghost:
                screen.blit(*self._ghost)
            for sid in ids:
                if SLOTS[sid].kind == "rj11":                # τα καλώδια RJ11: δαχτυλίδι στην υποδοχή
                    art.target_ring(screen, self.screen(SLOTS[sid].anchor, cam), 16, self.time)
        if self.flip < 0.01:
            for pid in PLUGS:
                if b.plug_active(pid) and not (self.drag and self.drag.get("pid") == pid) \
                        and not (self.plug_back and self.plug_back["pid"] == pid) \
                        and not any(r in self.hidden for r in PLUGS[pid].requires):
                    art.plug_halo(screen, self.screen(self._plug_point(pid), cam), self.time)
            if self.drag and self.drag["type"] == "plug" and self.mode == logic.HELP:
                target = PLUGS[self.drag["pid"]].target
                art.target_ring(screen, cam.proj(P.SOCKETS[target][0]), 18, self.time, art.GREEN)
            if step.switch and self.switched_at is None:
                art.plug_halo(screen, self.screen(P.SWITCH, cam), self.time, art.GREEN)

    def _hidden_screw(self, cam):
        """Αν η βίδα που μπαίνει τώρα δεν φαίνεται (π.χ. κάτω από τη βάση), πού να δείξει το βελάκι."""
        if self.anim is None or self.anim[1] is None:
            return None
        sid, i, _ = self.anim
        kind, axis, a, b, seat, out = SLOTS[sid].screws[i]
        if cam.facing(self.world_n(E.at(axis, out, 0, 0))) > 0.05:
            return None
        return self.screen(E.at(axis, seat, a, b), cam)

    def _draw_moving(self, screen, cam):
        for f in self.flights:
            x, y = f.pos(self.time)
            screen.blit(f.img, (round(x - f.off[0]), round(y - f.off[1])))
        d = self.drag
        if d and d["type"] == "part":
            img, off = self._hand(d["kind"])
            if d["target"]:
                art.magnet_arcs(screen, self.mouse, self.screen(SLOTS[d["target"]].anchor, cam), self.time)
            screen.blit(img, (round(d["pos"][0] - off[0]), round(d["pos"][1] - off[1])))
        if d and d["type"] == "plug" and d["socket"]:
            p = cam.proj(P.SOCKETS[d["socket"]][0])
            art.magnet_arcs(screen, self.mouse, p, self.time)
            art.label_tip(screen, p, P.SOCKET_LABEL[d["socket"]], art.BLUE)
        hidden = self._hidden_screw(cam)
        if hidden:
            art.spin_mark(screen, hidden, self.time)
        for pos, t0, word in self.pops:
            art.pop(screen, pos, self.time - t0, word)
        for pos, t0 in self.crosses:
            art.cross(screen, pos, self.time - t0)

    def _draw_ui(self, screen):
        screen.blit(self.top_bar, (0, 0))
        pygame.draw.line(screen, (214, 222, 236), (0, TOP_H), (WIDTH, TOP_H), 2)
        ui.text(screen, "Συναρμολόγηση", (82, TOP_H // 2), 28, art.INK, anchor="midleft")
        b = self.build
        if self.state != "start":
            done = {t for t in range(1, 8) if b.task_done(t)}
            words = None
            if self.mode != logic.SOLO:
                now = b.step.id if b.step else None
                words = [[(w, now in ids) for w, ids in TASK_WORDS[t]] for t in range(1, 8)]
            art.progress(screen, 372, b.task, done, words)
            title, _, _, col = MODE_INFO[self.mode]
            pygame.draw.rect(screen, ui.mix(col, (255, 255, 255), 0.88), self.mode_chip, border_radius=18)
            pygame.draw.rect(screen, col, self.mode_chip, 2, border_radius=18)
            ui.text(screen, title, self.mode_chip.center, 18, ui.shade(col, 0.75))
        for btn in self._buttons():
            btn.draw(screen, self.time)
        if self.state not in ("play",):
            return
        step = b.step
        if step:
            if step.switch:
                small = "Τέλος"
            elif self.mode == logic.SOLO:
                small = f"Μόνος μου · Εργασία {step.task}"
            else:
                small = f"Εργασία {step.task} · Βήμα {step.id}"
            if step.switch or self.mode == logic.HELP:
                big = step.title
            elif self.mode == logic.GUIDE:
                big = step.guide
            else:
                big = step.title if b.needs_hint else "Ποιο κομμάτι μπαίνει τώρα;"
            art.instruction(screen, INSTR, small, big)
        # το κουτί υλικών
        cards = self._card_rects()
        if cards:
            last = cards[-1][2]
            box = pygame.Rect(TRAY.x, TRAY.y, TRAY.w, min(TRAY.h, last.bottom - TRAY.y + 12))
            art.parts_box(screen, box, "Κουτί υλικών")
            small = self.mode == logic.SOLO
            size = (92, 46) if small else (140, 88)
            for kind, left, r in cards:
                if self.drag and self.drag.get("kind") == kind:
                    state = "hand"
                elif left <= 0:
                    state = "done"
                else:
                    state = "ready"
                total = PARTS[kind].count if self.mode == logic.SOLO else left + sum(
                    1 for sid in (step.slots if step else ()) if SLOTS[sid].kind == kind and sid in b.placed)
                art.card(screen, r, self._thumb(kind, size), PARTS[kind].name, left, total, state,
                         hover=r.collidepoint(self.mouse) and not self.drag, small=small)
        elif step and step.plugs:
            box = pygame.Rect(TRAY.x, TRAY.y, TRAY.w, 64 + 62 * len(step.plugs))
            self._draw_plug_list(screen, box, step)
        if step and step.plugs and cards:
            last = cards[-1][2]
            box = pygame.Rect(TRAY.x, last.bottom + 24, TRAY.w, 64 + 62 * len(step.plugs))
            if box.bottom <= TRAY.bottom:
                self._draw_plug_list(screen, box, step)
        # το R2 και τι λέει
        if self.message and self.time < self.message[3]:
            l1, l2, col = self.message[:3]
        else:
            l1, l2 = b.hint()
            col = art.BLUE
        art.bubble(screen, BUBBLE, l1, l2, col)
        self._draw_r2(screen)

    def _draw_plug_list(self, screen, box, step):
        ui.panel(screen, box, (255, 255, 255), radius=16, border=(214, 222, 236))
        ui.text(screen, "Συνδέσεις", (box.centerx, box.y + 24), 22, art.INK)
        for i, pid in enumerate(step.plugs):
            plug = PLUGS[pid]
            r = pygame.Rect(box.x + 10, box.y + 48 + i * 62, box.w - 20, 56)
            done = pid in self.build.connected
            pygame.draw.rect(screen, (232, 246, 236) if done else (244, 246, 250), r, border_radius=12)
            c = (r.x + 24, r.centery)
            if done:
                ui.circle(screen, art.GREEN, c, 13)
                pygame.draw.lines(screen, (255, 255, 255), False, [(c[0] - 6, c[1]), (c[0] - 1, c[1] + 5),
                                                                    (c[0] + 7, c[1] - 5)], 3)
            else:
                ui.circle(screen, (220, 224, 232), c, 13)
            ui.text(screen, plug.name, (r.x + 48, r.y + 18), 17, art.INK, anchor="midleft")
            if self.mode == logic.SOLO and not done:
                where = "→ ;"
            else:
                where = "→ " + P.SOCKET_LABEL[plug.target]
            ui.text(screen, where, (r.x + 48, r.y + 39), 17, (90, 100, 120), anchor="midleft", bold=False)

    def _draw_r2(self, screen):
        canvas = rart.body(R2_SIZE, self.led).copy()
        wheel = rart.wheel(R2_SIZE)
        canvas.blit(wheel, wheel.get_rect(center=(R2_SIZE * rart.WHEEL_AT[0], R2_SIZE * rart.WHEEL_AT[1])))
        canvas = pygame.transform.flip(canvas, True, False)
        screen.blit(canvas, canvas.get_rect(center=R2_AT))

    def _draw_done(self, screen):
        ui.panel(screen, BANNER, (255, 252, 240), radius=28, border=(250, 190, 50))
        ui.text(screen, "Μπράβο!", (BANNER.centerx, BANNER.y + 56), 56, (236, 118, 30), shadow=(250, 214, 150))
        ui.text(screen, "Το R2 είναι έτοιμο!", (BANNER.centerx, BANNER.y + 112), 26, art.INK)
        chip = pygame.Rect(BANNER.x, BANNER.bottom + 12, BANNER.w, 44)
        ui.panel(screen, chip, (255, 255, 255), radius=16, border=(214, 222, 236))
        m, s = divmod(int(self.elapsed), 60)
        mistakes = self.build.mistakes
        word = "λάθος" if mistakes == 1 else "λάθη"
        parts, plugs = len(self.build.placed), len(self.build.connected)
        ui.text(screen, f"{parts} κομμάτια · {plugs} συνδέσεις · {mistakes} {word} · {m}:{s:02d}", chip.center, 20,
                art.INK)

    def _draw_start(self, screen):
        veil = pygame.Surface((WIDTH, HEIGHT - TOP_H), pygame.SRCALPHA)
        veil.fill((230, 238, 248, 160))
        screen.blit(veil, (0, TOP_H))
        card = START_CARD
        ui.panel(screen, card, (255, 255, 255), radius=26, border=(214, 222, 236))
        ui.text(screen, "Φτιάξε το R2!", (card.centerx, card.y + 44), 40, art.INK)
        ui.text(screen, "Πώς θέλεις να το συναρμολογήσεις;", (card.centerx, card.y + 86), 22, (100, 110, 130),
                bold=False)
        for m, r in MODE_RECTS.items():
            title, l1, l2, col = MODE_INFO[m]
            hover = r.collidepoint(self.mouse)
            face = r.move(0, -4) if hover else r
            ui.panel(screen, face, ui.mix(col, (255, 255, 255), 0.8 if hover else 0.86), radius=20, border=col)
            ic = (face.centerx, face.y + 78)
            ui.circle(screen, (255, 255, 255), ic, 54)
            screen.blit(_mode_icon(m), _mode_icon(m).get_rect(center=ic))
            if m == logic.HELP:
                pygame.draw.circle(screen, art.MAGNET, ic, 54, 3)
            ui.text(screen, title, (face.centerx, face.y + 160), 28, ui.shade(col, 0.8))
            ui.text(screen, l1, (face.centerx, face.y + 196), 18, art.INK, bold=False)
            ui.text(screen, l2, (face.centerx, face.y + 220), 18, art.INK, bold=False)
        ui.text(screen, "Ξεκίνα από:", (card.x + 50, TASK_CHIPS[0].centery), 22, art.INK, anchor="midleft")
        for i, r in enumerate(TASK_CHIPS):
            on = self.start_task == i + 1
            pygame.draw.rect(screen, art.ORANGE if on else (236, 240, 246), r, border_radius=14)
            ui.text(screen, f"Εργ. {i + 1}", (r.centerx, r.y + 14), 17, (255, 255, 255) if on else art.INK)
            for k, (w, _) in enumerate(TASK_WORDS[i + 1]):
                art.fit_text(screen, w, (r.centerx, r.y + 33 + k * 14), 12,
                             (255, 255, 255) if on else (110, 118, 134), r.w - 6, bold=False)


# ---------------------------------------------------------------- σχήματα για τις κάρτες και το χέρι
_EXTRA_MESH = {"bluetooth": P.bluetooth, "led": P.white_led, "usb": P.usb_cable, "screwdriver": P.screwdriver,
               "allen": P.allen_key, "rj11": P.rj_coil}


def _kind_meshes(kind):
    """Το κομμάτι όπως είναι στο κουτί (για την κάρτα)."""
    if kind in _EXTRA_MESH:
        return [_EXTRA_MESH[kind]()]
    sid = next(s.id for s in SLOTS.values() if s.kind == kind)
    return _hand_meshes(kind, sid)


def _hand_meshes(kind, sid):
    """Το κομμάτι στη θέση sid, μαζί με το καλώδιό του αν έχει (ο κινητήρας, η μπαταρία)."""
    slot = SLOTS[sid]
    out = [slot.mesh(1.0)]
    if kind == "motor_left":
        out.append(P.plug_mesh("motor_l", *P.PLUG_REST["motor_l"]))
    elif kind == "motor_right":
        out.append(P.plug_mesh("motor_r", *P.PLUG_REST["motor_r"]))
    elif kind == "battery":
        out.append(P.plug_mesh("power", *P.PLUG_REST["power"]))
    elif kind == "rj11":
        out = [P.rj_coil().mapped(lambda p, a=slot.anchor: (p[0] + a[0], p[1] + a[1], p[2] + a[2] + 14), lambda n: n)]
    return out


def _mesh_center(meshes):
    pts = [p for m in meshes for p in m.points()]
    return tuple((min(p[i] for p in pts) + max(p[i] for p in pts)) / 2 for i in range(3))


_mode_icons = {}


def _mode_icon(mode):
    if mode not in _mode_icons:
        if mode == logic.HELP:
            img = E.thumbnail([P.motor(-1).tinted((120, 210, 255), 140)], (96, 76))
        elif mode == logic.GUIDE:
            img = pygame.Surface((96, 76), pygame.SRCALPHA)
            bx, by = 22, 6
            pygame.draw.rect(img, (62, 140, 226), (bx, by, 52, 64), border_radius=8)
            pygame.draw.rect(img, (255, 255, 255), (bx + 8, by + 8, 36, 48), border_radius=4)
            for k in range(5):
                pygame.draw.line(img, (160, 180, 210), (bx + 13, by + 17 + k * 8), (bx + 39, by + 17 + k * 8), 3)
        else:
            img = E.thumbnail([P.motor(1), P.wheel(1), P.ultrasonic().mapped(lambda p: (p[0], p[1] - 70, p[2]),
                                                                              lambda n: n)], (96, 76))
        _mode_icons[mode] = img
    return _mode_icons[mode]
