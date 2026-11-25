"""Πράξεις: το R2 τρέχει και περνά από την πόρτα με τη σωστή απάντηση.

Κάτω φαίνεται η πράξη (π.χ. «3 + 4 = ?»). Μπροστά έρχονται δύο πόρτες, ψηλά και χαμηλά, με
αριθμούς: πηδάς για την πάνω ή όχι για την κάτω. 6 πίστες: προσθέσεις και αφαιρέσεις ως το 10,
ως το 20, με δεκάδες ως το 100, προπαίδεια του 2, 5, 10 και όλη η προπαίδεια (games/calc/levels.py).
Η κίνηση, τα εμπόδια και τα γραφικά είναι κοινά με τους Αριθμούς και τις Λέξεις (games/runner).
"""
from .levels import LEVELS

GAME_ID = "calc"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from games.runner.scene import RunnerScene
    done = app.progress.completed(GAME_ID)
    first = next((i for i in range(len(LEVELS)) if i + 1 not in done), 0)
    return RunnerScene(app, GAME_ID, LEVELS, first)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from games.runner.art import menu_icon
    menu_icon(surf, center, "7", kind="door")
