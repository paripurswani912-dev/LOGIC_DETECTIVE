
import pygame
import settings
from puzzles.base_puzzle import BasePuzzle


class FinalOverridePuzzle(BasePuzzle):
    def __init__(self):
        super().__init__()

        self.title_font = pygame.font.Font(None, 46)
        self.heading_font = pygame.font.Font(None, 30)
        self.font = pygame.font.Font(None, 25)
        self.small_font = pygame.font.Font(None, 21)

        # Four binary inputs.
        self.input_values = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
        }

        # Four clickable input panels.
        self.input_rects = {
            "A": pygame.Rect(125, 270, 145, 90),
            "B": pygame.Rect(330, 270, 145, 90),
            "C": pygame.Rect(535, 270, 145, 90),
            "D": pygame.Rect(740, 270, 145, 90),
        }

        self.submit_rect = pygame.Rect(390, 405, 220, 55)

        self.time_left = settings.FINAL_LEVEL_TIME
        self.failed = False
        self.output_value = None

        self.message = "Set A, B, C and D, then submit."
        self.message_color = settings.WHITE

    def handle_event(self, event):
        if event.type not in (
            pygame.KEYDOWN,
            pygame.MOUSEBUTTONDOWN,
        ):
            return

        # After timeout, R restarts this puzzle only.
        if self.failed:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset_attempt()
            return

        if self.solved:
            return

        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_a: "A",
                pygame.K_b: "B",
                pygame.K_c: "C",
                pygame.K_d: "D",
            }

            if event.key in key_map:
                self.toggle_input(key_map[event.key])

            elif event.key in (
                pygame.K_RETURN,
                pygame.K_SPACE,
            ):
                self.check_answer()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return

            for name, rect in self.input_rects.items():
                if rect.collidepoint(event.pos):
                    self.toggle_input(name)
                    return

            if self.submit_rect.collidepoint(event.pos):
                self.check_answer()

    def toggle_input(self, name):
        self.input_values[name] = 1 - self.input_values[name]

        self.message = (
            f"Input {name} is now {self.input_values[name]}."
        )
        self.message_color = settings.CYAN
        self.output_value = None

    def calculate_output(self):
        """
        Evaluate Y = NOT((A OR B) AND (C XOR D)).

        XOR is 1 when C and D are different.
        """

        a = self.input_values["A"]
        b = self.input_values["B"]
        c = self.input_values["C"]
        d = self.input_values["D"]

        or_result = a or b
        xor_result = c != d
        and_result = or_result and xor_result
        output = not and_result

        return int(output)

    def check_answer(self):
        self.output_value = self.calculate_output()

        if self.output_value == 1:
            self.solved = True
            self.message = (
                "OVERRIDE ACCEPTED! Output Y = 1."
            )
            self.message_color = settings.GREEN
        else:
            self.message = (
                "ACCESS DENIED! Output Y = 0. "
                "Re-evaluate the expression."
            )
            self.message_color = settings.RED

    def update(self, dt):
        if self.solved or self.failed:
            return

        self.time_left -= dt

        if self.time_left <= 0:
            self.time_left = 0
            self.failed = True
            self.message = (
                "TIME EXPIRED! Press R to retry this level."
            )
            self.message_color = settings.RED

    def draw(self, screen):
        screen.fill(settings.BLACK)

        # Title
        title = self.title_font.render(
            "FINAL OVERRIDE",
            True,
            settings.CYAN,
        )
        screen.blit(
            title,
            title.get_rect(center=(500, 42)),
        )

        subtitle = self.small_font.render(
            "NEXUS-9 CORE SECURITY TERMINAL",
            True,
            settings.GREY,
        )
        screen.blit(
            subtitle,
            subtitle.get_rect(center=(500, 78)),
        )

        # Countdown
        seconds = max(0, int(self.time_left))
        timer_text = (
            f"TIME LEFT: {seconds // 60:02d}:"
            f"{seconds % 60:02d}"
        )

        timer_color = (
            settings.RED
            if seconds <= 20
            else settings.YELLOW
        )

        timer = self.heading_font.render(
            timer_text,
            True,
            timer_color,
        )
        screen.blit(
            timer,
            timer.get_rect(center=(500, 118)),
        )

        # Boolean expression
        expression = self.heading_font.render(
            "Y = NOT ((A OR B) AND (C XOR D))",
            True,
            settings.WHITE,
        )
        screen.blit(
            expression,
            expression.get_rect(center=(500, 170)),
        )

        # De Morgan's law hint
        hint = self.small_font.render(
            "Hint: NOT( X AND Y ) = NOT X OR NOT Y",
            True,
            settings.YELLOW,
        )
        screen.blit(
            hint,
            hint.get_rect(center=(500, 205)),
        )

        # Four binary input panels
        for name, rect in self.input_rects.items():
            value = self.input_values[name]
            color = (
                settings.GREEN
                if value == 1
                else settings.GREY
            )

            pygame.draw.rect(
                screen,
                settings.PANEL_BLUE,
                rect,
                border_radius=10,
            )
            pygame.draw.rect(
                screen,
                color,
                rect,
                width=3,
                border_radius=10,
            )

            label = self.heading_font.render(
                f"{name} = {value}",
                True,
                settings.WHITE,
            )
            screen.blit(
                label,
                label.get_rect(center=rect.center),
            )

            state_text = self.small_font.render(
                "ON" if value else "OFF",
                True,
                color,
            )
            screen.blit(
                state_text,
                state_text.get_rect(
                    center=(rect.centerx, rect.bottom + 20)
                ),
            )

        # Submit button
        button_color = (
            settings.GREEN
            if self.solved
            else settings.CYAN
        )

        pygame.draw.rect(
            screen,
            button_color,
            self.submit_rect,
            border_radius=8,
        )

        button_text = self.font.render(
            "ACCEPTED" if self.solved else "SUBMIT",
            True,
            settings.BLACK,
        )
        screen.blit(
            button_text,
            button_text.get_rect(
                center=self.submit_rect.center
            ),
        )

        # Output indicator
        if self.output_value is not None:
            output_text = self.heading_font.render(
                f"OUTPUT Y = {self.output_value}",
                True,
                (
                    settings.GREEN
                    if self.output_value == 1
                    else settings.RED
                ),
            )
            screen.blit(
                output_text,
                output_text.get_rect(center=(500, 485)),
            )

        # Feedback
        message = self.small_font.render(
            self.message,
            True,
            self.message_color,
        )
        screen.blit(
            message,
            message.get_rect(center=(500, 530)),
        )

        if self.failed:
            retry = self.font.render(
                "Press R to retry",
                True,
                settings.YELLOW,
            )
            screen.blit(
                retry,
                retry.get_rect(center=(500, 565)),
            )
        elif self.solved:
            success = self.heading_font.render(
                "FACILITY SECURITY DISABLED",
                True,
                settings.GREEN,
            )
            screen.blit(
                success,
                success.get_rect(center=(500, 575)),
            )
        else:
            controls = self.small_font.render(
                "Click an input or press A, B, C, D. "
                "ENTER = Submit",
                True,
                settings.GREY,
            )
            screen.blit(
                controls,
                controls.get_rect(center=(500, 590)),
            )

    def reset_attempt(self):
        super().reset_attempt()

        self.input_values = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
        }

        self.time_left = settings.FINAL_LEVEL_TIME
        self.failed = False
        self.output_value = None

        self.message = "Set A, B, C and D, then submit."
        self.message_color = settings.WHITE
