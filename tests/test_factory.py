"""Έλεγχοι για το Εργοστάσιο. Τρέξε:  py -m unittest discover tests"""
import os
import random
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from games.factory import LEVEL_COUNT, catalog, levels, logic  # noqa: E402
from games.factory.catalog import HW, ITEMS, OTHER, SW  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def shift(level=0, seed=1):
    return logic.Shift(levels.LEVELS[level], random.Random(seed))


def roll(sh, seconds, step=1 / 60):
    events = []
    for _ in range(int(seconds / step)):
        events += sh.update(step)
    return events


class ContentTests(unittest.TestCase):
    def test_every_object_has_a_drawing(self):
        pygame.init()
        from games.factory import items
        self.assertEqual(set(ITEMS), set(items.DRAW))
        for key in ITEMS:
            with self.subTest(key=key):
                img = items.image(key, 60)
                self.assertEqual(img.get_size(), (60, 60))
                visible = sum(img.get_at((x, y)).a > 0 for x in range(0, 60, 3) for y in range(0, 60, 3))
                self.assertGreater(visible, 40)

    def test_lists_agreed_with_the_teacher(self):
        kinds = {k: sorted(i.key for i in ITEMS.values() if i.kind == k) for k in (HW, SW, OTHER)}
        self.assertEqual(len(kinds[HW]), 12)          # 10 συσκευές + φορητός + στικάκι
        self.assertEqual(len(kinds[SW]), 8)
        self.assertEqual(len(kinds[OTHER]), 12)
        # τίποτα που μπερδεύει: ζώο ποντίκι, τηλέφωνο, αριθμομηχανή, φάκελος, χειριστήριο
        for word in ("τηλέφωνο", "αριθμομηχανή", "φάκελος", "χειριστήριο", "ποντικάκι"):
            self.assertFalse(any(word in i.the for i in ITEMS.values()), word)
        self.assertFalse({"gamepad", "phone", "calculator", "envelope"} & set(ITEMS))

    def test_levels(self):
        self.assertEqual(LEVEL_COUNT, 6)
        for n, lv in enumerate(levels.LEVELS, 1):
            with self.subTest(level=n):
                boxes = (HW, OTHER) if n <= 3 else (HW, SW, OTHER)
                self.assertEqual(tuple(lv["boxes"]), boxes)
                self.assertEqual(set(lv["bag"]), set(boxes))
                self.assertEqual(set(lv["pool"]), set(boxes))
                for kind, keys in lv["pool"].items():
                    self.assertTrue(keys)
                    self.assertTrue(all(ITEMS[k].kind == kind for k in keys))
                self.assertEqual(set(lv["examples"]), set(boxes))
                for kind, keys in lv["examples"].items():
                    self.assertTrue(all(ITEMS[k].kind == kind for k in keys))
                self.assertGreater(lv["gap"], 200)    # δύο αντικείμενα δεν πατάνε το ένα πάνω στο άλλο
                self.assertTrue(lv["goal_text"] and lv["tip"])
        for group in (levels.LEVELS[:3], levels.LEVELS[3:]):
            self.assertEqual([lv["speed"] for lv in group], sorted(lv["speed"] for lv in group))
            self.assertEqual([lv["goal"] for lv in group], sorted(lv["goal"] for lv in group))
        # η πρώτη πίστα έχει μόνο τις πιο γνωστές συσκευές
        self.assertEqual(set(levels.LEVELS[0]["pool"][HW]), set(levels.EASY_HW))

    def test_messages_name_the_right_box(self):
        for key, it in ITEMS.items():
            for box in (HW, SW, OTHER):
                if box == it.kind:
                    continue
                line1, line2 = catalog.wrong_text(key, box)
                self.assertIn(catalog.INTO[box], line1)
                self.assertIn(catalog.INTO[it.kind], line2)
                self.assertLess(len(line2), 70)
            self.assertTrue(catalog.lost_text(key)[0].startswith("Ωχ! Έπεσ"))
        self.assertEqual(catalog.wrong_text("speakers", OTHER)[1], "Τα ηχεία είναι συσκευές: πάνε στο ΥΛΙΚΟ Η/Υ.")
        self.assertEqual(catalog.wrong_text("app_music", OTHER)[1], "Είναι πρόγραμμα για μουσική: πάει στο ΛΟΓΙΣΜΙΚΟ.")
        self.assertEqual(catalog.wrong_text("umbrella", HW),
                         ("Ωχ! Όχι στο ΥΛΙΚΟ Η/Υ.", "Η ομπρέλα δεν είναι του υπολογιστή: πάει στον ΚΑΔΟ."))

    def test_no_train_word(self):
        for f in (ROOT / "games" / "factory").glob("*.py"):
            self.assertNotIn("train", f.read_text(encoding="utf-8").lower(), f.name)


class LogicTests(unittest.TestCase):
    def test_objects_come_along_and_fall_off_the_end(self):
        sh = shift()
        events = roll(sh, 0.1)
        self.assertEqual([e[0] for e in events], ["spawn"])
        first = sh.things[0]
        self.assertGreater(first.x, logic.BELT_START)
        # μέχρι να φτάσει στο τέλος έρχονται κι άλλα, με απόσταση gap μεταξύ τους
        events = roll(sh, (logic.BELT_END - logic.BELT_START) / sh.speed + 0.2)
        self.assertIn(("lost", first), events)
        xs = sorted(t.x for t in sh.things)
        self.assertTrue(all(b - a >= sh.gap - 2 for a, b in zip(xs, xs[1:])))
        self.assertEqual(sh.hearts, 2)
        self.assertEqual(sh.mistakes, [first.key])
        roll(sh, 60)
        self.assertTrue(sh.over)
        self.assertEqual(sh.hearts, 0)
        self.assertEqual(sh.update(1.0), [])          # μετά το τέλος η ταινία δεν κυλά
        self.assertLessEqual(len(sh.lessons()), 3)

    def test_right_box_streak_double_stars_and_heart_back(self):
        sh = shift(3)
        sh.hearts = 2
        stars = []
        for i in range(6):
            t = sh.spawn()
            r = sh.sort(t, t.kind)
            self.assertTrue(r["right"])
            self.assertNotIn(t, sh.things)
            stars.append(r["stars"])
            self.assertEqual(r["super"], i == 4)
            self.assertEqual(r["heart_back"], i == 4)
        self.assertEqual(stars, [1, 1, 1, 1, 2, 2])
        self.assertEqual((sh.got, sh.stars, sh.streak, sh.hearts), (6, 8, 6, 3))
        # λάθος: χάνει καρδιά και το σερί
        t = sh.spawn()
        wrong = next(b for b in sh.boxes if b != t.kind)
        r = sh.sort(t, wrong)
        self.assertFalse(r["right"])
        self.assertEqual((sh.hearts, sh.streak, sh.mistakes), (2, 0, [t.key]))
        t = sh.spawn()
        self.assertEqual(sh.sort(t, t.kind)["stars"], 1)

    def test_goal_finishes_and_belt_speeds_up(self):
        sh = shift(1)
        speeds = []
        while not sh.done:
            speeds.append(sh.speed)
            t = sh.spawn()
            sh.sort(t, t.kind)
        self.assertEqual(sh.got, sh.goal)
        self.assertTrue(sh.finished and not sh.over)
        self.assertEqual(speeds, sorted(speeds))
        self.assertAlmostEqual(sh.speed, sh.base_speed * (1 + logic.ACCEL))

    def test_mix_of_objects(self):
        for n, lv in enumerate(levels.LEVELS):
            sh = shift(n, seed=n)
            keys = [sh.spawn().key for _ in range(len(lv["bag"]) * 8)]
            kinds = [ITEMS[k].kind for k in keys]
            for kind in set(lv["bag"]):
                self.assertEqual(kinds.count(kind), lv["bag"].count(kind) * 8)
            self.assertTrue(all(a != b for a, b in zip(keys, keys[1:])))

    def test_take_put_back_and_front(self):
        sh = shift()
        a = sh.spawn()
        roll(sh, 1.0)
        b = sh.things[-1] if sh.things[-1] is not a else sh.spawn()
        self.assertIs(sh.front(), a)
        sh.take(a)
        self.assertIs(sh.front(), b)
        sh.put_back(a)
        self.assertIs(sh.front(), a)
        self.assertIs(sh.find(b.id), b)


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.app import App
        cls.app = App(headless=True)

    def open(self, level=0, speed=2):
        import games.factory as factory
        self.app.runner_speed = speed
        scene = factory.open_game(self.app)
        scene.load(level)
        return scene

    def run_for(self, scene, seconds):
        for _ in range(int(seconds * 60)):
            scene.update(1 / 60)

    def mouse(self, scene, kind, pos):
        if kind == pygame.MOUSEMOTION:
            scene.handle_event(pygame.event.Event(kind, pos=pos, rel=(0, 0), buttons=(1, 0, 0)))
        else:
            scene.handle_event(pygame.event.Event(kind, button=1, pos=pos))

    def click(self, scene, pos):
        self.mouse(scene, pygame.MOUSEBUTTONDOWN, pos)
        self.mouse(scene, pygame.MOUSEBUTTONUP, pos)

    def key(self, scene, key):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def drag(self, scene, thing, to):
        start = (thing.x, 250)
        self.mouse(scene, pygame.MOUSEBUTTONDOWN, start)
        self.mouse(scene, pygame.MOUSEMOTION, ((start[0] + to[0]) / 2, (start[1] + to[1]) / 2))
        self.mouse(scene, pygame.MOUSEMOTION, to)
        self.mouse(scene, pygame.MOUSEBUTTONUP, to)

    def start(self, scene):
        self.click(scene, scene.speed_rects[scene.speed_i].center)

    def wait_for_item(self, scene, x=200):
        for _ in range(60 * 30):
            scene.update(1 / 60)
            t = scene.target()
            if t is not None and t.x > x:
                return t
        self.fail("δεν ήρθε αντικείμενο")

    def test_starts_only_with_a_click_on_a_speed_shared_with_the_runners(self):
        scene = self.open(speed=0)
        self.run_for(scene, 1)
        self.key(scene, pygame.K_SPACE)
        self.key(scene, pygame.K_LEFT)
        self.click(scene, (640, 650))
        self.run_for(scene, 1)
        self.assertEqual(scene.state, "ready")
        self.assertEqual(scene.shift.things, [])
        self.click(scene, scene.speed_rects[1].center)
        self.assertEqual(scene.state, "run")
        self.assertEqual(self.app.runner_speed, 1)
        import games.numbers as numbers
        self.assertEqual(numbers.open_game(self.app).speed_i, 1)
        # στο «Αργά» η ταινία κυλά πιο αργά
        self.run_for(scene, 2)
        normal = scene.shift.distance
        slow = self.open(speed=0)
        self.start(slow)
        self.run_for(slow, 2)
        self.assertAlmostEqual(slow.shift.distance / normal, 0.6 / 0.8, places=2)

    def test_drag_into_right_box_and_wrong_box(self):
        scene = self.open()
        self.start(scene)
        t = self.wait_for_item(scene)
        box = scene.box_of[t.kind]
        self.drag(scene, t, (box.cx, 480))
        self.assertEqual(scene.shift.got, 1)
        self.run_for(scene, 0.6)
        self.assertIn(t.key, scene.peek[t.kind])
        self.assertEqual(scene.shift.stars, 1)
        # σε λάθος κουτί: καρδιά, σταματά η ταινία και το R2 εξηγεί
        t = self.wait_for_item(scene)
        wrong = next(b for b in scene.boxes if b.kind != t.kind)
        self.drag(scene, t, (wrong.cx, 500))
        self.assertEqual(scene.shift.hearts, 2)
        self.assertTrue(scene.frozen)
        self.assertEqual(scene.message[:2], catalog.wrong_text(t.key, wrong.kind))
        d = scene.shift.distance
        self.run_for(scene, 1.0)
        self.assertEqual(scene.shift.distance, d)
        self.run_for(scene, 2.0)
        self.assertIn(t.key, scene.peek[t.kind])      # πήγε μόνο του στο σωστό κουτί
        self.assertTrue(scene.frozen)
        self.key(scene, pygame.K_SPACE)              # μετά από λίγο, ένα πλήκτρο ξεκινά πάλι την ταινία
        self.assertFalse(scene.frozen)
        self.run_for(scene, 0.5)
        self.assertGreater(scene.shift.distance, d)

    def test_drop_outside_goes_back_and_click_chooses(self):
        scene = self.open()
        self.start(scene)
        first = self.wait_for_item(scene, 420)
        second = next(t for t in scene.shift.things if t is not first) if len(scene.shift.things) > 1 else None
        x = first.x
        self.drag(scene, first, (1200, 200))           # έξω από τα κουτιά: γυρίζει στην ταινία
        self.assertEqual((scene.shift.got, scene.shift.hearts), (0, 3))
        self.run_for(scene, 0.4)
        self.assertIn(first, scene.shift.things)
        self.assertGreaterEqual(first.x, x)
        if second is None:
            second = scene.shift.spawn()
        self.click(scene, (second.x, 250))               # κλικ πάνω του: το διαλέγει για τα βελάκια
        self.assertIs(scene.target(), second)
        key = {HW: pygame.K_LEFT, OTHER: pygame.K_RIGHT}[second.kind]
        self.key(scene, key)
        self.assertNotIn(second, scene.shift.things)
        self.assertEqual(scene.shift.got, 1)
        self.assertIs(scene.target(), first)

    def test_lost_objects_end_the_shift(self):
        scene = self.open(3)
        self.start(scene)
        self.run_for(scene, 60)
        self.assertEqual(scene.state, "over")
        self.assertEqual(len(scene.pile), 3)
        scene.draw(self.app.screen)
        self.assertIn(scene.btn_retry, scene.active_buttons())
        self.key(scene, pygame.K_RETURN)
        self.assertEqual(scene.state, "run")
        self.assertEqual(scene.shift.hearts, 3)

    def test_every_level_can_be_finished_with_the_keys(self):
        keys = {HW: pygame.K_LEFT, SW: pygame.K_DOWN, OTHER: pygame.K_RIGHT}
        scene = self.open(0)
        for n in range(LEVEL_COUNT):
            with self.subTest(level=n + 1):
                self.assertEqual(scene.index, n)
                self.assertEqual(scene.state, "ready")
                scene.draw(self.app.screen)
                self.start(scene)
                for _ in range(60 * 120):
                    scene.update(1 / 60)
                    t = scene.target()
                    if t is not None and t.x > 500 and scene.playing():
                        self.key(scene, keys[t.kind])
                    if scene.state == "done":
                        break
                    if scene.time % 1 < 1 / 60:
                        scene.draw(self.app.screen)
                self.assertEqual(scene.state, "done")
                self.assertEqual(scene.shift.hearts, 3)
                self.assertIn(n + 1, self.app.progress.completed("factory"))
                self.run_for(scene, 0.5)
                scene.draw(self.app.screen)
                self.assertIn(scene.btn_go, scene.active_buttons())
                self.click(scene, scene.btn_go.rect.center)
        self.assertEqual(scene.index, 0)               # μετά την 6η πίστα, πάλι η 1η

    def test_menu_card(self):
        from games import GAMES
        from games.menu import MenuScene
        entry = next(g for g in GAMES if g["id"] == "factory")
        self.assertEqual(entry["title"], "Εργοστάσιο")
        menu = MenuScene(self.app)
        menu.update(0.1)
        menu.draw(self.app.screen)
        self.assertTrue(any(c["game"]["id"] == "factory" for c in menu.cards))


if __name__ == "__main__":
    unittest.main()
