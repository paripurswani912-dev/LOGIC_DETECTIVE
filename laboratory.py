"""NEXUS-9 laboratory environment.

Preserves the interfaces used by InteractionManager and main.py.
"""

import math
import random
import pygame
import settings


class Laboratory:
    def __init__(self):
        self.walls = self._create_walls()

        # Preserve the terminal dictionary structure used by the backend.
        # Positions are adapted to the six-room layout.
        self.terminals = [
            {
                "id": "logic_lock",
                "name": "Logic Lock",
                "rect": pygame.Rect(179, 100, 78, 52),
                "puzzle_id": "logic_lock",
                "required_puzzle": None,
            },
            {
                "id": "hidden_transmission",
                "name": "Hidden Transmission",
                "rect": pygame.Rect(744, 100, 78, 52),
                "puzzle_id": "hidden_transmission",
                "required_puzzle": "logic_lock",
            },
            {
                "id": "memory_protocol",
                "name": "Memory Protocol",
                "rect": pygame.Rect(179, 295, 78, 52),
                "puzzle_id": "memory_protocol",
                "required_puzzle": "hidden_transmission",
            },
            {
                "id": "final_override",
                "name": "Final Override",
                "rect": pygame.Rect(744, 295, 78, 52),
                "puzzle_id": "final_override",
                "required_puzzle": "memory_protocol",
            },
            {
                "id": "logic_architect",
                "name": "Logic Architect",
                "rect": pygame.Rect(179, 485, 78, 52),
                "puzzle_id": "logic_architect",
                "required_puzzle": "final_override",
            },
            {
                "id": "signal_breaker",
                "name": "Signal Breaker",
                "rect": pygame.Rect(744, 485, 78, 52),
                "puzzle_id": "signal_breaker",
                "required_puzzle": "logic_architect",
            },
        ]

        self.doors = [
            {
                "id": "exit",
                "name": "Laboratory Exit",
                "rect": pygame.Rect(450, 20, 100, 28),
                "required_puzzle": "signal_breaker",
            }
        ]

        # The level labels intentionally show numbers only.
        self.level_positions = [
            (218, 190),
            (783, 190),
            (218, 385),
            (783, 385),
            (218, 575),
            (783, 575),
        ]
    

        self.label_font = pygame.font.Font(None, 24)
        self.status_font = pygame.font.Font(None, 17)
        self.level_font = pygame.font.Font(None, 25)
        self.door_font = pygame.font.Font(None, 25)
        self.hint_font = pygame.font.Font(None, 20)

        self.elapsed_time = 0.0

        # Six room rectangles.
        self.rooms = [
            pygame.Rect(30, 55, 375, 155),
            pygame.Rect(595, 55, 375, 155),
            pygame.Rect(30, 250, 375, 155),
            pygame.Rect(595, 250, 375, 155),
            pygame.Rect(30, 440, 375, 165),
            pygame.Rect(595, 440, 375, 165),
        ]

    def _create_walls(self):
        """Create the outer boundary and room partitions.

        The central corridor and room entrances remain open.
        """

        width = settings.SCREEN_WIDTH
        height = settings.SCREEN_HEIGHT
        wall = 18

        walls = [
            # Outer boundaries.
            pygame.Rect(0, 0, 430, wall),
            pygame.Rect(570, 0, width - 570, wall),
            pygame.Rect(0, 0, wall, height),
            pygame.Rect(width - wall, 0, wall, height),
            pygame.Rect(0, height - wall, width, wall),

            # Upper room dividers, with openings facing the corridor.
            pygame.Rect(18, 205, 385, wall),
            pygame.Rect(597, 205, 385, wall),

            # Middle room dividers, with openings facing the corridor.
            pygame.Rect(18, 400, 385, wall),
            pygame.Rect(597, 400, 385, wall),

            # Short vertical wall sections between rooms and corridor.
            # Openings are left for movement into the rooms.
            pygame.Rect(390, 55, 15, 65),
            pygame.Rect(390, 170, 15, 35),
            pygame.Rect(390, 225, 15, 45),
            pygame.Rect(390, 350, 15, 50),
            pygame.Rect(390, 420, 15, 45),
            pygame.Rect(390, 560, 15, 45),

            pygame.Rect(595, 55, 15, 65),
            pygame.Rect(595, 170, 15, 35),
            pygame.Rect(595, 225, 15, 45),
            pygame.Rect(595, 350, 15, 50),
            pygame.Rect(595, 420, 15, 45),
            pygame.Rect(595, 560, 15, 45),
        ]

        return walls

    def draw(self, screen, completed_puzzles=None):
        """Draw the laboratory background and interactive terminals."""

        if completed_puzzles is None:
            completed_puzzles = set()

        self.elapsed_time += 1 / max(settings.FPS, 1)

        screen.fill((5, 11, 19))

        self._draw_floor(screen)
        self._draw_corridor(screen)
        self._draw_rooms(screen)
        self._draw_equipment(screen)
        self._draw_floor_clutter(screen)
        self._draw_walls(screen)
        self._draw_terminals(screen, completed_puzzles)
        self._draw_exit(screen, completed_puzzles)

    def _draw_worn_floor(self, screen, area):
        """Draw a continuous, worn pixel-art floor in any rectangular area."""

        pygame.draw.rect(screen, (25, 34, 42), area)

        tile_size = 32

        # Tile seams.
        for x in range(
            (area.left // tile_size) * tile_size,
            area.right,
            tile_size,
        ):
            pygame.draw.line(
                screen,
                (38, 48, 55),
                (x, area.top),
                (x, area.bottom),
                1,
            )

        for y in range(
            (area.top // tile_size) * tile_size,
            area.bottom,
            tile_size,
        ):
            pygame.draw.line(
                screen,
                (38, 48, 55),
                (area.left, y),
                (area.right, y),
                1,
            )

        # Repeatable pixel chips, worn edges, and dark grime.
        # The pattern is anchored to world coordinates so it aligns
        # across adjacent floor sections.
        for row in range(area.top // tile_size, area.bottom // tile_size + 1):
            for col in range(area.left // tile_size, area.right // tile_size + 1):
                seed = (col * 37 + row * 61) % 101

                if seed < 34:
                    continue

                x = col * tile_size + 4 + (seed % 17)
                y = row * tile_size + 5 + ((seed * 3) % 17)

                chip_w = 3 + seed % 9
                chip_h = 2 + seed % 4

                chip = pygame.Rect(x, y, chip_w, chip_h)
                chip.clip_ip(area)

                if chip.width > 0 and chip.height > 0:
                    color = (
                        (13, 21, 27)
                        if seed % 2
                        else (19, 27, 32)
                    )

                    pygame.draw.rect(screen, color, chip)

                    # A tiny broken, lighter tile edge.
                    if chip.width > 4:
                        pygame.draw.rect(
                            screen,
                            (43, 47, 46),
                            (chip.x, chip.y, chip.width - 2, 1),
                        )

    def _draw_floor(self, screen):
        """Render a clustered pixel-art floor for an abandoned laboratory."""

        import random

        # Low-resolution texture: each source pixel becomes a crisp pixel cluster.
        scale = 3
        width = settings.SCREEN_WIDTH // scale
        height = settings.SCREEN_HEIGHT // scale

        rng = random.Random(42)

        floor = pygame.Surface((width, height))
        floor.fill((27, 35, 42))

        # Pixel-art palette.
        base_colors = [
            (31, 40, 47),
            (35, 43, 49),
            (28, 37, 44),
            (39, 46, 51),
            (33, 41, 47),
        ]

        dark = (16, 23, 29)
        deep_crack = (11, 17, 22)
        grime = (22, 27, 30)
        worn = (49, 55, 58)
        exposed_metal = (58, 64, 66)

        # --------------------------------------------------
        # 1. BUILD INDIVIDUAL METAL FLOOR TILES
        # --------------------------------------------------

        tile_size = 32 // scale

        for ty in range(0, height, tile_size):
            for tx in range(0, width, tile_size):

                tw = min(tile_size, width - tx)
                th = min(tile_size, height - ty)

                color = rng.choice(base_colors)

                pygame.draw.rect(
                    floor,
                    color,
                    (tx, ty, tw, th),
                )

                # Slightly brighter top edge and dark lower edge.
                pygame.draw.line(
                    floor,
                    (45, 52, 57),
                    (tx, ty),
                    (tx + tw - 1, ty),
                )

                pygame.draw.line(
                    floor,
                    dark,
                    (tx, ty + th - 1),
                    (tx + tw - 1, ty + th - 1),
                )

                # Uneven patches across each tile.
                for _ in range(rng.randint(3, 7)):
                    px = tx + rng.randrange(max(1, tw))
                    py = ty + rng.randrange(max(1, th))

                    patch_w = rng.randint(1, 4)
                    patch_h = rng.randint(1, 3)

                    patch_color = rng.choice([
                        (24, 31, 37),
                        (29, 36, 41),
                        (42, 47, 50),
                        (36, 42, 46),
                    ])

                    pygame.draw.rect(
                        floor,
                        patch_color,
                        (px, py, patch_w, patch_h),
                    )

        # --------------------------------------------------
        # 2. JAGGED CRACKS
        # --------------------------------------------------

        # Coordinates are in the final 1000 x 650 screen space.
        cracks = [
            [(90, 95), (99, 105), (96, 116), (106, 124)],
            [(270, 145), (261, 154), (266, 164), (254, 172)],
            [(345, 90), (336, 101), (342, 111)],
            [(695, 130), (706, 139), (700, 151), (710, 159)],
            [(820, 200), (809, 209), (813, 220)],
            [(160, 325), (170, 333), (164, 345), (175, 351)],
            [(345, 390), (335, 399), (341, 409)],
            [(685, 430), (675, 440), (682, 450), (672, 459)],
            [(850, 490), (840, 500), (845, 510)],
            [(245, 540), (254, 549), (248, 559)],
            [(440, 290), (450, 300), (443, 311)],
            [(555, 565), (546, 574), (551, 585)],
            [(925, 335), (914, 344), (920, 354)],
        ]

        def scaled_points(points):
            return [
                (int(x / scale), int(y / scale))
                for x, y in points
            ]

        for points in cracks:
            pixel_points = scaled_points(points)

            # Deep shadow.
            pygame.draw.lines(
                floor,
                deep_crack,
                False,
                pixel_points,
                2,
            )

            # Uneven worn edge beside the crack.
            highlight_points = [
                (x + 1, y - 1)
                for x, y in pixel_points
            ]

            pygame.draw.lines(
                floor,
                worn,
                False,
                highlight_points,
                1,
            )

            # Break up the crack with dark pixel clusters.
            for x, y in pixel_points:
                pygame.draw.rect(
                    floor,
                    deep_crack,
                    (x - 1, y, 2, 2),
                )

        # --------------------------------------------------
        # 3. IRREGULAR GRIME AND OIL STAIN CLUSTERS
        # --------------------------------------------------

        for _ in range(115):
            cx = rng.randrange(width)
            cy = rng.randrange(height)

            cluster_w = rng.randint(2, 8)
            cluster_h = rng.randint(1, 5)

            # Each cluster is built from overlapping rectangles,
            # creating uneven pixel-art shapes rather than circles.
            for _ in range(rng.randint(3, 8)):
                px = cx + rng.randint(-cluster_w, cluster_w)
                py = cy + rng.randint(-cluster_h, cluster_h)

                pw = rng.randint(1, 4)
                ph = rng.randint(1, 3)

                pygame.draw.rect(
                    floor,
                    rng.choice([
                        grime,
                        grime,
                        dark,
                        (25, 30, 33),
                        (31, 34, 36),
                    ]),
                    (px, py, pw, ph),
                )

        # --------------------------------------------------
        # 4. CHIPPED METAL EDGES AND SCRATCHES
        # --------------------------------------------------

        for _ in range(85):
            x = rng.randrange(width)
            y = rng.randrange(height)

            length = rng.randint(2, 6)

            color = rng.choice([
                worn,
                exposed_metal,
                dark,
            ])

            # Horizontal and stepped scratches.
            pygame.draw.line(
                floor,
                color,
                (x, y),
                (min(width - 1, x + length), y + rng.choice([-1, 0, 1])),
                1,
            )

            if rng.random() < 0.4:
                pygame.draw.rect(
                    floor,
                    color,
                    (x, min(height - 1, y + 1), 2, 1),
                )

        # --------------------------------------------------
        # 5. SCALE UP WITHOUT BLURRING PIXELS
        # --------------------------------------------------

        texture = pygame.transform.scale(
            floor,
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
        )

        screen.blit(texture, (0, 0))

        # --------------------------------------------------
        # 6. SUBTLE FLOOR EDGE SHADOW
        # --------------------------------------------------

        # Preserve the darker perimeter of the abandoned facility.
        pygame.draw.rect(
            screen,
            (13, 20, 26),
            pygame.Rect(
                18,
                18,
                settings.SCREEN_WIDTH - 36,
                settings.SCREEN_HEIGHT - 36,
            ),
            3,
        )

    
    def _draw_corridor(self, screen):
        """Draw a worn, chipped pixel-art corridor floor."""

        import random

        corridor = pygame.Rect(
            405, 18, 190, settings.SCREEN_HEIGHT - 36
        )

        # Dark, aged metal base.
        pygame.draw.rect(screen, (25, 34, 42), corridor)

        # Keep the existing corridor grid.
        tile_size = 32
        grid_color = (38, 48, 55)

        for x in range(405, 595, tile_size):
            pygame.draw.line(
                screen, grid_color,
                (x, 18), (x, settings.SCREEN_HEIGHT - 18), 1
            )

        for y in range(18, settings.SCREEN_HEIGHT - 18, tile_size):
            pygame.draw.line(
                screen, grid_color,
                (405, y), (595, y), 1
            )

        # Fixed random seed keeps the texture consistent every frame.
        rng = random.Random(91)

        # 1. Dark grime patches and chipped tile surfaces.
        for _ in range(170):
            x = rng.randint(corridor.left + 3, corridor.right - 5)
            y = rng.randint(corridor.top + 3, corridor.bottom - 5)

            width = rng.randint(2, 11)
            height = rng.randint(1, 5)

            chip = pygame.Rect(x, y, width, height)
            chip = chip.clip(corridor)

            color = rng.choice([
                (13, 21, 27),
                (17, 24, 29),
                (20, 28, 33),
                (31, 38, 41),
            ])

            pygame.draw.rect(screen, color, chip)

            # Small exposed, worn-metal edge.
            if width >= 5 and rng.random() < 0.45:
                pygame.draw.line(
                    screen,
                    (48, 53, 54),
                    (chip.left, chip.top),
                    (min(chip.right - 1, chip.left + width - 3), chip.top),
                    1,
                )

        # 2. Broken seams and irregular cracks.
        cracks = [
            [(425, 75), (433, 82), (429, 91), (438, 97)],
            [(555, 115), (546, 122), (551, 131)],
            [(450, 175), (460, 183), (454, 192)],
            [(530, 220), (521, 228), (527, 237), (519, 244)],
            [(435, 275), (444, 282), (439, 291)],
            [(565, 345), (555, 352), (560, 361)],
            [(470, 405), (462, 414), (469, 422)],
            [(540, 465), (531, 473), (536, 482)],
            [(425, 535), (435, 542), (429, 551)],
            [(505, 590), (496, 598), (502, 607)],
        ]

        for points in cracks:
            # Dark crack shadow.
            pygame.draw.lines(
                screen, (9, 15, 19), False, points, 3
            )

            # Thin worn edge makes the damage visible.
            worn_points = [
                (x + 2, y - 1) for x, y in points
            ]
            pygame.draw.lines(
                screen, (48, 53, 54), False, worn_points, 1
            )

        # 3. Scratches across the old metal.
        for _ in range(65):
            x = rng.randint(corridor.left + 4, corridor.right - 8)
            y = rng.randint(corridor.top + 4, corridor.bottom - 4)
            length = rng.randint(3, 13)

            color = rng.choice([
                (43, 49, 52),
                (50, 54, 55),
                (15, 22, 27),
            ])

            pygame.draw.line(
                screen,
                color,
                (x, y),
                (min(x + length, corridor.right - 2),
                 y + rng.choice([-1, 0, 1])),
                1,
            )

        # 4. Extra chipped corners on selected tiles.
        for x, y in [
            (408, 48), (470, 102), (552, 185),
            (416, 245), (486, 330), (560, 390),
            (440, 450), (515, 520), (570, 635),
        ]:
            pygame.draw.rect(
                screen, (11, 18, 23), (x, y, 8, 5)
            )
            pygame.draw.rect(
                screen, (42, 47, 49), (x + 2, y + 1, 4, 1)
            )

        # Preserve the corridor's existing boundary.
        pygame.draw.line(
            screen, (14, 22, 29),
            (corridor.left, corridor.top),
            (corridor.left, corridor.bottom), 3
        )
        pygame.draw.line(
            screen, (14, 22, 29),
            (corridor.right - 1, corridor.top),
            (corridor.right - 1, corridor.bottom), 3
        )


    
    def _draw_rooms(self, screen):
        """Draw room borders and brighter amber lights."""

        for index, room in enumerate(self.rooms):
            pygame.draw.rect(screen, (47, 65, 77), room, 2)

            pygame.draw.line(
                screen,
                (12, 21, 29),
                (room.left + 3, room.bottom - 4),
                (room.right - 3, room.bottom - 4),
                3,
            )

            light_x = room.centerx
            light_y = room.top + 18

            # Light housing.
            pygame.draw.rect(
                screen,
                (83, 59, 35),
                (light_x - 19, light_y - 4, 38, 9),
            )

            # Warm glow, drawn behind the light source.
            glow = pygame.Surface((48, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(
                glow, (255, 155, 45, 24), (0, 2, 48, 20)
            )
            pygame.draw.ellipse(
                glow, (255, 180, 70, 38), (8, 5, 32, 14)
            )
            screen.blit(
                glow, (light_x - 24, light_y - 12)
            )

            # Bright amber core.
            pygame.draw.rect(
                screen,
                (255, 174, 75),
                (light_x - 13, light_y - 1, 26, 3),
            )
            pygame.draw.rect(
                screen,
                (255, 230, 165),
                (light_x - 7, light_y - 1, 14, 3),
            )


        
    def _draw_floor_clutter(self, screen):
        """Draw scattered papers, cables and abandoned lab debris."""

        import random
        rng = random.Random(24)

        # Muted colors that suit the existing dark environment.
        paper_colors = [
            (113, 108, 89),
            (137, 128, 103),
            (91, 94, 88),
            (123, 119, 104),
        ]
        ink_colors = [(49, 57, 59), (65, 72, 69)]
        cable_colors = [
            (65, 29, 26),
            (24, 31, 37),
            (91, 42, 30),
        ]

        # Each paper is a small polygon, not a new floor tile.
        papers = [
            (85, 110, 18, 13),
            (330, 155, 20, 14),
            (285, 230, 16, 12),
            (350, 330, 21, 15),
            (80, 365, 18, 13),
            (325, 475, 20, 15),
            (95, 550, 17, 12),
            (350, 570, 22, 15),

            (635, 110, 19, 13),
            (850, 155, 21, 14),
            (930, 235, 18, 12),
            (650, 330, 20, 14),
            (865, 375, 17, 13),
            (635, 480, 21, 15),
            (930, 545, 19, 13),
            (660, 570, 18, 12),
        ]

        for x, y, w, h in papers:
            # Slightly irregular paper shape.
            points = [
                (x, y + 2),
                (x + w - 3, y),
                (x + w, y + h - 3),
                (x + 4, y + h),
            ]

            paper_color = rng.choice(paper_colors)
            pygame.draw.polygon(screen, (8, 13, 17), [
                (px + 2, py + 2) for px, py in points
            ])
            pygame.draw.polygon(screen, paper_color, points)
            pygame.draw.polygon(screen, (63, 68, 64), points, 1)

            # Tiny printed text/notes.
            for line in range(2):
                line_y = y + 4 + line * 4
                pygame.draw.line(
                    screen,
                    rng.choice(ink_colors),
                    (x + 4, line_y),
                    (x + rng.randint(8, max(9, w - 3)), line_y),
                    1,
                )

        # Small abandoned folders/files.
        files = [
            (110, 245), (350, 110), (85, 470),
            (330, 535), (650, 245), (900, 315),
            (865, 470), (640, 535),
        ]

        for x, y in files:
            # Folder tab.
            pygame.draw.rect(
                screen, (93, 65, 44),
                (x + 3, y, 9, 4)
            )
            pygame.draw.rect(
                screen, (69, 55, 43),
                (x, y + 3, 24, 15)
            )
            pygame.draw.rect(
                screen, (119, 91, 61),
                (x, y + 3, 24, 15), 1
            )
            pygame.draw.line(
                screen, (46, 43, 37),
                (x + 4, y + 8), (x + 19, y + 8), 1
            )
            pygame.draw.line(
                screen, (46, 43, 37),
                (x + 4, y + 12), (x + 15, y + 12), 1
            )

        # Loose cables running near room edges.
        cables = [
            [(40, 95), (48, 95), (48, 120), (58, 120)],
            [(345, 185), (360, 185), (360, 200), (380, 200)],
            [(40, 300), (52, 300), (52, 325), (65, 325)],
            [(345, 375), (360, 375), (360, 390), (380, 390)],
            [(40, 490), (53, 490), (53, 515), (67, 515)],
            [(345, 575), (359, 575), (359, 590), (380, 590)],

            [(620, 95), (635, 95), (635, 120), (648, 120)],
            [(930, 185), (945, 185), (945, 205), (960, 205)],
            [(620, 300), (635, 300), (635, 325), (648, 325)],
            [(930, 375), (946, 375), (946, 390), (960, 390)],
            [(620, 490), (635, 490), (635, 515), (650, 515)],
            [(930, 575), (945, 575), (945, 590), (960, 590)],
        ]

        for points in cables:
            color = rng.choice(cable_colors)

            # Dark cable shadow.
            shadow_points = [(x + 2, y + 2) for x, y in points]
            pygame.draw.lines(
                screen, (7, 12, 16), False, shadow_points, 5
            )

            # Main cable with angular pixel-art bends.
            pygame.draw.lines(
                screen, color, False, points, 3
            )

            # Small connector at the end.
            end_x, end_y = points[-1]
            pygame.draw.rect(
                screen, (89, 91, 82),
                (end_x - 2, end_y - 2, 5, 5)
            )

        # A few tiny pieces of scattered metal debris.
        debris = [
            (125, 175), (365, 250), (285, 360),
            (115, 430), (370, 525), (275, 580),
            (675, 175), (900, 225), (680, 430),
            (850, 525), (700, 585), (935, 350),
        ]

        for x, y in debris:
            pygame.draw.rect(
                screen, (12, 18, 22),
                (x, y, 7, 4)
            )
            pygame.draw.rect(
                screen, (64, 68, 65),
                (x + 1, y, 4, 1)
            )


    def _draw_equipment(self, screen):
        """Draw simple cabinets, stools, cables, and laboratory equipment."""

        for index, room in enumerate(self.rooms):
            # Cabinet near the outer wall.
            cabinet = pygame.Rect(
                room.left + 18,
                room.top + 42,
                30,
                52,
            )

            pygame.draw.rect(screen, (27, 43, 57), cabinet)
            pygame.draw.rect(screen, (65, 83, 96), cabinet, 2)

            for offset in (12, 25, 38):
                pygame.draw.line(
                    screen,
                    (123, 95, 58),
                    (cabinet.left + 5, cabinet.top + offset),
                    (cabinet.right - 5, cabinet.top + offset),
                    2,
                )

            # Small stool on the opposite side of each room.
            stool_x = room.right - 58
            stool_y = room.top + 90

            pygame.draw.ellipse(
                screen,
                (4, 9, 14),
                (stool_x - 13, stool_y - 13, 26, 26),
            )

            pygame.draw.ellipse(
                screen,
                (55, 67, 77),
                (stool_x - 11, stool_y - 11, 22, 22),
                2,
            )

            pygame.draw.line(
                screen,
                (49, 60, 70),
                (stool_x - 7, stool_y + 7),
                (stool_x - 10, stool_y + 18),
                3,
            )

            pygame.draw.line(
                screen,
                (49, 60, 70),
                (stool_x + 7, stool_y + 7),
                (stool_x + 10, stool_y + 18),
                3,
            )

            # A small equipment box.
            box = pygame.Rect(
                room.right - 43,
                room.top + 34,
                25,
                24,
            )

            pygame.draw.rect(screen, (47, 43, 40), box)
            pygame.draw.rect(screen, (91, 78, 65), box, 2)

            # Tiny status LED.
            led_color = (54, 220, 145) if index % 2 == 0 else (255, 158, 53)

            pygame.draw.rect(
                screen,
                led_color,
                (box.left + 5, box.top + 5, 4, 4),
            )


    def _draw_level_label(self, screen, index, room, unlocked, active):
        # Small pixel font; use an installed pixel font if available.
        font = pygame.font.SysFont("consolas", 13, bold=True)

        color = (20, 190, 198) if unlocked else (91, 105, 119)

        bob = (
            round(math.sin(self.elapsed_time * 2.5) * 2)
            if active else 0
        )

        label = f"LEVEL {index + 1}"
        label_surface = font.render(label, False, color)

        # Lock icon is drawn directly to avoid extra floating rectangles.
        icon_w, icon_h = 9, 9
        gap = 5
        total_w = icon_w + gap + label_surface.get_width()
        start_x = room.centerx - total_w // 2
        label_y = room.bottom - 44 + bob
        icon_x = start_x
        icon_y = label_y + 2

        # Pixel-art shackle.
        if unlocked:
            pygame.draw.line(
                screen, color,
                (icon_x + 3, icon_y + 3),
                (icon_x + 3, icon_y), 1
            )
            pygame.draw.line(
                screen, color,
                (icon_x + 3, icon_y),
                (icon_x + 7, icon_y), 1
            )
            pygame.draw.line(
                screen, color,
                (icon_x + 7, icon_y),
                (icon_x + 7, icon_y + 3), 1
            )
        else:
            pygame.draw.rect(
                screen, color,
                (icon_x + 2, icon_y, 5, 5), 1
            )

        pygame.draw.rect(
            screen, color,
            (icon_x, icon_y + 3, icon_w, 6), 1
        )

        screen.blit(
            label_surface,
            (start_x + icon_w + gap, label_y)
        )

        status = "AVAILABLE" if unlocked else "LOCKED"
        status_surface = font.render(status, False, color)

        screen.blit(
            status_surface,
            (
                room.centerx - status_surface.get_width() // 2,
                room.bottom - 23
            )
        )


    def _draw_walls(self, screen):
        """Draw chunky metallic walls."""

        for wall in self.walls:
            pygame.draw.rect(
                screen,
                (4, 9, 15),
                wall.move(0, 4),
            )

            pygame.draw.rect(
                screen,
                (29, 48, 65),
                wall,
            )

            pygame.draw.line(
                screen,
                (71, 93, 111),
                wall.topleft,
                wall.topright,
                2,
            )

            pygame.draw.rect(
                screen,
                (11, 20, 30),
                wall,
                1,
            )
            
            # Close the narrow gaps beside the exit with the existing wall style.
        wall_color = (14, 27, 38)
        wall_edge = (24, 40, 51)

        for wall_rect in (
            pygame.Rect(385, 18, 20, 38),
            pygame.Rect(595, 18, 20, 38),
            pygame.Rect(385, 610, 20, 28),
            pygame.Rect(595, 610, 20, 28),
        ):
            pygame.draw.rect(screen, wall_color, wall_rect)
            pygame.draw.rect(screen, wall_edge, wall_rect, 2)

    

    
    def _draw_terminals(self, screen, completed_puzzles):
        """Draw computer consoles with aligned pixel-style level labels."""

        level_font = pygame.font.SysFont("consolas", 12, bold=True)
        status_font = pygame.font.SysFont("consolas", 9, bold=True)

        for index, terminal in enumerate(self.terminals):
            puzzle_id = terminal["puzzle_id"]
            required = terminal["required_puzzle"]

            solved = puzzle_id in completed_puzzles
            unlocked = required is None or required in completed_puzzles

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

            # Pixel-art monitor casing with a slight top-down 3D effect.
            case = rect.inflate(10, 10)
            shadow = case.move(3, 4)
            pygame.draw.rect(screen, (4, 7, 11), shadow)
            pygame.draw.rect(screen, (24, 37, 49), case)
            pygame.draw.rect(screen, (70, 88, 101), case, 2)

            # Highlight and dark lower bezel.
            pygame.draw.line(
                screen, (104, 121, 130),
                (case.left + 3, case.top + 2),
                (case.right - 4, case.top + 2), 2
            )
            pygame.draw.line(
                screen, (9, 16, 23),
                (case.left + 3, case.bottom - 3),
                (case.right - 3, case.bottom - 3), 3
            )

            # Small casing screws.
            for sx in (case.left + 4, case.right - 4):
                pygame.draw.rect(
                    screen, (119, 132, 137),
                    (sx - 1, case.top + 4, 2, 2)
                )
                pygame.draw.rect(
                    screen, (119, 132, 137),
                    (sx - 1, case.bottom - 5, 2, 2)
                )

            # Screen.
            pygame.draw.rect(
                screen, (3, 15, 23), rect, border_radius=2
            )
            pygame.draw.rect(
                screen, color, rect, 2, border_radius=2
            )

            # Puzzle symbol.
            if index == 0:
                self._draw_logic_symbol(screen, rect, color)
            elif index == 1:
                self._draw_transmission_symbol(screen, rect, color)
            elif index == 2:
                self._draw_network_symbol(screen, rect, color)
            elif index == 3:
                self._draw_alarm_symbol(screen, rect, color)
            elif index == 4:
                self._draw_kmap_symbol(screen, rect, color)
            else:
                self._draw_signal_symbol(screen, rect, color)

            # Monitor power light.
            pygame.draw.rect(
                screen, color,
                (rect.left + 5, rect.bottom - 4, 5, 2)
            )

            # Monitor stand and base.
            cx = rect.centerx
            pygame.draw.rect(
                screen, (35, 48, 59),
                (cx - 3, rect.bottom + 2, 6, 4)
            )
            pygame.draw.rect(
                screen, (48, 62, 74),
                (cx - 11, rect.bottom + 5, 22, 3)
            )
            pygame.draw.line(
                screen, (17, 27, 36),
                (cx - 8, rect.bottom + 7),
                (cx + 8, rect.bottom + 7), 1
            )

            # Room-based placement keeps labels away from dividers.
            room = self.rooms[index]

            # Only the next unsolved, unlocked level bounces.
            active = unlocked and not solved
            bob = (
                round(math.sin(self.elapsed_time * 2.5) * 2)
                if active else 0
            )

            label_y = room.bottom - 43 + bob
            status_y = room.bottom - 20

            # Render label and icon as one centered group.
            label_surface = level_font.render(
                f"LEVEL {index + 1}", False, color
            )

            icon_width = 11
            gap = 4
            total_width = icon_width + gap + label_surface.get_width()
            start_x = room.centerx - total_width // 2
            icon_x = start_x
            icon_y = label_y + 1

            # Pixel-style lock/unlock symbol.
            if unlocked:
                # Open shackle.
                pygame.draw.line(
                    screen, color,
                    (icon_x + 3, icon_y + 6),
                    (icon_x + 3, icon_y + 2), 1
                )
                pygame.draw.line(
                    screen, color,
                    (icon_x + 3, icon_y + 2),
                    (icon_x + 7, icon_y + 2), 1
                )
                pygame.draw.line(
                    screen, color,
                    (icon_x + 7, icon_y + 2),
                    (icon_x + 7, icon_y + 4), 1
                )
            else:
                # Closed shackle.
                pygame.draw.rect(
                    screen, color,
                    (icon_x + 3, icon_y + 1, 5, 6), 1
                )

            # Lock body and keyhole.
            pygame.draw.rect(
                screen, color,
                (icon_x + 1, icon_y + 5, 9, 7), 1
            )
            screen.set_at((icon_x + 5, icon_y + 8), color)

            # Level text beside the lock.
            screen.blit(
                label_surface,
                (start_x + icon_width + gap, label_y)
            )

            # Status stays centered within its own room.
            status_surface = status_font.render(
                status_text, False, color
            )
            screen.blit(
                status_surface,
                status_surface.get_rect(
                    center=(room.centerx, status_y)
                )
            )



    def _draw_logic_symbol(self, screen, rect, color):
        x = rect.x + 15
        y = rect.y + 15

        pygame.draw.line(
            screen, color, (x, y), (x + 12, y), 2
        )
        pygame.draw.line(
            screen, color, (x, y + 10), (x + 12, y + 10), 2
        )
        pygame.draw.line(
            screen, color, (x + 12, y), (x + 12, y + 10), 2
        )

        pygame.draw.line(
            screen, color, (x + 12, y + 5), (x + 24, y + 5), 2
        )

    def _draw_transmission_symbol(self, screen, rect, color):
        x = rect.x + 10
        y = rect.y + 12

        for index, bit in enumerate("10110"):
            text = self.status_font.render(bit, True, color)
            screen.blit(text, (x + index * 11, y))

    def _draw_network_symbol(self, screen, rect, color):
        points = [
            (rect.x + 16, rect.y + 12),
            (rect.x + 48, rect.y + 14),
            (rect.x + 29, rect.y + 36),
        ]

        pygame.draw.line(screen, color, points[0], points[1], 2)
        pygame.draw.line(screen, color, points[1], points[2], 2)
        pygame.draw.line(screen, color, points[2], points[0], 2)

        for point in points:
            pygame.draw.circle(screen, color, point, 3)

    def _draw_alarm_symbol(self, screen, rect, color):
        points = [
            (rect.centerx, rect.y + 8),
            (rect.x + 12, rect.bottom - 9),
            (rect.right - 12, rect.bottom - 9),
        ]

        pygame.draw.polygon(screen, color, points, 2)

        pygame.draw.line(
            screen,
            color,
            (rect.centerx, rect.y + 17),
            (rect.centerx, rect.y + 27),
            2,
        )

        pygame.draw.circle(
            screen,
            color,
            (rect.centerx, rect.y + 32),
            1,
        )

    def _draw_kmap_symbol(self, screen, rect, color):
        grid = pygame.Rect(
            rect.x + 12,
            rect.y + 10,
            rect.width - 24,
            rect.height - 20,
        )

        pygame.draw.rect(screen, color, grid, 1)

        for x in range(1, 4):
            px = grid.x + grid.width * x // 4
            pygame.draw.line(
                screen, color, (px, grid.y), (px, grid.bottom), 1
            )

        for y in range(1, 3):
            py = grid.y + grid.height * y // 3
            pygame.draw.line(
                screen, color, (grid.x, py), (grid.right, py), 1
            )

    def _draw_signal_symbol(self, screen, rect, color):
        x = rect.x + 10
        y = rect.centery

        for index in range(5):
            bit_rect = pygame.Rect(
                x + index * 11,
                y - 7,
                8,
                14,
            )

            pygame.draw.rect(screen, color, bit_rect, 1)

            if index % 2 == 0:
                pygame.draw.rect(
                    screen,
                    color,
                    bit_rect.inflate(-4, -8),
                )

    def _draw_exit(self, screen, completed_puzzles):
        """Draw the top-center exit gate."""

        door = self.doors[0]
        unlocked = door["required_puzzle"] in completed_puzzles

        color = (
            settings.UNLOCKED_DOOR_COLOR
            if unlocked
            else settings.LOCKED_DOOR_COLOR
        )

        frame = pygame.Rect(430, 18, 140, 55)

        pygame.draw.rect(screen, (4, 8, 14), frame.inflate(8, 8))
        pygame.draw.rect(screen, (36, 49, 63), frame)
        pygame.draw.rect(screen, color, frame, 3)

        # Two door panels.
        pygame.draw.rect(
            screen,
            (27, 38, 49),
            (435, 44, 62, 24),
            border_radius=2,
        )

        pygame.draw.rect(
            screen,
            (27, 38, 49),
            (503, 44, 62, 24),
            border_radius=2,
        )

        # Hazard stripes.
        for index in range(8):
            x = 438 + index * 16

            pygame.draw.line(
                screen,
                (255, 165, 49),
                (x, 68),
                (x + 8, 60),
                3,
            )

        exit_text = self.door_font.render(
            "EXIT",
            True,
            (255, 88, 45),
        )

        screen.blit(
            exit_text,
            exit_text.get_rect(center=(500, 32)),
        )

    def get_obstacles(self, completed_puzzles=None):
        """Return collision rectangles for the player."""

        if completed_puzzles is None:
            completed_puzzles = set()

        obstacles = list(self.walls)

        for door in self.doors:
            if door["required_puzzle"] not in completed_puzzles:
                obstacles.append(door["rect"])

        return obstacles

    def get_interactable_objects(self):
        """Return the existing terminal and door objects."""

        return self.terminals + self.doors

    def get_nearby_interactable(self, player, completed_puzzles=None):
        """Find the nearest unlocked object within interaction distance."""

        if completed_puzzles is None:
            completed_puzzles = set()

        player_center = pygame.Vector2(player.rect.center)

        nearby_object = None
        closest_distance = float("inf")

        for obj in self.get_interactable_objects():
            required = obj.get("required_puzzle")

            if required and required not in completed_puzzles:
                continue

            distance = player_center.distance_to(
                pygame.Vector2(obj["rect"].center)
            )

            if (
                distance <= settings.INTERACTION_DISTANCE
                and distance < closest_distance
            ):
                nearby_object = obj
                closest_distance = distance

        return nearby_object

    def is_area_unlocked(self, area_id, completed_puzzles):
        """Preserve the existing area-unlock interface."""

        for obj in self.get_interactable_objects():
            if obj["id"] == area_id:
                required = obj.get("required_puzzle")

                return (
                    required is None
                    or required in completed_puzzles
                )

        return False

    def update_door_states(self, completed_puzzles):
        """Return the unlock state of every door."""

        return {
            door["id"]: (
                door["required_puzzle"] in completed_puzzles
            )
            for door in self.doors
        }