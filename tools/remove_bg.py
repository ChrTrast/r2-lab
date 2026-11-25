"""Background removal for the R2 part photos (beige wall, soft shadows).

Learns the wall colour from the photo border (smooth quadratic fit, so the
lighting gradient is followed), then marks as "part" any pixel that is
clearly bluer/whiter, more colourful or much darker than the wall.
Soft shadows (a bit darker, same hue) stay background.
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter, ImageOps

WORK = 1400         # side used to compute the mask
OUT_MAX = 900       # max side of the saved cut-out
PAD = 0.04          # margin around the part (fraction of its size)


def srgb_to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def fit_background(lab):
    """Quadratic surface per channel, fitted to the outer border band."""
    h, w, _ = lab.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = xx / w - 0.5, yy / h - 0.5
    band = max(4, int(0.06 * min(h, w)))
    border = np.zeros((h, w), bool)
    border[:band] = border[-band:] = True
    border[:, :band] = border[:, -band:] = True
    A = np.stack([np.ones_like(xn), xn, yn, xn * xn, yn * yn, xn * yn], -1)
    Ab = A[border]
    bg = np.empty_like(lab)
    for ch in range(3):
        v = lab[..., ch][border]
        keep = np.ones(len(v), bool)
        for _ in range(3):                      # robust: drop outliers
            coef, *_ = np.linalg.lstsq(Ab[keep], v[keep], rcond=None)
            res = v - Ab @ coef
            s = np.std(res[keep]) + 1e-6
            keep = np.abs(res) < 2.5 * s
        bg[..., ch] = A @ coef
    noise = np.array([np.std((lab[..., c] - bg[..., c])[border]) for c in range(3)])
    return bg, noise


def largest_components(mask, keep_frac=0.15):
    """Keep the biggest blob, plus any blob at least keep_frac of its size."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    sizes = [0]
    cur = 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if labels[y0, x0]:
            continue
        cur += 1
        labels[y0, x0] = cur
        q = deque([(y0, x0)])
        n = 0
        while q:
            y, x = q.popleft()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur
                    q.append((ny, nx))
        sizes.append(n)
    if cur == 0:
        return mask
    sizes = np.array(sizes)
    big = sizes.max()
    good = np.nonzero(sizes >= keep_frac * big)[0]
    good = good[good > 0]
    return np.isin(labels, good)


def fill_holes(mask):
    m = Image.fromarray((mask * 255).astype(np.uint8))
    m = ImageOps.expand(m, 1, fill=0)
    from PIL import ImageDraw
    ImageDraw.floodfill(m, (0, 0), 128)
    a = np.array(m)[1:-1, 1:-1]
    return a != 128


def morph(mask, size, op):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    f = ImageFilter.MaxFilter(size) if op == "dilate" else ImageFilter.MinFilter(size)
    return np.array(im.filter(f)) > 127


def make_mask(img, boxy=False, solid=True, opt=None):
    opt = opt or {}
    small = img.copy()
    small.thumbnail((WORK, WORK), Image.LANCZOS)
    small = small.filter(ImageFilter.GaussianBlur(1.0))
    lab = srgb_to_lab(np.asarray(small, np.float64))
    bg, noise = fit_background(lab)
    d = lab - bg
    dL, da, db = d[..., 0], d[..., 1], d[..., 2]
    chroma_diff = np.hypot(da, db)
    nb = max(noise[2], 0.8)
    na = max(noise[1], 0.6)
    nl = max(noise[0], 1.0)

    L = lab[..., 0]
    # Boards are white-on-beige, so the "bluer" test must be gentle there.
    # Coloured cables tint the wall next to them, so they get stricter tests.
    blue_t = opt.get("blue_t", 4.0)
    col_t = opt.get("col_t", 9.0)
    bluer = db < -max(blue_t, 4 * nb)                    # white PCB, blue/grey parts
    brighter = dL > max(opt.get("bright_t", 5.0), 4 * nl)                     # white plastic / PCB
    colourful = chroma_diff > max(col_t, 5 * max(na, nb))  # red/yellow/blue/green
    # Deep shadows get as dark as black plastic but keep the wall's beige hue;
    # black/grey parts lose it (b* drops) or are truly black.
    black = (L < 32) | ((dL < -20) & (db < -3.0))
    mask = bluer | brighter | colourful | black

    s = max(small.size) / 700                  # kernels were tuned at 700 px
    k1 = opt.get("open", int(3 * s) | 1 if solid else 3)   # thin cables must survive
    k2 = opt.get("close", int(5 * s) | 1 if solid else 5)  # keep gaps between wires
    mask = morph(mask, k1, "erode")
    mask = morph(mask, k1, "dilate")
    mask = morph(mask, k2, "dilate")
    mask = morph(mask, k2, "erode")
    mask = largest_components(mask)
    if boxy == "inner":
        # Fill everything inside the outline except a band along its edge,
        # so a mirror-like part in the middle comes back without adding
        # wall wedges at the rim.
        hull = convex_hull_mask(mask)
        r = int(opt.get("band", 0.025) * max(mask.shape)) * 2 + 1
        mask = mask | (hull & morph(hull, r, "erode"))
    elif boxy:
        mask = add_thick_concavities(mask)
    if solid:
        mask = fill_holes(mask)                 # boards: nothing is see-through
    else:
        # wall next to a coloured part picks up a little of its colour
        wall_or_shadow = (dL < 8) & (chroma_diff < 7.0)
        mask = fill_holes_smart(mask, wall_or_shadow)
    return mask, small.size


def label(mask):
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    sizes = [0]
    cur = 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if labels[y0, x0]:
            continue
        cur += 1
        labels[y0, x0] = cur
        q = deque([(y0, x0)])
        n = 0
        while q:
            y, x = q.popleft()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur
                    q.append((ny, nx))
        sizes.append(n)
    return labels, np.array(sizes)


def fill_holes_smart(mask, wall_like):
    """Fill enclosed gaps inside solid parts (e.g. an RGB LED that looks like
    the wall), but keep see-through the wall/shadow seen inside a loop of
    thin cable: there the surrounding part is thin, so a short step out of
    the gap already reaches other wall."""
    outside = ~fill_holes(mask)                 # background reachable from border
    holes = ~mask & ~outside
    labels, sizes = label(holes)
    area = mask.sum()
    h, w = mask.shape
    r = max(8, int(0.014 * max(h, w)))
    out = mask.copy()
    for i in range(1, len(sizes)):
        region = labels == i
        if sizes[i] < 0.004 * area:
            out |= region                       # tiny: screw holes, noise
            continue
        ys, xs = np.nonzero(region)
        y0, y1 = max(0, ys.min() - r - 1), min(h, ys.max() + r + 2)
        x0, x1 = max(0, xs.min() - r - 1), min(w, xs.max() + r + 2)
        sub = region[y0:y1, x0:x1]
        grown = morph(sub, 2 * r + 1, "dilate")
        ring = grown & ~sub
        not_part = ~mask[y0:y1, x0:x1]
        thin_frac = not_part[ring].mean() if ring.any() else 0.0
        wall_frac = wall_like[region].mean()
        see_through = (thin_frac > 0.12 and wall_frac > 0.5) or wall_frac > 0.85
        if not see_through:
            out |= region
    return out


def convex_hull_mask(mask):
    """Filled convex hull of a mask (monotone chain on boundary points)."""
    ys, xs = np.nonzero(mask)
    pts = sorted(set(zip(xs.tolist(), ys.tolist())))
    if len(pts) < 3:
        return mask

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    from PIL import ImageDraw
    im = Image.new("L", (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(im).polygon(hull, fill=255)
    return np.array(im) > 127


def add_thick_concavities(mask):
    """For boxy boards: put back chunks lost inside the outline (a shiny
    port that mirrors the wall), but not the thin slivers between parts
    that stick out of the board edge."""
    hull = convex_hull_mask(mask)
    gap = hull & ~mask
    k = max(9, int(0.03 * max(mask.shape))) | 1
    thick = morph(morph(gap, k, "erode"), k, "dilate")
    return mask | (thick & gap)


BOXY = {"IMG_20261105_105907": True,      # control board: plain rectangle
        "IMG_20261105_110610": "inner"}   # ball caster: mirror ball inside
LOOPY = {"IMG_20261105_110447",  # motor, servo, USB and RJ cables:
         "IMG_20261105_110503",  # the wall shows inside their loops
         "IMG_20261105_110517",
         "IMG_20261105_110527"}
OPT = {"IMG_20261105_110517": {"blue_t": 10.0, "col_t": 14.0, "open": 7, "close": 11},   # USB: tints the wall blue
       "IMG_20261105_110527": {"close": 11},                     # RJ cables
       "IMG_20261105_110610": {"bright_t": 8.0, "band": 0.009}}  # ball caster


def cut(path, out_path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    stem = os.path.splitext(os.path.basename(path))[0]
    mask, (sw, sh) = make_mask(img, boxy=BOXY.get(stem, False), solid=stem not in LOOPY,
                               opt=OPT.get(stem))
    ys, xs = np.nonzero(mask)
    W, H = img.size
    sx, sy = W / sw, H / sh
    x0, x1, y0, y1 = xs.min() * sx, (xs.max() + 1) * sx, ys.min() * sy, (ys.max() + 1) * sy
    pw, ph = (x1 - x0) * PAD + 8, (y1 - y0) * PAD + 8
    box = (int(max(0, x0 - pw)), int(max(0, y0 - ph)), int(min(W, x1 + pw)), int(min(H, y1 + ph)))

    m_img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    m_img = m_img.resize((W, H), Image.BICUBIC)
    crop = img.crop(box)
    alpha = m_img.crop(box)
    scale = min(1.0, OUT_MAX / max(crop.size))
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    crop = crop.resize(size, Image.LANCZOS)
    alpha = alpha.resize(size, Image.LANCZOS)
    # Slightly tighten and soften the edge so no beige halo remains.
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = crop.copy()
    out.putalpha(alpha)
    out.save(out_path, optimize=True)
    return out


def sheet(images, names, path, bg=(40, 44, 60)):
    cell = 260
    cols = 5
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * cell), bg)
    for i, im in enumerate(images):
        t = im.copy()
        t.thumbnail((cell - 16, cell - 16), Image.LANCZOS)
        x = (i % cols) * cell + (cell - t.width) // 2
        y = (i // cols) * cell + (cell - t.height) // 2
        canvas.paste(t, (x, y), t)
    canvas.save(path)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or sorted(f for f in os.listdir(src) if f.lower().endswith(".jpg"))
    os.makedirs(dst, exist_ok=True)
    outs = []
    for f in names:
        o = cut(os.path.join(src, f), os.path.join(dst, os.path.splitext(f)[0] + ".png"))
        print(f, o.size)
        outs.append(o)
    sheet(outs, names, os.path.join(dst, "_preview_dark.png"))
    sheet(outs, names, os.path.join(dst, "_preview_light.png"), bg=(250, 250, 250))
