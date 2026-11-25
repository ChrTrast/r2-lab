#!/bin/bash
# Εγκατάσταση του Εργαστηρίου R2 σε Ubuntu / Xubuntu για όλους τους χρήστες.
#   sudo ./install.sh        (ή: bash install.sh)
set -e
if [ "$(id -u)" -ne 0 ]; then
    exec sudo bash "$0" "$@"
fi
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/r2-lab

echo ">> Εγκατάσταση python3-pygame"
if ! PYGAME_HIDE_SUPPORT_PROMPT=1 python3 -c "import pygame" 2>/dev/null; then
    apt-get install -y python3-pygame || { apt-get update && apt-get install -y python3-pygame; }
fi

# Η προηγούμενη έκδοση λεγόταν «Παιχνίδια Μάθησης» (edu-games). Τη σβήνουμε,
# για να μη βγαίνουν δύο εικονίδια στο μενού.
if dpkg-query -W -f='${Status}' edu-games 2>/dev/null | grep -q "ok installed"; then
    echo ">> Αφαίρεση της παλιάς έκδοσης (πακέτο edu-games)"
    apt-get remove -y edu-games
fi
rm -rf /opt/edu-games
rm -f /usr/local/bin/edu-games /usr/share/applications/edu-games.desktop /usr/share/pixmaps/edu-games.png

echo ">> Αντιγραφή αρχείων στο $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -r "$SRC/core" "$SRC/games" "$SRC/assets" "$SRC/main.py" "$SRC/README.md" "$DEST/"
find "$DEST" -name __pycache__ -prune -exec rm -rf {} +
python3 -m compileall -q "$DEST" || true
chmod -R a+rX "$DEST"

echo ">> Εκκινητής και μενού εφαρμογών"
cat > /usr/local/bin/r2-lab << 'LAUNCH'
#!/bin/sh
exec python3 /opt/r2-lab/main.py "$@"
LAUNCH
chmod 755 /usr/local/bin/r2-lab
install -m 644 "$SRC/assets/r2-lab.png" /usr/share/pixmaps/r2-lab.png
install -m 644 "$SRC/r2-lab.desktop" /usr/share/applications/r2-lab.desktop
update-desktop-database -q /usr/share/applications 2>/dev/null || true

echo ">> Έτοιμο. Βρίσκεται στο μενού: Εκπαίδευση > Εργαστήρι R2  (ή εντολή: r2-lab)"
