
# Level 3: Memory Protocol — Security Network
# Uses the shared screen_borders.py monitor frame.
#
# Controls:
#   A / B / C / D = Probe the security system
#   R             = Reset the lamp
#   H             = Show a hint
#   ENTER         = Return to the lab after completing the level

import pygame
from .base_puzzle import BasePuzzle
from screen_borders import draw_pixel_monitor


# ---------------------------------------------------------
# COLOURS
# ---------------------------------------------------------

DARK_BLUE = (4, 10, 22)
PANEL_BLUE = (9, 24, 39)
CYAN = (0, 235, 245)
TEAL = (39, 91, 113)
RED = (255, 57, 70)
AMBER = (255, 181, 35)
BLUE = (70, 140, 255)
VIOLET = (180, 105, 245)
ORANGE = (255, 100, 30)
GREEN = (55, 245, 135)
WHITE = (220, 233, 245)
GREY = (132, 151, 174)
YELLOW = (255, 195, 50)


class MemoryProtocolPuzzle(BasePuzzle):
    """Deduce the hidden security system using the state lamp."""

    MAX_TRIPS = 3
    INPUTS = ["A", "B", "C", "D"]

    # State: (lamp colour, pulsating?, visible label)
    LAMPS = {
        "S0": (RED, False, "RED"),
        "S1": (AMBER, False, "AMBER"),
        "S2": (AMBER, True, "AMBER*"),
        "S3": (BLUE, False, "BLUE"),
        "S4": (BLUE, True, "BLUE*"),
        "S5": (VIOLET, False, "VIOLET"),
        "OPEN": (GREEN, False, "GREEN"),
        "ALARM": (ORANGE, True, "ALARM"),
    }

    # Hidden transition rules. The solution is not shown to players.
    TRANSITIONS = {
        "S0": {"A": "S1", "B": "S0", "C": "ALARM", "D": "ALARM"},
        "S1": {"A": "ALARM", "B": "S2", "C": "S0", "D": "S1"},
        "S2": {"A": "S3", "B": "S1", "C": "ALARM", "D": "S0"},
        "S3": {"A": "S0", "B": "ALARM", "C": "S4", "D": "S3"},
        "S4": {"A": "ALARM", "B": "S2", "C": "S3", "D": "S5"},
        "S5": {"A": "ALARM", "B": "S1", "C": "OPEN", "D": "ALARM"},
    }

    CLUES = [
        "1. There are RED, AMBER, BLUE, VIOLET, and GREEN lamps. Watch carefully!",
        "2. Steady or pulsating? A steady lamp means the first state of that colour. A pulsating lamp means the second state. Remember, two lamps can share the same colour!",
        "3. My bad habit: I have never pressed the same button twice in a row. Be careful!",
        "4. Stay alert, detective! Wrong moves trigger an ALARM. Three alarms will wipe your notebook.",
        "TIP: Press H anytime for a hint. Use your notebook to track what you discover!",
    ]

    HINTS = [
        "Hint: watch the lamp after every button press and record the changes.",
        "Hint: steady and pulsating lamps of the same colour are different states.",
        "Hint: use your notebook to track what each button does from each state.",
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
        self.message = "DETECTIVE, PROBE THE KEYPAD AND TRACK THE LAMP."
        self.known = {}
        self.notebook = []
        self.trail = ["RED"]
        self.trips = 0
        self.presses = 0
        self.hint_index = 0
        self.awaiting_exit_confirmation = False

    # ---------------------------------------------------------
    # GAME LOGIC
    # ---------------------------------------------------------

    def name(self, state):
        return self.LAMPS[state][2]

    def add_trail(self, text):
        self.trail.append(text)
        self.trail = self.trail[-8:]

    def press(self, inp):
        if self.solved or self.awaiting_exit_confirmation:
            return

        self.presses += 1

        # After an alarm, the next button press reboots the system.
        if self.state == "ALARM":
            self.state = "S0"
            self.add_trail("RED")
            self.message = f"SYSTEM REBOOTED BY BUTTON {inp}. LAMP: RED."
            return

        old_state = self.state
        key = (old_state, inp)
        next_state = self.TRANSITIONS[old_state][inp]

        # Record each discovered transition once.
        if key not in self.known:
            self.known[key] = next_state
            self.notebook.append(
                f"{self.name(old_state)} --{inp}--> {self.name(next_state)}"
            )

        self.state = next_state
        self.add_trail(self.name(next_state))
        self.message = (
            f"{self.name(old_state)} + {inp} -> {self.name(next_state)}"
        )

        if next_state == "ALARM":
            self.trips += 1
            self.message = (
                f"ALARM! COUNT: {self.trips}/{self.MAX_TRIPS}. "
                "PRESS ANY BUTTON TO REBOOT."
            )

            if self.trips >= self.MAX_TRIPS:
                self.known.clear()
                self.notebook.clear()
                self.trips = 0
                self.message = (
                    "TRACE COMPLETE! YOUR NOTEBOOK WAS WIPED. "
                    "START MAPPING AGAIN."
                )

        elif next_state == "OPEN":
            self.awaiting_exit_confirmation = True
            self.message = "ACCESS GRANTED! SECURITY NETWORK UNLOCKED."

    def reset_lamp(self):
        if self.solved or self.awaiting_exit_confirmation:
            return

        self.state = "S0"
        self.add_trail("RED")
        self.message = "MANUAL RESET: LAMP IS RED."

    def show_hint(self):
        if self.solved or self.awaiting_exit_confirmation:
            return

        self.message = self.HINTS[
            self.hint_index % len(self.HINTS)
        ]
        self.hint_index += 1

    def handle_event(self, event):
        # Keyboard only. Mouse clicks are ignored.
        if event.type != pygame.KEYDOWN:
            return

        if self.awaiting_exit_confirmation:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.solved = True
            return

        if self.solved:
            return

        if event.key in self.KEYMAP:
            self.press(self.KEYMAP[event.key])
        elif event.key == pygame.K_r:
            self.reset_lamp()
        elif event.key == pygame.K_h:
            self.show_hint()

    # ---------------------------------------------------------
    # DRAWING HELPERS
    # ---------------------------------------------------------

    def _font(self, size, bold=False):
        return pygame.font.SysFont("monospace", size, bold=bold)

    def _text(self, screen, text, font, colour, x, y):
        image = font.render(str(text), True, colour)
        screen.blit(image, (int(x), int(y)))
        return image.get_width(), image.get_height()

    def _wrap(self, text, font, max_width):
        """Wrap text to fit the available width."""
        words = text.split()
        lines = []
        current = ""

        for word in words:
            candidate = word if not current else current + " " + word

            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue

            if current:
                lines.append(current)

            # Split unusually long words if necessary.
            current = ""
            for char in word:
                candidate = current + char

                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = char

        if current:
            lines.append(current)

        return lines

    def _wrapped_text(
        self, screen, text, font, colour, x, y,
        max_width, line_height, max_height
    ):
        """Draw wrapped text only while it fits vertically and horizontally."""
        used_height = 0

        for line in self._wrap(text, font, max_width):
            if used_height + line_height > max_height:
                break

            self._text(
                screen, line, font, colour,
                x, y + used_height
            )
            used_height += line_height

        return used_height

    def _panel(self, screen, rect, title, title_font):
        pygame.draw.rect(screen, PANEL_BLUE, rect, border_radius=12)
        pygame.draw.rect(screen, TEAL, rect, 3, border_radius=12)

        self._text(
            screen, title, title_font, CYAN,
            rect.x + 16, rect.y + 13
        )

    # ---------------------------------------------------------
    # MAIN DRAW
    # ---------------------------------------------------------

    def draw(self, screen):
        screen.fill(DARK_BLUE)

        # Shared Level 1 pixel-art monitor border.
        panel = draw_pixel_monitor(screen)

        sx = panel.width / 1400
        sy = panel.height / 880
        scale = max(0.65, min(sx, sy, 1.2))

        def X(value):
            return int(panel.x + value * sx)

        def Y(value):
            return int(panel.y + value * sy)

        def W(value):
            return max(1, int(value * sx))

        def H(value):
            return max(1, int(value * sy))

        alert_font = self._font(max(14, int(19 * scale)), True)
        intro_font = self._font(max(17, int(25 * scale)), True)
        title_font = self._font(max(14, int(19 * scale)), True)

        # Slightly larger text inside the notes and notebook.
        notes_font = self._font(max(14, int(17 * scale)))
        notebook_font = self._font(max(14, int(17 * scale)))

        stat_font = self._font(max(14, int(17 * scale)), True)
        button_font = self._font(max(14, int(17 * scale)), True)
        message_font = self._font(max(13, int(16 * scale)), True)
        completion_font = self._font(max(20, int(27 * scale)), True)

        # -----------------------------------------------------
        # BLINKING SECURITY ALERT
        # -----------------------------------------------------

        blink_on = (pygame.time.get_ticks() // 450) % 2 == 0
        alert_colour = RED if blink_on else (135, 35, 48)

        self._text(
            screen,
            "■ SECURITY NETWORK // LEVEL THREE",
            alert_font,
            alert_colour,
            X(35), Y(25)
        )

        # -----------------------------------------------------
        # INTRODUCTION
        # -----------------------------------------------------

        intro = (
            "Oops! Seems like the guard of this facility has left "
            "something behind. Can you understand what's in it?"
        )

        self._wrapped_text(
            screen, intro, intro_font, CYAN,
            X(35), Y(67),
            W(1325), H(33), H(75)
        )

        # -----------------------------------------------------
        # ENLARGED, MATCHING NOTES AND NOTEBOOK PANELS
        # -----------------------------------------------------

        # Both panels have exactly the same height.
        # The extra height makes room for the H-key tip and line spacing.
        panel_top = Y(155)
        panel_height = H(350)

        notes_rect = pygame.Rect(
            X(35), panel_top, W(745), panel_height
        )
        notebook_rect = pygame.Rect(
            X(800), panel_top, W(565), panel_height
        )

        self._panel(screen, notes_rect, "GUARD'S NOTES", title_font)
        self._panel(screen, notebook_rect, "YOUR NOTEBOOK", title_font)

        # Guard's notes: larger type and additional space between points.
        notes_x = notes_rect.x + W(16)
        notes_y = notes_rect.y + H(49)
        notes_width = notes_rect.width - W(32)
        notes_bottom = notes_rect.bottom - H(12)

        note_line_height = H(22)
        note_gap = H(7)

        for index, note in enumerate(self.CLUES):
            available = notes_bottom - notes_y

            if available <= 0:
                break

            used = self._wrapped_text(
                screen, note, notes_font, WHITE,
                notes_x, notes_y,
                notes_width, note_line_height, available
            )

            notes_y += used + note_gap

        # Notebook entries: matching panel height, larger type and spacing.
        book_x = notebook_rect.x + W(16)
        book_y = notebook_rect.y + H(51)
        book_width = notebook_rect.width - W(32)
        book_bottom = notebook_rect.bottom - H(12)

        if not self.notebook:
            self._text(
                screen,
                "(NO TRANSITIONS RECORDED)",
                notebook_font, GREY,
                book_x, book_y
            )
        else:
            for entry in self.notebook[-8:]:
                available = book_bottom - book_y

                if available <= 0:
                    break

                used = self._wrapped_text(
                    screen, entry, notebook_font, WHITE,
                    book_x, book_y, book_width,
                    H(22), available
                )

                book_y += used + H(5)

        # -----------------------------------------------------
        # STATE LAMP AND STATISTICS
        # -----------------------------------------------------

        self._text(
            screen, "STATE LAMP",
            notes_font, GREY,
            X(35), Y(520)
        )

        colour, pulsing, label = self.LAMPS[self.state]

        if pulsing and (pygame.time.get_ticks() // 350) % 2:
            colour = tuple(int(c * 0.35) for c in colour)

        # Enlarged lamp circle.
        lamp_center = (X(175), Y(615))
        lamp_radius = max(31, int(55 * scale))

        pygame.draw.circle(screen, colour, lamp_center, lamp_radius)
        pygame.draw.circle(
            screen, WHITE, lamp_center,
            lamp_radius + 4, max(2, int(3 * scale))
        )

        stats_x = X(300)
        stats_y = Y(540)
        stat_gap = H(32)

        self._text(
            screen, f"LAMP: {label}",
            stat_font, WHITE, stats_x, stats_y
        )
        self._text(
            screen, f"ALARM COUNT: {self.trips}/{self.MAX_TRIPS}",
            notes_font, YELLOW, stats_x, stats_y + stat_gap
        )
        self._text(
            screen, f"BUTTONS PRESSED: {self.presses}",
            notes_font, WHITE, stats_x, stats_y + stat_gap * 2
        )

        total = sum(len(row) for row in self.TRANSITIONS.values())
        self._text(
            screen, f"TRANSITIONS MAPPED: {len(self.known)}/{total}",
            notes_font, GREY, stats_x, stats_y + stat_gap * 3
        )

        # Reset label — keyboard control is R.
        reset_rect = pygame.Rect(
            X(1000), Y(550), W(330), H(58)
        )

        pygame.draw.rect(screen, PANEL_BLUE, reset_rect)
        pygame.draw.rect(screen, YELLOW, reset_rect, 3)

        reset_label = button_font.render("RESET LAMP  R", True, YELLOW)
        screen.blit(
            reset_label,
            reset_label.get_rect(center=reset_rect.center)
        )

        # -----------------------------------------------------
        # KEYPAD
        # -----------------------------------------------------

        # Kept above the status area to prevent overlap.
        keypad_y = Y(690)
        keypad_h = H(57)
        keypad_left = X(35)
        keypad_right = X(1365)
        keypad_gap = W(15)

        button_width = (
            keypad_right - keypad_left - keypad_gap * 3
        ) // 4

        for index, letter in enumerate(self.INPUTS):
            rect = pygame.Rect(
                keypad_left + index * (button_width + keypad_gap),
                keypad_y,
                button_width,
                keypad_h
            )

            pygame.draw.rect(screen, PANEL_BLUE, rect)
            pygame.draw.rect(screen, CYAN, rect, 3)

            # Only BUTTON A, BUTTON B, BUTTON C, BUTTON D.
            label = button_font.render(f"BUTTON {letter}", True, CYAN)
            screen.blit(label, label.get_rect(center=rect.center))

        # -----------------------------------------------------
        # STATUS AND COMPLETION MESSAGE
        # -----------------------------------------------------

        # Reserved area below the keypad, still inside the monitor.
        status_x = X(35)
        status_y = Y(765)
        status_width = W(1330)
        status_height = H(95)

        if self.awaiting_exit_confirmation:
            completion_rect = pygame.Rect(
                status_x, status_y,
                status_width, status_height
            )
            pygame.draw.rect(screen, DARK_BLUE, completion_rect)

            self._text(
                screen, "ACCESS GRANTED!",
                completion_font, GREEN,
                status_x, status_y
            )

            self._text(
                screen, "YOU CRACKED THE SECURITY NETWORK, DETECTIVE!",
                message_font, WHITE,
                status_x, status_y + H(33)
            )

            self._text(
                screen, "PRESS ENTER TO RETURN TO THE LAB",
                message_font, YELLOW,
                status_x, status_y + H(63)
            )
        else:
            self._wrapped_text(
                screen, self.message, message_font, YELLOW,
                status_x, status_y,
                status_width, H(23), status_height
            )

        pygame.display.update()
