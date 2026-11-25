"""Οι κανόνες του Λαβύρινθου, χωρίς γραφικά, ώστε να ελέγχονται εύκολα.

Ο λαβύρινθος είναι πλέγμα από τετράγωνα. Το R2 στέκεται σε ένα τετράγωνο και κοιτάει
προς μία από τις 4 κατευθύνσεις. Κινείται όπως το πραγματικό ρομπότ:
  μπροστά / πίσω:          ένα τετράγωνο προς τα εκεί που κοιτάει / ανάποδα, χωρίς να γυρίσει
  στρίψε αριστερά / δεξιά: γυρίζει 90° επί τόπου, χωρίς να προχωρήσει
Αν από εκεί που πάει έχει τοίχο, δεν κινείται (χτυπά στον τοίχο).
"""
UP, RIGHT, DOWN, LEFT = range(4)
STEP = {UP: (0, -1), RIGHT: (1, 0), DOWN: (0, 1), LEFT: (-1, 0)}
COMMANDS = ("forward", "back", "left", "right")
SECONDS = 1     # στο πρόγραμμα: 1 τετράγωνο ή ¼ στροφής = «για 1 δευτερόλεπτα»


def direction(a, b):
    """Η κατεύθυνση από το τετράγωνο a στο διπλανό του b."""
    return next(d for d, step in STEP.items() if step == (b[0] - a[0], b[1] - a[1]))


class Maze:
    def __init__(self, text):
        """text: ο λαβύρινθος ζωγραφισμένος με χαρακτήρες (δες το levels.py)."""
        self.grid = [ln.strip() for ln in text.strip("\n").splitlines() if ln.strip()]
        h, w = len(self.grid), len(self.grid[0]) if self.grid else 0
        if h < 3 or w < 3 or h % 2 == 0 or w % 2 == 0 or any(len(row) != w for row in self.grid):
            raise ValueError("ο λαβύρινθος πρέπει να είναι ορθογώνιο με μονό πλάτος και ύψος")
        self.cols, self.rows = w // 2, h // 2
        self.start = self.goal = None
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch in "SG":
                    if x % 2 == 0 or y % 2 == 0:
                        raise ValueError(f"το {ch} πρέπει να είναι σε τετράγωνο (μονή γραμμή και στήλη)")
                    if ch == "S":
                        self.start = (x // 2, y // 2)
                    else:
                        self.goal = (x // 2, y // 2)
        if self.start is None or self.goal is None:
            raise ValueError("λείπει το S (αφετηρία) ή το G (φορτιστής)")

    def cells(self):
        return [(c, r) for r in range(self.rows) for c in range(self.cols)]

    def is_open(self, cell, d):
        """Αν από το τετράγωνο cell μπορεί να πάει προς την κατεύθυνση d (δεν έχει τοίχο)."""
        dx, dy = STEP[d]
        x, y = 2 * cell[0] + 1 + dx, 2 * cell[1] + 1 + dy
        if not (0 < x < len(self.grid[0]) - 1 and 0 < y < len(self.grid) - 1):
            return False
        return self.grid[y][x] != "#"

    @staticmethod
    def neighbor(cell, d):
        return (cell[0] + STEP[d][0], cell[1] + STEP[d][1])

    def start_facing(self):
        return next((d for d in (RIGHT, DOWN, LEFT, UP) if self.is_open(self.start, d)), RIGHT)

    def solve(self, start=None):
        """Η πιο σύντομη διαδρομή (λίστα τετραγώνων) από το start στον φορτιστή, ή None."""
        start = start or self.start
        prev, todo = {start: None}, [start]
        for cell in todo:
            for d in STEP:
                if self.is_open(cell, d):
                    n = self.neighbor(cell, d)
                    if n not in prev:
                        prev[n] = cell
                        todo.append(n)
        if self.goal not in prev:
            return None
        path, cell = [], self.goal
        while cell is not None:
            path.append(cell)
            cell = prev[cell]
        return path[::-1]


def commands_for(path, facing):
    """Τα πατήματα κουμπιών που περνούν το R2 από τη διαδρομή path (μόνο μπροστά και στροφές)."""
    out = []
    for a, b in zip(path, path[1:]):
        d = direction(a, b)
        turn = (d - facing) % 4
        out += {0: [], 1: ["right"], 2: ["right", "right"], 3: ["left"]}[turn]
        facing = d
        out.append("forward")
    return out


class Robot:
    def __init__(self, maze):
        self.maze = maze
        self.cell = maze.start
        self.facing = maze.start_facing()
        self.trail = [maze.start]       # τα τετράγωνα από όπου πέρασε, με τη σειρά
        self.done = False
        self.bumps = 0

    def command(self, name):
        """Εκτελεί μία εντολή. Επιστρέφει τι έγινε:

        ("turn", παλιά, νέα κατεύθυνση)    στροφή επί τόπου
        ("move", από, προς)                 πήγε στο διπλανό τετράγωνο
        ("bump", τετράγωνο, κατεύθυνση)     είχε τοίχο, δεν κινήθηκε
        ("done",)                           έφτασε στον φορτιστή (μαζί με το "move")
        """
        if name not in COMMANDS:
            raise ValueError(name)
        if self.done:
            return []
        if name in ("left", "right"):
            old = self.facing
            self.facing = (old + (1 if name == "right" else -1)) % 4
            return [("turn", old, self.facing)]
        d = self.facing if name == "forward" else (self.facing + 2) % 4
        if not self.maze.is_open(self.cell, d):
            self.bumps += 1
            return [("bump", self.cell, d)]
        old = self.cell
        self.cell = self.maze.neighbor(old, d)
        self.trail.append(self.cell)
        events = [("move", old, self.cell)]
        if self.cell == self.maze.goal:
            self.done = True
            events.append(("done",))
        return events


class Program:
    """Το πρόγραμμα που γράφεται μόνο του όσο το παιδί οδηγεί το R2, με τις εντολές του Mind+.

    Γράφεται μόνο ό,τι έκανε το R2 (όχι τα χτυπήματα στον τοίχο). Ίδιες εντολές στη σειρά
    γίνονται ένα μπλοκ με περισσότερα δευτερόλεπτα: μπροστά, μπροστά → «μπροστά για 2 δευτερόλεπτα».
    """

    def __init__(self):
        self.blocks = []          # [εντολή, πόσες φορές]

    def __len__(self):
        return len(self.blocks)

    def add(self, name):
        """Γράφει μία εντολή. Επιστρέφει ποιο μπλοκ γράφτηκε ή μεγάλωσε."""
        if name not in COMMANDS:
            raise ValueError(name)
        if self.blocks and self.blocks[-1][0] == name:
            self.blocks[-1][1] += 1
        else:
            self.blocks.append([name, 1])
        return len(self.blocks) - 1

    def seconds(self, index):
        return self.blocks[index][1] * SECONDS

    def steps(self):
        """Η εκτέλεση βήμα βήμα: (μπλοκ, εντολή, πρώτο βήμα του μπλοκ, τελευταίο βήμα του μπλοκ)."""
        return [(i, name, j == 0, j == n - 1) for i, (name, n) in enumerate(self.blocks) for j in range(n)]
