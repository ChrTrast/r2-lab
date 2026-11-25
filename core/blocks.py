"""Τα μπλοκ του R2, ζωγραφισμένα όπως στην επέκταση «Polytech R2» του Mind+ (που μοιάζει με Scratch 3).

Ένα μπλοκ είναι πλειάδα από κομμάτια:
    ("text", "Κινήσου")     λέξη πάνω στο μπλοκ
    ("drop", "μπροστά")     επιλογή με βελάκι ▾ (σκούρο πλαίσιο)
    ("num", "2")            αριθμός σε λευκό οβάλ
    ("color", (r, g, b))    χρωματιστό οβάλ (το χρώμα του Neopixel)
    ("round", κομμάτια)     στρογγυλό μπλοκ-τιμή του R2, π.χ. «Διάβασε απόσταση (cm)»
    ("hex", κομμάτια)       εξάγωνη ερώτηση (ΝΑΙ/ΟΧΙ) των Τελεστών, π.χ. ‹… < 15›
    ("r2hex", κομμάτια)     εξάγωνη ερώτηση του R2, π.χ. ‹Κουμπί αφής στο pin D11 , είναι πατημένο;›
    ("xround", κομμάτια)    μωβ μπλοκ-τιμή ενός «φανταστικού» αισθητήρα (με αστεράκι), π.χ. θερμοκρασία
Τα κείμενα είναι ακριβώς όπως στα φύλλα εργασίας του R2 (ΦΕ 1α και 1β· το PDF δεν είναι στο αποθετήριο)
και στο Mind+ (κατηγορίες R2 και Έλεγχος).

Χρώματα (κατηγορίες): "r2" σκούρο πράσινο με το λογότυπο R2, "control" πορτοκαλί (Έλεγχος),
"op" ανοιχτό πράσινο (Τελεστές). Τα «C» μπλοκ (επανάλαβε, για πάντα, εάν … αλλιώς) ζωγραφίζει η
Style.draw_shape: ένα μπλοκ είναι «χέρια» και «στόματα» με τη σειρά, π.χ. [κεφάλι, στόμα, κάτω χέρι].

Εδώ είναι και ό,τι άλλο χρειάζεται ένα παιχνίδι με προγράμματα:
    green_flag      η πράσινη σημαία του Scratch
    RunButton       το κουμπί «Εκτέλεση εντολών» με τη σημαία
    StackView       ο «χώρος προγράμματος»: το R2 starts και από κάτω τα μπλοκ, με κύλιση
                    και φωτισμένο το μπλοκ που τρέχει
"""
import math

import pygame

from . import ui

GREEN = (13, 110, 41)            # το πράσινο των μπλοκ του R2 στο Mind+
EDGE = (7, 80, 28)
FIELD = (9, 94, 34)
FIELD_EDGE = (74, 146, 96)
DIVIDER = (92, 160, 112)
NUM_TEXT = (80, 84, 92)
RUN = (255, 190, 20)             # κίτρινο περίγραμμα: το μπλοκ που τρέχει
FRESH = (255, 255, 255)          # λευκό περίγραμμα: το μπλοκ που μόλις γράφτηκε
CANVAS = (249, 249, 249)         # ο χώρος προγράμματος του Mind+
FLAG = (76, 191, 86)             # η πράσινη σημαία του Scratch
FLAG_EDGE = (69, 153, 61)
CONTROL, CONTROL_EDGE = (255, 171, 25), (207, 139, 23)      # Έλεγχος (πορτοκαλί)
OPERATOR, OPERATOR_EDGE = (89, 192, 89), (56, 148, 56)       # Τελεστές (ανοιχτό πράσινο)
EXTRA, EXTRA_EDGE = (146, 92, 214), (110, 62, 172)           # «φανταστικοί» αισθητήρες (μόνο στο παιχνίδι)
EVENT, EVENT_EDGE = (255, 191, 0), (204, 153, 0)             # Συμβάντα (κίτρινο), π.χ. «μετάδωσε μήνυμα»
CATS = {"r2": (GREEN, EDGE), "control": (CONTROL, CONTROL_EDGE), "op": (OPERATOR, OPERATOR_EDGE),
        "extra": (EXTRA, EXTRA_EDGE), "event": (EVENT, EVENT_EDGE)}
# το χρώμα των ▾ σε κάθε κατηγορία (όπου δεν λέει, το σκούρο πράσινο του R2)
DROP = {"event": ((232, 166, 0), (204, 143, 0))}
SS = 2                           # τα μπλοκ ζωγραφίζονται σε διπλό μέγεθος και μικραίνουν (λεία άκρα)


def _star(surf, c, r, col):
    """Αστεράκι πέντε ακτίνων (τα «φανταστικά» μπλοκ)."""
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    ui.fill_poly(surf, col, pts)


# ------------------------------------------------------------- τα μπλοκ
def number(n):
    """Ο αριθμός όπως γράφεται στο οβάλ: 2, 1.5 (με τελεία, όπως στο Mind+)."""
    return str(int(n)) if float(n).is_integer() else str(float(n))


def hat():
    return (("text", "R2 starts"),)


def move(direction, seconds):
    """Κινήσου [μπροστά/πίσω] με ταχύτητα [μικρή] για (seconds) δευτερόλεπτα."""
    word = "μπροστά" if direction == "forward" else "πίσω"
    return (("text", "Κινήσου"), ("drop", word), ("text", "με ταχύτητα"), ("drop", "μικρή"),
            ("text", "για"), ("num", number(seconds)), ("text", "δευτερόλεπτα"))


def turn(direction, seconds):
    """Στρίψε [δεξιά/αριστερά] για (seconds) δευτερόλεπτα."""
    word = "δεξιά" if direction == "right" else "αριστερά"
    return (("text", "Στρίψε"), ("drop", word), ("text", "για"), ("num", number(seconds)),
            ("text", "δευτερόλεπτα"))


_logo_fonts = {}


def _logo_font(size):
    if size not in _logo_fonts:
        _logo_fonts[size] = pygame.font.SysFont(ui.FONT_NAMES, size, bold=True, italic=True)
    return _logo_fonts[size]


class Style:
    """Τα μεγέθη των μπλοκ. Με τις αρχικές τιμές μοιάζουν με το Mind+ στο 100%.
    height, font, field (ύψος πλαισίων) και cap (πόσο ψηλώνει το καπέλο) είναι για scale = 1."""

    def __init__(self, scale=1.0, height=40, font=15, field=26, cap=16):
        k = scale * SS
        self.scale = scale
        self.k = k
        self.h = round(height * k)
        self.cap = round(cap * k)
        self.r = round(5 * k)
        self.field_h = round(field * k)
        self.font = ui.font(round(font * k), bold=False)
        self.logo = _logo_font(round(font * 1.27 * k))
        self.pad = round(8 * k)
        self.gap = round(6 * k)
        self.notch_x = round(14 * k)
        self.notch_w = round(30 * k)
        self.notch_d = round(6 * k)
        # για τα «C» μπλοκ και τα μπλοκ με εξάγωνο μέσα
        self.wall = round(16 * k)          # ο αριστερός τοίχος του «C»
        self.vpad = round(4 * k)           # γύρω από οβάλ και εξάγωνα
        self.mouth_min = round(22 * k)     # άδειο στόμα
        self.arm_end = round(26 * k)       # το κάτω χέρι
        self.else_arm = round(30 * k)      # το χέρι του «αλλιώς»
        self._cache = {}

    @property
    def step(self):
        """Πόσο πιο κάτω κουμπώνει το επόμενο μπλοκ (σε pixel της οθόνης)."""
        return self.h / SS

    @property
    def cap_px(self):
        return self.cap / SS

    # ---------------------------------------------------------- μεγέθη
    def _part_w(self, kind, s):
        tw = self.font.size(s)[0]
        if kind == "text":
            return tw
        if kind == "drop":
            return tw + round(24 * self.k)
        return max(tw + round(18 * self.k), round(30 * self.k))

    def _width_ss(self, parts):
        w = self.pad + self.logo.size("R2")[0] + 2 * self.gap + 1
        w += sum(self._part_w(k, s) for k, s in parts) + self.gap * (len(parts) - 1)
        return w + self.pad + round(4 * self.k)

    def width(self, parts):
        """Το πλάτος του μπλοκ σε pixel της οθόνης."""
        return math.ceil(self._width_ss(parts) / SS)

    # ---------------------------------------------------------- σχήμα
    def _notch(self, x0, y, reverse=False):
        """Η εγκοπή πάνω (ή το δοντάκι κάτω) σαν του Scratch 3."""
        pts = []
        for i in range(15):
            t = i / 14
            f = t / 0.3 if t < 0.3 else ((1 - t) / 0.3 if t > 0.7 else 1.0)
            f = f * f * (3 - 2 * f)
            pts.append((x0 + self.notch_w * t, y + self.notch_d * f))
        return pts[::-1] if reverse else pts

    @staticmethod
    def _arc(cx, cy, r, a0, a1, steps=6):
        return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps), cy + r * math.sin(a0 + (a1 - a0) * i / steps))
                for i in range(steps + 1)]

    def _outline(self, w, is_hat):
        top = self.cap if is_hat else 0
        b = top + self.h
        r = self.r
        pts = []
        if is_hat:
            cw = 86 * self.k                         # το «καπέλο» του R2 starts (καμπύλη Bezier)
            for i in range(17):
                t = i / 16
                x = 3 * (1 - t) ** 2 * t * (25 / 96 * cw) + 3 * (1 - t) * t * t * (71 / 96 * cw) + t ** 3 * cw
                y = top - (3 * (1 - t) ** 2 * t + 3 * (1 - t) * t * t) * self.cap * 1.33
                pts.append((x, y))
        else:
            pts += self._arc(r, top + r, r, math.pi, 1.5 * math.pi)
            pts += self._notch(self.notch_x, top)
        pts += self._arc(w - r, top + r, r, 1.5 * math.pi, 2 * math.pi)
        pts += self._arc(w - r, b - r, r, 0, 0.5 * math.pi)
        pts += self._notch(self.notch_x, b, reverse=True)
        pts += self._arc(r, b - r, r, 0.5 * math.pi, math.pi)
        return pts

    # ---------------------------------------------------------- ζωγραφική
    def _render(self, parts, is_hat):
        w = self._width_ss(parts)
        h = (self.cap if is_hat else 0) + self.h + self.notch_d + 2
        img = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        pts = [(x + 1, y + 1) for x, y in self._outline(w, is_hat)]
        ui.fill_poly(img, GREEN, pts, EDGE)
        pygame.draw.aalines(img, EDGE, True, pts)
        cy = (self.cap if is_hat else 0) + 1 + self.h // 2
        x = self.pad + 1
        logo = self.logo.render("R2", True, (255, 255, 255))
        img.blit(logo, logo.get_rect(midleft=(x, cy)))
        x += logo.get_width() + self.gap
        pygame.draw.line(img, DIVIDER, (x, cy - self.h * 0.32), (x, cy + self.h * 0.32), max(1, round(self.k / 2)))
        x += self.gap + 1
        line = max(1, round(self.k * 0.6))
        for kind, s in parts:
            pw = self._part_w(kind, s)
            t = self.font.render(s, True, NUM_TEXT if kind == "num" else (255, 255, 255))
            box = pygame.Rect(x, cy - self.field_h // 2, pw, self.field_h)
            if kind == "text":
                img.blit(t, t.get_rect(midleft=(x, cy)))
            elif kind == "drop":
                pygame.draw.rect(img, FIELD, box, border_radius=round(4 * self.k))
                pygame.draw.rect(img, FIELD_EDGE, box, width=line, border_radius=round(4 * self.k))
                img.blit(t, t.get_rect(midleft=(x + round(8 * self.k), cy)))
                ax, a = box.right - round(11 * self.k), round(2.8 * self.k)
                ui.fill_poly(img, (255, 255, 255), [(ax - a, cy - a * 0.5), (ax + a, cy - a * 0.5), (ax, cy + a * 0.7)])
            else:
                pygame.draw.rect(img, (255, 255, 255), box, border_radius=self.field_h // 2)
                pygame.draw.rect(img, (214, 220, 216), box, width=line, border_radius=self.field_h // 2)
                img.blit(t, t.get_rect(center=box.center))
            x += pw + self.gap
        size = ((w + 2) // SS, (h + 2) // SS)
        sil = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        ui.fill_poly(sil, (255, 255, 255), pts)
        return pygame.transform.smoothscale(img, size), pygame.transform.smoothscale(sil, size)

    def image(self, parts, is_hat=False):
        key = (tuple(parts), is_hat)
        if key not in self._cache:
            self._cache[key] = self._render(parts, is_hat)
        return self._cache[key][0]

    def _glow(self, parts, is_hat, color):
        key = (tuple(parts), is_hat, color)
        if key not in self._cache:
            self.image(parts, is_hat)
            sil = self._cache[(tuple(parts), is_hat)][1].copy()
            sil.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._cache[key] = sil
        return self._cache[key]

    def draw(self, surf, parts, topleft, is_hat=False, glow=None, glow_alpha=255):
        """Ζωγραφίζει ένα μπλοκ. topleft = η πάνω αριστερή γωνία του σώματος (όχι του καπέλου).
        glow: χρώμα περιγράμματος (RUN για το μπλοκ που τρέχει, FRESH για το καινούργιο)."""
        x = round(topleft[0])
        y = round(topleft[1] - (self.cap_px if is_hat else 0))
        if glow and glow_alpha > 0:
            sil = self._glow(parts, is_hat, glow)
            sil.set_alpha(int(glow_alpha))
            for i in range(16):
                a = i * math.pi / 8
                surf.blit(sil, (x + 4 * math.cos(a), y + 4 * math.sin(a)))
        img = self.image(parts, is_hat)
        surf.blit(img, (x, y))
        return pygame.Rect(x, y, img.get_width(), img.get_height())

    # ================================================ όλα τα σχήματα (Έλεγχος, Τελεστές, «C»)
    def part_size(self, kind, val):
        """Πλάτος και ύψος ενός κομματιού (σε pixel x SS)."""
        if kind in ("text", "drop", "num"):
            return self._part_w(kind, val), self.field_h
        if kind == "color":
            return round(40 * self.k), self.field_h
        w, h = self.row_size(val)
        if kind == "round":
            return self.pad + self.logo.size("R2")[0] + 2 * self.gap + 1 + w + self.pad, h + 2 * self.vpad
        if kind == "hex":
            hh = h + 2 * self.vpad
            return w + hh, hh
        if kind == "r2hex":
            hh = h + 2 * self.vpad
            return self.logo.size("R2")[0] + 2 * self.gap + 1 + w + hh, hh
        if kind == "xround":
            return self.pad + self.star_w + self.gap + w + self.pad, h + 2 * self.vpad
        raise ValueError(kind)

    @property
    def star_w(self):
        """Πόσο πιάνει το αστεράκι ενός «φανταστικού» αισθητήρα (pixel x SS)."""
        return round(16 * self.k)

    def logo_offset(self, kind, ph):
        """Πόσο μετά την αρχή ενός r2hex / xround αρχίζουν τα κομμάτια του (pixel x SS)."""
        if kind == "r2hex":
            return ph / 2 + self.logo.size("R2")[0] + 2 * self.gap + 1
        return self.pad + self.star_w + self.gap

    def row_size(self, parts):
        sizes = [self.part_size(k, v) for k, v in parts]
        return sum(w for w, _ in sizes) + self.gap * (len(parts) - 1), max(h for _, h in sizes)

    def arm_h(self, parts):
        """Το ύψος (pixel οθόνης) του χεριού που γράφει αυτά τα κομμάτια: ψηλώνει αν έχει εξάγωνο."""
        return max(self.h, self.row_size(parts)[1] + 2 * self.vpad) / SS

    def _arm_w(self, parts, cat):
        w = self.pad + (self.logo.size("R2")[0] + 2 * self.gap + 1 if cat == "r2" else 0)
        return w + self.row_size(parts)[0] + self.pad + round(4 * self.k)

    def block_width(self, parts, cat="r2"):
        """Το πλάτος (pixel οθόνης) ενός μπλοκ με αυτά τα κομμάτια."""
        return math.ceil(self._arm_w(parts, cat) / SS)

    def _hat_top(self, top):
        """Η καμπύλη πάνω πλευρά ενός «καπέλου» (όπως το R2 starts), από (0, top) ως (cw, top)."""
        cw = 86 * self.k
        pts = []
        for i in range(17):
            t = i / 16
            x = 3 * (1 - t) ** 2 * t * (25 / 96 * cw) + 3 * (1 - t) * t * t * (71 / 96 * cw) + t ** 3 * cw
            y = top - (3 * (1 - t) ** 2 * t + 3 * (1 - t) * t * t) * self.cap * 1.33
            pts.append((x, y))
        return pts

    def _shape_outline(self, w, segs, bottom_tab=True, hat=False):
        r, wall, nx = self.r, self.wall, self.notch_x
        top = self.cap if hat else 0                        # το «καπέλο» πιάνει χώρο πάνω από το σώμα
        if hat:
            pts = self._hat_top(top)
        else:
            pts = self._arc(r, r, r, math.pi, 1.5 * math.pi) + self._notch(nx, 0)
        pts += self._arc(w - r, top + r, r, 1.5 * math.pi, 2 * math.pi)
        y = top
        last = len(segs) - 1
        for i, seg in enumerate(segs):
            end = y + seg
            if i % 2 == 0:                                   # χέρι
                pts += self._arc(w - r, end - r, r, 0, 0.5 * math.pi)
                if i == last:
                    if bottom_tab:
                        pts += self._notch(nx, end, reverse=True)
                    pts += self._arc(r, end - r, r, 0.5 * math.pi, math.pi)
                else:                                        # δοντάκι μέσα στο στόμα
                    pts += self._notch(wall + nx, end, reverse=True)
                    pts += self._arc(wall + r, end + r, r, 1.5 * math.pi, math.pi)
            else:                                            # στόμα: κάτω, και δεξιά στο επόμενο χέρι
                pts += self._arc(wall + r, end - r, r, math.pi, 0.5 * math.pi)
                pts += self._notch(wall + nx, end)
                pts += self._arc(w - r, end + r, r, 1.5 * math.pi, 2 * math.pi)
            y = end
        return pts

    def _draw_row(self, img, parts, x, cy, drop=(FIELD, FIELD_EDGE)):
        line = max(1, round(self.k * 0.6))
        white = (255, 255, 255)
        for kind, val in parts:
            pw, ph = self.part_size(kind, val)
            box = pygame.Rect(round(x), round(cy - ph / 2), pw, ph)
            if kind == "text":
                t = self.font.render(val, True, white)
                img.blit(t, t.get_rect(midleft=(x, cy)))
            elif kind == "drop":
                t = self.font.render(val, True, white)
                pygame.draw.rect(img, drop[0], box, border_radius=round(4 * self.k))
                pygame.draw.rect(img, drop[1], box, width=line, border_radius=round(4 * self.k))
                img.blit(t, t.get_rect(midleft=(x + round(8 * self.k), cy)))
                ax, a = box.right - round(11 * self.k), round(2.8 * self.k)
                ui.fill_poly(img, white, [(ax - a, cy - a * 0.5), (ax + a, cy - a * 0.5), (ax, cy + a * 0.7)])
            elif kind == "num":
                t = self.font.render(val, True, NUM_TEXT)
                pygame.draw.rect(img, white, box, border_radius=ph // 2)
                pygame.draw.rect(img, (214, 220, 216), box, width=line, border_radius=ph // 2)
                img.blit(t, t.get_rect(center=box.center))
            elif kind == "color":
                pygame.draw.rect(img, white, box, border_radius=ph // 2)
                pygame.draw.rect(img, val, box.inflate(-2 * line - 2, -2 * line - 2), border_radius=ph // 2)
            elif kind == "round":
                pygame.draw.rect(img, GREEN, box, border_radius=ph // 2)
                pygame.draw.rect(img, EDGE, box, width=line, border_radius=ph // 2)
                xx = x + self.pad
                logo = self.logo.render("R2", True, white)
                img.blit(logo, logo.get_rect(midleft=(xx, cy)))
                xx += logo.get_width() + self.gap
                pygame.draw.line(img, DIVIDER, (xx, cy - ph * 0.32), (xx, cy + ph * 0.32), max(1, round(self.k / 2)))
                self._draw_row(img, val, xx + self.gap + 1, cy)
            elif kind == "hex":
                pts = [(x, cy), (x + ph / 2, cy - ph / 2), (x + pw - ph / 2, cy - ph / 2), (x + pw, cy),
                       (x + pw - ph / 2, cy + ph / 2), (x + ph / 2, cy + ph / 2)]
                ui.fill_poly(img, OPERATOR, pts, OPERATOR_EDGE)
                pygame.draw.aalines(img, OPERATOR_EDGE, True, pts)
                self._draw_row(img, val, x + ph / 2, cy)
            elif kind == "r2hex":
                pts = [(x, cy), (x + ph / 2, cy - ph / 2), (x + pw - ph / 2, cy - ph / 2), (x + pw, cy),
                       (x + pw - ph / 2, cy + ph / 2), (x + ph / 2, cy + ph / 2)]
                ui.fill_poly(img, GREEN, pts, EDGE)
                pygame.draw.aalines(img, EDGE, True, pts)
                xx = x + ph / 2
                logo = self.logo.render("R2", True, white)
                img.blit(logo, logo.get_rect(midleft=(xx, cy)))
                xx += logo.get_width() + self.gap
                pygame.draw.line(img, DIVIDER, (xx, cy - ph * 0.3), (xx, cy + ph * 0.3), max(1, round(self.k / 2)))
                self._draw_row(img, val, x + self.logo_offset(kind, ph), cy)
            elif kind == "xround":
                pygame.draw.rect(img, EXTRA, box, border_radius=ph // 2)
                pygame.draw.rect(img, EXTRA_EDGE, box, width=line, border_radius=ph // 2)
                _star(img, (x + self.pad + self.star_w / 2, cy), self.star_w * 0.5, white)
                self._draw_row(img, val, x + self.logo_offset(kind, ph), cy)
            x += pw + self.gap

    @staticmethod
    def _loop_arrow(img, x, y, s):
        """Το βελάκι ⤴ στο κάτω χέρι του «επανάλαβε» και του «για πάντα»."""
        w = max(2, round(s * 0.16))
        pygame.draw.lines(img, (255, 255, 255), False, [(x - s * 0.5, y + s * 0.3), (x + s * 0.1, y + s * 0.3),
                                                        (x + s * 0.25, y + s * 0.15), (x + s * 0.25, y - s * 0.2)], w)
        ui.fill_poly(img, (255, 255, 255), [(x + s * 0.25, y - s * 0.55), (x + s * 0.02, y - s * 0.18),
                                            (x + s * 0.48, y - s * 0.18)])

    def _render_shape(self, cat, segs, rows, bottom_tab, arrow, hat=False):
        fill, edge = CATS[cat]
        w = max(self._arm_w(p, cat) for p in rows.values())
        total = sum(segs)
        top = self.cap if hat else 0
        img = pygame.Surface((w + 2, top + total + self.notch_d + 2), pygame.SRCALPHA)
        pts = [(x + 1, y + 1) for x, y in self._shape_outline(w, segs, bottom_tab, hat)]
        ui.fill_poly(img, fill, pts, edge)
        pygame.draw.aalines(img, edge, True, pts)
        for i, parts in rows.items():
            cy = 1 + top + sum(segs[:i]) + segs[i] / 2
            x = self.pad + 1
            if cat == "r2":
                logo = self.logo.render("R2", True, (255, 255, 255))
                img.blit(logo, logo.get_rect(midleft=(x, cy)))
                x += logo.get_width() + self.gap
                pygame.draw.line(img, DIVIDER, (x, cy - self.h * 0.32), (x, cy + self.h * 0.32),
                                 max(1, round(self.k / 2)))
                x += self.gap + 1
            self._draw_row(img, parts, x, cy, DROP.get(cat, (FIELD, FIELD_EDGE)))
        if arrow:
            s = self.arm_end * 0.62
            self._loop_arrow(img, w - s * 0.9, 1 + top + total - segs[-1] / 2, s)
        size = ((w + 2) // SS, img.get_height() // SS)
        sil = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        ui.fill_poly(sil, (255, 255, 255), pts)
        return pygame.transform.smoothscale(img, size), pygame.transform.smoothscale(sil, size)

    def shape(self, cat, segs, rows, bottom_tab=True, arrow=False, hat=False):
        """Η εικόνα και το περίγραμμα (για λάμψη) ενός μπλοκ οποιουδήποτε σχήματος.

        cat: "r2" / "control" / "op". segs: ύψη (pixel οθόνης) χεριών και στομάτων με τη σειρά.
        rows: {αριθμός χεριού: κομμάτια}, π.χ. {0: κεφάλι, 2: «αλλιώς»}.
        bottom_tab=False για το «για πάντα» (δεν κουμπώνει τίποτα από κάτω). arrow: το βελάκι ⤴.
        hat=True: «καπέλο» (όπως το «όταν πατηθεί πλήκτρο»): η εικόνα ξεκινά cap_px πιο πάνω από το σώμα."""
        segs = tuple(max(1, round(s * SS)) for s in segs)
        key = ("shape", cat, segs, tuple((i, tuple(p)) for i, p in sorted(rows.items())), bottom_tab, arrow, hat)
        if key not in self._cache:
            if len(self._cache) > 600:
                self._cache.clear()
            self._cache[key] = self._render_shape(cat, segs, rows, bottom_tab, arrow, hat)
        return self._cache[key]

    def draw_shape(self, surf, topleft, cat, segs, rows, bottom_tab=True, arrow=False, glow=None, glow_alpha=255,
                   hat=False):
        """Ζωγραφίζει ένα μπλοκ οποιουδήποτε σχήματος στο topleft (η πάνω γωνία του σώματος, όχι του καπέλου).
        glow: χρώμα λάμψης γύρω του."""
        img, sil = self.shape(cat, segs, rows, bottom_tab, arrow, hat)
        x, y = round(topleft[0]), round(topleft[1] - (self.cap_px if hat else 0))
        if glow and glow_alpha > 0:
            g = sil.copy()
            g.fill((*glow, 255), special_flags=pygame.BLEND_RGBA_MULT)
            g.set_alpha(int(glow_alpha))
            for i in range(16):
                a = i * math.pi / 8
                surf.blit(g, (x + 4 * math.cos(a), y + 4 * math.sin(a)))
        surf.blit(img, (x, y))
        return pygame.Rect(x, y, img.get_width(), img.get_height())


# ------------------------------------------------------- πράσινη σημαία
_flags = {}


def green_flag(surf, center, size):
    """Η πράσινη σημαία του Scratch (ξεκινά το πρόγραμμα), μέσα σε τετράγωνο size×size."""
    size = max(8, int(size))
    if size not in _flags:
        k = 4
        s = size * k
        img = pygame.Surface((s, s), pygame.SRCALPHA)
        lw = max(2, round(s * 0.075))
        px, top, w, h, amp = s * 0.2, s * 0.14, s * 0.68, s * 0.46, s * 0.07
        n = 24
        upper = [(px + w * i / n, top - amp * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        lower = [(px + w * i / n, top + h - amp * math.sin(2 * math.pi * i / n)) for i in range(n, -1, -1)]
        pts = upper + lower
        pygame.draw.polygon(img, FLAG, pts)
        pygame.draw.lines(img, FLAG_EDGE, True, pts, lw)
        for x, y in pts:
            pygame.draw.circle(img, FLAG_EDGE, (x, y), lw / 2)
        pole = round(lw * 1.25)
        pygame.draw.line(img, FLAG_EDGE, (px, top), (px, s * 0.92), pole)
        pygame.draw.circle(img, FLAG_EDGE, (px, s * 0.92), pole / 2)
        pygame.draw.circle(img, FLAG_EDGE, (px, top), pole / 2)
        _flags[size] = pygame.transform.smoothscale(img, (size, size))
    img = _flags[size]
    surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))


class RunButton(ui.Button):
    """Το κουμπί «Εκτέλεση εντολών»: λευκό, για να ξεχωρίζει η πράσινη σημαία του Scratch."""

    def __init__(self, rect, action, label="Εκτέλεση εντολών", label_size=20):
        super().__init__(rect, label, None, (255, 255, 255), action, label_size=label_size)

    def draw(self, surf, time=0.0):
        r = self.rect
        if self.enabled and self.pulse:
            p = 0.5 + 0.5 * math.sin(time * 6)
            ui.glow(surf, r.inflate(12 + 8 * p, 12 + 8 * p), (255, 214, 60), 90 + 110 * p)
        depth = 5
        face = r.move(0, depth if self.pressed else 0)
        col = (236, 248, 238) if self.hover and not self.pressed else (255, 255, 255)
        pygame.draw.rect(surf, (150, 196, 158), r.move(0, depth), border_radius=16)
        pygame.draw.rect(surf, col, face, border_radius=16)
        pygame.draw.rect(surf, FLAG_EDGE, face, width=3, border_radius=16)
        green_flag(surf, (face.centerx, face.y + face.h * 0.40), min(face.w, face.h) * 0.56)
        ui.text(surf, self.label, (face.centerx, face.bottom - round(self.label_size * 0.9)), self.label_size, GREEN)


# ---------------------------------------------------- χώρος προγράμματος
class StackView:
    """Ένα πρόγραμμα σε χώρο σαν του Mind+: γκρι με τελίτσες, πάνω το R2 starts και από κάτω τα μπλοκ.

    Χωράνε rows γραμμές (μαζί με το R2 starts) και το μέγεθος των μπλοκ βγαίνει από το ύψος.
    Αν τα μπλοκ είναι περισσότερα, κυλάει μαλακά (show / scroll_by) και γράφει πόσα έμειναν πάνω/κάτω.
    rows=1: λωρίδα με ένα μόνο μπλοκ στη μέση της. Όταν γράφεται νέο, το παλιό ανεβαίνει και χάνεται.
    """
    PAD_X = 12
    PAD_TOP = 8

    def __init__(self, rect, rows, height=34, font=17.5, field=25, cap=14):
        self.rect = pygame.Rect(rect)
        self.rows = rows
        scale = math.floor((self.rect.h - 6 - self.PAD_TOP) / (cap + rows * height + 6) * 100) / 100
        self.style = Style(scale, height, font, field, cap)
        self.blocks = []
        self.target = 0               # η πρώτη γραμμή που φαίνεται (0 = το R2 starts)
        self.offset = 0.0             # το ίδιο, αλλά κινείται μαλακά προς το target

    def max_scroll(self):
        return max(0, len(self.blocks) + 1 - self.rows)

    def set_blocks(self, blocks):
        self.blocks = list(blocks)
        self.target = min(self.target, self.max_scroll())

    def show(self, index, below=0):
        """Κυλάει ώστε να φαίνεται το μπλοκ index και άλλα below από κάτω του (αν υπάρχουν)."""
        row = index + 1
        last = min(row + min(below, self.rows - 1), len(self.blocks))
        if last >= self.target + self.rows:
            self.target = last - self.rows + 1
        if row < self.target:
            self.target = row
        self.target = max(0, min(self.target, self.max_scroll()))

    def scroll_by(self, rows):
        self.target = max(0, min(self.target + rows, self.max_scroll()))

    def jump(self):
        self.offset = float(self.target)

    def update(self, dt):
        self.offset += (self.target - self.offset) * min(1.0, dt * 12)
        if abs(self.target - self.offset) < 0.01:
            self.offset = float(self.target)

    def hidden(self):
        """Πόσες γραμμές δεν φαίνονται (πάνω, κάτω)."""
        return self.target, max(0, len(self.blocks) + 1 - self.target - self.rows)

    def draw_background(self, surf):
        r = self.rect
        pygame.draw.rect(surf, CANVAS, r, border_radius=12)
        for y in range(r.y + 12, r.bottom - 4, 22):
            for x in range(r.x + 12, r.right - 4, 22):
                pygame.draw.circle(surf, (226, 228, 232), (x, y), 1)
        pygame.draw.rect(surf, (222, 226, 232), r, width=2, border_radius=12)

    def _base_y(self):
        """Πού είναι η πάνω άκρη της πρώτης γραμμής που φαίνεται."""
        st = self.style
        if self.rows == 1:
            return self.rect.centery - st.step / 2 + 2
        return self.rect.y + self.PAD_TOP + st.cap_px

    def _row_y(self, row):
        return self._base_y() + (row - self.offset) * self.style.step

    def block_rect(self, index):
        """Πού είναι (τώρα) το μπλοκ index πάνω στην οθόνη."""
        y = self._row_y(index + 1)
        return pygame.Rect(self.rect.x + self.PAD_X, round(y), self.style.width(self.blocks[index]),
                           round(self.style.step))

    def draw(self, surf, running=None, fresh=None, fresh_alpha=255):
        """running: το μπλοκ που τρέχει (κίτρινο). fresh: αυτό που μόλις γράφτηκε (λευκό, σβήνει)."""
        st = self.style
        old_clip = surf.get_clip()
        surf.set_clip(self.rect.inflate(-4, -4))
        x = self.rect.x + self.PAD_X
        base = self._base_y()
        for row in range(len(self.blocks) + 1):
            y = self._row_y(row)
            if y + st.step + 8 < self.rect.y or y - st.cap_px > self.rect.bottom:
                continue
            if self.rows == 1 and abs(y - base) >= st.step * 0.98:
                continue                      # λωρίδα: μόνο το μπλοκ της γραμμής (και όποιο γλιστράει)
            if row == 0:
                st.draw(surf, hat(), (x, y), is_hat=True)
                continue
            i = row - 1
            glow, alpha = None, 255
            if i == running:
                glow = RUN
            elif i == fresh:
                glow, alpha = FRESH, fresh_alpha
            st.draw(surf, self.blocks[i], (x, y), glow=glow, glow_alpha=alpha)
        above, below = self.hidden()
        if self.rows == 1:
            surf.set_clip(old_clip)
            shown = [(top, n) for top, n in ((True, above), (False, below)) if n > 0]
            for k, (top, n) in enumerate(shown):
                dy = 0 if len(shown) == 1 else (-14 if k == 0 else 14)
                self._pill(surf, top, n, midright=(self.rect.right - 14, self.rect.centery + dy))
            return
        for top, n in ((True, above), (False, below)):
            if n > 0:
                self._more(surf, top, n)
        surf.set_clip(old_clip)

    @staticmethod
    def _pill(surf, top, n, **pos):
        pill = pygame.Rect(0, 0, 160, 24)
        for k, v in pos.items():
            setattr(pill, k, v)
        pygame.draw.rect(surf, (255, 255, 255), pill, border_radius=12)
        pygame.draw.rect(surf, (200, 206, 216), pill, width=2, border_radius=12)
        ui.text(surf, f"{'▲' if top else '▼'} {n} ακόμα {'πάνω' if top else 'κάτω'}", pill.center, 14,
                (100, 110, 126))

    def _more(self, surf, top, n):
        r = self.rect
        fade = pygame.Surface((r.w - 4, 36), pygame.SRCALPHA)
        for yy in range(36):
            t = 1 - yy / 36 if top else yy / 36
            pygame.draw.line(fade, (*CANVAS, int(250 * t ** 0.7)), (0, yy), (r.w, yy))
        surf.blit(fade, (r.x + 2, r.y + 2 if top else r.bottom - 38))
        if top:
            self._pill(surf, top, n, midtop=(r.right - 100, r.y + 6))
        else:
            self._pill(surf, top, n, midbottom=(r.right - 100, r.bottom - 6))
