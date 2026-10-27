"""Basic Level 2 (Circuit Lab) headless checks: notebook wiring, notes and stage jumps.
Run:  python tests/test_basic_circuits.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pygame
import settings
from notebook import DetectiveNotebook
from puzzles.basic_circuits import BasicCircuitLabPuzzle, STAGES


def main():
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    nb = DetectiveNotebook()
    nb.set_mode("basic")

    # scientist notes, goal, hints and findings exist for the BASIC Level 2
    assert nb.SCIENTIST_NOTES["level_two"][0].startswith("Lab log: Entry 02 (beginner copy)")
    assert "circuit" in nb.LEVEL_GOALS["level_two"].lower()
    assert len(nb.LEVEL_HINTS["level_two"]) >= 3
    assert nb.LEVEL_PRACTICE["level_two"] == "BOOLEAN ALGEBRA"
    nb.set_mode("intermediate")                      # intermediate path is untouched
    assert "BINARY" in " ".join(nb.SCIENTIST_NOTES["level_two"])
    nb.set_mode("basic")

    puz = BasicCircuitLabPuzzle(notebook=nb)
    assert len(STAGES) == 10 and not puz.is_solved()
    for stage in range(10):                          # every stage loads and draws
        puz.stage, puz.act, puz.mode = stage, 0, "ACTIVITY"
        puz._load_activity()
        puz.draw(screen)

    # finishing stages feeds the shared MY BASIC NOTES sheet, in course order
    puz._save_notes(0); puz._save_notes(1); puz._save_sheet()
    sheet = nb.reference_notes["MY BASIC NOTES"]
    assert any("STAGE 1" in line for line in sheet)
    assert any("STAGE 2" in line for line in sheet)
    assert any("REVISION SHEET" in line for line in sheet)

    # standalone use (no add_basic_note) still works
    class Bare:
        reference_notes, reference_topics = {}, []
    bare = BasicCircuitLabPuzzle(notebook=Bare())
    bare._save_notes(0)
    assert "CIRCUIT LAB NOTES" in Bare.reference_notes
    print("basic circuits OK")


if __name__ == "__main__":
    main()
