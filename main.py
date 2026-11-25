"""Εργαστήρι R2 (R2 Lab): παιχνίδια ρομποτικής και μάθησης για παιδιά. Ξεκίνα από εδώ:

    py main.py                  (Windows)
    python3 main.py             (Linux)
Ανοίγει σε πλήρη οθόνη. Με --window ανοίγει σε παράθυρο. F11 = εναλλαγή.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

if sys.platform.startswith("win"):
    # Καθαρή εικόνα σε οθόνες με κλιμάκωση 125% / 150% / 200%,
    # και παράθυρο που χωράει στην οθόνη (αλλιώς τα Windows το μεγεθύνουν θολά).
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def _check_pygame():
    try:
        import pygame  # noqa: F401
    except ImportError:
        sys.exit("Λείπει το pygame. Εγκατάσταση:\n"
                 "  Ubuntu:  sudo apt install python3-pygame\n"
                 "  Windows: py -m pip install pygame-ce")


def main():
    _check_pygame()
    import pygame

    from core import paths
    from core.app import App
    from games.menu import MenuScene, window_icon

    parser = argparse.ArgumentParser(description="Εργαστήρι R2: παιχνίδια ρομποτικής και μάθησης για παιδιά")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--fullscreen", action="store_true", help="άνοιγμα σε πλήρη οθόνη (προεπιλογή)")
    g.add_argument("--window", action="store_true", help="άνοιγμα σε παράθυρο")
    args = parser.parse_args()
    app = App(title="Εργαστήρι R2", data_dir=str(paths.prepare(HERE)), fullscreen=not args.window)
    pygame.display.set_icon(window_icon())
    app.switch(MenuScene(app))
    app.run()


if __name__ == "__main__":
    main()
