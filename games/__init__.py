"""Τα παιχνίδια του κεντρικού μενού, με τη σειρά που εμφανίζονται.

- Για να βγάλεις ένα παιχνίδι από το μενού, σβήσε τη γραμμή του (ή βάλε # μπροστά).
- Για να προσθέσεις μια ιδέα, γράψε μια νέα γραμμή με "id" (λατινικά, χωρίς κενά)
  και "title". Το "color" είναι προαιρετικό. Χωρίς "module" η κάρτα δείχνει «Σύντομα!».
- Όταν το παιχνίδι γραφτεί, βάλε "module": "games.<φάκελος>". Ο φάκελος χρειάζεται
  μια συνάρτηση open_game(app) στο __init__.py του (δες το games/line_follow/__init__.py).

Το μενού χωράει όσα παιχνίδια θέλεις: ως 8 σε μία οθόνη, μετά κάνει σελίδες με βελάκια.
"""

GAMES = [
    {"id": "line_follow", "title": "Ακολούθησε", "color": (62, 140, 226), "module": "games.line_follow"},
    {"id": "cubes", "title": "Κύβοι", "color": (238, 146, 46), "module": "games.cubes"},
    {"id": "maze", "title": "Λαβύρινθος", "color": (84, 172, 96), "module": "games.maze"},
    {"id": "connect", "title": "Ένωσε", "color": (52, 172, 176), "module": "games.connect"},
    {"id": "numbers", "title": "Αριθμοί", "color": (156, 108, 210), "module": "games.numbers"},
    {"id": "words", "title": "Λέξεις", "color": (220, 88, 120), "module": "games.words"},
    {"id": "calc", "title": "Πράξεις", "color": (200, 150, 40), "module": "games.calc"},
    {"id": "factory", "title": "Εργοστάσιο", "color": (230, 110, 70), "module": "games.factory"},
    {"id": "program", "title": "Προγραμμάτισε", "color": (46, 150, 110), "module": "games.program"},
    {"id": "soccer", "title": "Ποδόσφαιρο", "color": (54, 148, 80), "module": "games.soccer"},
    {"id": "rescue", "title": "Αποστολές Διάσωσης", "color": (226, 96, 52), "module": "games.rescue"},
    {"id": "assembly", "title": "Συναρμολόγηση", "color": (90, 120, 200), "module": "games.assembly"},
]
