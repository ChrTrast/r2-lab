"""Τα μπλοκ στην οθόνη: πώς φαίνεται κάθε εντολή (ακριβώς όπως στο Mind+), ο χώρος προγράμματος
με τα «C» μπλοκ και το σύρσιμο, οι Εντολές (από όπου σέρνει το παιδί) και τα μικρά μενού
(▾ επιλογές, αριθμοί, χρώματα).

Οι λέξεις είναι του Mind+ (κατηγορίες R2 και Έλεγχος, δες τα screenshots του δασκάλου) και των
φύλλων εργασίας του R2.
"""
import math
from collections import namedtuple

import pygame

from core import blocks, ui
from core.blocks import SS
from . import logic

LED_RGB = {"red": (230, 56, 56), "green": (60, 190, 90), "blue": (52, 116, 240), "yellow": (250, 206, 40)}
WORDS = {"forward": "μπροστά", "back": "πίσω", "right": "δεξιά", "left": "αριστερά",
         "red": "κόκκινο", "green": "πράσινο", "blue": "μπλε", "yellow": "κίτρινο",
         "on": "Ενεργοποίηση", "off": "Απενεργοποίηση",
         "up_arrow": "πάνω βέλος", "down_arrow": "κάτω βέλος", "right_arrow": "δεξί βέλος",
         "left_arrow": "αριστερό βέλος"}
BASE = dict(height=34, font=17.5, field=25, cap=14)     # τα μεγέθη της StackView του Λαβύρινθου
GHOST = (176, 184, 196)
ERROR = (232, 60, 60)
DARK = (44, 54, 76)

_styles = {}


def style(scale):
    """Τα μπλοκ σε αυτό το μέγεθος (κρατιούνται, για να μη ζωγραφίζονται ξανά)."""
    scale = round(scale, 2)
    if scale not in _styles:
        _styles[scale] = blocks.Style(scale, **BASE)
    return _styles[scale]


# ================================================================ όψη
def distance(cm):
    """‹ R2 Διάβασε απόσταση (cm) < cm › (Τελεστές, με το μπλοκ-τιμή του R2 μέσα)."""
    return (("round", (("text", "Διάβασε απόσταση (cm)"),)), ("text", "<"), ("num", str(cm)))


def look(node):
    """(κατηγορία, σχήμα, κομμάτια κεφαλιού, κομμάτια «αλλιώς»). Σχήμα: stack, c, forever, e."""
    op = node["op"]
    if op == "move":
        return "r2", "stack", blocks.move(node["dir"], node["n"]), None
    if op == "turn":
        return "r2", "stack", blocks.turn(node["dir"], node["n"]), None
    if op == "go":
        return "r2", "stack", (("text", "Κινήσου"), ("drop", WORDS[node["dir"]]), ("text", "με ταχύτητα"),
                               ("drop", "μικρή")), None
    if op == "stop":
        return "r2", "stack", (("text", "Σταμάτησε"),), None
    if op == "line":
        return "r2", "stack", (("text", "Ακολούθησε τη μαύρη γραμμή"), ("drop", WORDS[node["mode"]])), None
    if op == "key":
        return "event", "hat", (("text", "όταν πατηθεί πλήκτρο"), ("drop", WORDS[node["key"]])), None
    if op == "led":
        return "r2", "stack", (("text", "Neopixel Led στο pin"), ("drop", "D12"), ("text", ","), ("drop", "Όλα"),
                               ("text", "με χρώμα"), ("color", LED_RGB[node["color"]]),
                               ("text", "και φωτεινότητα"), ("num", "50")), None
    if op == "wait":
        return "control", "stack", (("text", "περίμενε"), ("num", str(node["n"])), ("text", "δευτερόλεπτα")), None
    if op == "until":
        return "control", "stack", (("text", "περίμενε ώσπου"), ("hex", distance(node["cm"]))), None
    if op == "repeat":
        return "control", "c", (("text", "επανάλαβε"), ("num", str(node["n"]))), None
    if op == "forever":
        return "control", "forever", (("text", "για πάντα"),), None
    if op == "if":
        return "control", "e", (("text", "εάν"), ("hex", distance(node["cm"])), ("text", "τότε")), (("text", "αλλιώς"),)
    raise ValueError(op)


class Lang:
    """Η «γλώσσα» των μπλοκ: πώς φαίνεται κάθε μπλοκ (look), τι έχει μέσα του (mouths), ποια πεδία του
    αλλάζει το παιδί (fields), πού κουμπώνει ένα κομμάτι (can_insert) και οι λέξεις / τα χρώματα των μενού.
    Το «Προγραμμάτισε» έχει τη δική του (PROGRAM, πιο κάτω). Άλλα παιχνίδια φτιάχνουν δική τους."""

    def __init__(self, look, mouths, fields, can_insert, words=None, colors=None):
        self.look, self.mouths, self.fields, self.can_insert = look, mouths, fields, can_insert
        self.words = words if words is not None else WORDS
        self.colors = colors if colors is not None else LED_RGB


PROGRAM = Lang(lambda node: look(node), lambda node: logic.mouths(node), logic.FIELDS,
               lambda *a: logic.can_insert(*a))
# το τηλεκοντρόλ: ο χώρος έχει μόνο προγράμματα «όταν πατηθεί πλήκτρο» (χωρίς «R2 starts»)
REMOTE = Lang(lambda node: look(node), lambda node: logic.mouths(node), logic.FIELDS,
              lambda *a: logic.can_insert(*a, scripts=True))


Item = namedtuple("Item", "path node x y w cat segs rows tab arrow hat", defaults=(False,))
"""Ένα μπλοκ στη διάταξη: θέση (pixel, πριν την κύλιση), πλάτος, σχήμα. hat: «καπέλο» (η εικόνα του ξεκινά
cap_px πιο πάνω από το y)."""
HAT_GAP = 8                   # pixel ανάμεσα σε δύο προγράμματα «όταν πατηθεί πλήκτρο»


def width_of(st, node, lang=None):
    cat, _, head, mid = (lang or PROGRAM).look(node)
    w = st.block_width(head, cat)
    return max(w, st.block_width(mid, cat)) if mid else w


def layout(st, nodes, x, y, where=(), lang=None):
    """Πού μπαίνει κάθε μπλοκ μιας λίστας. Επιστρέφει (μπλοκ, ύψος, θέσεις όπου κουμπώνει κάτι).

    Θέση κουμπώματος: (λίστα, αριθμός μέσα στη λίστα, x, y)."""
    lang = lang or PROGRAM
    items, spots = [], []
    wall = st.wall / SS
    y0 = y
    for i, node in enumerate(nodes):
        spots.append((where, i, x, y))
        p = where + (i,)
        cat, kind, head, mid = lang.look(node)
        h0 = st.arm_h(head)
        w = width_of(st, node, lang)
        if kind == "stack":
            items.append(Item(p, node, x, y, w, cat, (h0,), {0: head}, True, False))
            y += h0
            continue
        if kind == "hat":                    # «όταν πατηθεί πλήκτρο»: το καπέλο και το πρόγραμμά του από κάτω
            items.append(Item(p, node, x, y, w, cat, (h0,), {0: head}, True, False, True))
            sub, sh, sub_spots = layout(st, lang.mouths(node)[0], x, y + h0, p + (0,), lang)
            items += sub
            spots += sub_spots
            y += h0 + sh + HAT_GAP + st.cap_px      # χώρος και για το καπέλο του επόμενου
            continue
        segs, inner = [h0], []
        yy = y + h0
        for b, body in enumerate(lang.mouths(node)):
            sub, sh, sub_spots = layout(st, body, x + wall, yy, p + (b,), lang)
            sh = max(sh, st.mouth_min / SS)
            inner += sub
            spots += sub_spots
            segs.append(sh)
            yy += sh
            if kind == "e" and b == 0:
                segs.append(st.else_arm / SS)
                yy += st.else_arm / SS
        segs.append(st.arm_end / SS)
        yy += st.arm_end / SS
        rows = {0: head}
        if mid:
            rows[2] = mid
        items.append(Item(p, node, x, y, w, cat, tuple(segs), rows, kind != "forever", kind in ("c", "forever")))
        items += inner
        y = yy
    spots.append((where, len(nodes), x, y))
    return items, y - y0, spots


def arm_rects(item):
    """Τα «χέρια» ενός μπλοκ (εκεί που το πιάνεις), σε pixel πριν την κύλιση."""
    out, y = [], item.y
    for i, h in enumerate(item.segs):
        if i % 2 == 0:
            out.append(pygame.Rect(round(item.x), round(y), item.w, max(1, round(h))))
        y += h
    return out


def field_boxes(st, parts, cat):
    """Τα πεδία ενός χεριού (▾, οβάλ, χρώμα) με τη σειρά: (είδος, Rect ως προς την αρχή του μπλοκ
    και το κέντρο του χεριού), σε pixel οθόνης. Ίδιοι λογαριασμοί με τη Style._render_shape."""
    out = []
    logo_w = st.logo.size("R2")[0]

    def walk(parts, x):
        for kind, val in parts:
            pw, ph = st.part_size(kind, val)
            if kind in ("drop", "num", "color"):
                out.append((kind, pygame.Rect(round(x / SS), round(-ph / 2 / SS), round(pw / SS), round(ph / SS))))
            elif kind == "round":
                walk(val, x + st.pad + logo_w + 2 * st.gap + 1)
            elif kind == "hex":
                walk(val, x + ph / 2)
            elif kind in ("r2hex", "xround"):
                walk(val, x + st.logo_offset(kind, ph))
            x += pw + st.gap

    x = st.pad + 1 + (logo_w + 2 * st.gap + 1 if cat == "r2" else 0)
    walk(parts, x)
    return out


def draw_items(surf, st, items, dy=0.0, running=None, error=None, fresh=None, fresh_alpha=255, ghosts=()):
    """Ζωγραφίζει τα μπλοκ. running/error/fresh: θέσεις (path) για κίτρινη/κόκκινη/λευκή λάμψη.
    ghosts: id των μπλοκ που δείχνουν πού θα κουμπώσει αυτό που σέρνεται (γκρι)."""
    for it in items:
        pos = (it.x, it.y + dy)
        if id(it.node) in ghosts:
            _, sil = st.shape(it.cat, it.segs, it.rows, it.tab, it.arrow, it.hat)
            g = sil.copy()
            g.fill((*GHOST, 170), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(g, (round(pos[0]), round(pos[1] - (st.cap_px if it.hat else 0))))
            continue
        glow, alpha = None, 255
        if it.path == error:
            glow = ERROR
        elif it.path == running:
            glow = blocks.RUN
        elif it.path == fresh:
            glow, alpha = blocks.FRESH, fresh_alpha
        st.draw_shape(surf, pos, it.cat, it.segs, it.rows, it.tab, it.arrow, glow=glow, glow_alpha=alpha,
                      hat=it.hat)


# ======================================================= ο χώρος προγράμματος
class CodeView:
    """Ο χώρος προγράμματος: γκρι με τελίτσες, πάνω το «R2 starts» και από κάτω το πρόγραμμα.

    Αν το πρόγραμμα δεν χωράει στο πλάτος, τα μπλοκ μικραίνουν. Αν δεν χωράει στο ύψος, κυλάει."""
    PAD = 12
    SCALES = (0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5)
    TALL = 0.65               # για να χωρέσει στο ύψος, μικραίνουν ως εδώ (μετά το πρόγραμμα κυλάει)

    def __init__(self, rect, lang=None, starts=True):
        self.rect = pygame.Rect(rect)
        self.lang = lang or PROGRAM
        self.starts = starts          # False: χωρίς «R2 starts» (τηλεκοντρόλ: τα προγράμματα έχουν δικό τους καπέλο)
        self.st = style(self.SCALES[0])
        self.items, self.spots, self.height = [], [], 0.0
        self.scroll = 0.0
        self.target = 0.0

    @property
    def origin(self):
        """Η πάνω αριστερή γωνία του πρώτου μπλοκ (κάτω από το R2 starts), πριν την κύλιση."""
        return self.rect.x + self.PAD, self.rect.y + 8 + self.st.cap_px + (self.st.step if self.starts else 0)

    def set_program(self, prog, extra=None):
        """Υπολογίζει πού μπαίνει κάθε μπλοκ. extra: ένα κομμάτι που σέρνεται (να χωράει κι αυτό).

        Τα μπλοκ μικραίνουν ώσπου να χωράει το πλάτος (πάντα) και το ύψος (ως το TALL, μετά κυλάει)."""
        for scale in self.SCALES:
            self.st = style(scale)
            x0, y0 = self.origin
            self.items, h, self.spots = layout(self.st, prog, x0, y0, lang=self.lang)
            widest = max([it.x + it.w for it in self.items] + [0])
            if extra:
                widest = max(widest, x0 + 30 + max(width_of(self.st, n, self.lang) for n in extra))
            height = h + self.st.step + self.st.cap_px + 20
            fits_tall = height + 30 <= self.rect.h or scale <= self.TALL
            if widest <= self.rect.right - 8 and fits_tall:
                break
        self.height = h + self.st.step + self.st.cap_px + 20
        self.target = min(self.target, self.max_scroll())

    def max_scroll(self):
        return max(0.0, self.height + 30 - self.rect.h)

    def end_y(self):
        """Πού (στην οθόνη) τελειώνει το πρόγραμμα."""
        last = [y for where, _, _, y in self.spots if where == ()]
        return (last[-1] if last else self.origin[1]) - self.scroll

    def scroll_by(self, dy):
        self.target = max(0.0, min(self.max_scroll(), self.target + dy))

    def show(self, path):
        """Κυλάει ώστε να φαίνεται το μπλοκ path."""
        it = self.item(path)
        if not it:
            return
        top, bottom = it.y - self.rect.y - 30, it.y + it.segs[0] - self.rect.y + 40
        if top < self.target:
            self.target = max(0.0, top)
        elif bottom > self.target + self.rect.h:
            self.target = min(self.max_scroll(), bottom - self.rect.h)

    def update(self, dt):
        self.scroll += (self.target - self.scroll) * min(1.0, dt * 12)
        if abs(self.target - self.scroll) < 0.5:
            self.scroll = self.target

    def item(self, path):
        return next((it for it in self.items if it.path == path), None)

    def screen_rect(self, path):
        """Πού είναι (τώρα) το κεφάλι του μπλοκ στην οθόνη."""
        it = self.item(path)
        if not it:
            return None
        return arm_rects(it)[0].move(0, -round(self.scroll))

    # --------------------------------------------------------------- πατήματα
    def block_at(self, pos):
        """Το μπλοκ κάτω από το ποντίκι (το πιο εσωτερικό), μόνο στα «χέρια» του."""
        if not self.rect.collidepoint(pos):
            return None
        x, y = pos[0], pos[1] + self.scroll
        found = None
        for it in self.items:
            if any(r.collidepoint(x, y) for r in arm_rects(it)):
                found = it
        return found

    def field_at(self, pos):
        """(μπλοκ, πεδίο, Rect στην οθόνη) αν το ποντίκι είναι πάνω σε ▾ / οβάλ / χρώμα που αλλάζει."""
        it = self.block_at(pos)
        if not it:
            return None
        names = self.lang.fields[it.node["op"]]
        cy = it.y + it.segs[0] / 2 - self.scroll
        for (kind, r), name in zip(field_boxes(self.st, it.rows[0], it.cat), names):
            box = r.move(round(it.x), round(cy))
            if name and box.inflate(6, 6).collidepoint(pos):
                return it, name, box
        return None

    def nearest_spot(self, prog, chunk, pos):
        """Η θέση όπου θα κουμπώσει ένα κομμάτι αν αφεθεί με την πάνω αριστερή γωνία στο pos."""
        best, best_d = None, None
        for where, index, x, y in self.spots:
            if not self.lang.can_insert(prog, where, index, chunk):
                continue
            d = math.hypot((pos[0] - x) * 0.6, pos[1] - (y - self.scroll))
            if best_d is None or d < best_d:
                best, best_d = (where, index), d
        return best

    # ---------------------------------------------------------------- ζωγραφική
    def draw(self, surf, running=None, error=None, fresh=None, fresh_alpha=255, ghosts=(), badges=None):
        r = self.rect
        pygame.draw.rect(surf, blocks.CANVAS, r, border_radius=12)
        off = round(self.scroll) % 22
        for y in range(r.y + 12 - off, r.bottom - 4, 22):
            if y < r.y + 4:
                continue
            for x in range(r.x + 12, r.right - 4, 22):
                pygame.draw.circle(surf, (226, 228, 232), (x, y), 1)
        old = surf.get_clip()
        surf.set_clip(r.inflate(-4, -4))
        st = self.st
        x0, y0 = self.origin
        if self.starts:
            st.draw(surf, blocks.hat(), (x0, y0 - st.step - self.scroll), is_hat=True)
        draw_items(surf, st, self.items, -self.scroll, running, error, fresh, fresh_alpha, ghosts)
        for path, text in (badges or {}).items():
            box = self.screen_rect(path)
            if box:
                chip = pygame.Rect(box.right + 6, box.centery - 11, 84, 22)
                pygame.draw.rect(surf, (255, 255, 255), chip, border_radius=11)
                pygame.draw.rect(surf, blocks.CONTROL, chip, width=2, border_radius=11)
                ui.text(surf, text, chip.center, 14, (180, 110, 10))
        surf.set_clip(old)
        if self.max_scroll() > 0:                  # μπάρα κύλισης
            frac = r.h / (self.height + 30)
            bar_h = max(30, r.h * frac)
            y = r.y + (r.h - bar_h) * (self.scroll / self.max_scroll())
            pygame.draw.rect(surf, (200, 206, 216), (r.right - 10, y + 4, 6, bar_h - 8), border_radius=3)
        pygame.draw.rect(surf, (222, 226, 232), r, width=2, border_radius=12)


def draw_chunk(surf, st, chunk, topleft, shadow=True, lang=None):
    """Ένα κομμάτι προγράμματος που σέρνεται (με σκιά)."""
    items, _, _ = layout(st, chunk, topleft[0], topleft[1], lang=lang)
    if shadow:
        for it in items:
            _, sil = st.shape(it.cat, it.segs, it.rows, it.tab, it.arrow, it.hat)
            g = sil.copy()
            g.fill((0, 0, 0, 60), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(g, (round(it.x) + 5, round(it.y - (st.cap_px if it.hat else 0)) + 7))
    draw_items(surf, st, items)


# ================================================================ Εντολές
class Palette:
    """Οι εντολές της πίστας, σε σειρές (όσες χωράνε), για να τις σέρνει ή να τις πατάει το παιδί."""
    GAP = 12

    def __init__(self, templates, x, y, width, scale=0.72, lang=None):
        self.st = style(scale)
        self.lang = lang or PROGRAM
        self.templates = templates
        self.entries = []                   # (πρότυπο, items, Rect)
        rows = []                           # [πλάτος που πιάστηκε, y, ύψος]
        cx, cy, row_h = x, y, 0.0
        for node in templates:
            top = self.st.cap_px if self.lang.look(node)[1] == "hat" else 0     # χώρος για το καπέλο
            items, h, _ = layout(self.st, [node], 0, 0, lang=self.lang)
            if top:
                h = self.st.arm_h(self.lang.look(node)[2]) + top
            w = width_of(self.st, node, self.lang)
            if cx > x and cx + w > x + width:
                cx, cy, row_h = x, cy + row_h + self.GAP, 0.0
            placed, _, _ = layout(self.st, [node], cx, cy + top, lang=self.lang)
            self.entries.append((node, placed, pygame.Rect(cx, cy, w, math.ceil(h + self.st.notch_d / SS))))
            cx += w + 14
            row_h = max(row_h, h)
        self.height = cy + row_h - y if templates else 0
        del rows

    def at(self, pos):
        for node, items, rect in self.entries:
            if rect.collidepoint(pos):
                # μόνο πάνω στα «χέρια», όχι στο άδειο στόμα ενός «C»
                if any(r.collidepoint(pos) for it in items[:1] for r in arm_rects(it)):
                    return node, rect
        return None

    def draw(self, surf, dim=False):
        for node, items, rect in self.entries:
            draw_items(surf, self.st, items)
        if dim:
            for _, _, rect in self.entries:
                veil = pygame.Surface(rect.inflate(8, 8).size, pygame.SRCALPHA)
                veil.fill((255, 255, 255, 140))
                surf.blit(veil, rect.inflate(8, 8))


# ================================================================ μενού
class Popup:
    """Το μικρό μενού που ανοίγει όταν πατάς ▾, έναν αριθμό ή ένα χρώμα πάνω σε μπλοκ.

    kind: "menu" (λίστα σαν του Mind+, στο χρώμα του μπλοκ, με ✓), "pad" (αριθμοί), "colors"."""

    def __init__(self, kind, anchor, options, chosen, path, field, cat="r2", words=None, colors=None):
        self.kind, self.options, self.chosen, self.path, self.field = kind, list(options), chosen, path, field
        self.cat = cat
        self.words = words if words is not None else WORDS
        self.colors = colors if colors is not None else LED_RGB
        self.hover = None
        anchor = pygame.Rect(anchor)
        if kind == "menu":
            w = max(ui.font(20, bold=False).size(self.words.get(o, str(o)))[0] for o in self.options) + 76
            h = 14 + 44 * len(self.options)
        elif kind == "pad":
            cols = 3 if len(self.options) <= 9 else 4
            rows = math.ceil(len(self.options) / cols)
            w, h = cols * 54 + 16, rows * 54 + 16
        else:
            w, h = len(self.options) * 56 + 16, 64
        self.rect = pygame.Rect(anchor.x - 6, anchor.bottom + 6, w, h)
        if self.rect.bottom > 712:
            self.rect.bottom = anchor.y - 6
        self.rect.right = min(self.rect.right, 1270)
        self.rect.x = max(self.rect.x, 8)
        self.cells = []
        for i, o in enumerate(self.options):
            if kind == "menu":
                c = pygame.Rect(self.rect.x + 6, self.rect.y + 7 + 44 * i, self.rect.w - 12, 44)
            elif kind == "pad":
                cols = 3 if len(self.options) <= 9 else 4
                c = pygame.Rect(self.rect.x + 10 + (i % cols) * 54, self.rect.y + 10 + (i // cols) * 54, 50, 50)
            else:
                c = pygame.Rect(self.rect.x + 10 + i * 56, self.rect.y + 7, 50, 50)
            self.cells.append((o, c))

    def at(self, pos):
        return next((o for o, c in self.cells if c.collidepoint(pos)), None)

    def draw(self, surf):
        r = self.rect
        sh = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 60), sh.get_rect(), border_radius=12)
        surf.blit(sh, r.move(0, 5))
        fill, edge = blocks.CATS[self.cat]
        if self.kind == "menu":
            pygame.draw.rect(surf, fill, r, border_radius=10)
            pygame.draw.rect(surf, edge, r, width=2, border_radius=10)
            f = ui.font(20, bold=False)
            for o, c in self.cells:
                if o == self.hover:
                    pygame.draw.rect(surf, ui.shade(fill, 0.75), c, border_radius=8)
                if o == self.chosen:
                    pygame.draw.lines(surf, (255, 255, 255), False, [(c.x + 12, c.centery), (c.x + 19, c.centery + 7),
                                                                     (c.x + 32, c.centery - 8)], 4)
                img = f.render(self.words.get(o, str(o)), True, (255, 255, 255))
                surf.blit(img, img.get_rect(midleft=(c.x + 44, c.centery)))
            return
        pygame.draw.rect(surf, (255, 255, 255), r, border_radius=14)
        pygame.draw.rect(surf, (200, 206, 216), r, width=2, border_radius=14)
        for o, c in self.cells:
            if self.kind == "pad":
                on = o == self.chosen
                col = fill if on else ((226, 236, 230) if o == self.hover else (240, 244, 242))
                pygame.draw.rect(surf, col, c, border_radius=25)
                ui.text(surf, str(o), c.center, 22, (255, 255, 255) if on else DARK)
            else:
                if o == self.chosen or o == self.hover:
                    ui.circle(surf, (40, 50, 70) if o == self.chosen else (170, 180, 196), c.center, 23)
                ui.circle(surf, (255, 255, 255), c.center, 20)
                ui.circle(surf, self.colors[o], c.center, 17)
