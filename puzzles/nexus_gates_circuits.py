"""puzzles/nexus_gates_circuits.py
Level 7 Phase 1 add-on: The Kill Switch Builder.

Synthesizes the master shutdown expression:
    Y = (A NAND B) XOR (C NOR D)
using at most 4 gates inside the shared Workbench circuit simulator.

Any functionally correct circuit passing all 16 rows of the truth table
and using <= 4 gates is accepted.
"""

import pygame
import settings

from puzzles.circuit_engine import (
    Circuit, Component, Workbench,
    BOX_FILL, CYAN, CYAN_DIM, WHITE, GREY, GREEN, YELLOW, RED, AREA_BG
)


PALETTE = ["NOT", "AND", "OR", "XOR", "XNOR", "NAND", "NOR"]
MAX_GATES = 4


def kill_switch_target(a, b, c, d):
    """Y = (A NAND B) XOR (C NOR D).

    Channel 1 (Power Bus Override): A NAND B
    Channel 2 (Logic Interlock Inversion): C NOR D
    Trigger: Exclusive-OR of both channels.
    """
    nand_ab = 1 - (a & b)
    nor_cd = 1 if (c == 0 and d == 0) else 0
    return nand_ab ^ nor_cd


def _make_kill_switch_circuit():
    c = Circuit()
    # Left switches: Upper pair (Power Subsystem), Lower pair (Auxiliary Logic)
    c.add(Component("A", "SWITCH", 0.08, 0.16, "A", "POWER A"))
    c.add(Component("B", "SWITCH", 0.08, 0.38, "B", "POWER B"))
    c.add(Component("C", "SWITCH", 0.08, 0.62, "C", "LOGIC C"))
    c.add(Component("D", "SWITCH", 0.08, 0.84, "D", "LOGIC D"))

    # Right output LED Y (Kill Switch Trigger)
    c.add(Component("Y", "LED", 0.92, 0.50, "Y", "KILL SW"))
    return c


class NexusGatesCircuitMixin:
    """Provides Phase 1 (Kill Switch synthesis) for NexusGatesPuzzle."""

    def _init_circuit_phase(self):
        self.circuit_verified = False
        self.circuit_message = (
            "Build Kill Switch: Y = (A NAND B) XOR (C NOR D). Max 4 gates. Click gate to place."
        )
        self.circuit_message_color = YELLOW
        self.workbench = Workbench(
            _make_kill_switch_circuit(),
            allow_wiring=True,
            allow_placing=True,
        )
        self.palette_rects = []
        self.circuit_buttons = {}

    def _reset_circuit(self):
        self.circuit_verified = False
        self.workbench = Workbench(
            _make_kill_switch_circuit(),
            allow_wiring=True,
            allow_placing=True,
        )
        self.circuit_message = "Workbench reset. Place gates from palette."
        self.circuit_message_color = CYAN

    def circuit_handle_event(self, event):
        """Handle mouse and keyboard events during the circuit build phase."""
        if self.circuit_verified:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.phase = "GATES"
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn_proceed = self.circuit_buttons.get("proceed")
                if btn_proceed and btn_proceed.collidepoint(event.pos):
                    self.phase = "GATES"
                    return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_circuit()
                return True
            if event.key == pygame.K_r:
                self._reset_circuit()
                return True

        # Palette clicking
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.palette_rects:
                if rect.collidepoint(event.pos):
                    msg = self.workbench.spawn(name, max_gates=MAX_GATES)
                    self.circuit_message = msg
                    self.circuit_message_color = CYAN
                    return True

            btn_verify = self.circuit_buttons.get("verify")
            if btn_verify and btn_verify.collidepoint(event.pos):
                self.verify_circuit()
                return True

            btn_reset = self.circuit_buttons.get("reset")
            if btn_reset and btn_reset.collidepoint(event.pos):
                self._reset_circuit()
                return True

            btn_proceed = self.circuit_buttons.get("proceed")
            if btn_proceed and btn_proceed.collidepoint(event.pos) and self.circuit_verified:
                self.phase = "GATES"
                return True

        # Workbench interaction (wiring, moving, flipping switches, right-click delete)
        msg = self.workbench.handle_event(event)
        if msg:
            self.circuit_message = msg
            self.circuit_message_color = CYAN

        return True

    def verify_circuit(self):
        """Evaluate circuit across all 16 input combinations."""
        c = self.workbench.circuit
        gate_count = c.count_gates()

        if gate_count > MAX_GATES:
            self.circuit_message = (
                f"GATE LIMIT EXCEEDED ({gate_count}/{MAX_GATES}). Reduce gate count."
            )
            self.circuit_message_color = RED
            return False

        rows = c.truth_table(["A", "B", "C", "D"], "Y")

        for (a, b, c_in, d), out in rows:
            if out is None:
                self.circuit_message = (
                    "CIRCUIT INCOMPLETE: Ensure all inputs are wired and connected to Y."
                )
                self.circuit_message_color = RED
                return False

        for (a, b, c_in, d), out in rows:
            expected = kill_switch_target(a, b, c_in, d)
            if out != expected:
                self.circuit_message = (
                    f"TEST FAILED at A={a} B={b} C={c_in} D={d}: expected {expected}, got {out}."
                )
                self.circuit_message_color = RED
                return False

        # All 16 passed!
        self.circuit_verified = True
        self.circuit_message = (
            "KILL SWITCH VERIFIED! Y = (A NAND B) XOR (C NOR D) CONFIRMED. PRESS ENTER TO OPEN GATES."
        )
        self.circuit_message_color = GREEN
        return True

    def _draw_circuit_phase(self, screen, inner, scale):
        """Draw Phase 1 circuit builder UI."""
        pad = max(8, int(12 * scale))
        gap = max(6, int(10 * scale))

        # 1. Header
        alert_text = "■ SECURITY OVERRIDE // PHASE ONE: SYNTHESIZE KILL SWITCH"
        alert_font = self._fit_font(alert_text, inner.width - 20, max(12, int(18 * scale)))
        self._text(screen, alert_text, alert_font, RED, inner.x + 6, inner.y + 4)

        sub_text = "NEXUS-9 KILL SWITCH PROTOCOL: Y = (A NAND B) XOR (C NOR D)  [LIMIT: 4 GATES]"
        sub_font = self._fit_font(sub_text, inner.width - 20, max(10, int(13 * scale)))
        self._text(screen, sub_text, sub_font, CYAN, inner.centerx, inner.y + max(25, int(30 * scale)), center=True)

        # 2. Gate Palette bar
        palette_y = inner.y + max(48, int(56 * scale))
        palette_h = max(38, int(46 * scale))
        palette_panel = pygame.Rect(inner.x, palette_y, inner.width, palette_h)
        self._draw_panel(screen, palette_panel, fill=BOX_FILL, border=CYAN_DIM)

        lbl_palette = "GATE PALETTE:"
        lbl_font = pygame.font.SysFont("monospace", max(10, int(12 * scale)), bold=True)
        self._text(screen, lbl_palette, lbl_font, GREY, palette_panel.x + 12, palette_panel.centery, center=False)

        btn_x = palette_panel.x + max(120, int(130 * scale))
        btn_w = max(55, int(72 * scale))
        btn_h = palette_h - 12
        btn_gap = max(4, int(8 * scale))

        self.palette_rects = []
        gate_font = pygame.font.SysFont("monospace", max(10, int(13 * scale)), bold=True)

        for gate in PALETTE:
            rect = pygame.Rect(btn_x, palette_panel.y + 6, btn_w, btn_h)
            self.palette_rects.append((gate, rect))

            hovered = rect.collidepoint(pygame.mouse.get_pos())
            border_col = CYAN if hovered else CYAN_DIM
            fill_col = (20, 48, 68) if hovered else (12, 28, 42)

            pygame.draw.rect(screen, fill_col, rect, border_radius=4)
            pygame.draw.rect(screen, border_col, rect, 1, border_radius=4)
            self._text(screen, gate, gate_font, WHITE if hovered else GREY, rect.centerx, rect.centery, center=True)

            btn_x += btn_w + btn_gap

        # Gates count: sits right after the last palette button, as
        # "| GATES: 3/4". The number updates every frame from the circuit.
        current_gates = self.workbench.circuit.count_gates()
        cnt_text = f"GATES: {current_gates}/{MAX_GATES}"
        cnt_col = RED if current_gates > MAX_GATES else (GREEN if current_gates > 0 else GREY)

        # btn_x is already just past the last button (loop adds width + gap).
        sep_x = btn_x + max(6, int(10 * scale))
        sep_w = gate_font.size("|")[0]
        self._text(
            screen, "|", gate_font, CYAN_DIM,
            sep_x + sep_w // 2, palette_panel.centery, center=True,
        )

        cnt_x = sep_x + sep_w + max(8, int(12 * scale))
        cnt_max_w = max(40, palette_panel.right - cnt_x - 12)
        cnt_font = self._fit_font(cnt_text, cnt_max_w, max(10, int(13 * scale)))
        cnt_w = cnt_font.size(cnt_text)[0]
        self._text(
            screen, cnt_text, cnt_font, cnt_col,
            cnt_x + cnt_w // 2, palette_panel.centery, center=True,
        )

        # 3. Workbench Canvas
        bottom_h = max(48, int(54 * scale))
        canvas_y = palette_panel.bottom + gap
        canvas_h = inner.bottom - bottom_h - gap - canvas_y
        canvas_panel = pygame.Rect(inner.x, canvas_y, inner.width, canvas_h)

        self._draw_panel(screen, canvas_panel, fill=AREA_BG, border=CYAN_DIM)
        self.workbench.area = canvas_panel
        self.workbench.draw(screen)

        # 4. Bottom controls and message bar
        bottom_panel = pygame.Rect(inner.x, inner.bottom - bottom_h, inner.width, bottom_h)
        self._draw_panel(screen, bottom_panel, fill=BOX_FILL, border=CYAN_DIM)

        # Buttons on the right of bottom bar
        ctrl_w = max(110, int(135 * scale))
        ctrl_h = bottom_h - 12
        ctrl_y = bottom_panel.y + 6

        # Proceed Button
        if self.circuit_verified:
            proc_rect = pygame.Rect(bottom_panel.right - ctrl_w - 8, ctrl_y, ctrl_w, ctrl_h)
            self.circuit_buttons["proceed"] = proc_rect
            pygame.draw.rect(screen, (25, 95, 55), proc_rect, border_radius=4)
            pygame.draw.rect(screen, GREEN, proc_rect, 2, border_radius=4)
            self._text(screen, "OPEN GATES ►", gate_font, WHITE, proc_rect.centerx, proc_rect.centery, center=True)
            right_offset = ctrl_w + 16
        else:
            right_offset = 8

        # Verify Button
        ver_rect = pygame.Rect(bottom_panel.right - right_offset - ctrl_w, ctrl_y, ctrl_w, ctrl_h)
        self.circuit_buttons["verify"] = ver_rect
        hover_ver = ver_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (22, 58, 80) if hover_ver else (14, 38, 56), ver_rect, border_radius=4)
        pygame.draw.rect(screen, CYAN if hover_ver else CYAN_DIM, ver_rect, 1, border_radius=4)
        self._text(screen, "TEST CIRCUIT", gate_font, CYAN if hover_ver else WHITE, ver_rect.centerx, ver_rect.centery, center=True)

        # Reset Button
        res_w = max(75, int(90 * scale))
        res_rect = pygame.Rect(ver_rect.left - res_w - 8, ctrl_y, res_w, ctrl_h)
        self.circuit_buttons["reset"] = res_rect
        hover_res = res_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (45, 20, 30) if hover_res else (28, 14, 20), res_rect, border_radius=4)
        pygame.draw.rect(screen, RED if hover_res else (120, 35, 45), res_rect, 1, border_radius=4)
        self._text(screen, "RESET", gate_font, RED if hover_res else GREY, res_rect.centerx, res_rect.centery, center=True)

        # Message text on left of bottom bar
        msg_max_w = res_rect.left - bottom_panel.left - 20
        msg_font = self._fit_font(self.circuit_message, msg_max_w, max(10, int(13 * scale)))
        self._text(
            screen,
            self.circuit_message,
            msg_font,
            self.circuit_message_color,
            bottom_panel.x + 14,
            bottom_panel.centery,
            center=False
        )
