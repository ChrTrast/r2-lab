"""Οι κανόνες της Συναρμολόγησης, χωρίς γραφικά: τι έχει μπει, ποιο βήμα είναι τώρα, αν ένα κομμάτι
ή ένα βύσμα μπορεί να μπει εκεί που το άφησε το παιδί και τι λέει το R2 όταν δεν μπορεί.

Τρόποι:
  HELP  «Με βοήθεια»: στο κουτί μόνο τα κομμάτια του βήματος, ένα διάφανο κομμάτι δείχνει τη θέση.
  GUIDE «Με τον οδηγό»: στο κουτί μόνο τα κομμάτια του βήματος, το παιδί διαβάζει και βρίσκει τη θέση.
  SOLO  «Μόνος μου»: όλα τα κομμάτια στο κουτί (και κάποια που δε χρειάζονται)· ποιο μπαίνει τώρα;
"""
from .steps import PARTS, PART_LIST, PLUGS, RJ_USED, REQUIRE_MSG, SLOTS, STEP_INDEX, STEPS, TASKS, WRONG

HELP, GUIDE, SOLO = "help", "guide", "solo"
MODES = (HELP, GUIDE, SOLO)
HINT_AFTER = 2          # στο «Μόνος μου», μετά από τόσα λάθη στο ίδιο βήμα το R2 λέει τι χρειάζεται


class Result:
    """Τι έγινε με ένα κομμάτι ή βύσμα που άφησε το παιδί.

    kind: "ok" (μπήκε), "miss" (δεν ήταν κοντά σε καμία θέση, γυρίζει στο κουτί χωρίς λάθος),
          "wrong" (λάθος θέση), "later" (σωστή θέση αλλά όχι ακόμα), "extra" (δε χρειάζεται).
    """

    def __init__(self, kind, msg=None, slot=None):
        self.kind, self.msg, self.slot = kind, msg, slot

    @property
    def ok(self):
        return self.kind == "ok"

    @property
    def mistake(self):
        return self.kind in ("wrong", "later", "extra")


class Build:
    def __init__(self, mode=HELP, start_task=1):
        self.mode = mode
        self.start_task = start_task
        self.placed = set()
        self.connected = set()
        self.switched = False
        self.mistakes = 0
        self.misses_here = 0
        for step in STEPS:
            if step.task < start_task:
                self.placed.update(step.slots)
                self.connected.update(step.plugs)
        self._seen_step = self.step_i

    # ------------------------------------------------------------ πού είμαστε
    def step_done(self, step):
        if step.switch:
            return self.switched
        return all(s in self.placed for s in step.slots) and all(p in self.connected for p in step.plugs)

    @property
    def step_i(self):
        for i, step in enumerate(STEPS):
            if not self.step_done(step):
                return i
        return len(STEPS)

    @property
    def step(self):
        i = self.step_i
        return STEPS[i] if i < len(STEPS) else None

    @property
    def finished(self):
        return self.step is None

    @property
    def task(self):
        step = self.step
        return step.task if step else 9

    def task_done(self, task):
        return all(self.step_done(s) for s in STEPS if s.task == task)

    @property
    def needs_hint(self):
        return self.mode == SOLO and self.misses_here >= HINT_AFTER

    def placed_count(self):
        return len(self.placed) + len(self.connected)

    # ------------------------------------------------------------ το κουτί
    def tray(self):
        """[(είδος, πόσα μένουν)] με τη σειρά που φαίνονται οι κάρτες."""
        if self.mode == SOLO:
            out = []
            for part in PART_LIST:
                used = sum(1 for s in self.placed if SLOTS[s].kind == part.kind)
                out.append((part.kind, part.count - used))
            return out
        step = self.step
        if step is None:
            return []
        kinds = []
        for sid in step.slots:
            k = SLOTS[sid].kind
            if k not in kinds:
                kinds.append(k)
        return [(k, sum(1 for sid in step.slots if SLOTS[sid].kind == k and sid not in self.placed)) for k in kinds]

    def left(self, kind):
        return dict(self.tray()).get(kind, 0)

    # ------------------------------------------------------------ θέσεις
    def free(self, slot_id):
        return slot_id not in self.placed

    def ready(self, slot_id):
        """Η θέση είναι ελεύθερη και το βήμα της έχει έρθει (και ό,τι χρειάζεται πριν έχει μπει)."""
        slot = SLOTS[slot_id]
        return (slot_id not in self.placed and STEP_INDEX[slot.step] <= self.step_i
                and all(r in self.placed for r in slot.requires))

    def wanted(self, kind):
        """Οι θέσεις όπου θα κολλήσει τώρα αυτό το είδος (για τον μαγνήτη και το «φάντασμα»)."""
        return [s.id for s in SLOTS.values() if s.kind == kind and self.ready(s.id)]

    def drop(self, kind, slot_id):
        """Το παιδί άφησε ένα κομμάτι κοντά στη θέση slot_id (ή None: μακριά από κάθε θέση)."""
        if slot_id is None:
            return Result("miss")
        part = PARTS[kind]
        slot = SLOTS[slot_id]
        if part.extra:
            return self._mistake(Result("extra", part.why))
        if kind == "rj11" and sum(1 for s in self.placed if SLOTS[s].kind == "rj11") >= RJ_USED:
            return self._mistake(Result("extra", ("Χρειαζόμαστε μόνο δύο καλώδια RJ11.",
                                                  "Τα άλλα δύο μένουν στο κουτί.")))
        if slot.kind != kind:
            msg = WRONG.get((kind, slot.kind)) or (f"Εδώ δε μπαίνει: {part.label}.",
                                                   f"Σε αυτή τη θέση μπαίνει: {PARTS[slot.kind].label}.")
            return self._mistake(Result("wrong", msg, slot))
        if slot_id in self.placed:
            return Result("miss")
        if STEP_INDEX[slot.step] > self.step_i:
            return self._mistake(Result("later", self._later_msg(), slot))
        if not all(r in self.placed for r in slot.requires):
            return self._mistake(Result("later", REQUIRE_MSG.get(kind, self._later_msg()), slot))
        self.placed.add(slot_id)
        self._advance()
        return Result("ok", slot=slot)

    # ------------------------------------------------------------ βύσματα
    def plug_visible(self, pid):
        """Το βύσμα υπάρχει πάνω στο ρομπότ (το κομμάτι του έχει μπει)."""
        return all(r in self.placed for r in PLUGS[pid].requires)

    def plug_active(self, pid):
        """Το παιδί μπορεί να το σύρει τώρα."""
        plug = PLUGS[pid]
        if pid in self.connected or not self.plug_visible(pid):
            return False
        if self.mode == SOLO:
            return True
        return STEP_INDEX[plug.step] <= self.step_i

    def drop_plug(self, pid, socket):
        if socket is None:
            return Result("miss")
        plug = PLUGS[pid]
        if STEP_INDEX[plug.step] > self.step_i:
            return self._mistake(Result("later", self._later_msg()))
        if socket != plug.target:
            return self._mistake(Result("wrong", plug.wrong))
        self.connected.add(pid)
        self._advance()
        return Result("ok")

    def press_switch(self):
        step = self.step
        if step is None or not step.switch:
            return Result("later", self._later_msg())
        self.switched = True
        self._advance()
        return Result("ok")

    # ------------------------------------------------------------ μηνύματα
    def _later_msg(self):
        step = self.step
        now = f"Τώρα: {step.title.lower()}." if step else ""
        if self.mode == SOLO and self.misses_here + 1 < HINT_AFTER:
            return ("Όχι ακόμα!", "Αυτό μπαίνει αργότερα. Ποιο κομμάτι μπαίνει πρώτο;")
        return ("Όχι ακόμα!", now)

    def hint(self):
        """Τι λέει το R2 όταν δεν έχει κάτι άλλο να πει."""
        step = self.step
        if step is None:
            return ("Το R2 είναι έτοιμο!", "Μπράβο!")
        if self.mode == HELP or step.switch:
            return step.hint
        if self.mode == GUIDE:
            return ("Διάβασε το βήμα του οδηγού.", "Βρες πού μπαίνει κάθε κομμάτι.")
        if self.needs_hint:
            return ("Βοήθεια: " + step.title.lower() + ".", TASKS.get(step.task, ""))
        return ("Ποιο κομμάτι μπαίνει τώρα;", "Θυμήσου τη σειρά του οδηγού συναρμολόγησης.")

    def _mistake(self, result):
        self.mistakes += 1
        self.misses_here += 1
        return result

    def _advance(self):
        if self.step_i != self._seen_step:
            self._seen_step = self.step_i
            self.misses_here = 0
