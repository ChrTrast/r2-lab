"""Έλεγχοι για το «Προγραμμάτισε». Τρέξε:  py -m unittest discover tests"""
import math
import os
import sys
import unittest
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.program import LEVEL_COUNT, levels, logic as L  # noqa: E402

LINE = """
S . . # .
. . . . G
"""


def worlds_of(level):
    return L.level_worlds(level)


def reasons(events):
    return [e.a for e in events if e.kind == "fail"]


# ===================================================================== λύτης
def straight_actions(worlds, waits=True):
    """Οι εντολές που δοκιμάζει ο λύτης: κίνηση, στροφή, LED στα χρώματα των πορτών, περίμενε."""
    acts = [L.move(d, n) for d in ("forward", "back") for n in range(1, 9)]
    acts += [L.turn(d, n) for d in ("right", "left") for n in range(1, 5)]
    colors = {L.DOORS[ch] for w in worlds for ch in w.cells.values() if ch in L.DOORS}
    acts += [L.led(c) for c in sorted(colors)]
    if waits and any(w.bug or w.sink or w.mover for w in worlds):
        acts += [L.wait(n) for n in range(1, 7)]
    return acts


def solve(world, acts, crystals=True, max_blocks=16):
    """Το πιο σύντομο πρόγραμμα χωρίς βρόχους (BFS): μία εντολή = ένα βήμα του ψαξίματος.
    Επιστρέφει τη λίστα με τις εντολές ή None."""
    period = 2 * len(world.bug) - 2 if world.bug and len(world.bug) > 1 else 1
    if world.sink:                                 # οι γέφυρες ξαναγίνονται ίδιες κάθε (πάνω + κάτω) δευτερόλεπτα
        period = math.lcm(period, world.sink[0] + world.sink[1])
    start = (world.start, world.face, None, frozenset(), 0)
    seen = {(start[0], start[1], start[2], start[3], 0)}
    todo = deque([(start, [])])
    while todo:
        (pos, face, led, taken, t), prog = todo.popleft()
        if len(prog) >= max_blocks:
            continue
        for a in acts:
            run = L.Run(world)
            run.pos, run.facing, run.led, run.taken, run.t = pos, face, led, set(taken), t
            run.do(a)
            if run.failure:
                continue
            if run.docked:
                if not crystals or run.taken == world.crystals:
                    return prog + [a]
                continue
            moved = min(run.t, len(world.mover)) if world.mover else 0      # η εργαλειοθήκη σταματά στο τέλος
            key = (run.pos, run.facing, run.led, frozenset(run.taken), run.t % period, moved)
            if key not in seen:
                seen.add(key)
                todo.append(((run.pos, run.facing, run.led, frozenset(run.taken), run.t), prog + [a]))
    return None


def one_edit_apart(a, b):
    """Διαφέρουν κατά μία αλλαγή: ένα πεδίο σε ένα μπλοκ, ή ένα μπλοκ παραπάνω/λιγότερο;"""
    fa, fb = list(L.walk(a)), list(L.walk(b))
    if len(fa) == len(fb):
        diffs = 0
        for (pa, na), (pb, nb) in zip(fa, fb):
            if pa != pb or na["op"] != nb["op"]:
                return False
            diffs += sum(1 for k in na if k not in ("body", "then", "else") and na[k] != nb[k])
        return diffs == 1
    if abs(len(fa) - len(fb)) != 1:
        return False
    small, big = (a, b) if len(fa) < len(fb) else (b, a)
    for path, _ in L.walk(big):
        trial = L.clone(big)
        lst = L.list_at(trial, path[:-1])
        if not L.mouths(lst[path[-1]]):
            del lst[path[-1]]
            if trial == small:
                return True
    return False


# ================================================================ κανόνες
class WorldTests(unittest.TestCase):
    def test_map_needs_one_start_and_one_charger(self):
        with self.assertRaises(ValueError):
            L.World("S . .\n. . .")
        with self.assertRaises(ValueError):
            L.World("S . G\n. .")
        with self.assertRaises(ValueError):
            L.World("S . G X")
        w = L.World(LINE)
        self.assertEqual((w.cols, w.rows, w.start, w.goal), (5, 2, (0, 0), (4, 1)))

    def test_seconds_are_squares_and_quarter_turns(self):
        run = L.Run(L.World("S . . . .\n. . . . G"))
        run.do(L.move("forward", 2))
        self.assertEqual((run.pos, run.t), ((2, 0), 2))
        run.do(L.turn("right", 2))                    # μισή στροφή: κοιτάει αριστερά
        self.assertEqual((run.facing, run.t), (L.LEFT, 4))
        run.do(L.move("back", 1))                     # πίσω χωρίς να γυρίσει
        self.assertEqual((run.pos, run.facing), ((3, 0), L.LEFT))

    def test_what_stops_the_robot(self):
        w = L.World("""
        S # T ~ R
        . . . . G
        """)
        for program, why in (([L.move("forward", 1)], "stone"), ([L.turn("left"), L.move("forward")], "edge"),
                              ([L.turn("right"), L.move(), L.turn("left"), L.move("forward", 2), L.turn("left"),
                                L.move()], "tree")):
            run = L.Run(w)
            self.assertEqual(reasons(run.play(program)), [why])
            self.assertFalse(run.docked)
        run = L.Run(L.World("S ~ G"))
        self.assertEqual(reasons(run.play([L.move("forward", 2)])), ["water"])

    def test_door_opens_with_the_led_color(self):
        w = L.World("S R . G")
        self.assertEqual(reasons(L.Run(w).play([L.move("forward", 3)])), ["door"])
        self.assertEqual(reasons(L.Run(w).play([L.led("blue"), L.move("forward", 3)])), ["door"])
        run = L.Run(w)
        events = run.play([L.led("red"), L.move("forward", 3)])
        self.assertTrue(run.docked)
        self.assertEqual([e.kind for e in events][-1], "dock")

    def test_charger_ends_the_program_and_crystals_are_counted(self):
        w = L.World("S c G . .")
        run = L.Run(w)
        events = run.play([L.move("forward", 4), L.turn("right")])
        self.assertTrue(run.docked)
        self.assertEqual(run.pos, (2, 0))              # σταμάτησε στον φορτιστή, μέσα στο «για 4»
        self.assertEqual(run.taken, {(1, 0)})
        self.assertNotIn("turn", [e.kind for e in events])

    def test_program_that_ends_early_fails(self):
        run = L.Run(L.World(LINE))
        events = run.play([L.move("forward", 1)])
        self.assertEqual(events[-1].kind, "fail")
        self.assertEqual((events[-1].a, events[-1].path), ("end", None))

    def test_distance_sensor(self):
        w = L.World("S . . # ~ G")
        self.assertEqual(w.distance((0, 0), L.RIGHT, None), 10 + 2 * 20)
        self.assertEqual(w.distance((2, 0), L.RIGHT, None), 10)
        self.assertEqual(w.distance((0, 0), L.LEFT, None), L.FAR_CM)
        water = L.World("S ~ ~ . G")
        self.assertEqual(water.distance((0, 0), L.RIGHT, None), L.FAR_CM)     # το νερό δεν το «βλέπει»
        door = L.World("S . B G")
        self.assertEqual(door.distance((0, 0), L.RIGHT, None), 30)
        self.assertEqual(door.distance((0, 0), L.RIGHT, "blue"), L.FAR_CM)

    def test_go_until_stop_like_the_worksheet(self):
        w = L.World("""
        S . . . # .
        ~ ~ ~ G ~ ~
        """)
        prog = [L.go(), L.until(15), L.stop(), L.turn("right"), L.move("forward", 1)]
        run = L.Run(w)
        run.play(prog)
        self.assertTrue(run.docked)
        prog[1] = L.until(35)                          # σταματά ένα κουτάκι νωρίτερα
        run = L.Run(w)
        self.assertEqual(reasons(run.play(prog)), ["water"])
        self.assertEqual(run.pos, (2, 0))

    def test_motors_keep_going_without_stop(self):
        run = L.Run(L.World("S . . . G"))
        run.play([L.go()])                             # «Κινήσου» χωρίς «Σταμάτησε»: φτάνει ως τον φορτιστή
        self.assertTrue(run.docked)
        run = L.Run(L.World("S . . # G"))
        self.assertEqual(reasons(run.play([L.go()])), ["stone"])

    def test_repeat_forever_and_if(self):
        w = L.World("""
        S . . #
        ~ ~ . ~
        ~ G . ~
        ~ ~ # ~
        """)
        run = L.Run(w)
        events = run.play([L.forever(L.if_else(15, [L.turn("right")], [L.move("forward", 1)]))])
        self.assertTrue(run.docked)
        loops = [e for e in events if e.kind == "loop"]
        self.assertEqual([e.a for e in loops], list(range(1, len(loops) + 1)))
        self.assertEqual({e.b for e in loops}, {0})
        branches = [e.a for e in events if e.kind == "branch"]
        self.assertEqual(branches.count(0), 2)         # δύο στροφές
        run = L.Run(L.World("S . . . G"))
        events = run.play([L.repeat(4, L.move("forward", 1))])
        self.assertEqual([e.a for e in events if e.kind == "loop"], [1, 2, 3, 4])
        self.assertTrue(run.docked)

    def test_endless_programs_stop(self):
        run = L.Run(L.World("S . ~ G"))
        self.assertEqual(reasons(run.play([L.forever(L.turn("right"))])), ["time"])
        run = L.Run(L.World("S . ~ G"))
        self.assertEqual(reasons(run.play([L.forever(L.led("red"))])), ["stuck"])
        run = L.Run(L.World("S . ~ G"))
        self.assertEqual(reasons(run.play([L.until(15)])), ["time"])

    def test_ladybug(self):
        w = L.World("""
        . . s . .
        S . s . G
        . . s . .
        """, bug=[(2, 0), (2, 1), (2, 2)])
        self.assertEqual([w.bug_at(t) for t in range(6)], [(2, 0), (2, 1), (2, 2), (2, 1), (2, 0), (2, 1)])
        self.assertEqual(reasons(L.Run(w).play([L.move("forward", 4)])), ["bug"])
        run = L.Run(w)
        run.play([L.wait(1), L.move("forward", 4)])
        self.assertEqual(run.failure[1], "bug")        # πέφτει πάνω της στο γύρισμα
        self.assertEqual(w.distance((1, 1), L.RIGHT, None, 1), 10)   # ο αισθητήρας τη βλέπει

    def test_remote_control_scripts(self):
        remote = [L.key("up_arrow", L.move("forward", 1)), L.key("right_arrow", L.turn("right", 1))]
        self.assertTrue(L.scripts(remote))
        self.assertFalse(L.scripts([L.move()]))
        w = L.World("""
        S . . .
        . . . G
        """)
        run = L.Run(w)
        self.assertEqual([e.kind for e in run.press(remote, "up_arrow")], ["block", "block", "move"])
        self.assertEqual(run.pos, (1, 0))
        self.assertEqual(list(run.press(remote, "down_arrow")), [])          # δεν υπάρχει: τίποτα
        self.assertEqual(run.pos, (1, 0))
        # με τα πατήματα του χάρτη (drive) το ελέγχουν και τα tests, χωρίς πληκτρολόγιο
        driven = L.World("""
        S . . .
        . . . G
        """, drive=["up_arrow", "up_arrow", "right_arrow", "up_arrow"])
        self.assertEqual(L.check([driven], remote + [L.key("left_arrow", L.turn("left", 1))]), (False, True))
        driven = L.World("S . . G", drive=["up_arrow"] * 3)
        self.assertEqual(L.check([driven], remote), (True, True))
        # οι εντολές μπαίνουν μόνο κάτω από ένα «όταν πατηθεί πλήκτρο», τα καπέλα μόνο ως νέο πρόγραμμα
        self.assertFalse(L.can_insert(remote, (), 2, [L.move()], scripts=True))
        self.assertTrue(L.can_insert(remote, (0, 0), 1, [L.move()], scripts=True))
        self.assertFalse(L.can_insert(remote, (0, 0), 1, [L.key()], scripts=True))
        self.assertTrue(L.can_insert(remote, (), 2, [L.key("left_arrow")], scripts=True))
        self.assertEqual(L.append_spot(remote), ((1, 0), 1))                  # κλικ: στο τελευταίο πρόγραμμα
        self.assertEqual(L.choices(L.key(), "key"), ("up_arrow", "down_arrow", "right_arrow", "left_arrow"))

    def test_line_follow(self):
        w = L.World("""
        S . . .
        . # . .
        . . G .
        """, line=[(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)])
        run = L.Run(w)
        events = run.play([L.follow("on")])            # ακολουθεί τη γραμμή και στρίβει μόνο του
        self.assertTrue(run.docked)
        self.assertEqual([e.kind for e in events if e.kind in ("move", "turn")], ["move", "move", "turn", "move", "move"])
        self.assertEqual(reasons(L.Run(w).play([L.follow("off")])), ["end"])
        end = L.World("S . . G", line=[(0, 0), (1, 0)])  # στο τέλος της γραμμής σταματά
        run = L.Run(end)
        run.play([L.follow("on")])
        self.assertEqual((run.failure[1], run.pos), ("end", (1, 0)))
        stone = L.World("S . # G", line=[(0, 0), (1, 0), (2, 0)])
        self.assertEqual(reasons(L.Run(stone).play([L.follow("on")])), ["stone"])
        run = L.Run(stone)                             # σταματά με τον αισθητήρα και «Απενεργοποίηση»
        run.play([L.follow("on"), L.until(15), L.follow("off")])
        self.assertEqual((run.failure[1], run.pos), ("end", (1, 0)))
        off = L.World("""
        S . . G
        . . . .
        """, line=[(0, 1), (1, 1)])
        self.assertEqual(reasons(L.Run(off).play([L.follow("on")])), ["noline"])   # δεν είναι πάνω στη γραμμή
        self.assertEqual(L.choices(L.follow(), "mode"), ("on", "off"))

    def test_moving_toolbox(self):
        w = L.World("""
        S . . . . G .
        """, mover=[(3, 0), (4, 0), (5, 0), (6, 0)])
        self.assertEqual([w.mover_at(t) for t in (0, 2, 3, 9)], [(3, 0), (5, 0), (6, 0), (6, 0)])
        self.assertEqual([w.distance((0, 0), L.RIGHT, None, t) for t in (0, 1)], [50, 70])  # ο αισθητήρας τη βλέπει
        run = L.Run(w)
        run.play([L.go(), L.until(15), L.stop()])      # την ακολουθεί ως δίπλα της: φορτιστής
        self.assertTrue(run.docked)
        run = L.Run(w)
        run.play([L.go(), L.until(35), L.stop()])      # σταματά ένα κουτάκι νωρίτερα
        self.assertEqual((run.failure[1], run.pos), ("end", (4, 0)))
        stuck = L.World("S . . G", mover=[(2, 0)])     # στέκεται: το R2 πέφτει πάνω της
        self.assertEqual(reasons(L.Run(stuck).play([L.move("forward", 3)])), ["box"])
        self.assertTrue(L.check([w], [L.move("forward", 5)])[0])          # μπαίνει εκεί που μόλις έφυγε

    def test_sinking_bridges(self):
        w = L.World("S . = . G", sink=(2, 2))          # 2 δευτερόλεπτα πάνω, 2 κάτω
        self.assertEqual([w.bridges_up(t) for t in range(6)], [True, True, False, False, True, True])
        self.assertTrue(w.bridge_up((1, 0), 3))        # τα άλλα κουτάκια δεν βουλιάζουν
        self.assertFalse(w.bridge_up((2, 0), 3))
        run = L.Run(w)
        run.play([L.move("forward", 4)])               # φτάνει στη γέφυρα τη στιγμή 2: είναι κάτω
        self.assertEqual(run.failure, ((0,), "bridge"))
        self.assertTrue(L.check([w], [L.wait(2), L.move("forward", 4)])[0])     # φτάνει τη στιγμή 4: πάνω
        near = L.World("S = . G", sink=(2, 2))
        self.assertTrue(L.check([near], [L.move("forward", 3)])[0])             # τη στιγμή 1 πάνω, φεύγει
        run = L.Run(near)
        run.play([L.move("forward", 1), L.wait(1), L.move("forward", 2)])
        self.assertEqual(run.failure, ((1,), "bridge"))  # περιμένει πάνω στη γέφυρα και βουλιάζει
        later = L.World("S . = . G", sink=(2, 2, 2))   # ο κύκλος έχει ήδη προχωρήσει 2 δευτερόλεπτα
        self.assertEqual([later.bridges_up(t) for t in range(4)], [False, False, True, True])
        self.assertTrue(L.check([later], [L.move("forward", 4)])[0])


class ProgramEditTests(unittest.TestCase):
    def prog(self):
        return [L.move("forward", 2), L.repeat(3, L.move(), L.turn("right")), L.turn("left")]

    def test_count_walk_get(self):
        p = self.prog()
        self.assertEqual(L.count(p), 5)
        self.assertEqual([path for path, _ in L.walk(p)], [(0,), (1,), (1, 0, 0), (1, 0, 1), (2,)])
        self.assertEqual(L.get(p, (1, 0, 1))["op"], "turn")
        self.assertEqual(L.ops(p), {"move", "repeat", "turn"})

    def test_take_takes_the_block_and_everything_below(self):
        p = self.prog()
        chunk = L.take(p, (1, 0, 0))
        self.assertEqual([n["op"] for n in chunk], ["move", "turn"])
        self.assertEqual(L.count(p), 3)
        self.assertTrue(L.insert(p, (), 0, chunk))
        self.assertEqual([n["op"] for n in p], ["move", "turn", "move", "repeat", "turn"])

    def test_nothing_snaps_under_forever(self):
        p = [L.move(), L.forever(L.turn())]
        self.assertFalse(L.can_insert(p, (), 2, [L.move()]))
        self.assertTrue(L.can_insert(p, (1, 0), 1, [L.move()]))
        self.assertFalse(L.can_insert(p, (), 0, [L.forever()]))      # «για πάντα» μόνο στο τέλος
        self.assertTrue(L.can_insert([L.move()], (), 1, [L.forever()]))
        self.assertEqual(L.append_spot(p), ((1, 0), 1))               # κλικ: μπαίνει μέσα στο «για πάντα»
        self.assertEqual(L.append_spot([L.move()]), ((), 1))

    def test_fields_and_choices(self):
        for op, node in (("move", L.move()), ("turn", L.turn()), ("led", L.led()), ("wait", L.wait()),
                         ("until", L.until()), ("repeat", L.repeat()), ("if", L.if_else()), ("go", L.go())):
            for field in L.FIELDS[op]:
                if field:
                    self.assertIn(node[field], L.choices(node, field), (op, field))
        self.assertEqual(L.choices(L.turn(), "dir"), ("right", "left"))
        self.assertEqual(L.choices(L.repeat(), "n")[-1], 10)
        self.assertIn(15, L.CM_CHOICES)
        self.assertIn(35, L.CM_CHOICES)


# ================================================================== πίστες
class LevelTests(unittest.TestCase):
    def test_levels_are_valid(self):
        self.assertEqual(LEVEL_COUNT, 20)
        modes = [lv["mode"] for lv in levels.LEVELS]
        self.assertEqual(modes[:3], ["see", "see", "see"])        # κίνηση, μία στροφή, πίσω
        self.assertEqual(set(modes), {"see", "fix", "write"})
        for n, lv in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                ws = worlds_of(lv)
                self.assertTrue(ws)
                self.assertGreaterEqual(lv["limit"], 1)
                self.assertTrue(lv["title"])
                if lv["mode"] == "see":
                    self.assertNotIn("palette", lv)
                    self.assertTrue(L.ops(lv["solution"]) <= {"move", "turn"})
                elif "palette" not in lv:                # «Διόρθωσε» χωρίς Εντολές: μόνο ▾ και αριθμοί
                    self.assertEqual(lv["mode"], "fix")
                    self.assertEqual([p for p, _ in L.walk(lv["program"])], [p for p, _ in L.walk(lv["solution"])])
                    self.assertEqual([n["op"] for _, n in L.walk(lv["program"])],
                                     [n["op"] for _, n in L.walk(lv["solution"])])
                else:
                    pal = {node["op"] for node in lv["palette"]}
                    self.assertTrue(L.ops(lv["solution"]) <= pal, "η λύση θέλει εντολή που δεν υπάρχει")
                    self.assertEqual(len(pal), len(lv["palette"]))
                if lv["mode"] == "fix":
                    self.assertIn("program", lv)
                elif not lv.get("keys"):                  # το τηλεκοντρόλ ξεκινά με το «μπροστά» έτοιμο
                    self.assertNotIn("program", lv)
                for w in ws:
                    self.assertIsNone(w.blocked(w.start, None))
                    if w.line:                            # η μαύρη γραμμή: κουτάκι κουτάκι, μέσα στον χάρτη
                        self.assertTrue(all(c in w.cells for c in w.line))
                        for a, b in zip(w.line, w.line[1:]):
                            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
                        self.assertEqual(len(set(w.line)), len(w.line))
                    self.assertLessEqual(w.cols, 9)
                    self.assertLessEqual(w.rows, 6)

    def test_every_level_can_be_solved_within_its_limit(self):
        """Ο λύτης βρίσκει δρόμο σε κάθε χάρτη, και η λύση της πίστας πετυχαίνει σε όλους τους χάρτες,
        με όλους τους κρυστάλλους, μέσα στο όριο εντολών (3 αστέρια)."""
        for n, lv in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                ws = worlds_of(lv)
                acts = straight_actions(ws)
                for w in ws:
                    self.assertIsNotNone(solve(w, acts), "ο χάρτης δεν λύνεται")
                self.assertEqual(L.check(ws, lv["solution"]), (True, True))
                self.assertLessEqual(L.count(lv["solution"]), lv["limit"])

    def test_limits_are_the_shortest_program(self):
        """Χωρίς βρόχους και αισθητήρα, το όριο είναι ακριβώς το πιο σύντομο πρόγραμμα
        (εκτός από όσες πίστες ο δάσκαλος ζήτησε πιο εύκολα 3 αστέρια: EASIER, πόσες εντολές παραπάνω)."""
        EASIER = {10: 2}                               # οι γέφυρες που βουλιάζουν: 8 αντί για 6
        for n, lv in enumerate(levels.LEVELS, 1):
            if lv["mode"] == "fix" or L.ops(lv["solution"]) & {"repeat", "forever", "if", "until", "go", "line",
                                                                "key"}:
                continue
            with self.subTest(level=n):
                ws = worlds_of(lv)
                best = solve(ws[0], straight_actions(ws))
                self.assertEqual(len(best) + EASIER.get(n, 0), lv["limit"])

    def test_loop_levels_need_the_loop(self):
        """Στις πίστες με «επανάλαβε» / «για πάντα», χωρίς βρόχο δεν φτάνουν οι εντολές του ορίου."""
        loops = 0
        for n, lv in enumerate(levels.LEVELS, 1):
            if not L.ops(lv["solution"]) & {"repeat", "forever"}:
                continue
            loops += 1
            with self.subTest(level=n):
                ws = worlds_of(lv)
                for w in ws:
                    best = solve(w, straight_actions(ws), max_blocks=lv["limit"])
                    self.assertIsNone(best, "βγαίνει και χωρίς βρόχο")
        self.assertGreaterEqual(loops, 4)

    def test_fix_levels_have_one_mistake(self):
        for n, lv in enumerate(levels.LEVELS, 1):
            if lv["mode"] != "fix":
                continue
            with self.subTest(level=n):
                ws = worlds_of(lv)
                self.assertFalse(L.check(ws, lv["program"])[0], "το έτοιμο πρόγραμμα δεν έχει λάθος")
                self.assertTrue(one_edit_apart(lv["program"], lv["solution"]))
                self.assertEqual(L.count(lv["solution"]), lv["limit"])

    def test_first_levels_order(self):
        """Η σειρά που ζήτησε ο δάσκαλος: Δες (κίνηση, μία στροφή, πίσω), τέσσερις εύκολες Διόρθωσε
        χωρίς Εντολές (αριθμός, στροφή, περίμενε, μπροστά/πίσω) και μετά το πρώτο Γράψε."""
        lv = levels.LEVELS
        self.assertEqual([x["mode"] for x in lv[:8]], ["see"] * 3 + ["fix"] * 4 + ["write"])
        self.assertEqual(L.ops(lv[0]["solution"]), {"move"})
        self.assertEqual([n["op"] for n in lv[1]["solution"]].count("turn"), 1)
        self.assertIn(L.move("back", 1), lv[2]["solution"])
        for i in range(3, 7):
            self.assertNotIn("palette", lv[i])
        self.assertEqual([n["op"] for n in lv[4]["program"]].count("turn"), 1)     # μία στροφή, η λάθος
        self.assertIn("wait", L.ops(lv[5]["solution"]))
        self.assertTrue(lv[5].get("bug"))
        self.assertIn(L.move("back", 2), lv[6]["program"])                          # «πίσω» αντί για «μπροστά»
        self.assertEqual(lv[7]["solution"], [L.move("forward", 6)])                # το πρώτο «Γράψε»: μία ευθεία
        self.assertEqual([n["op"] for n in lv[7]["palette"]], ["move"])
        self.assertEqual(lv[8]["mode"], "write")                                  # και μετά με μία στροφή

    def test_every_level_has_one_map(self):
        """Ο δάσκαλος ζήτησε έναν χάρτη σε κάθε πίστα: όταν ο χάρτης άλλαζε σε κάθε «Πάμε», τα παιδιά μπερδεύονταν."""
        for n, lv in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                self.assertEqual(len(lv["maps"]), 1)

    def test_sinking_bridges_level_needs_waiting(self):
        """Πίστα 10: ο ίδιος δρόμος χωρίς αναμονή πέφτει σε βυθισμένη γέφυρα· με «περίμενε 1, 2 ή 3» περνά.
        (Υπάρχει κι ένα κόλπο χωρίς «περίμενε»: μισή στροφή και όλος ο δρόμος με την όπισθεν.)"""
        lv = levels.LEVELS[9]
        self.assertTrue(lv.get("sink"))
        self.assertEqual(lv["solution"][0], L.wait(1))
        ws = worlds_of(lv)
        route = lv["solution"][1:]
        run = L.Run(ws[0])
        run.play(route)
        self.assertEqual(run.failure[1], "bridge")
        for n in (1, 2, 3):
            self.assertEqual(L.check(ws, [L.wait(n)] + route), (True, True))
        self.assertFalse(L.check(ws, [L.wait(4)] + route)[0])

    def first_failure(self, ws, program):
        for w in ws:
            run = L.Run(w)
            run.play(program)
            if run.failure:
                return run.failure[0]
        return None

    def test_blame_finds_the_block_to_fix_in_fix_levels(self):
        """Κόκκινη γίνεται η εντολή που διαφέρει από τη λύση, όχι εκείνη όπου σταμάτησε το R2."""
        for n, lv in enumerate(levels.LEVELS, 1):
            if lv["mode"] != "fix":
                continue
            with self.subTest(level=n):
                ws = worlds_of(lv)
                given, sol = lv["program"], lv["solution"]
                found = L.blame(ws, given, self.first_failure(ws, given), sol)
                a, b = list(L.walk(given)), list(L.walk(sol))
                if len(a) != len(b):                 # λείπει εντολή: κανένα πεδίο δεν φτάνει
                    self.assertIsNone(found)
                    continue
                wrong = next(pa for (pa, na), (_, nb) in zip(a, b) if na != nb and na["op"] == nb["op"]
                             and any(na[k] != nb[k] for k in na if k not in ("body", "then", "else")))
                self.assertEqual(found[0], wrong)

    def test_blame_finds_one_wrong_field_in_any_solution(self):
        """Ένα λάθος πεδίο σε οποιαδήποτε λύση: κόκκινο γίνεται ακριβώς αυτό το μπλοκ."""
        for n, lv in enumerate(levels.LEVELS, 1):
            ws, sol = worlds_of(lv), lv["solution"]
            for path, node in L.walk(sol):
                for field in L.FIELDS[node["op"]]:
                    if not field:
                        continue
                    other = next(v for v in L.choices(node, field) if v != node[field])
                    prog = L.clone(sol)
                    L.get(prog, path)[field] = other
                    if L.check(ws, prog)[0]:
                        continue
                    with self.subTest(level=n, block=path, field=field):
                        found = L.blame(ws, prog, self.first_failure(ws, prog), sol)
                        self.assertEqual(found, (path, field))


# ================================================================ όψη μπλοκ
class BlockLookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((10, 10))

    def words(self, node):
        from games.program import code
        cat, kind, head, mid = code.look(node)
        out = []

        def walk(parts):
            for k, v in parts:
                if k in ("round", "hex"):
                    walk(v)
                elif k != "color":
                    out.append(v)
        walk(head)
        if mid:
            walk(mid)
        return cat, kind, " ".join(out)

    def test_words_are_the_mind_plus_words(self):
        self.assertEqual(self.words(L.move("back", 2)),
                         ("r2", "stack", "Κινήσου πίσω με ταχύτητα μικρή για 2 δευτερόλεπτα"))
        self.assertEqual(self.words(L.turn("left", 1)), ("r2", "stack", "Στρίψε αριστερά για 1 δευτερόλεπτα"))
        self.assertEqual(self.words(L.go()), ("r2", "stack", "Κινήσου μπροστά με ταχύτητα μικρή"))
        self.assertEqual(self.words(L.stop()), ("r2", "stack", "Σταμάτησε"))
        self.assertEqual(self.words(L.follow("on")), ("r2", "stack", "Ακολούθησε τη μαύρη γραμμή Ενεργοποίηση"))
        self.assertEqual(self.words(L.key("up_arrow")), ("event", "hat", "όταν πατηθεί πλήκτρο πάνω βέλος"))
        self.assertEqual(self.words(L.key("left_arrow")), ("event", "hat", "όταν πατηθεί πλήκτρο αριστερό βέλος"))
        self.assertEqual(self.words(L.follow("off")), ("r2", "stack", "Ακολούθησε τη μαύρη γραμμή Απενεργοποίηση"))
        self.assertEqual(self.words(L.led("blue")),
                         ("r2", "stack", "Neopixel Led στο pin D12 , Όλα με χρώμα και φωτεινότητα 50"))
        self.assertEqual(self.words(L.wait(1)), ("control", "stack", "περίμενε 1 δευτερόλεπτα"))
        self.assertEqual(self.words(L.until(15)),
                         ("control", "stack", "περίμενε ώσπου Διάβασε απόσταση (cm) < 15"))
        self.assertEqual(self.words(L.repeat(10)), ("control", "c", "επανάλαβε 10"))
        self.assertEqual(self.words(L.forever()), ("control", "forever", "για πάντα"))
        self.assertEqual(self.words(L.if_else(20)),
                         ("control", "e", "εάν Διάβασε απόσταση (cm) < 20 τότε αλλιώς"))

    def test_every_field_can_be_clicked(self):
        from games.program import code
        st = code.style(0.8)
        for node in (L.move(), L.turn(), L.go(), L.led(), L.wait(), L.until(), L.repeat(), L.if_else()):
            cat, _, head, _ = code.look(node)
            boxes = code.field_boxes(st, head, cat)
            self.assertEqual(len(boxes), len(L.FIELDS[node["op"]]), node["op"])
            xs = [r.x for _, r in boxes]
            self.assertEqual(xs, sorted(xs))
            self.assertTrue(all(r.right <= st.block_width(head, cat) for _, r in boxes))

    def test_c_shapes(self):
        from core import blocks
        from games.program import code
        st = code.style(0.8)
        items, h, spots = code.layout(st, [L.repeat(4, L.move(), L.turn())], 0, 0)
        self.assertEqual([it.path for it in items], [(0,), (0, 0, 0), (0, 0, 1)])
        loop = items[0]
        self.assertEqual(len(loop.segs), 3)
        self.assertAlmostEqual(loop.segs[1], items[1].segs[0] + items[2].segs[0])
        self.assertTrue(loop.arrow and loop.tab)
        img, sil = st.shape(loop.cat, loop.segs, loop.rows, loop.tab, loop.arrow)
        self.assertGreater(img.get_height(), h - 1)
        # θέσεις κουμπώματος: πάνω και κάτω από το «επανάλαβε», και 3 μέσα στο στόμα του
        self.assertEqual(sorted((w, i) for w, i, _, _ in spots), [((), 0), ((), 1), ((0, 0), 0), ((0, 0), 1),
                                                                  ((0, 0), 2)])
        items, _, _ = code.layout(st, [L.forever(L.if_else(15, [L.turn()], [L.move()]))], 0, 0)
        self.assertFalse(items[0].tab)                 # κάτω από το «για πάντα» δεν κουμπώνει τίποτα
        self.assertEqual(len(items[1].segs), 5)
        hexed = st.arm_h(code.look(L.until())[2])
        self.assertGreater(hexed, st.arm_h(code.look(L.wait())[2]))   # με εξάγωνο είναι πιο ψηλό
        self.assertEqual(blocks.CATS["control"][0], blocks.CONTROL)


# ================================================================== οθόνη
class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def open(self, n):
        from games.program.scene import ProgramScene
        sc = ProgramScene(self.app, n - 1)
        sc.update(0.02)
        return sc

    def mouse(self, sc, kind, pos):
        types = {"down": pygame.MOUSEBUTTONDOWN, "up": pygame.MOUSEBUTTONUP, "move": pygame.MOUSEMOTION}
        data = {"pos": pos}
        if kind != "move":
            data["button"] = 1
        else:
            data.update(rel=(0, 0), buttons=(1, 0, 0))
        sc.handle_event(pygame.event.Event(types[kind], data))

    def click(self, sc, pos):
        self.mouse(sc, "down", pos)
        self.mouse(sc, "up", pos)

    def drive(self, sc, keys):
        """Πατάει βελάκια (τηλεκοντρόλ), το ένα μετά το άλλο, αφού τελειώσει το προηγούμενο."""
        codes = {"up_arrow": pygame.K_UP, "down_arrow": pygame.K_DOWN, "right_arrow": pygame.K_RIGHT,
                 "left_arrow": pygame.K_LEFT}
        for k in keys:
            sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=codes[k], mod=0))
            for _ in range(600):
                sc.update(1 / 30)
                if sc.source is None and sc.anim is None:
                    break

    def play(self, sc, limit=4000):
        for _ in range(limit):
            sc.update(1 / 30)
            if sc.celebrated or (sc.failure and not sc.busy):
                return
        self.fail("η εκτέλεση δεν τελείωσε")

    def test_menu_has_the_game(self):
        from games import GAMES
        entry = next(g for g in GAMES if g["id"] == "program")
        self.assertEqual(entry["title"], "Προγραμμάτισε")
        self.assertEqual(entry["module"], "games.program")
        from games import program
        surf = pygame.Surface((260, 200), pygame.SRCALPHA)
        program.draw_icon(surf, (130, 87))

    def test_every_level_opens_and_draws(self):
        for n in range(1, LEVEL_COUNT + 1):
            with self.subTest(level=n):
                sc = self.open(n)
                sc.draw(self.app.screen)
                c = sc.code_rect
                self.assertLessEqual(c.bottom, 712)
                self.assertLessEqual(sc.btn_run.rect.bottom, sc.view.rect.top)      # «Πάμε!» πάνω
                if sc.mode == "see":
                    self.assertLessEqual(sc.view.rect.bottom, c.bottom)
                else:                                                               # Αναίρεση / κάδος κάτω
                    self.assertLessEqual(sc.view.rect.bottom, sc.btn_undo.rect.top)
                    self.assertLessEqual(sc.btn_undo.rect.bottom + 4, c.bottom)
                self.assertGreaterEqual(sc.view.rect.h, 150)
                # η οδηγία χωράει ανάμεσα στα κουμπιά
                from core import ui
                self.assertLess(ui.font(20).size(levels.LEVELS[n - 1]["title"])[0] + 120, 860)

    def test_every_solution_wins_in_the_game(self):
        for n in range(1, LEVEL_COUNT + 1):
            with self.subTest(level=n):
                sc = self.open(n)
                sc.program = L.clone(levels.LEVELS[n - 1]["solution"])
                sc._changed()
                sc.run_or_stop()
                if sc.remote:                             # το τηλεκοντρόλ: πατάμε τα βελάκια της πίστας
                    self.drive(sc, levels.LEVELS[n - 1]["drive"])
                self.play(sc, 6000)
                self.assertTrue(sc.celebrated)
                self.assertEqual(sc.stars, [True, True, True])
                self.assertIn(n, self.app.progress.completed("program"))
                sc.draw(self.app.screen)

    def test_given_mistake_turns_the_block_red(self):
        sc = self.open(5)                             # λάθος στροφή: πέφτει στο νερό
        sc.run_or_stop()
        self.assertTrue(sc.busy)
        self.play(sc)
        self.assertEqual(sc.failure[:2], ((2,), "water"))   # σταμάτησε στην κίνηση μετά τη στροφή,
        self.assertEqual(sc.red_block(), (1,))               # αλλά κόκκινη γίνεται η λάθος στροφή
        sc.draw(self.app.screen)
        sc = self.open(4)                             # λάθος αριθμός: τελειώνει νωρίς
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[:2], (None, "end"))
        self.assertEqual(sc.red_block(), (2,))       # «για 1» αντί για 2
        sc.draw(self.app.screen)
        sc = self.open(6)                             # λάθος αναμονή: τη χτυπά η πασχαλίτσα
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[:2], ((2,), "bug"))
        self.assertEqual(sc.red_block(), (1,))       # το «περίμενε 3»
        sc.draw(self.app.screen)
        sc.set_field((1,), "n", 1)                    # διόρθωση: φεύγει το κόκκινο
        self.assertIsNone(sc.red_block())

    def settle(self, sc, limit=600):
        for _ in range(limit):
            sc.update(1 / 30)
            if sc.source is None and sc.anim is None:
                return

    def test_remote_control_in_the_game(self):
        """Το τηλεκοντρόλ: χειριστήριο πάνω, Εντολές, πρόγραμμα. Δίνεται μόνο το «μπροστά»: τα άλλα κουμπιά είναι
        γκρι ώσπου το παιδί να φτιάξει το πρόγραμμά τους. Χωρίς «Πάμε!»: κάθε κουμπί τρέχει το πρόγραμμά του."""
        n = next(i for i, lv in enumerate(levels.LEVELS, 1) if lv.get("keys"))
        self.assertEqual(n, 19)
        sc = self.open(n)
        self.assertTrue(sc.remote)
        self.assertFalse(sc.view.starts)                                     # χωρίς «R2 starts»
        self.assertNotIn(sc.btn_run, sc.active_buttons())                    # χωρίς «Πάμε!»
        self.assertLess(sc.panel.bottom, sc.pal_rect.top)                    # χειριστήριο, Εντολές,
        self.assertLess(sc.pal_rect.bottom, sc.code_rect.top)                # πρόγραμμα
        self.assertEqual(sc.program, [L.key("up_arrow", L.move("forward", 1))])
        self.assertEqual({k: c.enabled for k, c in sc.controls.items()},
                         {"forward": True, "back": False, "left": False, "right": False})
        sc.draw(self.app.screen)
        start = sc.cell
        self.click(sc, sc.controls["back"].rect.center)                      # γκρι: δεν κάνει τίποτα
        self.settle(sc)
        self.assertEqual(sc.cell, start)
        self.assertIn("πρόγραμμα", " ".join(sc.message[0]))
        self.click(sc, sc.controls["forward"].rect.center)                   # το «μπροστά» δουλεύει
        self.settle(sc)
        self.assertEqual(sc.cell, (start[0] + 1, start[1]))
        # το παιδί φτιάχνει το «πίσω»: καπέλο, βελάκι, εντολή
        hat, move = sc.palette.entries[0][2], sc.palette.entries[1][2]
        self.click(sc, hat.center)
        sc.draw(self.app.screen)
        from games.program import code
        item = sc.view.item((1,))                                           # το ▾ του νέου καπέλου
        box = code.field_boxes(sc.view.st, item.rows[0], item.cat)[0][1]
        box = box.move(round(item.x), round(item.y + item.segs[0] / 2 - sc.view.scroll))
        self.click(sc, box.center)
        self.assertEqual(sc.popup.kind, "menu")                              # λίστα με λέξεις, όχι αριθμητικό
        self.assertEqual([sc.popup.words[o] for o in sc.popup.options],
                         ["πάνω βέλος", "κάτω βέλος", "δεξί βέλος", "αριστερό βέλος"])
        sc.draw(self.app.screen)
        self.click(sc, dict(sc.popup.cells)["down_arrow"].center)
        self.assertEqual(sc.program[1]["key"], "down_arrow")
        sc.update(1 / 30)
        self.assertFalse(sc.controls["back"].enabled)                      # καπέλο χωρίς εντολή: ακόμα γκρι
        self.click(sc, move.center)
        sc.set_field((1, 0, 0), "dir", "back")
        sc.update(1 / 30)
        self.assertTrue(sc.controls["back"].enabled)
        self.press(sc, "back")                                               # τώρα δουλεύει
        self.settle(sc)
        self.assertEqual(sc.cell, start)
        sc.draw(self.app.screen)
        # με όλο το τηλεκοντρόλ φτάνει στον φορτιστή: 3 αστέρια
        sc.program = L.clone(levels.LEVELS[n - 1]["solution"])
        sc._changed()
        sc.restart()                                                         # το R2 στην αρχή, το πρόγραμμα μένει
        self.assertEqual(sc.program, levels.LEVELS[n - 1]["solution"])
        self.assertEqual(sc.cell, sc.world.start)
        self.drive(sc, levels.LEVELS[n - 1]["drive"])
        self.play(sc)
        self.assertTrue(sc.celebrated)
        self.assertEqual(sc.stars, [True, True, True])
        sc = self.open(n)                               # στο νερό: μήνυμα, το R2 μένει εκεί και συνεχίζει
        sc.program = L.clone(levels.LEVELS[n - 1]["solution"])
        sc._changed()
        self.drive(sc, ["right_arrow", "up_arrow"])
        self.assertEqual(sc.cell, sc.world.start)
        self.assertIsNone(sc.failure)
        self.drive(sc, ["left_arrow", "up_arrow"])
        self.assertEqual(sc.cell, (sc.world.start[0] + 1, sc.world.start[1]))
        sc.draw(self.app.screen)

    def test_line_follow_in_the_game(self):
        sc = self.open(17)
        self.assertTrue(sc.locked)
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[1], "end")          # «Απενεργοποίηση»: το R2 δεν ξεκινά
        self.assertEqual(sc.red_block(), (0,))
        sc.draw(self.app.screen)
        from games.program import code
        item = sc.view.item((0,))
        box = [r for (_, r), name in zip(code.field_boxes(sc.view.st, item.rows[0], item.cat), L.FIELDS["line"])
               if name][0].move(round(item.x), round(item.y + item.segs[0] / 2 - sc.view.scroll))
        self.click(sc, box.center)                      # το ▾ ανοίγει μενού με τις δύο επιλογές
        self.assertEqual((sc.popup.kind, tuple(sc.popup.options)), ("menu", ("on", "off")))
        sc.draw(self.app.screen)
        sc.popup = None
        sc.set_field((0,), "mode", "on")
        sc.run_or_stop()
        self.play(sc)
        self.assertTrue(sc.celebrated)

    def test_toolbox_moves_in_the_game(self):
        sc = self.open(14)
        self.assertEqual(sc.box_pose()[:2], (3.5, 1.5))
        sc.run_or_stop()
        for _ in range(60):
            sc.update(1 / 30)
        self.assertGreater(sc.box_pose()[0], 3.5)        # προχωρά μπροστά από το R2
        sc.draw(self.app.screen)
        self.play(sc)
        self.assertEqual(sc.failure[1], "end")          # «< 35»: σταματά πριν τον φορτιστή
        self.assertEqual(sc.red_block(), (1,))
        sc.set_field((1,), "cm", 15)
        sc.run_or_stop()
        self.play(sc)
        self.assertTrue(sc.celebrated)

    def test_bridge_sinks_in_the_game(self):
        sc = self.open(10)
        from games.program import art
        self.assertEqual(art.bridge_height(sc.world, sc.sim_t), 1.0)       # πριν το «Πάμε»: πάνω
        sc.program = L.clone(levels.LEVELS[9]["solution"][1:])           # χωρίς «περίμενε»
        sc._changed()
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[1], "bridge")
        self.assertEqual(art.bridge_height(sc.world, sc.sim_t), 0.0)       # φαίνεται βυθισμένη
        sc.draw(self.app.screen)
        sc.program.insert(0, L.wait(1))
        sc._changed()
        sc.run_or_stop()
        self.play(sc)
        self.assertTrue(sc.celebrated)

    def test_fix_levels_have_no_commands_and_locked_blocks(self):
        fix = [n for n, lv in enumerate(levels.LEVELS, 1) if lv["mode"] == "fix"]
        self.assertEqual(fix, [4, 5, 6, 7, 11, 14, 15, 16, 17])
        for n in fix:                                 # όλες οι «Διόρθωσε»: διόρθωση, όχι προσθήκη
            with self.subTest(level=n):
                sc = self.open(n)
                self.assertTrue(sc.locked)
                self.assertIsNone(sc.palette)
                self.assertNotIn(sc.btn_trash, sc.active_buttons())          # δεν σβήνεται όλο το πρόγραμμα
                self.assertIn(sc.btn_undo, sc.active_buttons())
                sc.draw(self.app.screen)
                before = L.clone(sc.program)
                r = sc.view.screen_rect((0,))                                  # σύρσιμο του 1ου μπλοκ έξω
                self.mouse(sc, "down", (r.x + 10, r.centery))
                self.mouse(sc, "move", (r.x + 30, r.centery - 40))
                self.mouse(sc, "move", (sc.panel.centerx, sc.panel.centery))
                self.mouse(sc, "up", (sc.panel.centerx, sc.panel.centery))
                self.assertIsNone(sc.drag)
                self.assertEqual(sc.program, before)                           # τα μπλοκ έμειναν στη θέση τους
        self.assertFalse(self.open(8).locked)                                 # το πρώτο «Γράψε» έχει Εντολές

    def test_fix_a_number_with_the_pad(self):
        sc = self.open(4)
        sc.draw(self.app.screen)
        from games.program import code
        item = sc.view.item((2,))
        boxes = [r for (_, r), name in zip(code.field_boxes(sc.view.st, item.rows[0], item.cat), L.FIELDS["move"])
                 if name == "n"]
        box = boxes[0].move(round(item.x), round(item.y + item.segs[0] / 2 - sc.view.scroll))
        self.click(sc, box.center)
        self.assertIsNotNone(sc.popup)
        self.assertEqual(sc.popup.kind, "pad")
        cell = dict(sc.popup.cells)[2]
        self.click(sc, cell.center)
        self.assertIsNone(sc.popup)
        self.assertEqual(sc.program[2]["n"], 2)
        sc.run_or_stop()
        self.play(sc)
        self.assertTrue(sc.celebrated)
        sc.undo()                                      # το «Μπράβο» κλειδώνει την αναίρεση
        self.assertEqual(sc.program[2]["n"], 2)

    def test_click_and_drag_blocks(self):
        sc = self.open(9)                             # «Γράψε» με Κινήσου και Στρίψε
        move_entry, turn_entry = sc.palette.entries[0][2], sc.palette.entries[1][2]
        self.click(sc, move_entry.center)              # κλικ: μπαίνει στο τέλος
        self.click(sc, move_entry.center)
        self.assertEqual([n["op"] for n in sc.program], ["move", "move"])
        sc.undo()
        self.assertEqual(len(sc.program), 1)
        # σύρσιμο ενός «Στρίψε» πάνω από το πρώτο μπλοκ
        start = (turn_entry.x + 20, turn_entry.centery)
        self.mouse(sc, "down", start)
        top = sc.view.screen_rect((0,))
        for k in range(1, 6):
            self.mouse(sc, "move", (start[0] + (top.x + 20 - start[0]) * k / 5,
                                    start[1] + (top.y + 4 - start[1]) * k / 5))
        self.assertIsNotNone(sc.drag)
        self.assertEqual(sc.preview, ((), 0))
        sc.draw(self.app.screen)                       # με τη γκρι σκιά
        self.mouse(sc, "up", (top.x + 20, top.y + 4))
        self.assertEqual([n["op"] for n in sc.program], ["turn", "move"])
        # σέρνω το πρώτο μπλοκ (και ό,τι είναι από κάτω) έξω, στις Εντολές: σβήνονται
        r = sc.view.screen_rect((0,))
        self.mouse(sc, "down", (r.x + 10, r.centery))
        self.mouse(sc, "move", (r.x + 30, r.centery - 40))
        self.mouse(sc, "move", (sc.panel.centerx, sc.panel.centery))
        self.mouse(sc, "up", (sc.panel.centerx, sc.panel.centery))
        self.assertEqual(sc.program, [])
        sc.undo()
        self.assertEqual([n["op"] for n in sc.program], ["turn", "move"])

    def press(self, sc, name, frames=30):
        """Κλικ σε ένα κουμπί του χειριστηρίου (πίστες «Δες»)."""
        pos = sc.controls[name].rect.center
        self.mouse(sc, "down", pos)
        self.mouse(sc, "up", pos)
        for _ in range(frames):
            sc.update(1 / 30)

    def test_see_mode_writes_and_merges(self):
        sc = self.open(1)
        self.press(sc, "left")
        self.press(sc, "forward")                      # δέντρο: χτυπά και δεν γράφεται
        self.assertEqual(sc.program, [L.turn("left", 1)])
        self.assertIsNone(sc.failure)
        self.press(sc, "right")
        for _ in range(3):
            self.press(sc, "forward", 1)               # πατήματα που περιμένουν τη σειρά τους
        for _ in range(60):
            sc.update(1 / 30)
        self.assertEqual(sc.program, [L.turn("left", 1), L.turn("right", 1), L.move("forward", 3)])
        self.press(sc, "forward", 60)
        self.assertEqual(sc.program[-1], L.move("forward", 4))
        self.assertTrue(sc.drove_home)
        self.assertTrue(sc.btn_run.pulse)
        sc.draw(self.app.screen)
        sc.run_or_stop()                               # «Πάμε»: το R2 τα κάνει μόνο του από την αρχή
        self.assertTrue(sc.busy)
        self.play(sc)
        self.assertTrue(sc.celebrated)
        self.assertEqual(sc.stars[2], False)           # 3 εντολές αντί για 1
        sc.draw(self.app.screen)

    def test_see_mode_ignores_arrow_keys(self):
        for number in (1, 2, 3):                       # οι πίστες «Δες»: μόνο τα κουμπιά οδηγούν το R2
            sc = self.open(number)
            self.assertEqual(levels.LEVELS[number - 1]["mode"], "see")
            start = sc.robot_pose()
            for k in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0))
                sc.handle_event(pygame.event.Event(pygame.KEYUP, key=k, mod=0))
                for _ in range(30):
                    sc.update(1 / 30)
            self.assertEqual(sc.program, [])
            self.assertFalse(sc.busy)
            self.assertEqual(sc.robot_pose(), start)

    def test_one_map_in_fix_levels(self):
        sc = self.open(16)                             # «Διόρθωσε» με αισθητήρα: πάντα ο ίδιος χάρτης
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[1], "water")
        sc.set_field((1,), "cm", 15)
        sc.run_or_stop()
        self.assertEqual(sc.variant, 0)
        self.play(sc, 8000)
        self.assertTrue(sc.celebrated)

    def test_map_changes_after_a_failure(self):
        """Ο κώδικας για πίστα με πολλούς χάρτες μένει (σήμερα καμία πίστα δεν έχει): δοκιμή με 3 χάρτες."""
        maps = ["""
         S . c . . . #
         ~ G ~ ~ ~ . ~
         # . . c . . ~
         ~ ~ ~ ~ ~ # ~
         """, """
         S c . . # ~ ~
         ~ ~ ~ . ~ ~ ~
         ~ G ~ c ~ ~ ~
         # . . . ~ ~ ~
         ~ ~ ~ # ~ ~ ~
         """, """
         S . . c . # ~
         ~ ~ ~ ~ . ~ ~
         ~ ~ ~ ~ c ~ ~
         ~ G . . . ~ ~
         ~ ~ ~ ~ # ~ ~
         """]
        sc = self.open(20)
        sc.worlds = [L.World(m) for m in maps]
        sc.boards = [None] * len(maps)
        sc.program = [L.forever(L.if_else(15, [L.turn("left")], [L.move("forward", 1)]))]
        sc._changed()
        sc.run_or_stop()
        self.play(sc)
        self.assertEqual(sc.failure[1], "edge")
        self.assertEqual(sc.variant, 0)                # το R2 μένει στον χάρτη όπου έκανε λάθος
        self.assertEqual(sc.red_block(), (0, 0, 0, 0, 0))
        sc.set_field((0, 0, 0, 0, 0), "dir", "right")
        self.assertIsNone(sc.failure)
        sc.run_or_stop()
        self.assertEqual(sc.variant, 1)                # νέο «Πάμε»: άλλος δρόμος
        self.play(sc, 12000)
        self.assertTrue(sc.celebrated)

    def test_stop_button_and_empty_program(self):
        sc = self.open(8)
        sc.run_or_stop()                               # κενό πρόγραμμα: τίποτα
        self.assertFalse(sc.busy)
        sc.program = L.clone(levels.LEVELS[7]["solution"])
        sc._changed()
        sc.run_or_stop()
        for _ in range(20):
            sc.update(1 / 30)
        sc.draw(self.app.screen)
        self.click(sc, sc.btn_run.rect.center)          # «Σταμάτα»
        self.assertFalse(sc.busy)
        self.assertEqual(sc.cell, sc.world.start)

    def test_flag_is_above_the_program_and_glows_when_waiting(self):
        for n in (1, 6, 15):
            with self.subTest(level=n):
                sc = self.open(n)
                self.assertLessEqual(sc.btn_run.rect.bottom, sc.view.rect.top)     # όπως στο Scratch
                self.assertTrue(sc.code_rect.contains(sc.btn_run.rect))
        sc = self.open(8)
        sc.append(L.move())
        sc.update(1 / 30)
        self.assertFalse(sc.btn_run.pulse)
        for _ in range(90):                            # λίγα δευτερόλεπτα χωρίς αλλαγή: λάμπει
            sc.update(1 / 30)
        self.assertTrue(sc.btn_run.pulse)
        sc.run_or_stop()
        sc.update(1 / 30)
        self.assertFalse(sc.btn_run.pulse)

    def test_drag_into_a_loop_and_bad_drop_spot(self):
        sc = self.open(12)
        sc.append(L.repeat(10))
        sc.append(L.move())                            # κλικ: μπαίνει κάτω από το «επανάλαβε»
        self.assertEqual([n["op"] for n in sc.program], ["repeat", "move"])
        sc.draw(self.app.screen)
        spot = sc.view.nearest_spot(sc.program, [L.turn()], (sc.view.item((0,)).x + 30,
                                                            sc.view.item((0,)).y + sc.view.item((0,)).segs[0]))
        self.assertEqual(spot, ((0, 0), 0))            # μέσα στο στόμα
        sc.program = [L.forever()]
        sc._changed()
        sc.append(L.move())
        self.assertEqual(sc.program, [L.forever(L.move())])


if __name__ == "__main__":
    unittest.main()
