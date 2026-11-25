"""Οι 6 πίστες των Πράξεων: η διαδρομή και τι πράξεις λύνει το παιδί.

Κάθε πίστα έχει 8 πόρτες (CHOICE), με αρκετό χώρο πριν από την καθεμία για να λογαριάσει.
Οι πράξεις αλλάζουν σε κάθε προσπάθεια (games/calc/lesson.py). Η ταχύτητα είναι λίγο πιο
αργή από τους Αριθμούς και τις Λέξεις, γιατί εδώ το παιδί πρέπει να λογαριάσει.
"""
from games.runner.chunks import (BLOCK, BLOCK2, CHOICE, GRAV_CHOICE, GRAV_GAP, GRAV_IN, GRAV_OUT, GRAV_S2,
                                 PAD_SPIKES, PAD_WALL, PIT, RING_SPIKES, ROCKET_CHOICE, ROCKET_IN, ROCKET_OUT,
                                 ROCKET_PILLARS, S1, S2, S3, SPEED, STAIRS, TOP_SPIKE, build, flat)
from . import lesson as L

C = CHOICE

LEVELS = [
    {   # 1: αγκάθια και κουτιά
        "lesson": L.MathLesson("Προσθέσεις ως το 10", L.add10),
        "speed": 5.0,
        "rows": build(flat(8), S1, flat(4), C, S2, flat(4), C, BLOCK, flat(4), C, S1, flat(4), C,
                      BLOCK2, flat(4), C, STAIRS, flat(2), C, S2, flat(4), C, TOP_SPIKE, flat(2), C, flat(8)),
    },
    {   # 2: + τραμπολίνο
        "lesson": L.MathLesson("Αφαιρέσεις ως το 10", L.sub10),
        "speed": 5.5,
        "rows": build(flat(8), S1, flat(4), C, PAD_WALL, flat(2), C, S2, flat(4), C, PAD_SPIKES, flat(2), C,
                      STAIRS, flat(2), C, PAD_WALL, flat(2), C, TOP_SPIKE, flat(2), C, PIT, flat(2), C, flat(8)),
    },
    {   # 3: + δαχτυλίδι
        "lesson": L.MathLesson("Προσθέσεις και αφαιρέσεις ως το 20", L.mixed20),
        "speed": 6.0,
        "rows": build(flat(8), S2, flat(4), C, RING_SPIKES, flat(4), C, PAD_WALL, flat(2), C, RING_SPIKES,
                      flat(4), C, PIT, flat(4), C, PAD_SPIKES, flat(4), C, RING_SPIKES, flat(4), C, STAIRS,
                      flat(2), C, flat(8)),
    },
    {   # 4: + ανάποδη βαρύτητα
        "lesson": L.MathLesson("Με δεκάδες, ως το 100", L.tens100),
        "speed": 6.5,
        "rows": build(flat(8), S2, flat(4), C, RING_SPIKES, flat(4), C, GRAV_IN, GRAV_GAP, GRAV_CHOICE, GRAV_S2,
                      GRAV_GAP, GRAV_CHOICE, GRAV_OUT, flat(4), C, PAD_WALL, flat(2), C, GRAV_IN, GRAV_GAP,
                      GRAV_CHOICE, GRAV_OUT, S2, flat(4), C, flat(8)),
    },
    {   # 5: + πύραυλος
        "lesson": L.MathLesson("Προπαίδεια του 2, του 5 και του 10", L.times2510),
        "speed": 7.0,
        "rows": build(flat(8), S2, flat(6), C, PAD_SPIKES, flat(4), C, ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE,
                      ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_OUT, flat(4), C, RING_SPIKES, flat(4), C, GRAV_IN,
                      GRAV_GAP, GRAV_CHOICE, GRAV_OUT, flat(4), ROCKET_IN, ROCKET_PILLARS, ROCKET_CHOICE,
                      ROCKET_OUT, flat(8)),
    },
    {   # 6: όλα μαζί, πιο γρήγορα
        "lesson": L.MathLesson("Όλη η προπαίδεια", L.times_all),
        "speed": 7.5, "fast": 8.5,
        "rows": build(flat(8), S3, flat(6), C, RING_SPIKES, flat(6), C, SPEED, PAD_SPIKES, flat(6), C, GRAV_IN,
                      GRAV_GAP, GRAV_CHOICE, GRAV_S2, GRAV_GAP, GRAV_CHOICE, GRAV_OUT, flat(4), C, ROCKET_IN,
                      ROCKET_PILLARS, ROCKET_CHOICE, ROCKET_OUT, PIT, flat(6), C, STAIRS, flat(8)),
    },
]
