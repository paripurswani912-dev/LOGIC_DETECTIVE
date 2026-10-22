# puzzles/logic_architect_circuits.py
# Level 5 add-on. Adds a BUILD step AFTER the K-map grouping step:
#
#   FILL    (reconstruct the K-map)      <- original
#   GROUP   (find the minimal groups)    <- original
#   BUILD   (place gates, wire, test)    <- NEW (this file)
#
# Used as a mixin by LogicArchitectPuzzle. It relies on these existing
# members of that class:
#   draw_text, fit_font (static helpers), awaiting_return, solved,
#   ONES, DONT_CARE, _draw_map (the old draw method, renamed)

import pygame
import settings

from puzzles.circuit_engine import Circuit, Component, Workbench
from screen_borders import draw_pixel_monitor

PALETTE = ["NOT", "AND", "OR", "XOR", "XNOR", "NAND", "NOR"]
MAX_GATES = 7
OPTIMAL_GATES = 4          # XNOR + NOT + AND + OR


def _make_build_circuit():
    c = Circuit()
    for i, name in enumerate("ABCD"):
        c.add(Component(name, "SWITCH", 0.09, 0.14 + i * 0.24, name))
    c.add(Component("Y", "LED", 0.92, 0.50, "F"))
    return c


class LogicArchitectCircuitMixin:

    # ---------------------------------------------------------
    # SETUP / RESET
    # ---------------------------------------------------------

    def _init_circuits(self):
        """Call at the end of __init__ and in reset_attempt()."""
        self.final_expr = ""
        self.build = Workbench(
            _make_build_circuit(), allow_wiring=True, allow_placing=True
        )
        self.palette_rects = []
        self.build_message = ""
        self.build_color = settings.YELLOW

    def start_build_phase(self):
        """Called by check_solution() when the groups are correct."""
        self.phase = "BUILD"
        self.build_message = (
            "Click a gate to add it, wire it up, then press ENTER."
        )
        self.build_color = settings.YELLOW

    # ---------------------------------------------------------
    # EVENTS (returns True when the event was consumed)
    # ---------------------------------------------------------

    def circuit_handle_event(self, event):
        if (
            self.phase != "BUILD"
            or self.awaiting_return
            or self.solved
        ):
            return False

        self._build_event(event)
        return True

    def _build_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_build()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in zip(PALETTE, self.palette_rects):
                if rect.collidepoint(event.pos):
                    self.build_message = self.build.spawn(
                        name, max_gates=MAX_GATES
                    )
                    self.build_color = settings.CYAN
                    return

        msg = self.build.handle_event(event)
        if msg:
            self.build_message = msg
            self.build_color = settings.CYAN

    # ---------------------------------------------------------
    # CHECKING
    # ---------------------------------------------------------

    @staticmethod
    def _minterm(bits):
        a, b, c, d = bits
        return (a << 3) | (b << 2) | (c << 1) | d

    def _expected(self, bits):
        """1, 0, or None (don't-care) for A, B, C, D."""
        m = self._minterm(bits)
        if m in self.DONT_CARE:
            return None
        return 1 if m in self.ONES else 0

    def verify_build(self):
        rows = self.build.circuit.truth_table(["A", "B", "C", "D"], "Y")

        for bits, out in rows:
            if out is None:
                self.build_message = (
                    "CIRCUIT INCOMPLETE: every input pin needs a wire, "
                    "and F must be connected."
                )
                self.build_color = settings.RED
                return

        tested = 0
        for bits, out in rows:
            expected = self._expected(bits)
            if expected is None:
                continue            # don't-care: either output is fine
            tested += 1
            if out != expected:
                a, b, c, d = bits
                self.build_message = (
                    f"WRONG at A={a} B={b} C={c} D={d} "
                    f"(m{self._minterm(bits)}): "
                    f"expected {expected}, got {out}."
                )
                self.build_color = settings.RED
                return

        used = self.build.circuit.count_gates()
        self.awaiting_return = True
        if used <= OPTIMAL_GATES:
            self.build_message = (
                f"CIRCUIT VERIFIED! {tested}/{tested} tests pass "
                f"with {used} gates: OPTIMAL!"
            )
        else:
            self.build_message = (
                f"CIRCUIT VERIFIED! {tested}/{tested} tests pass "
                f"({used} gates). Can you do it in {OPTIMAL_GATES}?"
            )
        self.build_color = settings.GREEN

    # ---------------------------------------------------------
    # DRAWING
    # ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "BUILD":
            self._draw_build(screen)
        else:
            self._draw_map(screen)

    def _centered(self, screen, text, size, colour, cx, y, width):
        font = self.fit_font(text, size, width)
        return self.draw_text(
            screen, text, font, colour, (cx, y),
            center=True, max_width=width,
        )

    def _draw_build(self, screen):
        screen.fill(settings.BLACK)
        panel = draw_pixel_monitor(screen)

        margin_x = max(20, int(panel.width * 0.025))
        left = panel.x + margin_x
        right = panel.right - margin_x
        width = right - left
        cx = panel.centerx
        ph = panel.height

        # Blinking alert
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            alert = "VAULT ALARM PUZZLE // LEVEL FIVE // BUILD THE CIRCUIT"
            y = panel.y + int(ph * 0.035)
            font = self.fit_font(
                alert, max(18, int(panel.width * 0.018)), width - 40
            )
            pygame.draw.rect(
                screen, settings.RED, (left + 3, y + 3, 12, 12)
            )
            self.draw_text(
                screen, alert, font, settings.RED,
                (left + 31, y), max_width=width - 40,
            )

        y = panel.y + int(ph * 0.10)
        self._centered(
            screen, f"BUILD IT:  {self.final_expr}",
            max(24, int(panel.width * 0.026)), settings.CYAN,
            cx, y, width,
        )
        y += int(ph * 0.05)

        for text in (
            "Click a gate below to add it. Drag gates to move them. "
            "Drag from an OUTPUT pin (right) to an INPUT pin (left).",
            "Right-click a gate to delete it, or an input pin to "
            "remove a wire. Click A-D to flip the switches.",
        ):
            self._centered(
                screen, text, max(17, int(panel.width * 0.016)),
                settings.WHITE, cx, y, width,
            )
            y += int(ph * 0.035)
        y += int(ph * 0.012)

        # Gate palette
        gap = 8
        btn_w = (width - gap * (len(PALETTE) - 1)) // len(PALETTE)
        btn_h = max(32, int(ph * 0.058))
        self.palette_rects = []
        for i, name in enumerate(PALETTE):
            rect = pygame.Rect(left + i * (btn_w + gap), y, btn_w, btn_h)
            self.palette_rects.append(rect)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(
                screen, settings.PANEL_BLUE, rect, border_radius=8
            )
            pygame.draw.rect(
                screen,
                settings.CYAN if hover else settings.GREY,
                rect, width=3, border_radius=8,
            )
            font = self.fit_font(
                name, max(22, int(btn_h * 0.6)), btn_w - 12
            )
            self.draw_text(
                screen, name, font, settings.YELLOW,
                rect.center, center=True, max_width=btn_w - 12,
            )
        y += btn_h + 10

        # Workbench + live check column
        area_h = max(150, panel.bottom - y - int(ph * 0.14))
        self.build.area = pygame.Rect(left, y, int(width * 0.70), area_h)
        self.build.draw(screen)

        col_x = self.build.area.right + 16
        col_w = right - col_x
        circuit = self.build.circuit
        bits = tuple(circuit.comps[n].value for n in "ABCD")
        expected = self._expected(bits)
        yours = circuit.value("Y")
        a, b, c, d = bits

        line_h = max(26, int(ph * 0.05))
        small = max(17, int(panel.width * 0.016))

        self.draw_text(
            screen, "LIVE CHECK",
            self.fit_font("LIVE CHECK", small + 4, col_w),
            settings.CYAN, (col_x, y), max_width=col_w,
        )

        if expected is None:
            exp_text = "EXPECTED F = X (any)"
            ok = True
        else:
            exp_text = f"EXPECTED F = {expected}"
            ok = yours == expected

        rows = [
            (f"A={a} B={b} C={c} D={d}", settings.WHITE),
            (exp_text, settings.YELLOW),
            (
                "YOUR F = ?" if yours is None else f"YOUR F = {yours}",
                settings.GREY if yours is None
                else (settings.GREEN if ok else settings.RED),
            ),
            (
                f"GATES: {circuit.count_gates()}/{MAX_GATES}",
                settings.WHITE,
            ),
            (f"TIP: {OPTIMAL_GATES} gates is enough", settings.GREY),
        ]
        ry = y + line_h
        for text, colour in rows:
            self.draw_text(
                screen, text, self.fit_font(text, small, col_w),
                colour, (col_x, ry), max_width=col_w,
            )
            ry += line_h

        # Footer
        fy = self.build.area.bottom + int(ph * 0.03)
        if self.awaiting_return:
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                self._centered(
                    screen, self.build_message,
                    max(20, int(panel.width * 0.019)), settings.GREEN,
                    cx, fy, width,
                )
            self._centered(
                screen,
                "NOTHING ESCAPES YOUR LOGIC, DETECTIVE. VAULT UNLOCKED!",
                max(18, int(panel.width * 0.018)), self.ORANGE,
                cx, fy + int(ph * 0.04), width,
            )
            self._centered(
                screen, "PRESS ENTER TO RETURN TO THE LAB",
                max(17, int(panel.width * 0.016)), settings.GREY,
                cx, fy + int(ph * 0.08), width,
            )
        else:
            self._centered(
                screen, self.build_message,
                max(19, int(panel.width * 0.018)), self.build_color,
                cx, fy, width,
            )
            self._centered(
                screen, "ENTER: test all 15 required input combinations "
                        "(m12 is a don't-care)",
                max(17, int(panel.width * 0.016)), settings.GREY,
                cx, fy + int(ph * 0.045), width,
            )