"""Το R2 πάνω στη ράγα των Κύβων, χωρίς γραφικά.

Το R2 κινείται μόνο δεξιά-αριστερά, πάνω από τον τοίχο, και κοιτάει πάντα δεξιά.
Κρατάει τον κύβο μπροστά του. Πηγαίνει ώσπου ο κύβος να βρεθεί πάνω από τη στήλη
και τον σπρώχνει μέσα. Οι κύβοι περιμένουν τη σειρά τους, και όσο περισσότεροι
περιμένουν τόσο πιο γρήγορα πηγαίνει. Όταν δεν έχει δουλειά, μένει εκεί που είναι
ή πηγαίνει στη θέση park_x (ο φορτιστής), αν του τη δώσουν.
"""
import math

SPEED = 560            # pixels το δευτερόλεπτο
ACCEL = 3600           # πόσο γρήγορα ξεκινά και φρενάρει
PUSH_TIME = 0.16       # πόσο κρατάει το σπρώξιμο του κύβου
HURRY_STEP, HURRY_MAX = 0.5, 3.0


class Carrier:
    def __init__(self, x, wheel_r=12.0):
        self.x = float(x)
        self.v = 0.0               # ταχύτητα (πάντα θετική, η φορά βγαίνει από τον στόχο)
        self.wheel_r = wheel_r
        self.spin = 0.0            # πόσο έχει γυρίσει η ρόδα (μοίρες)
        self.jobs = []             # [{"x", "col", "n", "ctype"}]: οι κύβοι που περιμένουν
        self.push = 0.0            # 0..1: πόσο έχει σπρώξει τον πρώτο κύβο
        self.park_x = None
        self.parked = False

    @property
    def busy(self):
        return bool(self.jobs)

    @property
    def hurry(self):
        return min(HURRY_MAX, 1 + HURRY_STEP * max(0, len(self.jobs) - 1))

    @property
    def carrying(self):
        return self.jobs[0] if self.jobs else None

    def carry(self, x, col, n, ctype):
        """Νέα δουλειά: πήγαινε στο x και άφησε τον κύβο ctype (ο n-οστός της στήλης col)."""
        self.jobs.append({"x": float(x), "col": col, "n": n, "ctype": ctype})

    def cancel(self, col, n):
        """Ο κύβος βγήκε από τον τοίχο πριν τον αφήσει το R2 (Αναίρεση, δεξί κλικ)."""
        for i, job in enumerate(self.jobs):
            if (job["col"], job["n"]) == (col, n):
                if i == 0:
                    self.push = 0.0
                del self.jobs[i]
                return True
        return False

    def clear(self):
        self.jobs.clear()
        self.push = 0.0

    def place(self, x):
        """Βάζει το R2 κατευθείαν στο x, σταματημένο και χωρίς δουλειές."""
        self.x = float(x)
        self.v = 0.0
        self.clear()
        self.park_x = None
        self.parked = False

    def _drive(self, target, dt, events):
        """Ένα βήμα προς το target. Επιστρέφει True όταν έχει φτάσει."""
        d = target - self.x
        if abs(d) < 0.5:
            self.x = target
            self.v = 0.0
            return True
        if self.v == 0.0:
            events.append(("drive",))
        top = min(SPEED * self.hurry, math.sqrt(2 * ACCEL * abs(d)))
        self.v = min(top, self.v + ACCEL * dt)
        step = min(abs(d), max(self.v, 40.0) * dt)
        self.x += math.copysign(step, d)
        self.spin += math.copysign(math.degrees(step / self.wheel_r), d)
        return False

    def update(self, dt):
        """Προχωρά το R2. Επιστρέφει γεγονότα: ("drive",) όταν ξεκινά να κινείται,
        ("drop", job) όταν αφήνει έναν κύβο, ("park",) όταν φτάνει στο park_x."""
        events = []
        if self.jobs:
            self.parked = False
            job = self.jobs[0]
            if self._drive(job["x"], dt, events):
                self.push += dt / (PUSH_TIME / self.hurry)
                if self.push >= 1.0:
                    self.push = 0.0
                    events.append(("drop", self.jobs.pop(0)))
        elif self.park_x is not None:
            if self._drive(self.park_x, dt, events) and not self.parked:
                self.parked = True
                events.append(("park",))
        else:
            self.parked = False
            self.v = 0.0
        return events
