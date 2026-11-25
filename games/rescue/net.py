"""Το μάθημα στο δίκτυο του εργαστηρίου (χωρίς ίντερνετ και χωρίς server, όπως το Ποδόσφαιρο).

- Lesson: η «καρδιά» του μαθήματος, χωρίς δίκτυο: ποιος υπολογιστής έχει ποιο οικόπεδο, το δάσος
  (sim.Forest) που τρέχει εδώ, η βοήθεια του δασκάλου, η παύση, το πάγωμα.
- Host: ο υπολογιστής του δασκάλου. Ένα Lesson που μιλά με τους μαθητές (TCP, γραμμές JSON) και απαντά
  σε όποιον ψάχνει μάθημα (UDP broadcast), με τα εργαλεία του net.py του Ποδοσφαίρου.
- Client: ο υπολογιστής των μαθητών. Στέλνει τα πατήματα του χειριστηρίου και δέχεται «φωτογραφίες» του
  δάσους (snap), που τις ζωγραφίζει. Practice: η «Εξάσκηση» σε έναν υπολογιστή (ένα Lesson εδώ, με
  αυτόματα R2 στα άλλα οικόπεδα). Client και Practice έχουν τα ίδια πεδία (StudentState) για την οθόνη.

Όλα είναι «non-blocking»: οι οθόνες καλούν poll()/tick() σε κάθε καρέ.
"""
import socket
import time
import uuid
from collections import deque

from core import __version__ as VERSION
from games.soccer.net import Conn, Finder, HELLO_TIMEOUT, PING_EVERY, SILENCE, CONNECT_TIMEOUT, WINDOWS, \
    _encode, primary_ip, valid_ip  # noqa: F401
from . import sim as S
from . import world as W

PL_LIMIT = 40              # τόσα μπλοκ το πολύ σε ένα πρόγραμμα

DISC_PORT = 47821
GAME_PORT = 47822
PORT_TRIES = 16
NAME_MAX = 14
MAX_SEATS = 25
SNAP_EVERY = 0.08          # το πολύ τόσο συχνά πάει μια «φωτογραφία» του δάσους
SNAP_ALIVE = 1.0           # και τουλάχιστον μία το δευτερόλεπτο
STUCK_AFTER = 75.0         # τόσα δευτερόλεπτα χωρίς κίνηση (και η δουλειά δεν έγινε) = «κόλλησε»
IDLE_AFTER = 45.0          # τόσα δευτερόλεπτα από την αρχή χωρίς καμία κίνηση = «δεν κουνήθηκε»
RESULT_TIME = 8.0          # πόσο φαίνονται τα αποτελέσματα πριν τον επόμενο γύρο
READY_WAIT = 2.5           # όλοι «Έτοιμοι!»: η εκτέλεση ξεκινά σε τόσα δευτερόλεπτα
PROG_EVERY = 0.35          # κάθε πότε στέλνει ο μαθητής το πρόγραμμά του (όταν αλλάζει)
WHY_HINT = {"tree": "Το R2 χτυπά σε δέντρο. Μήπως στρίβει από την άλλη;",
            "rock": "Το R2 χτυπά σε βράχο. Μήπως στρίβει από την άλλη;",
            "water": "Το R2 πάει στο νερό! Μετρήστε ξανά τα κουτάκια.",
            "fence": "Το R2 χτυπά στον φράχτη: πάει πολύ μακριά ή προς τα λάθος.",
            "stone": "Το R2 σπρώχνει μόνο προς τα μπροστά.", "animal": "Ένα ζώο στον δρόμο: περιμένετε λίγο.",
            "branch": "Το κλαδί είναι κάτω.", "fire": "Φωτιά! Το R2 πάει προς τη φωτιά.",
            "bridge": "Πέτρα πάνω στο γεφυράκι δεν πάει.",
            "heavy": "Ο βράχος είναι βαρύς: σπρώξτε τον μαζί με τον γείτονα!",
            "time": "Το R2 περίμενε και περίμενε... Μήπως το σύμβολο (< ή >) ή ο αριθμός είναι λάθος;",
            "noline": "Το R2 δεν είναι πάνω στη μαύρη γραμμή. Πρώτα πήγαινε ως την αρχή της."}
TEACHER_MSGS = ("Μπράβο!", "Μιλήστε με τον γείτονα!", "Κοιτάξτε τον χάρτη!", "Ελάτε στον πίνακα!",
                "Προσοχή στα ζώα!")


def clean_name(text):
    """Ένα όνομα: κεφαλαίο το πρώτο γράμμα, ως NAME_MAX γράμματα, χωρίς περίεργα σύμβολα."""
    out = "".join(ch for ch in str(text) if ch.isalnum() or ch in " -'&")
    out = " ".join(out.split())[:NAME_MAX]
    return out[:1].upper() + out[1:]


def test_program(data, k, prog):
    """Η «Δοκιμή» ενός οικοπέδου: τρέχει μόνο το R2 του, με το πρόγραμμά του. Επιστρέφει το αποτέλεσμα."""
    f = S.Forest(data)
    f.start_run({k: prog}, test=True)
    t = 0.0
    while f.run_phase != "end" and t < 120:
        f.tick(0.1)
        t += 0.1
    return f.run_results().get(k, ["empty", None, None])


def program_hint(result, kind=None):
    status, why, path = result
    if status == "ok" and why == "partner":
        return "Το πρόγραμμά σας είναι σωστό! Ο γείτονας πρέπει να φτάσει κι αυτός στον βράχο."
    if status == "ok" and why == "chain":
        return "Το πρόγραμμά σας είναι σωστό! Η μπάρα δεν άνοιξε: ο γείτονας δεν πάτησε το πεντάλ."
    if status == "ok":
        return "Το πρόγραμμα πετυχαίνει! Πατήστε «Έτοιμοι!»."
    if status == "empty":
        return "Ξεκινήστε: σύρετε μια εντολή κάτω από το «R2 starts»."
    if status == "short" and kind == "bars":
        return "Το R2 δεν φτάνει στο πεντάλ. Μετρήστε ξανά τα κουτάκια."
    if status == "short" and kind == "rock":
        return "Το R2 δεν φτάνει στον βράχο. Ακολουθεί τη μαύρη γραμμή;"
    if status == "short":
        return "Το R2 σταματά πριν σπρώξει την πέτρα. Μήπως θέλει περισσότερα κουτάκια;"
    if kind == "bars" and why == "branch":
        return "Η μπάρα ήταν κλειστή! Περίμενε ώσπου η απόσταση να γίνει μεγάλη: «απόσταση > 20»."
    if kind == "bars" and why == "fence":
        return "Το R2 πήγε πέρα από το πεντάλ. Λιγότερα κουτάκια!"
    return WHY_HINT.get(why, "Κοιτάξτε πού σταματά το R2 στη «Δοκιμή».")


FIX_TEXT = {
    "more": "Θέλει περισσότερα κουτάκια στο κόκκινο μπλοκ.",
    "fewer": "Λιγότερα κουτάκια στο κόκκινο μπλοκ: το R2 πάει πολύ μακριά.",
    "turn": "Η στροφή στο κόκκινο μπλοκ είναι από την άλλη μεριά.",
    "turns": "Άλλαξε τον αριθμό της στροφής στο κόκκινο μπλοκ.",
    "dir": "Το κόκκινο μπλοκ πάει από την άλλη μεριά (μπροστά ή πίσω).",
    "cmp": "Κοίτα το σύμβολο (< ή >) στο κόκκινο μπλοκ.",
    "cm": "Άλλαξε τον αριθμό (cm) στο κόκκινο μπλοκ.",
    "back_end": "Σχεδόν! Στο τέλος χρειάζεται και ένα βήμα πίσω.",
    "fwd_end": "Σχεδόν! Στο τέλος λίγα κουτάκια ακόμα μπροστά.",
    "turn_first": "Πρώτα χρειάζεται μια στροφή, για να κοιτάει το R2 προς τα εκεί που πάει.",
    "line_end": "Στο τέλος: «Ακολούθησε τη μαύρη γραμμή».",
    "until_first": "Πριν κινηθεί το R2: «περίμενε ώσπου» να ανοίξει η μπάρα.",
    "remove": "Το κόκκινο μπλοκ περισσεύει.",
}


def program_fix(data, k, prog):
    """Η πιο μικρή αλλαγή που κάνει το πρόγραμμα να πετυχαίνει (στη «Δοκιμή»): (είδος, μπλοκ για κόκκινο,
    κείμενο) ή None. Στη Διόρθωσε μόνο αλλαγές σε πεδία· στη Γράψε και ένα μπλοκ που λείπει ή περισσεύει."""
    if not isinstance(prog, list) or not prog or not all(isinstance(n, dict) for n in prog):
        return None
    if test_program(data, k, prog)[0] == "ok":
        return None
    write = data.get("mode") == "write"
    palette = set(data.get("palette") or [])

    def edit(i, field, value):
        out = [dict(n) for n in prog]
        out[i][field] = value
        return out

    tiers = [[], [], [], []]
    for i, nd in enumerate(prog):
        op, n = nd.get("op"), nd.get("n", 1)
        if op == "move":
            for dn in (1, -1):
                if isinstance(n, int) and 1 <= n + dn <= 9:
                    tiers[0].append(("more" if dn > 0 else "fewer", (i,), edit(i, "n", n + dn)))
            for dn in (2, -2, 3, -3):
                if isinstance(n, int) and 1 <= n + dn <= 9:
                    tiers[2].append(("more" if dn > 0 else "fewer", (i,), edit(i, "n", n + dn)))
            tiers[2].append(("dir", (i,), edit(i, "dir", "back" if nd.get("dir") != "back" else "forward")))
        elif op == "turn":
            tiers[0].append(("turn", (i,), edit(i, "dir", "left" if nd.get("dir") == "right" else "right")))
            tiers[2].append(("turns", (i,), edit(i, "n", 2 if n == 1 else 1)))
        elif op == "until":
            tiers[0].append(("cmp", (i,), edit(i, "cmp", "<" if nd.get("cmp") == ">" else ">")))
            tiers[2] += [("cm", (i,), edit(i, "cm", cm)) for cm in (10, 20, 30, 40, 50) if cm != nd.get("cm")]
    if write:
        last = (len(prog) - 1,)
        if "move" in palette:
            tiers[1].append(("back_end", last, prog + [W.move_block("back", 1)]))
            tiers[1] += [("fwd_end", last, prog + [W.move_block("forward", m)]) for m in (1, 2)]
        if "turn" in palette:
            tiers[1] += [("turn_first", (0,), [W.turn_block(d, 1)] + prog) for d in ("left", "right")]
        if "line" in palette and not any(n.get("op") == "line" for n in prog):
            tiers[1].append(("line_end", last, prog + [W.line_block()]))
        if "until" in palette and not any(n.get("op") == "until" for n in prog):
            j = next((i for i, n in enumerate(prog) if n.get("op") == "move"), len(prog))
            tiers[1].append(("until_first", (min(j, len(prog) - 1),), prog[:j] + [W.until_block(">", 20)] + prog[j:]))
        if len(prog) > 1:
            tiers[3] += [("remove", (i,), prog[:i] + prog[i + 1:]) for i in range(len(prog))]
    for tier in tiers:
        for kind, path, cand in tier:
            if test_program(data, k, cand)[0] == "ok":
                return kind, path, FIX_TEXT[kind]
    return None


def route_cells(forest, k):
    """Η βοήθεια «Δρόμος»: τα κουτάκια ως εκεί όπου το R2 σπρώχνει την πέτρα (ή ως το πεντάλ)."""
    plan = forest.make_plan(k)
    if not plan:
        return []
    p = forest.plots[k]
    x0, y0 = p["x0"], p["y0"]
    plot, stones = forest.local_plot(k)
    r = forest.robots[k]
    pos, face = (r["pos"][0] - x0, r["pos"][1] - y0), r["face"]
    cells = [r["pos"]]
    for a in plan:
        pos, face, stones, what = W.step(plot, pos, face, a, stones, True)
        g = (pos[0] + x0, pos[1] + y0)
        if g != cells[-1]:
            cells.append(g)
        if what == "push":
            break
    return [list(c) for c in cells]


class Lesson:
    """Το μάθημα χωρίς δίκτυο. Οι υποκλάσεις στέλνουν τα μηνύματα (send / broadcast)."""

    def __init__(self, title="ΜΑΘΗΜΑ"):
        self.title = title
        self.pcs = {}                 # pc -> {"pc", "name", "host", "seat", "on"}
        self.bots = 0                 # αυτόματα R2 στο τέλος (για επίδειξη ή όταν λείπουν μαθητές)
        self.state = "lobby"          # lobby, level
        self.data = None
        self.forest = None
        self.level_id = None
        self.level_no = 0
        self.assign = {}              # οικόπεδο -> pc (None: αυτόματο R2)
        self.paused = False
        self.frozen = False
        self.clock = 0.0
        self.completed = None         # callback(level_id) όταν η τάξη πετύχει
        self.help_log = deque(maxlen=30)
        self._snap_t = -9.0
        self._snap_ver = -1
        self._sent_event = 0
        self._rec_sent = {}
        self._stuck = {}
        self._stuck_t = -9.0
        self.done_sent = False
        # κεφάλαια με πρόγραμμα
        self.mode = "drive"
        self.phase = None             # plan, run, result, done
        self.round = 0
        self.programs = {}
        self.ready = {}
        self.plan_seconds = 180
        self.left = 0.0
        self.ready_at = None
        self.results = {}
        self.history = {}
        self.edited = {}
        self.result_at = 0.0
        self.class_ok = False
        self._tests = {}

    # ------------------------------------------------------------ μηνύματα (οι υποκλάσεις τα στέλνουν)
    def send(self, pc, msg):
        pass

    def broadcast(self, msg):
        for pc in list(self.pcs):
            self.send(pc, msg)

    # ------------------------------------------------------------ υπολογιστές
    def add_pc(self, pc, name, host=""):
        name = clean_name(name) or "Ομάδα"
        seat = self._free_seat()
        self.pcs[pc] = {"pc": pc, "name": name, "host": host, "seat": seat, "on": True}
        self._lobby()
        return self.pcs[pc]

    def _free_seat(self):
        taken = {p["seat"] for p in self.pcs.values()}
        return next((s for s in range(MAX_SEATS) if s not in taken), None)

    def drop_pc(self, pc):
        p = self.pcs.get(pc)
        if p is None:
            return
        if self.state == "level" and pc in self.assign.values():
            p["on"] = False           # το οικόπεδό του μένει, με αυτόματο R2 ως να ξαναμπεί
            k = self.plot_of(pc)
            if k and self.forest:
                self.forest.set_auto(k, True)
        else:
            del self.pcs[pc]
        self._lobby()

    def seat(self, pc, seat):
        """Ο δάσκαλος βάζει τον υπολογιστή σε μια θέση της αίθουσας (αν είναι πιασμένη, ανταλλάσσουν)."""
        if pc not in self.pcs or not 0 <= seat < MAX_SEATS:
            return
        other = next((p for p in self.pcs.values() if p["seat"] == seat), None)
        if other:
            other["seat"] = self.pcs[pc]["seat"]
        self.pcs[pc]["seat"] = seat
        self._lobby()

    def order(self):
        """Οι υπολογιστές με τη σειρά των θέσεων (αυτή είναι η σειρά των οικοπέδων)."""
        seated = [p for p in self.pcs.values() if p["on"] and p["seat"] is not None]
        return [p["pc"] for p in sorted(seated, key=lambda p: p["seat"])]

    def plot_of(self, pc):
        return next((k for k, v in self.assign.items() if v == pc), None)

    def name_of(self, k):
        pc = self.assign.get(k)
        if pc is None or pc not in self.pcs:
            return "R2"
        return self.pcs[pc]["name"]

    def size(self):
        return max(W.MIN_PCS, min(W.MAX_PCS, len(self.order()) + self.bots))

    def _lobby(self):
        if self.state == "lobby":
            self.broadcast({"t": "lobby", "title": self.title, "n": len(self.pcs)})

    # ------------------------------------------------------------ πίστα
    def start_level(self, level_id, seed=None):
        order = self.order()
        n = max(W.MIN_PCS, min(W.MAX_PCS, len(order) + self.bots))
        self.level_no += 1
        self.data = W.build(level_id, n, seed if seed is not None else self.level_no)
        self.level_id = str(level_id)
        self.forest = S.Forest(self.data)
        self.assign = {k: (order[k - 1] if k <= len(order) else None) for k in range(1, n + 1)}
        for k, pc in self.assign.items():
            if pc is None:
                self.forest.set_auto(k, True)
        self.state = "level"
        self.paused = False
        self.done_sent = False
        self._snap_ver = -1
        self._sent_event = 0
        self._rec_sent = {}
        self._stuck = {}
        self.mode = self.data.get("mode", "drive")
        self.results, self.history, self._tests = {}, {k: [] for k in self.assign}, {}
        self.class_ok = False
        if self.mode != "drive":
            self.programs = {k: [dict(n) for n in (p.get("given") or [])] for k, p in self.forest.plots.items()}
            self.edited = {k: self.clock for k in self.assign}
            self.round = 1
            self._plan(send=False)
        else:
            self.phase = None
        for pc in list(self.pcs):
            self._send_level(pc)

    def names(self):
        return {str(k): self.name_of(k) for k in self.assign}

    def _send_level(self, pc):
        if self.data is None:
            return
        k = self.plot_of(pc)
        self.send(pc, {"t": "level", "data": W.strip_answers(self.data), "k": k, "names": self.names(),
                       "no": self.level_no, "frozen": self.frozen, "mode": self.mode,
                       "prog": self.programs.get(k, []) if k else [], "round": self.round, "phase": self.phase,
                       "left": self.left, "timed": self.plan_seconds > 0, "paused": self.paused,
                       "res": {str(kk): v for kk, v in self.results.items()}})
        self.send(pc, {"t": "snap", "s": self.forest.snapshot(since=self.forest.event_id)})
        if k:
            self.send(pc, {"t": "rec", "p": self.forest.rec.get(k, [])})

    def act(self, pc, action):
        k = self.plot_of(pc)
        if k and self.forest and not self.paused and not self.frozen:
            self.forest.act(k, action)

    def reset_plot(self, k):
        if self.forest:
            self.forest.reset_plot(k)

    def tick(self, dt):
        """Ο χρόνος του μαθήματος (καλείται σε κάθε καρέ)."""
        self.clock += dt
        f = self.forest
        if self.state != "level" or f is None:
            return
        if self.mode != "drive":
            self._tick_rounds(dt)
            f = self.forest
        if not self.paused and not self.frozen:
            f.tick(dt)
        if f.version != self._snap_ver and self.clock - self._snap_t >= SNAP_EVERY or \
                self.clock - self._snap_t >= SNAP_ALIVE:
            self._snap_t = self.clock
            self._snap_ver = f.version
            self.broadcast({"t": "snap", "s": f.snapshot(since=self._sent_event)})
            self._sent_event = f.event_id
        for k, pc in self.assign.items():
            rec = f.rec.get(k, [])
            if pc is not None and self._rec_sent.get(k) != rec:
                self._rec_sent[k] = [dict(n) for n in rec]
                self.send(pc, {"t": "rec", "p": rec})
        if f.done and not self.done_sent and self.mode == "drive":
            self.done_sent = True
            saved, total, out, fires = f.counts()
            self.broadcast({"t": "done", "saved": saved, "animals": total, "fires": fires})
            if self.completed:
                self.completed(self.level_id)

    # ------------------------------------------------------------ γύροι (κεφάλαια με πρόγραμμα)
    def _plan(self, send=True):
        self.phase = "plan"
        self.left = float(self.plan_seconds)
        self.ready = {k: False for k in self.assign}
        self.ready_at = None
        if send:
            self._phase()

    def _phase(self):
        self.broadcast({"t": "phase", "phase": self.phase, "round": self.round, "left": self.left,
                        "paused": self.paused})

    def humans(self):
        """Τα οικόπεδα που έχουν παιδιά συνδεδεμένα (χωρίς αυτόματο R2)."""
        f = self.forest
        return [k for k, pc in self.assign.items() if pc is not None and self.pcs.get(pc, {}).get("on")
                and not f.auto.get(k)]

    def set_program(self, pc, prog, ready):
        k = self.plot_of(pc)
        if not k or self.mode == "drive" or not isinstance(prog, list):
            return
        prog = prog[:PL_LIMIT]
        if prog != self.programs.get(k):
            self.edited[k] = self.clock
            self._tests.pop(k, None)
            self._tests.pop(("fix", k), None)
        self.programs[k] = prog
        if self.phase == "plan":
            self.ready[k] = bool(ready) and bool(prog)

    def run_now(self):
        """«Εκτέλεση!»: όλα τα R2 τρέχουν τα προγράμματά τους (τα αυτόματα τη λύση) σε καινούργιο δάσος."""
        if self.state != "level" or self.phase != "plan":
            return
        old_auto = dict(self.forest.auto)
        self.forest = S.Forest(self.data)
        progs = {}
        for k, p in self.forest.plots.items():
            self.forest.auto[k] = old_auto.get(k, False)
            progs[k] = (p.get("program") or []) if old_auto.get(k) else (self.programs.get(k) or [])
        self.forest.start_run(progs)
        self._run_progs = progs
        self.phase = "run"
        self.paused = False
        self._snap_ver = -1
        self._sent_event = 0
        self._phase()

    def _finish_run(self):
        f = self.forest
        self.results = f.run_results()
        # «σωστό, αλλά ο γείτονας...»: μόνο αν το πρόγραμμα πετυχαίνει και στη «Δοκιμή»
        for k, r in list(self.results.items()):
            if r[0] == "ok" and r[1] in ("partner", "chain"):
                t = test_program(self.data, k, getattr(self, "_run_progs", {}).get(k) or [])
                if t[0] != "ok":
                    self.results[k] = t
        for k, r in self.results.items():
            self.history.setdefault(k, []).append(r)
        self.class_ok = f.all_saved() and all(fi["out"] for fi in f.fires)
        self.phase = "done" if self.class_ok else "result"
        self.result_at = self.clock
        saved, total, out, fires = f.counts()
        self.broadcast({"t": "result", "res": {str(k): v for k, v in self.results.items()}, "ok": self.class_ok,
                        "round": self.round, "saved": saved, "animals": total, "out": out, "fires": fires})
        self._phase()
        if self.class_ok:
            self.broadcast({"t": "done", "saved": saved, "animals": total, "fires": fires})
            if self.completed:
                self.completed(self.level_id)

    def next_round(self):
        if self.phase not in ("result",):
            return
        old_auto = dict(self.forest.auto)
        self.forest = S.Forest(self.data)
        for k in self.forest.plots:
            self.forest.auto[k] = old_auto.get(k, False)
        self.round += 1
        self._snap_ver = -1
        self._sent_event = 0
        self._plan()

    def _tick_rounds(self, dt):
        if self.paused:
            return
        if self.phase == "plan":
            if self.plan_seconds > 0 and not self.frozen:
                self.left = max(0.0, self.left - dt)
            hum = self.humans()
            if hum and all(self.ready.get(k) for k in hum):
                if self.ready_at is None:
                    self.ready_at = self.clock + READY_WAIT
                    self.broadcast({"t": "allready", "in": READY_WAIT})
            else:
                self.ready_at = None
            if (self.ready_at is not None and self.clock >= self.ready_at) or \
                    (self.plan_seconds > 0 and self.left <= 0):
                self.run_now()
        elif self.phase == "run":
            if self.forest.run_phase == "end":
                self._finish_run()
        elif self.phase == "result":
            if self.clock >= self.result_at + RESULT_TIME:
                self.next_round()

    def add_time(self, seconds=60):
        if self.phase == "plan" and self.plan_seconds > 0:
            self.left += seconds
            self._phase()

    def test_result(self, k):
        """Η «Δοκιμή» του τρέχοντος προγράμματος (για τη βοήθεια του δασκάλου), φυλαγμένη ώσπου να αλλάξει."""
        if k not in self._tests:
            self._tests[k] = test_program(self.data, k, self.programs.get(k) or [])
        return self._tests[k]

    def fix_result(self, k):
        """Η πιο μικρή διόρθωση του προγράμματος (ή None), φυλαγμένη μαζί με τη «Δοκιμή»."""
        key = ("fix", k)
        if key not in self._tests:
            res = self.test_result(k)
            self._tests[key] = None if res[0] in ("ok", "empty") else program_fix(self.data, k, self.programs.get(k) or [])
        return self._tests[key]

    # ------------------------------------------------------------ για το πάνελ του δασκάλου
    def status(self, k):
        """off, bot, auto, done, stuck, idle, drive (και στα προγράμματα: ready, write, ok, fail, run)"""
        f = self.forest
        pc = self.assign.get(k)
        if pc is None:
            return "bot"
        if not self.pcs.get(pc, {}).get("on"):
            return "off"
        if f.auto.get(k):
            return "auto"
        if self.mode != "drive":
            if self.phase == "run":
                return "run"
            last = self.results.get(k)
            if self.phase in ("result", "done"):
                return "ok" if last and last[0] == "ok" else "fail"
            if self.ready.get(k):
                return "ready"
            if last and last[0] != "ok" and self.clock - self.edited.get(k, 0) > 60:
                return "stuck"
            return "write"
        if f.plot_done(k):
            return "done"
        st = f.stats[k]
        if self.clock - self._stuck_t > 2.0:
            self._stuck_t = self.clock
            self._stuck = {kk: f.make_plan(kk) is None for kk in f.plots
                           if not f.auto.get(kk) and not f.plot_done_stones(kk)}
        if self._stuck.get(k):
            return "stuck"
        if st["first"] is None:
            return "idle" if f.clock > IDLE_AFTER else "drive"
        if f.clock - st["last"] > STUCK_AFTER:
            return "stuck"
        return "drive"

    def suggest_hint(self, k):
        f = self.forest
        lv = W.level(self.level_id)
        if f is None:
            return lv["hint"]
        if self.mode != "drive":
            res = self.test_result(k)
            fix = self.fix_result(k)
            if fix:
                return fix[2]
            return program_hint(res, self.data.get("kind")) if res[0] != "empty" or not self.programs.get(k)                 else lv["hint"]
        if any(a["wait"] == k for a in f.animals if not a["safe"]):
            return "Κάνε στην άκρη, να περάσουν τα ζώα!"
        if not f.plot_done_stones(k) and f.make_plan(k) is None:
            return "Η πέτρα κόλλησε! Πάτα «Ξανά» και ξεκίνα από την αρχή."
        p = f.plots[k]
        if f.plot_done_stones(k):
            pedal = p.get("pedal")
            if pedal and tuple(pedal) != f.robots[k]["pos"]:
                return "Πήγαινε στο κίτρινο πεντάλ και μείνε εκεί, να περάσει ο γείτονας!"
            if pedal:
                return "Μείνε πάνω στο πεντάλ ώσπου να περάσει ο γείτονας!"
        if p.get("arm") and f.make_plan(k) is not None:
            return "Περίμενε τον γείτονα να πατήσει το κλαδί, μετά πέρνα από κάτω!"
        return lv["hint"]

    def help(self, k, kind, data=None):
        """Βοήθεια σε ένα οικόπεδο. kind: hint, route, next, msg."""
        pc = self.assign.get(k)
        f = self.forest
        if kind == "hint":
            data = data or self.suggest_hint(k)
        elif kind == "route" and self.mode != "drive":
            fresh = S.Forest(self.data)
            data = route_cells(fresh, k)
        elif kind == "route":
            data = route_cells(f, k)
        elif kind == "blame":
            res = self.test_result(k)
            fix = self.fix_result(k)
            data = (list(fix[1]) if fix else res[2]) if res[0] != "ok" else None
        elif kind == "solution":
            data = f.plots[k].get("program") or []
            self.programs[k] = [dict(n) for n in data]
            self._tests.pop(k, None)
            self._tests.pop(("fix", k), None)
        elif kind == "next":
            plan = f.make_plan(k)
            data = plan[0] if plan else None
        self.help_log.append((self.clock, k, kind))
        if pc is not None:
            self.send(pc, {"t": "help", "kind": kind, "data": data})
        return data

    def set_auto(self, k, on=None):
        f = self.forest
        if f is None or k not in f.plots or self.assign.get(k) is None:
            return
        on = (not f.auto.get(k)) if on is None else bool(on)
        f.set_auto(k, on)
        pc = self.assign.get(k)
        if pc is not None:
            self.send(pc, {"t": "help", "kind": "auto", "data": on})

    # ------------------------------------------------------------ κουμπιά του δασκάλου
    def pause(self, on=None):
        if self.state != "level" or self.forest is None:
            return
        self.paused = (not self.paused) if on is None else bool(on)
        self.forest.paused = self.paused
        self._snap_ver = -1
        if self.mode != "drive":
            self._phase()

    def freeze(self, on=None):
        self.frozen = (not self.frozen) if on is None else bool(on)
        self.broadcast({"t": "freeze", "on": self.frozen})

    def to_lobby(self):
        self.state = "lobby"
        self.phase = None
        self.mode = "drive"
        self.data = None
        self.forest = None
        self.assign = {}
        for pc in [pc for pc, p in self.pcs.items() if not p["on"]]:
            del self.pcs[pc]
        self.broadcast({"t": "lobby", "title": self.title, "n": len(self.pcs)})


# ================================================================ ο υπολογιστής του δασκάλου
class Host(Lesson):
    role = "host"

    def __init__(self, title="ΜΑΘΗΜΑ", port=GAME_PORT, disc_port=DISC_PORT):
        super().__init__(title)
        self.id = uuid.uuid4().hex[:10]
        self.conns = {}               # pc -> Conn
        self.pending = []
        self._next_pc = 1
        self.ip = primary_ip() or "127.0.0.1"
        self.closed = False
        self._ping_t = 0.0
        self._open_server(port)
        self._open_beacon(disc_port)

    def _open_server(self, port):
        last = None
        for p in range(port, port + PORT_TRIES):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                if WINDOWS:
                    s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
                else:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", p))
                s.listen(MAX_SEATS + 4)
                s.setblocking(False)
                self.server, self.port = s, p
                return
            except OSError as e:
                last = e
                s.close()
        raise OSError(f"καμία ελεύθερη θύρα ({last})")

    def _open_beacon(self, disc_port):
        self.beacon = None
        try:
            b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            b.bind(("", disc_port))
            b.setblocking(False)
            self.beacon = b
        except OSError:
            self.beacon = None

    def info(self):
        return {"t": "field", "id": self.id, "name": self.title, "port": self.port, "v": VERSION,
                "state": "lobby", "n": [len(self.pcs), 0], "max": MAX_SEATS, "game": "rescue2"}

    def send(self, pc, msg):
        c = self.conns.get(pc)
        if c and not c.closed:
            c.send(msg)

    def broadcast(self, msg):
        data = _encode(msg)
        for c in self.conns.values():
            if not c.closed:
                c.out += data
                c.flush()

    def poll(self):
        if self.closed:
            return
        now = time.monotonic()
        while True:
            try:
                sock, _ = self.server.accept()
            except (BlockingIOError, InterruptedError, OSError):
                break
            self.pending.append(Conn(sock))
        for c in list(self.pending):
            for m in c.read():
                if m.get("t") == "hello":
                    self._hello(c, m)
                    break
            if c.closed or now - c.born > HELLO_TIMEOUT:
                if c not in self.conns.values():
                    c.close()
            if c.closed or c in self.conns.values():
                self.pending.remove(c)
        for pc, c in list(self.conns.items()):
            for m in c.read():
                self._message(pc, m)
            if c.closed or now - c.heard > SILENCE * 2:
                c.close()
                self.conns.pop(pc, None)
                self.drop_pc(pc)
        self._answer_finders()
        if now - self._ping_t > PING_EVERY:
            self._ping_t = now
            self.broadcast({"t": "ping"})

    def _hello(self, c, m):
        if m.get("v") != VERSION:
            c.send({"t": "deny", "why": "version", "v": VERSION})
            c.close()
            return
        host = str(m.get("host", ""))[:40]
        name = clean_name(m.get("name", "")) or "Ομάδα"
        # ξαναμπαίνει ένας υπολογιστής που είχε οικόπεδο (ίδιο όνομα υπολογιστή): παίρνει πίσω το οικόπεδό του
        back = next((p for p in self.pcs.values() if not p["on"] and host and p["host"] == host), None)
        if back:
            pc = back["pc"]
            back["on"] = True
            back["name"] = name
            self.conns[pc] = c
            c.send({"t": "welcome", "pc": pc, "title": self.title})
            k = self.plot_of(pc)
            if k and self.forest:
                self.forest.set_auto(k, False)
            self._rec_sent.pop(k, None)
            self._send_level(pc)
            return
        if len([p for p in self.pcs.values() if p["on"]]) >= MAX_SEATS:
            c.send({"t": "deny", "why": "full"})
            c.close()
            return
        pc = self._next_pc
        self._next_pc += 1
        self.conns[pc] = c
        c.send({"t": "welcome", "pc": pc, "title": self.title})
        self.add_pc(pc, name, host)
        if self.state == "level":
            self.send(pc, {"t": "lobby", "title": self.title, "n": len(self.pcs), "late": True})

    def _message(self, pc, m):
        t = m.get("t")
        if t == "act":
            self.act(pc, m.get("a"))
        elif t == "prog":
            self.set_program(pc, m.get("p"), m.get("ready"))
        elif t == "reset":
            k = self.plot_of(pc)
            if k and not self.paused and not self.frozen:
                self.reset_plot(k)
        elif t == "bye":
            c = self.conns.pop(pc, None)
            if c:
                c.close()
            self.drop_pc(pc)

    def _answer_finders(self):
        if self.beacon is None:
            return
        import json
        while True:
            try:
                data, addr = self.beacon.recvfrom(4096)
            except (BlockingIOError, InterruptedError, OSError):
                break
            try:
                m = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(m, dict) and m.get("t") == "find":
                try:
                    self.beacon.sendto(_encode(self.info()), addr)
                except OSError:
                    pass

    def tick(self, dt):
        self.poll()
        super().tick(dt)

    def close(self):
        if self.closed:
            return
        self.broadcast({"t": "bye"})
        for c in list(self.conns.values()) + self.pending:
            c.flush()
            c.close()
        self.conns, self.pending = {}, []
        for s in (self.server, self.beacon):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self.closed = True


# ================================================================ ο υπολογιστής των μαθητών
class StudentState:
    """Ό,τι ξέρει ο υπολογιστής των μαθητών για το μάθημα (το διαβάζει η οθόνη)."""

    def _reset_state(self):
        self.state = "connecting"     # connecting, hello, lobby, level, closed
        self.error = None
        self.pc = None
        self.title = ""
        self.late = False
        self.data = None
        self.forest = None
        self.k = None
        self.names = {}
        self.level_no = 0
        self.frozen = False
        self.done = None              # (σώθηκαν, ζώα, φωτιές) όταν τελειώσει η πίστα
        self.rec = []
        self.helps = deque()          # βοήθεια από τον δάσκαλο, για την οθόνη
        self.events = deque()         # ό,τι έγινε στο δάσος (χτυπήματα, πέτρες, ζώα...)
        self.lobby_n = 0
        self.mode = "drive"
        self.phase = None
        self.round = 0
        self.left = 0.0
        self.timed = True
        self.paused = False
        self.start_prog = []
        self.results = None
        self.class_ok = None
        self.allready_at = None
        self._phase_clock = time.monotonic()

    def _handle(self, m):
        t = m.get("t")
        if t == "welcome":
            self.pc = m.get("pc")
            self.title = m.get("title", "")
            self.state = "lobby"
        elif t == "deny":
            why = m.get("why")
            if why == "version":
                self._fail(f"Ο υπολογιστής του δασκάλου έχει άλλη έκδοση ({m.get('v')}, εδώ {VERSION}). "
                           "Βάλτε την ίδια έκδοση σε όλους τους υπολογιστές.")
            else:
                self._fail("Το μάθημα είναι γεμάτο.")
        elif t == "lobby":
            self.state = "lobby"
            self.title = m.get("title", self.title)
            self.lobby_n = m.get("n", 0)
            self.late = bool(m.get("late"))
            self.data = None
            self.forest = None
        elif t == "level":
            self.data = m.get("data")
            self.forest = S.Forest(self.data)
            self.k = m.get("k")
            self.names = {int(k): v for k, v in (m.get("names") or {}).items()}
            self.level_no = m.get("no", 0)
            self.frozen = bool(m.get("frozen"))
            self.done = None
            self.rec = []
            self.late = False
            self.events.clear()
            self.mode = m.get("mode", "drive")
            self.start_prog = m.get("prog") or []
            self.round = m.get("round", 0)
            self.phase = m.get("phase")
            self.left = float(m.get("left") or 0)
            self.timed = bool(m.get("timed", True))
            self.paused = bool(m.get("paused"))
            res = m.get("res") or {}
            self.results = {int(k): v for k, v in res.items()} or None
            self.class_ok = None
            self._phase_clock = time.monotonic()
            self.state = "level" if self.k else "lobby"
            self.helps.append(("level", None))
        elif t == "snap":
            if self.forest is not None:
                for e in self.forest.apply(m.get("s") or {}):
                    self.events.append(e)
        elif t == "rec":
            self.rec = m.get("p") or []
        elif t == "phase":
            self.phase = m.get("phase")
            self.round = m.get("round", self.round)
            self.left = float(m.get("left", 0))
            self.paused = bool(m.get("paused"))
            self._phase_clock = time.monotonic()
            if self.phase == "plan":
                self.allready_at = None
                self.results = None if m.get("round", 1) == 1 else self.results
            self.helps.append(("phase", self.phase))
        elif t == "result":
            self.results = {int(k): v for k, v in (m.get("res") or {}).items()}
            self.class_ok = bool(m.get("ok"))
            self.last_counts = (m.get("saved", 0), m.get("animals", 0), m.get("out", 0), m.get("fires", 0))
        elif t == "allready":
            self.allready_at = time.monotonic() + float(m.get("in", 0))
        elif t == "done":
            self.done = (m.get("saved", 0), m.get("animals", 0), m.get("fires", 0))
        elif t == "help":
            self.helps.append((m.get("kind"), m.get("data")))
        elif t == "freeze":
            self.frozen = bool(m.get("on"))
        elif t == "bye":
            self._fail("Ο δάσκαλος έκλεισε το μάθημα.")

    def _fail(self, text):
        self.state = "closed"
        if self.error is None:
            self.error = text

    def time_left(self):
        """Ο χρόνος σχεδιασμού που μένει (μετρά και τοπικά ανάμεσα στα μηνύματα)."""
        if self.phase != "plan" or self.paused or not self.timed or self.frozen:
            return self.left
        return max(0.0, self.left - (time.monotonic() - self._phase_clock))


class Client(StudentState):
    role = "client"

    def __init__(self, name, addr, port):
        self._reset_state()
        self.name_typed = clean_name(name) or "Ομάδα"
        self.addr, self.port = addr, port
        self.conn = None
        self._t0 = time.monotonic()
        self._ping_t = 0.0
        self._prog_t = 0.0
        self._sent = None
        self._pending_prog = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        try:
            self.sock.connect_ex((addr, port))
        except OSError:
            self._fail("Δεν βρέθηκε ο υπολογιστής του δασκάλου.")

    def _fail(self, text):
        super()._fail(text)
        if getattr(self, "conn", None):
            self.conn.close()
        else:
            try:
                self.sock.close()
            except (OSError, AttributeError):
                pass

    def poll(self):
        import select
        if self.state == "closed":
            return
        now = time.monotonic()
        if self.state == "connecting":
            try:
                _, w, x = select.select([], [self.sock], [self.sock], 0)
            except (OSError, ValueError):
                self._fail("Δεν βρέθηκε ο υπολογιστής του δασκάλου.")
                return
            if w or x:
                err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err or x:
                    self._fail("Δεν βρέθηκε ο υπολογιστής του δασκάλου.")
                    return
                self.conn = Conn(self.sock)
                self.conn.send({"t": "hello", "v": VERSION, "name": self.name_typed, "host": socket.gethostname()})
                self.state = "hello"
            elif now - self._t0 > CONNECT_TIMEOUT:
                self._fail("Δεν βρέθηκε ο υπολογιστής του δασκάλου.")
            return
        for m in self.conn.read():
            self._handle(m)
        if self.state == "closed":
            return
        if self.conn.closed or now - self.conn.heard > SILENCE * 2:
            self._fail("Χάθηκε η σύνδεση με τον δάσκαλο.")
            return
        if self._pending_prog is not None and now - self._prog_t >= PROG_EVERY:
            self._prog_t = now
            self.conn.send(self._pending_prog)
            self._sent, self._pending_prog = self._pending_prog, None
        # «είμαι εδώ»: αλλιώς, όταν τα παιδιά δεν πατούν τίποτα για λίγο, ο δάσκαλος κλείνει τη σύνδεση
        if now - self._ping_t >= PING_EVERY:
            self._ping_t = now
            self.conn.send({"t": "ping"})

    def tick(self, dt):
        self.poll()

    def _handle(self, m):
        super()._handle(m)
        if m.get("t") in ("level", "phase") and self.phase == "plan":
            self._sent = None         # νέος γύρος: ο δάσκαλος ξεκινά πάλι από «όχι έτοιμοι»

    def send_program(self, prog, ready):
        msg = {"t": "prog", "p": prog, "ready": bool(ready)}
        if msg != self._sent:
            self._pending_prog = msg

    def act(self, action):
        if self.conn and not self.conn.closed:
            self.conn.send({"t": "act", "a": action})

    def reset(self):
        if self.conn and not self.conn.closed:
            self.conn.send({"t": "reset"})

    def close(self):
        if self.conn and not self.conn.closed:
            if self._pending_prog:
                self.conn.send(self._pending_prog)
            self.conn.send({"t": "bye"})
            self.conn.flush()
            self.conn.close()
        elif self.conn is None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.state = "closed"


# ================================================================ εξάσκηση σε έναν υπολογιστή
class _PracticeLesson(Lesson):
    def __init__(self, link):
        super().__init__("ΕΞΑΣΚΗΣΗ")
        self.link = link

    def send(self, pc, msg):
        if pc == 1:
            self.link._handle(msg)

    def broadcast(self, msg):
        self.link._handle(msg)


class Practice(StudentState):
    """Η «Εξάσκηση»: ένα μάθημα μέσα στον ίδιο υπολογιστή. Τα παιδιά παίρνουν ένα οικόπεδο και τα άλλα
    έχουν αυτόματα R2, σαν να παίζουν με την τάξη."""
    role = "practice"
    PLOTS = 4
    ME = 2

    def __init__(self, name):
        self._reset_state()
        self.name_typed = clean_name(name) or "Ομάδα"
        self.lesson = _PracticeLesson(self)
        self.state = "lobby"
        self.pc = 1
        self.level_id = None

    def start(self, level_id):
        L = self.lesson
        L.pcs = {}
        L.add_pc(1, self.name_typed, "local")
        L.pcs[1]["seat"] = self.ME - 1
        L.bots = self.PLOTS - 1
        self.level_id = str(level_id)
        L.level_no += 1
        L.data = W.build(level_id, self.PLOTS, L.level_no)
        L.level_id = str(level_id)
        L.forest = S.Forest(L.data)
        L.assign = {k: (1 if k == self.ME else None) for k in range(1, self.PLOTS + 1)}
        for k, pc in L.assign.items():
            if pc is None:
                L.forest.set_auto(k, True)
        L.state = "level"
        L.paused = False
        L.done_sent = False
        L._snap_ver = -1
        L._sent_event = 0
        L._rec_sent = {}
        L.mode = L.data.get("mode", "drive")
        L.plan_seconds = 0
        L.results, L.history, L._tests = {}, {k: [] for k in L.assign}, {}
        L.class_ok = False
        if L.mode != "drive":
            L.programs = {k: [dict(n) for n in (p.get("given") or [])] for k, p in L.forest.plots.items()}
            L.edited = {k: L.clock for k in L.assign}
            L.round = 1
            L._plan(send=False)
        else:
            L.phase = None
        L._send_level(1)

    def poll(self):
        pass

    def tick(self, dt):
        self.lesson.tick(dt)

    def act(self, action):
        self.lesson.act(1, action)

    def send_program(self, prog, ready):
        self.lesson.set_program(1, prog, ready)

    def reset(self):
        k = self.lesson.plot_of(1)
        if k:
            self.lesson.reset_plot(k)

    def close(self):
        self.state = "closed"
