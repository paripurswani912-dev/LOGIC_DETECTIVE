
import pygame
import settings

from puzzles.base_puzzle import BasePuzzle
from screen_borders import draw_pixel_monitor


class FinalOverridePuzzle(BasePuzzle):
    """Level 4: Evaluate a Boolean expression before time runs out."""

    def __init__(self):
        super().__init__()

        self.input_values = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
        }

        self.time_left = settings.FINAL_LEVEL_TIME
        self.failed = False
        self.output_value = None

        # Press Enter a second time to return to the lab.
        self.awaiting_return = False
        self.completed = False

        self.message = "Set A, B, C and D, then submit your answer."
        self.message_color = settings.WHITE

        self.title_font = pygame.font.Font(None, 44)
        self.heading_font = pygame.font.Font(None, 32)
        self.expression_font = pygame.font.Font(None, 38)
        self.input_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 23)

        self.input_rects = {}
        self.submit_rect = pygame.Rect(0, 0, 0, 0)
        self.expression_rect = pygame.Rect(0, 0, 0, 0)

    # ---------------------------------------------------------------
    # Logic
    # ---------------------------------------------------------------

    def toggle_input(self, name):
        if self.failed or self.awaiting_return:
            return

        self.input_values[name] = 1 - self.input_values[name]
        self.output_value = None

        self.message = f"Input {name} is now {self.input_values[name]}."
        self.message_color = settings.CYAN

    def calculate_output(self):
        """
        Evaluate Y = NOT ((A OR B) AND (C XOR D)).
        XOR is 1 when C and D are different.
        """
        a = self.input_values["A"]
        b = self.input_values["B"]
        c = self.input_values["C"]
        d = self.input_values["D"]

        or_result = bool(a or b)
        xor_result = c != d
        and_result = or_result and xor_result
        output = not and_result

        return int(output)

    def check_answer(self):
        if self.failed or self.awaiting_return:
            return

        self.output_value = self.calculate_output()

        if self.output_value == 1:
            self.awaiting_return = True
            self.message = "OVERRIDE ACCEPTED!"
            self.message_color = settings.GREEN
        else:
            self.message = (
                "ACCESS DENIED! Output is 0. "
                "Re-evaluate the expression!"
            )
            self.message_color = settings.RED

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
        self.awaiting_return = False
        self.completed = False

        self.message = "Set A, B, C and D, then submit your answer."
        self.message_color = settings.WHITE

    # ---------------------------------------------------------------
    # Keyboard controls
    # ---------------------------------------------------------------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.failed:
            if event.key == pygame.K_r:
                self.reset_attempt()
            return

        if self.awaiting_return:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.completed = True
                self.solved = True
            return

        if self.solved:
            return

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
            pygame.K_KP_ENTER,
            pygame.K_SPACE,
        ):
            self.check_answer()

    # ---------------------------------------------------------------
    # Timer
    # ---------------------------------------------------------------

    def update(self, dt):
        if self.failed or self.awaiting_return or self.solved:
            return

        self.time_left -= dt

        if self.time_left <= 0:
            self.time_left = 0
            self.failed = True
            self.message = "TIME EXPIRED! Press R to retry this level."
            self.message_color = settings.RED

    # ---------------------------------------------------------------
    # Drawing helpers
    # ---------------------------------------------------------------

    @staticmethod
    def draw_text(
        screen,
        text,
        font,
        color,
        position,
        center=False,
        max_width=None,
    ):
        """Draw text, shrinking it when necessary to fit."""

        if max_width is not None:
            while True:
                image = font.render(text, True, color)

                if image.get_width() <= max_width or font.get_height() <= 14:
                    break

                font = pygame.font.Font(
                    None,
                    max(14, font.get_height() - 1),
                )
        else:
            image = font.render(text, True, color)

        rect = image.get_rect()

        if center:
            rect.center = position
        else:
            rect.topleft = position

        screen.blit(image, rect)
        return rect

    @staticmethod
    def fit_font(text, preferred_size, max_width, bold=False):
        size = preferred_size

        while size > 14:
            font = pygame.font.Font(None, size)
            image = font.render(text, True, (255, 255, 255))

            if image.get_width() <= max_width:
                return font

            size -= 1

        return pygame.font.Font(None, 14)

    # ---------------------------------------------------------------
    # Draw screen
    # ---------------------------------------------------------------

    def draw(self, screen):
        screen.fill(settings.BLACK)

        # Shared monitor frame: keep the border consistent with Levels 1–3.
        panel = draw_pixel_monitor(screen)

        width, height = screen.get_size()

        margin_x = max(20, int(panel.width * 0.025))
        content_left = panel.x + margin_x
        content_right = panel.right - margin_x
        content_width = content_right - content_left
        center_x = panel.centerx

        # -----------------------------------------------------------
        # Blinking security alert
        # The square and text share the same blink timing and color.
        # -----------------------------------------------------------

        alert_y = panel.y + int(panel.height * 0.045)
        alert_visible = (pygame.time.get_ticks() // 500) % 2 == 0

        if alert_visible:
            alert_text = "SECURITY NETWORK // LEVEL FOUR"
            alert_font = self.fit_font(
                alert_text,
                max(18, int(panel.width * 0.018)),
                content_width - 40,
            )

            alert_surface = alert_font.render(
                alert_text,
                True,
                settings.RED,
            )

            # Vertically align the square with the actual text height.
            square_size = max(12, min(16, int(alert_surface.get_height() * 0.62)))
            square_x = content_left + 3
            square_y = alert_y + (
                alert_surface.get_height() - square_size
            ) // 2

            pygame.draw.rect(
                screen,
                settings.RED,
                pygame.Rect(
                    square_x,
                    square_y,
                    square_size,
                    square_size,
                ),
            )

            self.draw_text(
                screen,
                alert_text,
                alert_font,
                settings.RED,
                (square_x + square_size + 14, alert_y),
                max_width=content_width - square_size - 25,
            )

        # -----------------------------------------------------------
        # Intro line
        # -----------------------------------------------------------

        intro = (
            "The timer is already running, Detective! "
            "THINK FAST BEFORE FLIPPING THE SWITCH..."
        )

        intro_y = panel.y + int(panel.height * 0.105)
        intro_font = self.fit_font(
            intro,
            max(22, int(panel.width * 0.023)),
            content_width,
        )

        self.draw_text(
            screen,
            intro,
            intro_font,
            settings.CYAN,
            (center_x, intro_y),
            center=True,
            max_width=content_width,
        )

        # -----------------------------------------------------------
        # Countdown
        # -----------------------------------------------------------

        seconds = max(0, int(self.time_left))
        timer_text = (
            f"TIME LEFT: {seconds // 60:02d}:"
            f"{seconds % 60:02d}"
        )

        timer_color = (
            settings.RED if seconds <= 20 else settings.YELLOW
        )

        timer_y = panel.y + int(panel.height * 0.17)
        timer_font = self.fit_font(
            timer_text,
            max(28, int(panel.width * 0.033)),
            content_width,
        )

        self.draw_text(
            screen,
            timer_text,
            timer_font,
            timer_color,
            (center_x, timer_y),
            center=True,
            max_width=content_width,
        )

        # Keyboard instructions remain outside the main expression box.
        controls_text = (
            "A/B/C/D: Toggle inputs   |   ENTER: Submit your answer"
        )
        controls_y = panel.y + int(panel.height * 0.245)

        controls_font = self.fit_font(
            controls_text,
            max(18, int(panel.width * 0.018)),
            content_width,
        )

        self.draw_text(
            screen,
            controls_text,
            controls_font,
            settings.GREY,
            (center_x, controls_y),
            center=True,
            max_width=content_width,
        )

        # -----------------------------------------------------------
        # Main Boolean expression box
        # -----------------------------------------------------------

        box_top = panel.y + int(panel.height * 0.285)
        box_bottom = panel.bottom - int(panel.height * 0.055)

        box = pygame.Rect(
            content_left,
            box_top,
            content_width,
            box_bottom - box_top,
        )

        self.expression_rect = box

        pygame.draw.rect(
            screen,
            settings.PANEL_BLUE,
            box,
            border_radius=18,
        )

        pygame.draw.rect(
            screen,
            settings.CYAN,
            box,
            width=3,
            border_radius=18,
        )

        # Expression
        expression = "Y = NOT ((A OR B) AND (C XOR D))"
        expression_y = box.y + int(box.height * 0.075)

        expression_font = self.fit_font(
            expression,
            max(26, int(box.width * 0.030)),
            box.width - 40,
        )

        self.draw_text(
            screen,
            expression,
            expression_font,
            settings.WHITE,
            (box.centerx, expression_y),
            center=True,
            max_width=box.width - 40,
        )

        # Reminder beneath the expression.
        remember = "Remember: XOR is 1 only when its inputs differ."
        remember_y = box.y + int(box.height * 0.16)

        remember_font = self.fit_font(
            remember,
            max(19, int(box.width * 0.020)),
            box.width - 40,
        )

        self.draw_text(
            screen,
            remember,
            remember_font,
            settings.YELLOW,
            (box.centerx, remember_y),
            center=True,
            max_width=box.width - 40,
        )

        simplify = "Try simplifying the expression before submitting."
        simplify_y = box.y + int(box.height * 0.225)

        simplify_font = self.fit_font(
            simplify,
            max(19, int(box.width * 0.020)),
            box.width - 40,
        )

        self.draw_text(
            screen,
            simplify,
            simplify_font,
            settings.YELLOW,
            (box.centerx, simplify_y),
            center=True,
            max_width=box.width - 40,
        )

        # -----------------------------------------------------------
        # Four input panels
        # -----------------------------------------------------------

        input_y = box.y + int(box.height * 0.34)
        input_h = max(78, int(box.height * 0.255))
        gap = max(12, int(box.width * 0.022))
        input_w = (
            box.width - 2 * 30 - 3 * gap
        ) // 4

        input_start_x = box.x + (
            box.width - (4 * input_w + 3 * gap)
        ) // 2

        self.input_rects = {}

        for index, name in enumerate(("A", "B", "C", "D")):
            x = input_start_x + index * (input_w + gap)

            rect = pygame.Rect(
                x,
                input_y,
                input_w,
                input_h,
            )
            self.input_rects[name] = rect

            value = self.input_values[name]
            active = value == 1

            border_color = settings.CYAN if active else settings.GREY
            state_color = settings.GREEN if active else settings.GREY

            pygame.draw.rect(
                screen,
                settings.BLACK,
                rect,
                border_radius=12,
            )

            pygame.draw.rect(
                screen,
                border_color,
                rect,
                width=3,
                border_radius=12,
            )

            strip_h = max(24, int(input_h * 0.34))
            strip_rect = pygame.Rect(
                rect.x + 2,
                rect.bottom - strip_h - 2,
                rect.width - 4,
                strip_h,
            )

            pygame.draw.rect(
                screen,
                settings.PANEL_BLUE,
                strip_rect,
                border_radius=8,
            )

            label = f"{name} = {value}"
            label_font = self.fit_font(
                label,
                max(24, int(input_h * 0.30)),
                rect.width - 12,
            )

            self.draw_text(
                screen,
                label,
                label_font,
                settings.WHITE,
                (
                    rect.centerx,
                    rect.y + int(input_h * 0.34),
                ),
                center=True,
                max_width=rect.width - 12,
            )

            state_text = "ON" if active else "OFF"
            state_font = self.fit_font(
                state_text,
                max(18, int(input_h * 0.21)),
                strip_rect.width - 10,
            )

            self.draw_text(
                screen,
                state_text,
                state_font,
                state_color,
                strip_rect.center,
                center=True,
                max_width=strip_rect.width - 10,
            )

            press_text = f"Press {name}"
            press_font = self.fit_font(
                press_text,
                max(16, int(panel.width * 0.017)),
                rect.width,
            )

            self.draw_text(
                screen,
                press_text,
                press_font,
                settings.GREY,
                (
                    rect.centerx,
                    rect.bottom + max(12, int(box.height * 0.025)),
                ),
                center=True,
                max_width=rect.width,
            )

        # -----------------------------------------------------------
        # Submit button / accepted state
        # -----------------------------------------------------------

        button_w = min(
            int(box.width * 0.34),
            max(240, int(panel.width * 0.34)),
        )
        button_h = max(46, int(box.height * 0.105))

        button_y = box.y + int(box.height * 0.68)
        max_button_y = (
            box.bottom - button_h - int(box.height * 0.22)
        )
        button_y = min(button_y, max_button_y)

        self.submit_rect = pygame.Rect(
            center_x - button_w // 2,
            button_y,
            button_w,
            button_h,
        )

        if self.awaiting_return:
            button_color = settings.GREEN
            button_label = "ACCEPTED"
            button_text_color = settings.BLACK
        else:
            button_color = settings.CYAN
            button_label = "SUBMIT [ENTER]"
            button_text_color = settings.BLACK

        outer_rect = self.submit_rect.inflate(10, 10)

        pygame.draw.rect(
            screen,
            settings.PANEL_BLUE,
            outer_rect,
            border_radius=14,
        )

        pygame.draw.rect(
            screen,
            settings.CYAN if not self.awaiting_return else settings.GREEN,
            outer_rect,
            width=2,
            border_radius=14,
        )

        pygame.draw.rect(
            screen,
            button_color,
            self.submit_rect,
            border_radius=12,
        )

        button_font = self.fit_font(
            button_label,
            max(22, int(button_h * 0.48)),
            button_w - 20,
        )

        self.draw_text(
            screen,
            button_label,
            button_font,
            button_text_color,
            self.submit_rect.center,
            center=True,
            max_width=button_w - 20,
        )

        # -----------------------------------------------------------
        # Output / feedback
        # -----------------------------------------------------------

        if self.failed:
            feedback_y = box.y + int(box.height * 0.86)
            feedback = self.message

            feedback_font = self.fit_font(
                feedback,
                max(18, int(box.width * 0.019)),
                box.width - 36,
            )

            self.draw_text(
                screen,
                feedback,
                feedback_font,
                settings.RED,
                (box.centerx, feedback_y),
                center=True,
                max_width=box.width - 36,
            )

            retry_y = min(
                box.bottom - 22,
                feedback_y + max(28, int(box.height * 0.055)),
            )

            self.draw_text(
                screen,
                "PRESS R TO RETRY",
                self.small_font,
                settings.YELLOW,
                (box.centerx, retry_y),
                center=True,
                max_width=box.width - 36,
            )

        elif self.awaiting_return:
            success_y = self.submit_rect.bottom + max(
                22, int(box.height * 0.055)
            )

            return_y = success_y + max(
                30, int(box.height * 0.065)
            )

            return_limit = box.bottom - 20

            if return_y > return_limit:
                success_y = box.bottom - int(box.height * 0.13)
                return_y = box.bottom - int(box.height * 0.065)

            # Blink the success message in orange.
            success_visible = (
                pygame.time.get_ticks() // 500
            ) % 2 == 0

            success_text = "YOU WERE FAST, DETECTIVE!"
            success_font = self.fit_font(
                success_text,
                max(24, int(box.width * 0.027)),
                box.width - 36,
            )

            if success_visible:
                self.draw_text(
                    screen,
                    success_text,
                    success_font,
                    settings.YELLOW,
                    (box.centerx, success_y),
                    center=True,
                    max_width=box.width - 36,
                )

            return_text = "PRESS ENTER AGAIN TO RETURN TO THE LAB"
            return_font = self.fit_font(
                return_text,
                max(17, int(box.width * 0.019)),
                box.width - 36,
            )

            self.draw_text(
                screen,
                return_text,
                return_font,
                settings.YELLOW,
                (box.centerx, return_y),
                center=True,
                max_width=box.width - 36,
            )

        else:
            if self.output_value is not None:
                output_text = f"OUTPUT Y = {self.output_value}"
                output_color = (
                    settings.GREEN
                    if self.output_value == 1
                    else settings.RED
                )

                output_y = box.y + int(box.height * 0.84)

                self.draw_text(
                    screen,
                    output_text,
                    self.heading_font,
                    output_color,
                    (box.centerx, output_y),
                    center=True,
                    max_width=box.width - 36,
                )

            else:
                message_y = box.y + int(box.height * 0.84)

                message_font = self.fit_font(
                    self.message,
                    max(18, int(box.width * 0.019)),
                    box.width - 36,
                )

                self.draw_text(
                    screen,
                    self.message,
                    message_font,
                    self.message_color,
                    (box.centerx, message_y),
                    center=True,
                    max_width=box.width - 36,
                )
