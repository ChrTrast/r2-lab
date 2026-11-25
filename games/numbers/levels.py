"""Οι 6 πίστες των Αριθμών: η διαδρομή και ποιους αριθμούς μαζεύει το παιδί με τη σειρά.

Κάθε πίστα έχει 10 επιλογές (CHOICE): σε καθεμία μία φούσκα ψηλά και μία χαμηλά.
Η μία έχει τον σωστό επόμενο αριθμό. Σε κάθε προσπάθεια αλλάζει ποια είναι πάνω.
"""
from games.runner.chunks import (BLOCK, BLOCK2, CHOICE, GRAV_CHOICE, GRAV_IN, GRAV_OUT, GRAV_S2, PAD_SPIKES,
                                 PAD_WALL, PIT, RING_SPIKES, ROCKET_CHOICE, ROCKET_IN, ROCKET_OUT,
                                 ROCKET_PILLARS, S1, S2, S3, SPEED, STAIRS, TOP_SPIKE, build, flat)
from .lesson import NumbersLesson

LEVELS = [
    {   # 1: αγκάθια και κουτιά
        "lesson": NumbersLesson("Μέτρα:", "Μάζεψε τους αριθμούς με τη σειρά: 1, 2, 3…", list(range(1, 11))),
        "speed": 5.5,
        "rows": build(flat(6), S1, CHOICE, S1, CHOICE, BLOCK, CHOICE, S2, CHOICE, BLOCK2, CHOICE, S1, CHOICE,
                      STAIRS, CHOICE, S2, CHOICE, TOP_SPIKE, CHOICE, S2, CHOICE, flat(8)),
    },
    {   # 2: + τραμπολίνο
        "lesson": NumbersLesson("Από το 11:", "Συνέχισε να μετράς από το 11 και πάνω.", list(range(11, 21))),
        "speed": 6.0,
        "rows": build(flat(6), S1, CHOICE, PAD_WALL, CHOICE, S2, CHOICE, PAD_SPIKES, CHOICE, STAIRS, CHOICE,
                      PAD_WALL, CHOICE, TOP_SPIKE, CHOICE, PAD_SPIKES, CHOICE, PIT, CHOICE, S2, CHOICE, flat(8)),
    },
    {   # 3: + δαχτυλίδι
        "lesson": NumbersLesson("Ανά 2:", "Μέτρα ανά 2: 2, 4, 6…", list(range(2, 21, 2))),
        "speed": 6.5,
        "rows": build(flat(6), S2, CHOICE, RING_SPIKES, CHOICE, PAD_WALL, CHOICE, RING_SPIKES, CHOICE, TOP_SPIKE,
                      CHOICE, PIT, CHOICE, RING_SPIKES, CHOICE, PAD_SPIKES, CHOICE, STAIRS, CHOICE, RING_SPIKES,
                      CHOICE, flat(8)),
    },
    {   # 4: + ανάποδη βαρύτητα
        "lesson": NumbersLesson("Ανά 5:", "Μέτρα ανά 5: 5, 10, 15…", list(range(5, 51, 5))),
        "speed": 7.0,
        "rows": build(flat(6), S2, CHOICE, RING_SPIKES, CHOICE, GRAV_IN, GRAV_S2, GRAV_CHOICE, GRAV_S2,
                      GRAV_CHOICE, GRAV_OUT, CHOICE, PAD_WALL, CHOICE, GRAV_IN, GRAV_CHOICE, GRAV_S2, GRAV_CHOICE,
                      GRAV_OUT, S3, CHOICE, PIT, CHOICE, flat(8)),
    },
    {   # 5: + πύραυλος
        "lesson": NumbersLesson("Ανά 10:", "Μέτρα ανά 10: 10, 20, 30…", list(range(10, 101, 10))),
        "speed": 7.5,
        "rows": build(flat(6), S2, CHOICE, PAD_SPIKES, CHOICE, ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE,
                      ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_OUT, CHOICE, RING_SPIKES, CHOICE, GRAV_IN, GRAV_CHOICE,
                      GRAV_S2, GRAV_CHOICE, GRAV_OUT, ROCKET_IN, ROCKET_CHOICE, ROCKET_OUT, CHOICE, flat(8)),
    },
    {   # 6: όλα μαζί, πιο γρήγορα
        "lesson": NumbersLesson("Ανά 3:", "Μέτρα ανά 3: 3, 6, 9…", list(range(3, 31, 3))),
        "speed": 8.0, "fast": 9.0,
        "rows": build(flat(6), S3, CHOICE, RING_SPIKES, CHOICE, SPEED, PAD_SPIKES, CHOICE, GRAV_IN, GRAV_S2,
                      GRAV_CHOICE, GRAV_OUT, PIT, CHOICE, ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_OUT,
                      CHOICE, STAIRS, CHOICE, GRAV_IN, GRAV_CHOICE, GRAV_OUT, CHOICE, flat(8)),
    },
]
