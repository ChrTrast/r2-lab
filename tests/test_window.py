"""Πλήρης οθόνη / παράθυρο: η εικόνα 1280x720 γεμίζει την οθόνη και τα κλικ πέφτουν στο σωστό σημείο."""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from core.app import HEIGHT, WIDTH, App, Scene  # noqa: E402


class Recorder(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.events = []

    def handle_event(self, event):
        self.events.append(event)

    def draw(self, screen):
        screen.fill((200, 30, 30))


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App(headless=True)

    def tearDown(self):
        pygame.display.set_mode((WIDTH, HEIGHT))
        self.app._fit()

    def resize(self, w, h):
        pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.app._fit()

    def test_same_size_needs_no_scaling(self):
        self.assertEqual(self.app.view, pygame.Rect(0, 0, WIDTH, HEIGHT))
        self.assertEqual(self.app.to_game((100, 200)), (100, 200))

    def test_full_hd_fills_the_screen(self):
        self.resize(1920, 1080)
        self.assertEqual(self.app.view, pygame.Rect(0, 0, 1920, 1080))
        self.assertEqual(self.app.to_game((960, 540)), (640, 360))
        self.assertEqual(self.app.to_game((1919, 1079)), (1279, 719))

    def test_4_3_screen_gets_black_bars(self):
        self.resize(1024, 768)
        self.assertEqual(self.app.view, pygame.Rect(0, 96, 1024, 576))
        self.assertEqual(self.app.to_game((0, 96)), (0, 0))
        self.assertEqual(self.app.to_game((512, 384)), (640, 360))

    def test_clicks_and_drawing_follow_the_window_size(self):
        self.resize(1920, 1080)
        scene = Recorder(self.app)
        self.app.switch(scene)
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(1920 // 4, 1080 // 4), button=1))
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(300, 150), rel=(30, 15), buttons=(1, 0, 0)))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.app.running = True
        quit_mock = pygame.quit
        pygame.quit = lambda: None   # να μη κλείσει το pygame για τους άλλους ελέγχους
        try:
            self.app.run()
        finally:
            pygame.quit = quit_mock
        down, motion = scene.events
        self.assertEqual(down.pos, (320, 180))
        self.assertEqual(down.button, 1)
        self.assertEqual(motion.pos, (200, 100))
        self.assertEqual(motion.rel, (20, 10))
        window = pygame.display.get_surface()
        self.assertEqual(tuple(window.get_at((1900, 1060)))[:3], (200, 30, 30))

    def test_f11_switches_between_fullscreen_and_window(self):
        self.app.set_fullscreen(True)
        self.assertTrue(self.app.fullscreen)
        self.app.set_fullscreen(False)
        self.assertFalse(self.app.fullscreen)
        self.assertEqual(pygame.display.get_surface().get_size(), App._window_size())
        x, y = self.app.to_game(self.app.view.center)
        self.assertAlmostEqual(x, WIDTH // 2, delta=1)
        self.assertAlmostEqual(y, HEIGHT // 2, delta=1)


if __name__ == "__main__":
    unittest.main()
