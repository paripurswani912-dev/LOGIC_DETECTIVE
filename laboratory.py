
# laboratory.py
# Creates the NEXUS-9 laboratory map, walls, terminals, and doors.

import pygame
import settings


class Laboratory:
    def __init__(self):
        self.walls = self._create_walls()

        # Puzzle terminals placed around the laboratory.
        self.terminals = [
            {
                "id": "logic_lock",
                "name": "Logic Lock",
                "rect": pygame.Rect(150, 130, 65, 45),
                "puzzle_id": "logic_lock",
                "required_puzzle": None,
            },
            {
                "id": "hidden_transmission",
                "name": "Hidden Transmission",
                "rect": pygame.Rect(760, 130, 65, 45),
                "puzzle_id": "hidden_transmission",
                "required_puzzle": "logic_lock",
            },
            {
                "id": "memory_protocol",
                "name": "Memory Protocol",
                "rect": pygame.Rect(150, 450, 65, 45),
                "puzzle_id": "memory_protocol",
                "required_puzzle": "hidden_transmission",
            },
            {
                "id": "final_override",
                "name": "Final Override",
                "rect": pygame.Rect(760, 450, 65, 45),
                "puzzle_id": "final_override",
                "required_puzzle": "memory_protocol",
            },
        ]

        # Exit becomes available after the final puzzle.
        self.doors = [
            {
                "id": "exit",
                "name": "Laboratory Exit",
                "rect": pygame.Rect(450, 0, 100, 25),
                "required_puzzle": "final_override",
            }
        ]

        self.label_font = pygame.font.Font(None, 23)
        self.status_font = pygame.font.Font(None, 19)
        self.door_font = pygame.font.Font(None, 22)

    def _create_walls(self):
        """Create the laboratory's outer boundary and interior walls."""

        return [
            # Left and right boundaries.
            pygame.Rect(
                0, 0, 20, settings.SCREEN_HEIGHT
            ),
            pygame.Rect(
                settings.SCREEN_WIDTH - 20,
                0,
                20,
                settings.SCREEN_HEIGHT,
            ),

            # Bottom boundary.
            pygame.Rect(
                0,
                settings.SCREEN_HEIGHT - 20,
                settings.SCREEN_WIDTH,
                20,
            ),

            # Top boundary, leaving an opening for the exit.
            pygame.Rect(0, 0, 450, 20),
            pygame.Rect(550, 0, 450, 20),

            # Interior dividers with passageways.
            pygame.Rect(300, 100, 20, 170),
            pygame.Rect(300, 330, 20, 170),
            pygame.Rect(680, 100, 20, 170),
            pygame.Rect(680, 330, 20, 170),
        ]

    def draw(self, screen, completed_puzzles=None):
        """Draw the floor, walls, terminals, and exit door."""

        if completed_puzzles is None:
            completed_puzzles = set()

        # Background floor.
        screen.fill(settings.FLOOR_COLOR)

        # Subtle futuristic floor grid.
        grid_color = (32, 43, 58)

        for x in range(20, settings.SCREEN_WIDTH, 40):
            pygame.draw.line(
                screen,
                grid_color,
                (x, 20),
                (x, settings.SCREEN_HEIGHT - 20),
            )

        for y in range(20, settings.SCREEN_HEIGHT, 40):
            pygame.draw.line(
                screen,
                grid_color,
                (20, y),
                (settings.SCREEN_WIDTH - 20, y),
            )

        # Draw walls with a lighter outline.
        wall_outline = (75, 95, 120)

        for wall in self.walls:
            pygame.draw.rect(
                screen, settings.WALL_COLOR, wall
            )
            pygame.draw.rect(
                screen, wall_outline, wall, 2
            )

        # Draw puzzle terminals and their labels.
        for terminal in self.terminals:
            terminal_id = terminal["puzzle_id"]
            required = terminal["required_puzzle"]

            solved = terminal_id in completed_puzzles
            unlocked = (
                required is None
                or required in completed_puzzles
            )

            if solved:
                color = settings.GREEN
                status_text = "COMPLETED"
            elif unlocked:
                color = settings.CYAN
                status_text = "AVAILABLE"
            else:
                color = settings.GREY
                status_text = "LOCKED"

            rect = terminal["rect"]

            # Outer outline gives the terminal a glow-like effect.
            glow_rect = rect.inflate(10, 10)

            pygame.draw.rect(
                screen,
                color,
                glow_rect,
                2,
                border_radius=8,
            )

            # Main terminal body.
            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=5,
            )

            pygame.draw.rect(
                screen,
                settings.WHITE,
                rect,
                width=2,
                border_radius=5,
            )

            # Dark screen inside the terminal.
            inner_rect = rect.inflate(-16, -16)

            pygame.draw.rect(
                screen,
                settings.DARK_BLUE,
                inner_rect,
                border_radius=3,
            )

            # Terminal name below the terminal.
            label = self.label_font.render(
                terminal["name"],
                True,
                settings.WHITE,
            )

            label_rect = label.get_rect(
                midtop=(
                    rect.centerx,
                    rect.bottom + 7,
                )
            )

            screen.blit(label, label_rect)

            # Current terminal status.
            status = self.status_font.render(
                status_text,
                True,
                color,
            )

            status_rect = status.get_rect(
                midtop=(
                    rect.centerx,
                    label_rect.bottom + 3,
                )
            )

            screen.blit(status, status_rect)

        # Draw the laboratory exit.
        for door in self.doors:
            unlocked = (
                door["required_puzzle"]
                in completed_puzzles
            )

            color = (
                settings.UNLOCKED_DOOR_COLOR
                if unlocked
                else settings.LOCKED_DOOR_COLOR
            )

            rect = door["rect"]

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=4,
            )

            pygame.draw.rect(
                screen,
                settings.WHITE,
                rect,
                width=2,
                border_radius=4,
            )

            # Exit label.
            door_label = self.door_font.render(
                "EXIT",
                True,
                settings.WHITE,
            )

            door_label_rect = door_label.get_rect(
                center=(
                    rect.centerx,
                    rect.bottom + 15,
                )
            )

            screen.blit(
                door_label,
                door_label_rect,
            )

    def get_obstacles(self, completed_puzzles=None):
        """Return walls and doors that currently block movement."""

        if completed_puzzles is None:
            completed_puzzles = set()

        obstacles = list(self.walls)

        for door in self.doors:
            if (
                door["required_puzzle"]
                not in completed_puzzles
            ):
                obstacles.append(door["rect"])

        return obstacles

    def get_interactable_objects(self):
        """Return terminals and doors as interaction targets."""

        return self.terminals + self.doors

    def get_nearby_interactable(
        self, player, completed_puzzles=None
    ):
        """Find an accessible object close enough to interact with."""

        if completed_puzzles is None:
            completed_puzzles = set()

        player_center = pygame.Vector2(
            player.rect.center
        )

        nearby_object = None
        closest_distance = float("inf")

        for obj in self.get_interactable_objects():
            required = obj.get("required_puzzle")

            # Skip terminals and doors whose prerequisites are unmet.
            if (
                required
                and required not in completed_puzzles
            ):
                continue

            object_center = pygame.Vector2(
                obj["rect"].center
            )

            distance = player_center.distance_to(
                object_center
            )

            if (
                distance <= settings.INTERACTION_DISTANCE
                and distance < closest_distance
            ):
                nearby_object = obj
                closest_distance = distance

        return nearby_object

    def is_area_unlocked(
        self, area_id, completed_puzzles
    ):
        """Check whether an area's prerequisite puzzle is complete."""

        for terminal in self.terminals:
            if terminal["id"] == area_id:
                required = terminal["required_puzzle"]

                return (
                    required is None
                    or required in completed_puzzles
                )

        for door in self.doors:
            if door["id"] == area_id:
                return (
                    door["required_puzzle"]
                    in completed_puzzles
                )

        return False

    def update_door_states(self, completed_puzzles):
        """Return the current unlocked state of each door."""

        return {
            door["id"]: (
                door["required_puzzle"]
                in completed_puzzles
            )
            for door in self.doors
        }
