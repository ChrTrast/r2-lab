"""Ακολούθησε: φτιάξε τη μαύρη γραμμή ώστε το R2 να φτάσει στον φορτιστή (line follower).

Από κάθε παιχνίδι το μενού χρειάζεται μόνο την open_game(app), που επιστρέφει την οθόνη του.
Τα GAME_ID και LEVEL_COUNT είναι προαιρετικά: με αυτά η κάρτα δείχνει πόσα επίπεδα τελείωσαν.
"""
from .levels import LEVELS

GAME_ID = "line_follow"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from .scene import LineFollowScene
    done = app.progress.completed(GAME_ID)
    first_open = next((i for i in range(LEVEL_COUNT) if i + 1 not in done), 0)
    return LineFollowScene(app, first_open)
