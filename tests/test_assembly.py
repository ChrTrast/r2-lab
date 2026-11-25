"""Έλεγχοι για τη Συναρμολόγηση. Τρέξε:  py -m unittest discover tests"""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.assembly import logic, steps  # noqa: E402
from games.assembly import parts as P  # noqa: E402
from games.assembly.steps import PARTS, PLUGS, SLOTS, STEPS  # noqa: E402


def finish(build):
    """Βάζει όλα τα κομμάτια και τα βύσματα σωστά, βήμα βήμα."""
    for step in STEPS:
        for sid in step.slots:
            if sid not in build.placed:
                res = build.drop(SLOTS[sid].kind, sid)
                assert res.ok, (sid, res.kind, res.msg)
        for pid in step.plugs:
            if pid not in build.connected:
                res = build.drop_plug(pid, PLUGS[pid].target)
                assert res.ok, (pid, res.kind, res.msg)
        if step.switch:
            assert build.press_switch().ok


class DataTests(unittest.TestCase):
    def test_every_slot_is_in_exactly_one_step(self):
        listed = [sid for s in STEPS for sid in s.slots]
        self.assertEqual(sorted(listed), sorted(SLOTS))
        for sid, slot in SLOTS.items():
            step = STEPS[steps.STEP_INDEX[slot.step]]
            self.assertIn(sid, step.slots)

    def test_plugs_go_to_real_sockets_once(self):
        listed = [pid for s in STEPS for pid in s.plugs]
        self.assertEqual(sorted(listed), sorted(PLUGS))
        targets = [p.target for p in PLUGS.values()]
        self.assertEqual(len(targets), len(set(targets)))
        for p in PLUGS.values():
            self.assertIn(p.target, P.SOCKETS)
            for r in p.requires:
                self.assertIn(r, SLOTS)

    def test_box_has_the_right_number_of_parts(self):
        for kind, part in PARTS.items():
            slots = sum(1 for s in SLOTS.values() if s.kind == kind)
            if part.extra:
                self.assertEqual(slots, 0, kind)
                self.assertTrue(part.why, kind)
            elif kind == "rj11":
                self.assertEqual(slots, steps.RJ_USED)
                self.assertEqual(part.count, 4)        # όπως το κουτί του κιτ
            else:
                self.assertEqual(slots, part.count, kind)

    def test_seven_tasks_of_the_manual_then_the_switch(self):
        self.assertEqual(sorted({s.task for s in STEPS if not s.switch}), list(range(1, 8)))
        self.assertTrue(STEPS[-1].switch)
        self.assertEqual(len(steps.TASK_SHORT), 7)

    def test_only_task_3_turns_the_robot_over(self):
        for s in STEPS:
            self.assertEqual(s.view[2], s.task == 3, s.id)
        for sid in ("line_sensor", "caster"):
            self.assertTrue(SLOTS[sid].under)

    def test_lego_base_stays(self):
        """Η βάση για τουβλάκια μένει μόνιμα (ο δάσκαλος το ζήτησε έτσι)."""
        b = logic.Build(logic.HELP)
        finish(b)
        self.assertIn("lego", b.placed)


class LogicTests(unittest.TestCase):
    def test_every_mode_can_be_finished_without_mistakes(self):
        for mode in logic.MODES:
            with self.subTest(mode=mode):
                b = logic.Build(mode)
                finish(b)
                self.assertTrue(b.finished)
                self.assertEqual(b.mistakes, 0)

    def test_start_from_any_task(self):
        for task in range(1, 8):
            b = logic.Build(logic.GUIDE, task)
            self.assertEqual(b.task, task)
            self.assertTrue(all(b.task_done(t) for t in range(1, task)))
            finish(b)
            self.assertTrue(b.finished)

    def test_motors_left_and_right(self):
        b = logic.Build(logic.HELP)
        for i in range(4):
            b.drop("standoff_long", f"so_long_{i}")
        res = b.drop("motor_left", "motor_r")
        self.assertEqual(res.kind, "wrong")
        self.assertIn("ΑΡΙΣΤΕΡΑ", res.msg[0])
        res = b.drop("motor_right", "motor_l")
        self.assertIn("ΔΕΞΙΑ", res.msg[0])
        self.assertEqual(b.mistakes, 2)
        self.assertTrue(b.drop("motor_left", "motor_l").ok)

    def test_later_step_is_refused(self):
        b = logic.Build(logic.SOLO)
        res = b.drop("wheel", "wheel_l")
        self.assertEqual(res.kind, "later")
        self.assertNotIn("wheel_l", b.placed)
        res = b.drop("wheel", "wheel_l")
        self.assertIn("τώρα", res.msg[1].lower())          # μετά από 2 λάθη το R2 λέει τι χρειάζεται
        self.assertTrue(b.needs_hint)

    def test_caster_needs_the_line_sensor_first(self):
        b = logic.Build(logic.HELP, 3)
        res = b.drop("caster", "caster")
        self.assertEqual(res.kind, "later")
        self.assertIn("γραμμής", res.msg[0])
        self.assertTrue(b.drop("line_sensor", "line_sensor").ok)
        self.assertTrue(b.drop("caster", "caster").ok)

    def test_extra_parts_are_not_needed(self):
        b = logic.Build(logic.SOLO)
        for kind in ("bluetooth", "led", "usb", "screwdriver", "allen"):
            res = b.drop(kind, "so_long_0")
            self.assertEqual(res.kind, "extra")
            self.assertEqual(res.msg, PARTS[kind].why)
        self.assertEqual(b.placed, set())

    def test_only_two_rj11_cables(self):
        b = logic.Build(logic.SOLO, 6)
        self.assertTrue(b.drop("rj11", "rj_ultra").ok)
        self.assertTrue(b.drop("rj11", "rj_line").ok)
        self.assertEqual(b.drop("rj11", "rj_line").kind, "extra")
        self.assertEqual(b.left("rj11"), 2)

    def test_plugs_and_ports(self):
        b = logic.Build(logic.HELP, 6)
        self.assertFalse(b.plug_active("rj_ultra"))         # πρώτα το καλώδιο στον αισθητήρα
        b.drop("rj11", "rj_ultra")
        self.assertTrue(b.plug_active("rj_ultra"))
        res = b.drop_plug("rj_ultra", "I2C")
        self.assertEqual(res.kind, "wrong")
        self.assertIn("A0 / D2", res.msg[0])
        self.assertEqual(b.drop_plug("motor_l", "MA").kind, "wrong")
        self.assertTrue(b.drop_plug("motor_l", "MB").ok)
        self.assertTrue(b.drop_plug("motor_r", "MA").ok)
        self.assertTrue(b.drop_plug("rj_ultra", "A0D2").ok)

    def test_motor_plugs_wait_for_their_step_except_solo(self):
        help_b = logic.Build(logic.HELP, 5)
        solo_b = logic.Build(logic.SOLO, 5)
        for b in (help_b, solo_b):
            b.drop("board", "board")
        self.assertFalse(help_b.plug_active("motor_l"))
        self.assertTrue(solo_b.plug_active("motor_l"))
        self.assertEqual(solo_b.drop_plug("motor_l", "MB").kind, "later")

    def test_tray(self):
        b = logic.Build(logic.HELP)
        self.assertEqual(b.tray(), [("standoff_long", 4)])
        b.drop("standoff_long", "so_long_0")
        self.assertEqual(b.tray(), [("standoff_long", 3)])
        solo = logic.Build(logic.SOLO)
        self.assertEqual([k for k, _ in solo.tray()], [p.kind for p in steps.PART_LIST])

    def test_switch_only_at_the_end(self):
        b = logic.Build(logic.HELP)
        self.assertFalse(b.press_switch().ok)
        self.assertFalse(b.switched)


class DrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((10, 10))

    def test_every_kind_has_a_picture(self):
        from games.assembly import eng3d as E
        from games.assembly import scene
        for kind in PARTS:
            with self.subTest(kind=kind):
                meshes = scene._kind_meshes(kind)
                self.assertTrue(any(m.faces for m in meshes))
                img = E.thumbnail(meshes, (90, 60))
                visible = sum(img.get_at((x, y)).a > 0 for x in range(0, 90, 3) for y in range(0, 60, 3))
                self.assertGreater(visible, 20, kind)

    def test_thing_under_a_plate_stays_hidden(self):
        """Ένα κουτί ακριβώς κάτω από μια πλάκα (όπως ο κινητήρας κάτω από τη βάση) δεν φαίνεται από πάνω."""
        from games.assembly import eng3d as E
        plate, under = E.Mesh(), E.Mesh()
        plate.box(-50, 50, -50, 50, 40, 42, (40, 40, 46), split=3, plate=True)
        under.box(10, 34, -40, -10, 20, 39.5, (250, 200, 40), plate=True)
        cam = E.Camera(146, 24, 3.0, 300, 300)
        img, rect = E.render([plate, under], cam, pygame.Rect(0, 0, 600, 600))
        x, y = cam.proj((22, -25, 39.5))
        c = img.get_at((round(x), round(y)))
        self.assertLess(c.r, 120, "το κίτρινο κουτί φαίνεται μέσα από την πλάκα")

    def test_translucent_keeps_what_is_below(self):
        """Το ακρυλικό πάνελ δεν «σβήνει» την πλακέτα από κάτω του (να μη φαίνεται το ταπέτο)."""
        from games.assembly import eng3d as E
        board, glass = E.Mesh(), E.Mesh()
        board.box(-40, 40, -40, 40, 0, 2, (240, 240, 236), plate=True)
        glass.box(-30, 30, -30, 30, 10, 12, (210, 230, 250), alpha=72, plate=True)
        cam = E.Camera(-30, 40, 3.0, 300, 300)
        img, _ = E.render([board, glass], cam, pygame.Rect(0, 0, 600, 600))
        x, y = cam.proj((0, 0, 12))
        self.assertEqual(img.get_at((round(x), round(y))).a, 255)

    def test_ultrasonic_card_shows_both_eyes(self):
        """Η κάρτα του αισθητήρα υπερήχων τον δείχνει από μπροστά."""
        from games.assembly import scene
        yaw, _ = scene.THUMB_VIEW["ultrasonic"]
        self.assertGreater(abs((yaw + 180) % 360 - 180), 90)

    def test_camera_unproject(self):
        from games.assembly import eng3d as E
        cam = E.Camera(-30, 40, 3.0, 400, 300)
        p = (12.0, 34.0, 56.0)
        sx, sy = cam.proj(p)
        q = cam.unproject(sx, sy, 56.0)
        for a, b in zip(p, q):
            self.assertAlmostEqual(a, b, places=6)


class SceneTests(unittest.TestCase):
    """Παίζει όλο το παιχνίδι με το «ποντίκι», όπως ένα παιδί, στο «Με βοήθεια»."""

    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def ev(self, sc, t, **kw):
        sc.handle_event(pygame.event.Event(t, kw))

    def run_frames(self, sc, n, draw_every=10):
        for i in range(n):
            sc.update(1 / 60)
            if i % draw_every == 0:
                sc.draw(self.app.screen)

    def drag(self, sc, start, end):
        start = (int(start[0]), int(start[1]))
        end = (int(end[0]), int(end[1]))
        self.ev(sc, pygame.MOUSEMOTION, pos=start, rel=(0, 0), buttons=(0, 0, 0))
        self.ev(sc, pygame.MOUSEBUTTONDOWN, pos=start, button=1)
        self.run_frames(sc, 40)
        self.ev(sc, pygame.MOUSEMOTION, pos=end, rel=(0, 0), buttons=(1, 0, 0))
        sc.update(1 / 60)
        self.ev(sc, pygame.MOUSEBUTTONUP, pos=end, button=1)
        self.run_frames(sc, 30)

    def test_play_through(self):
        from games.assembly import open_game, scene
        sc = open_game(self.app)
        sc.draw(self.app.screen)
        mode_card = scene.MODE_RECTS[logic.HELP].center
        self.ev(sc, pygame.MOUSEBUTTONDOWN, pos=mode_card, button=1)
        self.assertEqual(sc.state, "play")
        for step in STEPS:
            self.run_frames(sc, 90)
            if step.switch:
                break
            for sid in step.slots:
                kind = SLOTS[sid].kind
                card = next(r for k, left, r in sc._card_rects() if k == kind and left > 0)
                self.drag(sc, card.center, sc.screen(SLOTS[sid].anchor))
                self.assertIn(sid, sc.build.placed, sid)
            for pid in step.plugs:
                self.drag(sc, sc.screen(P.PLUG_REST[pid][0]), sc.camera().proj(P.SOCKETS[PLUGS[pid].target][0]))
                self.assertIn(pid, sc.build.connected, pid)
        sw = sc.screen(P.SWITCH)
        self.ev(sc, pygame.MOUSEBUTTONDOWN, pos=(int(sw[0]), int(sw[1])), button=1)
        self.run_frames(sc, 120)
        self.assertEqual(sc.state, "done")
        self.assertEqual(sc.build.mistakes, 0)
        sc.start_drive()
        self.run_frames(sc, 60 * 7)
        self.assertEqual(sc.state, "done")

    def test_wrong_place_goes_back_to_the_box(self):
        from games.assembly import open_game
        sc = open_game(self.app)
        sc.start_task = 1
        sc.begin(logic.HELP)
        self.run_frames(sc, 60)
        for i in range(4):
            card = sc._card_rects()[0][2]
            self.drag(sc, card.center, sc.screen(SLOTS[f"so_long_{i}"].anchor))
        self.run_frames(sc, 90)
        card = next(r for k, left, r in sc._card_rects() if k == "motor_left")
        self.drag(sc, card.center, sc.screen(SLOTS["motor_r"].anchor))
        self.assertNotIn("motor_l", sc.build.placed)
        self.assertEqual(sc.build.mistakes, 1)
        self.assertIn("ΑΡΙΣΤΕΡΑ", sc.message[0])


if __name__ == "__main__":
    unittest.main()
