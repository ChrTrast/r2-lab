"""Κύβοι: χτίσε στον τοίχο το σχέδιο του τετραδίου, ρίχνοντας κύβους στις στήλες."""
from .patterns import BUILT_IN

GAME_ID = "cubes"
LEVEL_COUNT = len(BUILT_IN)


def open_game(app):
    from .scene import CubesScene
    done = app.progress.completed(GAME_ID)
    first_open = next((i for i in range(LEVEL_COUNT) if i + 1 not in done), 0)
    return CubesScene(app, first_open)


def draw_icon(surf, center):
    from .art import draw_icon as draw
    draw(surf, center)
