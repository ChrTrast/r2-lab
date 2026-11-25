"""Λαβύρινθος: οδήγησε το ρομπότ R2 στον φορτιστή με τα κουμπιά ή τα βελάκια.

Εισαγωγή στη ρομποτική για τις μικρές τάξεις: μπροστά, πίσω και στροφές επί τόπου,
όπως στο πραγματικό R2. 20 λαβύρινθοι που μεγαλώνουν (games/maze/levels.py).
"""
from .levels import LEVELS

GAME_ID = "maze"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from .scene import MazeScene
    done = app.progress.completed(GAME_ID)
    first_open = next((i for i in range(LEVEL_COUNT) if i + 1 not in done), 0)
    return MazeScene(app, first_open)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from .art import menu_icon
    menu_icon(surf, center)
