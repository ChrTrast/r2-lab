"""Το «μάθημα» των Πράξεων: νέες πράξεις σε κάθε προσπάθεια και λάθος απαντήσεις που μπερδεύουν.

Κάθε «φτιάχτης» (add10, sub10, …) δίνει (κείμενο, σωστή απάντηση, λάθος απαντήσεις).
Οι λάθος είναι αυτές που κάνουν συχνά τα παιδιά: ένα πάνω/κάτω, ±10 στις δεκάδες,
το διπλανό αποτέλεσμα στην προπαίδεια (π.χ. 7 × 8: 48 ή 63 αντί για 56).
"""
from games.runner import art


def near(r, steps, lo=0, hi=200):
    out = []
    for s in steps:
        for v in (r - s, r + s):
            if lo <= v <= hi and v != r and v not in out:
                out.append(v)
    return out


# ------------------------------------------------------------ οι πράξεις
def add10(rng):
    a = rng.randint(1, 8)
    b = rng.randint(1, 10 - a)
    return f"{a} + {b} = ?", a + b, near(a + b, (1, 2))


def sub10(rng):
    a = rng.randint(3, 10)
    b = rng.randint(1, a - 1)
    return f"{a} − {b} = ?", a - b, near(a - b, (1, 2))


def mixed20(rng):
    if rng.random() < 0.5:
        a = rng.randint(4, 15)
        b = rng.randint(2, 20 - a)
        r, text = a + b, f"{a} + {b} = ?"
    else:
        a = rng.randint(11, 20)
        b = rng.randint(2, 9)
        r, text = a - b, f"{a} − {b} = ?"
    return text, r, near(r, (1, 2, 10), hi=20)


def tens100(rng):
    kind = rng.randrange(4)
    if kind == 0:                                   # 40 + 30
        a = 10 * rng.randint(1, 8)
        b = 10 * rng.randint(1, (100 - a) // 10)
        r, text = a + b, f"{a} + {b} = ?"
    elif kind == 1:                                 # 56 + 20
        a = rng.choice([n for n in range(12, 80) if n % 10])
        b = 10 * rng.randint(1, (100 - a) // 10)
        r, text = a + b, f"{a} + {b} = ?"
    elif kind == 2:                                 # 70 − 20
        a = 10 * rng.randint(3, 10)
        b = 10 * rng.randint(1, a // 10 - 1)
        r, text = a - b, f"{a} − {b} = ?"
    else:                                           # 85 − 30
        a = rng.choice([n for n in range(31, 100) if n % 10])
        b = 10 * rng.randint(1, a // 10 - 1)
        r, text = a - b, f"{a} − {b} = ?"
    return text, r, near(r, (10, 1), hi=100)


def _times(a, b, rng, both=True):
    """a × b. Λάθος: το διπλανό αποτέλεσμα του a (και του b, αν both)."""
    r = a * b
    cands = [a * (b + 1), a * (b - 1)] + ([(a + 1) * b, (a - 1) * b] if both else [])
    wrongs = sorted({v for v in cands if 0 < v <= 100 and v != r})
    if rng.random() < 0.5:
        a, b = b, a
    return f"{a} × {b} = ?", r, wrongs


def times2510(rng):
    return _times(rng.choice((2, 5, 10)), rng.randint(1, 10), rng, both=False)


def times_all(rng):
    return _times(rng.randint(2, 9), rng.randint(2, 9), rng)


# ------------------------------------------------------------ το μάθημα
class MathLesson:
    item = "door"

    def __init__(self, title, make, count=8):
        self.goal = f"{title}! Πέρνα από την πόρτα με τη σωστή απάντηση."
        self.make = make
        self.seq = [None] * count            # μία πόρτα για κάθε πράξη
        self.questions = []
        self.done_text = "Έλυσες όλες τις πράξεις!"

    def pairs(self, rng):
        """Νέες πράξεις (όλες διαφορετικές) για μια προσπάθεια: (σωστή, λάθος) για κάθε πόρτα."""
        self.questions = []
        seen = set()
        while len(self.questions) < len(self.seq):
            q = self.make(rng)
            if q[0] not in seen and q[2]:
                seen.add(q[0])
                self.questions.append(q)
        return [(str(r), str(rng.choice(wrongs))) for _, r, wrongs in self.questions]

    def solved(self, i):
        text, r, _ = self.questions[i]
        return text.replace("?", str(r))

    def wrong_text(self, i, label):
        return f"Ωχ! Όχι το {label}.", self.solved(i)

    def draw_panel(self, surf, center, got, time, since=9.0):
        n = len(self.seq)
        if not self.questions:
            return
        if got and (since < 1.0 or got == n):
            art.math_panel(surf, center, self.solved(got - 1), got, n, solved=True, time=time)
        else:
            art.math_panel(surf, center, self.questions[got][0], got, n, time=time)
