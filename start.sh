#!/bin/bash
# Ξεκινά τα παιχνίδια χωρίς εγκατάσταση (Linux).   ./start.sh   (ή: bash start.sh)
#   ./start.sh --window    σε παράθυρο (αλλιώς πλήρης οθόνη)
cd "$(dirname "$0")"
if ! PYGAME_HIDE_SUPPORT_PROMPT=1 python3 -c "import pygame" 2>/dev/null; then
    echo "Λείπει το pygame. Εγκατάσταση:  sudo apt install python3-pygame"
    exit 1
fi
exec python3 main.py "$@"
