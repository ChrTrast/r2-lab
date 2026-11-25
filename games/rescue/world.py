"""Το δάσος των «Αποστολών Διάσωσης»: οι πίστες, τα οικόπεδα και τα ποτάμια.

- Κάθε υπολογιστής έχει ένα οικόπεδο 6x6 με χαμηλό φράχτη. Το R2 του δεν βγαίνει ποτέ από το οικόπεδο.
- Τα διπλανά οικόπεδα (διπλανές θέσεις στην αίθουσα) φτιάχνουν ένα «ποτάμι» (ομάδα) 2 έως 5 οικοπέδων,
  που ακολουθούν το ένα το άλλο σαν φιδάκι. Από το ένα οικόπεδο στο επόμενο περνούν το νερό, τα ζώα
  (από ανοίγματα στον φράχτη) και το κλαδί-τραμπάλα.
- Δύο νερά: στο ποτάμι («w») η πέτρα γίνεται πέρασμα και το νερό συνεχίζει· στο αυλάκι («c») η πέτρα
  το κλείνει και το νερό πάει από το άλλο αυλάκι.
- Το R2 σπρώχνει μόνο προς τα μπροστά και μόνο μία πέτρα. Δεν μπαίνει σε νερό, σε αυλάκι ή σε φωτιά.

build(level_id, n, seed) φτιάχνει όλο το δάσος για n υπολογιστές. Κάθε οικόπεδο ελέγχεται με τον
λύτη (solve), που βρίσκει και τις κινήσεις για το «Αυτόματο R2» και τη βοήθεια «Δρόμος».
"""
import random
from collections import deque

PLOT = 6
MIN_PCS, MAX_PCS = 2, 25
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)
ACTIONS = ("forward", "back", "left", "right")
SIDE_NAME = {UP: "up", RIGHT: "right", DOWN: "down", LEFT: "left"}
TEAM_NAMES = "ΑΒΓΔΕΖΗ"

# ------------------------------------------------------------------ πίστες
CHAPTERS = [
    {"no": 1, "title": "Χειριστήριο", "mode": "drive", "levels": ["1", "2", "3"]},
    {"no": 2, "title": "Διόρθωσε", "mode": "fix", "levels": ["4", "5", "6"]},
    {"no": 3, "title": "Γράψε", "mode": "write", "levels": ["7", "8", "9", "10"]},
    {"no": 4, "title": "Αισθητήρες", "mode": "sense", "levels": ["11", "12", "13", "14"]},
]
LEVELS = [
    dict(id="1", no=1, chapter=1, kind="cross", title="Πέρασμα για τα ζώα",
         goal="Σπρώξε την πέτρα στο ποτάμι, για να περάσουν τα ζώα!",
         about=["Οδηγούν το R2 με τα κουμπιά ή τα βελάκια, όλοι μαζί.",
                "Πέτρα στο ποτάμι = πέρασμα για τα ζώα."],
         hint="Στάσου πίσω από την πέτρα και πήγαινε μπροστά: το R2 τη σπρώχνει."),
    dict(id="2", no=2, chapter=1, kind="dam", title="Το αυλάκι",
         goal="Κλείσε το αυλάκι με την πέτρα, να πάει το νερό στη φωτιά!",
         about=["Κάθε οικόπεδο κλείνει το αυλάκι που χάνει το νερό.",
                "Το νερό περνά από οικόπεδο σε οικόπεδο ως τη φωτιά."],
         hint="Ποιο αυλάκι πάει το νερό αλλού; Σπρώξε την πέτρα μέσα του."),
    dict(id="3", no=3, chapter=1, kind="branch", title="Το κλαδί",
         goal="Κλείσε το αυλάκι και βοήθησε τον γείτονα με το κλαδί!",
         about=["Το R2 πατά το κλαδί και ανοίγει τον δρόμο του γείτονα.",
                "Μείνε πάνω στο κλαδί ώσπου να περάσει!"],
         hint="Το κλαδί σηκώνεται όσο ένα R2 πατά την κίτρινη άκρη του."),
    # ---- Διόρθωσε: έτοιμο πρόγραμμα με ένα λάθος (έναν αριθμό ή μια στροφή)
    dict(id="4", no=4, chapter=2, mode="fix", kind="cross", prog=dict(shape="line", fix=True),
         title="Διόρθωσε: το πέρασμα", goal="Ένας αριθμός είναι λάθος. Διόρθωσέ τον: η πέτρα στο ποτάμι!",
         about=["Κάθε οικόπεδο έχει έτοιμο πρόγραμμα με ένα λάθος.", "«Δοκιμή», διόρθωση, «Έτοιμοι!»."],
         hint="Μέτρα τα κουτάκια ως την πέτρα και ένα ακόμα για να τη σπρώξεις."),
    dict(id="5", no=5, chapter=2, mode="fix", kind="dam", prog=dict(shape="turn", fix=True),
         title="Διόρθωσε: το αυλάκι", goal="Βρες το λάθος: η πέτρα πρέπει να πάει στο αυλάκι!",
         about=["Δύο μπλοκ, ένα λάθος: η στροφή ή ο αριθμός;", "Όλα τα αυλάκια κλειστά = το νερό στη φωτιά."],
         hint="Προς τα πού πρέπει να κοιτάει το R2 για να σπρώξει την πέτρα;"),
    dict(id="6", no=6, chapter=2, mode="fix", kind="dam", prog=dict(shape="corner", fix=True),
         title="Διόρθωσε: με μία στροφή", goal="Ένα από τα τρία μπλοκ έχει λάθος. Βρες το!",
         about=["Τρία μπλοκ: μπροστά, στροφή, μπροστά.", "Η «Δοκιμή» δείχνει πού κάνει λάθος."],
         hint="Κοίτα πού σταματά το R2 στη «Δοκιμή»: εκεί είναι το λάθος μπλοκ."),
    # ---- Γράψε: λίγα μπλοκ
    dict(id="7", no=7, chapter=3, mode="write", kind="cross", prog=dict(shape="line"), palette=("move",),
         title="Ένα μπλοκ", goal="Γράψε το πρόγραμμα: η πέτρα στο ποτάμι!",
         about=["Το R2 κοιτάει ήδη την πέτρα: ένα «Κινήσου» φτάνει.", "Πόσα κουτάκια;"],
         hint="Ένα «Κινήσου μπροστά»: τόσα κουτάκια όσα ως την πέτρα, και ένα ακόμα."),
    dict(id="8", no=8, chapter=3, mode="write", kind="dam", prog=dict(shape="turn"), palette=("move", "turn"),
         title="Στρίψε και σπρώξε", goal="Στρίψε προς την πέτρα και σπρώξ' τη στο αυλάκι!",
         about=["Δύο μπλοκ: «Στρίψε» και «Κινήσου».", "Όλοι μαζί φέρνουν το νερό στη φωτιά."],
         hint="Πρώτα «Στρίψε» προς την πέτρα, μετά «Κινήσου μπροστά»."),
    dict(id="9", no=9, chapter=3, mode="write", kind="cross", prog=dict(shape="line", leave=True),
         palette=("move",), title="Στην άκρη για τα ζώα",
         goal="Σπρώξε την πέτρα στο ποτάμι και μετά κάνε πίσω, να περάσουν τα ζώα!",
         about=["Δύο μπλοκ: «Κινήσου μπροστά» και «Κινήσου πίσω».", "Τα ζώα περνούν μόνο αν το R2 κάνει στην άκρη."],
         hint="Μετά το σπρώξιμο: «Κινήσου πίσω 1», για να ελευθερωθεί το πέρασμα."),
    dict(id="10", no=10, chapter=3, mode="write", kind="dam", prog=dict(shape="corner"), palette=("move", "turn"),
         title="Ο δρόμος με τη στροφή", goal="Πήγαινε ως τη γραμμή της πέτρας, στρίψε και σπρώξε!",
         about=["Τρία μπλοκ: μπροστά, στροφή, μπροστά.", "Η «Δοκιμή» βοηθά να βρείτε τους αριθμούς."],
         hint="Μέτρα πόσα κουτάκια ως τη γραμμή της πέτρας. Μετά στρίψε προς αυτήν."),
    # ---- Αισθητήρες: απόσταση (οι μπάρες) και γραμμή, ως 3 μπλοκ
    dict(id="11", no=11, chapter=4, mode="fix", pill="sense", kind="bars", prog=dict(sense=True, fix=True),
         title="Διόρθωσε: η μπάρα", goal="Κάτι είναι λάθος! Περίμενε να ανοίξει η μπάρα και πάτα το πεντάλ.",
         about=["Ο αισθητήρας απόστασης βλέπει τη μπάρα.", "Ανοίγει όταν ο γείτονας πατήσει το πεντάλ."],
         hint="Κλειστή μπάρα: 10 cm. Ανοιχτή: πολύ πιο μακριά. «περίμενε ώσπου απόσταση > 20»."),
    dict(id="12", no=12, chapter=4, mode="write", pill="sense", kind="bars", prog=dict(sense=True, turn=True),
         palette=("turn", "until", "move"), title="Περίμενε τη μπάρα",
         goal="Στρίψε προς τη μπάρα, περίμενε να ανοίξει και πήγαινε στο πεντάλ!",
         about=["Στρίψε, περίμενε ώσπου, Κινήσου: τρία μπλοκ.", "Η μία μπάρα ανοίγει την άλλη ως το νερό."],
         hint="Ο αισθητήρας κοιτάει μπροστά: πρώτα στρίψε προς τη μπάρα και μετά «περίμενε ώσπου»."),
    dict(id="13", no=13, chapter=4, mode="write", pill="sense", kind="cross", prog=dict(line=True),
         palette=("move", "turn", "line"), title="Η μαύρη γραμμή",
         goal="Πήγαινε στη μαύρη γραμμή και άφησε το R2 να την ακολουθήσει ως την πέτρα!",
         about=["Αισθητήρας γραμμής: ένα μπλοκ, όλες οι στροφές.", "Στο τέλος της γραμμής σπρώχνει την πέτρα."],
         hint="Πρώτα «Κινήσου» ως την αρχή της γραμμής και μετά «Ακολούθησε τη μαύρη γραμμή»."),
    dict(id="14", no=14, chapter=4, mode="write", pill="sense", kind="rock", prog=dict(line=True),
         palette=("move", "turn", "line"), title="Ο μεγάλος βράχος",
         goal="Ο βράχος είναι βαρύς: σπρώξτε τον στο ποτάμι μαζί με τον γείτονα!",
         about=["Δύο γείτονες σπρώχνουν μαζί τον μεγάλο βράχο.", "Όποιος φτάσει πρώτος περιμένει τον άλλο."],
         hint="Ακολουθήστε τη γραμμή ως τον βράχο. Το R2 που φτάνει πρώτο περιμένει τον γείτονα."),
]
for _lv in LEVELS:
    _lv.setdefault("mode", "drive")
    _lv.setdefault("prog", None)
    _lv.setdefault("palette", ())
    _lv.setdefault("pill", _lv["mode"])
BY_ID = {lv["id"]: lv for lv in LEVELS}
MAX_ACTIONS = 120                # τόσες κινήσεις το πολύ από ένα πρόγραμμα (π.χ. «επανάλαβε» μέσα σε «επανάλαβε»)
MAX_WAIT = 30                    # «περίμενε ώσπου»: τόσα βήματα το πολύ, μετά το R2 τα παρατά
TEST_WAIT = 12                   # στη «Δοκιμή» (η μπάρα εκεί ανοίγει σε 4 βήματα)
CM_TILE, CM_NEAR, CM_FAR = 20, 10, 300     # ο αισθητήρας απόστασης, όπως στο «Προγραμμάτισε»
CM_CHOICES = (10, 20, 30, 40, 50)


def level(level_id):
    return BY_ID[str(level_id)]


def next_level(level_id):
    ids = [lv["id"] for lv in LEVELS]
    i = ids.index(str(level_id))
    return ids[i + 1] if i + 1 < len(ids) else None


# ------------------------------------------------------------------ ομάδες και θέσεις
TEAM_SHAPES = {
    2: [(0, 0), (1, 0)],
    3: [(0, 0), (1, 0), (1, 1)],
    4: [(0, 0), (1, 0), (1, 1), (0, 1)],
    5: [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1)],
}


def team_sizes(n):
    """2-5 υπολογιστές: ένα ποτάμι. Περισσότεροι: ποτάμια των 3 έως 5, όσο πιο ίσα γίνεται."""
    n = max(MIN_PCS, min(MAX_PCS, n))
    if n <= 5:
        return [n]
    t = -(-n // 5)
    base, extra = divmod(n, t)
    return [base + 1] * extra + [base] * (t - extra)


def shape_size(size):
    cols = 1 + max(c for c, _ in TEAM_SHAPES[size])
    rows = 1 + max(r for _, r in TEAM_SHAPES[size])
    return cols * PLOT, rows * PLOT


def arrange(sizes, aspect=3.0):
    """Πού μπαίνει κάθε ποτάμι στο δάσος (σε σειρές, με μια λωρίδα δέντρα ανάμεσα).
    Διαλέγει πόσα ποτάμια ανά σειρά ώστε το δάσος να χωράει όσο πιο μεγάλο σε οθόνη με λόγο aspect."""
    best = None
    for per_row in range(1, len(sizes) + 1):
        rows = [sizes[i:i + per_row] for i in range(0, len(sizes), per_row)]
        W = max(sum(shape_size(s)[0] for s in row) + len(row) - 1 for row in rows)
        H = sum(max(shape_size(s)[1] for s in row) for row in rows) + len(rows) - 1
        k = min(aspect / (W + H * 0.46), 1.0 / (H * 0.8 + 4))
        if best is None or k > best[0] + 1e-9:
            best = (k, per_row, W, H)
    _, per_row, W, H = best
    origins, y = [], 0
    for i in range(0, len(sizes), per_row):
        row = sizes[i:i + per_row]
        x = 0
        for s in row:
            origins.append((x, y))
            x += shape_size(s)[0] + 1
        y += max(shape_size(s)[1] for s in row) + 1
    return origins, W, H


# ------------------------------------------------------------------ μικρά εργαλεία
def side_cell(side, i):
    return {UP: (i, 0), DOWN: (i, PLOT - 1), LEFT: (0, i), RIGHT: (PLOT - 1, i)}[side]


def inward(side):
    return (side + 2) % 4


def inside(c):
    return 0 <= c[0] < PLOT and 0 <= c[1] < PLOT


def add(c, d, n=1):
    return (c[0] + DX[d] * n, c[1] + DY[d] * n)


def dir_of(a, b):
    for d in range(4):
        if add(a, d) == b:
            return d
    return None


def neighbors(c):
    for d in range(4):
        n = add(c, d)
        if inside(n):
            yield n


def bfs(start, ok, goal=None):
    """Αποστάσεις από το start μέσα από κουτάκια όπου ok(c). Με goal: η διαδρομή ως εκεί (ή None)."""
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if goal is not None and c == goal:
            path = []
            while c is not None:
                path.append(c)
                c = prev[c]
            return path[::-1]
        for n in neighbors(c):
            if n not in prev and ok(n):
                prev[n] = c
                q.append(n)
    return None if goal is not None else set(prev)


def straight_path(a, sa, b, sb, rng):
    """Διαδρομή νερού από το κουτάκι a (στην πλευρά sa) ως το b (στην πλευρά sb), με το πολύ δύο γωνίες."""
    da = inward(sa)
    path = [a]
    c = a
    if sb == (sa + 2) % 4:                       # απέναντι πλευρά: ευθεία με ένα «σκαλοπάτι»
        axis_len = PLOT - 1
        turn_at = rng.randint(1, axis_len - 1)
        for step in range(axis_len):
            if step == turn_at:
                while (c[1] if da in (LEFT, RIGHT) else c[0]) != (b[1] if da in (LEFT, RIGHT) else b[0]):
                    if da in (LEFT, RIGHT):
                        c = (c[0], c[1] + (1 if b[1] > c[1] else -1))
                    else:
                        c = (c[0] + (1 if b[0] > c[0] else -1), c[1])
                    path.append(c)
            c = add(c, da)
            path.append(c)
        while c != b:                            # αν το σκαλοπάτι δεν έγινε (turn_at στο τέλος)
            if da in (LEFT, RIGHT):
                c = (c[0], c[1] + (1 if b[1] > c[1] else -1))
            else:
                c = (c[0] + (1 if b[0] > c[0] else -1), c[1])
            path.append(c)
        return path
    if sb == sa:
        return None
    # διπλανές πλευρές: πρώτα προς τα μέσα ως τη γραμμή του b, μετά προς την πλευρά του b
    db = sb
    while (c[0] if da in (LEFT, RIGHT) else c[1]) != (b[0] if da in (LEFT, RIGHT) else b[1]):
        c = add(c, da)
        path.append(c)
    while c != b:
        c = add(c, db)
        path.append(c)
    return path


# ------------------------------------------------------------------ ο λύτης (και οι κανόνες κίνησης)
class Plot:
    """Ένα οικόπεδο για τον λύτη: τα κουτάκια του (τοπικές συντεταγμένες 0-5) και οι πέτρες του."""

    def __init__(self, cells, arm=(), pedal=None):
        self.cells = cells               # (x, y) -> χαρακτήρας
        self.arm = set(arm)

    def robot_ok(self, c, stones, arm_up):
        if not inside(c) or c in stones:
            return False
        ch = self.cells.get(c, ".")
        if ch in ".mpB":
            return not (c in self.arm and not arm_up)
        return False

    def push_ok(self, c, stones, arm_up):
        """Πού μπορεί να πάει μια πέτρα: σε άδειο έδαφος, σε ποτάμι (πέρασμα), σε αυλάκι (το κλείνει)."""
        if not inside(c) or c in stones or ("fixed", c) in stones:
            return None
        ch = self.cells.get(c, ".")
        if ch == "w":
            return "x"
        if ch == "c":
            return "d"
        if ch in ".m" and c not in self.arm:
            return "."
        return None


def step(plot, pos, face, action, stones, arm_up=True):
    """Μία κίνηση του R2 (για τον λύτη). Επιστρέφει (θέση, κατεύθυνση, πέτρες, τι έγινε)."""
    if action == "left":
        return pos, (face + 3) % 4, stones, "turn"
    if action == "right":
        return pos, (face + 1) % 4, stones, "turn"
    d = face if action == "forward" else (face + 2) % 4
    t = add(pos, d)
    if t in stones:
        if action != "forward":
            return pos, face, stones, "bump"
        u = add(t, d)
        kind = plot.push_ok(u, stones, arm_up)
        if kind is None:
            return pos, face, stones, "bump"
        st = dict(stones)
        del st[t]
        if kind == ".":
            st[u] = "."
        else:
            st[("fixed", u)] = kind              # πέρασμα ή φράγμα: δεν κουνιέται ξανά
        return t, face, st, "push"
    if plot.robot_ok(t, _ground_stones(stones), arm_up) or _crossing_at(stones, t):
        return t, face, stones, "move"
    return pos, face, stones, "bump"


def _ground_stones(stones):
    return {k for k in stones if not (isinstance(k[0], str))}


def _crossing_at(stones, c):
    return stones.get(("fixed", c)) == "x"


def solve(plot, pos, face, stones, goal, arm_up=True, limit=60000):
    """Οι λιγότερες κινήσεις ώσπου goal(θέση, πέτρες) να είναι αληθές. stones: {(x, y): "."}.
    Επιστρέφει (κινήσεις, θέση, κατεύθυνση, πέτρες) ή None."""
    start = (pos, face, frozenset(stones.items()))
    prev = {start: None}
    q = deque([start])
    while q:
        state = q.popleft()
        p, f, st = state
        sd = dict(st)
        if goal(p, sd):
            acts = []
            s = state
            while prev[s] is not None:
                s, a = prev[s]
                acts.append(a)
            return acts[::-1], p, f, sd
        if len(prev) > limit:
            return None
        for a in ACTIONS:
            np_, nf, nst, what = step(plot, p, f, a, sd, arm_up)
            if what == "bump":
                continue
            ns = (np_, nf, frozenset(nst.items()))
            if ns not in prev:
                prev[ns] = (state, a)
                q.append(ns)
    return None


# ------------------------------------------------------------------ η κατασκευή ενός οικοπέδου
class Fail(Exception):
    pass


def _region(cells, start, extra_ok=lambda c: False, blocked=()):
    """Τα κουτάκια όπου μπορεί να πάει ένα R2 (ή ένα ζώο) από το start, χωρίς να περάσει νερό."""
    def ok(c):
        if c in blocked:
            return False
        return cells.get(c, ".") in ".mpB" or extra_ok(c)
    if start in blocked:
        return set()
    return bfs(start, ok)


def _place_trees(cells, rng, keep, checks, density):
    """Δέντρα και βράχοι σε τυχαία κουτάκια, χωρίς να χαλάσουν οι διαδρομές που ελέγχουν τα checks."""
    free = [c for c in ((x, y) for y in range(PLOT) for x in range(PLOT)) if cells.get(c, ".") == "." and c not in keep]
    rng.shuffle(free)
    want = int(len(free) * density)
    placed = 0
    for c in free:
        if placed >= want:
            break
        cells[c] = "T" if rng.random() < 0.8 else "R"
        if all(chk() for chk in checks):
            placed += 1
        else:
            cells[c] = "."


def _fork(path, rng, cells, avoid):
    """Μια διακλάδωση πάνω στη διαδρομή: (F, W1, W2, κατεύθυνση) όπου W1 το αυλάκι που χάνει το νερό
    και W2 η λιμνούλα στο τέλος του."""
    options = []
    for i in range(1, len(path) - 1):
        a, f, b = path[i - 1], path[i], path[i + 1]
        if dir_of(a, f) != dir_of(f, b):
            continue                             # μόνο σε ευθύ κομμάτι
        d = dir_of(a, f)
        for wd in ((d + 1) % 4, (d + 3) % 4):
            w1, w2 = add(f, wd), add(f, wd, 2)
            if inside(w1) and inside(w2) and cells.get(w1, ".") == "." and cells.get(w2, ".") == "." \
                    and w1 not in avoid and w2 not in avoid:
                options.append((f, w1, w2, wd))
    if not options:
        raise Fail("fork")
    return rng.choice(options)


def _dam_spot(cells, w1, wd, rng, avoid):
    """Πού μπαίνει η πέτρα για να κλείσει το αυλάκι w1: δίπλα του, με χώρο για το R2 πίσω της."""
    options = []
    for pd in ((wd + 1) % 4, (wd + 3) % 4):
        s, p = add(w1, pd), add(w1, pd, 2)
        if inside(s) and inside(p) and cells.get(s, ".") == "." and cells.get(p, ".") == "." \
                and s not in avoid and p not in avoid:
            options.append((s, p, (pd + 2) % 4))
    if not options:
        raise Fail("dam")
    return rng.choice(options)


def _pick_start(region, target, rng, avoid, min_d=2):
    far = [c for c in region if c not in avoid and abs(c[0] - target[0]) + abs(c[1] - target[1]) >= min_d]
    if not far:
        raise Fail("start")
    return rng.choice(far)


def _pedal_fits(outs, next_out, i):
    """Ταιριάζει το πεντάλ στη θέση i για το επόμενο οικόπεδο; Αν εκείνο στρίβει, η μεριά του κλαδιού
    όπου είναι το φράγμα του πρέπει να έχει αρκετό χώρο."""
    nin = (outs + 2) % 4
    if next_out is None:
        return 1 <= i <= 4
    if next_out == (nin + 2) % 4:
        return 1 <= i <= 4
    # η πλευρά εξόδου του επόμενου είναι στη μεριά «μικρότερο i» ή «μεγαλύτερο i»
    low = next_out in (UP, LEFT)
    return i >= 3 if not low else i <= 2


def make_plot(kind, role, ins, outs, free_sides, rng, next_out=None, prog=None):
    """Ένα οικόπεδο. ins = (πλευρά, πύλη νερού, δεύτερος δείκτης) από το προηγούμενο οικόπεδο ή None.
    outs = πλευρά προς το επόμενο ή None. role: "A"/"B" τα δύο οικόπεδα του μεγάλου βράχου (πίστα 14).
    Επιστρέφει λεξικό με τοπικές συντεταγμένες."""
    if kind == "bars":
        return make_bars_plot(ins, outs, free_sides, rng, next_out, prog)
    cells = {}
    first, last = ins is None, outs is None
    # ---- η είσοδος του νερού: από το προηγούμενο οικόπεδο ή από μια πηγή
    if ins:
        in_side, in_gate, in_extra = ins
        entry = side_cell(in_side, in_gate)
    else:
        choices = [s for s in free_sides if s != outs] or [s for s in range(4) if s != outs]
        in_side = rng.choice(choices)
        in_gate, in_extra = rng.randint(1, PLOT - 2), None
        entry = side_cell(in_side, in_gate)
    out = {"side": outs}
    water = "w" if kind == "cross" else "c"
    # ---- η έξοδος
    if not last:
        arm_cells = set()
        if kind == "branch" and ins:
            base = side_cell(in_side, in_extra)
            arm_cells = {add(base, inward(in_side), k) for k in range(3)}
        for _ in range(12):
            g = rng.randint(1, PLOT - 2)
            exit_ = side_cell(outs, g)
            if role == "A" and not inside(add(exit_, (outs + 1) % 4, 2)):
                continue                         # ο βράχος και το R2 πίσω του, στην άκρη δίπλα στην πύλη
            path = straight_path(entry, in_side, exit_, outs, rng)
            if path and not arm_cells & set(path):
                break
        else:
            if role:
                raise Fail("gate")
        out["gate"] = g
    elif kind == "cross":
        ends = [s for s in free_sides if s != in_side] or [s for s in range(4) if s != in_side]
        se = rng.choice(ends)
        exit_ = side_cell(se, rng.randint(1, PLOT - 2))
        path = straight_path(entry, in_side, exit_, se, rng)
    else:
        path = None                              # η φωτιά: η διαδρομή φτιάχνεται πιο κάτω
    if path is not None and (len(path) < 4 or len(set(path)) != len(path)):
        raise Fail("path")
    if role == "A" and path[-2] != add(path[-1], inward(outs)):
        raise Fail("rock gate")
    if role == "B" and (path[1] != add(entry, inward(in_side)) or not inside(add(entry, (inward(in_side) + 1) % 4, 2))):
        raise Fail("rock entry")
    plot = {"kind": kind, "in": in_side, "out": outs, "entry": entry, "first": first, "last": last}
    stones, goals, animals, meadow, fire, arm, pedal = [], [], [], [], [], [], None
    chan_next = {}

    if kind == "cross":
        for c in path:
            cells[c] = "w"
        if first:
            cells[entry] = "S"                   # η πηγή του ποταμιού
        # οι δύο όχθες: δεξιά όχθη = δεξιά καθώς κυλά το νερό
        f0 = dir_of(path[1], path[2]) if len(path) > 2 else dir_of(path[0], path[1])
        probe = add(path[1], (f0 + 1) % 4)
        if not inside(probe) or cells.get(probe, ".") != ".":
            raise Fail("bank")
        right = _region(cells, probe)
        left = {c for c in ((x, y) for y in range(PLOT) for x in range(PLOT))
                if cells.get(c, ".") == "." and c not in right}
        if not left or not right:
            raise Fail("banks")
        gaps = []
        if ins:
            gc = side_cell(in_side, in_extra)
            if gc not in right:
                raise Fail("gap in")
            gaps.append(gc)
        if not last:
            opts = [i for i in range(PLOT) if i != out["gate"] and side_cell(outs, i) in right]
            if role == "A":                      # το άνοιγμα: εκεί που στέκεται το R2 πριν σπρώξει
                gi = side_index(outs, add(side_cell(outs, out["gate"]), (outs + 1) % 4, 2))
                opts = [gi] if gi in opts else []
            if not opts:
                raise Fail("gap out")
            gi = rng.choice(opts)
            out["extra"] = gi
            gaps.append(side_cell(outs, gi))
        else:
            edge = [c for c in right if c[0] in (0, PLOT - 1) or c[1] in (0, PLOT - 1)]
            rng.shuffle(edge)
            for c in edge:
                group = [c] + [n for n in neighbors(c) if n in right][:2]
                if len(group) >= 2:
                    meadow = group
                    break
            if not meadow:
                raise Fail("meadow")
            for c in meadow:
                cells[c] = "m"
        # το πέρασμα
        options = []
        for i in range(1, len(path) - 1):
            x = path[i]
            if cells[x] != "w":
                continue
            d = dir_of(path[i - 1], x) if dir_of(path[i - 1], x) == dir_of(x, path[i + 1]) else None
            if d is None:
                continue
            lft, rgt = add(x, (d + 3) % 4), add(x, (d + 1) % 4)
            if not (inside(lft) and inside(rgt) and lft in left and rgt in right):
                continue
            for bank, side_d in ((rgt, (d + 1) % 4),):      # το R2 στην απέναντι όχθη από τα ζώα
                behind = add(bank, side_d)
                if inside(behind) and cells.get(behind, ".") == "." and behind not in gaps and behind not in meadow \
                        and bank not in gaps and bank not in meadow:
                    options.append((x, lft, rgt, bank, behind, (side_d + 2) % 4))
        if role in ("A", "B"):
            # ο μεγάλος βράχος: πέφτει στο ποτάμι πάνω στον φράχτη, μισός σε κάθε οικόπεδο
            x = path[-1] if role == "A" else entry
            flow = outs if role == "A" else inward(in_side)
            lft, rgt = add(x, (flow + 3) % 4), add(x, (flow + 1) % 4)
            s, p, push_d = rgt, add(x, (flow + 1) % 4, 2), (flow + 3) % 4
            ok = inside(lft) and lft in left and rgt in right and p in right and cells.get(p, ".") == "." \
                and p not in meadow
            options = [(x, lft, rgt, s, p, push_d)] if ok else []
        if not options:
            raise Fail("crossing")
        x, lft, rgt, s, p, push_d = rng.choice(options)
        plot["push"] = (s, p, push_d)
        stones = [s]
        goals = [("stone", 0, x, "x"), ("leave", (lft, x, rgt))]   # μετά: στην άκρη, να περάσουν τα ζώα
        bank_cells = right if s in right else left
        animal_spots = [c for c in left if c not in (lft, s, p) and c not in gaps]
        rng.shuffle(animal_spots)
        n_an = 2 if len(animal_spots) >= 2 else len(animal_spots)
        if n_an == 0:
            raise Fail("animals")
        kinds = rng.choice([("rabbit", "rabbit"), ("deer", "fawn"), ("fox", "cub"), ("rabbit", "fox"),
                            ("deer", "rabbit")])
        for i in range(n_an):
            animals.append({"kind": kinds[i], "cell": animal_spots[i]})
        start = _pick_start(bank_cells - {s, p}, p, rng, set(gaps) | set(meadow) | {a["cell"] for a in animals}, 2)
        keep = {x, lft, rgt, s, p, start} | set(gaps) | set(meadow) | {a["cell"] for a in animals}
        targets_r = [c for c in gaps if not ins or c != side_cell(in_side, in_extra)] or meadow

        def chk_robot():
            return p in _region(cells, start, blocked={s})

        def chk_animals():
            reach = _region(cells, lft)
            return all(a["cell"] in reach for a in animals)

        def chk_right():
            reach = _region(cells, rgt)
            need = set(targets_r) | set(gaps)
            return all(c in reach for c in need)

        def chk_park():
            """Μια θέση στην όχθη όπου το R2 κάνει στην άκρη χωρίς να κλείνει τον δρόμο των ζώων."""
            need = set(targets_r) | set(gaps)
            for c in _region(cells, s):
                if c in (lft, x, rgt, s) or c in gaps or c in meadow:
                    continue
                reach = _region(cells, rgt, blocked={c})
                if all(t in reach for t in need):
                    return True
            return False
        checks = [chk_robot, chk_animals, chk_right, chk_park]
        if not all(chk() for chk in checks):
            raise Fail("layout")
        if prog and prog.get("line"):
            # η μαύρη γραμμή: από λίγο πιο πέρα ως την πέτρα (το R2 τη σπρώχνει στο τέλος της γραμμής)
            lfree = _region(cells, p, blocked={s}) - {lft, x, rgt, p} - set(gaps) - set(meadow) \
                - {a["cell"] for a in animals}
            line, lead = _make_line(lfree, p, s, rng)
            plot["line"] = line
            plot["lead"] = lead
            keep |= set(line) | set(lead) | {(c[0], c[1] + 1) for c in line + lead}
        _place_trees(cells, rng, keep, checks, 0.3)
        plot["gaps"] = gaps
        plot["crossing"] = x
        if role in ("A", "B"):
            plot["rock"] = role
    else:
        # ---- αυλάκι με διακλάδωση· στο τελευταίο οικόπεδο καταλήγει στη φωτιά
        pocket = []
        arm_line, arm = [], []
        if kind == "branch" and ins:
            d_in = inward(in_side)
            base = side_cell(in_side, in_extra)
            arm_line = [add(base, d_in, k) for k in range(PLOT)]
            arm = arm_line[:3]
        if last:
            corners = [(0, 0), (PLOT - 1, 0), (0, PLOT - 1), (PLOT - 1, PLOT - 1)]
            corners = [c for c in corners if abs(c[0] - entry[0]) + abs(c[1] - entry[1]) >= 5 and c not in arm_line]
            if not corners:
                raise Fail("corner")
            corner = rng.choice(corners)
            pocket = [corner]
            along = [n for n in neighbors(corner) if (n[0] in (0, PLOT - 1) or n[1] in (0, PLOT - 1))
                     and n not in arm_line]
            if rng.random() < 0.6 and along:
                pocket.append(rng.choice(along))
            fire = sorted({n for c in pocket for n in neighbors(c) if n not in pocket})
            if any(c in arm for c in fire):
                raise Fail("fire arm")
            ends = [n for f in fire for n in neighbors(f)
                    if n not in fire and n not in pocket and n != entry and n not in arm]
            if not ends:
                raise Fail("end")
            end = rng.choice(ends)
            blocked = set(fire) | set(pocket) | set(arm)
            path = bfs(entry, lambda c: c not in blocked, goal=end)
            if path is None or len(path) < 4:
                raise Fail("fire path")
            for c in fire:
                cells[c] = "F"
            plot["fire_end"] = end
            for i, c in enumerate(pocket):
                animals.append({"kind": ("fox", "cub", "rabbit")[i % 3], "cell": c})
            if len(pocket) == 1:
                animals.append({"kind": "cub", "cell": pocket[0]})
        if any(c in arm for c in path):
            raise Fail("arm")
        for c in path:
            cells[c] = "c"
        if first:
            cells[entry] = "S"
        # ---- ο τοίχος του κλαδιού: τα κουτάκια μετά το κλαδί, στην ίδια γραμμή, γίνονται δέντρα
        for c in arm_line[3:]:
            if cells.get(c, ".") == ".":
                cells[c] = "T"

        def half(c):
            if not arm_line:
                return 0
            v = c[1] if in_side in (LEFT, RIGHT) else c[0]
            return None if v == in_extra else (0 if v < in_extra else 1)

        # ---- όλες οι δυνατές διακλαδώσεις μαζί με τη θέση της πέτρας
        avoid = set(pocket) | set(fire) | set(arm_line) | {entry}
        combos = []
        for i in range(1, len(path) - 1):
            a, f, b = path[i - 1], path[i], path[i + 1]
            if dir_of(a, f) != dir_of(f, b) or f in arm_line:
                continue
            d = dir_of(a, f)
            for wd in ((d + 1) % 4, (d + 3) % 4):
                w1, w2 = add(f, wd), add(f, wd, 2)
                if not (inside(w1) and inside(w2)) or cells.get(w1, ".") != "." or cells.get(w2, ".") != "." \
                        or w1 in avoid or w2 in avoid:
                    continue
                for pd in ((wd + 1) % 4, (wd + 3) % 4):
                    s, p = add(w1, pd), add(w1, pd, 2)
                    if inside(s) and inside(p) and cells.get(s, ".") == "." and cells.get(p, ".") == "." \
                            and s not in avoid and p not in avoid and half(s) is not None and half(p) == half(s):
                        combos.append((f, w1, w2, wd, s, p))
        if kind == "branch" and ins and not last:
            pedal_halves = {half(side_cell(outs, i)) for i in range(PLOT)
                            if i != out["gate"] and cells.get(side_cell(outs, i), ".") == "."}
            combos = [cb for cb in combos if any(h is not None and h != half(cb[5]) for h in pedal_halves)]
        if not combos:
            raise Fail("dam")
        f, w1, w2, wd, s, p = rng.choice(combos)
        plot["push"] = (s, p, dir_of(p, s))
        cells[w1] = "c"
        cells[w2] = "w"
        for i in range(len(path) - 1):
            chan_next[path[i]] = [path[i + 1]]
        chan_next[f] = [w1, chan_next[f][0]]           # πρώτα στο αυλάκι που χάνει το νερό
        chan_next[w1] = [w2]
        if first:
            plot["source"] = path[1]
            chan_next.pop(entry, None)
        else:
            plot["source"] = entry
        stones = [s]
        goals = [("stone", 0, w1, "d")]
        plot["dam"] = w1
        # ---- γεφυράκια πάνω από το αυλάκι (το νερό περνά από κάτω, το R2 από πάνω)
        near_f = {f, w1, add(f, dir_of(path[path.index(f) - 1], f)), path[path.index(f) - 1]}
        spots = [path[i] for i in range(1, len(path) - 1)
                 if dir_of(path[i - 1], path[i]) == dir_of(path[i], path[i + 1]) and path[i] not in near_f
                 and path[i] not in arm_line and path[i] != plot.get("fire_end")]
        rng.shuffle(spots)
        bridges = []
        for c in spots:
            if len(bridges) >= 2:
                break
            if all(abs(c[0] - b[0]) + abs(c[1] - b[1]) > 1 for b in bridges):
                cells[c] = "B"
                bridges.append(c)
        if last:
            reach = _region(cells, pocket[0], extra_ok=lambda c: cells.get(c) == "F") - set(pocket) - set(fire) - {s, p}
            far = sorted(reach, key=lambda c: (-(abs(c[0] - pocket[0][0]) + abs(c[1] - pocket[0][1])), c))
            if len(far) < 3:
                raise Fail("meadow")
            meadow = [far[0]] + [n for n in neighbors(far[0]) if n in reach][:2]
            if len(meadow) < 2:
                raise Fail("meadow small")
            for c in meadow:
                cells[c] = "m"
        for c in arm:
            cells[c] = "a"
        arm_set = set(arm)

        def region(start_c, arm_up, blocked=()):
            return _region(cells, start_c, extra_ok=lambda c: cells.get(c) == "a" and arm_up, blocked=blocked)

        # ---- το πεντάλ του κλαδιού για το επόμενο οικόπεδο (πίστα 3)
        down_from_p = region(p, False, blocked={s})
        up_from_p = region(p, True, blocked={s})
        busy = {s, p} | set(meadow) | set(pocket)
        if kind == "branch" and not last:
            opts = []
            for i in range(PLOT):
                c = side_cell(outs, i)
                if i == out["gate"] or cells.get(c, ".") != "." or c in busy:
                    continue
                if ins:
                    ok = c in up_from_p and c not in down_from_p      # πέρα από το δικό του κλαδί
                else:
                    ok = c in down_from_p
                if ok:
                    opts.append(i)
            if not opts:
                raise Fail("pedal")
            good = [i for i in opts if _pedal_fits(outs, next_out, i)]
            pi = rng.choice(good or opts)
            pedal = side_cell(outs, pi)
            cells[pedal] = "p"
            out["extra"] = pi
            busy.add(pedal)
        # ---- πού ξεκινά το R2
        if kind == "branch" and ins and last:
            other = up_from_p - down_from_p - arm_set - busy
            start = _pick_start(other, p, rng, set(), 2)
        else:
            start = _pick_start(down_from_p - busy, p, rng, set(), 2)
        keep = {s, p, start, f, w1, w2, plot.get("fire_end")} | busy | set(fire) | arm_set | set(bridges)

        def chk_robot():
            if kind == "branch" and ins and last:
                return p in region(start, True, blocked={s}) and p not in region(start, False, blocked={s})
            return p in region(start, False, blocked={s})

        def chk_pedal():
            if not pedal:
                return True
            if ins:
                return pedal in region(p, True) and pedal not in region(p, False)
            return pedal in region(p, False)

        def chk_meadow():
            if not last:
                return True
            reach = _region(cells, pocket[0], extra_ok=lambda c: cells.get(c) == "F", blocked={s})
            return all(c in reach for c in meadow) and not any(c in _region(cells, pocket[0]) for c in meadow)
        checks = [chk_robot, chk_pedal, chk_meadow]
        if not all(chk() for chk in checks):
            raise Fail("layout")
        _place_trees(cells, rng, keep, checks, 0.22)
        if pedal:
            goals.append(("robot", pedal))
        plot["bridges"] = bridges
    plot.update(cells=cells, stones=stones, goals=goals, animals=animals, meadow=meadow, fire=fire, arm=arm,
                pedal=pedal, chan_next=chan_next, path=path)
    if prog and prog.get("line"):
        # ---- η μαύρη γραμμή: «Κινήσου» ως την αρχή της και «Ακολούθησε τη μαύρη γραμμή»
        plot["goals"] = [g for g in plot["goals"] if g[0] != "leave"]
        lead, line = plot["lead"], plot["line"]
        start = lead[0]
        face = dir_of(lead[0], lead[1]) if len(lead) > 1 else dir_of(lead[0], line[0])
        program = [move_block("forward", len(lead)), line_block()]
        pos, f2, st, ok, why = simulate_prog(plot, start, face, {c: "." for c in plot["stones"]}, program)
        if not (ok and goals_met(plot["goals"], pos, st)):
            raise Fail("line program")
        plot["start"] = (start, face)
        plot["program"] = program
        plot["solution"] = []
        return plot, out
    if prog:
        # ---- κεφάλαια με πρόγραμμα: το R2 ξεκινά ώστε να φτάνουν λίγα μπλοκ
        if not prog.get("leave"):
            plot["goals"] = [g for g in plot["goals"] if g[0] != "leave"]
        start, face, program = program_start(plot, prog["shape"], prog.get("leave"), rng)
        plot["start"] = (start, face)
        plot["program"] = program
        plot["solution"] = [a for a, _ in flatten(program)]
        if prog.get("fix"):
            plot["given"] = make_bug(plot, program, rng)
        return plot, out
    # ---- αρχή του R2 και λύση
    face = rng.randrange(4)
    plot["start"] = (start, face)
    sol = plan(plot, start, face, {c: "." for c in stones}, goals, arm_up=True)
    if sol is None or len(sol) < 2:
        raise Fail("unsolvable")
    plot["solution"] = sol
    return plot, out


# ------------------------------------------------------------------ τα προγράμματα (Διόρθωσε, Γράψε)
def move_block(d="forward", n=1):
    return {"op": "move", "dir": d, "n": n}


def turn_block(d="right", n=1):
    return {"op": "turn", "dir": d, "n": n}


def until_block(cmp=">", cm=20):
    return {"op": "until", "cmp": cmp, "cm": cm}


def line_block():
    return {"op": "line", "mode": "on"}


def side_index(side, c):
    """Ο αριθμός ενός κουτακιού πάνω στην πλευρά side (0-5)."""
    return c[0] if side in (UP, DOWN) else c[1]


def sees(dist, node):
    """«Διάβασε απόσταση (cm) < cm» ή «> cm»."""
    try:
        cm = int(node.get("cm", 20))
    except (TypeError, ValueError):
        cm = 20
    return dist > cm if node.get("cmp") == ">" else dist < cm


def has_sensors(program):
    """Έχει το πρόγραμμα «περίμενε ώσπου» ή «Ακολούθησε τη μαύρη γραμμή»;"""
    if not isinstance(program, list):
        return False
    for node in program:
        if isinstance(node, dict):
            if node.get("op") in ("until", "line"):
                return True
            if node.get("op") == "repeat" and has_sensors(node.get("body")):
                return True
    return False


def _count(node):
    try:
        return max(0, min(10, int(node.get("n", 1))))
    except (TypeError, ValueError):
        return 0


def run_steps(program, sense, max_wait=MAX_WAIT):
    """Το πρόγραμμα την ώρα που τρέχει, ένα βήμα τη φορά (γεννήτρια). Βγάζει (κίνηση, θέση του μπλοκ):
    forward / back / left / right / wait, ή "fail:λόγος" (time: περίμενε πολύ, noline: δεν βρήκε γραμμή).
    sense("dist") = τι μετρά ο αισθητήρας απόστασης τώρα (cm). sense("line") = η επόμενη κίνηση πάνω στη
    γραμμή, None στο τέλος της, "noline" αν το R2 δεν είναι πάνω της. Οι αισθητήρες ρωτιούνται τη στιγμή
    του βήματος, άρα το πρόγραμμα «βλέπει» τι κάνουν τα άλλα R2."""

    def walk(nodes, path):
        if not isinstance(nodes, list):
            return
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            p = path + (i,)
            op = node.get("op")
            n = _count(node)
            if op == "move":
                for _ in range(n):
                    yield ("back" if node.get("dir") == "back" else "forward", p)
            elif op == "turn":
                for _ in range(n):
                    yield ("left" if node.get("dir") == "left" else "right", p)
            elif op == "wait":
                for _ in range(n):
                    yield ("wait", p)
            elif op == "until":
                waited = 0
                while not sees(sense("dist"), node):
                    if waited >= max_wait:
                        yield ("fail:time", p)
                        return
                    yield ("wait", p)
                    waited += 1
            elif op == "line":
                if node.get("mode", "on") != "on":
                    continue
                for _ in range(MAX_ACTIONS):
                    a = sense("line")
                    if a is None:
                        break
                    if a == "noline":
                        yield ("fail:noline", p)
                        return
                    yield (a, p)
            elif op == "repeat":
                for _ in range(n):
                    yield from walk(node.get("body") or [], p + (0,))

    count = 0
    for step_ in walk(program, ()):
        yield step_
        if step_[0].startswith("fail:"):
            return
        count += 1
        if count >= MAX_ACTIONS:
            return


def node_at(program, path):
    """Το μπλοκ στη θέση path (όπως στο «Προγραμμάτισε»: (3,) ή (0, 0, 1) μέσα σε «επανάλαβε»)."""
    try:
        node = program[path[0]]
        rest = list(path[1:])
        while rest:
            m, j = rest[0], rest[1]
            rest = rest[2:]
            node = (node.get("body") or [])[j] if m == 0 else None
        return node if isinstance(node, dict) else None
    except (IndexError, KeyError, TypeError, AttributeError):
        return None


def line_next(line, pos, face):
    """Ο αισθητήρας γραμμής: η επόμενη κίνηση πάνω στη μαύρη γραμμή (None στο τέλος της)."""
    if not line or pos not in line:
        return "noline"
    i = line.index(pos)
    if i == len(line) - 1:
        return None
    d = dir_of(pos, line[i + 1])
    if d == face:
        return "forward"
    return "left" if (d - face) % 4 == 3 else "right"


def distance_local(sp, pos, face, stones, blocked=()):
    """Ο αισθητήρας απόστασης μέσα σε ένα οικόπεδο (για τον έλεγχο των πιστών): δέντρα, βράχοι, πέτρες,
    κλειστή μπάρα και ο φράχτης. Το νερό δεν είναι εμπόδιο (ο υπέρηχος περνά από πάνω)."""
    free = 0
    c = add(pos, face)
    while inside(c):
        ch = sp.cells.get(c, ".")
        if ch in "TRS" or c in blocked or (c in stones and stones[c] == "."):
            break
        free += 1
        c = add(c, face)
    return CM_NEAR + CM_TILE * free


def simulate_prog(plot, start, face, stones, program, lift=None):
    """Τρέχει ένα πρόγραμμα (και με αισθητήρες) σε ένα οικόπεδο. lift: σε ποιο βήμα ανοίγει η μπάρα του
    (None: ανοιχτή από την αρχή). Επιστρέφει (θέση, κατεύθυνση, πέτρες, πέτυχε, λόγος)."""
    sp = solver_plot(plot)
    arm = set(plot.get("arm") or ())
    line = list(plot.get("line") or [])
    st = {"pos": start, "face": face, "stones": dict(stones), "t": 0}

    def up():
        return lift is None or st["t"] >= lift

    def sense(kind):
        if kind == "dist":
            return distance_local(sp, st["pos"], st["face"], st["stones"], () if up() else arm)
        return line_next(line, st["pos"], st["face"])

    for action, _p in run_steps(program, sense):
        if action.startswith("fail:"):
            return st["pos"], st["face"], st["stones"], False, action[5:]
        if action != "wait":
            pos, f, sto, what = step(sp, st["pos"], st["face"], action, st["stones"], up())
            if what == "bump":
                return st["pos"], st["face"], st["stones"], False, "bump"
            st.update(pos=pos, face=f, stones=sto)
        st["t"] += 1
    return st["pos"], st["face"], st["stones"], True, None


def _make_line(free, p, s, rng):
    """Η μαύρη γραμμή: τυχαίος δρόμος με στροφές που τελειώνει ... → p → s (η πέτρα). Δεν ακουμπά τον εαυτό
    της. Επιστρέφει (γραμμή, κουτάκια πριν από την αρχή της για το R2: [αρχή του R2, ..., ένα πριν])."""
    if len(free) < 7:
        raise Fail("line")                       # δεν χωράει γραμμή με στροφές
    for attempt in range(120):
        line = [s, p]
        cur, d = p, dir_of(s, p)
        want = rng.randint(7, 11)
        run = 1
        while len(line) < want:
            opts = []
            for nd in (d, (d + 1) % 4, (d + 3) % 4):
                n = add(cur, nd)
                if n not in free or n in line:
                    continue
                if any(m in line and m != cur for m in neighbors(n)):
                    continue
                w = 3 if nd == d and run < 2 else (1 if nd == d else 2)
                opts += [(nd, n)] * w
            if not opts:
                break
            nd, n = rng.choice(opts)
            run = run + 1 if nd == d else 1
            line.append(n)
            cur, d = n, nd
        if len(line) < 7:
            continue
        line = line[::-1]
        turns = sum(1 for i in range(1, len(line) - 1) if dir_of(line[i - 1], line[i]) != dir_of(line[i], line[i + 1]))
        if turns < 2:
            continue
        # το R2 ξεκινά 1-2 κουτάκια πριν από την αρχή, ευθεία ή από το πλάι
        first = dir_of(line[0], line[1])
        leads = []
        for back in ((first + 2) % 4, (first + 1) % 4, (first + 3) % 4):
            for m in (2, 1):
                cs = [add(line[0], back, i) for i in range(m, 0, -1)]
                if all(c in free and c not in line and not any(nb in line[1:] for nb in neighbors(c)) for c in cs):
                    leads.append(cs)
        if leads:
            return line, rng.choice(leads)
    raise Fail("line")


# ------------------------------------------------------------------ οι μπάρες (πίστες 11-12)
def _tf(c, rot, flip):
    x, y = c
    if flip:
        y = PLOT - 1 - y
    for _ in range(rot):
        x, y = PLOT - 1 - y, x
    return (x, y)


def _tf_dir(d, rot, flip):
    if flip and d in (UP, DOWN):
        d = (d + 2) % 4
    return (d + rot) % 4


ALL_CELLS = [(x, y) for y in range(PLOT) for x in range(PLOT)]


def make_bars_plot(ins, outs, free_sides, rng, next_out=None, prog=None):
    """Ένα οικόπεδο της αλυσίδας με τις μπάρες. Η μπάρα (σε όλο το πλάτος) ανοίγει όταν το R2 του
    προηγούμενου οικοπέδου πατά το πεντάλ του. Το R2 περιμένει μπροστά της με τον αισθητήρα απόστασης, περνά
    και πατά το δικό του πεντάλ (στην άκρη, δίπλα στη μπάρα του επόμενου). Στο τελευταίο οικόπεδο το πεντάλ
    σηκώνει το φράγμα του αυλακιού και το νερό πάει στη φωτιά.
    Φτιάχνεται «ίσιο» (μπάρα από αριστερά, έξοδος δεξιά ή κάτω) και μετά γυρίζει στη σωστή θέση."""
    prog = prog or {}
    I = ins[0] if ins else None
    first, last = ins is None, outs is None
    opts = []
    for rot in range(4):
        for flip in (False, True):
            if I is not None and _tf_dir(LEFT, rot, flip) != I:
                continue
            for oc in ((RIGHT, DOWN) if not last else (None,)):
                if oc is not None and _tf_dir(oc, rot, flip) != outs:
                    continue
                opts.append((rot, flip, oc))
    if not opts:
        raise Fail("bars orient")
    e = None
    if ins:
        good = []
        for rot, flip, oc in opts:
            inv = {_tf(c, rot, flip): c for c in ALL_CELLS}
            ec = inv[side_cell(I, ins[2])][1]
            if 1 <= ec <= 4 and (not last or ec <= 2):
                good.append((rot, flip, oc, ec))
        if not good:
            raise Fail("bars e")
        rot, flip, oc, e = rng.choice(good)
    else:
        rot, flip, oc = rng.choice(opts)
    cells, animals, meadow, fire, pocket, path, chan_next = {}, [], [], [], [], [], {}
    arm = [(x, e) for x in range(PLOT)] if ins else []
    for c in arm:
        cells[c] = "a"
    sluice = None
    source = None
    fire_end = None
    if not last:
        if first:
            D = oc
            pedal = side_cell(oc, rng.randint(1, 4))
            k = rng.randint(2, 4)
            start = add(pedal, (D + 2) % 4, k)
        elif oc == DOWN:
            px = rng.randint(1, 4)
            start, D, pedal = (px, e - 1), DOWN, (px, PLOT - 1)
            k = PLOT - e
        else:
            choices_ = [((PLOT - 1, e - 1), DOWN, (PLOT - 1, py)) for py in range(e + 1, 5)]
            choices_ += [((PLOT - 1, e + 1), UP, (PLOT - 1, py)) for py in range(1, e)]
            if not choices_:
                raise Fail("bars pedal")
            start, D, pedal = rng.choice(choices_)
            k = abs(pedal[1] - start[1])
        robot_line = [add(start, D, i) for i in range(k + 1)]
        cells[pedal] = "p"
    else:
        # το τελευταίο: η μπάρα πάνω (σειρά e = 1 ή 2), από κάτω το αυλάκι, το φράγμα και η φωτιά
        px = rng.randint(0, PLOT - 1)
        yp = rng.randint(e + 2, 4)
        start, D, pedal = (px, e - 1), DOWN, (px, yp)
        k = yp - (e - 1)
        robot_line = [add(start, D, i) for i in range(k + 1)]
        R = rng.choice((LEFT, RIGHT))
        a1 = add(pedal, R)
        up_c, dn_c = add(a1, UP), add(a1, DOWN)
        if not (inside(a1) and inside(dn_c)) or up_c[1] <= e:
            raise Fail("sluice")
        forbid = set(robot_line) | set(arm) | {a1, up_c, dn_c}
        corners = [c for c in ((0, PLOT - 1), (PLOT - 1, PLOT - 1)) if c not in forbid]
        if not corners:
            raise Fail("corner")
        corner = rng.choice(corners)
        pocket = [corner]
        along = [n for n in neighbors(corner) if n[1] == PLOT - 1 and n not in forbid]
        if along and rng.random() < 0.6:
            pocket.append(rng.choice(along))
        fire = sorted({n for c in pocket for n in neighbors(c) if n not in pocket})
        if any(c in forbid or c[1] <= e for c in fire):
            raise Fail("fire")
        block = forbid | set(fire) | set(pocket)
        ends = [n for f in fire for n in neighbors(f) if n not in block and n[1] > e]
        rng.shuffle(ends)
        down = None
        for end in ends:
            down = bfs(dn_c, lambda c: c not in block - {dn_c} and c[1] > e, goal=end)
            if down:
                fire_end = end
                break
        if not down:
            raise Fail("fire path")
        block2 = block | set(down)
        springs = [c for c in ALL_CELLS if (c[0] == PLOT - 1 or c[1] == PLOT - 1) and c[1] > e and c not in block2
                   and c[0] != 0]
        rng.shuffle(springs)
        upper = None
        for sc in springs:
            upper = bfs(sc, lambda c: c not in block2 - {up_c} and c[1] > e, goal=up_c)
            if upper and len(upper) >= 2:
                break
            upper = None
        if not upper:
            raise Fail("spring")
        path = upper + [a1] + down
        if len(set(path)) != len(path):
            raise Fail("path")
        for c in path:
            cells[c] = "c"
        cells[path[0]] = "S"
        source = path[1]
        for i in range(1, len(path) - 1):
            chan_next[path[i]] = [path[i + 1]]
        for c in fire:
            cells[c] = "F"
        for i, c in enumerate(pocket):
            animals.append({"kind": ("fox", "cub", "rabbit")[i % 3], "cell": c})
        if len(pocket) == 1:
            animals.append({"kind": "cub", "cell": pocket[0]})
        cells[pedal] = "p"
        sluice = {"pedal": pedal, "arm": [a1]}

        def zone(fire_ok):
            return _region(cells, pocket[0], extra_ok=lambda c: fire_ok and cells.get(c) == "F",
                           blocked=set(arm) | {pedal}) - set(pocket)
        reach = zone(True) - set(fire) - set(robot_line)
        far = sorted(reach, key=lambda c: (-(abs(c[0] - pocket[0][0]) + abs(c[1] - pocket[0][1])), c))
        if len(far) < 2:
            raise Fail("meadow")
        meadow = [far[0]] + [n for n in neighbors(far[0]) if n in reach][:2]
        if len(meadow) < 2:
            raise Fail("meadow small")
        for c in meadow:
            cells[c] = "m"
    keep = set(robot_line) | set(meadow) | set(pocket) | set(fire)
    if fire_end:
        keep.add(fire_end)

    def chk_meadow():
        if not last:
            return True
        reach = _region(cells, pocket[0], extra_ok=lambda c: cells.get(c) == "F", blocked=set(arm) | {pedal})
        before = _region(cells, pocket[0], blocked=set(arm) | {pedal})
        return all(c in reach for c in meadow) and not any(c in before for c in meadow)
    if not chk_meadow():
        raise Fail("meadow path")
    _place_trees(cells, rng, keep, [chk_meadow], 0.3)
    # από τα «ίσια» στις πραγματικές θέσεις
    T = (lambda c: _tf(c, rot, flip))
    TD = (lambda d: _tf_dir(d, rot, flip))
    real = {T(c): ch for c, ch in cells.items()}
    pedal_r = T(pedal)
    start_r, D_r = T(start), TD(D)
    goals = [("robot", pedal_r)]
    plot = {"kind": "bars", "in": I, "out": outs, "entry": None, "first": first, "last": last,
            "cells": real, "stones": [], "goals": goals,
            "animals": [{"kind": a["kind"], "cell": T(a["cell"])} for a in animals],
            "meadow": [T(c) for c in meadow], "fire": [T(c) for c in fire], "arm": [T(c) for c in arm],
            "pedal": pedal_r, "chan_next": {T(c): [T(t) for t in nxt] for c, nxt in chan_next.items()},
            "path": [T(c) for c in path] if path else None, "bridges": []}
    if last:
        plot["fire_end"] = T(fire_end)
        plot["source"] = T(source)
        plot["spring"] = True
        plot["sluice"] = {"pedal": T(sluice["pedal"]), "arm": [T(c) for c in sluice["arm"]]}
    out = {"side": outs}
    if not last:
        out["gate"] = None
        out["extra"] = side_index(outs, pedal_r)
    # το πρόγραμμα: (στροφή,) περίμενε ώσπου απόσταση > 20, Κινήσου μπροστά k
    face = D_r
    program = []
    if prog.get("turn"):
        face = (D_r + rng.choice((1, 3))) % 4
        program.append(turn_block("left" if (face + 3) % 4 == D_r else "right", 1))
    program += [until_block(">", 20), move_block("forward", k)]
    plot["start"] = (start_r, face)
    plot["program"] = program
    plot["solution"] = []
    for lift in ((None,) if first else (1, 4, 9, 20)):
        pos, f2, st, ok, why = simulate_prog(plot, start_r, face, {}, program, lift)
        if not (ok and pos == pedal_r):
            raise Fail("bars program")
    if prog.get("fix"):
        plot["given"] = make_bug_sense(plot, program, first, rng)
    return plot, out


def make_bug_sense(plot, program, first, rng):
    """Το πρόγραμμα της «Διόρθωσε» με αισθητήρα: ένα λάθος (το σύμβολο, ο αριθμός cm ή τα κουτάκια)."""
    start, face = plot["start"]
    options = []
    for i, node in enumerate(program):
        if node["op"] == "until":
            options += [(i, "cmp", "<"), (i, "cm", 50)]
        elif node["op"] == "move":
            options += [(i, "n", n) for n in (node["n"] - 1, node["n"] + 1) if 1 <= n <= 9]
    rng.shuffle(options)
    options.sort(key=lambda o: o[1] == "n")          # πρώτα ένα λάθος στον αισθητήρα
    for i, field, value in options:
        bug = [dict(nd) for nd in program]
        bug[i][field] = value
        fails = False
        for lift in ((None,) if first else (4,)):
            pos, f2, st, ok, why = simulate_prog(plot, start, face, {}, bug, lift)
            if not ok or pos != plot["pedal"]:
                fails = True
        if fails:
            return bug
    raise Fail("bug")


def to_blocks(actions):
    """Κινήσεις → μπλοκ του «Προγραμμάτισε» (ίδιες κινήσεις στη σειρά = ένα μπλοκ με αριθμό)."""
    out = []
    for a in actions:
        if a in ("forward", "back"):
            node = move_block(a, 1)
        elif a in ("left", "right"):
            node = turn_block(a, 1)
        else:
            node = {"op": "wait", "n": 1}
        last = out[-1] if out else None
        if last and last["op"] == node["op"] and last.get("dir") == node.get("dir") and last["n"] < 9:
            last["n"] += 1
        else:
            out.append(node)
    return out


def flatten(program, path=()):
    """Μπλοκ → κινήσεις [(κίνηση, θέση του μπλοκ)]. Όπως στο «Προγραμμάτισε»: 1 δευτερόλεπτο = 1 κουτάκι
    ή ¼ στροφής. Ό,τι δεν είναι σωστό μπλοκ αγνοείται."""
    out = []
    if not isinstance(program, list):
        return out
    for i, node in enumerate(program):
        if len(out) >= MAX_ACTIONS:
            break
        if not isinstance(node, dict):
            continue
        p = path + (i,)
        op = node.get("op")
        try:
            n = max(0, min(10, int(node.get("n", 1))))
        except (TypeError, ValueError):
            n = 0
        if op == "move":
            out += [("back" if node.get("dir") == "back" else "forward", p)] * n
        elif op == "turn":
            out += [("left" if node.get("dir") == "left" else "right", p)] * n
        elif op == "wait":
            out += [("wait", p)] * n
        elif op == "repeat":
            body = flatten(node.get("body") or [], p + (0,))
            for _ in range(n):
                out += body
                if len(out) >= MAX_ACTIONS:
                    break
    return out[:MAX_ACTIONS]


def simulate(plot, pos, face, stones, actions, arm_up=True):
    """Τρέχει κινήσεις στο οικόπεδο (για τον έλεγχο). Επιστρέφει (θέση, κατεύθυνση, πέτρες, χωρίς χτύπημα)."""
    sp = solver_plot(plot)
    for a in actions:
        if a == "wait":
            continue
        pos, face, stones, what = step(sp, pos, face, a, stones, arm_up)
        if what == "bump":
            return pos, face, stones, False
    return pos, face, stones, True


def goals_met(goals, pos, stones):
    for g in goals:
        if g[0] == "stone" and ("fixed", g[2]) not in stones:
            return False
        if g[0] == "leave" and pos in set(g[1]):
            return False
        if g[0] == "robot" and pos != g[1]:
            return False
    return True


def program_start(plot, shape, leave, rng):
    """Πού ξεκινά το R2 ώστε το πρόγραμμα να είναι σύντομο. shape: line (ένα «Κινήσου»), turn (στροφή και
    «Κινήσου») ή corner (μπροστά, στροφή, μπροστά). Επιστρέφει (κουτάκι, κατεύθυνση, πρόγραμμα)."""
    s, p, push_d = plot["push"]
    sp = solver_plot(plot)
    stones = {c: "." for c in plot["stones"]}
    animals = {a["cell"] for a in plot["animals"]}
    back = (push_d + 2) % 4

    def free(c):
        return inside(c) and sp.robot_ok(c, set(stones), True) and c not in animals

    options = []
    for m in range(0, 4):
        q = add(p, back, m)
        if not all(free(add(p, back, i)) for i in range(0, m + 1)):
            break
        if shape == "line":
            options.append((q, push_d, [move_block("forward", m + 1)]))
        for f in ((push_d + 1) % 4, (push_d + 3) % 4):
            tdir = "right" if (f + 1) % 4 == push_d else "left"
            if shape == "turn":
                options.append((q, f, [turn_block(tdir, 1), move_block("forward", m + 1)]))
            elif shape == "corner":
                for a in range(1, 4):
                    if not free(add(q, (f + 2) % 4, a)):
                        break
                    options.append((add(q, (f + 2) % 4, a), f,
                                    [move_block("forward", a), turn_block(tdir, 1), move_block("forward", m + 1)]))
    rng.shuffle(options)
    if shape == "line":                       # λίγο πιο μακριά από την πέτρα: πιο ενδιαφέρον
        options.sort(key=lambda o: o[2][0]["n"] < 2)
    for start, face, program in options:
        if leave:
            program = program + [move_block("back", 1)]
        acts = [a for a, _ in flatten(program)]
        pos, f2, st, ok = simulate(plot, start, face, dict(stones), acts)
        if ok and goals_met(plot["goals"], pos, st):
            return start, face, program
    raise Fail("program start")


def make_bug(plot, program, rng):
    """Το πρόγραμμα της «Διόρθωσε»: το σωστό με ένα λάθος (έναν αριθμό ή μια στροφή) που δεν πετυχαίνει."""
    (start, face) = plot["start"]
    stones = {c: "." for c in plot["stones"]}
    options = []
    for i, node in enumerate(program):
        if node["op"] == "move":
            for n in (node["n"] - 1, node["n"] + 1, node["n"] + 2):
                if 1 <= n <= 9:
                    options.append((i, "n", n))
        elif node["op"] == "turn":
            options.append((i, "dir", "left" if node["dir"] == "right" else "right"))
    rng.shuffle(options)
    for i, field, value in options:
        bug = [dict(nd) for nd in program]
        bug[i][field] = value
        acts = [a for a, _ in flatten(bug)]
        pos, f2, st, ok = simulate(plot, start, face, dict(stones), acts)
        if not (ok and goals_met(plot["goals"], pos, st)):
            return bug
    raise Fail("bug")


def solver_plot(plot):
    cells = dict(plot["cells"])
    for c, ch in list(cells.items()):
        if ch in "a":
            cells[c] = "."
    return Plot(cells, arm=plot.get("arm") or ())


def plan(plot, pos, face, stones, goals, arm_up=True):
    """Όλες οι κινήσεις για τους στόχους του οικοπέδου με τη σειρά. stones: {(x, y): "."} ή και σταθερές."""
    sp = solver_plot(plot)
    acts = []
    for g in goals:
        if g[0] == "stone":
            target = g[2]
            if stones.get(("fixed", target)):
                continue

            def ok(p, st, target=target):
                return ("fixed", target) in st
        elif g[0] == "leave":
            target = set(g[1])

            def ok(p, st, target=target):
                return p not in target
        else:
            target = g[1]

            def ok(p, st, target=target):
                return p == target
        res = solve(sp, pos, face, stones, ok, arm_up=arm_up)
        if res is None:
            return None
        a, pos, face, stones = res
        acts += a
    return acts


# ------------------------------------------------------------------ όλο το δάσος
def free_sides_of(shape, idx):
    c, r = shape[idx]
    taken = set(shape)
    out = []
    for d in range(4):
        if (c + DX[d], r + DY[d]) not in taken:
            out.append(d)
    return out


def build(level_id, n, seed=0):
    """Το δάσος για n υπολογιστές (οικόπεδα 1..n με τη σειρά των θέσεων)."""
    lv = level(level_id)
    kind = lv["kind"]
    prog = lv.get("prog")
    n = max(MIN_PCS, min(MAX_PCS, n))
    sizes = team_sizes(n)
    origins, W, H = arrange(sizes)
    rng = random.Random(f"{level_id}-{n}-{seed}")
    grid = [["T"] * W for _ in range(H)]              # ό,τι δεν είναι οικόπεδο: δάσος
    plots, teams = [], []
    k = 0
    for t, size in enumerate(sizes):
        shape = TEAM_SHAPES[size]
        ox, oy = origins[t]
        team_plots = None
        for attempt in range(400):
            try:
                team_plots = _make_team(kind, shape, rng, prog)
                break
            except Fail:
                continue
        if team_plots is None:
            raise RuntimeError(f"δεν φτιάχτηκε το ποτάμι {t} ({level_id}, n={n}, seed={seed})")
        ids = []
        for j, pl in enumerate(team_plots):
            k += 1
            c, r = shape[j]
            pl["k"] = k
            pl["team"] = t
            pl["x0"], pl["y0"] = ox + c * PLOT, oy + r * PLOT
            plots.append(pl)
            ids.append(k)
        cols, rows = shape_size(size)
        teams.append({"name": f"Ποτάμι {TEAM_NAMES[t]}", "plots": ids, "box": [ox, oy, ox + cols, oy + rows]})
    # λωρίδες ανάμεσα στα ποτάμια: δέντρα, λίγοι βράχοι
    brng = random.Random(f"belt-{n}-{seed}")
    for y in range(H):
        for x in range(W):
            grid[y][x] = "T" if brng.random() < 0.82 else "R"
    return _assemble(lv, n, seed, W, H, grid, plots, teams)


def _make_team(kind, shape, rng, prog=None):
    out_plots = []
    ins = None
    m = len(shape)
    for j in range(m):
        outs = None
        if j < m - 1:
            (c1, r1), (c2, r2) = shape[j], shape[j + 1]
            outs = {(1, 0): RIGHT, (-1, 0): LEFT, (0, 1): DOWN, (0, -1): UP}[(c2 - c1, r2 - r1)]
        free = free_sides_of(shape, j)
        next_out = None
        if j < m - 2:
            (c2, r2), (c3, r3) = shape[j + 1], shape[j + 2]
            next_out = {(1, 0): RIGHT, (-1, 0): LEFT, (0, 1): DOWN, (0, -1): UP}[(c3 - c2, r3 - r2)]
        role = None
        if kind == "rock":
            role = "A" if j % 2 == 0 and j < m - 1 else ("B" if j % 2 == 1 else None)
        pl = None
        for attempt in range(80):
            try:
                pl, out = make_plot("cross" if kind == "rock" else kind, role, ins, outs, free, rng, next_out, prog)
                break
            except Fail:
                pl = None
        if pl is None:
            raise Fail("plot")
        out_plots.append(pl)
        if outs is not None:
            ins = ((outs + 2) % 4, out["gate"], out.get("extra"))
    return out_plots


def _assemble(lv, n, seed, W, H, grid, plots, teams):
    """Από τα οικόπεδα (τοπικά) στο δάσος (ολικές συντεταγμένες), σε μορφή που πάει και στο δίκτυο."""
    chan_next, sources, fires, seesaws, animals, meadows, gaps = {}, [], [], [], [], {}, []
    plot_info = []
    by_k = {pl["k"]: pl for pl in plots}
    for pl in plots:
        x0, y0 = pl["x0"], pl["y0"]

        def G(c, x0=x0, y0=y0):
            return (c[0] + x0, c[1] + y0)
        for y in range(PLOT):
            for x in range(PLOT):
                ch = pl["cells"].get((x, y), ".")
                grid[y0 + y][x0 + x] = ch
        for c, nxt in pl["chan_next"].items():
            chan_next[G(c)] = [G(t) for t in nxt]
        if pl["chan_next"]:
            if pl["first"] or pl.get("spring"):
                sources.append(G(pl["source"]))
        # η σύνδεση του αυλακιού με το επόμενο οικόπεδο
        if pl["kind"] not in ("cross", "bars") and not pl["last"]:
            exit_ = pl["path"][-1]
            nxt = by_k[pl["k"] + 1]
            chan_next[G(exit_)] = [(nxt["entry"][0] + nxt["x0"], nxt["entry"][1] + nxt["y0"])]
        if pl["fire"]:
            fires.append({"cells": [G(c) for c in pl["fire"]], "end": G(pl["fire_end"]), "team": pl["team"]})
        if pl.get("arm"):
            prev = by_k[pl["k"] - 1]
            seesaws.append({"from": prev["k"], "to": pl["k"], "arm": [G(c) for c in pl["arm"]],
                            "pedal": [prev["pedal"][0] + prev["x0"], prev["pedal"][1] + prev["y0"]],
                            "in": pl["in"]})
        if pl.get("sluice"):                     # το φράγμα του αυλακιού: πεντάλ και κλαδί στο ίδιο οικόπεδο
            sl = pl["sluice"]
            seesaws.append({"from": pl["k"], "to": pl["k"], "arm": [G(c) for c in sl["arm"]],
                            "pedal": list(G(sl["pedal"])), "in": dir_of(sl["pedal"], sl["arm"][0])})
        for a in pl["animals"]:
            animals.append({"kind": a["kind"], "cell": G(a["cell"]), "team": pl["team"], "home": pl["k"]})
        if pl["meadow"]:
            meadows.setdefault(pl["team"], []).extend(G(c) for c in pl["meadow"])
        (sx, sy), face = pl["start"]
        plot_info.append({"k": pl["k"], "team": pl["team"], "x0": x0, "y0": y0, "in": pl["in"], "out": pl["out"],
                          "first": pl["first"], "last": pl["last"], "start": [sx + x0, sy + y0, face],
                          "stones": [list(G(c)) for c in pl["stones"]],
                          "goals": [_goal_global(g, G) for g in pl["goals"]],
                          "solution": pl["solution"], "pedal": list(G(pl["pedal"])) if pl["pedal"] else None,
                          "arm": [list(G(c)) for c in pl["arm"]], "crossing": list(G(pl["crossing"])) if pl.get("crossing") else None,
                          "dam": list(G(pl["dam"])) if pl.get("dam") else None,
                          "program": pl.get("program"), "given": pl.get("given"),
                          "line": [list(G(c)) for c in pl.get("line") or []], "rock": pl.get("rock")})
    # ανοίγματα στον φράχτη για τα ζώα (πίστα 1): ζευγάρια κουτακιών σε διπλανά οικόπεδα
    for pl in plots:
        if pl["kind"] == "cross" and not pl["last"]:
            nxt = by_k[pl["k"] + 1]
            out_gap = pl["gaps"][-1]
            a = (out_gap[0] + pl["x0"], out_gap[1] + pl["y0"])
            b = (a[0] + DX[pl["out"]], a[1] + DY[pl["out"]])
            gaps.append([list(a), list(b)])
    # ο μεγάλος βράχος: οι δύο πέτρες (μία σε κάθε οικόπεδο) κουνιούνται μαζί
    rocks = []
    for pl in plots:
        if pl.get("rock") == "A" and pl["k"] + 1 in by_k and by_k[pl["k"] + 1].get("rock") == "B":
            rocks.append({"plots": [pl["k"], pl["k"] + 1], "dir": pl["push"][2]})
    return {
        "level": lv["id"], "kind": lv["kind"], "mode": lv["mode"], "palette": list(lv["palette"]),
        "rocks": rocks,
        "n": n, "seed": seed, "W": W, "H": H,
        "grid": ["".join(row) for row in grid],
        "plots": plot_info, "teams": teams,
        "chan": [[list(c), [list(t) for t in nxt]] for c, nxt in chan_next.items()],
        "sources": [list(c) for c in sources],
        "fires": [{"cells": [list(c) for c in f["cells"]], "end": list(f["end"]), "team": f["team"]} for f in fires],
        "seesaws": seesaws, "animals": [{"kind": a["kind"], "cell": list(a["cell"]), "team": a["team"],
                                         "home": a["home"]} for a in animals],
        "meadows": {str(t): [list(c) for c in cs] for t, cs in meadows.items()},
        "gaps": gaps,
    }


def _goal_global(g, G):
    if g[0] == "stone":
        return ["stone", g[1], list(G(g[2])), g[3]]
    if g[0] == "leave":
        return ["leave", [list(G(c)) for c in g[1]]]
    return [g[0], list(G(g[1]))]


def strip_answers(data):
    """Η πίστα όπως πάει στους μαθητές: χωρίς τις λύσεις."""
    out = dict(data)
    out["plots"] = [{k: v for k, v in p.items() if k not in ("solution", "program")} for p in data["plots"]]
    return out
