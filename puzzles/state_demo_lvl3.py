import pygame

CYAN = (0, 235, 245)
WHITE = (30, 30, 30)        # text colour on the grey notebook paper
INK = (40, 40, 50)
YELLOW = (255, 195, 50)
PAPER_DARK = (170, 175, 182)
LAMP = {
    "RED": (255, 57, 70),
    "AMBER": (255, 195, 50),
    "GREEN": (55, 245, 135),
}

# (current state, button) -> next state. Anything else goes back to RED.
RULES = {("RED", "A"): "AMBER", ("AMBER", "B"): "GREEN"}


class MiniStateDemo:
    """A tiny playable state machine for the notebook page."""

    def __init__(self):
        self.reset()
        self.buttons = {}
        self._fonts = {}

    def reset(self):
        self.state = "RED"
        self.steps = 0
        self.fired = None          # which table row lit up
        self.message = ("You are in RED. Press A or B to see what happens.")

    def _font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.SysFont("monospace", size, bold=True)
        return self._fonts[size]

    def press(self, button):
        if self.state == "GREEN":
            self.message = "The lock is open! Press RESET to play again."
            return
        before = self.state
        self.steps += 1
        if (before, button) in RULES:
            self.state = RULES[(before, button)]
            self.fired = (before, button)
            self.message = (
                f"You were in {before}. You pressed {button}. "
                f"Rule: {before} + {button} -> {self.state}. "
                f"Now you are in {self.state}."
            )
            if self.state == "GREEN":
                self.message += " GREEN means OPEN. You did it!"
        else:
            self.state = "RED"
            self.fired = "other"
            self.message = (
                f"You were in {before}. {button} is the wrong button here, "
                "so the lock goes back to RED."
            )

    def handle_event(self, event):
        """Returns True if the event was used."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    self.reset() if name == "RESET" else self.press(name)
                    return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                self.press("A")
                return True
            if event.key == pygame.K_b:
                self.press("B")
                return True
        return False

    def _wrap(self, text, font, width):
        lines, line = [], ""
        for word in text.split():
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def draw(self, screen, rect):
        """Draw inside `rect` (about 520 x 190 pixels or larger)."""
        pygame.draw.rect(screen, (205, 208, 214), rect)
        pygame.draw.rect(screen, INK, rect, 2)
        title = self._font(14).render("TRY IT: REACH GREEN", True, INK)
        screen.blit(title, (rect.x + 12, rect.y + 8))

        # lamp (the state)
        cx, cy = rect.x + 70, rect.y + 80
        pygame.draw.circle(screen, LAMP[self.state], (cx, cy), 32)
        pygame.draw.circle(screen, INK, (cx, cy), 32, 3)
        name = self._font(13).render(f"STATE: {self.state}", True, INK)
        screen.blit(name, name.get_rect(center=(cx, cy + 50)))

        # buttons (the input)
        self.buttons = {}
        labels = [("A", "A"), ("B", "B"), ("RESET", "RESET")]
        bx = rect.x + 140
        mouse = pygame.mouse.get_pos()
        for key, text in labels:
            w = 90 if key == "RESET" else 56
            r = pygame.Rect(bx, rect.y + 50, w, 36)
            self.buttons[key] = r
            hover = r.collidepoint(mouse)
            pygame.draw.rect(screen, (235, 238, 242) if hover else (222, 225, 230), r)
            pygame.draw.rect(screen, INK, r, 2)
            t = self._font(14).render(text, True, INK)
            screen.blit(t, t.get_rect(center=r.center))
            bx += w + 10

        # rule table (the transitions); the row that just fired is lit
        tx, ty = rect.x + 140, rect.y + 100
        rows = [
            (("RED", "A"), "RED  + A  ->  AMBER"),
            (("AMBER", "B"), "AMBER + B  ->  GREEN"),
            ("other", "anything else -> RED"),
        ]
        for i, (key, text) in enumerate(rows):
            row = pygame.Rect(tx, ty + i * 22, 230, 20)
            if self.fired == key:
                pygame.draw.rect(screen, YELLOW, row)
            t = self._font(12).render(text, True, INK)
            screen.blit(t, (row.x + 6, row.y + 3))

        # plain-English explanation of the last press
        font = self._font(12)
        lines = self._wrap(self.message, font, rect.width - 24)
        y = rect.y + 178
        for line in lines[:3]:
            screen.blit(font.render(line, True, INK), (rect.x + 12, y))
            y += 18

        steps = self._font(12).render(f"PRESSES: {self.steps}", True, INK)
        screen.blit(steps, (rect.right - steps.get_width() - 12, rect.y + 8))