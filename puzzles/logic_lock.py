# puzzles/logic_lock.py
# Level 1: Logic Lock — Pixel-Art Computer Interface

import pygame
from puzzles.base_puzzle import BasePuzzle
from puzzles.logic_lock_circuits import LogicLockCircuitMixin  # CHANGED


# CHANGED: the mixin comes BEFORE BasePuzzle
class LogicLockPuzzle(LogicLockCircuitMixin, BasePuzzle):

    def __init__(self):
        super().__init__()

        self.title = "LOGIC LOCK"
        self.selected_gate = None
        self.selected_row = 0
        self.elapsed_time = 0.0

        self.truth_table = [
            {"a": 0, "b": 0, "answer": None},
            {"a": 0, "b": 1, "answer": None},
            {"a": 1, "b": 0, "answer": None},
            {"a": 1, "b": 1, "answer": None},
        ]

        self.submitted = False
        self.alarm_activated = False
        self.awaiting_exit_confirmation = False

        self.message = ""
        self.feedback_color = (255, 220, 65)

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

        self.font = self._make_font(17)
        self.small_font = self._make_font(14)
        self.title_font = self._make_font(25)

        # CHANGED: must stay LAST, after fonts and elapsed_time exist.
        self._init_circuits()

    def _make_font(self, size):
        return pygame.font.SysFont(
            self.pixel_font_name, size, bold=True
        )

    # ---------------------------------------------------------
    # PIXEL MONITOR FRAME
    # ---------------------------------------------------------

    def _draw_pixel_monitor(self, screen, rect):
        x, y, w, h = rect

        bezel = (28, 30, 52)
        bezel_light = (48, 54, 91)
        bezel_dark = (15, 17, 34)
        screen_black = (4, 10, 22)
        screen_edge = (39, 91, 113)

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

        pygame.draw.rect(screen, screen_black, panel)
        pygame.draw.rect(screen, screen_edge, panel, 3)

        for px in range(panel.x + 8, panel.right - 8, 14):
            pygame.draw.rect(
                screen, (40, 86, 109),
                (px, panel.y + 5, 9, 3)
            )

        # Tiny monitor indicator lights.
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

    def _draw_text(
        self, screen, text, x, y, color, font=None
    ):
        font = font or self.small_font
        surface = font.render(text, False, color)
        screen.blit(surface, (x, y))
        return surface.get_rect(topleft=(x, y))

    def _fit_text(
        self, text, max_width, preferred_size, color
    ):
        size = preferred_size

        while size >= 8:
            font = self._make_font(size)
            surface = font.render(text, False, color)

            if surface.get_width() <= max_width:
                return surface

            size -= 1

        return self._make_font(8).render(
            text, False, color
        )

    # ---------------------------------------------------------
    # KEYBOARD CONTROLS
    # ---------------------------------------------------------

    def handle_event(self, event):
        # CHANGED: the Gate Lab and BUILD phase get the event first.
        if self.circuit_handle_event(event):
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):

            # After a successful activation, Enter a second time
            # to let the main game exit the puzzle interface.
            if self.awaiting_exit_confirmation:
                self.solved = True
                return

            if self.solved:
                return

            self.check_answer()
            return

        # Don't allow changing the circuit while the success
        # message is waiting for the second Enter.
        if self.solved or self.awaiting_exit_confirmation:
            return

        row_keys = {
            pygame.K_1: 0,
            pygame.K_2: 1,
            pygame.K_3: 2,
            pygame.K_4: 3,
            pygame.K_KP1: 0,
            pygame.K_KP2: 1,
            pygame.K_KP3: 2,
            pygame.K_KP4: 3,
        }

        if event.key in row_keys:
            self.selected_row = row_keys[event.key]

        elif event.key in (pygame.K_LEFT, pygame.K_0):
            self.truth_table[
                self.selected_row
            ]["answer"] = 0

        elif event.key in (pygame.K_RIGHT, pygame.K_1):
            self.truth_table[
                self.selected_row
            ]["answer"] = 1

        elif event.key == pygame.K_a:
            self.selected_gate = "AND"

        elif event.key == pygame.K_o:
            self.selected_gate = "OR"

    # ---------------------------------------------------------
    # CHECK THE ANSWER (analysis step)
    # ---------------------------------------------------------

    def check_answer(self):
        correct_outputs = [0, 0, 0, 1]
        entered_outputs = [
            row["answer"] for row in self.truth_table
        ]

        # CHANGED: a correct answer now unlocks the BUILD phase.
        # The alarm is activated only after the built circuit is
        # verified (see verify_build in logic_lock_circuits.py).
        if (
            self.selected_gate == "AND"
            and entered_outputs == correct_outputs
        ):
            self.start_build_phase()
            return

        # Incorrect answer: alarm stays deactivated.
        self.submitted = True
        self.alarm_activated = False
        self.message = "ALARM IS STILL IN DEACTIVATED MODE!"
        self.feedback_color = (255, 220, 65)

        # Reset failed attempts for another try.
        for row in self.truth_table:
            row["answer"] = None

        self.selected_row = 0
        self.selected_gate = None

    def update(self, dt):
        self.elapsed_time += dt

    # ---------------------------------------------------------
    # DRAW: ANALYSIS SCREEN
    # CHANGED: renamed from draw() to _draw_analyze(). The mixin's
    # draw() now chooses between this, the Gate Lab and BUILD.
    # ---------------------------------------------------------

    def _draw_analyze(self, screen):
        screen.fill((5, 7, 17))

        width, height = screen.get_size()

        monitor_rect = pygame.Rect(
            18, 14, width - 36, height - 28
        )

        panel = self._draw_pixel_monitor(
            screen, monitor_rect
        )

        left = panel.left + 22
        right = panel.right - 22
        content_width = right - left

        y = panel.top + 17

        # 1. Blinking security alert.
        if int(self.elapsed_time * 2.5) % 2 == 0:
            pygame.draw.rect(
                screen, (255, 55, 69),
                (left, y + 4, 8, 8)
            )

            alert = self._fit_text(
                "SECURITY BREACH // LEVEL ONE",
                content_width - 20,
                16,
                (255, 65, 78),
            )
            screen.blit(alert, (left + 19, y))

        y += 32

        # 2. Main warning.
        self._draw_text(
            screen,
            "INTRUSION DETECTED!",
            left, y,
            (0, 229, 239),
            self.title_font,
        )

        y += 36

        # 3. Single-line challenge.
        instruction_lines = [
            "Input A: Smoke sensor detects smoke.",
            "Input B: Security system is armed.",
            "Alarm activates only when BOTH inputs are ON.",
        ]

        instruction_font = self._make_font(17)
        for line in instruction_lines:
            surface = instruction_font.render(
                line, False, (222, 232, 244)
            )
            screen.blit(surface, (left, y))
            y += 23

        y += 4

        pygame.draw.line(
            screen, (48, 75, 105),
            (left, y), (right, y), 2
        )
        y += 10

        # 4. Controls.
        self._draw_text(
            screen, "CONTROLS",
            left, y,
            (255, 184, 72), self.font
        )
        y += 24

        controls = [
            "KEYS 1-4: Select row number",
            "LEFT ARROW KEY / RIGHT ARROW KEY: Set output to '0' OR '1'",
            # CHANGED: P added on the same line, so the layout
            # doesn't move.
            "A: AND Gate | O: OR Gate | P: Gate Lab (optional)",
            "ENTER: Verify the circuit",
        ]

        for line in controls:
            surface = self._fit_text(
                line, content_width, 13,
                (190, 207, 226)
            )
            screen.blit(surface, (left, y))
            y += 20

        y += 2

        pygame.draw.line(
            screen, (48, 75, 105),
            (left, y), (right, y), 2
        )
        y += 10

        # 5. Gate selector.
        self._draw_text(
            screen, "SELECT THE LOGIC GATE",
            left, y,
            (0, 229, 239), self.font
        )
        y += 27

        gap = 14
        gate_width = (content_width - gap) // 2
        gate_height = 31

        and_rect = pygame.Rect(
            left, y, gate_width, gate_height
        )
        or_rect = pygame.Rect(
            left + gate_width + gap, y,
            gate_width, gate_height
        )

        # Both buttons are grey until selected.
        neutral = (104, 115, 132)
        selected = (0, 218, 231)

        and_color = (
            selected if self.selected_gate == "AND"
            else neutral
        )
        or_color = (
            selected if self.selected_gate == "OR"
            else neutral
        )

        for rect, color in (
            (and_rect, and_color),
            (or_rect, or_color),
        ):
            pygame.draw.rect(
                screen, (8, 23, 38), rect
            )
            pygame.draw.rect(screen, color, rect, 3)

        and_label = self._make_font(13).render(
            "[A] AND GATE", False, and_color
        )
        or_label = self._make_font(13).render(
            "[O] OR GATE", False, or_color
        )

        screen.blit(
            and_label,
            and_label.get_rect(center=and_rect.center)
        )
        screen.blit(
            or_label,
            or_label.get_rect(center=or_rect.center)
        )

        y += gate_height + 9

        # 6. Circuit table.
        self._draw_text(
            screen, "CIRCUIT CONFIGURATION",
            left, y,
            (255, 184, 72), self.font
        )
        y += 25

        table_width = int(content_width * 0.92)
        col_widths = [
            int(table_width * 0.27),
            int(table_width * 0.25),
            int(table_width * 0.25),
        ]
        col_widths.append(
            table_width - sum(col_widths)
        )

        col_x = [left]
        for col_width in col_widths:
            col_x.append(col_x[-1] + col_width)

        headers = ["ROW", "A", "B", "OUTPUT"]
        header_height = 25
        row_height = 29

        for col, label in enumerate(headers):
            cell = pygame.Rect(
                col_x[col], y,
                col_widths[col], header_height
            )

            pygame.draw.rect(
                screen, (13, 29, 44), cell
            )
            pygame.draw.rect(
                screen, (44, 103, 125), cell, 2
            )

            label_surface = self._fit_text(
                label, col_widths[col] - 10,
                14, (255, 184, 72)
            )

            screen.blit(
                label_surface,
                label_surface.get_rect(
                    midleft=(cell.x + 6, cell.centery)
                )
            )

        y += header_height

        for index, row in enumerate(self.truth_table):
            values = [
                str(index + 1),
                str(row["a"]),
                str(row["b"]),
                (
                    "—" if row["answer"] is None
                    else str(row["answer"])
                ),
            ]

            is_selected = index == self.selected_row

            for col, value in enumerate(values):
                cell = pygame.Rect(
                    col_x[col], y,
                    col_widths[col], row_height
                )

                fill = (
                    (14, 43, 58)
                    if is_selected
                    else (7, 17, 31)
                )

                border = (
                    (0, 205, 220)
                    if is_selected
                    else (40, 83, 105)
                )

                pygame.draw.rect(screen, fill, cell)
                pygame.draw.rect(
                    screen, border, cell,
                    2 if is_selected else 1
                )

                text_color = (
                    (0, 235, 239)
                    if is_selected
                    else (220, 232, 245)
                )

                value_surface = self._fit_text(
                    value, col_widths[col] - 10,
                    14, text_color
                )

                screen.blit(
                    value_surface,
                    value_surface.get_rect(
                        midleft=(cell.x + 6, cell.centery)
                    )
                )

            y += row_height

        # 7. Result message. (Only a WRONG answer shows here now,
        # because a correct one moves on to the BUILD screen.)
        if self.submitted and not self.alarm_activated:
            status_surface = self._fit_text(
                "ALARM IS STILL IN DEACTIVATED MODE!",
                content_width,
                15,
                (255, 220, 65),
            )

            status_y = y + 9
            max_status_y = (
                panel.bottom - status_surface.get_height() - 12
            )
            status_y = min(status_y, max_status_y)

            if int(self.elapsed_time * 2.5) % 2 == 0:
                screen.blit(
                    status_surface,
                    (left, status_y)
                )

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    def reset_attempt(self):
        super().reset_attempt()

        for row in self.truth_table:
            row["answer"] = None

        self.selected_row = 0
        self.selected_gate = None
        self.solved = False

        self.submitted = False
        self.alarm_activated = False
        self.awaiting_exit_confirmation = False

        self.elapsed_time = 0.0
        self.message = ""
        self.feedback_color = (255, 220, 65)

        self._init_circuits()  # CHANGED: back to ANALYZE phase