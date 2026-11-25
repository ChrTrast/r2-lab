"""Τα αντικείμενα του Εργοστασίου: σε ποιο κουτί πάει το καθένα και πώς το λέμε στα μηνύματα.

Χωρίς γραφικά (οι ζωγραφιές είναι στο items.py, με τα ίδια ονόματα).
Για να βγάλεις ένα αντικείμενο από το παιχνίδι, σβήσε το από τις λίστες του levels.py.
"""
from typing import NamedTuple

HW, SW, OTHER = "hw", "sw", "other"          # Υλικό, Λογισμικό, Κάδος
BOX_NAMES = {HW: "ΥΛΙΚΟ Η/Υ", SW: "ΛΟΓΙΣΜΙΚΟ", OTHER: "ΚΑΔΟΣ"}
INTO = {HW: "στο ΥΛΙΚΟ Η/Υ", SW: "στο ΛΟΓΙΣΜΙΚΟ", OTHER: "στον ΚΑΔΟ"}


class Item(NamedTuple):
    key: str          # το όνομα της ζωγραφιάς στο items.py
    kind: str         # HW, SW ή OTHER: το σωστό κουτί
    the: str          # με το άρθρο, π.χ. «το ποντίκι» (στα προγράμματα: «το πρόγραμμα για μουσική»)
    plural: bool = False
    use: str = ""     # μόνο στα προγράμματα: για τι είναι, π.χ. «μουσική»


def _hw(key, the, plural=False):
    return Item(key, HW, the, plural)


def _sw(key, use):
    return Item(key, SW, "το πρόγραμμα για " + use, False, use)


def _other(key, the):
    return Item(key, OTHER, the)


ITEMS = {i.key: i for i in [
    # Υλικό: οι συσκευές του υπολογιστή
    _hw("keyboard", "το πληκτρολόγιο"), _hw("mouse", "το ποντίκι"), _hw("monitor", "η οθόνη"),
    _hw("printer", "ο εκτυπωτής"), _hw("speakers", "τα ηχεία", True), _hw("headphones", "τα ακουστικά", True),
    _hw("microphone", "το μικρόφωνο"), _hw("webcam", "η κάμερα"), _hw("scanner", "ο σαρωτής"),
    _hw("tower", "η κεντρική μονάδα"), _hw("laptop", "ο φορητός υπολογιστής"), _hw("usb", "το στικάκι USB"),
    # Λογισμικό: τα προγράμματα
    _sw("app_paint", "ζωγραφική"), _sw("app_text", "κείμενα"), _sw("app_game", "παιχνίδια"),
    _sw("app_music", "μουσική"), _sw("app_photos", "φωτογραφίες"), _sw("app_video", "βίντεο"),
    _sw("app_web", "το ίντερνετ"), _sw("app_code", "προγραμματισμό"),
    # Κάδος: άσχετα με τον υπολογιστή
    _other("umbrella", "η ομπρέλα"), _other("unicorn", "ο μονόκερος"), _other("scooter", "το πατίνι"),
    _other("ball", "η μπάλα"), _other("shoe", "το παπούτσι"), _other("apple", "το μήλο"),
    _other("icecream", "το παγωτό"), _other("teddy", "το αρκουδάκι"), _other("flower", "το λουλούδι"),
    _other("hat", "το καπέλο"), _other("bucket", "το κουβαδάκι"), _other("carrot", "το καρότο"),
]}


def _cap(s):
    return s[:1].upper() + s[1:]


def wrong_text(key, box):
    """Οι δύο γραμμές που λέει το R2 όταν ένα αντικείμενο μπει σε λάθος κουτί."""
    it = ITEMS[key]
    line1 = f"Ωχ! Όχι {INTO[box]}."
    goes = "πάνε" if it.plural else "πάει"
    if it.kind == HW:
        line2 = f"{_cap(it.the)} είναι {'συσκευές' if it.plural else 'συσκευή'}: {goes} {INTO[HW]}."
    elif it.kind == SW:
        line2 = f"Είναι πρόγραμμα για {it.use}: πάει {INTO[SW]}."
    else:
        line2 = f"{_cap(it.the)} δεν είναι του υπολογιστή: {goes} {INTO[OTHER]}."
    return line1, line2


def lost_text(key):
    """Οι δύο γραμμές όταν ένα αντικείμενο πέσει από την ταινία."""
    it = ITEMS[key]
    return f"Ωχ! {'Έπεσαν' if it.plural else 'Έπεσε'} {it.the}!", "Πρόλαβε τα αντικείμενα πριν φτάσουν στο τέλος!"
