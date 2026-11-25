"""Έλεγχοι για το τρέξιμο του R2, τους Αριθμούς, τις Λέξεις και τις Πράξεις.

Τρέξε:  py -m unittest discover tests
"""
import os
import random
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.calc import lesson as calc_lesson  # noqa: E402
from games.calc import levels as calc_levels  # noqa: E402
from games.numbers import LEVEL_COUNT, levels  # noqa: E402
from games.words import levels as word_levels  # noqa: E402
from games.words import pictures  # noqa: E402
from games.runner import art as runner_art  # noqa: E402
from games.runner import logic  # noqa: E402
from games.runner.chunks import build, flat  # noqa: E402
from games.runner.logic import GROUND, HIT, TILE  # noqa: E402


def floor(line):
    """Κομμάτι με κάτι μόνο στη γραμμή του πατώματος."""
    return ["." * len(line)] * 7 + [line]


def track(*parts, speed=6.0):
    return logic.Track(build(flat(6), *parts, flat(8)), speed)


def run(tr, hold_at=(), steps=600):
    """Τρέχει χωρίς πατήματα, εκτός από τα βήματα hold_at (πατημένο). Επιστρέφει τον runner και τα γεγονότα."""
    r = logic.Runner(tr)
    events = []
    held = False
    for k in range(steps):
        h = k in hold_at
        events += r.step(h, pressed=h and not held)
        held = h
        if r.dead or r.done:
            break
    return r, events


class PhysicsTests(unittest.TestCase):
    def test_jump_height_is_about_two_and_a_half_boxes(self):
        r = logic.Runner(track())
        r.step(True, pressed=True)
        top = r.y
        for _ in range(120):
            r.step(False)
            top = min(top, r.y)
        self.assertAlmostEqual((GROUND - HIT - top) / TILE, 2.4, delta=0.15)
        self.assertTrue(r.grounded)

    def test_spike_without_jump_crashes(self):
        r, events = run(track(floor("..^..")))
        self.assertTrue(r.dead)
        self.assertIn(("crash",), events)

    def test_running_into_a_block_crashes_but_landing_on_it_is_fine(self):
        tr = track(floor("..#..."))
        r, _ = run(tr)
        self.assertTrue(r.dead)
        # πηδά λίγο πριν και πατά πάνω στο κουτί
        start = int((8 * TILE - 2.2 * TILE - tr.start_x) / tr.speed / logic.STEP)
        r, _ = run(tr, hold_at={start})
        self.assertTrue(r.done and not r.dead)

    def test_pad_throws_over_a_wall(self):
        r, events = run(track(build(["." * 15] * 5 + ["........###....", "........###....",
                                                     "...._...###...."])))
        self.assertTrue(r.done, events)
        self.assertTrue(any(e[0] == "pad" for e in events))

    def test_gravity_portal_flips_and_back(self):
        tr = track(build(["##########"] + ["." * 10] * 4 + ["..G.......", "." * 10, "." * 10]),
                   build(["##########"] + ["." * 10] * 4 + ["..g.......", "." * 10, "." * 10]))
        r = logic.Runner(tr)
        while r.next_portal == 0:
            r.step(False)
        for _ in range(90):
            r.step(False)
        self.assertEqual(r.g, -1)
        self.assertAlmostEqual(r.y, logic.TOP + TILE, delta=1)      # τρέχει κάτω από το ταβάνι
        while not r.done:
            r.step(False)
        self.assertEqual(r.g, 1)
        self.assertAlmostEqual(r.y, GROUND - HIT, delta=1)

    def test_rocket_rises_when_held_and_falls_when_released(self):
        tr = track(build(["." * 10] * 5 + ["..R.......", "." * 10, "." * 10]), flat(30))
        r = logic.Runner(tr)
        while r.mode != "rocket":
            r.step(False)
        y0 = r.y
        for _ in range(40):
            r.step(True)
        self.assertLess(r.y, y0 - 40)
        y1 = r.y
        for _ in range(90):
            r.step(False)
        self.assertGreater(r.y, y1 + 20)

    def test_choice_picks_by_height(self):
        tr = track("""
            ........
            ........
            ........
            ........
            ........
            ...A....
            ........
            ...B....""")
        self.assertEqual(len(tr.choices), 1)
        _, events = run(tr)
        self.assertIn(("pick", 0, "B"), events)
        start = int((9.5 * TILE - 2.4 * TILE - tr.start_x) / tr.speed / logic.STEP)
        _, events = run(tr, hold_at={start})
        self.assertIn(("pick", 0, "A"), events)

    def test_bad_track_is_refused(self):
        with self.assertRaises(ValueError):
            logic.Track(["..x.."] * 8, 6)
        with self.assertRaises(ValueError):
            logic.Track(["...A..."] + ["......."] * 7, 6)


class NumbersTests(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(LEVEL_COUNT, 6)
        speeds = []
        for n, lv in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
                self.assertEqual(len(tr.choices), len(lv["lesson"].seq))
                self.assertEqual(len(tr.choices), 10)
                seconds = (tr.finish_x - tr.start_x) / tr.speed
                self.assertTrue(20 < seconds < 40, seconds)
                speeds.append(lv["speed"])
        self.assertEqual(speeds, sorted(speeds))          # κάθε πίστα πιο γρήγορη

    def test_every_level_can_be_finished_whatever_the_answers(self):
        """Ο λύτης περνά κάθε πίστα και με όλες τις σωστές φούσκες ψηλά, και με όλες χαμηλά."""
        for n, lv in enumerate(levels.LEVELS, 1):
            tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
            for pick in ("A", "B"):
                with self.subTest(level=n, pick=pick):
                    self.assertIsNotNone(logic.solve(tr, [pick] * len(tr.choices), every=8))

    def test_wrong_numbers_are_never_the_right_one(self):
        rng = random.Random(3)
        for lv in levels.LEVELS:
            lesson = lv["lesson"]
            for _ in range(20):
                for (right, wrong), n in zip(lesson.pairs(rng), lesson.seq):
                    self.assertEqual(right, str(n))
                    self.assertNotEqual(right, wrong)
                    self.assertGreater(int(wrong), 0)
            line1, line2 = lesson.wrong_text(2, "99")
            self.assertIn("99", line1)
            self.assertIn(str(lesson.seq[2]), line2)


class WordsTests(unittest.TestCase):
    def test_levels(self):
        speeds, lengths = [], []
        for n, lv in enumerate(word_levels.LEVELS, 1):
            with self.subTest(level=n):
                lesson = lv["lesson"]
                tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
                self.assertEqual(len(tr.choices), len(lesson.seq))        # μία επιλογή για κάθε γράμμα
                self.assertEqual(len(lesson.words), 2)
                for word, pic in lesson.words:
                    self.assertTrue(word.isupper() and word.isalpha(), word)
                    self.assertTrue(set(word) <= set("ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"), word)
                    self.assertIn(pic, pictures.DRAW)
                seconds = (tr.finish_x - tr.start_x) / tr.speed
                self.assertTrue(15 < seconds < 45, seconds)
                speeds.append(lv["speed"])
                lengths.append(max(len(w) for w, _ in lesson.words))
        self.assertEqual(speeds, sorted(speeds))
        self.assertEqual(lengths, sorted(lengths))          # οι λέξεις μεγαλώνουν

    def test_every_level_can_be_finished_whatever_the_answers(self):
        for n, lv in enumerate(word_levels.LEVELS, 1):
            tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
            for pick in ("A", "B"):
                with self.subTest(level=n, pick=pick):
                    self.assertIsNotNone(logic.solve(tr, [pick] * len(tr.choices), every=8))

    def test_wrong_letters_and_spelling_traps(self):
        rng = random.Random(5)
        for lv in word_levels.LEVELS:
            lesson = lv["lesson"]
            for _ in range(20):
                for (right, wrong), ch in zip(lesson.pairs(rng), lesson.seq):
                    self.assertEqual(right, ch)
                    self.assertNotEqual(right, wrong)
        moon = word_levels.WordsLesson([("ΦΕΓΓΑΡΙ", "moon"), ("ΠΑΠΟΥΤΣΙ", "shoe")], traps=True)
        traps = {moon.seq[i] + "/" + moon.trap(i) for i in range(len(moon.seq)) if moon.trap(i)}
        self.assertIn("Ι/ΗΥ", traps)                       # ΦΕΓΓΑΡΙ: Ι, Η ή Υ στο τέλος
        self.assertEqual(moon.trap(10), "")                # ΠΑΠΟΥ: το Ο του ΟΥ δεν γίνεται Ω
        self.assertEqual(moon.trap(11), "")                # ούτε το Υ του ΟΥ γίνεται Ι
        bike = word_levels.WordsLesson([("ΠΟΔΗΛΑΤΟ", "bicycle")], traps=True)
        self.assertEqual(bike.trap(1), "Ω")
        self.assertEqual(bike.trap(3), "ΙΥ")
        line1, line2 = bike.wrong_text(3, "Ι")
        self.assertIn("Ι", line1)
        self.assertIn("ΠΟΔ", line2)

    def test_panel_shows_the_right_word(self):
        lesson = word_levels.LEVELS[0]["lesson"]           # ΜΗΛΟ, ΓΑΤΑ
        surf = pygame.Surface((1280, 720))
        seen = []

        def fake(s, c, word, filled, pic, t):
            seen.append((word, filled))
            pic(s, pygame.Rect(0, 0, 76, 76))

        with mock.patch.object(runner_art, "word_panel", fake):
            lesson.draw_panel(surf, (640, 665), 2, 0.0)
            lesson.draw_panel(surf, (640, 665), 4, 0.0, since=0.3)     # μόλις τελείωσε το ΜΗΛΟ
            lesson.draw_panel(surf, (640, 665), 4, 0.0, since=2.0)
            lesson.draw_panel(surf, (640, 665), 8, 0.0, since=2.0)
        self.assertEqual(seen, [("ΜΗΛΟ", 2), ("ΜΗΛΟ", 4), ("ΓΑΤΑ", 0), ("ΓΑΤΑ", 4)])
        self.assertEqual(lesson.sound_after(4), "complete")
        self.assertIsNone(lesson.sound_after(3))

    def test_every_picture_draws(self):
        for name in pictures.DRAW:
            img = pictures.picture(name, 76)
            self.assertEqual(img.get_size(), (76, 76))
            self.assertGreater(pygame.mask.from_surface(img).count(), 76 * 76 // 6, name)


class CalcTests(unittest.TestCase):
    def test_levels(self):
        speeds = []
        for n, lv in enumerate(calc_levels.LEVELS, 1):
            with self.subTest(level=n):
                tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
                self.assertEqual(len(tr.choices), 8)
                self.assertEqual(len(lv["lesson"].seq), 8)
                gaps = [(b["x"] - a["x"]) / tr.speed for a, b in zip(tr.choices, tr.choices[1:])]
                self.assertGreater(min(gaps), 2.5)                 # χρόνος για να λογαριάσει
                speeds.append(lv["speed"])
        self.assertEqual(speeds, sorted(speeds))

    def test_every_level_can_be_finished_whatever_the_answers(self):
        for n, lv in enumerate(calc_levels.LEVELS, 1):
            tr = logic.Track(lv["rows"], lv["speed"], lv.get("fast"))
            for pick in ("A", "B"):
                with self.subTest(level=n, pick=pick):
                    self.assertIsNotNone(logic.solve(tr, [pick] * len(tr.choices), every=8))

    def test_questions_are_right_and_in_range(self):
        limits = {calc_lesson.add10: 10, calc_lesson.sub10: 10, calc_lesson.mixed20: 20,
                  calc_lesson.tens100: 100, calc_lesson.times2510: 100, calc_lesson.times_all: 81}
        rng = random.Random(7)
        for make, top in limits.items():
            for _ in range(300):
                text, r, wrongs = make(rng)
                expr = text.replace(" = ?", "").replace("−", "-").replace("×", "*")
                a, op, b = expr.split()
                self.assertEqual(eval(expr), r, text)
                self.assertTrue(0 < r <= top, text)
                self.assertTrue(int(a) <= top and int(b) <= top, text)
                self.assertTrue(wrongs and r not in wrongs, text)
                self.assertTrue(all(0 <= w <= max(top, 100) for w in wrongs), text)
                if make is calc_lesson.tens100:
                    self.assertTrue(int(a) % 10 == 0 or int(b) % 10 == 0, text)
                if make in (calc_lesson.times2510, calc_lesson.times_all):
                    self.assertTrue(all(w % int(a) == 0 or w % int(b) == 0 for w in wrongs), text)

    def test_a_lesson_gives_different_questions_each_try(self):
        lesson = calc_levels.LEVELS[0]["lesson"]
        rng = random.Random(2)
        first = lesson.pairs(rng)
        texts = [q[0] for q in lesson.questions]
        self.assertEqual(len(set(texts)), 8)
        for (right, wrong), (text, r, _) in zip(first, lesson.questions):
            self.assertEqual(right, str(r))
            self.assertNotEqual(right, wrong)
        lesson.pairs(rng)
        self.assertNotEqual(texts, [q[0] for q in lesson.questions])
        self.assertEqual(lesson.wrong_text(0, "99"), ("Ωχ! Όχι το 99.", lesson.solved(0)))
        self.assertNotIn("?", lesson.solved(0))


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def open(self, level=0, speed=2):
        import games.numbers as numbers
        self.app.runner_speed = speed                       # ο λύτης παίζει στο «Γρήγορα» (κανονικός χρόνος)
        scene = numbers.open_game(self.app)
        scene.load(level)
        return scene

    def key(self, scene, down):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=pygame.K_SPACE))

    def click(self, scene, pos):
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))

    def start(self, scene):
        """Ξεκινά την πίστα όπως το παιδί: κλικ στην ταχύτητα που είναι ήδη διαλεγμένη."""
        self.click(scene, scene.speed_rects[scene.speed_i].center)

    def test_starts_only_with_a_click_on_a_speed_then_crashes_and_restarts(self):
        scene = self.open()
        for _ in range(30):
            scene.update(1 / 60)
        self.assertEqual(scene.state, "ready")
        self.key(scene, True)                               # το Space δεν ξεκινά
        self.key(scene, False)
        self.click(scene, (640, 600))                       # ούτε κλικ έξω από τις ταχύτητες
        for _ in range(30):
            scene.update(1 / 60)
        self.assertEqual(scene.state, "ready")
        self.start(scene)
        self.assertEqual(scene.state, "run")
        for _ in range(400):
            scene.update(1 / 60)
            scene.draw(self.app.screen)
            if scene.state == "crash":
                break
        self.assertEqual(scene.state, "crash")             # δεν πήδηξε: χτύπησε στο πρώτο αγκάθι
        for _ in range(int(60 * 1.1)):
            scene.update(1 / 60)
        self.assertEqual(scene.attempt, 2)
        self.assertEqual(scene.state, "ready")
        for _ in range(60):
            scene.update(1 / 60)
        self.assertEqual(scene.state, "run")                # ξεκινά μόνο του τη δεύτερη φορά

    def play(self, scene, picks):
        """Παίζει την προσπάθεια που περιμένει στην αφετηρία, με τα πατήματα του λύτη."""
        plan = logic.solve(scene.track, picks, every=8)
        self.assertIsNotNone(plan)
        for _ in range(20):
            scene.update(1 / 60)
        self.start(scene)
        scene.update(0.0)
        held = False
        for h in plan:
            if h != held:
                self.key(scene, h)
                held = h
            scene.update(8 * logic.STEP + 1e-9)
            if scene.state != "run":
                break
        self.key(scene, False)

    def test_wrong_bubble_restarts_and_right_path_finishes(self):
        scene = self.open()
        picks = [it["right"] for it in scene.items]
        picks[3] = "A" if picks[3] == "B" else "B"           # η 4η απάντηση λάθος
        self.play(scene, picks)
        self.assertEqual(scene.state, "wrong")
        self.assertEqual(scene.got, 3)
        self.assertIn(str(levels.LEVELS[0]["lesson"].seq[3]), scene.wrong[1])
        scene.draw(self.app.screen)
        for _ in range(int(60 * 3.2)):
            scene.update(1 / 60)
        self.assertEqual(scene.attempt, 2)
        self.assertEqual(scene.got, 0)
        scene.new_attempt(wait=True)
        self.play(scene, [it["right"] for it in scene.items])
        self.assertEqual(scene.state, "finish")
        self.assertEqual(scene.got, 10)
        for _ in range(240):
            scene.update(1 / 60)
            scene.draw(self.app.screen)
        self.assertIsNotNone(scene.charging_at)
        self.assertTrue(scene.celebrated)
        self.assertIn(1, self.app.progress.completed("numbers"))

    def test_click_on_bravo_goes_to_next_level(self):
        from games.runner.scene import BANNER_POS
        scene = self.open()
        self.assertFalse(scene.banner.contains(BANNER_POS, scene.time, BANNER_POS))   # κρυφό: δεν πιάνει κλικ
        self.play(scene, [it["right"] for it in scene.items])
        self.assertEqual(scene.state, "finish")
        for _ in range(240):
            scene.update(1 / 60)
            if scene.celebrated:
                break
        for _ in range(60 * 10):                            # δεν σβήνει μόνο του
            scene.update(1 / 60)
        self.assertTrue(scene.banner.visible(scene.time))
        self.click(scene, (BANNER_POS[0] + 320, BANNER_POS[1]))   # δίπλα στην πινακίδα: τίποτα
        self.assertEqual(scene.index, 0)
        self.click(scene, (BANNER_POS[0] + 200, BANNER_POS[1] + 60))   # πάνω στην πινακίδα
        self.assertEqual(scene.index, 1)
        self.assertEqual(scene.state, "ready")
        self.assertFalse(scene.banner.visible(scene.time))

    def test_speed_choice_slows_time_and_is_remembered(self):
        for speed, factor in ((0, 0.6), (1, 0.8), (2, 1.0)):
            scene = self.open(speed=2)
            for _ in range(20):
                scene.update(1 / 60)
            self.click(scene, scene.speed_rects[speed].center)      # διαλέγει ταχύτητα και ξεκινά
            self.assertEqual((scene.state, scene.speed_i), ("run", speed))
            for _ in range(60):                            # ένα δευτερόλεπτο
                scene.update(1 / 60)
            self.assertAlmostEqual(scene.runner.time, factor, delta=0.03)
        # η επιλογή μένει: την επόμενη φορά (και στα άλλα παιχνίδια) είναι διαλεγμένη η ίδια
        scene = self.open(speed=2)
        scene.draw(self.app.screen)
        self.click(scene, scene.speed_rects[0].center)
        self.assertEqual(scene.speed_i, 0)
        self.assertEqual(self.app.runner_speed, 0)
        self.assertEqual(scene.btn_speed.label, "Αργά")
        scene.cycle_speed()
        self.assertEqual(scene.btn_speed.label, "Κανονικά")
        import games.words as words
        self.assertEqual(words.open_game(self.app).speed_i, 1)   # ίδια ταχύτητα και στα άλλα παιχνίδια

    def test_every_runner_game_opens_and_draws_every_level(self):
        import games.calc as calc
        import games.numbers as numbers
        import games.words as words
        for game in (numbers, words, calc):
            scene = game.open_game(self.app)
            for i in range(game.LEVEL_COUNT):
                with self.subTest(game=game.GAME_ID, level=i + 1):
                    scene.load(i)
                    for _ in range(5):
                        scene.update(1 / 60)
                    scene.draw(self.app.screen)
                    self.assertEqual(len(scene.items), len(scene.track.choices))
                    if game is calc:                           # οι πόρτες δεν μπαίνουν σε κουτιά
                        for pair in scene.doors:
                            self.assertFalse(pair[0].colliderect(pair[1]))
                            for rect in pair:
                                self.assertGreater(rect.h, 70)
                                self.assertFalse(any(rect.colliderect(pygame.Rect(b)) for b in scene.track.blocks))


if __name__ == "__main__":
    unittest.main()
