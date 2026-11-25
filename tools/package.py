"""Φτιάχνει το dist/r2-lab.zip για μεταφορά σε άλλον υπολογιστή (Ubuntu ή Windows).

    py tools/package.py          (Windows)
    python3 tools/package.py     (Linux)

Μέσα στο zip τα scripts του Linux έχουν δικαίωμα εκτέλεσης, οπότε μετά το unzip
δουλεύει κατευθείαν το ./install.sh. Η πρόοδος και τα σχέδια των παιδιών δεν μπαίνουν.
"""
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = ["core", "games", "assets", "tools", "tests", "main.py", "README.md",
           "start.bat", "start.sh", "install.sh", "uninstall.sh", "r2-lab.desktop"]
EXECUTABLE = {"install.sh", "uninstall.sh", "start.sh", "main.py"}
SKIP_FILES = {"progress.json", "cubes_patterns.json"}


def files():
    for item in INCLUDE:
        path = os.path.join(ROOT, item)
        if not os.path.isdir(path):
            yield path
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if name not in SKIP_FILES and not name.endswith(".pyc"):
                    yield os.path.join(dirpath, name)


def build(out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files():
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            info = zipfile.ZipInfo("r2-lab/" + rel, date_time=time.localtime(os.path.getmtime(path))[:6])
            info.create_system = 3      # Unix, ώστε το unzip να κρατήσει τα δικαιώματα
            mode = 0o755 if os.path.basename(path) in EXECUTABLE else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as f:
                z.writestr(info, f.read())
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "r2-lab.zip")
    print("saved", build(target))
