
# puzzles/logic_lock.py
# Level 1: Logic Lock

import pygame
import settings

from puzzles.base_puzzle import BasePuzzle


class LogicLockPuzzle(BasePuzzle):

    def __init__(self):
        super().__init__()

        self.title = "LOGIC LOCK"
        self.selected_gate = None
        self.selected_row = 0

        self.truth_table = [
            {"a": 0, "b": 0, "answer": None},
            {"a": 0, "b": 1, "answer": None},
            {"a": 1, "b": 0, "answer": None},
            {"a": 1, "b": 1, "answer": None},
        ]

        self.message = (
            "The alarm must activate only when BOTH inputs are ON."
        )

        self.font = pygame.font.Font(None, 27)
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 46)

    def handle_event(self, event):
        """Handle row selection, outputs, and gate selection."""

        if event.type != pygame.KEYDOWN or self.solved:
            return

        # Select a row using 1, 2, 3, or 4.
        if event.key in (
            pygame.K_1,
            pygame.K_2,
            pygame.K_3,
            pygame.K_4
        ):
            self.selected_row = event.key - pygame.K_1
            self.message = (
                f"Row {self.selected_row + 1} selected. "
                "LEFT = output 0; RIGHT = output 1."
            )

        # Set the output without changing the selected row.
        elif event.key == pygame.K_LEFT:
            self.truth_table[self.selected_row]["answer"] = 0
            self.message = (
                f"Row {self.selected_row + 1}: output set to 0."
            )

        elif event.key == pygame.K_RIGHT:
            self.truth_table[self.selected_row]["answer"] = 1
            self.message = (
                f"Row {self.selected_row + 1}: output set to 1."
            )

        # Select the logic gate.
        elif event.key == pygame.K_a:
            self.selected_gate = "AND"
            self.message = "AND gate selected."

        elif event.key == pygame.K_o:
            self.selected_gate = "OR"
            self.message = "OR gate selected."

        # Submit the answer.
        elif event.key == pygame.K_RETURN:
            self.check_answer()

    def check_answer(self):
        """Check the selected gate and all four outputs."""

        if self.selected_gate is None:
            self.message = "Choose AND (A) or OR (O) first."
            return

        if any(
            row["answer"] is None
            for row in self.truth_table
        ):
            self.message = "Complete all four output rows first."
            return

        correct_outputs = [0, 0, 0, 1]

        entered_outputs = [
            row["answer"]
            for row in self.truth_table
        ]

        if (
            self.selected_gate == "AND"
            and entered_outputs == correct_outputs
        ):
            self.solved = True
            self.message = (
                "ACCESS GRANTED! The AND gate is correct."
            )

        elif self.selected_gate == "OR":
            self.message = (
                "Incorrect gate. OR activates when either "
                "input is ON."
            )

        else:
            self.message = (
                "Incorrect truth table. Check each row and retry."
            )

    def update(self, dt):
        """No continuous updates are needed for this puzzle."""
        pass

    def draw(self, screen):
        """Draw the complete Logic Lock puzzle screen."""

        screen.fill(settings.DARK_BLUE)

        # Title
        title = self.title_font.render(
            self.title, True, settings.CYAN
        )
        screen.blit(title, (55, 30))

        instructions = [
            "SECURITY CIRCUIT TAMPERED",
            "The alarm must activate ONLY when BOTH inputs are ON.",
            "Select a row using keys 1-4.",
            "Press LEFT for output 0; RIGHT for output 1.",
            "Choose AND with A or OR with O, then press ENTER.",
        ]

        y = 90

        for line in instructions:
            rendered = self.small_font.render(
                line, True, settings.WHITE
            )
            screen.blit(rendered, (55, y))
            y += 29

        # Truth table headings
        headers = [
            ("ROW", 100),
            ("A", 220),
            ("B", 310),
            ("OUTPUT", 415),
        ]

        for label, x in headers:
            rendered = self.font.render(
                label, True, settings.YELLOW
            )
            screen.blit(rendered, (x, 260))

        # Truth table rows
        for index, row in enumerate(self.truth_table):
            y = 300 + index * 43

            # Highlight the currently selected row.
            if index == self.selected_row:
                pygame.draw.rect(
                    screen,
                    settings.PANEL_BLUE,
                    pygame.Rect(75, y - 5, 445, 36),
                    border_radius=5
                )

            output = (
                "_"
                if row["answer"] is None
                else str(row["answer"])
            )

            values = [
                (str(index + 1), 105),
                (str(row["a"]), 225),
                (str(row["b"]), 315),
                (output, 440),
            ]

            for value, x in values:
                color = (
                    settings.CYAN
                    if index == self.selected_row
                    else settings.WHITE
                )

                rendered = self.font.render(
                    value, True, color
                )
                screen.blit(rendered, (x, y))

        # Gate selection information
        gate_label = (
            f"Selected gate: {self.selected_gate or 'None'}"
        )

        screen.blit(
            self.font.render(
                gate_label, True, settings.GREEN
            ),
            (575, 290)
        )

        screen.blit(
            self.small_font.render(
                "A = AND gate",
                True,
                settings.WHITE
            ),
            (575, 335)
        )

        screen.blit(
            self.small_font.render(
                "O = OR gate",
                True,
                settings.WHITE
            ),
            (575, 365)
        )

        # Feedback message
        message_lines = self._wrap_message(
            self.message, 43
        )

        for index, line in enumerate(message_lines):
            rendered = self.small_font.render(
                line, True, settings.YELLOW
            )
            screen.blit(
                rendered,
                (55, 500 + index * 25)
            )

        if self.solved:
            status = "LEVEL 1 COMPLETE"

            color = settings.GREEN

        else:
            status = "Awaiting correct answer"

            color = settings.GREY

        screen.blit(
            self.small_font.render(
                status, True, color
            ),
            (575, 420)
        )

    def _wrap_message(self, message, max_length):
        """Split feedback into lines that fit the interface."""

        words = message.split()
        lines = []
        current_line = ""

        for word in words:
            candidate = f"{current_line} {word}".strip()

            if len(candidate) > max_length and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate

        if current_line:
            lines.append(current_line)

        return lines

    def reset_attempt(self):
        """Reset this puzzle without affecting other levels."""

        super().reset_attempt()

        for row in self.truth_table:
            row["answer"] = None

        self.selected_row = 0
        self.selected_gate = None

        self.message = (
            "Try the security circuit again."
        )
