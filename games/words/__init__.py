"""Λέξεις: το R2 τρέχει και μαζεύει τα γράμματα μιας λέξης με τη σειρά.

Κάτω φαίνεται μια ζωγραφιά (π.χ. ένα μήλο) και κουτάκια για τα γράμματα της λέξης (ΜΗΛΟ).
Σε κάθε επιλογή υπάρχουν δύο φούσκες, ψηλά και χαμηλά: πηδάς ή όχι για να πάρεις το σωστό γράμμα.
6 πίστες με δύο λέξεις η καθεμία, από 4 ως 9 γράμματα (games/words/levels.py). Από την 4η πίστα
το λάθος γράμμα είναι συχνά παγίδα ορθογραφίας (Ο/Ω, Η/Ι/Υ). Η κίνηση, τα εμπόδια και τα γραφικά
είναι κοινά με τους Αριθμούς και τις Πράξεις (games/runner).
"""
from .levels import LEVELS

GAME_ID = "words"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from games.runner.scene import RunnerScene
    done = app.progress.completed(GAME_ID)
    first = next((i for i in range(len(LEVELS)) if i + 1 not in done), 0)
    return RunnerScene(app, GAME_ID, LEVELS, first)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from games.runner.art import menu_icon
    menu_icon(surf, center, "Α")
