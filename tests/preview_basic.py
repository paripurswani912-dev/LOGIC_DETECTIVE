"""Play a Basic course directly, without walking through the lab or unlocking levels.

    python tests/preview_basic.py gates     Basic Level 1: logic gates from zero
    python tests/preview_basic.py kmap      Basic Karnaugh maps

N opens the notebook (your MY BASIC NOTES fill in as you finish stages).
ESC closes the notebook, or quits when it is closed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame

import settings
from notebook import DetectiveNotebook
from puzzles.basic_gates import BasicGatesPuzzle
from puzzles.basic_kmap import BasicKarnaughPuzzle

COURSES = {"gates": BasicGatesPuzzle, "kmap": BasicKarnaughPuzzle}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kmap"
    if name not in COURSES:
        print("usage: python tests/preview_basic.py [gates|kmap]")
        return
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.display.set_caption(f"Basic preview: {name}")
    clock = pygame.time.Clock()

    notebook = DetectiveNotebook()
    notebook.set_mode("basic")
    puzzle = COURSES[name](notebook=notebook)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                notebook.toggle()
            elif notebook.open:
                notebook.handle_event(event)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                puzzle.handle_event(event)
        if not notebook.open:
            puzzle.update(dt)
        puzzle.draw(screen)
        if notebook.open:
            notebook.draw(screen)
        if puzzle.is_solved():
            font = pygame.font.Font(None, 40)
            msg = font.render("COURSE COMPLETE!  Press ESC to quit.", True, settings.GREEN)
            screen.blit(msg, msg.get_rect(center=(settings.SCREEN_WIDTH // 2, 40)))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
