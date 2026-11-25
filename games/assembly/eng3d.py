"""Μικρή τρισδιάστατη μηχανή για τη Συναρμολόγηση.

Κάθε κομμάτι του R2 είναι μια λίστα από επίπεδα πολύγωνα (Face) με χρώμα και κάθετο διάνυσμα.
Μια ορθογραφική κάμερα (Camera) τα γυρίζει (yaw γύρω από τον κατακόρυφο άξονα, pitch πόσο από ψηλά)
και τα ζωγραφίζουμε από το πιο μακρινό προς το πιο κοντινό (painter's algorithm). Οι μεγάλες
πλευρές χωρίζονται σε κομματάκια ώστε η σειρά να βγαίνει σωστή.

Μονάδες: χιλιοστά. x προς τα δεξιά του ρομπότ (όπως το κοιτάμε από πίσω), y προς τα μπροστά,
z προς τα πάνω. Οι «τρύπες», τα αυτοκόλλητα και τα γράμματα (decals) ζωγραφίζονται αμέσως μετά
την πλευρά τους, μόνο αν φαίνεται εκείνη.
"""
import heapq
import itertools
import math

import pygame


def shade(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c[:3])


def norm(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def centroid(pts):
    k = len(pts)
    return (sum(p[0] for p in pts) / k, sum(p[1] for p in pts) / k, sum(p[2] for p in pts) / k)


def at(axis, t, u, v):
    """Σημείο με συντεταγμένη t στον άξονα axis και (u, v) στους άλλους δύο."""
    if axis == "x":
        return (t, u, v)
    if axis == "y":
        return (u, t, v)
    return (u, v, t)


_groups = itertools.count(1)


class Face:
    __slots__ = ("pts", "col", "n", "decals", "outline", "alpha", "width", "plate", "grp")

    def __init__(self, pts, col, n, outline=True, alpha=255, width=0.0, plate=False, grp=0):
        self.pts, self.col, self.n = pts, col, n
        self.decals = []      # (σημεία, χρώμα) ή ("text", κέντρο, u, v, κείμενο, χρώμα)
        self.outline, self.alpha = outline, alpha
        self.width = width    # για τα καλώδια (n = None): το πάχος σε χιλιοστά
        self.plate = plate    # μεγάλη επίπεδη πλευρά: ό,τι είναι πίσω της ζωγραφίζεται πρώτο (δες _ordered)
        self.grp = grp        # σε ποιο σχήμα (κουτί, κύλινδρο...) ανήκει· οι πλευρές του ίδιου δεν κρύβουν η μία την άλλη


class Mesh:
    def __init__(self, faces=None):
        self.faces = faces if faces is not None else []

    def add(self, other):
        self.faces.extend(other.faces)
        return self

    # ------------------------------------------------------------ σχήματα
    def poly(self, pts, col, normal, **kw):
        f = Face(list(pts), col, normal, **kw)
        self.faces.append(f)
        return f

    def box(self, x0, x1, y0, y1, z0, z1, col, top=None, bottom=None, split=1, plate=False, **kw):
        """Κουτί. Επιστρέφει τις πλευρές του με όνομα (front = +y, back = -y, left = -x ...).

        split: σε πόσα κομμάτια ανά άξονα χωρίζεται κάθε πλευρά (το "top_all" έχει όλα τα κομμάτια).
        """
        kw = dict(kw, grp=next(_groups))
        sides = (
            ("front", [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
            ("back", [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
            ("left", [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
            ("right", [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
            ("top", [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
            ("bottom", [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        )
        out = {}
        for name, pts, n in sides:
            c = top if (name == "top" and top) else (bottom if (name == "bottom" and bottom) else col)
            if split > 1:
                kw2 = dict(kw, outline=False)
                faces = [self.poly(q, c, n, **kw2) for q in split_quad(pts, split)]
                out[name], out[name + "_all"] = faces[0], faces
            else:
                out[name] = self.poly(pts, c, n, **kw)
                out[name + "_all"] = [out[name]]
            if plate:
                for f in out[name + "_all"]:
                    f.plate = face_area(f.pts) > PLATE_AREA
        return out

    def cyl(self, axis, a, b, t0, t1, r, col, n=16, cap=None, groove=None, phase=0.0, caps=(True, True), r1=None,
            **kw):
        """Κύλινδρος (ή κόλουρος κώνος με r1) κατά μήκος του άξονα, με κέντρο (a, b) στους άλλους δύο."""
        r1 = r if r1 is None else r1
        kw = dict(kw, grp=next(_groups))
        sgn = 1 if t1 > t0 else -1
        slope = (r - r1) / max(1e-6, abs(t1 - t0)) * sgn

        def P(t, ang, rr):
            return at(axis, t, a + rr * math.cos(ang), b + rr * math.sin(ang))

        out = {"side": []}
        kw2 = dict(kw, outline=False)
        for i in range(n):
            a0 = phase + 2 * math.pi * i / n
            a1 = phase + 2 * math.pi * (i + 1) / n
            am = (a0 + a1) / 2
            q = [P(t0, a0, r), P(t0, a1, r), P(t1, a1, r1), P(t1, a0, r1)]
            nn = norm(at(axis, slope, math.cos(am), math.sin(am)))
            out["side"].append(self.poly(q, groove if (groove and i % 2) else col, nn, **kw2))
        if caps[0] and r > 0:
            out["cap0"] = self.poly([P(t0, phase + 2 * math.pi * i / n, r) for i in range(n)], cap or col,
                                    at(axis, -sgn, 0, 0), **kw)
        if caps[1] and r1 > 0:
            out["cap1"] = self.poly([P(t1, phase + 2 * math.pi * i / n, r1) for i in range(n)], cap or col,
                                    at(axis, sgn, 0, 0), **kw)
        return out

    def prism(self, axis, outline, t0, t1, col, cap=None, plate=False, **kw):
        """Ένα περίγραμμα (u, v) κάθετα στον άξονα, «τραβηγμένο» από t0 ως t1 (π.χ. πλάκες)."""
        kw = dict(kw, grp=next(_groups))
        out = {"side": []}
        k = len(outline)
        area = sum(outline[i][0] * outline[(i + 1) % k][1] - outline[(i + 1) % k][0] * outline[i][1]
                   for i in range(k))
        sgn = 1 if area > 0 else -1
        kw2 = dict(kw, outline=False)
        for i in range(k):
            (u0, v0), (u1, v1) = outline[i], outline[(i + 1) % k]
            q = [at(axis, t0, u0, v0), at(axis, t0, u1, v1), at(axis, t1, u1, v1), at(axis, t1, u0, v0)]
            out["side"].append(self.poly(q, col, norm(at(axis, 0, (v1 - v0) * sgn, -(u1 - u0) * sgn)), **kw2))
        hi, lo = (t1, t0) if t1 > t0 else (t0, t1)
        out["cap_hi"] = self.poly([at(axis, hi, u, v) for u, v in outline], cap or col, at(axis, 1, 0, 0), **kw)
        out["cap_lo"] = self.poly([at(axis, lo, u, v) for u, v in outline], cap or col, at(axis, -1, 0, 0), **kw)
        if plate:
            out["cap_hi"].plate = out["cap_lo"].plate = face_area(out["cap_hi"].pts) > PLATE_AREA
        return out

    def sphere(self, c, r, col, n=12, m=7):
        grp = next(_groups)
        for j in range(m):
            t0, t1 = math.pi * j / m - math.pi / 2, math.pi * (j + 1) / m - math.pi / 2
            for i in range(n):
                a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                pts = [(c[0] + r * math.cos(t) * math.cos(a), c[1] + r * math.cos(t) * math.sin(a), c[2] + r * math.sin(t))
                       for t, a in ((t0, a0), (t0, a1), (t1, a1), (t1, a0))]
                tm, am = (t0 + t1) / 2, (a0 + a1) / 2
                self.poly(pts, col, (math.cos(tm) * math.cos(am), math.cos(tm) * math.sin(am), math.sin(tm)),
                          outline=False, grp=grp)

    def tube(self, pts, col, width):
        """Καλώδιο: σειρά από χοντρές γραμμές (φαίνονται από κάθε μεριά)."""
        for a, b in zip(pts, pts[1:]):
            self.faces.append(Face([a, b], col, None, False, 255, width))

    # ------------------------------------------------------------ μετασχηματισμοί
    def mapped(self, fp, fn):
        out = Mesh()
        for f in self.faces:
            if f.n is None:
                out.faces.append(Face([fp(f.pts[0]), fp(f.pts[1])], f.col, None, False, 255, f.width))
                continue
            g = Face([fp(p) for p in f.pts], f.col, fn(f.n), f.outline, f.alpha, plate=f.plate, grp=f.grp)
            for d in f.decals:
                if d[0] == "text":
                    _, c, u, v, s, col = d
                    g.decals.append(("text", fp(c), fn(u), fn(v), s, col))
                else:
                    g.decals.append(([fp(p) for p in d[0]], d[1]))
            out.faces.append(g)
        return out

    def moved(self, dx, dy, dz):
        return self.mapped(lambda p: (p[0] + dx, p[1] + dy, p[2] + dz), lambda n: n)

    def tinted(self, col, alpha):
        """Ίδιο σχήμα, ένα διάφανο χρώμα (το «φάντασμα» που δείχνει πού πάει ένα κομμάτι)."""
        return Mesh([Face(f.pts, col, f.n, True, alpha, plate=f.plate, grp=f.grp) for f in self.faces
                     if f.n is not None])

    def points(self):
        for f in self.faces:
            yield from f.pts


PLATE_AREA = 80.0     # mm²: πλευρές πιο μεγάλες από αυτό μετράνε ως «πλάκες»


def face_area(pts):
    nx = ny = nz = 0.0
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        nx += a[1] * b[2] - a[2] * b[1]
        ny += a[2] * b[0] - a[0] * b[2]
        nz += a[0] * b[1] - a[1] * b[0]
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def split_quad(pts, k):
    a, b, c, d = pts

    def lerp(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t)

    out = []
    for i in range(k):
        for j in range(k):
            u0, u1, v0, v1 = i / k, (i + 1) / k, j / k, (j + 1) / k
            out.append([lerp(lerp(a, b, u0), lerp(d, c, u0), v0), lerp(lerp(a, b, u1), lerp(d, c, u1), v0),
                        lerp(lerp(a, b, u1), lerp(d, c, u1), v1), lerp(lerp(a, b, u0), lerp(d, c, u0), v1)])
    return out


def circle_pts(axis, t, a, b, r, n=12, phase=0.0):
    return [at(axis, t, a + r * math.cos(phase + 2 * math.pi * i / n), b + r * math.sin(phase + 2 * math.pi * i / n))
            for i in range(n)]


def rounded_rect(u0, u1, v0, v1, r, n=5):
    pts = []
    for cu, cv, a0 in ((u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180), (u1 - r, v0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def bezier(p0, p1, p2, p3, n=16):
    out = []
    for k in range(n + 1):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append(tuple(a * p0[i] + b * p1[i] + c * p2[i] + d * p3[i] for i in range(3)))
    return out


def decal_on(faces, pts, col):
    """Βάζει ένα «αυτοκόλλητο» στο κομμάτι της πλευράς (από τα faces) που περιέχει το κέντρο του."""
    c = centroid(pts)
    for f in faces:
        xs, ys, zs = [p[0] for p in f.pts], [p[1] for p in f.pts], [p[2] for p in f.pts]
        if (min(xs) - 0.01 <= c[0] <= max(xs) + 0.01 and min(ys) - 0.01 <= c[1] <= max(ys) + 0.01
                and min(zs) - 0.01 <= c[2] <= max(zs) + 0.01):
            f.decals.append((pts, col))
            return f
    faces[0].decals.append((pts, col))
    return faces[0]


# ---------------------------------------------------------------- κάμερα
class Camera:
    """Ορθογραφική κάμερα. yaw: 0 = κοιτάμε από πίσω, 90 = από δεξιά, 180 = από μπροστά.
    pitch: πόσες μοίρες από ψηλά. scale: pixels ανά χιλιοστό. (cx, cy): πού πέφτει το σημείο (0, 0, 0).
    """

    LIGHT = norm((-0.45, 0.62, 0.64))    # από πάνω αριστερά, λίγο προς εμάς (στις συντεταγμένες της κάμερας)

    def __init__(self, yaw, pitch, scale, cx=0.0, cy=0.0):
        self.yaw, self.pitch, self.scale, self.cx, self.cy = yaw, pitch, scale, cx, cy
        self.cyw, self.syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        self.cp, self.sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def looking_at(self, target, screen):
        """Η ίδια κάμερα, μετακινημένη ώστε το σημείο target να πέφτει στο σημείο screen της οθόνης."""
        sx, sy = Camera(self.yaw, self.pitch, self.scale).proj(target)
        return Camera(self.yaw, self.pitch, self.scale, screen[0] - sx, screen[1] - sy)

    def moved(self, dx, dy):
        return Camera(self.yaw, self.pitch, self.scale, self.cx + dx, self.cy + dy)

    def scaled(self, f, ox=0.0, oy=0.0):
        """Για ζωγράφισμα σε μεγαλύτερη εικόνα που ξεκινά στο (ox, oy) της οθόνης."""
        return Camera(self.yaw, self.pitch, self.scale * f, (self.cx - ox) * f, (self.cy - oy) * f)

    def cam(self, p):
        x, y, z = p
        x1 = x * self.cyw + y * self.syw
        y1 = -x * self.syw + y * self.cyw
        return x1, y1 * self.sp + z * self.cp, y1 * self.cp - z * self.sp

    def proj(self, p):
        x1, up, _ = self.cam(p)
        return (self.cx + x1 * self.scale, self.cy - up * self.scale)

    def depth(self, p):
        x, y, z = p
        return (-x * self.syw + y * self.cyw) * self.cp - z * self.sp

    def facing(self, n):
        y1 = -n[0] * self.syw + n[1] * self.cyw
        return -(y1 * self.cp - n[2] * self.sp)

    def light(self, n):
        x1 = n[0] * self.cyw + n[1] * self.syw
        y1 = -n[0] * self.syw + n[1] * self.cyw
        up = y1 * self.sp + n[2] * self.cp
        toward = -(y1 * self.cp - n[2] * self.sp)
        L = self.LIGHT
        return max(0.0, x1 * L[0] + up * L[1] + toward * L[2])

    def unproject(self, sx, sy, z):
        """Το σημείο του οριζόντιου επιπέδου (ύψος z) που φαίνεται στη θέση (sx, sy) της οθόνης."""
        x1 = (sx - self.cx) / self.scale
        up = (self.cy - sy) / self.scale
        y1 = (up - z * self.cp) / max(0.05, self.sp)
        return (x1 * self.cyw - y1 * self.syw, x1 * self.syw + y1 * self.cyw, z)


def bounds(cam, meshes, pad=4):
    """Το ορθογώνιο της οθόνης που πιάνουν τα κομμάτια."""
    xs, ys = [], []
    for m in meshes:
        for p in m.points():
            sx, sy = cam.proj(p)
            xs.append(sx)
            ys.append(sy)
    if not xs:
        return pygame.Rect(0, 0, 0, 0)
    x0, y0 = math.floor(min(xs)) - pad, math.floor(min(ys)) - pad
    return pygame.Rect(x0, y0, math.ceil(max(xs)) + pad - x0, math.ceil(max(ys)) + pad - y0)


def _ordered(cam, meshes):
    """Η σειρά ζωγραφίσματος: από το πιο μακρινό στο πιο κοντινό, με μια διόρθωση για τις «πλάκες».

    Η απλή ταξινόμηση με το κέντρο κάθε πλευράς κάνει λάθη όταν κάτι μικρό είναι ακριβώς κάτω από μια
    μεγάλη πλάκα (η βίδα κάτω από τη βάση, το πάνω μέρος των κινητήρων): φαινόταν «μέσα από» την πλάκα.
    Γι' αυτό, για κάθε πλάκα που φαίνεται: ό,τι είναι ολόκληρο πίσω από το επίπεδό της και πέφτει πάνω της
    στην οθόνη ζωγραφίζεται πριν από αυτή, και ό,τι είναι ολόκληρο μπροστά ζωγραφίζεται μετά.
    Επιστρέφει [(πλευρά, σημεία στην οθόνη)].
    """
    items = []
    for m in meshes:
        for f in m.faces:
            if f.n is not None and cam.facing(f.n) <= 0.01:
                continue
            pts = [cam.proj(p) for p in f.pts]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            d = sum(cam.depth(p) for p in f.pts) / len(f.pts)
            items.append((f, pts, d, min(xs), max(xs), min(ys), max(ys)))
    n = len(items)
    succ = [[] for _ in range(n)]
    indeg = [0] * n
    for pi in range(n):
        P = items[pi][0]
        if not P.plate:
            continue
        ax0, ax1, ay0, ay1 = items[pi][3:]
        nx, ny, nz = P.n
        ox, oy, oz = P.pts[0]
        grp = P.grp
        # δύο κατευθύνσεις πάνω στην πλάκα: μετράμε αν κάτι είναι πραγματικά από πάνω ή από κάτω της
        u = norm((ny, -nx, 0.0) if abs(nz) < 0.9 else (1.0, 0.0, -nx / nz if nz else 0.0))
        w = (ny * u[2] - nz * u[1], nz * u[0] - nx * u[2], nx * u[1] - ny * u[0])
        pu = [p[0] * u[0] + p[1] * u[1] + p[2] * u[2] for p in P.pts]
        pw = [p[0] * w[0] + p[1] * w[1] + p[2] * w[2] for p in P.pts]
        u0, u1, w0, w1 = min(pu) + 0.3, max(pu) - 0.3, min(pw) + 0.3, max(pw) - 0.3
        for fi in range(n):
            it = items[fi]
            if it[3] >= ax1 - 1 or it[4] <= ax0 + 1 or it[5] >= ay1 - 1 or it[6] <= ay0 + 1 or fi == pi:
                continue
            if grp and it[0].grp == grp:           # πλευρές του ίδιου σχήματος δεν κρύβουν η μία την άλλη
                continue
            fpts = it[0].pts
            fu = [p[0] * u[0] + p[1] * u[1] + p[2] * u[2] for p in fpts]
            if max(fu) <= u0 or min(fu) >= u1:     # δίπλα στην πλάκα, όχι από πάνω ή από κάτω της
                continue
            fw = [p[0] * w[0] + p[1] * w[1] + p[2] * w[2] for p in fpts]
            if max(fw) <= w0 or min(fw) >= w1:
                continue
            lo, hi = 1e9, -1e9
            for x, y, z in fpts:
                v = (x - ox) * nx + (y - oy) * ny + (z - oz) * nz
                if v < lo:
                    lo = v
                if v > hi:
                    hi = v
            # (μετράει και ό,τι απλώς ακουμπά την πλάκα, π.χ. τα «μάτια» πάνω στον αισθητήρα υπερήχων)
            if hi <= 0.05 and lo < -0.05:           # ολόκληρο πίσω από την πλάκα: πρώτα αυτό
                succ[fi].append(pi)
                indeg[pi] += 1
            elif lo >= -0.05 and hi > 0.05:         # ολόκληρο μπροστά: μετά την πλάκα
                succ[pi].append(fi)
                indeg[fi] += 1
    heap = [(-items[i][2], i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    by_depth = sorted(range(n), key=lambda i: -items[i][2])
    done = [False] * n
    order, k = [], 0
    while len(order) < n:
        if not heap:
            # κύκλος (σπάνιο): βγάζουμε το πιο μακρινό που περιμένει, και συνεχίζουμε κανονικά
            while done[by_depth[k]]:
                k += 1
            heapq.heappush(heap, (-items[by_depth[k]][2], by_depth[k]))
        _, i = heapq.heappop(heap)
        if done[i]:
            continue
        done[i] = True
        order.append(i)
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0 and not done[j]:
                heapq.heappush(heap, (-items[j][2], j))
    return [(items[i][0], items[i][1]) for i in order]


def _translucent(surf, pts, col, alpha, edge):
    """Ημιδιάφανη πλευρά (το ακρυλικό, τα «φαντάσματα») σε δικό της στρώμα, ώστε να ανακατευτεί με ό,τι
    είναι από κάτω. Αν ζωγραφιζόταν κατευθείαν, θα «έσβηνε» την εικόνα από κάτω της (θα φαινόταν το
    ταπέτο αντί για την πλακέτα)."""
    x0, y0 = math.floor(min(p[0] for p in pts)) - 2, math.floor(min(p[1] for p in pts)) - 2
    x1, y1 = math.ceil(max(p[0] for p in pts)) + 2, math.ceil(max(p[1] for p in pts)) + 2
    if x1 <= x0 or y1 <= y0:
        return
    layer = pygame.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
    local = [(x - x0, y - y0) for x, y in pts]
    pygame.draw.polygon(layer, (*col, alpha), local)
    pygame.draw.aalines(layer, (*edge, min(255, alpha + 100)), True, local)
    surf.blit(layer, (x0, y0))


def draw(surf, cam, meshes, outline=True):
    """Ζωγραφίζει όλα τα πολύγωνα από το πιο μακρινό στο πιο κοντινό."""
    edge_w = max(1, round(cam.scale * 0.32))
    for f, pts in _ordered(cam, meshes):
        if f.n is None:
            w = max(1, round(f.width * cam.scale))
            pygame.draw.line(surf, f.col, pts[0], pts[1], w)
            if w > 3:
                pygame.draw.circle(surf, f.col, pts[1], w / 2)
            continue
        lit = 0.58 + 0.5 * cam.light(f.n)
        col = shade(f.col, lit)
        if f.alpha < 255:
            _translucent(surf, pts, col, f.alpha, shade(f.col, 1.15))
        else:
            pygame.draw.polygon(surf, col, pts)
            if outline and f.outline:
                bright = sum(f.col[:3])
                ec = (74, 76, 86) if bright < 160 else shade(f.col, 0.5 if bright > 300 else 0.6)
                pygame.draw.lines(surf, ec, True, pts, edge_w)
        for d in f.decals:
            if d[0] == "text":
                _text_decal(surf, cam, d)
            else:
                pygame.draw.polygon(surf, shade(d[1], lit), [cam.proj(p) for p in d[0]])


_fonts = {}


def _text_decal(surf, cam, d):
    """Γράμματα πάνω σε μια πλευρά: u, v είναι οι κατευθύνσεις (και το μέγεθος) του κειμένου."""
    _, c, u, v, s, col = d
    size = max(6, round(cam.scale * 5.2))
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("segoeui,arial,dejavusans,freesans", size, bold=True)
    p0 = cam.proj(c)
    pu = cam.proj((c[0] + u[0], c[1] + u[1], c[2] + u[2]))
    pv = cam.proj((c[0] + v[0], c[1] + v[1], c[2] + v[2]))
    fx = math.hypot(pu[0] - p0[0], pu[1] - p0[1]) / cam.scale
    fy = math.hypot(pv[0] - p0[0], pv[1] - p0[1]) / cam.scale
    if fx < 0.25 or fy < 0.12:
        return
    img = _fonts[size].render(s, True, col)
    w, h = img.get_size()
    img = pygame.transform.smoothscale(img, (max(1, round(w * fx)), max(1, round(h * fy))))
    ang = math.degrees(math.atan2(-(pu[1] - p0[1]), pu[0] - p0[0]))
    # αν το κείμενο φαίνεται «καθρέφτης» (βλέπουμε την πλευρά από την άλλη μεριά), μην το γράψεις
    cross = (pu[0] - p0[0]) * (pv[1] - p0[1]) - (pu[1] - p0[1]) * (pv[0] - p0[0])
    if cross > 0:
        return
    img = pygame.transform.rotate(img, ang)
    surf.blit(img, img.get_rect(center=(round(p0[0]), round(p0[1]))))


def render(meshes, cam, rect=None, ss=2, outline=True):
    """Ζωγραφίζει τα κομμάτια σε διάφανη εικόνα, σε ss φορές μεγαλύτερο μέγεθος, και τη μικραίνει.

    rect: το κομμάτι της οθόνης που θέλουμε (αλλιώς όσο πιάνουν τα κομμάτια). Επιστρέφει (εικόνα, rect).
    """
    if rect is None:
        rect = bounds(cam, meshes)
    rect = pygame.Rect(rect)
    if rect.w <= 0 or rect.h <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA), pygame.Rect(rect.x, rect.y, 1, 1)
    big = pygame.Surface((rect.w * ss, rect.h * ss), pygame.SRCALPHA)
    draw(big, cam.scaled(ss, rect.x, rect.y), meshes, outline)
    return pygame.transform.smoothscale(big, rect.size), rect


def fit_camera(meshes, yaw, pitch, size, pad=8):
    """Κάμερα που χωράει τα κομμάτια ακριβώς μέσα σε εικόνα μεγέθους size (για τις κάρτες)."""
    c = Camera(yaw, pitch, 1.0)
    pts = [c.proj(p) for m in meshes for p in m.points()]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(1e-3, max(xs) - min(xs)), max(1e-3, max(ys) - min(ys))
    s = min((size[0] - 2 * pad) / w, (size[1] - 2 * pad) / h)
    return Camera(yaw, pitch, s, size[0] / 2 - (min(xs) + w / 2) * s, size[1] / 2 - (min(ys) + h / 2) * s)


def thumbnail(meshes, size, yaw=-30, pitch=28, pad=8):
    cam = fit_camera(meshes, yaw, pitch, size, pad)
    img, _ = render(meshes, cam, pygame.Rect(0, 0, size[0], size[1]))
    return img
