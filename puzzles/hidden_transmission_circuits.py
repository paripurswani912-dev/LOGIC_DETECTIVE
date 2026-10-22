# puzzles/hidden_transmission_circuits.py
# Level 2 add-on: BUILD phase. Wire a Gray -> Binary converter
# (3 XOR gates) and verify it against all 16 inputs.
#
# Mixin for HiddenTransmissionPuzzle. Relies on:
#   _draw_pixel_monitor, _fit_text, elapsed_time,
#   awaiting_exit_confirmation, solved

import pygame

from puzzles.circuit_engine import (
    Circuit, Component, Workbench, YELLOW, WHITE, GREY, CYAN, ORANGE, RED,
)

G_IDS = ["G3", "G2", "G1", "G0"]
B_IDS = ["B3", "B2", "B1", "B0"]


def gray_to_bin(bits):
    out = [bits[0]]
    for g in bits[1:]:
        out.append(out[-1] ^ g)
    return tuple(out)


def _make_circuit():
    c = Circuit()
    rows = [0.13, 0.38, 0.62, 0.87]
    for gid, bid, ry in zip(G_IDS, B_IDS, rows):
        c.add(Component(gid, "SWITCH", 0.08, ry, gid))
        c.add(Component(bid, "LED", 0.92, ry, bid))
    # Pre-placed XOR gates; the player only draws the wires.
    c.add(Component("X2", "XOR", 0.34, 0.38))
    c.add(Component("X1", "XOR", 0.54, 0.62))
    c.add(Component("X0", "XOR", 0.74, 0.87))
    return c


def _bits_text(values):
    return "".join("?" if v is None else str(v) for v in values)


class HiddenTransmissionCircuitMixin:

    def _init_circuits(self):
        self.phase = "SOLVE"  # SOLVE -> BUILD
        self.build = Workbench(_make_circuit())
        self.build_message = ""

    def start_build_phase(self):
        self.phase = "BUILD"
        self.build_message = (
            "ALL DECODED! NOW AUTOMATE IT: build a Gray-to-Binary "
            "converter from the XOR gates."
        )

    # returns True when the event was consumed
    def circuit_handle_event(self, event):
        if (
            self.phase != "BUILD"
            or self.awaiting_exit_confirmation
            or self.solved
        ):
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_build()
            return True

        msg = self.build.handle_event(event)
        if msg:
            self.build_message = msg
        return True

    def verify_build(self):
        rows = self.build.circuit.truth_table_multi(G_IDS, B_IDS)

        if any(None in outs for _, outs in rows):
            self.build_message = (
                "CIRCUIT INCOMPLETE: every LED and XOR input needs a wire."
            )
            return

        wrong = sum(
            1 for bits, outs in rows if outs != gray_to_bin(bits)
        )
        if wrong:
            self.build_message = (
                f"WRONG LOGIC: {wrong} of 16 inputs give the wrong binary. "
                "Hint: each binary bit = previous binary bit XOR next Gray bit."
            )
        else:
            self.awaiting_exit_confirmation = True
            self.elapsed_time = 0.0
            self.build_message = "CONVERTER VERIFIED! ALL 16 INPUTS CORRECT!"

    def _draw_build(self, screen):
        screen.fill((5, 7, 17))
        w, h = screen.get_size()
        panel = self._draw_pixel_monitor(
            screen, pygame.Rect(18, 14, w - 36, h - 28)
        )
        left, right = panel.left + 22, panel.right - 22
        width = right - left
        y = panel.top + 17

        if int(self.elapsed_time * 2.5) % 2 == 0:
            pygame.draw.rect(screen, RED, (left, y + 4, 8, 8))
            alert = self._fit_text(
                "SIGNAL INTERCEPTED // LEVEL TWO // BUILD",
                width - 20, 16, RED,
            )
            screen.blit(alert, (left + 19, y))
        y += 32

        title = self._fit_text("BUILD THE GRAY-TO-BINARY CONVERTER",
                               width, 22, CYAN)
        screen.blit(title, (left, y))
        y += title.get_height() + 8

        for text in (
            "B3 = G3   |   B2 = B3 XOR G2   |   B1 = B2 XOR G1   "
            "|   B0 = B1 XOR G0",
            "Drag from an OUTPUT pin (right) to an INPUT pin (left). "
            "Right-click an input pin to remove a wire.",
        ):
            line = self._fit_text(text, width, 14, WHITE)
            screen.blit(line, (left, y))
            y += 22
        y += 8

        area_h = max(260, panel.bottom - y - 85)
        self.build.area = pygame.Rect(left, y, int(width * 0.68), area_h)
        self.build.draw(screen)

        # Live readout beside the workbench.
        c = self.build.circuit
        gray = [c.comps[i].value for i in G_IDS]
        outs = [c.value(i) for i in B_IDS]
        rx = self.build.area.right + 22
        rw = right - rx
        ry = y
        for label, text, colour in (
            ("GRAY IN", _bits_text(gray), CYAN),
            ("YOUR OUTPUT", _bits_text(outs), YELLOW),
            ("AS DECIMAL",
             "?" if None in outs else str(int("".join(map(str, outs)), 2)),
             ORANGE),
        ):
            lab = self._fit_text(label, rw, 14, GREY)
            screen.blit(lab, (rx, ry))
            val = self._fit_text(text, rw, 26, colour)
            screen.blit(val, (rx, ry + 20))
            ry += 70

        y = self.build.area.bottom + 12
        if self.awaiting_exit_confirmation:
            if int(self.elapsed_time * 2.5) % 2 == 0:
                msg = self._fit_text(self.build_message, width, 15, YELLOW)
                screen.blit(msg, (left, y))
            hint = self._fit_text("PRESS ENTER AGAIN TO CONTINUE",
                                  width, 13, GREY)
            screen.blit(hint, (left, y + 26))
        else:
            colour = RED if self.build_message.startswith(
                ("WRONG", "CIRCUIT INC")) else YELLOW
            msg = self._fit_text(self.build_message, width, 14, colour)
            screen.blit(msg, (left, y))
            hint = self._fit_text(
                "Click a switch to flip it   |   ENTER: Verify the circuit",
                width, 13, GREY,
            )
            screen.blit(hint, (left, y + 24))