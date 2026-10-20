# Level 3: Memory Protocol — Security Network (FSM)
import pygame
from .base_puzzle import BasePuzzle
import settings


class MemoryProtocolPuzzle(BasePuzzle):
    """A deterministic finite-state-machine security challenge."""

    def __init__(self):
        super().__init__()
        self.state = "LOCKED"
        self.message = "Reach UNLOCKED using the transition rules."
        self.history = ["System initialized: LOCKED"]
        self.transitions = {
            ("LOCKED", "VALID CARD"): "VERIFYING",
            ("LOCKED", "INVALID CARD"): "WARNING",
            ("VERIFYING", "CONFIRM"): "UNLOCKED",
            ("VERIFYING", "INVALID CARD"): "WARNING",
            ("WARNING", "VALID CARD"): "VERIFYING",
            ("WARNING", "INVALID CARD"): "LOCKDOWN",
            ("LOCKED", "RESET"): "LOCKED",
            ("VERIFYING", "RESET"): "LOCKED",
            ("WARNING", "RESET"): "LOCKED",
            ("LOCKDOWN", "RESET"): "LOCKED",
        }
        self.colors = {
            "LOCKED": settings.RED,
            "VERIFYING": settings.YELLOW,
            "WARNING": settings.YELLOW,
            "LOCKDOWN": settings.RED,
            "UNLOCKED": settings.GREEN,
        }

    def apply_input(self, input_name):
        if self.solved:
            return
        key = (self.state, input_name)
        if key not in self.transitions:
            self.message = f"{input_name} is not accepted in {self.state}."
            self.history.append(self.message)
        else:
            old_state = self.state
            self.state = self.transitions[key]
            self.message = f"{old_state} + {input_name} -> {self.state}"
            self.history.append(self.message)
            if self.state == "UNLOCKED":
                self.solved = True
                self.message = "ACCESS GRANTED! Security network unlocked."
        self.history = self.history[-4:]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            keys = {
                pygame.K_v: "VALID CARD",
                pygame.K_i: "INVALID CARD",
                pygame.K_c: "CONFIRM",
                pygame.K_r: "RESET",
            }
            if event.key in keys:
                self.apply_input(keys[event.key])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            if 60 <= y <= 110:
                if 60 <= x < 280:
                    self.apply_input("VALID CARD")
                elif 290 <= x < 510:
                    self.apply_input("INVALID CARD")
                elif 520 <= x < 740:
                    self.apply_input("CONFIRM")
                elif 750 <= x < 930:
                    self.apply_input("RESET")

    def draw(self, screen):
        screen.fill(settings.DARK_BLUE)
        title = pygame.font.Font(None, 42)
        heading = pygame.font.Font(None, 28)
        body = pygame.font.Font(None, 22)
        small = pygame.font.Font(None, 19)

        def write(text, font, color, x, y, center=False):
            image = font.render(text, True, color)
            rect = image.get_rect()
            rect.center = (x, y) if center else rect.center
            if not center:
                rect.topleft = (x, y)
            screen.blit(image, rect)

        write("LEVEL 3: MEMORY PROTOCOL", title, settings.CYAN, 35, 25)
        write("SECURITY NETWORK / FINITE-STATE MACHINE", body, settings.GREY, 38, 70)

        pygame.draw.rect(screen, settings.PANEL_BLUE, (60, 115, 880, 100), border_radius=10)
        write("CURRENT STATE", small, settings.GREY, 82, 130)
        write(self.state, heading, self.colors[self.state], 82, 157)
        write("Inputs cause transitions; an input may be invalid for a state.",
              body, settings.WHITE, 350, 160)

        pygame.draw.rect(screen, settings.PANEL_BLUE, (60, 230, 880, 145), border_radius=10)
        write("TRANSITION RULES", heading, settings.CYAN, 80, 242)
        rules = [
            "LOCKED + VALID CARD -> VERIFYING",
            "LOCKED + INVALID CARD -> WARNING",
            "VERIFYING + CONFIRM -> UNLOCKED",
            "VERIFYING + INVALID CARD -> WARNING; WARNING + INVALID CARD -> LOCKDOWN",
            "WARNING + VALID CARD -> VERIFYING; RESET from LOCKED/VERIFYING/WARNING/LOCKDOWN -> LOCKED",
        ]
        for i, line in enumerate(rules):
            write(line, small, settings.WHITE, 82, 274 + i * 19)

        buttons = [
            (60, 220, "VALID CARD [V]", settings.GREEN),
            (290, 220, "INVALID CARD [I]", settings.RED),
            (520, 220, "CONFIRM [C]", settings.CYAN),
            (750, 180, "RESET [R]", settings.YELLOW),
        ]
        for x, width, label, color in buttons:
            rect = pygame.Rect(x, 395, width, 52)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            image = body.render(label, True, settings.DARK_BLUE)
            screen.blit(image, image.get_rect(center=rect.center))

        write("EVENT LOG", heading, settings.CYAN, 70, 465)
        for i, entry in enumerate(self.history[-4:]):
            write(entry, small, settings.WHITE, 75, 498 + i * 22)

        write("Goal: reach UNLOCKED. Hint: VALID CARD, then CONFIRM.",
              small, settings.YELLOW, 70, 610)
        if self.solved:
            write("LEVEL COMPLETE", heading, settings.GREEN, 700, 610)
