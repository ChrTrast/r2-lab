"""Συναρμολόγηση: το παιδί συναρμολογεί το R2 κομμάτι κομμάτι, με τη σειρά του οδηγού συναρμολόγησης.

Χωρίς βίδες: κάθε κομμάτι κολλάει σαν μαγνήτης όταν το φέρεις κοντά στη θέση του και οι βίδες του
μπαίνουν μόνες τους. Τρεις τρόποι: «Με βοήθεια», «Με τον οδηγό», «Μόνος μου».
Τα βήματα είναι στο games/assembly/steps.py, οι κανόνες στο logic.py, τα 3D σχήματα στο parts.py.
"""
GAME_ID = "assembly"


def open_game(app):
    from .scene import AssemblyScene
    return AssemblyScene(app)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from .art import menu_icon
    menu_icon(surf, center)
