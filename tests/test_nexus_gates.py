"""Automated tests for Level 7 (NEXUS-9 // THE FALSE EXIT) and regression tests for Levels 1-6."""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Headless video driver for pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
screen_1000 = pygame.display.set_mode((1000, 650))

import puzzles.nexus_gates as ng_module
from puzzles.nexus_gates import NexusGatesPuzzle, CLUES, CORRECT_PLAQUE
from glitch_scene import GlitchScene

# Level 1-6 puzzles for regression
from puzzles.logic_lock import LogicLockPuzzle
from puzzles.hidden_transmission import HiddenTransmissionPuzzle
from puzzles.memory_protocol import MemoryProtocolPuzzle
from puzzles.final_override import FinalOverridePuzzle
from puzzles.logic_architect import LogicArchitectPuzzle
from puzzles.signal_breaker import SignalBreakerPuzzle


def test_clues_and_plaques():
    print("Testing Clues and Plaque Generation...")
    # Verify CLUES constants
    assert CLUES["L1_AND_TABLE"] == "0001"
    assert CLUES["L2_NUMBERS"] == "3 5 9 14 3 5 8 12"
    assert CLUES["L3_SEQUENCE"] == "A-B-A-C-D-C"
    assert CLUES["L4_ONES"] == "10"
    assert CLUES["L5_EXPR"] == "B XNOR D + B C'"
    assert CLUES["L6_KEY"] == "K7"
    assert CLUES["L6_SEED"] == "01101"

    # Test generation across multiple seeds
    puzzle = NexusGatesPuzzle()
    for seed in range(50):
        puzzle.seed_counter = seed
        puzzle._generate_plaques()
        assert len(puzzle.gates) == 4
        # Exactly one is correct
        assert puzzle.gates[puzzle.correct_index] == CORRECT_PLAQUE
        # All 4 plaques are distinct
        tuples = [tuple(g[k] for k in ["L1", "L2", "L3", "L4", "L5", "L6"]) for g in puzzle.gates]
        assert len(set(tuples)) == 4, f"Duplicate gate generated for seed {seed}"
        # Decoys are never equal to correct
        for i, g in enumerate(puzzle.gates):
            if i != puzzle.correct_index:
                assert g != CORRECT_PLAQUE
    print("[OK] Clues and plaque generation passed.")


def test_gameplay_mechanics():
    print("Testing Gameplay Mechanics (Choices, Aggressive Mode, Restart, Win)...")
    puzzle = NexusGatesPuzzle()
    puzzle.phase = "GATES"  # test gates mechanics directly

    # 1. Correct choice immediately wins
    corr = puzzle.correct_index
    puzzle.selected_gate = corr
    puzzle._confirm_choice()
    assert puzzle.opened_gate == corr
    assert puzzle.solved_awaiting_confirm is True
    # Press Enter to finish
    event_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    puzzle.handle_event(event_enter)
    assert puzzle.is_solved() is True
    print("[OK] Correct choice win sequence passed.")

    # 2. Strike 1 triggers aggressive mode
    puzzle.restart()
    wrong_gate = (puzzle.correct_index + 1) % 4
    puzzle.selected_gate = wrong_gate
    puzzle._confirm_choice()
    assert puzzle.strikes == 1
    assert puzzle.aggressive is True
    assert puzzle.countdown == 45.0
    assert "ACCESS DENIED" in puzzle.message
    # Check that message does NOT reveal which field was wrong
    for key in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        assert key not in puzzle.message
    print("[OK] Strike 1 aggressive mode passed.")

    # 3. Timeout counts as strike 2 and reboots gates
    puzzle.update(46.0)  # advance past 45s
    assert puzzle.strikes == 0
    assert puzzle.aggressive is False
    assert "REBOOTED" in puzzle.message
    print("[OK] Timeout reboot passed.")

    # 4. Strike 2 triggers reboot
    puzzle.restart()
    wrong_gate = (puzzle.correct_index + 1) % 4
    puzzle.selected_gate = wrong_gate
    puzzle._confirm_choice()  # strike 1
    assert puzzle.strikes == 1
    wrong_gate_2 = (puzzle.correct_index + 2) % 4
    puzzle.selected_gate = wrong_gate_2
    puzzle._confirm_choice()  # strike 2 -> reboot
    assert puzzle.strikes == 0
    assert puzzle.aggressive is False
    assert "REBOOTED" in puzzle.message
    print("[OK] Strike 2 reboot passed.")


def test_build_kill_switch_toggle():
    print("Testing BUILD_KILL_SWITCH toggle...")
    # Test with BUILD_KILL_SWITCH = False
    ng_module.BUILD_KILL_SWITCH = False
    p_false = NexusGatesPuzzle()
    assert p_false.phase == "GATES"

    # Test with BUILD_KILL_SWITCH = True
    ng_module.BUILD_KILL_SWITCH = True
    p_true = NexusGatesPuzzle()
    assert p_true.phase == "KILL_SWITCH"

    # Verify Kill Switch synthesis with 3 gates: NAND(A, B), NOR(C, D), XOR(g1, g2)
    # NAND(A, B) -> g1
    # NOR(C, D)  -> g2
    # XOR(g1, g2) -> g3 -> Y
    c = p_true.workbench.circuit
    # Spawn NAND
    p_true.workbench.spawn("NAND", max_gates=4)
    # Spawn NOR
    p_true.workbench.spawn("NOR", max_gates=4)
    # Spawn XOR
    p_true.workbench.spawn("XOR", max_gates=4)

    assert c.count_gates() == 3
    # Connect A and B to NAND (g1)
    c.connect("A", "g1", 0)
    c.connect("B", "g1", 1)
    # Connect C and D to NOR (g2)
    c.connect("C", "g2", 0)
    c.connect("D", "g2", 1)
    # Connect g1 and g2 to XOR (g3)
    c.connect("g1", "g3", 0)
    c.connect("g2", "g3", 1)
    # Connect g3 to Y
    c.connect("g3", "Y", 0)

    # Verify circuit
    assert p_true.verify_circuit() is True
    assert p_true.circuit_verified is True
    assert "KILL SWITCH VERIFIED" in p_true.circuit_message

    # Confirm transition to GATES phase
    event_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    p_true.circuit_handle_event(event_enter)
    assert p_true.phase == "GATES"

    print("[OK] BUILD_KILL_SWITCH toggle and synthesis verification passed.")


def test_glitch_scene():
    print("Testing GlitchScene transition...")
    glitch = GlitchScene()
    assert glitch.is_done() is False
    glitch.update(0.8)
    assert glitch.is_done() is False
    glitch.update(0.8)
    assert glitch.is_done() is True
    # Test drawing
    glitch.draw(screen_1000)
    print("[OK] GlitchScene passed.")


def test_render_and_screenshots():
    print("Testing rendering at 1000x650 and 1500x1000...")
    p = NexusGatesPuzzle()

    # 1. 1000x650 - Kill switch phase
    p.phase = "KILL_SWITCH"
    s1 = pygame.display.set_mode((1000, 650))
    p.draw(s1)
    pygame.image.save(s1, "tests/screenshot_1000x650_killswitch.png")

    # 2. 1000x650 - Gates phase
    p.phase = "GATES"
    p.draw(s1)
    pygame.image.save(s1, "tests/screenshot_1000x650_gates.png")

    # 3. 1000x650 - Aggressive mode
    p.aggressive = True
    p.draw(s1)
    pygame.image.save(s1, "tests/screenshot_1000x650_aggressive.png")

    # 4. 1500x1000 - Gates phase
    s2 = pygame.display.set_mode((1500, 1000))
    p.aggressive = False
    p.draw(s2)
    pygame.image.save(s2, "tests/screenshot_1500x1000_gates.png")

    print("[OK] Rendering and screenshot capture passed.")


def test_regression_levels_1_to_6():
    print("Testing Levels 1-6 Regression (Instantiate and draw 1 frame each)...")
    s = pygame.display.set_mode((1000, 650))

    puzzles = [
        ("Level 1: LogicLock", LogicLockPuzzle()),
        ("Level 2: HiddenTransmission", HiddenTransmissionPuzzle()),
        ("Level 3: MemoryProtocol", MemoryProtocolPuzzle()),
        ("Level 4: FinalOverride", FinalOverridePuzzle()),
        ("Level 5: LogicArchitect", LogicArchitectPuzzle()),
        ("Level 6: SignalBreaker", SignalBreakerPuzzle()),
    ]

    for name, p in puzzles:
        p.update(0.016)
        p.draw(s)
        assert p.is_solved() is False
        print(f"  [OK] {name} OK")

    print("[OK] Levels 1-6 regression tests passed.")


if __name__ == "__main__":
    test_clues_and_plaques()
    test_gameplay_mechanics()
    test_build_kill_switch_toggle()
    test_glitch_scene()
    test_render_and_screenshots()
    test_regression_levels_1_to_6()
    print("\nALL LEVEL 7 AND REGRESSION TESTS COMPLETED SUCCESSFULLY!")
