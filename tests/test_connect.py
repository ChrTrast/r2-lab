"""Έλεγχοι για το «Ένωσε». Τρέξε:  py -m unittest discover tests"""
import itertools
import math
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.connect import logic, pictures  # noqa: E402


class LogicTests(unittest.TestCase):
    def test_dots_in_order_draw_lines(self):
        game = logic.DotGame([([(0, 0), (100, 0), (100, 100)], 0)])
        self.assertEqual(game.click((0, 0)), [("dot", 0)])
        self.assertEqual(game.click((101, 2)), [("dot", 1), ("line", 0, 1)])
        self.assertEqual(game.click((100, 100)),
                         [("dot", 2), ("line", 1, 2), ("line", 2, 0), ("group", 0), ("done",)])
        self.assertTrue(game.done)
        self.assertEqual(game.click((0, 0)), [])

    def test_wrong_dot_and_miss(self):
        game = logic.DotGame([([(0, 0), (200, 0)], None)])
        self.assertEqual(game.click((200, 0)), [("wrong", 1)])
        self.assertEqual(game.click((80, 80)), [("miss",)])
        self.assertEqual(game.next, 0)

    def test_groups_do_not_join(self):
        game = logic.DotGame([([(0, 0), (100, 0)], None), ([(0, 200), (100, 200)], None)])
        events = [e for p in game.dots for e in game.click(p)]
        self.assertEqual(game.lines, [(0, 1), (2, 3)])
        self.assertIn(("group", 0), events)
        self.assertEqual(events[-1], ("done",))


class PictureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_dots_fit_and_are_not_too_close(self):
        w, h = pictures.CANVAS
        for pic in pictures.PICTURES:
            with self.subTest(picture=pic.name):
                dots = [p for points, _ in pic.groups for p in points]
                self.assertGreaterEqual(len(dots), 5)
                for x, y in dots:
                    self.assertTrue(20 <= x <= w - 20 and 20 <= y <= h - 20, (x, y))
                closest = min(math.dist(a, b) for a, b in itertools.combinations(dots, 2))
                self.assertGreaterEqual(closest, 28)

    def test_each_number_sits_by_its_own_dot(self):
        for pic in pictures.PICTURES:
            dots = [p for points, _ in pic.groups for p in points]
            for i, label in enumerate(logic.label_positions(pic.groups)):
                own = math.dist(label, dots[i])
                other = min(math.dist(label, d) for j, d in enumerate(dots) if j != i)
                with self.subTest(picture=pic.name, dot=i + 1):
                    self.assertLess(own + 6, other)

    def test_every_picture_draws(self):
        for pic in pictures.PICTURES:
            with self.subTest(picture=pic.name):
                surf = pic.backdrop()
                self.assertEqual(surf.get_size(), pictures.CANVAS)
                pic.sketch(surf, pictures.make_tf(), pictures.OUTLINE)
                for t in (0.0, 0.7, 3.3, 9.9):
                    pic.final(surf, t)

    def test_named_groups_match(self):
        for pic in pictures.PICTURES:
            if pic.group_names:
                self.assertEqual(len(pic.group_names), len(pic.groups))

    def test_r2_home_is_away_from_the_dots(self):
        """Η γωνία όπου περιμένει το R2 και μπαίνει ο φορτιστής δεν σκεπάζει τελείες ή αριθμούς."""
        for pic in pictures.PICTURES:
            home = logic.home_position(pic.groups, pictures.CANVAS, side=pic.home)
            dots = [p for points, _ in pic.groups for p in points]
            near = min(math.dist(home, p) for p in dots + logic.label_positions(pic.groups))
            with self.subTest(picture=pic.name):
                self.assertGreater(near, 90)


class ConnectSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def click(self, scene, pos):
        scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))

    def run_until(self, scene, done, seconds=30):
        for _ in range(int(seconds * 60)):
            if done():
                return
            scene.update(1 / 60)
            scene.draw(self.app.screen)
        self.fail("δεν έγινε εγκαίρως")

    def test_finish_a_picture_with_mouse(self):
        from games.connect import scene as cs
        scene = cs.ConnectScene(self.app, 7)          # αστερισμοί: ομάδες με ονόματα
        bx, by = cs.BOARD.topleft
        self.assertEqual(scene.painter.pos, scene.home)
        self.click(scene, (bx + 5, by + 5))           # κλικ στο κενό
        self.assertTrue(scene.message.startswith("Ψάξε"))
        for x, y in scene.game.dots:
            self.click(scene, (bx + int(x) + 3, by + int(y) - 3))
            scene.update(1 / 60)
        self.assertTrue(scene.game.done)
        self.assertIsNone(scene.drawn_time)           # το R2 ζωγραφίζει ακόμα
        self.click(scene, (bx + 300, by + 300))       # κλικ πριν τελειώσει: δεν αλλάζει εικόνα
        self.assertEqual(scene.index, 7)
        self.run_until(scene, lambda: scene.celebrated)
        # το R2 ζωγράφισε όλες τις γραμμές, με σηκωμένο μαρκαδόρο ανάμεσα στους αστερισμούς
        dots = scene.game.dots
        self.assertEqual(scene.painter.ink, [(dots[a], dots[b]) for a, b in scene.game.lines])
        self.assertEqual(scene.painter.pos, scene.home)   # και πήγε στον φορτιστή
        self.assertIsNotNone(scene.charge_time)
        self.assertIn(8, self.app.progress.completed("connect"))

    def test_click_on_the_drawing_opens_the_next(self):
        from games.connect import scene as cs
        scene = cs.ConnectScene(self.app, 0)
        bx, by = cs.BOARD.topleft
        for x, y in scene.game.dots:
            self.click(scene, (bx + int(x), by + int(y)))
        self.run_until(scene, lambda: scene.can_go_next)
        self.click(scene, (bx + 480, by + 288))
        self.assertEqual(scene.index, 1)
        self.assertFalse(scene.game.done)
        self.assertEqual(scene.painter.pos, scene.home)

    def test_painter_draws_only_with_pen_down(self):
        from games.connect.scene import Painter
        p = Painter((0, 0))
        p.go((100, 0), pen=False)
        p.go((100, 100), pen=True)
        t = 0.0
        while p.busy:
            t += 1 / 60
            p.update(t)
        self.assertEqual(p.pos, (100, 100))
        self.assertEqual(p.ink, [((100, 0), (100, 100))])
        self.assertAlmostEqual(p.angle, 180)        # κοιτάει κάτω

    def test_menu_opens_connect(self):
        from games.connect.scene import ConnectScene
        from games.menu import MenuScene
        menu = MenuScene(self.app)
        card = next(c for c in menu.cards if c["game"]["id"] == "connect")
        self.click(menu, card["rect"].center)
        self.assertIsInstance(self.app.scene, ConnectScene)


if __name__ == "__main__":
    unittest.main()
