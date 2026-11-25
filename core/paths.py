"""Πού γράφει το παιχνίδι τα αρχεία κάθε χρήστη (τα σχέδια των Κύβων).

Linux:   ~/.config/r2-lab/      (ή $XDG_CONFIG_HOME/r2-lab)
Windows: %APPDATA%\\r2-lab\\
Έτσι δουλεύει και όταν το πρόγραμμα είναι εγκατεστημένο σε φάκελο συστήματος (/opt/r2-lab),
και κάθε χρήστης έχει τα δικά του σχέδια. Τα τελειωμένα επίπεδα δεν αποθηκεύονται (core/save.py).
"""
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "r2-lab"
USER_FILES = ("cubes_patterns.json",)


def user_dir():
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def prepare(code_dir, target=None):
    """Φτιάχνει τον φάκελο του χρήστη και επιστρέφει τη διαδρομή του.

    Αν βρει αρχεία από παλιότερη έκδοση δίπλα στον κώδικα, τα μεταφέρει εκεί.
    Αν ο φάκελος δεν φτιάχνεται, γράφει δίπλα στον κώδικα όπως πριν.
    """
    target = Path(target) if target else user_dir()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(code_dir)
    for name in USER_FILES:
        old, new = Path(code_dir) / name, target / name
        if old.exists() and not new.exists():
            try:
                shutil.copy2(old, new)
                old.unlink()
            except OSError:
                pass
    return target
