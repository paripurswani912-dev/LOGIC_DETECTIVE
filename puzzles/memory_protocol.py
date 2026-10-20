# Level 3: Memory Protocol — Security Network (hidden color-coded FSM)
#
# The player never sees the transition rules. The only output is a coloured lamp.
# Two states share each colour (one steady, one pulsing), so the player must
# REMEMBER where they are, probe the machine, and use the guard's log to find
# the one route to GREEN. Wrong presses trip an alarm; too many alarms wipe the
# player's notebook (hence "memory" protocol).
import pygame
from .base_puzzle import BasePuzzle
import settings

AMBER = (255, 176, 0)
BLUE = (70, 130, 255)
VIOLET = (175, 95, 235)
ORANGE = (255, 90, 0)


class MemoryProtocolPuzzle(BasePuzzle):
    """Deduce a hidden finite-state machine from lamp colours and a guard's log."""

    MAX_TRIPS = 3
    INPUTS = ["A", "B", "C", "D"]

    # state id -> (lamp colour, pulsing?, display name)
    LAMPS = {
        "S0": (settings.RED, False, "RED"),
        "S1": (AMBER, False, "AMBER"),
        "S2": (AMBER, True, "AMBER*"),
        "S3": (BLUE, False, "BLUE"),
        "S4": (BLUE, True, "BLUE*"),
        "S5": (VIOLET, False, "VIOLET"),
        "OPEN": (settings.GREEN, False, "GREEN"),
        "ALARM": (ORANGE, True, "ALARM"),
    }

    # Hidden machine. Unique shortest route to OPEN: A, B, A, C, D, C
    TRANSITIONS = {
        "S0": {"A": "S1", "B": "S0", "C": "ALARM", "D": "ALARM"},
        "S1": {"A": "ALARM", "B": "S2", "C": "S0", "D": "S1"},
        "S2": {"A": "S3", "B": "S1", "C": "ALARM", "D": "S0"},
        "S3": {"A": "S0", "B": "ALARM", "C": "S4", "D": "S3"},
        "S4": {"A": "ALARM", "B": "S2", "C": "S3", "D": "S5"},
        "S5": {"A": "ALARM", "B": "S1", "C": "OPEN", "D": "ALARM"},
    }

    CLUES = [
        "1. Guard's lamp log: RED, AMBER, AMBER, BLUE, BLUE, VIOLET, GREEN.",
        "2. A pulsing lamp (*) is the 2nd of its colour; steady is the 1st.",
        "3. He never pressed the same button twice in a row.",
        "4. Same button + different lamp = different result.",
        "5. A wrong press trips ALARM; any button then reboots to RED.",
        "6. Three alarms start a trace: your notebook gets WIPED.",
        "7. The lamp is the only output. Press H for a hint.",
    ]

    HINTS = [
        "Hint: the notebook records every press you make. Read it before pressing.",
        "Hint: from RED, two buttons trip the alarm, one does nothing, one moves on.",
        "Hint: the two AMBER lamps behave differently. Watch which one pulses.",
    ]

    KEYMAP = {
        pygame.K_a: "A",
        pygame.K_b: "B",
        pygame.K_c: "C",
        pygame.K_d: "D",
    }

    def __init__(self):
        super().__init__()
        self.state = "S0"
        self.message = "Probe the keypad. Watch the lamp. Remember what it does."
        self.known = {}          # (state, input) -> next state
        self.notebook = []       # human readable discoveries
        self.trail = ["RED"]
        self.trips = 0
        self.presses = 0
        self.hint_index = 0

    # ---------------------------------------------------------------- logic
    def name(self, state):
        return self.LAMPS[state][2]

    def add_trail(self, text):
        self.trail.append(text)
        self.trail = self.trail[-7:]

    def press(self, inp):
        if self.solved:
            return
        self.presses += 1

        if self.state == "ALARM":
            self.state = "S0"
            self.add_trail("RED")
            self.message = f"Button {inp}: system rebooted. Lamp is RED again."
            return

        key = (self.state, inp)
        nxt = self.TRANSITIONS[self.state][inp]
        if key not in self.known:
            self.known[key] = nxt
            self.notebook.append(f"{self.name(self.state)}  --{inp}-->  {self.name(nxt)}")
        old = self.state
        self.state = nxt
        self.add_trail(self.name(nxt))
        self.message = f"{self.name(old)} + {inp} -> {self.name(nxt)}"

        if nxt == "ALARM":
            self.trips += 1
            self.message = f"ALARM! Alarm count {self.trips}/{self.MAX_TRIPS}. Press any button to reboot."
            if self.trips >= self.MAX_TRIPS:
                self.known.clear()
                self.notebook.clear()
                self.trips = 0
                self.message = "TRACE COMPLETE: your notebook was wiped! Reboot and start mapping again."
        elif nxt == "OPEN":
            self.solved = True
            self.message = "ACCESS GRANTED! The security network is unlocked."

    def reset_lamp(self):
        if self.solved:
            return
        self.state = "S0"
        self.add_trail("RED")
        self.message = "Manual reset: lamp is RED."

    def show_hint(self):
        self.message = self.HINTS[self.hint_index % len(self.HINTS)]
        self.hint_index += 1

    # ---------------------------------------------------------------- input
    def button_rect(self, i):
        return pygame.Rect(60 + i * 226, 470, 200, 55)

    def reset_rect(self):
        return pygame.Rect(700, 350, 240, 48)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.KEYMAP:
                self.press(self.KEYMAP[event.key])
            elif event.key == pygame.K_r:
                self.reset_lamp()
            elif event.key == pygame.K_h:
                self.show_hint()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, inp in enumerate(self.INPUTS):
                if self.button_rect(i).collidepoint(event.pos):
                    self.press(inp)
                    return
            if self.reset_rect().collidepoint(event.pos):
                self.reset_lamp()

    # ----------------------------------------------------------------- draw
    def draw(self, screen):
        screen.fill(settings.DARK_BLUE)
        title = pygame.font.Font(None, 42)
        heading = pygame.font.Font(None, 28)
        body = pygame.font.Font(None, 22)
        small = pygame.font.Font(None, 19)

        def write(text, font, color, x, y, center=False):
            image = font.render(text, True, color)
            rect = image.get_rect()
            if center:
                rect.center = (x, y)
            else:
                rect.topleft = (x, y)
            screen.blit(image, rect)

        write("LEVEL 3: MEMORY PROTOCOL", title, settings.CYAN, 35, 25)
        write("SECURITY NETWORK / HIDDEN FINITE-STATE MACHINE", body, settings.GREY, 38, 70)

        # Case file
        pygame.draw.rect(screen, settings.PANEL_BLUE, (60, 100, 500, 215), border_radius=10)
        write("CASE FILE: GUARD'S NOTES", heading, settings.CYAN, 80, 110)
        for i, line in enumerate(self.CLUES):
            write(line, small, settings.WHITE, 82, 142 + i * 23)

        # Notebook
        pygame.draw.rect(screen, settings.PANEL_BLUE, (580, 100, 360, 215), border_radius=10)
        write("YOUR NOTEBOOK", heading, settings.CYAN, 600, 110)
        if not self.notebook:
            write("(nothing recorded yet)", small, settings.GREY, 602, 142)
        for i, line in enumerate(self.notebook[-8:]):
            write(line, small, settings.WHITE, 602, 142 + i * 21)

        # Lamp
        write("STATE LAMP", small, settings.GREY, 95, 322)
        color, pulsing, label = self.LAMPS[self.state]
        if pulsing and (pygame.time.get_ticks() // 350) % 2:
            color = tuple(int(c * 0.35) for c in color)
        center = (140, 395)
        pygame.draw.circle(screen, color, center, 48)
        pygame.draw.circle(screen, settings.WHITE, center, 53, 3)

        write(f"Lamp: {label}", heading, settings.WHITE, 240, 345)
        write(f"Alarm count: {self.trips}/{self.MAX_TRIPS}", body, settings.YELLOW, 240, 377)
        write(f"Buttons pressed: {self.presses}", body, settings.WHITE, 240, 402)
        total = sum(len(v) for v in self.TRANSITIONS.values())
        write(f"Transitions mapped: {len(self.known)}/{total}", body, settings.WHITE, 240, 427)

        rect = self.reset_rect()
        pygame.draw.rect(screen, settings.YELLOW, rect, border_radius=8)
        image = body.render("RESET LAMP [R]", True, settings.DARK_BLUE)
        screen.blit(image, image.get_rect(center=rect.center))

        # Keypad
        for i, inp in enumerate(self.INPUTS):
            rect = self.button_rect(i)
            pygame.draw.rect(screen, settings.CYAN, rect, border_radius=8)
            image = heading.render(f"BUTTON {inp} [{inp}]", True, settings.DARK_BLUE)
            screen.blit(image, image.get_rect(center=rect.center))

        write(self.message, body, settings.YELLOW, 60, 548)
        write("Path: " + "  >  ".join(self.trail), small, settings.GREY, 60, 582)
        if self.solved:
            write("LEVEL COMPLETE", heading, settings.GREEN, 760, 582)