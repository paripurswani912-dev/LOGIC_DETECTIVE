"""Headless playthrough test for Basic Level 1.

Run from the project folder:
    python tests/test_basic_gates.py
Screenshots are written to tests/basic_shots/ so you can eyeball every stage.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import settings  # noqa: E402
from puzzles.basic_gates import BasicGatesPuzzle, gate_out, outputs_for, rows_for  # noqa: E402
from notebook import DetectiveNotebook  # noqa: E402

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "basic_shots")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


def shot(puz, screen, name):
    puz.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, name + ".png"))


def solve_step(puz, screen, stage_no, step_no):
    """Answer the current step correctly, using only keyboard/mouse events."""
    step, st = puz.step, puz.st
    kind = step["kind"]
    puz.draw(screen)                      # registers clickable buttons

    if kind == "bulbs":
        for i, (x, y) in enumerate(zip(st["bulbs"], step["target"])):
            if x != y:
                puz.handle_event(key(pygame.K_1 + i))
    elif kind == "read_bits":
        for b in step["pattern"]:
            puz.handle_event(key(pygame.K_0 + b))
    elif kind == "explore":
        gate = step["gate"]
        seq = [("a", 1)] if gate == "NOT" else [("b", 1), ("a", 1), ("b", 1)]
        for who, _ in seq:
            puz.handle_event(key(pygame.K_a if who == "a" else pygame.K_b))
    elif kind == "combine":
        puz.handle_event(key(pygame.K_t))            # AND + NOT
        puz.handle_event(key(pygame.K_2))            # OR (NOT stays on)
    elif kind == "table":
        want = outputs_for(step["gate"])
        for v in want:
            puz.handle_event(key(pygame.K_0 + v))
    elif kind == "choice":
        opts = step["options"]
        if all(isinstance(v, int) for _l, v in opts):
            puz.handle_event(key(pygame.K_0 + step["correct"]))
        else:
            idx = [v for _l, v in opts].index(step["correct"])
            puz.handle_event(key(pygame.K_1 + idx))
    if stage_no in (1, 3, 4, 7, 8) and step_no in (0, 1, 2):
        shot(puz, screen, f"stage{stage_no}_step{step_no + 1}_{kind}")
    puz.handle_event(key(pygame.K_RETURN))


def main():
    os.makedirs(SHOTS, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))

    nb = DetectiveNotebook()
    nb.set_mode("basic")
    puz = BasicGatesPuzzle(notebook=nb)

    # ---- tiered hints + wrong-answer behaviour on stage 1 ----
    puz.draw(screen)
    assert puz.st["tier"] == 0
    puz.handle_event(key(pygame.K_h))
    assert puz.st["tier"] == 1
    puz.handle_event(key(pygame.K_h))
    puz.handle_event(key(pygame.K_h))
    puz.handle_event(key(pygame.K_h))
    assert puz.st["tier"] == 3, "tier must stop at 3"
    shot(puz, screen, "hint_tier3")
    puz._enter_step()
    for _ in range(3):
        puz.handle_event(key(pygame.K_RETURN))          # 3 wrong checks
    assert puz.st["wrong"] == 3 and puz.st["tier"] == 3, "3 wrong tries reveal answer"

    # ---- leave and come back keeps progress (same object) ----
    puz.handle_event(key(pygame.K_1))
    # ---- play every stage ----
    puz._enter_step()
    for stage_no in range(1, 9):
        assert puz.stage_i == stage_no - 1, (puz.stage_i, stage_no)
        n_steps = len(puz.stage["steps"])
        for step_no in range(n_steps):
            assert puz.phase == "play"
            solve_step(puz, screen, stage_no, step_no)
        assert puz.phase == "done", f"stage {stage_no} should show the summary card"
        shot(puz, screen, f"stage{stage_no}_done")
        assert puz.stage["id"] in puz.saved_stages
        puz.handle_event(key(pygame.K_RETURN))

    assert puz.is_solved(), "level should be solved after stage 8"

    # ---- notebook autofill ----
    notes = nb.reference_notes["MY BASIC NOTES"]
    text = "\n".join(notes)
    for needle in ("STAGE 3: NOT GATE", "STAGE 4: AND GATE", "STAGE 5: OR GATE",
                   "STAGE 6: XOR GATE", "STAGE 7: NAND AND NOR", "STAGE 8: CHEAT SHEET",
                   "Math:"):
        assert needle in text, needle
    # truth-table maths agrees with the notes
    assert outputs_for("AND") == [0, 0, 0, 1]
    assert outputs_for("XOR") == [0, 1, 1, 0]
    assert gate_out("NAND", 1, 1) == 0 and gate_out("NOR", 0, 0) == 1
    assert rows_for("NOT") == [(0,), (1,)]

    # ---- notebook page renders ----
    nb.toggle()
    nb._open_topic("MY BASIC NOTES")
    nb.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "notebook_my_basic_notes.png"))
    nb._go_back()
    nb.draw(screen)
    nb.page = "reference_index"
    nb.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "notebook_index.png"))
    print("ALL BASIC LEVEL 1 TESTS PASSED")


if __name__ == "__main__":
    main()
