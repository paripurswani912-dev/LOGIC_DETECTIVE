# Level 6: Signal Breaker — crack an LFSR stream cipher
#
# Original puzzle rules:
# - Five-cell register shifts right.
# - Right-most cell is the output bit.
# - Feedback is XOR of the selected taps.
# - Hidden seed: [0, 1, 1, 0, 1].
# - Correct taps: cells 3 and 5 (indices 2 and 4).
# - First 12 output bits must match the intercepted header.
# - Remaining keystream decrypts the final transmission: K7.
#
# Controls:
# - Click a register cell to toggle its seed bit.
# - Click a TAP button or press 1-5 to toggle a tap.
# - SPACE: one clock pulse.
# - X: four clock pulses.
# - BACKSPACE: reset the run.
# - H: show a hint.
# - ENTER: return to the lab after solving.

import pygame

from .base_puzzle import BasePuzzle
from screen_borders import draw_pixel_monitor


# ------------------------------------------------------------
# Colours
# ------------------------------------------------------------

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


def lfsr_stream(seed, taps, count):
    """Generate an LFSR output stream using the puzzle's original rules."""
    reg = list(seed)
    output = []

    for _ in range(count):
        output.append(reg[-1])
        feedback = 0
        for tap in taps:
            feedback ^= reg[tap]
        reg = [feedback] + reg[:-1]

    return output


class SignalBreakerPuzzle(BasePuzzle):
    """Crack the hidden LFSR and recover the intercepted transmission."""

    SECRET = "K7"
    SEED = [0, 1, 1, 0, 1]
    TRUE_TAPS = (2, 4)
    HEADER_LEN = 12
    CELLS = 5

    CLUES = [
        "The cipher engine uses a 5-cell register.",
        "The register shifts RIGHT with every clock pulse.",
        "The bit leaving the right end is the output.",
        "The new left bit is the XOR of the tapped cells.",
        "Exactly TWO taps are used. Cell 5 is always one of them.",
        "The seed is unknown. The first five output bits reveal it backwards.",
        "Match all 12 intercepted header bits to crack the generator.",
        "Then keep clocking to decrypt the final transmission.",
        "A wrong header bit locks the run. Press H for a hint.",
    ]

    HINTS = [
        "The first bit out is the right-most register cell.",
        "The first five header bits reveal the seed BACKWARDS.",
        "Cell 5 is always tapped. Try one other cell.",
        "You need exactly two taps. Keep the register and header in sync.",
    ]

    def __init__(self):
        super().__init__()

        secret_bits = []
        for char in self.SECRET:
            secret_bits.extend(int(bit) for bit in format(ord(char), "08b"))

        self.total_len = self.HEADER_LEN + len(secret_bits)
        stream = lfsr_stream(self.SEED, self.TRUE_TAPS, self.total_len)
        self.header = stream[:self.HEADER_LEN]
        self.cipher = [
            plain ^ key
            for plain, key in zip(secret_bits, stream[self.HEADER_LEN:])
        ]

        self.seed = [0] * self.CELLS
        self.taps = set()
        self.hint_index = 0
        self.transmission_complete = False
        self.restart(
            "Detective, set the seed, choose two taps, and pulse the clock."
        )

    # --------------------------------------------------------
    # Text and panel helpers
    # --------------------------------------------------------

    def _text(self, screen, text, font, color, x, y, center=False):
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.center = (int(x), int(y))
        else:
            rect.topleft = (int(x), int(y))
        screen.blit(image, rect)
        return rect

    def _fit_font(self, text, max_width, start_size, min_size=9):
        max_width = max(1, int(max_width))
        size = max(int(min_size), int(start_size))

        while size > min_size:
            font = pygame.font.SysFont("monospace", size, bold=True)
            if font.size(str(text))[0] <= max_width:
                return font
            size -= 1

        return pygame.font.SysFont("monospace", min_size, bold=True)

    def _wrapped_lines(self, text, font, max_width):
        words = str(text).split()
        if not words:
            return [""]

        max_width = max(1, int(max_width))
        lines = []
        current = words[0]

        for word in words[1:]:
            candidate = current + " " + word
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    def _draw_panel(self, screen, rect, border=CYAN_DIM, fill=PANEL):
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

    def _draw_bit_boxes(
        self, screen, bits, x, y, box_size, gap, filled_colour,
        empty_colour=PANEL_DARK, text_colour=DARK_INK
    ):
        font = pygame.font.SysFont("monospace", max(10, int(box_size * 0.55)), bold=True)

        for index, bit in enumerate(bits):
            rect = pygame.Rect(
                int(x + index * (box_size + gap)),
                int(y),
                int(box_size),
                int(box_size),
            )
            if bit is None:
                pygame.draw.rect(screen, empty_colour, rect, border_radius=4)
                pygame.draw.rect(screen, GREY, rect, 1, border_radius=4)
            else:
                pygame.draw.rect(screen, filled_colour, rect, border_radius=4)
                self._text(
                    screen, bit, font, text_colour,
                    rect.centerx, rect.centery, center=True
                )

    # --------------------------------------------------------
    # Puzzle logic
    # --------------------------------------------------------

    def restart(self, message="Register reset. Seed and taps unlocked."):
        self.reg = list(self.seed)
        self.outputs = []
        self.clock_count = 0
        self.broken = False
        self.generator_ok = False
        self.transmission_complete = False
        self.solved = False
        self.message = message

    def toggle_seed(self, index):
        if self.transmission_complete:
            return
        if self.clock_count > 0:
            self.message = "Seed is locked while running. Press BACKSPACE to reset."
            return
        self.seed[index] ^= 1
        self.reg = list(self.seed)
        self.message = "Seed: " + "".join(map(str, self.seed))

    def toggle_tap(self, index):
        if self.transmission_complete:
            return
        if self.clock_count > 0:
            self.message = "Taps are locked while running. Press BACKSPACE to reset."
            return

        if index in self.taps:
            self.taps.remove(index)
        else:
            self.taps.add(index)

        selected = ", ".join(str(tap + 1) for tap in sorted(self.taps)) or "none"
        self.message = f"Selected taps: {selected}"

    def decrypted_bits(self):
        keys = self.outputs[self.HEADER_LEN:]
        return [
            self.cipher[index] ^ key
            for index, key in enumerate(keys)
        ]

    def decoded_text(self):
        bits = self.decrypted_bits()
        chars = []

        for index in range(0, len(bits) - 7, 8):
            byte = bits[index:index + 8]
            value = int("".join(map(str, byte)), 2)
            chars.append(chr(value) if 32 <= value < 127 else "?")

        return "".join(chars)

    def clock_pulse(self):
        if self.transmission_complete or self.solved:
            return

        if self.broken:
            self.message = (
                "Output diverged. Press BACKSPACE to reset and rethink the seed or taps."
            )
            return

        if len(self.taps) != 2:
            self.message = "Select exactly TWO taps before clocking."
            return

        if len(self.outputs) >= self.total_len:
            return

        output_bit = self.reg[-1]
        feedback = 0
        for tap in self.taps:
            feedback ^= self.reg[tap]

        self.reg = [feedback] + self.reg[:-1]
        self.outputs.append(output_bit)
        self.clock_count += 1
        index = len(self.outputs) - 1

        if index < self.HEADER_LEN:
            expected = self.header[index]
            if output_bit != expected:
                self.broken = True
                self.message = (
                    f"HEADER MISMATCH at bit {index + 1}: you produced "
                    f"{output_bit}, expected {expected}. Press BACKSPACE to retry."
                )
            elif index == self.HEADER_LEN - 1:
                self.generator_ok = True
                self.message = "GENERATOR CRACKED! Keep clocking to decrypt the transmission."
            else:
                self.message = f"Header bit {index + 1}/{self.HEADER_LEN} matches."
        else:
            decoded = self.decoded_text()
            self.message = f"Decrypting transmission: {decoded or '...'}"
            if len(self.outputs) == self.total_len:
                self.transmission_complete = True
                self.message = f'FINAL TRANSMISSION RECOVERED: "{self.decoded_text()}"'

    def clock_four(self):
        """Perform up to four clock pulses."""
        for _ in range(4):
            if self.broken or self.transmission_complete:
                break
            self.clock_pulse()

    # --------------------------------------------------------
    # Responsive layout
    # --------------------------------------------------------

    def _layout(self, screen):
        width, height = screen.get_size()

        # Geometry of the shared screen_borders.py monitor panel.
        monitor = pygame.Rect(18, 14, width - 36, height - 28)
        panel = pygame.Rect(
            monitor.x + 27, monitor.y + 27,
            monitor.width - 54, monitor.height - 54
        )
        inner = pygame.Rect(
            panel.x + 16, panel.y + 24,
            panel.width - 32, panel.height - 48
        )

        scale = min(width / 1500, height / 1000)
        scale = max(0.65, min(1.2, scale))
        gap = max(8, int(14 * scale))
        pad = max(10, int(16 * scale))

        alert_y = inner.y + 4
        subtitle_y = alert_y + max(27, int(34 * scale))
        title_y = subtitle_y + max(32, int(38 * scale))
        top_y = title_y + max(36, int(42 * scale))

        left_width = int((inner.width - gap) * 0.56)
        right_width = inner.width - gap - left_width
        top_height = max(150, min(int(inner.height * 0.34), 205))

        report = pygame.Rect(inner.x, top_y, left_width, top_height)
        header = pygame.Rect(report.right + gap, top_y, right_width, top_height)

        register_y = report.bottom + gap
        register_height = max(118, min(int(inner.height * 0.23), 178))
        register = pygame.Rect(inner.x, register_y, inner.width, register_height)

        controls_y = register.bottom + gap
        controls_height = max(40, min(int(58 * scale), 62))
        controls = pygame.Rect(inner.x, controls_y, inner.width, controls_height)

        message_y = controls.bottom + gap
        message_height = max(48, inner.bottom - message_y)
        message = pygame.Rect(inner.x, message_y, inner.width, message_height)

        return {
            "screen": pygame.Rect(0, 0, width, height),
            "monitor": monitor,
            "panel": panel,
            "inner": inner,
            "report": report,
            "header": header,
            "register": register,
            "controls": controls,
            "message": message,
            "alert_y": alert_y,
            "subtitle_y": subtitle_y,
            "title_y": title_y,
            "gap": gap,
            "pad": pad,
            "scale": scale,
        }

    def _register_geometry(self, screen):
        layout = self._layout(screen)
        rect = layout["register"]
        scale = layout["scale"]
        pad = layout["pad"]

        # Slightly wider reserved areas make IN > and > OUT legible.
        left_reserved = max(int(rect.width * 0.29), int(130 * scale))
        right_reserved = max(68, int(82 * scale))
        usable_x = rect.x + left_reserved
        usable_width = max(1, rect.right - right_reserved - usable_x)
        cell_gap = max(5, int(10 * scale))

        cell_width = min(
            int(88 * scale),
            int((usable_width - 4 * cell_gap) / 5),
        )
        cell_width = max(32, cell_width)
        total_width = 5 * cell_width + 4 * cell_gap
        start_x = usable_x + max(0, (usable_width - total_width) // 2)

        cell_height = max(42, int(56 * scale))
        cell_y = rect.y + max(34, int(39 * scale))
        tap_height = max(26, int(32 * scale))
        tap_y = cell_y + cell_height + max(5, int(7 * scale))

        cells = []
        taps = []
        for index in range(self.CELLS):
            x = start_x + index * (cell_width + cell_gap)
            cells.append(pygame.Rect(x, cell_y, cell_width, cell_height))
            taps.append(pygame.Rect(x, tap_y, cell_width, tap_height))

        return cells, taps

    def cell_rect(self, index, screen=None):
        if screen is None:
            screen = pygame.display.get_surface()
        if screen is None:
            return pygame.Rect(280 + index * 90, 330, 70, 50)
        return self._register_geometry(screen)[0][index]

    def tap_rect(self, index, screen=None):
        if screen is None:
            screen = pygame.display.get_surface()
        if screen is None:
            return pygame.Rect(280 + index * 90, 398, 70, 28)
        return self._register_geometry(screen)[1][index]

    def button_rect(self, index, screen=None):
        if screen is None:
            screen = pygame.display.get_surface()
        if screen is None:
            return pygame.Rect(60 + index * 220, 445, 200, 45)

        layout = self._layout(screen)
        controls = layout["controls"]
        gap = max(8, int(12 * layout["scale"]))
        button_width = (controls.width - 2 * gap) // 3
        return pygame.Rect(
            controls.x + index * (button_width + gap),
            controls.y,
            button_width,
            controls.height,
        )

    # --------------------------------------------------------
    # Input handling
    # --------------------------------------------------------

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.transmission_complete:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.solved = True
                return

            if event.key == pygame.K_SPACE:
                self.clock_pulse()
            elif event.key == pygame.K_x:
                self.clock_four()
            elif event.key == pygame.K_BACKSPACE:
                self.restart("Register reset. Seed and taps unlocked.")
            elif event.key == pygame.K_h:
                self.message = self.HINTS[self.hint_index % len(self.HINTS)]
                self.hint_index += 1
            elif pygame.K_1 <= event.key <= pygame.K_5:
                self.toggle_tap(event.key - pygame.K_1)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.transmission_complete or self.clock_count > 0:
                return

            if not hasattr(event, "pos"):
                return
            screen = pygame.display.get_surface()
            if screen is None:
                return

            cells, tap_buttons = self._register_geometry(screen)
            for index, rect in enumerate(cells):
                if rect.collidepoint(event.pos):
                    self.toggle_seed(index)
                    return

            for index, rect in enumerate(tap_buttons):
                if rect.collidepoint(event.pos):
                    self.toggle_tap(index)
                    return

            for index in range(3):
                if self.button_rect(index, screen).collidepoint(event.pos):
                    if index == 0:
                        self.clock_pulse()
                    elif index == 1:
                        self.clock_four()
                    else:
                        self.restart("Register reset. Seed and taps unlocked.")
                    return

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    def draw(self, screen):
        screen.fill(BG)
        monitor_panel = draw_pixel_monitor(screen)
        layout = self._layout(screen)

        # Use the actual shared border's returned panel and inset content.
        inner = pygame.Rect(
            monitor_panel.x + 16,
            monitor_panel.y + 24,
            monitor_panel.width - 32,
            monitor_panel.height - 48,
        )
        layout["inner"] = inner

        scale = layout["scale"]
        gap = layout["gap"]
        pad = layout["pad"]

        alert_font = pygame.font.SysFont("monospace", max(12, int(19 * scale)), bold=True)
        title_font = pygame.font.SysFont("monospace", max(19, int(30 * scale)), bold=True)
        heading_font = pygame.font.SysFont("monospace", max(14, int(20 * scale)), bold=True)
        body_font = pygame.font.SysFont("monospace", max(11, int(14 * scale)), bold=True)
        small_font = pygame.font.SysFont("monospace", max(10, int(12 * scale)), bold=True)

        # Blinking alert: 450 ms interval, matching the earlier levels.
        blink_on = (pygame.time.get_ticks() // 450) % 2 == 0
        alert_colour = RED if blink_on else (135, 35, 48)
        alert_text = "■ SECURITY BREACH // LEVEL SIX"
        alert_font = self._fit_font(alert_text, inner.width - 20, max(12, int(19 * scale)))
        self._text(screen, alert_text, alert_font, alert_colour, inner.x + 6, inner.y + 5)

        subtitle = "EVERY BIT MATTERS, DETECTIVE. CRACK THE SIGNAL AND ESCAPE THE LABORATORY."
        subtitle_font = self._fit_font(subtitle, inner.width - 20, max(11, int(14 * scale)))
        self._text(
            screen, subtitle, subtitle_font, CYAN, inner.centerx,
            inner.y + max(36, int(43 * scale)), center=True
        )
        self._text(
            screen, "SIGNAL BREAKER", title_font, CYAN,
            inner.x + 4, inner.y + max(60, int(72 * scale))
        )

        # Upper row: intercept report and intercepted header.
        top_y = inner.y + max(96, int(112 * scale))
        top_height = max(150, min(int(inner.height * 0.34), 205))
        left_width = int((inner.width - gap) * 0.56)
        right_width = inner.width - gap - left_width
        report = pygame.Rect(inner.x, top_y, left_width, top_height)
        header = pygame.Rect(report.right + gap, top_y, right_width, top_height)
        self._draw_panel(screen, report)
        self._draw_panel(screen, header)

        self._text(screen, "INTERCEPT REPORT", heading_font, CYAN, report.x + pad, report.y + 10)
        clue_font = self._fit_font(
            "The seed is unknown. The first five output bits reveal it backwards.",
            report.width - 2 * pad, max(10, int(12 * scale))
        )
        clue_y = report.y + max(35, int(41 * scale))
        clue_line_height = clue_font.get_linesize() + 2
        clue_width = report.width - 2 * pad

        for clue in self.CLUES:
            wrapped = self._wrapped_lines("- " + clue, clue_font, clue_width)
            for line in wrapped:
                if clue_y + clue_line_height > report.bottom - 8:
                    break
                self._text(screen, line, clue_font, WHITE, report.x + pad, clue_y)
                clue_y += clue_line_height
            if clue_y + clue_line_height > report.bottom - 8:
                break

        header_title = "INTERCEPTED HEADER (12 BITS)"
        self._text(
            screen, header_title,
            self._fit_font(header_title, header.width - 2 * pad, max(12, int(19 * scale))),
            CYAN, header.x + pad, header.y + 10
        )

        bit_gap = max(2, int(4 * scale))
        available_bit_width = header.width - 2 * pad
        bit_size = min(
            int(28 * scale),
            int((available_bit_width - 11 * bit_gap) / self.HEADER_LEN)
        )
        bit_size = max(12, bit_size)
        total_bits_width = self.HEADER_LEN * bit_size + (self.HEADER_LEN - 1) * bit_gap
        bits_x = header.centerx - total_bits_width // 2
        header_bits_y = header.y + max(40, int(48 * scale))
        self._draw_bit_boxes(
            screen, self.header, bits_x, header_bits_y, bit_size, bit_gap,
            CYAN, text_colour=DARK_INK
        )

        self._text(
            screen, "YOUR OUTPUT", small_font, GREY,
            header.x + pad, header.y + max(75, int(86 * scale))
        )
        shown_outputs = [
            self.outputs[index] if index < len(self.outputs) else None
            for index in range(self.HEADER_LEN)
        ]
        output_y = header.y + max(97, int(110 * scale))

        for index, bit in enumerate(shown_outputs):
            x = bits_x + index * (bit_size + bit_gap)
            rect = pygame.Rect(x, output_y, bit_size, bit_size)
            if bit is None:
                pygame.draw.rect(screen, PANEL_DARK, rect, border_radius=4)
                pygame.draw.rect(screen, GREY, rect, 1, border_radius=4)
            else:
                fill = GREEN if bit == self.header[index] else RED
                pygame.draw.rect(screen, fill, rect, border_radius=4)
                self._text(
                    screen, bit, small_font, DARK_INK,
                    rect.centerx, rect.centery, center=True
                )

        status_y = header.y + max(130, int(148 * scale))
        self._text(
            screen, f"CLOCK PULSES: {self.clock_count}",
            body_font, WHITE, header.x + pad, status_y
        )

        stage_text = (
            "STAGE 2 // DECRYPT THE TRANSMISSION"
            if self.generator_ok else "STAGE 1 // BREAK THE GENERATOR"
        )
        stage_font = self._fit_font(stage_text, header.width - 2 * pad, max(10, int(12 * scale)))
        self._text(
            screen, stage_text, stage_font, YELLOW,
            header.x + pad, header.bottom - stage_font.get_linesize() - 9
        )

        # Register panel.
        register_y = report.bottom + gap
        register_height = max(118, min(int(inner.height * 0.23), 178))
        register = pygame.Rect(inner.x, register_y, inner.width, register_height)
        self._draw_panel(screen, register)
        self._text(
            screen, "5-CELL REGISTER", heading_font, CYAN,
            register.x + pad, register.y + 9
        )

        instructions = "Click a cell to toggle its seed bit."
        instruction_width = int(register.width * 0.22)
        instruction_font = self._fit_font(
            instructions, instruction_width, max(10, int(13 * scale))
        )
        instruction_lines = self._wrapped_lines(instructions, instruction_font, instruction_width)
        instruction_y = register.y + max(34, int(42 * scale))
        for line in instruction_lines[:3]:
            self._text(
                screen, line, instruction_font, GREY,
                register.x + pad, instruction_y
            )
            instruction_y += instruction_font.get_linesize() + 2

        self._text(
            screen, "Select exactly TWO taps.", small_font, YELLOW,
            register.x + pad,
            min(register.bottom - small_font.get_linesize() - 8, instruction_y + 4)
        )

        cells, tap_buttons = self._register_geometry(screen)
        cell_y = cells[0].y
        cell_height = cells[0].height

        in_label = "IN >"
        in_font = self._fit_font(in_label, max(30, cells[0].x - register.x - pad - 8), max(10, int(12 * scale)))
        self._text(
            screen, in_label, in_font, WHITE,
            max(register.x + pad, cells[0].x - in_font.size(in_label)[0] - 8),
            cell_y + cell_height // 2, center=False
        )

        out_label = "> OUT"
        out_font = self._fit_font(out_label, max(35, register.right - tap_buttons[-1].right - 8), max(10, int(12 * scale)))
        self._text(
            screen, out_label, out_font, WHITE,
            min(register.right - out_font.size(out_label)[0] - 8, tap_buttons[-1].right + 8),
            cell_y + cell_height // 2
        )

        for index, bit in enumerate(self.reg):
            cell = cells[index]
            fill = GREEN if bit else PANEL_DARK
            ink = DARK_INK if bit else WHITE
            pygame.draw.rect(screen, fill, cell, border_radius=6)
            pygame.draw.rect(screen, WHITE, cell, 2, border_radius=6)

            bit_font = pygame.font.SysFont(
                "monospace", max(15, int(cell_height * 0.43)), bold=True
            )
            self._text(
                screen, bit, bit_font, ink,
                cell.centerx, cell.centery, center=True
            )

            tap_rect = tap_buttons[index]
            tap_on = index in self.taps
            pygame.draw.rect(
                screen, YELLOW if tap_on else PANEL_DARK,
                tap_rect, border_radius=4
            )
            pygame.draw.rect(
                screen, YELLOW if tap_on else GREY,
                tap_rect, 1, border_radius=4
            )
            tap_label = f"TAP {index + 1}"
            tap_font = self._fit_font(
                tap_label, tap_rect.width - 4, max(9, int(11 * scale))
            )
            self._text(
                screen, tap_label, tap_font,
                DARK_INK if tap_on else WHITE,
                tap_rect.centerx, tap_rect.centery, center=True
            )

        # Three control buttons.
        controls = pygame.Rect(
            inner.x, register.bottom + gap, inner.width,
            max(40, min(int(58 * scale), 62))
        )
        control_gap = max(8, int(12 * scale))
        control_width = (controls.width - 2 * control_gap) // 3
        control_data = [
            ("CLOCK [SPACE]", CYAN),
            ("CLOCK x4 [X]", GREEN),
            ("RESET [BACKSPACE]", RED),
        ]

        for index, (label, colour) in enumerate(control_data):
            rect = pygame.Rect(
                controls.x + index * (control_width + control_gap),
                controls.y, control_width, controls.height
            )
            pygame.draw.rect(screen, colour, rect, border_radius=8)
            pygame.draw.rect(screen, WHITE, rect, 1, border_radius=8)
            label_font = self._fit_font(label, rect.width - 16, max(11, int(15 * scale)))
            self._text(
                screen, label, label_font, DARK_INK,
                rect.centerx, rect.centery, center=True
            )

        # Bottom panel: keep status/detail rows separate from the message box.
        message_y = controls.bottom + gap
        message_bottom = inner.bottom - 2
        message_height = max(48, message_bottom - message_y)
        message_panel = pygame.Rect(inner.x, message_y, inner.width, message_height)
        self._draw_panel(screen, message_panel)

        left_section_width = int(message_panel.width * 0.30)
        divider_x = message_panel.x + left_section_width
        self._text(
            screen, "DECRYPTION MODULE", small_font, CYAN,
            message_panel.x + 12, message_panel.y + 8
        )

        module_status = "ONLINE // STREAM ACTIVE" if self.generator_ok else "OFFLINE"
        module_colour = GREEN if self.generator_ok else GREY
        status_y = message_panel.y + 28
        status_font = self._fit_font(
            module_status, left_section_width - 24, max(10, int(12 * scale))
        )
        self._text(
            screen, module_status, status_font, module_colour,
            message_panel.x + 12, status_y
        )

        # Only show the decoded detail if there is enough vertical room.
        detail_line = (
            f"Decoded: {self.decoded_text() or '...'}"
            if self.generator_ok else "Crack the generator first."
        )
        detail_font = self._fit_font(
            detail_line, left_section_width - 24, max(9, int(11 * scale))
        )
        detail_y = message_panel.y + 47
        if detail_y + detail_font.get_linesize() > message_panel.bottom - 4:
            detail_y = message_panel.bottom - detail_font.get_linesize() - 4
        if detail_y > status_y + status_font.get_linesize() - 1:
            self._text(
                screen, detail_line, detail_font,
                GREEN if self.generator_ok else WHITE,
                message_panel.x + 12, detail_y
            )

        pygame.draw.line(
            screen, CYAN_DIM,
            (divider_x, message_panel.y + 8),
            (divider_x, message_panel.bottom - 8), 2
        )

        current_x = divider_x + 14
        current_width = message_panel.right - current_x - 12
        self._text(
            screen, "CURRENT MESSAGE", small_font, CYAN,
            current_x, message_panel.y + 7
        )

        message_box = pygame.Rect(
            current_x, message_panel.y + 26,
            current_width, max(18, message_panel.height - 34)
        )
        pygame.draw.rect(screen, PANEL_DARK, message_box, border_radius=5)
        pygame.draw.rect(screen, CYAN_DIM, message_box, 1, border_radius=5)

        if self.transmission_complete:
            # Keep the recovered transmission and Enter prompt on ONE line so
            # they sit side by side instead of colliding in short message boxes.
            final_text = f'RECOVERED: "{self.decoded_text()}"   |   PRESS ENTER TO RETURN TO THE LAB'
            final_font = self._fit_font(
                final_text, message_box.width - 16, max(8, int(11 * scale))
            )
            final_y = message_box.y + max(
                2, (message_box.height - final_font.get_linesize()) // 2
            )
            self._text(
                screen, final_text, final_font, GREEN,
                message_box.x + 8, final_y
            )

        else:
            message_font = self._fit_font(
                self.message, message_box.width - 16, max(10, int(13 * scale))
            )
            lines = self._wrapped_lines(self.message, message_font, message_box.width - 16)
            line_height = message_font.get_linesize() + 2
            total_text_height = len(lines) * line_height
            max_lines = max(1, (message_box.height - 6) // max(1, line_height))
            if len(lines) > max_lines:
                lines = lines[:max_lines]
            line_y = message_box.y + max(3, (message_box.height - min(total_text_height, message_box.height - 4)) // 2)
            for line in lines:
                if line_y + line_height > message_box.bottom - 2:
                    break
                self._text(
                    screen, line, message_font, YELLOW,
                    message_box.x + 8, line_y
                )
                line_y += line_height
