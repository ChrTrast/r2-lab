"""Το τρέξιμο του R2 χωρίς γραφικά: η πίστα, η κίνηση, τα άλματα, οι πύλες, τα χτυπήματα.

Η πίστα γράφεται με χαρακτήρες σε 8 γραμμές (η πάνω είναι το ταβάνι, η κάτω πατά στο πάτωμα).
Κάθε χαρακτήρας είναι ένα κουτάκι (TILE):

    .  κενό                         #  κουτί
    ^  αγκάθι (πατά κάτω)           v  αγκάθι που κρέμεται από πάνω
    _  τραμπολίνο                   o  δαχτυλίδι άλματος
    G  πύλη: ανάποδα, στο ταβάνι    g  πύλη: πίσω στο πάτωμα
    R  πύλη: πύραυλος               W  πύλη: πίσω στις ρόδες
    >  πύλη ταχύτητας
    A, B  οι δύο επιλογές (A η πάνω, B η κάτω), στην ίδια στήλη

Το R2 ξεκινά στη στήλη START_COL. Το τέρμα (ο φορτιστής) είναι FINISH_BACK στήλες πριν από το τέλος.
Η κίνηση γίνεται με σταθερό βήμα STEP, ώστε να είναι ίδια σε κάθε υπολογιστή (και στον έλεγχο).
"""
import copy

TILE = 64
ROWS = 8
GROUND = 610                     # το πάτωμα (y της οθόνης 1280x720)
TOP = GROUND - ROWS * TILE       # 98: το πάνω όριο του κόσμου
STEP = 1 / 120
HIT = 52                         # το τετράγωνο που «χτυπάει» το R2 (λίγο μικρότερο από ένα κουτί)
GRAVITY = 2900.0
JUMP_V = 950.0                   # άλμα: περίπου 2.4 κουτάκια ψηλά
PAD_V = 1230.0                   # τραμπολίνο: περίπου 4 κουτάκια ψηλά
MAX_FALL = 1400.0
ROCKET_UP, ROCKET_DOWN, ROCKET_MAX = 2300.0, 2000.0, 520.0
SNAP = 18                        # αν πέσει λίγο χαμηλά στην άκρη ενός κουτιού, ανεβαίνει πάνω του
JUMP_BUFFER = 0.12               # πάτημα λίγο πριν προσγειωθεί μετράει
COYOTE = 0.07                    # ...και λίγο αφού φύγει από την άκρη ενός κουτιού
RING_R = 46                      # πόσο κοντά στο δαχτυλίδι πρέπει να είναι το R2
SPIKE_W, SPIKE_H = 20, 34        # το «επικίνδυνο» κομμάτι του αγκαθιού (μικρό, για να συγχωρεί)
START_COL = 2
FINISH_BACK = 4

PORTALS = {"G": "gravity_up", "g": "gravity_down", "R": "rocket", "W": "run", ">": "speed"}


def overlap(a, b):
    return a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]


def rows_from(text):
    """Οι 8 γραμμές μιας πίστας από κείμενο (αγνοεί κενές γραμμές και εσοχές)."""
    rows = [line.strip() for line in text.strip("\n").splitlines() if line.strip()]
    if len(rows) != ROWS or len({len(r) for r in rows}) != 1:
        raise ValueError(f"η πίστα θέλει {ROWS} ίσες γραμμές")
    return rows


class Track:
    """Μια πίστα: πού είναι τα κουτιά, τα αγκάθια, οι πύλες και οι επιλογές."""

    def __init__(self, rows, speed, fast=None):
        if isinstance(rows, str):
            rows = rows_from(rows)
        self.rows = rows
        self.cols = len(rows[0])
        self.speed = speed * TILE
        self.fast = (fast if fast is not None else speed + 1.5) * TILE
        self.start_x = START_COL * TILE
        self.finish_x = (self.cols - FINISH_BACK) * TILE
        self.blocks = self._blocks(rows)
        self.spikes, self.pads, self.rings, self.portals = [], [], [], []
        pairs = {}
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                x, y = c * TILE, TOP + r * TILE
                mid = x + (TILE - SPIKE_W) / 2
                if ch == "^":
                    self.spikes.append({"x": x, "y": y + TILE, "down": False,
                                        "box": (mid, y + TILE - SPIKE_H, SPIKE_W, SPIKE_H)})
                elif ch == "v":
                    self.spikes.append({"x": x, "y": y, "down": True, "box": (mid, y, SPIKE_W, SPIKE_H)})
                elif ch == "_":
                    self.pads.append({"x": x, "y": y + TILE, "box": (x + 4, y + TILE - 18, TILE - 8, 18)})
                elif ch == "o":
                    self.rings.append((x + TILE / 2, y + TILE / 2))
                elif ch in PORTALS:
                    self.portals.append({"x": x + TILE / 2, "y": y + TILE / 2, "kind": PORTALS[ch]})
                elif ch in "AB":
                    pairs.setdefault(c, {})[ch] = y + TILE / 2
                elif ch not in ".#":
                    raise ValueError(f"άγνωστος χαρακτήρας {ch!r} στη στήλη {c}")
        self.portals.sort(key=lambda p: p["x"])
        self.choices = []
        for c in sorted(pairs):
            p = pairs[c]
            if set(p) != {"A", "B"}:
                raise ValueError(f"η στήλη {c} θέλει και A και B")
            self.choices.append({"x": c * TILE + TILE / 2, "ya": p["A"], "yb": p["B"], "split": (p["A"] + p["B"]) / 2})
        # για γρήγορο ψάξιμο: ποια πράγματα υπάρχουν σε κάθε στήλη
        self.near = {"block": {}, "spike": {}, "pad": {}, "ring": {}}
        for i, b in enumerate(self.blocks):
            self._index("block", i, b[0], b[0] + b[2])
        for i, s in enumerate(self.spikes):
            self._index("spike", i, s["x"], s["x"] + TILE)
        for i, p in enumerate(self.pads):
            self._index("pad", i, p["x"], p["x"] + TILE)
        for i, (x, y) in enumerate(self.rings):
            self._index("ring", i, x - TILE, x + TILE)

    @staticmethod
    def _blocks(rows):
        """Τα κουτιά ενωμένα σε ορθογώνια (σειρές που ταιριάζουν ακριβώς μπαίνουν η μία κάτω από την άλλη)."""
        runs = []
        for r, line in enumerate(rows):
            c = 0
            while c < len(line):
                if line[c] == "#":
                    c0 = c
                    while c < len(line) and line[c] == "#":
                        c += 1
                    runs.append([c0, r, c - c0, 1])
                else:
                    c += 1
        merged = []
        for run in runs:
            for m in merged:
                if m[0] == run[0] and m[2] == run[2] and m[1] + m[3] == run[1]:
                    m[3] += 1
                    break
            else:
                merged.append(run)
        return [(c * TILE, TOP + r * TILE, w * TILE, h * TILE) for c, r, w, h in merged]

    def _index(self, kind, i, x0, x1):
        for col in range(int(x0 // TILE), int((x1 - 1) // TILE) + 1):
            self.near[kind].setdefault(col, []).append(i)

    def around(self, kind, x0, x1):
        found = []
        for col in range(int(x0 // TILE) - 1, int(x1 // TILE) + 2):
            for i in self.near[kind].get(col, ()):
                if i not in found:
                    found.append(i)
        return found


class Runner:
    """Το R2 πάνω στην πίστα. Κάθε step() προχωρά STEP δευτερόλεπτα και επιστρέφει τι έγινε."""

    def __init__(self, track):
        self.track = track
        self.x = track.start_x
        self.y = GROUND - HIT
        self.vy = 0.0
        self.g = 1                   # 1: πέφτει προς τα κάτω, -1: «πέφτει» προς το ταβάνι
        self.mode = "run"            # run: ρόδες και άλματα, rocket: πύραυλος
        self.speed = track.speed
        self.grounded = True
        self.air = 0.0               # πόση ώρα δεν πατά κάπου
        self.time = 0.0
        self.press_at = -9.0
        self.held = False
        self.used = set()            # τραμπολίνα και δαχτυλίδια που χρησιμοποιήθηκαν
        self.next_portal = 0
        self.next_choice = 0
        self.distance = 0.0
        self.dead = False
        self.done = False

    def clone(self):
        c = copy.copy(self)
        c.used = set(self.used)
        return c

    def box(self):
        return (self.x, self.y, HIT, HIT)

    def center(self):
        return (self.x + HIT / 2, self.y + HIT / 2)

    def progress(self):
        t = self.track
        return max(0.0, min(1.0, (self.x - t.start_x) / (t.finish_x - t.start_x)))

    # ------------------------------------------------------------ ένα βήμα
    def step(self, held, pressed=False):
        events = []
        if self.dead or self.done:
            return events
        t = self.track
        self.time += STEP
        if pressed:
            self.press_at = self.time
        self.held = held
        buffered = self.time - self.press_at <= JUMP_BUFFER

        # 1. μπροστά: αν χτυπήσει σε πλευρά κουτιού, χάνει (εκτός αν είναι λίγο πιο χαμηλά: ανεβαίνει)
        dx = self.speed * STEP
        self.x += dx
        self.distance += dx
        blocks = [t.blocks[i] for i in t.around("block", self.x, self.x + HIT)]
        for b in blocks:
            if overlap(self.box(), b):
                depth = (self.y + HIT - b[1]) if self.g == 1 else (b[1] + b[3] - self.y)
                if 0 < depth <= SNAP:
                    self.y = b[1] - HIT if self.g == 1 else b[1] + b[3]
                    self.vy = 0.0
                else:
                    return self._crash(events)
        if any(overlap(self.box(), b) for b in blocks):
            return self._crash(events)

        # 2. πάνω-κάτω
        if self.mode == "run":
            self.vy = max(-MAX_FALL, min(MAX_FALL, self.vy + GRAVITY * self.g * STEP))
        else:
            acc = -ROCKET_UP if held else ROCKET_DOWN
            self.vy = max(-ROCKET_MAX, min(ROCKET_MAX, self.vy + acc * STEP))
        self.y += self.vy * STEP
        down = 1 if self.mode == "rocket" else self.g      # προς τα πού «πέφτει»
        self.grounded = False
        for b in blocks:
            if overlap(self.box(), b):
                if self.vy * down > 0:                       # πέφτει πάνω του: πατά
                    self.y = b[1] - HIT if down == 1 else b[1] + b[3]
                    self.grounded = True
                else:                                        # χτυπά από κάτω: απλώς σταματά
                    self.y = b[1] + b[3] if down == 1 else b[1] - HIT
                self.vy = 0.0
        if self.y + HIT > GROUND:
            self.y = GROUND - HIT
            self.vy = min(self.vy, 0.0) if down == 1 else 0.0
            self.grounded = self.grounded or down == 1
        if self.y < TOP:
            self.y = TOP
            self.vy = max(self.vy, 0.0) if down == -1 else 0.0
            self.grounded = self.grounded or down == -1
        self.air = 0.0 if self.grounded else self.air + STEP

        # 3. άλμα (κρατώντας πατημένο πηδάει ξανά μόλις πατήσει κάτω)
        if self.mode == "run" and self.air <= COYOTE and (held or buffered):
            self._jump(JUMP_V)
            events.append(("jump",))

        # 4. τραμπολίνα, δαχτυλίδια, αγκάθια
        box = self.box()
        for i in t.around("pad", self.x, self.x + HIT):
            if ("pad", i) not in self.used and overlap(box, t.pads[i]["box"]):
                self.used.add(("pad", i))
                self._jump(PAD_V)
                events.append(("pad", i))
        if self.mode == "run" and (held or self.time - self.press_at <= JUMP_BUFFER):
            cx, cy = self.center()
            for i in t.around("ring", self.x, self.x + HIT):
                rx, ry = t.rings[i]
                if ("ring", i) not in self.used and (cx - rx) ** 2 + (cy - ry) ** 2 <= RING_R ** 2:
                    self.used.add(("ring", i))
                    self._jump(JUMP_V)
                    events.append(("ring", i))
                    break
        for i in t.around("spike", self.x, self.x + HIT):
            if overlap(box, t.spikes[i]["box"]):
                return self._crash(events)

        # 5. πύλες, επιλογές, τέρμα (μετρούν όταν περάσει το κέντρο του R2)
        cx, cy = self.center()
        while self.next_portal < len(t.portals) and cx >= t.portals[self.next_portal]["x"]:
            kind = t.portals[self.next_portal]["kind"]
            self.next_portal += 1
            self._portal(kind)
            events.append(("portal", kind))
        while self.next_choice < len(t.choices) and cx >= t.choices[self.next_choice]["x"]:
            ch = t.choices[self.next_choice]
            events.append(("pick", self.next_choice, "A" if cy < ch["split"] else "B"))
            self.next_choice += 1
        if cx >= t.finish_x:
            self.done = True
            events.append(("finish",))
        return events

    def _jump(self, v):
        self.vy = -v * self.g
        self.grounded = False
        self.air = 1.0
        self.press_at = -9.0

    def _portal(self, kind):
        if kind == "gravity_up":
            self.g = -1
            self.vy *= 0.4
        elif kind == "gravity_down":
            self.g = 1
            self.vy *= 0.4
        elif kind == "rocket":
            self.mode = "rocket"
            self.g = 1
            self.vy *= 0.3
        elif kind == "run":
            self.mode = "run"
        elif kind == "speed":
            self.speed = self.track.fast

    def _crash(self, events):
        self.dead = True
        events.append(("crash",))
        return events


# ------------------------------------------------------------------ έλεγχος
def solve(track, picks=None, every=8, offset=0, limit=3000, report=None):
    """Υπάρχει τρόπος να φτάσει το R2 στο τέρμα; Δοκιμάζει «πατημένο» ή «αφημένο» κάθε `every`
    βήματα (8 βήματα = 1/15 του δευτερολέπτου). Με picks (λίστα 'A'/'B') πρέπει να πάρει
    σε κάθε επιλογή αυτό που λέει η λίστα. Επιστρέφει τη σειρά των πατημάτων ή None.
    Στο report (dict) γράφει ως ποια στήλη έφτασε, για να βρεθεί πού κολλάει μια πίστα."""
    def key(r):
        if r.mode == "rocket":
            return (round(r.y / 8), round(r.vy / 80), r.mode, r.held, r.next_choice)
        return (round(r.y / 2), round(r.vy / 16), r.grounded, r.mode, r.g, r.held, r.next_choice,
                frozenset(r.used))

    frontier = [(Runner(track), [])]
    first = offset or every
    while frontier:
        if report is not None:
            report["col"] = int(frontier[0][0].x // TILE)
        nxt = {}
        for runner, plan in frontier:
            for hold in (False, True):
                r = runner.clone()
                ok = True
                n = first if not plan else every
                for k in range(n):
                    events = r.step(hold, pressed=hold and k == 0 and not runner.held)
                    for ev in events:
                        if ev[0] == "crash":
                            ok = False
                        elif ev[0] == "pick" and picks is not None and picks[ev[1]] != ev[2]:
                            ok = False
                        elif ev[0] == "finish":
                            return plan + [hold]
                    if not ok:
                        break
                if ok:
                    nxt.setdefault(key(r), (r, plan + [hold]))
        frontier = list(nxt.values())[:limit]
    return None
