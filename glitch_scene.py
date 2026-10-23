"""Glitch transition scene between false exit and Level 7.

Renders 1.5 seconds of intense screen glitching, horizontal jitter,
RGB slice displacement, and flashes "YOU THOUGHT YOU ESCAPED ME?" in RED,
then smoothly transitions into Level 7.
"""

import math
import random
import pygame
import settings


class GlitchScene:
    """Standalone 1.5-second glitch transition sequence."""

    DURATION = 1.5  # seconds

    def __init__(self):
        self.elapsed = 0.0
        self.done = False
        self.font_large = pygame.font.SysFont("monospace", 36, bold=True)
        self.font_sub = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_glitch = pygame.font.SysFont("monospace", 14, bold=True)
        self.rng = random.Random(42)

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.DURATION:
            self.done = True

    def is_done(self):
        return self.done

    def draw(self, screen):
        width, height = screen.get_size()
        t = self.elapsed

        # 1. Dark corrupted background with red and cyan artifacts
        screen.fill((4, 6, 14))

        # Horizontal glitch scanlines and noise blocks
        for _ in range(16):
            sy = random.randint(0, height - 1)
            sh = random.randint(2, 12)
            sx = random.randint(0, width // 2)
            sw = random.randint(width // 4, width)
            color = random.choice([
                (180, 20, 40),
                (15, 60, 80),
                (255, 48, 75),
                (0, 180, 200),
                (20, 25, 45),
            ])
            pygame.draw.rect(screen, color, (sx, sy, sw, sh))

        # 2. Main menacing message
        # Jitter position slightly
        jitter_x = random.randint(-4, 4) if random.random() < 0.6 else 0
        jitter_y = random.randint(-2, 2) if random.random() < 0.6 else 0

        center_x = width // 2 + jitter_x
        center_y = height // 2 + jitter_y

        # Flashing red text
        flash_red = (255, 48, 75) if (int(t * 12) % 2 == 0) else (200, 25, 45)

        # RGB split shadow behind text
        if random.random() < 0.7:
            cyan_text = self.font_large.render("YOU THOUGHT YOU ESCAPED ME?", True, (0, 218, 225))
            screen.blit(cyan_text, cyan_text.get_rect(center=(center_x + 5, center_y - 2)))

        main_text = self.font_large.render("YOU THOUGHT YOU ESCAPED ME?", True, flash_red)
        screen.blit(main_text, main_text.get_rect(center=(center_x, center_y)))

        # Subtitle
        sub_text = self.font_sub.render("NEXUS-9 // THE FALSE EXIT", True, (220, 235, 246))
        screen.blit(sub_text, sub_text.get_rect(center=(center_x, center_y + 48)))

        # Terminal status warning
        warning_msg = f"OVERRIDE DETECTED // SECTOR LOCK ACTIVE [{(self.DURATION - t):0.1f}s]"
        status_text = self.font_glitch.render(warning_msg, True, (255, 190, 45))
        screen.blit(status_text, status_text.get_rect(center=(center_x, center_y + 85)))

        # 3. Surface slice displacement glitch
        temp = screen.copy()
        slice_count = random.randint(3, 7)
        for _ in range(slice_count):
            slice_y = random.randint(0, height - 20)
            slice_h = random.randint(6, 28)
            offset_x = random.randint(-25, 25)
            screen.blit(temp, (offset_x, slice_y), area=pygame.Rect(0, slice_y, width, slice_h))

        # 4. Red flash overlay
        if random.random() < 0.25:
            flash = pygame.Surface((width, height), pygame.SRCALPHA)
            flash.fill((255, 30, 50, random.randint(30, 80)))
            screen.blit(flash, (0, 0))
