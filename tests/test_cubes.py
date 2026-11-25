"""Έλεγχοι για τους Κύβους. Τρέξε:  py -m unittest discover tests"""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games.cubes import logic, patterns  # noqa: E402


def build(columns, offset=0):
    wall = logic.Wall()
    for i, column in enumerate(columns):
        for ctype in column:
            assert wall.drop(i + offset, ctype)
    return wall


class PatternTests(unittest.TestCase):
    def test_every_pattern_fits_and_uses_given_cubes(self):
        for number, p in enumerate(patterns.BUILT_IN, 1):
            with self.subTest(pattern=number):
                self.assertLessEqual(len(p.columns), logic.COLS)
                used = {t for c in p.columns for t in c}
                self.assertLessEqual(used, set(p.palette))
                self.assertLessEqual(used, set(patterns.cubes_for(p, number)))
                wall = build(p.columns)
                self.assertTrue(logic.matches(wall.columns, p.columns))

    def test_ten_patterns(self):
        self.assertEqual(len(patterns.BUILT_IN), 10)
        from games.cubes import LEVEL_COUNT
        self.assertEqual(LEVEL_COUNT, 10)

    def test_match_anywhere_on_the_wall(self):
        target = patterns.BUILT_IN[0].columns
        self.assertTrue(logic.matches(build(target, offset=4).columns, target))

    def test_two_halves_are_one_cube(self):
        self.assertTrue(logic.matches(build([[10, 10], [11, 2, 11]]).columns, [[1], [2, 2]]))
        self.assertFalse(logic.matches(build([[10]]).columns, [[1]]))

    def test_air_on_top_does_not_count_but_air_below_does(self):
        self.assertTrue(logic.matches(build([[1, 5]]).columns, [[1]]))
        self.assertFalse(logic.matches(build([[1]]).columns, [[5, 1]]))

    def test_gap_between_columns_matters(self):
        self.assertFalse(logic.matches(build([[1], [1]]).columns, [[1], [], [1]]))
        self.assertTrue(logic.matches(build([[1], [], [1]], offset=2).columns, [[1], [], [1]]))

    def test_undo_and_take_top(self):
        wall = build([[1, 2], [3]])
        self.assertEqual(wall.take_top(0), 2)
        self.assertEqual(wall.undo(), (1, 3))
        self.assertEqual(wall.undo(), (0, 1))
        self.assertTrue(wall.empty)
        self.assertIsNone(wall.undo())

    def test_column_holds_ten_cubes(self):
        wall = logic.Wall()
        for _ in range(10):
            self.assertTrue(wall.drop(0, 1))
        self.assertFalse(wall.drop(0, 10))


class CarrierTests(unittest.TestCase):
    """Το R2 στη ράγα, χωρίς γραφικά."""

    def run_for(self, r2, seconds):
        events = []
        for _ in range(int(seconds * 60)):
            events += r2.update(1 / 60)
        return events

    def test_takes_cubes_in_order_and_pushes_them(self):
        from games.cubes.robot import Carrier
        r2 = Carrier(0)
        r2.carry(200, 3, 0, 1)
        r2.carry(80, 1, 0, 2)
        events = self.run_for(r2, 3)
        drops = [e[1]["col"] for e in events if e[0] == "drop"]
        self.assertEqual(drops, [3, 1])
        self.assertEqual(r2.x, 80)
        self.assertFalse(r2.busy)
        self.assertEqual(sum(1 for e in events if e[0] == "drive"), 2)

    def test_cancel_and_park(self):
        from games.cubes.robot import Carrier
        r2 = Carrier(100)
        r2.carry(300, 5, 2, 1)
        self.assertTrue(r2.cancel(5, 2))
        self.assertFalse(r2.cancel(5, 2))
        r2.park_x = 0
        events = self.run_for(r2, 2)
        self.assertEqual([e for e in events if e[0] == "park"], [("park",)])
        self.assertTrue(r2.parked)
        self.assertEqual(r2.x, 0)

    def test_hurries_when_many_cubes_wait(self):
        from games.cubes.robot import Carrier
        r2 = Carrier(0)
        self.assertEqual(r2.hurry, 1.0)
        for n in range(6):
            r2.carry(40, 0, n, 1)
        self.assertGreater(r2.hurry, 2)


class CubesSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pygame
        from core.app import App
        cls.pygame = pygame
        cls.app = App(headless=True)

    def click(self, scene, pos, button=1):
        pg = self.pygame
        scene.handle_event(pg.event.Event(pg.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
        scene.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=pos, button=button))
        scene.handle_event(pg.event.Event(pg.MOUSEBUTTONUP, pos=pos, button=button))

    @staticmethod
    def settle(scene, seconds=30):
        """Τρέχει το παιχνίδι ώσπου το R2 να αφήσει όλους τους κύβους και να πέσουν."""
        for _ in range(int(seconds * 60)):
            scene.update(1 / 60)
            if not scene.carrier.busy and not scene.falling:
                break

    def test_build_first_pattern_with_mouse(self):
        from games.cubes import scene as cs
        from games.maze import art as r2art
        scene = cs.CubesScene(self.app, 0)
        target = scene.pattern.columns
        for i, column in enumerate(target):
            for ctype in column:
                slot = scene.slot_rects()[scene.palette.index(ctype)]
                self.click(scene, slot.center)
                self.click(scene, (cs.WALL.x + (i + 2) * cs.CUBE + 5, cs.WALL.y + 10))
            for _ in range(30):
                scene.update(1 / 60)
                scene.draw(self.app.screen)
        self.settle(scene)
        self.assertTrue(scene.matched)
        self.assertIn(1, self.app.progress.completed("cubes"))
        # το R2 πηγαίνει στον φορτιστή, το LED γίνεται πράσινο και μετά έρχεται η γιορτή
        for _ in range(240):
            scene.update(1 / 60)
        self.assertTrue(scene.carrier.parked)
        self.assertEqual(scene.carrier.x, cs.DOCK_X)
        self.assertEqual(scene._led(), r2art.LED_GREEN)
        self.assertTrue(scene.celebrated)
        scene.draw(self.app.screen)
        # δεξί κλικ βγάζει τον πάνω κύβο και το σχέδιο δεν ταιριάζει πια
        self.click(scene, (cs.WALL.x + 2 * cs.CUBE + 5, cs.WALL.bottom - 5), button=3)
        self.assertFalse(scene.matched)
        self.assertNotEqual(scene._led(), r2art.LED_GREEN)

    def test_cube_waits_for_r2(self):
        from games.cubes import scene as cs
        scene = cs.CubesScene(self.app, 0)
        scene.drop(7, 1)
        self.assertEqual(scene.wall.columns[7], [1])        # γράφτηκε στον τοίχο...
        self.assertTrue(scene.carrier.busy)                 # ...αλλά τον κρατάει ακόμα το R2
        self.assertEqual(scene.carrier.carrying["col"], 7)
        scene.update(1 / 60)
        scene.draw(self.app.screen)
        self.settle(scene)
        self.assertEqual(scene.carrier.x, cs.stop_x(7))
        self.assertFalse(scene.carrier.busy)

    def test_undo_takes_the_cube_back_from_r2(self):
        from games.cubes import scene as cs
        scene = cs.CubesScene(self.app, 0)
        scene.drop(5, 1)
        scene.drop(5, 2)
        scene.undo()
        self.assertEqual(scene.wall.columns[5], [1])
        self.assertEqual([j["ctype"] for j in scene.carrier.jobs], [1])
        scene.take_top(5)
        self.assertFalse(scene.carrier.busy)
        self.assertTrue(scene.wall.empty)

    def test_full_column_turns_led_red(self):
        from games.cubes import scene as cs
        from games.maze import art as r2art
        scene = cs.CubesScene(self.app, 0)
        for _ in range(10):
            scene.drop(0, 1)
        self.settle(scene)
        scene.drop(0, 1)
        self.assertEqual(scene.message, cs.MSG["full"])
        self.assertEqual(scene._led(), r2art.LED_RED)
        scene.draw(self.app.screen)
        for _ in range(60):
            scene.update(1 / 60)
        self.assertEqual(scene._led(), r2art.LED_BLUE)

    def test_free_play_is_not_saved(self):
        from games.cubes import scene as cs
        scene = cs.CubesScene(self.app, None)
        self.assertFalse(hasattr(scene, "btn_save"))
        scene.drop(3, 1)
        scene.drop(4, 6)
        self.settle(scene)
        self.assertTrue(scene.free)
        self.assertFalse(scene.matched)
        scene.draw(self.app.screen)
        scene.next_pattern()                        # «Επόμενο» πηγαίνει στο σχέδιο 1
        self.assertEqual(scene.index, 0)
        self.assertEqual(len(scene.dots()), len(patterns.BUILT_IN))

    def test_menu_opens_cubes(self):
        from games.cubes.scene import CubesScene
        from games.menu import MenuScene
        menu = MenuScene(self.app)
        card = next(c for c in menu.cards if c["game"]["id"] == "cubes")
        self.click(menu, card["rect"].center)
        self.assertIsInstance(self.app.scene, CubesScene)


if __name__ == "__main__":
    unittest.main()
