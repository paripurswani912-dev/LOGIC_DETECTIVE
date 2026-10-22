
# puzzles/hidden_transmission.py
# Level 2: Hidden Transmission — Pixel-Art Computer Interface

import pygame
import settings
from puzzles.base_puzzle import BasePuzzle


class HiddenTransmissionPuzzle(BasePuzzle):

    def __init__(self):
        super().__init__()

        self.current_question = 0
        self.user_input = ""
        self.elapsed_time = 0.0

        self.message = ""
        self.message_color = (0, 230, 130)
        self.awaiting_exit_confirmation = False

        available_fonts = {
            name.lower() for name in pygame.font.get_fonts()
        }

        pixel_fonts = [
            "press start 2p",
            "pixeloid sans",
            "pixel operator",
            "monospace",
        ]

        self.pixel_font_name = next(
            (
                name for name in pixel_fonts
                if name.lower() in available_fonts
            ),
            "monospace",
        )

        self.questions = [
            {
                "type": "BINARY",
                "signal": "0011",
                "answer": "3",
                "hint": "Convert binary 0011 to decimal.",
                "clue": "Every bit hides a number. Can you uncover the truth?",
            },
            {
                "type": "BINARY",
                "signal": "0101",
                "answer": "5",
                "hint": "Convert binary 0101 to decimal.",
                "clue": "The signal is simple. Or is it?",
            },
            {
                "type": "BINARY",
                "signal": "1001",
                "answer": "9",
                "hint": "Convert binary 1001 to decimal.",
                "clue": "One wrong conversion could bury the evidence.",
            },
            {
                "type": "BINARY",
                "signal": "1110",
                "answer": "14",
                "hint": "Convert binary 1110 to decimal.",
                "clue": "You're close. Don't let the final bits fool you.",
            },
            {
                "type": "GRAY CODE",
                "signal": "0010",
                "answer": "3",
                "hint": "Convert Gray code 0010 to binary, then decimal.",
                "clue": "This code doesn't speak in ordinary binary. Can you crack it?",
            },
            {
                "type": "GRAY CODE",
                "signal": "0111",
                "answer": "5",
                "hint": "Convert Gray code 0111 to binary, then decimal.",
                "clue": "The pattern has changed. Will you notice?",
            },
            {
                "type": "GRAY CODE",
                "signal": "1100",
                "answer": "8",
                "hint": "Convert Gray code 1100 to binary, then decimal.",
                "clue": "The truth is hidden in the transitions.",
            },
            {
                "type": "GRAY CODE",
                "signal": "1010",
                "answer": "12",
                "hint": "Convert Gray code 1010 to binary, then decimal.",
                "clue": "One final signal stands between you and the truth.",
            },
        ]

        self.font = self._make_font(16)
        self.small_font = self._make_font(13)
        self.title_font = self._make_font(25)
        self.signal_font = self._make_font(34)
        self.input_font = self._make_font(27)
        self.feedback_font = self._make_font(16)

        self.cyan = (0, 229, 239)
        self.pink = (235, 105, 177)
        self.orange = (255, 184, 72)
        self.white = (220, 232, 244)
        self.grey = (132, 151, 174)
        self.red = (255, 65, 78)
        self.green = (0, 230, 130)
        self.yellow = (255, 220, 65)

        self.screen_black = (4, 10, 22)
        self.screen_edge = (39, 91, 113)

    def _make_font(self, size):
        return pygame.font.SysFont(
            self.pixel_font_name, size, bold=True
        )

    # ---------------------------------------------------------
    # PIXEL MONITOR FRAME
    # Local to Level 2; does not change the Level 1 border.
    # ---------------------------------------------------------

    def _draw_pixel_monitor(self, screen, rect):
        x, y, w, h = rect

        bezel = (28, 30, 52)
        bezel_light = (48, 54, 91)
        bezel_dark = (15, 17, 34)

        pygame.draw.rect(
            screen, (2, 3, 10),
            (x + 8, y + 8, w, h)
        )

        pygame.draw.rect(
            screen, bezel,
            (x + 8, y + 4, w - 16, h - 8)
        )
        pygame.draw.rect(
            screen, bezel,
            (x + 4, y + 10, w - 8, h - 20)
        )

        step = 8
        corners = [
            (x + 16, y),
            (x + 8, y + 8),
            (x, y + 16),
            (x + w - 24, y),
            (x + w - 16, y + 8),
            (x + w - 8, y + 16),
            (x + 16, y + h - 8),
            (x + 8, y + h - 16),
            (x, y + h - 24),
            (x + w - 24, y + h - 8),
            (x + w - 16, y + h - 16),
            (x + w - 8, y + h - 24),
        ]

        for px, py in corners:
            pygame.draw.rect(
                screen, bezel_light,
                (px, py, step, step)
            )

        pygame.draw.rect(
            screen, bezel_dark,
            (x + 18, y + 18, w - 36, h - 36)
        )

        panel = pygame.Rect(
            x + 27, y + 27, w - 54, h - 54
        )

        pygame.draw.rect(screen, self.screen_black, panel)
        pygame.draw.rect(screen, self.screen_edge, panel, 3)

        for px in range(panel.x + 8, panel.right - 8, 14):
            pygame.draw.rect(
                screen, (40, 86, 109),
                (px, panel.y + 5, 9, 3)
            )

        # Small monitor indicator lights.
        pygame.draw.rect(
            screen, (4, 5, 12),
            (x + w - 54, y + h - 13, 9, 4)
        )
        pygame.draw.rect(
            screen, (4, 5, 12),
            (x + w - 38, y + h - 13, 9, 4)
        )
        pygame.draw.rect(
            screen, (0, 218, 225),
            (x + w - 38, y + h - 13, 5, 4)
        )

        return panel

    # ---------------------------------------------------------
    # TEXT HELPERS
    # ---------------------------------------------------------

    def _fit_text(self, text, max_width, preferred_size, color):
        size = preferred_size

        while size >= 8:
            font = self._make_font(size)
            surface = font.render(text, False, color)

            if surface.get_width() <= max_width:
                return surface

            size -= 1

        return self._make_font(8).render(text, False, color)

    def _draw_centered(
        self, screen, text, center_x, y, color, font, max_width=None
    ):
        if max_width is not None:
            surface = self._fit_text(
                text, max_width, font.get_height(), color
            )
        else:
            surface = font.render(text, False, color)

        screen.blit(
            surface,
            surface.get_rect(midtop=(center_x, y))
        )
        return surface

    # ---------------------------------------------------------
    # KEYBOARD CONTROLS
    # ---------------------------------------------------------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # The victory screen stays until Enter is pressed again.
        if self.awaiting_exit_confirmation:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.solved = True
            return

        if self.solved:
            return

        if event.key == pygame.K_ESCAPE:
            return

        if event.key == pygame.K_BACKSPACE:
            self.user_input = self.user_input[:-1]
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.check_answer()
            return

        # Accept decimal digits only, up to two characters.
        if event.unicode.isdigit() and len(self.user_input) < 2:
            self.user_input += event.unicode

    # ---------------------------------------------------------
    # ANSWER CHECKING
    # ---------------------------------------------------------

    def check_answer(self):
        if not self.user_input:
            self.message = "ENTER AN ANSWER FIRST."
            self.message_color = self.yellow
            return

        question = self.questions[self.current_question]

        if self.user_input != question["answer"]:
            self.message = "INCORRECT ANSWER. TRY AGAIN."
            self.message_color = self.red
            self.user_input = ""
            return

        # Final answer: show the blinking victory message first.
        if self.current_question == len(self.questions) - 1:
            self.awaiting_exit_confirmation = True
            self.message = "YOU DECODED THEM ALL, DETECTIVE!"
            self.message_color = self.yellow
            self.user_input = ""
            self.elapsed_time = 0.0
            return

        # Correct answer: advance to the next transmission.
        self.current_question += 1
        self.user_input = ""
        self.message = "CORRECT! NEXT TRANSMISSION RECEIVED."
        self.message_color = self.green

    def update(self, dt):
        self.elapsed_time += dt

    # ---------------------------------------------------------
    # DRAW INTERFACE
    # ---------------------------------------------------------

    def draw(self, screen):
        screen.fill((5, 7, 17))

        width, height = screen.get_size()
        center_x = width // 2

        monitor_rect = pygame.Rect(
            18, 14, width - 36, height - 28
        )
        panel = self._draw_pixel_monitor(screen, monitor_rect)

        left = panel.left + 22
        right = panel.right - 22
        content_width = right - left

        compact = height < 700
        gap = 5 if compact else 8

        # 1. Blinking alert.
        y = panel.top + 17

        if int(self.elapsed_time * 2.5) % 2 == 0:
            pygame.draw.rect(
                screen, self.red,
                (left, y + 4, 8, 8)
            )

            alert = self._fit_text(
                "SIGNAL INTERCEPTED // LEVEL TWO",
                content_width - 20,
                16,
                self.red,
            )
            screen.blit(alert, (left + 19, y))

        y += 32

        # 2. Main warning.
        warning = self._fit_text(
            "INTRUSION DETECTED!",
            content_width,
            25,
            self.cyan,
        )
        screen.blit(warning, (left, y))
        y += warning.get_height() + 8

        # 3. Challenge line.
        challenge = (
            "EIGHT TRANSMISSIONS DETECTED. CAN YOU DECODE THEM "
            "BEFORE THE SIGNAL DISAPPEARS?"
        )
        challenge_surface = self._fit_text(
            challenge, content_width, 14, self.white
        )
        screen.blit(challenge_surface, (left, y))
        y += challenge_surface.get_height() + 15

        pygame.draw.line(
            screen, (48, 75, 105),
            (left, y), (right, y), 2
        )
        y += 10

        # 4. Controls.
        controls_title = self._make_font(17).render(
            "CONTROLS", False, self.orange
        )
        screen.blit(controls_title, (left, y))
        y += controls_title.get_height() + 4

        controls = [
            "Type your answers in decimal!",
            "ENTER: Submits the answer",
            "BACKSPACE: Deletes the digits",
            "ESC: Return to the lab",
        ]

        control_font_size = 13 if compact else 14
        control_gap = 20 if compact else 23

        for line in controls:
            surface = self._fit_text(
                line, content_width, control_font_size, self.white
            )
            screen.blit(surface, (left, y))
            y += control_gap

        y += 3

        pygame.draw.line(
            screen, (48, 75, 105),
            (left, y), (right, y), 2
        )

        content_top = y + (10 if compact else 14)
        content_bottom = panel.bottom - (16 if compact else 22)

        # After the second Enter, show the completed screen.
        if self.solved:
            success_title = self._fit_text(
                "SIGNAL RECOVERY COMPLETE",
                content_width,
                20,
                self.green,
            )
            screen.blit(
                success_title,
                success_title.get_rect(
                    center=(center_x, content_top + 45)
                )
            )

            code_surface = self._make_font(30).render(
                "35891412", False, self.cyan
            )
            screen.blit(
                code_surface,
                code_surface.get_rect(
                    center=(center_x, content_top + 105)
                )
            )

            return

        question = self.questions[self.current_question]

        # Transmission number.
        title_y = content_top
        transmission_surface = self._fit_text(
            f"TRANSMISSION {self.current_question + 1:02d}",
            content_width,
            19,
            self.cyan,
        )
        screen.blit(
            transmission_surface,
            transmission_surface.get_rect(
                midtop=(center_x, title_y)
            )
        )

        # Binary / Gray-code signal.
        signal_y = title_y + transmission_surface.get_height() + (
            23 if compact else 28
        )
        signal_surface = self._fit_text(
            question["signal"], content_width, 34, self.cyan
        )
        screen.blit(
            signal_surface,
            signal_surface.get_rect(
                midtop=(center_x, signal_y)
            )
        )

        # Pink transmission clue.
        clue_y = signal_y + signal_surface.get_height() + gap + 3
        clue_surface = self._fit_text(
            question["clue"], content_width, 16, self.pink
        )
        screen.blit(
            clue_surface,
            clue_surface.get_rect(
                midtop=(center_x, clue_y)
            )
        )

        # Conversion instruction.
        hint_y = clue_y + clue_surface.get_height() + (
            17 if compact else 20
        )
        hint_surface = self._fit_text(
            question["hint"], content_width, 15, self.white
        )
        screen.blit(
            hint_surface,
            hint_surface.get_rect(
                midtop=(center_x, hint_y)
            )
        )

        # Answer label.
        answer_label_y = (
            hint_y + hint_surface.get_height() + (22 if compact else 27)
        )
        answer_label = self._fit_text(
            "YOUR DECIMAL ANSWER",
            content_width,
            16,
            self.orange,
        )
        screen.blit(
            answer_label,
            answer_label.get_rect(
                midtop=(center_x, answer_label_y)
            )
        )

        # One answer box, with one placeholder per answer digit.
        digit_count = len(question["answer"])
        digit_spacing = 35 if compact else 40
        box_padding = 20
        box_width = digit_count * digit_spacing + box_padding * 2
        box_height = 46 if compact else 50
        box_width = min(box_width, content_width - 12)

        box_y = answer_label_y + answer_label.get_height() + 8

        input_rect = pygame.Rect(
            center_x - box_width // 2,
            box_y,
            box_width,
            box_height,
        )

        pygame.draw.rect(
            screen,
            (39, 91, 113),
            input_rect,
            3,
        )

        # Show typed digits in the middle of the box.
        if self.user_input:
            entered_surface = self.input_font.render(
                self.user_input, False, self.orange
            )
            screen.blit(
                entered_surface,
                entered_surface.get_rect(center=input_rect.center)
            )

        # Draw the remaining answer placeholders.
        placeholder_spacing = min(
            digit_spacing,
            (input_rect.width - 24) / digit_count
        )
        total_width = (digit_count - 1) * placeholder_spacing

        for index in range(len(self.user_input), digit_count):
            placeholder_x = (
                center_x - total_width / 2
                + index * placeholder_spacing
            )
            underline = self._make_font(23).render(
                "_", False, self.orange
            )
            screen.blit(
                underline,
                underline.get_rect(
                    center=(int(placeholder_x), input_rect.centery + 1)
                )
            )

        # Feedback or blinking final victory message.
        if self.awaiting_exit_confirmation:
            if int(self.elapsed_time * 2.5) % 2 == 0:
                message_surface = self._fit_text(
                    "YOU DECODED THEM ALL, DETECTIVE!",
                    content_width,
                    18,
                    self.yellow,
                )
            else:
                message_surface = None
        else:
            message_surface = self._fit_text(
                self.message,
                content_width,
                16,
                self.message_color,
            ) if self.message else None

        if message_surface:
            feedback_y = input_rect.bottom + (10 if compact else 13)

            # Keep the feedback inside the monitor panel.
            max_feedback_y = (
                content_bottom - message_surface.get_height()
            )
            feedback_y = min(feedback_y, max_feedback_y)

            screen.blit(
                message_surface,
                message_surface.get_rect(
                    center=(
                        center_x,
                        feedback_y + message_surface.get_height() // 2,
                    )
                )
            )

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    def reset_attempt(self):
        super().reset_attempt()

        self.current_question = 0
        self.user_input = ""
        self.elapsed_time = 0.0
        self.message = ""
        self.message_color = self.green
        self.awaiting_exit_confirmation = False
