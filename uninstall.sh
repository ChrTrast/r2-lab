#!/bin/bash
# Απεγκατάσταση του Εργαστηρίου R2.   sudo ./uninstall.sh   (ή: bash uninstall.sh)
set -e
if [ "$(id -u)" -ne 0 ]; then
    exec sudo bash "$0" "$@"
fi
rm -rf /opt/r2-lab
rm -f /usr/local/bin/r2-lab /usr/share/applications/r2-lab.desktop /usr/share/pixmaps/r2-lab.png
update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Το Εργαστήρι R2 αφαιρέθηκε. (Τα σχέδια των Κύβων κάθε χρήστη μένουν στο ~/.config/r2-lab)"
