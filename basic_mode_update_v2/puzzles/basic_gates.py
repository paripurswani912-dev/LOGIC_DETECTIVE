# puzzles/basic_gates.py
# BASIC LEVEL 1 - "Logic Gates From Zero"
#
# For players who have never seen digital electronics. Eight short stages:
#   1  ON and OFF        (0 = OFF, 1 = ON, click the bulbs)
#   2  Reading bits      (a row of bulbs is a row of 0s and 1s)
#   3  NOT               (the opposite)
#   4  AND               (both needed)
#   5  OR                (at least one)
#   6  XOR               (different)
#   7  Combine           (gate + NOT = NAND / NOR)
#   8  Symbols + boss    (symbol match, truth-table match, "fix the alarm")
#
# Every gate stage follows the same four beats:
#   SEE IT (sandbox) -> SAY IT (rule) -> PREDICT IT (truth table) -> PROVE IT (stories)
#
# Features
#   * Tiered hints: H = nudge, H again = stronger hint, H again = the answer.
#     Three wrong tries also reveal the answer.
#   * Math link: every finished stage shows the formula behind the gate.
#   * Notebook auto-fill: every finished stage writes its rule, truth table,
#     symbol and formula into NOTEBOOK > TEST THE LOGIC > MY BASIC NOTES.
#   * Progress is kept if the player leaves with ESC and comes back.
#
# Controls
#   Mouse click / keys         flip switches and bulbs, pick answers
#   0 / 1                      set a truth-table cell or choose OFF / ON
#   UP / DOWN                  move between truth-table rows
#   1-4                        choose an option in multiple-choice steps
#   ENTER                      check the answer / go to the next stage
#   H                          hint (press again for a stronger one)
#   ESC                        leave (handled by main.py), N notebook

import random

import pygame

import settings
from puzzles.base_puzzle import BasePuzzle


# ------------------------------------------------------------------
# COLOURS
# ------------------------------------------------------------------
BG = (7, 16, 27)
PANEL = (15, 31, 47)
PANEL_EDGE = (35, 100, 125)
CYAN = settings.CYAN
GREEN = settings.GREEN
RED = settings.RED
YELLOW = settings.YELLOW
GREY = settings.GREY
WHITE = settings.WHITE
WIRE_ON = (70, 235, 130)
WIRE_OFF = (78, 98, 118)
BULB_ON = (255, 218, 92)
BULB_OFF = (36, 46, 60)


# ------------------------------------------------------------------
# GATE KNOWLEDGE (single source of truth for rules, maths and notes)
# ------------------------------------------------------------------
def gate_out(gate, a, b=0):
    if gate == "NOT":
        return 1 - a
    if gate == "AND":
        return a & b
    if gate == "OR":
        return a | b
    if gate == "XOR":
        return a ^ b
    if gate == "NAND":
        return 1 - (a & b)
    if gate == "NOR":
        return 1 - (a | b)
    raise ValueError(gate)


def rows_for(gate):
    if gate == "NOT":
        return [(0,), (1,)]
    return [(0, 0), (0, 1), (1, 0), (1, 1)]


def outputs_for(gate):
    return [gate_out(gate, *r) for r in rows_for(gate)]


GINFO = {
    "NOT": {
        "tag": "the opposite",
        "analogy": "A night-light: it is ON when the room is dark (room light OFF).",
        "rule": "NOT flips its input. 0 becomes 1 and 1 becomes 0.",
        "math": "Y = 1 - A   (written A' or NOT A)",
        "memory": "NOT = opposite, like a mirror.",
        "symbol": "A triangle with a small circle. The circle means 'flip it'.",
        "short": "NOT flips the input.",
    },
    "AND": {
        "tag": "both needed",
        "analogy": "A safe that opens only if you have the KEY and you know the CODE.",
        "rule": "AND is ON only when ALL its inputs are ON.",
        "math": "Y = A x B   (multiplication! 1x1 = 1, anything x 0 = 0)",
        "memory": "AND = both. One OFF input kills the output.",
        "symbol": "A 'D' shape: flat back, round front.",
        "short": "AND needs both inputs ON.",
    },
    "OR": {
        "tag": "at least one",
        "analogy": "A room with two doors. You get in if the front OR the back door is open.",
        "rule": "OR is ON when AT LEAST ONE input is ON.",
        "math": "Y = A + B, but the answer never goes above 1   (1 + 1 = 1)",
        "memory": "OR = either (or both). It is OFF only when everything is OFF.",
        "symbol": "Curved back, pointed front (like a shield).",
        "short": "OR needs at least one input ON.",
    },
    "XOR": {
        "tag": "different",
        "analogy": "A staircase light with a switch downstairs and one upstairs.",
        "rule": "XOR is ON when the inputs are DIFFERENT.",
        "math": "Y = A + B and throw away the carry   (1 + 1 = 0)   i.e. (A + B) mod 2",
        "memory": "XOR = different. Same inputs give 0.",
        "symbol": "Like OR, but with an extra curved line at the back.",
        "short": "XOR is ON when the inputs differ.",
    },
    "NAND": {
        "tag": "AND then NOT",
        "analogy": "AND followed by NOT: the exact opposite of AND.",
        "rule": "NAND is OFF only when ALL inputs are ON.",
        "math": "Y = 1 - (A x B)",
        "memory": "NAND = NOT AND. Looks like AND with a circle.",
        "symbol": "AND shape with a small circle at the output.",
        "short": "NAND is the opposite of AND.",
    },
    "NOR": {
        "tag": "OR then NOT",
        "analogy": "OR followed by NOT: the exact opposite of OR.",
        "rule": "NOR is ON only when ALL inputs are OFF.",
        "math": "Y = 1 - (A + B)   with the sum capped at 1",
        "memory": "NOR = NOT OR. Looks like OR with a circle.",
        "symbol": "OR shape with a small circle at the output.",
        "short": "NOR is the opposite of OR.",
    },
}

# Extra wording used by the stage-8 symbol hints.
SYMBOL_HINTS = {
    "NOT": "It is a triangle. Only one input goes in.",
    "AND": "The back is FLAT and the front is round, like a letter D.",
    "OR": "The back is CURVED and the front comes to a point.",
    "XOR": "It looks like OR but has a SECOND curved line at the back.",
    "NAND": "It is the flat-backed AND shape, plus a small circle at the output.",
    "NOR": "It is the curved-back OR shape, plus a small circle at the output.",
}

# Hints for filling a truth table: nudge, stronger, answer.
TABLE_HINTS = {
    "NOT": [
        "NOT is a mirror. Y shows the opposite of A.",
        "When A is 0, Y is 1. When A is 1, Y is 0.",
        "Answer, top to bottom: 1, 0.",
    ],
    "AND": [
        "Think of the safe: key AND code. When does it open?",
        "AND is ON only when BOTH inputs are 1. So three rows are 0 and one row is 1.",
        "Answer, top to bottom: 0, 0, 0, 1.",
    ],
    "OR": [
        "Two doors: you get in if EITHER is open. Which rows have at least one 1?",
        "OR is OFF only when BOTH inputs are 0. The other three rows are 1.",
        "Answer, top to bottom: 0, 1, 1, 1.",
    ],
    "XOR": [
        "Staircase light: it is ON when the two switches are in DIFFERENT positions.",
        "Rows 00 and 11 have equal inputs, so 0. Rows 01 and 10 are different, so 1.",
        "Answer, top to bottom: 0, 1, 1, 0.",
    ],
    "NAND": [
        "NAND = AND followed by NOT. Work out AND for the row first, then flip it.",
        "AND gives 0, 0, 0, 1 down the rows. Flip every one of them.",
        "Answer, top to bottom: 1, 1, 1, 0.",
    ],
    "NOR": [
        "NOR = OR followed by NOT. Work out OR for the row first, then flip it.",
        "OR gives 0, 1, 1, 1 down the rows. Flip every one of them.",
        "Answer, top to bottom: 1, 0, 0, 0.",
    ],
}

PRAISE = ["Correct!", "Nice work!", "Exactly right!", "You got it!", "Well done!"]


# ------------------------------------------------------------------
# STAGE BUILDERS
# ------------------------------------------------------------------
def _scenario(gate, story, chips, answer, why):
    """A 'prove it' story question answered with OFF (0) or ON (1)."""
    inputs = " and ".join(f"{name} = {val}" for name, val in chips)
    return {
        "kind": "choice",
        "visual": "chips",
        "q": story,
        "chips": chips,
        "options": [("OFF  (0)", 0), ("ON  (1)", 1)],
        "correct": answer,
        "task": "Is the output ON or OFF?",
        "ok": why,
        "hints": [
            f"Think about the gate: {GINFO[gate]['short']}",
            f"Write the situation as numbers ({inputs}) and apply the rule: "
            f"{GINFO[gate]['rule']}",
            f"The answer is {answer}. {why}",
        ],
    }


def _explore_step(gate):
    def reveal(p):
        need = p.missing_combo()
        if need is None:
            return "You have tried every combination. Press ENTER."
        return "Still untried: " + need + ". Set the switches like that."

    return {
        "kind": "explore",
        "gate": gate,
        "task": "Flip the switches. Try EVERY combination and watch the bulb.",
        "hints": [
            "Click the switches (or press A and B) and watch the bulb react.",
            "The boxes under the circuit show which combinations you have tried. "
            "Fill them all.",
            reveal,
        ],
    }


def _table_step(gate, task=None):
    return {
        "kind": "table",
        "gate": gate,
        "task": task or "Fill in the Y column. What does the bulb do on each row?",
        "hints": TABLE_HINTS[gate],
    }


def _gate_stage(gate, number):
    info = GINFO[gate]
    scen = {
        "NOT": [
            _scenario("NOT", "A night-light turns ON when the room is dark. "
                      "The room light is ON (1). Is the night-light ON?",
                      [("Room light", 1)], 0,
                      "The room light is 1, NOT flips it to 0."),
            _scenario("NOT", "Now the room light is OFF (0). Is the night-light ON?",
                      [("Room light", 0)], 1,
                      "The room light is 0, NOT flips it to 1."),
        ],
        "AND": [
            _scenario("AND", "A safe opens only if you have the KEY and know the "
                      "CODE. You have the key but forgot the code. Does it open?",
                      [("Key", 1), ("Code", 0)], 0,
                      "AND needs both. The code is 0, so the output is 0."),
            _scenario("AND", "Now you have the key AND you remember the code. "
                      "Does it open?",
                      [("Key", 1), ("Code", 1)], 1,
                      "Both inputs are 1, so AND gives 1."),
        ],
        "OR": [
            _scenario("OR", "A room has a front door and a back door. The front "
                      "is locked but the back is open. Can you get in?",
                      [("Front open", 0), ("Back open", 1)], 1,
                      "OR needs at least one 1. The back door is 1."),
            _scenario("OR", "Now BOTH doors are locked. Can you get in?",
                      [("Front open", 0), ("Back open", 0)], 0,
                      "OR is only OFF when every input is 0."),
        ],
        "XOR": [
            _scenario("XOR", "Staircase light: the downstairs switch is UP (1) and "
                      "the upstairs switch is DOWN (0). Is the light ON?",
                      [("Downstairs", 1), ("Upstairs", 0)], 1,
                      "The switches are different (1 and 0), so XOR gives 1."),
            _scenario("XOR", "Now BOTH switches are UP (1). Is the light ON?",
                      [("Downstairs", 1), ("Upstairs", 1)], 0,
                      "The switches are the same, so XOR gives 0. "
                      "This is the row where XOR differs from OR!"),
        ],
    }[gate]

    steps = [_explore_step(gate), _table_step(gate)] + scen
    return {
        "id": f"s{number}_{gate.lower()}",
        "title": gate,
        "sub": info["tag"],
        "gates": [gate],
        "brief": [info["analogy"], info["rule"]],
        "steps": steps,
    }


def _stage_onoff():
    return {
        "id": "s1_onoff",
        "title": "ON and OFF",
        "sub": "0 = OFF, 1 = ON",
        "gates": [],
        "brief": [
            "Computers only understand two things: ON and OFF.",
            "We write ON as 1 and OFF as 0. Click a bulb to flip it.",
        ],
        "steps": [
            {
                "kind": "bulbs",
                "start": [1, 1, 0, 1],
                "target": [0, 0, 0, 0],
                "task": "Turn every bulb OFF (0).",
                "hints": [
                    "Click a bulb to flip it. A glowing bulb is ON (1).",
                    "Click only the bulbs that are glowing. Dark bulbs are already 0.",
                    lambda p: "Click bulb number(s): " + p.wrong_bulbs_text() + ".",
                ],
            },
            {
                "kind": "bulbs",
                "start": [0, 1, 0, 0],
                "target": [1, 1, 1, 1],
                "task": "Turn every bulb ON (1).",
                "hints": [
                    "Now we want 1 everywhere. Click the bulbs that are dark.",
                    "A dark bulb is 0. Clicking it makes it 1.",
                    lambda p: "Click bulb number(s): " + p.wrong_bulbs_text() + ".",
                ],
            },
            {
                "kind": "bulbs",
                "start": [0, 0, 0, 0],
                "target": [1, 0, 1, 1],
                "task": "Make your bulbs match the TARGET row.",
                "hints": [
                    "Compare the target row and your row, bulb by bulb, left to right.",
                    "Wherever the target glows, yours must glow. Wherever it is dark, yours is dark.",
                    lambda p: "Click bulb number(s): " + p.wrong_bulbs_text() + ".",
                ],
            },
        ],
    }


def _stage_bits():
    def bits_hint(pattern):
        text = " ".join(str(b) for b in pattern)
        return [
            "Read the bulbs from left to right. Glowing = 1, dark = 0.",
            "Type one digit per bulb, in the same order as the bulbs.",
            f"The answer is {text}.",
        ]

    return {
        "id": "s2_bits",
        "title": "Reading bits",
        "sub": "a row of bulbs is a number",
        "gates": [],
        "brief": [
            "Each 0 or 1 is called a BIT. A row of bits can be read like a word.",
            "Read left to right. Glowing bulb = 1, dark bulb = 0.",
        ],
        "steps": [
            {
                "kind": "read_bits",
                "pattern": [1, 0, 0, 1],
                "task": "Type the bits shown by the bulbs.",
                "hints": bits_hint([1, 0, 0, 1]),
            },
            {
                "kind": "read_bits",
                "pattern": [0, 1, 1, 0],
                "task": "Type the bits shown by the bulbs.",
                "hints": bits_hint([0, 1, 1, 0]),
            },
            {
                "kind": "bulbs",
                "start": [0, 0, 0, 0],
                "target": [1, 1, 0, 1],
                "target_as_bits": True,
                "task": "Now the other way round: light the bulbs to show 1 1 0 1.",
                "hints": [
                    "The code says 1 1 0 1. Bulb 1 = first digit, bulb 2 = second, and so on.",
                    "Light bulbs 1, 2 and 4. Leave bulb 3 dark.",
                    lambda p: "Click bulb number(s): " + p.wrong_bulbs_text() + ".",
                ],
            },
        ],
    }


def _stage_combine():
    def combo_reveal(p):
        return ("Pick AND, press T to add NOT, then do the same for OR. "
                "Watch the name change.")

    nand_pred = _scenario(
        "NAND", "A NAND gate gets A = 1 and B = 1. What is its output?",
        [("A", 1), ("B", 1)], 0,
        "AND(1,1) = 1, then NOT flips it to 0.")
    nand_pred["hints"][0] = "NAND = AND followed by NOT. What does AND give for 1 and 1?"
    nor_pred = _scenario(
        "NOR", "A NOR gate gets A = 0 and B = 0. What is its output?",
        [("A", 0), ("B", 0)], 1,
        "OR(0,0) = 0, then NOT flips it to 1.")
    nor_pred["hints"][0] = "NOR = OR followed by NOT. What does OR give for 0 and 0?"

    return {
        "id": "s7_combine",
        "title": "Combine gates",
        "sub": "gate + NOT = NAND / NOR",
        "gates": ["NAND", "NOR"],
        "brief": [
            "Gates can be chained: the output of one is the input of the next.",
            "A NOT after AND gives NAND. A NOT after OR gives NOR. "
            "The small circle on a symbol means 'NOT is built in'.",
        ],
        "steps": [
            {
                "kind": "combine",
                "task": "Pick a gate, add NOT with T, and flip the switches. "
                        "Try it on AND and on OR.",
                "hints": [
                    "Click AND, then press T (or click ADD NOT). Look at the new name.",
                    "NOT flips the answer of the gate before it. Compare the bulb with and without NOT.",
                    combo_reveal,
                ],
            },
            _table_step("NAND", "Fill in the NAND table (AND, then NOT)."),
            _table_step("NOR", "Fill in the NOR table (OR, then NOT)."),
            nand_pred,
            nor_pred,
        ],
    }


def _stage_review():
    names = ["NOT", "AND", "OR", "XOR", "NAND", "NOR"]
    steps = []

    for gate in names:
        steps.append({
            "kind": "choice",
            "visual": "symbol",
            "gate": gate,
            "q": "Which gate has this symbol?",
            "options": [(n, n) for n in ("NOT", "AND", "OR", "XOR")]
            if gate in ("NOT", "AND", "OR", "XOR")
            else [(n, n) for n in ("AND", "OR", "NAND", "NOR")],
            "correct": gate,
            "task": "Pick the name that matches the symbol.",
            "ok": f"{gate}: {GINFO[gate]['symbol']}",
            "hints": [
                SYMBOL_HINTS[gate],
                "Flat back = AND family. Curved back = OR family. "
                "A small circle on the output means NOT is attached.",
                f"It is {gate}.",
            ],
        })

    for gate, others in (("OR", ("AND", "OR", "XOR", "NOR")),
                         ("NAND", ("AND", "OR", "NAND", "NOR")),
                         ("XOR", ("AND", "OR", "XOR", "NAND"))):
        steps.append({
            "kind": "choice",
            "visual": "column",
            "gate": gate,
            "q": "A mystery gate gives these outputs. Which gate is it?",
            "options": [(n, n) for n in others],
            "correct": gate,
            "task": "Read the Y column from top to bottom and pick the gate.",
            "ok": f"{gate} outputs " + " ".join(map(str, outputs_for(gate))) + ".",
            "hints": [
                "Read the Y column top to bottom. Count how many 1s there are.",
                "AND: 0 0 0 1.  OR: 0 1 1 1.  XOR: 0 1 1 0.  NAND: 1 1 1 0.  NOR: 1 0 0 0.",
                f"It is {gate}: " + " ".join(map(str, outputs_for(gate))) + ".",
            ],
        })

    boss_cases = [(1, 0, 0), (0, 0, 0), (1, 1, 1), (0, 1, 0)]
    for a, b, c in boss_cases:
        o = a | b
        n = 1 - c
        out = o & n
        steps.append({
            "kind": "choice",
            "visual": "boss",
            "inputs": (a, b, c),
            "q": "FIX THE ALARM: it rings when (door OR window is open) AND "
                 "the guard badge is NOT scanned. Does it ring?",
            "options": [("SILENT  (0)", 0), ("RINGS  (1)", 1)],
            "correct": out,
            "task": f"Door = {a}, Window = {b}, Badge = {c}. Work left to right.",
            "ok": f"OR gives {o}, NOT gives {n}, AND gives {out}.",
            "hints": [
                "Work left to right. First find what the OR gate gives, "
                "then what the NOT gate gives.",
                "Then feed those two answers into the AND gate.",
                f"OR = {o}, NOT = {n}, so AND = {out}. The alarm output is {out}.",
            ],
        })

    return {
        "id": "s8_review",
        "title": "Symbols and the alarm",
        "sub": "revision + boss",
        "gates": [],
        "brief": [
            "Time to put it all together. First recognise the symbols and truth tables.",
            "Then use NOT, OR and AND together to fix the alarm circuit.",
        ],
        "steps": steps,
    }


def build_stages():
    return [
        _stage_onoff(),
        _stage_bits(),
        _gate_stage("NOT", 3),
        _gate_stage("AND", 4),
        _gate_stage("OR", 5),
        _gate_stage("XOR", 6),
        _stage_combine(),
        _stage_review(),
    ]


# ------------------------------------------------------------------
# DRAWING HELPERS
# ------------------------------------------------------------------
def _bezier(p0, p1, p2, steps=16):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0],
                    a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def gate_pins(gate, rect):
    """Pin positions of a gate drawn into rect: (in_top, in_bottom, out)."""
    x, y, w, h = rect
    mid = y + h // 2
    if gate == "NOT":
        return (x, mid), (x, mid), (x + w, mid)
    return (x, y + h // 3), (x, y + (2 * h) // 3), (x + w, mid)


def draw_gate(screen, gate, rect, color, stroke=3):
    """Draw a standard logic gate symbol inside rect."""
    x, y, w, h = rect
    mid = y + h // 2
    top = y + int(h * 0.12)
    bot = y + int(h * 0.88)
    in_top = y + h // 3
    in_bot = y + (2 * h) // 3
    bubble = max(8, stroke * 2 + 4)
    has_bubble = gate in ("NAND", "NOR", "XNOR", "NOT")
    out_len = max(8, int(w * 0.14))
    gap = max(6, int(w * 0.06)) if gate in ("XOR", "XNOR") else 0
    left = x + int(w * 0.14) + gap
    right = x + w - out_len - (bubble if has_bubble else 0)
    bw = max(12, right - left)

    def line(p, q):
        pygame.draw.line(screen, color, (int(p[0]), int(p[1])),
                         (int(q[0]), int(q[1])), stroke)

    def poly(points, close=False):
        pts = [(int(px), int(py)) for px, py in points]
        pygame.draw.lines(screen, color, close, pts, stroke)

    if gate == "NOT":
        poly([(left, top), (right, mid), (left, bot)], close=True)
        line((x, mid), (left, mid))
    elif gate in ("AND", "NAND"):
        xc = left + bw * 0.5
        upper = _bezier((xc, top), (right, top), (right, mid))
        lower = _bezier((right, mid), (right, bot), (xc, bot))
        poly([(left, top)] + upper + lower[1:] + [(left, bot)], close=True)
        line((x, in_top), (left, in_top))
        line((x, in_bot), (left, in_bot))
    else:  # OR, NOR, XOR, XNOR
        depth = bw * 0.36

        def back(base):
            return _bezier((base, top), (base + depth, mid), (base, bot))

        def back_x(base, yy):
            t = (yy - top) / (bot - top)
            return base + 2 * t * (1 - t) * depth

        poly(_bezier((left, top), (left + bw * 0.55, top), (right, mid)))
        poly(_bezier((left, bot), (left + bw * 0.55, bot), (right, mid)))
        poly(back(left))
        base = left
        if gate in ("XOR", "XNOR"):
            base = left - gap
            poly(back(base))
        line((x, in_top), (back_x(base, in_top), in_top))
        line((x, in_bot), (back_x(base, in_bot), in_bot))

    if has_bubble:
        pygame.draw.circle(screen, color,
                           (right + bubble // 2, mid), bubble // 2, stroke)
        line((right + bubble, mid), (x + w, mid))
    else:
        line((right, mid), (x + w, mid))


def draw_wire(screen, p0, p1, on, width=4, elbow=True):
    color = WIRE_ON if on else WIRE_OFF
    if elbow and p0[1] != p1[1]:
        mx = (p0[0] + p1[0]) // 2
        pts = [p0, (mx, p0[1]), (mx, p1[1]), p1]
    else:
        pts = [p0, p1]
    pygame.draw.lines(screen, color, False, pts, width)


def draw_bulb(screen, cx, cy, r, on, label=None, font=None):
    if on:
        glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        for k, alpha in ((2.3, 22), (1.8, 40), (1.4, 70)):
            pygame.draw.circle(glow, (255, 214, 80, alpha),
                               (r * 5 // 2, r * 5 // 2), int(r * k))
        screen.blit(glow, (cx - r * 5 // 2, cy - r * 5 // 2))
    pygame.draw.circle(screen, BULB_ON if on else BULB_OFF, (cx, cy), r)
    pygame.draw.circle(screen, WHITE if on else GREY, (cx, cy), r, 3)
    base = pygame.Rect(0, 0, int(r * 0.9), int(r * 0.45))
    base.midtop = (cx, cy + r - 2)
    pygame.draw.rect(screen, GREY, base, border_radius=3)
    if label is not None and font is not None:
        img = font.render(str(label), True, WHITE)
        screen.blit(img, img.get_rect(center=(cx, cy + r + 30)))


def wrap_text(font, text, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------
# THE PUZZLE
# ------------------------------------------------------------------
WORK = pygame.Rect(30, 85, 600, 470)       # workspace
SIDE = pygame.Rect(650, 85, 320, 470)      # briefing + hints
FULL = pygame.Rect(30, 85, 940, 470)       # stage-complete card


class BasicGatesPuzzle(BasePuzzle):
    """Eight-stage beginner course on ON/OFF, bits and logic gates."""

    COURSE_TITLE = "BASIC LEVEL 1  -  LOGIC GATES FROM ZERO"
    LEGEND_EXTRA = {
        "bulbs": "click bulbs or press 1-4",
        "read_bits": "type 0 or 1, BACKSPACE deletes",
        "explore": "click switches or press A / B",
        "combine": "A / B switches, 1-3 gate, T = add NOT",
        "table": "click cell or UP/DOWN, then 0 or 1",
        "choice": "click an answer or press 0/1 (or 1-4)",
    }

    def _make_stages(self):
        return build_stages()

    def __init__(self, notebook=None):
        super().__init__()
        self.notebook = notebook
        self.stages = self._make_stages()
        self.stage_i = 0
        self.step_i = 0
        self.phase = "play"            # "play" or "done"
        self.st = {}
        self.buttons = []
        self.toast = ""
        self.toast_ok = True
        self.toast_time = 0.0
        self.clock = 0.0
        self.saved_stages = set()
        self.last_bulbs = [0, 0, 0, 0]

        self.f_title = pygame.font.Font(None, 40)
        self.f_big = pygame.font.Font(None, 54)
        self.f_body = pygame.font.Font(None, 28)
        self.f_small = pygame.font.Font(None, 23)
        self.f_tiny = pygame.font.Font(None, 20)

        self._enter_step()

    # ---------------- state helpers ----------------
    @property
    def stage(self):
        return self.stages[self.stage_i]

    @property
    def step(self):
        return self.stage["steps"][self.step_i]

    def _enter_step(self):
        step = self.step
        kind = step["kind"]
        self.st = {"wrong": 0, "tier": 0}
        if kind == "bulbs":
            self.st["bulbs"] = list(step["start"])
        elif kind == "read_bits":
            self.st["typed"] = ""
        elif kind == "explore":
            self.st.update(a=0, b=0, seen={(0, 0)})
        elif kind == "combine":
            self.st.update(a=0, b=0, gate="AND", use_not=False, seen=set())
        elif kind == "table":
            n = len(rows_for(step["gate"]))
            self.st.update(cells=[None] * n, sel=0, bad=set())
        elif kind == "choice":
            self.st["sel"] = None
        self._say("", True)

    def _say(self, text, ok=True, seconds=4.0):
        self.toast = text
        self.toast_ok = ok
        self.toast_time = seconds

    def missing_combo(self):
        if self.step["kind"] != "explore":
            return None
        gate = self.step["gate"]
        seen = self.st.get("seen", set())
        if gate == "NOT":
            for a in (0, 1):
                if not any(x[0] == a for x in seen):
                    return f"A = {a}"
            return None
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
            if (a, b) not in seen:
                return f"A = {a}, B = {b}"
        return None

    def wrong_bulbs_text(self):
        bulbs = self.st.get("bulbs", [])
        target = self.step.get("target", [])
        idx = [str(i + 1) for i, (x, y) in enumerate(zip(bulbs, target)) if x != y]
        return ", ".join(idx) if idx else "none, they all match. Press ENTER"

    def _hint_text(self):
        tier = self.st.get("tier", 0)
        if tier == 0:
            return None
        hints = self.step.get("hints", [])
        h = hints[min(tier, len(hints)) - 1]
        return h(self) if callable(h) else h

    # ---------------- events ----------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self._on_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action in self.buttons:
                if rect.collidepoint(event.pos):
                    self._on_action(action)
                    break

    def _on_key(self, event):
        key = event.key
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.phase == "done":
                self._next_stage()
            else:
                self._check()
            return
        if self.phase == "done":
            return
        if key == pygame.K_h:
            self._hint()
            return

        kind = self.step["kind"]
        digit = self._digit(key)

        if kind == "bulbs":
            if digit is not None and 1 <= digit <= 4:
                self._on_action(("bulb", digit - 1))
        elif kind == "read_bits":
            if digit in (0, 1) and len(self.st["typed"]) < len(self.step["pattern"]):
                self.st["typed"] += str(digit)
            elif key == pygame.K_BACKSPACE:
                self.st["typed"] = self.st["typed"][:-1]
        elif kind == "explore":
            if key == pygame.K_a:
                self._on_action(("switch", "a"))
            elif key == pygame.K_b and self.step["gate"] != "NOT":
                self._on_action(("switch", "b"))
        elif kind == "combine":
            if key == pygame.K_a:
                self._on_action(("switch", "a"))
            elif key == pygame.K_b:
                self._on_action(("switch", "b"))
            elif key == pygame.K_t:
                self._on_action(("toggle_not",))
            elif key == pygame.K_1:
                self._on_action(("pick_gate", "AND"))
            elif key == pygame.K_2:
                self._on_action(("pick_gate", "OR"))
            elif key == pygame.K_3:
                self._on_action(("pick_gate", "XOR"))
        elif kind == "table":
            n = len(self.st["cells"])
            if key == pygame.K_UP:
                self.st["sel"] = (self.st["sel"] - 1) % n
            elif key == pygame.K_DOWN:
                self.st["sel"] = (self.st["sel"] + 1) % n
            elif digit in (0, 1):
                self.st["cells"][self.st["sel"]] = digit
                self.st["bad"].discard(self.st["sel"])
                if self.st["sel"] < n - 1:
                    self.st["sel"] += 1
        elif kind == "choice":
            opts = self.step["options"]
            if all(isinstance(v, int) for _l, v in opts):
                if digit in (0, 1):
                    self.st["sel"] = digit
            elif digit is not None and 1 <= digit <= len(opts):
                self.st["sel"] = digit - 1

    @staticmethod
    def _digit(key):
        if pygame.K_0 <= key <= pygame.K_9:
            return key - pygame.K_0
        if pygame.K_KP0 <= key <= pygame.K_KP9:
            return key - pygame.K_KP0
        return None

    def _on_action(self, action):
        name = action[0]
        st = self.st
        if name == "bulb":
            st["bulbs"][action[1]] ^= 1
        elif name == "switch":
            st[action[1]] ^= 1
            self._record_combo()
        elif name == "toggle_not":
            st["use_not"] = not st["use_not"]
            self._record_combo()
        elif name == "pick_gate":
            st["gate"] = action[1]
            self._record_combo()
        elif name == "type":
            if len(st["typed"]) < len(self.step["pattern"]):
                st["typed"] += action[1]
        elif name == "cell":
            i = action[1]
            st["sel"] = i
            cur = st["cells"][i]
            st["cells"][i] = 0 if cur is None else 1 - cur
            st["bad"].discard(i)
        elif name == "opt":
            opts = self.step["options"]
            st["sel"] = opts[action[1]][1] if all(
                isinstance(v, int) for _l, v in opts) else action[1]
        elif name == "check":
            self._check()
        elif name == "hint":
            self._hint()
        elif name == "next":
            self._next_stage()

    def _record_combo(self):
        st = self.st
        kind = self.step["kind"]
        if kind == "explore":
            gate = self.step["gate"]
            st["seen"].add((st["a"], 0 if gate == "NOT" else st["b"]))
        elif kind == "combine" and st["use_not"]:
            st["seen"].add(st["gate"])

    def _hint(self):
        if self.st.get("tier", 0) < 3:
            self.st["tier"] += 1
        self._say("", True)

    # ---------------- checking ----------------
    def _wrong(self, text):
        self.st["wrong"] += 1
        if self.st["wrong"] >= 3 and self.st["tier"] < 3:
            self.st["tier"] = 3
            text += "  The answer is now shown in the hint box."
        self._say(text, False, 6.0)

    def _right(self, extra=""):
        msg = random.choice(PRAISE) + (" " + extra if extra else "")
        self._advance(msg)

    def _check(self):
        step, st = self.step, self.st
        kind = step["kind"]

        if kind == "bulbs":
            if st["bulbs"] == step["target"]:
                self.last_bulbs = list(st["bulbs"])
                self._right()
            else:
                n = sum(1 for x, y in zip(st["bulbs"], step["target"]) if x != y)
                self._wrong(f"Not yet: {n} bulb(s) still differ from the target.")

        elif kind == "read_bits":
            want = "".join(str(b) for b in step["pattern"])
            if len(st["typed"]) < len(want):
                self._say("Type one digit (0 or 1) for every bulb first.", False)
            elif st["typed"] == want:
                self._right()
            else:
                self._wrong("Not quite. Remember: glowing bulb = 1, dark bulb = 0.")

        elif kind == "explore":
            need = 2 if step["gate"] == "NOT" else 4
            if step["gate"] == "NOT":
                got = len({s[0] for s in st["seen"]})
            else:
                got = len(st["seen"])
            if got >= need:
                self._right("You have seen every combination.")
            else:
                self._say(f"Try every combination first ({got}/{need} done).", False)

        elif kind == "combine":
            if {"AND", "OR"} <= st["seen"]:
                self._right("AND + NOT = NAND, and OR + NOT = NOR.")
            else:
                missing = [g for g in ("AND", "OR") if g not in st["seen"]]
                self._say("Add NOT to " + " and ".join(missing) + " first.", False)

        elif kind == "table":
            if None in st["cells"]:
                self._say("Fill every Y cell first (select it, then press 0 or 1).",
                          False)
                return
            want = outputs_for(step["gate"])
            bad = {i for i, (x, y) in enumerate(zip(st["cells"], want)) if x != y}
            st["bad"] = bad
            if not bad:
                self._right()
            else:
                first = min(bad)
                row = rows_for(step["gate"])[first]
                names = "A = %d" % row[0] + (", B = %d" % row[1] if len(row) > 1 else "")
                self._wrong(f"{len(bad)} row(s) wrong. Check the row with {names}.")

        elif kind == "choice":
            if st["sel"] is None:
                self._say("Pick an answer first.", False)
                return
            opts = step["options"]
            chosen = opts[st["sel"]][1] if not all(
                isinstance(v, int) for _l, v in opts) else st["sel"]
            if chosen == step["correct"]:
                self._right(step.get("ok", ""))
            else:
                self._wrong("Not quite. Press H if you want a hint.")

    def _advance(self, message):
        self.step_i += 1
        if self.step_i >= len(self.stage["steps"]):
            self.step_i = len(self.stage["steps"]) - 1
            self._finish_stage()
            return
        self._enter_step()
        self._say(message, True)

    # ---------------- stage completion + notebook autofill ----------------
    def _finish_stage(self):
        self.phase = "done"
        self._say("", True)
        sid = self.stage["id"]
        if sid not in self.saved_stages:
            self.saved_stages.add(sid)
            if self.notebook is not None and hasattr(self.notebook, "add_basic_note"):
                self.notebook.add_basic_note(sid, self.notebook_lines(self.stage))

    def _next_stage(self):
        if self.phase != "done":
            return
        if self.stage_i >= len(self.stages) - 1:
            self.solved = True
            return
        self.stage_i += 1
        self.step_i = 0
        self.phase = "play"
        self._enter_step()

    def notebook_lines(self, stage):
        """Lines written into NOTEBOOK > TEST THE LOGIC > MY BASIC NOTES."""
        sid = stage["id"]
        n = int(sid[1])
        lines = []

        def table_line(gate):
            if gate == "NOT":
                return "- Table (A = Y): 0=1, 1=0"
            pairs = ", ".join(f"{a}{b}={gate_out(gate, a, b)}" for a, b in rows_for(gate))
            return f"- Table (AB = Y): {pairs}"

        if sid == "s1_onoff":
            lines += [
                f"STAGE {n}: ON AND OFF",
                "- 0 = OFF = false.  1 = ON = true.",
                "- A digital circuit only ever sees these two values.",
                "- Each 0 or 1 is called a BIT.",
            ]
        elif sid == "s2_bits":
            lines += [
                f"STAGE {n}: BITS",
                "- A row of bits is a binary number. Read it left to right.",
                "- Place values from the right: 1, 2, 4, 8.",
                "- Example: 1101 = 8 + 4 + 0 + 1 = 13.",
            ]
        elif sid == "s7_combine":
            lines += [
                f"STAGE {n}: NAND AND NOR",
                "- A circle on the output of a symbol means NOT is built in.",
                "- NAND = AND then NOT. " + table_line("NAND")[2:],
                "- NOR = OR then NOT. " + table_line("NOR")[2:],
                "- Math: NAND: Y = 1 - (A x B).  NOR: Y = 1 - (A + B), sum capped at 1.",
                "- NAND is OFF only when all inputs are ON. NOR is ON only when all inputs are OFF.",
            ]
        elif sid == "s8_review":
            lines += [
                f"STAGE {n}: CHEAT SHEET",
                "- NOT: flips.   AND: both ON.   OR: at least one ON.   XOR: different.",
                "- NAND: opposite of AND.   NOR: opposite of OR.",
                "- Y column (AB = 00, 01, 10, 11): AND 0001, OR 0111, XOR 0110, NAND 1110, NOR 1000.",
                "- Symbols: flat back = AND family, curved back = OR family, circle = NOT built in.",
                "- Alarm circuit: Y = (Door OR Window) AND (NOT Badge).",
            ]
        else:
            gate = stage["gates"][0]
            info = GINFO[gate]
            lines += [
                f"STAGE {n}: {gate} GATE",
                "- Rule: " + info["rule"],
                table_line(gate),
                "- Symbol: " + info["symbol"],
                "- Math: " + info["math"],
                "- Remember: " + info["memory"],
            ]
        return lines

    # ---------------- update / draw ----------------
    def update(self, dt):
        self.clock += dt
        if self.toast_time > 0:
            self.toast_time -= dt
            if self.toast_time <= 0:
                self.toast = ""

    def draw(self, screen):
        self.buttons = []
        screen.fill(BG)
        self._draw_header(screen)

        if self.phase == "done":
            self._draw_done(screen)
        else:
            pygame.draw.rect(screen, PANEL, WORK, border_radius=10)
            pygame.draw.rect(screen, PANEL_EDGE, WORK, 2, border_radius=10)
            self._draw_side(screen)
            kind = self.step["kind"]
            getattr(self, "_draw_" + kind)(screen)

        self._draw_footer(screen)

    # --- header / footer / side ---
    def _draw_header(self, screen):
        pygame.draw.rect(screen, PANEL, (0, 0, settings.SCREEN_WIDTH, 72))
        pygame.draw.line(screen, PANEL_EDGE, (0, 72), (settings.SCREEN_WIDTH, 72), 2)
        small = self.f_tiny.render(self.COURSE_TITLE, True, CYAN)
        screen.blit(small, (30, 10))
        text = (f"Stage {self.stage_i + 1}/{len(self.stages)}: "
                f"{self.stage['title']}  -  {self.stage['sub']}")
        size = 40
        while size > 22:
            font = pygame.font.Font(None, size)
            if font.size(text)[0] <= 640:
                break
            size -= 2
        screen.blit(font.render(text, True, WHITE), (30, 34))

        for i in range(len(self.stages)):
            cx = 700 + i * 34
            if i < self.stage_i or (i == self.stage_i and self.phase == "done"):
                pygame.draw.circle(screen, GREEN, (cx, 22), 11)
            elif i == self.stage_i:
                pygame.draw.circle(screen, CYAN, (cx, 22), 11, 3)
            else:
                pygame.draw.circle(screen, GREY, (cx, 22), 11, 2)
            num = self.f_tiny.render(str(i + 1), True, BG if i < self.stage_i else WHITE)
            screen.blit(num, num.get_rect(center=(cx, 22)))
        if self.phase == "play":
            total = len(self.stage["steps"])
            txt = self.f_tiny.render(f"Step {self.step_i + 1} of {total}", True, GREY)
            screen.blit(txt, (700, 46))

    def _draw_footer(self, screen):
        y = 572
        if self.toast:
            col = GREEN if self.toast_ok else YELLOW
            for i, line in enumerate(wrap_text(self.f_body, self.toast, 930)[:2]):
                screen.blit(self.f_body.render(line, True, col), (30, y + i * 24))
        legend = self._legend()
        screen.blit(self.f_tiny.render(legend, True, GREY), (30, 624))

        if self.phase == "play":
            rect = pygame.Rect(790, 590, 90, 32)
            self._button(screen, rect, "CHECK", ("check",), CYAN)
            rect = pygame.Rect(890, 590, 80, 32)
            self._button(screen, rect, "HINT", ("hint",), YELLOW)

    def _legend(self):
        if self.phase == "done":
            return "[ENTER] next stage    [N] notebook    [ESC] leave (progress is saved)"
        kind = self.step["kind"]
        extra = self.LEGEND_EXTRA.get(kind, "")
        return f"[ENTER] check    [H] hint (press again for more)    {extra}    [N] notebook    [ESC] leave"

    def _button(self, screen, rect, label, action, color):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (24, 52, 74) if hover else PANEL, rect, border_radius=6)
        pygame.draw.rect(screen, color, rect, 2, border_radius=6)
        img = self.f_small.render(label, True, color)
        screen.blit(img, img.get_rect(center=rect.center))
        self.buttons.append((rect, action))

    def _draw_side(self, screen):
        pygame.draw.rect(screen, PANEL, SIDE, border_radius=10)
        pygame.draw.rect(screen, PANEL_EDGE, SIDE, 2, border_radius=10)
        screen.set_clip(SIDE.inflate(-4, -4))
        y = SIDE.y + 12
        screen.blit(self.f_small.render("BRIEFING", True, CYAN), (SIDE.x + 14, y))
        y += 28
        for para in self.stage["brief"]:
            for line in wrap_text(self.f_tiny, para, SIDE.width - 28):
                screen.blit(self.f_tiny.render(line, True, WHITE), (SIDE.x + 14, y))
                y += 20
            y += 6
        y += 4
        screen.blit(self.f_small.render("YOUR TASK", True, GREEN), (SIDE.x + 14, y))
        y += 26
        for line in wrap_text(self.f_tiny, self.step["task"], SIDE.width - 28):
            screen.blit(self.f_tiny.render(line, True, WHITE), (SIDE.x + 14, y))
            y += 20

        box = pygame.Rect(SIDE.x + 10, SIDE.bottom - 168, SIDE.width - 20, 158)
        pygame.draw.rect(screen, (22, 40, 30) if self.st["tier"] else (18, 30, 44),
                         box, border_radius=8)
        pygame.draw.rect(screen, YELLOW, box, 2, border_radius=8)
        tier = self.st["tier"]
        labels = {0: "HINT", 1: "HINT 1/3  (a nudge)", 2: "HINT 2/3  (stronger)",
                  3: "HINT 3/3  (the answer)"}
        screen.blit(self.f_small.render(labels[tier], True, YELLOW), (box.x + 10, box.y + 8))
        text = self._hint_text() or "Stuck? Press H. Press it again for a stronger hint."
        color = WHITE if tier else GREY
        yy = box.y + 34
        for line in wrap_text(self.f_tiny, text, box.width - 20)[:6]:
            screen.blit(self.f_tiny.render(line, True, color), (box.x + 10, yy))
            yy += 19
        screen.set_clip(None)

    # --- shared small widgets ---
    def _chip(self, screen, cx, cy, text, on=None, w=84, h=40):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)
        fill = (24, 90, 55) if on else (30, 42, 56)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, GREEN if on else GREY, rect, 2, border_radius=8)
        img = self.f_small.render(text, True, WHITE)
        screen.blit(img, img.get_rect(center=rect.center))
        return rect

    def _switch(self, screen, cx, cy, label, value, action=None):
        rect = pygame.Rect(0, 0, 96, 46)
        rect.center = (cx, cy)
        pygame.draw.rect(screen, (22, 80, 52) if value else (36, 44, 58),
                         rect, border_radius=23)
        pygame.draw.rect(screen, GREEN if value else GREY, rect, 3, border_radius=23)
        knob_x = rect.right - 23 if value else rect.left + 23
        pygame.draw.circle(screen, WHITE, (knob_x, cy), 17)
        txt = self.f_small.render(f"{label} = {value}", True, WHITE)
        screen.blit(txt, txt.get_rect(center=(cx, cy - 36)))
        if action:
            self.buttons.append((rect.inflate(10, 30), action))
        return rect

    # --- stage 1/2: bulbs ---
    def _draw_bulbs(self, screen):
        step, st = self.step, self.st
        n = len(step["target"])
        xs = [WORK.centerx + (i - (n - 1) / 2) * 120 for i in range(n)]

        screen.blit(self.f_small.render("TARGET", True, CYAN), (WORK.x + 24, WORK.y + 22))
        if step.get("target_as_bits"):
            code = "   ".join(str(b) for b in step["target"])
            img = self.f_big.render(code, True, YELLOW)
            screen.blit(img, img.get_rect(center=(WORK.centerx, WORK.y + 90)))
        else:
            for x, v in zip(xs, step["target"]):
                draw_bulb(screen, int(x), WORK.y + 85, 22, v, v, self.f_small)

        pygame.draw.line(screen, PANEL_EDGE, (WORK.x + 20, WORK.y + 170),
                         (WORK.right - 20, WORK.y + 170), 2)
        screen.blit(self.f_small.render("YOUR BULBS  (click to flip)", True, GREEN),
                    (WORK.x + 24, WORK.y + 190))
        for i, (x, v) in enumerate(zip(xs, st["bulbs"])):
            cx, cy = int(x), WORK.y + 295
            draw_bulb(screen, cx, cy, 40, v, f"{i + 1}:  {v}", self.f_body)
            self.buttons.append((pygame.Rect(cx - 55, cy - 55, 110, 130), ("bulb", i)))

        match = sum(1 for x, y in zip(st["bulbs"], step["target"]) if x == y)
        txt = self.f_body.render(f"Bulbs matching: {match} / {n}", True,
                                 GREEN if match == n else WHITE)
        screen.blit(txt, txt.get_rect(center=(WORK.centerx, WORK.bottom - 40)))
        key = self.f_tiny.render("Glowing bulb = 1 (ON)      Dark bulb = 0 (OFF)", True, GREY)
        screen.blit(key, key.get_rect(center=(WORK.centerx, WORK.bottom - 16)))

    def _draw_read_bits(self, screen):
        step, st = self.step, self.st
        n = len(step["pattern"])
        xs = [WORK.centerx + (i - (n - 1) / 2) * 120 for i in range(n)]
        screen.blit(self.f_small.render("LOOK AT THE BULBS", True, CYAN),
                    (WORK.x + 24, WORK.y + 22))
        for x, v in zip(xs, step["pattern"]):
            draw_bulb(screen, int(x), WORK.y + 130, 40, v)

        screen.blit(self.f_small.render("TYPE THE BITS (left to right)", True, GREEN),
                    (WORK.x + 24, WORK.y + 250))
        for i, x in enumerate(xs):
            box = pygame.Rect(0, 0, 76, 76)
            box.center = (int(x), WORK.y + 340)
            pygame.draw.rect(screen, (24, 40, 58), box, border_radius=8)
            filled = i < len(st["typed"])
            pygame.draw.rect(screen, YELLOW if i == len(st["typed"]) else GREY, box, 3,
                             border_radius=8)
            if filled:
                img = self.f_big.render(st["typed"][i], True, WHITE)
                screen.blit(img, img.get_rect(center=box.center))
        # on-screen keys for mouse players
        for k, label in enumerate(("0", "1")):
            rect = pygame.Rect(WORK.centerx - 110 + k * 120, WORK.bottom - 80, 100, 44)
            self._button(screen, rect, label, ("type", label), WHITE)

    # --- stages 3-6: explore ---
    def _draw_explore(self, screen):
        step, st = self.step, self.st
        gate = step["gate"]
        info = GINFO[gate]
        for i, line in enumerate(wrap_text(self.f_small, info["analogy"], WORK.width - 40)):
            screen.blit(self.f_small.render(line, True, CYAN), (WORK.x + 20, WORK.y + 16 + i * 22))

        sym = pygame.Rect(260, 225, 170, 130)
        ina, inb, out = gate_pins(gate, sym)
        a, b = st["a"], st["b"]
        y_val = gate_out(gate, a, b)

        if gate == "NOT":
            sw_a = (110, ina[1])
            self._switch(screen, sw_a[0], sw_a[1], "A", a, ("switch", "a"))
            draw_wire(screen, (sw_a[0] + 48, sw_a[1]), ina, a)
        else:
            self._switch(screen, 110, 215, "A", a, ("switch", "a"))
            self._switch(screen, 110, 365, "B", b, ("switch", "b"))
            draw_wire(screen, (158, 215), ina, a)
            draw_wire(screen, (158, 365), inb, b)

        draw_gate(screen, gate, sym, WHITE)
        label = self.f_small.render(gate, True, YELLOW)
        screen.blit(label, label.get_rect(center=(sym.centerx, sym.bottom + 16)))

        bulb = (545, out[1])
        draw_wire(screen, out, (bulb[0] - 42, out[1]), y_val)
        draw_bulb(screen, bulb[0], bulb[1], 38, y_val)
        yl = self.f_body.render(f"Y = {y_val}", True, BULB_ON if y_val else GREY)
        screen.blit(yl, yl.get_rect(center=(bulb[0], bulb[1] + 70)))

        # combinations tracker
        screen.blit(self.f_tiny.render("COMBINATIONS TRIED", True, GREY),
                    (WORK.x + 24, WORK.bottom - 74))
        if gate == "NOT":
            combos = [(0, 0), (1, 0)]
            labels = ["A = 0", "A = 1"]
            seen = {(s[0], 0) for s in st["seen"]}
        else:
            combos = [(0, 0), (0, 1), (1, 0), (1, 1)]
            labels = [f"{x}{y}" for x, y in combos]
            seen = st["seen"]
        for i, (c, lab) in enumerate(zip(combos, labels)):
            self._chip(screen, WORK.x + 80 + i * 100, WORK.bottom - 32, lab,
                       c in seen, w=84)

    # --- stage 7: combine ---
    def _draw_combine(self, screen):
        st = self.st
        gate = st["gate"]
        use_not = st["use_not"]
        a, b = st["a"], st["b"]

        # gate selector + NOT toggle
        for i, g in enumerate(("AND", "OR", "XOR")):
            rect = pygame.Rect(WORK.x + 24 + i * 100, WORK.y + 18, 90, 36)
            col = YELLOW if g == gate else GREY
            self._button(screen, rect, f"{i + 1}  {g}", ("pick_gate", g), col)
        rect = pygame.Rect(WORK.right - 190, WORK.y + 18, 166, 36)
        self._button(screen, rect, "REMOVE NOT [T]" if use_not else "ADD NOT [T]",
                     ("toggle_not",), GREEN if use_not else CYAN)

        sym = pygame.Rect(190, 235, 150, 130)
        ina, inb, out = gate_pins(gate, sym)
        self._switch(screen, 95, 235, "A", a, ("switch", "a"))
        self._switch(screen, 95, 395, "B", b, ("switch", "b"))
        draw_wire(screen, (143, 235), ina, a)
        draw_wire(screen, (143, 395), inb, b)
        draw_gate(screen, gate, sym, WHITE)

        base = gate_out(gate, a, b)
        final = 1 - base if use_not else base
        not_rect = pygame.Rect(385, 260, 100, 80)
        nin, _n2, nout = gate_pins("NOT", not_rect)
        draw_wire(screen, out, nin, base, elbow=False)
        draw_gate(screen, "NOT", not_rect, WHITE if use_not else (70, 84, 100))
        if not use_not:
            draw_wire(screen, nin, nout, base, elbow=False)
        bulb = (545, 300)
        draw_wire(screen, nout, (bulb[0] - 38, 300), final, elbow=False)
        draw_bulb(screen, bulb[0], bulb[1], 32, final)
        yl = self.f_body.render(f"Y = {final}", True, BULB_ON if final else GREY)
        screen.blit(yl, yl.get_rect(center=(bulb[0], bulb[1] + 66)))

        name = {"AND": "NAND", "OR": "NOR", "XOR": "XNOR"}[gate] if use_not else gate
        title = f"{gate} + NOT  =  {name}" if use_not else f"{gate}  (no NOT yet)"
        img = self.f_title.render(title, True, YELLOW if use_not else WHITE)
        screen.blit(img, img.get_rect(center=(WORK.centerx, WORK.bottom - 62)))
        done = [g for g in ("AND", "OR") if g in st["seen"]]
        msg = self.f_tiny.render(
            "NOT added to: " + (", ".join(done) if done else "nothing yet") + "   (need AND and OR)",
            True, GREEN if len(done) == 2 else GREY)
        screen.blit(msg, msg.get_rect(center=(WORK.centerx, WORK.bottom - 28)))

    # --- truth table ---
    def _draw_table(self, screen):
        step, st = self.step, self.st
        gate = step["gate"]
        rows = rows_for(gate)
        two = gate != "NOT"

        screen.blit(self.f_small.render("A truth table lists every input and its output.",
                                        True, CYAN), (WORK.x + 20, WORK.y + 16))
        screen.blit(self.f_tiny.render("Click a Y cell (or UP/DOWN), then press 0 or 1.",
                                       True, GREY), (WORK.x + 20, WORK.y + 42))
        x0, y0 = 90, 140
        cols = [("A", x0), ("B", x0 + 80), ("Y", x0 + 190)] if two else \
               [("A", x0), ("Y", x0 + 120)]
        for name, cx in cols:
            hd = pygame.Rect(cx, y0, 66, 38)
            pygame.draw.rect(screen, (30, 60, 84), hd, border_radius=6)
            img = self.f_body.render(name, True, YELLOW if name == "Y" else WHITE)
            screen.blit(img, img.get_rect(center=hd.center))

        for i, row in enumerate(rows):
            ry = y0 + 52 + i * 62
            for j, v in enumerate(row):
                cell = pygame.Rect(cols[j][1], ry, 66, 50)
                pygame.draw.rect(screen, (24, 40, 58), cell, border_radius=6)
                img = self.f_title.render(str(v), True, WHITE)
                screen.blit(img, img.get_rect(center=cell.center))
            ycx = cols[-1][1]
            cell = pygame.Rect(ycx, ry, 66, 50)
            val = st["cells"][i]
            pygame.draw.rect(screen, (28, 54, 40) if val is not None else (30, 34, 44),
                             cell, border_radius=6)
            edge = RED if i in st["bad"] else (YELLOW if i == st["sel"] else GREY)
            pygame.draw.rect(screen, edge, cell, 3, border_radius=6)
            txt = "?" if val is None else str(val)
            img = self.f_title.render(txt, True, GREY if val is None else GREEN)
            screen.blit(img, img.get_rect(center=cell.center))
            self.buttons.append((cell, ("cell", i)))
            if val is not None and not st["bad"]:
                draw_bulb(screen, ycx + 90, ry + 25, 14, val)

        sym = pygame.Rect(400, 190, 190, 130)
        draw_gate(screen, gate, sym, WHITE)
        lab = self.f_body.render(gate, True, YELLOW)
        screen.blit(lab, lab.get_rect(center=(sym.centerx, sym.bottom + 20)))
        for i, line in enumerate(wrap_text(self.f_tiny, GINFO[gate]["rule"], 200)):
            screen.blit(self.f_tiny.render(line, True, GREY),
                        (sym.x - 6, sym.bottom + 46 + i * 18))

    # --- multiple-choice steps ---
    def _draw_choice(self, screen):
        step, st = self.step, self.st
        y = WORK.y + 16
        for line in wrap_text(self.f_body, step["q"], WORK.width - 40):
            screen.blit(self.f_body.render(line, True, WHITE), (WORK.x + 20, y))
            y += 28

        visual = step["visual"]
        cy = WORK.y + 215
        opts = step["options"]
        int_opts = all(isinstance(v, int) for _l, v in opts)
        rects = self._option_rects(opts, int_opts)
        options_top = min(r.y for r in rects)
        if visual == "chips":
            n = len(step["chips"])
            for i, (name, val) in enumerate(step["chips"]):
                cx = int(WORK.centerx + (i - (n - 1) / 2) * 220)
                draw_bulb(screen, cx, cy, 30, val)
                img = self.f_small.render(f"{name} = {val}", True, WHITE)
                screen.blit(img, img.get_rect(center=(cx, cy + 62)))
        elif visual == "symbol":
            draw_gate(screen, step["gate"], pygame.Rect(WORK.centerx - 120, cy - 70, 240, 150),
                      WHITE, stroke=4)
        elif visual == "column":
            self._draw_mystery_column(screen, step["gate"], WORK.centerx - 130, cy - 80)
        elif visual == "boss":
            self._draw_boss(screen, step["inputs"])
        else:
            self._draw_extra_visual(screen, step, y, options_top - 8)

        for i, ((label, val), rect) in enumerate(zip(opts, rects)):
            selected = (st["sel"] == val) if int_opts else (st["sel"] == i)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (30, 70, 56) if selected else ((24, 46, 66) if hover else (20, 34, 50)),
                             rect, border_radius=8)
            pygame.draw.rect(screen, GREEN if selected else GREY, rect, 3, border_radius=8)
            prefix = "" if int_opts else f"{i + 1}  "
            img = self.f_body.render(prefix + label, True, WHITE)
            screen.blit(img, img.get_rect(center=rect.center))
            self.buttons.append((rect, ("opt", i)))

    def _draw_extra_visual(self, screen, step, top, bottom):
        """Hook: subclasses draw their own picture above the answer buttons."""

    def _option_rects(self, opts, int_opts):
        """Answer buttons: a row when the labels are short, a stack when long."""
        n = len(opts)
        prefix = "" if int_opts else "4  "
        widest = max(self.f_body.size(prefix + label)[0] for label, _v in opts)
        row_w = 210 if n == 2 else 128
        if widest <= row_w - 16:
            gap = 20
            total = n * row_w + (n - 1) * gap
            x = WORK.centerx - total // 2
            return [pygame.Rect(x + i * (row_w + gap), WORK.bottom - 78, row_w, 56)
                    for i in range(n)]
        height, gap = 40, 8
        total = n * height + (n - 1) * gap
        top = WORK.bottom - 14 - total
        return [pygame.Rect(WORK.x + 30, top + i * (height + gap), WORK.width - 60, height)
                for i in range(n)]

    def _draw_mystery_column(self, screen, gate, x0, y0):
        out = outputs_for(gate)
        for name, cx in (("A", x0), ("B", x0 + 80), ("Y", x0 + 170)):
            hd = pygame.Rect(cx, y0, 66, 34)
            pygame.draw.rect(screen, (30, 60, 84), hd, border_radius=6)
            img = self.f_body.render(name, True, YELLOW if name == "Y" else WHITE)
            screen.blit(img, img.get_rect(center=hd.center))
        for i, (a, b) in enumerate(rows_for(gate)):
            ry = y0 + 42 + i * 42
            for cx, v, col in ((x0, a, WHITE), (x0 + 80, b, WHITE), (x0 + 170, out[i], GREEN)):
                cell = pygame.Rect(cx, ry, 66, 36)
                pygame.draw.rect(screen, (24, 40, 58), cell, border_radius=6)
                img = self.f_body.render(str(v), True, col)
                screen.blit(img, img.get_rect(center=cell.center))

    def _draw_boss(self, screen, inputs):
        a, b, c = inputs
        oy = 62
        or_r = pygame.Rect(240, 150 + oy, 120, 84)
        not_r = pygame.Rect(240, 280 + oy, 120, 60)
        and_r = pygame.Rect(430, 190 + oy, 130, 100)
        o_a, o_b, o_out = gate_pins("OR", or_r)
        n_in, _n2, n_out = gate_pins("NOT", not_r)
        a_in, a_b, a_out = gate_pins("AND", and_r)

        sources = [("Door", a, 110, 172 + oy), ("Window", b, 110, 214 + oy),
                   ("Badge", c, 110, 310 + oy)]
        for name, val, sx, sy in sources:
            self._chip(screen, sx, sy, f"{name} {val}", val, w=124, h=34)
        draw_wire(screen, (172, 172 + oy), o_a, a)
        draw_wire(screen, (172, 214 + oy), o_b, b)
        draw_wire(screen, (172, 310 + oy), n_in, c)

        draw_gate(screen, "OR", or_r, WHITE)
        draw_gate(screen, "NOT", not_r, WHITE)
        draw_gate(screen, "AND", and_r, WHITE)
        neutral = (80, 130, 160)
        pygame.draw.lines(screen, neutral, False,
                          [o_out, (400, o_out[1]), (400, a_in[1]), a_in], 4)
        pygame.draw.lines(screen, neutral, False,
                          [n_out, (400, n_out[1]), (400, a_b[1]), a_b], 4)
        pygame.draw.line(screen, neutral, a_out, (a_out[0] + 40, a_out[1]), 4)
        draw_bulb(screen, a_out[0] + 80, a_out[1], 24, 0)
        q = self.f_body.render("?", True, YELLOW)
        screen.blit(q, q.get_rect(center=(a_out[0] + 80, a_out[1] + 50)))
        for text, r in (("OR", or_r), ("NOT", not_r), ("AND", and_r)):
            img = self.f_tiny.render(text, True, YELLOW)
            screen.blit(img, img.get_rect(center=(r.centerx, r.bottom + 12)))

    # --- stage-complete card ---
    def _draw_done(self, screen):
        stage = self.stage
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, GREEN, FULL, 3, border_radius=10)
        n = self.stage_i + 1
        head = self.f_big.render(f"STAGE {n} COMPLETE", True, GREEN)
        screen.blit(head, (FULL.x + 24, FULL.y + 14))
        sub = self.f_body.render(f"{stage['title']}  -  {stage['sub']}", True, WHITE)
        screen.blit(sub, (FULL.x + 24, FULL.y + 62))

        left = pygame.Rect(FULL.x + 24, FULL.y + 100, 330, 300)
        gates = stage["gates"]
        sid = stage["id"]
        if sid == "s1_onoff":
            for i, v in enumerate((0, 1)):
                draw_bulb(screen, left.x + 80 + i * 150, left.y + 70, 38, v,
                          "OFF = 0" if v == 0 else "ON = 1", self.f_body)
        elif sid == "s2_bits":
            self._done_table(screen, left.x + 10, left.y + 10,
                             ["Place", "8", "4", "2", "1"],
                             [["Bit", "1", "1", "0", "1"],
                              ["Worth", "8", "4", "0", "1"]], 62)
            screen.blit(self.f_body.render("8 + 4 + 0 + 1 = 13", True, YELLOW),
                        (left.x + 10, left.y + 140))
        elif sid == "s8_review":
            names = ["NOT", "AND", "OR", "XOR", "NAND", "NOR"]
            rows = [[g] + ([" ".join(map(str, outputs_for(g)))]) for g in names]
            self._done_table(screen, left.x + 10, left.y - 6, ["Gate", "Y  (00 01 10 11)"],
                             rows, [90, 210], rowh=34)
        elif len(gates) == 1:
            g = gates[0]
            draw_gate(screen, g, pygame.Rect(left.x + 10, left.y, 170, 110), WHITE, 4)
            hdr = ["A", "Y"] if g == "NOT" else ["A", "B", "Y"]
            rows = [[*map(str, r), str(gate_out(g, *r))] for r in rows_for(g)]
            self._done_table(screen, left.x + 10, left.y + 130, hdr, rows, 62, rowh=34)
        else:
            for i, g in enumerate(gates):
                draw_gate(screen, g, pygame.Rect(left.x + 10 + i * 170, left.y, 150, 100), WHITE, 3)
            rows = [[str(a), str(b), str(gate_out("NAND", a, b)), str(gate_out("NOR", a, b))]
                    for a, b in rows_for("NAND")]
            self._done_table(screen, left.x + 10, left.y + 120, ["A", "B", "NAND", "NOR"],
                             rows, 70, rowh=34)

        # right column: rule / math / memory
        rx = FULL.x + 390
        rw = FULL.right - rx - 24
        y = FULL.y + 104
        items = self._done_items(stage)
        for label, text in items:
            screen.blit(self.f_small.render(label, True, CYAN), (rx, y))
            y += 24
            for line in wrap_text(self.f_small, text, rw):
                screen.blit(self.f_small.render(line, True, WHITE), (rx, y))
                y += 23
            y += 10

        note = self.f_small.render(
            "Saved to NOTEBOOK [N]  >  TEST THE LOGIC  >  MY BASIC NOTES", True, YELLOW)
        screen.blit(note, (FULL.x + 24, FULL.bottom - 62))
        rect = pygame.Rect(FULL.right - 230, FULL.bottom - 52, 210, 38)
        last = self.stage_i >= len(self.stages) - 1
        self._button(screen, rect, "FINISH LEVEL" if last else "NEXT STAGE  [ENTER]",
                     ("next",), GREEN)

    def _done_items(self, stage):
        sid = stage["id"]
        if sid == "s1_onoff":
            return [("RULE", "0 means OFF. 1 means ON. That is the only language a digital circuit speaks."),
                    ("NEW WORD", "Each 0 or 1 is called a BIT.")]
        if sid == "s2_bits":
            return [("RULE", "A row of bits is a binary number, read left to right."),
                    ("MATH LINK", "Place values from the right are 1, 2, 4, 8 ... (each one doubles). "
                                  "Add up the places that hold a 1: 1101 = 8 + 4 + 1 = 13."),
                    ("NEXT", "Now we meet the gates that make decisions with bits.")]
        if sid == "s7_combine":
            return [("RULE", "Put NOT after AND to get NAND. Put NOT after OR to get NOR."),
                    ("SYMBOL", "A small circle on the output means 'NOT is built in'."),
                    ("MATH LINK", "NAND: Y = 1 - (A x B).   NOR: Y = 1 - (A + B), with the sum capped at 1."),
                    ("REMEMBER", "NAND is OFF only when all inputs are ON. NOR is ON only when all inputs are OFF.")]
        if sid == "s8_review":
            return [("YOU CAN NOW", "Read 0 and 1, name six gates from their symbol, fill their truth tables, "
                                    "and trace a small circuit."),
                    ("ALARM CIRCUIT", "Y = (Door OR Window) AND (NOT Badge)."),
                    ("NEXT", "Everything is in your notebook as a cheat sheet. "
                             "Use it to revise before moving on!")]
        g = stage["gates"][0]
        info = GINFO[g]
        return [("RULE", info["rule"]), ("MATH LINK", info["math"]),
                ("SYMBOL", info["symbol"]), ("REMEMBER", info["memory"])]

    def _done_table(self, screen, x, y, headers, rows, colw, rowh=36):
        widths = list(colw) if isinstance(colw, (list, tuple)) else [colw] * len(headers)
        xs = [x + sum(widths[:j]) for j in range(len(widths))]
        for j, h in enumerate(headers):
            rect = pygame.Rect(xs[j], y, widths[j] - 4, rowh - 2)
            pygame.draw.rect(screen, (30, 60, 84), rect, border_radius=4)
            img = self.f_small.render(h, True, YELLOW)
            screen.blit(img, img.get_rect(center=rect.center))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                rect = pygame.Rect(xs[j], y + (i + 1) * rowh, widths[j] - 4, rowh - 2)
                pygame.draw.rect(screen, (22, 38, 54), rect, border_radius=4)
                last = j == len(row) - 1
                img = self.f_small.render(v, True, GREEN if last and len(headers) > 2 else WHITE)
                screen.blit(img, img.get_rect(center=rect.center))
