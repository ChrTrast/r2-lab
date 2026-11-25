"""Αριθμοί: το R2 τρέχει και μαζεύει τους αριθμούς με τη σειρά (μέτρημα ανά 1, 2, 5, 10 και 3).

Σε κάθε επιλογή υπάρχουν δύο φούσκες, ψηλά και χαμηλά: πηδάς ή όχι για να πάρεις τη σωστή.
6 πίστες που γίνονται πιο γρήγορες (games/numbers/levels.py). Η κίνηση, τα εμπόδια και
τα γραφικά είναι κοινά με τις Λέξεις και τις Πράξεις (games/runner).
"""
from .levels import LEVELS

GAME_ID = "numbers"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from games.runner.scene import RunnerScene
    done = app.progress.completed(GAME_ID)
    first = next((i for i in range(len(LEVELS)) if i + 1 not in done), 0)
    return RunnerScene(app, GAME_ID, LEVELS, first)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from games.runner.art import menu_icon
    menu_icon(surf, center, "5")
