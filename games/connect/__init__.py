"""Ένωσε: πάτα τις τελείες με τη σειρά 1, 2, 3… και φτιάξε την εικόνα."""
from .pictures import PICTURES

GAME_ID = "connect"
LEVEL_COUNT = len(PICTURES)


def open_game(app):
    from .scene import ConnectScene
    done = app.progress.completed(GAME_ID)
    first_open = next((i for i in range(LEVEL_COUNT) if i + 1 not in done), 0)
    return ConnectScene(app, first_open)
