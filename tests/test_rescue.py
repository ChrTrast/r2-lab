"""Έλεγχοι για τις «Αποστολές Διάσωσης» (το δάσος). Τρέξε:  py -m unittest discover tests"""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.rescue import net, sim as S, world as W  # noqa: E402

TEST_DISC = 47931          # άλλες θύρες από το παιχνίδι, για να μη μπερδευτούν με ανοιχτό μάθημα
TEST_GAME = 47932


def run_auto(forest, limit=400.0, dt=0.05):
    for k in forest.plots:
        forest.set_auto(k, True)
    t = 0.0
    while not forest.done and t < limit:
        forest.tick(dt)
        t += dt
    return forest.done


def first_plot_of_kind(data, kind_test):
    return next(p for p in data["plots"] if kind_test(p))


# ================================================================ το δάσος
class TestWorld(unittest.TestCase):
    def test_team_sizes(self):
        for n in range(1, 30):
            sizes = W.team_sizes(n)
            m = max(W.MIN_PCS, min(W.MAX_PCS, n))
            self.assertEqual(sum(sizes), m, n)
            self.assertTrue(all(2 <= s <= 5 for s in sizes), (n, sizes))
            if len(sizes) > 1:
                self.assertTrue(all(s >= 3 for s in sizes), (n, sizes))
        self.assertEqual(W.team_sizes(2), [2])
        self.assertEqual(W.team_sizes(12), [4, 4, 4])
        self.assertEqual(W.team_sizes(25), [5, 5, 5, 5, 5])

    def test_every_level_builds_and_solves(self):
        for lid in ("1", "2", "3"):
            for n in (2, 3, 4, 5, 6, 9, 13, 25):
                d = W.build(lid, n, seed=1)
                self.assertEqual(len(d["plots"]), n)
                self.assertEqual(len(d["grid"]), d["H"])
                self.assertTrue(all(len(row) == d["W"] for row in d["grid"]))
                for p in d["plots"]:
                    self.assertGreaterEqual(len(p["solution"]), 2, (lid, n, p["k"]))

    def test_level_features(self):
        d = W.build("1", 8, 0)
        self.assertEqual(len(d["fires"]), 0)
        self.assertEqual(len(d["gaps"]), 8 - len(d["teams"]))         # ένα άνοιγμα ανάμεσα σε διαδοχικά οικόπεδα
        self.assertEqual(len(d["meadows"]), len(d["teams"]))
        d = W.build("2", 8, 0)
        self.assertEqual(len(d["fires"]), len(d["teams"]))
        self.assertEqual(len(d["sources"]), len(d["teams"]))
        self.assertEqual(d["seesaws"], [])
        d = W.build("3", 8, 0)
        self.assertEqual(len(d["seesaws"]), 8 - len(d["teams"]))      # ένα κλαδί σε κάθε σύνορο του ποταμιού

    def test_same_seed_same_forest(self):
        a, b = W.build("3", 7, 4), W.build("3", 7, 4)
        self.assertEqual(a["grid"], b["grid"])
        self.assertNotEqual(W.build("3", 7, 5)["grid"], a["grid"])

    def test_build_is_quick(self):
        t = time.time()
        W.build("3", 25, 2)
        self.assertLess(time.time() - t, 5.0)

    def test_answers_are_stripped(self):
        d = W.strip_answers(W.build("2", 4, 0))
        self.assertTrue(all("solution" not in p for p in d["plots"]))


# ================================================================ οι κανόνες
class TestSim(unittest.TestCase):
    def test_autopilot_finishes_every_level(self):
        for lid in ("1", "2", "3"):
            for n in (2, 4, 5, 7, 12):
                f = S.Forest(W.build(lid, n, seed=2))
                self.assertTrue(run_auto(f), (lid, n, f.counts()))
                saved, total, out, fires = f.counts()
                self.assertEqual(saved, total)
                self.assertEqual(out, fires)

    def test_stone_into_river_makes_a_crossing(self):
        f = S.Forest(W.build("1", 2, 0))
        k = 1
        for a in W.build("1", 2, 0)["plots"][0]["solution"]:
            f.act(k, a)
            for _ in range(20):
                f.tick(0.05)
        p = f.plots[k]
        self.assertEqual(f.fixed_at(tuple(p["crossing"])), "x")
        self.assertTrue(any(e[2] == "splash" for e in f.events))

    def test_dam_sends_the_water_on(self):
        d = W.build("2", 3, 0)
        f = S.Forest(d)
        for _ in range(100):
            f.tick(0.05)
        first, last = d["plots"][0], d["plots"][-1]
        self.assertNotIn(tuple(d["fires"][0]["end"]), f.wet)           # χωρίς φράγματα το νερό χάνεται
        for p in d["plots"]:
            s = next(st for st in f.stones if st["home"] == p["k"])
            s["pos"], s["state"] = tuple(p["dam"]), "d"
        f._target = f.flow_target()
        for _ in range(200):
            f.tick(0.05)
        self.assertIn(tuple(d["fires"][0]["end"]), f.wet)
        self.assertTrue(all(fi["out"] for fi in f.fires))
        del first, last

    def test_robot_stays_in_its_plot_and_cannot_pull(self):
        d = W.build("2", 2, 1)
        f = S.Forest(d)
        k = 1
        p = f.plots[k]
        # βάλε το R2 στην άκρη του οικοπέδου, να κοιτάει έξω
        f.robots[k]["pos"] = (p["x0"], p["y0"] + 3)
        f.robots[k]["face"] = W.LEFT
        why = f.passable_robot((p["x0"] - 1, p["y0"] + 3), k)
        self.assertEqual(why, "fence")
        # μια πέτρα πίσω από το R2: το «Πίσω» δεν τη σπρώχνει
        s = f.stones[0]
        s["pos"], s["state"] = (p["x0"] + 1, p["y0"] + 3), "."
        f.grid[p["y0"] + 3][p["x0"] + 1] = "."
        f.robots[k]["face"] = W.LEFT
        before = f.robots[k]["pos"]
        self.assertEqual(f._do(k, "back"), "bump")
        self.assertEqual(f.robots[k]["pos"], before)

    def test_branch_rises_while_someone_stands_on_the_pedal(self):
        d = W.build("3", 2, 0)
        f = S.Forest(d)
        s = f.seesaws[0]
        self.assertFalse(s["up"])
        arm_cell = s["arm"][0]
        self.assertEqual(f.passable_robot(arm_cell, s["to"]), "branch")
        f.robots[s["from"]]["pos"] = s["pedal"]
        f._update_arms()
        self.assertTrue(s["up"])
        self.assertIsNone(f.passable_robot(arm_cell, s["to"]))
        # το R2 του γείτονα κάτω από το κλαδί: δεν πέφτει όσο είναι εκεί
        f.robots[s["to"]]["pos"] = arm_cell
        f.robots[s["from"]]["pos"] = tuple(d["plots"][0]["start"][:2])
        f._update_arms()
        self.assertTrue(s["up"])
        f.robots[s["to"]]["pos"] = tuple(d["plots"][1]["start"][:2])
        f._update_arms()
        self.assertFalse(s["up"])

    def test_reset_brings_robot_and_stones_back(self):
        d = W.build("2", 2, 3)
        f = S.Forest(d)
        k = 1
        for a in d["plots"][0]["solution"]:
            f.act(k, a)
            for _ in range(15):
                f.tick(0.05)
        self.assertTrue(f.plot_done_stones(k))
        f.reset_plot(k)
        x, y, face = d["plots"][0]["start"]
        self.assertEqual(f.robots[k]["pos"], (x, y))
        self.assertEqual(f.robots[k]["face"], face)
        self.assertFalse(f.plot_done_stones(k))
        self.assertEqual(f.rec[k], [])

    def test_driving_writes_the_program(self):
        f = S.Forest(W.build("2", 2, 3))
        for a in ("left", "left", "right"):
            f._do(1, a)
        self.assertEqual(f.rec[1][0], {"op": "turn", "dir": "left", "n": 2})
        self.assertEqual(f.rec[1][1]["dir"], "right")

    def test_snapshot_round_trip(self):
        d = W.build("3", 4, 1)
        host = S.Forest(d)
        for k in host.plots:
            host.set_auto(k, True)
        for _ in range(300):
            host.tick(0.05)
        client = S.Forest(W.strip_answers(d))
        client.apply(host.snapshot())
        self.assertEqual({k: r["pos"] for k, r in client.robots.items()}, {k: r["pos"] for k, r in host.robots.items()})
        self.assertEqual(client.wet, host.wet)
        self.assertEqual([s["up"] for s in client.seesaws], [s["up"] for s in host.seesaws])
        self.assertEqual([(s["pos"], s["state"]) for s in client.stones], [(s["pos"], s["state"]) for s in host.stones])

    def test_animals_ask_the_robot_to_move(self):
        d = W.build("1", 2, 0)
        f = S.Forest(d)
        p = d["plots"][0]
        # το πέρασμα έγινε, αλλά το R2 στέκεται πάνω στον δρόμο των ζώων (στην απέναντι όχθη)
        x, y = p["crossing"]
        st = next(s for s in f.stones if s["home"] == 1)
        st["pos"], st["state"] = (x, y), "x"
        f.robots[1]["pos"] = (x, y)                       # πάνω στο πέρασμα: άλλος δρόμος δεν υπάρχει
        f.robots[1]["queue"].clear()
        for _ in range(30):
            f.tick(0.05)
        self.assertTrue(any(an["wait"] == 1 for an in f.animals))
        f.set_auto(1, True)                               # το αυτόματο R2 κάνει στην άκρη
        for _ in range(200):
            f.tick(0.05)
        self.assertNotEqual(f.robots[1]["pos"], (x, y))


# ================================================================ τα προγράμματα (Διόρθωσε, Γράψε)
PROGRAM_LEVELS = {"4": 1, "5": 2, "6": 3, "7": 1, "8": 2, "9": 2, "10": 3}


def run_programs(forest, progs, limit=200.0):
    forest.start_run(progs)
    t = 0.0
    while forest.run_phase != "end" and t < limit:
        forest.tick(0.05)
        t += 0.05
    return forest.run_results()


class TestPrograms(unittest.TestCase):
    def test_programs_are_short(self):
        for lid, blocks in PROGRAM_LEVELS.items():
            lv = W.level(lid)
            for n in (2, 5, 12, 25):
                d = W.build(lid, n, seed=1)
                for p in d["plots"]:
                    self.assertEqual(len(p["program"]), blocks, (lid, n, p["k"]))
                    if lv["prog"].get("fix"):
                        self.assertEqual(len(p["given"]), blocks)
                        self.assertNotEqual(p["given"], p["program"])
                    else:
                        self.assertIsNone(p["given"])

    def test_right_programs_save_everyone(self):
        for lid in PROGRAM_LEVELS:
            for n in (2, 4, 9):
                d = W.build(lid, n, seed=2)
                f = S.Forest(d)
                res = run_programs(f, {p["k"]: p["program"] for p in d["plots"]})
                self.assertTrue(all(r[0] == "ok" for r in res.values()), (lid, n, res))
                self.assertTrue(f.all_saved() and all(fi["out"] for fi in f.fires), (lid, n, f.counts()))

    def test_given_programs_have_a_mistake(self):
        for lid in ("4", "5", "6"):
            d = W.build(lid, 4, seed=3)
            f = S.Forest(d)
            res = run_programs(f, {p["k"]: p["given"] for p in d["plots"]})
            self.assertFalse(any(r[0] == "ok" for r in res.values()), lid)

    def test_results_name_the_block(self):
        d = W.build("10", 2, seed=1)
        p = d["plots"][0]
        wrong = [dict(nd) for nd in p["program"]]
        wrong[1]["dir"] = "left" if wrong[1]["dir"] == "right" else "right"
        res = net.test_program(d, p["k"], wrong)
        self.assertNotEqual(res[0], "ok")
        self.assertIsNotNone(res[2])
        self.assertTrue(net.program_hint(res))
        self.assertEqual(net.test_program(d, p["k"], p["program"])[0], "ok")
        self.assertEqual(net.test_program(d, p["k"], [])[0], "empty")

    def test_fix_hint_finds_the_smallest_change(self):
        d = W.build("8", 4, seed=8)
        p = d["plots"][1]
        turn, move = p["program"]
        other = "left" if turn["dir"] == "right" else "right"
        cases = [([dict(turn, dir=other), move], "turn", (0,)),
                 ([turn, dict(move, n=move["n"] + 1)], "fewer", (1,)),
                 ([turn, dict(move, n=move["n"] - 1)] if move["n"] > 1 else None, "more", (1,)),
                 ([move], "turn_first", (0,))]
        for prog, kind, path in cases:
            if prog is None:
                continue
            fix = net.program_fix(d, p["k"], prog)
            self.assertEqual(fix[:2], (kind, path), prog)
        self.assertIsNone(net.program_fix(d, p["k"], p["program"]))
        d = W.build("9", 4, seed=9)
        p = d["plots"][1]
        self.assertEqual(net.program_fix(d, p["k"], p["program"][:1])[0], "back_end")   # «και ένα βήμα πίσω»
        d = W.build("5", 4, seed=2)                    # Διόρθωσε: μόνο αλλαγές σε πεδία
        p = d["plots"][1]
        fix = net.program_fix(d, p["k"], p["given"])
        self.assertIn(fix[0], ("more", "fewer", "turn", "turns", "dir"))

    def test_flatten_and_blocks(self):
        prog = [{"op": "move", "dir": "forward", "n": 3}, {"op": "turn", "dir": "left", "n": 1},
                {"op": "repeat", "n": 2, "body": [{"op": "move", "dir": "back", "n": 1}]}, {"op": "wait", "n": 1}]
        acts = [a for a, _ in W.flatten(prog)]
        self.assertEqual(acts, ["forward"] * 3 + ["left", "back", "back", "wait"])
        self.assertEqual(W.to_blocks(["forward", "forward", "left"]),
                         [{"op": "move", "dir": "forward", "n": 2}, {"op": "turn", "dir": "left", "n": 1}])
        self.assertEqual(W.flatten("όχι πρόγραμμα"), [])
        self.assertLessEqual(len(W.flatten([{"op": "repeat", "n": 10, "body": [
            {"op": "repeat", "n": 10, "body": [{"op": "move", "dir": "forward", "n": 9}]}]}])), W.MAX_ACTIONS)


# ================================================================ Αισθητήρες (μπάρες, γραμμή, βράχος)
SENSE_LEVELS = ("11", "12", "13", "14")


class TestSensors(unittest.TestCase):
    def test_levels_build_with_few_blocks(self):
        for lid in SENSE_LEVELS:
            lv = W.level(lid)
            for n in (2, 3, 5, 12, 25):
                d = W.build(lid, n, seed=1)
                for p in d["plots"]:
                    self.assertTrue(1 <= len(p["program"]) <= 3, (lid, n, p["k"]))
                    if lv["prog"].get("fix"):
                        self.assertNotEqual(p["given"], p["program"])
                if lid == "14":
                    want = sum(len(t["plots"]) // 2 for t in d["teams"])
                    self.assertEqual(len(d["rocks"]), want)
                if lid in ("13", "14"):
                    self.assertTrue(all(len(p["line"]) >= 7 for p in d["plots"]))

    def test_right_programs_save_everyone(self):
        for lid in SENSE_LEVELS:
            for n in (2, 3, 5, 9):
                d = W.build(lid, n, seed=2)
                f = S.Forest(d)
                res = run_programs(f, {p["k"]: p["program"] for p in d["plots"]})
                self.assertTrue(all(r == ["ok", None, None] for r in res.values()), (lid, n, res))
                self.assertTrue(f.all_saved() and all(fi["out"] for fi in f.fires), (lid, n, f.counts()))

    def test_given_programs_have_a_mistake(self):
        d = W.build("11", 4, seed=3)
        res = run_programs(S.Forest(d), {p["k"]: p["given"] for p in d["plots"]})
        self.assertTrue(all(r[0] != "ok" or r[1] == "chain" for r in res.values()))
        self.assertNotEqual(res[1][0], "ok")
        for p in d["plots"]:
            self.assertNotEqual(net.test_program(d, p["k"], p["given"])[0], "ok")
            self.assertEqual(net.test_program(d, p["k"], p["program"])[0], "ok")

    def test_the_bar_opens_the_next_bar(self):
        d = W.build("11", 3, seed=0)
        f = S.Forest(d)
        self.assertFalse(any(s["up"] for s in f.seesaws))
        res = run_programs(f, {p["k"]: p["program"] for p in d["plots"]})
        self.assertTrue(all(s["up"] for s in f.seesaws))
        self.assertTrue(all(f.robots[p["k"]]["pos"] == tuple(p["pedal"]) for p in d["plots"]))

    def test_broken_chain_is_not_their_fault(self):
        d = W.build("11", 4, seed=1)
        progs = {p["k"]: p["program"] for p in d["plots"]}
        progs[1] = []
        res = run_programs(S.Forest(d), progs)
        self.assertEqual(res[1][0], "empty")
        self.assertTrue(all(res[k] == ["ok", "chain", None] for k in (2, 3, 4)), res)

    def test_the_rock_needs_two(self):
        d = W.build("14", 2, seed=0)
        a, b = d["plots"]
        f = S.Forest(d)
        res = run_programs(f, {1: a["program"], 2: []})
        self.assertEqual(res[1], ["ok", "partner", None])
        self.assertTrue(all(s["state"] == "." for s in f.stones))
        f = S.Forest(d)
        res = run_programs(f, {1: a["program"], 2: b["program"]})
        self.assertTrue(all(r == ["ok", None, None] for r in res.values()), res)
        self.assertTrue(all(s["state"] == "x" for s in f.stones))
        # στη «Δοκιμή» ο γείτονας σπρώχνει μαζί
        self.assertEqual(net.test_program(d, 1, a["program"])[0], "ok")

    def test_line_sensor(self):
        d = W.build("13", 2, seed=0)
        p = d["plots"][0]
        self.assertEqual(net.test_program(d, 1, [W.line_block()])[:2], ["bump", "noline"])
        self.assertEqual(net.test_program(d, 1, p["program"])[0], "ok")
        self.assertEqual(W.line_next([(0, 0), (1, 0), (1, 1)], (0, 0), W.DOWN), "left")
        self.assertEqual(W.line_next([(0, 0), (1, 0), (1, 1)], (1, 0), W.RIGHT), "right")
        self.assertIsNone(W.line_next([(0, 0), (1, 0)], (1, 0), W.RIGHT))

    def test_until_waits_for_the_sensor(self):
        reads = iter([10, 10, 10, 50, 50])
        steps = list(W.run_steps([W.until_block(">", 20), W.move_block("forward", 2)], lambda kind: next(reads)))
        self.assertEqual([a for a, _ in steps], ["wait", "wait", "wait", "forward", "forward"])
        steps = list(W.run_steps([W.until_block("<", 20)], lambda kind: 50, max_wait=3))
        self.assertEqual(steps[-1][0], "fail:time")
        self.assertEqual(W.node_at([{"op": "repeat", "n": 2, "body": [W.line_block()]}], (0, 0, 0))["op"], "line")

    def test_lesson_checks_a_chain_result(self):
        """«σωστό, η μπάρα δεν άνοιξε» μόνο όταν το πρόγραμμα πετυχαίνει και στη «Δοκιμή»."""
        L = _Box()
        for pc in (10, 11, 12):
            L.add_pc(pc, f"Π{pc}", f"pc{pc}")
        L.start_level("11", seed=4)
        k1, k2, k3 = (L.plot_of(pc) for pc in (10, 11, 12))
        wrong = [dict(nd) for nd in L.forest.plots[k3]["program"]]
        wrong[-1]["n"] += 1
        L.set_program(10, [], True)
        L.set_program(11, L.forest.plots[k2]["program"], True)
        L.set_program(12, wrong, True)
        L.run_now()
        for _ in range(3000):
            L.tick(0.05)
            if L.phase in ("result", "done"):
                break
        self.assertEqual(L.results[k2], ["ok", "chain", None])
        self.assertNotEqual(L.results[k3][0], "ok")


# ================================================================ το μάθημα (χωρίς δίκτυο)
class _Box(net.Lesson):
    def __init__(self):
        super().__init__("Ε1")
        self.sent = []

    def send(self, pc, msg):
        self.sent.append((pc, msg))


class TestLesson(unittest.TestCase):
    def make(self, n=3):
        L = _Box()
        for i in range(n):
            L.add_pc(10 + i, f"Παιδί {i}", f"PC-{i}")
        return L

    def test_plots_follow_the_seats(self):
        L = self.make(3)
        L.seat(10, 5)
        L.start_level("1", seed=1)
        self.assertEqual(L.assign[3], 10)                 # η θέση 5 είναι μετά τις 1 και 2
        self.assertEqual(L.assign[1], 11)
        self.assertTrue(all(pc in L.pcs for pc in L.assign.values()))
        levels = [m for pc, m in L.sent if m["t"] == "level"]
        self.assertEqual(len(levels), 3)
        self.assertTrue(all("solution" not in p for p in levels[0]["data"]["plots"]))

    def test_bots_and_one_pc(self):
        L = self.make(1)
        L.start_level("2", seed=0)
        self.assertEqual(len(L.assign), 2)
        self.assertTrue(L.forest.auto[2])
        self.assertEqual(L.status(2), "bot")

    def test_act_moves_the_robot_and_status(self):
        L = self.make(2)
        L.start_level("2", seed=2)
        k = L.plot_of(10)
        plan = list(L.forest.make_plan(k))
        before = L.forest.robots[k]["pos"], L.forest.robots[k]["face"]
        L.act(10, plan[0])
        L.tick(0.5)
        self.assertNotEqual((L.forest.robots[k]["pos"], L.forest.robots[k]["face"]), before)
        self.assertEqual(L.status(k), "drive")
        L.forest.clock = 500
        L.forest.stats[L.plot_of(11)]["first"] = None
        self.assertEqual(L.status(L.plot_of(11)), "idle")

    def test_drop_pc_gives_autopilot(self):
        L = self.make(2)
        L.start_level("1", seed=0)
        k = L.plot_of(11)
        L.drop_pc(11)
        self.assertTrue(L.forest.auto[k])
        self.assertEqual(L.status(k), "off")

    def test_help_messages(self):
        L = self.make(2)
        L.start_level("3", seed=1)
        k = L.plot_of(10)
        L.sent.clear()
        L.help(k, "hint")
        L.help(k, "route")
        L.help(k, "next")
        L.help(k, "msg", "Μπράβο!")
        kinds = [m["kind"] for pc, m in L.sent if m["t"] == "help"]
        self.assertEqual(kinds, ["hint", "route", "next", "msg"])
        route = [m["data"] for pc, m in L.sent if m.get("kind") == "route"][0]
        self.assertGreaterEqual(len(route), 2)
        nxt = [m["data"] for pc, m in L.sent if m.get("kind") == "next"][0]
        self.assertIn(nxt, W.ACTIONS)
        L.set_auto(k, True)
        self.assertTrue(L.forest.auto[k])

    def test_completed_callback(self):
        L = self.make(2)
        got = []
        L.completed = got.append
        L.start_level("2", seed=1)
        for k in L.forest.plots:
            L.forest.set_auto(k, True)
        for _ in range(4000):
            L.tick(0.05)
            if got:
                break
        self.assertEqual(got, ["2"])
        self.assertTrue(any(m["t"] == "done" for pc, m in L.sent))

    def test_rounds_in_a_program_level(self):
        L = self.make(3)
        got = []
        L.completed = got.append
        L.start_level("8", seed=1)
        self.assertEqual((L.mode, L.phase, L.round), ("write", "plan", 1))
        for pc in (10, 11, 12):
            k = L.plot_of(pc)
            prog = L.forest.plots[k]["program"] if pc != 12 else [{"op": "move", "dir": "forward", "n": 1}]
            L.set_program(pc, prog, True)
        for _ in range(3000):
            L.tick(0.05)
            if L.phase in ("result", "done"):
                break
        self.assertEqual(L.phase, "result")
        self.assertNotEqual(L.results[L.plot_of(12)][0], "ok")
        self.assertEqual(L.status(L.plot_of(12)), "fail")
        L.sent.clear()
        L.help(L.plot_of(12), "blame")
        L.help(L.plot_of(12), "solution")
        kinds = [m["kind"] for pc, m in L.sent if m["t"] == "help"]
        self.assertEqual(kinds, ["blame", "solution"])
        for _ in range(400):
            L.tick(0.05)
            if L.phase == "plan":
                break
        self.assertEqual((L.phase, L.round), ("plan", 2))
        for pc in (10, 11, 12):
            L.set_program(pc, L.programs[L.plot_of(pc)], True)
        for _ in range(3000):
            L.tick(0.05)
            if L.phase == "done":
                break
        self.assertEqual(got, ["8"])

    def test_fix_level_starts_with_the_given_program(self):
        L = self.make(2)
        L.start_level("5", seed=0)
        level = [m for pc, m in L.sent if m["t"] == "level"][0]
        self.assertEqual(level["mode"], "fix")
        self.assertEqual(level["prog"], L.forest.plots[level["k"]]["given"])
        self.assertTrue(all("program" not in p for p in level["data"]["plots"]))
        L.add_time(60)
        self.assertGreater(L.left, L.plan_seconds)

    def test_pause_and_freeze(self):
        L = self.make(2)
        L.start_level("1", seed=0)
        L.pause(True)
        k = L.plot_of(10)
        before = L.forest.robots[k]["pos"]
        L.act(10, "forward")
        L.tick(1.0)
        self.assertEqual(L.forest.robots[k]["pos"], before)
        L.pause(False)
        L.freeze(True)
        self.assertTrue(any(m["t"] == "freeze" and m["on"] for pc, m in L.sent))


# ================================================================ το δίκτυο
class TestNetwork(unittest.TestCase):
    def pump(self, host, clients, seconds=1.0, until=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            host.tick(0.02)
            for c in clients:
                c.poll()
            if until and until():
                return True
            time.sleep(0.005)
        return until() if until else True

    def test_join_drive_and_snapshots(self):
        host = net.Host("Ε2", port=TEST_GAME, disc_port=TEST_DISC)
        try:
            a = net.Client("Ελένη", "127.0.0.1", host.port)
            b = net.Client("Νίκος", "127.0.0.1", host.port)
            self.assertTrue(self.pump(host, [a, b], 4, lambda: len(host.pcs) == 2 and a.state == "lobby"
                                      and b.state == "lobby"))
            self.assertEqual(host.pcs[1]["name"], "Ελένη")
            host.start_level("2", seed=2)
            self.assertTrue(self.pump(host, [a, b], 3, lambda: a.state == "level" and b.state == "level"))
            self.assertEqual((a.k, b.k), (1, 2))
            plan = list(host.forest.make_plan(1))
            a.act(plan[0])
            self.assertTrue(self.pump(host, [a, b], 3, lambda: host.forest.stats[1]["moves"] >= 1))
            self.assertTrue(self.pump(host, [a, b], 3, lambda: b.forest.robots[1]["pos"] == host.forest.robots[1]["pos"]
                                      and b.forest.robots[1]["face"] == host.forest.robots[1]["face"]))
            self.assertTrue(self.pump(host, [a, b], 3, lambda: len(a.rec) >= 1))
            a.reset()
            self.assertTrue(self.pump(host, [a, b], 3, lambda: host.forest.rec[1] == []))
            for k in host.forest.plots:
                host.forest.set_auto(k, True)
            self.assertTrue(self.pump(host, [a, b], 30, lambda: a.done is not None and b.done is not None))
            a.close()
            self.assertTrue(self.pump(host, [b], 3, lambda: not host.pcs[1]["on"]))
            b.close()
        finally:
            host.close()

    def quiet_minute(self, host, clients):
        for _ in range(240):
            self.skip += 0.25
            for c in clients:
                c.poll()
            time.sleep(0.002)
            host.tick(0.0)
            time.sleep(0.002)

    def test_quiet_students_stay_connected(self):
        real, self.skip = time.monotonic, 0.0
        with mock.patch("time.monotonic", lambda: real() + self.skip):
            host = net.Host("Ε2", port=TEST_GAME, disc_port=TEST_DISC)
            try:
                a = net.Client("Ελένη", "127.0.0.1", host.port)
                self.assertTrue(self.pump(host, [a], 4, lambda: a.state == "lobby"))
                self.quiet_minute(host, [a])
                self.assertEqual(a.state, "lobby")
                host.start_level("1", seed=1)
                self.assertTrue(self.pump(host, [a], 3, lambda: a.state == "level"))
                self.quiet_minute(host, [a])
                self.assertEqual(a.state, "level", a.error)
                self.assertTrue(host.pcs[1]["on"])
                a.close()
            finally:
                host.close()

    def test_program_round_over_the_network(self):
        for lid in ("7", "12"):                    # και με αισθητήρα (η μπάρα του γείτονα)
            self._program_round(lid)

    def _program_round(self, lid):
        old = net.PROG_EVERY
        net.PROG_EVERY = 0
        host = net.Host("Ε2", port=TEST_GAME, disc_port=TEST_DISC)
        try:
            a = net.Client("Ελένη", "127.0.0.1", host.port)
            b = net.Client("Νίκος", "127.0.0.1", host.port)
            self.assertTrue(self.pump(host, [a, b], 4, lambda: a.state == "lobby" and b.state == "lobby"))
            host.start_level(lid, seed=2)
            self.assertTrue(self.pump(host, [a, b], 3, lambda: a.state == "level" and b.state == "level"))
            self.assertEqual(a.mode, "write")
            for c in (a, b):
                c.send_program(host.forest.plots[c.k]["program"], True)
            self.assertTrue(self.pump(host, [a, b], 5, lambda: host.phase == "run"))
            seen = []
            self.assertTrue(self.pump(host, [a, b], 30, lambda: seen.append(a.forest.run_view.get(a.k)) or
                                      (a.results is not None and a.class_ok is not None)))
            self.assertTrue(any(v and v[0] for v in seen))         # το μπλοκ που τρέχει φτάνει στον μαθητή
            self.assertTrue(a.class_ok, lid)
            self.assertTrue(self.pump(host, [a, b], 3, lambda: a.done is not None))
            a.close()
            b.close()
        finally:
            net.PROG_EVERY = old
            host.close()

    def test_wrong_version_denied(self):
        import socket
        host = net.Host("Ε2", port=TEST_GAME, disc_port=TEST_DISC)
        sock = socket.create_connection(("127.0.0.1", host.port), timeout=2)
        try:
            c = net.Conn(sock)
            c.send({"t": "hello", "v": "0.0.1", "name": "Α", "host": "παλιός"})
            got = []
            end = time.monotonic() + 3
            while time.monotonic() < end and not got:
                host.tick(0.02)
                got = c.read()
                time.sleep(0.01)
            self.assertEqual(got[0]["t"], "deny")
            self.assertEqual(got[0]["why"], "version")
        finally:
            c.close()
            host.close()


# ================================================================ η εξάσκηση και οι οθόνες
class TestPractice(unittest.TestCase):
    def test_practice_plays_a_level(self):
        link = net.Practice("Γιώργος")
        link.start("2")
        self.assertEqual(link.state, "level")
        self.assertEqual(link.k, net.Practice.ME)
        k = link.k
        link.lesson.forest.set_auto(k, True)
        for _ in range(3000):
            link.tick(0.05)
            if link.done:
                break
        self.assertIsNotNone(link.done)
        self.assertEqual(link.forest.robots[k]["pos"], link.lesson.forest.robots[k]["pos"])


class TestScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True, data_dir=tempfile.mkdtemp())
        cls.app.sounds.enabled = False

    def frames(self, sc, n=5, keys=()):
        for e in keys:
            sc.handle_event(e)
        for _ in range(n):
            sc.update(1 / 30)
        sc.draw(self.app.screen)

    def test_student_screen_practice(self):
        from games.rescue import student
        for lid in ("1", "2", "3"):
            link = net.Practice("Ελένη")
            link.start(lid)
            sc = student.StudentScene(self.app, link)
            keys = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="", scancode=0),
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="", scancode=0)]
            self.frames(sc, 20, keys)
            self.assertGreaterEqual(link.lesson.forest.stats[link.k]["moves"] +
                                    link.lesson.forest.stats[link.k]["bumps"], 1)
            sc.toggle_full()
            self.frames(sc, 3)
            sc.toggle_full()
            link.lesson.forest.set_auto(link.k, True)
            for _ in range(3000):
                sc.update(0.05)
                if link.done:
                    break
            self.frames(sc, 3)
            self.assertIsNotNone(link.done)

    def test_student_screen_programs(self):
        from games.rescue import student
        for lid in ("5", "8"):
            link = net.Practice("Ελένη")
            link.start(lid)
            sc = student.StudentScene(self.app, link)
            self.frames(sc, 5)
            self.assertTrue(sc.programming)
            self.assertEqual(sc.editor.fix, lid == "5")
            sc.do_test()
            self.frames(sc, 60)
            for _ in range(600):                 # όσο τρέχει η Δοκιμή δεν αλλάζει το πρόγραμμα
                if sc.can_edit():
                    break
                sc.update(0.05)
            self.assertTrue(sc.can_edit())
            if lid == "5":
                self.assertIsNotNone(sc.editor.error)      # το δοσμένο πρόγραμμα έχει λάθος
            sc.editor.set_program(link.lesson.forest.plots[link.k]["program"])
            sc.do_test()
            for _ in range(200):
                sc.update(0.05)
            self.assertIsNone(sc.editor.error)
            sc.toggle_ready()
            for _ in range(3000):
                sc.update(0.05)
                if link.done:
                    break
            self.frames(sc, 3)
            self.assertIsNotNone(link.done)

    def test_teacher_screens_programs(self):
        from games.rescue import teacher
        T = teacher.TeacherScene(self.app)
        try:
            T.host.add_pc(100, "Μαρία", "PC-01")
            T.host.bots = 2
            T.selected = "6"
            self.frames(T, 3)
            T.start()
            self.frames(T, 5)
            T.open_help(1)
            for kind in ("hint", "blame", "route"):
                T.help(kind)
            self.frames(T, 3)
            T.help("auto")                     # η «Λύση» στα προγράμματα: το σωστό πρόγραμμα στην οθόνη τους
            self.assertEqual(T.host.programs[1], T.host.forest.plots[1]["program"])
            T.close_help()
            T.run_now()
            for _ in range(3000):
                T.update(0.05)
                if T.host.phase in ("result", "done"):
                    break
            self.frames(T, 3)
            self.assertEqual(T.host.phase, "done")
        finally:
            T.host.close()

    def test_student_screen_sensors(self):
        from games.rescue import student
        for lid in ("11", "13"):
            link = net.Practice("Ελένη")
            link.start(lid)
            sc = student.StudentScene(self.app, link)
            self.frames(sc, 5)
            self.assertTrue(sc.programming)
            sc.editor.set_program(link.lesson.forest.plots[link.k]["program"])
            sc.do_test()
            for _ in range(400):
                sc.update(0.05)
                if sc.test is None:
                    break
            sc.draw(self.app.screen)
            self.assertIsNone(sc.editor.error)
            sc.toggle_ready()
            for _ in range(3000):
                sc.update(0.05)
                if link.done:
                    break
            self.frames(sc, 3)
            self.assertIsNotNone(link.done, lid)

    def test_practice_level_dots_change_level(self):
        from games.rescue import student, art
        link = net.Practice("Ελένη")
        link.start("3")
        sc = student.StudentScene(self.app, link)
        self.frames(sc, 3)
        ids = [lid for ch in W.CHAPTERS for lid in ch.get("levels", [])]
        total = len(ids)
        for no in (5, 1, 12):
            x = 653 - (total - 1) * 16 + (no - 1) * 32
            self.assertEqual(art.level_dot_at((x, 30), 653, 30), no)
            sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, 30)))
            self.frames(sc, 3)
            self.assertEqual(link.level_id, ids[no - 1])
            self.assertEqual(sc.programming, W.level(ids[no - 1])["mode"] != "drive")

    def test_pedal_star_waits_for_the_neighbour(self):
        """Πίστα 3: το «κλαδί για τον γείτονα» μετρά μόνο όταν ο γείτονας πέρασε κάτω από το κλαδί."""
        from games.rescue import student
        link = net.Practice("Ελένη")
        link.start("3")
        sc = student.StudentScene(self.app, link)
        f = link.lesson.forest
        f.set_auto(link.k, True)
        seen = set()
        for _ in range(4000):
            sc.update(0.05)
            hint = sc._pedal_hint()
            if hint:
                seen.add(hint[0][0])
            if f.plot_done_stones(link.k) and not f.neighbour_passed(link.k):
                self.assertFalse(f.plot_done(link.k))
            if f.done:
                break
        self.assertTrue(f.done)
        self.assertTrue(f.plot_done(link.k))
        self.assertIn("Μείνε στο πεντάλ", seen)

    def test_last_level_ends_the_game(self):
        from games.rescue import teacher
        self.assertIsNone(W.next_level(W.LEVELS[-1]["id"]))
        T = teacher.TeacherScene(self.app)
        try:
            T.host.bots = 2
            T.selected = W.LEVELS[-1]["id"]
            self.frames(T, 3)
            T.start()
            self.frames(T, 3)
            self.assertNotIn(T.btn_next, T.buttons())          # στην τελευταία πίστα: όχι «Επόμενη»
            T.run_now()
            for _ in range(3000):
                T.update(0.05)
                if T.host.phase in ("result", "done"):
                    break
            self.frames(T, 3)
            self.assertEqual(T.host.phase, "done")
            self.assertIn(T.btn_done_end, T.buttons())
            self.assertNotIn(T.btn_done_next, T.buttons())
            T.btn_done_end.action()
            self.assertEqual(T.page, "setup")
        finally:
            T.host.close()

    def test_editor_sensor_blocks(self):
        from games.rescue import editor as E
        ed = E.Editor((800, 104, 460, 200), (812, 320, 436, 300), ("turn", "until", "move"))
        self.assertEqual([n["op"] for n in ed.palette.templates], ["turn", "until", "move"])
        ed.set_program([W.until_block(">", 20), W.line_block()])
        ed.set_field((0,), "cmp", "<")
        self.assertEqual(ed.program[0]["cmp"], "<")
        self.assertEqual(E.choices(ed.program[0], "cm"), E.CM_CHOICES)
        ed.draw_code(self.app.screen)
        ed.draw_palette(self.app.screen)

    def test_teacher_screens(self):
        from games.rescue import teacher
        T = teacher.TeacherScene(self.app)
        try:
            T.host.add_pc(100, "Μαρία", "PC-01")
            T.host.add_pc(101, "Νίκος", "PC-02")
            T.host.bots = 3
            self.frames(T, 3)
            T.selected = "3"
            T.start()
            self.frames(T, 10)
            T.view_key = 0
            self.frames(T, 3)
            T.open_help(1)
            for kind in ("hint", "route", "next"):
                T.help(kind)
            T.toggle_msgs()
            self.frames(T, 3)
            T.close_help()
            T.big = True
            self.frames(T, 3)
            for k in T.host.forest.plots:
                T.host.forest.set_auto(k, True)
            for _ in range(3000):
                T.update(0.05)
                if T.host.forest.done:
                    break
            self.frames(T, 3)
            self.assertTrue(T.host.forest.done)
            self.assertIn("3", T.store.klass(T.klass)["done"])
            T.next_level()
            self.frames(T, 3)
        finally:
            T.host.close()

    def test_start_join_practice_screens(self):
        from games.rescue import scene
        for cls in (scene.StartScene, scene.JoinScene, scene.PracticeScene):
            sc = cls(self.app)
            self.frames(sc, 3)
            if hasattr(sc, "finder") and sc.finder:
                sc.finder.close()
        sc = scene.MessageScene(self.app, "Χάθηκε η σύνδεση με τον δάσκαλο.")
        self.frames(sc, 2)

    def test_menu_icon(self):
        from games.rescue import draw_icon
        surf = pygame.Surface((300, 200))
        draw_icon(surf, (150, 100))


if __name__ == "__main__":
    unittest.main()
