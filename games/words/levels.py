"""Οι 6 πίστες των Λέξεων: η διαδρομή και οι δύο λέξεις κάθε πίστας (με τη ζωγραφιά τους).

Κάθε πίστα έχει τόσες επιλογές (CHOICE) όσα είναι τα γράμματα των δύο λέξεων.
Από την 4η πίστα η λάθος φούσκα είναι συχνά «παγίδα ορθογραφίας» (Ο/Ω, Η/Ι/Υ).
"""
from games.runner.chunks import (BLOCK, BLOCK2, CHOICE, GRAV_CHOICE, GRAV_IN, GRAV_OUT, GRAV_S2, PAD_SPIKES,
                                 PAD_WALL, PIT, RING_SPIKES, ROCKET_CHOICE, ROCKET_IN, ROCKET_OUT,
                                 ROCKET_PILLARS, S1, S2, S3, SPEED, STAIRS, TOP_SPIKE, build, flat)
from .lesson import WordsLesson

C = CHOICE

LEVELS = [
    {   # 1: αγκάθια και κουτιά (4 + 4 γράμματα)
        "lesson": WordsLesson([("ΜΗΛΟ", "apple"), ("ΓΑΤΑ", "cat")]),
        "speed": 5.5,
        "rows": build(flat(6), S1, C, C, S2, C, BLOCK, C,
                      S1, C, C, BLOCK2, C, S2, C, flat(8)),
    },
    {   # 2: + τραμπολίνο (5 + 5)
        "lesson": WordsLesson([("ΣΠΙΤΙ", "house"), ("ΒΑΡΚΑ", "boat")]),
        "speed": 6.0,
        "rows": build(flat(6), S1, C, C, PAD_WALL, C, S2, C, C,
                      PAD_SPIKES, C, C, STAIRS, C, TOP_SPIKE, C, C, flat(8)),
    },
    {   # 3: + δαχτυλίδι (6 + 6)
        "lesson": WordsLesson([("ΔΕΝΤΡΟ", "tree"), ("ΧΕΛΩΝΑ", "turtle")]),
        "speed": 6.5,
        "rows": build(flat(6), S2, C, C, RING_SPIKES, C, C, PIT, C, C,
                      RING_SPIKES, C, C, PAD_WALL, C, C, TOP_SPIKE, C, C, flat(8)),
    },
    {   # 4: + ανάποδη βαρύτητα (7 + 8), παγίδες ορθογραφίας
        "lesson": WordsLesson([("ΦΕΓΓΑΡΙ", "moon"), ("ΠΑΠΟΥΤΣΙ", "shoe")], traps=True),
        "speed": 7.0,
        "rows": build(flat(6), S2, C, C, RING_SPIKES, C, GRAV_IN, GRAV_CHOICE, GRAV_S2, GRAV_CHOICE, GRAV_CHOICE,
                      GRAV_OUT, C,
                      PAD_WALL, C, C, S3, C, GRAV_IN, GRAV_CHOICE, GRAV_S2, GRAV_CHOICE, GRAV_OUT, C, C, PIT, C,
                      flat(8)),
    },
    {   # 5: + πύραυλος (8 + 8)
        "lesson": WordsLesson([("ΠΟΔΗΛΑΤΟ", "bicycle"), ("ΛΟΥΛΟΥΔΙ", "flower")], traps=True),
        "speed": 7.5,
        "rows": build(flat(6), S2, C, C, PAD_SPIKES, C, ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_CHOICE,
                      ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_OUT, C, C,
                      RING_SPIKES, C, C, GRAV_IN, GRAV_CHOICE, GRAV_S2, GRAV_CHOICE, GRAV_OUT, C, ROCKET_IN,
                      ROCKET_CHOICE, ROCKET_OUT, C, C, flat(8)),
    },
    {   # 6: όλα μαζί, πιο γρήγορα (9 + 9)
        "lesson": WordsLesson([("ΠΕΤΑΛΟΥΔΑ", "butterfly"), ("ΑΕΡΟΠΛΑΝΟ", "airplane")], traps=True),
        "speed": 8.0, "fast": 9.0,
        "rows": build(flat(6), S3, C, C, RING_SPIKES, C, C, SPEED, PAD_SPIKES, C, GRAV_IN, GRAV_CHOICE, GRAV_S2,
                      GRAV_CHOICE, GRAV_OUT, C, C,
                      ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_CHOICE, ROCKET_OUT, C, C, PIT, C, STAIRS,
                      C, GRAV_IN, GRAV_CHOICE, GRAV_CHOICE, GRAV_OUT, C, flat(8)),
    },
]
