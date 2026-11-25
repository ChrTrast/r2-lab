"""Ο χώρος προγράμματος των μαθητών (κεφάλαια Διόρθωσε και Γράψε), με τα μπλοκ του «Προγραμμάτισε».

- Γράψε: οι Εντολές πάνω (σύρσιμο κάτω από το «R2 starts» ή πάτημα για να μπουν στο τέλος), το πρόγραμμα
  από κάτω, Αναίρεση και κάδος. Μπλοκ που σέρνεται έξω σβήνεται.
- Διόρθωσε: τα μπλοκ μένουν στη θέση τους· το παιδί αλλάζει μόνο ▾ και αριθμούς.
Όταν τρέχει το R2 ο χώρος κλειδώνει και φωτίζεται κίτρινο το μπλοκ που τρέχει. Μετά από λάθος: κόκκινο μπλοκ.
"""
import math

import pygame

from core import ui
from games.program import code, logic as PL

DRAG_START = 6
UNDO_MAX = 60
FRESH_TIME = 0.8
TEMPLATES = {"move": lambda: PL.move("forward", 1), "turn": lambda: PL.turn("right", 1), "wait": lambda: PL.wait(1),
             "until": lambda: {"op": "until", "cmp": ">", "cm": 20}, "line": lambda: {"op": "line", "mode": "on"}}
WORDS = dict(code.WORDS, **{"<": "<", ">": ">"})
CM_CHOICES = (10, 20, 30, 40, 50)


def look(node):
    """Όπως στο «Προγραμμάτισε», με δύο διαφορές: στο «περίμενε ώσπου» αλλάζει και το σύμβολο (< ή >)
    και το «Ακολούθησε τη μαύρη γραμμή» ακολουθεί τη γραμμή ως το τέλος της."""
    op = node["op"]
    if op == "until":
        hexa = (("round", (("text", "Διάβασε απόσταση (cm)"),)), ("drop", node.get("cmp", "<")),
                ("num", str(node.get("cm", 20))))
        return "control", "stack", (("text", "περίμενε ώσπου"), ("hex", hexa)), None
    if op == "line":
        return "r2", "stack", (("text", "Ακολούθησε τη μαύρη γραμμή"), ("drop", code.WORDS["on"])), None
    return code.look(node)


def choices(node, field):
    if field == "cmp":
        return ("<", ">")
    if field == "cm":
        return CM_CHOICES
    return PL.choices(node, field)


FIELDS = dict(PL.FIELDS, until=("cmp", "cm"), line=(None,))
LANG = code.Lang(look, lambda node: PL.mouths(node), FIELDS, lambda *a: PL.can_insert(*a), words=WORDS)


class Editor:
    def __init__(self, palette_rect, code_rect, palette=(), fix=False, sounds=None):
        self.sounds = sounds
        self.fix = fix
        self.palette_rect = pygame.Rect(palette_rect) if palette_rect else None
        self.code_rect = pygame.Rect(code_rect)
        self.program = []
        self.history = []
        self.locked = False
        self.popup = None
        self.drag = None
        self.press = None
        self.preview = None
        self.fresh = None
        self.time = 0.0
        self.mouse = (0, 0)
        self.running = None           # το μπλοκ που φωτίζεται κίτρινο
        self.error = None             # το μπλοκ που γίνεται κόκκινο
        self.changed_at = 0.0
        self.palette = None
        if self.palette_rect and not fix:
            templates = [TEMPLATES[t]() for t in palette if t in TEMPLATES]
            r = self.palette_rect
            self.palette = code.Palette(templates, r.x + 18, r.y + 48, r.w - 36, 0.6, lang=LANG)
        c = self.code_rect
        self.view = code.CodeView((c.x, c.y, c.w, c.h), lang=LANG)
        B = ui.Button
        self.btn_undo = B((0, 0, 86, 56), "Αναίρεση", ui.icon_undo, (120, 130, 150), self.undo, label_size=14)
        self.btn_trash = B((0, 0, 86, 56), "Σβήσ' τα", ui.icon_trash, (120, 130, 150), self.clear, label_size=14)

    def _play(self, name, vol=0.6):
        if self.sounds:
            self.sounds.play(name, vol)

    # ------------------------------------------------------------ πρόγραμμα
    def set_program(self, prog, remember=False):
        if remember:
            self._remember()
        self.program = PL.clone(prog or [])
        self.view.set_program(self.program)
        self.error = None
        self.changed_at = self.time

    def _remember(self):
        self.history.append(PL.clone(self.program))
        del self.history[:-UNDO_MAX]

    def _changed(self):
        self.view.set_program(self.program)
        self.error = None
        self.changed_at = self.time

    def undo(self):
        if self.history and not self.locked:
            self.program = self.history.pop()
            self._changed()
            self._play("remove")

    def clear(self):
        if self.program and not self.locked and not self.fix:
            self._remember()
            self.program = []
            self._changed()
            self._play("remove", 0.7)

    def append(self, template):
        where, index = PL.append_spot(self.program)
        chunk = [PL.clone([template])[0]]
        if not PL.can_insert(self.program, where, index, chunk):
            self._play("deny")
            return
        self._remember()
        PL.insert(self.program, where, index, chunk)
        self._changed()
        path = where + (index,)
        self.fresh = (path, self.time)
        self.view.show(path)
        self._play("place", 0.7)

    def set_field(self, path, field, value):
        node = PL.get(self.program, path)
        if node.get(field) == value:
            return
        self._remember()
        node[field] = value
        self._changed()
        self.fresh = (path, self.time)
        self._play("select", 0.7)

    # ------------------------------------------------------------ ποντίκι
    def buttons(self):
        self.btn_undo.enabled = bool(self.history) and not self.locked
        self.btn_trash.enabled = bool(self.program) and not self.locked and not self.fix
        return [self.btn_undo] + ([] if self.fix else [self.btn_trash])

    def busy(self):
        return self.drag is not None or self.popup is not None

    def down(self, pos):
        """Πάτημα: True αν το χειρίστηκε ο χώρος προγράμματος."""
        self.mouse = pos
        if self.popup:
            choice = self.popup.at(pos)
            p, self.popup = self.popup, None
            if choice is not None:
                self.set_field(p.path, p.field, choice)
            return True
        if self.locked:
            return False
        if self.palette:
            hit = self.palette.at(pos)
            if hit:
                node, rect = hit
                self.press = {"pos": pos, "template": node, "rect": rect}
                return True
        field = self.view.field_at(pos)
        if field:
            item, name, rect = field
            options = choices(item.node, name)
            if name == "color":
                kind = "colors"
            elif all(isinstance(o, (int, float)) for o in options):
                kind = "pad"
            else:
                kind = "menu"
            self.popup = code.Popup(kind, rect, options, item.node.get(name), item.path, name, item.cat, words=WORDS)
            self._play("button")
            return True
        if self.fix:
            return False
        item = self.view.block_at(pos)
        if item:
            self.press = {"pos": pos, "path": item.path, "rect": self.view.screen_rect(item.path)}
            return True
        return False

    def motion(self, pos):
        self.mouse = pos
        if self.popup:
            self.popup.hover = self.popup.at(pos)
        if self.press and not self.drag:
            if math.hypot(pos[0] - self.press["pos"][0], pos[1] - self.press["pos"][1]) >= DRAG_START:
                self._start_drag()
        if self.drag:
            self._update_preview()

    def up(self, pos):
        self.mouse = pos
        if self.press:
            p, self.press = self.press, None
            if "template" in p:
                self.append(p["template"])
            return True
        if self.drag:
            self._drop()
            return True
        return False

    def wheel(self, dy):
        if self.view.rect.collidepoint(self.mouse):
            self.view.scroll_by(-dy * 40)

    def _start_drag(self):
        p = self.press
        grab = (p["pos"][0] - p["rect"].x, p["pos"][1] - p["rect"].y)
        if "template" in p:
            chunk, origin = PL.clone([p["template"]]), "palette"
        else:
            self._remember()
            chunk, origin = PL.take(self.program, p["path"]), "program"
            self._changed()
        self.drag = {"chunk": chunk, "grab": grab, "from": origin}
        self.press = None
        self._play("pick", 0.5)
        self._update_preview()

    def _drag_topleft(self):
        g = self.drag["grab"]
        return self.mouse[0] - g[0], self.mouse[1] - g[1]

    def _update_preview(self):
        chunk = self.drag["chunk"]
        if self.view.rect.collidepoint(self.mouse):
            self.view.set_program(self.program, extra=chunk)
            spot = self.view.nearest_spot(self.program, chunk, self._drag_topleft())
        else:
            spot = None
        if spot != self.preview:
            self.preview = spot
            if spot:
                trial = PL.clone(self.program)
                PL.insert(trial, spot[0], spot[1], chunk)
                self.view.set_program(trial)
            else:
                self.view.set_program(self.program)

    def _drop(self):
        d, self.drag = self.drag, None
        spot, self.preview = self.preview, None
        chunk = d["chunk"]
        if spot and PL.can_insert(self.program, spot[0], spot[1], chunk):
            if d["from"] == "palette":
                self._remember()
            PL.insert(self.program, spot[0], spot[1], chunk)
            self._changed()
            self.fresh = (spot[0] + (spot[1],), self.time)
            self._play("place", 0.7)
            return
        if d["from"] == "program":
            self._play("remove", 0.7)
        self._changed()

    def cancel(self):
        """Κλείνει μενού και σύρσιμο (π.χ. όταν ξεκινά η εκτέλεση)."""
        self.popup = None
        if self.drag:
            self._drop()
        self.press = None

    def hand(self, pos):
        if self.locked:
            return False
        if self.palette and self.palette.at(pos):
            return True
        if self.view.field_at(pos):
            return True
        return (not self.fix and bool(self.view.block_at(pos))) or self.drag is not None

    # ------------------------------------------------------------ χρόνος και ζωγραφική
    def update(self, dt):
        self.time += dt
        self.view.update(dt)

    def draw_palette(self, s):
        if self.palette:
            self.palette.draw(s, dim=self.locked)

    def draw_code(self, s):
        fresh, alpha = None, 255
        if self.fresh and self.time - self.fresh[1] < FRESH_TIME:
            fresh, alpha = self.fresh[0], int(255 * (1 - (self.time - self.fresh[1]) / FRESH_TIME))
        self.view.draw(s, running=self.running, error=self.error, fresh=fresh, fresh_alpha=alpha)

    def draw_top(self, s):
        """Ό,τι πάει πάνω από όλα: το κομμάτι που σέρνεται και το μενού."""
        if self.drag:
            code.draw_chunk(s, self.view.st, self.drag["chunk"], self._drag_topleft(), lang=LANG)
        if self.popup:
            self.popup.draw(s)
