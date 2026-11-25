"""Το ρομπότ του υπολογιστή: πατάει «πλήκτρα» (Input) όπως ένα παιδί.

Επιθετικός: πάει πίσω από τη μπάλα (από την πλευρά του δικού του τέρματος) και τη σπρώχνει προς
το τέρμα του αντιπάλου. Στο κανονικό και στο δύσκολο κλωτσάει κιόλας, όταν η μπάλα είναι μπροστά του
και θα πήγαινε μέσα στο τέρμα. Αν βρεθεί ανάμεσα στη μπάλα και στο αντίπαλο τέρμα, κάνει κύκλο γύρω της,
για να μη σπρώξει τη μπάλα προς το δικό του τέρμα.
Αμυντικός (όταν η ομάδα έχει 2+ R2 και αυτό είναι το πιο κοντινό στο δικό της τέρμα): στέκεται
ανάμεσα στη μπάλα και στο τέρμα του, και βγαίνει στη μπάλα μόνο όταν έρθει κοντά.
"""
import math

from . import logic as L

LEVELS = {
    # ταχύτητα, κάθε πότε αποφασίζει (s), νεκρή ζώνη στροφής (μοίρες), κλωτσάει, λάθος στόχευσης (px)
    "easy": (0.62, 0.22, 16, False, 40),
    "normal": (0.8, 0.12, 11, True, 22),
    "hard": (1.0, 0.03, 7, True, 8),
}


class Bot:
    def __init__(self, level="normal", rng=None):
        self.level = level if level in LEVELS else "normal"
        self.speed, self.every, dead, self.kicks, self.noise = LEVELS[self.level]
        self.dead = math.radians(dead)
        import random
        self.rng = rng or random.Random()
        self.wait = 0.0
        self.kick = 0                     # ο μετρητής της κλωτσιάς (όπως ενός παιδιού που πατά Space)
        self.last = L.Input()
        self.blocked = 0.0
        self.escape = 0.0
        self.aim = (0.0, 0.0)

    def reset(self):
        """Στην αρχή και μετά από γκολ: λίγη τυχαία καθυστέρηση, για να μη γίνεται κάθε φορά το ίδιο."""
        self.wait = self.rng.uniform(0.0, 0.4)
        self.last = L.Input(kick=self.kick)
        self.blocked = self.escape = 0.0
        self.aim = (self.rng.uniform(-1, 1) * self.noise, self.rng.uniform(-1, 1) * self.noise)

    def decide(self, match, r, dt):
        if self.escape > 0:               # κόλλησε σε τοίχο ή R2: πίσω με στροφή
            self.escape -= dt
            return L.Input(-self.speed, 1.0, self.kick)
        self.wait -= dt
        if self.wait > 0:
            self._watch_blocked(r, dt)
            return self.last
        self.wait = self.every
        if self.rng.random() < 0.15:
            self.aim = (self.rng.uniform(-1, 1) * self.noise, self.rng.uniform(-1, 1) * self.noise)
        self.last = self._think(match, r)
        self._watch_blocked(r, dt)
        return self.last

    def _watch_blocked(self, r, dt):
        if self.last.fwd > 0.3 and abs(r.v) < 25:
            self.blocked += dt
            if self.blocked > 0.9:
                self.blocked = 0.0
                self.escape = 0.55
        else:
            self.blocked = 0.0

    # ------------------------------------------------------------ σκέψη
    def _think(self, match, r):
        if match.phase != "play":
            return L.Input(kick=self.kick)
        b = match.ball
        lead = 0.25
        bx = min(L.FW - L.BALL_R, max(L.BALL_R, b.x + b.vx * lead))
        by = min(L.FH - L.BALL_R, max(L.BALL_R, b.y + b.vy * lead))
        goal = (L.FW + 30, L.FH / 2) if r.team == L.BLUE else (-30, L.FH / 2)
        own = (-10, L.FH / 2) if r.team == L.BLUE else (L.FW + 10, L.FH / 2)
        if self._is_defender(match, r, own):
            near = math.hypot(bx - own[0], by - own[1]) < 300
            if not near:
                ox, oy = bx - own[0], by - own[1]
                d = math.hypot(ox, oy) or 1.0
                tx, ty = own[0] + ox / d * 130, own[1] + oy / d * 130
                return self._steer(r, tx, ty, slow=True)
        gx, gy = goal[0] - bx, goal[1] - by
        gd = math.hypot(gx, gy) or 1.0
        ux, uy = gx / gd, gy / gd                              # από τη μπάλα προς το αντίπαλο τέρμα
        rx, ry = bx - r.x, by - r.y
        rd = math.hypot(rx, ry) or 1.0
        behind = (rx * ux + ry * uy) / rd                      # 1 = ακριβώς πίσω από τη μπάλα
        if behind > math.cos(math.radians(32)) and rd < 150:
            tx, ty = bx + ux * 40 + self.aim[0], by + uy * 40 + self.aim[1]
            if self.kicks and r.reload <= 0 and self._shot(match, r, b, goal):
                self.kick = (self.kick + 1) % L.KICK_WRAP
            return self._steer(r, tx, ty)
        back = L.HALF_LEN + L.BALL_R + 22
        tx, ty = bx - ux * back, by - uy * back
        if (r.x - bx) * ux + (r.y - by) * uy > -20:            # μπροστά από τη μπάλα: γύρω γύρω
            side = 1 if (ux * (r.y - by) - uy * (r.x - bx)) > 0 else -1
            tx, ty = bx - ux * 70 - uy * 95 * side, by - uy * 70 + ux * 95 * side
        tx = min(L.FW - 30, max(30, tx))
        ty = min(L.FH - 30, max(30, ty))
        return self._steer(r, tx + self.aim[0] * 0.5, ty + self.aim[1] * 0.5)

    @staticmethod
    def _shot(match, r, b, goal):
        """Η μπάλα είναι μπροστά στην πλάκα και, αν φύγει ίσια, πάει μέσα στο τέρμα χωρίς να βρει R2."""
        dx, dy = r.dir
        ox, oy = b.x - r.x, b.y - r.y
        f, s = ox * dx + oy * dy, -ox * dy + oy * dx
        if not (L.HALF_LEN < f < L.HALF_LEN + L.BALL_R + L.KICK_REACH - 2 and abs(s) < L.HALF_WID - 4):
            return False
        gx = goal[0] - b.x
        if abs(gx) > 750 or gx * dx <= 0:
            return False
        dist = gx / dx
        if not L.GOAL_TOP + 25 < b.y + dy * dist < L.GOAL_BOTTOM - 25:
            return False
        for o in match.robots.values():
            if o is r:
                continue
            px, py = o.x - b.x, o.y - b.y
            along = px * dx + py * dy
            if 0 < along < dist and abs(-px * dy + py * dx) < L.ROBOT_R + L.BALL_R + 6:
                return False
        return True

    def _is_defender(self, match, r, own):
        mates = [m for m in match.robots.values() if m.team == r.team]
        if len(mates) < 2:
            return False
        closest = min(mates, key=lambda m: math.hypot(m.x - own[0], m.y - own[1]))
        return closest is r

    def _steer(self, r, tx, ty, slow=False):
        dx, dy = tx - r.x, ty - r.y
        dist = math.hypot(dx, dy)
        if dist < 14:
            return L.Input(0.0, 0.0, self.kick)
        err = L.wrap(math.atan2(dy, dx) - r.a)
        turn = 0.0 if abs(err) < self.dead else (1.0 if err > 0 else -1.0)
        if abs(err) < math.radians(65):
            fwd = self.speed * (0.6 if slow and dist < 60 else 1.0)
        elif abs(err) > math.radians(150) and dist < 90:
            fwd, turn = -self.speed * 0.7, 0.0                  # ο στόχος είναι ακριβώς πίσω: όπισθεν
        else:
            fwd = 0.0                                           # στροφή επί τόπου
        return L.Input(fwd, turn, self.kick)
