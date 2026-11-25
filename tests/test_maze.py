"""Έλεγχοι για τον Λαβύρινθο. Τρέξε:  py -m unittest discover tests"""
import itertools
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.maze import LEVEL_COUNT, levels, logic  # noqa: E402

SMALL = """
    #######
    #S  # #
    ### # #
    # # # #
    # # # #
    #    G#
    #######
"""


class MazeTests(unittest.TestCase):
    def test_every_maze_is_valid(self):
        self.assertEqual(LEVEL_COUNT, 20)
        sizes = []
        for n, text in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                maze = logic.Maze(text)
                grid = maze.grid
                # κλειστό περίγραμμα, τοίχος σε κάθε γωνία τετραγώνων
                self.assertTrue(set(grid[0]) == set(grid[-1]) == {"#"})
                self.assertTrue(all(row[0] == row[-1] == "#" for row in grid))
                for y in range(0, len(grid), 2):
                    for x in range(0, len(grid[0]), 2):
                        self.assertEqual(grid[y][x], "#", (x, y))
                self.assertEqual(sum(row.count("S") for row in grid), 1)
                self.assertEqual(sum(row.count("G") for row in grid), 1)
                # όλα τα τετράγωνα φτάνονται και δεν υπάρχουν κύκλοι (ένας μόνο σωστός δρόμος)
                reach = {maze.start}
                todo = [maze.start]
                for cell in todo:
                    for d in logic.STEP:
                        if maze.is_open(cell, d) and maze.neighbor(cell, d) not in reach:
                            reach.add(maze.neighbor(cell, d))
                            todo.append(maze.neighbor(cell, d))
                self.assertEqual(len(reach), maze.cols * maze.rows)
                doors = sum(maze.is_open(c, logic.RIGHT) + maze.is_open(c, logic.DOWN) for c in maze.cells())
                self.assertEqual(doors, maze.cols * maze.rows - 1)
                self.assertIsNotNone(maze.solve())
                sizes.append((maze.cols, maze.rows))
        self.assertEqual(sizes[0], (3, 3))
        self.assertEqual(sizes[-1], (19, 12))
        areas = [c * r for c, r in sizes]
        self.assertEqual(areas, sorted(areas))
        self.assertEqual(len(set(areas)), len(areas))      # κάθε λαβύρινθος μεγαλύτερος από τον προηγούμενο

    def test_bad_text_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.Maze("#####\n#S  #\n#####")             # λείπει ο φορτιστής
        with self.assertRaises(ValueError):
            logic.Maze("####\n#SG#\n####")                # ζυγό πλάτος


class RobotTests(unittest.TestCase):
    def test_start_faces_the_open_way(self):
        robot = logic.Robot(logic.Maze(SMALL))
        self.assertEqual(robot.cell, (0, 0))
        self.assertEqual(robot.facing, logic.RIGHT)
        down_only = logic.Maze(levels.LEVELS[3])            # στο 4ο ανοίγει μόνο προς τα κάτω
        self.assertEqual(logic.Robot(down_only).facing, logic.DOWN)

    def test_turns_happen_in_place(self):
        robot = logic.Robot(logic.Maze(SMALL))
        self.assertEqual(robot.command("right"), [("turn", logic.RIGHT, logic.DOWN)])
        self.assertEqual(robot.cell, (0, 0))
        for _ in range(3):
            robot.command("right")
        self.assertEqual(robot.facing, logic.RIGHT)
        robot.command("left")
        self.assertEqual(robot.facing, logic.UP)
        self.assertEqual(robot.trail, [(0, 0)])

    def test_wall_stops_the_robot(self):
        robot = logic.Robot(logic.Maze(SMALL))
        robot.command("right")                               # κοιτάει κάτω, εκεί έχει τοίχο
        self.assertEqual(robot.command("forward"), [("bump", (0, 0), logic.DOWN)])
        self.assertEqual(robot.cell, (0, 0))
        self.assertEqual(robot.bumps, 1)

    def test_back_moves_without_turning(self):
        robot = logic.Robot(logic.Maze(SMALL))
        robot.command("forward")
        self.assertEqual(robot.cell, (1, 0))
        self.assertEqual(robot.command("back"), [("move", (1, 0), (0, 0))])
        self.assertEqual(robot.facing, logic.RIGHT)
        self.assertEqual(robot.trail, [(0, 0), (1, 0), (0, 0)])

    def test_every_level_can_be_driven_to_the_charger(self):
        for n, text in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                maze = logic.Maze(text)
                robot = logic.Robot(maze)
                events = [e for name in logic.commands_for(maze.solve(), robot.facing) for e in robot.command(name)]
                self.assertTrue(robot.done)
                self.assertEqual(events[-1], ("done",))
                self.assertNotIn("bump", [e[0] for e in events])
                self.assertEqual(robot.command("forward"), [])

    def test_unknown_command(self):
        with self.assertRaises(ValueError):
            logic.Robot(logic.Maze(SMALL)).command("jump")


class ProgramTests(unittest.TestCase):
    def test_same_commands_join_into_one_block(self):
        p = logic.Program()
        for name in ("forward", "forward", "forward", "right", "right", "forward", "back"):
            p.add(name)
        self.assertEqual(p.blocks, [["forward", 3], ["right", 2], ["forward", 1], ["back", 1]])
        self.assertEqual([p.seconds(i) for i in range(len(p))], [3, 2, 1, 1])      # 1 τετράγωνο ή ¼ = 1"
        steps = p.steps()
        self.assertEqual(len(steps), 7)
        self.assertEqual(steps[0], (0, "forward", True, False))
        self.assertEqual(steps[2], (0, "forward", False, True))
        self.assertEqual(steps[5], (2, "forward", True, True))
        with self.assertRaises(ValueError):
            p.add("jump")


class BlockTests(unittest.TestCase):
    """Τα μπλοκ γράφουν ακριβώς ό,τι τα μπλοκ του R2 στο Mind+ (φύλλα εργασίας 1α και 1β)."""

    @staticmethod
    def words(parts):
        return " ".join(s for _kind, s in parts)

    def test_wording_matches_mind_plus(self):
        from core import blocks
        self.assertEqual(self.words(blocks.hat()), "R2 starts")
        self.assertEqual(self.words(blocks.move("forward", 2)),
                         "Κινήσου μπροστά με ταχύτητα μικρή για 2 δευτερόλεπτα")
        self.assertEqual(self.words(blocks.move("back", 3)), "Κινήσου πίσω με ταχύτητα μικρή για 3 δευτερόλεπτα")
        self.assertEqual(self.words(blocks.turn("right", 2)), "Στρίψε δεξιά για 2 δευτερόλεπτα")
        self.assertEqual(self.words(blocks.turn("left", 1)), "Στρίψε αριστερά για 1 δευτερόλεπτα")
        self.assertEqual([k for k, _s in blocks.turn("left", 1)], ["text", "drop", "text", "num", "text"])
        self.assertEqual(blocks.number(1.5), "1.5")
        self.assertEqual(blocks.number(4.0), "4")


class MazeSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def run_frames(self, scene, seconds):
        for _ in range(int(seconds * 60)):
            scene.update(1 / 60)

    def key(self, scene, key, down=True):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0,
                                              unicode="", scancode=0))

    def test_arrow_key_presses_the_button(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 0)
        self.key(scene, pygame.K_RIGHT)
        self.assertTrue(scene.controls["right"].pressed(scene.time))
        self.assertFalse(scene.controls["forward"].pressed(scene.time))
        self.assertEqual(scene.robot.facing, logic.DOWN)
        self.key(scene, pygame.K_RIGHT, down=False)
        self.run_frames(scene, 0.5)
        self.assertFalse(scene.controls["right"].pressed(scene.time))
        self.assertAlmostEqual(scene.angle, 180.0)
        scene.draw(self.app.screen)

    def test_bump_shows_message_and_red_light(self):
        from games.maze import art
        from games.maze.scene import MSG, MazeScene
        scene = MazeScene(self.app, 0)
        self.key(scene, pygame.K_DOWN)                      # πίσω: τοίχος
        self.assertEqual(scene.message, MSG["bump"])
        self.assertEqual(scene.led(), art.LED_RED)
        self.run_frames(scene, 0.2)
        scene.draw(self.app.screen)
        self.run_frames(scene, 1.0)
        self.assertEqual(scene.robot.cell, (0, 0))
        self.assertEqual(scene.led(), art.LED_BLUE)

    def test_drive_to_the_charger_with_keys(self):
        from games.maze.scene import MazeScene
        keys = {"forward": pygame.K_UP, "back": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}
        scene = MazeScene(self.app, 2)
        for name in logic.commands_for(scene.maze.solve(), scene.robot.facing):
            self.key(scene, keys[name])
            self.key(scene, keys[name], down=False)
            self.run_frames(scene, 0.15)                    # γρήγορα πατήματα: περιμένουν τη σειρά τους
            scene.draw(self.app.screen)
            self.run_frames(scene, 0.25)
        self.run_frames(scene, 2.0)
        self.assertTrue(scene.robot.done)
        self.assertTrue(scene.celebrated)
        self.assertIn(3, self.app.progress.completed("maze"))
        self.assertEqual(scene.pos, scene.board.center(scene.maze.goal))
        scene.draw(self.app.screen)

    def test_next_button_beside_bravo(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 0)
        go = scene.btn_go.rect.center
        self.assertNotIn(scene.btn_go, scene.active_buttons())   # πριν τον φορτιστή δεν φαίνεται
        for name in logic.commands_for(scene.maze.solve(), scene.robot.facing):
            scene.command(name)
            self.run_frames(scene, 0.5)
        self.run_frames(scene, 10.0)                             # το «Μπράβο» δεν σβήνει μόνο του
        self.assertTrue(scene.celebrated)
        self.assertIn(scene.btn_go, scene.active_buttons())
        scene.draw(self.app.screen)
        self.assertEqual(scene.index, 0)
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=go, button=1))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=go, button=1))
        self.assertEqual(scene.index, 1)
        self.assertFalse(scene.celebrated)
        self.assertNotIn(scene.btn_go, scene.active_buttons())

    def test_quick_presses_all_happen(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 1)                      # 4×3: πάνω σειρά ανοιχτή δεξιά ως το (1, 0)
        for key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_LEFT):
            self.key(scene, key)
            self.key(scene, key, down=False)
        self.run_frames(scene, 1.5)
        self.assertEqual(scene.robot.cell, (1, 0))
        self.assertEqual(scene.robot.facing, logic.RIGHT)
        self.assertEqual(scene.angle % 360, 90.0)

    def test_bump_cancels_waiting_presses(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 0)
        # 1ο μπροστά: πάει στο (1, 0). 2ο: τοίχος. Το 3ο περίμενε και ακυρώνεται μετά το χτύπημα.
        for _ in range(3):
            self.key(scene, pygame.K_UP)
        self.run_frames(scene, 1.5)
        self.assertEqual(scene.robot.cell, (1, 0))
        self.assertEqual(scene.robot.bumps, 1)

    def test_mouse_on_buttons_drives_the_robot(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 0)
        pos = scene.controls["forward"].rect.center
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        self.assertTrue(scene.controls["forward"].pressed(scene.time))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
        self.run_frames(scene, 0.5)
        self.assertEqual(scene.robot.cell, (1, 0))

    def drive_to_charger(self, scene):
        cmds = logic.commands_for(scene.maze.solve(), scene.robot.facing)
        for name in cmds:
            scene.command(name)
            self.run_frames(scene, 0.4)
        self.run_frames(scene, 1.0)
        return cmds

    def test_program_writes_what_the_robot_did(self):
        from games.maze.scene import MazeScene
        scene = MazeScene(self.app, 1)                      # 4×3
        self.key(scene, pygame.K_DOWN)                      # πίσω: τοίχος, δεν γράφεται
        self.run_frames(scene, 1.0)
        self.assertEqual(scene.program.blocks, [])
        cmds = self.drive_to_charger(scene)
        expected = [[k, len(list(g))] for k, g in itertools.groupby(cmds)]
        self.assertEqual(scene.program.blocks, expected)
        self.assertEqual(len(scene.view.blocks), len(expected))
        scene.command("forward")                            # μετά τον φορτιστή δεν γράφεται τίποτα
        self.assertEqual(scene.program.blocks, expected)
        scene.draw(self.app.screen)

    def test_program_view_fits_and_scrolls(self):
        from core import blocks
        from games.maze.scene import PROGRAM_ROWS, Layout
        view = blocks.StackView(Layout("side").canvas, PROGRAM_ROWS)
        widest = blocks.move("forward", 12)
        self.assertLessEqual(view.PAD_X + view.style.width(widest), view.rect.w)     # χωράει στο πλάτος
        # φαίνονται ολόκληρα το R2 starts και 10 εντολές
        self.assertLessEqual(view._row_y(PROGRAM_ROWS - 1) + view.style.step, view.rect.bottom)
        view.set_blocks([widest] * 15)
        self.assertEqual(view.hidden(), (0, 5))
        view.show(14)                                       # το τελευταίο: κυλάει ως κάτω
        self.assertEqual(view.hidden(), (5, 0))
        view.show(2, below=2)
        self.assertEqual(view.target, 3)
        view.scroll_by(-10)
        self.assertEqual(view.target, 0)
        view.jump()
        view.draw(self.app.screen, running=3, fresh=4, fresh_alpha=100)
        # η λωρίδα των μεγάλων λαβυρίνθων: ένα μπλοκ, το τελευταίο
        strip = blocks.StackView(Layout("strip").canvas, 1)
        self.assertLessEqual(strip.PAD_X + strip.style.width(widest), strip.rect.w - 180)   # και το «▲ …»
        self.assertEqual(strip.hidden(), (0, 0))            # άδειο: φαίνεται μόνο το R2 starts
        strip.set_blocks([widest] * 15)
        strip.show(14, below=2)
        self.assertEqual(strip.hidden(), (15, 0))
        strip.scroll_by(-1)
        self.assertEqual(strip.hidden(), (14, 1))
        strip.draw(self.app.screen, fresh=13, fresh_alpha=200)

    def test_green_flag_runs_the_program(self):
        from games.maze.scene import CELEBRATE_AFTER, MSG, RUN_PAUSE, MazeScene
        scene = MazeScene(self.app, 0)
        self.drive_to_charger(scene)
        written = [b[:] for b in scene.program.blocks]
        self.assertTrue(scene.celebrated)
        self.assertIn(scene.btn_run, scene.active_buttons())
        scene.draw(self.app.screen)
        pos = scene.btn_run.rect.center
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
        self.assertTrue(scene.replaying)                    # το R2 γύρισε στην ΑΡΧΗ
        self.assertFalse(scene.celebrated)
        self.assertEqual(scene.robot.cell, scene.maze.start)
        self.assertEqual(scene.message, MSG["run"])
        self.assertNotIn(scene.btn_run, scene.active_buttons())
        self.key(scene, pygame.K_UP)                        # το χειριστήριο δεν δουλεύει όσο τρέχει
        self.assertFalse(scene.controls["forward"].pressed(scene.time))
        self.run_frames(scene, RUN_PAUSE + 0.5)
        self.assertEqual(scene.running, 0)
        scene.draw(self.app.screen)
        # κάθε μπλοκ κρατά όσα δευτερόλεπτα γράφει, και φωτίζονται με τη σειρά
        total = sum(scene.program.seconds(i) for i in range(len(scene.program)))
        seen = []
        for _ in range(int((total - 0.6) * 60)):
            scene.update(1 / 60)
            if scene.running is not None and (not seen or seen[-1] != scene.running):
                seen.append(scene.running)
        self.assertTrue(scene.replaying)
        self.assertEqual(seen, list(range(len(written))))
        self.run_frames(scene, 0.5 + CELEBRATE_AFTER + 0.2)
        self.assertFalse(scene.replaying)
        self.assertIsNone(scene.running)
        self.assertTrue(scene.robot.done)
        self.assertTrue(scene.celebrated)
        self.assertEqual(scene.pos, scene.board.center(scene.maze.goal))
        self.assertEqual(scene.program.blocks, written)     # η εκτέλεση δεν ξαναγράφει το πρόγραμμα
        scene.draw(self.app.screen)

    def test_big_mazes_write_the_program_without_flag(self):
        from games.maze.scene import SIDE_LEVELS, MazeScene
        scene = MazeScene(self.app, SIDE_LEVELS)            # ο 7ος: λωρίδα κάτω, χωρίς σημαία
        self.assertEqual(scene.view.rows, 1)
        cmds = self.drive_to_charger(scene)
        expected = [[k, len(list(g))] for k, g in itertools.groupby(cmds)]
        self.assertEqual(scene.program.blocks, expected)
        self.assertEqual(scene.view.hidden(), (len(expected), 0))      # φαίνεται το τελευταίο
        self.assertTrue(scene.celebrated)
        self.assertNotIn(scene.btn_run, scene.active_buttons())
        self.assertIn(scene.btn_go, scene.active_buttons())
        scene.run_program()                                 # δεν κάνει τίποτα εδώ
        self.assertFalse(scene.replaying)
        scene.mouse = scene.layout.canvas.center            # η ροδέλα δείχνει τις προηγούμενες
        scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=2, flipped=False))
        self.assertEqual(scene.view.hidden(), (len(expected) - 2, 2))
        scene.draw(self.app.screen)

    def test_every_level_draws(self):
        from games.maze.scene import SIDE_LEVELS, MazeScene
        scene = MazeScene(self.app, 0)
        for i in range(LEVEL_COUNT):
            with self.subTest(level=i + 1):
                scene.load(i)
                scene.update(1 / 60)
                scene.draw(self.app.screen)
                self.assertTrue(scene.layout.board.contains(scene.board.frame))
                self.assertEqual(scene.layout.mode, "side" if i < SIDE_LEVELS else "strip")
                self.assertEqual(scene.layout.run_rect is not None, i < SIDE_LEVELS)
                self.assertFalse(scene.board.frame.colliderect(scene.layout.code))

    def test_menu_opens_maze(self):
        from games.maze.scene import MazeScene
        from games.menu import MenuScene
        menu = MenuScene(self.app)
        card = next(c for c in menu.cards if c["game"]["id"] == "maze")
        menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=card["rect"].center, button=1))
        self.assertIsInstance(self.app.scene, MazeScene)


if __name__ == "__main__":
    unittest.main()
