"""Βγάζει τις εικόνες της σελίδας στο GitHub (docs/screenshots/*.png), χωρίς να ανοίξει παράθυρο.

    py tools/screenshots.py              (Windows)
    python3 tools/screenshots.py         (Linux)

Κάθε εικόνα είναι 1280x720: το μενού και η πρώτη οθόνη των παιχνιδιών της λίστας SHOTS,
αυτών που δείχνει το README. Με --all βγάζει όλα τα παιχνίδια.
"""
import importlib
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
SHOTS = ["line_follow", "cubes", "maze", "program", "numbers", "rescue"]
sys.path.insert(0, ROOT)


def snap(app, scene, name, frames=40):
    """Τρέχει τη σκηνή λίγο (για να μπουν τα κινούμενα στη θέση τους) και τη σώζει."""
    import pygame
    for _ in range(frames):
        scene.update(1 / 60)
    scene.draw(app.screen)
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))
    print("saved", name)


def main():
    from core.app import App
    from games import GAMES
    from games.menu import MenuScene

    os.makedirs(OUT, exist_ok=True)
    app = App(headless=True)
    snap(app, MenuScene(app), "menu")
    for g in GAMES:
        if "module" not in g or ("--all" not in sys.argv and g["id"] not in SHOTS):
            continue
        app.scene = None
        scene = importlib.import_module(g["module"]).open_game(app)
        snap(app, app.scene or scene, g["id"])


if __name__ == "__main__":
    main()
