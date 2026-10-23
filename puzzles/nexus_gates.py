"""puzzles/nexus_gates.py
Level 7: NEXUS-9 // THE FALSE EXIT.

Secret final level. The rogue AI NEXUS-9 has sealed the true exit behind
four monolithic security gates. Exactly one gate has an authentic plaque matching
all previous system records. Three decoys contain realistic corruption.

The detective has 2 attempts. On the first failure, NEXUS goes aggressive
with digital distortion, jitter, and a 45-second lockdown countdown.
A second failure reboots the gates with a new permutation.
Opening the correct gate shuts down NEXUS-9 and triggers the real escape.
"""

import math
import random
import pygame
import settings

from .base_puzzle import BasePuzzle
from screen_borders import draw_pixel_monitor
from .nexus_gates_circuits import NexusGatesCircuitMixin


# ----------------------------------------------------------------------
# LEVEL 7 CONFIGURATION & CLUE DATA
# ----------------------------------------------------------------------

BUILD_KILL_SWITCH = True

CLUES = {
    "L1_AND_TABLE": "0001",
    "L2_NUMBERS":   "3 5 9 14 3 5 8 12",
    "L3_SEQUENCE":  "A-B-A-C-D-C",
    "L4_ONES":      "10",                       # number of rows where Y = 1 out of 16
    "L5_EXPR":      "B XNOR D + B C'",
    "L6_KEY":       "K7",
    "L6_SEED":      "01101",
}


# ----------------------------------------------------------------------
# COLOURS (matching Levels 1-6 UI)
# ----------------------------------------------------------------------

BG = (4, 10, 22)
PANEL = (15, 34, 49)
PANEL_DARK = (8, 22, 35)
CYAN = (0, 218, 225)
CYAN_DIM = (39, 91, 113)
WHITE = (220, 235, 246)
GREY = (112, 137, 158)
YELLOW = (255, 190, 45)
GREEN = (35, 230, 125)
RED = (255, 48, 75)
DARK_INK = (4, 20, 30)


# Plaque field display labels
FIELD_KEYS = ["L1", "L2", "L3", "L4", "L5", "L6"]
FIELD_LABELS = {
    "L1": "L1 AND TABLE",
    "L2": "L2 NUMBERS",
    "L3": "L3 SEQUENCE",
    "L4": "L4 ROWS HIGH",
    "L5": "L5 EXPRESSION",
    "L6": "L6 KEY / SEED",
}

# Authentic constant values
CORRECT_PLAQUE = {
    "L1": CLUES["L1_AND_TABLE"],
    "L2": CLUES["L2_NUMBERS"],
    "L3": CLUES["L3_SEQUENCE"],
    "L4": CLUES["L4_ONES"],
    "L5": CLUES["L5_EXPR"],
    "L6": f"{CLUES['L6_KEY']} / {CLUES['L6_SEED']}",
}

# Realistic decoy mutations
DECOY_MUTATIONS = {
    "L1": ["0111", "0110"],
    "L2": [
        "3 9 5 14 3 5 8 12",
        "3 5 9 14 5 3 8 12",
        "3 5 9 13 3 5 8 12",
        "3 5 9 14 3 5 7 12",
        "3 5 9 14 3 5 8 11",
    ],
    "L3": ["A-B-C-A-D-C", "A-B-A-C-C-D", "A-B-A-D-C-C", "A-A-B-C-D-C"],
    "L4": ["6", "12", "8"],
    "L5": ["B XOR D + B C'", "B XNOR D + B C"],
    "L6": ["K9 / 01101", "7K / 01101", "K7 / 10110"],
}


class NexusGatesPuzzle(NexusGatesCircuitMixin, BasePuzzle):
    """Level 7: The False Exit — Four Gate Terminal."""

    def __init__(self):
        super().__init__()
        self.seed_counter = 77
        self.strikes = 0
        self.aggressive = False
        self.countdown = 45.0
        self.selected_gate = 0
        self.opened_gate = None
        self.solved_awaiting_confirm = False
        self.gate_rects = []
        self.gate_buttons = []
        self.gates = []
        self.correct_index = 0

        # Phase control
        if BUILD_KILL_SWITCH:
            self.phase = "KILL_SWITCH"
            self._init_circuit_phase()
        else:
            self.phase = "GATES"

        self.restart("Select the authentic gate (1-4 or Click). Press ENTER to confirm.")

    def _generate_plaques(self):
        """Generate four gates where exactly one is authentic and 3 are unique decoys."""
        rng = random.Random(self.seed_counter)
        self.seed_counter += 1

        correct = dict(CORRECT_PLAQUE)
        decoys = []
        seen = {tuple(correct[k] for k in FIELD_KEYS)}

        attempts = 0
        while len(decoys) < 3 and attempts < 200:
            attempts += 1
            d = dict(CORRECT_PLAQUE)
            n_mutations = rng.choice([1, 2])
            mutated_fields = rng.sample(FIELD_KEYS, n_mutations)
            for k in mutated_fields:
                d[k] = rng.choice(DECOY_MUTATIONS[k])

            tup = tuple(d[k] for k in FIELD_KEYS)
            if tup not in seen:
                seen.add(tup)
                decoys.append(d)

        all_gates = [correct] + decoys
        rng.shuffle(all_gates)
        self.gates = all_gates
        self.correct_index = self.gates.index(correct)

    def restart(self, message="Gate system initialized. Review all plaques carefully."):
        """Reset attempts, reshuffle plaques with new seed, and restore state."""
        self.strikes = 0
        self.aggressive = False
        self.countdown = 45.0
        self.opened_gate = None
        self.solved_awaiting_confirm = False
        self.solved = False
        self.message = message
        self.message_color = YELLOW
        self._generate_plaques()

    def update(self, dt):
        """Update countdown timer and aggressive glitch state."""
        if self.phase == "GATES" and self.aggressive and not self.solved_awaiting_confirm:
            self.countdown -= dt
            if self.countdown <= 0.0:
                self.countdown = 0.0
                # Timeout counts as wrong choice 2
                self.restart("TIMEOUT! NEXUS-9 REBOOTED THE GATES. SECURITY CODES RESHUFFLED.")
                self.message_color = RED

    def handle_event(self, event):
        """Handle mouse and keyboard interactions."""
        if self.phase == "KILL_SWITCH":
            return self.circuit_handle_event(event)

        # In GATES phase:
        if self.solved_awaiting_confirm:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.solved = True
            return

        # Key navigation
        if event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_4:
                self.selected_gate = event.key - pygame.K_1
                self.message = f"Gate {self.selected_gate + 1} selected. Press ENTER to verify."
                self.message_color = CYAN
            elif event.key == pygame.K_LEFT:
                self.selected_gate = (self.selected_gate - 1) % 4
                self.message = f"Gate {self.selected_gate + 1} selected."
                self.message_color = CYAN
            elif event.key == pygame.K_RIGHT:
                self.selected_gate = (self.selected_gate + 1) % 4
                self.message = f"Gate {self.selected_gate + 1} selected."
                self.message_color = CYAN
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_choice()

        # Mouse clicks
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Click on a gate body or its select button
            for idx, rect in enumerate(self.gate_rects):
                if rect.collidepoint(event.pos):
                    if self.selected_gate == idx:
                        self._confirm_choice()
                    else:
                        self.selected_gate = idx
                        self.message = f"Gate {idx + 1} selected. Click again or press ENTER to confirm."
                        self.message_color = CYAN
                    return

    def _confirm_choice(self):
        """Process gate confirmation and trigger aggressive mode or restart."""
        if self.selected_gate == self.correct_index:
            # Correct gate chosen!
            self.opened_gate = self.selected_gate
            self.solved_awaiting_confirm = True
            self.aggressive = False
            self.message = "ACCESS GRANTED // NEXUS-9 SHUTDOWN. PRESS ENTER TO COMPLETE ESCAPE."
            self.message_color = GREEN
        else:
            # Wrong choice
            if self.strikes == 0:
                self.strikes = 1
                self.aggressive = True
                self.countdown = 45.0
                self.message = (
                    "ACCESS DENIED! NEXUS-9 AGGRESSIVE LOCKDOWN ENGAGED. 45s BEFORE GATE PURGE."
                )
                self.message_color = RED
            else:
                # Second strike: full reboot
                self.restart("NEXUS-9 REBOOTED THE GATES. SECURITY CODES RESHUFFLED.")
                self.message_color = RED

    # ------------------------------------------------------------------
    # DRAWING & LAYOUT
    # ------------------------------------------------------------------

    def _text(self, screen, text, font, color, x, y, center=False):
        img = font.render(str(text), True, color)
        rect = img.get_rect()
        if center:
            rect.center = (int(x), int(y))
        else:
            rect.topleft = (int(x), int(y))
        screen.blit(img, rect)
        return rect

    def _fit_font(self, text, max_width, start_size, min_size=8):
        max_width = max(1, int(max_width))
        size = max(int(min_size), int(start_size))
        while size > min_size:
            f = pygame.font.SysFont("monospace", size, bold=True)
            if f.size(str(text))[0] <= max_width:
                return f
            size -= 1
        return pygame.font.SysFont("monospace", int(min_size), bold=True)

    def _wrapped_lines(self, text, font, max_width):
        words = str(text).split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for w in words[1:]:
            cand = current + " " + w
            if font.size(cand)[0] <= max_width:
                current = cand
            else:
                lines.append(current)
                current = w
        lines.append(current)
        return lines

    def _draw_panel(self, screen, rect, border=CYAN_DIM, fill=PANEL):
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

    def draw(self, screen):
        """Draw Level 7 within the pixel monitor frame."""
        screen.fill(BG)
        panel = draw_pixel_monitor(screen)
        inner = pygame.Rect(
            panel.x + 16,
            panel.y + 24,
            panel.width - 32,
            panel.height - 48
        )

        w, h = screen.get_size()
        scale = max(0.65, min(1.2, min(w / 1500, h / 1000)))

        if self.phase == "KILL_SWITCH":
            self._draw_circuit_phase(screen, inner, scale)
        else:
            self._draw_gates_phase(screen, inner, scale)

        # Aggressive mode glitch rendering
        if self.aggressive and not self.solved_awaiting_confirm:
            self._apply_glitch_effects(screen, inner)

    def _draw_gates_phase(self, screen, inner, scale):
        """Render the 4 security gates side by side with their plaques."""
        pad = max(6, int(10 * scale))
        gap = max(6, int(10 * scale))

        # 1. Blinking alert
        blink_on = (pygame.time.get_ticks() // 450) % 2 == 0
        if self.aggressive:
            alert_color = RED if (pygame.time.get_ticks() // 200) % 2 == 0 else (180, 20, 35)
            alert_text = f"■ CRITICAL SECURITY BREACH // LOCKDOWN: {self.countdown:04.1f}s // STRIKE 1/2"
        else:
            alert_color = RED if blink_on else (135, 35, 48)
            alert_text = "■ SECURITY BREACH // LEVEL SEVEN"

        alert_font = self._fit_font(alert_text, inner.width - 20, max(12, int(18 * scale)))
        self._text(screen, alert_text, alert_font, alert_color, inner.x + 6, inner.y + 3)

        # 2. Subtitle & Title
        sub_text = "NEXUS-9 // THE FALSE EXIT — ONLY ONE GATE MATCHES ALL LAB LOGS"
        sub_font = self._fit_font(sub_text, inner.width - 20, max(10, int(13 * scale)))
        self._text(
            screen, sub_text, sub_font, CYAN, inner.centerx,
            inner.y + max(24, int(29 * scale)), center=True
        )

        title_font = pygame.font.SysFont("monospace", max(16, int(24 * scale)), bold=True)
        title_y = inner.y + max(42, int(50 * scale))
        self._text(screen, "CORE AIRLOCK GATES", title_font, CYAN, inner.x + 4, title_y)

        # 3. Four Gate Doors Side by Side
        bottom_h = max(44, int(50 * scale))
        gates_top = title_y + max(26, int(32 * scale))
        gates_bottom = inner.bottom - bottom_h - gap
        gate_h = gates_bottom - gates_top

        total_gaps = 3 * gap
        gate_w = (inner.width - total_gaps) // 4

        self.gate_rects = []
        self.gate_buttons = []

        mouse_pos = pygame.mouse.get_pos()

        for i in range(4):
            gx = inner.x + i * (gate_w + gap)
            gate_rect = pygame.Rect(gx, gates_top, gate_w, gate_h)
            self.gate_rects.append(gate_rect)

            is_selected = (self.selected_gate == i)
            is_opened = (self.opened_gate == i)
            is_hovered = gate_rect.collidepoint(mouse_pos)

            # Gate border and body styling
            if is_opened:
                border_color = GREEN
                door_fill = (15, 45, 30)
            elif is_selected:
                border_color = YELLOW
                door_fill = (22, 42, 58)
            elif is_hovered:
                border_color = CYAN
                door_fill = (16, 36, 52)
            else:
                border_color = CYAN_DIM
                door_fill = PANEL_DARK

            # Draw outer gate door frame
            pygame.draw.rect(screen, door_fill, gate_rect, border_radius=6)
            pygame.draw.rect(screen, border_color, gate_rect, 2 if not is_selected else 3, border_radius=6)

            # Rivet studs on corners
            rivet_color = (60, 85, 110)
            for rx in (gate_rect.left + 6, gate_rect.right - 8):
                for ry in (gate_rect.top + 6, gate_rect.bottom - 8):
                    pygame.draw.rect(screen, rivet_color, (rx, ry, 3, 3))

            # Gate Header Bar
            header_h = max(24, int(28 * scale))
            hdr_rect = pygame.Rect(gate_rect.x + 4, gate_rect.y + 4, gate_rect.w - 8, header_h)
            pygame.draw.rect(screen, (8, 20, 32), hdr_rect, border_radius=4)
            pygame.draw.rect(screen, border_color, hdr_rect, 1, border_radius=4)

            # Status LED
            led_color = GREEN if is_opened else (YELLOW if is_selected else (CYAN if is_hovered else CYAN_DIM))
            pygame.draw.circle(screen, led_color, (hdr_rect.x + 12, hdr_rect.centery), 4)

            gate_label = f"GATE 0{i + 1}"
            lbl_font = pygame.font.SysFont("monospace", max(11, int(14 * scale)), bold=True)
            self._text(screen, gate_label, lbl_font, WHITE if (is_selected or is_opened) else GREY, hdr_rect.centerx, hdr_rect.centery, center=True)

            # Plaque Area
            plaque_margin = 8
            button_h = max(24, int(28 * scale))
            plaque_top = hdr_rect.bottom + 6
            plaque_bottom = gate_rect.bottom - button_h - 10
            plaque_h = plaque_bottom - plaque_top

            plaque_rect = pygame.Rect(gate_rect.x + plaque_margin, plaque_top, gate_rect.w - 2 * plaque_margin, plaque_h)
            pygame.draw.rect(screen, (6, 16, 26), plaque_rect, border_radius=4)
            pygame.draw.rect(screen, (25, 60, 80), plaque_rect, 1, border_radius=4)

            # Plaque Content: 6 Clue Fields
            gate_data = self.gates[i]
            row_h = plaque_h / 6.0

            field_font = pygame.font.SysFont("monospace", max(8, int(10 * scale)), bold=True)
            val_base_size = max(10, int(12 * scale))

            for f_idx, key in enumerate(FIELD_KEYS):
                row_y = plaque_top + f_idx * row_h
                val = gate_data[key]
                lbl = FIELD_LABELS[key]

                # Draw tiny field label
                self._text(screen, lbl, field_font, CYAN_DIM, plaque_rect.x + 6, row_y + 3)

                # Draw value dynamically fitted
                val_font = self._fit_font(val, plaque_rect.w - 12, val_base_size, min_size=8)
                val_color = GREEN if is_opened else (WHITE if is_selected else (200, 215, 230))
                self._text(screen, val, val_font, val_color, plaque_rect.x + 6, row_y + row_h * 0.44)

                # Divider line
                if f_idx < 5:
                    pygame.draw.line(screen, (15, 35, 50), (plaque_rect.x + 4, row_y + row_h - 1), (plaque_rect.right - 4, row_y + row_h - 1), 1)

            # Bottom Gate Action Button
            btn_rect = pygame.Rect(gate_rect.x + 8, gate_rect.bottom - button_h - 6, gate_rect.w - 16, button_h)
            self.gate_buttons.append(btn_rect)

            if is_opened:
                btn_fill = (25, 95, 55)
                btn_border = GREEN
                btn_text = "► UNLOCKED ◄"
                btn_txt_col = WHITE
            elif is_selected:
                btn_fill = (65, 50, 15)
                btn_border = YELLOW
                btn_text = "[ ENTER ] UNLOCK"
                btn_txt_col = YELLOW
            elif is_hovered:
                btn_fill = (15, 45, 65)
                btn_border = CYAN
                btn_text = f"SELECT [{i + 1}]"
                btn_txt_col = CYAN
            else:
                btn_fill = (10, 25, 38)
                btn_border = CYAN_DIM
                btn_text = f"GATE {i + 1}"
                btn_txt_col = GREY

            pygame.draw.rect(screen, btn_fill, btn_rect, border_radius=4)
            pygame.draw.rect(screen, btn_border, btn_rect, 1, border_radius=4)
            b_font = self._fit_font(btn_text, btn_rect.w - 6, max(9, int(12 * scale)))
            self._text(screen, btn_text, b_font, btn_txt_col, btn_rect.centerx, btn_rect.centery, center=True)

        # 4. Bottom message and status box
        msg_panel = pygame.Rect(inner.x, inner.bottom - bottom_h, inner.width, bottom_h)
        self._draw_panel(screen, msg_panel, border=CYAN_DIM, fill=PANEL)

        msg_font = self._fit_font(self.message, msg_panel.width - 24, max(11, int(14 * scale)))
        self._text(
            screen, self.message, msg_font, self.message_color,
            msg_panel.centerx, msg_panel.centery, center=True
        )

    def _apply_glitch_effects(self, screen, inner):
        """Pure pygame surface slice displacement and RGB chromatic jitter."""
        w, h = screen.get_size()

        # 1. Horizontal slice shifts
        temp = screen.copy()
        slices = random.randint(3, 6)
        for _ in range(slices):
            sy = random.randint(inner.top, max(inner.top + 1, inner.bottom - 20))
            sh = random.randint(4, 18)
            sx_off = random.randint(-12, 12)
            screen.blit(temp, (sx_off, sy), area=pygame.Rect(0, sy, w, sh))

        # 2. Subtle red tint flicker
        if random.random() < 0.35:
            red_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            red_surf.fill((255, 30, 45, random.randint(15, 40)))
            screen.blit(red_surf, (0, 0))
