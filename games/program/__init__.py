"""Προγραμμάτισε: το παιδί φτιάχνει πρόγραμμα για το R2 με τα ίδια μπλοκ που έχει το Mind+ στην τάξη
και πατά «Πάμε!». Το R2 το εκτελεί βήμα βήμα σε ένα νησάκι από κυβάκια, και φωτίζεται το μπλοκ που τρέχει.

Τρία είδη πίστας: «Δες» (οδηγείς με κουμπιά και το πρόγραμμα γράφεται μόνο του), «Διόρθωσε»
(έτοιμο πρόγραμμα με ένα λάθος) και «Γράψε» (όλο το πρόγραμμα). 20 πίστες για Α'-ΣΤ' (levels.py):
κίνηση και στροφές, «επανάλαβε», το LED που ανοίγει πόρτες, «περίμενε», ο αισθητήρας απόστασης,
«για πάντα» και «εάν … τότε … αλλιώς».
"""
from .levels import LEVELS

GAME_ID = "program"
LEVEL_COUNT = len(LEVELS)


def open_game(app):
    from .scene import ProgramScene
    done = app.progress.completed(GAME_ID)
    first = next((i for i in range(LEVEL_COUNT) if i + 1 not in done), 0)
    return ProgramScene(app, first)


def draw_icon(surf, center):
    """Το εικονίδιο της κάρτας στο μενού."""
    from .art import menu_icon
    menu_icon(surf, center)
