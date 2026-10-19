
# puzzles/hidden_transmission.py
# Level 2: Decode four binary and four Gray-code transmissions.

import pygame
import settings
from puzzles.base_puzzle import BasePuzzle


class HiddenTransmissionPuzzle(BasePuzzle):
    """Eight-question binary and Gray-code decoding challenge."""

    def __init__(self):
        super().__init__()

        self.title_font = pygame.font.Font(None, 46)
        self.heading_font = pygame.font.Font(None, 31)
        self.font = pygame.font.Font(None, 27)
        self.input_font = pygame.font.Font(None, 40)
        self.small_font = pygame.font.Font(None, 22)

        self.questions = [
            {
                "type": "BINARY",
                "signal": "0011",
                "answer": "3",
                "hint": "Convert binary 0011 to decimal.",
            },
            {
                "type": "BINARY",
                "signal": "0101",
                "answer": "5",
                "hint": "Convert binary 0101 to decimal.",
            },
            {
                "type": "BINARY",
                "signal": "1001",
                "answer": "9",
                "hint": "Convert binary 1001 to decimal.",
            },
            {
                "type": "BINARY",
                "signal": "1110",
                "answer": "14",
                "hint": "Convert binary 1110 to decimal.",
            },
            {
                "type": "GRAY CODE",
                "signal": "0010",
                "answer": "3",
                "hint": "Convert Gray code 0010 to binary, then decimal.",
            },
            {
                "type": "GRAY CODE",
                "signal": "0111",
                "answer": "5",
                "hint": "Convert Gray code 0111 to binary, then decimal.",
            },
            {
                "type": "GRAY CODE",
                "signal": "1100",
                "answer": "8",
                "hint": "Convert Gray code 1100 to binary, then decimal.",
            },
            {
                "type": "GRAY CODE",
                "signal": "1010",
                "answer": "12",
                "hint": "Convert Gray code 1010 to binary, then decimal.",
            },
        ]

        self.current_question = 0
        self.user_input = ""
        self.message = "Recover the corrupted transmission."
        self.message_color = settings.WHITE

    def handle_event(self, event):
        """Handle keyboard input for the current question."""

        if event.type != pygame.KEYDOWN or self.solved:
            return

        if event.key == pygame.K_BACKSPACE:
            self.user_input = self.user_input[:-1]
            return

        if event.key == pygame.K_RETURN:
            self.check_answer()
            return

        # Accept only decimal digits, with at most two characters.
        if event.unicode.isdigit() and len(self.user_input) < 2:
            self.user_input += event.unicode

    def check_answer(self):
        """Check the answer and advance to the next question."""

        if not self.user_input:
            self.message = "Enter an answer first."
            self.message_color = settings.YELLOW
            return

        question = self.questions[self.current_question]

        if self.user_input != question["answer"]:
            self.message = "Incorrect answer. Try again."
            self.message_color = settings.RED
            self.user_input = ""
            return

        # All eight questions have been answered correctly.
        if self.current_question == len(self.questions) - 1:
            self.solved = True
            self.message = "All signals decoded! Access code recovered: 35891412"
            self.message_color = settings.GREEN
            return

        self.current_question += 1
        self.user_input = ""
        self.message = "Correct! Next transmission received."
        self.message_color = settings.GREEN

    def update(self, dt):
        """No continuous updates are required for this puzzle."""
        pass

    def draw(self, screen):
        """Draw the Hidden Transmission puzzle screen."""

        screen.fill(settings.DARK_BLUE)

        # Title.
        title = self.title_font.render(
            "HIDDEN TRANSMISSION",
            True,
            settings.CYAN,
        )
        screen.blit(
            title,
            title.get_rect(center=(500, 75)),
        )

        # Progress counter.
        if self.solved:
            progress_text = "8 / 8 TRANSMISSIONS DECODED"
        else:
            progress_text = (
                f"TRANSMISSION {self.current_question + 1} / "
                f"{len(self.questions)}"
            )

        progress_surface = self.font.render(
            progress_text,
            True,
            settings.WHITE,
        )
        screen.blit(
            progress_surface,
            progress_surface.get_rect(center=(500, 130)),
        )

        # Progress bar.
        bar_rect = pygame.Rect(250, 155, 500, 12)
        pygame.draw.rect(
            screen, settings.GREY, bar_rect, border_radius=5
        )

        completed_width = int(
            bar_rect.width
            * (
                (self.current_question + 1)
                if self.solved
                else self.current_question
            )
            / len(self.questions)
        )

        if completed_width > 0:
            completed_rect = pygame.Rect(
                bar_rect.x,
                bar_rect.y,
                completed_width,
                bar_rect.height,
            )
            pygame.draw.rect(
                screen,
                settings.GREEN,
                completed_rect,
                border_radius=5,
            )

        if self.solved:
            heading = self.heading_font.render(
                "SIGNAL RECOVERY COMPLETE",
                True,
                settings.GREEN,
            )
            screen.blit(
                heading,
                heading.get_rect(center=(500, 235)),
            )

            code_text = self.input_font.render(
                "35891412",
                True,
                settings.CYAN,
            )
            screen.blit(
                code_text,
                code_text.get_rect(center=(500, 315)),
            )

        else:
            question = self.questions[self.current_question]

            # Question type.
            heading = self.heading_font.render(
                question["type"],
                True,
                settings.YELLOW,
            )
            screen.blit(
                heading,
                heading.get_rect(center=(500, 225)),
            )

            # Encoded signal.
            signal = self.title_font.render(
                question["signal"],
                True,
                settings.CYAN,
            )
            screen.blit(
                signal,
                signal.get_rect(center=(500, 300)),
            )

            # Instructions.
            hint = self.small_font.render(
                question["hint"],
                True,
                settings.WHITE,
            )
            screen.blit(
                hint,
                hint.get_rect(center=(500, 355)),
            )

            # User input.
            input_label = self.small_font.render(
                "YOUR DECIMAL ANSWER",
                True,
                settings.GREY,
            )
            screen.blit(
                input_label,
                input_label.get_rect(center=(500, 410)),
            )

            input_surface = self.input_font.render(
                self.user_input or "_",
                True,
                settings.YELLOW,
            )
            screen.blit(
                input_surface,
                input_surface.get_rect(center=(500, 455)),
            )

            instructions = self.small_font.render(
                "Type your answer | ENTER: Submit | BACKSPACE: Delete",
                True,
                settings.GREY,
            )
            screen.blit(
                instructions,
                instructions.get_rect(center=(500, 515)),
            )

        # Feedback.
        message_surface = self.small_font.render(
            self.message,
            True,
            self.message_color,
        )
        screen.blit(
            message_surface,
            message_surface.get_rect(center=(500, 570)),
        )

        escape_text = self.small_font.render(
            "ESC: Return to laboratory",
            True,
            settings.GREY,
        )
        screen.blit(
            escape_text,
            escape_text.get_rect(center=(500, 620)),
        )

    def reset_attempt(self):
        """Reset the puzzle when a fresh attempt is requested."""

        super().reset_attempt()
        self.current_question = 0
        self.user_input = ""
        self.message = "Recover the corrupted transmission."
        self.message_color = settings.WHITE
