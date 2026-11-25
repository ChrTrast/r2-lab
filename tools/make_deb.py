"""Φτιάχνει το πακέτο dist/r2-lab_<έκδοση>_all.deb για Ubuntu / Xubuntu (και Debian).

    py tools/make_deb.py          (Windows)
    python3 tools/make_deb.py     (Linux)

Δεν χρειάζεται dpkg ή Linux: το .deb είναι ένα αρχείο «ar» με τρία κομμάτια
(debian-binary, control.tar.gz, data.tar.gz), που τα φτιάχνουμε με την Python.

Στο Ubuntu:   sudo apt install ./r2-lab_1.10.0_all.deb    (φέρνει μόνο του και το pygame)
Αφαίρεση:     sudo apt remove r2-lab

Μπαίνει στις ίδιες θέσεις με το install.sh:
  /opt/r2-lab/                               το πρόγραμμα
  /usr/bin/r2-lab                            η εντολή (r2-lab --window: σε παράθυρο)
  /usr/share/applications/r2-lab.desktop     στο μενού εφαρμογών: Εκπαίδευση
  /usr/share/pixmaps/r2-lab.png              το εικονίδιο
Αν βρει παλιά εγκατάσταση από το install.sh, τη σβήνει πρώτα.
Η προηγούμενη έκδοση λεγόταν «Παιχνίδια Μάθησης» (πακέτο edu-games): το apt την αφαιρεί
μόνο του (Conflicts), και το preinst σβήνει ό,τι είχε αφήσει το παλιό install.sh.
"""
import hashlib
import io
import os
import re
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = "r2-lab"
APP_DIR = "opt/r2-lab"
PROGRAM = ["core", "games", "main.py", "README.md"]
EXECUTABLE = {APP_DIR + "/main.py", "usr/bin/r2-lab"}
CONTROL = """\
Package: r2-lab
Version: {version}
Architecture: all
Maintainer: Χρόνης Τραστόγιαννος <ctrastogia@sch.gr>
Installed-Size: {size}
Depends: python3 (>= 3.10), python3-pygame (>= 2.1), fonts-dejavu-core
Conflicts: edu-games
Replaces: edu-games
Section: games
Priority: optional
Description: Εργαστήρι R2 (R2 Lab) - robotics and learning games for young children
 Logic, robotics and learning games in Greek, with the robot R2:
 line follower, cubes, maze, connect the dots, numbers, words, sums,
 hardware-or-software factory and block programming for the R2 robot.
 .
 Παιχνίδια λογικής, ρομποτικής και μάθησης για μικρά παιδιά, με το ρομπότ R2.
"""
LAUNCHER = """\
#!/bin/sh
exec python3 /opt/r2-lab/main.py "$@"
"""
PREINST = """\
#!/bin/sh
set -e
# Πρώτη εγκατάσταση: σβήνει ό,τι άφησε το install.sh, για να μην ανοίγει η παλιά έκδοση.
# Το edu-games είναι το παλιό όνομα («Παιχνίδια Μάθησης»): χωρίς αυτό θα έμεναν δύο εικονίδια στο μενού.
if [ "$1" = "install" ]; then
    for name in r2-lab edu-games; do
        if [ -f /usr/local/bin/$name ] && grep -q "/opt/$name/main.py" /usr/local/bin/$name; then
            rm -f /usr/local/bin/$name /usr/share/applications/$name.desktop /usr/share/pixmaps/$name.png
            rm -rf /opt/$name
        fi
    done
    rm -rf /opt/r2-lab
fi
exit 0
"""
POSTINST = """\
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    python3 -m compileall -q /opt/r2-lab >/dev/null 2>&1 || true
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
fi
exit 0
"""
PRERM = """\
#!/bin/sh
set -e
find /opt/r2-lab -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
exit 0
"""


def version():
    with open(os.path.join(ROOT, "core", "__init__.py"), encoding="utf-8") as f:
        return re.search(r'__version__\s*=\s*"([^"]+)"', f.read()).group(1)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def payload():
    """Τα αρχεία του πακέτου: {θέση μέσα στο σύστημα (χωρίς / μπροστά): περιεχόμενο}."""
    files = {}
    for item in PROGRAM:
        path = os.path.join(ROOT, item)
        if os.path.isfile(path):
            files[f"{APP_DIR}/{item}"] = _read(path)
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if not name.endswith((".pyc", ".pyo")):
                    full = os.path.join(dirpath, name)
                    rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                    files[f"{APP_DIR}/{rel}"] = _read(full)
    icon = _read(os.path.join(ROOT, "assets", "r2-lab.png"))
    files[f"{APP_DIR}/assets/r2-lab.png"] = icon
    files["usr/share/pixmaps/r2-lab.png"] = icon
    desktop = _read(os.path.join(ROOT, "r2-lab.desktop")).replace(b"\r\n", b"\n")
    files["usr/share/applications/r2-lab.desktop"] = desktop
    files["usr/bin/r2-lab"] = LAUNCHER.encode()
    return files


def _info(name, mtime, size=0, mode=0o644, directory=False):
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = mtime
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    if directory:
        info.type = tarfile.DIRTYPE
    return info


def _tar_gz(files, mtime, executable=()):
    """tar.gz με κάτοχο τον root και όλους τους φακέλους πριν από τα αρχεία τους."""
    dirs = set()
    for name in files:
        parts = name.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        tar.addfile(_info("./", mtime, mode=0o755, directory=True))
        for d in sorted(dirs):
            tar.addfile(_info(f"./{d}/", mtime, mode=0o755, directory=True))
        for name in sorted(files):
            data = files[name]
            mode = 0o755 if name in executable else 0o644
            tar.addfile(_info(f"./{name}", mtime, len(data), mode), io.BytesIO(data))
    return buf.getvalue()


def _ar_member(name, data, mtime):
    header = f"{name:<16}{mtime:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n".encode("ascii")
    assert len(header) == 60
    return header + data + (b"\n" if len(data) % 2 else b"")


def build(out=None):
    ver = version()
    out = out or os.path.join(ROOT, "dist", f"{PACKAGE}_{ver}_all.deb")
    mtime = int(time.time())
    files = payload()
    size_kb = sum((len(d) + 1023) // 1024 for d in files.values()) + len({os.path.dirname(n) for n in files})
    md5sums = "".join(f"{hashlib.md5(files[n]).hexdigest()}  {n}\n" for n in sorted(files))
    control = {
        "control": CONTROL.format(version=ver, size=size_kb).encode("utf-8"),
        "md5sums": md5sums.encode("utf-8"),
        "preinst": PREINST.encode("utf-8"),
        "postinst": POSTINST.encode("utf-8"),
        "prerm": PRERM.encode("utf-8"),
    }
    control_tar = _tar_gz(control, mtime, executable={"preinst", "postinst", "prerm"})
    data_tar = _tar_gz(files, mtime, executable=EXECUTABLE)
    deb = (b"!<arch>\n" + _ar_member("debian-binary", b"2.0\n", mtime)
           + _ar_member("control.tar.gz", control_tar, mtime) + _ar_member("data.tar.gz", data_tar, mtime))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(deb)
    return out


if __name__ == "__main__":
    print("saved", build(sys.argv[1] if len(sys.argv) > 1 else None))
