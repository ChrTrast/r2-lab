"""Οι κανόνες των Κύβων, χωρίς γραφικά, ώστε να ελέγχονται εύκολα.

Ο τοίχος έχει 10 στήλες. Οι κύβοι πέφτουν και στοιβάζονται σε κάθε στήλη.
Τα ύψη μετριούνται σε «μισά»: ολόκληρος κύβος = 2, μισός (πλακάκι) = 1.
Σε κάθε στήλη χωράνε 10 ολόκληροι κύβοι. Υπάρχουν 16 είδη κύβων (CUBES).
"""
from dataclasses import dataclass

COLS = 10
MAX_HALVES = 20

BLUE, RED, GREEN, YELLOW = "blue", "red", "green", "yellow"


@dataclass(frozen=True)
class Cube:
    halves: int     # 2 = ολόκληρος, 1 = μισός
    kind: str       # solid, air (διάφανος), diag_up, diag_down, split
    colors: tuple   # diag: (πάνω, κάτω) μέρος, split: (αριστερά, δεξιά)


CUBES = {
    1: Cube(2, "solid", (BLUE,)), 2: Cube(2, "solid", (RED,)),
    3: Cube(2, "solid", (GREEN,)), 4: Cube(2, "solid", (YELLOW,)),
    5: Cube(2, "air", ()),
    6: Cube(2, "diag_up", (BLUE, RED)), 7: Cube(2, "diag_down", (BLUE, RED)),
    8: Cube(2, "diag_up", (RED, BLUE)), 9: Cube(2, "diag_down", (RED, BLUE)),
    10: Cube(1, "solid", (BLUE,)), 11: Cube(1, "solid", (RED,)),
    12: Cube(1, "solid", (GREEN,)), 13: Cube(1, "solid", (YELLOW,)),
    14: Cube(1, "air", ()),
    15: Cube(1, "split", (RED, BLUE)), 16: Cube(1, "split", (BLUE, RED)),
}
FULL_CUBES = tuple(range(1, 10))
HALF_CUBES = tuple(range(10, 17))


def layers(column):
    """Η στήλη ως στρώσεις μισού ύψους, ώστε όσα φαίνονται ίδια να μετράνε ίδια.

    Δύο μπλε πλακάκια = ένας μπλε κύβος. Οι δίχρωμοι κύβοι δεν χωρίζονται.
    Οι διάφανοι κύβοι στην κορυφή της στήλης δεν μετράνε.
    """
    out = []
    for ctype in column:
        cube = CUBES[ctype]
        if cube.kind == "solid":
            out += [cube.colors[0]] * cube.halves
        elif cube.kind == "air":
            out += ["air"] * cube.halves
        else:
            out.append(ctype)
    while out and out[-1] == "air":
        out.pop()
    return tuple(out)


def shape(columns):
    """Το σχήμα χωρίς τις άδειες στήλες δεξιά και αριστερά: χτίζεται σε όποιο σημείο θέλει το παιδί."""
    cols = [layers(c) for c in columns]
    while cols and not cols[0]:
        cols.pop(0)
    while cols and not cols[-1]:
        cols.pop()
    return tuple(cols)


def matches(columns, target):
    goal = shape(target)
    return bool(goal) and shape(columns) == goal


class Wall:
    def __init__(self):
        self.columns = [[] for _ in range(COLS)]
        self.history = []   # σε ποιες στήλες έπεσαν οι κύβοι, με τη σειρά

    def height(self, col):
        return sum(CUBES[t].halves for t in self.columns[col])

    def fits(self, col, ctype):
        return 0 <= col < COLS and self.height(col) + CUBES[ctype].halves <= MAX_HALVES

    def drop(self, col, ctype):
        if not self.fits(col, ctype):
            return False
        self.columns[col].append(ctype)
        self.history.append(col)
        return True

    def undo(self):
        """Βγάζει τον τελευταίο κύβο που μπήκε. Επιστρέφει (στήλη, κύβος) ή None."""
        if not self.history:
            return None
        col = self.history.pop()
        return col, self.columns[col].pop()

    def take_top(self, col):
        """Βγάζει τον πάνω κύβο μιας στήλης."""
        if not self.columns[col]:
            return None
        ctype = self.columns[col].pop()
        last = len(self.history) - 1 - self.history[::-1].index(col)
        del self.history[last]
        return ctype

    def clear(self):
        self.columns = [[] for _ in range(COLS)]
        self.history = []

    @property
    def empty(self):
        return not self.history
