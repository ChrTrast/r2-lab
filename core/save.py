"""Θυμάται ποια επίπεδα τελείωσε το παιδί, μόνο όσο είναι ανοιχτό το πρόγραμμα.

Δεν γράφεται σε αρχείο: κάθε φορά που ανοίγει το πρόγραμμα όλα ξεκινούν από την αρχή
(πίστα 1, χωρίς αστέρια), ώστε το επόμενο παιδί να μη βρίσκει το παιχνίδι του προηγούμενου.
Αν βγει στο μενού και ξαναμπεί, συνεχίζει από εκεί που ήταν.
"""


class Progress:
    def __init__(self):
        self.data = {}

    def completed(self, game):
        return set(self.data.get(game, []))

    def mark(self, game, level):
        self.data[game] = sorted(self.completed(game) | {level})
