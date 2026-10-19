
# interactions.py
# Handles nearby objects and the E-key interaction system.

import pygame
import settings


class InteractionManager:
    def __init__(self):
        self.nearby_object = None
        self.font = pygame.font.Font(None, 25)

    def find_nearby_object(self, player, objects,
                           completed_puzzles=None):
        """Find the closest accessible object within interaction range."""

        if completed_puzzles is None:
            completed_puzzles = set()

        player_center = pygame.Vector2(player.rect.center)
        self.nearby_object = None
        closest_distance = float("inf")

        for obj in objects:
            required = obj.get("required_puzzle")

            # Do not offer interactions for locked objects.
            if required and required not in completed_puzzles:
                continue

            object_center = pygame.Vector2(obj["rect"].center)
            distance = player_center.distance_to(object_center)

            if (
                distance <= settings.INTERACTION_DISTANCE
                and distance < closest_distance
            ):
                self.nearby_object = obj
                closest_distance = distance

        return self.nearby_object

    def handle_event(self, event, player, game_state):
        """Handle E when the player is near an accessible object."""

        if event.type != pygame.KEYDOWN:
            return None

        if event.key != pygame.K_e:
            return None

        if self.nearby_object is None:
            return None

        obj = self.nearby_object

        # A terminal requests its puzzle.
        if "puzzle_id" in obj:
            game_state.set_status(f"Accessing {obj['name']}...")
            return ("puzzle", obj["puzzle_id"])

        # A door requires its own interaction.
        game_state.set_status(f"Interacting with {obj['name']}...")
        return ("door", obj["id"])

    def draw_prompt(self, screen, nearby_object):
        """Display an interaction prompt near the bottom of the screen."""

        if nearby_object is None:
            return

        message = f"Press E to interact: {nearby_object['name']}"
        text = self.font.render(message, True, settings.WHITE)

        panel = pygame.Rect(
            0,
            settings.SCREEN_HEIGHT - 55,
            settings.SCREEN_WIDTH,
            55
        )

        pygame.draw.rect(screen, settings.PANEL_BLUE, panel)

        screen.blit(
            text,
            text.get_rect(
                center=(settings.SCREEN_WIDTH // 2,
                        settings.SCREEN_HEIGHT - 28)
            )
        )

    def interact_with(self, object_id, objects):
        """Find an object by its ID."""

        for obj in objects:
            if obj["id"] == object_id:
                return obj

        return None
