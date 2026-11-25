"""Τα κομμάτια του R2 σε 3D, στη θέση που έχουν όταν το ρομπότ είναι συναρμολογημένο (χιλιοστά).

Τα σχήματα ακολουθούν τις φωτογραφίες του οδηγού συναρμολόγησης: μαύρο μεταλλικό σασί με πλαϊνά
τοιχώματα, κίτρινοι κινητήρες κάτω από τη βάση, ασπρόμαυρες ρόδες, ο αισθητήρας υπερήχων μπροστά,
ο αισθητήρας γραμμής και ο σφαιρικός τροχός από κάτω, η βάση για τουβλάκια μπροστά, η θήκη μπαταρίας,
ο λευκός ελεγκτής polytech πάνω σε χάλκινα διαχωριστικά και το διάφανο ακρυλικό πάνελ.
"""
import math

from . import eng3d as E
from .eng3d import Mesh, at, bezier, circle_pts, decal_on, rounded_rect

CHASSIS = (46, 47, 53)
BRASS = (222, 176, 78)
YELLOW_M = (250, 200, 44)
SILVER = (186, 190, 198)
WHITE_PL = (244, 244, 240)
PCB = (238, 240, 236)
TIRE, GROOVE = (44, 45, 50), (28, 29, 33)
SOCKET = (34, 36, 42)
HOLE = (12, 12, 16)
Y, R, G, B = (250, 214, 40), (226, 56, 52), (52, 162, 80), (70, 172, 232)
CABLE = (40, 92, 214)
RED_W, BLACK_W = (214, 40, 40), (30, 30, 34)
STEEL = (200, 206, 214)
LEGO = (40, 110, 220)
SCREW = (150, 154, 164)

DECK_Z = 42                 # η πάνω επιφάνεια της βάσης (σασί)
WALL_TOP = DECK_Z           # τα πλαϊνά τοιχώματα φτάνουν ως το ύψος της βάσης (δεν ψηλώνουν πάνω της)
BOARD_Z = 82                # η κάτω επιφάνεια του ελεγκτή (πάνω στα διαχωριστικά των 40 mm)
BOARD_TOP = BOARD_Z + 2
SHORT_TOP = BOARD_TOP + 15  # η κορυφή των μικρών διαχωριστικών
STANDOFFS = ((-40, 20), (40, 20), (-40, 80), (40, 80))
CENTER = (0, 56, 44)        # το «κέντρο» του ρομπότ, εκεί κοιτάει η κάμερα


# ---------------------------------------------------------------- μικρά βοηθητικά
def ring8(faces, axis, t, a, b, rc=4.2, rr=1.6, rad=8.0):
    """Η χαρακτηριστική τρύπα του σασί: μια μεγάλη στη μέση και οκτώ μικρές γύρω της."""
    decal_on(faces, circle_pts(axis, t, a, b, rc, 14), HOLE)
    for k in range(8):
        ang = 2 * math.pi * k / 8 + math.pi / 8
        decal_on(faces, circle_pts(axis, t, a + rad * math.cos(ang), b + rad * math.sin(ang), rr, 8), HOLE)


def slot_hole(faces, axis, t, a, b, w, h):
    pts = [at(axis, t, u, v) for u, v in rounded_rect(a - w / 2, a + w / 2, b - h / 2, b + h / 2, h / 2 - 0.01, 4)]
    decal_on(faces, pts, HOLE)


def checker(face, axis, t, u0, u1, v0, v1, cols):
    """Καρό αυτοκόλλητο 2x2 (όπως στις υποδοχές RJ11 των αισθητήρων)."""
    um, vm, k = (u0 + u1) / 2, (v0 + v1) / 2, 0.8
    for (a0, a1), (b0, b1), col in (((u0 + k, um), (vm, v1 - k), cols[0]), ((um, u1 - k), (vm, v1 - k), cols[1]),
                                    ((u0 + k, um), (v0 + k, vm), cols[1]), ((um, u1 - k), (v0 + k, vm), cols[0])):
        face.decals.append(([at(axis, t, a0, b0), at(axis, t, a1, b0), at(axis, t, a1, b1), at(axis, t, a0, b1)], col))


def text(face, c, s, col, size=1.0, flip=False):
    u = (size, 0, 0) if not flip else (-size, 0, 0)
    v = (0, size, 0) if not flip else (0, -size, 0)
    face.decals.append(("text", c, u, v, s, col))


# ---------------------------------------------------------------- σασί
def chassis():
    m = Mesh()
    deck = m.box(-46, 46, 0, 112, DECK_Z - 2, DECK_Z, CHASSIS, split=3, plate=True)
    top, bottom = deck["top_all"], deck["bottom_all"]
    for faces, z in ((top, DECK_Z), (bottom, DECK_Z - 2)):
        for sx in (-1, 1):
            ring8(faces, "z", z, sx * 24, 98)
            slot_hole(faces, "z", z, sx * 22, 76, 18, 7)
        decal_on(faces, [(-5, 90, z), (5, 90, z), (5, 102, z), (-5, 102, z)], HOLE)
        for x, y in STANDOFFS:
            # οι τρύπες των διαχωριστικών: με ανοιχτό γκρι χείλος, για να φαίνονται πάνω στη μαύρη βάση
            # (φαίνεται και γύρω από το διαχωριστικό, σαν ροδέλα)
            decal_on(faces, circle_pts("z", z, x, y, 4.6, 16), (150, 154, 166))
            decal_on(faces, circle_pts("z", z, x, y, 2.5, 12), (6, 6, 8))
        for y in (40, 58):
            decal_on(faces, circle_pts("z", z, 0, y, 1.7, 8), HOLE)
    # τα δύο μακριά πλαϊνά τοιχώματα με τις στρογγυλές άκρες: κρέμονται προς τα κάτω από τις άκρες
    # της βάσης (η βάση ενώνεται στο πάνω χείλος τους, όπως στις φωτογραφίες του οδηγού)
    wall = rounded_rect(-24, 136, 14, WALL_TOP, 13, 5)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 46, sx * 48))
        w = m.prism("x", wall, x0, x1, CHASSIS, plate=True)
        for f, xx in ((w["cap_hi"], x1), (w["cap_lo"], x0)):
            for yy, zz in ((-11, 28), (123, 28), (30, 30)):
                ring8([f], "x", xx, yy, zz, rc=4.6 if yy == 30 else 3.6, rr=1.5, rad=8)
            slot_hole([f], "x", xx, 76, 28, 22, 6)
    # πίσω χείλος προς τα κάτω, μπροστινό χείλος προς τα πάνω (εκεί βιδώνει ο αισθητήρας υπερήχων)
    lip = m.box(-30, 30, 0, 2, 24, DECK_Z - 2, CHASSIS, plate=True)
    slot_hole([lip["back"]], "y", 0, 0, 32, 30, 6)
    front = m.box(-28, 28, 110, 112, DECK_Z, 62, CHASSIS, plate=True)
    for f, yy in ((front["front"], 112), (front["back"], 110)):
        ring8([f], "y", yy, 0, 52, rc=3.4, rr=1.4, rad=7)
    return m


# ---------------------------------------------------------------- βίδες, παξιμάδια, διαχωριστικά
def standoff(x, y, z0, z1, r=2.9, phase=0.0):
    m = Mesh()
    s = m.cyl("z", x, y, z0, z1, r, BRASS, n=6, phase=math.pi / 6 + phase)
    s["cap1"].decals.append((circle_pts("z", z1, x, y, 1.3, 8), (120, 90, 30)))
    return m


def screw(spec, k=1.0):
    """Μια βίδα ή ένα παξιμάδι. k: πόσο έχει μπει (0 = λίγο έξω, 1 = βιδωμένη). Γυρίζει όσο μπαίνει."""
    kind, axis, a, b, seat, out = spec
    off = (1 - k) * 9 * out
    turn = (1 - k) * 4 * math.pi
    t0, t1 = seat + off, seat + off + out * (2.5 if kind != "nut" else 2.2)
    m = Mesh()
    if kind == "nut":
        s = m.cyl(axis, a, b, t0, t1, 3.0, (176, 180, 188), n=6, phase=turn)
        s["cap1"].decals.append((circle_pts(axis, t1, a, b, 1.4, 8), (90, 94, 102)))
    elif kind == "round":
        s = m.cyl(axis, a, b, t0, t1, 2.8, (170, 174, 184), n=12, r1=2.2)
        for du, dv in ((1.6, 0.35), (0.35, 1.6)):
            ca, sa = math.cos(turn), math.sin(turn)
            pts = [at(axis, t1, a + (u * du) * ca - (v * dv) * sa, b + (u * du) * sa + (v * dv) * ca)
                   for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            s["cap1"].decals.append((pts, (60, 62, 70)))
    else:
        s = m.cyl(axis, a, b, t0, t1, 2.7, SCREW, n=10)
        s["cap1"].decals.append((circle_pts(axis, t1, a, b, 1.25, 6, turn), (40, 42, 48)))
    return m


# ---------------------------------------------------------------- κινητήρες και ρόδες
def motor(side):
    """side -1 = αριστερός (κοντό καλώδιο), +1 = δεξιός (μακρύ καλώδιο). Χωρίς το καλώδιο."""
    m = Mesh()
    x0, x1 = sorted((side * 22, side * 45.5))
    m.box(x0, x1, 12, 50, 20, 39.5, YELLOW_M, plate=True)
    m.box(x0 + 3, x1 - 3, 50, 53, 23, 37, (232, 182, 30))
    can_x = side * 33.5
    m.cyl("y", can_x, 30, 53, 74, 9.5, SILVER, n=14)
    m.cyl("y", can_x, 30, 74, 77, 6.5, (60, 62, 70), n=12)
    # ο λευκός άξονας περνά από το τοίχωμα (εκεί κουμπώνει η ρόδα) και βγαίνει λίγο και από μέσα
    sx0, sx1 = sorted((side * 45.5, side * 58))
    m.cyl("x", 30, 30, sx0, sx1, 2.7, WHITE_PL, n=8)
    ix0, ix1 = sorted((side * 22, side * 18))
    m.cyl("x", 30, 30, ix0, ix1, 2.7, WHITE_PL, n=8)
    return m


def wheel(side, spin=0.0):
    m = Mesh()
    lo, hi = sorted((side * 50, side * 72))
    t = m.cyl("x", 30, 30, lo, hi, 30, TIRE, n=30, groove=GROOVE, phase=spin)
    for key, xx in (("cap0", lo), ("cap1", hi)):
        f = t[key]
        f.decals.append((circle_pts("x", xx, 30, 30, 22, 24), WHITE_PL))
        f.decals.append((circle_pts("x", xx, 30, 30, 20, 24), (230, 232, 230)))
        for k in range(5):
            a = spin + 2 * math.pi * k / 5
            f.decals.append((circle_pts("x", xx, 30 + 12.5 * math.cos(a), 30 + 12.5 * math.sin(a), 4.2, 10),
                             (196, 198, 198)))
        f.decals.append((circle_pts("x", xx, 30, 30, 5, 10), (252, 252, 252)))
    return m


# ---------------------------------------------------------------- αισθητήρες
ULTRA_SOCKET = (0, 107.5, 84)       # το άνοιγμα της υποδοχής RJ11 του αισθητήρα υπερήχων (από πάνω)
LINE_SOCKET = (0, 127, 50)          # και του αισθητήρα γραμμής


def ultrasonic():
    m = Mesh()
    outline = [(-30, 40), (30, 40), (30, 72), (18, 88), (-18, 88), (-30, 72)]
    m.prism("y", outline, 113, 115, (214, 218, 224), plate=True)
    for ex in (-14, 14):
        c = m.cyl("y", ex, 58, 115, 128, 9.2, SILVER, n=16)
        c["cap1"].decals.append((circle_pts("y", 128, ex, 58, 7.6, 16), (72, 76, 88)))
        c["cap1"].decals.append((circle_pts("y", 128, ex, 58, 3.0, 10), (40, 42, 50)))
    s = m.box(-6, 6, 102, 113, 72, 84, SOCKET)
    checker(s["back"], "y", 102, -6, 6, 72, 84, (B, Y))
    s["top"].decals.append(([(-4, 104, 84), (4, 104, 84), (4, 111, 84), (-4, 111, 84)], (14, 14, 18)))
    return m


def line_sensor():
    m = Mesh()
    outline = [(-22, 86), (22, 86), (26, 120), (18, 136), (-18, 136), (-26, 120)]
    m.prism("z", outline, 37.5, 40, PCB, plate=True)
    for x in (-13, 0, 13):
        b = m.box(x - 3, x + 3, 126, 132, 34.5, 37.5, (30, 30, 36))
        b["bottom"].decals.append(([(x - 2, 127, 34.5), (x - 0.3, 127, 34.5), (x - 0.3, 131, 34.5),
                                    (x - 2, 131, 34.5)], (90, 140, 230)))
    s = m.box(-5, 5, 122, 132, 40, 50, SOCKET)
    checker(s["top"], "z", 50, -5, 5, 122, 132, (Y, B))
    return m


def caster():
    m = Mesh()
    m.prism("z", rounded_rect(-18, 18, 97, 111, 6, 4), 33.5, 37.5, WHITE_PL, plate=True)
    m.cyl("z", 0, 104, 12, 33.5, 9.5, WHITE_PL, n=16)
    m.sphere((0, 104, 8), 8, STEEL, n=12, m=7)
    return m


# ---------------------------------------------------------------- βάση για τουβλάκια, μπαταρία
def lego():
    m = Mesh()
    m.box(-40, 40, 84, 108, DECK_Z, DECK_Z + 3.2, LEGO, split=2, plate=True)
    for i in range(10):
        for j in range(3):
            m.cyl("z", -36 + i * 8, 88 + j * 8, DECK_Z + 3.2, DECK_Z + 5, 2.4, LEGO, n=10)
    return m


def tape():
    """Η ταινία διπλής όψης κάτω από τη θήκη μπαταρίας (φαίνεται μόνο όσο κολλάει η θήκη)."""
    m = Mesh()
    m.box(-22, 22, 16, 72, DECK_Z, DECK_Z + 0.6, (236, 238, 240), split=2)
    return m


def battery():
    m = Mesh()
    b = m.box(-29, 29, 6, 82, DECK_Z, DECK_Z + 15, (34, 35, 40), top=(50, 52, 58), split=2, plate=True)
    tops = b["top_all"]
    z = DECK_Z + 15
    for k in range(6):
        y0 = 9 + k * 12.2
        decal_on(tops, [(-26, y0, z), (26, y0, z), (26, y0 + 10.6, z), (-26, y0 + 10.6, z)], (22, 22, 26))
        for sx in (-1, 1):
            cx = sx * 23
            decal_on(tops, [(cx - 1.6, y0 + 2, z), (cx + 1.6, y0 + 2, z), (cx + 1.6, y0 + 8.6, z),
                            (cx - 1.6, y0 + 8.6, z)], (176, 180, 190) if (k + (sx > 0)) % 2 else (130, 134, 142))
    return m


# ---------------------------------------------------------------- ελεγκτής
PORTS_FRONT = (("A7", "A6", "ab", Y, R), ("I2C", "", "one", G, G), ("A3 A2", "A1", "chk", Y, R),
               ("D2", "A0", "ab", Y, R))
PORTS_BACK = (("D12", "", "ab", B, Y), ("D11", "", "ab", B, Y), ("D9", "D10", "chk", Y, B),
              ("D8", "D3", "chk", Y, B))
PORT_X = (-31, -15, 1, 17)
PORT_ROWS = {"front": (74, 86), "back": (14, 26)}
SWITCH = (45, 44, BOARD_TOP + 4)        # ο διακόπτης ON/OFF στη δεξιά άκρη


def board(led=(70, 170, 230), switch_on=False):
    m = Mesh()
    zt = BOARD_TOP
    p = m.box(-54, 54, 12, 88, BOARD_Z, zt, PCB, split=3, plate=True)
    tops = p["top_all"]
    for x, y in STANDOFFS:
        decal_on(tops, circle_pts("z", zt, x, y, 3.6, 12), (214, 180, 90))
        decal_on(tops, circle_pts("z", zt, x, y, 1.7, 8), (30, 30, 30))
    for row, ports in (("front", PORTS_FRONT), ("back", PORTS_BACK)):
        y0, y1 = PORT_ROWS[row]
        for i, (t1, t2, kind, c1, c2) in enumerate(ports):
            x = PORT_X[i]
            s = m.box(x - 6, x + 6, y0, y1, zt, zt + 12, SOCKET)
            top, z, ym = s["top"], zt + 12, (y0 + y1) / 2
            if kind == "chk":
                checker(top, "z", z, x - 6, x + 6, y0, y1, (c1, c2))
            elif kind == "one":
                top.decals.append(([(x - 5.2, y0 + 0.8, z), (x + 5.2, y0 + 0.8, z), (x + 5.2, y1 - 0.8, z),
                                    (x - 5.2, y1 - 0.8, z)], c1))
            else:
                top.decals.append(([(x - 5.2, ym, z), (x + 5.2, ym, z), (x + 5.2, y1 - 0.8, z), (x - 5.2, y1 - 0.8, z)], c1))
                top.decals.append(([(x - 5.2, y0 + 0.8, z), (x + 5.2, y0 + 0.8, z), (x + 5.2, ym, z), (x - 5.2, ym, z)], c2))
            text(top, (x, ym + 2.8, z), t1, (30, 30, 40) if c1 in (Y, B) else (255, 255, 255))
            if t2:
                text(top, (x, ym - 2.8, z), t2, (255, 255, 255) if c2 == R else (30, 30, 40))
            # το άνοιγμα: προς τα μπροστά για την μπροστινή σειρά, προς τα πίσω για την πίσω
            yy, f = (y1, s["front"]) if row == "front" else (y0, s["back"])
            f.decals.append(([(x - 4, yy, zt + 2), (x + 4, yy, zt + 2), (x + 4, yy, zt + 9), (x - 4, yy, zt + 9)],
                             (12, 12, 14)))
    m.box(24, 36, 10, 24, zt, zt + 10, (200, 204, 212))                       # USB
    for name, y in (("MA", 53), ("MB", 39)):
        c = m.box(-53, -45, y - 3.5, y + 3.5, zt, zt + 6, WHITE_PL)
        c["left"].decals.append(([(-53, y - 2, zt + 1.5), (-53, y + 2, zt + 1.5), (-53, y + 2, zt + 4.5),
                                  (-53, y - 2, zt + 4.5)], (60, 60, 64)))
        text(decal_target(tops, (-38, y, zt)), (-38, y, zt), name, (40, 40, 50))
    c = m.box(45, 53, 59.5, 66.5, zt, zt + 6, WHITE_PL)                        # DC-IN
    c["right"].decals.append(([(53, 61.5, zt + 1.5), (53, 64.5, zt + 1.5), (53, 64.5, zt + 4.5), (53, 61.5, zt + 4.5)],
                              (60, 60, 64)))
    text(decal_target(tops, (36, 63, zt)), (36, 63, zt), "DC-IN", (40, 40, 50), 0.8)
    # διακόπτης ON/OFF: ο μοχλός πάει προς τα μπροστά όταν ανάβει
    sx, sy, _ = SWITCH
    m.box(sx - 5, sx + 5, sy - 6, sy + 6, zt, zt + 4, (70, 72, 80))
    ly = sy + (3 if switch_on else -3)
    m.box(sx - 1.5, sx + 1.5, ly - 2, ly + 2, zt + 4, zt + 7, (236, 236, 240))
    text(decal_target(tops, (sx - 12, sy + 6, zt)), (sx - 12, sy + 6, zt), "ON", (40, 40, 50), 0.7)
    text(decal_target(tops, (sx - 12, sy - 6, zt)), (sx - 12, sy - 6, zt), "OFF", (40, 40, 50), 0.7)
    m.box(-12, 0, 44, 56, zt, zt + 1.6, (40, 40, 46))                           # τσιπ
    m.cyl("z", -24, 36, zt, zt + 6, 5, (36, 36, 40), n=14)                    # βομβητής
    m.cyl("z", 22, 54, zt, zt + 3, 2.0, led, n=10)                            # LED
    text(decal_target(tops, (0, 33, zt)), (0, 33, zt), "polytech", (120, 124, 134))
    return m


def decal_target(faces, c):
    for f in faces:
        xs, ys = [p[0] for p in f.pts], [p[1] for p in f.pts]
        if min(xs) <= c[0] <= max(xs) and min(ys) <= c[1] <= max(ys):
            return f
    return faces[0]


def acrylic():
    m = Mesh()
    out = [(-50, 14), (50, 14), (50, 86), (18, 86), (18, 70), (-14, 70), (-14, 86), (-50, 86)]
    m.prism("z", out, SHORT_TOP, SHORT_TOP + 3, (210, 230, 250), alpha=72, plate=True)
    return m


# ---------------------------------------------------------------- υποδοχές του ελεγκτή (για τα βύσματα)
def _socket_entries():
    out = {}
    names_front = ("A7A6", "I2C", "A1A2A3", "A0D2")
    names_back = ("D12", "D11", "D9D10", "D8D3")
    for i, x in enumerate(PORT_X):
        out[names_front[i]] = ((x, 87, BOARD_TOP + 5.5), (0, 1, 0))
        out[names_back[i]] = ((x, 13, BOARD_TOP + 5.5), (0, -1, 0))
    out["MA"] = ((-54, 53, BOARD_TOP + 3), (-1, 0, 0))
    out["MB"] = ((-54, 39, BOARD_TOP + 3), (-1, 0, 0))
    out["DCIN"] = ((54, 63, BOARD_TOP + 3), (1, 0, 0))
    return out


SOCKETS = _socket_entries()       # όνομα -> (σημείο εισόδου, κατεύθυνση από όπου έρχεται το καλώδιο)
SOCKET_LABEL = {"A7A6": "A7 / A6", "I2C": "I2C", "A1A2A3": "A1 / A2 / A3", "A0D2": "A0 / D2", "D12": "D12",
                "D11": "D11", "D9D10": "D9 / D10", "D8D3": "D8 / D3", "MA": "MA", "MB": "MB", "DCIN": "DC-IN"}
RJ_SOCKETS = ("A7A6", "I2C", "A1A2A3", "A0D2", "D12", "D11", "D9D10", "D8D3")


# ---------------------------------------------------------------- καλώδια και βύσματα
# κάθε βύσμα: από πού ξεκινά το καλώδιο (σημείο, κατεύθυνση), πού ακουμπά όταν είναι ελεύθερο
PLUG_START = {
    "motor_l": ((-33.5, 77.5, 30), (0, 1, 0)),
    "motor_r": ((33.5, 77.5, 30), (0, 1, 0)),
    "power": ((29, 80, DECK_Z + 9), (1, 0, 0)),
    "rj_ultra": (ULTRA_SOCKET, (0, 0, 1)),
    "rj_line": (LINE_SOCKET, (0, 0, 1)),
}
PLUG_REST = {
    "motor_l": ((-43, 100, 44), (0, 0, 1)),
    "motor_r": ((43, 104, 44), (0, 0, 1)),
    "power": ((36, 92, DECK_Z + 9), (0, 0, 1)),
    "rj_ultra": ((24, 98, 102), (0, 0, 1)),
    "rj_line": ((-24, 136, 62), (0, 0, 1)),
}
PLUG_KIND = {"motor_l": "white", "motor_r": "white", "power": "white", "rj_ultra": "rj", "rj_line": "rj"}
# πόσο «φουσκώνει» το καλώδιο κοντά στις δύο άκρες (για ωραίες καμπύλες)
_BULGE = {"motor_l": (16, 20), "motor_r": (26, 34), "power": (12, 18), "rj_ultra": (36, 22), "rj_line": (30, 24)}


def plug_mesh(name, end, direction, color=None):
    """Το καλώδιο από την αρχή του ως το βύσμα στο σημείο end, που μπαίνει από την κατεύθυνση direction."""
    m = Mesh()
    (s, sd) = PLUG_START[name]
    b0, b1 = _BULGE[name]
    p1 = (s[0] + sd[0] * b0, s[1] + sd[1] * b0, s[2] + sd[2] * b0)
    p2 = (end[0] + direction[0] * b1, end[1] + direction[1] * b1, end[2] + direction[2] * b1)
    if name in ("motor_l", "motor_r"):
        # κάτω από τη βάση προς τα μπροστά, βγαίνει μπροστά (δίπλα στον αισθητήρα) και ανεβαίνει πάνω
        side = -1 if name == "motor_l" else 1
        mid = (side * 36, 121, 46)
        pts = bezier(s, (s[0], 112, s[2]), (mid[0], mid[1], 34), mid, 8)
        rise = 18 if direction[2] > 0.5 else 52
        pts += bezier(mid, (mid[0], mid[1], mid[2] + rise), p2, end, 14)[1:]
        for dx, col in ((-0.9, RED_W), (0.9, BLACK_W)):
            m.tube([(p[0] + dx, p[1], p[2]) for p in pts], col, 1.5)
    elif name == "power":
        pts = bezier(s, p1, p2, end, 14)
        m.tube(pts, RED_W, 1.5)
        m.tube([(p[0], p[1] - 1.6, p[2] - 0.4) for p in pts], BLACK_W, 1.5)
    else:
        pts = bezier(s, p1, p2, end, 18)
        m.tube(pts, color or CABLE, 3.2)
    _plug_head(m, name, end, direction)
    return m


def _plug_head(m, name, end, d):
    kind = PLUG_KIND[name]
    x, y, z = end
    if kind == "rj":
        col = (214, 228, 238)
        h = 3.6
    else:
        col = WHITE_PL
        h = 3.0
    # μικρό κουτάκι λίγο έξω από την υποδοχή, κατά την κατεύθυνση του καλωδίου
    cx, cy, cz = x + d[0] * h, y + d[1] * h, z + d[2] * h
    ex = h if abs(d[0]) > 0.5 else 3.4
    ey = h if abs(d[1]) > 0.5 else 3.4
    ez = h if abs(d[2]) > 0.5 else 2.6
    m.box(cx - ex, cx + ex, cy - ey, cy + ey, cz - ez, cz + ez, col)


def rj_coil():
    """Ένα καλώδιο RJ11 τυλιγμένο, όπως είναι στο κουτί (για την κάρτα)."""
    m = Mesh()
    pts = [(28 * math.cos(a), 18 * math.sin(a), 4 * math.sin(a * 0.5)) for a in
           (2 * math.pi * k / 40 * 1.6 for k in range(41))]
    m.tube(pts, CABLE, 3.4)
    for p in (pts[0], pts[-1]):
        m.box(p[0] - 3.5, p[0] + 3.5, p[1] - 3.5, p[1] + 3.5, p[2] - 3, p[2] + 3, (214, 228, 238))
    return m


# ---------------------------------------------------------------- όσα είναι στο κουτί αλλά δεν χρειάζονται
def bluetooth():
    m = Mesh()
    m.box(-9, 9, 0, 34, 0, 1.6, (40, 110, 200))
    m.box(-7, 7, 4, 30, 1.6, 4, (90, 160, 230))
    m.box(-7, 7, 31, 34, 1.6, 2.4, (230, 230, 230))
    for k in range(4):
        m.box(-6 + k * 4 - 0.6, -6 + k * 4 + 0.6, 34, 42, 0.5, 1.7, (210, 190, 120))
    return m


def white_led():
    m = Mesh()
    m.box(-12, 12, 0, 24, 0, 1.6, PCB)
    m.cyl("z", 0, 8, 1.6, 6, 3.2, (252, 252, 252), n=12)
    m.sphere((0, 8, 6), 3.2, (255, 255, 255), n=10, m=4)
    s = m.box(-6, 6, 14, 24, 1.6, 11, SOCKET)
    checker(s["top"], "z", 11, -6, 6, 14, 24, (B, Y))
    return m


def usb_cable():
    m = Mesh()
    pts = [(-30 + 60 * k / 30, 14 * math.sin(k / 30 * 2 * math.pi), 2) for k in range(31)]
    m.tube(pts, (70, 72, 80), 3.0)
    m.box(-44, -30, -4, 4, 0, 5, (200, 204, 212))
    m.box(-34, -28, -5, 5, -1, 6, (60, 62, 70))
    m.box(30, 40, -6, 6, -1, 8, (200, 204, 212))
    m.box(28, 34, -6, 6, -2, 9, (60, 62, 70))
    return m


def screwdriver():
    m = Mesh()
    m.cyl("x", 0, 6, -40, -8, 6, (226, 60, 50), n=12)
    m.cyl("x", 0, 6, -8, 0, 3.4, (40, 40, 44), n=10)
    m.cyl("x", 0, 6, 0, 36, 1.5, (190, 194, 202), n=8)
    return m


def allen_key():
    m = Mesh()
    m.cyl("x", 0, 2, -30, 0, 1.5, (40, 40, 46), n=6)
    m.cyl("y", 0, 2, 0, 12, 1.5, (40, 40, 46), n=6)
    return m
