
# main.py
# Main game loop for Logic Detective.

import pygame
import settings

from game_state import GameState
from player import Player
from laboratory import Laboratory
from interactions import InteractionManager
from progress import ProgressManager
from puzzles.logic_lock import LogicLockPuzzle
from puzzles.hidden_transmission import HiddenTransmissionPuzzle
from puzzles.memory_protocol import MemoryProtocolPuzzle
from puzzles.final_override import FinalOverridePuzzle
def draw_centered_text(screen, font, text, color, y):
    """Draw text centered horizontally."""

    rendered = font.render(text, True, color)
    screen.blit(
        rendered,
        rendered.get_rect(
            center=(settings.SCREEN_WIDTH // 2, y)
        ),
    )


def draw_title_screen(screen, title_font, normal_font):
    """Draw the opening title screen."""

    screen.fill(settings.BLACK)

    draw_centered_text(
        screen, title_font, "LOGIC DETECTIVE",
        settings.CYAN, 210
    )
    draw_centered_text(
        screen, normal_font, "THE DIGITAL ESCAPE ROOM",
        settings.WHITE, 265
    )
    draw_centered_text(
        screen, normal_font,
        "NEXUS-9 has sealed the research facility.",
        settings.GREY, 340
    )
    draw_centered_text(
        screen, normal_font,
        "Investigate the laboratory. Solve the logic puzzles.",
        settings.GREY, 375
    )
    draw_centered_text(
        screen, normal_font, "Press ENTER to begin",
        settings.GREEN, 455
    )


def draw_laboratory_screen(
    screen, laboratory, player, interaction_manager,
    progress, font, game_state
):
    """Draw the laboratory, player, interaction prompt, and progress."""

    completed_puzzles = progress.completed_puzzles

    laboratory.draw(screen, completed_puzzles)
    player.draw(screen)

    nearby = interaction_manager.find_nearby_object(
        player,
        laboratory.get_interactable_objects(),
        completed_puzzles,
    )

    interaction_manager.draw_prompt(screen, nearby)

    progress_text = (
        f"Puzzles solved: {progress.get_completed_count()}/4"
    )
    rendered = font.render(
        progress_text, True, settings.WHITE
    )
    screen.blit(rendered, (30, 30))

    if game_state.status_message:
        message = font.render(
            game_state.status_message,
            True,
            settings.YELLOW,
        )
        screen.blit(message, (30, 58))


def draw_ending_screen(screen, title_font, normal_font):
    """Draw the temporary ending screen."""

    screen.fill(settings.BLACK)

    draw_centered_text(
        screen, title_font, "FACILITY EXIT REACHED",
        settings.GREEN, 260
    )
    draw_centered_text(
        screen, normal_font,
        "The story ending will be added later.",
        settings.WHITE, 320
    )
    draw_centered_text(
        screen, normal_font,
        "Press ENTER or ESC to quit",
        settings.YELLOW, 400
    )


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
    )
    pygame.display.set_caption(settings.GAME_TITLE)

    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 54)
    normal_font = pygame.font.Font(None, 27)
    small_font = pygame.font.Font(None, 25)

    game_state = GameState()
    laboratory = Laboratory()
    interaction_manager = InteractionManager()
    progress = ProgressManager()

    player = Player(485, 295)

    # Track which level is currently open.
    active_puzzle_id = None

    running = True

    while running:
        dt = min(clock.tick(settings.FPS) / 1000.0, 0.05)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type != pygame.KEYDOWN:
                continue

            # TITLE SCREEN
            if game_state.current_mode == GameState.TITLE:
                if event.key == pygame.K_RETURN:
                    game_state.change_mode(GameState.LABORATORY)
                    game_state.set_status(
                        "Explore the laboratory. Find the first terminal."
                    )

            # LABORATORY
            elif game_state.current_mode == GameState.LABORATORY:

                if event.key == pygame.K_ESCAPE:
                    game_state.change_mode(GameState.TITLE)

                elif event.key == pygame.K_e:
                    # Refresh the nearby object when interacting.
                    nearby = interaction_manager.find_nearby_object(
                        player,
                        laboratory.get_interactable_objects(),
                        progress.completed_puzzles,
                    )

                    if nearby is None:
                        continue

                    result = interaction_manager.handle_event(
                        event, player, game_state
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

                        if object_id == "logic_lock":
                            puzzle = LogicLockPuzzle()

                        elif object_id == "hidden_transmission":
                            puzzle = HiddenTransmissionPuzzle()

                        elif object_id == "memory_protocol":
                            puzzle = MemoryProtocolPuzzle()

                        elif object_id == "final_override":
                            puzzle = FinalOverridePuzzle()
                        else:
                            game_state.set_status(
                                "This puzzle is still under development."
                            )
                            continue

                        active_puzzle_id = object_id
                        game_state.open_puzzle(puzzle)

                    elif object_type == "door":
                        if object_id == "exit":
                            if progress.is_game_completed():
                                game_state.change_mode(GameState.ENDING)
                            else:
                                game_state.set_status(
                                    "The exit is locked. Solve all four puzzles."
                                )

            # PUZZLE SCREEN
            elif game_state.current_mode == GameState.PUZZLE:

                if event.key == pygame.K_ESCAPE:
                    game_state.close_puzzle()
                    active_puzzle_id = None
                    continue

                puzzle = game_state.active_puzzle

                if puzzle is None:
                    game_state.close_puzzle()
                    active_puzzle_id = None
                    continue

                puzzle.handle_event(event)

                if puzzle.is_solved():
                    completed_id = active_puzzle_id

                    if (
                        completed_id is not None
                        and progress.complete_puzzle(completed_id)
                    ):
                        if completed_id == "logic_lock":
                            game_state.set_status(
                                "Logic Lock solved! Hidden Transmission unlocked."
                            )
                        elif completed_id == "hidden_transmission":
                            game_state.set_status(
                                "Hidden Transmission solved! Memory Protocol unlocked."
                            )
                        elif completed_id == "memory_protocol":
                            game_state.set_status(
                                "Memory Protocol solved! Final Override unlocked."
                            )
                    game_state.close_puzzle()
                    active_puzzle_id = None

            # ENDING SCREEN
            elif game_state.current_mode == GameState.ENDING:
                if event.key in (
                    pygame.K_RETURN,
                    pygame.K_ESCAPE,
                ):
                    running = False

        # PLAYER MOVEMENT
        if game_state.current_mode == GameState.LABORATORY:
            keys = pygame.key.get_pressed()

            player.handle_movement(
                keys,
                dt,
                laboratory.get_obstacles(
                    progress.completed_puzzles
                ),
            )

        # DRAW CURRENT SCREEN
        if game_state.current_mode == GameState.TITLE:
            draw_title_screen(
                screen, title_font, normal_font
            )

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
            draw_ending_screen(
                screen, title_font, normal_font
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
