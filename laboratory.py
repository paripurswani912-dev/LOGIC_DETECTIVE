# laboratory.py
# Creates the NEXUS-9 laboratory map, walls, terminals, and exit.

import pygame
import settings


class Laboratory:
    def __init__(self):
        self.walls = self._create_walls()
        self.terminals = [
            {
                "id": "logic_lock", "name": "Logic Lock",
                "rect": pygame.Rect(150, 130, 65, 45),
                "puzzle_id": "logic_lock", "required_puzzle": None,
            },
            {
                "id": "hidden_transmission", "name": "Hidden Transmission",
                "rect": pygame.Rect(760, 130, 65, 45),
                "puzzle_id": "hidden_transmission",
                "required_puzzle": "logic_lock",
            },
            {
                "id": "memory_protocol", "name": "Memory Protocol",
                "rect": pygame.Rect(150, 450, 65, 45),
                "puzzle_id": "memory_protocol",
                "required_puzzle": "hidden_transmission",
            },
            {
                "id": "final_override", "name": "Final Override",
                "rect": pygame.Rect(760, 450, 65, 45),
                "puzzle_id": "final_override",
                "required_puzzle": "memory_protocol",
            },
            {
                "id": "logic_architect", "name": "Logic Architect",
                "rect": pygame.Rect(450, 275, 65, 45),
                "puzzle_id": "logic_architect",
                "required_puzzle": "final_override",
            },
            {
                "id": "signal_breaker", "name": "Signal Breaker",
                "rect": pygame.Rect(450, 465, 65, 45),
                "puzzle_id": "signal_breaker",
                "required_puzzle": "logic_architect",
            },
        ]
        self.doors = [
            {
                "id": "exit", "name": "Laboratory Exit",
                "rect": pygame.Rect(450, 0, 100, 25),
                "required_puzzle": "signal_breaker",
            }
        ]
        self.label_font = pygame.font.Font(None, 23)
        self.status_font = pygame.font.Font(None, 19)
        self.door_font = pygame.font.Font(None, 22)

    def _create_walls(self):
        return [
            pygame.Rect(0, 0, 20, settings.SCREEN_HEIGHT),
            pygame.Rect(settings.SCREEN_WIDTH - 20, 0, 20, settings.SCREEN_HEIGHT),
            pygame.Rect(0, settings.SCREEN_HEIGHT - 20, settings.SCREEN_WIDTH, 20),
            pygame.Rect(0, 0, 450, 20),
            pygame.Rect(550, 0, 450, 20),
            pygame.Rect(300, 100, 20, 170),
            pygame.Rect(300, 330, 20, 170),
            pygame.Rect(680, 100, 20, 170),
            pygame.Rect(680, 330, 20, 170),
        ]

    def draw(self, screen, completed_puzzles=None):
        if completed_puzzles is None:
            completed_puzzles = set()

        screen.fill(settings.FLOOR_COLOR)
        grid_color = (32, 43, 58)
        for x in range(20, settings.SCREEN_WIDTH, 40):
            pygame.draw.line(screen, grid_color, (x, 20),
                             (x, settings.SCREEN_HEIGHT - 20))
        for y in range(20, settings.SCREEN_HEIGHT, 40):
            pygame.draw.line(screen, grid_color, (20, y),
                             (settings.SCREEN_WIDTH - 20, y))

        wall_outline = (75, 95, 120)
        for wall in self.walls:
            pygame.draw.rect(screen, settings.WALL_COLOR, wall)
            pygame.draw.rect(screen, wall_outline, wall, 2)

        for terminal in self.terminals:
            terminal_id = terminal["puzzle_id"]
            required = terminal["required_puzzle"]
            solved = terminal_id in completed_puzzles
            unlocked = required is None or required in completed_puzzles

            if solved:
                color, status_text = settings.GREEN, "COMPLETED"
            elif unlocked:
                color, status_text = settings.CYAN, "AVAILABLE"
            else:
                color, status_text = settings.GREY, "LOCKED"

            rect = terminal["rect"]
            pygame.draw.rect(screen, color, rect.inflate(10, 10),
                             2, border_radius=8)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, settings.WHITE, rect, 2, border_radius=5)
            pygame.draw.rect(screen, settings.DARK_BLUE,
                             rect.inflate(-16, -16), border_radius=3)

            label = self.label_font.render(terminal["name"], True, settings.WHITE)
            label_rect = label.get_rect(midtop=(rect.centerx, rect.bottom + 7))
            screen.blit(label, label_rect)

            status = self.status_font.render(status_text, True, color)
            screen.blit(status, status.get_rect(
                midtop=(rect.centerx, label_rect.bottom + 3)
            ))

        for door in self.doors:
            unlocked = door["required_puzzle"] in completed_puzzles
            color = settings.UNLOCKED_DOOR_COLOR if unlocked else settings.LOCKED_DOOR_COLOR
            rect = door["rect"]
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, settings.WHITE, rect, 2, border_radius=4)
            label = self.door_font.render("EXIT", True, settings.WHITE)
            screen.blit(label, label.get_rect(center=(rect.centerx, rect.bottom + 15)))

    def get_obstacles(self, completed_puzzles=None):
        if completed_puzzles is None:
            completed_puzzles = set()
        obstacles = list(self.walls)
        for door in self.doors:
            if door["required_puzzle"] not in completed_puzzles:
                obstacles.append(door["rect"])
        return obstacles

    def get_interactable_objects(self):
        return self.terminals + self.doors

    def get_nearby_interactable(self, player, completed_puzzles=None):
        if completed_puzzles is None:
            completed_puzzles = set()
        player_center = pygame.Vector2(player.rect.center)
        nearby_object = None
        closest_distance = float("inf")

        for obj in self.get_interactable_objects():
            required = obj.get("required_puzzle")
            if required and required not in completed_puzzles:
                continue
            distance = player_center.distance_to(pygame.Vector2(obj["rect"].center))
            if distance <= settings.INTERACTION_DISTANCE and distance < closest_distance:
                nearby_object = obj
                closest_distance = distance
        return nearby_object

    def is_area_unlocked(self, area_id, completed_puzzles):
        for obj in self.get_interactable_objects():
            if obj["id"] == area_id:
                required = obj.get("required_puzzle")
                return required is None or required in completed_puzzles
        return False

    def update_door_states(self, completed_puzzles):
        return {
            door["id"]: door["required_puzzle"] in completed_puzzles
            for door in self.doors
        }
