# Level 5: Logic Architect — interactive 3-variable K-map
import pygame
from .base_puzzle import BasePuzzle
import settings


class LogicArchitectPuzzle(BasePuzzle):
    """Interactive SOP K-map. Select valid groups of 1s until all 1s are covered."""

    # Gray-code columns 00, 01, 11, 10
    CELL_VALUES = [[0, 1, 3, 2], [4, 5, 7, 6]]
    ONES = {1, 2, 3, 5, 7}

    def __init__(self):
        super().__init__()
        self.selected = set()
        self.groups = []
        self.message = "Click 1-cells to select a group; SPACE saves the group."
        self.grid_x, self.grid_y = 260, 205
        self.cell_width, self.cell_height = 105, 78

    def cell_rect(self, row, col):
        return pygame.Rect(self.grid_x + col * self.cell_width,
                           self.grid_y + row * self.cell_height,
                           self.cell_width, self.cell_height)

    @staticmethod
    def is_power_of_two(n):
        return n > 0 and (n & (n - 1)) == 0

    def is_valid_group(self, cells):
        if not cells or len(cells) not in (1, 2, 4, 8):
            return False
        minterms = {self.CELL_VALUES[r][c] for r, c in cells}
        if not minterms.issubset(self.ONES):
            return False
        rows = sorted({r for r, c in cells})
        cols = sorted({c for r, c in cells})
        if len(cells) != len(rows) * len(cols):
            return False
        if len(rows) not in (1, 2) or len(cols) not in (1, 2, 4):
            return False
        if len(rows) == 2 and rows != [0, 1]:
            return False
        if len(cols) == 2 and (cols[1] - cols[0]) not in (1, 3):
            return False
        return self.is_power_of_two(len(cells))

    def add_group(self):
        if not self.selected:
            self.message = "Select cells first."
        elif not self.is_valid_group(self.selected):
            self.message = "Invalid group: select adjacent 1s in a group of 1, 2, 4 or 8."
        else:
            if set(self.selected) not in self.groups:
                self.groups.append(set(self.selected))
            self.selected.clear()
            self.message = f"Group saved ({len(self.groups)}). Cover every 1-cell."

    def check_solution(self):
        covered = set()
        for group in self.groups:
            covered.update(self.CELL_VALUES[r][c] for r, c in group)
        missing = self.ONES - covered
        if missing:
            self.message = "Still uncovered: " + ", ".join(f"m{x}" for x in sorted(missing))
            return
        self.solved = True
        self.message = "Solved! Simplified expression: F = C + A'B"

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r in range(2):
                for c in range(4):
                    if self.cell_rect(r, c).collidepoint(event.pos):
                        minterm = self.CELL_VALUES[r][c]
                        if minterm not in self.ONES:
                            self.message = f"m{minterm} is 0; this SOP map groups 1s."
                            return
                        cell = (r, c)
                        if cell in self.selected:
                            self.selected.remove(cell)
                        else:
                            self.selected.add(cell)
                        self.message = f"{len(self.selected)} cell(s) selected. Press SPACE to save."
                        return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.add_group()
            elif event.key == pygame.K_RETURN:
                self.check_solution()
            elif event.key == pygame.K_BACKSPACE:
                if self.groups:
                    self.groups.pop()
                    self.message = "Removed the last group."
                else:
                    self.selected.clear()
                    self.message = "Selection cleared."
            elif event.key == pygame.K_h:
                self.message = "Hint: group m1, m3, m5, m7; then group m2 with m3."

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

        write("LEVEL 5: LOGIC ARCHITECT", title, settings.CYAN, 35, 25)
        write("KARNAUGH MAP / SOP SIMPLIFICATION", body, settings.GREY, 38, 70)
        write("F(A,B,C) = Σm(1,2,3,5,7)", heading, settings.WHITE, 260, 125)
        write("BC", small, settings.CYAN, 230, 180)
        write("00      01      11      10", body, settings.WHITE, 260, 177)
        write("A=0", body, settings.CYAN, 190, 230)
        write("A=1", body, settings.CYAN, 190, 310)

        for r in range(2):
            for c in range(4):
                rect = self.cell_rect(r, c)
                minterm = self.CELL_VALUES[r][c]
                value = 1 if minterm in self.ONES else 0
                in_saved_group = any((r, c) in group for group in self.groups)
                fill = settings.CYAN if (r, c) in self.selected else (
                    settings.GREEN if in_saved_group else settings.PANEL_BLUE
                )
                pygame.draw.rect(screen, fill, rect, border_radius=5)
                pygame.draw.rect(screen, settings.GREY, rect, 2, border_radius=5)
                ink = settings.DARK_BLUE if fill in (settings.CYAN, settings.GREEN) else settings.WHITE
                write(str(value), title, ink, rect.centerx, rect.centery - 9, True)
                write(f"m{minterm}", small, ink, rect.centerx, rect.bottom - 17, True)

        pygame.draw.rect(screen, settings.PANEL_BLUE, (60, 395, 880, 145), border_radius=10)
        write("HOW TO SOLVE", heading, settings.CYAN, 80, 410)
        instructions = [
            "1. Click cells containing 1 to select a group.",
            "2. Press SPACE to save the group. Groups may overlap or wrap around.",
            "3. Cover every 1-cell, then press ENTER to check.",
            "BACKSPACE removes the last group. H gives a hint.",
        ]
        for i, line in enumerate(instructions):
            write(line, small, settings.WHITE, 82, 445 + i * 21)
        write(f"Groups saved: {len(self.groups)}", body, settings.GREEN, 700, 125)
        write(self.message, small, settings.YELLOW, 60, 565)
        if self.solved:
            write("LEVEL COMPLETE", heading, settings.GREEN, settings.SCREEN_WIDTH // 2, 620, True)
