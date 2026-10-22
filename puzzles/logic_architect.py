# Level 5: Vault Alarm Puzzle
# Four-variable Karnaugh map with don't-cares, wraparound,
# overlapping groups, and horizontal/vertical grouping only.
# Only maximal (prime) groups are accepted, and the final answer
# must use the minimum number of groups.
#
# Phases: FILL (rebuild the K-map) -> GROUP (simplify)
#         -> BUILD (wire the simplified expression as a circuit)

import itertools
import pygame
import settings

from .base_puzzle import BasePuzzle
from .logic_architect_circuits import LogicArchitectCircuitMixin
from screen_borders import draw_pixel_monitor


class LogicArchitectPuzzle(LogicArchitectCircuitMixin, BasePuzzle):
    """Reconstruct the vault alarm K-map, simplify it, then build it."""

    GRAY = [0, 1, 3, 2]
    LABELS = ["00", "01", "11", "10"]
    VARS = "ABCD"

    ONES = {0, 2, 4, 5, 7, 8, 10, 13, 15}
    DONT_CARE = {12}
    EVIDENCE_ORDER = [13, 2, 7, 0, 10, 4, 15, 5, 8]

    GROUP_COLORS = [
        (255, 90, 90),
        (255, 200, 60),
        (120, 220, 255),
        (190, 130, 255),
        (120, 255, 160),
        (255, 150, 220),
    ]

    PINK = (255, 115, 190)
    ORANGE = (255, 155, 45)
    LIGHT_BLUE = (75, 235, 255)

    CELL_ONE = (24, 145, 145)
    CELL_ZERO = (17, 35, 52)
    CELL_X = (145, 105, 35)

    HINTS = [
        "Rows are AB and columns are CD, in Gray-code order: 00, 01, 11, 10.",
        "The map wraps around: opposite edges touch, including the corners.",
        "Groups must be 1, 2, 4, 8, or 16 cells. Use X if helpful, never 0.",
        "Make each group as large as possible. Overlap is fine, and fewer groups is better.",
    ]

    def __init__(self):
        super().__init__()

        self.phase = "FILL"
        self.player = [[0] * 4 for _ in range(4)]  # 0, 1, 2 = X
        self.selected = set()
        self.groups = []

        self.hint_index = 0
        self.message = "Place each recorded scene in its correct K-map cell."

        self.awaiting_return = False
        self.completed = False

        self.last_click_time = 0
        self.last_click_cell = None

        self.grid_x = 0
        self.grid_y = 0
        self.cell_width = 0
        self.cell_height = 0

        self.all_rects = set()
        self.case_rect = pygame.Rect(0, 0, 0, 0)
        self.map_rect = pygame.Rect(0, 0, 0, 0)

        self.ones_cells = {
            cell for cell in self.all_cells()
            if self.minterm(*cell) in self.ONES
        }

        self.dc_cells = {
            cell for cell in self.all_cells()
            if self.minterm(*cell) in self.DONT_CARE
        }

        self.all_groups = self.build_rects()
        self.primes = self.find_maximal_groups()
        self.min_cover = self.compute_min_cover()

        # NEW: circuit BUILD phase state
        self._init_circuits()

    # ------------------------------------------------------------
    # K-map logic
    # ------------------------------------------------------------

    @staticmethod
    def all_cells():
        return [(r, c) for r in range(4) for c in range(4)]

    def minterm(self, r, c):
        return (self.GRAY[r] << 2) | self.GRAY[c]

    def target_value(self, r, c):
        minterm = self.minterm(r, c)

        if minterm in self.ONES:
            return 1

        if minterm in self.DONT_CARE:
            return 2

        return 0

    def build_rects(self):
        """Build straight horizontal/vertical groups with wraparound."""
        groups = set()

        for height in (1, 2, 4):
            for width in (1, 2, 4):
                size = height * width

                if size not in (1, 2, 4, 8, 16):
                    continue

                for r0 in range(4):
                    for c0 in range(4):
                        group = frozenset(
                            (
                                (r0 + dr) % 4,
                                (c0 + dc) % 4,
                            )
                            for dr in range(height)
                            for dc in range(width)
                        )
                        groups.add(group)

        return groups

    def valid_group(self, group):
        usable = self.ones_cells | self.dc_cells

        return (
            group in self.all_groups
            and group <= usable
            and bool(group & self.ones_cells)
        )

    def find_maximal_groups(self):
        usable = self.ones_cells | self.dc_cells

        valid = [
            group for group in self.all_groups
            if group <= usable and group & self.ones_cells
        ]

        return {
            group for group in valid
            if not any(group < other for other in valid)
        }

    def compute_min_cover(self):
        primes = list(self.primes)

        for count in range(1, len(primes) + 1):
            for combination in itertools.combinations(primes, count):
                if set().union(*combination) >= self.ones_cells:
                    return count

        return len(primes)

    def term_for(self, group):
        minterms = [self.minterm(r, c) for r, c in group]
        term = ""

        for bit in (3, 2, 1, 0):
            values = {(m >> bit) & 1 for m in minterms}

            if values == {1}:
                term += self.VARS[3 - bit]
            elif values == {0}:
                term += self.VARS[3 - bit] + "'"

        return term or "1"

    # ------------------------------------------------------------
    # Puzzle actions
    # ------------------------------------------------------------

    def verify_map(self):
        wrong = sum(
            self.player[r][c] != self.target_value(r, c)
            for r, c in self.all_cells()
        )

        if wrong:
            self.message = (
                f"{wrong} cell(s) are incorrect. "
                "Check the recorded scenes and corrupted footage."
            )
            return

        self.phase = "GROUP"
        self.selected.clear()
        self.message = (
            "Map reconstructed! Select a group and press SPACE to save it."
        )

    def add_group(self):
        if not self.selected:
            self.message = "Select one or more cells first."
            return

        group = frozenset(self.selected)

        if group not in self.all_groups:
            self.message = (
                "Invalid shape. Use a horizontal or vertical group "
                "of 1, 2, 4, 8, or 16 cells."
            )
            return

        if not self.valid_group(group):
            self.message = (
                "Groups may contain 1s and Xs, but never 0s. "
                "Include at least one 1."
            )
            return

        if group in self.groups:
            self.message = "That group has already been saved."
            self.selected.clear()
            return

        # Only the largest possible groups are allowed (simplification rule).
        if group not in self.primes:
            self.message = (
                "This group can be made bigger. Look for the largest "
                "group, using wraparound and Xs."
            )
            self.selected.clear()
            return

        # Groups may overlap.
        self.groups.append(group)
        self.selected.clear()

        self.message = (
            f"Group {len(self.groups)} saved. Groups may overlap. "
            "Cover every 1, then press ENTER to check."
        )

    def check_solution(self):
        if not self.groups:
            self.message = "Save at least one valid group first."
            return

        covered = set().union(*self.groups)

        missing = sorted(
            self.minterm(r, c)
            for r, c in self.ones_cells - covered
        )

        if missing:
            self.message = (
                "Still uncovered: "
                + ", ".join(f"m{m}" for m in missing)
            )
            return

        for index, group in enumerate(self.groups, start=1):
            if not self.valid_group(group) or group not in self.primes:
                self.message = (
                    f"Group {index} is invalid. Remove it and try again."
                )
                return

        # Every 1 is covered, but is the expression fully simplified?
        if len(self.groups) > self.min_cover:
            self.message = (
                "Everything is covered, but it is not simplified. "
                f"Some groups are redundant. Use only {self.min_cover} groups."
            )
            return

        terms = sorted(set(self.term_for(group) for group in self.groups))

        # CHANGED: the level is no longer finished here. Save the
        # simplified expression and move on to the BUILD phase.
        self.final_expr = "F = " + " + ".join(terms)
        self.message = self.final_expr
        self.start_build_phase()

    def reset_attempt(self):
        super().reset_attempt()

        self.phase = "FILL"
        self.player = [[0] * 4 for _ in range(4)]
        self.selected.clear()
        self.groups.clear()

        self.hint_index = 0
        self.message = "Place each recorded scene in its correct K-map cell."

        self.awaiting_return = False
        self.completed = False

        self.last_click_time = 0
        self.last_click_cell = None

        # NEW: fresh build board
        self._init_circuits()

    # ------------------------------------------------------------
    # Mouse and keyboard controls
    # ------------------------------------------------------------

    def handle_event(self, event):
        # NEW: the BUILD phase (keyboard + mouse) is handled by the
        # mixin. It returns False in the other phases and once the
        # circuit is verified (awaiting_return).
        if self.circuit_handle_event(event):
            return

        if self.awaiting_return:
            if (
                event.type == pygame.KEYDOWN
                and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
            ):
                self.completed = True
                self.solved = True
            return

        if self.solved:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, c in self.all_cells():
                rect = self.cell_rect(r, c)

                if not rect.collidepoint(event.pos):
                    continue

                if self.phase == "FILL":
                    # Single click cycles 0 -> 1 -> X -> 0.
                    # Double-click sets X directly.
                    now = pygame.time.get_ticks()
                    clicked_cell = (r, c)

                    is_double_click = (
                        getattr(event, "clicks", 1) >= 2
                        or (
                            self.last_click_cell == clicked_cell
                            and now - self.last_click_time < 350
                        )
                    )

                    if is_double_click:
                        self.player[r][c] = 2
                        self.message = (
                            f"m{self.minterm(r, c)} set to X "
                            "(corrupted footage)."
                        )
                        self.last_click_cell = None
                        self.last_click_time = 0
                    else:
                        self.player[r][c] = (
                            self.player[r][c] + 1
                        ) % 3

                        value_name = ("0", "1", "X")[self.player[r][c]]
                        self.message = (
                            f"m{self.minterm(r, c)} set to {value_name}."
                        )

                        self.last_click_cell = clicked_cell
                        self.last_click_time = now

                else:
                    cell = (r, c)

                    if cell not in (self.ones_cells | self.dc_cells):
                        self.message = (
                            f"m{self.minterm(r, c)} is 0 "
                            "and cannot be grouped."
                        )
                        return

                    if cell in self.selected:
                        self.selected.remove(cell)
                    else:
                        self.selected.add(cell)

                    self.message = (
                        f"{len(self.selected)} cell(s) selected. "
                        "Press SPACE to save the group."
                    )

                return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_h:
            self.message = self.HINTS[
                self.hint_index % len(self.HINTS)
            ]
            self.hint_index += 1

        elif self.phase == "FILL":
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_map()

        else:
            if event.key == pygame.K_SPACE:
                self.add_group()

            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.check_solution()

            elif event.key == pygame.K_BACKSPACE:
                if self.selected:
                    self.selected.clear()
                    self.message = "Selection cleared."
                elif self.groups:
                    self.groups.pop()
                    self.message = "Last saved group removed."

    # ------------------------------------------------------------
    # Responsive drawing helpers
    # ------------------------------------------------------------

    @staticmethod
    def draw_text(
        screen, text, font, color, position,
        center=False, max_width=None
    ):
        """Shrink a line of text to fit its allotted width."""
        current_size = font.get_height()
        current_font = font

        while True:
            image = current_font.render(text, True, color)

            if max_width is None or image.get_width() <= max_width:
                break

            if current_size <= 14:
                break

            current_size -= 1
            current_font = pygame.font.Font(None, current_size)

        rect = image.get_rect()

        if center:
            rect.center = position
        else:
            rect.topleft = position

        screen.blit(image, rect)
        return rect

    @staticmethod
    def fit_font(text, preferred_size, max_width, color=(255, 255, 255)):
        size = preferred_size

        while size > 14:
            font = pygame.font.Font(None, size)

            if font.size(text)[0] <= max_width:
                return font

            size -= 1

        return pygame.font.Font(None, 14)

    def cell_rect(self, r, c):
        return pygame.Rect(
            self.grid_x + c * self.cell_width,
            self.grid_y + r * self.cell_height,
            self.cell_width,
            self.cell_height,
        )

    def draw_centered(self, screen, text, font, color, x, y, max_width):
        return self.draw_text(
            screen,
            text,
            font,
            color,
            (x, y),
            center=True,
            max_width=max_width,
        )

    # ------------------------------------------------------------
    # Draw screen
    # (renamed from draw -> _draw_map; the mixin's draw() picks the
    #  K-map screen or the BUILD screen)
    # ------------------------------------------------------------

    def _draw_map(self, screen):
        screen.fill(settings.BLACK)

        # Shared pixel-art monitor frame.
        panel = draw_pixel_monitor(screen)

        pw, ph = panel.width, panel.height
        margin_x = max(20, int(pw * 0.025))

        content_left = panel.left + margin_x
        content_right = panel.right - margin_x
        content_width = content_right - content_left
        center_x = panel.centerx

        title_size = max(20, min(32, int(pw * 0.024)))
        body_size = max(17, min(24, int(pw * 0.018)))
        small_size = max(15, min(21, int(pw * 0.015)))

        title_font = pygame.font.Font(None, title_size)
        body_font = pygame.font.Font(None, body_size)
        small_font = pygame.font.Font(None, small_size)

        # --------------------------------------------------------
        # Blinking red alert
        # --------------------------------------------------------

        alert_y = panel.top + int(ph * 0.035)
        alert_visible = (pygame.time.get_ticks() // 500) % 2 == 0

        if alert_visible:
            alert_text = "VAULT ALARM PUZZLE // LEVEL FIVE"
            alert_font = self.fit_font(
                alert_text, title_size, content_width - 35
            )

            icon_size = max(10, int(alert_font.get_height() * 0.55))

            icon_rect = pygame.Rect(
                content_left,
                alert_y + max(
                    2,
                    (alert_font.get_height() - icon_size) // 2,
                ),
                icon_size,
                icon_size,
            )

            pygame.draw.rect(screen, settings.RED, icon_rect)

            self.draw_text(
                screen,
                alert_text,
                alert_font,
                settings.RED,
                (icon_rect.right + 12, alert_y),
                max_width=content_width - icon_size - 16,
            )

        # --------------------------------------------------------
        # Static light-blue introduction
        # --------------------------------------------------------

        intro = (
            "EVERY CLUE MATTERS, DETECTIVE. "
            "RECONSTRUCT THE TRUTH AND SIMPLIFY THE LOGIC."
        )

        intro_y = panel.top + int(ph * 0.085)
        intro_font = self.fit_font(intro, body_size, content_width)

        self.draw_centered(
            screen,
            intro,
            intro_font,
            self.LIGHT_BLUE,
            center_x,
            intro_y,
            content_width,
        )

        # --------------------------------------------------------
        # Case file
        # Pink corrupted-footage lines retain their reserved space.
        # --------------------------------------------------------

        case_top = panel.top + int(ph * 0.135)
        case_height = int(ph * 0.325)

        self.case_rect = pygame.Rect(
            content_left,
            case_top,
            content_width,
            case_height,
        )

        pygame.draw.rect(
            screen,
            settings.PANEL_BLUE,
            self.case_rect,
            border_radius=14,
        )

        case_pad = max(16, int(content_width * 0.015))
        case_x = self.case_rect.x + case_pad
        case_inner_width = self.case_rect.width - case_pad * 2

        case_title_y = self.case_rect.y + 10

        self.draw_text(
            screen,
            "CASE FILE:",
            title_font,
            settings.CYAN,
            (case_x, case_title_y),
            max_width=case_inner_width,
        )

        legend = "A = Door | B = Motion | C = Laser | D = Camera"
        legend_y = case_title_y + title_font.get_height() + 5

        self.draw_text(
            screen,
            legend,
            small_font,
            settings.GREY,
            (case_x, legend_y),
            max_width=case_inner_width,
        )

        case_intro = (
            "The vault alarm rang in these scenes. "
            "Take a deep breath and solve it:"
        )
        case_intro_y = legend_y + small_font.get_height() + 5

        self.draw_text(
            screen,
            case_intro,
            small_font,
            settings.WHITE,
            (case_x, case_intro_y),
            max_width=case_inner_width,
        )

        # Reserve the bottom of the case file for both pink lines.
        corrupt_line_height = small_font.get_height()
        corrupt_detail_y = self.case_rect.bottom - corrupt_line_height - 10
        corrupt_heading_y = corrupt_detail_y - corrupt_line_height - 3

        scenes_y = case_intro_y + small_font.get_height() + 6
        scenes_bottom = corrupt_heading_y - 7

        column_gap = max(18, int(case_inner_width * 0.035))
        column_width = (case_inner_width - column_gap) // 2

        row_gap = max(
            18,
            (scenes_bottom - scenes_y - small_font.get_height()) // 4,
        )

        left_scenes = self.EVIDENCE_ORDER[:5]
        right_scenes = self.EVIDENCE_ORDER[5:]

        def draw_scene(minterm, number, x, y, max_width):
            a = (minterm >> 3) & 1
            b = (minterm >> 2) & 1
            c = (minterm >> 1) & 1
            d = minterm & 1

            line = (
                f"{number}. A = {a}, B = {b}, "
                f"C = {c}, D = {d}"
            )

            self.draw_text(
                screen,
                line,
                small_font,
                settings.WHITE,
                (x, y),
                max_width=max_width,
            )

        for i, minterm in enumerate(left_scenes):
            draw_scene(
                minterm,
                i + 1,
                case_x,
                scenes_y + i * row_gap,
                column_width,
            )

        for i, minterm in enumerate(right_scenes):
            draw_scene(
                minterm,
                i + 6,
                case_x + column_width + column_gap,
                scenes_y + i * row_gap,
                column_width,
            )

        # Pink lines stay below the scene list, not on top of it.
        self.draw_text(
            screen,
            "But, there was corrupted footage too:",
            small_font,
            self.PINK,
            (case_x, corrupt_heading_y),
            max_width=case_inner_width,
        )

        self.draw_text(
            screen,
            "A = 1, B = 1, C = 0, D = 0 (X / DON'T-CARE)",
            small_font,
            self.PINK,
            (case_x, corrupt_detail_y),
            max_width=case_inner_width,
        )

        # --------------------------------------------------------
        # K-map heading and instructions
        # --------------------------------------------------------

        map_heading_y = self.case_rect.bottom + int(ph * 0.014)

        self.draw_text(
            screen,
            "RECONSTRUCT THE K-MAP",
            title_font,
            settings.GREEN,
            (content_left, map_heading_y),
            max_width=content_width,
        )

        if self.phase == "FILL":
            instruction = (
                "Place the recorded scenes into the correct cells. "
                "Use X for corrupted footage."
            )
        else:
            instruction = (
                "Select the largest possible groups, then press SPACE "
                "to save each one. Groups may overlap and wrap around."
            )

        instruction_y = map_heading_y + title_font.get_height() + 3
        instruction_font = self.fit_font(
            instruction,
            small_size,
            content_width,
        )

        self.draw_text(
            screen,
            instruction,
            instruction_font,
            settings.YELLOW,
            (content_left, instruction_y),
            max_width=content_width,
        )

        # --------------------------------------------------------
        # Responsive K-map geometry
        # --------------------------------------------------------

        map_area_top = instruction_y + instruction_font.get_height() + 5

        # Reserve room for the status and completion footer.
        footer_reserve = int(ph * 0.17)
        available_bottom = panel.bottom - footer_reserve
        available_map_height = max(130, available_bottom - map_area_top)

        preferred_grid_width = int(content_width * 0.67)
        preferred_grid_height = int(available_map_height * 0.86)

        label_space_left = max(
            30,
            min(48, int(preferred_grid_width * 0.10)),
        )

        label_space_top = max(
            22,
            min(32, int(preferred_grid_height * 0.10)),
        )

        cell_width = min(
            (preferred_grid_width - label_space_left) // 4,
            int((content_width - label_space_left - 20) / 4),
        )

        cell_height = (preferred_grid_height - label_space_top) // 4

        cell_width = max(28, cell_width)
        cell_height = max(25, cell_height)

        max_cell_width = max(
            28,
            (content_width - label_space_left - 20) // 4,
        )

        max_cell_height = max(
            25,
            (available_map_height - label_space_top) // 4,
        )

        self.cell_width = min(cell_width, max_cell_width)

        # Each K-map cell is 2 pixels taller. Width is unchanged.
        # Keep the whole map within its available area.
        self.cell_height = min(cell_height + 2, max_cell_height)

        grid_width = self.cell_width * 4
        grid_height = self.cell_height * 4
        total_width = grid_width + label_space_left

        grid_left = center_x - total_width // 2 + label_space_left
        grid_top = map_area_top + label_space_top

        self.grid_x = grid_left
        self.grid_y = grid_top

        self.map_rect = pygame.Rect(
            grid_left,
            grid_top,
            grid_width,
            grid_height,
        )

        axis_font = self.fit_font(
            "AB\\CD",
            small_size,
            label_space_left,
        )

        self.draw_centered(
            screen,
            "AB\\CD",
            axis_font,
            settings.CYAN,
            grid_left - label_space_left // 2,
            map_area_top + label_space_top // 2,
            label_space_left,
        )

        label_font = pygame.font.Font(
            None,
            max(15, min(22, int(self.cell_width * 0.22))),
        )

        for i, label in enumerate(self.LABELS):
            cx = grid_left + i * self.cell_width + self.cell_width // 2
            cy = grid_top + i * self.cell_height + self.cell_height // 2

            self.draw_centered(
                screen,
                label,
                label_font,
                settings.CYAN,
                cx,
                grid_top - label_space_top // 2,
                self.cell_width,
            )

            self.draw_centered(
                screen,
                label,
                label_font,
                settings.CYAN,
                grid_left - label_space_left // 2,
                cy,
                label_space_left,
            )

        # --------------------------------------------------------
        # Draw K-map cells
        # --------------------------------------------------------

        for r, c in self.all_cells():
            rect = self.cell_rect(r, c)
            minterm = self.minterm(r, c)
            value = self.player[r][c]

            if self.phase == "GROUP" and (r, c) in self.selected:
                fill, ink = settings.CYAN, settings.DARK_BLUE
            elif value == 1:
                fill, ink = self.CELL_ONE, settings.WHITE
            elif value == 2:
                fill, ink = self.CELL_X, settings.WHITE
            else:
                fill, ink = self.CELL_ZERO, settings.WHITE

            pygame.draw.rect(
                screen,
                fill,
                rect,
                border_radius=5,
            )

            pygame.draw.rect(
                screen,
                settings.GREY,
                rect,
                2,
                border_radius=5,
            )

            value_text = ("0", "1", "X")[value]
            cell_font = self.fit_font(
                value_text,
                max(18, int(self.cell_height * 0.42)),
                self.cell_width - 8,
            )

            self.draw_centered(
                screen,
                value_text,
                cell_font,
                ink,
                rect.centerx,
                rect.y + int(rect.height * 0.38),
                rect.width - 8,
            )

            minterm_font = self.fit_font(
                f"m{minterm}",
                max(14, int(self.cell_height * 0.22)),
                rect.width - 6,
            )

            self.draw_centered(
                screen,
                f"m{minterm}",
                minterm_font,
                ink,
                rect.centerx,
                rect.bottom - max(10, int(rect.height * 0.18)),
                rect.width - 6,
            )

        # Saved groups use colored outlines. Insets make overlaps visible.
        for group_index, group in enumerate(self.groups):
            color = self.GROUP_COLORS[
                group_index % len(self.GROUP_COLORS)
            ]
            inset = 5 + (group_index % 4) * 3

            for r, c in group:
                rect = self.cell_rect(r, c).inflate(-inset, -inset)

                pygame.draw.rect(
                    screen,
                    color,
                    rect,
                    width=3,
                    border_radius=5,
                )

        # --------------------------------------------------------
        # Status beneath the map
        # --------------------------------------------------------

        status_y = self.map_rect.bottom + 7

        if self.phase == "FILL":
            status_text = (
                "Single-click: 1 | "
                "Double-click: X | ENTER: Verify the map"
            )
        else:
            status_text = (
                "Click the cells to select | SPACE: Save Groups | "
                "BACKSPACE: Undo Groups | ENTER: Verify the Groups"
            )

        status_font = self.fit_font(
            status_text,
            small_size,
            content_width,
        )

        self.draw_centered(
            screen,
            status_text,
            status_font,
            settings.GREY,
            center_x,
            status_y,
            content_width,
        )

        groups_y = status_y + status_font.get_height() + 4

        if self.phase == "GROUP":
            self.draw_centered(
                screen,
                f"Groups saved: {len(self.groups)}",
                body_font,
                settings.CYAN,
                center_x,
                groups_y,
                content_width,
            )

        # --------------------------------------------------------
        # Feedback footer
        # (the victory screen now lives in the BUILD phase)
        # --------------------------------------------------------

        footer_top = panel.bottom - int(ph * 0.115)

        message_font = self.fit_font(
            self.message,
            small_size,
            content_width,
        )

        message_y = min(
            panel.bottom - 20,
            max(
                groups_y + small_font.get_height() + 4,
                footer_top,
            ),
        )

        self.draw_centered(
            screen,
            self.message,
            message_font,
            settings.YELLOW,
            center_x,
            message_y,
            content_width,
        )