"""Η λογική του «Ακολούθησε», χωρίς γραφικά, ώστε να ελέγχεται εύκολα.

Το ταμπλό έχει 5 στήλες και 4 σειρές. Ένα κελί είναι (στήλη, σειρά) και
η σειρά 0 είναι η πιο πίσω. Το R2 ξεκινά από μια γραμμή δεξιά της
σειράς 2 και πρέπει να φτάσει στον φορτιστή, αριστερά της σειράς 1.
Αν η γραμμή κόβεται ή δεν ταιριάζει, το R2 κάνει αναστροφή και γυρίζει στην αρχή.

Οι πίστες 12-15 έχουν και:
- σταθερά κομμάτια (βιδωμένα στο ταμπλό, δεν βγαίνουν), ανάμεσά τους γέφυρες στο ποτάμι
  και η διασταύρωση, όπου το R2 πηγαίνει πάντα ευθεία, άρα περνά από εκεί δύο φορές,
- γρανάζια: η μπάρα του φορτιστή ανοίγει μόνο όταν το R2 τα έχει μαζέψει όλα.
"""
import math

W, N, E, S = "W", "N", "E", "S"
OPPOSITE = {W: E, E: W, N: S, S: N}
STEP = {W: (-1, 0), E: (1, 0), N: (0, -1), S: (0, 1)}
SIDE_MID = {W: (0.0, 0.5), E: (1.0, 0.5), N: (0.5, 0.0), S: (0.5, 1.0)}

# Τα 6 κομμάτια της μαύρης γραμμής, με τη σειρά που έχουν στον δίσκο.
# Κάθε κομμάτι ενώνει δύο πλευρές του κελιού.
PIECES = {1: (W, S), 2: (W, N), 3: (N, E), 4: (S, E), 5: (N, S), 6: (W, E)}
PIECE_TYPES = tuple(PIECES)
CROSS = 7      # η διασταύρωση: μόνο σταθερή στο ταμπλό, το R2 τη διασχίζει ευθεία

COLS, ROWS = 5, 4
START_ROW, END_ROW = 2, 1
FIRST_CELL = (COLS - 1, START_ROW)   # το πρώτο κελί του ταμπλό που συναντά το R2
CHARGER_GATE = (-1, END_ROW)         # η σταθερή γραμμή αμέσως μετά το ταμπλό
CHARGER = (-2, END_ROW)              # εδώ σταματά το R2 στο τέλος (ο φορτιστής)
HOME = (COLS + 1, START_ROW)         # εδώ περιμένει το R2 (η «ΑΡΧΗ»)
FIXED_LINE = frozenset({CHARGER_GATE, CHARGER, (COLS, START_ROW), HOME})


def other_end(ptype, side):
    """Από ποια πλευρά βγαίνει το R2 αν μπει από `side` (ή None)."""
    if ptype == CROSS:
        return OPPOSITE[side]
    a, b = PIECES[ptype]
    if side == a:
        return b
    if side == b:
        return a
    return None


def neighbor(cell, side):
    dc, dr = STEP[side]
    return (cell[0] + dc, cell[1] + dr)


def is_straight(a, b):
    return OPPOSITE[a] == b


def path_length(a, b):
    return 1.0 if is_straight(a, b) else math.pi / 4


def point_on_piece(entry, exit_, t):
    """Θέση (u, v) και κατεύθυνση (du, dv) μέσα στο κελί.

    Το t πάει από 0 (πλευρά εισόδου) ως 1 (πλευρά εξόδου).
    Οι στροφές είναι τεταρτοκύκλια με κέντρο τη γωνία του κελιού.
    """
    (x0, y0), (x1, y1) = SIDE_MID[entry], SIDE_MID[exit_]
    if is_straight(entry, exit_):
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), (x1 - x0, y1 - y0)
    cx = 0.0 if W in (entry, exit_) else 1.0
    cy = 0.0 if N in (entry, exit_) else 1.0
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    a = a0 + d * t
    sign = 1.0 if d > 0 else -1.0
    pos = (cx + 0.5 * math.cos(a), cy + 0.5 * math.sin(a))
    return pos, (-math.sin(a) * sign, math.cos(a) * sign)


class Board:
    """Το ταμπλό: τα κομμάτια του παιδιού, τα κλειστά κελιά, τα σταθερά κομμάτια, τα γρανάζια."""

    def __init__(self, blocked=(), fixed=(), gears=()):
        self.blocked = set(blocked)
        self.fixed = dict(fixed)
        self.gears = frozenset(gears)
        self.pieces = {}

    @staticmethod
    def on_board(cell):
        return 0 <= cell[0] < COLS and 0 <= cell[1] < ROWS

    def free(self, cell):
        """Μπορεί να μπει εδώ κομμάτι; (όχι σε δέντρο, νερό ή σταθερό κομμάτι)"""
        return self.on_board(cell) and cell not in self.blocked and cell not in self.fixed

    def piece_at(self, cell):
        if cell in FIXED_LINE:
            return 6
        if cell in self.fixed:
            return self.fixed[cell]
        return self.pieces.get(cell)

    def place(self, cell, ptype):
        self.pieces[cell] = ptype

    def remove(self, cell):
        return self.pieces.pop(cell, None)

    def trace(self):
        """Ακολουθεί τη γραμμή από την αρχή, χωρίς να νοιάζεται για τα γρανάζια.

        Επιστρέφει (φτάνει στη μπάρα του φορτιστή;, τα κελιά που πέρασε με τη σειρά).
        Στη διασταύρωση το ίδιο κελί μπαίνει δύο φορές.
        """
        cell, entry = FIRST_CELL, E
        visited = []
        for _ in range(4 * COLS * ROWS):
            if cell == CHARGER_GATE and entry == E:
                return True, visited
            if not self.on_board(cell):
                return False, visited
            ptype = self.piece_at(cell)
            out = other_end(ptype, entry) if ptype else None
            if out is None:
                return False, visited
            visited.append(cell)
            cell, entry = neighbor(cell, out), OPPOSITE[out]
        return False, visited

    def missing_gears(self, visited):
        return self.gears - set(visited)

    def follow(self):
        """Επιστρέφει (το R2 θα φτάσει στον φορτιστή;, τα κελιά που πέρασε)."""
        reached, visited = self.trace()
        return reached and not self.missing_gears(visited), visited


def iter_solutions(pieces, blocked=(), fixed=(), gears=()):
    """Όλες οι διαδρομές που λύνουν ένα επίπεδο, η καθεμιά λίστα από (κελί, κομμάτι).

    Μετράνε μόνο τα κομμάτια του παιδιού, όχι τα σταθερά.
    """
    counts = dict(zip(PIECE_TYPES, pieces))
    blocked, fixed, gears = set(blocked), dict(fixed), frozenset(gears)

    def search(cell, entry, used, got):
        if cell == CHARGER_GATE and entry == E:
            if gears <= got:
                yield []
            return
        if not Board.on_board(cell) or cell in blocked:
            return
        got = got | ({cell} & gears)
        if cell in fixed:
            ptype = fixed[cell]
            out = other_end(ptype, entry)
            # η διασταύρωση δέχεται μία οριζόντια και μία κάθετη διέλευση
            key = (cell, entry in (W, E)) if ptype == CROSS else cell
            if out is None or key in used:
                return
            yield from search(neighbor(cell, out), OPPOSITE[out], used | {key}, got)
            return
        if cell in used:
            return
        for ptype in PIECE_TYPES:
            out = other_end(ptype, entry)
            if out is None or counts[ptype] == 0:
                continue
            counts[ptype] -= 1
            for rest in search(neighbor(cell, out), OPPOSITE[out], used | {cell}, got):
                yield [(cell, ptype)] + rest
            counts[ptype] += 1

    return search(FIRST_CELL, E, frozenset(), frozenset())


def solve(pieces, blocked=(), fixed=(), gears=()):
    """Βρίσκει μια λύση για ένα επίπεδο: λίστα από (κελί, κομμάτι), ή None."""
    return next(iter_solutions(pieces, blocked, fixed, gears), None)


class Robot:
    """Το R2 ακολουθεί τη μαύρη γραμμή.

    Καταστάσεις: idle (περιμένει), running, turning (κάνει αναστροφή), arrived.
    Όταν βρει κελί χωρίς σωστή γραμμή, ή κλειστή τη μπάρα του φορτιστή, γυρίζει πίσω ως την αφετηρία.
    Μαζεύει τα γρανάζια που περνά (collected) και τα αφήνει ξανά στη θέση τους όταν γυρίσει στην αρχή.
    """

    MAX_SPEED = 1.15   # κελιά το δευτερόλεπτο
    ACCEL = 1.4
    TURN_TIME = 0.9

    def __init__(self):
        self.reset()

    def reset(self):
        self.cell = HOME
        self.entry, self.exit = E, W
        self.t = 0.5
        self.state = "idle"
        self.speed = 0.0
        self.turn_progress = 0.0
        self.collected = set()

    def start(self):
        if self.state != "idle":
            return False
        self.state = "running"
        self.speed = 0.0
        return True

    @property
    def moving(self):
        return self.state in ("running", "turning")

    def occupied(self):
        """Τα κελιά που πατάει το R2 (δεν αλλάζουν όσο είναι πάνω τους)."""
        cells = {self.cell}
        if self.t < 0.35:
            cells.add(neighbor(self.cell, self.entry))
        return cells

    def pose(self):
        """Θέση (X, Y) πάνω στο ταμπλό και κατεύθυνση (hx, hy)."""
        (u, v), (du, dv) = point_on_piece(self.entry, self.exit, self.t)
        if self.state == "turning":
            p = self.turn_progress
            a = math.pi * p * p * (3 - 2 * p)
            c, s = math.cos(a), math.sin(a)
            du, dv = du * c - dv * s, du * s + dv * c
        return self.cell[0] + u, self.cell[1] + v, du, dv

    def _stop_point(self):
        if self.cell == CHARGER and self.exit == W:
            return 0.5
        if self.cell == HOME and self.exit == E:
            return 0.5
        return None

    def _target_speed(self):
        length = path_length(self.entry, self.exit)
        stop = self._stop_point()
        if stop is not None:
            left = max(0.0, stop - self.t) * length
        else:
            nxt = neighbor(self.cell, self.exit)
            if (nxt == CHARGER and self.exit == W) or (nxt == HOME and self.exit == E):
                left = (1.0 - self.t) * length + 0.5
            else:
                return self.MAX_SPEED
        return min(self.MAX_SPEED, 0.2 + left * 2.0)

    def update(self, dt, board):
        """Προχωρά το R2. Επιστρέφει γεγονότα: enter, gear, turn, barrier, home, arrived."""
        events = []
        if self.state == "turning":
            self.turn_progress += dt / self.TURN_TIME
            if self.turn_progress >= 1.0:
                self.entry, self.exit = self.exit, self.entry
                self.t = 0.0
                self.turn_progress = 0.0
                self.state = "running"
                self.speed = 0.0
            return events
        if self.state != "running":
            return events

        target = self._target_speed()
        self.speed = min(target, self.speed + self.ACCEL * dt)
        dist = self.speed * dt
        while dist > 0 and self.state == "running":
            length = path_length(self.entry, self.exit)
            stop = self._stop_point()
            end_t = stop if stop is not None and self.t <= stop else 1.0
            room = (end_t - self.t) * length
            if dist < room:
                self.t += dist / length
                break
            dist -= room
            self.t = end_t
            if end_t < 1.0:
                self.speed = 0.0
                if self.cell == CHARGER:
                    self.state = "arrived"
                    events.append("arrived")
                else:
                    # Πίσω στην αφετηρία: κοιτάζει ξανά προς το ταμπλό, τα γρανάζια ξαναμπαίνουν στη θέση τους.
                    self.state = "idle"
                    self.entry, self.exit = self.exit, self.entry
                    self.collected = set()
                    events.append("home")
                break
            nxt = neighbor(self.cell, self.exit)
            entry = OPPOSITE[self.exit]
            ptype = board.piece_at(nxt)
            out = other_end(ptype, entry) if ptype else None
            barrier = nxt == CHARGER_GATE and entry == E and bool(board.gears - self.collected)
            if out is not None and not barrier:
                self.cell, self.entry, self.exit, self.t = nxt, entry, out, 0.0
                events.append("enter")
            else:
                self.state = "turning"
                self.turn_progress = 0.0
                self.speed = 0.0
                events.append("barrier" if barrier else "turn")
        # το γρανάζι μαζεύεται όταν το R2 φτάσει στη μέση του κελιού
        if self.cell in board.gears and self.cell not in self.collected and self.t >= 0.45:
            self.collected.add(self.cell)
            events.append("gear")
        return events
