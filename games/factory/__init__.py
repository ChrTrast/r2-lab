"""Εργοστάσιο: τα αντικείμενα έρχονται πάνω σε μια ταινία και το παιδί τα βάζει στο σωστό κουτί,
πριν πέσουν από το τέλος της. Μαθαίνει τι είναι το υλικό και το λογισμικό του υπολογιστή (ΤΠΕ).

Πίστες 1-3: ΥΛΙΚΟ Η/Υ (οι συσκευές του υπολογιστή) και ΚΑΔΟΣ (όλα τα άλλα).
Πίστες 4-6: και ΛΟΓΙΣΜΙΚΟ (τα προγράμματα, που μπαίνουν μέσα στον υπολογιστή).
Οι πίστες είναι στο games/factory/levels.py και τα αντικείμενα στο catalog.py.
"""
from .levels import LEVELS

GAME_ID = "factory"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from .scene import FactoryScene
    done = app.progress.completed(GAME_ID)
    first = next((i for i in range(len(LEVELS)) if i + 1 not in done), 0)
    return FactoryScene(app, GAME_ID, LEVELS, first)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from .art import menu_icon
    menu_icon(surf, center)
