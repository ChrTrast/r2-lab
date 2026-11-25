"""Το «μάθημα» των Λέξεων: τα γράμματα των λέξεων με τη σειρά και οι λάθος επιλογές.

Οι λέξεις είναι με κεφαλαία (χωρίς τόνους). Σε κάθε επιλογή η μία φούσκα έχει το σωστό γράμμα.
Η άλλη έχει ένα τυχαίο γράμμα ή, με traps=True, μια «παγίδα ορθογραφίας»: Ο αντί για Ω,
Ι ή Υ αντί για Η, κ.λπ. (μόνο όπου το λάθος ακούγεται ίδιο, όχι μέσα σε ΟΥ, ΑΙ, ΕΙ, ΟΙ).
"""
from games.runner import art
from . import pictures

ALPHABET = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
SOUND_ALIKE = {"Ο": "Ω", "Ω": "Ο", "Η": "ΙΥ", "Ι": "ΗΥ", "Υ": "ΗΙ"}


class WordsLesson:
    def __init__(self, words, traps=False):
        self.words = words                      # [(λέξη, ζωγραφιά), ...]
        self.traps = traps
        self.goal = "Δες τη ζωγραφιά και μάζεψε τα γράμματα με τη σειρά."
        self.done_text = "Έγραψες όλες τις λέξεις!"
        self.letters = []                       # (ποια λέξη, θέση μέσα στη λέξη)
        for w, (word, _) in enumerate(words):
            for pos in range(len(word)):
                self.letters.append((w, pos))
        self.seq = [words[w][0][pos] for w, pos in self.letters]

    def trap(self, i):
        """Τα γράμματα που ακούγονται ίδια με το σωστό σε αυτή τη θέση (ή κενό)."""
        w, pos = self.letters[i]
        word = self.words[w][0]
        ch = word[pos]
        prev = word[pos - 1] if pos else ""
        nxt = word[pos + 1] if pos + 1 < len(word) else ""
        if ch == "Υ" and prev in "ΑΕΟ":         # ΑΥ, ΕΥ, ΟΥ
            return ""
        if ch == "Ι" and prev in "ΑΕΟΥ":        # ΑΙ, ΕΙ, ΟΙ, ΥΙ
            return ""
        if ch == "Ο" and nxt in "ΥΙ":           # ΟΥ, ΟΙ
            return ""
        return SOUND_ALIKE.get(ch, "")

    def pairs(self, rng):
        out = []
        for i, ch in enumerate(self.seq):
            alike = self.trap(i) if self.traps else ""
            wrong = rng.choice(alike) if alike else rng.choice([c for c in ALPHABET if c != ch])
            out.append((ch, wrong))
        return out

    def wrong_text(self, i, label):
        w, pos = self.letters[i]
        word = self.words[w][0]
        letter = word[pos]
        if pos == 0:
            return f"Ωχ! Όχι το {label}.", f"Η λέξη {word} αρχίζει από {letter}."
        return f"Ωχ! Όχι το {label}.", f"{word}: μετά το {word[:pos]} έρχεται {letter}."

    def sound_after(self, got):
        """Όταν τελειώνει μια λέξη, ακούγεται κάτι παραπάνω."""
        if got and (got == len(self.seq) or self.letters[got][1] == 0):
            return "complete"
        return None

    def draw_panel(self, surf, center, got, time, since=9.0):
        """Η τρέχουσα λέξη. Μόλις τελειώσει μια λέξη, μένει λίγο ολόκληρη πριν φανεί η επόμενη."""
        n = len(self.seq)
        if got and since < 1.2 and (got == n or self.letters[got][1] == 0):
            w = self.letters[got - 1][0]
        else:
            w = self.letters[min(got, n - 1)][0]
        word, pic = self.words[w]
        start = next(i for i, (ww, _) in enumerate(self.letters) if ww == w)
        filled = max(0, min(len(word), got - start))
        art.word_panel(surf, center, word, filled, lambda s, r: pictures.draw(s, r, pic), time)
