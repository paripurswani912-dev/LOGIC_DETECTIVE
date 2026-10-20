# Level 6: Signal Breaker — crack an LFSR stream cipher
#
# A 5-cell shift register shifts RIGHT. The bit that falls off the right end is
# the keystream output; the new bit entering on the left is the XOR of the
# "tapped" cells. The player only knows the first 12 intercepted output bits.
#
# Deductions required:
#   * Seed unknown: the first 5 output bits are the seed read BACKWARDS.
#   * Taps unknown: exactly two, one of which is cell 5 -> test the candidates.
#   * Once the 12-bit header matches, keep clocking: the ciphertext decrypts
#     live (cipher XOR keystream) into the final transmission.
import pygame
from .base_puzzle import BasePuzzle
import settings


def lfsr_stream(seed, taps, count):
    reg = list(seed)
    out = []
    for _ in range(count):
        out.append(reg[-1])
        fb = 0
        for t in taps:
            fb ^= reg[t]
        reg = [fb] + reg[:-1]
    return out


class SignalBreakerPuzzle(BasePuzzle):
    """Break a hidden LFSR from an intercepted header, then decrypt the message."""

    SECRET = "K7"                 # change to your story's final code (2-3 chars works well)
    SEED = [0, 1, 1, 0, 1]        # hidden: boot vector
    TRUE_TAPS = (2, 4)            # hidden: cells 3 and 5 (0-indexed 2 and 4)
    HEADER_LEN = 12
    CELLS = 5

    CLUES = [
        "INTERCEPT REPORT",
        "- Cipher engine: 5-cell register, shifts RIGHT every clock.",
        "- Output bit = the cell that falls off the right end.",
        "- New bit enters on the LEFT = XOR of the tapped cells.",
        "- Exactly two taps, and one of them is cell 5. Seed unknown.",
        "- The 12-bit header is on the monitor. Match it exactly.",
        "- Then keep clocking: the ciphertext decrypts itself.",
        "- A wrong output bit locks the run. Press H for a hint.",
    ]

    HINTS = [
        "Hint: the first bit out is the right-most cell. Where do the first 5 header bits come from?",
        "Hint: the seed is the first 5 header bits read BACKWARDS. Click register cells to set it.",
        "Hint: cell 5 is always tapped. Try cell 1, 2, 3 or 4 as the other tap.",
    ]

    def __init__(self):
        super().__init__()
        secret_bits = []
        for ch in self.SECRET:
            secret_bits += [int(b) for b in format(ord(ch), "08b")]
        self.total_len = self.HEADER_LEN + len(secret_bits)
        stream = lfsr_stream(self.SEED, self.TRUE_TAPS, self.total_len)
        self.header = stream[:self.HEADER_LEN]
        self.cipher = [p ^ k for p, k in zip(secret_bits, stream[self.HEADER_LEN:])]

        self.seed = [0] * self.CELLS
        self.taps = set()
        self.hint_index = 0
        self.restart("Set the seed (click cells), choose taps, then pulse the clock.")

    # --------------------------------------------------------------- logic
    def restart(self, message):
        self.reg = list(self.seed)
        self.outputs = []
        self.clock_count = 0
        self.broken = False
        self.generator_ok = False
        self.message = message

    def toggle_seed(self, i):
        if self.clock_count > 0:
            self.message = "Seed is locked while running. RESET first."
            return
        self.seed[i] ^= 1
        self.reg = list(self.seed)
        self.message = f"Seed = {''.join(map(str, self.seed))}"

    def toggle_tap(self, i):
        if self.clock_count > 0:
            self.message = "Taps are locked while running. RESET first."
            return
        if i in self.taps:
            self.taps.remove(i)
        else:
            self.taps.add(i)
        shown = ", ".join(str(t + 1) for t in sorted(self.taps)) or "none"
        self.message = f"Taps on cell(s): {shown}"

    def decrypted_bits(self):
        keys = self.outputs[self.HEADER_LEN:]
        return [self.cipher[i] ^ k for i, k in enumerate(keys)]

    def decoded_text(self):
        bits = self.decrypted_bits()
        chars = []
        for i in range(0, len(bits) - 7, 8):
            value = int("".join(map(str, bits[i:i + 8])), 2)
            chars.append(chr(value) if 32 <= value < 127 else "?")
        return "".join(chars)

    def clock_pulse(self):
        if self.solved:
            return
        if self.broken:
            self.message = "Output already diverged. RESET (BACKSPACE) and rethink the seed or taps."
            return
        if not self.taps:
            self.message = "Select at least one tap: with none, the feedback bit is always 0."
            return
        if len(self.outputs) >= self.total_len:
            return

        out = self.reg[-1]
        fb = 0
        for t in self.taps:
            fb ^= self.reg[t]
        self.reg = [fb] + self.reg[:-1]
        self.outputs.append(out)
        self.clock_count += 1
        idx = len(self.outputs) - 1

        if idx < self.HEADER_LEN:
            if out != self.header[idx]:
                self.broken = True
                self.message = f"Output bit {idx + 1} is {out} but the intercept says {self.header[idx]}. Run locked."
            elif idx == self.HEADER_LEN - 1:
                self.generator_ok = True
                self.message = "GENERATOR CRACKED! Keep clocking to decrypt the message."
            else:
                self.message = f"Output bit {idx + 1} matches."
        else:
            self.message = f"Decrypted so far: {self.decoded_text() or '...'}"
            if len(self.outputs) == self.total_len:
                self.solved = True
                self.message = f'FINAL TRANSMISSION RECOVERED: "{self.decoded_text()}"'

    # -------------------------------------------------------------- events
    def cell_rect(self, i):
        return pygame.Rect(200 + i * 90, 330, 70, 60)

    def tap_rect(self, i):
        return pygame.Rect(200 + i * 90, 398, 70, 28)

    def button_rect(self, i):
        return pygame.Rect(60 + i * 220, 445, 200, 45)

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.clock_pulse()
            elif event.key == pygame.K_x:
                for _ in range(4):
                    self.clock_pulse()
            elif event.key == pygame.K_BACKSPACE:
                self.restart("Register reset to your seed. Taps unlocked.")
            elif event.key == pygame.K_h:
                self.message = self.HINTS[self.hint_index % len(self.HINTS)]
                self.hint_index += 1
            elif pygame.K_1 <= event.key <= pygame.K_5:
                self.toggle_tap(event.key - pygame.K_1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(self.CELLS):
                if self.cell_rect(i).collidepoint(event.pos):
                    self.toggle_seed(i)
                    return
                if self.tap_rect(i).collidepoint(event.pos):
                    self.toggle_tap(i)
                    return
            if self.button_rect(0).collidepoint(event.pos):
                self.clock_pulse()
            elif self.button_rect(1).collidepoint(event.pos):
                for _ in range(4):
                    self.clock_pulse()
            elif self.button_rect(2).collidepoint(event.pos):
                self.restart("Register reset to your seed. Taps unlocked.")

    # ---------------------------------------------------------------- draw
    def draw(self, screen):
        screen.fill(settings.DARK_BLUE)
        title = pygame.font.Font(None, 42)
        heading = pygame.font.Font(None, 28)
        body = pygame.font.Font(None, 22)
        small = pygame.font.Font(None, 19)

        def write(text, font, color, x, y, center=False):
            image = font.render(text, True, color)
            rect = image.get_rect()
            if center:
                rect.center = (x, y)
            else:
                rect.topleft = (x, y)
            screen.blit(image, rect)

        def bit_row(items, x, y, size, step):
            """items: list of (bit or None, fill colour or None)."""
            for i, (bit, fill) in enumerate(items):
                rect = pygame.Rect(x + i * step, y, size, size)
                if bit is None:
                    pygame.draw.rect(screen, settings.PANEL_BLUE, rect, border_radius=4)
                    pygame.draw.rect(screen, settings.GREY, rect, 1, border_radius=4)
                else:
                    pygame.draw.rect(screen, fill, rect, border_radius=4)
                    write(str(bit), body, settings.DARK_BLUE, rect.centerx, rect.centery, True)

        write("LEVEL 6: SIGNAL BREAKER", title, settings.CYAN, 35, 25)
        write("SEQUENTIAL LOGIC / LFSR STREAM CIPHER", body, settings.GREY, 38, 70)

        # Clues
        pygame.draw.rect(screen, settings.PANEL_BLUE, (40, 100, 520, 215), border_radius=10)
        write(self.CLUES[0], heading, settings.CYAN, 60, 110)
        for i, line in enumerate(self.CLUES[1:]):
            write(line, small, settings.WHITE, 62, 142 + i * 23)

        # Monitor
        pygame.draw.rect(screen, settings.PANEL_BLUE, (580, 100, 360, 215), border_radius=10)
        write("INTERCEPTED HEADER", small, settings.GREY, 592, 112)
        bit_row([(b, settings.CYAN) for b in self.header], 592, 132, 26, 29)
        write("YOUR OUTPUT", small, settings.GREY, 592, 175)
        mine = []
        for i in range(self.HEADER_LEN):
            if i < len(self.outputs):
                ok = self.outputs[i] == self.header[i]
                mine.append((self.outputs[i], settings.GREEN if ok else settings.RED))
            else:
                mine.append((None, None))
        bit_row(mine, 592, 195, 26, 29)
        write(f"Clock pulses: {self.clock_count}", body, settings.WHITE, 592, 245)
        stage = "STAGE 2: DECRYPT" if self.generator_ok else "STAGE 1: BREAK THE GENERATOR"
        write(stage, small, settings.YELLOW, 592, 272)

        # Register
        write("REGISTER", heading, settings.CYAN, 60, 345)
        write("(click a cell = seed bit)", small, settings.GREY, 60, 372)
        write("IN >", body, settings.WHITE, 158, 352)
        write("> OUT", body, settings.WHITE, 645, 352)
        for i, bit in enumerate(self.reg):
            rect = self.cell_rect(i)
            pygame.draw.rect(screen, settings.GREEN if bit else settings.PANEL_BLUE, rect, border_radius=8)
            pygame.draw.rect(screen, settings.WHITE, rect, 2, border_radius=8)
            ink = settings.DARK_BLUE if bit else settings.WHITE
            write(str(bit), title, ink, rect.centerx, rect.centery, True)
            tap = self.tap_rect(i)
            on = i in self.taps
            pygame.draw.rect(screen, settings.YELLOW if on else settings.PANEL_BLUE, tap, border_radius=6)
            pygame.draw.rect(screen, settings.GREY, tap, 1, border_radius=6)
            ink = settings.DARK_BLUE if on else settings.WHITE
            write(f"TAP {i + 1} [{i + 1}]", small, ink, tap.centerx, tap.centery, True)

        # Buttons
        for i, (label, color) in enumerate([("CLOCK [SPACE]", settings.CYAN),
                                            ("CLOCK x4 [X]", settings.GREEN),
                                            ("RESET [BACKSPACE]", settings.RED)]):
            rect = self.button_rect(i)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            image = body.render(label, True, settings.DARK_BLUE)
            screen.blit(image, image.get_rect(center=rect.center))

        # Decrypt module
        if self.generator_ok:
            keys = self.outputs[self.HEADER_LEN:]
            plain = self.decrypted_bits()
            n = len(self.cipher)
            write("CIPHERTEXT", small, settings.GREY, 60, 508)
            bit_row([(b, settings.CYAN) for b in self.cipher], 200, 503, 22, 26)
            write("KEYSTREAM", small, settings.GREY, 60, 538)
            bit_row([(keys[i], settings.YELLOW) if i < len(keys) else (None, None) for i in range(n)],
                    200, 533, 22, 26)
            write("PLAINTEXT", small, settings.GREY, 60, 568)
            bit_row([(plain[i], settings.GREEN) if i < len(plain) else (None, None) for i in range(n)],
                    200, 563, 22, 26)
            write(f"Decoded: {self.decoded_text()}", heading, settings.GREEN, 650, 563)
        else:
            write("DECRYPT MODULE OFFLINE: crack the generator first.", small, settings.GREY, 60, 520)

        write(self.message, small, settings.YELLOW, 60, 610)
        if self.solved:
            write("LEVEL COMPLETE", heading, settings.GREEN, 760, 610)