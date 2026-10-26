"""Tests for Basic Level 6 (flip-flops, shift registers, counters).

Run from the project folder:   python tests/test_basic_seq.py
Screenshots go to tests/seq_shots/.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import settings  # noqa: E402
from notebook import DetectiveNotebook  # noqa: E402
from puzzles.basic_seq import (  # noqa: E402
    BasicSequentialPuzzle, FF_INPUTS, X, bit_of, bits_str, build_seq_stages, char_next, char_rows,
    count_states, excitation, ff_next, input_combos, shift_right, simulate_ff, t_inputs,
)

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seq_shots")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


# ------------------------------------------------------------------
def test_engine():
    # SR / D / T / JK behaviour
    assert ff_next("SR", 0, 1, 0) == 1 and ff_next("SR", 1, 0, 1) == 0 and ff_next("SR", 1, 0, 0) == 1
    assert ff_next("SR", 0, 1, 1) is None
    assert [ff_next("D", q, d) for q in (0, 1) for d in (0, 1)] == [0, 1, 0, 1]
    assert ff_next("T", 0, 1) == 1 and ff_next("T", 1, 1) == 0 and ff_next("T", 1, 0) == 1
    assert ff_next("JK", 1, 1, 1) == 0 and ff_next("JK", 0, 1, 1) == 1
    assert char_next("SR") == [0, 1, 0, 0, 1, 1, X, X]
    assert char_next("JK") == [0, 1, 0, 0, 1, 1, 1, 0]
    # excitation table of the JK flip-flop (the one the player fills in)
    exc = excitation("JK")
    assert exc[(0, 0)] == (0, X) and exc[(0, 1)] == (1, X) and exc[(1, 0)] == (X, 1) and exc[(1, 1)] == (X, 0)
    assert excitation("SR")[(0, 0)] == (0, X) and excitation("SR")[(1, 1)] == (X, 0)
    assert excitation("D")[(1, 0)] == (0,) and excitation("T")[(0, 1)] == (1,)
    # shift register + counters
    assert shift_right([0, 0, 0, 0], 1) == [1, 0, 0, 0] and shift_right([1, 0, 1, 1], 0) == [0, 1, 0, 1]
    assert count_states(3, 8, 0, 8) == [0, 1, 2, 3, 4, 5, 6, 7, 0]
    assert count_states(3, 6, 0, 7) == [0, 1, 2, 3, 4, 5, 0, 1]
    assert t_inputs(0b011, 3) == [1, 1, 1] and t_inputs(0b111, 3) == [1, 1, 1] and t_inputs(0b001, 3) == [1, 1, 0]
    assert t_inputs(0b010, 3) == [1, 0, 0]          # Q0 = 0, so T1 and T2 are 0
    # simulate_ff example used in the JK exam question
    assert simulate_ff("JK", 0, [(1, 0), (0, 0), (1, 1), (1, 1), (0, 1), (1, 0)]) == [1, 1, 0, 1, 0, 1]
    # synchronous counter really is a binary counter when T follows the rule
    s = 0
    for _ in range(20):
        t = t_inputs(s, 4)
        nxt = sum((bit_of(s, i) ^ t[i]) << i for i in range(4))
        assert nxt == (s + 1) % 16
        s = nxt
    print("  engine OK")


def test_content():
    stages = build_seq_stages()
    assert len(stages) == 8
    for stage in stages:
        assert stage["steps"] and stage["brief"] and stage["items"] and stage["example"]
        for step in stage["steps"]:
            assert len(step["hints"]) == 3, (stage["id"], step["task"])
            if step["kind"] == "choice":
                values = [v for _l, v in step["options"]]
                assert step["correct"] in values and len(set(values)) == len(values), step["q"]

    # --- flip-flop conversion answers: the right wiring works, every wrong option fails ---
    def works(old, new, wiring):
        for q in (0, 1):
            for inp in input_combos(new):
                drive = wiring(q, *inp)
                if drive is None:
                    return False
                if ff_next(old, q, *drive) != ff_next(new, q, *inp):
                    return False
        return True
    inv = lambda v: 1 - v
    jk_t = {"J = K = T": lambda q, t: (t, t), "J = T, K = 0": lambda q, t: (t, 0),
            "J = K = 1": lambda q, t: (1, 1), "J = T, K = T'": lambda q, t: (t, inv(t))}
    assert [k for k, w in jk_t.items() if works("JK", "T", w)] == ["J = K = T"]
    jk_d = {"D": lambda q, d: (d, d), "D'": lambda q, d: (d, inv(d)), "0": lambda q, d: (d, 0), "1": lambda q, d: (d, 1)}
    assert [k for k, w in jk_d.items() if works("JK", "D", w)] == ["D'"]
    d_t = {"T": lambda q, t: (t,), "T'": lambda q, t: (inv(t),), "T OR Q": lambda q, t: (t | q,),
           "T XOR Q": lambda q, t: (t ^ q,)}
    assert [k for k, w in d_t.items() if works("D", "T", w)] == ["T XOR Q"]
    sr_d = {"D": lambda q, d: (d, d), "D'": lambda q, d: (d, inv(d)), "0": lambda q, d: (d, 0), "1": lambda q, d: (d, 1)}
    assert [k for k, w in sr_d.items() if works("SR", "D", w)] == ["D'"]

    # --- counter facts used in questions ---
    assert [n for n in range(1, 9) if 2 ** n >= 12][0] == 4
    assert [n for n in range(1, 9) if 2 ** n >= 100][0] == 7
    first = lambda a, b: next(s for s in range(16) if bit_of(s, a) and bit_of(s, b))
    assert first(3, 1) == 10 and first(2, 0) == 5 and first(3, 0) == 9       # mod-10 reset gate = Q3 and Q1
    t2 = [t_inputs(s, 3)[2] for s in range(8)]
    assert t2 == [int(s & 3 == 3) for s in range(8)]                            # T2 = Q0 AND Q1
    assert [t_inputs(s, 2)[0] for s in range(4)] == [1, 1, 1, 1]
    assert [t_inputs(s, 2)[1] for s in range(4)] == [bit_of(s, 0) for s in range(4)]   # T1 = Q0
    assert t_inputs(0b0111, 4)[3] == 1 and t_inputs(0b0101, 4)[3] == 0          # T3 = Q0 Q1 Q2

    # --- every table / wave / register row stored in the content matches the engine ---
    reg = [0, 0, 0, 0]
    for si, want in zip([1, 1, 0, 1], ["1000", "1100", "0110", "1011"]):
        reg = shift_right(reg, si)
        assert "".join(map(str, reg)) == want
    reg = [1, 0, 1, 1]
    for si, want in zip([0, 1, 1], ["0101", "1010", "1101"]):
        reg = shift_right(reg, si)
        assert "".join(map(str, reg)) == want
    reg = [0, 0, 0, 0]
    for bit in [1, 1, 0, 1]:                       # first bit entered travels furthest
        reg = shift_right(reg, bit)
    assert reg == [1, 0, 1, 1]
    reg, out = [1, 0, 1, 1], []                    # PISO: right-most bit leaves first
    for _ in range(4):
        out.append(reg[-1]); reg = shift_right(reg, 0)
    assert out == [1, 1, 0, 1]
    # characteristic equations printed on the boss card
    for q in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                assert ff_next("JK", q, j, k) == ((j & (1 - q)) | ((1 - k) & q))
    print("  content OK (every authored answer agrees with the engine)")


def test_hints(screen):
    puz = BasicSequentialPuzzle(DetectiveNotebook())
    total = 0
    for si in range(len(puz.stages)):
        for ti in range(len(puz.stages[si]["steps"])):
            puz.stage_i, puz.step_i, puz.phase = si, ti, "play"
            puz._enter_step()
            assert puz._hint_text() is None
            for tier in (1, 2, 3):
                puz.handle_event(key(pygame.K_h))
                text = puz._hint_text()
                assert isinstance(text, str) and len(text) > 8, (si, ti, tier)
            puz.handle_event(key(pygame.K_h))
            assert puz.st["tier"] == 3
            puz.draw(screen)
            total += 1
        puz.phase = "done"
        puz.draw(screen)
    print("  hints OK (3 tiers on all", total, "steps, every screen draws)")


# ------------------------------------------------------------------
def solve(puz, screen):
    """Answer the current step using real key events."""
    step, st = puz.step, puz.st
    kind = step["kind"]
    puz.draw(screen)
    if kind == "sdemo":
        for _ in range(len(step["frames"]) - 1):
            puz.handle_event(key(pygame.K_RIGHT))
    elif kind == "ffplay":
        names = FF_INPUTS[step["ff"]]
        for combo in input_combos(step["ff"]):
            for i, name in enumerate(names):
                if st["ins"][i] != combo[i]:
                    puz.handle_event(key(getattr(pygame, "K_" + name.lower())))
            puz.handle_event(key(pygame.K_SPACE))
    elif kind == "fftable":
        for v in step["expect"]:
            puz.handle_event(key(pygame.K_x if v == X else pygame.K_0 + v))
    elif kind == "wavefill":
        for v in step["expect"]:
            puz.handle_event(key(pygame.K_0 + v))
    elif kind == "regplay":
        if "target_reg" in step:
            for bit in reversed(step["target_reg"]):
                if st["si"] != bit:
                    puz.handle_event(key(pygame.K_s))
                puz.handle_event(key(pygame.K_SPACE))
        else:
            for i, bit in enumerate(step["need_load"]):
                if st["par"][i] != bit:
                    puz.handle_event(key(pygame.K_1 + i))
            puz.handle_event(key(pygame.K_l))
            for _ in range(len(step["target_out"])):
                puz.handle_event(key(pygame.K_SPACE))
    elif kind == "seqtable":
        for row in step["expect"]:
            for ch in row:
                puz.handle_event(key(pygame.K_0 + int(ch)))
    elif kind == "cntplay":
        for _ in range(40):
            if (step["need"].get("rollover") and st["rolled"]) or \
               (step["need"].get("t_seen") is not None and step["need"]["t_seen"] in st["t_seen"]):
                break
            puz.handle_event(key(pygame.K_SPACE))
    elif kind == "exctable":
        for row in step["expect"]:
            for v in row:
                puz.handle_event(key(pygame.K_x if v == X else pygame.K_0 + v))
    elif kind == "choice":
        opts = step["options"]
        if all(isinstance(v, int) for _l, v in opts):
            puz.handle_event(key(pygame.K_0 + step["correct"]))
        else:
            puz.handle_event(key(pygame.K_1 + [v for _l, v in opts].index(step["correct"])))
    else:
        raise AssertionError(kind)
    return kind


def shot(puz, screen, name):
    puz.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, name + ".png"))


def test_mouse(screen):
    """The same widgets must also work with the mouse."""
    puz = BasicSequentialPuzzle(DetectiveNotebook())
    puz.stage_i, puz.step_i = 0, 1                     # SR sandbox
    puz._enter_step()
    puz.draw(screen)
    switches = [r for r, a in puz.buttons if a[0] == "fin"]
    clock = [r for r, a in puz.buttons if a == ("fclock",)][0]
    puz.handle_event(click(switches[0].center))
    puz.draw(screen)
    assert puz.st["ins"] == [1, 0]
    puz.handle_event(click(clock.center))
    assert puz.st["q"] == 1 and len(puz.st["seen"]) == 1
    puz.stage_i, puz.step_i = 1, 3                     # wavefill
    puz._enter_step()
    puz.draw(screen)
    cell = [r for r, a in puz.buttons if a == ("wcell", 0)][0]
    puz.handle_event(click(cell.center))
    assert puz.st["vals"][0] == 0
    puz.handle_event(click(cell.center))
    assert puz.st["vals"][0] == 1
    puz.stage_i, puz.step_i = 4, 5                     # PISO sandbox
    puz._enter_step()
    puz.draw(screen)
    chip = [r for r, a in puz.buttons if a == ("rpar", 1)][0]
    puz.handle_event(click(chip.center))
    load = [r for r, a in puz.buttons if a == ("rload",)][0]
    puz.handle_event(click(load.center))
    assert puz.st["reg"] == [0, 1, 0, 0]
    puz.stage_i, puz.step_i = 5, 1                     # counter sandbox
    puz._enter_step()
    puz.draw(screen)
    clk = [r for r, a in puz.buttons if a == ("cclock",)][0]
    puz.handle_event(click(clk.center))
    assert puz.st["state"] == 1
    print("  mouse OK (switches, clock, cells, chips, load, counter)")


def test_playthrough(screen):
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    puz = BasicSequentialPuzzle(nb)

    # wrong answers keep the step and 3 misses reveal the answer
    puz.stage_i, puz.step_i = 1, 3
    puz._enter_step()
    for _ in range(3):
        puz.handle_event(key(pygame.K_0))              # type 0 into the first box
        for _ in range(5):
            puz.handle_event(key(pygame.K_1))
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.step_i == 3 and puz.st["wrong"] == 3 and puz.st["tier"] == 3
    puz.stage_i, puz.step_i = 0, 0
    puz._enter_step()

    seen = set()
    for si in range(len(puz.stages)):
        assert puz.stage_i == si
        for ti in range(len(puz.stage["steps"])):
            assert puz.phase == "play"
            if ti in (0, 1) or puz.step["kind"] in ("regplay", "cntplay", "seqtable", "exctable"):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{puz.step['kind']}_before")
            seen.add(solve(puz, screen))
            if ti in (1, 2):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{puz.step['kind']}_solved")
            puz.handle_event(key(pygame.K_RETURN))
        assert puz.phase == "done", f"stage {si + 1} should be finished"
        shot(puz, screen, f"s{si + 1}_done")
        assert puz.stage["id"] in puz.saved_stages
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.is_solved()
    assert {"sdemo", "ffplay", "fftable", "wavefill", "regplay", "seqtable", "cntplay", "exctable", "choice"} <= seen

    text = "\n".join(nb.reference_notes["MY BASIC NOTES"])
    for needle in ("SEQUENTIAL 1: MEMORY", "SEQUENTIAL 2: CLOCK", "SEQUENTIAL 4: FLIP-FLOP CONVERSION",
                   "SEQUENTIAL 5: SHIFT REGISTERS", "SEQUENTIAL 7: SYNCHRONOUS COUNTERS",
                   "SEQUENTIAL 8: CHEAT SHEET", "Characteristic equations"):
        assert needle in text, needle
    for line in nb.reference_notes["MY BASIC NOTES"]:
        if line.startswith("SEQUENTIAL"):
            assert line.isupper() or not any(c.islower() for c in line), line   # heading renders as a heading
    nb.toggle()
    nb._open_topic("MY BASIC NOTES")
    nb.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "notebook_seq_notes.png"))
    print("  playthrough OK (8 stages, every step kind, notebook autofilled)")


def test_notebook():
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    nb.add_basic_note("q1_memory", ["SEQUENTIAL 1: X"])
    nb.add_basic_note("k1_neighbours", ["KARNAUGH 1: X"])
    nb.add_basic_note("s1_onoff", ["STAGE 1: X"])
    notes = nb.reference_notes["MY BASIC NOTES"]
    assert notes.index("STAGE 1: X") < notes.index("KARNAUGH 1: X") < notes.index("SEQUENTIAL 1: X")
    assert "FLIP-FLOP" in " ".join(nb.SCIENTIST_NOTES["level_six"]).upper()
    # terminal 5 is the Basic combinational course (Level 5)
    assert nb.SCIENTIST_NOTES["level_five"] != DetectiveNotebook.SCIENTIST_NOTES["level_five"]
    assert nb.SCIENTIST_NOTES["level_four"] != DetectiveNotebook.SCIENTIST_NOTES["level_four"]   # K-map text still there
    nb.set_mode("intermediate")
    for name in ("SCIENTIST_NOTES", "LEVEL_GOALS", "LEVEL_HINTS", "DEFAULT_FINDINGS", "LEVEL_PRACTICE"):
        assert getattr(nb, name) == getattr(DetectiveNotebook, name), name
    print("  notebook order + per-mode text OK")


def main():
    os.makedirs(SHOTS, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.mouse.get_pos = lambda: (0, 0)
    print("Level 6 (flip-flops, registers, counters) tests")
    test_engine()
    test_content()
    test_hints(screen)
    test_mouse(screen)
    test_playthrough(screen)
    test_notebook()
    print("ALL BASIC SEQUENTIAL TESTS PASSED")


if __name__ == "__main__":
    main()