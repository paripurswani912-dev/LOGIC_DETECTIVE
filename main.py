"""Main game loop for Logic Detective."""
import random
import math
import pygame
import settings
import pygame
import os

from notebook import DetectiveNotebook
from game_state import GameState
from player import Player
from laboratory import Laboratory
from interactions import InteractionManager
from progress import ProgressManager

from puzzles.logic_lock import LogicLockPuzzle
from puzzles.hidden_transmission import HiddenTransmissionPuzzle
from puzzles.memory_protocol import MemoryProtocolPuzzle
from puzzles.final_override import FinalOverridePuzzle
from puzzles.logic_architect import LogicArchitectPuzzle
from puzzles.signal_breaker import SignalBreakerPuzzle



def draw_centered_text(screen, font, text, color, y):
    rendered = font.render(text, True, color)

    screen.blit(
        rendered,
        rendered.get_rect(
            center=(settings.SCREEN_WIDTH // 2, y)
        ),
    )



def draw_title_screen(screen, title_font, normal_font):
    """Draw the pixel-art digital circuit entry screen."""

    import random
    import pygame

    width, height = screen.get_size()

    # ---------------------------------------------------------
    # COLOURS
    # ---------------------------------------------------------
    BACKGROUND = (3, 12, 18)
    CIRCUIT_DARK = (4, 32, 30)
    CIRCUIT_GREEN = (5, 75, 52)
    CIRCUIT_BRIGHT = (8, 125, 72)
    CIRCUIT_LIGHT = (20, 190, 105)
    YELLOW = (255, 211, 65)

    CHIP_DARK = (35, 40, 49)
    CHIP_EDGE = (76, 84, 95)
    PIN_LIGHT = (126, 139, 153)
    PIN_DARK = (48, 58, 72)

    SCREEN_GREY = (158, 169, 181)
    SCREEN_LIGHT = (202, 210, 218)
    SCREEN_SHADOW = (127, 140, 153)
    CONTENT_BG = (7, 20, 27)

    CYAN = (36, 225, 229)
    WHITE = (235, 243, 248)
    MUTED = (179, 197, 207)
    GREEN = (45, 235, 130)

    screen.fill(BACKGROUND)

    # ---------------------------------------------------------
    # PIXEL CIRCUIT-BOARD BACKGROUND
    # ---------------------------------------------------------
    rng = random.Random(29)

    tile = max(7, min(width, height) // 65)
    cols = (width + tile - 1) // tile
    rows = (height + tile - 1) // tile

    for row in range(rows):
        for col in range(cols):
            x = col * tile
            y = row * tile

            shade = rng.random()

            if shade < 0.30:
                colour = CIRCUIT_DARK
            elif shade < 0.53:
                colour = CIRCUIT_GREEN
            elif shade < 0.64:
                colour = CIRCUIT_BRIGHT
            else:
                colour = BACKGROUND

            pygame.draw.rect(
                screen,
                colour,
                (x, y, tile - 1, tile - 1),
            )

            if rng.random() < 0.035:
                pygame.draw.rect(
                    screen,
                    YELLOW,
                    (x, y, tile - 1, tile - 1),
                )

    # ---------------------------------------------------------
    # ANGULAR DIGITAL CIRCUIT TRACES
    # ---------------------------------------------------------
    trace_width = max(2, tile // 3)
    node_size = max(4, tile - 2)
    margin = max(tile, 8)

    def draw_circuit_trace(points, colour, line_width=trace_width):
        if len(points) >= 2:
            pygame.draw.lines(
                screen,
                colour,
                False,
                points,
                line_width,
            )

        for px, py in points:
            pygame.draw.rect(
                screen,
                colour,
                (
                    int(px - node_size // 2),
                    int(py - node_size // 2),
                    node_size,
                    node_size,
                ),
            )

    for side in ("left", "right"):
        trace_count = max(5, height // 105)

        for i in range(trace_count):
            start_y = margin + i * max(
                tile * 4,
                height // max(6, trace_count),
            )
            start_y = min(height - margin, start_y)

            if side == "left":
                start_x = rng.randint(
                    margin,
                    max(margin + 1, width // 6),
                )
                mid_x = min(
                    width // 4,
                    start_x + rng.randint(tile * 2, tile * 6),
                )
                end_x = min(
                    width // 3,
                    mid_x + rng.randint(tile * 2, tile * 4),
                )
            else:
                start_x = rng.randint(
                    width * 5 // 6,
                    width - margin,
                )
                mid_x = max(
                    width * 3 // 4,
                    start_x - rng.randint(tile * 2, tile * 6),
                )
                end_x = max(
                    width * 2 // 3,
                    mid_x - rng.randint(tile * 2, tile * 4),
                )

            bend_y = max(
                margin,
                min(
                    height - margin,
                    start_y
                    + rng.choice([-1, 1])
                    * rng.randint(tile * 2, tile * 5),
                ),
            )

            colour = rng.choice([
                CIRCUIT_GREEN,
                CIRCUIT_BRIGHT,
                CIRCUIT_LIGHT,
            ])

            draw_circuit_trace(
                [
                    (start_x, start_y),
                    (mid_x, start_y),
                    (mid_x, bend_y),
                    (end_x, bend_y),
                ],
                colour,
            )

            if rng.random() < 0.35:
                pygame.draw.rect(
                    screen,
                    YELLOW,
                    (
                        int(end_x - node_size // 2),
                        int(bend_y - node_size // 2),
                        node_size,
                        node_size,
                    ),
                )

    # Short traces near the top and bottom edges.
    for edge_y in (margin, height - margin):
        for _ in range(max(4, width // 250)):
            start_x = rng.randint(
                0,
                max(1, width - tile * 5),
            )
            end_x = min(
                width - 1,
                start_x + rng.randint(tile * 2, tile * 5),
            )
            bend_y = max(
                0,
                min(
                    height - 1,
                    edge_y + rng.choice([-1, 1]) * tile * 2,
                ),
            )

            draw_circuit_trace(
                [
                    (start_x, edge_y),
                    (start_x, bend_y),
                    (end_x, bend_y),
                ],
                rng.choice([
                    CIRCUIT_GREEN,
                    CIRCUIT_BRIGHT,
                ]),
            )

    # ---------------------------------------------------------
    # CENTRAL CPU CHIP
    # ---------------------------------------------------------
    chip_width = min(int(width * 0.65), 970)
    chip_height = min(int(height * 0.72), 710)

    chip_width = min(chip_width, width - 32)
    chip_height = min(chip_height, height - 32)

    chip_width = max(1, chip_width)
    chip_height = max(1, chip_height)

    chip = pygame.Rect(
        (width - chip_width) // 2,
        (height - chip_height) // 2,
        chip_width,
        chip_height,
    )

    # CPU pins around the chip.
    pin_gap = max(9, tile * 2)
    pin_width = max(5, tile - 1)
    pin_length = max(7, tile)

    for x in range(
        chip.left + pin_gap,
        chip.right - pin_gap,
        pin_gap,
    ):
        for pin_y in (
            chip.top - pin_length,
            chip.bottom,
        ):
            pin_rect = pygame.Rect(
                x,
                pin_y,
                pin_width,
                pin_length,
            ).clip(screen.get_rect())

            if pin_rect.width > 0 and pin_rect.height > 0:
                pygame.draw.rect(screen, PIN_DARK, pin_rect)
                pygame.draw.rect(
                    screen,
                    PIN_LIGHT,
                    pin_rect,
                    max(1, tile // 7),
                )

    for y in range(
        chip.top + pin_gap,
        chip.bottom - pin_gap,
        pin_gap,
    ):
        for pin_x in (
            chip.left - pin_length,
            chip.right,
        ):
            pin_rect = pygame.Rect(
                pin_x,
                y,
                pin_length,
                pin_width,
            ).clip(screen.get_rect())

            if pin_rect.width > 0 and pin_rect.height > 0:
                pygame.draw.rect(screen, PIN_DARK, pin_rect)
                pygame.draw.rect(
                    screen,
                    PIN_LIGHT,
                    pin_rect,
                    max(1, tile // 7),
                )

    # Outer chip frame.
    outer = chip.inflate(10, 10).clip(screen.get_rect())
    pygame.draw.rect(screen, PIN_DARK, outer)

    pygame.draw.rect(screen, CHIP_EDGE, chip)

    step = max(7, tile + 2)
    pygame.draw.rect(
        screen,
        CHIP_DARK,
        chip.inflate(-step, -step),
    )

    # Enlarged pixel corners for a clearer CPU-chip silhouette.
    corner_size = max(14, tile * 2)

    for sx in (chip.left, chip.right - corner_size):
        for sy in (chip.top, chip.bottom - corner_size):
            corner = pygame.Rect(
                sx,
                sy,
                corner_size,
                corner_size,
            ).clip(screen.get_rect())

            pygame.draw.rect(screen, CHIP_EDGE, corner)

            inner_corner = corner.inflate(
                -max(3, tile // 2),
                -max(3, tile // 2),
            )

            if inner_corner.width > 0 and inner_corner.height > 0:
                pygame.draw.rect(
                    screen,
                    CHIP_DARK,
                    inner_corner,
                )

    # Main body of the chip.
    body_rect = chip.inflate(-step * 2, -step * 2)
    pygame.draw.rect(screen, CHIP_DARK, body_rect)

    # ---------------------------------------------------------
    # GREY PIXEL DISPLAY FRAME
    # ---------------------------------------------------------
    inset = max(14, tile * 2)
    display = body_rect.inflate(-inset * 2, -inset * 2)

    pygame.draw.rect(screen, SCREEN_GREY, display)
    pygame.draw.rect(
        screen,
        SCREEN_LIGHT,
        display,
        max(3, tile // 2),
    )

    frame_inset = max(6, tile)
    inner_frame = display.inflate(
        -frame_inset * 2,
        -frame_inset * 2,
    )
    pygame.draw.rect(screen, SCREEN_SHADOW, inner_frame)

    inner_inset = max(6, tile)
    content = inner_frame.inflate(
        -inner_inset * 2,
        -inner_inset * 2,
    )
    pygame.draw.rect(screen, CONTENT_BG, content)

    pygame.draw.rect(
        screen,
        (35, 52, 65),
        content,
        max(1, tile // 5),
    )

    # ---------------------------------------------------------
    # TEXT LAYOUT HELPERS
    # ---------------------------------------------------------
    def fit_font(text, max_width, start_size, min_size=10, bold=True):
        size = max(min_size, start_size)

        while size > min_size:
            candidate = pygame.font.SysFont(
                "consolas",
                size,
                bold=bold,
            )

            if candidate.size(text)[0] <= max_width:
                return candidate

            size -= 1

        return pygame.font.SysFont(
            "consolas",
            min_size,
            bold=bold,
        )

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = word if not current else current + " " + word

            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)

                # Break very long words safely if necessary.
                if font.size(word)[0] > max_width:
                    partial = ""

                    for character in word:
                        candidate = partial + character

                        if font.size(candidate)[0] <= max_width:
                            partial = candidate
                        else:
                            if partial:
                                lines.append(partial)
                            partial = character

                    current = partial
                else:
                    current = word

        if current:
            lines.append(current)

        return lines

    def draw_centered(text, font, colour, center_x, center_y, clip_rect):
        image = font.render(text, True, colour)
        rect = image.get_rect(
            center=(int(center_x), int(center_y)),
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        screen.blit(image, rect)
        screen.set_clip(old_clip)

    # ---------------------------------------------------------
    # ENTRY TEXT
    # ---------------------------------------------------------
    max_text_width = max(
        1,
        content.width - max(24, tile * 5),
    )

    welcome = "Welcome to the"
    title = "LOGIC DETECTIVE: A Digital Escape Room"

    description = (
        "NEXUS-9 has sealed the research facility shut. "
        "Can you be the detective to solve the complex puzzles "
        "and make an escape?"
    )

    instruction = "If yes, then press ENTER to begin."

    welcome_font = fit_font(
        welcome,
        max_text_width,
        max(16, int(height * 0.038)),
        11,
    )

    title_font_fitted = fit_font(
        title,
        max_text_width,
        max(18, int(height * 0.043)),
        11,
    )

    body_font = pygame.font.SysFont(
        "consolas",
        max(10, min(21, int(height * 0.024))),
        bold=True,
    )

    instruction_font = fit_font(
        instruction,
        max_text_width,
        max(12, int(height * 0.026)),
        10,
    )

    description_lines = wrap_text(
        description,
        body_font,
        max_text_width,
    )

    # ---------------------------------------------------------
    # VERTICALLY CENTER THE COMPLETE TEXT BLOCK
    # ---------------------------------------------------------
    # Measure the complete block first, then center the block
    # inside the grey display instead of anchoring it at the top.
    gap_small = max(7, int(content.height * 0.025))
    gap_large = max(12, int(content.height * 0.045))
    line_gap = max(2, tile // 3)

    def measure_text_block():
        description_line_height = body_font.get_linesize() + line_gap

        return (
            welcome_font.get_linesize()
            + gap_small
            + title_font_fitted.get_linesize()
            + gap_large
            + len(description_lines) * description_line_height
            + gap_large
            + instruction_font.get_linesize()
        )

    # Shrink fonts if the complete block is too tall.
    available_height = max(1, content.height - max(20, tile * 4))

    while measure_text_block() > available_height:
        if (
            welcome_font.get_height() <= 10
            and title_font_fitted.get_height() <= 10
            and body_font.get_height() <= 10
            and instruction_font.get_height() <= 10
        ):
            break

        welcome_font = pygame.font.SysFont(
            "consolas",
            max(10, welcome_font.get_height() - 1),
            bold=True,
        )

        title_font_fitted = fit_font(
            title,
            max_text_width,
            max(10, title_font_fitted.get_height() - 1),
            10,
        )

        body_font = pygame.font.SysFont(
            "consolas",
            max(10, body_font.get_height() - 1),
            bold=True,
        )

        instruction_font = pygame.font.SysFont(
            "consolas",
            max(10, instruction_font.get_height() - 1),
            bold=True,
        )

        description_lines = wrap_text(
            description,
            body_font,
            max_text_width,
        )

        gap_small = max(4, gap_small - 1)
        gap_large = max(5, gap_large - 1)
        line_gap = max(1, line_gap - 1)

    block_height = measure_text_block()

    # The whole group is centered vertically in the content box.
    y = content.centery - block_height // 2
    center_x = content.centerx

    draw_centered(
        welcome,
        welcome_font,
        CYAN,
        center_x,
        y + welcome_font.get_linesize() // 2,
        content,
    )
    y += welcome_font.get_linesize() + gap_small

    draw_centered(
        title,
        title_font_fitted,
        WHITE,
        center_x,
        y + title_font_fitted.get_linesize() // 2,
        content,
    )
    y += title_font_fitted.get_linesize() + gap_large

    description_line_height = body_font.get_linesize() + line_gap

    for line in description_lines:
        draw_centered(
            line,
            body_font,
            MUTED,
            center_x,
            y + body_font.get_linesize() // 2,
            content,
        )
        y += description_line_height

    y += gap_large

    draw_centered(
        instruction,
        instruction_font,
        GREEN,
        center_x,
        y + instruction_font.get_linesize() // 2,
        content,
    )


def draw_spotlight(screen, player, radius=70):
    """Soft, warm spotlight that follows the detective."""

    px, py = player.rect.center

    # 1. Gently darken the environment without hiding floor details.
    darkness = pygame.Surface(
        screen.get_size(),
        pygame.SRCALPHA,
    )
    darkness.fill((0, 0, 0, 100))
    screen.blit(darkness, (0, 0))

    # 2. Create a soft-edged light gradient.
    light = pygame.Surface(
        (radius * 2, radius * 2),
        pygame.SRCALPHA,
    )

    for r in range(radius, 0, -2):
        # Strongest in the centre, fading smoothly at the edges.
        distance = r / radius
        alpha = int(45 * (1 - distance) ** 2)

        if alpha > 0:
            pygame.draw.circle(
                light,
                (110, 110, 80, alpha),
                (radius, radius),
                r,
            )

    # 3. Blend the warm light over the existing floor.
    screen.blit(
        light,
        (px - radius, py - radius),
        special_flags=pygame.BLEND_RGBA_ADD,
    )





def draw_laboratory_screen(
    screen,
    laboratory,
    player,
    interaction_manager,
    progress,
    font,
    game_state,
):
    """Render the laboratory without changing puzzle interactions."""

    completed_puzzles = progress.completed_puzzles

    # Draw the laboratory environment.
    laboratory.draw(screen, completed_puzzles)

    # Apply lighting over the floor and environment.
    draw_spotlight(screen, player)

    # Keep the detective crisp and visible.
    player.draw(screen)

    # Draw nearby interaction prompt.
    nearby = interaction_manager.find_nearby_object(
        player,
        laboratory.get_interactable_objects(),
        completed_puzzles,
    )

    interaction_manager.draw_prompt(screen, nearby)

    # Compact HUD panel.
    hud = pygame.Rect(14, 12, 350, 64)

    pygame.draw.rect(
        screen,
        (5, 13, 22),
        hud,
        border_radius=4,
    )

    pygame.draw.rect(
        screen,
        (41, 73, 91),
        hud,
        2,
        border_radius=4,
    )

    # First line: restored systems count.
    progress_text = (
        f"SYSTEMS RESTORED: "
        f"{progress.get_completed_count()}/"
        f"{len(progress.puzzle_order)}"
    )

    progress_font = pygame.font.SysFont(
        "consolas", 15, bold=True
    )

    progress_surface = progress_font.render(
        progress_text,
        False,
        settings.WHITE,
    )

    screen.blit(
        progress_surface,
        (24, 20),
    )

    # Second line: instruction.
    if game_state.status_message:
        instruction_font = pygame.font.SysFont(
            "consolas", 11, bold=True
        )

        message = instruction_font.render(
            game_state.status_message,
            False,
            settings.YELLOW,
        )

        # Keep the instruction within the smaller panel.
        available_width = hud.width - 20

        if message.get_width() > available_width:
            instruction_font = pygame.font.SysFont(
                "consolas", 9, bold=True
            )

            message = instruction_font.render(
                game_state.status_message,
                False,
                settings.YELLOW,
            )

        screen.blit(
            message,
            (24, 44),
        )


def draw_ending_screen(screen, title_font, normal_font, fireworks):
    """Draw the final celebration over a dark screen."""

    screen.fill((3, 5, 12))

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    for particle in fireworks:
        x, y = int(particle["x"]), int(particle["y"])
        color = particle["color"]
        radius = particle["radius"]

        pygame.draw.circle(
            screen,
            color,
            (x, y),
            radius,
        )

    message = "Congratulations, Detective!"
    subtitle = "You have made it out of the laboratory..."

    draw_centered_text(
        screen,
        title_font,
        message,
        (45, 230, 120),
        settings.SCREEN_HEIGHT // 2 - 35,
    )

    draw_centered_text(
        screen,
        normal_font,
        subtitle,
        settings.WHITE,
        settings.SCREEN_HEIGHT // 2 + 20,
    )


def create_firework(fireworks, screen_width, screen_height):
    """Create one burst of colourful fireworks particles."""

    center_x = random.randint(
        screen_width // 6,
        screen_width * 5 // 6,
    )
    center_y = random.randint(
        screen_height // 6,
        screen_height // 2,
    )

    colors = [
        (255, 70, 90),
        (0, 220, 255),
        (255, 195, 50),
        (80, 255, 140),
        (210, 100, 255),
        (255, 255, 255),
    ]

    color = random.choice(colors)

    for _ in range(45):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.0, 4.0)

        fireworks.append({
            "x": float(center_x),
            "y": float(center_y),
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": random.randint(35, 65),
            "color": color,
            "radius": random.randint(2, 4),
        })


def update_fireworks(fireworks):
    """Move particles and remove expired ones."""

    for particle in fireworks[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] += 0.035
        particle["life"] -= 1

        if particle["life"] <= 0:
            fireworks.remove(particle)


def main():
    pygame.init()
    notebook = DetectiveNotebook()
    screen = pygame.display.set_mode(
        (
            settings.SCREEN_WIDTH,
            settings.SCREEN_HEIGHT,
        )
    )

    pygame.display.set_caption(settings.GAME_TITLE)

    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 54)
    normal_font = pygame.font.Font(None, 27)
    small_font = pygame.font.Font(None, 22)

    game_state = GameState()
    laboratory = Laboratory()
    interaction_manager = InteractionManager()
    progress = ProgressManager()

    player = Player(485, 295)

    active_puzzle_id = None
    running = True

    fireworks = []
    firework_timer = 0

    while running:
        dt = min(
            clock.tick(settings.FPS) / 1000.0,
            0.05,
        )

        for event in pygame.event.get():

            # Always allow the window to close, even while the notebook is open.
            if event.type == pygame.QUIT:
                running = False
                continue

            # N toggles the notebook in the title screen, laboratory,
            # puzzle rooms, and ending screen.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                notebook.toggle()
                continue

            # While the notebook is open, it consumes the remaining events
            # so controls do not activate the game underneath it.
            if notebook.open:
                notebook.handle_event(event)
                continue

            mode = game_state.current_mode

            if mode == GameState.TITLE:
                if (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_RETURN
                ):
                    game_state.change_mode(GameState.LABORATORY)
                    game_state.set_status(
                        "Explore the laboratory. Find the first terminal."
                    )
                continue

            if mode == GameState.LABORATORY:
                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_ESCAPE:
                    game_state.change_mode(GameState.TITLE)
                    continue

                if event.key != pygame.K_e:
                    continue

                nearby = interaction_manager.find_nearby_object(
                    player,
                    laboratory.get_interactable_objects(),
                    progress.completed_puzzles,
                )

                if nearby is None:
                    continue

                result = interaction_manager.handle_event(
                    event,
                    player,
                    game_state,
                )

                if result is None:
                    continue

                object_type, object_id = result

                if object_type == "puzzle":
                    if not progress.is_unlocked(object_id):
                        game_state.set_status(
                            "Locked! Complete the previous puzzle first."
                        )
                        continue

                    if progress.is_completed(object_id):
                        game_state.set_status(
                            "You have already completed this puzzle."
                        )
                        continue

                    puzzle_classes = {
                        "logic_lock": LogicLockPuzzle,
                        "hidden_transmission": HiddenTransmissionPuzzle,
                        "memory_protocol": MemoryProtocolPuzzle,
                        "final_override": FinalOverridePuzzle,
                        "logic_architect": LogicArchitectPuzzle,
                        "signal_breaker": SignalBreakerPuzzle,
                    }

                    puzzle_class = puzzle_classes.get(object_id)

                    if puzzle_class is None:
                        game_state.set_status(
                            "This puzzle is not implemented yet."
                        )
                        continue

                    active_puzzle_id = object_id
                    game_state.open_puzzle(puzzle_class())

                elif object_type == "door" and object_id == "exit":
                    if progress.is_game_completed():
                        game_state.change_mode(GameState.ENDING)
                    else:
                        game_state.set_status(
                            f"The exit is locked. Solve all "
                            f"{len(progress.puzzle_order)} puzzles first."
                        )

                continue

            if mode == GameState.PUZZLE:
                if (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                ):
                    game_state.close_puzzle()
                    active_puzzle_id = None
                    continue

                puzzle = game_state.active_puzzle

                if puzzle is None:
                    game_state.close_puzzle()
                    active_puzzle_id = None
                    continue

                if event.type == pygame.KEYDOWN:
                    puzzle.handle_event(event)
                elif event.type in (
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                    pygame.MOUSEMOTION,
                ):
                    puzzle.handle_event(event)

                if puzzle.is_solved():
                    completed_id = active_puzzle_id

                    if (
                        completed_id is not None
                        and progress.complete_puzzle(completed_id)
                    ):
                        next_index = (
                            progress.puzzle_order.index(completed_id) + 1
                        )

                        if next_index < len(progress.puzzle_order):
                            next_name = (
                                progress.puzzle_order[next_index]
                                .replace("_", " ")
                                .title()
                            )
                            game_state.set_status(
                                f"{completed_id.replace('_', ' ').title()} "
                                f"solved! {next_name} unlocked."
                            )
                        else:
                            game_state.set_status(
                                "All six puzzles solved! The exit is unlocked."
                            )

                    game_state.close_puzzle()
                    active_puzzle_id = None

                continue

            if mode == GameState.ENDING:
                if (
                    event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_RETURN, pygame.K_ESCAPE)
                ):
                    running = False

        if game_state.current_mode == GameState.LABORATORY:
            player.handle_movement(
                pygame.key.get_pressed(),
                dt,
                laboratory.get_obstacles(progress.completed_puzzles),
            )

            if progress.is_game_completed():
                exit_door = next(
                    (
                        door for door in laboratory.doors
                        if door["id"] == "exit"
                    ),
                    None,
                )

                if (
                    exit_door is not None
                    and player.rect.colliderect(exit_door["rect"])
                ):
                    game_state.change_mode(GameState.ENDING)
                    fireworks.clear()
                    firework_timer = 0

        if game_state.current_mode == GameState.TITLE:
            draw_title_screen(screen, title_font, normal_font)
        elif game_state.current_mode == GameState.LABORATORY:
            draw_laboratory_screen(
                screen,
                laboratory,
                player,
                interaction_manager,
                progress,
                small_font,
                game_state,
            )
        elif game_state.current_mode == GameState.PUZZLE:
            if game_state.active_puzzle is not None:
                game_state.active_puzzle.update(dt)
                game_state.active_puzzle.draw(screen)
        elif game_state.current_mode == GameState.ENDING:
            # Keep launching firework bursts throughout the celebration.
            firework_timer += 1

            if firework_timer >= 18:
                create_firework(
                    fireworks,
                    settings.SCREEN_WIDTH,
                    settings.SCREEN_HEIGHT,
                )
                firework_timer = 0

            update_fireworks(fireworks)

            draw_ending_screen(
                screen,
                title_font,
                normal_font,
                fireworks,
            )

        # Draw the notebook AFTER the current game scene so its translucent
        # overlay and page appear in every game mode, not only at the ending.
        if notebook.open:
            notebook.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()