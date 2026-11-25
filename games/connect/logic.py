"""Οι κανόνες του «Ένωσε», χωρίς γραφικά, ώστε να ελέγχονται εύκολα.

Οι τελείες έχουν αριθμούς 1, 2, 3… Το παιδί τις πατά με τη σειρά και κάθε σωστή τελεία
ενώνεται με γραμμή με την προηγούμενη.
Μια εικόνα μπορεί να έχει ομάδες (π.χ. έναν αστερισμό η καθεμία): η πρώτη τελεία μιας ομάδας
δεν ενώνεται με την τελευταία της προηγούμενης. Στο τέλος της, μια ομάδα μπορεί να «κλείσει»
με γραμμή πίσω σε μια δική της τελεία.
"""
import math

HIT_RADIUS = 24   # πόσο κοντά στην τελεία πρέπει να πέσει το κλικ (μεγάλο, για μικρά χέρια)


def _segment_distance(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length = dx * dx + dy * dy
    k = 0.0 if length == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length))
    return math.hypot(p[0] - ax - k * dx, p[1] - ay - k * dy)


def label_positions(groups, distance=19):
    """Πού μπαίνει ο αριθμός κάθε τελείας.

    Δοκιμάζει θέσεις γύρω από την τελεία και κρατά αυτή που απέχει περισσότερο από τις άλλες
    τελείες και από τις γραμμές της εικόνας, προτιμώντας την πλευρά προς τα έξω.
    Έτσι κάθε αριθμός είναι καθαρά δίπλα στη δική του τελεία.
    """
    dots, segments = _picture_lines(groups)
    out = []
    i = 0
    for points, _ in groups:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        for x, y in points:
            ox, oy = x - cx, y - cy
            norm = math.hypot(ox, oy) or 1.0
            best, best_score = None, None
            for step in range(16):
                a = step * math.pi / 8
                lx, ly = x + distance * math.cos(a), y + distance * math.sin(a)
                near_dot = min((math.hypot(lx - qx, ly - qy) for j, (qx, qy) in enumerate(dots) if j != i),
                               default=99)
                near_line = min((_segment_distance((lx, ly), s, e) for s, e in segments), default=99)
                outward = (math.cos(a) * ox + math.sin(a) * oy) / norm
                # πρώτα να μη μοιάζει ότι ανήκει σε άλλη τελεία, μετά να μην πατά γραμμή
                score = 2 * min(near_dot - distance, 26) + min(near_line, 20) + 5 * outward
                if best_score is None or score > best_score:
                    best, best_score = (lx, ly), score
            out.append(best)
            i += 1
    return out


def _picture_lines(groups):
    dots, segments = [], []
    for points, close_to in groups:
        first = len(dots)
        dots += [tuple(p) for p in points]
        segments += [(dots[i], dots[i + 1]) for i in range(first, len(dots) - 1)]
        if close_to is not None:
            segments.append((dots[-1], dots[first + close_to]))
    return dots, segments


def home_position(groups, canvas, inset=56, side=None):
    """Πού περιμένει το R2 στην αρχή και πού εμφανίζεται ο φορτιστής στο τέλος.

    Μία από τις δύο κάτω γωνίες: αυτή που απέχει περισσότερο από τις τελείες, τους αριθμούς
    και τις γραμμές της εικόνας. side ("left" ή "right") διαλέγει γωνία χωρίς υπολογισμό.
    """
    w, h = canvas
    corners = {"left": (inset, h - inset), "right": (w - inset, h - inset)}
    if side in corners:
        return corners[side]
    dots, segments = _picture_lines(groups)
    marks = dots + label_positions(groups)

    def room(p):
        near = min((math.hypot(p[0] - x, p[1] - y) for x, y in marks), default=999)
        line = min((_segment_distance(p, a, b) for a, b in segments), default=999)
        return min(near, line)
    return max(corners.values(), key=lambda p: room(p) + (1 if p[0] < w / 2 else 0))


class DotGame:
    def __init__(self, groups):
        """groups: λίστα από (σημεία, κλείσιμο). Κλείσιμο: None ή η θέση της τελείας της ομάδας
        στην οποία γυρίζει η γραμμή στο τέλος (0 = στην πρώτη)."""
        self.dots = []
        self.group_of = []
        self.starts = set()
        self.closings = {}
        for g, (points, close_to) in enumerate(groups):
            first = len(self.dots)
            self.starts.add(first)
            self.dots += [tuple(p) for p in points]
            self.group_of += [g] * len(points)
            if close_to is not None:
                self.closings[len(self.dots) - 1] = first + close_to
        self.next = 0
        self.lines = []

    @property
    def done(self):
        return self.next >= len(self.dots)

    def distance(self, pos, i):
        x, y = self.dots[i]
        return math.hypot(pos[0] - x, pos[1] - y)

    def nearest(self, pos, radius=HIT_RADIUS):
        best = min(range(len(self.dots)), key=lambda i: self.distance(pos, i), default=None)
        if best is not None and self.distance(pos, best) <= radius:
            return best
        return None

    def click(self, pos, radius=HIT_RADIUS):
        """Ένα κλικ στη θέση pos. Επιστρέφει τι έγινε, με τη σειρά:

        ("dot", i)          σωστή τελεία
        ("line", a, b)      νέα γραμμή από την τελεία a στη b
        ("group", g)        τελείωσε η ομάδα g
        ("done",)           τελείωσε η εικόνα
        ("wrong", j)        το κλικ έπεσε σε άλλη τελεία (j)
        ("miss",)           το κλικ δεν έπεσε σε τελεία
        """
        if self.done:
            return []
        i = self.next
        if self.distance(pos, i) > radius:
            other = self.nearest(pos, radius)
            return [("wrong", other)] if other is not None else [("miss",)]
        events = [("dot", i)]
        if i not in self.starts:
            self.lines.append((i - 1, i))
            events.append(("line", i - 1, i))
        last_of_group = i + 1 == len(self.dots) or (i + 1) in self.starts
        if last_of_group:
            if i in self.closings:
                self.lines.append((i, self.closings[i]))
                events.append(("line", i, self.closings[i]))
            events.append(("group", self.group_of[i]))
        self.next += 1
        if self.done:
            events.append(("done",))
        return events
