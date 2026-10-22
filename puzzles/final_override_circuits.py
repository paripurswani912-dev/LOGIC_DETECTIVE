# puzzles/final_override_circuits.py
# Level 4 add-on. Adds two steps AFTER the original "solve" step:
#
#   SOLVE    (original puzzle, timer runs here only)
#   IDENTIFY pick the simplified expression from four choices
#   BUILD    place gates from a palette, wire them, test all 16 inputs
#
# Used as a mixin by FinalOverridePuzzle. It relies on these existing
# members of that class:
#   draw_text, fit_font (static helpers), failed, awaiting_return,
#   solved, _draw_solve (the old draw method, renamed)

import pygame
import settings

from puzzles.circuit_engine import Circuit, Component, Workbench
from screen_borders import draw_pixel_monitor

PALETTE = ["NOT", "AND", "OR", "XOR", "XNOR", "NAND", "NOR"]
MAX_GATES = 8
OPTIMAL_GATES = 3          # NOR + XNOR + OR

# Y = NOT((A OR B) AND (C XOR D))  =  A'B' + (C XNOR D)
OPTIONS = [
    ("Y = A'B' + (C XOR D)", False),
    ("Y = (A + B)(C XNOR D)", False),
    ("Y = A'B' + (C XNOR D)", True),
    ("Y = A'B' + C D", False),
]
CORRECT_TEXT = next(text for text, ok in OPTIONS if ok)


def target(a, b, c, d):
    """The original expression: Y = NOT((A OR B) AND (C XOR D))."""
    return 1 - ((a | b) & (c ^ d))


def _make_build_circuit():
    c = Circuit()
    for i, name in enumerate("ABCD"):
        c.add(Component(name, "SWITCH", 0.09, 0.14 + i * 0.24, name))
    c.add(Component("Y", "LED", 0.92, 0.50, "Y"))
    return c


class FinalOverrideCircuitMixin:

    # ---------------------------------------------------------
    # SETUP / RESET
    # ---------------------------------------------------------

    def _init_circuits(self):
        self.phase = "SOLVE"            # SOLVE -> IDENTIFY -> BUILD
        self.pick_index = None
        self.pick_rects = []
        self.pick_message = (
            "Pick the expression, then press ENTER."
        )
        self.pick_color = settings.YELLOW

        self.build = Workbench(
            _make_build_circuit(), allow_wiring=True, allow_placing=True
        )
        self.palette_rects = []
        self.build_message = ""
        self.build_color = settings.YELLOW

    def start_identify_phase(self):
        """Called by check_answer() when the SOLVE step succeeds."""
        self.phase = "IDENTIFY"
        self.pick_index = None
        self.pick_message = "Pick the expression, then press ENTER."
        self.pick_color = settings.YELLOW

    def start_build_phase(self):
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
            self.phase == "SOLVE"
            or self.failed
            or self.awaiting_return
            or self.solved
        ):
            return False

        if self.phase == "IDENTIFY":
            self._identify_event(event)
        else:
            self._build_event(event)
        return True

    # ---- IDENTIFY ----

    def _identify_event(self, event):
        if event.type == pygame.KEYDOWN:
            keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]
            if event.key in keys:
                self.pick_index = keys.index(event.key)
            elif event.key == pygame.K_UP:
                self.pick_index = (
                    len(OPTIONS) - 1 if self.pick_index in (None, 0)
                    else self.pick_index - 1
                )
            elif event.key == pygame.K_DOWN:
                self.pick_index = (
                    0 if self.pick_index is None
                    else (self.pick_index + 1) % len(OPTIONS)
                )
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_pick()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.pick_rects):
                if rect.collidepoint(event.pos):
                    self.pick_index = i

    def _confirm_pick(self):
        if self.pick_index is None:
            self.pick_message = "SELECT AN EXPRESSION FIRST."
            self.pick_color = settings.YELLOW
        elif OPTIONS[self.pick_index][1]:
            self.start_build_phase()
        else:
            self.pick_message = (
                "NOT EQUIVALENT. Test it: does it match the original "
                "for every A, B, C, D?"
            )
            self.pick_color = settings.RED
            self.pick_index = None

    # ---- BUILD ----

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

    def verify_build(self):
        rows = self.build.circuit.truth_table(["A", "B", "C", "D"], "Y")

        for bits, out in rows:
            if out is None:
                self.build_message = (
                    "CIRCUIT INCOMPLETE: every input pin needs a wire, "
                    "and Y must be connected."
                )
                self.build_color = settings.RED
                return

        for bits, out in rows:
            if out != target(*bits):
                a, b, c, d = bits
                self.build_message = (
                    f"WRONG at A={a} B={b} C={c} D={d}: "
                    f"expected {target(*bits)}, got {out}."
                )
                self.build_color = settings.RED
                return

        used = self.build.circuit.count_gates()
        self.awaiting_return = True
        if used <= OPTIMAL_GATES:
            self.build_message = (
                f"CIRCUIT VERIFIED! 16/16 tests pass with {used} gates: "
                "OPTIMAL!"
            )
        else:
            self.build_message = (
                f"CIRCUIT VERIFIED! 16/16 tests pass ({used} gates). "
                f"Can you do it in {OPTIMAL_GATES}?"
            )
        self.build_color = settings.GREEN

    # ---------------------------------------------------------
    # DRAWING
    # ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "IDENTIFY":
            self._draw_identify(screen)
        elif self.phase == "BUILD":
            self._draw_build(screen)
        else:
            self._draw_solve(screen)

    def _frame(self, screen, alert_text):
        screen.fill(settings.BLACK)
        panel = draw_pixel_monitor(screen)

        margin_x = max(20, int(panel.width * 0.025))
        left = panel.x + margin_x
        right = panel.right - margin_x
        width = right - left

        if (pygame.time.get_ticks() // 500) % 2 == 0:
            y = panel.y + int(panel.height * 0.045)
            font = self.fit_font(
                alert_text, max(18, int(panel.width * 0.018)), width - 40
            )
            pygame.draw.rect(
                screen, settings.RED, (left + 3, y + 3, 12, 12)
            )
            self.draw_text(
                screen, alert_text, font, settings.RED,
                (left + 31, y), max_width=width - 40,
            )
        return panel, left, right, width

    def _centered(self, screen, text, size, colour, cx, y, width):
        font = self.fit_font(text, size, width)
        return self.draw_text(
            screen, text, font, colour, (cx, y),
            center=True, max_width=width,
        )

    # ---- IDENTIFY screen ----

    def _draw_identify(self, screen):
        panel, left, right, width = self._frame(
            screen, "SECURITY NETWORK // LEVEL FOUR // STEP 2 OF 3"
        )
        cx = panel.centerx
        ph = panel.height

        self._centered(
            screen, "OVERRIDE ACCEPTED! NOW IDENTIFY THE SIMPLIFIED FORM.",
            max(22, int(panel.width * 0.023)), settings.CYAN,
            cx, panel.y + int(ph * 0.13), width,
        )
        self._centered(
            screen, "Y = NOT ((A OR B) AND (C XOR D))",
            max(26, int(panel.width * 0.028)), settings.WHITE,
            cx, panel.y + int(ph * 0.21), width,
        )
        self._centered(
            screen, "Which expression is equivalent to it?",
            max(20, int(panel.width * 0.019)), settings.YELLOW,
            cx, panel.y + int(ph * 0.275), width,
        )

        opt_h = max(46, int(ph * 0.095))
        gap = max(10, int(ph * 0.022))
        opt_w = int(width * 0.74)
        top = panel.y + int(ph * 0.33)

        self.pick_rects = []
        for i, (text, _) in enumerate(OPTIONS):
            rect = pygame.Rect(cx - opt_w // 2, top + i * (opt_h + gap),
                               opt_w, opt_h)
            self.pick_rects.append(rect)
            chosen = i == self.pick_index

            pygame.draw.rect(
                screen, settings.PANEL_BLUE, rect, border_radius=10
            )
            pygame.draw.rect(
                screen,
                settings.CYAN if chosen else settings.GREY,
                rect, width=3, border_radius=10,
            )
            label = f"[{i + 1}]   {text}"
            font = self.fit_font(
                label, max(24, int(opt_h * 0.5)), rect.width - 30
            )
            self.draw_text(
                screen, label, font,
                settings.CYAN if chosen else settings.WHITE,
                rect.center, center=True, max_width=rect.width - 30,
            )

        y = top + len(OPTIONS) * (opt_h + gap)
        self._centered(
            screen, self.pick_message,
            max(19, int(panel.width * 0.019)), self.pick_color,
            cx, y + 4, width,
        )
        self._centered(
            screen, "1-4 or click: select   |   ENTER: confirm",
            max(17, int(panel.width * 0.016)), settings.GREY,
            cx, y + int(ph * 0.05), width,
        )

    # ---- BUILD screen ----

    def _draw_build(self, screen):
        panel, left, right, width = self._frame(
            screen, "SECURITY NETWORK // LEVEL FOUR // STEP 3 OF 3"
        )
        cx = panel.centerx
        ph = panel.height
        y = panel.y + int(ph * 0.10)

        self._centered(
            screen, f"BUILD IT:  {CORRECT_TEXT}",
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
        a, b, c, d = (circuit.comps[n].value for n in "ABCD")
        expected = target(a, b, c, d)
        yours = circuit.value("Y")

        line_h = max(26, int(ph * 0.05))
        small = max(17, int(panel.width * 0.016))

        self.draw_text(
            screen, "LIVE CHECK",
            self.fit_font("LIVE CHECK", small + 4, col_w),
            settings.CYAN, (col_x, y), max_width=col_w,
        )
        rows = [
            (f"A={a} B={b} C={c} D={d}", settings.WHITE),
            (f"EXPECTED Y = {expected}", settings.YELLOW),
            (
                "YOUR Y = ?" if yours is None else f"YOUR Y = {yours}",
                settings.GREY if yours is None
                else (settings.GREEN if yours == expected
                      else settings.RED),
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
                screen, "PRESS ENTER AGAIN TO RETURN TO THE LAB",
                max(17, int(panel.width * 0.016)), settings.YELLOW,
                cx, fy + int(ph * 0.045), width,
            )
        else:
            self._centered(
                screen, self.build_message,
                max(19, int(panel.width * 0.018)), self.build_color,
                cx, fy, width,
            )
            self._centered(
                screen, "ENTER: test all 16 input combinations",
                max(17, int(panel.width * 0.016)), settings.GREY,
                cx, fy + int(ph * 0.045), width,
            )