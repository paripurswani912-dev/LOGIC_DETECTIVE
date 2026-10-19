
# player.py
# Handles player position, movement, collision, and drawing.

import pygame
import settings


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(
            x,
            y,
            settings.PLAYER_WIDTH,
            settings.PLAYER_HEIGHT
        )

        self.speed = settings.PLAYER_SPEED
        self.color = settings.CYAN


    def handle_movement(self, keys, dt, obstacles):
        """Move the player and prevent walking through obstacles."""

        dx = 0
        dy = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1

        movement = pygame.Vector2(dx, dy)

        if movement.length_squared() > 0:
            movement = movement.normalize()

        # Move horizontally and resolve collisions.
        self.rect.x += round(movement.x * self.speed * dt)

        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if movement.x > 0:
                    self.rect.right = obstacle.left
                elif movement.x < 0:
                    self.rect.left = obstacle.right

        # Move vertically and resolve collisions.
        self.rect.y += round(movement.y * self.speed * dt)

        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if movement.y > 0:
                    self.rect.bottom = obstacle.top
                elif movement.y < 0:
                    self.rect.top = obstacle.bottom


    def draw(self, screen):
        """Draw the player on the game screen."""

        pygame.draw.rect(
            screen,
            self.color,
            self.rect,
            border_radius=6
        )

    def get_rect(self):
        """Return the player's rectangle for collision checks."""
        return self.rect
