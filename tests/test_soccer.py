"""Έλεγχοι για το Ποδόσφαιρο. Τρέξε:  py -m unittest discover tests"""
import json
import math
import os
import random
import sys
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.soccer import logic as L, net  # noqa: E402

TEST_DISC = 47911          # άλλες θύρες από το παιχνίδι, για να μη μπερδευτούν με ένα ανοιχτό γήπεδο
TEST_GAME = 47912


def players(nb=1, ny=1, bot_b=None, bot_y=None):
    out = [{"id": 1 + i, "name": f"B{i}", "team": L.BLUE, "bot": bot_b} for i in range(nb)]
    out += [{"id": 10 + i, "name": f"Y{i}", "team": L.YELLOW, "bot": bot_y} for i in range(ny)]
    return out


def run(m, seconds, inputs=None, step=1 / 60):
    events = []
    for _ in range(int(seconds / step)):
        events += m.update(step, inputs)
    return events


def playing(m):
    """Προσπερνά το 3, 2, 1."""
    run(m, L.COUNT_TIME + 0.05)
    assert m.phase == "play"
    return m


class PhysicsTests(unittest.TestCase):
    def test_countdown_then_play(self):
        m = L.Match(players(), 3)
        start = (m.robots[1].x, m.robots[1].y)
        ev = run(m, 1.9, {1: L.Input(1, 0, False)})
        self.assertEqual(m.phase, "count")
        self.assertEqual((m.robots[1].x, m.robots[1].y), start, "τα R2 περιμένουν το «Πάμε!»")
        self.assertEqual([e[1] for e in ev if e[0] == "count"], [3, 2])
        ev = run(m, 1.2, {1: L.Input(1, 0, False)})
        self.assertEqual([e[1] for e in ev if e[0] == "count"], [1])
        self.assertIn("go", [e[0] for e in ev])
        self.assertEqual(m.phase, "play")

    def test_drive_like_two_motors(self):
        m = playing(L.Match(players(), 3))
        r = m.robots[1]
        x0 = r.x
        run(m, 0.5, {1: L.Input(1, 0, False)})
        self.assertGreater(r.x, x0 + 60, "μπροστά = δεξιά για τη μπλε ομάδα")
        a0 = r.a
        run(m, 0.25, {1: L.Input(0, 1, False)})
        self.assertGreater(L.wrap(r.a - a0), 0.5, "→ στρίβει δεξιόστροφα")
        self.assertLess(abs(r.v), 1.0, "στροφή επί τόπου")
        a0 = r.a
        run(m, 0.25, {1: L.Input(0, -1, False)})
        self.assertLess(L.wrap(r.a - a0), -0.5)

    def test_kick(self):
        m = playing(L.Match(players(), 3))
        r = m.robots[1]
        r.x, r.y, r.a = 300, 150, 0.0
        m.ball.x, m.ball.y = 300 + L.HALF_LEN + L.BALL_R + 3, 150
        run(m, 0.05, {1: L.Input(0, 0, 0)})
        ev = run(m, 0.1, {1: L.Input(0, 0, 1)})
        names = [e[0] for e in ev]
        self.assertIn("shoot", names)
        self.assertIn("kick", names)
        self.assertGreater(m.ball.vx, L.KICK_SPEED * 0.9, "η μπάλα φεύγει μπροστά")
        self.assertLess(abs(m.ball.vy), 1.0, "ίσια, προς τα εκεί που κοιτάει το R2")
        self.assertEqual(m.ball.last, 1)
        snap = m.snapshot()
        m.ball.x, m.ball.y, m.ball.vx, m.ball.vy = r.x + 50, r.y, 0.0, 0.0
        ev = run(m, 0.1, {1: L.Input(0, 0, 2)})
        self.assertNotIn("shoot", [e[0] for e in ev], "θέλει λίγο χρόνο για να ξαναοπλίσει")
        self.assertEqual(m.ball.vx, 0.0)
        run(m, L.KICK_RELOAD, {1: L.Input(0, 0, 2)})
        ev = run(m, 0.1, {1: L.Input(0, 0, 3)})
        self.assertIn("kick", [e[0] for e in ev])
        self.assertEqual(len(snap["r"][0]), 6)

    def test_kick_misses_a_ball_that_is_not_in_front(self):
        m = playing(L.Match(players(), 3))
        r = m.robots[1]
        r.x, r.y, r.a = 300, 150, 0.0
        for bx, by in ((300, 150 + L.HALF_WID + L.BALL_R + 4), (300 + 120, 150), (300 - 60, 150)):
            m.ball.x, m.ball.y, m.ball.vx, m.ball.vy = bx, by, 0.0, 0.0
            run(m, L.KICK_RELOAD, {1: L.Input(0, 0, r.kick_seen)})
            ev = run(m, 0.1, {1: L.Input(0, 0, r.kick_seen + 1)})
            self.assertIn("shoot", [e[0] for e in ev], "η πλάκα βγαίνει")
            self.assertNotIn("kick", [e[0] for e in ev], (bx, by))
            self.assertLess(math.hypot(m.ball.vx, m.ball.vy), 1.0)

    def test_presses_during_the_countdown_do_not_kick(self):
        m = L.Match(players(), 3)
        m.ball.x = m.robots[1].x + L.HALF_LEN + L.BALL_R + 3
        m.ball.y = m.robots[1].y
        ev = run(m, L.COUNT_TIME + 0.3, {1: L.Input(0, 0, 7)})
        self.assertNotIn("shoot", [e[0] for e in ev])
        ev = run(m, 0.1, {1: L.Input(0, 0, 8)})
        self.assertIn("shoot", [e[0] for e in ev])

    def test_ball_never_leaves_the_field(self):
        rng = random.Random(3)
        m = playing(L.Match(players(2, 2, "hard", "hard"), 5, seed=1))
        for _ in range(300):
            b = m.ball
            if rng.random() < 0.05:
                b.vx, b.vy = rng.uniform(-1500, 1500), rng.uniform(-1500, 1500)
            m.update(1 / 60)
            self.assertTrue(-L.GOAL_D <= b.x <= L.FW + L.GOAL_D and 0 <= b.y <= L.FH, (b.x, b.y))
            for r in m.robots.values():
                self.assertTrue(0 <= r.x <= L.FW and 0 <= r.y <= L.FH)

    def test_robots_cannot_enter_the_goals(self):
        m = playing(L.Match(players(), 3))
        r = m.robots[1]
        r.x, r.y, r.a = L.FW - 80, L.FH / 2, 0.0
        run(m, 1.5, {1: L.Input(1, 0, False)})
        self.assertLessEqual(r.x, L.FW - L.WALL_R + 0.5)

    def test_push_the_ball_forward(self):
        m = playing(L.Match(players(), 3))
        r = m.robots[1]
        r.x, r.y, r.a = 300, 150, 0.0
        m.ball.x, m.ball.y = 360, 150
        run(m, 0.8, {1: L.Input(1, 0, False)})
        self.assertGreater(m.ball.x, 420)
        self.assertLess(abs(m.ball.y - 150), 30, "η ίσια μπροστινή πλευρά σπρώχνει ίσια")
        self.assertEqual(m.ball.last, 1)


class RuleTests(unittest.TestCase):
    def test_goals_on_both_sides(self):
        m = playing(L.Match(players(), 3))
        m.ball.last = 1
        m.ball.x, m.ball.y, m.ball.vx, m.ball.vy = L.FW - 30, L.FH / 2, 500, 0
        ev = run(m, 0.5)
        self.assertIn("goal", [e[0] for e in ev])
        self.assertEqual(m.score, {L.BLUE: 1, L.YELLOW: 0})
        self.assertEqual(m.goals[-1], [L.BLUE, "B0", False])
        self.assertEqual(m.phase, "goal")
        clock = m.clock
        run(m, L.GOAL_TIME + 0.1)
        self.assertEqual(m.phase, "count", "μετά το γκολ: ξανά στη σέντρα")
        self.assertEqual(m.clock, clock, "ο χρόνος σταματά στο γκολ")
        self.assertEqual((m.ball.x, m.ball.y), (L.FW / 2, L.FH / 2))
        playing(m)
        m.ball.last = 1                                  # ο μπλε τη βάζει στο δικό του τέρμα
        m.ball.x, m.ball.y, m.ball.vx, m.ball.vy = 30, L.FH / 2 + 40, -500, 0
        run(m, 0.5)
        self.assertEqual(m.score, {L.BLUE: 1, L.YELLOW: 1})
        self.assertEqual(m.goals[-1], [L.YELLOW, "", True], "αυτογκόλ")

    def test_ball_beside_the_goal_bounces(self):
        m = playing(L.Match(players(), 3))
        m.ball.x, m.ball.y, m.ball.vx, m.ball.vy = L.FW - 40, L.GOAL_TOP - 40, 600, 0
        run(m, 0.6)
        self.assertEqual(m.score, {L.BLUE: 0, L.YELLOW: 0})
        self.assertLess(m.ball.vx, 0)

    def test_stuck_ball_goes_to_a_neutral_spot(self):
        m = playing(L.Match(players(), 3))
        for r in m.robots.values():
            r.x, r.y = 200 if r.team == L.BLUE else 900, 500
        m.ball.x, m.ball.y = 60, 60
        ev = run(m, L.STUCK_TIME + 0.2)
        self.assertIn("spot", [e[0] for e in ev])
        self.assertIn((m.ball.x, m.ball.y), [tuple(p) for p in L.NEUTRAL])

    def test_match_ends_with_the_clock(self):
        m = playing(L.Match(players(), 2))
        m.clock = 0.5
        ev = run(m, 0.7)
        self.assertEqual(m.phase, "end")
        self.assertIn("end", [e[0] for e in ev])
        x = m.robots[1].x
        run(m, 1.0, {1: L.Input(1, 0, False)})
        self.assertEqual(m.robots[1].x, x)

    def test_kickoff_positions_mirror(self):
        for n in (1, 2, 3):
            m = L.Match(players(n, n), 3)
            blue = sorted((round(r.x, 6), round(r.y, 6)) for r in m.robots.values() if r.team == L.BLUE)
            yellow = sorted((round(L.FW - r.x, 6), round(r.y, 6)) for r in m.robots.values() if r.team == L.YELLOW)
            self.assertEqual(blue, yellow)
            self.assertTrue(all(x < L.FW / 2 - L.ROBOT_R for x, _ in blue))

    def test_snapshot_is_json(self):
        m = L.Match(players(3, 3, None, "easy"), 3)
        run(m, 4.0)
        snap = json.loads(json.dumps(m.snapshot()))
        self.assertEqual(len(snap["r"]), 6)
        self.assertEqual(snap["ph"], "play")
        self.assertEqual(snap["sc"], [0, 0])

    def test_bad_input_is_ignored(self):
        self.assertEqual(L.Input.from_list("rubbish").as_list(), [0.0, 0.0, 0])
        self.assertEqual(L.Input.from_list([9, -9, 1]).as_list(), [1.0, -1.0, 1])
        self.assertEqual(L.Input.from_list([0, 0, L.KICK_WRAP + 2]).kick, 2)
        self.assertEqual(L.Input.from_list([0, 0, "x"]).as_list(), [0.0, 0.0, 0])
        self.assertEqual(L.Input(1, 1, 5).still().as_list(), [0.0, 0.0, 5])


class BotTests(unittest.TestCase):
    def test_hard_bot_scores_against_nobody(self):
        m = playing(L.Match(players(1, 1, None, "hard"), 5, seed=2))
        run(m, 40)
        self.assertGreaterEqual(m.score[L.YELLOW], 2)

    def test_bots_kick(self):
        m = L.Match(players(1, 1, "hard", "easy"), 2, seed=0)
        shots = 0
        while m.phase != "end":
            shots += sum(1 for e in m.update(1 / 30) if e[0] == "shoot")
        self.assertGreater(shots, 0, "το δύσκολο ρομπότ κλωτσάει")
        m = L.Match(players(1, 1, "easy", "easy"), 2, seed=0)
        while m.phase != "end":
            self.assertNotIn("shoot", [e[0] for e in m.update(1 / 30)], "το εύκολο μόνο σπρώχνει")

    def test_levels_are_in_order(self):
        def goals(level, other, seed):
            m = L.Match(players(1, 1, level, other), 2, seed=seed)
            while m.phase != "end":
                m.update(1 / 30)
            return m.score[L.BLUE] - m.score[L.YELLOW]
        self.assertGreater(sum(goals("hard", "easy", s) for s in range(3)), 6)

    def test_teams_are_fair(self):
        diff = 0
        for seed in range(4):
            m = L.Match(players(2, 2, "normal", "normal"), 2, seed=seed)
            while m.phase != "end":
                m.update(1 / 30)
            diff += m.score[L.BLUE] - m.score[L.YELLOW]
        self.assertLessEqual(abs(diff), 8, "καμία ομάδα δεν έχει πλεονέκτημα")


class NameTests(unittest.TestCase):
    def test_capitals_without_accents(self):
        self.assertEqual(net.clean_name("μαρία"), "ΜΑΡΙΑ")
        self.assertEqual(net.clean_name("  Γιώργος!!  "), "ΓΙΩΡΓΟΣ")
        self.assertEqual(net.clean_name("Χαράλαμπος Παπαδόπουλος"), "ΧΑΡΑΛΑΜΠΟΣ")
        self.assertEqual(net.typed_name("άννα "), "ΑΝΝΑ ")
        self.assertEqual(net._unique("ΝΙΚΟΣ", {"ΝΙΚΟΣ"}), "ΝΙΚΟΣ 2")

    def test_ip(self):
        self.assertTrue(net.valid_ip("192.168.1.23"))
        self.assertFalse(net.valid_ip("192.168.1"))
        self.assertFalse(net.valid_ip("300.1.1.1"))


def pump(*sides, seconds=0.6):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        for s in sides:
            s.poll()
        time.sleep(0.005)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.host = net.Host("Μαρία", 2, port=TEST_GAME, disc_port=TEST_DISC)
        self.clients = []

    def tearDown(self):
        for c in self.clients:
            c.close()
        self.host.close()

    def join(self, name):
        c = net.Client(name, "127.0.0.1", self.host.port)
        self.clients.append(c)
        pump(self.host, *self.clients)
        return c

    def test_finder_sees_the_field(self):
        f = net.Finder(port=TEST_DISC)
        try:
            end = time.monotonic() + 3
            while time.monotonic() < end and not f.fields():
                self.host.poll()
                f.poll()
                time.sleep(0.01)
            fields = f.fields()
            self.assertEqual(len(fields), 1)
            self.assertEqual(fields[0]["name"], "ΜΑΡΙΑ")
            self.assertEqual(fields[0]["port"], self.host.port)
            self.assertEqual(fields[0]["state"], "lobby")
        finally:
            f.close()

    def test_join_teams_bots_and_play(self):
        a = self.join("Γιώργος")
        b = self.join("γιώργος")
        self.assertEqual((a.state, b.state), ("lobby", "lobby"))
        names = {p["name"]: p["team"] for p in a.players}
        self.assertEqual(names, {"ΜΑΡΙΑ": L.BLUE, "ΓΙΩΡΓΟΣ": L.YELLOW, "ΓΙΩΡΓΟΣ 2": L.BLUE})
        b.swap()
        pump(self.host, a, b, seconds=0.3)
        self.assertEqual(self.host.player(b.me)["team"], L.YELLOW)
        bot = self.host.add_bot(L.BLUE)
        pump(self.host, a, b, seconds=0.3)
        self.assertIn("ΡΟΜΠΟΤ", [p["name"] for p in b.players])
        self.assertTrue(self.host.can_start())
        self.host.start()
        last = time.monotonic()
        end = last + L.COUNT_TIME + 1.5
        while time.monotonic() < end:
            now = time.monotonic()
            dt, last = now - last, now
            self.host.update(dt, L.Input())
            a.update(dt, L.Input(1, 0, False))
            b.update(dt, L.Input())
            time.sleep(1 / 120)
        self.assertEqual(a.state, "match")
        self.assertGreater(len(a.snaps), 10)
        r = self.host.match.robots[a.me]
        self.assertLess(r.x, L.FW - L.FORMATION[2][0][0] * L.FW - 80, "το R2 του Client κινήθηκε (κίτρινο: προς τα αριστερά)")
        view = b.view()
        self.assertEqual({row[0] for row in view["r"]}, {1, a.me, b.me, bot})
        a.close()
        pump(self.host, b, seconds=0.3)
        self.assertNotIn(a.me, self.host.match.robots, "όποιος φεύγει, βγαίνει από το γήπεδο")
        self.host.to_lobby()
        pump(self.host, b, seconds=0.3)
        self.assertEqual(b.state, "lobby")

    def test_two_players_on_one_computer(self):
        a = self.join("Γιώργος")
        b = self.join("Ελένη")
        a.add_local("Νίκος")
        pump(self.host, a, b, seconds=0.3)
        ids = a.mine()
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids[0], a.me)
        second = self.host.player(ids[1])
        self.assertEqual((second["name"], second["pc"]), ("ΝΙΚΟΣ", a.pc))
        self.assertEqual(b.mine(), [b.me], "ο άλλος υπολογιστής έχει έναν παίκτη")
        a.add_local("Τρίτος")
        pump(self.host, a, b, seconds=0.2)
        self.assertEqual(len(a.mine()), 2, "ως δύο παίκτες σε κάθε υπολογιστή")
        team = second["team"]
        a.swap(ids[1])
        b.swap(ids[1])                                   # ο άλλος υπολογιστής δεν αλλάζει ξένο παίκτη
        pump(self.host, a, b, seconds=0.3)
        self.assertEqual(self.host.player(ids[1])["team"], L.other(team))
        self.assertEqual(self.host.add_local("Μαρκος"), self.host._next - 1)
        self.assertEqual(len(self.host.mine()), 2, "και ο υπολογιστής με το γήπεδο")
        self.host.start()
        pump(self.host, a, b, seconds=0.2)
        robots = self.host.match.robots
        start = {pid: (robots[pid].x, robots[pid].y) for pid in robots}
        last = time.monotonic()
        end = last + L.COUNT_TIME + 1.2
        while time.monotonic() < end:
            now = time.monotonic()
            dt, last = now - last, now
            self.host.update(dt, {})
            a.update(dt, {ids[0]: L.Input(1, 0, 0), ids[1]: L.Input(-1, 0, 0)})
            b.update(dt, {b.me: L.Input(), 1: L.Input(1, 0, 0)})      # ξένος παίκτης: αγνοείται
            time.sleep(1 / 120)
        moved = {pid: math.hypot(robots[pid].x - start[pid][0], robots[pid].y - start[pid][1]) for pid in start}
        self.assertGreater(moved[ids[0]], 60, "ο πρώτος (W A S D) κινήθηκε")
        self.assertGreater(moved[ids[1]], 60, "και ο δεύτερος (βελάκια)")
        self.assertLess(moved[1], 5, "ο b δεν μπορεί να οδηγήσει το R2 άλλου υπολογιστή")
        a.close()
        pump(self.host, b, seconds=0.3)
        self.assertNotIn(ids[0], robots)
        self.assertNotIn(ids[1], robots, "φεύγουν και οι δύο παίκτες του υπολογιστή")

    def test_second_player_leaves_and_full_field(self):
        a = self.join("Άννα")
        a.add_local("Βασω")
        pump(self.host, a, seconds=0.3)
        first, second = a.mine()
        a.drop_local(first)                              # μόνο ο δεύτερος βγαίνει έτσι
        pump(self.host, a, seconds=0.2)
        self.assertEqual(a.mine(), [first, second])
        a.drop_local(second)
        pump(self.host, a, seconds=0.2)
        self.assertEqual(a.mine(), [first])
        self.assertEqual(a.state, "lobby")
        for team in (L.BLUE, L.YELLOW, L.BLUE, L.YELLOW):
            self.host.add_bot(team)
        self.assertEqual(len(self.host.players), 2 * L.MAX_TEAM)
        a.add_local("Βασω")
        pump(self.host, a, seconds=0.2)
        self.assertEqual(a.mine(), [first], "γεμάτο γήπεδο")
        self.assertIsNone(self.host.add_local("Κανείς"))

    def test_deny_when_full_or_playing_or_other_version(self):
        for i in range(5):
            self.join(f"Π{i}")
        late = self.join("Αργός")
        self.assertEqual(late.state, "closed")
        self.assertIn("γεμάτο", late.error)
        self.host.remove(self.clients[0].me)
        self.host.start()
        pump(self.host, *self.clients, seconds=0.2)
        later = self.join("Άλλος")
        self.assertEqual(later.state, "closed")
        self.assertIn("Παίζουν", later.error)
        self.host.to_lobby()
        # ένας υπολογιστής με παλιότερη έκδοση του προγράμματος
        import socket
        sock = socket.create_connection(("127.0.0.1", self.host.port), timeout=2)
        conn = net.Conn(sock)
        conn.send({"t": "hello", "v": "0.0.1", "name": "Παλιός"})
        answer = []
        end = time.monotonic() + 1
        while time.monotonic() < end and not answer:
            self.host.poll()
            answer = conn.read()
            time.sleep(0.01)
        conn.close()
        self.assertEqual(answer[0]["t"], "deny")
        self.assertEqual(answer[0]["why"], "version")
        self.assertNotIn("ΠΑΛΙΟΣ", [p["name"] for p in self.host.players])

    def test_host_leaves(self):
        a = self.join("Νίκος")
        self.host.close()
        pump(a, seconds=0.3)
        self.assertEqual(a.state, "closed")
        self.assertIn("έκλεισε", a.error)

    def test_nobody_there(self):
        c = net.Client("Κανείς", "127.0.0.1", TEST_GAME + 30)
        self.clients.append(c)
        end = time.monotonic() + net.CONNECT_TIMEOUT + 1
        while time.monotonic() < end and c.state != "closed":
            c.poll()
            time.sleep(0.02)
        self.assertEqual(c.state, "closed")


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def click(self, sc, pos):
        sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))

    def frames(self, sc, n):
        for _ in range(n):
            sc.update(1 / 60)
        sc.draw(self.app.screen)

    def test_in_the_menu(self):
        from games import GAMES
        self.assertIn("games.soccer", [g.get("module") for g in GAMES])

    def test_play_against_the_computer(self):
        from games.soccer import scene as S
        sc = S.SoccerScene(self.app)
        self.frames(sc, 2)
        self.click(sc, sc.page.tiles[0].center)
        self.assertIsInstance(sc.page, S.SetupPage)
        self.click(sc, sc.page.level_rects[1].center)
        self.assertEqual(sc.prefs["level"], "hard")
        self.click(sc, sc.page.btn_go.rect.center)
        self.assertIsInstance(sc.page, S.MatchPage)
        self.frames(sc, 240)
        m = sc.page.session.match
        self.assertEqual(m.phase, "play")
        self.assertEqual(m.bots[2].level, "hard")
        m.clock = 0.1
        self.frames(sc, 120)
        self.assertTrue(sc.page.end_visible())
        self.click(sc, sc.page.btn_again.rect.center)
        self.assertEqual(sc.page.session.match.phase, "count")
        self.assertFalse(sc.page.end_visible())

    def test_wasd_works_with_a_greek_keyboard(self):
        from games.soccer import scene as S
        sc = S.SoccerScene(self.app)
        sc.go(S.MatchPage(sc, S.LocalSession("two", "easy", 2)))
        m = sc.page.session.match
        self.frames(sc, int(L.COUNT_TIME * 60) + 5)
        x = m.robots[1].x
        # το φυσικό πλήκτρο W με ελληνικό πληκτρολόγιο γράφει «ς»: το scancode μένει 26
        sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord("ς"), scancode=S.SC_W, mod=0, unicode="ς"))
        self.frames(sc, 30)
        self.assertGreater(m.robots[1].x, x + 40)
        sc.handle_event(pygame.event.Event(pygame.KEYUP, key=ord("ς"), scancode=S.SC_W, mod=0))
        self.assertNotIn(S.SC_W, sc.keys)

    def test_kick_keys_count_presses(self):
        from games.soccer import scene as S
        sc = S.SoccerScene(self.app)
        space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, scancode=S.SC_SPACE, mod=0, unicode=" ")
        sc.handle_event(space)
        sc.handle_event(space)                           # η αυτόματη επανάληψη δεν μετράει
        self.assertEqual(sc.kicks, {"one": 1, "left": 1, "right": 0})
        sc.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, scancode=S.SC_SPACE, mod=0))
        sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, scancode=S.SC_RETURN, mod=0,
                                           unicode="\r"))
        self.assertEqual(sc.kicks, {"one": 2, "left": 1, "right": 1})
        self.assertEqual(sc.pad("right").kick, 1)

    def test_second_player_in_the_lobby(self):
        from games.soccer import scene as S
        sc = S.SoccerScene(self.app)
        sc.prefs = {"name": "ΜΑΡΙΑ", "level": "easy", "minutes": 3}
        host = net.Host("ΜΑΡΙΑ", 2, port=TEST_GAME + 5, disc_port=TEST_DISC + 5)
        sc.go(S.LobbyPage(sc, host))
        try:
            self.frames(sc, 2)
            self.click(sc, sc.page.btn_second.rect.center)
            self.assertTrue(sc.page.second_open)
            self.frames(sc, 1)
            self.assertFalse(sc.page.btn_in.enabled, "χωρίς όνομα δεν μπαίνει")
            for ch in "Νίκος":
                sc.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=ch))
            sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, scancode=S.SC_RETURN, mod=0,
                                               unicode="\r"))
            self.assertFalse(sc.page.second_open)
            self.assertEqual([host.player(pid)["name"] for pid in host.mine()], ["ΜΑΡΙΑ", "ΝΙΚΟΣ"])
            self.frames(sc, 2)
            self.assertIsNone(sc.page.btn_second.action, "ως δύο σε κάθε υπολογιστή")
            second = host.player(host.mine()[1])
            team = second["team"]
            i = [p["id"] for p in sc.page.team_list(team)].index(second["id"])
            self.click(sc, sc.page.swap_btns[(team, i)].rect.center)
            self.assertNotEqual(second["team"], team)
            self.frames(sc, 2)
            host.add_bot(L.YELLOW)
            self.frames(sc, 2)
            self.click(sc, sc.page.btn_start.rect.center)
            self.assertIsInstance(sc.page, S.MatchPage)
            self.frames(sc, int(L.COUNT_TIME * 60) + 5)
            robots = host.match.robots
            first_id, second_id = host.mine()
            x1, x2 = robots[first_id].x, robots[second_id].x
            sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord("w"), scancode=S.SC_W, mod=0, unicode="w"))
            self.frames(sc, 30)
            self.assertGreater(abs(robots[first_id].x - x1), 40, "W οδηγεί τον πρώτο")
            self.assertLess(abs(robots[second_id].x - x2), 1, "όχι τον δεύτερο")
        finally:
            sc.to_menu()
        self.assertTrue(host.closed)

    def test_network_pages(self):
        from games.soccer import scene as S
        sc = S.SoccerScene(self.app)
        sc.prefs = {"name": "", "level": "easy", "minutes": 3}
        sc.go(S.NetListPage(sc))
        self.frames(sc, 2)
        self.click(sc, sc.page.btn_make.rect.center)
        self.assertIsInstance(sc.page, S.NetListPage, "χωρίς όνομα δεν φτιάχνεται γήπεδο")
        for ch in "Μαρία":
            sc.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=ch))
        self.assertEqual(sc.prefs["name"], "ΜΑΡΙΑ")
        self.click(sc, sc.page.btn_make.rect.center)
        self.assertIsInstance(sc.page, S.LobbyPage)
        host = sc.page.session
        try:
            self.frames(sc, 2)
            self.assertFalse(sc.page.btn_start.enabled or host.can_start(), "η κίτρινη ομάδα είναι άδεια")
            add, _ = sc.page.slot_btns[(L.YELLOW, 0)]
            self.click(sc, add.rect.center)
            self.frames(sc, 2)
            self.assertTrue(host.can_start())
            self.click(sc, sc.page.btn_start.rect.center)
            self.assertIsInstance(sc.page, S.MatchPage)
            self.frames(sc, 60)
            host.match.clock = 0.0
            host.match.phase = "play"
            self.frames(sc, 120)
            self.click(sc, sc.page.btn_mid.rect.center)
            self.assertIsInstance(sc.page, S.LobbyPage)
        finally:
            sc.to_menu()
        self.assertTrue(host.closed)


if __name__ == "__main__":
    unittest.main()
