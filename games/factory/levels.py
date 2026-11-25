"""Οι 6 πίστες του Εργοστασίου.

Κάθε πίστα:
    boxes   τα κουτιά, από αριστερά προς τα δεξιά (2 ή 3)
    bag     πόσο συχνά έρχεται κάθε είδος: π.χ. (HW, SW, SW, OTHER) = τα μισά είναι προγράμματα
    pool    ποια αντικείμενα μπορεί να έρθουν από κάθε είδος (τα ονόματα του catalog.py)
    goal    πόσα πρέπει να μπουν στο σωστό κουτί για να τελειώσει η πίστα
    speed   pixels το δευτερόλεπτο στο «Γρήγορα» (το «Αργά» είναι 0.6 από αυτό, το «Κανονικά» 0.8)
    gap     pixels ανάμεσα σε δύο αντικείμενα πάνω στην ταινία
Μέσα στην πίστα η ταινία επιταχύνει λίγο λίγο (logic.ACCEL).
"""
from .catalog import HW, OTHER, SW

EASY_HW = ["keyboard", "mouse", "monitor", "printer", "speakers", "headphones"]
ALL_HW = EASY_HW + ["microphone", "webcam", "scanner", "tower", "laptop", "usb"]
SOFTWARE = ["app_paint", "app_text", "app_game", "app_music", "app_photos", "app_video", "app_web", "app_code"]
OTHERS = ["umbrella", "unicorn", "scooter", "ball", "shoe", "apple", "icecream", "teddy", "flower", "hat",
          "bucket", "carrot"]

_TWO = {"boxes": (HW, OTHER), "bag": (HW, OTHER),
        "goal_text": "Οι συσκευές του υπολογιστή στο ΥΛΙΚΟ Η/Υ, όλα τα άλλα στον ΚΑΔΟ!"}
_THREE = {"boxes": (HW, SW, OTHER), "bag": (HW, SW, OTHER),
          "goal_text": "Συσκευές στο ΥΛΙΚΟ Η/Υ, προγράμματα στο ΛΟΓΙΣΜΙΚΟ, τα άλλα στον ΚΑΔΟ!"}

LEVELS = [
    dict(_TWO, pool={HW: EASY_HW, OTHER: OTHERS}, goal=10, speed=195, gap=260,
         examples={HW: ("keyboard", "mouse", "monitor"), OTHER: ("umbrella", "ball", "apple")},
         tip="Σύρε κάθε αντικείμενο στο κουτί του (ή πάτα τα βελάκια ← →) πριν πέσει από την ταινία!"),
    dict(_TWO, pool={HW: ALL_HW, OTHER: OTHERS}, goal=12, speed=225, gap=245,
         examples={HW: ("microphone", "webcam", "tower"), OTHER: ("unicorn", "scooter", "teddy")},
         tip="Πιο πολλές συσκευές! 5 σωστά στη σειρά = Σούπερ!"),
    dict(_TWO, pool={HW: ALL_HW, OTHER: OTHERS}, goal=14, speed=260, gap=225,
         examples={HW: ("scanner", "laptop", "usb"), OTHER: ("shoe", "icecream", "hat")},
         tip="Πιο γρήγορα, και πιο πολλά μαζί πάνω στην ταινία!"),
    dict(_THREE, bag=(HW, SW, SW, OTHER), pool={HW: ALL_HW, SW: SOFTWARE, OTHER: OTHERS}, goal=12, speed=195, gap=260,
         examples={HW: ("keyboard", "mouse", "printer"), SW: ("app_paint", "app_text", "app_game"),
                   OTHER: ("umbrella", "ball", "flower")},
         tip="Νέο κουτί: ΛΟΓΙΣΜΙΚΟ (βελάκι ↓)! Τα προγράμματα μπαίνουν μέσα στον υπολογιστή."),
    dict(_THREE, pool={HW: ALL_HW, SW: SOFTWARE, OTHER: OTHERS}, goal=14, speed=240, gap=235,
         examples={HW: ("headphones", "webcam", "tower"), SW: ("app_music", "app_photos", "app_video"),
                   OTHER: ("apple", "teddy", "bucket")},
         tip="Πιο γρήγορα! Πάτα ← ↓ → ή σύρε με το ποντίκι."),
    dict(_THREE, pool={HW: ALL_HW, SW: SOFTWARE, OTHER: OTHERS}, goal=16, speed=285, gap=210,
         examples={HW: ("speakers", "scanner", "laptop"), SW: ("app_web", "app_code", "app_game"),
                   OTHER: ("unicorn", "carrot", "hat")},
         tip="Η πιο γρήγορη ταινία. Μπορείς;"),
]
