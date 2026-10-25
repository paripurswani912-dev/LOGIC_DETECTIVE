"""Tests for the Basic Karnaugh Map course.

Run from the project folder:
    python tests/test_basic_kmap.py
Screenshots are written to tests/kmap_shots/.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import settings  # noqa: E402
from notebook import DetectiveNotebook  # noqa: E402
from puzzles.basic_kmap import (  # noqa: E402
    BasicKarnaughPuzzle, cell_name, analyse, build_kmap_stages, check_loops, cell_minterm,
    expr_str, illegal_reason, minterm_cell, prime_loops, sets_for, solution_loops,
    term_str, vals_from, cube_cells, col_codes, row_codes,
)

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kmap_shots")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


# ------------------------------------------------------------------
# 1. ENGINE
# ------------------------------------------------------------------
def test_engine():
    # gray-code layout: every pair of touching cells differs in exactly one bit
    for n in (2, 3, 4):
        rows, cols = len(row_codes(n)), len(col_codes(n))
        for r in range(rows):
            for c in range(cols):
                m = cell_minterm(n, r, c)
                assert minterm_cell(n, m) == (r, c)
                for dr, dc in ((0, 1), (1, 0)):
                    m2 = cell_minterm(n, (r + dr) % rows, (c + dc) % cols)
                    if m2 != m and (rows > 2 or dr == 0) and (cols > 2 or dc == 0):
                        assert bin(m ^ m2).count("1") == 1, (n, m, m2)

    # loops: legal cubes vs illegal shapes
    assert analyse({4, 5}, 3)["cube"]
    assert not analyse({0, 7}, 3)["cube"]                    # diagonal
    assert not analyse({0, 1, 3, 7}, 4)["cube"]              # L shape
    assert not analyse({0, 1, 3}, 3)["cube"]                 # size 3
    assert analyse({0, 2, 8, 10}, 4)["cube"]                 # four corners
    assert analyse({0, 2, 4, 6}, 3)["cube"]                  # wraps left-right

    # reading terms
    assert term_str({0}, 3) == "A'B'C'" and term_str({0, 1}, 3) == "A'B'"
    assert term_str({0, 1, 2, 3}, 3) == "A'"           # stage 4 demo captions
    assert term_str({4, 5}, 3) == "AB'"
    # minterm / maxterm facts used in stages 3 and 8
    assert cell_name(3, 3) == "A'BC" and cell_name(6, 3) == "ABC'"
    assert term_str({5}, 3, "pos") == "(A' + B + C')" and term_str({1}, 3, "pos") == "(A + B + C')"
    assert term_str({0, 1}, 3, "pos") == "(A + B)"
    assert term_str({0, 2, 8, 10}, 4) == "B'D'"
    assert term_str({0, 1}, 3, "pos") == "(A + B)"
    assert term_str({5, 7, 13, 15}, 4, "pos") == "(B' + D')"
    assert term_str({0, 1, 2, 3, 8, 9, 10, 11}, 4) == "B'"

    # reasons
    allowed = {0, 1, 2, 7}
    assert "1, 2, 4, 8" in illegal_reason(frozenset({0, 1, 2}), 3, allowed)
    assert "rectangle" in illegal_reason(frozenset({0, 7}), 3, allowed)
    assert "may only hold" in illegal_reason(frozenset({0, 1, 3, 2}), 3, {0, 1, 2})
    assert illegal_reason(frozenset({0, 1}), 3, allowed) is None

    # K-map minimisation matches known textbook answers
    v = vals_from(4, {1, 3, 7, 11, 15}, {0, 2, 5})
    loops = solution_loops(4, v)
    assert len(loops) == 2 and {3, 7, 11, 15} in [set(l) for l in loops]
    seg = vals_from(4, {0, 2, 6, 8}, set(range(10, 16)))
    assert expr_str(solution_loops(4, seg), 4) in ("B'D' + CD'", "CD' + B'D'")
    pos = solution_loops(3, vals_from(3, {2, 3, 4, 6, 7}), "zeros")
    assert sorted(term_str(l, 3, "pos") for l in pos) == ["(A + B)", "(B + C')"]

    # check_loops feedback
    v3 = vals_from(3, {0, 2, 4, 5, 6})
    ok, _ = check_loops(3, [frozenset({0, 2, 4, 6}), frozenset({4, 5})], v3, "ones")
    assert ok
    ok, msg = check_loops(3, [frozenset({0, 2}), frozenset({4, 5})], v3, "ones")
    assert not ok and "stretched" in msg
    ok, msg = check_loops(3, [frozenset({0, 2, 4, 6})], v3, "ones")
    assert not ok and "outside" in msg
    ok, msg = check_loops(3, [frozenset({0, 2, 4, 6}), frozenset({4, 5}), frozenset({4, 6})], v3, "ones")
    assert not ok
    ok, msg = check_loops(4, [frozenset({0, 1})], vals_from(4, {2}, {0, 1}), "ones")
    assert not ok and "X" in msg
    print("  engine OK")


# ------------------------------------------------------------------
# 2. AUTHORED CONTENT AGREES WITH THE ENGINE
# ------------------------------------------------------------------
def test_content():
    stages = build_kmap_stages()
    assert len(stages) == 9
    for stage in stages:
        assert stage["steps"] and stage["brief"] and stage["items"] and stage["example"]
        n, vals, loops = stage["example"]
        for l in loops:
            assert l <= set(range(1 << n))
        for step in stage["steps"]:
            assert len(step["hints"]) == 3, (stage["id"], step["task"])
            kind = step["kind"]
            if kind == "kloops":
                allowed, targets = sets_for(step["n"], step["vals"], step["mode"])
                assert solution_loops(step["n"], step["vals"], step["mode"]), stage["id"]
            if kind == "kstretch":
                n = step["n"]
                primes = [p for p in prime_loops(n, set(step["ones"]), set(step["ones"]))
                          if step["start"] in p]
                assert primes
            if kind == "kfill":
                assert step["ones"] and len(step["line"]) < 60
            if kind == "choice" and step.get("visual") == "kmap":
                n, vals = step["kn"], step["kvals"]
                labels = [l for l, _v in step["options"]]
                values = [v for _l, v in step["options"]]
                assert step["correct"] in values
                assert len(set(values)) == len(values)
                # legal/illegal verdicts must match the engine
                if stage["id"] == "k4_legal":
                    loop = frozenset(step["khl"])
                    allowed = {m for m, v in vals.items() if v == 1}
                    reason = illegal_reason(loop, n, allowed)
                    k = len(loop)
                    verdict = ("ok" if reason is None else
                               "size" if k & (k - 1) else
                               "shape" if not analyse(loop, n)["cube"] else "zero")
                    assert verdict == step["correct"], (step["q"], verdict, step["correct"])
                # expression answers must equal what the loops read as
                if stage["id"] in ("k7_sop", "k8_pos") and step["kloops"]:
                    mode = "sop" if stage["id"] == "k7_sop" else "pos"
                    loops = [l for l, _i in step["kloops"]]
                    assert step["correct"] == expr_str(loops, n, mode), stage["id"]
                    if mode == "sop":
                        allowed, targets = sets_for(n, vals, "ones")
                    else:
                        allowed, targets = sets_for(n, vals, "zeros")
                    assert set().union(*loops) == targets, "loops must cover exactly the target cells"
                    assert all(l in prime_loops(n, allowed, targets) for l in loops)
    print("  content OK (every authored answer agrees with the engine)")


# ------------------------------------------------------------------
# 3. HINT TIERS FOR EVERY STEP
# ------------------------------------------------------------------
def test_hints(screen):
    nb = DetectiveNotebook()
    puz = BasicKarnaughPuzzle(nb)
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
            puz.draw(screen)                         # must render without errors
    print("  hints OK (3 tiers on all", sum(len(s["steps"]) for s in puz.stages), "steps)")


# ------------------------------------------------------------------
# 4. FULL PLAYTHROUGH WITH REAL EVENTS
# ------------------------------------------------------------------
def click_cell(puz, screen, m):
    puz.draw(screen)
    for rect, action in puz.buttons:
        if action == ("kcell", m):
            puz.handle_event(click(rect.center))
            return
    raise AssertionError(f"cell {m} not clickable")


def solve(puz, screen):
    step, st = puz.step, puz.st
    kind = step["kind"]
    n = step.get("n", 3)
    puz.draw(screen)

    if kind == "kinspect":
        for a, b in ((2, 3), (0, 2), (0, 3)):
            click_cell(puz, screen, a)
            click_cell(puz, screen, b)
    elif kind == "kfill":
        for m in sorted(step["ones"]):
            click_cell(puz, screen, m)
    elif kind == "kpick":
        click_cell(puz, screen, step["target"])
    elif kind == "kloops":
        for loop in solution_loops(n, step["vals"], step["mode"]):
            for m in sorted(loop):
                click_cell(puz, screen, m)
            puz.handle_event(key(pygame.K_l))
        assert len(st["loops"]) == len(solution_loops(n, step["vals"], step["mode"]))
    elif kind == "kstretch":
        primes = [p for p in prime_loops(n, set(step["ones"]), set(step["ones"])) if step["start"] in p]
        best = max(primes, key=len)
        free = analyse(best, n)["free"]
        for i in range(n):
            if free & (1 << (n - 1 - i)):
                puz.handle_event(key(pygame.K_a + i))
    elif kind == "kterm":
        for i, want in enumerate(puz._expected_states()):
            for _ in range({"plain": 1, "bar": 2, "drop": 3}[want]):
                puz.handle_event(key(pygame.K_a + i))
    elif kind == "kdemo":
        for _ in range(len(step["frames"]) - 1):
            puz.handle_event(key(pygame.K_RIGHT))
    elif kind == "choice":
        opts = step["options"]
        idx = [v for _l, v in opts].index(step["correct"])
        puz.handle_event(key(pygame.K_1 + idx))
    else:
        raise AssertionError(kind)
    puz.draw(screen)
    return kind


def shot(puz, screen, name):
    puz.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, name + ".png"))


def test_playthrough(screen):
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    puz = BasicKarnaughPuzzle(nb)

    # wrong answers: tier jumps to 3 after three misses, nothing advances
    puz.handle_event(key(pygame.K_RETURN))
    assert puz.step_i == 0
    puz._enter_step()
    for _ in range(3):
        puz.stage_i, puz.step_i = 1, 0
        puz._enter_step()
        break
    puz.stage_i = 1
    puz._enter_step()
    puz.draw(screen)
    for _ in range(3):
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.st["wrong"] == 3 and puz.st["tier"] == 3
    puz.stage_i, puz.step_i = 0, 0
    puz._enter_step()

    seen_kinds = set()
    for si in range(len(puz.stages)):
        assert puz.stage_i == si
        for ti in range(len(puz.stage["steps"])):
            assert puz.phase == "play"
            if ti in (0, 1) or puz.step["kind"] in ("kloops", "kstretch", "kterm"):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{puz.step['kind']}_before")
            seen_kinds.add(solve(puz, screen))
            if ti in (0, 1) or puz.step["kind"] in ("kloops", "kstretch", "kterm"):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{puz.step['kind']}_solved")
            puz.handle_event(key(pygame.K_RETURN))
        assert puz.phase == "done", f"stage {si + 1} should be finished"
        shot(puz, screen, f"s{si + 1}_done")
        assert puz.stage["id"] in puz.saved_stages
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.is_solved()
    assert {"kinspect", "kfill", "kpick", "kloops", "kstretch", "kterm", "kdemo", "choice"} <= seen_kinds

    text = "\n".join(nb.reference_notes["MY BASIC NOTES"])
    for needle in ("KARNAUGH 1: NEIGHBOURS", "KARNAUGH 3: MINTERMS", "KARNAUGH 4: LEGAL LOOPS",
                   "KARNAUGH 8: POS (LOOP THE ZEROS)", "MAXTERM", "KARNAUGH 9: DON'T CARES",
                   "segment e lights for 0, 2, 6, 8"):
        assert needle in text, needle

    nb.toggle()
    nb._open_topic("MY BASIC NOTES")
    nb.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "notebook_kmap_notes.png"))
    print("  playthrough OK (9 stages, every step kind, notebook autofilled)")


def test_notebook_order_and_text():
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    nb.add_basic_note("k1_neighbours", ["KARNAUGH 1: X"])
    nb.add_basic_note("s3_not", ["STAGE 3: NOT GATE"])
    notes = nb.reference_notes["MY BASIC NOTES"]
    assert notes.index("STAGE 3: NOT GATE") < notes.index("KARNAUGH 1: X"), "gates before K-maps"
    # BASIC path: K-maps live on terminal 4 (level_four); terminal 5 keeps its original text
    assert "K-MAP" in " ".join(nb.SCIENTIST_NOTES["level_four"]).upper()
    assert nb.LEVEL_PRACTICE["level_four"] == "KARNAUGH MAPS"
    assert "Karnaugh" not in nb.LEVEL_GOALS["level_four"] or "Karnaugh" in nb.LEVEL_GOALS["level_four"]
    assert nb.SCIENTIST_NOTES["level_five"] == DetectiveNotebook.SCIENTIST_NOTES["level_five"]
    assert nb.LEVEL_GOALS["level_five"] == DetectiveNotebook.LEVEL_GOALS["level_five"]
    nb.set_mode("intermediate")
    # INTERMEDIATE is untouched
    for name in ("SCIENTIST_NOTES", "LEVEL_GOALS", "LEVEL_HINTS", "DEFAULT_FINDINGS", "LEVEL_PRACTICE"):
        assert getattr(nb, name) == getattr(DetectiveNotebook, name), name
    assert nb.LEVEL_PRACTICE["level_four"] == "BOOLEAN ALGEBRA"
    assert "MY BASIC NOTES" not in nb.reference_topics
    print("  notebook order + per-mode text OK")


def main():
    os.makedirs(SHOTS, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    print("K-map tests")
    test_engine()
    test_content()
    test_hints(screen)
    test_playthrough(screen)
    test_notebook_order_and_text()
    print("ALL BASIC KARNAUGH TESTS PASSED")


if __name__ == "__main__":
    main()
