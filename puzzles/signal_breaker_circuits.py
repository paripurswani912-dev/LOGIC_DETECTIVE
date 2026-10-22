# puzzles/signal_breaker_circuits.py
# Level 6 add-on: the mandatory BUILD phase.
#
# ANALYZE (existing puzzle) -> BUILD (this file) -> solved.
#
# The player wires the LFSR as a real sequential circuit:
#   5 D flip-flops in a chain  (Q1->D2, Q2->D3, Q3->D4, Q4->D5)
#   XOR of Q3 and Q5 -> D1     (the feedback taps)
#   Q5 is the key-stream output bit
#   Q5 XOR CIPHER -> PLAINTEXT (decrypts "K7" on its own)
#
# Used as a mixin by SignalBreakerPuzzle, so it relies on these
# existing attributes/methods of that class:
#   header, cipher, seed, SECRET, HEADER_LEN, total_len, solved,
#   _text, _fit_font, _wrapped_lines, _draw_panel

import pygame

from puzzles.circuit_engine import (
    Circuit, Component, Workbench, GREEN, YELLOW, WHITE, GREY,
    CYAN, CYAN_DIM, RED,
)
from screen_borders import draw_pixel_monitor

BG = (4, 10, 22)
DARK_INK = (4, 20, 30)
FF_IDS = ["F1", "F2", "F3", "F4", "F5"]

BUILD_HINTS = [
    "Chain: Q of each flip-flop goes to the D of the next one (FF1>FF2>FF3>FF4>FF5).",
    "Feedback: wire Q of FF3 and Q of FF5 into the feedback XOR, then the XOR into D of FF1.",
    "Click a flip-flop to set its seed bit before the first clock pulse.",
    "Decrypt: wire Q of FF5 and the CIPHER bit into the DECRYPT XOR, then into PLAINTEXT.",
]


class SignalBreakerCircuitMixin:

    # ---------------------------------------------------------
    # SETUP / RESET
    # ---------------------------------------------------------

    def _make_lfsr_circuit(self):
        c = Circuit()

        # Smaller parts and labels, and wires that route themselves
        # around parts, captions and each other.
        c.size_scale = 0.8
        c.font_scale = 0.85
        c.auto_route = True

        # Start layout: flip-flops across the top, the two XOR stages
        # and the cipher along the bottom. Every part can be dragged
        # to rearrange it.
        top_y, bot_y = 0.22, 0.68

        c.add(Component("X", "XOR", 0.16, bot_y, "", "FEEDBACK"))

        for i, x in enumerate([0.22, 0.34, 0.46, 0.58, 0.70]):
            c.add(Component(
                FF_IDS[i], "DFF", x, top_y, f"FF{i + 1}", f"CELL {i + 1}"
            ))

        c.add(Component("KEY", "LED", 0.90, top_y, "KEY BIT"))
        c.add(Component("C", "SOURCE", 0.44, bot_y, "CIPHER", "CIPHERTEXT"))
        c.add(Component("X2", "XOR", 0.66, bot_y, "", "DECRYPT"))
        c.add(Component("P", "LED", 0.90, bot_y, "PLAINTEXT"))

        c.connect("F5", "KEY", 0)  # pre-wired: shows the output bit
        c.reset()
        return c
    
    def _init_circuits(self):
        self.phase = "ANALYZE"  # ANALYZE -> BUILD
        self.build_verified = False
        self.build_hint_index = 0
        self.plain_bits = []
        self.build_buttons = []
        self.build_status = "info"
        self.build_message = ""
        self.build = Workbench(
            self._make_lfsr_circuit(),
            allow_wiring=True, allow_placing=False, allow_preset=True,
            allow_moving=True,
        )

    def start_build_phase(self):
        """Called when the player presses ENTER on the solved puzzle."""
        self.phase = "BUILD"
        self.build_verified = False
        self.plain_bits = []

        c = self.build.circuit
        for i, fid in enumerate(FF_IDS):  # carry the cracked seed over
            c.comps[fid].init = self.seed[i]
        c.reset()
        self._sync_cipher()
        self._say(
            "GENERATOR CRACKED ON PAPER. NOW BUILD THE MACHINE: wire the "
            "flip-flops, the feedback XOR and the decrypt XOR. Press H for hints.",
            "info",
        )

    def _say(self, message, status="info"):
        self.build_message = message
        self.build_status = status

    # ---------------------------------------------------------
    # CIPHER SOURCE / DECODING
    # ---------------------------------------------------------

    def _set_cipher(self, tick):
        """The CIPHER input shows the ciphertext bit for this tick."""
        idx = tick - self.HEADER_LEN
        bit = self.cipher[idx] if 0 <= idx < len(self.cipher) else 0
        self.build.circuit.comps["C"].value = bit

    def _sync_cipher(self):
        self._set_cipher(self.build.circuit.ticks)

    def _decode(self, bits):
        chars = []
        for i in range(0, len(bits) - 7, 8):
            byte = bits[i:i + 8]
            if None in byte:
                chars.append("?")
                continue
            value = int("".join(map(str, byte)), 2)
            chars.append(chr(value) if 32 <= value < 127 else "?")
        return "".join(chars)

    # ---------------------------------------------------------
    # CLOCKING
    # ---------------------------------------------------------

    def _clock_once(self):
        c = self.build.circuit
        if c.ticks >= self.total_len:
            self._say("Transmission complete. Press RESET to run it again.")
            return False

        self._sync_cipher()
        t = c.ticks
        out = c.comps["F5"].state
        plain = c.value("P") if t >= self.HEADER_LEN else None

        if not c.clock():
            self._say(
                "CIRCUIT INCOMPLETE: every flip-flop needs a wire into its "
                "D input.", "error",
            )
            return False

        if t >= self.HEADER_LEN:
            self.plain_bits.append(plain)
        self._sync_cipher()

        if t < self.HEADER_LEN:
            if out == self.header[t]:
                if t == self.HEADER_LEN - 1:
                    self._say(
                        "KEY-STREAM MATCHES THE INTERCEPTED HEADER! Press "
                        "ENTER to verify, or keep clocking.", "ok",
                    )
                else:
                    self._say(f"Header bit {t + 1}/{self.HEADER_LEN} matches.")
            else:
                self._say(
                    f"HEADER MISMATCH at bit {t + 1}: circuit gave {out}, "
                    f"expected {self.header[t]}. Press RESET and recheck.",
                    "error",
                )
        else:
            if plain is None:
                self._say(
                    "Key-stream OK, but the DECRYPT path isn't wired yet.",
                    "info",
                )
            else:
                self._say(
                    f"Decrypting: {self._decode(self.plain_bits) or '...'}"
                )
        return True

    def _clock_four(self):
        for _ in range(4):
            if not self._clock_once():
                break

    def _reset_run(self):
        c = self.build.circuit
        c.reset()
        self.plain_bits = []
        self._sync_cipher()
        self._say("Register reset to the seed. Click a flip-flop to change it.")

    # ---------------------------------------------------------
    # VERIFY THE BUILT CIRCUIT (simulates a fresh run from the seed)
    # ---------------------------------------------------------

    def verify_build(self):
        c = self.build.circuit

        missing = [
            str(i + 1) for i, fid in enumerate(FF_IDS)
            if c.source_of(fid, 0) is None
        ]
        if missing:
            self._say(
                "CIRCUIT INCOMPLETE: no wire into D of FF" + ", FF".join(missing)
                + ".", "error",
            )
            return

        saved = c.save_run()
        c.reset()
        kind, message = self._run_checks()
        c.restore_run(saved)
        self._sync_cipher()
        self._say(message, kind)

    def _run_checks(self):
        c = self.build.circuit

        for t in range(self.HEADER_LEN):
            out = c.comps["F5"].state
            if out != self.header[t]:
                hint = (
                    "Check the seed bits."
                    if t < 5 else "Check which cells feed the feedback XOR."
                )
                return "error", (
                    f"HEADER MISMATCH at bit {t + 1}: circuit gave {out}, "
                    f"expected {self.header[t]}. {hint}"
                )
            c.clock()

        bits = []
        for t in range(self.HEADER_LEN, self.total_len):
            self._set_cipher(t)
            plain = c.value("P")
            if plain is None:
                return "info", (
                    "GENERATOR VERIFIED! Now decrypt: wire Q of FF5 and the "
                    "CIPHER bit into the DECRYPT XOR, then into PLAINTEXT."
                )
            bits.append(plain)
            c.clock()

        text = self._decode(bits)
        if text != self.SECRET:
            return "error", (
                f'DECRYPTION WRONG: the circuit produced "{text}". '
                "Plaintext = key-stream XOR ciphertext."
            )

        self.build_verified = True
        return "ok", (
            f'MACHINE VERIFIED! THE CIRCUIT DECRYPTED THE TRANSMISSION: "{text}"'
        )

    # ---------------------------------------------------------
    # EVENTS  (returns True when the event was consumed)
    # ---------------------------------------------------------

    def circuit_handle_event(self, event):
        if self.phase != "BUILD":
            return False
        if self.solved:
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.build_verified:
                    self.solved = True
                else:
                    self.verify_build()
            elif event.key == pygame.K_SPACE:
                self._clock_once()
            elif event.key == pygame.K_x:
                self._clock_four()
            elif event.key == pygame.K_BACKSPACE:
                self._reset_run()
            elif event.key == pygame.K_h:
                hint = BUILD_HINTS[self.build_hint_index % len(BUILD_HINTS)]
                self.build_hint_index += 1
                self._say(hint)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.build_buttons):
                if rect.collidepoint(event.pos):
                    if index == 0:
                        self._clock_once()
                    elif index == 1:
                        self._clock_four()
                    elif index == 2:
                        self._reset_run()
                    elif self.build_verified:
                        self.solved = True
                    else:
                        self.verify_build()
                    return True

        msg = self.build.handle_event(event)
        if msg:
            self._say(msg)
        return True

    # ---------------------------------------------------------
    # DRAWING
    # ---------------------------------------------------------

    def _draw_build(self, screen):
        screen.fill(BG)
        panel = draw_pixel_monitor(screen)

        # Inner area, kept well inside the purple monitor border.
        inner = pygame.Rect(
            panel.x + 24, panel.y + 20, panel.width - 48, panel.height - 52
        )
        x, w, gap = inner.x, inner.width, 6
        y = inner.y

        # header lines
        blink_on = (pygame.time.get_ticks() // 450) % 2 == 0
        alert = "■ SECURITY BREACH // LEVEL SIX"
        alert_font = self._fit_font(alert, w - 20, 16)
        self._text(
            screen, alert, alert_font,
            RED if blink_on else (135, 35, 48), x + 6, y,
        )
        y += alert_font.get_linesize() + 2

        title = "BUILD THE SIGNAL MACHINE"
        title_font = self._fit_font(title, w - 20, 24)
        self._text(screen, title, title_font, CYAN, x + 4, y)
        y += title_font.get_linesize() + 2

        body_font = pygame.font.SysFont("monospace", 12, bold=True)
        instructions = (
            "Drag from an OUTPUT pin (right) to an INPUT pin (left). Chain the "
            "5 flip-flops, XOR cells 3 and 5 back into D1, and click a flip-flop "
            "to set its seed. Then wire Q5 and the CIPHER bit into the DECRYPT "
            "XOR to read the PLAINTEXT. Right-click an input pin to remove a wire."
        )
        lines = self._wrapped_lines(instructions, body_font, w - 12)[:3]
        for line in lines:
            self._text(screen, line, body_font, WHITE, x + 6, y)
            y += body_font.get_linesize()
        y += 4

        # ---- layout budget ----
        # Fixed parts shrink first on short windows so the workbench
        # always keeps enough height for the captions under its rows.
        rows = 7
        row_h, btn_h, msg_h = 14, 36, 44

        def bench_space():
            timing = 26 + rows * row_h + 6
            return inner.bottom - y - (timing + btn_h + msg_h + 3 * gap)

        if bench_space() < 240:
            row_h, btn_h, msg_h = 12, 32, 38
        bench_h = max(150, bench_space())
        timing_h = 26 + rows * row_h + 6

        # workbench
        self.build.area = pygame.Rect(x, y, w, bench_h)
        self.build.draw(screen)
        y = self.build.area.bottom + gap

        # timing diagram
        timing = pygame.Rect(x, y, w, timing_h)
        self._draw_timing(screen, timing, row_h)
        y = timing.bottom + gap

        # buttons
        labels = [
            ("CLOCK [SPACE]", CYAN),
            ("CLOCK x4 [X]", GREEN),
            ("RESET [BACKSPACE]", RED),
            (
                "CONTINUE [ENTER]" if self.build_verified
                else "VERIFY [ENTER]",
                YELLOW,
            ),
        ]
        btn_w = (w - 3 * gap) // 4
        self.build_buttons = []
        for i, (label, colour) in enumerate(labels):
            rect = pygame.Rect(x + i * (btn_w + gap), y, btn_w, btn_h)
            self.build_buttons.append(rect)
            pygame.draw.rect(screen, colour, rect, border_radius=8)
            pygame.draw.rect(screen, WHITE, rect, 1, border_radius=8)
            font = self._fit_font(label, rect.width - 14, 15)
            self._text(
                screen, label, font, DARK_INK,
                rect.centerx, rect.centery, center=True,
            )
        y += btn_h + gap

        # message box: ends exactly at the bottom of the inner area,
        # so it can never spill over the monitor border.
        msg_rect = pygame.Rect(x, y, w, max(30, inner.bottom - y))
        self._draw_panel(screen, msg_rect)
        colour = {"error": RED, "ok": GREEN}.get(self.build_status, YELLOW)
        msg_font = pygame.font.SysFont("monospace", 12, bold=True)
        msg_lines = self._wrapped_lines(
            self.build_message, msg_font, msg_rect.width - 20
        )
        if self.build_verified:
            msg_lines = msg_lines[:1]
        line_y = msg_rect.y + 6
        for line in msg_lines[:2]:
            self._text(screen, line, msg_font, colour, msg_rect.x + 10, line_y)
            line_y += msg_font.get_linesize()
        if self.build_verified and blink_on:
            self._text(
                screen, "PRESS ENTER TO RETURN TO THE LAB", msg_font, YELLOW,
                msg_rect.x + 10, line_y,
            )

    # ---- timing diagram ----

    def _wave(self, screen, vals, x0, top, colw, row_h, colour_fn):
        hi, lo = top + 3, top + row_h - 3
        prev = None
        for i, v in enumerate(vals):
            level = hi if v else lo
            xa = x0 + int(i * colw)
            xb = x0 + int((i + 1) * colw)
            colour = colour_fn(i, v)
            pygame.draw.line(screen, colour, (xa, level), (xb, level), 2)
            if prev is not None and prev != v:
                pygame.draw.line(screen, colour, (xa, hi), (xa, lo), 2)
            prev = v

    def _draw_timing(self, screen, rect, row_h):
        self._draw_panel(screen, rect)
        c = self.build.circuit
        small = pygame.font.SysFont("monospace", 12, bold=True)
        digit = pygame.font.SysFont("monospace", 11, bold=True)

        pad, label_w = 10, 62
        self._text(
            screen, "TIMING DIAGRAM", small, CYAN, rect.x + pad, rect.y + 6
        )
        decoded = self._decode(self.plain_bits)
        info = f"DECODED: {decoded or '...'}   |   CLOCK PULSES: {c.ticks}"
        info_font = self._fit_font(info, rect.width // 2, 12)
        self._text(
            screen, info, info_font, GREEN if decoded else GREY,
            rect.right - pad - info_font.size(info)[0], rect.y + 6,
        )

        x0 = rect.x + pad + label_w
        colw = (rect.width - 2 * pad - label_w) / self.total_len
        ty = rect.y + 24
        rows = 7

        # header columns are shaded; the rest is the encrypted message
        pygame.draw.rect(
            screen, (10, 30, 44),
            (x0, ty, int(colw * self.HEADER_LEN), rows * row_h),
        )
        if c.ticks < self.total_len:
            pygame.draw.rect(
                screen, YELLOW,
                (x0 + int(c.ticks * colw), ty, max(2, int(colw)), rows * row_h),
                1,
            )

        names = ["CLK", "Q1", "Q2", "Q3", "Q4", "Q5", "HDR|PT"]
        for r, name in enumerate(names):
            top = ty + r * row_h
            label_colour = YELLOW if r == 5 else GREY
            self._text(
                screen, name, small, label_colour, rect.x + pad,
                top + (row_h - small.get_linesize()) // 2,
            )

            if r == 0:
                hi, lo = top + 3, top + row_h - 3
                for i in range(min(c.ticks, self.total_len)):
                    xa = x0 + int(i * colw)
                    xm = x0 + int((i + 0.5) * colw)
                    xb = x0 + int((i + 1) * colw)
                    pygame.draw.lines(
                        screen, CYAN_DIM, False,
                        [(xa, lo), (xa, hi), (xm, hi), (xm, lo), (xb, lo)], 2,
                    )
            elif 1 <= r <= 5:
                hist = c.history.get(FF_IDS[r - 1], [])
                hist = hist[:self.total_len]

                def colour_fn(i, v, r=r):
                    if r == 5 and i < self.HEADER_LEN:
                        return GREEN if v == self.header[i] else RED
                    return CYAN

                self._wave(screen, hist, x0, top, colw, row_h, colour_fn)
            elif colw >= 11:
                for i in range(self.total_len):
                    cx = x0 + int((i + 0.5) * colw)
                    if i < self.HEADER_LEN:
                        txt, col = str(self.header[i]), CYAN_DIM
                    else:
                        j = i - self.HEADER_LEN
                        if j >= len(self.plain_bits):
                            continue
                        bit = self.plain_bits[j]
                        txt = "?" if bit is None else str(bit)
                        col = GREEN
                    self._text(
                        screen, txt, digit, col, cx,
                        top + row_h // 2, center=True,
                    )