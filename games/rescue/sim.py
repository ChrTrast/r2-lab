"""Οι κανόνες του δάσους την ώρα που παίζουν (ζωντανή οδήγηση, κεφάλαιο «Χειριστήριο»).

Forest κρατά ό,τι αλλάζει: τα R2, τις πέτρες, το νερό στα αυλάκια, τις φωτιές, τα κλαδιά και τα ζώα.
- Στον υπολογιστή του δασκάλου (και στην Εξάσκηση) τρέχει ο χρόνος: tick(dt), act(k, κίνηση).
- Στους μαθητές το ίδιο αντικείμενο απλώς δέχεται τις «φωτογραφίες» του δασκάλου (apply) για να
  ζωγραφιστούν, χωρίς να τρέχει κανόνες.

Κανόνες: το R2 κάνει μία κίνηση τη φορά (STEP δευτερόλεπτα), ως QUEUE_MAX πατήματα περιμένουν.
Πέτρα στο ποτάμι = πέρασμα, πέτρα στο αυλάκι = φράγμα (δεν ξανακουνιούνται). Το νερό προχωρά ένα κουτάκι
κάθε FLOW δευτερόλεπτα και, σε μια διακλάδωση, πάει στο πρώτο ανοιχτό αυλάκι. Μόλις φτάσει στη φωτιά,
η φωτιά σβήνει. Το κλαδί σηκώνεται όσο ένα R2 πατά το πεντάλ του (ή όσο ένα R2 είναι από κάτω του).
Τα ζώα πάνε μόνα τους στο λιβάδι όταν ανοίξει ο δρόμος (ένα κουτάκι κάθε ANIMAL_STEP).
"""
from collections import deque

from games.program import logic as PL
from . import world as W

STEP = 0.34
TURN = 0.28
BUMP_TIME = 0.5
FLOW = 0.12
ANIMAL_STEP = 0.42
QUEUE_MAX = 3
RUN_STEP = 0.45            # στην εκτέλεση προγραμμάτων: μία κίνηση κάθε τόσο, όλα τα R2 μαζί
SETTLE_QUIET = 2.5         # μετά τα προγράμματα: τόση ώρα χωρίς αλλαγές = τέλος
SETTLE_MAX = 30.0
HOLD_MAX = 30              # βήματα που σπρώχνει μόνο του ένα R2 τον μεγάλο βράχο πριν τα παρατήσει
TEST_LIFT = 4              # στη «Δοκιμή»: σε τόσα βήματα η μπάρα ανοίγει μόνη της (σαν να ήρθε ο γείτονας)
EVENTS_KEEP = 40
ROBOT_OK = ".mpB"
ANIMAL_OK = ".mpB"


class Forest:
    def __init__(self, data):
        self.data = data
        self.W, self.H = data["W"], data["H"]
        self.grid = [list(row) for row in data["grid"]]
        self.plots = {p["k"]: p for p in data["plots"]}
        self.owner = [[0] * self.W for _ in range(self.H)]
        for p in data["plots"]:
            for y in range(W.PLOT):
                for x in range(W.PLOT):
                    self.owner[p["y0"] + y][p["x0"] + x] = p["k"]
        self.chan_next = {tuple(c): [tuple(t) for t in nxt] for c, nxt in data["chan"]}
        cells = set(self.chan_next)
        for nxt in self.chan_next.values():
            cells.update(nxt)
        self.chan_cells = sorted(c for c in cells if self.cell(c) in "cB")
        self.chan_index = {c: i for i, c in enumerate(self.chan_cells)}
        self.sources = [tuple(c) for c in data["sources"]]
        self.fires = [{"cells": [tuple(c) for c in f["cells"]], "end": tuple(f["end"]), "team": f["team"], "out": False}
                      for f in data["fires"]]
        self.seesaws = [{"pedal": tuple(s["pedal"]), "arm": [tuple(c) for c in s["arm"]], "up": False,
                         "from": s["from"], "to": s["to"], "in": s["in"]} for s in data["seesaws"]]
        self.arm_of = {c: i for i, s in enumerate(self.seesaws) for c in s["arm"]}
        self.meadows = {int(t): [tuple(c) for c in cs] for t, cs in data["meadows"].items()}
        self.gap_pairs = {frozenset((tuple(a), tuple(b))) for a, b in data["gaps"]}
        self.clock = 0.0
        self.paused = False
        self.events = deque(maxlen=EVENTS_KEEP)
        self.event_id = 0
        self.version = 0
        self.done = False
        self.done_at = None
        self.robots = {}
        self.stones = []
        self.auto = {k: False for k in self.plots}
        self._plan = {k: None for k in self.plots}
        self._plan_ver = {k: -1 for k in self.plots}
        self._wait_since = {}
        self.rec = {k: [] for k in self.plots}
        self.stats = {k: {"moves": 0, "bumps": 0, "last": 0.0, "first": None} for k in self.plots}
        for k, p in self.plots.items():
            x, y, f = p["start"]
            self.robots[k] = {"pos": (x, y), "face": f, "busy": 0.0, "queue": deque(), "last": None}
            for c in p["stones"]:
                self.stones.append({"pos": tuple(c), "start": tuple(c), "home": k, "state": "."})
        # ο μεγάλος βράχος: δύο πέτρες (μία σε κάθε οικόπεδο) που κουνιούνται μόνο μαζί
        for rk in data.get("rocks") or []:
            ia, ib = (next(i for i, st in enumerate(self.stones) if st["home"] == k) for k in rk["plots"])
            self.stones[ia].update(big=ib, dir=rk["dir"])
            self.stones[ib].update(big=ia, dir=rk["dir"])
        self.lines = {k: [tuple(c) for c in p.get("line") or []] for k, p in self.plots.items()}
        self.animals = [{"kind": a["kind"], "pos": tuple(a["cell"]), "face": W.RIGHT, "team": a["team"],
                         "safe": False, "next": 0.3 + 0.05 * i, "wait": None, "start": tuple(a["cell"])}
                        for i, a in enumerate(data["animals"])]
        self.wet = set()
        self.run = None               # εκτέλεση προγραμμάτων: οικόπεδο -> {"gen", "state", "why", "path", ...}
        self.run_phase = None         # robots, settle, end
        self.run_test = False
        self.hold = False             # τα ζώα περιμένουν όσο τρέχουν τα προγράμματα
        self._run_acc = 0.0
        self._settle_t = 0.0
        self._settle_ver = -1
        self._quiet_t = 0.0
        self.recording = True
        self.run_view = {}            # στους μαθητές: ποιο μπλοκ τρέχει σε κάθε οικόπεδο
        self._run_n = 0
        self._flow_t = 0.0
        self._target = set()
        self._update_arms()
        self._target = self.flow_target()

    # ------------------------------------------------------------ βοηθητικά
    def cell(self, c):
        x, y = c
        if 0 <= x < self.W and 0 <= y < self.H:
            return self.grid[y][x]
        return "#"

    def owner_of(self, c):
        x, y = c
        if 0 <= x < self.W and 0 <= y < self.H:
            return self.owner[y][x]
        return 0

    def stone_at(self, c, state=None):
        for i, s in enumerate(self.stones):
            if s["pos"] == c and (state is None or s["state"] == state):
                return i
        return None

    def ground_stone(self, c):
        return self.stone_at(c, ".")

    def fixed_at(self, c):
        for s in self.stones:
            if s["pos"] == c and s["state"] != ".":
                return s["state"]
        return None

    def burning(self, c):
        return any(not f["out"] and c in f["cells"] for f in self.fires)

    def arm_down(self, c):
        i = self.arm_of.get(c)
        return i is not None and not self.seesaws[i]["up"]

    def robot_at(self, c):
        for k, r in self.robots.items():
            if r["pos"] == c:
                return k
        return None

    def animal_at(self, c):
        return any(a["pos"] == c and not a["safe"] for a in self.animals)

    def _event(self, kind, k=None, data=None):
        self.event_id += 1
        self.events.append((self.event_id, round(self.clock, 2), kind, k, data))
        self.version += 1

    # ------------------------------------------------------------ R2
    def passable_robot(self, c, k):
        """Μπορεί το R2 του οικοπέδου k να μπει στο κουτάκι c; (None) ή ο λόγος που δεν μπορεί."""
        if self.owner_of(c) != k:
            return "fence"
        ch = self.cell(c)
        if self.fixed_at(c) == "x":
            return None
        if ch == "F":
            return "fire" if self.burning(c) else None
        if ch == "a":
            return "branch" if self.arm_down(c) else None
        if ch in ROBOT_OK:
            return None
        return {"T": "tree", "R": "rock", "S": "rock", "w": "water", "c": "water"}.get(ch, "tree")

    def act(self, k, action):
        """Ένα πάτημα στο χειριστήριο του οικοπέδου k."""
        r = self.robots.get(k)
        if r is None or action not in W.ACTIONS or self.done or self.paused or self.auto.get(k) or self.run:
            return False
        if len(r["queue"]) >= QUEUE_MAX:
            return False
        r["queue"].append(action)
        return True

    def _do(self, k, action):
        r = self.robots[k]
        st = self.stats[k]
        if st["first"] is None:
            st["first"] = self.clock
        if action in ("left", "right"):
            r["face"] = (r["face"] + (3 if action == "left" else 1)) % 4
            r["busy"] = self.clock + TURN
            r["last"] = action
            st["moves"] += 1
            st["last"] = self.clock
            if self.recording:
                self._record(k, PL.turn(action, 1))
            self.version += 1
            return "turn"
        d = r["face"] if action == "forward" else (r["face"] + 2) % 4
        t = W.add(r["pos"], d)
        why = None
        si = self.ground_stone(t)
        if si is not None:
            if action != "forward":
                why = "stone"
            elif self.stones[si].get("big") is not None:
                why = "heavy"
            else:
                u = W.add(t, d)
                why = self._push_target(u, k)
                if why is None:
                    self._push(si, u)
        else:
            why = self.passable_robot(t, k)
            if why is None and (self.animal_at(t) or self.robot_at(t) is not None):
                why = "animal"
        if why:
            r["busy"] = self.clock + BUMP_TIME
            st["bumps"] += 1
            self._event("bump", k, why)
            r["queue"].clear()
            return "bump"
        r["pos"] = t
        r["busy"] = self.clock + STEP
        r["last"] = action
        st["moves"] += 1
        st["last"] = self.clock
        if self.recording:
            self._record(k, PL.move(action, 1))
        self._update_arms()
        self.version += 1
        return "move"

    def _push_target(self, u, k):
        if self.owner_of(u) != k:
            return "fence"
        if self.stone_at(u) is not None:
            return "stone"
        if self.robot_at(u) is not None or self.animal_at(u):
            return "animal"
        ch = self.cell(u)
        if ch in "wc":
            return None
        if ch == "F" and not self.burning(u):
            return None
        if ch in ".m":
            return None
        return {"T": "tree", "R": "rock", "S": "rock", "B": "bridge", "F": "fire", "a": "branch",
                "p": "branch"}.get(ch, "tree")

    def _push(self, si, u):
        s = self.stones[si]
        s["pos"] = u
        ch = self.cell(u)
        if ch == "w":
            s["state"] = "x"
            self._event("splash", s["home"], list(u))
        elif ch == "c":
            s["state"] = "d"
            self._event("dam", s["home"], list(u))
            self._target = self.flow_target()
        else:
            self._event("push", s["home"], list(u))

    def _record(self, k, node):
        """Το πρόγραμμα που γράφεται μόνο του όσο οδηγούν (όπως στο «Δες» του «Προγραμμάτισε»)."""
        rec = self.rec[k]
        if rec and rec[-1]["op"] == node["op"] and rec[-1]["dir"] == node["dir"] and rec[-1]["n"] < 9:
            rec[-1]["n"] += 1
        else:
            rec.append(node)

    def reset_plot(self, k):
        """«Ξανά»: το R2 και οι πέτρες του οικοπέδου στην αρχή."""
        p = self.plots[k]
        r = self.robots[k]
        x, y, f = p["start"]
        if self.robot_at((x, y)) not in (None, k):
            return False
        r.update(pos=(x, y), face=f, busy=self.clock + 0.2, last=None)
        r["queue"].clear()
        for s in self.stones:
            if s["home"] == k:
                s["pos"], s["state"] = s["start"], "."
        self.rec[k] = []
        self._plan[k] = None
        self._update_arms()
        self._target = self.flow_target()
        self._event("reset", k)
        return True

    # ------------------------------------------------------------ κλαδιά
    def _update_arms(self):
        changed = False
        for i, s in enumerate(self.seesaws):
            on_pedal = self.robot_at(s["pedal"]) is not None
            if self.run_test and self.run and s["from"] not in self.run and self._run_n >= TEST_LIFT:
                on_pedal = True                  # στη «Δοκιμή» ο γείτονας «έρχεται» μόνος του
            under = any(self.robot_at(c) is not None for c in s["arm"]) or \
                any(a["pos"] in s["arm"] and not a["safe"] for a in self.animals)
            up = on_pedal or (s["up"] and under)
            if up != s["up"]:
                s["up"] = up
                self._event("arm", s["to"], up)
                changed = True
        if changed and any(self.cell(c) in "cB" for s in self.seesaws for c in s["arm"]):
            self._target = self.flow_target()

    # ------------------------------------------------------------ νερό
    def flow_target(self):
        """Πού θα φτάσει το νερό με τα φράγματα που υπάρχουν τώρα."""
        dams = {s["pos"] for s in self.stones if s["state"] == "d"}
        # το φράγμα: κλαδί κάτω πάνω από το αυλάκι
        dams |= {c for s in self.seesaws if not s["up"] for c in s["arm"] if self.cell(c) in "cB"}
        out = set()
        q = deque(c for c in self.sources if c not in dams)
        out.update(q)
        while q:
            c = q.popleft()
            nxt = self.chan_next.get(c, [])
            for t in nxt:
                if t in dams:
                    continue
                if self.cell(t) not in "cB":
                    break                         # λιμνούλα: το νερό σταματά εκεί
                if t not in out:
                    out.add(t)
                    q.append(t)
                break                             # μόνο το πρώτο ανοιχτό αυλάκι
        return out

    def _flow_step(self):
        changed = False
        dry = self.wet - self._target
        if dry:
            self.wet -= dry
            changed = True
        grow = set()
        for c in self._target - self.wet:
            if c in self.sources:
                grow.add(c)
        for c in self.wet:
            for t in self.chan_next.get(c, []):
                if t in self._target and t not in self.wet:
                    grow.add(t)
        if grow:
            self.wet |= grow
            changed = True
        if changed:
            self.version += 1
        for i, f in enumerate(self.fires):
            if not f["out"] and f["end"] in self.wet:
                f["out"] = True
                self._event("fire_out", None, f["team"])

    # ------------------------------------------------------------ ζώα
    def _animal_ok(self, c, team, ignore_robots=False):
        ch = self.cell(c)
        if self.owner_of(c) == 0:
            return False
        if ch in ANIMAL_OK:
            pass
        elif ch == "a":
            if self.arm_down(c):
                return False
        elif ch == "F":
            if self.burning(c):
                return False
        elif ch == "w":
            if self.fixed_at(c) != "x":
                return False
        elif ch == "c":
            if c in self.wet or self.fixed_at(c):
                return False
        else:
            return False
        if self.ground_stone(c) is not None:
            return False
        if not ignore_robots:
            k = self.robot_at(c)
            if k is not None and not self._squeezable(k):
                return False
        return True

    def _squeezable(self, k):
        """Ένα R2 που τελείωσε τη δουλειά του και στέκεται ακίνητο λίγη ώρα: τα ζώα περνούν δίπλα του
        (για να μην κολλάει ποτέ το δάσος σε στενό διάδρομο)."""
        r = self.robots[k]
        if r["queue"] or self.run_phase == "robots" or not self.plot_done_stones(k):
            return False
        return self.clock - max(self.stats[k]["last"], r["busy"]) >= 3.0

    def _animal_path(self, a, ignore_robots=False):
        goals = self.meadows.get(a["team"], [])
        if not goals:
            return None
        taken = {b["pos"] for b in self.animals if b["safe"]}
        free = [g for g in goals if g not in taken] or goals
        goal_set = set(free)
        start = a["pos"]
        prev = {start: None}
        q = deque([start])
        while q:
            c = q.popleft()
            if c in goal_set and c != start:
                path = []
                while c is not None:
                    path.append(c)
                    c = prev[c]
                return path[::-1]
            for d in range(4):
                n = W.add(c, d)
                if n in prev:
                    continue
                if self.owner_of(n) != self.owner_of(c) and frozenset((c, n)) not in self.gap_pairs:
                    continue
                if self._animal_ok(n, a["team"], ignore_robots):
                    prev[n] = c
                    q.append(n)
        return None

    def _animal_step(self, a):
        if a["pos"] in self.meadows.get(a["team"], []) and not a["safe"]:
            a["safe"] = True
            self._event("saved", self.owner_of(a["pos"]), a["kind"])
            return
        path = self._animal_path(a)
        if path and len(path) > 1:
            nxt = path[1]
            a["face"] = W.dir_of(a["pos"], nxt) if W.dir_of(a["pos"], nxt) is not None else a["face"]
            a["pos"] = nxt
            a["wait"] = None
            self.version += 1
            if nxt in self.meadows.get(a["team"], []):
                a["safe"] = True
                self._event("saved", self.owner_of(nxt), a["kind"])
            return
        # μήπως περιμένει ένα R2 να κάνει στην άκρη;
        alt = self._animal_path(a, ignore_robots=True)
        wait = None
        for c in (alt or [])[1:]:
            k = self.robot_at(c)
            if k is not None:
                wait = k                          # αυτό το R2 κλείνει τον δρόμο
                break
        if wait != a["wait"]:
            a["wait"] = wait
            self.version += 1

    # ------------------------------------------------------------ αυτόματο R2
    def local_plot(self, k):
        """Το οικόπεδο k για τον λύτη: τοπικά κουτάκια, πέτρες και στόχοι όπως είναι τώρα."""
        p = self.plots[k]
        x0, y0 = p["x0"], p["y0"]
        cells = {}
        for y in range(W.PLOT):
            for x in range(W.PLOT):
                c = (x0 + x, y0 + y)
                ch = self.cell(c)
                if ch == "F" and not self.burning(c):
                    ch = "."
                if ch == "a":
                    ch = "."
                cells[(x, y)] = ch
        arm = [(c[0] - x0, c[1] - y0) for c in p.get("arm") or []]
        stones = {}
        for s in self.stones:
            if s["home"] != k:
                continue
            lc = (s["pos"][0] - x0, s["pos"][1] - y0)
            if s["state"] == ".":
                stones[lc] = "."
            else:
                stones[("fixed", lc)] = s["state"]
        return W.Plot(cells, arm=arm), stones

    def goals_left(self, k):
        p = self.plots[k]
        out = []
        for g in p["goals"]:
            if g[0] == "stone":
                if self.fixed_at(tuple(g[2])) != g[3]:
                    out.append(g)
            elif g[0] == "leave":
                if not out and self.robots[k]["pos"] in {tuple(c) for c in g[1]}:
                    out.append(g)
            else:
                out.append(g)
        return out

    def plot_done(self, k):
        """Έκανε το οικόπεδο τη δουλειά του; (το πεντάλ μετρά όταν ο γείτονας έχει περάσει)"""
        p = self.plots[k]
        for g in p["goals"]:
            if g[0] == "stone" and self.fixed_at(tuple(g[2])) != g[3]:
                return False
            if g[0] == "robot" and not self.neighbour_passed(k):
                return False                     # το πεντάλ: μένει εκεί ώσπου να περάσει ο γείτονας
        return True

    def next_of(self, k):
        """Το οικόπεδο του γείτονα που ανοίγει το πεντάλ του k (ή None)."""
        return next((s["to"] for s in self.seesaws if s["from"] == k and s["to"] != k), None)

    def crossed(self, k):
        """Πέρασε το R2 του k κάτω από το δικό του κλαδί; (έφτασε στο πεντάλ του, ή, στο τελευταίο οικόπεδο
        χωρίς πεντάλ, έκλεισε το αυλάκι πέρα από το κλαδί, ή πέρασε ήδη και ο επόμενος)"""
        p = self.plots[k]
        if not p.get("arm"):
            return True
        if p.get("pedal") and self.robots[k]["pos"] == tuple(p["pedal"]):
            return True
        if not p.get("pedal"):
            return self.plot_done_stones(k)
        nxt = self.next_of(k)
        return nxt is not None and self.crossed(nxt)

    def neighbour_passed(self, k):
        nxt = self.next_of(k)
        return nxt is None or self.crossed(nxt)

    def plot_done_stones(self, k):
        return all(self.fixed_at(tuple(g[2])) == g[3] for g in self.plots[k]["goals"] if g[0] == "stone")

    def make_plan(self, k):
        plot, stones = self.local_plot(k)
        p = self.plots[k]
        x0, y0 = p["x0"], p["y0"]
        r = self.robots[k]
        pos = (r["pos"][0] - x0, r["pos"][1] - y0)
        face = r["face"]
        acts = []
        for g in self.goals_left(k):
            if g[0] == "stone":
                target = (g[2][0] - x0, g[2][1] - y0)
                if ("fixed", target) in stones:
                    continue
                ok = (lambda q, st, target=target: ("fixed", target) in st)
            elif g[0] == "leave":
                target = {(c[0] - x0, c[1] - y0) for c in g[1]}
                ok = (lambda q, st, target=target: q not in target)
            else:
                target = (g[1][0] - x0, g[1][1] - y0)
                ok = (lambda q, st, target=target: q == target)
            res = W.solve(plot, pos, face, stones, ok, arm_up=True)
            if res is None:
                return None
            a, pos, face, stones = res
            acts += a
        return deque(acts)

    def make_way(self, k):
        """Κινήσεις για να φύγει το R2 από τον δρόμο των ζώων που το περιμένουν: πηγαίνει στην πιο κοντινή
        θέση από όπου τα ζώα περνούν."""
        waiting = [a for a in self.animals if a["wait"] == k and not a["safe"]]
        if not waiting:
            return None
        p = self.plots[k]
        x0, y0 = p["x0"], p["y0"]
        r = self.robots[k]
        here = (r["pos"][0] - x0, r["pos"][1] - y0)
        plot, stones = self.local_plot(k)
        for key in list(stones):
            if isinstance(key[0], str):
                plot.cells[key[1]] = "T"
                del stones[key]
        for a in self.animals:
            if not a["safe"] and self.owner_of(a["pos"]) == k:
                plot.cells[(a["pos"][0] - x0, a["pos"][1] - y0)] = "T"
        reach = W.bfs(here, lambda c: plot.robot_ok(c, set(stones), False))
        order = sorted(reach, key=lambda c: (abs(c[0] - here[0]) + abs(c[1] - here[1]), c))
        saved = r["pos"]
        good = set()
        for c in order:
            if c == here:
                continue
            r["pos"] = (c[0] + x0, c[1] + y0)            # δοκιμή: αν το R2 στεκόταν εκεί, περνούν τα ζώα;
            if all(self._animal_path(a) for a in waiting):
                good.add(c)
                if len(good) >= 3:
                    break
        r["pos"] = saved
        if good:
            res = W.solve(plot, here, r["face"], stones, lambda q, st: q in good, arm_up=False, limit=4000)
            if res is not None and res[0]:
                return deque(res[0])
        busy = set()
        for a in waiting:
            busy.update(self._animal_path(a, ignore_robots=True) or [])
        local = {(c[0] - x0, c[1] - y0) for c in busy}
        for strict in (True, False):
            plot, stones = self.local_plot(k)
            for a in self.animals:
                if not a["safe"] and self.owner_of(a["pos"]) == k:
                    plot.cells[(a["pos"][0] - x0, a["pos"][1] - y0)] = "T"
            for key in list(stones):
                if isinstance(key[0], str):               # τα περάσματα μένουν για τα ζώα
                    plot.cells[key[1]] = "T"
                    del stones[key]
            if strict:
                for c in local:
                    if c != here and c in plot.cells:
                        plot.cells[c] = "T"
            res = W.solve(plot, here, r["face"], stones, lambda q, st: q not in local, arm_up=False, limit=4000)
            if res is not None and res[0]:
                return deque(res[0])
        return None

    def _autopilot(self, k):
        r = self.robots[k]
        if r["queue"] or self.clock < r["busy"]:
            return
        plan = self._plan[k]
        if not plan:
            if self._plan_ver[k] == self.version:
                return                            # τίποτα δεν άλλαξε από τον τελευταίο έλεγχο
            self._plan_ver[k] = self.version
            plan = self.make_plan(k)
            if not plan and self.plot_done_stones(k):
                plan = self.make_way(k)
            self._plan[k] = plan
            if not plan:
                return
        a = plan[0]
        if a in ("forward", "back"):
            d = r["face"] if a == "forward" else (r["face"] + 2) % 4
            t = W.add(r["pos"], d)
            if self.arm_down(t) or (self.robot_at(t) is not None) or self.animal_at(t):
                # περιμένει (το κλαδί, ένα ζώο που περνά)· αν αργεί, ξανασχεδιάζει
                since = self._wait_since.setdefault(k, self.clock)
                if self.animal_at(t) and self.clock - since > 1.0:
                    self._plan[k] = None
                    self._plan_ver[k] = -1
                    self._wait_since.pop(k, None)
                return
        self._wait_since.pop(k, None)
        plan.popleft()
        before = (r["pos"], r["face"])
        res = self._do(k, a)
        if res == "bump" or (res == "move" and (r["pos"], r["face"]) == before):
            self._plan[k] = None

    def set_auto(self, k, on):
        self.auto[k] = bool(on)
        self._plan[k] = None
        self.robots[k]["queue"].clear()

    # ------------------------------------------------------------ εκτέλεση προγραμμάτων
    def start_run(self, progs, test=False):
        """progs: {οικόπεδο: πρόγραμμα (μπλοκ)}. test: η «Δοκιμή» ενός οικοπέδου (τα ζώα δεν κουνιούνται,
        η μπάρα ανοίγει μόνη της, ο γείτονας «σπρώχνει» μαζί τον μεγάλο βράχο)."""
        self.recording = False
        self.run = {}
        for k, prog in progs.items():
            if k in self.robots:
                prog = prog if isinstance(prog, list) else []
                self.run[k] = {"gen": W.run_steps(prog, self._sensor(k), W.TEST_WAIT if test else W.MAX_WAIT), "prog": prog, "pending": None,
                               "state": "run", "why": None, "path": None, "last": None, "n": 0, "hold": 0}
                self.robots[k]["queue"].clear()
        self.run_phase = "robots"
        self.run_test = test
        self.hold = True
        self._run_n = 0
        self._run_acc = RUN_STEP * 0.6
        self.version += 1

    # ------------------------------------------------------------ αισθητήρες
    def _sensor(self, k):
        def sense(kind):
            return self.distance(k) if kind == "dist" else self.line_step(k)
        return sense

    def _sensor_hit(self, c):
        ch = self.cell(c)
        if ch in "TRS":
            return True
        if ch == "a" and self.arm_down(c):
            return True
        return self.ground_stone(c) is not None or self.robot_at(c) is not None or self.animal_at(c)

    def distance(self, k):
        """«Διάβασε απόσταση (cm)»: ως το πρώτο εμπόδιο μπροστά στο R2 (και ο φράχτης του οικοπέδου)."""
        r = self.robots[k]
        c, free = r["pos"], 0
        for _ in range(3 * W.PLOT):
            c = W.add(c, r["face"])
            if self.owner_of(c) != k or self._sensor_hit(c):
                return W.CM_NEAR + W.CM_TILE * free
            free += 1
        return W.CM_FAR

    def line_step(self, k):
        r = self.robots[k]
        return W.line_next(self.lines.get(k) or [], r["pos"], r["face"])

    # ------------------------------------------------------------ ο μεγάλος βράχος
    def _big_push(self, k, action):
        """Το R2 σπρώχνει τον μεγάλο βράχο προς τη σωστή μεριά; (ο αριθμός της πέτρας ή None)"""
        if action != "forward":
            return None
        r = self.robots[k]
        si = self.ground_stone(W.add(r["pos"], r["face"]))
        if si is None or self.stones[si].get("big") is None or self.stones[si]["dir"] != r["face"]:
            return None
        return si

    def _move_big(self, si):
        pair = (si, self.stones[si]["big"])
        targets = [W.add(self.stones[i]["pos"], self.stones[i]["dir"]) for i in pair]
        if any(self._push_target(u, self.stones[i]["home"]) for i, u in zip(pair, targets)):
            return False
        for i, u in zip(pair, targets):
            self._push(i, u)
        return True

    def _chain_broken(self, k, st, path):
        """Το R2 περιμένει («περίμενε ώσπου») μπροστά στη μπάρα του, που είναι κλειστή, και το R2 του
        γείτονα δεν θα πατήσει πια το πεντάλ (το πρόγραμμά του τελείωσε αλλού)."""
        node = W.node_at(st["prog"], path)
        if self.run_test or not node or node.get("op") != "until":
            return False
        r = self.robots[k]
        ahead = W.add(r["pos"], r["face"])
        for s in self.seesaws:
            if s["to"] == k and s["from"] != k and not s["up"] and ahead in s["arm"]:
                other = self.run.get(s["from"])
                if (other is None or other["state"] != "run") and self.robot_at(s["pedal"]) is None:
                    return True
        return False

    def _run_step(self):
        self._run_n += 1
        intents = {}
        for k, st in self.run.items():
            if st["state"] != "run":
                continue
            if st["pending"] is not None:
                intents[k] = st["pending"]
                continue
            try:
                action, path = next(st["gen"])
            except StopIteration:
                st["state"] = "end"
                continue
            st["path"] = st["last"] = path
            if action.startswith("fail:"):
                st["state"] = "bump"
                st["why"] = action[5:]
                self._event("bump", k, st["why"])
                continue
            if action == "wait" and self._chain_broken(k, st, path):
                st["state"], st["why"] = "partner", "chain"   # περιμένει μπάρα που δεν θα ανοίξει πια
                continue
            st["n"] += 1
            intents[k] = (action, path)
        # ο μεγάλος βράχος κουνιέται μόνο όταν τον σπρώχνουν και τα δύο R2 στο ίδιο βήμα
        pushing = {k: si for k, (a, _) in intents.items() for si in [self._big_push(k, a)] if si is not None}
        moved = set()
        for k, si in pushing.items():
            st = self.run[k]
            partner = self.stones[si]["big"]
            if si in moved or ((partner in pushing.values() or self.run_test) and self._move_big(si)):
                moved |= {si, partner}
                continue
            # περιμένει τον γείτονα: σπρώχνει επί τόπου
            st["pending"] = intents.pop(k)
            st["hold"] += 1
            if st["hold"] == 1:
                self._event("heavy", k)
            if st["hold"] > HOLD_MAX:
                st["state"] = "bump"
                st["why"] = "heavy"
                st["pending"] = None
        for k, (action, path) in intents.items():
            st = self.run[k]
            st["pending"] = None
            st["hold"] = 0
            if action == "wait":
                self.robots[k]["busy"] = self.clock + RUN_STEP * 0.9
                continue
            before = self.event_id
            if self._do(k, action) == "bump":
                st["state"] = "bump"
                st["why"] = next((e[4] for e in reversed(self.events) if e[0] > before and e[2] == "bump"), "tree")
        self._update_arms()
        # όποιος σπρώχνει μόνος του και ο γείτονας δεν έρχεται πια: σωστός, περιμένει τον γείτονα
        running = [k for k, st in self.run.items() if st["state"] == "run"]
        if running and all(self.run[k]["pending"] is not None for k in running):
            for k in running:
                si = self._big_push(k, "forward")
                other = self.stones[self.stones[si]["big"]]["home"] if si is not None else None
                if other is None or self.run.get(other, {}).get("state") != "run":
                    self.run[k]["state"], self.run[k]["why"] = "partner", "partner"
                    self.run[k]["pending"] = None
        self.version += 1
        if all(st["state"] != "run" for st in self.run.values()):
            self.run_phase = "settle"
            self._settle_t = self.clock
            self._quiet_t = self.clock
            self._settle_ver = self.version
            if not self.run_test:
                self.hold = False

    def _run_tick(self, dt):
        if self.run_phase == "robots":
            self._run_acc += dt
            while self._run_acc >= RUN_STEP and self.run_phase == "robots":
                self._run_acc -= RUN_STEP
                self._run_step()
            return
        if self.run_phase != "settle":
            return
        if self.run_test:
            if self.clock - self._settle_t > 1.2:
                self.run_phase = "end"
            return
        # τα R2 που κλείνουν τον δρόμο των ζώων κάνουν στην άκρη μόνα τους
        for k, r in self.robots.items():
            if not r["queue"] and self.clock >= r["busy"] and any(a["wait"] == k for a in self.animals if not a["safe"]):
                plan = self.make_way(k)
                if plan:
                    r["queue"].extend(list(plan)[:QUEUE_MAX])
        if self.version != self._settle_ver:
            self._settle_ver = self.version
            self._quiet_t = self.clock
        if not self.done and self.all_saved() and all(f["out"] for f in self.fires):
            self.done = True
            self.done_at = self.clock
            self._event("done")
        quiet = SETTLE_QUIET + (3.5 if any(a["wait"] for a in self.animals if not a["safe"]) else 0)
        if self.done or self.clock - self._quiet_t > quiet or self.clock - self._settle_t > SETTLE_MAX:
            self.run_phase = "end"
            self.version += 1

    def run_results(self):
        """{οικόπεδο: [αποτέλεσμα, λόγος, μπλοκ]}: ok, bump (χτύπησε ή σταμάτησε: time, noline, heavy),
        short (το πρόγραμμα τελείωσε νωρίς), empty. ["ok", "partner"]: σωστό, ο γείτονας δεν ήρθε στον βράχο."""
        out = {}
        for k, st in (self.run or {}).items():
            goals = [g for g in self.plots[k]["goals"] if g[0] in ("stone", "leave", "robot")]
            ok = True
            for g in goals:
                if g[0] == "stone" and self.fixed_at(tuple(g[2])) != g[3]:
                    ok = False
                elif g[0] == "leave" and self.robots[k]["pos"] in {tuple(c) for c in g[1]}:
                    ok = False
                elif g[0] == "robot" and self.robots[k]["pos"] != tuple(g[1]):
                    ok = False
            path = list(st["path"]) if st["path"] else None
            if st["state"] == "partner":
                out[k] = ["ok", st["why"] or "partner", None]
            elif ok and st["state"] != "bump":
                out[k] = ["ok", None, None]
            elif st["state"] == "bump":
                out[k] = ["bump", st["why"], path]
            elif st["n"] == 0 and not W.has_sensors(st["prog"]):
                out[k] = ["empty", None, None]
            else:
                out[k] = ["short", None, list(st["last"]) if st["last"] else None]
        return out

    # ------------------------------------------------------------ ο χρόνος
    def tick(self, dt):
        if self.paused:
            return
        self.clock += dt
        if self.run:
            self._run_tick(dt)
        for k, r in self.robots.items():
            if self.run and k in self.run and self.run_phase == "robots":
                continue
            if self.auto.get(k) and not self.run and self.data.get("mode", "drive") == "drive":
                self._autopilot(k)               # στις πίστες με πρόγραμμα: μόνο στην «Εκτέλεση»
            elif r["queue"] and self.clock >= r["busy"]:
                self._do(k, r["queue"].popleft())
        self._update_arms()
        self._flow_t += dt
        while self._flow_t >= FLOW:
            self._flow_t -= FLOW
            self._flow_step()
        for a in self.animals:
            if not a["safe"] and self.clock >= a["next"] and not self.hold:
                a["next"] = self.clock + ANIMAL_STEP
                self._animal_step(a)
        if not self.done and self.all_saved() and all(f["out"] for f in self.fires):
            self.done = True
            self.done_at = self.clock
            self._event("done")

    def all_saved(self):
        return all(a["safe"] for a in self.animals)

    # ------------------------------------------------------------ μετρήσεις
    def counts(self, team=None):
        an = [a for a in self.animals if team is None or a["team"] == team]
        fi = [f for f in self.fires if team is None or f["team"] == team]
        return (sum(a["safe"] for a in an), len(an), sum(f["out"] for f in fi), len(fi))

    # ------------------------------------------------------------ «φωτογραφίες» για το δίκτυο
    def snapshot(self, since=0):
        wet = "".join("1" if c in self.wet else "0" for c in self.chan_cells)
        return {
            "r": [[r["pos"][0], r["pos"][1], r["face"]] for k, r in sorted(self.robots.items())],
            "s": [[s["pos"][0], s["pos"][1], s["state"]] for s in self.stones],
            "w": wet,
            "a": [[a["pos"][0], a["pos"][1], a["face"], int(a["safe"]), a["wait"] or 0] for a in self.animals],
            "f": [int(f["out"]) for f in self.fires],
            "arm": [int(s["up"]) for s in self.seesaws],
            "e": [list(e) for e in self.events if e[0] > since],
            "done": self.done, "t": round(self.clock, 2), "p": self.paused,
            "auto": [k for k, v in self.auto.items() if v],
            "ri": {str(k): [list(st["path"]) if st["path"] else None, st["state"]] for k, st in self.run.items()}
            if self.run else {},
            "rp": self.run_phase,
        }

    def apply(self, snap):
        """Στους μαθητές: η κατάσταση όπως την έστειλε ο δάσκαλος."""
        for (k, r), (x, y, f) in zip(sorted(self.robots.items()), snap.get("r", [])):
            r["pos"], r["face"] = (x, y), f
        for s, (x, y, st) in zip(self.stones, snap.get("s", [])):
            s["pos"], s["state"] = (x, y), st
        w = snap.get("w", "")
        self.wet = {c for c, v in zip(self.chan_cells, w) if v == "1"}
        for a, v in zip(self.animals, snap.get("a", [])):
            a["pos"], a["face"], a["safe"] = (v[0], v[1]), v[2], bool(v[3])
            a["wait"] = v[4] or None
        for f, out in zip(self.fires, snap.get("f", [])):
            f["out"] = bool(out)
        for s, up in zip(self.seesaws, snap.get("arm", [])):
            s["up"] = bool(up)
        self.done = bool(snap.get("done"))
        self.clock = snap.get("t", self.clock)
        self.paused = bool(snap.get("p"))
        autos = set(snap.get("auto", []))
        self.auto = {k: k in autos for k in self.plots}
        self.run_view = {int(k): v for k, v in (snap.get("ri") or {}).items()}
        self.run_phase = snap.get("rp")
        self.version += 1
        return [tuple(e) for e in snap.get("e", [])]
