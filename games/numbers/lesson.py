"""Το «μάθημα» των Αριθμών: ποιος αριθμός έρχεται μετά, και ποιος είναι ο λάθος της κάθε επιλογής."""
from games.runner import art


class NumbersLesson:
    def __init__(self, label, goal, seq):
        self.label = label           # στο πάνελ, π.χ. «Ανά 2:»
        self.goal = goal             # στην αρχή της πίστας
        self.seq = seq
        self.step = seq[1] - seq[0]
        self.done_text = "Μάζεψες όλους τους αριθμούς!"

    def wrongs(self, i):
        """Οι λάθος αριθμοί που μπερδεύουν: ένα πάνω/κάτω, ο προηγούμενος, ο μεθεπόμενος."""
        n, k = self.seq[i], self.step
        return sorted({n + 1, n - 1, n + k, n - k, n + 2 * k} - {n, 0} - {m for m in (n - 1, n - k) if m < 0})

    def pairs(self, rng):
        return [(str(n), str(rng.choice(self.wrongs(i)))) for i, n in enumerate(self.seq)]

    def wrong_text(self, i, label):
        if i == 0:
            return f"Ωχ! Όχι το {label}.", f"Ξεκινάμε από το {self.seq[0]}."
        return f"Ωχ! Όχι το {label}.", f"Μετά το {self.seq[i - 1]} έρχεται το {self.seq[i]}."

    def draw_panel(self, surf, center, got, time, since=9.0):
        art.numbers_panel(surf, center, self.label, self.seq, got, time)
