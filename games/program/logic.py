"""Οι κανόνες του «Προγραμμάτισε», χωρίς γραφικά, ώστε να ελέγχονται εύκολα.

Ο κόσμος είναι ένα νησάκι από κουτάκια (δες το levels.py για τους χαρακτήρες του χάρτη).
Το R2 στέκεται σε ένα κουτάκι και κοιτάει προς μία από τις 4 κατευθύνσεις.
Όπως στον Λαβύρινθο, 1 δευτερόλεπτο = 1 κουτάκι ή ¼ στροφής:
    «Κινήσου μπροστά … για 3 δευτερόλεπτα»   3 κουτάκια μπροστά
    «Στρίψε δεξιά για 2 δευτερόλεπτα»         μισή στροφή επί τόπου

Το πρόγραμμα είναι λίστα από μπλοκ (λεξικά με "op"). Τα «C» μπλοκ έχουν μέσα τους λίστες:
    {"op": "move", "dir": "forward"|"back", "n": 3}      Κινήσου … για n δευτερόλεπτα
    {"op": "turn", "dir": "right"|"left", "n": 1}        Στρίψε … για n δευτερόλεπτα
    {"op": "go", "dir": "forward"|"back"}                Κινήσου … με ταχύτητα μικρή (χωρίς τέλος)
    {"op": "stop"}                                       Σταμάτησε
    {"op": "line", "mode": "on"|"off"}                   Ακολούθησε τη μαύρη γραμμή [Ενεργοποίηση]
    {"op": "key", "key": "up_arrow", "body": [...]}      όταν πατηθεί πλήκτρο [πάνω βέλος] (καπέλο: τρέχει το
                                                         πρόγραμμα από κάτω του όταν πατηθεί το βελάκι)
    {"op": "led", "color": "red"}                        Neopixel Led … με χρώμα ●
    {"op": "wait", "n": 1}                               περίμενε n δευτερόλεπτα
    {"op": "until", "cm": 15}                            περίμενε ώσπου ‹Διάβασε απόσταση (cm) < 15›
    {"op": "repeat", "n": 4, "body": [...]}              επανάλαβε n
    {"op": "forever", "body": [...]}                     για πάντα
    {"op": "if", "cm": 15, "then": [...], "else": [...]} εάν ‹απόσταση < cm› τότε … αλλιώς …
Η θέση ενός μπλοκ (path) είναι πλειάδα: (3,) το 4ο μπλοκ, (0, 0, 1) το 2ο μπλοκ μέσα στο
1ο στόμα του 1ου μπλοκ. Στο «εάν» το στόμα 0 είναι το «τότε» και το 1 το «αλλιώς».
"""
import copy
from collections import namedtuple

UP, RIGHT, DOWN, LEFT = range(4)
STEP = {UP: (0, -1), RIGHT: (1, 0), DOWN: (0, 1), LEFT: (-1, 0)}
FACES = {"up": UP, "right": RIGHT, "down": DOWN, "left": LEFT}
COLORS = ("red", "green", "blue", "yellow")
DOORS = {"R": "red", "B": "blue", "Y": "yellow", "P": "green"}
GROUND = ".SGc=s"                 # πατήματα (χορτάρι, αρχή, φορτιστής, κρύσταλλος, γέφυρα, άμμος)
MAP_CHARS = GROUND + "#T~" + "".join(DOORS)
CM_PER_TILE = 20                  # κάθε κουτάκι είναι 20 cm
NEAR_CM = 10                      # εμπόδιο στο διπλανό κουτάκι: 10 cm
FAR_CM = 300                      # ο αισθητήρας δεν βλέπει τίποτα μπροστά
CM_CHOICES = (10, 15, 20, 25, 30, 35, 40, 45, 50)
MAX_TIME = 90                     # δευτερόλεπτα: μετά το R2 σταματά (πρόγραμμα χωρίς τέλος)
MAX_WAIT = 30                     # πόσο περιμένει το «περίμενε ώσπου»
C_OPS = ("repeat", "forever", "if")
KEYS = ("up_arrow", "down_arrow", "right_arrow", "left_arrow")       # τα βελάκια, με τη σειρά του Mind+
LIMIT_BLOCKS = 40                 # πόσα μπλοκ χωράει ένα πρόγραμμα


def neighbor(cell, d):
    return cell[0] + STEP[d][0], cell[1] + STEP[d][1]


# ================================================================ ο κόσμος
class World:
    """Ένας χάρτης. text: γραμμές με χαρακτήρες χωρισμένους με κενά. bug: η διαδρομή της πασχαλίτσας.
    sink: (πάνω, κάτω) ή (πάνω, κάτω, ήδη): οι γέφυρες «=» μένουν τόσα δευτερόλεπτα πάνω από το νερό και τόσα
    κάτω, ξανά και ξανά· «ήδη»: πόσα δευτερόλεπτα του κύκλου έχουν περάσει στο «Πάμε» (0: μόλις ανέβηκαν).
    mover: η διαδρομή ενός μεγάλου αντικειμένου (εργαλειοθήκη): προχωρά 1 κουτάκι το δευτερόλεπτο και μένει
    στο τελευταίο. Είναι εμπόδιο και το βλέπει ο αισθητήρας.
    line: τα κουτάκια μιας μαύρης γραμμής, με τη σειρά από την αρχή ως το τέλος της, για το
    «Ακολούθησε τη μαύρη γραμμή».
    drive: πατήματα πλήκτρων (για το τηλεκοντρόλ): με αυτά τα δοκιμάζουν οι έλεγχοι, χωρίς πληκτρολόγιο."""

    def __init__(self, text, face="right", bug=None, sink=None, mover=None, line=None, drive=None):
        rows = [ln.split() for ln in text.strip("\n").splitlines() if ln.strip()]
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("ο χάρτης πρέπει να είναι ορθογώνιος")
        self.cols, self.rows = len(rows[0]), len(rows)
        self.cells = {(x, y): ch for y, row in enumerate(rows) for x, ch in enumerate(row)}
        bad = {ch for ch in self.cells.values() if len(ch) != 1 or ch not in MAP_CHARS}
        if bad:
            raise ValueError(f"άγνωστοι χαρακτήρες: {bad}")
        starts = [c for c, ch in self.cells.items() if ch == "S"]
        goals = [c for c, ch in self.cells.items() if ch == "G"]
        if len(starts) != 1 or len(goals) != 1:
            raise ValueError("θέλει ένα S (αρχή) και ένα G (φορτιστή)")
        self.start, self.goal = starts[0], goals[0]
        self.crystals = frozenset(c for c, ch in self.cells.items() if ch == "c")
        self.face = FACES[face]
        self.bug = [tuple(c) for c in bug] if bug else None
        self.sink = tuple(sink) if sink else None
        self.mover = [tuple(c) for c in mover] if mover else None
        self.line = [tuple(c) for c in line] if line else None
        self.line_index = {c: i for i, c in enumerate(self.line)} if self.line else {}
        self.drive = list(drive) if drive else []

    def at(self, cell):
        return self.cells.get(cell)

    def bug_at(self, t):
        """Πού είναι η πασχαλίτσα τη στιγμή t (πηγαινοέρχεται, 1 κουτάκι το δευτερόλεπτο)."""
        if not self.bug:
            return None
        n = len(self.bug)
        if n == 1:
            return self.bug[0]
        k = t % (2 * n - 2)
        return self.bug[k if k < n else 2 * n - 2 - k]

    def mover_at(self, t):
        """Πού είναι το αντικείμενο που κινείται τη στιγμή t (ή None)."""
        if not self.mover:
            return None
        return self.mover[max(0, min(t, len(self.mover) - 1))]

    def bridges_up(self, t):
        """Είναι πάνω οι γέφυρες τη στιγμή t (ακέραια δευτερόλεπτα από το «Πάμε»);"""
        if not self.sink:
            return True
        up, down, already = (tuple(self.sink) + (0,))[:3]
        return (t + already) % (up + down) < up

    def bridge_up(self, cell, t):
        """Πατιέται η γέφυρα τη στιγμή t; (όλα τα άλλα κουτάκια: ναι)"""
        return self.cells.get(cell) != "=" or self.bridges_up(t)

    def blocked(self, cell, led):
        """Γιατί δεν μπορεί να μπει στο κουτάκι (χωρίς την πασχαλίτσα), ή None αν μπορεί."""
        ch = self.at(cell)
        if ch is None:
            return "edge"
        if ch == "#":
            return "stone"
        if ch == "T":
            return "tree"
        if ch == "~":
            return "water"
        if ch in DOORS and DOORS[ch] != led:
            return "door"
        return None

    def distance(self, cell, d, led, t=0):
        """Τι μετρά ο αισθητήρας απόστασης (cm). Βλέπει πέτρες, δέντρα, κλειστές πόρτες, την πασχαλίτσα.
        Το νερό και ο γκρεμός δεν είναι εμπόδια για τον υπέρηχο: περνά από πάνω τους."""
        free = 0
        bug, box = self.bug_at(t), self.mover_at(t)
        c = neighbor(cell, d)
        while self.at(c) is not None:
            if self.blocked(c, led) in ("stone", "tree", "door") or c in (bug, box):
                return NEAR_CM + CM_PER_TILE * free
            free += 1
            c = neighbor(c, d)
        return FAR_CM


# ============================================================ το πρόγραμμα
def move(d="forward", n=1):
    return {"op": "move", "dir": d, "n": n}


def turn(d="right", n=1):
    return {"op": "turn", "dir": d, "n": n}


def go(d="forward"):
    return {"op": "go", "dir": d}


def stop():
    return {"op": "stop"}


def key(k="up_arrow", *body):
    """«όταν πατηθεί πλήκτρο [k]» με το πρόγραμμά του από κάτω."""
    return {"op": "key", "key": k, "body": list(body)}


def scripts(program):
    """Είναι πρόγραμμα με «όταν πατηθεί πλήκτρο» (τηλεκοντρόλ);"""
    return any(node["op"] == "key" for node in program)


def follow(mode="on"):
    """«Ακολούθησε τη μαύρη γραμμή [Ενεργοποίηση / Απενεργοποίηση]»"""
    return {"op": "line", "mode": mode}


def led(color="red"):
    return {"op": "led", "color": color}


def wait(n=1):
    return {"op": "wait", "n": n}


def until(cm=15):
    return {"op": "until", "cm": cm}


def repeat(n=10, *body):
    return {"op": "repeat", "n": n, "body": list(body)}


def forever(*body):
    return {"op": "forever", "body": list(body)}


def if_else(cm=15, then=(), other=()):
    return {"op": "if", "cm": cm, "then": list(then), "else": list(other)}


def mouths(node):
    """Οι λίστες μέσα σε ένα «C» μπλοκ, με τη σειρά (0, 1)."""
    op = node["op"]
    if op in ("repeat", "forever", "key"):
        return [node["body"]]
    if op == "if":
        return [node["then"], node["else"]]
    return []


def count(prog):
    """Πόσα μπλοκ έχει το πρόγραμμα (μαζί με όσα είναι μέσα σε άλλα)."""
    return sum(1 + sum(count(m) for m in mouths(node)) for node in prog)


def ops(prog):
    """Τα είδη των μπλοκ που χρησιμοποιεί το πρόγραμμα."""
    out = set()
    for node in prog:
        out.add(node["op"])
        for m in mouths(node):
            out |= ops(m)
    return out


def walk(prog, path=()):
    """Όλα τα μπλοκ με τη θέση τους, από πάνω προς τα κάτω."""
    for i, node in enumerate(prog):
        p = path + (i,)
        yield p, node
        for b, m in enumerate(mouths(node)):
            yield from walk(m, p + (b,))


def get(prog, path):
    node = prog[path[0]]
    for k in range(1, len(path), 2):
        node = mouths(node)[path[k]][path[k + 1]]
    return node


def list_at(prog, where):
    """where: () για το κυρίως πρόγραμμα, ή (θέση μπλοκ…, στόμα) για τη λίστα ενός στόματος."""
    if not where:
        return prog
    return mouths(get(prog, where[:-1]))[where[-1]]


def ends_with_cap(chunk):
    return bool(chunk) and chunk[-1]["op"] == "forever"


def can_insert(prog, where, index, chunk, scripts=False):
    """Ένα κομμάτι μπαίνει εκεί; Κάτω από το «για πάντα» δεν κουμπώνει τίποτα (όπως στο Mind+).
    Το «όταν πατηθεί πλήκτρο» μπαίνει μόνο ως νέο πρόγραμμα (όχι μέσα σε άλλο). scripts=True (τηλεκοντρόλ):
    ο χώρος έχει μόνο τέτοια προγράμματα, άρα οι άλλες εντολές μπαίνουν μόνο κάτω από ένα «όταν πατηθεί»."""
    lst = list_at(prog, where)
    if not 0 <= index <= len(lst):
        return False
    hats = [node["op"] == "key" for node in chunk]
    if any(hats) and (where != () or not all(hats)):
        return False
    if scripts and where == () and not all(hats):
        return False
    if index > 0 and lst[index - 1]["op"] == "forever":
        return False
    if ends_with_cap(chunk) and index < len(lst):
        return False
    return count(prog) + count(chunk) <= LIMIT_BLOCKS


def insert(prog, where, index, chunk):
    if not can_insert(prog, where, index, chunk):
        return False
    list_at(prog, where)[index:index] = chunk
    return True


def take(prog, path):
    """Βγάζει το μπλοκ και όσα είναι από κάτω του στην ίδια λίστα (όπως όταν το σέρνεις στο Mind+)."""
    lst = list_at(prog, path[:-1])
    chunk = lst[path[-1]:]
    del lst[path[-1]:]
    return chunk


def append_spot(prog):
    """Πού μπαίνει ένα μπλοκ με κλικ στις Εντολές: στο τέλος (ή μέσα στο «για πάντα», αν τελειώνει έτσι)."""
    where = ()
    while True:
        lst = list_at(prog, where)
        if lst and lst[-1]["op"] in ("forever", "key"):
            where = where + (len(lst) - 1, 0)
            continue
        return where, len(lst)


# τα πεδία που αλλάζει το παιδί, με τη σειρά που φαίνονται στο μπλοκ (▾, οβάλ, χρώμα).
# None: φαίνεται όπως στο Mind+ αλλά δεν αλλάζει (ταχύτητα «μικρή», pin D12, «Όλα», φωτεινότητα 50).
FIELDS = {
    "move": ("dir", None, "n"),
    "turn": ("dir", "n"),
    "go": ("dir", None),
    "stop": (),
    "line": ("mode",),
    "key": ("key",),
    "led": (None, None, "color", None),
    "wait": ("n",),
    "until": ("cm",),
    "repeat": ("n",),
    "forever": (),
    "if": ("cm",),
}


def choices(node, field):
    """Οι επιλογές ενός πεδίου."""
    op = node["op"]
    if field == "mode":
        return ("on", "off")
    if field == "key":
        return KEYS
    if field == "dir":
        return ("right", "left") if op == "turn" else ("forward", "back")
    if field == "color":
        return COLORS
    if field == "cm":
        return CM_CHOICES
    if op == "repeat":
        return tuple(range(1, 11))
    return tuple(range(1, 10))


# ============================================================== η εκτέλεση
Event = namedtuple("Event", "kind path a b t", defaults=(None, None, 0))
"""Τι έγινε σε ένα βήμα της εκτέλεσης:
    block  ξεκινά το μπλοκ path                       loop   a-οστή φορά από b (b=0: για πάντα)
    move   από a σε b (1 δευτερόλεπτο)                branch a = 0 «τότε», 1 «αλλιώς»
    turn   από την κατεύθυνση a στη b (1 δευτ.)       led    a = το νέο χρώμα
    wait   το R2 περιμένει (1 δευτ.)                  crystal a = το κουτάκι του κρυστάλλου
    dock   έφτασε στον φορτιστή (τέλος, μπράβο)
    fail   a = γιατί: stone, tree, water, edge, door, bug, end, time, stuck. b = το κουτάκι
t: πότε (σε δευτερόλεπτα από την αρχή)."""


class _Done(Exception):
    pass


class Run:
    """Μία εκτέλεση ενός προγράμματος σε έναν χάρτη."""

    def __init__(self, world):
        self.world = world
        self.pos = world.start
        self.facing = world.face
        self.led = None
        self.moving = None            # "forward"/"back": «Κινήσου … με ταχύτητα μικρή» χωρίς τέλος
        self.t = 0
        self.taken = set()
        self.docked = False
        self.failure = None           # (path, γιατί)
        self._idle = 0
        self.max_time = MAX_TIME      # το τηλεκοντρόλ το μεγαλώνει (το παιδί οδηγεί όσο θέλει)

    def events(self, program):
        """Εκτελεί το πρόγραμμα και δίνει τα γεγονότα ένα ένα (γεννήτρια). Το τηλεκοντρόλ (προγράμματα
        «όταν πατηθεί πλήκτρο») τρέχει με τα πατήματα του χάρτη (world.drive): έτσι το ελέγχουν τα tests."""
        try:
            if scripts(program):
                for k in self.world.drive:
                    yield from self._scripts(program, k)
                yield from self._fail(None, "end", self.pos)
            yield from self._list(program, ())
            while self.moving:        # τελείωσε το πρόγραμμα, αλλά τα μοτέρ γυρίζουν ακόμα
                yield from self._tick(None)
            yield from self._fail(None, "end", self.pos)
        except _Done:
            return

    def press(self, program, k):
        """Πατήθηκε το βελάκι k: τρέχουν τα προγράμματα «όταν πατηθεί πλήκτρο [k]» (γεννήτρια).
        Τελειώνει όταν τελειώσουν, ή όταν το R2 φτάσει στον φορτιστή ή κάνει λάθος."""
        try:
            yield from self._scripts(program, k)
        except _Done:
            return

    def _scripts(self, program, k):
        for i, node in enumerate(program):
            if node["op"] == "key" and node["key"] == k:
                yield Event("block", (i,), t=self.t)
                yield from self._list(node["body"], (i, 0))
        self.moving = None

    def play(self, program):
        """Εκτελεί όλο το πρόγραμμα. Επιστρέφει τη λίστα με τα γεγονότα."""
        return list(self.events(program))

    def do(self, node):
        """Εκτελεί ένα μόνο μπλοκ, από εκεί που είναι τώρα το R2 (για τον λύτη των ελέγχων)."""
        out = []
        try:
            for e in self._node(node, (0,)):
                out.append(e)
        except _Done:
            pass
        return out

    # ---------------------------------------------------------------- μπλοκ
    def _list(self, nodes, path):
        for i, node in enumerate(nodes):
            yield from self._node(node, path + (i,))

    def _node(self, node, p):
        op = node["op"]
        yield Event("block", p, t=self.t)
        if op == "move":
            for _ in range(node["n"]):
                d = self.facing if node["dir"] == "forward" else (self.facing + 2) % 4
                yield from self._step(p, d)
            self.moving = None
        elif op == "turn":
            for _ in range(node["n"]):
                yield from self._turn(p, 1 if node["dir"] == "right" else -1)
            self.moving = None
        elif op == "go":
            self.moving = node["dir"]
        elif op == "stop":
            self.moving = None
        elif op == "key":                     # «όταν πατηθεί πλήκτρο»: τρέχει μόνο με το πάτημα (press)
            pass
        elif op == "line":                    # ακολουθεί τη γραμμή όσο περνά ο χρόνος (όπως το «Κινήσου» χωρίς τέλος)
            if node["mode"] == "on":
                self.moving = "line"
            elif self.moving == "line":
                self.moving = None
        elif op == "led":
            self.led = node["color"]
            yield Event("led", p, node["color"], t=self.t)
        elif op == "wait":
            for _ in range(node["n"]):
                yield from self._tick(p)
        elif op == "until":
            waited = 0
            while not self.sees(node["cm"]):
                if waited >= MAX_WAIT:
                    yield from self._fail(p, "time", self.pos)
                yield from self._tick(p)
                waited += 1
        elif op == "repeat":
            for k in range(node["n"]):
                yield Event("loop", p, k + 1, node["n"], self.t)
                yield from self._list(node["body"], p + (0,))
        elif op == "forever":
            k = 0
            while True:
                k += 1
                yield Event("loop", p, k, 0, self.t)
                before = self.t
                yield from self._list(node["body"], p + (0,))
                self._idle = self._idle + 1 if self.t == before else 0
                if self._idle > 50:
                    yield from self._fail(p, "stuck", self.pos)
        elif op == "if":
            branch = 0 if self.sees(node["cm"]) else 1
            yield Event("branch", p, branch, t=self.t)
            yield from self._list(mouths(node)[branch], p + (branch,))
        else:
            raise ValueError(op)

    def sees(self, cm):
        """«Διάβασε απόσταση (cm) < cm»"""
        return self.world.distance(self.pos, self.facing, self.led, self.t) < cm

    # ------------------------------------------------------- ένα δευτερόλεπτο
    def _clock(self, p):
        if self.t >= self.max_time:
            yield from self._fail(p, "time", self.pos)

    def _bug_hits(self, a, b):
        """Ακουμπά την πασχαλίτσα, αν το R2 πάει από a σε b σε αυτό το δευτερόλεπτο;
        Δεν μπαίνει εκεί που είναι ή πάει η πασχαλίτσα, ούτε τη βρίσκει από πίσω του."""
        w = self.world
        if not w.bug:
            return False
        p0, p1 = w.bug_at(self.t), w.bug_at(self.t + 1)
        return b in (p0, p1) or p1 == a

    def _box_hits(self, a, b):
        """Πέφτει πάνω στο αντικείμενο που κινείται, αν το R2 πάει από a σε b σε αυτό το δευτερόλεπτο;
        Εκεί που θα είναι σε 1 δευτερόλεπτο δεν μπαίνει, ούτε το αφήνει να έρθει πάνω του·
        στο κουτάκι που μόλις αφήνει μπορεί να μπει (το ακολουθεί)."""
        w = self.world
        if not w.mover:
            return False
        m1 = w.mover_at(self.t + 1)
        return b == m1 or m1 == a

    def _step(self, p, d):
        yield from self._clock(p)
        a, b = self.pos, neighbor(self.pos, d)
        why = self.world.blocked(b, self.led)
        if why:
            yield from self._fail(p, why, b)
        if self._bug_hits(a, b):
            yield from self._fail(p, "bug", b)
        if self._box_hits(a, b):
            yield from self._fail(p, "box", b)
        if not self.world.bridge_up(b, self.t + 1):     # φτάνει εκεί σε 1 δευτερόλεπτο: έχει βουλιάξει
            yield from self._fail(p, "bridge", b)
        self.pos = b
        yield Event("move", p, a, b, self.t)
        self.t += 1
        if b in self.world.crystals and b not in self.taken:
            self.taken.add(b)
            yield Event("crystal", p, b, t=self.t)
        if b == self.world.goal:
            self.docked = True
            self.moving = None
            yield Event("dock", p, b, t=self.t)
            raise _Done

    def _turn(self, p, way):
        yield from self._clock(p)
        if self._bug_hits(self.pos, self.pos):
            yield from self._fail(p, "bug", self.pos)
        if self._box_hits(self.pos, self.pos):
            yield from self._fail(p, "box", self.pos)
        if not self.world.bridge_up(self.pos, self.t + 1):  # στρίβει πάνω σε γέφυρα που βουλιάζει
            yield from self._fail(p, "bridge", self.pos)
        old = self.facing
        self.facing = (old + way) % 4
        yield Event("turn", p, old, self.facing, self.t)
        self.t += 1

    def _follow(self, p):
        """Ένα δευτερόλεπτο του «Ακολούθησε τη μαύρη γραμμή»: ένα κουτάκι πάνω στη γραμμή, ή μία στροφή
        στις γωνίες της. Στο τέλος της γραμμής τα μοτέρ σταματούν."""
        w = self.world
        i = w.line_index.get(self.pos)
        if i is None:
            yield from self._fail(p, "noline", self.pos)
        if i == len(w.line) - 1:
            self.moving = None
            yield from self._tick(p)
            return
        nxt = w.line[i + 1]
        d = next(k for k in STEP if neighbor(self.pos, k) == nxt)
        if d == self.facing:
            yield from self._step(p, d)
        else:
            yield from self._turn(p, -1 if (d - self.facing) % 4 == 3 else 1)

    def _tick(self, p):
        """Ένα δευτερόλεπτο αναμονής: αν τα μοτέρ γυρίζουν, το R2 προχωρά ένα κουτάκι."""
        if self.moving == "line":
            yield from self._follow(p)
            return
        if self.moving:
            d = self.facing if self.moving == "forward" else (self.facing + 2) % 4
            yield from self._step(p, d)
            return
        yield from self._clock(p)
        if self._bug_hits(self.pos, self.pos):
            yield from self._fail(p, "bug", self.pos)
        if self._box_hits(self.pos, self.pos):
            yield from self._fail(p, "box", self.pos)
        if not self.world.bridge_up(self.pos, self.t + 1):  # περιμένει πάνω σε γέφυρα που βουλιάζει
            yield from self._fail(p, "bridge", self.pos)
        yield Event("wait", p, t=self.t)
        self.t += 1

    def _fail(self, p, why, cell):
        self.failure = (p, why)
        self.moving = None
        yield Event("fail", p, why, cell, self.t)
        raise _Done


def level_worlds(level):
    """Οι χάρτες μιας πίστας (λεξικό του levels.py)."""
    return [World(m, level.get("face", "right"), level.get("bug"), level.get("sink"), level.get("mover"),
                  level.get("line"), level.get("drive")) for m in level["maps"]]


def check(level_worlds, program):
    """Τρέχει το πρόγραμμα σε όλους τους χάρτες. Επιστρέφει (έφτασε παντού, μάζεψε όλους τους κρυστάλλους)."""
    docked, crystals = True, True
    for world in level_worlds:
        run = Run(world)
        run.play(program)
        docked = docked and run.docked
        crystals = crystals and run.taken == world.crystals
    return docked, crystals


def blame(level_worlds, program, failed=None, solution=None):
    """Ποια εντολή θέλει διόρθωση, όταν το πρόγραμμα αποτυγχάνει. Το R2 συνήθως σταματά σε μια εντολή
    μετά το λάθος (π.χ. η λάθος στροφή φαίνεται όταν το R2 προχωρήσει στο νερό), οπότε ψάχνουμε το μπλοκ
    που, αν αλλάξει ένα πεδίο του (κατεύθυνση, αριθμός, χρώμα, cm), το πρόγραμμα πετυχαίνει σε όλους τους χάρτες.

    Αν βγαίνουν πολλά: πρώτα αυτό που δίνει τη λύση της πίστας, μετά αυτό που μαζεύει και τους κρυστάλλους,
    μετά το πιο κοντινό πριν από το μπλοκ όπου σταμάτησε το R2 (failed). Επιστρέφει (θέση, πεδίο) ή None
    (π.χ. όταν λείπει ή περισσεύει μια εντολή)."""
    order = [p for p, _ in walk(program)]
    stop_at = order.index(failed) if failed in order else len(order)
    best, best_key = None, None
    for i, (path, node) in enumerate(walk(program)):
        for field in FIELDS[node["op"]]:
            if not field:
                continue
            for value in choices(node, field):
                if value == node[field]:
                    continue
                trial = clone(program)
                get(trial, path)[field] = value
                docked, crystals = check(level_worlds, trial)
                if not docked:
                    continue
                key = (trial == solution, crystals, i <= stop_at, i if i <= stop_at else -i)
                if best_key is None or key > best_key:
                    best, best_key = (path, field), key
    return best


def clone(prog):
    return copy.deepcopy(prog)
