"""Οι κανόνες και η φυσική του Ποδοσφαίρου, χωρίς γραφικά (τα τρέχει και ο υπολογιστής με το γήπεδο).

Το γήπεδο είναι όπως τα γήπεδα ρομποτικής: τοίχος γύρω γύρω (η μπάλα δεν βγαίνει ποτέ έξω),
κομμένες γωνίες για να μην κολλάει η μπάλα, το μπλε τέρμα αριστερά και το κίτρινο δεξιά.
Η Μπλε ομάδα φυλάει το μπλε τέρμα και βάζει γκολ στο κίτρινο.

Συντεταγμένες σε pixels, με αρχή την πάνω αριστερή γωνία της μοκέτας: x δεξιά, y κάτω.
Η γωνία a του R2 είναι σε ακτίνια: 0 = κοιτάει δεξιά, π/2 = κάτω (δεξιόστροφα στην οθόνη).

Το R2 κινείται όπως το αληθινό με τα δύο μοτέρ: μπροστά, πίσω και στροφή επί τόπου ή σε καμπύλη.
Με την κλωτσιά βγαίνει για λίγο μια πλάκα από μπροστά (όπως ο «kicker» των ρομπότ ποδοσφαίρου):
αν η μπάλα είναι εκεί, φεύγει ίσια προς τα εκεί που κοιτάει το R2. Μετά θέλει λίγο χρόνο να ξαναοπλίσει.
Για τη μπάλα το R2 είναι ένα ορθογώνιο (ίσια μπροστινή πλευρά, για να σπρώχνει τη μπάλα ίσια),
για τα άλλα R2 και τους τοίχους ένας κύκλος.
"""
import math
import random

FW, FH = 1124, 568                 # η μοκέτα
GOAL_W, GOAL_D = 190, 40           # το άνοιγμα και το βάθος του τέρματος
CORNER = 38                        # οι κομμένες γωνίες
GOAL_TOP, GOAL_BOTTOM = FH / 2 - GOAL_W / 2, FH / 2 + GOAL_W / 2

ROBOT_SIZE = 70                    # πόσο μεγάλο ζωγραφίζεται
ROBOT_R = 34                       # κύκλος για R2 με R2
WALL_R = 36                        # κύκλος για R2 με τοίχο
HALF_LEN, HALF_WID = 33, 30        # το ορθογώνιο του R2 (μπρος-πίσω, πλάι) για τη μπάλα
BALL_R = 15

V_MAX = 250.0                      # pixels/δευτερόλεπτο
ACCEL, BRAKE = 900.0, 1500.0
TURN = math.radians(230)           # ακτίνια/δευτερόλεπτο
KICK_SPEED = 450.0                 # πόσο πιο γρήγορα από το R2 φεύγει η μπάλα με την κλωτσιά
KICK_TIME = 0.15                   # πόση ώρα μένει έξω η πλάκα (όσο είναι έξω, κλωτσάει τη μπάλα)
KICK_RELOAD = 0.45                 # από την αρχή μιας κλωτσιάς ως την επόμενη
KICK_REACH = 14                    # πόσο βγαίνει η πλάκα μπροστά από το R2
KICK_WRAP = 1000                   # ο μετρητής των πατημάτων γυρίζει στο 0 εδώ
BALL_FRICTION = 0.85               # η μπάλα χάνει ταχύτητα σιγά σιγά στη μοκέτα
BALL_MAX = 950.0
BOUNCE_WALL, BOUNCE_ROBOT = 0.65, 0.45

STEP = 1 / 120                     # η φυσική τρέχει σε σταθερά βήματα
COUNT_TIME = 3.0                   # 3, 2, 1, Πάμε!
GOAL_TIME = 3.0                    # πόσο μένει η μπάλα στο δίχτυ πριν ξαναρχίσει
STUCK_TIME = 10.0                  # μπάλα που δεν πάει πουθενά τόση ώρα πάει σε ουδέτερο σημείο
STUCK_DIST = 50.0
MAX_TEAM = 3
MINUTES = (2, 3, 5)

BLUE, YELLOW = "b", "y"
TEAMS = (BLUE, YELLOW)
NEUTRAL = [(FW / 2, FH / 2)] + [(FW / 2 + dx, FH / 2 + dy) for dx in (-300, 300) for dy in (-150, 150)]
# πού στέκονται τα R2 της μπλε ομάδας στην αρχή (κλάσματα του γηπέδου). Η κίτρινη είναι ο καθρέφτης.
FORMATION = {1: [(0.30, 0.50)],
             2: [(0.32, 0.50), (0.13, 0.50)],
             3: [(0.33, 0.50), (0.20, 0.24), (0.20, 0.76)]}


def other(team):
    return YELLOW if team == BLUE else BLUE


def _poly(pocket):
    """Τα τοιχώματα του γηπέδου, με τη σειρά. pocket=True: με τις «τσέπες» των τέρματων (για τη μπάλα)."""
    k, gt, gb = CORNER, GOAL_TOP, GOAL_BOTTOM
    right = [(FW, k), (FW, gt), (FW + GOAL_D, gt), (FW + GOAL_D, gb), (FW, gb), (FW, FH - k)] if pocket \
        else [(FW, k), (FW, FH - k)]
    left = [(0, FH - k), (0, gb), (-GOAL_D, gb), (-GOAL_D, gt), (0, gt), (0, k)] if pocket \
        else [(0, FH - k), (0, k)]
    pts = [(k, 0), (FW - k, 0)] + right + [(FW - k, FH), (k, FH)] + left
    return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]


BALL_WALLS = _poly(True)
ROBOT_WALLS = _poly(False)


def _push_out(x, y, r, walls):
    """Βγάζει έναν κύκλο έξω από τους τοίχους. Επιστρέφει x, y και την τελευταία κάθετο (ή None)."""
    normal = None
    for (ax, ay), (bx, by) in walls:
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        cx, cy = ax + dx * t, ay + dy * t
        ox, oy = x - cx, y - cy
        d2 = ox * ox + oy * oy
        if d2 < r * r:
            d = math.sqrt(d2)
            if d < 1e-6:                  # ακριβώς πάνω στον τοίχο: προς τα μέσα του γηπέδου
                ox, oy, d = -dy, dx, math.hypot(dx, dy)
            nx, ny = ox / d, oy / d
            x, y = cx + nx * r, cy + ny * r
            normal = (nx, ny)
    return x, y, normal


def wrap(a):
    """Γωνία στο (-π, π]."""
    return (a + math.pi) % (2 * math.pi) - math.pi


class Input:
    """Τι πατάει ο παίκτης: fwd μπροστά 1 / πίσω -1, turn δεξιά 1 / αριστερά -1.
    kick: πόσες φορές έχει πατηθεί το πλήκτρο της κλωτσιάς. Κάθε φορά που αλλάζει, το R2 κλωτσάει.
    Είναι μετρητής και όχι «πατημένο ή όχι», για να μη χάνεται στο δίκτυο ένα πολύ γρήγορο πάτημα.
    Τα ρομπότ του υπολογιστή μπορούν να δώσουν και κλάσματα (π.χ. fwd 0.7 = πιο αργά)."""
    __slots__ = ("fwd", "turn", "kick")

    def __init__(self, fwd=0.0, turn=0.0, kick=0):
        self.fwd, self.turn, self.kick = fwd, turn, int(kick) % KICK_WRAP

    def as_list(self):
        return [self.fwd, self.turn, self.kick]

    @classmethod
    def from_list(cls, data):
        try:
            f, t, k = data
            return cls(max(-1.0, min(1.0, float(f))), max(-1.0, min(1.0, float(t))), int(k))
        except (TypeError, ValueError, OverflowError):
            return cls()

    def still(self):
        """Τα ίδια χωρίς κίνηση (π.χ. όσο είναι ανοιχτό το «Φεύγεις;»): ο μετρητής μένει ίδιος,
        αλλιώς θα έμοιαζε με πάτημα."""
        return Input(0.0, 0.0, self.kick)

    def __eq__(self, o):
        return isinstance(o, Input) and self.as_list() == o.as_list()


class Robot:
    def __init__(self, pid, team):
        self.id = pid
        self.team = team
        self.x = self.y = self.a = 0.0
        self.v = 0.0
        self.w = 0.0
        self.inp = Input()
        self.reset_kick()

    def reset_kick(self):
        self.kick_seen = None         # ο μετρητής που είδαμε τελευταία (None: δεν έχουμε δει ακόμα)
        self.kick_t = KICK_TIME       # πόση ώρα πριν άρχισε η κλωτσιά (KICK_TIME και πάνω: η πλάκα είναι μέσα)
        self.kick_done = True         # η μπάλα έφυγε ήδη με αυτή την κλωτσιά
        self.reload = 0.0

    @property
    def dir(self):
        return math.cos(self.a), math.sin(self.a)

    @property
    def kicking(self):
        return self.kick_t < KICK_TIME

    def drive(self, dt):
        """Κινεί το R2 για dt. Επιστρέφει True αν μόλις άρχισε κλωτσιά."""
        inp = self.inp
        fired = False
        self.reload = max(0.0, self.reload - dt)
        self.kick_t = min(KICK_TIME, self.kick_t + dt)
        if self.kick_seen is None:
            self.kick_seen = inp.kick
        elif inp.kick != self.kick_seen:
            self.kick_seen = inp.kick
            if self.reload <= 0:
                self.kick_t, self.kick_done, self.reload = 0.0, False, KICK_RELOAD
                fired = True
        target = inp.fwd * V_MAX
        rate = ACCEL if abs(target) > abs(self.v) and target * self.v >= 0 else BRAKE
        dv = target - self.v
        self.v += max(-rate * dt, min(rate * dt, dv))
        self.w = inp.turn * TURN
        self.a = wrap(self.a + self.w * dt)
        dx, dy = self.dir
        self.x += dx * self.v * dt
        self.y += dy * self.v * dt
        return fired

    def velocity_at(self, px, py):
        """Η ταχύτητα ενός σημείου του R2 (κίνηση + περιστροφή)."""
        dx, dy = self.dir
        return dx * self.v - self.w * (py - self.y), dy * self.v + self.w * (px - self.x)


class Ball:
    def __init__(self):
        self.x, self.y = FW / 2, FH / 2
        self.vx = self.vy = 0.0
        self.last = None          # ποιο R2 την άγγιξε τελευταίο


class Match:
    """Ένας αγώνας. players: λίστα από dict με id, name, team και bot (None ή "easy"/"normal"/"hard")."""

    def __init__(self, players, minutes=3, seed=None):
        from . import ai
        self.players = {p["id"]: dict(p) for p in players}
        self.robots = {}
        self.bots = {}
        for p in players:
            self.robots[p["id"]] = Robot(p["id"], p["team"])
            if p.get("bot"):
                self.bots[p["id"]] = ai.Bot(p["bot"], random.Random(seed if seed is None else seed + p["id"]))
        self.ball = Ball()
        self.minutes = minutes
        self.clock = minutes * 60.0
        self.score = {BLUE: 0, YELLOW: 0}
        self.goals = []           # [ομάδα που σκόραρε, όνομα σκόρερ ή "", αυτογκόλ]
        self.time = 0.0           # χρόνος αγώνα (και για το δίκτυο)
        self.phase = "count"
        self.phase_t = 0.0
        self.events = []
        self._acc = 0.0
        self._anchor = (FW / 2, FH / 2)
        self._still = 0.0
        self.kickoff()

    # ------------------------------------------------------------ θέσεις
    def team_ids(self, team):
        return [pid for pid, p in self.players.items() if p["team"] == team]

    def kickoff(self):
        for team in TEAMS:
            ids = self.team_ids(team)
            spots = FORMATION.get(len(ids)) or [(0.15 + 0.2 * (i % 2), (i + 1) / (len(ids) + 1))
                                                for i in range(len(ids))]
            for pid, (fx, fy) in zip(ids, spots):
                r = self.robots[pid]
                r.x = fx * FW if team == BLUE else FW - fx * FW
                r.y = fy * FH
                r.a = 0.0 if team == BLUE else math.pi
                r.v = r.w = 0.0
                r.reset_kick()            # ό,τι πατήθηκε στο 3, 2, 1 δεν κλωτσάει στο «Πάμε!»
        b = self.ball
        b.x, b.y, b.vx, b.vy = FW / 2, FH / 2, 0.0, 0.0
        self._anchor, self._still = (b.x, b.y), 0.0
        self.phase, self.phase_t = "count", 0.0
        for bot in self.bots.values():
            bot.reset()

    def remove(self, pid):
        """Ένας παίκτης έφυγε από το δίκτυο: το R2 του βγαίνει από το γήπεδο."""
        self.robots.pop(pid, None)
        self.players.pop(pid, None)
        self.bots.pop(pid, None)
        if self.ball.last == pid:
            self.ball.last = None

    # ------------------------------------------------------------ χρόνος
    def update(self, dt, inputs=None):
        """inputs: {id: Input} για τους παίκτες. Επιστρέφει τα γεγονότα (για ήχους): λίστα [όνομα, δύναμη]."""
        self.events = []
        inputs = inputs or {}
        self._acc = min(self._acc + dt, 0.25)
        while self._acc >= STEP:
            self._acc -= STEP
            self._step(inputs)
        return self.events

    def _step(self, inputs):
        dt = STEP
        self.time += dt
        self.phase_t += dt
        if self.phase == "count":
            before = math.ceil(COUNT_TIME - (self.phase_t - dt) - 1e-9)
            now = math.ceil(COUNT_TIME - self.phase_t - 1e-9)
            if self.phase_t <= dt + 1e-9:
                self.events.append(["count", before])
            elif now != before and now > 0:
                self.events.append(["count", now])
            if self.phase_t >= COUNT_TIME:
                self.phase, self.phase_t = "play", 0.0
                self.events.append(["go", 1])
            return                     # τα R2 περιμένουν το «Πάμε!»
        if self.phase == "end":
            return
        for pid, r in self.robots.items():
            if pid in self.bots:
                r.inp = self.bots[pid].decide(self, r, dt)
            else:
                r.inp = inputs.get(pid) or Input(kick=r.kick_seen or 0)
            if r.drive(dt):
                self.events.append(["shoot", 1])
        for _ in range(3):              # R2 με R2 και R2 με τοίχο, λίγες φορές για να «κάτσουν»
            self._collide_robots()
            for r in self.robots.values():
                r.x, r.y, _ = _push_out(r.x, r.y, WALL_R, ROBOT_WALLS)
        self._move_ball(dt)
        if self.phase == "play":
            self.clock = max(0.0, self.clock - dt)
            self._check_goal()
            self._check_stuck(dt)
            if self.clock <= 0 and self.phase == "play":
                self.phase, self.phase_t = "end", 0.0
                for r in self.robots.values():
                    r.v = r.w = 0.0
                    r.kick_t = KICK_TIME
                self.events.append(["end", 1])
        elif self.phase == "goal" and self.phase_t >= GOAL_TIME:
            self.kickoff()
            self.events.append(["whistle", 1])

    # ------------------------------------------------------------ συγκρούσεις
    def _collide_robots(self):
        rs = list(self.robots.values())
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                dx, dy = b.x - a.x, b.y - a.y
                d2 = dx * dx + dy * dy
                if d2 < (2 * ROBOT_R) ** 2:
                    d = math.sqrt(d2) or 1e-6
                    if d2 == 0:
                        dx, dy = 1.0, 0.0
                    push = (2 * ROBOT_R - d) / 2
                    nx, ny = dx / d, dy / d
                    a.x -= nx * push
                    a.y -= ny * push
                    b.x += nx * push
                    b.y += ny * push

    def _ball_vs_robot(self, r, bounce=True):
        """Αν η μπάλα ακουμπά το ορθογώνιο του R2, τη βγάζει έξω και τη σπρώχνει. True αν ακούμπησε."""
        b = self.ball
        dx, dy = r.dir
        ox, oy = b.x - r.x, b.y - r.y
        f = ox * dx + oy * dy             # μπροστά/πίσω
        s = -ox * dy + oy * dx            # πλάι
        cf = max(-HALF_LEN, min(HALF_LEN, f))
        cs = max(-HALF_WID, min(HALF_WID, s))
        lf, ls = f - cf, s - cs
        d2 = lf * lf + ls * ls
        if d2 >= BALL_R * BALL_R:
            return False
        if d2 > 1e-9:
            d = math.sqrt(d2)
            nf, ns = lf / d, ls / d
            pen = BALL_R - d
        else:                             # το κέντρο της μπάλας μέσα στο R2: από την πιο κοντινή πλευρά
            gaps = [(HALF_LEN - f, 1, 0), (HALF_LEN + f, -1, 0), (HALF_WID - s, 0, 1), (HALF_WID + s, 0, -1)]
            gap, nf, ns = min(gaps)
            pen = gap + BALL_R
        nx, ny = nf * dx - ns * dy, nf * dy + ns * dx
        b.x += nx * pen
        b.y += ny * pen
        b.last = r.id
        if bounce:
            px, py = r.x + (cf * dx - cs * dy), r.y + (cf * dy + cs * dx)
            vx, vy = r.velocity_at(px, py)
            rel = (b.vx - vx) * nx + (b.vy - vy) * ny
            if rel < 0:
                before = math.hypot(b.vx, b.vy)
                b.vx -= (1 + BOUNCE_ROBOT) * rel * nx
                b.vy -= (1 + BOUNCE_ROBOT) * rel * ny
                # μπάλα «στριμωγμένη» ανάμεσα σε δύο R2 δεν πετάγεται σαν σφαίρα
                limit = max(before, abs(r.v) * 1.6 + 80)
                sp = math.hypot(b.vx, b.vy)
                if sp > limit:
                    b.vx, b.vy = b.vx * limit / sp, b.vy * limit / sp
                if rel < -60:
                    self.events.append(["kick", min(1.0, -rel / 600)])
        return True

    def _move_ball(self, dt):
        b = self.ball
        b.x += b.vx * dt
        b.y += b.vy * dt
        f = math.exp(-BALL_FRICTION * dt)
        b.vx *= f
        b.vy *= f
        sp = math.hypot(b.vx, b.vy)
        if sp > BALL_MAX:
            b.vx, b.vy = b.vx * BALL_MAX / sp, b.vy * BALL_MAX / sp
        # κάθε βήμα με άλλη σειρά, για να μην κερδίζει πάντα η ίδια ομάδα όταν σπρώχνουν και οι δύο
        order = list(self.robots.values())
        self._flip = not getattr(self, "_flip", False)
        if self._flip:
            order.reverse()
        for _ in range(2):
            for r in order:
                self._ball_vs_robot(r)
        for r in order:
            if r.kicking and not r.kick_done and self._kick(r):
                r.kick_done = True
        b.x, b.y, n = _push_out(b.x, b.y, BALL_R, BALL_WALLS)
        if n:
            vn = b.vx * n[0] + b.vy * n[1]
            if vn < 0:
                b.vx -= (1 + BOUNCE_WALL) * vn * n[0]
                b.vy -= (1 + BOUNCE_WALL) * vn * n[1]
                if vn < -80:
                    self.events.append(["wall", min(1.0, -vn / 700)])
        # η μπάλα σφήνωσε ανάμεσα σε R2 και τοίχο, ή ανάμεσα σε δύο R2: τα R2 κάνουν πίσω,
        # η μπάλα δεν μπαίνει μέσα τους
        for r in order:
            ox, oy = b.x - r.x, b.y - r.y
            if ox * ox + oy * oy < (HALF_LEN + HALF_WID + BALL_R) ** 2 and self._overlaps(r):
                self._robot_yields(r)
        # ασφάλεια: η μπάλα δεν βγαίνει ποτέ από το γήπεδο
        if not (-GOAL_D <= b.x <= FW + GOAL_D and 0 <= b.y <= FH):
            b.x, b.y, b.vx, b.vy = FW / 2, FH / 2, 0.0, 0.0

    def _kick(self, r):
        """Η πλάκα είναι έξω: αν η μπάλα είναι μπροστά της, φεύγει ίσια μπροστά. True αν την κλώτσησε."""
        b = self.ball
        dx, dy = r.dir
        ox, oy = b.x - r.x, b.y - r.y
        f = ox * dx + oy * dy             # πόσο μπροστά
        s = -ox * dy + oy * dx            # πόσο στο πλάι
        if not (HALF_LEN < f <= HALF_LEN + BALL_R + KICK_REACH and abs(s) < HALF_WID + BALL_R * 0.7):
            return False
        vf = b.vx * dx + b.vy * dy
        vs = -b.vx * dy + b.vy * dx
        vf = max(vf, max(r.v, 0.0) + KICK_SPEED)
        vs *= 0.4
        b.vx, b.vy = vf * dx - vs * dy, vf * dy + vs * dx
        sp = math.hypot(b.vx, b.vy)
        if sp > BALL_MAX:
            b.vx, b.vy = b.vx * BALL_MAX / sp, b.vy * BALL_MAX / sp
        b.last = r.id
        self.events.append(["kick", 1.0])
        return True

    def _overlaps(self, r):
        b = self.ball
        dx, dy = r.dir
        ox, oy = b.x - r.x, b.y - r.y
        f, s = ox * dx + oy * dy, -ox * dy + oy * dx
        lf = f - max(-HALF_LEN, min(HALF_LEN, f))
        ls = s - max(-HALF_WID, min(HALF_WID, s))
        return lf * lf + ls * ls < (BALL_R - 0.5) ** 2

    def _robot_yields(self, r):
        b = self.ball
        for _ in range(6):
            if not self._overlaps(r):
                break
            ox, oy = r.x - b.x, r.y - b.y
            d = math.hypot(ox, oy) or 1.0
            r.x += ox / d * 2
            r.y += oy / d * 2
        r.v = min(r.v, 0.0) if r.v > 0 else r.v

    # ------------------------------------------------------------ κανόνες
    def _check_goal(self):
        b = self.ball
        if not GOAL_TOP < b.y < GOAL_BOTTOM:
            return
        if b.x < -BALL_R:
            team = YELLOW           # μπήκε στο μπλε τέρμα
        elif b.x > FW + BALL_R:
            team = BLUE
        else:
            return
        self.score[team] += 1
        scorer = self.players.get(b.last)
        own = scorer is not None and scorer["team"] != team
        name = scorer["name"] if scorer is not None and not own else ""
        self.goals.append([team, name, own])
        self.phase, self.phase_t = "goal", 0.0
        self.events.append(["goal", 1])

    def _check_stuck(self, dt):
        b = self.ball
        if math.hypot(b.x - self._anchor[0], b.y - self._anchor[1]) > STUCK_DIST:
            self._anchor, self._still = (b.x, b.y), 0.0
            return
        self._still += dt
        if self._still < STUCK_TIME:
            return
        free = [p for p in NEUTRAL
                if all(math.hypot(r.x - p[0], r.y - p[1]) > ROBOT_R + BALL_R + 12 for r in self.robots.values())]
        spot = min(free or NEUTRAL[:1], key=lambda p: math.hypot(p[0] - b.x, p[1] - b.y))
        b.x, b.y, b.vx, b.vy = spot[0], spot[1], 0.0, 0.0
        self._anchor, self._still = spot, 0.0
        self.events.append(["spot", 1])

    # ------------------------------------------------------------ για ζωγραφική και δίκτυο
    def snapshot(self):
        """Όλα όσα χρειάζεται η οθόνη, σε μορφή που στέλνεται στο δίκτυο (JSON).
        Για κάθε R2: [id, x, y, γωνία, 1 αν είναι έξω η πλάκα της κλωτσιάς, ταχύτητα]."""
        return {"ht": round(self.time, 4), "ph": self.phase, "pt": round(self.phase_t, 3),
                "clk": round(self.clock, 2), "sc": [self.score[BLUE], self.score[YELLOW]],
                "ball": [round(self.ball.x, 1), round(self.ball.y, 1)],
                "r": [[pid, round(r.x, 1), round(r.y, 1), round(r.a, 3), int(r.kicking), round(r.v, 1)]
                      for pid, r in self.robots.items()],
                "goals": [list(g) for g in self.goals]}

    def roster(self):
        return [dict(p) for p in self.players.values()]
