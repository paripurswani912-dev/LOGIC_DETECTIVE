"""Top-down pixel-style detective."""

import pygame
import settings


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(
            x,
            y,
            settings.PLAYER_WIDTH,
            settings.PLAYER_HEIGHT,
        )

        self.speed = settings.PLAYER_SPEED
        self.facing = "down"

        self.walk_time = 0.0
        self.moving = False

    def handle_movement(self, keys, dt, obstacles):
        dx = (
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        )

        dy = (
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )

        movement = pygame.Vector2(dx, dy)
        self.moving = movement.length_squared() > 0

        if self.moving:
            movement = movement.normalize()
            self.walk_time += dt

            if abs(movement.x) > abs(movement.y):
                self.facing = "right" if movement.x > 0 else "left"
            else:
                self.facing = "down" if movement.y > 0 else "up"
        else:
            self.walk_time = 0.0

        # Horizontal movement and collision resolution.
        self.rect.x += round(movement.x * self.speed * dt)

        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if movement.x > 0:
                    self.rect.right = obstacle.left
                elif movement.x < 0:
                    self.rect.left = obstacle.right

        # Vertical movement and collision resolution.
        self.rect.y += round(movement.y * self.speed * dt)

        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if movement.y > 0:
                    self.rect.bottom = obstacle.top
                elif movement.y < 0:
                    self.rect.top = obstacle.bottom

        # Keep the detective inside the screen.
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(settings.SCREEN_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(settings.SCREEN_HEIGHT, self.rect.bottom)

    def draw(self, screen):
        """Draw a small detective using pixel-style geometric shapes."""

        x, y = self.rect.center

        # Alternate the legs while walking.
        step = 0

        if self.moving:
            step = 2 if int(self.walk_time * 12) % 2 else -2

        bob = 1 if self.moving and step > 0 else 0

        # Shadow.
        pygame.draw.ellipse(
            screen,
            (3, 7, 12),
            (x - 12, y + 9, 24, 8),
        )

        # Legs and shoes.
        pygame.draw.rect(
            screen,
            (31, 24, 23),
            (x - 8 + step, y + 12, 6, 6),
        )

        pygame.draw.rect(
            screen,
            (31, 24, 23),
            (x + 2 - step, y + 12, 6, 6),
        )

        # Brown trench coat.
        pygame.draw.rect(
            screen,
            (105, 61, 35),
            (x - 8, y - 1 + bob, 16, 17),
        )

        pygame.draw.rect(
            screen,
            (170, 108, 57),
            (x - 7, y + 1 + bob, 5, 12),
        )

        pygame.draw.rect(
            screen,
            (170, 108, 57),
            (x + 2, y + 1 + bob, 5, 12),
        )

        # Face.
        pygame.draw.rect(
            screen,
            (211, 157, 111),
            (x - 5, y - 10 + bob, 10, 10),
        )

        # Hair.
        pygame.draw.rect(
            screen,
            (48, 31, 24),
            (x - 6, y - 11 + bob, 12, 4),
        )

        # Fedora brim.
        pygame.draw.rect(
            screen,
            (48, 31, 25),
            (x - 11, y - 13 + bob, 22, 4),
        )

        # Fedora crown.
        pygame.draw.rect(
            screen,
            (69, 43, 31),
            (x - 7, y - 19 + bob, 14, 7),
        )

        # Hat band.
        pygame.draw.rect(
            screen,
            (204, 132, 59),
            (x - 6, y - 14 + bob, 12, 2),
        )

        # Coat highlight.
        pygame.draw.rect(
            screen,
            (222, 166, 90),
            (x - 2, y + 1 + bob, 3, 10),
        )

    def get_rect(self):
        return self.rect 