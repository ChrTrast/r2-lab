"""Έλεγχοι για το «Ακολούθησε» (line follower) και το μενού. Τρέξε:  py -m unittest discover tests"""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games.line_follow import logic  # noqa: E402
from games.line_follow.levels import LEVELS  # noqa: E402


def run_robot(board, seconds=90, dt=1 / 60):
    robot = logic.Robot()
    robot.start()
    events = []
    for _ in range(int(seconds / dt)):
        events += [e for e in robot.update(dt, board) if e != "enter"]
        if robot.state in ("idle", "arrived"):
            break
    return robot, events


def solved_board(level, solution=None):
    board = level.board()
    for cell, ptype in solution or logic.solve(*level.solve_args()):
        board.place(cell, ptype)
    return board


NEW = [(n, level) for n, level in enumerate(LEVELS, 1) if level.special]


class LevelTests(unittest.TestCase):
    def test_every_level_can_be_solved(self):
        for number, level in enumerate(LEVELS, 1):
            with self.subTest(level=number):
                solution = logic.solve(*level.solve_args())
                self.assertIsNotNone(solution)
                for cell, _ in solution:
                    self.assertTrue(level.board().free(cell))
                board = solved_board(level, solution)
                self.assertTrue(board.follow()[0])
                robot, events = run_robot(board)
                self.assertEqual(robot.state, "arrived")
                self.assertEqual([e for e in events if e != "gear"], ["arrived"])
                self.assertEqual(events.count("gear"), len(level.gears))
                self.assertEqual(robot.collected, set(level.gears))

    def test_first_levels_step_by_step(self):
        """Πίστες 1-11: 1-5 λύσεις, ως 12 κομμάτια, κανένα περιττό κομμάτι, μήνυμα και σκηνικό σε κάθε εμπόδιο."""
        first = LEVELS[:11]
        self.assertEqual(len(first), 11)
        for number, level in enumerate(first, 1):
            with self.subTest(level=number):
                self.assertFalse(level.special)
                self.assertTrue(level.hint)
                self.assertEqual(len(level.kinds), len(level.blocked))
                solutions = list(logic.iter_solutions(*level.solve_args()))
                self.assertTrue(1 <= len(solutions) <= 5)
                longest = max(solutions, key=len)
                self.assertLessEqual(len(longest), 12)
                used = tuple(sum(1 for _, p in longest if p == t) for t in logic.PIECE_TYPES)
                self.assertEqual(used, level.pieces)
        self.assertEqual(len({(lv.pieces, lv.blocked) for lv in first}), 11)   # καμία πίστα δεν επαναλαμβάνεται

    def test_four_new_levels_at_the_end(self):
        self.assertEqual([n for n, _ in NEW], [12, 13, 14, 15])
        self.assertTrue(all(level.gears and level.hint for _, level in NEW))

    def test_new_levels_are_not_too_hard(self):
        """Σύντομη λύση (έως 9 κομμάτια), λίγες λύσεις, και ένα κομμάτι παραπάνω από κάθε τύπο που χρειάζεται."""
        for number, level in NEW:
            with self.subTest(level=number):
                solutions = list(logic.iter_solutions(*level.solve_args()))
                self.assertTrue(1 <= len(solutions) <= 3)
                shortest = min(solutions, key=len)
                self.assertLessEqual(len(shortest), 9)
                for ptype, given in zip(logic.PIECE_TYPES, level.pieces):
                    needed = sum(1 for _, p in shortest if p == ptype)
                    self.assertEqual(given, needed + 1 if needed else 0)

    def test_river_is_crossed_on_a_bridge(self):
        for number, level in NEW:
            if not level.water:
                continue
            with self.subTest(level=number):
                bridges = {cell for cell, _ in level.fixed if cell in level.water}
                self.assertGreaterEqual(len(bridges), 2)
                self.assertTrue(set(level.water) - bridges <= set(level.closed))
                for solution in logic.iter_solutions(*level.solve_args()):
                    visited = solved_board(level, solution).trace()[1]
                    self.assertEqual(sum(1 for cell in visited if cell in level.water), 1)

    def test_every_solution_uses_the_crossing_twice(self):
        for number, level in NEW:
            crossings = [cell for cell, ptype in level.fixed if ptype == logic.CROSS]
            if crossings:
                with self.subTest(level=number):
                    for solution in logic.iter_solutions(*level.solve_args()):
                        visited = solved_board(level, solution).trace()[1]
                        self.assertEqual(visited.count(crossings[0]), 2)


class RobotTests(unittest.TestCase):
    def test_empty_board_robot_turns_back_home(self):
        robot, events = run_robot(logic.Board())
        self.assertEqual(events, ["turn", "home"])
        self.assertEqual((robot.state, robot.cell, robot.exit), ("idle", logic.HOME, logic.W))

    def test_gap_in_line_sends_robot_back(self):
        level = LEVELS[1]
        solution = logic.solve(level.pieces, level.blocked)
        board = logic.Board(level.blocked)
        for cell, ptype in solution[:-2]:
            board.place(cell, ptype)
        self.assertFalse(board.follow()[0])
        robot, events = run_robot(board)
        self.assertEqual(events, ["turn", "home"])
        self.assertEqual(robot.state, "idle")

    def test_crossing_goes_straight(self):
        for side in (logic.W, logic.E, logic.N, logic.S):
            self.assertEqual(logic.other_end(logic.CROSS, side), logic.OPPOSITE[side])

    def test_closed_barrier_sends_robot_back_and_gears_return(self):
        level = LEVELS[11]
        # μια γραμμή που φτάνει στον φορτιστή χωρίς να περνά από όλα τα γρανάζια
        for path in logic.iter_solutions((9,) * 6, level.closed, level.fixed):
            board = solved_board(level, path)
            reached, visited = board.trace()
            if board.missing_gears(visited):
                break
        self.assertTrue(reached)
        self.assertFalse(board.follow()[0])
        robot = logic.Robot()
        robot.start()
        events = []
        for _ in range(60 * 90):
            events += [e for e in robot.update(1 / 60, board) if e != "enter"]
            if robot.state == "idle":
                break
        self.assertIn("barrier", events)
        self.assertNotIn("turn", events)
        self.assertEqual(events[-1], "home")
        self.assertEqual(robot.collected, set())     # τα γρανάζια ξαναμπαίνουν στη θέση τους

    def test_fixed_pieces_and_water_take_no_pieces(self):
        level = LEVELS[14]
        board = level.board()
        for cell, ptype in level.fixed:
            self.assertFalse(board.free(cell))
            self.assertEqual(board.piece_at(cell), ptype)
        for cell in level.water:
            self.assertFalse(board.free(cell))

    def test_wrong_piece_blocks_the_way(self):
        board = logic.Board()
        board.place(logic.FIRST_CELL, 5)   # κάθετη γραμμή: δεν μπαίνει από δεξιά
        self.assertFalse(board.follow()[0])

    def test_curves_follow_quarter_circles(self):
        for ptype, (a, b) in logic.PIECES.items():
            for t in (0.0, 0.5, 1.0):
                (u, v), _ = logic.point_on_piece(a, b, t)
                self.assertTrue(-1e-9 <= u <= 1 + 1e-9 and -1e-9 <= v <= 1 + 1e-9, (ptype, t, u, v))
            start = logic.point_on_piece(a, b, 0)[0]
            end_reversed = logic.point_on_piece(b, a, 1)[0]
            self.assertAlmostEqual(start[0], end_reversed[0])
            self.assertAlmostEqual(start[1], end_reversed[1])


class SceneTests(unittest.TestCase):
    """Παίζει ένα επίπεδο με «κλικ» του ποντικιού, χωρίς παράθυρο."""

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

    def test_play_level_with_mouse(self):
        from games.line_follow.scene import LineFollowScene
        scene = LineFollowScene(self.app, 6)
        level = LEVELS[6]
        for cell, ptype in logic.solve(level.pieces, level.blocked):
            self.click(scene, scene.slots[logic.PIECE_TYPES.index(ptype)].center)
            x, y = scene.geo.pt(cell[0] + 0.5, cell[1] + 0.5, 16)
            self.click(scene, (int(x), int(y)))
        self.assertTrue(scene.complete)
        self.assertTrue(scene.locked)          # mode 0: το ταμπλό κλειδώνει
        self.click(scene, scene.btn_go.rect.center)
        for _ in range(60 * 60):
            scene.update(1 / 60)
            if scene.arrived:
                break
        scene.draw(self.app.screen)
        self.assertTrue(scene.arrived)

    def test_hard_levels_play_to_the_end(self):
        from games.line_follow.scene import MSG, LineFollowScene
        for number, level in NEW:
            with self.subTest(level=number):
                scene = LineFollowScene(self.app, number - 1)
                self.assertEqual(scene.message, level.hint)
                for cell, _ in level.fixed:          # τα σταθερά κομμάτια δεν βγαίνουν
                    x, y = scene.geo.pt(cell[0] + 0.5, cell[1] + 0.5, 16)
                    self.click(scene, (int(x), int(y)), button=3)
                    self.assertIn(cell, scene.board.fixed)
                    self.assertFalse(scene.can_place(cell))
                solution = logic.solve(*level.solve_args())
                for cell, ptype in solution[:-1]:
                    scene.place(cell, ptype)
                self.assertFalse(scene.complete)
                scene.place(*solution[-1])
                self.assertTrue(scene.complete)
                self.assertEqual(scene.message, MSG["ready"])
                gears_seen, opened = 0, False
                for _ in range(60 * 60):
                    scene.update(1 / 60)
                    gears_seen = max(gears_seen, len(scene.gear_fx))
                    opened = opened or scene.barrier_open >= 1
                    if scene.arrived:
                        break
                    if _ % 90 == 0:
                        scene.draw(self.app.screen)
                scene.draw(self.app.screen)
                self.assertTrue(scene.arrived)
                self.assertEqual(gears_seen, len(level.gears))
                self.assertTrue(opened)

    def test_missing_gear_message(self):
        from games.line_follow.scene import MSG, LineFollowScene
        scene = LineFollowScene(self.app, 11)
        level = LEVELS[11]
        for path in logic.iter_solutions((9,) * 6, level.closed, level.fixed):
            board = solved_board(level, path)
            if board.missing_gears(board.trace()[1]):
                break
        scene.counts = {t: 9 for t in logic.PIECE_TYPES}
        for cell, ptype in path:
            scene.place(cell, ptype)
        self.assertFalse(scene.complete)
        self.assertEqual(scene.message, MSG["gears"])

    def assert_draws_something(self, scene):
        screen = self.app.screen
        screen.fill((0, 0, 0))
        scene.update(1 / 60)
        scene.draw(screen)
        colors = {tuple(screen.get_at((x, y)))[:3] for x in range(40, 1280, 160) for y in range(40, 720, 120)}
        self.assertGreater(len(colors), 5, f"{type(scene).__name__} left the screen empty")

    def test_scenes_draw_on_screen(self):
        from core.app import Scene
        from games.connect.scene import ConnectScene
        from games.cubes.scene import CubesScene
        from games.menu import MenuScene
        from games.line_follow.scene import LineFollowScene
        for cls in (MenuScene, LineFollowScene, CubesScene, ConnectScene):
            with self.subTest(scene=cls.__name__):
                self.assertIsNot(cls.draw, Scene.draw)
                self.assertIsNot(cls.update, Scene.update)
                self.assert_draws_something(cls(self.app))

    def test_menu_holds_any_number_of_games(self):
        from games.menu import PER_PAGE, MenuScene, card_rects
        area = self.pygame.Rect(0, 140, 1280, 495)
        for n in range(1, PER_PAGE + 1):
            rects = card_rects(n)
            self.assertEqual(len(rects), n)
            for i, r in enumerate(rects):
                self.assertTrue(area.contains(r), (n, r))
                self.assertEqual(r.collidelist(rects[:i]), -1, (n, r))
        ideas = [{"id": f"idea{i}", "title": f"Ιδέα {i}"} for i in range(11)]
        menu = MenuScene(self.app, ideas)
        self.app.switch(menu)
        self.assertEqual((menu.pages, len(menu.cards)), (2, PER_PAGE))
        menu.show_page(1)
        self.assertEqual(len(menu.cards), 3)
        self.assert_draws_something(menu)
        self.click(menu, menu.cards[0]["rect"].center)    # «Σύντομα!»: δεν ανοίγει
        self.assertIs(self.app.scene, menu)

    def test_menu_opens_line_follow(self):
        from games.menu import MenuScene, window_icon
        from games.line_follow.scene import LineFollowScene
        self.assertEqual(window_icon().get_size(), (64, 64))
        menu = MenuScene(self.app)
        menu.update(1 / 60)
        menu.draw(self.app.screen)
        self.click(menu, menu.cards[0]["rect"].center)
        self.assertIsInstance(self.app.scene, LineFollowScene)

    def test_each_launch_starts_from_level_one(self):
        import games.cubes
        import games.line_follow
        from core.save import Progress
        old = self.app.progress
        try:
            self.app.progress = Progress()          # όπως όταν ανοίγει ξανά το πρόγραμμα
            self.assertEqual(games.line_follow.open_game(self.app).level_index, 0)
            self.assertEqual(games.cubes.open_game(self.app).index, 0)
            self.app.progress.mark("line_follow", 1)       # στο ίδιο άνοιγμα συνεχίζει από την επόμενη
            self.assertEqual(games.line_follow.open_game(self.app).level_index, 1)
        finally:
            self.app.progress = old
        self.assertFalse(hasattr(Progress(), "save"))   # δεν γράφεται αρχείο


if __name__ == "__main__":
    unittest.main()
