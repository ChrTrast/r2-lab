"""Φτιάχνει το εικονίδιο της εφαρμογής: assets/r2-lab.png (μενού εφαρμογών του Linux)
και assets/r2-lab.ico (το .exe και ο installer των Windows).

    python3 tools/make_icon.py
"""
import io
import os
import struct
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from core import ui  # noqa: E402
from games.cubes import art as cubes_art  # noqa: E402
from games.maze import art as r2  # noqa: E402

SIZE = 256


def make_icon():
    pygame.init()
    pygame.display.set_mode((1, 1))
    s = 2
    # ζωγραφίζουμε σε συμπαγή επιφάνεια (για σωστές σκιές) και μετά κόβουμε τις γωνίες
    big = pygame.Surface((SIZE * s, SIZE * s))
    big.fill((62, 140, 226))
    pygame.draw.rect(big, (126, 192, 92), (0, 168 * s, SIZE * s, 88 * s))
    for x, y, r in ((70, 62, 26), (100, 54, 32), (132, 64, 24)):
        ui.circle(big, (255, 255, 255), (x * s, y * s), r * s)
    # λευκή πίστα με τη μαύρη γραμμή του line follower
    pygame.draw.rect(big, (226, 222, 210), (0, 172 * s, SIZE * s, 52 * s))
    pygame.draw.rect(big, (248, 246, 238), (0, 170 * s, SIZE * s, 51 * s))
    pygame.draw.rect(big, (28, 28, 32), (0, 190 * s, SIZE * s, 12 * s))
    cubes_art.draw_cube(big, 4, 160 * s, 196 * s, 40 * s)
    cubes_art.draw_cube(big, 2, 200 * s, 196 * s, 40 * s)
    cubes_art.draw_cube(big, 1, 180 * s, 156 * s, 40 * s)
    r2.draw_robot(big, (72 * s, 196 * s), 86 * s, 90, r2.LED_GREEN)
    icon = pygame.Surface((SIZE * s, SIZE * s), pygame.SRCALPHA)
    icon.blit(big, (0, 0))
    mask = pygame.Surface((SIZE * s, SIZE * s), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (8 * s, 8 * s, 240 * s, 240 * s), border_radius=52 * s)
    icon.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return pygame.transform.smoothscale(icon, (SIZE, SIZE))


ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def write_ico(icon, out):
    """Γράφει το εικονίδιο σε .ico με όλα τα μεγέθη που θέλουν τα Windows (το καθένα σε PNG)."""
    images = []
    for size in ICO_SIZES:
        buf = io.BytesIO()
        pygame.image.save(pygame.transform.smoothscale(icon, (size, size)), buf, "png")
        images.append((size, buf.getvalue()))
    offset = 6 + 16 * len(images)
    data = struct.pack("<HHH", 0, 1, len(images))
    for size, png in images:
        side = 0 if size >= 256 else size           # το 0 σημαίνει 256
        data += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    with open(out, "wb") as f:
        f.write(data + b"".join(png for _, png in images))


if __name__ == "__main__":
    out = os.path.join(ROOT, "assets", "r2-lab.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    icon = make_icon()
    pygame.image.save(icon, out)
    print("saved", out)
    write_ico(icon, os.path.splitext(out)[0] + ".ico")
    print("saved", os.path.splitext(out)[0] + ".ico")
