# puzzles/basic_comb.py
# BASIC LEVEL 5 - "Combinational Circuits" (9 stages)
#
# Plugs into terminal 5 (puzzle_id logic_architect, notebook level_five) on the
# BASIC path only.  It reuses the frame, hints, notebook autofill and answer
# buttons of puzzles/basic_gates.py, and the circuits of puzzles/comb_lab.py
# (the same circuits the notebook lab shows).
#
#   1  Half adder          add two bits (Sum = XOR, Carry = AND)
#   2  Full adder          add three bits, built from two half adders      [exam]
#   3  Subtractors         half and full subtractor, borrow                [exam]
#   4  Adder chains        4-bit parallel adder, adder-subtractor          [syllabus]
#   5  Parity              even parity generator and checker               [exam]
#   6  Gray code           binary <-> Gray with XOR gates                  [exam]
#   7  Decoder             a code in, ONE wire out (minterm generator)     [exam]
#   8  Multiplexer         many in, one out; 4:1 and 8:1 implementations   [exam]
#   9  BOSS                five paper-style questions
#
# Every stage starts with WHAT IS IT FOR, then SEE IT (demo + sandbox),
# SAY IT (the rule), PREDICT IT (fill a table) and PROVE IT (build / exam step).
# Steps marked EXAM STYLE copy the wording of the real past papers.
#
# New step kinds (all keyboard and mouse):
#   cframes   step through a demo with BACK / NEXT (or LEFT / RIGHT)
#   csee      sandbox: flip the switches and watch the circuit
#   ctable    fill a truth table (click a cell or arrows + 0 / 1)
#   cslots    choose the gate for every "?" in a circuit (click, SPACE, 1-3)
#   cmux      choose what goes on every data input of a multiplexer
#   cbits     light the bulbs that show a binary answer
#   choice    the usual multiple-choice step (with circuit / K-map pictures)

import math

import pygame

from puzzles.basic_gates import (
    BasicGatesPuzzle, WORK, SIDE, FULL, wrap_text,
    PANEL, PANEL_EDGE, CYAN, GREEN, YELLOW, GREY, WHITE, RED, BG,
    draw_bulb,
)
from puzzles import comb_lab as CL
from puzzles.basic_kmap import draw_kmap, vals_from, solution_loops

if not hasattr(BasicGatesPuzzle, "LEGEND_EXTRA"):
    raise ImportError(
        "puzzles/basic_gates.py is the OLD version. Replace it with the one from "
        "the v5 project (basic_comb.py needs the updated file)."
    )

EXAM, SYLL = "EXAM STYLE", "SYLLABUS"


def H(a, b, c):
    """Exactly three tiered hints: nudge, stronger, the answer."""
    return [a, b, c]


def _mt(ones, n=3):
    return "Sum m(" + ", ".join(str(m) for m in sorted(ones)) + ")"


# ------------------------------------------------------------------
# STEP BUILDERS
# ------------------------------------------------------------------
def frames_step(sim, frames, task, hints=None, tag=None):
    return {"kind": "cframes", "sim": sim, "frames": frames, "task": task, "tag": tag,
            "hints": hints or H("Press NEXT (or the RIGHT arrow) to move to the next picture.",
                                "Look at every picture. The step finishes when you have seen them all.",
                                "Click NEXT until all the dots are green, then press CHECK.")}


def see_step(sim, goals, task, hints, note=None, start=None, tag=None):
    return {"kind": "csee", "sim": sim, "goals": goals, "task": task, "hints": hints,
            "note": note, "start": start or {}, "tag": tag}


def _exam_task(task, exam):
    return ('Exam question: "' + exam + '"  ' + task) if exam else task


def table_step(sim, cols, task, hints, rows=None, default=None, exam=None, note=None):
    task = _exam_task(task, exam)
    return {"kind": "ctable", "sim": sim, "cols": cols, "rows": rows, "default": default,
            "task": task, "hints": hints, "tag": EXAM if exam else None, "exam": exam, "note": note}


def slots_step(sim, hidden, labels, reasons, task, hints, options=("AND", "OR", "XOR"),
               exam=None, note=None):
    task = _exam_task(task, exam)
    return {"kind": "cslots", "sim": sim, "hidden": hidden, "labels": labels, "reasons": reasons,
            "options": list(options), "task": task, "hints": hints,
            "tag": EXAM if exam else None, "exam": exam, "note": note}


def choice_step(q, options, correct, task, hints, ok="", visual="text", tag=None, **extra):
    st = {"kind": "choice", "visual": visual, "q": q, "options": [(o, o) for o in options],
          "correct": correct, "task": task, "hints": hints, "ok": ok, "tag": tag}
    st.update(extra)
    return st


def bits_step(context, labels, target, task, hints, tag=None):
    return {"kind": "cbits", "context": context, "labels": labels, "target": target,
            "task": task, "hints": hints, "tag": tag}


def _ones_to_pairs(ones, nvars, last="D"):
    """Per data-input slot: (value for last var 0, value for last var 1)."""
    out = []
    for k in range(1 << (nvars - 1)):
        out.append((int((2 * k) in ones), int((2 * k + 1) in ones)))
    return out


def mux_expected(ones, nvars, n_sel, last):
    """Expected option string for every data input of a MUX."""
    res = []
    if nvars == n_sel:
        return [str(int(k in ones)) for k in range(1 << n_sel)]
    for k in range(1 << n_sel):
        a, b = int((2 * k) in ones), int((2 * k + 1) in ones)
        res.append({(0, 0): "0", (1, 1): "1", (0, 1): last, (1, 0): last + "'"}[(a, b)])
    return res


def mux_step(ones, nvars, n_sel, sel_names, last, fn_text, options, task, hints, exam=None):
    task = _exam_task(task, exam)
    return {"kind": "cmux", "ones": set(ones), "nvars": nvars, "n_sel": n_sel,
            "sel_names": sel_names, "last": last, "fn_text": fn_text, "options": options,
            "task": task, "hints": hints, "tag": EXAM if exam else None, "exam": exam}


# ------------------------------------------------------------------
# THE NINE STAGES
# ------------------------------------------------------------------
def _fv(**kw):
    return kw


def stage_half():
    caps = [
        ("A = 0, B = 0", dict(A=0, B=0), "0 + 0 = 0. Both bulbs stay OFF."),
        ("A = 0, B = 1", dict(A=0, B=1), "0 + 1 = 1. Sum is ON, Carry is OFF."),
        ("A = 1, B = 0", dict(A=1, B=0), "1 + 0 = 1. Sum is ON, Carry is OFF."),
        ("A = 1, B = 1", dict(A=1, B=1),
         "1 + 1 = 2, and 2 is written 10 in binary. Sum shows the 0, Carry shows the 1. "
         "Sum = XOR, Carry = AND."),
    ]
    return {
        "id": "c1_half", "title": "Half adder", "sub": "adding two bits", "gates": [],
        "brief": [
            "WHAT IS IT FOR? A calculator adds with tiny circuits. 1 + 1 = 2 needs two "
            "digits (10), so the answer has a SUM bulb and a CARRY bulb.",
            "Rule: Sum = XOR, Carry = AND.",
        ],
        "steps": [
            frames_step("ha", [{"vals": v, "caption": c} for _l, v, c in caps],
                        "Watch all four additions. Press NEXT."),
            see_step("ha", [("rows", 4)], "Now YOU flip A and B. Try all four rows.",
                     H("Click a switch (or press 1 and 2) and watch the bulbs.",
                       "There are four rows: 00, 01, 10 and 11. The table on the right ticks them off.",
                       "Flip A and B until each of the four rows has been highlighted once.")),
            table_step("ha", ["Sum", "Carry"], "Predict: fill the Sum and Carry columns.",
                       H("Add the two bits. Write the answer in binary: the right digit is Sum, the left digit is Carry.",
                         "Row 1 1: 1 + 1 = 2 = binary 10, so Carry = 1 and Sum = 0.",
                         "Sum column: 0 1 1 0.   Carry column: 0 0 0 1.")),
            slots_step("ha", {"s": "XOR", "c": "AND"}, {"s": "makes SUM", "c": "makes CARRY"},
                       {"s": "SUM is 1 when the two bits are DIFFERENT (0+1 or 1+0). The gate for 'different' is XOR.",
                        "c": "CARRY is 1 only when BOTH bits are 1. The gate for 'both' is AND."},
                       "Build the half adder: click each ? and choose its gate.",
                       H("Look at the truth table: when is Sum ON? When are the bits different or the same?",
                         "Sum column 0 1 1 0 is the XOR gate. Carry column 0 0 0 1 is the AND gate.",
                         "Top gate (SUM) = XOR.  Bottom gate (CARRY) = AND.")),
            choice_step("A half adder gets A = 1 and B = 1. Read CARRY then SUM as one binary number. "
                        "What number is it?", ["00", "01", "10", "11"], "10",
                        "Pick the number shown by Carry and Sum together.",
                        H("Carry is the left digit, Sum is the right digit.",
                          "1 + 1 = 2. How do you write 2 in binary?",
                          "Carry = 1, Sum = 0, so the number is 10 (two)."),
                        ok="Binary 10 = 2 = 1 + 1."),
            choice_step("A half adder has no memory: its outputs depend ONLY on A and B right now. "
                        "That is a COMBINATIONAL circuit. Which one below is NOT combinational "
                        "(it remembers the past)?",
                        ["A half adder", "A decoder", "A lock that remembers the last 3 digits you typed",
                         "A bank of AND gates"],
                        "A lock that remembers the last 3 digits you typed",
                        "Pick the circuit that needs memory.",
                        H("Combinational = output depends only on the inputs now.",
                          "Which choice needs to remember something from earlier?",
                          "The lock that remembers earlier digits. That is a SEQUENTIAL circuit (Level 6)."),
                        ok="Combinational = no memory. Sequential = has memory."),
        ],
        "done": ("sim", "ha", dict(A=1, B=1)),
        "items": [
            ("RULE", "Sum = A xor B (1 when the bits differ).  Carry = A AND B (1 when both are 1)."),
            ("MATH LINK", "1 + 1 = 2 = binary 10. Carry is the 2s place, Sum is the 1s place."),
            ("REMEMBER", "Half adder = XOR + AND. 'Half' because nothing is carried IN."),
            ("EXAM", "Asked with truth table, logic diagram and K-map (Nov 2023)."),
        ],
    }


def stage_full():
    frames = [
        (dict(A=1, B=1, Cin=0),
         "1 + 1 + 0 = 2 = binary 10. The first half adder gives Sum 0, Carry 1. The second adds Cin 0. "
         "So Sum = 0, Cout = 1."),
        (dict(A=0, B=1, Cin=1),
         "0 + 1 + 1 = 2 = binary 10. First half adder: Sum 1. The second adds Cin 1: Sum 0 and it carries. "
         "So Sum = 0, Cout = 1."),
        (dict(A=1, B=1, Cin=1),
         "1 + 1 + 1 = 3 = binary 11. Sum = 1 and Cout = 1. This is the only row with three 1s."),
        (dict(A=0, B=0, Cin=1),
         "0 + 0 + 1 = 1 = binary 01. Only the carry-in is ON, so Sum = 1 and Cout = 0."),
    ]
    cout_ones, sum_ones = {3, 5, 6, 7}, {1, 2, 4, 7}
    return {
        "id": "c2_full", "title": "Full adder", "sub": "adding three bits", "gates": [],
        "brief": [
            "WHAT IS IT FOR? Numbers have many columns. From the second column on, you add THREE "
            "bits: A, B and the carry from the column before.",
            "Rule: Sum = A xor B xor Cin. Cout = 1 when at least two inputs are 1.",
        ],
        "steps": [
            frames_step("fa", [{"vals": v, "caption": c} for v, c in frames],
                        "Watch four additions. Notice the two half adders (HA 1, HA 2)."),
            see_step("fa", [("rows", 8)], "Flip A, B and Cin. Find all 8 rows.",
                     H("Click the switches (or press 1, 2, 3). The highlighted row moves in the table.",
                       "Rows go 000, 001, 010 ... 111. Try to light up every row once.",
                       "Count in binary with the switches: 000, 001, 010, 011, 100, 101, 110, 111.")),
            table_step("fa", ["Sum", "Cout"], "Fill the Sum and Cout columns for all 8 rows.",
                       H("Count the 1s among A, B and Cin. Write that count in binary: left digit = Cout, right digit = Sum.",
                         "One 1 gives 01 (Sum 1). Two 1s give 10 (Cout 1). Three 1s give 11.",
                         "Sum column: 0 1 1 0 1 0 0 1.   Cout column: 0 0 0 1 0 1 1 1."),
                       exam="Design full adder with truth table & logic diagram."),
            choice_step("Cout K-map (C in the map means Cin). Three loops cover the 1s. "
                        "Which expression do they give?",
                        ["AB + AC + BC", "A + B + C", "ABC", "A xor B xor C"], "AB + AC + BC",
                        "Read the three loops of the Cout map.",
                        H("Each loop is two touching 1s. Read each loop as in the K-map level.",
                          "Loops: cells 110+111 = AB, cells 101+111 = AC, cells 011+111 = BC.",
                          "Cout = AB + AC + BC (any two of the three inputs ON)."),
                        ok="Cout = AB + A.Cin + B.Cin.", visual="kmap",
                        kmap=(3, cout_ones, True), tag=EXAM),
            choice_step("Sum K-map. No two 1s touch (it is a checkerboard). What does that tell you?",
                        ["Nothing can be looped: it stays as an XOR",
                         "Loop the four corners", "Loop all the 1s into one big loop", "Sum is always 1"],
                        "Nothing can be looped: it stays as an XOR",
                        "Look at where the 1s sit.",
                        H("A loop needs two touching 1s. Do any 1s touch?",
                          "In a checkerboard every 1 has only 0s as neighbours.",
                          "No loops are possible, so Sum cannot be shortened: Sum = A xor B xor Cin."),
                        ok="A checkerboard map is the sign of XOR.", visual="kmap",
                        kmap=(3, sum_ones, False), tag=EXAM),
            slots_step("fa", {"x1": "XOR", "a1": "AND", "x2": "XOR", "a2": "AND", "o": "OR"},
                       {"x1": "HA1 sum", "a1": "HA1 carry", "x2": "SUM", "a2": "HA2 carry", "o": "makes Cout"},
                       {"x1": "HA 1 adds A and B. Its sum is 1 when A and B differ: XOR.",
                        "a1": "HA 1's carry is 1 when A and B are BOTH 1: AND.",
                        "x2": "HA 2 adds HA 1's sum and Cin. Sum = XOR again. This is the final SUM.",
                        "a2": "HA 2's carry is 1 when its two inputs are BOTH 1: AND.",
                        "o": "Either half adder can make the carry. 'Either one' = OR."},
                       "Complete the logic diagram: two half adders and one more gate.",
                       H("Each half adder is XOR (sum) plus AND (carry). Two half adders = 2 XOR + 2 AND.",
                         "The two carries are joined by a gate that says 'either one'.",
                         "HA1: XOR and AND. HA2: XOR and AND. Last gate: OR."),
                       exam="Design full adder with truth table & logic diagram."),
            choice_step("The Sum column is 1 on rows 1, 2, 4, 7, so Sum = Sum m(1, 2, 4, 7). "
                        "Which list is the Cout column?",
                        [_mt(cout_ones), _mt(sum_ones), "Sum m(0, 3, 5, 6)", "Sum m(1, 3, 5, 7)"], _mt(cout_ones),
                        "Level 4 link: pick the minterm list of Cout.",
                        H("Cout is 1 when at least two inputs are 1. Which row numbers have two or three 1s?",
                          "Rows 011, 101, 110 and 111 have two or more 1s. Convert them to numbers.",
                          "Cout = Sum m(3, 5, 6, 7)."),
                        ok="Cout = Sum m(3, 5, 6, 7)."),
        ],
        "done": ("sim", "fa", dict(A=1, B=1, Cin=1)),
        "items": [
            ("RULE", "Sum = A xor B xor Cin = Sum m(1,2,4,7).  Cout = AB + A.Cin + B.Cin = Sum m(3,5,6,7)."),
            ("MATH LINK", "Count the 1s (0 to 3) and write the count in binary: Cout Sum."),
            ("REMEMBER", "Full adder = 2 half adders + 1 OR gate."),
            ("EXAM", "Asked in Nov 2023, Apr 2026 and Sep 2026."),
        ],
    }


def stage_sub():
    fr = [
        (dict(A=0, B=0), "0 - 0 = 0. Nothing to borrow."),
        (dict(A=0, B=1), "0 - 1 cannot be done in one column. Borrow 1 from the left (it is worth 2): "
                         "2 - 1 = 1. So Diff = 1 and Borrow = 1."),
        (dict(A=1, B=0), "1 - 0 = 1. Nothing to borrow."),
        (dict(A=1, B=1), "1 - 1 = 0. Nothing to borrow. Diff = XOR, Borrow = (NOT A) AND B."),
    ]
    bout = {1, 2, 3, 7}
    return {
        "id": "c3_sub", "title": "Subtractors", "sub": "taking away, with a borrow", "gates": [],
        "brief": [
            "WHAT IS IT FOR? 1 - 0, 1 - 1 and 0 - 0 are easy. But 0 - 1 needs a BORROW from the "
            "left column. The outputs are DIFF and BORROW.",
            "Rule: Diff = XOR. Borrow = (NOT A) AND B.",
        ],
        "steps": [
            frames_step("hs", [{"vals": v, "caption": c} for v, c in fr],
                        "Watch the four subtractions. Press NEXT."),
            see_step("hs", [("rows", 4)], "Flip A and B. Try all four rows. Find the borrow.",
                     H("Click the switches. Which row makes the Borrow bulb light?",
                       "Borrow lights only when you take a BIG number from a SMALL one.",
                       "Set A = 0 and B = 1: that is the only borrow row.")),
            table_step("hs", ["Diff", "Borrow"], "Predict: fill Diff (A - B) and Borrow.",
                       H("Diff = A - B written in one digit. Borrow = 1 when A is smaller than B.",
                         "Row 0 1: 0 - 1 needs a borrow: Diff = 1, Borrow = 1.",
                         "Diff column: 0 1 1 0.   Borrow column: 0 1 0 0.")),
            slots_step("hs", {"d": "XOR", "b": "AND"}, {"d": "makes DIFF", "b": "makes BORROW"},
                       {"d": "Diff is 1 when the bits are different, like the adder's Sum: XOR.",
                        "b": "Borrow = (NOT A) AND B. The NOT gate is already there, so you need AND."},
                       "Build the half subtractor: choose the gate for each ?.",
                       H("Compare with the half adder: one gate is the same, one has a NOT in front.",
                         "Diff column 0 1 1 0 is XOR. Borrow is ON when NOT A and B are both ON.",
                         "DIFF = XOR.  BORROW = AND (fed by NOT A and B).")),
            table_step("fs", ["Diff", "Bout"], "Fill Diff and Bout (borrow out) for all 8 rows.",
                       H("Diff is 1 when an ODD number of the three inputs are 1 (like the adder's Sum).",
                         "Bout is 1 when A is too small for B + Bin. Rows 001, 010, 011 and 111 need a borrow.",
                         "Diff: 0 1 1 0 1 0 0 1.   Bout: 0 1 1 1 0 0 0 1."),
                       exam="Design full subtractor with truth table & logic diagram."),
            choice_step("The Diff column is 1 on rows 1, 2, 4, 7: the same list as the adder's Sum. "
                        "Which list is Bout (borrow out)?",
                        [_mt(bout), _mt({3, 5, 6, 7}), _mt({1, 2, 4, 7}), "Sum m(0, 4, 5, 6)"], _mt(bout),
                        "Level 4 link: pick the minterm list of Bout.",
                        H("Bout is 1 on rows 001, 010, 011 and 111 of your table.",
                          "Convert those rows to numbers: 1, 2, 3 and 7.",
                          "Bout = Sum m(1, 2, 3, 7) = A'B + A'Bin + B.Bin."),
                        ok="Bout = A'B + A'Bin + B.Bin.", tag=EXAM),
            slots_step("fs", {"b1": "AND", "d1": "XOR", "b2": "AND", "d2": "XOR", "o": "OR"},
                       {"b1": "HS1 borrow", "d1": "HS1 diff", "b2": "HS2 borrow", "d2": "DIFF", "o": "makes Bout"},
                       {"b1": "HS 1 borrow = (NOT A) AND B: AND.",
                        "d1": "HS 1 diff = A xor B: XOR.",
                        "b2": "HS 2 borrow = (NOT first diff) AND Bin: AND.",
                        "d2": "HS 2 diff = first diff xor Bin. This is the final DIFF: XOR.",
                        "o": "Either half subtractor may need a borrow: 'either one' = OR."},
                       "Complete the logic diagram: two half subtractors and one more gate.",
                       H("Same shape as the full adder: two halves and a joiner.",
                         "Each half subtractor is XOR (diff) plus AND (borrow, with a NOT in front).",
                         "HS1: AND + XOR. HS2: AND + XOR. Last gate: OR."),
                       exam="Design full subtractor with truth table & logic diagram."),
        ],
        "done": ("sim", "fs", dict(A=0, B=1, Bin=1)),
        "items": [
            ("RULE", "Diff = A xor B xor Bin = Sum m(1,2,4,7).  Bout = A'B + A'Bin + B.Bin = Sum m(1,2,3,7)."),
            ("MATH LINK", "Borrowing moves 2 from the left column into this one: 2 - 1 = 1."),
            ("REMEMBER", "Subtractor = adder with a NOT in front of A for the borrow."),
            ("EXAM", "Asked in Nov 2024 and Nov 2025."),
        ],
    }


def stage_chain():
    fr = [
        (dict(A3=0, A2=1, A1=1, A0=0, B3=0, B2=0, B1=1, B0=1, Cin=0), 0,
         "A = 0110 (6), B = 0011 (3). Column 0: 0 + 1 + 0 = 1. S0 = 1, no carry."),
        (dict(A3=0, A2=1, A1=1, A0=0, B3=0, B2=0, B1=1, B0=1, Cin=0), 1,
         "Column 1: 1 + 1 + 0 = 2 = binary 10. S1 = 0, and a carry moves LEFT to the next adder."),
        (dict(A3=0, A2=1, A1=1, A0=0, B3=0, B2=0, B1=1, B0=1, Cin=0), 2,
         "Column 2: 1 + 0 + 1 (the carry) = 2. S2 = 0, and another carry moves left."),
        (dict(A3=0, A2=1, A1=1, A0=0, B3=0, B2=0, B1=1, B0=1, Cin=0), 3,
         "Column 3: 0 + 0 + 1 (the carry) = 1. S3 = 1. Answer 1001 = 9, and 6 + 3 = 9."),
    ]
    base = dict(A3=0, A2=1, A1=1, A0=1, B3=0, B2=0, B1=1, B0=1)
    sub = [
        (dict(base, M=0), "A = 0111 (7), B = 0011 (3). With M = 0 the XORs keep B as it is: 7 + 3 = 10."),
        (dict(base, M=1), "Now M = 1. Every XOR FLIPS B: 0011 becomes 1100."),
        (dict(base, M=1), "M is also the carry-in, so the adder adds an extra 1: 0111 + 1100 + 1 = 10100."),
        (dict(base, M=1), "Ignore the left carry. 0100 = 4, and 7 - 3 = 4. Cout = 1 means the answer is not negative."),
    ]
    return {
        "id": "c4_chain", "title": "Adder chains", "sub": "4-bit adder, adder-subtractor", "gates": [],
        "brief": [
            "WHAT IS IT FOR? To add 6 + 3 you need one full adder per bit. Chain them: each "
            "carry-out feeds the carry-in of its left neighbour. One XOR trick makes it subtract too.",
            "Rule: A - B = A + (flipped B) + 1.",
        ],
        "steps": [
            frames_step("add4", [{"vals": v, "active": a, "caption": c} for v, a, c in fr],
                        "Watch 6 + 3, one column at a time.", tag=SYLL),
            see_step("add4", [("pred", "Make Cout light up", lambda v, o: o["Cout"] == 1)],
                     "Flip the switches until the adder overflows: Cout must light.",
                     H("Cout lights when the answer is too big for 4 bits (16 or more).",
                       "Try 1111 + 0001: set A3 A2 A1 A0 = 1 and B0 = 1.",
                       "Turn on A3, A2, A1, A0 and B0. 15 + 1 = 16 needs a fifth bit."), tag=SYLL),
            bits_step(["A = 0101 (5)", "B = 0111 (7)", "Cin = 0"], ["Cout", "S3", "S2", "S1", "S0"],
                      [0, 1, 1, 0, 0],
                      "Predict 5 + 7: light the bulbs of the answer.",
                      H("Add 5 + 7 in ordinary maths first, then write the answer in binary on 5 bulbs.",
                        "5 + 7 = 12 = 8 + 4. Place values from the right: 1, 2, 4, 8.",
                        "12 = 01100: Cout 0, S3 1, S2 1, S1 0, S0 0."), tag=SYLL),
            choice_step("An XOR gate has B on one input and M on the other. What does it do to B when M = 1?",
                        ["It flips B (0 becomes 1, 1 becomes 0)", "It keeps B the same",
                         "It forces B to 0", "It forces B to 1"],
                        "It flips B (0 becomes 1, 1 becomes 0)",
                        "Look at the XOR table, rows with M = 1.",
                        H("XOR gives 1 when its inputs are DIFFERENT.",
                          "With M = 1: B = 0 gives 1, and B = 1 gives 0.",
                          "The output is the opposite of B: it flips B."),
                        ok="XOR with 1 = NOT. XOR with 0 = leave alone.", visual="xor", tag=SYLL),
            frames_step("addsub", [{"vals": v, "caption": c} for v, c in sub],
                        "Watch 7 - 3 done by the adder-subtractor.", tag=SYLL),
            see_step("addsub",
                     [("pred", "Try M = 0 (add)", lambda v, o: v["M"] == 0 and (v["B0"] or v["B1"] or v["B2"] or v["B3"])),
                      ("pred", "Try M = 1 (subtract)", lambda v, o: v["M"] == 1 and (v["B0"] or v["B1"] or v["B2"] or v["B3"]))],
                     "Set some bits of A and B. Try both M = 0 and M = 1.",
                     H("Turn on a few A and B switches, then flip M.",
                       "M is the switch on the right. Watch the XOR row flip B when M = 1.",
                       "Set B0 = 1 and A0 = 1, then try M = 0 and M = 1."), tag=SYLL),
            bits_step(["A = 1001 (9)", "B = 0100 (4)", "M = 1  (subtract)"],
                      ["Cout", "S3", "S2", "S1", "S0"], [1, 0, 1, 0, 1],
                      "Work out 9 - 4 with the circuit: light Cout and S3 to S0.",
                      H("M = 1: flip B, then add A + flipped B + 1.",
                        "B = 0100 flips to 1011. Now 1001 + 1011 + 1 = ?",
                        "9 + 11 + 1 = 21 = 10101: Cout 1, S = 0101 (that is 5)."), tag=SYLL),
        ],
        "done": ("table", ["M", "B", "B xor M"], [["0", "0", "0"], ["0", "1", "1"], ["1", "0", "1"], ["1", "1", "0"]]),
        "items": [
            ("RULE", "Parallel adder: carry-out of each full adder = carry-in of the next."),
            ("MATH LINK", "A - B = A + (NOT B) + 1. XOR with M flips B, and M is the +1."),
            ("REMEMBER", "M = 0: add.  M = 1: subtract. Cout = 1 after subtracting means not negative."),
            ("EXAM", "In the syllabus but not asked yet. Needs only what you know."),
        ],
    }


def stage_parity():
    fr = [
        (dict(A=1, B=0, C=1, D=0), "Message 1 0 1 0 has two 1s (even), so P = 0. Sent: 1 0 1 0 0."),
        (dict(A=1, B=1, C=1, D=0), "Message 1 1 1 0 has three 1s (odd). P = 1 makes four (even). Sent: 1 1 1 0 1."),
        (dict(A=1, B=1, C=1, D=1), "Message 1 1 1 1 has four 1s. Already even, so P = 0."),
        (dict(A=0, B=0, C=0, D=1), "Message 0 0 0 1 has one 1 (odd), so P = 1."),
    ]
    odd = sorted(m for m in range(16) if bin(m).count("1") % 2)
    even = sorted(m for m in range(16) if bin(m).count("1") % 2 == 0)
    return {
        "id": "c5_parity", "title": "Parity", "sub": "catching damaged bits", "gates": [],
        "brief": [
            "WHAT IS IT FOR? A bit can flip on a wire. So the sender adds one extra PARITY bit "
            "to make the number of 1s EVEN. If the receiver counts an ODD number, something broke.",
            "Rule: P = A xor B xor C xor D.",
        ],
        "steps": [
            frames_step("par4", [{"vals": v, "caption": c} for v, c in fr],
                        "Watch four messages get their parity bit."),
            see_step("par4", [("rows", 8)], "Flip A to D. Find 8 different messages.",
                     H("Click the switches (or press 1 to 4). Watch P and the table.",
                       "P changes every time the number of 1s in A B C D goes from even to odd.",
                       "Just try 8 different combinations. Any 8 will do.")),
            choice_step("XOR gives 1 when its two inputs differ. 1 xor 1 = 0, then 0 xor 1 = 1. "
                        "What does a chain of XORs tell you about the bits?",
                        ["It is 1 when the number of 1s is ODD", "It is 1 when all bits are 1",
                         "It is 1 when any bit is 1", "It is 1 when the number of 1s is EVEN"],
                        "It is 1 when the number of 1s is ODD",
                        "Say it in words: when is the XOR chain ON?",
                        H("Each 1 flips the running answer. Start at 0 and flip once for every 1.",
                          "Flip an odd number of times and you end on 1.",
                          "ON when the number of 1s is odd. That is exactly what we need for P."),
                        ok="P = 1 exactly when the message has an odd number of 1s."),
            table_step("par4", ["P"], "Fill the even-parity bit P for all 16 messages (click a 0 to make it 1).",
                       H("P = 1 when the message A B C D has an ODD number of 1s. Count them.",
                         "Rows with one 1 or three 1s need P = 1. Rows with 0, 2 or 4 ones keep P = 0.",
                         "P = 1 on rows " + ", ".join(map(str, odd)) + "."),
                       default=0, exam="Design an even parity bit generator for 4 bit input."),
            choice_step("Which expression gives P, and which rows is it 1 on?",
                        ["P = A xor B xor C xor D = " + _mt(odd), "P = ABCD", "P = A + B + C + D",
                         "P = A xor B xor C xor D = " + _mt(even)],
                        "P = A xor B xor C xor D = " + _mt(odd),
                        "Pick the right expression and minterm list.",
                        H("P is 1 on the messages with an ODD number of 1s.",
                          "Which list holds the numbers 1, 2, 4, 7, 8 ...? Those have one or three 1s.",
                          "P = A xor B xor C xor D = " + _mt(odd) + "."),
                        ok="P = " + _mt(odd) + ".", tag=EXAM),
            slots_step("par4", {"x1": "XOR", "x2": "XOR", "p": "XOR"},
                       {"x1": "A xor B", "x2": "C xor D", "p": "makes P"},
                       {"x1": "First pair: 'odd number of 1s' is XOR.",
                        "x2": "Second pair: XOR again.",
                        "p": "Join the two pair-results the same way: XOR."},
                       "Draw the logic diagram of the generator: choose the three gates.",
                       H("Every gate does the same job: it passes on 'odd number of 1s'.",
                         "A chain (or tree) of the same gate, three times.",
                         "All three gates are XOR."),
                       exam="Design an even parity bit generator for 4 bit input."),
            see_step("parchk",
                     [("pred", "Make Error light up (a damaged message)", lambda v, o: o["Error"] == 1),
                      ("pred", "Make Error = 0 with 2 or more 1s", lambda v, o: o["Error"] == 0 and sum(v.values()) >= 2)],
                     "CHECKER: A to D is the message, P the parity bit received. Flip one bit and watch Error.",
                     H("Start with a good message plus its P (an even count of 1s), then flip ONE switch.",
                       "Try A = 1, B = 1 (and P = 0): Error = 0. Now flip P: Error = 1.",
                       "Good: A = 1, B = 1. Damaged: A = 1, B = 1, P = 1."),
                     note="Checker: it XORs the message AND the parity bit. Error = 1 means an odd count."),
        ],
        "done": ("sim", "par4", dict(A=1, B=1, C=1, D=0)),
        "items": [
            ("RULE", "Even parity: message + P always holds an EVEN number of 1s. P = A xor B xor C xor D."),
            ("MATH LINK", "Odd + odd = even, even + even = even. XOR adds up the 1s without carry."),
            ("REMEMBER", "Generator makes P. Checker XORs message + P: Error = 1 means damage."),
            ("EXAM", "4-bit generator asked in Nov 2024, Nov 2025 and Sep 2026."),
        ],
    }


def stage_gray():
    seq = [(0, "0000", "0000", "Binary 0000 -> Gray 0000."),
           (1, "0001", "0001", "Binary 0001 -> Gray 0001. One bit changed."),
           (2, "0010", "0011", "Binary 0010 -> Gray 0011. Binary changed 2 bits, Gray only 1."),
           (3, "0011", "0010", "Binary 0011 -> Gray 0010. Only one Gray bit changed."),
           (4, "0100", "0110", "Binary 0100 -> Gray 0110. Only one Gray bit changed.")]

    def bv(b):
        return {f"B{3 - i}": int(ch) for i, ch in enumerate(b)}

    g_rows = [(0, 1, 1, 0), (0, 1, 1, 1), (1, 0, 0, 0), (1, 0, 0, 1), (1, 1, 0, 0), (1, 1, 1, 1)]
    gv = dict(G3=1, G2=0, G1=1, G0=1)
    return {
        "id": "c6_gray", "title": "Gray code", "sub": "one bit changes at a time", "gates": [],
        "brief": [
            "WHAT IS IT FOR? A position sensor in plain binary can glitch: 0111 to 1000 flips FOUR "
            "bits at once. In GRAY code only ONE bit changes per step.",
            "Rule: Gray bit = B xor (the bit to its left).",
        ],
        "steps": [
            frames_step("b2g", [{"vals": bv(b), "caption": c} for _n, b, _g, c in seq],
                        "Count 0, 1, 2, 3, 4 and watch which Gray bits change."),
            see_step("b2g", [("rows", 6)], "Flip B3 to B0. Try 6 different numbers.",
                     H("Click the switches (or press 1 to 4). Watch the G bulbs.",
                       "The table on the right shows every binary number and its Gray code.",
                       "Any 6 different combinations will do.")),
            table_step("b2g", ["G3", "G2", "G1", "G0"], "Fill in the Gray code of these 6 binary numbers.",
                       H("G3 is the same as B3. Every other G bit = B xor the bit to its left.",
                         "Example 0110: G3 = 0, G2 = 0 xor 1 = 1, G1 = 1 xor 1 = 0, G0 = 1 xor 0 = 1.",
                         "0110 -> 0101,  0111 -> 0100,  1000 -> 1100,  1001 -> 1101,  1100 -> 1010,  1111 -> 1000."),
                       rows=g_rows),
            choice_step("Which set of equations converts BINARY to GRAY?",
                        ["G3 = B3, G2 = B3 xor B2, G1 = B2 xor B1, G0 = B1 xor B0",
                         "G3 = B3, G2 = B3 + B2, G1 = B2 + B1, G0 = B1 + B0",
                         "G3 = B3 xor B2, G2 = B2 xor B1, G1 = B1 xor B0, G0 = B0",
                         "Every G bit = B3 xor B2 xor B1 xor B0"],
                        "G3 = B3, G2 = B3 xor B2, G1 = B2 xor B1, G0 = B1 xor B0",
                        "Check your table against each set of equations.",
                        H("Test 0110 -> 0101 in each option. G3 must be 0, G2 must be 1.",
                          "The left bit is copied; each other bit XORs with the bit on its left.",
                          "G3 = B3, G2 = B3 xor B2, G1 = B2 xor B1, G0 = B1 xor B0."),
                        ok="Copy the left bit, XOR the rest in pairs.", tag=EXAM),
            slots_step("b2g", {"g2": "XOR", "g1": "XOR", "g0": "XOR"},
                       {"g2": "makes G2", "g1": "makes G1", "g0": "makes G0"},
                       {"g2": "G2 = B3 xor B2.", "g1": "G1 = B2 xor B1.", "g0": "G0 = B1 xor B0."},
                       "Draw the converter: choose the gate for G2, G1 and G0.",
                       H("Each Gray bit is made from two neighbouring binary bits.",
                         "The rule for each pair is the same gate every time.",
                         "All three are XOR. (G3 is just a wire from B3.)"),
                       exam="Design a 4-bit binary to Gray code converter."),
            frames_step("g2b", [{"vals": gv, "caption": c} for c in (
                "Now the other way. Gray 1 0 1 1. B3 = G3 = 1 (copy the left bit).",
                "B2 = B3 xor G2 = 1 xor 0 = 1.",
                "B1 = B2 xor G1 = 1 xor 1 = 0. Use the BINARY bit just found.",
                "B0 = B1 xor G0 = 0 xor 1 = 1. So Gray 1011 is binary 1101 (13).")],
                "Watch Gray to binary. Each step XORs with the previous binary bit.", tag=EXAM),
            bits_step(["Gray = 1 1 1 0", "B3 = G3. Then each B = (previous B) xor (this G)."],
                      ["B3", "B2", "B1", "B0"], [1, 0, 1, 1],
                      "Convert Gray 1110 to binary: light the bulbs.",
                      H("B3 = 1. Then B2 = B3 xor G2, and so on, using the binary bit you just found.",
                        "B2 = 1 xor 1 = 0. B1 = 0 xor 1 = 1. B0 = 1 xor 0 = 1.",
                        "Binary = 1 0 1 1."), tag=EXAM),
        ],
        "done": ("sim", "b2g", dict(B3=0, B2=1, B1=1, B0=0)),
        "items": [
            ("RULE", "Binary to Gray: G3 = B3, then G = B xor (bit on its left)."),
            ("RULE 2", "Gray to binary: B3 = G3, then B = (previous B) xor (this G)."),
            ("MATH LINK", "XOR is addition without carry, so each Gray bit is a 'difference' of neighbours."),
            ("EXAM", "Asked in Nov 2023, Apr 2026 and Sep 2026 (binary to Gray and Gray to binary)."),
        ],
    }


def stage_decoder():
    fr = []
    for k, (a, b) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
        cap = f"Input {a}{b} = {k}: only line Y{k} is ON. (Y{k} is the minterm m{k}.)"
        if k == 3:
            cap += " A decoder is a minterm generator."
        fr.append((dict(A=a, B=b), cap))
    return {
        "id": "c7_decoder", "title": "Decoder", "sub": "a code in, ONE wire out", "gates": [],
        "brief": [
            "WHAT IS IT FOR? A decoder turns a CODE into ONE chosen wire, like a lift panel: "
            "the code for floor 2 lights only lamp 2. De-code means un-code.",
            "Rule: n inputs give 2^n outputs. Output Yk is ON when the input code is k.",
        ],
        "steps": [
            frames_step("dec2", [{"vals": v, "caption": c} for v, c in fr],
                        "Watch the four codes. Which line lights each time?"),
            see_step("dec2", [("rows", 4)], "Flip A and B. Try all four codes.",
                     H("Click the switches (or press 1 and 2).",
                       "Each code lights exactly one of the four bulbs.",
                       "Try 00, 01, 10 and 11.")),
            choice_step("A 2-to-4 decoder gets A = 1 and B = 0. Which output line lights?",
                        ["Y0", "Y1", "Y2", "Y3"], "Y2", "Read the input as a binary number.",
                        H("A B = 1 0 is a binary number. What number is 10?",
                          "10 in binary = 2.",
                          "Y2 lights."),
                        ok="Binary 10 = 2, so Y2.", visual="sim", sim="dec2", vals=dict(A=1, B=0)),
            slots_step("dec2", {f"y{m}": "AND" for m in range(4)}, {f"y{m}": f"Y{m}" for m in range(4)},
                       {f"y{m}": f"Y{m} needs both of its two input wires ON at once: AND." for m in range(4)},
                       "Draw the logic diagram: which gate sits at every output?",
                       H("Each output is ON for ONE input code only: both wires into it must be ON.",
                         "The gate that needs both inputs ON is AND (the NOT gates are already placed).",
                         "All four are AND."),
                       exam="Explain 2 to 4 line Decoder with logic diagram and truth table."),
            see_step("dec3", [("rows", 6)], "Now 3 inputs and 8 lines. Try 6 different codes.",
                     H("Click the switches (or press 1 to 3).",
                       "Watch the one lit bulb walk down Y0 ... Y7.",
                       "Try 000, 001, 010, 011, 100 and 101."),
                     note="Three input bits give 2 x 2 x 2 = 8 lines."),
            table_step("dec3", [f"Y{m}" for m in range(8)],
                       "Fill the 3-to-8 truth table: click the single 1 on each row.",
                       H("In each row exactly ONE output is 1: the one whose number equals the input code.",
                         "Row 000 -> Y0, row 001 -> Y1, row 010 -> Y2 ... row 111 -> Y7 (a diagonal).",
                         "Put a 1 on the diagonal: row k has its 1 in column Yk."),
                       default=0, exam="Design 3 to 8 line decoder with logic diagram and truth table."),
            choice_step("In your 3-to-8 decoder, which product term drives Y5? (5 = 101)",
                        ["A B' C", "A' B C'", "A B C'", "A' B' C"], "A B' C",
                        "Write 101 as letters: 1 = plain letter, 0 = letter with a bar.",
                        H("5 in binary is 101. A is 1, B is 0, C is 1.",
                          "A stays plain, B gets a bar, C stays plain.",
                          "Y5 = A B' C (minterm m5)."),
                        ok="Y5 = m5 = A B' C. Level 4 minterms again!", tag=EXAM),
            choice_step("Cout of the full adder is Sum m(3, 5, 6, 7). With a 3-to-8 decoder and ONE OR gate, "
                        "which outputs go into the OR gate?",
                        ["Y3, Y5, Y6, Y7", "Y1, Y2, Y4, Y7", "Y0, Y1, Y2, Y4", "All eight"],
                        "Y3, Y5, Y6, Y7", "Use the minterm list as a shopping list.",
                        H("A decoder output IS a minterm. OR them to make the function.",
                          "The function is ON for minterms 3, 5, 6 and 7.",
                          "OR together Y3, Y5, Y6 and Y7."),
                        ok="Any Sum m(...) = OR of those decoder outputs."),
        ],
        "done": ("sim", "dec3", dict(A=1, B=0, C=1)),
        "items": [
            ("RULE", "A decoder has n inputs and 2^n outputs. Exactly one output is ON: Yk for input code k."),
            ("MATH LINK", "2 inputs: 2^2 = 4 lines. 3 inputs: 2^3 = 8 lines. Yk = minterm mk."),
            ("REMEMBER", "Function = OR of its decoder outputs: Cout = Y3 + Y5 + Y6 + Y7."),
            ("EXAM", "3-to-8 asked in Nov 2024, Nov 2025, Sep 2026. 2-to-4 in Apr 2026."),
        ],
    }


def stage_mux():
    fr = [
        (dict(S=0, I0=1, I1=0), "S = 0: the switch points at I0. Y copies I0 = 1."),
        (dict(S=1, I0=1, I1=0), "S = 1: the switch points at I1. Y copies I1 = 0."),
        (dict(S=1, I0=0, I1=1), "S = 1 and I1 = 1, so Y = 1. I0 is ignored."),
    ]
    ones_sum = {1, 2, 4, 7}
    ones_4v = {1, 3, 4, 11, 12, 13, 14, 15}
    e4 = mux_expected(ones_sum, 3, 2, "C")
    e8 = mux_expected(ones_4v, 4, 3, "D")
    return {
        "id": "c8_mux", "title": "Multiplexer", "sub": "many in, one out", "gates": [],
        "brief": [
            "WHAT IS IT FOR? A MUX is a selector: many inputs, ONE output, like choosing 1 of 8 TV "
            "channels. The SELECT lines say which input gets through.",
            "Rule: n selects choose 1 of 2^n inputs. Ik sits where minterm mk sits.",
        ],
        "steps": [
            frames_step("mux2", [{"vals": v, "caption": c} for v, c in fr],
                        "Watch the 2:1 MUX switch between two inputs."),
            see_step("mux2", [("rows", 6)], "Flip S, I0 and I1. Try 6 different rows.",
                     H("Click the switches (or press 1 to 3).",
                       "Flip S and see which input Y follows.",
                       "Try different I0 and I1 values with S = 0 and with S = 1."),
                     note="Y = I0 when S = 0, and Y = I1 when S = 1."),
            see_step("mux4", [("rows", 4)], "A 4:1 MUX has 2 select lines. Try all 4 select codes.",
                     H("Flip S1 and S0 (switches 1 and 2). The arrow shows the chosen input.",
                       "Set a data input to 1 and watch Y when its select code is chosen.",
                       "Try S1 S0 = 00, 01, 10 and 11."),
                     note="2 select lines give 2^2 = 4 choices."),
            choice_step("An 8:1 MUX has S2 S1 S0 = 1 0 1. Which data input reaches Y?",
                        ["I5", "I1", "I4", "I6"], "I5", "Read the select lines as a binary number.",
                        H("S2 S1 S0 = 1 0 1 is a binary number. Which number?",
                          "101 = 4 + 0 + 1.",
                          "5, so Y copies I5."),
                        ok="Select code k picks data input Ik."),
            mux_step(ones_sum, 3, 3, ["A", "B", "C"], "", "F(A,B,C) = Sum m(1, 2, 4, 7)",
                     ["0", "1"],
                     "Warm-up: 8:1 MUX, 3 variables. Put 0 or 1 on every data input.",
                     H("A, B, C are the select lines. Data input Ik gets 1 if minterm mk is in the list.",
                       "The list is 1, 2, 4, 7. So I1, I2, I4 and I7 get 1.",
                       "I0..I7 = 0 1 1 0 1 0 0 1.")),
            mux_step(ones_sum, 3, 2, ["A", "B"], "C", "F(A,B,C) = Sum m(1, 2, 4, 7)",
                     ["0", "1", "C", "C'"],
                     "Fill I0 to I3: A, B select and C goes to the data inputs.",
                     H("For each select code AB, look at the two rows (C = 0 and C = 1) beside it.",
                       "If F = 0, 0 -> put 0.  1, 1 -> put 1.  0, 1 -> put C.  1, 0 -> put C'.",
                       "I0 = C, I1 = C', I2 = C', I3 = C."),
                     exam="Use 4*1 Mux to implement the logic function F = Sum m(1, 2, 4, 7)."),
            mux_step(ones_4v, 4, 3, ["A", "B", "C"], "D", "F(A,B,C,D) = Sum m(1, 3, 4, 11, 12, 13, 14, 15)",
                     ["0", "1", "D", "D'"],
                     "Fill I0 to I7: A, B, C select and D goes to the data inputs.",
                     H("Pair the rows: select ABC = 000 owns m0 and m1 (D = 0 and D = 1), ABC = 001 owns m2 and m3 ...",
                       "Look at the two values beside each slot: 0,1 -> D.  1,0 -> D'.  0,0 -> 0.  1,1 -> 1.",
                       "I0..I7 = " + ", ".join(e8) + "."),
                     exam="Use 8*1 MUX to implement the logic function F = Sum m(1, 3, 4, 11, 12, 13, 14, 15)."),
            choice_step("How many select lines does a 16:1 MUX need?",
                        ["4", "2", "8", "16"], "4", "Use the 2^n rule.",
                        H("n select lines choose among 2^n inputs.",
                          "Which power of 2 gives 16?",
                          "2^4 = 16, so 4 select lines."),
                        ok="2^4 = 16."),
        ],
        "done": ("sim", "mux4", dict(S1=1, S0=0, I2=1)),
        "items": [
            ("RULE", "A MUX copies ONE data input to Y, chosen by the select lines. n select lines -> 2^n inputs."),
            ("MATH LINK", "Ik sits where minterm mk sits: put 1 on Ik if mk is in the list, else 0."),
            ("REMEMBER", "One variable too many? Use the pair trick: (0,0) -> 0, (1,1) -> 1, (0,1) -> var, (1,0) -> var'."),
            ("EXAM", "8:1 asked Nov 2024 and Apr 2026. 4:1 asked Sep 2026."),
        ],
    }


def stage_boss():
    bcout = _mt({3, 5, 6, 7})
    return {
        "id": "c9_boss", "title": "BOSS: mixed exam", "sub": "seven paper-style questions", "gates": [],
        "brief": [
            "Final test. One question from each topic: adder, subtractor, parity, decoder, MUX "
            "and the adder-subtractor.",
            "Work like in the exam. You still have 3 hints on each.",
        ],
        "steps": [
            choice_step("A full adder gets A = 1, B = 0 and Cin = 1. What are Cout and Sum?",
                        ["Cout 1, Sum 0", "Cout 0, Sum 1", "Cout 1, Sum 1", "Cout 0, Sum 0"], "Cout 1, Sum 0",
                        "Add the three bits.",
                        H("Add 1 + 0 + 1 in ordinary maths.",
                          "The answer is 2. Write it in binary: Cout is the left digit.",
                          "1 + 0 + 1 = 2 = binary 10: Cout 1, Sum 0."),
                        ok="1 + 0 + 1 = 10.", visual="sim", sim="fa", vals=dict(A=1, B=0, Cin=1), tag=EXAM),
            choice_step("A full subtractor gets A = 0, B = 1 and Bin = 1. What are Bout and Diff?",
                        ["Bout 1, Diff 0", "Bout 0, Diff 1", "Bout 1, Diff 1", "Bout 0, Diff 0"], "Bout 1, Diff 0",
                        "Subtract and decide if a borrow is needed.",
                        H("0 - 1 - 1 is negative, so a borrow is needed.",
                          "Diff = A xor B xor Bin = 0 xor 1 xor 1.",
                          "Bout = 1 and Diff = 0."),
                        ok="Diff = 0 xor 1 xor 1 = 0, and it borrows.", visual="sim", sim="fs",
                        vals=dict(A=0, B=1, Bin=1), tag=EXAM),
            choice_step("Even parity bit for the 4-bit message 1 1 0 1?",
                        ["P = 1", "P = 0"], "P = 1", "Count the 1s in the message.",
                        H("Count the 1s in 1 1 0 1.",
                          "Three 1s is odd. P must make the total even.",
                          "P = 1 (three plus one makes four)."),
                        ok="Three 1s, so P = 1.", tag=EXAM),
            choice_step("A receiver gets message 1 0 1 1 and parity bit 0 (even parity is used). Is it OK?",
                        ["Error: odd number of 1s", "OK: even number of 1s"], "Error: odd number of 1s",
                        "Count ALL the 1s received, parity bit included.",
                        H("Count the 1s in 1 0 1 1 and add the parity bit.",
                          "1 0 1 1 has three 1s, the parity bit adds none.",
                          "Three is odd, so there is an error."),
                        ok="Even parity needs an EVEN count.", tag=EXAM),
            choice_step("A 3-to-8 decoder gets A B C = 1 1 0. Which output line is ON?",
                        ["Y6", "Y3", "Y5", "Y7"], "Y6", "Read the input as a binary number.",
                        H("110 in binary is which number?",
                          "4 + 2 + 0.",
                          "Y6 (minterm m6)."),
                        ok="110 = 6, so Y6.", visual="sim", sim="dec3", vals=dict(A=1, B=1, C=0), tag=EXAM),
            mux_step({3, 5, 6, 7}, 3, 2, ["A", "B"], "C", "F(A,B,C) = Sum m(3, 5, 6, 7)   (practice function)",
                     ["0", "1", "C", "C'"],
                     "Practice: the full adder's Cout on a 4:1 MUX. A and B select, C goes to the data inputs.",
                     H("For each select code AB, look at the two rows beside it (C = 0 and C = 1).",
                       "AB = 00: 0,0.  AB = 01: 0,1.  AB = 10: 0,1.  AB = 11: 1,1.",
                       "I0 = 0, I1 = C, I2 = C, I3 = 1."), exam="Use 4*1 MUX (practice function)."),
            choice_step("An adder-subtractor has M = 1 and B = 0 1 1 0. What do the XOR gates give, "
                        "and what is the carry-in?",
                        ["1 0 0 1, carry-in 1", "0 1 1 0, carry-in 0", "1 0 0 1, carry-in 0", "0 1 1 0, carry-in 1"],
                        "1 0 0 1, carry-in 1", "M = 1 means subtract.",
                        H("XOR with M = 1 flips every bit of B.",
                          "M is also wired to the carry-in.",
                          "B flips to 1 0 0 1 and the carry-in is 1."),
                        ok="Flip B and add 1: A - B = A + B' + 1.", visual="xor", tag=EXAM),
        ],
        "done": ("table", ["Topic", "Rule"],
                 [["Adder", "xor + and"], ["Subtractor", "A'B borrow"], ["Parity", "xor chain"],
                  ["Decoder", "2^n lines"], ["MUX", "2^n inputs"]]),
        "items": [
            ("YOU CAN NOW", "Build adders, subtractors, parity generators, Gray converters, decoders "
                            "and multiplexers, and explain what each one is FOR."),
            ("ONE SHEET", "Half adder: XOR + AND.  Full adder: 2 HA + OR.  Parity: XOR chain.  "
                          "Decoder: Yk = minterm.  MUX: Ik = minterm mk."),
            ("NEXT", "Everything is in your notebook. The COMBINATIONAL CIRCUITS lab lets you replay each circuit."),
        ],
    }


def build_comb_stages():
    return [stage_half(), stage_full(), stage_sub(), stage_chain(), stage_parity(),
            stage_gray(), stage_decoder(), stage_mux(), stage_boss()]


# ------------------------------------------------------------------
# THE PUZZLE
# ------------------------------------------------------------------
class BasicCombinationalPuzzle(BasicGatesPuzzle):
    """Nine-stage beginner course on combinational circuits."""

    COURSE_TITLE = "BASIC LEVEL 5  -  COMBINATIONAL CIRCUITS"
    LEGEND_EXTRA = dict(BasicGatesPuzzle.LEGEND_EXTRA, **{
        "cframes": "NEXT / BACK or LEFT / RIGHT, then CHECK",
        "csee": "click switches or press 1-9",
        "ctable": "click a cell, or arrows + 0 / 1",
        "cslots": "click a ?, SPACE = next gate, 1-3 = pick, TAB = next ?",
        "cmux": "UP / DOWN = slot, 1-4 = pick, SPACE = next",
        "cbits": "click bulbs or press 1-5",
        "choice": "click an answer or press 1-4",
    })

    def _make_stages(self):
        return build_comb_stages()

    def __init__(self, notebook=None):
        super().__init__(notebook)
        self.cfonts = {"body": self.f_body, "small": self.f_small, "tiny": self.f_tiny}

    # ---------------- helpers ----------------
    @property
    def sim(self):
        return CL.BY_ID[self.step["sim"]]

    def _outs(self):
        return CL.sim_outs(self.sim, self.st["vals"])

    def _key_names(self):
        sim = self.sim
        if sim["net"] is not None and sim["draw"] is None:
            return [i["name"] for i in sim["net"].inputs]
        return sim["inputs"]

    # ---------------- step state ----------------
    def _enter_step(self):
        super()._enter_step()
        step, st = self.step, self.st
        kind = step["kind"]
        if kind in ("csee", "cslots"):
            sim = self.sim
            st["vals"] = CL.default_vals(sim)
            st["vals"].update(step.get("start", {}))
            st["rows"] = set()
            st["done"] = set()
            st["bad"] = set()
            st["sel"] = 0
            st["types"] = {nid: None for nid in step.get("hidden", {})}
            self._note_vals()
        elif kind == "cframes":
            st.update(frame=0, seen=1)
        elif kind == "ctable":
            sim, rows, cols, exp = self._table_spec(step)
            default = step.get("default")
            st["cells"] = {(r, c): default for r in range(len(rows)) for c in range(len(cols))}
            st["cur"] = (0, 0)
            st["bad"] = set()
        elif kind == "cmux":
            n = 1 << step["n_sel"]
            st["slots"] = [None] * n
            st["sel"] = 0
            st["bad"] = set()
        elif kind == "cbits":
            st["bits"] = [0] * len(step["target"])

    def _note_vals(self):
        """Record the row seen and which sandbox goals are met."""
        st, step = self.st, self.step
        if step["kind"] != "csee":
            return
        sim = self.sim
        st["rows"].add(CL.row_index(sim, st["vals"]))
        outs = self._outs()
        for i, g in enumerate(step["goals"]):
            if g[0] == "rows":
                if len(st["rows"]) >= g[1]:
                    st["done"].add(i)
            elif g[2](st["vals"], outs):
                st["done"].add(i)

    # ---------------- table helpers ----------------
    def _table_spec(self, step):
        sim = CL.BY_ID[step["sim"]]
        rows = step.get("rows") or [c for c, _o in CL.table_rows(sim)]
        cols = step["cols"]
        exp = []
        for r in rows:
            v = CL.default_vals(sim)
            v.update(dict(zip(sim["tin"], r)))
            o = CL.sim_outs(sim, v)
            exp.append([o[c] for c in cols])
        return sim, rows, cols, exp

    # ---------------- events ----------------
    def _on_key(self, event):
        key = event.key
        if self.phase == "done" or key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_h):
            return super()._on_key(event)
        kind = self.step["kind"]
        st = self.st
        d = self._digit(key)
        if kind == "csee":
            if d is not None:
                idx = 9 if d == 0 else d - 1
                names = self._key_names()
                if idx < len(names):
                    self._on_action(("in", names[idx]))
            elif key == pygame.K_MINUS:
                names = self._key_names()
                if len(names) > 10:
                    self._on_action(("in", names[10]))
        elif kind == "cframes":
            if key == pygame.K_LEFT:
                self._on_action(("frame", -1))
            elif key == pygame.K_RIGHT:
                self._on_action(("frame", 1))
        elif kind == "ctable":
            self._table_key(key, d)
        elif kind == "cslots":
            ids = list(self.step["hidden"])
            if key in (pygame.K_TAB, pygame.K_DOWN):
                st["sel"] = (st["sel"] + 1) % len(ids)
            elif key == pygame.K_UP:
                st["sel"] = (st["sel"] - 1) % len(ids)
            elif key == pygame.K_SPACE:
                self._on_action(("slot", ids[st["sel"]]))
            elif d is not None and 1 <= d <= len(self.step["options"]):
                self._set_slot(ids[st["sel"]], self.step["options"][d - 1])
        elif kind == "cmux":
            n = len(st["slots"])
            opts = self.step["options"]
            if key == pygame.K_UP:
                st["sel"] = (st["sel"] - 1) % n
            elif key in (pygame.K_DOWN, pygame.K_TAB):
                st["sel"] = (st["sel"] + 1) % n
            elif key == pygame.K_SPACE:
                self._cycle_mux(st["sel"])
            elif d is not None and 1 <= d <= len(opts):
                self._set_mux(st["sel"], opts[d - 1])
        elif kind == "cbits":
            if d is not None and 1 <= d <= len(st["bits"]):
                st["bits"][d - 1] ^= 1
        else:
            super()._on_key(event)

    def _table_key(self, key, d):
        st = self.st
        sim, rows, cols, _exp = self._table_spec(self.step)
        r, c = st["cur"]
        if key == pygame.K_UP:
            st["cur"] = ((r - 1) % len(rows), c)
        elif key == pygame.K_DOWN:
            st["cur"] = ((r + 1) % len(rows), c)
        elif key == pygame.K_LEFT:
            st["cur"] = (r, (c - 1) % len(cols))
        elif key == pygame.K_RIGHT:
            st["cur"] = (r, (c + 1) % len(cols))
        elif d in (0, 1):
            st["cells"][(r, c)] = d
            st["bad"].discard((r, c))
            if r < len(rows) - 1:
                st["cur"] = (r + 1, c)
            elif c < len(cols) - 1:
                st["cur"] = (0, c + 1)

    def _on_action(self, action):
        name = action[0]
        st = self.st
        if self.phase != "play":
            return super()._on_action(action)
        kind = self.step["kind"]
        if name == "in" and kind in ("csee", "cslots"):
            st["vals"][action[1]] = 1 - st["vals"].get(action[1], 0)
            self._note_vals()
        elif name == "frame":
            frames = len(self.step["frames"])
            st["frame"] = (st["frame"] + action[1]) % frames
            st["seen"] = max(st["seen"], st["frame"] + 1)
        elif name == "tcell":
            r, c = action[1], action[2]
            st["cur"] = (r, c)
            cur = st["cells"][(r, c)]
            st["cells"][(r, c)] = 0 if cur is None else 1 - cur
            st["bad"].discard((r, c))
        elif name == "slot":
            ids = list(self.step["hidden"])
            st["sel"] = ids.index(action[1])
            opts = self.step["options"]
            cur = st["types"][action[1]]
            nxt = opts[0] if cur is None else opts[(opts.index(cur) + 1) % len(opts)]
            self._set_slot(action[1], nxt)
        elif name == "slotopt":
            ids = list(self.step["hidden"])
            self._set_slot(ids[st["sel"]], action[1])
        elif name == "mslot":
            st["sel"] = action[1]
            self._cycle_mux(action[1])
        elif name == "mopt":
            self._set_mux(st["sel"], action[1])
        elif name == "bit":
            st["bits"][action[1]] ^= 1
        else:
            super()._on_action(action)

    def _set_slot(self, nid, gate):
        self.st["types"][nid] = gate
        self.st["bad"].discard(nid)

    def _cycle_mux(self, k):
        opts = self.step["options"]
        cur = self.st["slots"][k]
        self._set_mux(k, opts[0] if cur is None else opts[(opts.index(cur) + 1) % len(opts)])

    def _set_mux(self, k, opt):
        self.st["slots"][k] = opt
        self.st["bad"].discard(k)

    # ---------------- checking ----------------
    def _check(self):
        step, st = self.step, self.st
        kind = step["kind"]
        if kind == "cframes":
            if st["seen"] >= len(step["frames"]):
                self._advance("")
            else:
                self._say(f"Look at every picture first ({st['seen']}/{len(step['frames'])}).", False)
        elif kind == "csee":
            missing = [i for i in range(len(step["goals"])) if i not in st["done"]]
            if not missing:
                self._right()
            else:
                g = step["goals"][missing[0]]
                if g[0] == "rows":
                    self._say(f"Try more rows ({len(st['rows'])}/{g[1]} so far).", False)
                else:
                    self._say("Not yet: " + g[1] + ".", False)
        elif kind == "ctable":
            self._check_table()
        elif kind == "cslots":
            self._check_slots()
        elif kind == "cmux":
            self._check_mux()
        elif kind == "cbits":
            if st["bits"] == step["target"]:
                self._right()
            else:
                n = sum(1 for x, y in zip(st["bits"], step["target"]) if x != y)
                self._wrong(f"Not yet: {n} bulb(s) differ. Work it out column by column.")
        else:
            super()._check()

    def _check_table(self):
        step, st = self.step, self.st
        sim, rows, cols, exp = self._table_spec(step)
        if any(v is None for v in st["cells"].values()):
            self._say("Fill every cell first (select it, then press 0 or 1).", False)
            return
        bad = {(r, c) for r in range(len(rows)) for c in range(len(cols))
               if st["cells"][(r, c)] != exp[r][c]}
        st["bad"] = bad
        if not bad:
            self._right()
            return
        r, c = min(bad)
        names = ", ".join(f"{n} = {v}" for n, v in zip(sim["tin"], rows[r]))
        self._wrong(f"{len(bad)} cell(s) wrong. Check the {cols[c]} cell of the row with {names}.")

    def _check_slots(self):
        step, st = self.step, self.st
        ids = list(step["hidden"])
        empty = [i for i in ids if st["types"][i] is None]
        if empty:
            self._say(f"Choose a gate for every ? first ({len(empty)} left).", False)
            return
        bad = [i for i in ids if st["types"][i] != step["hidden"][i]]
        st["bad"] = set(bad)
        if not bad:
            self._right("The circuit works: flip the switches to test it.")
        else:
            i = bad[0]
            self._wrong(f"{step['labels'][i]}: {step['reasons'][i]}")

    def _mux_expect(self):
        s = self.step
        return mux_expected(s["ones"], s["nvars"], s["n_sel"], s["last"])

    def _check_mux(self):
        step, st = self.step, self.st
        if None in st["slots"]:
            self._say("Fill every data input first.", False)
            return
        exp = self._mux_expect()
        bad = {k for k in range(len(exp)) if st["slots"][k] != exp[k]}
        st["bad"] = bad
        if not bad:
            self._right("F = " + ", ".join(exp) + " on I0 ... I%d." % (len(exp) - 1))
            return
        k = min(bad)
        lo, hi = self._mux_pair(k)
        if step["nvars"] == step["n_sel"]:
            self._wrong(f"I{k}: minterm m{k} is {lo}, so I{k} must be {lo}.")
        else:
            self._wrong(f"I{k}: the pair is {lo}, {hi} (last variable 0, then 1). "
                        f"Pairs: 0,0 -> 0   1,1 -> 1   0,1 -> {step['last']}   1,0 -> {step['last']}'.")

    def _mux_pair(self, k):
        s = self.step
        if s["nvars"] == s["n_sel"]:
            return int(k in s["ones"]), None
        return int((2 * k) in s["ones"]), int((2 * k + 1) in s["ones"])

    # ---------------- drawing: frame extras ----------------
    def _tag(self):
        return self.step.get("tag") if self.phase == "play" else None

    def _pill(self, screen, rect, text, color):
        pygame.draw.rect(screen, (24, 36, 30) if color == GREEN else (40, 36, 18), rect, border_radius=10)
        pygame.draw.rect(screen, color, rect, 2, border_radius=10)
        img = self.f_tiny.render(text, True, color)
        screen.blit(img, img.get_rect(center=rect.center))

    def _draw_header(self, screen):
        super()._draw_header(screen)
        tag = self._tag()
        if tag:
            self._pill(screen, pygame.Rect(836, 44, 134, 22), tag, YELLOW if tag == EXAM else CYAN)

    def side_needed_height(self):
        """Pixels the briefing and task use in the side box (a test checks this fits)."""
        y = 12 + 28
        for para in self.stage["brief"]:
            y += 20 * len(wrap_text(self.f_tiny, para, SIDE.width - 28)) + 6
        y += 4 + 26
        y += 20 * len(wrap_text(self.f_tiny, self.step["task"], SIDE.width - 28))
        return y

    # ---------------- drawing: shared ----------------
    def _note_lines(self, screen, text, y=None, color=CYAN, n=2):
        y = WORK.y + 12 if y is None else y
        for line in wrap_text(self.f_small, text, WORK.width - 36)[:n]:
            screen.blit(self.f_small.render(line, True, color), (WORK.x + 18, y))
            y += 22
        return y

    def _readout(self, screen, y, sim, vals, lines=2):
        outs = CL.sim_outs(sim, vals)
        if sim["readout"]:
            for line in sim["readout"](vals, outs)[:lines]:
                for sub in wrap_text(self.f_small, line, WORK.width - 36)[:1]:
                    screen.blit(self.f_small.render(sub, True, WHITE), (WORK.x + 18, y))
                    y += 22

    # ---------------- drawing: csee ----------------
    def _draw_csee(self, screen):
        step, st = self.step, self.st
        sim = self.sim
        self._note_lines(screen, step.get("note") or ("WHAT IS IT FOR?  " + sim["purpose"]), n=2)
        top = WORK.y + 58
        bottom = WORK.bottom - 92
        tv = CL.table_view(sim, st["vals"])
        tab_w = 0
        if tv is not None:
            tab_w = min(250, CL.table_col_width(tv[0], tv[1], self.cfonts) * len(tv[0]) + 10)
        area = pygame.Rect(WORK.x + 8, top, WORK.width - 16 - (tab_w + 6 if tab_w else 0), bottom - top)
        CL.render_sim(screen, sim, area, st["vals"], CL.DARK, self.cfonts, hits=self.buttons)
        if tv is not None:
            CL.draw_table(screen, pygame.Rect(area.right + 6, top, tab_w, bottom - top),
                          tv[0], tv[1], tv[2], CL.DARK, self.cfonts)
        self._readout(screen, bottom + 4, sim, st["vals"])
        self._goal_chips(screen)

    def _goal_chips(self, screen):
        step, st = self.step, self.st
        x = WORK.x + 18
        y = WORK.bottom - 34
        for i, g in enumerate(step["goals"]):
            label = f"{len(st['rows'])}/{g[1]} rows tried" if g[0] == "rows" else g[1]
            ok = i in st["done"]
            if g[0] == "rows" and ok:
                label = f"{g[1]} rows tried"
            img = self.f_small.render(("[x] " if ok else "[ ] ") + label, True, GREEN if ok else GREY)
            screen.blit(img, (x, y))
            x += img.get_width() + 24

    # ---------------- drawing: cframes ----------------
    def _draw_cframes(self, screen):
        step, st = self.step, self.st
        sim = self.sim
        frame = step["frames"][st["frame"]]
        total = len(step["frames"])
        for i in range(total):
            cx = WORK.centerx - (total - 1) * 14 + i * 28
            if i == st["frame"]:
                pygame.draw.circle(screen, CYAN, (cx, WORK.y + 24), 8)
            elif i < st["seen"]:
                pygame.draw.circle(screen, GREEN, (cx, WORK.y + 24), 6)
            else:
                pygame.draw.circle(screen, GREY, (cx, WORK.y + 24), 6, 2)
        for label, delta, bx in (("< BACK", -1, WORK.x + 14), ("NEXT >", 1, WORK.right - 124)):
            self._button(screen, pygame.Rect(bx, WORK.y + 8, 110, 32), label, ("frame", delta), CYAN)
        vals = CL.default_vals(sim)
        vals.update(frame["vals"])
        area = pygame.Rect(WORK.x + 8, WORK.y + 48, WORK.width - 16, WORK.height - 48 - 110)
        CL.render_sim(screen, sim, area, vals, CL.DARK, self.cfonts, hits=None,
                      active=frame.get("active"), in_keys=False)
        y = WORK.bottom - 100
        for line in wrap_text(self.f_body, frame["caption"], WORK.width - 36)[:4]:
            screen.blit(self.f_body.render(line, True, WHITE), (WORK.x + 18, y))
            y += 24

    # ---------------- drawing: ctable ----------------
    def _draw_ctable(self, screen):
        step, st = self.step, self.st
        sim, rows, cols, exp = self._table_spec(step)
        note = step.get("note") or "Click a cell to flip it, or use the arrow keys and press 0 or 1."
        self._note_lines(screen, note, n=2)
        nin, nout = len(sim["tin"]), len(cols)
        nblocks = 2 if len(rows) > 8 else 1
        per = int(math.ceil(len(rows) / float(nblocks)))
        ncol = nin + nout
        cw = max(26, min(50, (WORK.width - 40 - (nblocks - 1) * 30) // (nblocks * ncol)))
        rh = max(22, min(36, (WORK.height - 120) // (per + 1)))
        width = ncol * cw
        total_w = nblocks * width + (nblocks - 1) * 30
        x0 = WORK.x + (WORK.width - total_w) // 2
        y0 = WORK.y + 72
        for b in range(nblocks):
            bx = x0 + b * (width + 30)
            heads = list(sim["tin"]) + list(cols)
            for j, h in enumerate(heads):
                r = pygame.Rect(bx + j * cw, y0, cw - 3, rh - 2)
                pygame.draw.rect(screen, (30, 60, 84), r, border_radius=4)
                img = self.f_small.render(h, True, YELLOW if j >= nin else WHITE)
                if img.get_width() > r.w - 2:
                    img = self.f_tiny.render(h, True, YELLOW if j >= nin else WHITE)
                screen.blit(img, img.get_rect(center=r.center))
            for i in range(per):
                ri = b * per + i
                if ri >= len(rows):
                    break
                ry = y0 + (i + 1) * rh
                for j, v in enumerate(rows[ri]):
                    r = pygame.Rect(bx + j * cw, ry, cw - 3, rh - 2)
                    pygame.draw.rect(screen, (24, 40, 58), r, border_radius=4)
                    img = self.f_body.render(str(v), True, WHITE)
                    screen.blit(img, img.get_rect(center=r.center))
                for c in range(nout):
                    r = pygame.Rect(bx + (nin + c) * cw, ry, cw - 3, rh - 2)
                    val = st["cells"][(ri, c)]
                    pygame.draw.rect(screen, (28, 54, 40) if val else (30, 34, 44), r, border_radius=4)
                    edge = RED if (ri, c) in st["bad"] else (YELLOW if st["cur"] == (ri, c) else GREY)
                    pygame.draw.rect(screen, edge, r, 3 if edge != GREY else 1, border_radius=4)
                    txt = "?" if val is None else str(val)
                    col = GREY if val is None else (GREEN if val else (120, 136, 150))
                    img = self.f_body.render(txt, True, col)
                    screen.blit(img, img.get_rect(center=r.center))
                    self.buttons.append((r, ("tcell", ri, c)))

    # ---------------- drawing: cslots ----------------
    def _draw_cslots(self, screen):
        step, st = self.step, self.st
        sim = self.sim
        ids = list(step["hidden"])
        n_left = sum(1 for i in ids if st["types"][i] is None)
        self._note_lines(screen, step.get("note") or "Click a ? to choose its gate. "
                         "Flip the switches to test your circuit.", n=2)
        top, bottom = WORK.y + 58, WORK.bottom - 96
        area = pygame.Rect(WORK.x + 8, top, WORK.width - 16, bottom - top)
        hover = None
        mp = pygame.mouse.get_pos()
        hits = []
        info = CL.render_sim(screen, sim, area, st["vals"], CL.DARK, self.cfonts, hits=hits,
                             types=dict(st["types"]), mask_outputs=n_left > 0)
        self.buttons.extend(hits)
        for rect, act in hits:
            if act[0] == "slot" and rect.collidepoint(mp):
                hover = act[1]
        if isinstance(info, dict):
            for nid in ids:
                r = info.get(nid)
                if r is None:
                    continue
                if nid in st["bad"]:
                    pygame.draw.rect(screen, RED, r.inflate(10, 10), 3, border_radius=6)
                if ids[st["sel"]] == nid:
                    pygame.draw.rect(screen, YELLOW, r.inflate(12, 12), 2, border_radius=7)
                lab = step["labels"].get(nid)
                if lab:
                    img = self.f_tiny.render(lab, True, YELLOW)
                    box = img.get_rect(midtop=(r.centerx, r.bottom + 3)).inflate(6, 2)
                    pygame.draw.rect(screen, (11, 24, 38), box, border_radius=4)
                    screen.blit(img, img.get_rect(center=box.center))
            if hover:
                opts = step["options"]
                cur = st["types"][hover]
                nxt = opts[0] if cur is None else opts[(opts.index(cur) + 1) % len(opts)]
                r = info[hover]
                tip = self.f_tiny.render(f"click: {cur or '?'} -> {nxt}", True, WHITE)
                box = tip.get_rect(midbottom=(r.centerx, r.y - 6)).inflate(10, 6)
                pygame.draw.rect(screen, (10, 20, 30), box, border_radius=5)
                pygame.draw.rect(screen, YELLOW, box, 1, border_radius=5)
                screen.blit(tip, tip.get_rect(center=box.center))
        # option buttons for the selected slot
        sel = ids[st["sel"]]
        y = WORK.bottom - 78
        screen.blit(self.f_small.render(f"Selected: {step['labels'].get(sel, sel)}", True, YELLOW),
                    (WORK.x + 18, y))
        for k, opt in enumerate(step["options"]):
            r = pygame.Rect(WORK.x + 18 + k * 96, y + 26, 88, 32)
            on = st["types"][sel] == opt
            self._button(screen, r, f"{k + 1}  {opt}", ("slotopt", opt), GREEN if on else GREY)
        if n_left == 0:
            o = CL.sim_outs(sim, st["vals"])
            txt = "Output now:  " + "  ".join(f"{k}={o[k]}" for k in sim["outs"][:4])
            room = WORK.right - (WORK.x + 300) - 10
            font = self.f_small if self.f_small.size(txt)[0] <= room else self.f_tiny
            screen.blit(font.render(txt, True, GREEN), (WORK.x + 300, y + 34))
        else:
            screen.blit(self.f_small.render(f"{n_left} ? left", True, GREY), (WORK.x + 330, y + 32))

    # ---------------- drawing: cmux ----------------
    def _draw_cmux(self, screen):
        step, st = self.step, self.st
        n_sel = step["n_sel"]
        nslots = 1 << n_sel
        exp_full = step["nvars"] != n_sel
        screen.blit(self.f_small.render(step["fn_text"], True, CYAN), (WORK.x + 18, WORK.y + 12))
        hint = ("Each slot: look at the pair of rows for that select code."
                if exp_full else "Each slot: is its minterm in the list?")
        screen.blit(self.f_tiny.render(hint, True, GREY), (WORK.x + 18, WORK.y + 36))
        top = WORK.y + 62
        avail = WORK.height - 62 - 96
        rh = min(34, avail // nslots)
        sel_names = step["sel_names"]
        bx0, bx1 = WORK.x + 420, WORK.x + 484
        ytop = top
        ybot = top + rh * nslots
        pts = [(bx0, ytop), (bx1, ytop + 14), (bx1, ybot - 14), (bx0, ybot)]
        pygame.draw.polygon(screen, PANEL, pts)
        pygame.draw.polygon(screen, WHITE, pts, 2)
        lab = self.f_small.render(f"MUX {nslots}:1", True, WHITE)
        screen.blit(lab, lab.get_rect(center=((bx0 + bx1) // 2, (ytop + ybot) // 2)))
        for k in range(nslots):
            y = top + k * rh
            cy = y + rh // 2
            row = pygame.Rect(WORK.x + 14, y + 1, 300, rh - 2)
            sel = st["sel"] == k
            pygame.draw.rect(screen, (30, 50, 70) if sel else (20, 34, 50), row, border_radius=5)
            pygame.draw.rect(screen, RED if k in st["bad"] else (YELLOW if sel else (50, 70, 90)),
                             row, 2, border_radius=5)
            code = format(k, f"0{n_sel}b")
            lo, hi = self._mux_pair(k)
            if exp_full:
                m0, m1 = 2 * k, 2 * k + 1
                txt = f"I{k}  {''.join(sel_names)}={code}   m{m0}={lo}  m{m1}={hi}"
            else:
                txt = f"I{k}  {''.join(sel_names)}={code}   m{k} = {lo}"
            screen.blit(self.f_tiny.render(txt, True, WHITE), (row.x + 8, row.centery - 8))
            chosen = st["slots"][k]
            chip = pygame.Rect(WORK.x + 326, y + 3, 56, rh - 6)
            pygame.draw.rect(screen, (30, 70, 56) if chosen else (30, 34, 44), chip, border_radius=6)
            pygame.draw.rect(screen, GREEN if chosen else GREY, chip, 2, border_radius=6)
            img = self.f_small.render(chosen or "?", True, WHITE if chosen else GREY)
            screen.blit(img, img.get_rect(center=chip.center))
            pygame.draw.line(screen, GREEN if chosen else GREY, (chip.right, cy), (bx0, cy), 2)
            self.buttons.append((row, ("mslot", k)))
            self.buttons.append((chip, ("mslot", k)))
        oy = (ytop + ybot) // 2
        pygame.draw.line(screen, GREY, (bx1, oy), (bx1 + 36, oy), 3)
        screen.blit(self.f_body.render("F", True, YELLOW), (bx1 + 44, oy - 10))
        sx = (bx0 + bx1) // 2 - 8
        screen.blit(self.f_tiny.render("selects: " + " ".join(sel_names), True, CYAN),
                    (bx0 - 8, ybot + 6))
        # option buttons
        y = WORK.bottom - 70
        screen.blit(self.f_small.render(f"Selected slot: I{st['sel']}", True, YELLOW), (WORK.x + 18, y))
        for k, opt in enumerate(step["options"]):
            r = pygame.Rect(WORK.x + 18 + k * 96, y + 26, 88, 32)
            on = st["slots"][st["sel"]] == opt
            self._button(screen, r, f"{k + 1}  {opt}", ("mopt", opt), GREEN if on else GREY)

    # ---------------- drawing: cbits ----------------
    def _draw_cbits(self, screen):
        step, st = self.step, self.st
        y = WORK.y + 22
        for line in step["context"]:
            screen.blit(self.f_title.render(line, True, WHITE), (WORK.x + 24, y))
            y += 40
        n = len(step["target"])
        xs = [WORK.centerx + (i - (n - 1) / 2.0) * 100 for i in range(n)]
        by = WORK.y + 280
        screen.blit(self.f_small.render("YOUR ANSWER (click the bulbs)", True, GREEN), (WORK.x + 24, by - 80))
        for i, (x, v) in enumerate(zip(xs, st["bits"])):
            cx = int(x)
            draw_bulb(screen, cx, by, 32, v)
            lab = self.f_small.render(step["labels"][i], True, WHITE)
            screen.blit(lab, lab.get_rect(center=(cx, by + 50)))
            val = self.f_body.render(str(v), True, YELLOW if v else GREY)
            screen.blit(val, val.get_rect(center=(cx, by + 76)))
            self.buttons.append((pygame.Rect(cx - 45, by - 45, 90, 150), ("bit", i)))
        num = 0
        for b in st["bits"]:
            num = num * 2 + b
        screen.blit(self.f_body.render(f"Your bulbs read {num} in ordinary maths", True, CYAN),
                    (WORK.x + 24, WORK.bottom - 34))

    # ---------------- drawing: choice pictures ----------------
    def _draw_extra_visual(self, screen, step, top, bottom):
        visual = step["visual"]
        area = pygame.Rect(WORK.x + 10, top + 2, WORK.width - 20, max(40, bottom - top - 4))
        if visual == "sim":
            sim = CL.BY_ID[step["sim"]]
            vals = CL.default_vals(sim)
            vals.update(step["vals"])
            CL.render_sim(screen, sim, area, vals, CL.DARK, self.cfonts, hits=None,
                          mask_outputs=True, in_keys=False)
        elif visual == "kmap":
            n, ones, loops_on = step["kmap"]
            vals = vals_from(n, ones)
            loops = []
            if loops_on:
                loops = [(l, i) for i, l in enumerate(solution_loops(n, vals, "ones"))]
            cell = max(30, min(52, (area.h - 40) // 2))
            origin = (area.x + 90, area.y + 28)
            draw_kmap(screen, (self.f_body, self.f_small, self.f_tiny), origin, cell, n, vals=vals,
                      loops=loops, nums=True)
            tx = origin[0] + 4 * cell + 36
            lines = ["Rows: A    Columns: B C", "Cells with a small number are m0 .. m7",
                     "1s at: " + ", ".join(str(m) for m in sorted(ones))]
            for i, line in enumerate(lines):
                screen.blit(self.f_tiny.render(line, True, GREY), (tx, area.y + 30 + i * 20))
        elif visual == "xor":
            rows = [["0", "0", "0"], ["0", "1", "1"], ["1", "0", "1"], ["1", "1", "0"]]
            CL.draw_table(screen, pygame.Rect(area.x + 40, area.y + 2, 200, area.h - 4),
                          ["M", "B", "B xor M"], rows, None, CL.DARK, self.cfonts)
            lines = ["When M = 0 the output is B: unchanged.", "When M = 1 the output is NOT B."]
            for i, line in enumerate(lines):
                screen.blit(self.f_small.render(line, True, WHITE), (area.x + 270, area.y + 30 + i * 28))

    # ---------------- stage-complete card ----------------
    def _done_text_height(self, stage):
        rw = FULL.right - (FULL.x + 390) - 24
        y = 0
        for _label, text in stage["items"]:
            y += 24 + 23 * len(wrap_text(self.f_small, text, rw)) + 10
        return y

    def _draw_done(self, screen):
        stage = self.stage
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, GREEN, FULL, 3, border_radius=10)
        screen.blit(self.f_big.render(f"STAGE {self.stage_i + 1} COMPLETE", True, GREEN), (FULL.x + 24, FULL.y + 14))
        screen.blit(self.f_body.render(f"{stage['title']}  -  {stage['sub']}", True, WHITE),
                    (FULL.x + 24, FULL.y + 62))
        left = pygame.Rect(FULL.x + 20, FULL.y + 100, 350, 290)
        kind = stage["done"][0]
        if kind == "sim":
            sim = CL.BY_ID[stage["done"][1]]
            vals = CL.default_vals(sim)
            vals.update(stage["done"][2])
            pygame.draw.rect(screen, (11, 24, 38), left, border_radius=8)
            CL.render_sim(screen, sim, left.inflate(-4, -4), vals, CL.DARK, self.cfonts, hits=None, in_keys=False)
        else:
            self._done_table(screen, left.x + 6, left.y + 6, stage["done"][1], stage["done"][2],
                             [110, 130] if len(stage["done"][1]) == 2 else 80, rowh=36)
        rx = FULL.x + 390
        rw = FULL.right - rx - 24
        y = FULL.y + 100
        for label, text in stage["items"]:
            screen.blit(self.f_small.render(label, True, CYAN), (rx, y))
            y += 24
            for line in wrap_text(self.f_small, text, rw):
                screen.blit(self.f_small.render(line, True, WHITE), (rx, y))
                y += 23
            y += 10
        screen.blit(self.f_small.render(
            "Saved to NOTEBOOK [N]  >  TEST THE LOGIC  >  MY BASIC NOTES", True, YELLOW),
            (FULL.x + 24, FULL.bottom - 62))
        screen.blit(self.f_tiny.render(
            "Replay any circuit: NOTEBOOK > TEST THE LOGIC > COMBINATIONAL CIRCUITS", True, GREY),
            (FULL.x + 24, FULL.bottom - 38))
        rect = pygame.Rect(FULL.right - 230, FULL.bottom - 52, 210, 38)
        last = self.stage_i >= len(self.stages) - 1
        self._button(screen, rect, "FINISH LEVEL" if last else "NEXT STAGE  [ENTER]", ("next",), GREEN)

    # ---------------- notebook autofill ----------------
    def notebook_lines(self, stage):
        return NOTES[stage["id"]]


NOTES = {
    "c1_half": [
        "COMBINATIONAL 1: HALF ADDER",
        "- A circuit whose output depends ONLY on its inputs now is COMBINATIONAL (no memory).",
        "- 1 + 1 = 2 = binary 10, so adding two bits needs a SUM bulb and a CARRY bulb.",
        "- Sum = A xor B (1 when the bits differ). Carry = A AND B (1 when both are 1).",
        "- Half adder = XOR + AND. 'Half' because nothing is carried IN.",
    ],
    "c2_full": [
        "COMBINATIONAL 2: FULL ADDER",
        "- Adds THREE bits: A, B and the carry-in Cin. Count the 1s and write the count in binary: Cout Sum.",
        "- Sum = A xor B xor Cin = Sum m(1, 2, 4, 7). Cout = AB + A.Cin + B.Cin = Sum m(3, 5, 6, 7).",
        "- K-map: the Sum map is a checkerboard (no loops = XOR). The Cout map has three 2-cell loops.",
        "- Build it: two half adders and one OR gate (the OR joins the two carries).",
    ],
    "c3_sub": [
        "COMBINATIONAL 3: SUBTRACTORS",
        "- Half subtractor: Diff = A xor B. Borrow = A'.B (borrow when A is 0 and B is 1).",
        "- Full subtractor: Diff = A xor B xor Bin = Sum m(1, 2, 4, 7) (same as the adder's Sum).",
        "- Bout = A'B + A'Bin + B.Bin = Sum m(1, 2, 3, 7).",
        "- Build it: two half subtractors and one OR gate.",
    ],
    "c4_chain": [
        "COMBINATIONAL 4: ADDER CHAINS",
        "- 4-bit PARALLEL (ripple carry) adder: four full adders, each carry-out feeds the next carry-in.",
        "- Subtract with the same chain: A - B = A + (NOT B) + 1.",
        "- ADDER-SUBTRACTOR: an XOR on every B bit, and the mode bit M also goes to the first carry-in.",
        "- M = 0: add (XOR keeps B).  M = 1: subtract (XOR flips B, carry-in adds 1).",
    ],
    "c5_parity": [
        "COMBINATIONAL 5: PARITY",
        "- EVEN parity: add one bit P so that message + P has an EVEN number of 1s.",
        "- Generator: P = A xor B xor C xor D = Sum m(1, 2, 4, 7, 8, 11, 13, 14).",
        "- Checker: XOR the message AND P. Error = 1 means an odd count, so a bit was damaged.",
        "- Only one flipped bit is caught. Two flipped bits cancel out.",
    ],
    "c6_gray": [
        "COMBINATIONAL 6: GRAY CODE",
        "- Gray code changes only ONE bit between neighbouring numbers.",
        "- Binary to Gray: G3 = B3, G2 = B3 xor B2, G1 = B2 xor B1, G0 = B1 xor B0.",
        "- Gray to binary: B3 = G3, B2 = B3 xor G2, B1 = B2 xor G1, B0 = B1 xor G0.",
        "- Example: Gray 1011 = binary 1101 (13).",
    ],
    "c7_decoder": [
        "COMBINATIONAL 7: DECODER",
        "- A decoder turns an n-bit code into ONE active line out of 2^n.",
        "- 2-to-4: Y0 = A'B', Y1 = A'B, Y2 = AB', Y3 = AB. 3-to-8: Yk is the minterm mk (Y5 = AB'C).",
        "- A decoder is a minterm generator. Any Sum m(...) = OR of those outputs.",
        "- Example: full adder Cout = Y3 + Y5 + Y6 + Y7.",
    ],
    "c8_mux": [
        "COMBINATIONAL 8: MULTIPLEXER",
        "- A MUX copies ONE data input to the output. n select lines choose among 2^n inputs.",
        "- 2:1: Y = S'.I0 + S.I1. Data input Ik sits where minterm mk sits.",
        "- 3 variables on an 8:1 MUX: put 1 on Ik if mk is in the list. F = Sum m(1,2,4,7): 0 1 1 0 1 0 0 1.",
        "- Fewer selects: the pair trick. For each select code look at (last var = 0, last var = 1): "
        "(0,0) = 0, (1,1) = 1, (0,1) = var, (1,0) = var'.",
        "- F = Sum m(1,2,4,7) on a 4:1 MUX (A,B select): I0..I3 = C, C', C', C.",
        "- F = Sum m(1,3,4,11,12,13,14,15) on an 8:1 MUX (A,B,C select): I0..I7 = D, D, D', 0, 0, D, 1, 1.",
    ],
    "c9_boss": [
        "COMBINATIONAL CHEAT SHEET",
        "- Half adder: Sum = A xor B, Carry = AB.  Full adder: Sum m(1,2,4,7), Cout m(3,5,6,7).",
        "- Subtractor: Diff m(1,2,4,7), Bout m(1,2,3,7).  Adder-subtractor: XOR on B, M is the carry-in.",
        "- Parity P = XOR of the message. Gray: G = B xor (bit on its left).",
        "- Decoder: n inputs, 2^n lines, Yk = mk.  MUX: n selects, 2^n data inputs, Ik = mk.",
        "- Replay any circuit in NOTEBOOK > TEST THE LOGIC > COMBINATIONAL CIRCUITS.",
    ],
}
