# puzzles/logic_lock_circuits.py
# Level 1 progression:
# Stage 3: Existing truth-table puzzle, then mandatory circuit build
# (Stage 2 "Gate Analysis" page has been removed.)

import pygame

from puzzles.circuit_engine import (
    Circuit, Component, Workbench, GREEN, YELLOW, WHITE, GREY,
    CYAN, CYAN_DIM, ORANGE, RED, BOX_FILL,
)

CORRECT_OUTPUTS = [0, 0, 0, 1]

BG = (5, 7, 17)
PANEL = (7, 17, 31)
SYMBOL = (0, 218, 231)
SYMBOL_DIM = (44, 103, 125)
TEXT = (220, 232, 244)


def _make_circuit(wired=True):
    c = Circuit()
    c.add(Component("A", "SWITCH", 0.13, 0.28, "A", "SMOKE SENSOR"))
    c.add(Component("B", "SWITCH", 0.13, 0.72, "B", "SYSTEM ARMED"))
    c.add(Component("G", "AND", 0.50, 0.50))
    c.add(Component("Y", "LED", 0.87, 0.50, "ALARM"))

    if wired:
        c.connect("A", "G", 0)
        c.connect("B", "G", 1)
        c.connect("G", "Y", 0)

    return c


def _pixel_line(surface, color, points, width=3):
    """Chunky, pixel-style lines for logic-gate symbols."""
    points = [(int(x), int(y)) for x, y in points]
    pygame.draw.lines(surface, color, False, points, width)

    # Square endpoint pixels give the strokes a retro look.
    for x, y in points:
        pygame.draw.rect(
            surface, color,
            (x - width // 2, y - width // 2, width, width)
        )


def draw_gate_symbol(surface, gate, rect, color=SYMBOL, scale=1):
    """Draw a recognizable logic-gate symbol using Pygame primitives.

    No longer used by the removed gate page. Kept in case another file
    imports it; safe to delete if nothing else uses it.
    """
    rect = pygame.Rect(rect)
    cx, cy = rect.center

    w = max(12, int(rect.width * 0.66))
    h = max(12, int(rect.height * 0.66))
    left = cx - w // 2
    right = cx + w // 2
    top = cy - h // 2
    bottom = cy + h // 2
    mid = cy
    stroke = max(2, int(3 * scale))

    input_top = (left - max(5, w // 5), top + h // 3)
    input_bottom = (left - max(5, w // 5), top + 2 * h // 3)

    _pixel_line(surface, color, [
        input_top, (left, input_top[1])
    ], stroke)
    _pixel_line(surface, color, [
        input_bottom, (left, input_bottom[1])
    ], stroke)

    if gate in ("AND", "NAND"):
        points = [
            (left, top), (left + w // 2, top),
            (left + 3 * w // 4, top + h // 8),
            (right, mid),
            (left + 3 * w // 4, bottom - h // 8),
            (left + w // 2, bottom), (left, bottom),
            (left, top),
        ]
        _pixel_line(surface, color, points, stroke)

    elif gate in ("OR", "NOR", "XOR", "XNOR"):
        points = [
            (left, top),
            (left + w // 3, top),
            (left + 2 * w // 3, top + h // 8),
            (right, mid),
            (left + 2 * w // 3, bottom - h // 8),
            (left + w // 3, bottom),
            (left, bottom),
            (left + w // 6, mid),
            (left, top),
        ]
        _pixel_line(surface, color, points, stroke)

        if gate in ("XOR", "XNOR"):
            _pixel_line(surface, color, [
                (left - max(5, w // 6), top),
                (left - max(2, w // 12), mid),
                (left - max(5, w // 6), bottom),
            ], stroke)

    elif gate == "NOT":
        _pixel_line(surface, color, [
            (left, top), (right - 5, mid), (left, bottom),
            (left, top)
        ], stroke)
        pygame.draw.circle(surface, color, (right, mid), 4, stroke)

    elif gate == "BUFFER":
        _pixel_line(surface, color, [
            (left, top), (right, mid), (left, bottom),
            (left, top)
        ], stroke)

    if gate in ("NAND", "NOR", "XNOR"):
        pygame.draw.circle(
            surface, color, (right + 5, mid), 4, stroke
        )

    output_x = right + (11 if gate in ("NAND", "NOR", "XNOR", "NOT") else 4)
    _pixel_line(surface, color, [
        (output_x, mid), (min(rect.right - 2, output_x + 10), mid)
    ], stroke)


class LogicLockCircuitMixin:
    # ---------------------------------------------------------
    # SETUP / RESET
    # ---------------------------------------------------------

    def _init_circuits(self):
        # Start directly at the existing truth-table puzzle (ANALYZE).
        # This is the same state the game used to reach after the
        # old gate-analysis page was completed.
        self.phase = "ANALYZE"
        self.lab_open = False          # kept in case other code reads it
        self.selected_gate = None
        self.selected_row = 0

        self.build = Workbench(_make_circuit(wired=False))
        self.build_message = (
            "Wire A and B into the gate, then connect the gate to ALARM."
        )

    def start_build_phase(self):
        self.phase = "BUILD"
        self.lab_open = False
        self.build_message = (
            "AND IS CORRECT! NOW BUILD IT: wire A and B into the gate, "
            "and the gate into the ALARM."
        )

    # ---------------------------------------------------------
    # EVENTS
    # ---------------------------------------------------------

    def circuit_handle_event(self, event):
        if self.awaiting_exit_confirmation or self.solved:
            return False

        if self.phase == "ANALYZE":
            return False

        if self.phase == "BUILD":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.verify_build()
                return True

            msg = self.build.handle_event(event)
            if msg:
                self.build_message = msg
            return True

        return False

    # ---------------------------------------------------------
    # VERIFY THE BUILT CIRCUIT
    # ---------------------------------------------------------

    def verify_build(self):
        rows = self.build.circuit.truth_table(["A", "B"], "Y")
        outputs = [out for _, out in rows]

        if None in outputs:
            self.build_message = (
                "CIRCUIT INCOMPLETE: every input pin needs a wire."
            )
        elif outputs != CORRECT_OUTPUTS:
            self.build_message = (
                "WRONG LOGIC: the alarm must ring ONLY when A and B "
                "are both 1. Check your wiring."
            )
        else:
            self.awaiting_exit_confirmation = True
            self.submitted = True
            self.alarm_activated = True
            self.build_message = "CIRCUIT VERIFIED! ALARM HAS BEEN ACTIVATED!"

    # ---------------------------------------------------------
    # DRAW ROUTING
    # ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "BUILD":
            self._draw_build(screen)
        else:
            self._draw_analyze(screen)

    def _frame(self, screen, alert_text, alert_colour):
        screen.fill(BG)
        w, h = screen.get_size()
        panel = self._draw_pixel_monitor(
            screen, pygame.Rect(18, 14, w - 36, h - 28)
        )
        left = panel.left + 22
        right = panel.right - 22
        y = panel.top + 17

        if int(self.elapsed_time * 2.5) % 2 == 0:
            pygame.draw.rect(
                screen, alert_colour, (left, y + 4, 8, 8)
            )
            alert = self._fit_text(
                alert_text, right - left - 20, 16, alert_colour
            )
            screen.blit(alert, (left + 19, y))

        return panel, left, right, y + 32

    def _draw_live_table(self, screen, x, y, w, bench):
        circuit = bench.circuit
        current = (
            circuit.comps["A"].value,
            circuit.comps["B"].value,
        )
        rows = circuit.truth_table(["A", "B"], "Y")
        col_w = max(1, w // 3)
        header_h, row_h = 23, 25

        for col, label in enumerate(["A", "B", "Y"]):
            cell = pygame.Rect(x + col * col_w, y, col_w, header_h)
            pygame.draw.rect(screen, (13, 29, 44), cell)
            pygame.draw.rect(screen, CYAN_DIM, cell, 2)
            self._draw_text(
                screen, label, cell.x + 6, cell.y + 4,
                ORANGE, self.small_font
            )

        y += header_h
        for bits, out in rows:
            active = bits == current
            values = [
                str(bits[0]), str(bits[1]),
                "—" if out is None else str(out)
            ]

            for col, value in enumerate(values):
                cell = pygame.Rect(
                    x + col * col_w, y, col_w, row_h
                )
                pygame.draw.rect(
                    screen, (14, 43, 58) if active else PANEL, cell
                )
                pygame.draw.rect(
                    screen, SYMBOL if active else (40, 83, 105),
                    cell, 2 if active else 1
                )
                colour = GREEN if col == 2 and out == 1 else WHITE
                self._draw_text(
                    screen, value, cell.x + 6, cell.y + 5,
                    colour, self.small_font
                )
            y += row_h

        return y

    def _draw_build(self, screen):
        panel, left, right, y = self._frame(
            screen, "SECURITY BREACH // LEVEL ONE // STAGE 4: BUILD", RED
        )
        width = right - left

        self._draw_text(
            screen, "BUILD THE ALARM CIRCUIT", left, y,
            CYAN, self.title_font
        )
        y += 38

        for text in (
            "Mission: ring the alarm only when smoke is detected AND "
            "the system is armed.",
            "Drag from an OUTPUT pin to an INPUT pin. Right-click an "
            "input pin to remove a wire.",
        ):
            line = self._fit_text(text, width, 14, WHITE)
            screen.blit(line, (left, y))
            y += 22
        y += 10

        area_h = max(150, panel.bottom - y - 85)
        self.build.area = pygame.Rect(
            left, y, int(width * 0.62), area_h
        )
        self.build.draw(screen)

        table_x = self.build.area.right + 22
        self._draw_text(
            screen, "LIVE TRUTH TABLE", table_x, y, CYAN, self.font
        )
        self._draw_live_table(
            screen, table_x, y + 28, right - table_x, self.build
        )

        y = self.build.area.bottom + 12

        if self.awaiting_exit_confirmation:
            msg = self._fit_text(self.build_message, width, 14, YELLOW)
            screen.blit(msg, (left, y))
            hint = self._fit_text(
                "PRESS ENTER AGAIN TO CONTINUE", width, 13, GREY
            )
            screen.blit(hint, (left, y + 26))
        else:
            colour = RED if self.build_message.startswith(
                ("WRONG", "CIRCUIT INC")
            ) else YELLOW
            msg = self._fit_text(self.build_message, width, 14, colour)
            screen.blit(msg, (left, y))
            hint = self._fit_text(
                "ENTER: Verify the circuit", width, 13, GREY
            )
            screen.blit(hint, (left, y + 24))