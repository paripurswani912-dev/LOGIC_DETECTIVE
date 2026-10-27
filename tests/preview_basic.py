"""Play a Basic course directly, without walking through the lab or unlocking levels.

    python tests/preview_basic.py gates     Basic Level 1: logic gates from zero
    python tests/preview_basic.py circuits  Basic Level 2: Circuit Lab (add a stage number, e.g. "circuits 7")
    python tests/preview_basic.py kmap      Basic Karnaugh maps
    python tests/preview_basic.py comb      Basic Level 5: combinational circuits
    python tests/preview_basic.py num       Basic Level 3: number systems and codes
    python tests/preview_basic.py seq       Basic Level 6: flip-flops, registers, counters
    python tests/preview_basic.py lab       the notebook lab COMBINATIONAL CIRCUITS (opens at once)

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
from puzzles.basic_circuits import BasicCircuitLabPuzzle
from puzzles.basic_kmap import BasicKarnaughPuzzle
from puzzles.basic_comb import BasicCombinationalPuzzle
from puzzles.basic_seq import BasicSequentialPuzzle
from puzzles.basic_numbers import BasicNumberSystemsPuzzle

COURSES = {"gates": BasicGatesPuzzle, "kmap": BasicKarnaughPuzzle,
           "circuits": BasicCircuitLabPuzzle,
           "comb": BasicCombinationalPuzzle, "lab": BasicCombinationalPuzzle,
           "seq": BasicSequentialPuzzle,
           "num": BasicNumberSystemsPuzzle}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kmap"
    if name not in COURSES:
        print("usage: python tests/preview_basic.py [gates|circuits|num|kmap|comb|seq|lab]")
        return
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.display.set_caption(f"Basic preview: {name}")
    clock = pygame.time.Clock()

    notebook = DetectiveNotebook()
    notebook.set_mode("basic")
    puzzle = COURSES[name](notebook=notebook)
    if name == "circuits" and len(sys.argv) > 2 and sys.argv[2].isdigit():
        # optional stage jump: python tests/preview_basic.py circuits 7
        puzzle.stage = max(1, min(10, int(sys.argv[2]))) - 1
        puzzle.act = 0
        puzzle._load_activity()
    if name == "lab":                      # jump straight into the notebook lab
        notebook.toggle()
        notebook._open_topic("COMBINATIONAL CIRCUITS")

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
