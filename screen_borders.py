
# screen_borders.py
# Shared pixel-art monitor frame for puzzle screens.
# Level 1 keeps its existing border code unchanged.

import pygame


def draw_pixel_monitor(screen, rect=None):
    """Draw the shared pixel-art monitor and return its inner panel."""

    if rect is None:
        width, height = screen.get_size()
        rect = pygame.Rect(
            18, 14,
            width - 36,
            height - 28,
        )
    else:
        rect = pygame.Rect(rect)

    x, y, w, h = rect

    bezel = (28, 30, 52)
    bezel_light = (48, 54, 91)
    bezel_dark = (15, 17, 34)
    screen_black = (4, 10, 22)
    screen_edge = (39, 91, 113)

    # Shadow and outer bezel.
    pygame.draw.rect(
        screen, (2, 3, 10),
        (x + 8, y + 8, w, h),
    )
    pygame.draw.rect(
        screen, bezel,
        (x + 8, y + 4, w - 16, h - 8),
    )
    pygame.draw.rect(
        screen, bezel,
        (x + 4, y + 10, w - 8, h - 20),
    )

    # Stepped pixel-art corners.
    step = 8
    corners = [
        (x + 16, y),
        (x + 8, y + 8),
        (x, y + 16),
        (x + w - 24, y),
        (x + w - 16, y + 8),
        (x + w - 8, y + 16),
        (x + 16, y + h - 8),
        (x + 8, y + h - 16),
        (x, y + h - 24),
        (x + w - 24, y + h - 8),
        (x + w - 16, y + h - 16),
        (x + w - 8, y + h - 24),
    ]

    for px, py in corners:
        pygame.draw.rect(
            screen, bezel_light,
            (px, py, step, step),
        )

    # Inner bezel and display panel.
    pygame.draw.rect(
        screen, bezel_dark,
        (x + 18, y + 18, w - 36, h - 36),
    )

    panel = pygame.Rect(
        x + 27, y + 27,
        w - 54, h - 54,
    )

    pygame.draw.rect(screen, screen_black, panel)
    pygame.draw.rect(screen, screen_edge, panel, 3)

    # Dashed pixel line along the top of the display.
    for px in range(panel.x + 8, panel.right - 8, 14):
        pygame.draw.rect(
            screen, (40, 86, 109),
            (px, panel.y + 5, 9, 3),
        )

    # Tiny monitor indicator lights.
    pygame.draw.rect(
        screen, (4, 5, 12),
        (x + w - 54, y + h - 13, 9, 4),
    )
    pygame.draw.rect(
        screen, (4, 5, 12),
        (x + w - 38, y + h - 13, 9, 4),
    )
    pygame.draw.rect(
        screen, (0, 218, 225),
        (x + w - 38, y + h - 13, 5, 4),
    )

    return panel
