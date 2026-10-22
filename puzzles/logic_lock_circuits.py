# puzzles/logic_lock_circuits.py
# Level 1 add-on: Gate Lab (optional sandbox, key P) and the
# mandatory BUILD phase (wire the AND-gate alarm and verify it).
#
# Used as a mixin by LogicLockPuzzle, so it relies on these
# existing methods/attributes of that class:
#   _make_font, _draw_text, _fit_text, _draw_pixel_monitor,
#   elapsed_time, awaiting_exit_confirmation, submitted,
#   alarm_activated, message

import pygame

from puzzles.circuit_engine import (
    Circuit, Component, Workbench, GREEN, YELLOW, WHITE, GREY,
    CYAN, CYAN_DIM, ORANGE, RED, BOX_FILL,
)

LAB_GATES = ["AND", "OR", "XOR", "NAND", "NOR", "XNOR"]
CORRECT_OUTPUTS = [0, 0, 0, 1]


def _make_circuit(wired):
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


class LogicLockCircuitMixin:

    # ---------------------------------------------------------
    # SETUP / RESET
    # ---------------------------------------------------------

    def _init_circuits(self):
        self.phase = "ANALYZE"  # ANALYZE -> BUILD
        self.lab_open = False
        self.lab_gate_index = 0
        self.lab_message = (
            "Click the switches. Press 1-6 or click a gate to swap it."
        )
        self.lab_buttons = []

        self.lab = Workbench(_make_circuit(wired=True), allow_wiring=False)
        self.build = Workbench(_make_circuit(wired=False))
        self.build_message = (
            "Wire the circuit, test all 4 switch combinations, "
            "then press ENTER."
        )

    def start_build_phase(self):
        self.phase = "BUILD"
        self.lab_open = False
        self.build_message = (
            "AND IS CORRECT! NOW BUILD IT: wire A and B into the gate, "
            "and the gate into the ALARM."
        )

    # ---------------------------------------------------------
    # EVENTS  (returns True when the event was consumed)
    # ---------------------------------------------------------

    def circuit_handle_event(self, event):
        # Success screen: let the original Enter handling run.
        if self.awaiting_exit_confirmation or self.solved:
            return False

        if self.phase == "ANALYZE":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.lab_open = not self.lab_open
                return True
            if not self.lab_open:
                return False
            self._lab_event(event)
            return True

        # BUILD phase
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_build()
            return True

        msg = self.build.handle_event(event)
        if msg:
            self.build_message = msg
        return True

    def _set_lab_gate(self, index):
        self.lab_gate_index = index
        self.lab.circuit.comps["G"].kind = LAB_GATES[index]
        self.lab_message = f"{LAB_GATES[index]} gate selected. Test it!"

    def _lab_event(self, event):
        if event.type == pygame.KEYDOWN:
            keys = [
                pygame.K_1, pygame.K_2, pygame.K_3,
                pygame.K_4, pygame.K_5, pygame.K_6,
            ]
            if event.key in keys:
                self._set_lab_gate(keys.index(event.key))
            return

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            for index, rect in enumerate(self.lab_buttons):
                if rect.collidepoint(event.pos):
                    self._set_lab_gate(index)
                    return

        msg = self.lab.handle_event(event)
        if msg:
            self.lab_message = msg

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
    # DRAWING
    # ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "BUILD":
            self._draw_build(screen)
        elif self.lab_open:
            self._draw_lab(screen)
        else:
            self._draw_analyze(screen)

    def _frame(self, screen, alert_text, alert_colour):
        screen.fill((5, 7, 17))
        w, h = screen.get_size()
        panel = self._draw_pixel_monitor(
            screen, pygame.Rect(18, 14, w - 36, h - 28)
        )
        left = panel.left + 22
        right = panel.right - 22
        y = panel.top + 17

        if int(self.elapsed_time * 2.5) % 2 == 0:
            pygame.draw.rect(screen, alert_colour, (left, y + 4, 8, 8))
            alert = self._fit_text(
                alert_text, right - left - 20, 16, alert_colour
            )
            screen.blit(alert, (left + 19, y))

        return panel, left, right, y + 32

    def _draw_live_table(self, screen, x, y, w, bench):
        circuit = bench.circuit
        current = (circuit.comps["A"].value, circuit.comps["B"].value)
        rows = circuit.truth_table(["A", "B"], "Y")

        col_w = w // 3
        header_h, row_h = 25, 29

        for col, label in enumerate(["A", "B", "Y"]):
            cell = pygame.Rect(x + col * col_w, y, col_w, header_h)
            pygame.draw.rect(screen, (13, 29, 44), cell)
            pygame.draw.rect(screen, CYAN_DIM, cell, 2)
            self._draw_text(
                screen, label, cell.x + 8, cell.y + 5,
                ORANGE, self.small_font,
            )

        y += header_h
        for bits, out in rows:
            active = bits == current
            values = [str(bits[0]), str(bits[1]),
                      "—" if out is None else str(out)]
            for col, value in enumerate(values):
                cell = pygame.Rect(x + col * col_w, y, col_w, row_h)
                pygame.draw.rect(
                    screen, (14, 43, 58) if active else (7, 17, 31), cell
                )
                pygame.draw.rect(
                    screen, (0, 205, 220) if active else (40, 83, 105),
                    cell, 2 if active else 1,
                )
                colour = WHITE
                if col == 2 and out == 1:
                    colour = GREEN
                self._draw_text(
                    screen, value, cell.x + 8, cell.y + 7,
                    colour, self.small_font,
                )
            y += row_h
        return y

    # ---- Gate Lab ----

    def _draw_lab(self, screen):
        panel, left, right, y = self._frame(
            screen, "GATE LAB // SANDBOX (OPTIONAL)", YELLOW
        )
        width = right - left

        self._draw_text(
            screen, "GATE LAB", left, y, CYAN, self.title_font
        )
        y += 36

        line = self._fit_text(
            "Flip the switches and compare the gates. Which one rings "
            "the alarm ONLY when BOTH inputs are ON?",
            width, 15, WHITE,
        )
        screen.blit(line, (left, y))
        y += 30

        # Gate selector buttons
        gap = 8
        btn_w = (width - gap * (len(LAB_GATES) - 1)) // len(LAB_GATES)
        self.lab_buttons = []
        for i, name in enumerate(LAB_GATES):
            rect = pygame.Rect(left + i * (btn_w + gap), y, btn_w, 31)
            self.lab_buttons.append(rect)
            selected = i == self.lab_gate_index
            colour = CYAN if selected else (104, 115, 132)
            pygame.draw.rect(screen, (8, 23, 38), rect)
            pygame.draw.rect(screen, colour, rect, 3)
            label = self._fit_text(
                f"[{i + 1}] {name}", btn_w - 10, 13, colour
            )
            screen.blit(label, label.get_rect(center=rect.center))
        y += 31 + 14

        area_h = max(150, panel.bottom - y - 95)
        self.lab.area = pygame.Rect(left, y, int(width * 0.62), area_h)
        self.lab.draw(screen)

        table_x = self.lab.area.right + 22
        self._draw_text(
            screen, f"TRUTH TABLE: {LAB_GATES[self.lab_gate_index]}",
            table_x, y, CYAN, self.font,
        )
        self._draw_live_table(
            screen, table_x, y + 28, right - table_x, self.lab
        )

        y = self.lab.area.bottom + 12
        msg = self._fit_text(self.lab_message, width, 14, YELLOW)
        screen.blit(msg, (left, y))
        hint = self._fit_text(
            "P: Back to the mission   |   Click a switch to flip it",
            width, 13, GREY,
        )
        screen.blit(hint, (left, y + 24))

    # ---- Build phase ----

    def _draw_build(self, screen):
        panel, left, right, y = self._frame(
            screen, "SECURITY BREACH // LEVEL ONE // BUILD", RED
        )
        width = right - left

        self._draw_text(
            screen, "BUILD THE ALARM CIRCUIT", left, y,
            (0, 229, 239), self.title_font,
        )
        y += 38

        for text in (
            "Mission: ring the alarm only when smoke is detected AND "
            "the system is armed.",
            "Drag from an OUTPUT pin (right side) to an INPUT pin "
            "(left side). Right-click an input pin to remove a wire.",
        ):
            line = self._fit_text(text, width, 14, WHITE)
            screen.blit(line, (left, y))
            y += 22
        y += 10

        area_h = max(150, panel.bottom - y - 85)
        self.build.area = pygame.Rect(left, y, int(width * 0.62), area_h)
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
            if int(self.elapsed_time * 2.5) % 2 == 0:
                msg = self._fit_text(self.build_message, width, 15, YELLOW)
                screen.blit(msg, (left, y))
            hint = self._fit_text(
                "PRESS ENTER AGAIN TO CONTINUE", width, 13, GREY
            )
            screen.blit(hint, (left, y + 26))
        else:
            colour = YELLOW
            if self.build_message.startswith(("WRONG", "CIRCUIT INC")):
                colour = RED
            msg = self._fit_text(self.build_message, width, 14, colour)
            screen.blit(msg, (left, y))
            hint = self._fit_text(
                "ENTER: Verify the circuit", width, 13, GREY
            )
            screen.blit(hint, (left, y + 24))