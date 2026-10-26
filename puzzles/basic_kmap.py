# puzzles/basic_kmap.py
# BASIC KARNAUGH MAPS - "Shrink a formula with a picture" (9 stages)
#
# Plugs into terminal 4 (puzzle_id final_override, notebook level_four) on the BASIC path.
# It reuses the frame, hints, notebook autofill and answer buttons of
# puzzles/basic_gates.py, and adds a small K-map engine.
#
#   1  Neighbours          a K-map is a truth table where neighbours differ in ONE variable
#   2  Fill the map        truth table -> map (2, 3 and 4 variables), reading Gray-code labels
#   3  Minterms           every cell has a number and a name (m0, m1 ...)
#   4  Legal or illegal?   the grouping rules: size, shape, contents
#   5  Stretch the loop    why 4 and not 8: keep doubling until a 0 blocks you
#   6  Wrap-around         edges touch, the four corners are one loop
#   7  Loop -> term -> SOP read a loop as a product term, OR the terms together
#   8  POS + maxterms      loop the 0s, read sums, AND them (De Morgan link)
#   9  Don't cares + boss  X = wildcard, then 7-segment display segment "e"
#
# The big idea taught everywhere: neighbouring cells differ in exactly one
# variable, so when both are 1 that variable cancels (A + A' = 1).
#
# Controls
#   mouse                  click cells / buttons
#   arrows + SPACE         move a cursor over the map and click with the keyboard
#   L / U / C              (loop stages) loop the selected cells / undo / clear selection
#   A B C D                (stretch + read stages) the variable of that name
#   ENTER                  check / continue          H  hint (press again for more)
#
# UI NOTE: this version lays every screen out from the top down (text first,
# then the map, then the side panel / buttons), and shrinks the map to fit,
# so nothing can sit on top of anything else. The puzzle LOGIC is unchanged.

import itertools
import random

import pygame

from puzzles.basic_gates import (
    BasicGatesPuzzle, WORK, FULL, wrap_text,
    PANEL, CYAN, GREEN, YELLOW, GREY, WHITE,
)

if not hasattr(BasicGatesPuzzle, "LEGEND_EXTRA"):
    raise ImportError(
        "puzzles/basic_gates.py is the OLD version. Replace it with the one from "
        "basic_mode_update_v2.zip (basic_kmap.py needs the updated file)."
    )

VARS = "ABCD"
LOOP_COLORS = [(255, 128, 96), (96, 200, 255), (255, 214, 86),
               (196, 130, 255), (112, 240, 152)]
X = 2          # value used for "don't care"


# ------------------------------------------------------------------
# K-MAP ENGINE  (unchanged)
# ------------------------------------------------------------------
def popcount(x):
    return bin(x).count("1")


def col_bits(n):
    return 1 if n == 2 else 2


def row_codes(n):
    return [0, 1] if n in (2, 3) else [0, 1, 3, 2]


def col_codes(n):
    return [0, 1] if n == 2 else [0, 1, 3, 2]


def cell_minterm(n, r, c):
    return (row_codes(n)[r] << col_bits(n)) | col_codes(n)[c]


def minterm_cell(n, m):
    for r in range(len(row_codes(n))):
        for c in range(len(col_codes(n))):
            if cell_minterm(n, r, c) == m:
                return r, c
    raise ValueError(m)


def bits(m, n):
    return format(m, f"0{n}b")


def vals_from(n, ones, dcs=()):
    return {m: (1 if m in ones else X if m in dcs else 0) for m in range(1 << n)}


def cube_cells(base, free):
    base &= ~free
    cells, sub = [], free
    while True:
        cells.append(base | sub)
        if sub == 0:
            break
        sub = (sub - 1) & free
    return frozenset(cells)


def analyse(cells, n):
    """Describe a set of minterms: is it a legal loop, which variables are fixed?"""
    cells = list(cells)
    full = (1 << n) - 1
    a, o = full, 0
    for m in cells:
        a &= m
        o |= m
    free = o ^ a
    cube = len(set(cells)) == len(cells) == (1 << popcount(free))
    fixed_mask = full ^ free
    return {"size": len(cells), "free": free, "fixed_mask": fixed_mask,
            "fixed_val": a & fixed_mask, "cube": cube}


def literals(info, n, mode):
    out = []
    for i, name in enumerate(VARS[:n]):
        bit = 1 << (n - 1 - i)
        if info["fixed_mask"] & bit:
            one = bool(info["fixed_val"] & bit)
            if mode == "sop":
                out.append(name if one else name + "'")
            else:                       # POS reads a zero-loop inverted
                out.append(name + "'" if one else name)
    return out


def term_str(cells, n, mode="sop"):
    lits = literals(analyse(cells, n), n, mode)
    if mode == "sop":
        return "".join(lits) if lits else "1"
    if not lits:
        return "0"
    return lits[0] if len(lits) == 1 else "(" + " + ".join(lits) + ")"


def expr_str(loops, n, mode="sop"):
    terms = [term_str(l, n, mode) for l in loops]
    return " + ".join(terms) if mode == "sop" else "".join(terms)


def cell_name(m, n):
    """Product-term name of one cell, e.g. minterm 5 of 3 variables -> AB'C."""
    return "".join(v if m & (1 << (n - 1 - i)) else v + "'"
                   for i, v in enumerate(VARS[:n]))


def all_cubes(n):
    seen = set()
    for free in range(1 << n):
        for base in range(1 << n):
            if base & free:
                continue
            cells = cube_cells(base, free)
            if cells not in seen:
                seen.add(cells)
                yield cells, free


def prime_loops(n, allowed, targets):
    """Biggest legal loops (cannot be stretched) that hold at least one target."""
    res = []
    for cells, free in all_cubes(n):
        if not cells <= allowed or not (cells & targets):
            continue
        extendable = False
        for i in range(n):
            bit = 1 << i
            if free & bit:
                continue
            if frozenset(m ^ bit for m in cells) <= allowed:
                extendable = True
                break
        if not extendable:
            res.append(cells)
    return res


def min_cover(n, primes, targets):
    for k in range(1, len(primes) + 1):
        for combo in itertools.combinations(primes, k):
            if set().union(*combo) >= targets:
                return list(combo)
    return []


def sets_for(n, vals, mode):
    ones = {m for m, v in vals.items() if v == 1}
    zeros = {m for m, v in vals.items() if v == 0}
    dcs = {m for m, v in vals.items() if v == X}
    if mode == "zeros":
        return zeros | dcs, zeros
    return ones | dcs, ones


def solution_loops(n, vals, mode="ones"):
    allowed, targets = sets_for(n, vals, mode)
    return min_cover(n, prime_loops(n, allowed, targets), targets)


def illegal_reason(cells, n, allowed, mode="ones"):
    k = len(cells)
    if k == 0:
        return "Select some cells first (click them), then press LOOP IT."
    if k & (k - 1):
        return (f"A loop must hold 1, 2, 4, 8 or 16 cells. You picked {k}. "
                "Loops never hold 3, 5, 6 or 7 cells.")
    if not analyse(cells, n)["cube"]:
        return ("The cells must form a rectangle (it may wrap around an edge). "
                "Diagonals and L-shapes are not legal.")
    bad = sorted(set(cells) - allowed)
    if bad:
        what = "1s (and X's)" if mode == "ones" else "0s (and X's)"
        return (f"A loop may only hold {what}. "
                f"Cell {bits(bad[0], n)} is not allowed.")
    return None


def check_loops(n, loops, vals, mode):
    """Return (ok, message) for the player's complete set of loops."""
    allowed, targets = sets_for(n, vals, mode)
    if not loops:
        return False, "Draw at least one loop first."
    primes = set(prime_loops(n, allowed, targets))
    for i, loop in enumerate(loops):
        if not (loop & targets):
            return False, f"Loop {i + 1} holds only X's. It covers nothing, so remove it."
    for i, loop in enumerate(loops):
        if loop not in primes:
            return False, (f"Loop {i + 1} is legal but can be stretched bigger. "
                           "Always make loops as big as possible.")
    covered = set().union(*loops)
    missing = targets - covered
    if missing:
        return False, f"{len(missing)} cell(s) that must be covered are still outside every loop."
    best = len(min_cover(n, list(primes), targets))
    if len(loops) > best:
        return False, ("Everything is covered, but you used more loops than needed. "
                       "Is one loop already covered by the others?")
    return True, ""


# ------------------------------------------------------------------
# STAGE DATA  (logic unchanged - only the wording of hints / captions was simplified)
# ------------------------------------------------------------------
def _loop_text(p):
    return p.solution_text()


def _expr_options(n, loops, mode, seed):
    """Correct SOP/POS expression plus three believable wrong ones."""
    correct = expr_str(loops, n, mode)
    wrong = []

    def flip(term_cells):
        info = analyse(term_cells, n)
        info = dict(info, fixed_val=info["fixed_mask"] & ~info["fixed_val"])
        return info

    # 1. flip every bar in the first loop
    first = flip(loops[0])
    lits = literals(first, n, mode)
    t0 = ("".join(lits) if mode == "sop" else
          (lits[0] if len(lits) == 1 else "(" + " + ".join(lits) + ")"))
    rest = [term_str(l, n, mode) for l in loops[1:]]
    wrong.append(" + ".join([t0] + rest) if mode == "sop" else "".join([t0] + rest))
    # 2. forget the last loop
    if len(loops) > 1:
        wrong.append(expr_str(loops[:-1], n, mode))
    # 3. mix up AND / OR
    terms = [term_str(l, n, mode) for l in loops]
    wrong.append("".join(terms) if mode == "sop" else " + ".join(terms))
    # 4. flip every bar everywhere
    flipped = []
    for l in loops:
        lt = literals(flip(l), n, mode)
        if mode == "sop":
            flipped.append("".join(lt))
        else:
            flipped.append(lt[0] if len(lt) == 1 else "(" + " + ".join(lt) + ")")
    wrong.append(" + ".join(flipped) if mode == "sop" else "".join(flipped))

    uniq = []
    for w in wrong:
        if w != correct and w not in uniq:
            uniq.append(w)
    opts = [correct] + uniq[:3]
    random.Random(seed).shuffle(opts)
    return [(o, o) for o in opts], correct


def _kmap_choice(n, vals, loops, q, correct, options, task, ok, hints, highlight=()):
    return {
        "kind": "choice", "visual": "kmap", "q": q, "options": options,
        "correct": correct, "task": task, "ok": ok, "hints": hints,
        "kn": n, "kvals": vals, "kloops": loops, "khl": set(highlight),
    }


def _stage_neighbours():
    vals2 = vals_from(2, {2, 3})
    gray_vals = vals_from(3, set())
    return {
        "id": "k1_neighbours", "title": "Neighbours", "sub": "one step = one variable",
        "brief": [
            "A Karnaugh map (K-map) is a truth table drawn as a grid.",
            "Its secret: cells that touch differ in exactly ONE variable. "
            "If both touching cells are 1, that variable cancels out.",
        ],
        "steps": [
            {
                "kind": "kinspect", "n": 2, "vals": vals2,
                "task": "Click two cells, one after the other. Find 2 pairs of neighbours and 1 diagonal pair.",
                "hints": [
                    "Click one cell, then click a second cell. The box on the right tells you what you found.",
                    "NEIGHBOURS share a side (side by side, or one above the other). A DIAGONAL pair only touches at a corner.",
                    lambda p: "Try it: click 10 then 11 (neighbours). Click 00 then 10 (neighbours). Click 00 then 11 (diagonal).",
                ],
            },
            _kmap_choice(
                3, gray_vals, [],
                "Why are the columns ordered 00, 01, 11, 10 and not 00, 01, 10, 11?",
                "one",
                [("Neighbouring columns differ in only ONE bit", "one"),
                 ("It is alphabetical order", "alpha"),
                 ("It is a random choice", "random"),
                 ("It just looks nicer", "nice")],
                "Pick the reason for this column order.",
                "This is called Gray code: 00, 01, 11, 10. Each step changes only one bit, so neighbours stay neighbours.",
                [
                    "Look at 01 and 10 side by side. Two bits change at once (0 to 1 and 1 to 0).",
                    "In Gray code, each step changes exactly ONE bit. That keeps touching cells one variable apart.",
                    "The answer is: neighbouring columns differ in only one bit.",
                ],
                highlight={3, 7, 2, 6},
            ),
            _kmap_choice(
                2, vals_from(2, {2, 3}), [(frozenset({2, 3}), 0)],
                "Both cells in the loop are 1: AB' and AB. Which variable changes between them?",
                "B",
                [("A", "A"), ("B", "B")],
                "Which variable is different in the two cells?",
                "B changes (0 to 1) while A stays 1, so B cancels.",
                [
                    "Look at the label of each cell. AB' has B = 0. AB has B = 1.",
                    "The letter that is different in the two cells is the one that cancels.",
                    "The answer is B. A stays 1 in both cells.",
                ],
            ),
            _kmap_choice(
                2, vals_from(2, {2, 3}), [(frozenset({2, 3}), 0)],
                "So AB' + AB simplifies to what?",
                "A",
                [("A", "A"), ("B", "B"), ("AB", "AB"), ("1", "1")],
                "Pick the simplified expression.",
                "AB' + AB = A(B' + B) = A. The variable that changed (B) disappears.",
                [
                    "Take out the letter both cells share: A(B' + B).",
                    "B' + B always equals 1, so only the shared letter is left.",
                    "The answer is A.",
                ],
            ),
        ],
        "example": (2, vals2, [frozenset({2, 3})]),
        "items": [
            ("RULE", "Neighbouring cells differ in exactly ONE variable. "
                     "Two neighbouring 1s merge and that variable cancels."),
            ("MATH LINK", "AB' + AB = A(B' + B) = A, because B' + B = 1."),
            ("WHY GRAY CODE", "Row and column labels run 00, 01, 11, 10 so that neighbours stay one bit apart."),
        ],
    }


def _fill_step(n, ones):
    names = VARS[:n]
    listing = ", ".join(bits(m, n) for m in sorted(ones))
    return {
        "kind": "kfill", "n": n, "ones": set(ones),
        "line": f"F = 1 when {names} = {listing}",
        "task": f"Click the cells where F = 1. Read the {names} labels carefully.",
        "hints": [
            "Each cell sits where its ROW label meets its COLUMN label. Read the row bits first, then the column bits.",
            "The column order is 00, 01, 11, 10. Column 11 comes BEFORE column 10. Read the labels, do not count cells.",
            lambda p: p.fill_answer_text(),
        ],
    }


def _pick_step(n, target, prompt):
    return {
        "kind": "kpick", "n": n, "target": target,
        "line": prompt,
        "task": "Click the cell with that label.",
        "hints": [
            "The first letters give the ROW label. The last letters give the COLUMN label.",
            "Rows and columns are NOT in counting order. Read the labels, do not count cells.",
            lambda p: p.pick_answer_text(),
        ],
    }


def _stage_fill():
    return {
        "id": "k2_fill", "title": "Fill the map", "sub": "truth table to grid",
        "brief": [
            "2 variables give a 2 x 2 map, 3 variables a 2 x 4 map, 4 variables a 4 x 4 map.",
            "A cell is the row label and column label put together. "
            "Remember: the labels run in Gray order, 00 01 11 10.",
        ],
        "steps": [
            _fill_step(3, {1, 3, 7}),
            _fill_step(3, {0, 2, 4, 6}),
            _fill_step(4, {0, 5, 10, 15}),
            _pick_step(3, 5, "Click the cell where A = 1, B = 0, C = 1."),
            _pick_step(4, 6, "Click the cell where ABCD = 0110."),
        ],
        "example": (3, vals_from(3, {1, 3, 7}), []),
        "items": [
            ("RULE", "A cell's address is its row bits followed by its column bits (ABC = row A, column BC)."),
            ("SIZES", "2 variables: 2x2. 3 variables: 2x4. 4 variables: 4x4. 5 variables: two 4x4 maps."),
            ("WATCH OUT", "Column 11 comes before column 10. Read labels, never count cells."),
        ],
    }


def _judge(n, ones, loop, verdict, why, hints_extra):
    labels = [("LEGAL loop", "ok"),
              ("ILLEGAL: wrong shape", "shape"),
              ("ILLEGAL: wrong size", "size"),
              ("ILLEGAL: has a 0 inside", "zero")]
    return _kmap_choice(
        n, vals_from(n, ones), [(frozenset(loop), 0)],
        "Is this loop legal? If not, why?",
        verdict, labels, "Check the size, shape and contents of the highlighted loop.", why,
        [
            "Check three things: SIZE (1, 2, 4 or 8 cells?), SHAPE (a rectangle?) and CONTENTS (only 1s?).",
            hints_extra,
            {"ok": "The answer is: legal.", "shape": "The answer is: illegal shape.",
             "size": "The answer is: illegal size.", "zero": "The answer is: illegal, it holds a 0."}[verdict],
        ],
        highlight=loop,
    )


def _stage_legal():
    return {
        "id": "k4_legal", "title": "Legal or illegal?", "sub": "the grouping rules",
        "brief": [
            "A loop is legal only if it passes THREE checks.",
            "SIZE: 1, 2, 4 or 8 cells (powers of 2). SHAPE: a rectangle, wrapping round edges allowed. "
            "CONTENTS: only 1s (and X's).",
        ],
        "steps": [
            _judge(3, {1, 3, 5, 7}, {1, 3, 5, 7}, "ok",
                   "Legal: a 2 x 2 block of 1s, size 4.",
                   "Count the cells (4 is a power of 2), look at the shape (a square) and check that there are no 0s."),
            _judge(3, {0, 2, 7}, {0, 7}, "shape",
                   "Illegal shape: the two 1s touch only at a corner (a diagonal). They differ in 3 variables.",
                   "These cells touch only at a corner. Do corner cells count as neighbours?"),
            _judge(4, {0, 1, 3, 7}, {0, 1, 3, 7}, "shape",
                   "Illegal shape: 4 cells, but in an L-shape. A loop must be a rectangle.",
                   "Four cells is a good size, but look at the outline. Is it a rectangle?"),
            _judge(3, {0, 1, 3}, {0, 1, 3}, "size",
                   "Illegal size: 3 cells. Loops come in 1, 2, 4, 8. Use a loop of 2 and a loop of 1 (or two loops of 2).",
                   "Count the cells. Is that number 1, 2, 4 or 8?"),
            _judge(3, {0, 1, 2}, {0, 1, 3, 2}, "zero",
                   "Illegal: the loop of 4 contains cell 011 which is a 0.",
                   "The size and shape are fine. Look INSIDE the loop. Is every cell a 1?"),
            _judge(3, {0, 2, 4, 6}, {0, 2, 4, 6}, "ok",
                   "Legal! The loop wraps from the right edge to the left edge. That is allowed.",
                   "The loop touches both edges. Remember: the map wraps around."),
        ],
        "example": (3, vals_from(3, {0, 1, 3, 2}), [frozenset({0, 1, 2, 3})]),
        "items": [
            ("SIZE", "A loop holds 1, 2, 4, 8 (or 16) cells. Never 3, 5, 6 or 7."),
            ("SHAPE", "A rectangle, which may wrap around an edge. No diagonals, no L-shapes."),
            ("CONTENTS", "Only 1s (and X's). One 0 inside makes the loop illegal."),
        ],
    }


def _stretch(n, ones, start, why):
    return {
        "kind": "kstretch", "n": n, "ones": set(ones), "start": start, "why": why,
        "task": "Start at the START cell. Double the loop with the buttons until the next "
                "doubling would swallow a 0. Then press ENTER.",
        "hints": [
            "Point at a button (do not click yet) to preview the cells it would add. "
            "Green = allowed, red = a 0 is in the way.",
            "Keep every doubling that works. Stop when every button that is left is blocked by a 0.",
            lambda p: p.stretch_answer_text(),
        ],
    }


def _frames_stretch():
    return [
        {"cells": {0}, "loops": [(frozenset({0}), 0)],
         "caption": "Start with ONE cell: the 1 at 000. As a formula it needs all three letters: A'B'C'."},
        {"cells": {1}, "loops": [(frozenset({0, 1}), 0)],
         "caption": "Double it: the loop swallows its neighbour 001. Only C changes, so C disappears. "
                    "Formula: A'B' (two letters)."},
        {"cells": {2, 3}, "loops": [(frozenset({0, 1, 2, 3}), 0)],
         "caption": "Double again, this time across B. Now 4 cells and the formula is just A'. "
                    "A bigger loop means a shorter formula."},
        {"cells": {4, 5, 6, 7}, "bad": {5, 6, 7}, "loops": [(frozenset({0, 1, 2, 3}), 0)],
         "caption": "Double once more? That needs cells 4, 5, 6 and 7, but 5, 6 and 7 are 0 (red). "
                    "Blocked! So we stop at 4 cells, not 8."},
    ]


def _stage_stretch():
    demo_vals = vals_from(3, {0, 1, 2, 3, 4})
    return {
        "id": "k5_stretch", "title": "Stretch the loop", "sub": "why 4 and not 8?",
        "brief": [
            "Why loop at all? A bigger loop gives a SHORTER formula. "
            "So we start at one cell and DOUBLE the loop: 1, 2, 4, 8 cells.",
            "Each doubling swallows the neighbours that differ in one variable. "
            "Stop when the next doubling would swallow a 0.",
        ],
        "steps": [
            {"kind": "kdemo", "n": 3, "vals": demo_vals, "frames": _frames_stretch(),
             "task": "Watch all four views (LEFT / RIGHT keys), then press ENTER.",
             "hints": ["Use the LEFT and RIGHT arrow keys (or the buttons at the top) to change view.",
                       "Look at all four views, then press ENTER.",
                       "Press RIGHT until all four dots at the top are lit, then press ENTER."]},
            _stretch(3, {0, 1, 2, 3, 4}, 0,
                     "It stops at 4, not 8: the full map would need cells 5, 6 and 7, which are 0."),
            _stretch(4, set(range(8)), 5,
                     "All 8 cells of the top half are 1, so the loop doubles three times."),
            _stretch(4, {0, 2, 8, 10}, 0,
                     "The four corners form one loop of 4 because the map wraps around."),
        ],
        "example": (3, demo_vals, [frozenset({0, 1, 2, 3})]),
        "items": [
            ("RULE", "Start at one cell and double the loop (1, 2, 4, 8) until the next doubling "
                     "would swallow a 0."),
            ("WHY 4 NOT 8", "Doubling again would pull in a 0 cell, which is illegal."),
            ("WHY BIGGER IS BETTER", "Every doubling removes one letter from the formula."),
            ("MATH LINK", "A loop of 2^k cells on an n-variable map gives a term with n - k letters."),
        ],
    }


def _minterm_fill_step(n, ones):
    step = _fill_step(n, ones)
    step["line"] = "F = " + " + ".join(f"m{m}" for m in sorted(ones))
    step["task"] = "Each m-number is a cell number. Click every cell in the list."
    step["hints"] = [
        "m3 means the cell numbered 3. Write 3 in binary (011), then find that address on the map.",
        "Place values for three letters are 4, 2, 1. For example 6 = 4 + 2 = 110.",
        step["hints"][2],
    ]
    return step


def _stage_minterms():
    demo_vals = vals_from(3, {1, 3, 7})
    demo = [
        {"cells": {3}, "nums": True,
         "caption": "Every cell has a NUMBER: its address read as a binary number. "
                    "Cell 011 is number 3 (0 + 2 + 1)."},
        {"cells": {3}, "marks": {3: "m3"},
         "caption": "A cell's full NAME is the AND of ALL the letters, with a bar on every letter that is 0. "
                    "Cell 011 is A'BC. This one-cell product is called a MINTERM: m3."},
        {"cells": {1, 3, 7}, "marks": {1: "m1", 3: "m3", 7: "m7"},
         "caption": "F is 1 on three cells, so F = m1 + m3 + m7. "
                    "Short form: F = Sum m(1, 3, 7)."},
        {"cells": set(), "nums": True,
         "caption": "A minterm is 1 for exactly ONE input row. A 3-letter map has 2^3 = 8 cells, "
                    "so 8 minterms: m0 to m7."},
    ]
    q_cell = _kmap_choice(
        3, vals_from(3, {5}), [],
        "The highlighted cell has the address ABC = 101. Which minterm is it?",
        "m5", [("m3", "m3"), ("m5", "m5"), ("m6", "m6"), ("m7", "m7")],
        "Read the address as a binary number.",
        "101 = 4 + 0 + 1 = 5, so this cell is m5.",
        ["Read the address 101 as a binary number.",
         "Place values for three letters are 4, 2, 1. So 101 = 4 + 0 + 1.",
         "The answer is m5."],
        highlight={5})
    q_name = {
        "kind": "choice", "visual": "none",
        "q": "Which product is minterm m6 of the letters A, B, C?",
        "options": [("AB'C'", "a"), ("ABC'", "b"), ("A'BC", "c"), ("ABC", "d")],
        "correct": "b", "task": "Turn 6 into 3 bits, then write the letters.",
        "ok": "6 = 110, so A = 1, B = 1, C = 0 gives ABC'.",
        "hints": ["First write 6 in binary using 3 bits.",
                  "6 = 110, so A = 1, B = 1, C = 0. A 1 stays plain and a 0 gets a bar.",
                  "The answer is ABC'."],
    }
    q_count = {
        "kind": "choice", "visual": "none",
        "q": "How many minterms does a 4-letter map (A, B, C, D) have?",
        "options": [("8", "8"), ("12", "12"), ("16", "16"), ("32", "32")],
        "correct": "16", "task": "There is one minterm for every cell.",
        "ok": "4 letters give 2^4 = 16 cells, so 16 minterms (m0 to m15).",
        "hints": ["There is one minterm for every cell of the map.",
                  "A 4-letter map is 4 cells wide and 4 cells tall.",
                  "The answer is 16, because 2^4 = 16."],
    }
    return {
        "id": "k3_minterms", "title": "Minterms", "sub": "the name of a cell",
        "brief": [
            "Every cell on the map has a number and a full name. The full name is called a MINTERM.",
            "You need this word to read maps later. A minterm is just one cell written as an AND "
            "of all the letters.",
        ],
        "steps": [
            {"kind": "kdemo", "n": 3, "vals": demo_vals, "frames": demo,
             "task": "Watch all four views (LEFT / RIGHT keys), then press ENTER.",
             "hints": ["Use the LEFT and RIGHT arrow keys (or the buttons at the top) to change view.",
                       "Look at all four views, then press ENTER.",
                       "Press RIGHT until all four dots at the top are lit, then press ENTER."]},
            q_cell, q_name,
            _minterm_fill_step(3, {0, 3, 5, 6}),
            q_count,
        ],
        "example": (3, vals_from(3, {0, 3, 5, 6}), []),
        "items": [
            ("MINTERM", "The AND of ALL the letters for one cell, with a bar on each letter that is 0. "
                        "Cell 011 = A'BC = m3."),
            ("CELL NUMBER", "Read the address as binary: 101 = 4 + 0 + 1 = 5, so it is m5."),
            ("SHORT FORM", "F = m1 + m3 + m7 is written F = Sum m(1, 3, 7)."),
            ("MATH LINK", "n letters give 2^n cells, so 2^n minterms (4 letters: 16)."),
        ],
    }


def _frames_wrap():
    return [
        {"cells": {0, 2}, "wrap": "h",
         "caption": "The left edge touches the right edge. Cells 0000 and 0010 are neighbours: only C changes."},
        {"cells": {0, 8}, "wrap": "v",
         "caption": "The top edge touches the bottom edge. Cells 0000 and 1000 are neighbours: only A changes."},
        {"cells": {0, 2, 8, 10}, "loops": [(frozenset({0, 2, 8, 10}), 0)],
         "caption": "So the four corners are neighbours in a ring. They form ONE loop of 4."},
        {"cells": set(), "caption": "Imagine rolling the map into a tube, then bending the tube into a doughnut. "
                                    "That is why edges touch."},
    ]


def _loops_step(n, vals, mode, task, hints, show_terms=False, sevenseg=None):
    return {"kind": "kloops", "n": n, "vals": vals, "mode": mode, "task": task,
            "hints": hints, "show_terms": show_terms, "sevenseg": sevenseg}


LOOP_HINTS = [
    "Click every cell of ONE loop, then press L (or the LOOP IT button). Make each loop as big as you can.",
    "Every cell you must cover needs to be inside a loop. Use as FEW loops as you can. Loops may overlap.",
    lambda p: p.solution_text(),
]


def _stage_wrap():
    return {
        "id": "k6_wrap", "title": "Wrap-around", "sub": "edges touch, corners join",
        "brief": [
            "The map has no real edges. The left side touches the right side, "
            "and the top touches the bottom.",
            "Cover every 1 with the fewest and biggest loops. Loops may overlap.",
        ],
        "steps": [
            {"kind": "kdemo", "n": 4, "vals": vals_from(4, set()), "frames": _frames_wrap(),
             "task": "Watch all four views (LEFT / RIGHT keys), then press ENTER.",
             "hints": [
                 "The demo changes by itself. You can also use the LEFT and RIGHT arrow keys.",
                 "Look at all four pictures, then press ENTER.",
                 "Press RIGHT until all four dots at the top are lit, then press ENTER.",
             ]},
            _loops_step(3, vals_from(3, {0, 2, 4, 5, 6}), "ones",
                        "Loop all the 1s with the fewest, biggest loops. One loop wraps around!", LOOP_HINTS),
            _loops_step(4, vals_from(4, {0, 2, 8, 10}), "ones",
                        "Loop all the 1s. Where are the four corners?", LOOP_HINTS),
            _loops_step(4, vals_from(4, {0, 1, 2, 3, 8, 9, 10, 11, 13}), "ones",
                        "Loop all the 1s. The top row and bottom row are neighbours.", LOOP_HINTS),
        ],
        "example": (4, vals_from(4, {0, 2, 8, 10}), [frozenset({0, 2, 8, 10})]),
        "items": [
            ("RULE", "The map wraps: left touches right, top touches bottom."),
            ("CORNERS", "The four corners of a 4-variable map form ONE loop of 4 (B'D')."),
            ("GOAL", "Cover every 1 with the fewest, biggest loops. Overlap is fine."),
        ],
    }


def _term_step(n, loop, mode, vals, task=None):
    cells = frozenset(loop)
    return {
        "kind": "kterm", "n": n, "loop": cells, "mode": mode, "vals": vals,
        "task": task or "For each letter choose: stays 1 (A), stays 0 (A'), or changes (drop).",
        "hints": [
            "Look at the addresses of the loop cells (listed on the right). Check ONE letter at a time.",
            ("Is the letter the same in every cell? Always 1: pick the plain letter (A). "
             "Always 0: pick the letter with a bar (A'). It changes: pick drop.") if mode == "sop" else
            ("This is a loop of 0s, so it works the other way round. Always 0: pick the plain letter (A). "
             "Always 1: pick the letter with a bar (A'). It changes: pick drop."),
            lambda p: "The term is " + term_str(p.step["loop"], p.step["n"], p.step["mode"]) + ".",
        ],
    }


def _stage_sop():
    vals_a = vals_from(3, {1, 3, 6, 7})
    loops_a = [frozenset({1, 3}), frozenset({6, 7})]
    opts_a, ans_a = _expr_options(3, loops_a, "sop", 11)
    vals_b = vals_from(4, {0, 1, 2, 3, 10, 11})
    loops_b = [frozenset({0, 1, 2, 3}), frozenset({2, 3, 10, 11})]
    opts_b, ans_b = _expr_options(4, loops_b, "sop", 12)
    sop_hints = [
        "Read each loop as a product term (letters written next to each other), then join the terms with +.",
        "For each loop: a letter that changes is dropped. A letter that is always 1 stays plain. A letter that is always 0 gets a bar.",
    ]
    return {
        "id": "k7_sop", "title": "Loop to term to SOP", "sub": "reading the loops",
        "brief": [
            "Read each loop with three questions per variable: stays 1, stays 0, or changes?",
            "Stays 1: write the letter. Stays 0: write it with a bar. Changes: drop it. "
            "AND the letters, then OR the terms: that is SOP (sum of products).",
        ],
        "steps": [
            _term_step(3, {4, 5}, "sop", vals_from(3, {4, 5})),
            _term_step(4, {0, 2, 8, 10}, "sop", vals_from(4, {0, 2, 8, 10})),
            _kmap_choice(3, vals_a, [(l, i) for i, l in enumerate(loops_a)],
                         "Which SOP expression do these two loops give?", ans_a, opts_a,
                         "Read each loop, then join the terms with +.",
                         f"F = {ans_a}", sop_hints + [f"The answer is {ans_a}."]),
            _kmap_choice(4, vals_b, [(l, i) for i, l in enumerate(loops_b)],
                         "Which SOP expression do these two loops give?", ans_b, opts_b,
                         "Read each loop, then join the terms with +.",
                         f"F = {ans_b}", sop_hints + [f"The answer is {ans_b}."]),
        ],
        "example": (3, vals_a, loops_a),
        "items": [
            ("RECIPE", "Per variable: stays 1 = letter, stays 0 = letter with a bar, changes = dropped."),
            ("SOP", "AND the letters inside a loop, OR the loops together. Here: " + ans_a + "."),
            ("MATH LINK", "A loop of 2^k cells on n variables leaves n - k letters. "
                          "Bigger loop = shorter term."),
        ],
    }


def _stage_pos():
    f_vals = vals_from(3, {2, 3, 4, 5, 6, 7})
    zero_loop = [(frozenset({0, 1}), 0)]
    demo = [
        {"cells": {2, 3, 4, 5, 6, 7}, "loops": [(frozenset({2, 3, 6, 7}), 0), (frozenset({4, 5, 6, 7}), 1)],
         "caption": "SOP: loop the 1s. The loops give B and A, so F = A + B."},
        {"cells": {0}, "marks": {0: "M0"},
         "caption": "POS: look at the 0s instead. A 0 cell has a MAXTERM: the OR of ALL the letters. "
                    "Cell 000 gives (A + B + C). Name: M0."},
        {"cells": {0, 1}, "marks": {0: "M0", 1: "M1"},
         "caption": "Rule: a letter that is 0 stays plain, a letter that is 1 gets a bar. "
                    "Cell 001 gives (A + B + C') = M1. A minterm is the opposite: there 1 stays plain."},
        {"cells": {0, 1}, "loops": zero_loop,
         "caption": "Neighbouring 0s merge just like 1s: (A + B + C)(A + B + C') = (A + B). "
                    "C changes, so C cancels."},
        {"cells": {0, 1}, "loops": zero_loop,
         "caption": "So read a 0-loop as a SUM: stays 0 = plain letter, stays 1 = barred letter. "
                    "(De Morgan flips the loop A'B' of F' into A + B.)"},
        {"cells": set(),
         "caption": "Same answer both ways: A + B. Short forms: F = Sum m(2, 3, 4, 5, 6, 7) and "
                    "F = Prod M(0, 1). Join the sums with AND. POS is handy when the 0s are fewer."},
    ]
    pos_vals = vals_from(3, {2, 3, 4, 6, 7})
    zloops = [frozenset({0, 1}), frozenset({1, 5})]
    opts_p, ans_p = _expr_options(3, zloops, "pos", 21)
    cmp_vals = vals_from(3, {1, 2, 4, 5, 6, 7})
    assert term_str({5}, 3, "pos") == "(A' + B + C')"
    max_opts = [("(A' + B + C')", "ok"), ("(A + B' + C)", "w1"), ("AB'C", "w2"), ("(A' + B' + C')", "w3")]
    random.Random(5).shuffle(max_opts)
    q_max = _kmap_choice(
        3, pos_vals, [], "The highlighted cell is a 0 (ABC = 101). What is its maxterm?",
        "ok", max_opts, "Write the OR (sum) of all the letters for this 0 cell.",
        "101: A = 1 gets a bar, B = 0 stays plain, C = 1 gets a bar: (A' + B + C') = M5.",
        ["A maxterm is a SUM (letters joined with +). A letter that is 0 stays plain, a letter that is 1 gets a bar.",
         "ABC = 101: A is 1 (bar), B is 0 (plain), C is 1 (bar).",
         "The answer is (A' + B + C')."],
        highlight={5})
    q_prod = {
        "kind": "choice", "visual": "none",
        "q": "F = Prod M(0, 1, 5). On which cells is F equal to 0?",
        "options": [("0, 1 and 5", "z"), ("2, 3, 4, 6, 7", "o"), ("Only cell 5", "c"), ("All 8 cells", "a")],
        "correct": "z", "task": "Prod M lists the zeros.",
        "ok": "Each M is a cell where F is 0. Sum m lists the 1s, Prod M lists the 0s.",
        "hints": ["Each M in the list is a cell where F is 0.",
                  "Sum m lists the cells where F = 1. Prod M lists the cells where F = 0.",
                  "F is 0 on cells 0, 1 and 5."],
    }
    return {
        "id": "k8_pos", "title": "POS", "sub": "loop the zeros",
        "brief": [
            "POS means product of sums. Loop the 0s instead of the 1s. "
            "Every 0 cell has a MAXTERM: an OR of all the letters.",
            "Why it works: the 0-loops give F' (the opposite). De Morgan's theorem flips them back "
            "into sums that you AND together.",
        ],
        "steps": [
            {"kind": "kdemo", "n": 3, "vals": f_vals, "frames": demo,
             "task": "Watch all six views (LEFT / RIGHT keys), then press ENTER.",
             "hints": ["Use the LEFT and RIGHT arrow keys (or the buttons at the top) to change view.",
                       "Look at every view, then press ENTER.",
                       "Press RIGHT until all six dots at the top are lit, then press ENTER."]},
            q_max, q_prod,
            _term_step(3, {0, 1}, "pos", vals_from(3, {2, 3, 4, 5, 6, 7}),
                       "Read this loop of 0s as a SUM: stays 0 = letter, stays 1 = letter with a bar, changes = drop."),
            _term_step(4, {5, 7, 13, 15}, "pos", vals_from(4, set(range(16)) - {5, 7, 13, 15}),
                       "Read this loop of 0s as a SUM. The 0s are the highlighted cells."),
            _loops_step(3, pos_vals, "zeros",
                        "Loop the 0s this time (the grey cells), with the fewest, biggest loops.",
                        LOOP_HINTS, show_terms=True),
            _kmap_choice(3, pos_vals, [(l, i) for i, l in enumerate(zloops)],
                         "Which POS expression do these loops of 0s give?", ans_p, opts_p,
                         "Read each 0-loop as a sum, then AND the sums.",
                         f"F = {ans_p}",
                         ["Read each loop of 0s as a SUM: stays 0 = plain, stays 1 = barred, changes = dropped.",
                          "Then AND the brackets together (write them next to each other).",
                          f"The answer is {ans_p}."]),
            _kmap_choice(3, cmp_vals, [], "Count loops: this map needs 3 loops of 1s (SOP). How many loops "
                                          "of 0s does POS need? Which form is shorter?",
                         "POS", [("SOP", "SOP"), ("POS", "POS"), ("Same", "same")],
                         "Pick the form that needs fewer loops.",
                         "The 0s at 000 and 011 are two single cells, so POS needs 2 loops. SOP needs 3.",
                         ["Count the loops of 1s (SOP), then count the loops of 0s (POS).",
                          "The two 0s are not neighbours, so they make two loops. The 1s need three.",
                          "The answer is POS."]),
        ],
        "example": (3, pos_vals, zloops),
        "items": [
            ("RECIPE", "Loop the 0s. Stays 0 = letter, stays 1 = letter with a bar, changes = dropped. "
                       "OR the letters in a loop, AND the loops."),
            ("MAXTERM", "The OR of ALL letters for one 0 cell: a 0 stays plain, a 1 gets a bar. "
                        "Cell 001 = (A + B + C') = M1."),
            ("SHORT FORM", "F = Prod M(0, 1, 5) lists the cells where F = 0. Sum m lists the 1s."),
            ("WHY (DE MORGAN)", "The 0-loops give F'. De Morgan turns that into sums and flips every bar. "
                                "Here F = " + ans_p + "."),
        ],
    }


def _stage_dc():
    dc_vals = vals_from(4, {1, 3, 7, 11, 15}, {0, 2, 5})
    demo = [
        {"cells": {0, 2, 5}, "caption": "X means DON'T CARE: that input never happens, so we may treat it as 0 "
                                        "or 1, whichever helps. Yellow cells are X."},
        {"cells": {3, 7, 11, 15}, "loops": [(frozenset({3, 7, 11, 15}), 0)],
         "caption": "Use an X as a 1 only if it lets a loop grow bigger. This loop needs no X."},
        {"cells": {0, 1, 2, 3}, "loops": [(frozenset({0, 1, 2, 3}), 1)],
         "caption": "Here two X's help: the loop of 4 is better than a loop of only 1 and 3."},
        {"cells": {5}, "caption": "The X at 0101 is not needed here, and that is fine. You never have to "
                                  "cover every X, and you never loop X's on their own."},
    ]
    seg_vals = vals_from(4, {0, 2, 6, 8}, set(range(10, 16)))
    seg_loops = [frozenset({0, 2, 8, 10}), frozenset({2, 6, 10, 14})]
    seg_expr = expr_str(seg_loops, 4, "sop")
    seg_opts = [("B'D' + CD'", "ok"), ("B'D' + CD", "w1"), ("BD' + C'D'", "w2"), ("B'D + CD'", "w3")]
    assert seg_expr == "B'D' + CD'", seg_expr
    return {
        "id": "k9_dc", "title": "Don't cares + boss", "sub": "X cells and the 7-segment display",
        "brief": [
            "X means DON'T CARE: that input can never happen, so it may count as 0 or 1.",
            "Use an X as a 1 only when it makes a loop bigger. Boss: simplify one segment of a "
            "7-segment display. BCD inputs 10 to 15 never occur, so they are X.",
        ],
        "steps": [
            {"kind": "kdemo", "n": 4, "vals": dc_vals, "frames": demo,
             "task": "Watch all four views (LEFT / RIGHT keys), then press ENTER.",
             "hints": ["Use the LEFT and RIGHT arrow keys (or the buttons at the top) to change view.",
                       "Look at all four views, then press ENTER.",
                       "Press RIGHT until all four dots at the top are lit, then press ENTER."]},
            _loops_step(4, dc_vals, "ones",
                        "Loop the 1s. Use the X's only if they make a loop bigger.",
                        LOOP_HINTS + [], show_terms=True),
            {"kind": "choice", "visual": "none",
             "q": "Do you have to put EVERY X inside a loop?",
             "options": [("YES, all of them", "yes"), ("NO, only if it helps", "no")],
             "correct": "no", "task": "True or false about X cells.",
             "ok": "X means 'don't care'. Use it only when it enlarges a loop.",
             "hints": ["Think about what 'don't care' means.",
                       "An X is optional: it can be 0 or 1, whichever is more useful.",
                       "The answer is NO."]},
            {"kind": "choice", "visual": "none",
             "q": "A loop contains only X cells and no 1s. Is it useful?",
             "options": [("YES, it simplifies", "yes"), ("NO, it covers nothing", "no")],
             "correct": "no", "task": "Think about what a loop is for.",
             "ok": "A loop exists to cover 1s. A loop of only X's adds a term for nothing.",
             "hints": ["What is a loop supposed to cover?",
                       "Loops cover 1s. X's are only helpers.",
                       "The answer is NO."]},
            _loops_step(4, seg_vals, "ones",
                        "BOSS: segment e lights for digits 0, 2, 6, 8. Loop it. Inputs 10-15 are X.",
                        LOOP_HINTS, show_terms=True, sevenseg="e"),
            _kmap_choice(4, seg_vals, [(l, i) for i, l in enumerate(seg_loops)],
                         "Segment e of the display is lit by which expression?", "ok", seg_opts,
                         "Read each loop, then join the terms with +.",
                         "e = B'D' + CD'. The X cells made both loops bigger.",
                         ["Read each loop as a product term, then join them with +.",
                          "The corner loop gives B'D'. The loop down the CD' column gives CD'.",
                          "The answer is B'D' + CD'."]),
        ],
        "example": (4, seg_vals, seg_loops),
        "items": [
            ("X RULES", "Treat an X as 1 only if it makes a loop bigger. You need not cover every X. "
                        "Never loop X's alone."),
            ("BCD", "Inputs 10 to 15 never occur in BCD, so all six cells are X."),
            ("BOSS RESULT", "7-segment segment e lights for 0, 2, 6, 8: e = B'D' + CD'."),
        ],
    }


def build_kmap_stages():
    return [_stage_neighbours(), _stage_fill(), _stage_minterms(), _stage_legal(),
            _stage_stretch(), _stage_wrap(), _stage_sop(), _stage_pos(), _stage_dc()]


# ------------------------------------------------------------------
# DRAWING THE MAP
# ------------------------------------------------------------------
def draw_kmap(screen, fonts, origin, cell, n, vals=None, selected=(), loops=(),
              highlight=(), cursor=None, nums=False, marks=None, bad=()):
    """Draw a K-map. Returns {minterm: Rect}. vals: minterm -> 0/1/X (None hides)."""
    f_body, f_small, f_tiny = fonts
    x0, y0 = origin
    rows, cols = len(row_codes(n)), len(col_codes(n))
    cb = col_bits(n)
    rb = n - cb
    rects = {}

    # labels sit in the margin above / left of the grid
    corner = f"{VARS[:rb]}\\{VARS[rb:n]}"
    img = f_tiny.render(corner, True, CYAN)
    screen.blit(img, img.get_rect(midright=(x0 - 8, y0 - 14)))
    for c, code in enumerate(col_codes(n)):
        img = f_small.render(format(code, f"0{cb}b"), True, YELLOW)
        screen.blit(img, img.get_rect(center=(x0 + c * cell + cell // 2, y0 - 14)))
    for r, code in enumerate(row_codes(n)):
        img = f_small.render(format(code, f"0{rb}b"), True, YELLOW)
        screen.blit(img, img.get_rect(midright=(x0 - 8, y0 + r * cell + cell // 2)))

    for r in range(rows):
        for c in range(cols):
            m = cell_minterm(n, r, c)
            rect = pygame.Rect(x0 + c * cell, y0 + r * cell, cell, cell)
            rects[m] = rect
            fill = (22, 40, 58)
            if m in highlight:
                fill = (36, 78, 62)
            if m in bad:
                fill = (104, 38, 44)
            pygame.draw.rect(screen, fill, rect)
            pygame.draw.rect(screen, (70, 96, 116), rect, 1)
            v = None if vals is None else vals.get(m)
            if v is not None and not (marks and m in marks):
                txt, col = {0: ("0", (120, 136, 150)), 1: ("1", GREEN), X: ("X", YELLOW)}[v]
                img = f_body.render(txt, True, col)
                screen.blit(img, img.get_rect(center=rect.center))
            if nums:
                img = f_tiny.render(str(m), True, (110, 130, 146))
                screen.blit(img, (rect.x + 4, rect.y + 3))
            if marks and m in marks:
                img = f_small.render(marks[m], True, WHITE)
                screen.blit(img, img.get_rect(center=rect.center))

    # loops: a soft coloured tint plus a coloured outline, so they are easy to see
    for cells, idx in loops:
        color = LOOP_COLORS[idx % len(LOOP_COLORS)]
        inset = 3 + (idx % 3) * 3
        for m in cells:
            full = rects[m]
            tint = pygame.Surface(full.size, pygame.SRCALPHA)
            tint.fill((color[0], color[1], color[2], 34))
            screen.blit(tint, full.topleft)
            rect = full.inflate(-2 * inset, -2 * inset)
            pygame.draw.rect(screen, color, rect, 3, border_radius=6)
    for m in selected:
        pygame.draw.rect(screen, YELLOW, rects[m], 4)
        glow = pygame.Surface(rects[m].size, pygame.SRCALPHA)
        glow.fill((255, 214, 86, 55))
        screen.blit(glow, rects[m].topleft)
    if cursor is not None and cursor in rects:
        pygame.draw.rect(screen, CYAN, rects[cursor].inflate(4, 4), 2, border_radius=3)
    return rects


def draw_seven_seg(screen, x, y, lit, size=1.0):
    """A small 7-segment digit with the given segments lit (letters a-g)."""
    w, h, t = int(46 * size), int(70 * size), max(4, int(7 * size))
    segs = {
        "a": (x + t, y, w - 2 * t, t),
        "b": (x + w - t, y + t, t, h // 2 - t),
        "c": (x + w - t, y + h // 2, t, h // 2 - t),
        "d": (x + t, y + h - t, w - 2 * t, t),
        "e": (x, y + h // 2, t, h // 2 - t),
        "f": (x, y + t, t, h // 2 - t),
        "g": (x + t, y + h // 2 - t // 2, w - 2 * t, t),
    }
    for name, rect in segs.items():
        on = name in lit
        pygame.draw.rect(screen, (255, 90, 70) if on else (46, 54, 66), rect, border_radius=2)


# ------------------------------------------------------------------
# THE PUZZLE
# ------------------------------------------------------------------
class BasicKarnaughPuzzle(BasicGatesPuzzle):
    """Nine-stage beginner course on Karnaugh maps (SOP, POS, don't cares)."""

    COURSE_TITLE = "BASIC LEVEL  -  KARNAUGH MAPS"
    LEGEND_EXTRA = dict(BasicGatesPuzzle.LEGEND_EXTRA, **{
        "kinspect": "click two cells (or arrows + SPACE)",
        "kfill": "click cells to flip 0 / 1 (or arrows + SPACE)",
        "kpick": "click the cell (or arrows + SPACE)",
        "kstretch": "press A B C D to stretch or shrink",
        "kloops": "click cells, L = loop them, U = undo, C = clear",
        "kterm": "click a choice or press A B C D to cycle",
        "kdemo": "LEFT / RIGHT to move, ENTER when you've seen all",
    })

    # ---- layout constants (all screens are built top-down from these) ----
    PAD = 20            # left / right margin inside WORK
    LABEL_GAP = 30      # room above the grid for the column labels
    FOOT = 12           # gap kept free at the very bottom

    def _make_stages(self):
        return build_kmap_stages()

    def __init__(self, notebook=None):
        self.demo_clock = 0.0
        super().__init__(notebook)
        self.fonts = (self.f_body, self.f_small, self.f_tiny)

    # ---------------- step state ----------------
    def _enter_step(self):
        super()._enter_step()
        step, st = self.step, self.st
        kind = step["kind"]
        n = step.get("n", 3)
        st["cursor"] = 0
        if kind == "kinspect":
            st.update(sel=[], nb=set(), diag=set(), lines=["Click two cells to compare them."])
        elif kind == "kfill":
            st["cells"] = {m: 0 for m in range(1 << n)}
        elif kind == "kpick":
            st["pick"] = None
        elif kind == "kloops":
            st.update(sel=set(), loops=[])
        elif kind == "kstretch":
            st.update(free=0, blocked=set(),
                      info="Press a button (or its letter) to double the loop. "
                           "Point at a button to preview.")
        elif kind == "kterm":
            st["states"] = [None] * n
        elif kind == "kdemo":
            st.update(frame=0, seen=1)
            self.demo_clock = 0.0

    # helper text used by hints
    def solution_text(self):
        step = self.step
        n = step["n"]
        loops = solution_loops(n, step["vals"], step["mode"])
        parts = []
        for i, loop in enumerate(loops):
            parts.append(f"Loop {i + 1}: " + ", ".join(bits(m, n) for m in sorted(loop)))
        return "One possible answer.  " + ".  ".join(parts) + "."

    def fill_answer_text(self):
        n = self.step["n"]
        cells = []
        for m in sorted(self.step["ones"]):
            r, c = minterm_cell(n, m)
            rb = n - col_bits(n)
            cells.append(f"row {format(row_codes(n)[r], f'0{rb}b')} / column "
                         f"{format(col_codes(n)[c], f'0{col_bits(n)}b')}")
        return "Click these cells: " + "; ".join(cells) + "."

    def pick_answer_text(self):
        n = self.step["n"]
        r, c = minterm_cell(n, self.step["target"])
        rb = n - col_bits(n)
        return (f"Click row {format(row_codes(n)[r], f'0{rb}b')}, column "
                f"{format(col_codes(n)[c], f'0{col_bits(n)}b')}.")

    def stretch_answer_text(self):
        step = self.step
        n, start = step["n"], step["start"]
        allowed = set(step["ones"])
        primes = [p for p in prime_loops(n, allowed, allowed) if start in p]
        best = max(primes, key=len)
        free = analyse(best, n)["free"]
        letters = [VARS[i] for i in range(n) if free & (1 << (n - 1 - i))]
        return "Press these letters: " + " and ".join(letters) + ". Then press ENTER."

    def _loop_cells(self):
        st, step = self.st, self.step
        start, free = step["start"], st["free"]
        return cube_cells(start, free)

    # ---------------- events (unchanged) ----------------
    def _on_key(self, event):
        key = event.key
        if self.phase == "done" or key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_h):
            return super()._on_key(event)
        kind = self.step["kind"]
        st = self.st
        n = self.step.get("n", 3)

        if kind in ("kinspect", "kfill", "kpick", "kloops"):
            rows, cols = len(row_codes(n)), len(col_codes(n))
            r, c = minterm_cell(n, st["cursor"])
            moved = True
            if key == pygame.K_UP:
                r = (r - 1) % rows
            elif key == pygame.K_DOWN:
                r = (r + 1) % rows
            elif key == pygame.K_LEFT:
                c = (c - 1) % cols
            elif key == pygame.K_RIGHT:
                c = (c + 1) % cols
            else:
                moved = False
            if moved:
                st["cursor"] = cell_minterm(n, r, c)
                return
            if key == pygame.K_SPACE:
                self._on_action(("kcell", st["cursor"]))
                return
        if kind == "kloops":
            if key == pygame.K_l:
                self._on_action(("kloop",))
            elif key in (pygame.K_u, pygame.K_BACKSPACE):
                self._on_action(("kundo",))
            elif key == pygame.K_c:
                self._on_action(("kclear",))
            return
        if kind == "kstretch":
            if pygame.K_a <= key <= pygame.K_d:
                idx = key - pygame.K_a
                if idx < n:
                    self._on_action(("kstretch", idx))
            return
        if kind == "kterm":
            if pygame.K_a <= key <= pygame.K_d:
                idx = key - pygame.K_a
                if idx < n:
                    cur = st["states"][idx]
                    order = ["plain", "bar", "drop"]
                    nxt = order[0] if cur is None else order[(order.index(cur) + 1) % 3]
                    st["states"][idx] = nxt
            return
        if kind == "kdemo":
            frames = len(self.step["frames"])
            if key == pygame.K_RIGHT:
                st["frame"] = (st["frame"] + 1) % frames
            elif key == pygame.K_LEFT:
                st["frame"] = (st["frame"] - 1) % frames
            st["seen"] = max(st["seen"], st["frame"] + 1)
            self.demo_clock = 0.0
            return
        if kind in ("kinspect", "kfill", "kpick"):
            return
        return super()._on_key(event)

    def _on_action(self, action):
        name = action[0]
        st = self.st
        if name == "kframe":
            self._on_action_frame(action[1])
            return
        step = self.step if self.phase == "play" else None
        n = step.get("n", 3) if step else 3

        if name == "kcell" and step is not None:
            m = action[1]
            st["cursor"] = m
            kind = step["kind"]
            if kind == "kinspect":
                if len(st["sel"]) >= 2:
                    st["sel"] = []
                if m not in st["sel"]:
                    st["sel"].append(m)
                if len(st["sel"]) == 2:
                    self._inspect_pair(*st["sel"])
                else:
                    st["lines"] = [f"Cell {cell_name(m, n)} chosen. Now click a second cell."]
            elif kind == "kfill":
                st["cells"][m] ^= 1
            elif kind == "kpick":
                st["pick"] = m
            elif kind == "kloops":
                if m in st["sel"]:
                    st["sel"].discard(m)
                else:
                    st["sel"].add(m)
            return
        if name == "kloop":
            self._make_loop()
            return
        if name == "kundo":
            if st.get("loops"):
                st["loops"].pop()
                self._say("Last loop removed.", True)
            return
        if name == "kclear":
            st["sel"] = set()
            return
        if name == "kstretch":
            self._stretch(action[1])
            return
        if name == "kstate":
            st["states"][action[1]] = action[2]
            return
        return super()._on_action(action)

    def _inspect_pair(self, a, b):
        n = self.step["n"]
        vals = self.step["vals"]
        st = self.st
        diff = a ^ b
        lines = [f"{cell_name(a, n)}  and  {cell_name(b, n)}"]
        pair = frozenset((a, b))
        if popcount(diff) == 1:
            var = VARS[n - 1 - (diff.bit_length() - 1)]
            st["nb"].add(pair)
            lines.append(f"They differ in ONE variable ({var}), so they are NEIGHBOURS.")
            if vals[a] == 1 and vals[b] == 1:
                term = term_str([a, b], n)
                lines.append(f"Both are 1: {cell_name(a, n)} + {cell_name(b, n)} = {term}.")
                lines.append(f"{var} cancels, because {var}' + {var} = 1.")
            else:
                lines.append("One of them is 0, so there is nothing to merge here.")
        else:
            st["diag"].add(pair)
            lines.append(f"They differ in {popcount(diff)} variables, so they are NOT neighbours (diagonal).")
        st["lines"] = lines

    def _make_loop(self):
        step, st = self.step, self.st
        n = step["n"]
        allowed, _t = sets_for(n, step["vals"], step["mode"])
        cells = frozenset(st["sel"])
        reason = illegal_reason(cells, n, allowed, step["mode"])
        if reason:
            self._say(reason, False, 7.0)
            return
        if cells in st["loops"]:
            self._say("You already made that loop.", False)
            return
        st["loops"].append(cells)
        st["sel"] = set()
        self._say(f"Loop {len(st['loops'])} added ({len(cells)} cells).", True)

    def _stretch(self, idx):
        step, st = self.step, self.st
        n = step["n"]
        bit = 1 << (n - 1 - idx)
        name = VARS[idx]
        st["blocked"] = set()
        if st["free"] & bit:
            st["free"] &= ~bit
            st["info"] = f"Undid the doubling across {name}."
            return
        trial = st["free"] | bit
        cells = cube_cells(step["start"], trial)
        blocked = sorted(m for m in cells if m not in step["ones"])
        if blocked:
            st["blocked"] = {m for m in cells if m not in step["ones"]}
            st["info"] = (f"Blocked! Doubling across {name} would swallow cell "
                          f"{bits(blocked[0], n)}, and that is a 0 (shown in red).")
            self._say(st["info"], False, 6.0)
            return
        st["free"] = trial
        st["info"] = (f"Doubled across {name}: the loop now has {len(cells)} cells. "
                      f"{name} changes inside the loop, so {name} disappears from the formula.")
        self._say("", True)

    # ---------------- checking (unchanged) ----------------
    def _check(self):
        step, st = self.step, self.st
        kind = step["kind"]
        n = step.get("n", 3)

        if kind == "kinspect":
            if len(st["nb"]) >= 2 and len(st["diag"]) >= 1:
                self._right("Neighbours differ in one variable.")
            else:
                self._say(f"Found {len(st['nb'])}/2 neighbour pairs and {len(st['diag'])}/1 diagonal pair.", False)
        elif kind == "kfill":
            ones = {m for m, v in st["cells"].items() if v == 1}
            if ones == step["ones"]:
                self._right()
            else:
                bad = sorted(ones ^ step["ones"])
                self._wrong(f"{len(bad)} cell(s) wrong. Check the cell for {bits(bad[0], n)}.")
        elif kind == "kpick":
            if st["pick"] is None:
                self._say("Click a cell first.", False)
            elif st["pick"] == step["target"]:
                self._right()
            else:
                self._wrong(f"That cell is {bits(st['pick'], n)}. Read the row and column labels again.")
        elif kind == "kloops":
            ok, msg = check_loops(n, st["loops"], step["vals"], step["mode"])
            if ok:
                self._right("Fewest, biggest loops.")
            else:
                self._wrong(msg)
        elif kind == "kstretch":
            cells = self._loop_cells()
            primes = [p for p in prime_loops(n, set(step["ones"]), set(step["ones"])) if step["start"] in p]
            best = max(len(p) for p in primes)
            if len(cells) == best:
                self._right(step["why"])
            else:
                self._wrong(f"The loop has {len(cells)} cells but it can still be stretched. Try another letter.")
        elif kind == "kterm":
            want = self._expected_states()
            if None in st["states"]:
                self._say("Choose something for every variable first.", False)
            elif st["states"] == want:
                self._right("Term: " + term_str(step["loop"], n, step["mode"]) + ".")
            else:
                self._wrong("Not quite. Compare the loop's cells: which letters stay the same, which change?")
        elif kind == "kdemo":
            if st["seen"] >= len(step["frames"]):
                self._advance("")
            else:
                self._say(f"Watch every view first ({st['seen']}/{len(step['frames'])}).", False)
        else:
            super()._check()

    def _expected_states(self):
        step = self.step
        n = step["n"]
        info = analyse(step["loop"], n)
        out = []
        for i in range(n):
            bit = 1 << (n - 1 - i)
            if not (info["fixed_mask"] & bit):
                out.append("drop")
            else:
                one = bool(info["fixed_val"] & bit)
                if step["mode"] == "sop":
                    out.append("plain" if one else "bar")
                else:
                    out.append("bar" if one else "plain")
        return out

    # ---------------- update (unchanged) ----------------
    def update(self, dt):
        super().update(dt)
        if self.phase == "play" and self.step["kind"] == "kdemo":
            self.demo_clock += dt
            if self.demo_clock >= 4.0:
                self.demo_clock = 0.0
                frames = len(self.step["frames"])
                self.st["frame"] = (self.st["frame"] + 1) % frames
                self.st["seen"] = max(self.st["seen"], self.st["frame"] + 1)

    # ------------------------------------------------------------------
    # DRAWING HELPERS  (top-down layout, map shrinks to fit)
    # ------------------------------------------------------------------
    def _cell_size(self, n, bottom=None, top=None, maxw=None):
        rows = len(row_codes(n))
        cols = len(col_codes(n))
        size = {2: 84, 3: 68, 4: 58}[n]
        if bottom is not None and top is not None:
            size = min(size, max(30, (bottom - top) // rows))
        if maxw:
            size = min(size, max(30, maxw // cols))
        return size

    def _map_origin(self, n, cell, top=None):
        x0 = WORK.x + 78
        y0 = WORK.y + 112 if top is None else top
        return x0, y0

    def draw(self, screen):
        self._screen = screen
        super().draw(screen)

    def _text_block(self, screen, text, y, font, color, x=None, width=None, max_lines=3, gap=2):
        """Draw wrapped text from y downwards. Returns the y just below the text."""
        x = WORK.x + self.PAD if x is None else x
        width = WORK.width - 2 * self.PAD if width is None else width
        lh = font.get_linesize() + gap
        for line in wrap_text(font, text, width)[:max_lines]:
            screen.blit(font.render(line, True, color), (x, y))
            y += lh
        return y

    def _intro_lines(self, text, y=None):
        """The instruction line(s) at the top of a screen. Returns the y below them."""
        y = WORK.y + 12 if y is None else y
        y = self._text_block(screen=self._screen, text=text, y=y, font=self.f_small,
                             color=CYAN, max_lines=3, gap=2)
        return y + 6

    def _map(self, screen, n, top=None, bottom=None, panel=0, **kw):
        """Draw a map that fits between `top` and `bottom` and leaves `panel` px free on the right."""
        maxw = WORK.width - 78 - self.PAD - panel
        cell = self._cell_size(n, bottom=bottom, top=top, maxw=maxw)
        origin = self._map_origin(n, cell, top)
        rects = draw_kmap(screen, self.fonts, origin, cell, n, **kw)
        return rects, origin, cell

    def _register_cells(self, rects):
        for m, rect in rects.items():
            self.buttons.append((rect, ("kcell", m)))

    def _info_box(self, screen, x, y, w, lines, color=WHITE, limit=None, font=None):
        """Wrapped lines in a side panel. Stops before `limit` so it never runs into things below."""
        font = font or self.f_small
        lh = font.get_linesize() + 2
        for line in lines:
            for sub in wrap_text(font, line, w):
                if limit is not None and y + lh > limit:
                    return y
                screen.blit(font.render(sub, True, color), (x, y))
                y += lh
            y += 4
        return y

    # ---------------- kinspect ----------------
    def _draw_kinspect(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        y = self._intro_lines(step["task"])
        bottom = WORK.bottom - 44
        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=bottom, panel=230,
                                        vals=step["vals"], selected=st["sel"], cursor=st["cursor"])
        self._register_cells(rects)
        x = origin[0] + len(col_codes(n)) * cell + 40
        self._info_box(screen, x, origin[1] - 10, WORK.right - x - 14, st["lines"], limit=bottom)
        screen.blit(self.f_small.render(
            f"Neighbour pairs found: {len(st['nb'])}/2      Diagonal pairs found: {len(st['diag'])}/1",
            True, GREEN), (WORK.x + self.PAD, WORK.bottom - 32))

    # ---------------- kfill ----------------
    def _draw_kfill(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        y = self._intro_lines(step["task"])
        y = self._text_block(screen, step["line"], y, self.f_body, YELLOW, max_lines=2, gap=2) + 2
        bottom = WORK.bottom - 44
        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=bottom,
                                        vals=st["cells"], cursor=st["cursor"])
        self._register_cells(rects)
        count = sum(st["cells"].values())
        screen.blit(self.f_small.render(
            f"Cells set to 1: {count} / {len(step['ones'])}", True,
            GREEN if count == len(step["ones"]) else WHITE), (WORK.x + self.PAD, WORK.bottom - 32))

    # ---------------- kpick ----------------
    def _draw_kpick(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        y = self._intro_lines(step["task"])
        y = self._text_block(screen, step["line"], y, self.f_body, YELLOW, max_lines=2, gap=2) + 2
        marks = {st["pick"]: "?"} if st["pick"] is not None else None
        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=WORK.bottom - self.FOOT - 6,
                                        vals=None,
                                        selected=[st["pick"]] if st["pick"] is not None else [],
                                        cursor=st["cursor"], marks=marks)
        self._register_cells(rects)

    # ---------------- kloops ----------------
    def _draw_kloops(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        mode = step["mode"]
        y = self._intro_lines(step["task"])
        loops = [(l, i) for i, l in enumerate(st["loops"])]
        by = WORK.bottom - 52                     # button row
        sel_y = by - 24                           # "Selected cells" line
        map_bottom = sel_y - 8
        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=map_bottom, panel=230,
                                        vals=step["vals"], selected=st["sel"],
                                        loops=loops, cursor=st["cursor"])
        self._register_cells(rects)

        # side panel
        x = origin[0] + len(col_codes(n)) * cell + 26
        w = WORK.right - x - 12
        py = origin[1] - 10
        if step.get("sevenseg"):
            draw_seven_seg(screen, x + 4, py, step["sevenseg"], 0.8)
            screen.blit(self.f_tiny.render(f"segment {step['sevenseg']}", True, GREY), (x + 56, py + 22))
            py += 66
        screen.blit(self.f_small.render(f"Loops of {'1s' if mode == 'ones' else '0s'}:", True, CYAN), (x, py))
        py += 26
        if not st["loops"]:
            screen.blit(self.f_tiny.render("(none yet)", True, GREY), (x, py))
            py += 18
        for i, loop in enumerate(st["loops"]):
            if py > sel_y - 30:
                break
            color = LOOP_COLORS[i % len(LOOP_COLORS)]
            pygame.draw.rect(screen, color, (x, py + 3, 14, 14), border_radius=3)
            text = f"{len(loop)} cells"
            if step.get("show_terms"):
                text += "  =  " + term_str(loop, n, "sop" if mode == "ones" else "pos")
            screen.blit(self.f_small.render(text, True, WHITE), (x + 22, py))
            py += 24
        if any(v == X for v in step["vals"].values()) and py < sel_y - 24:
            self._info_box(screen, x, py + 4, w,
                           ["X = don't care. Use it only to make a loop bigger."],
                           color=YELLOW, limit=sel_y, font=self.f_tiny)

        # status line + buttons
        sel = self.f_tiny.render(
            f"Selected cells: {len(st['sel'])}   (click a selected cell again to unselect it)", True, GREY)
        screen.blit(sel, (WORK.x + self.PAD, sel_y))
        bx = WORK.x + self.PAD
        bw = min(130, (WORK.width - 2 * self.PAD - 24) // 3)
        for label, act, col in (("LOOP IT [L]", ("kloop",), GREEN), ("UNDO [U]", ("kundo",), YELLOW),
                                ("CLEAR [C]", ("kclear",), GREY)):
            rect = pygame.Rect(bx, by, bw, 36)
            self._button(screen, rect, label, act, col)
            bx += bw + 12

    # ---------------- kstretch ----------------
    def _draw_kstretch(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        start = step["start"]
        y = self._intro_lines(step["task"])
        cells = self._loop_cells()
        vals = vals_from(n, step["ones"])

        by = WORK.bottom - 52
        legend_y = by - 22
        map_bottom = legend_y - 8
        bw = min(138, (WORK.width - 2 * self.PAD - (n - 1) * 8) // n)
        btns = [pygame.Rect(WORK.x + self.PAD + i * (bw + 8), by, bw, 36) for i in range(n)]

        # hover preview: which cells would this doubling swallow?
        highlight, bad = set(), set(st["blocked"])
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(btns):
            bit = 1 << (n - 1 - i)
            if rect.collidepoint(mouse) and not (st["free"] & bit):
                new = set(cube_cells(start, st["free"] | bit)) - set(cells)
                highlight = new & set(step["ones"])
                bad = new - set(step["ones"])

        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=map_bottom, panel=240,
                                        vals=vals, loops=[(cells, 0)], highlight=highlight, bad=bad)
        flag = self.f_tiny.render("START", True, CYAN)
        screen.blit(flag, flag.get_rect(midbottom=(rects[start].centerx, rects[start].bottom - 2)))

        x = origin[0] + len(col_codes(n)) * cell + 26
        w = WORK.right - x - 12
        info = analyse(cells, n)
        left = n - popcount(info["free"])
        lines = [f"Cells in the loop: {len(cells)}",
                 f"Formula for this loop: {term_str(cells, n)}",
                 f"Letters left: {left}  (one cell alone needs all {n})"]
        py = self._info_box(screen, x, origin[1] - 10, w, lines, WHITE, limit=map_bottom)
        self._info_box(screen, x, py + 6, w, [st["info"]], YELLOW, limit=map_bottom)

        screen.blit(self.f_tiny.render(
            "Green preview = allowed.   Red = a 0 is in the way.", True, GREY),
            (WORK.x + self.PAD, legend_y))
        for i, rect in enumerate(btns):
            on = bool(st["free"] & (1 << (n - 1 - i)))
            label = f"{'Undo' if on else 'Double'} {VARS[i]}"
            self._button(screen, rect, label, ("kstretch", i), YELLOW if on else CYAN)

    # ---------------- kterm ----------------
    def _draw_kterm(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        mode = step["mode"]
        y = self._intro_lines(step["task"])
        loop = step["loop"]
        bottom = WORK.bottom - self.FOOT
        rects, origin, cell = self._map(screen, n, top=y + self.LABEL_GAP, bottom=bottom, panel=270,
                                        vals=step["vals"], loops=[(loop, 0)])
        x = origin[0] + len(col_codes(n)) * cell + 26
        w = WORK.right - x - 10
        addr = "Loop cells:  " + ",  ".join(bits(m, n) for m in sorted(loop))
        py = self._info_box(screen, x, origin[1] - 10, w, [addr], GREY, limit=bottom)

        # column headings so the three buttons explain themselves
        heads = ["stays 1", "stays 0", "changes"] if mode == "sop" else ["stays 0", "stays 1", "changes"]
        for j, text in enumerate(heads):
            img = self.f_tiny.render(text, True, CYAN)
            screen.blit(img, img.get_rect(midtop=(x + 34 + j * 62 + 28, py)))
        py += 20

        avail = bottom - py - 36          # keep room for the "Term:" line
        rowh = max(36, min(42, avail // max(1, n)))
        order = [("plain", ""), ("bar", "'"), ("drop", None)]
        for i in range(n):
            name = VARS[i]
            screen.blit(self.f_body.render(name, True, YELLOW), (x, py + 4))
            for j, (state, suffix) in enumerate(order):
                label = name + suffix if suffix is not None else "drop"
                rect = pygame.Rect(x + 34 + j * 62, py, 56, rowh - 6)
                sel = st["states"][i] == state
                pygame.draw.rect(screen, (30, 70, 56) if sel else (20, 34, 50), rect, border_radius=6)
                pygame.draw.rect(screen, GREEN if sel else GREY, rect, 2, border_radius=6)
                img = self.f_small.render(label, True, WHITE)
                screen.blit(img, img.get_rect(center=rect.center))
                self.buttons.append((rect, ("kstate", i, state)))
            py += rowh
        lits = []
        for i in range(n):
            s = st["states"][i]
            if s == "plain":
                lits.append(VARS[i])
            elif s == "bar":
                lits.append(VARS[i] + "'")
            elif s is None:
                lits.append("?")
        if mode == "sop":
            text = "Term:  " + ("".join(lits) if lits else "1")
        else:
            text = "Sum:  (" + " + ".join(lits) + ")" if lits else "Sum:  0"
        screen.blit(self.f_body.render(text, True, GREEN), (x, py + 6))

    # ---------------- kdemo ----------------
    def _draw_kdemo(self, screen):
        step, st = self.step, self.st
        n = step["n"]
        frame = step["frames"][st["frame"]]
        loops = [(l, i) for l, i in frame.get("loops", [])]

        # header: back button, progress dots, next button, then one short instruction line
        total = len(step["frames"])
        for i in range(total):
            cx = WORK.centerx - (total - 1) * 14 + i * 28
            if i == st["frame"]:
                pygame.draw.circle(screen, CYAN, (cx, WORK.y + 24), 8)
            elif i < st["seen"]:
                pygame.draw.circle(screen, GREEN, (cx, WORK.y + 24), 6)
            else:
                pygame.draw.circle(screen, GREY, (cx, WORK.y + 24), 6, 2)
        for label, delta, bx in (("< BACK", -1, WORK.x + self.PAD), ("NEXT >", 1, WORK.right - self.PAD - 110)):
            rect = pygame.Rect(bx, WORK.y + 8, 110, 32)
            self._button(screen, rect, label, ("kframe", delta), CYAN)
        task = self.f_tiny.render(f"View {st['frame'] + 1} of {total}  -  {step['task']}", True, GREY)
        screen.blit(task, task.get_rect(midtop=(WORK.centerx, WORK.y + 48)))

        # caption box at the bottom (measured first, so the map can stay clear of it)
        cap_font = self.f_body
        cap_lines = wrap_text(cap_font, frame["caption"], WORK.width - 2 * self.PAD - 16)
        if len(cap_lines) > 4:
            cap_font = self.f_small
            cap_lines = wrap_text(cap_font, frame["caption"], WORK.width - 2 * self.PAD - 16)
        cap_lines = cap_lines[:5]
        lh = cap_font.get_linesize() + 2
        box_h = lh * len(cap_lines) + 16
        box = pygame.Rect(WORK.x + 10, WORK.bottom - self.FOOT - box_h, WORK.width - 20, box_h)

        # map between the header and the caption box
        top = WORK.y + 112
        map_bottom = box.y - 36            # leaves room for the "wraps" arrows under the map
        rects, origin, cell = self._map(screen, n, top=top, bottom=map_bottom,
                                        vals=step["vals"], highlight=frame.get("cells", ()), loops=loops,
                                        bad=frame.get("bad", ()), nums=frame.get("nums", False),
                                        marks=frame.get("marks"))
        wrap = frame.get("wrap")
        cols = len(col_codes(n))
        rows = len(row_codes(n))
        if wrap == "h":
            y = origin[1] + cell // 2
            pygame.draw.line(screen, YELLOW, (origin[0] + cols * cell + 4, y), (origin[0] + cols * cell + 34, y), 3)
            pygame.draw.line(screen, YELLOW, (origin[0] - 32, y), (origin[0] - 58, y), 3)
            screen.blit(self.f_tiny.render("wraps", True, YELLOW), (origin[0] + cols * cell + 6, y - 20))
        elif wrap == "v":
            x = origin[0] + cell // 2
            pygame.draw.line(screen, YELLOW, (x, origin[1] - 44), (x, origin[1] - 30), 3)
            pygame.draw.line(screen, YELLOW, (x, origin[1] + rows * cell + 4), (x, origin[1] + rows * cell + 20), 3)
            screen.blit(self.f_tiny.render("wraps", True, YELLOW), (x + 8, origin[1] + rows * cell + 6))

        pygame.draw.rect(screen, (16, 28, 42), box, border_radius=8)
        pygame.draw.rect(screen, (60, 90, 112), box, 1, border_radius=8)
        ty = box.y + 8
        for line in cap_lines:
            screen.blit(cap_font.render(line, True, WHITE), (box.x + 8, ty))
            ty += lh

    def _on_action_frame(self, delta):
        st = self.st
        frames = len(self.step["frames"])
        st["frame"] = (st["frame"] + delta) % frames
        st["seen"] = max(st["seen"], st["frame"] + 1)
        self.demo_clock = 0.0

    # ---------------- map shown inside multiple-choice questions ----------------
    def _draw_extra_visual(self, screen, step, top, bottom):
        if step["visual"] == "kmap":
            n = step["kn"]
            maxw = WORK.width - 78 - self.PAD - 40
            cell = self._cell_size(n, bottom=bottom - 10, top=top + 34, maxw=maxw)
            width = len(col_codes(n)) * cell
            origin = (WORK.centerx - width // 2 + 20, top + 34)
            draw_kmap(screen, self.fonts, origin, cell, n, vals=step["kvals"],
                      loops=step["kloops"], highlight=step["khl"])

    # ---------------- stage-complete card ----------------
    def _draw_done(self, screen):
        stage = self.stage
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, GREEN, FULL, 3, border_radius=10)
        n_stage = self.stage_i + 1
        title = self.f_big.render(f"STAGE {n_stage} COMPLETE", True, GREEN)
        screen.blit(title, (FULL.x + 24, FULL.y + 14))
        sub_y = FULL.y + 14 + title.get_height() + 6
        screen.blit(self.f_body.render(f"{stage['title']}  -  {stage['sub']}", True, WHITE),
                    (FULL.x + 24, sub_y))
        content_top = sub_y + self.f_body.get_linesize() + 14

        # footer first (so everything above can be measured against it)
        last = self.stage_i >= len(self.stages) - 1
        btn_w = 210
        foot_lines = wrap_text(self.f_small,
                               "Saved to NOTEBOOK [N]  >  TEST THE LOGIC  >  MY BASIC NOTES",
                               FULL.width - 48 - btn_w - 16)
        foot_lh = self.f_small.get_linesize() + 2
        foot_y = FULL.bottom - 16 - foot_lh * len(foot_lines)
        for i, line in enumerate(foot_lines):
            screen.blit(self.f_small.render(line, True, YELLOW), (FULL.x + 24, foot_y + i * foot_lh))
        rect = pygame.Rect(FULL.right - btn_w - 20, FULL.bottom - 54, btn_w, 38)
        self._button(screen, rect, "FINISH LEVEL" if last else "NEXT STAGE  [ENTER]", ("next",), GREEN)
        content_bottom = min(foot_y, rect.y) - 10

        # example map on the left, shrunk to fit
        n, vals, loops = stage["example"]
        rows = len(row_codes(n))
        cols = len(col_codes(n))
        cell = {2: 70, 3: 60, 4: 52}[n]
        cell = min(cell, max(30, (content_bottom - (content_top + self.LABEL_GAP)) // rows))
        origin = (FULL.x + 90, content_top + self.LABEL_GAP)
        draw_kmap(screen, self.fonts, origin, cell, n, vals=vals,
                  loops=[(l, i) for i, l in enumerate(loops)])

        # notes on the right: pick the biggest font that fits
        rx = max(FULL.x + 390, origin[0] + cols * cell + 40)
        rw = FULL.right - rx - 24
        avail = content_bottom - content_top

        def measure(font):
            lh = font.get_linesize() + 1
            h = 0
            for label, text in stage["items"]:
                h += lh + 2 + len(wrap_text(font, text, rw)) * lh + 8
            return h

        font = self.f_small if measure(self.f_small) <= avail else self.f_tiny
        lh = font.get_linesize() + 1
        y = content_top
        for label, text in stage["items"]:
            screen.blit(font.render(label, True, CYAN), (rx, y))
            y += lh + 2
            for line in wrap_text(font, text, rw):
                screen.blit(font.render(line, True, WHITE), (rx, y))
                y += lh
            y += 8

    # ---------------- notebook autofill (unchanged) ----------------
    def notebook_lines(self, stage):
        sid = stage["id"]
        lines = {
            "k1_neighbours": [
                "KARNAUGH 1: NEIGHBOURS",
                "- A K-map is a truth table drawn as a grid. Touching cells differ in exactly ONE variable.",
                "- Two touching 1s merge and that variable cancels: AB' + AB = A(B' + B) = A.",
                "- Row and column labels use Gray code (00, 01, 11, 10) so neighbours stay one bit apart.",
            ],
            "k2_fill": [
                "KARNAUGH 2: FILLING THE MAP",
                "- 2 variables: 2x2 map.  3 variables: 2x4.  4 variables: 4x4.  5 variables: two 4x4 maps.",
                "- A cell's address is its row bits then its column bits (ABC = row A, column BC).",
                "- Read the labels: column 11 comes BEFORE column 10. Never count cells.",
            ],
            "k3_minterms": [
                "KARNAUGH 3: MINTERMS",
                "- Every cell has an address. Read it as a binary number: 101 = 4 + 0 + 1 = 5, so it is cell 5.",
                "- A MINTERM is the AND of ALL the letters for one cell, with a bar on every letter that is 0. Cell 011 = A'BC = m3.",
                "- F = m1 + m3 + m7 means F is 1 on cells 1, 3 and 7. Short form: F = Sum m(1, 3, 7).",
                "- n letters give 2^n cells and 2^n minterms (4 letters: 16).",
            ],
            "k4_legal": [
                "KARNAUGH 4: LEGAL LOOPS",
                "- SIZE: a loop has 1, 2, 4, 8 (or 16) cells. Never 3, 5, 6 or 7.",
                "- SHAPE: a rectangle, which may wrap round an edge. No diagonals, no L-shapes.",
                "- CONTENTS: only 1s (and X's). One 0 inside makes the loop illegal.",
            ],
            "k5_stretch": [
                "KARNAUGH 5: BIGGEST LOOPS",
                "- Start at one cell and DOUBLE the loop (1, 2, 4, 8) until the next doubling would swallow a 0.",
                "- Why 4 and not 8? Doubling again would pull in a 0 cell.",
                "- Every doubling removes one letter, so a bigger loop gives a shorter formula.",
                "- Math: a loop of 2^k cells on an n-variable map gives a term with n - k variables.",
            ],
            "k6_wrap": [
                "KARNAUGH 6: WRAP-AROUND",
                "- The map wraps: left touches right, top touches bottom.",
                "- The 4 corners of a 4-variable map form ONE loop of 4: B'D'.",
                "- Cover every 1 with the FEWEST, BIGGEST loops. Loops may overlap.",
            ],
            "k7_sop": [
                "KARNAUGH 7: READING LOOPS (SOP)",
                "- Per variable: stays 1 = write the letter. Stays 0 = letter with a bar. Changes = drop it.",
                "- AND the letters in one loop (a product term), then OR the terms: SOP = sum of products.",
                "- Example: loop of cells 100 and 101 gives AB' (C changes, so C is dropped).",
            ],
            "k8_pos": [
                "KARNAUGH 8: POS (LOOP THE ZEROS)",
                "- Loop the 0s. Read each loop as a SUM: stays 0 = letter, stays 1 = letter with a bar, changes = drop.",
                "- AND the sums together: POS = product of sums. Example: F = (A + B)(B + C').",
                "- MAXTERM: the OR of ALL the letters for one 0 cell. A 0 stays plain, a 1 gets a bar. Cell 001 = (A + B + C') = M1.",
                "- A maxterm is the opposite of a minterm: M1 = (m1)'. F = Prod M(0, 1, 5) lists the cells where F = 0.",
                "- Why: the 0-loops give F'. De Morgan turns that into sums and flips every bar.",
                "- Use POS when the 0s are fewer or give bigger loops than the 1s.",
            ],
            "k9_dc": [
                "KARNAUGH 9: DON'T CARES AND 7-SEGMENT",
                "- X = don't care (that input never happens). Count it as 1 ONLY if it makes a loop bigger.",
                "- You do NOT have to cover every X. Never make a loop that holds only X's.",
                "- BCD uses 0 to 9, so inputs 10 to 15 are all X.",
                "- 7-segment segment e lights for 0, 2, 6, 8: e = B'D' + CD'.",
            ],
        }
        return lines[sid]