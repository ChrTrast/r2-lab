"""Οι κανόνες του Εργοστασίου, χωρίς γραφικά.

Μια βάρδια (Shift) είναι μια πίστα: τα αντικείμενα βγαίνουν από αριστερά πάνω στην ταινία και
προχωρούν δεξιά. Όποιο φτάσει στο τέλος της ταινίας πέφτει (χάνεται μια καρδιά). Όποιο μπει σε
λάθος κουτί χάνει επίσης μια καρδιά. Με 3 χαμένες καρδιές τελειώνει η βάρδια. Η πίστα τελειώνει
όταν μπουν «goal» αντικείμενα στο σωστό κουτί.
Κάθε σωστό δίνει ένα αστέρι. Με STREAK σωστά στη σειρά: «Σούπερ!», τα αστέρια μετράνε διπλά
ώσπου να γίνει λάθος, και αν λείπει καρδιά επιστρέφει μία.
Οι αποστάσεις είναι σε pixels της οθόνης (1280 x 720).
"""
import random

from .catalog import ITEMS

BELT_START = 30       # εκεί εμφανίζεται κάθε νέο αντικείμενο (μέσα στο άνοιγμα του τοίχου)
BELT_END = 1000       # όταν το κέντρο ενός αντικειμένου φτάσει εδώ, πέφτει
HEARTS = 3
STREAK = 5
ACCEL = 0.4           # όταν τελειώνει η πίστα, η ταινία πάει τόσο πιο γρήγορα (+40%)
EMPTY_GAP = 0.4       # αν η ταινία αδειάσει, το επόμενο έρχεται μετά από τόσο από το κανονικό κενό


class Thing:
    """Ένα αντικείμενο πάνω στην ταινία (ή στο χέρι του παιδιού, ή στον αέρα)."""
    __slots__ = ("id", "key", "kind", "x")

    def __init__(self, id_, key, x):
        self.id = id_
        self.key = key
        self.kind = ITEMS[key].kind
        self.x = x

    def __repr__(self):
        return f"Thing({self.key}, x={self.x:.0f})"


class Shift:
    def __init__(self, level, rng=None):
        self.level = level
        self.rng = rng or random.Random()
        self.boxes = tuple(level["boxes"])
        self.goal = level["goal"]
        self.base_speed = level["speed"]
        self.gap = level["gap"]
        self.things = []              # πάνω στην ταινία
        self.hearts = HEARTS
        self.got = 0                  # πόσα μπήκαν στο σωστό κουτί
        self.stars = 0
        self.streak = 0
        self.mistakes = []            # τα λάθος ή χαμένα, με τη σειρά (για το «Θυμήσου»)
        self.distance = 0.0           # πόσο έχει κυλήσει η ταινία (για τα γραφικά)
        self.since_spawn = self.gap   # το πρώτο έρχεται αμέσως
        self._bag = []
        self._decks = {}
        self._last = None
        self._next_id = 0

    # ------------------------------------------------------------ state
    @property
    def over(self):
        return self.hearts <= 0

    @property
    def done(self):
        return self.got >= self.goal

    @property
    def finished(self):
        return self.over or self.done

    @property
    def speed(self):
        return self.base_speed * (1 + ACCEL * min(1.0, self.got / self.goal))

    @property
    def double(self):
        """Τα αστέρια μετράνε διπλά (σερί)."""
        return self.streak >= STREAK

    def front(self):
        """Το αντικείμενο που είναι πιο κοντά στο τέλος (αυτό στέλνουν τα βελάκια)."""
        return max(self.things, key=lambda t: t.x, default=None)

    def find(self, thing_id):
        return next((t for t in self.things if t.id == thing_id), None)

    # ------------------------------------------------------------- belt
    def _pick_key(self):
        if not self._bag:
            self._bag = list(self.level["bag"])
            self.rng.shuffle(self._bag)
        kind = self._bag.pop()
        deck = self._decks.get(kind)
        if not deck:
            deck = list(self.level["pool"][kind])
            self.rng.shuffle(deck)
            if len(deck) > 1 and deck[-1] == self._last:
                deck[0], deck[-1] = deck[-1], deck[0]
            self._decks[kind] = deck
        self._last = deck.pop()
        return self._last

    def spawn(self):
        thing = Thing(self._next_id, self._pick_key(), BELT_START)
        self._next_id += 1
        self.things.append(thing)
        self.since_spawn = 0.0
        return thing

    def update(self, dt):
        """Κυλά την ταινία dt δευτερόλεπτα. Επιστρέφει γεγονότα: ("spawn", thing), ("lost", thing)."""
        if self.finished:
            return []
        events = []
        d = self.speed * dt
        self.distance += d
        self.since_spawn += d
        for t in self.things:
            t.x += d
        for t in [t for t in self.things if t.x >= BELT_END]:
            self.things.remove(t)
            self._miss(t)
            events.append(("lost", t))
            if self.over:
                return events
        if self.since_spawn >= self.gap or (not self.things and self.since_spawn >= self.gap * EMPTY_GAP):
            events.append(("spawn", self.spawn()))
        return events

    def take(self, thing):
        """Το παιδί σήκωσε το αντικείμενο από την ταινία."""
        if thing in self.things:
            self.things.remove(thing)

    def put_back(self, thing):
        """Το άφησε έξω από τα κουτιά: γυρίζει στην ταινία, εκεί που ήταν."""
        if thing not in self.things and not self.finished:
            thing.x = min(thing.x, BELT_END - 1)
            self.things.append(thing)

    # ------------------------------------------------------------- sort
    def sort(self, thing, box):
        """Το αντικείμενο μπαίνει στο κουτί box. Επιστρέφει dict με:
        right (σωστό;), stars (πόσα αστέρια πήρε), super (μόλις έγινε σερί), heart_back (πήρε πίσω καρδιά)."""
        self.take(thing)
        result = {"right": box == thing.kind, "stars": 0, "super": False, "heart_back": False}
        if self.finished:
            return result
        if result["right"]:
            self.got += 1
            self.streak += 1
            result["stars"] = 2 if self.double else 1
            self.stars += result["stars"]
            if self.streak % STREAK == 0:
                result["super"] = True
                if self.hearts < HEARTS:
                    self.hearts += 1
                    result["heart_back"] = True
        else:
            self._miss(thing)
        return result

    def _miss(self, thing):
        self.hearts -= 1
        self.streak = 0
        self.mistakes.append(thing.key)

    def lessons(self, n=3):
        """Τα πρώτα n διαφορετικά αντικείμενα που μπήκαν σε λάθος κουτί ή έπεσαν."""
        seen = []
        for key in self.mistakes:
            if key not in seen:
                seen.append(key)
        return seen[:n]
