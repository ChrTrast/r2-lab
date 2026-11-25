"""Το παράθυρο και ο κύκλος του παιχνιδιού. Κάθε οθόνη (μενού, παιχνίδι...) είναι μια Scene."""
import pygame

from .save import Progress
from .sound import SoundBank

WIDTH, HEIGHT = 1280, 720


class Scene:
    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass


class App:
    """Οι σκηνές ζωγραφίζουν πάντα σε εικόνα 1280x720 (self.screen).

    Η App τη μεγαλώνει ώστε να γεμίζει την πλήρη οθόνη ή το παράθυρο (με μαύρες λωρίδες
    αν η αναλογία διαφέρει) και μετατρέπει τις θέσεις του ποντικιού πίσω σε 1280x720.
    Έτσι δεν χρειάζεται το pygame.SCALED, που στις παλιότερες εκδόσεις του pygame
    (π.χ. του Ubuntu) κλειδώνει το μέγεθος του παραθύρου.
    """

    def __init__(self, title="Παιχνίδια", data_dir=None, headless=False, fullscreen=False):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                pass
        self.headless = headless
        self.fullscreen = False
        self.window = None
        if headless:
            self.window = pygame.display.set_mode((WIDTH, HEIGHT))
        else:
            self.set_fullscreen(fullscreen)
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self._fit()
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.progress = Progress()
        # εδώ γράφουν τα παιχνίδια τα αρχεία τους (π.χ. τα σχέδια των παιδιών στους Κύβους)
        self.data_dir = data_dir
        self.scene = None
        self.running = True

    # ---------- οθόνη ----------
    def set_fullscreen(self, on):
        """Πλήρης οθόνη στην ανάλυση της οθόνης, αλλιώς παράθυρο που αλλάζει μέγεθος."""
        if on:
            try:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                self.fullscreen = True
                self._fit()
                return
            except pygame.error:
                pass
        self.fullscreen = False
        self.window = pygame.display.set_mode(self._window_size(), pygame.RESIZABLE)
        self._fit()

    @staticmethod
    def _window_size():
        """1280x720, ή μικρότερο (ίδια αναλογία) αν δεν χωράει στην οθόνη."""
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError, pygame.error):
            return WIDTH, HEIGHT
        w = int(min(WIDTH, dw * 0.9, dh * 0.85 * WIDTH / HEIGHT))
        return w, w * HEIGHT // WIDTH

    def _fit(self):
        """Υπολογίζει πού και σε τι μέγεθος μπαίνει η εικόνα 1280x720 στο παράθυρο."""
        self.window = pygame.display.get_surface() or self.window
        if not hasattr(self, "screen"):
            return
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        w, h = max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale))
        self.view = pygame.Rect((ww - w) // 2, (wh - h) // 2, w, h)
        self._window_size_now = (ww, wh)
        self._scaled = None if self.view.size == (WIDTH, HEIGHT) else pygame.Surface(self.view.size, 0, self.screen)

    def to_game(self, pos):
        """Θέση στο παράθυρο -> θέση στην εικόνα 1280x720."""
        return (int((pos[0] - self.view.x) * WIDTH / self.view.w),
                int((pos[1] - self.view.y) * HEIGHT / self.view.h))

    def _game_event(self, e):
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            data = dict(e.dict, pos=self.to_game(e.pos))
            if "rel" in data:
                data["rel"] = (int(e.rel[0] * WIDTH / self.view.w), int(e.rel[1] * HEIGHT / self.view.h))
            return pygame.event.Event(e.type, data)
        return e

    def _present(self):
        window = pygame.display.get_surface()
        if window is not self.window or window.get_size() != self._window_size_now:
            self._fit()   # άλλαξε το παράθυρο (μεγιστοποίηση, τράβηγμα γωνίας, F11)
        if self._scaled is None:
            self.window.blit(self.screen, self.view)
        else:
            self.window.fill((0, 0, 0))
            try:
                pygame.transform.smoothscale(self.screen, self.view.size, self._scaled)
            except ValueError:
                pygame.transform.scale(self.screen, self.view.size, self._scaled)
            self.window.blit(self._scaled, self.view)
        pygame.display.flip()

    # ---------- σκηνές ----------
    def switch(self, scene):
        self.scene = scene

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.set_fullscreen(not self.fullscreen)
                else:
                    self.scene.handle_event(self._game_event(event))
            self.scene.update(dt)
            self.scene.draw(self.screen)
            self._present()
        pygame.quit()
