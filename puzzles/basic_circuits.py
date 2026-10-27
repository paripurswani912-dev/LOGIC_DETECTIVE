# puzzles/basic_circuits.py
# Logic Detective: BASIC LEVEL 2 - CIRCUIT LAB
# "Circuits and Understanding Boolean Algebra"  (10 stages, 60 activities)
#
# Built on the shared engine (puzzles/circuit_engine.py) and monitor frame
# (screen_borders.py). Nothing in circuit_engine.py has to change: this file
# subclasses Workbench (LabBench) to add per-source wire colours and ghost-wire
# hints.
#
# Activity kinds
#   explore : prebuilt circuit(s). Toggle every input row, then answer.
#             (lock=True turns it into PREDICT: switches stay locked until
#             the student commits a prediction.)
#   build   : place gates from a palette, drag them, wire them, test them.
#             Some builds start from a broken circuit (REPAIR).
#   table   : fill in the truth table (and SAME? column) from a live circuit.
#   choose  : click each line to cycle through its options (keywords,
#             proof reasons, valid/wrong steps ...).
#
# Hooks for the host game
#   puzzle = BasicCircuitLabPuzzle(notebook=None)
#   puzzle.attach_notebook(notebook)   # optional: stage notes get saved
#   puzzle.handle_event(event) / puzzle.draw(screen)
#   puzzle.solved       -> True after the final screen is confirmed
#   puzzle.wants_exit   -> True when the player pressed ESC (host decides)
#
# Controls: ENTER check | H hint | N notebook (host forwards N) | ESC exit
#           A-D flip the matching switch, mouse for everything else.

import itertools
import math

import pygame

from puzzles.circuit_engine import (
    Circuit, Component, Workbench, draw_pixel_gate_symbol,
    CYAN, CYAN_DIM, WHITE, GREY, GREEN, YELLOW, ORANGE, RED, AREA_BG,
)

from screen_borders import draw_pixel_monitor

try:
    from .base_puzzle import BasePuzzle
except Exception:  # pragma: no cover - lets the file import stand-alone
    class BasePuzzle:
        def __init__(self):
            self.solved = False

        def handle_event(self, event):
            pass

        def draw(self, screen):
            pass


# ---------------------------------------------------------------------------
# COLOURS
# ---------------------------------------------------------------------------

DARK_BLUE = (4, 10, 22)
PANEL_BLUE = (9, 24, 39)
TEAL = (39, 91, 113)
ROW_LINE = (30, 62, 82)
ROW_ON = (16, 56, 74)
DIM_RED = (135, 35, 48)
INK = (4, 20, 30)

# Wire colours follow the SOURCE of the signal (documented in the hint panel):
#   switch A = cyan, B = orange, C = purple, D = pink, constants = silver,
#   gate outputs cycle green / yellow / blue / coral / aqua / lilac.
INPUT_COL = {
    "A": (0, 229, 239), "B": (255, 184, 72),
    "C": (190, 125, 255), "D": (255, 105, 160),
}
CONST_COL = (170, 185, 200)
GATE_COLS = [
    (70, 230, 130), (255, 220, 65), (110, 165, 255),
    (255, 125, 90), (90, 225, 215), (235, 150, 255),
]
NO_SIGNAL = (80, 95, 110)

NOTEBOOK_TOPIC = "CIRCUIT LAB NOTES"
SHEET_TOPIC = "CIRCUIT LAB SHEET"

PALETTE_ALL = ["NOT", "AND", "OR", "XOR", "XNOR", "NAND", "NOR"]
GNAME = {
    "NOT": "NOT", "AND": "AND2", "OR": "OR2", "NAND": "NAND2",
    "NOR": "NOR2", "XOR": "XOR2", "XNOR": "XNOR2",
}


# ---------------------------------------------------------------------------
# BOOLEAN EXPRESSIONS  (nested tuples: ("AND", "A", ("NOT", "B")))
# ---------------------------------------------------------------------------

def ev(e, env):
    """Evaluate an expression tuple. Leaves: input letters, "0", "1"."""
    if isinstance(e, str):
        if e in ("0", "1"):
            return int(e)
        return env[e]
    k = e[0]
    if k == "NOT":
        return 1 - ev(e[1], env)
    a, b = ev(e[1], env), ev(e[2], env)
    if k == "AND":
        return a & b
    if k == "OR":
        return a | b
    if k == "XOR":
        return a ^ b
    if k == "NAND":
        return 1 - (a & b)
    if k == "NOR":
        return 1 - (a | b)
    if k == "XNOR":
        return 1 - (a ^ b)
    raise ValueError(k)


def _depth(e):
    if isinstance(e, str):
        return 0
    return 1 + max(_depth(k) for k in e[1:])


def rows_of(n):
    return list(itertools.product((0, 1), repeat=n))


def row_text(inputs, bits):
    return " ".join(f"{i}={b}" for i, b in zip(inputs, bits))


# ---------------------------------------------------------------------------
# CIRCUIT BUILDER  (expression tuples -> engine Circuit)
# ---------------------------------------------------------------------------

def build_circuit(inputs, outs, names=None, deletable=False):
    """outs: [(out_id, expr_or_None, caption, label)].
    expr None gives an unwired lamp (a blank bench for BUILD activities).
    Gates are ids g1, g2... in post-order. Positions are bench fractions."""
    names = names or {}
    c = Circuit()
    c.size_scale, c.font_scale = 0.72, 0.8
    n = len(inputs)
    ys = [0.5] if n == 1 else [0.14 + 0.72 * i / (n - 1) for i in range(n)]
    for letter, y in zip(inputs, ys):
        c.add(Component(letter, "SWITCH", 0.07, y, letter,
                        names.get(letter, "")))

    m = len(outs)
    exprs = [o[1] for o in outs if o[1] is not None]
    maxd = max([_depth(x) for x in exprs] or [1]) or 1

    def xs(d):
        return 0.5 if maxd == 1 else 0.26 + 0.48 * (d - 1) / (maxd - 1)

    gates, consts, counter = {}, {}, [0]

    def walk(e, k):
        if isinstance(e, str):
            if e in ("0", "1"):
                if e not in consts:
                    cid = "K" + e
                    comp = c.add(Component(
                        cid, "SOURCE", 0.07, 0.15 if e == "1" else 0.85,
                        "HIGH" if e == "1" else "LOW"))
                    comp.value = int(e)
                    consts[e] = cid
                return consts[e]
            return e
        kids = [walk(x, k) for x in e[1:]]
        counter[0] += 1
        gid = f"g{counter[0]}"
        gates[gid] = dict(kind=e[0], kids=kids, depth=_depth(e), out=k)
        return gid

    roots = [walk(o[1], k) if o[1] is not None else None
             for k, o in enumerate(outs)]

    for k, (oid, _expr, cap, label) in enumerate(outs):
        lo, hi = 0.08 + 0.84 * k / m, 0.08 + 0.84 * (k + 1) / m
        by = {}
        for gid, g in gates.items():
            if g["out"] == k:
                by.setdefault(g["depth"], []).append(gid)
        for d, lst in by.items():
            for i, gid in enumerate(lst):
                y = lo + (hi - lo) * (i + 1) / (len(lst) + 1)
                kind = gates[gid]["kind"]
                c.add(Component(gid, kind, xs(d), y, "", GNAME[kind],
                                deletable=deletable))
        c.add(Component(oid, "LED", 0.93, (lo + hi) / 2, label, cap))

    for gid, g in gates.items():
        for pin, src in enumerate(g["kids"]):
            c.wires.append((src, gid, pin))
    for k, (oid, *_rest) in enumerate(outs):
        if roots[k] is not None:
            c.wires.append((roots[k], oid, 0))
    return c


def apply_fault(c, fault):
    """Break a prebuilt circuit on purpose (REPAIR activities)."""
    kind = fault[0]
    if kind == "drop":                      # remove a wire
        c.disconnect(fault[1], fault[2])
    elif kind == "rewire":                  # wrong source on a pin
        c.disconnect(fault[1], fault[2])
        c.wires.append((fault[3], fault[1], fault[2]))
    elif kind == "kind":                    # wrong gate fitted
        c.comps[fault[1]].kind = fault[2]
        c.comps[fault[1]].sub = GNAME[fault[2]]


# ---------------------------------------------------------------------------
# DRAWING HELPERS
# ---------------------------------------------------------------------------

_FONTS = {}


def font(size):
    size = max(8, int(size))
    if size not in _FONTS:
        _FONTS[size] = pygame.font.SysFont("monospace", size, bold=True)
    return _FONTS[size]


def wrap(text, f, width):
    out = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split():
            test = (line + " " + word).strip()
            if f.size(test)[0] <= width or not line:
                line = test
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def fit_font(text, width, start, low=10):
    start = max(int(start), int(low))
    for size in range(int(start), int(low) - 1, -1):
        f = font(size)
        if f.size(text)[0] <= width:
            return f
    return font(low)


def fit_text(screen, text, rect, colour, start=15, low=10, gap=3):
    """Draw wrapped text in the biggest font that fits inside rect."""
    start = max(int(start), int(low))
    size, lines, lh, f = start, [], 0, None
    for size in range(int(start), int(low) - 1, -1):
        f = font(size)
        lines = wrap(text, f, rect.w)
        lh = f.get_linesize() + gap
        if len(lines) * lh - gap <= rect.h:
            break
    y = rect.y
    for ln in lines:
        if y + f.get_linesize() > rect.bottom + 2:
            break
        screen.blit(f.render(ln, True, colour), (rect.x, y))
        y += lh
    return y


def panel(screen, rect, border=TEAL, fill=PANEL_BLUE, width=2, radius=8):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width, border_radius=radius)


def button(screen, rect, text, colour, hover=False, size=15, fill=PANEL_BLUE,
           text_colour=None):
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, WHITE if hover else colour, rect, 2,
                     border_radius=6)
    f = fit_font(text, rect.w - 10, size, 9)
    img = f.render(text, True, text_colour or colour)
    screen.blit(img, img.get_rect(center=rect.center))


def draw_path(screen, pts, colour, width=3):
    pygame.draw.lines(screen, colour, False, pts, width)
    for p in pts[1:-1]:
        pygame.draw.circle(screen, colour, (int(p[0]), int(p[1])),
                           max(1, width // 2))


def draw_dashed(screen, pts, colour, width=3, dash=9, gap=7, phase=0.0):
    period = dash + gap
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        d = -(phase % period)
        while d < length:
            s, e = max(d, 0), min(d + dash, length)
            if e > s:
                pygame.draw.line(
                    screen, colour,
                    (a[0] + ux * s, a[1] + uy * s),
                    (a[0] + ux * e, a[1] + uy * e), width)
            d += period


class Lay:
    """Maps the 1400 x 880 design grid onto the monitor panel."""

    def __init__(self, panel_rect):
        self.panel = panel_rect
        self.sx = panel_rect.width / 1400
        self.sy = panel_rect.height / 880
        self.scale = max(0.65, min(self.sx, self.sy, 1.2))

    def X(self, v):
        return int(self.panel.x + v * self.sx)

    def Y(self, v):
        return int(self.panel.y + v * self.sy)

    def W(self, v):
        return max(1, int(v * self.sx))

    def H(self, v):
        return max(1, int(v * self.sy))

    def R(self, x, y, w, h):
        return pygame.Rect(self.X(x), self.Y(y), self.W(w), self.H(h))


# ---------------------------------------------------------------------------
# LAB BENCH: engine Workbench + per-source wire colours + ghost wires
# ---------------------------------------------------------------------------

class LabBench(Workbench):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ghost = None          # (src_id, dst_id, pin) overlay only

    def wire_colour(self, sid):
        comp = self.circuit.comps[sid]
        if self.circuit.value(sid) is None:
            return NO_SIGNAL
        if sid in INPUT_COL:
            return INPUT_COL[sid]
        if comp.kind == "SOURCE":
            return CONST_COL
        if sid[:1] == "g" and sid[1:].isdigit():
            return GATE_COLS[int(sid[1:]) % len(GATE_COLS)]
        return GATE_COLS[0]

    def _draw_wires(self, screen):
        used_h, used_v = [], []
        for src_id, dst_id, pin in self.circuit.wires:
            src = self.circuit.comps[src_id]
            dst = self.circuit.comps[dst_id]
            p0, p1 = self.out_pin(src), self.in_pin(dst, pin)
            pts = self._auto_route(src_id, dst_id, p0, p1, used_h, used_v)
            self._record(pts, src_id, used_h, used_v)
            on = self.circuit.value(src_id) == 1
            draw_path(screen, pts, self.wire_colour(src_id), 4 if on else 3)

    def _draw_ghost(self, screen):
        if not self.ghost:
            return
        src_id, dst_id, pin = self.ghost
        if src_id not in self.circuit.comps or dst_id not in self.circuit.comps:
            return
        p0 = self.out_pin(self.circuit.comps[src_id])
        p1 = self.in_pin(self.circuit.comps[dst_id], pin)
        pts = self._auto_route(src_id, dst_id, p0, p1, [], [])
        t = pygame.time.get_ticks()
        glow = 0.65 + 0.35 * math.sin(t / 230)
        col = (int(255 * glow), int(220 * glow), int(65 * glow))
        draw_dashed(screen, pts, col, 3, phase=t / 35)
        size = 12 + int(4 * math.sin(t / 230))
        for p in (p0, p1):
            pygame.draw.rect(screen, col,
                             (p[0] - size // 2, p[1] - size // 2, size, size), 2)
            pygame.draw.rect(screen, YELLOW, (p[0] - 3, p[1] - 3, 6, 6))

    def draw(self, screen, ticks=0):
        pygame.draw.rect(screen, AREA_BG, self.area)
        pygame.draw.rect(screen, CYAN_DIM, self.area, 2)
        old_clip = screen.get_clip()
        screen.set_clip(self.area)
        for gx in range(self.area.x + 12, self.area.right, 24):
            for gy in range(self.area.y + 12, self.area.bottom, 24):
                screen.set_at((gx, gy), (22, 45, 62))
        self._draw_wires(screen)
        for comp in self.circuit.comps.values():
            self._draw_component(screen, comp)
        self._draw_ghost(screen)
        if self.drag_from is not None:
            src = self.circuit.comps[self.drag_from]
            pygame.draw.line(screen, YELLOW, self.out_pin(src), self.mouse, 3)
        screen.set_clip(old_clip)

    def add_gate(self, kind, max_gates):
        """Spawn a gate and give it its caption (AND2, NOT, ...)."""
        before = set(self.circuit.comps)
        msg = self.spawn(kind, max_gates=max_gates)
        for cid in self.circuit.comps:
            if cid not in before:
                self.circuit.comps[cid].sub = GNAME[kind]
        return msg


# ---------------------------------------------------------------------------
# ACTIVITY DEFINITIONS
# ---------------------------------------------------------------------------

def _hints(h, default):
    h = list(h)
    while len(h) < 3:
        h.append(default)
    return h[:3]


def explore(title, tag, story, brief, task, hints, inputs, outs, names=None,
            ask=None, need_visit=True, lock=False, why=""):
    """outs: [(label, expr, caption)]"""
    third = ("Explanation: " + ask["why"]) if ask and ask.get("why") \
        else "Test every row and compare the lamps."
    return dict(kind="explore", title=title, tag=tag, story=story,
                brief=brief, task=task, hints=_hints(hints, third),
                inputs=inputs, outs=outs, names=names or {}, ask=ask,
                need_visit=need_visit, lock=lock, why=why)


def build(title, tag, story, brief, task, hints, inputs, outs, palette,
          max_gates, names=None, preset=None, faults=(), show_goal=False,
          why=""):
    """outs: [(label, target_expr, solution_expr, caption)]
    preset: expression pre-built on the bench (REPAIR), faults break it."""
    third = ("GHOST WIRE ON: connect the glowing yellow squares. If no "
             "wire shows, place the gate named in the status line.")
    return dict(kind="build", title=title, tag=tag, story=story,
                brief=brief, task=task, hints=_hints(hints, third),
                inputs=inputs, outs=outs, palette=palette,
                max_gates=max_gates, names=names or {}, preset=preset,
                faults=list(faults), show_goal=show_goal, why=why)


def table(title, tag, story, brief, task, hints, inputs, outs, names=None,
          match=False, why=""):
    third = ("Set the switches to one row, read the lamp, then copy that "
             "value into the table. Repeat for every row.")
    return dict(kind="table", title=title, tag=tag, story=story,
                brief=brief, task=task, hints=_hints(hints, third),
                inputs=inputs, outs=outs, names=names or {}, match=match,
                why=why)


def choose(title, tag, story, brief, task, hints, rows, options, why=""):
    """rows: [(text, answer_index)]"""
    third = "Take the lines one at a time and decide before you click."
    return dict(kind="choose", title=title, tag=tag, story=story,
                brief=brief, task=task, hints=_hints(hints, third),
                rows=rows, options=options, why=why, inputs=[])


YN = ["YES", "NO"]
GATES7 = ["AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR"]
LAWS = ["Distributive", "Complement", "Identity", "Domination",
        "Absorption", "Commutative", "De Morgan"]
ROWS2 = ["00", "01", "10", "11"]
OR_AB = ("OR", ("AND", "A", "B"), ("NOT", "C"))
XOR_SOP = ("OR", ("AND", ("NOT", "A"), "B"), ("AND", "A", ("NOT", "B")))

STAGES = []

# ---------------------------------------------------------------- STAGE 1
STAGES.append(dict(
    title="MEET THE SEVEN GATES",
    sub="Choose the gate that matches the job",
    acts=[
        explore(
            "AND: BOTH CONDITIONS REQUIRED", "EXPLORE",
            "A laboratory machine must start only when the safety KEY is "
            "inserted AND the operator is AUTHorised.",
            "An AND gate gives 1 only when every input is 1. Think of one "
            "door with two locks: both must be open. Boolean: Y = A·B.",
            "Click the KEY and AUTH switches through all four rows and "
            "watch the MACHINE lamp. Then answer the question.",
            ["Try every row: 00, 01, 10 and 11.",
             "Count the rows that switch the MACHINE lamp on."],
            ["A", "B"], [("Y", ("AND", "A", "B"), "MACHINE")],
            names={"A": "KEY", "B": "AUTH"},
            ask=dict(q="If an OR gate were used instead, would the machine "
                       "start with ONLY the key inserted?",
                     opts=YN, answer=0,
                     why="OR needs just one input at 1, so the key alone "
                         "would start the machine. AND is the safe choice."),
            why="AND = both conditions. One missing condition keeps it 0."),
        explore(
            "OR: EITHER CONDITION IS ENOUGH", "EXPLORE",
            "A campus help alarm must ring if the EMERGENCY button OR the "
            "SMOKE detector is active.",
            "An OR gate gives 1 when at least one input is 1. Either "
            "signal alone is enough. Boolean: Y = A + B.",
            "Toggle both switches through every row. Compare with the AND "
            "gate from the last activity, then answer.",
            ["Switch on only SMOKE. Does the alarm ring?",
             "OR is 0 only when both inputs are 0."],
            ["A", "B"], [("Y", ("OR", "A", "B"), "ALARM")],
            names={"A": "EMERG", "B": "SMOKE"},
            ask=dict(q="With an AND gate instead, would the alarm ring "
                       "when ONLY smoke is detected?",
                     opts=YN, answer=1,
                     why="AND would stay silent until both signals were "
                         "on, and a single real emergency would be missed."),
            why="OR = at least one condition. Both on is also allowed."),
        build(
            "NOT: REVERSE THE SIGNAL", "BUILD",
            "A warning lamp must be ON when the door is NOT closed. The "
            "sensor gives 1 when the door is closed.",
            "A NOT gate has one input and flips it: 0 becomes 1 and 1 "
            "becomes 0. Boolean: Y = A'.",
            "Place a NOT gate, wire DOOR into it, wire it to the lamp, "
            "then toggle DOOR and read the table.",
            ["Click NOT in the palette bar to place a gate.",
             "Drag from DOOR's right pin to the NOT gate's left pin, then "
             "from the NOT gate's right pin to the lamp."],
            ["A"], [("Y", ("NOT", "A"), ("NOT", "A"), "WARNING")],
            ["NOT"], 1, names={"A": "DOOR"},
            why="The output is always the opposite of the input."),
        explore(
            "NAND AND NOR: INVERTED DECISIONS", "COMPARE",
            "NAND: a lock stays ACTIVE unless BOTH release keys are turned. "
            "NOR: a system arms only when NEITHER alert is present.",
            "NAND = AND followed by NOT, so it is 0 only when both inputs "
            "are 1 (not both). NOR = OR followed by NOT, so it is 1 only "
            "when both inputs are 0 (neither).",
            "Toggle all four rows. Watch the NAND lamp and the NOR lamp, "
            "then answer.",
            ["Compare the two lamps on row 01.",
             "Find the single row where the NOR lamp is on."],
            ["A", "B"], [("NAND", ("NAND", "A", "B"), ""),
                         ("NOR", ("NOR", "A", "B"), "")],
            ask=dict(q="Which gate outputs 1 ONLY when both inputs are 0?",
                     opts=["NAND", "NOR"], answer=1,
                     why="NOR means neither input is 1, so only 00 gives "
                         "1. NAND is 0 only on 11."),
            why="Not both (NAND) is different from neither (NOR)."),
        explore(
            "XOR: DIFFERENT, NOT JUST EITHER", "COMPARE",
            "A staircase lamp should toggle when exactly ONE of the two "
            "wall switches is up. Compare XOR with OR.",
            "XOR gives 1 when the inputs DIFFER. OR gives 1 when at least "
            "one input is 1, so OR also gives 1 on 11. XOR does not.",
            "Toggle all rows and look closely at row 11 on both lamps, "
            "then answer.",
            ["Set both switches to 1 and compare the two lamps.",
             "XOR means exactly one."],
            ["A", "B"], [("XOR", ("XOR", "A", "B"), ""),
                         ("OR", ("OR", "A", "B"), "")],
            ask=dict(q="On row 11, which gate outputs 0?",
                     opts=["XOR", "OR"], answer=0,
                     why="Both inputs are 1, so they do not differ. XOR "
                         "gives 0 while OR still gives 1."),
            why="XOR and OR agree on 00, 01 and 10 but differ on 11."),
        build(
            "XNOR: DO THE TWO MATCH?", "BUILD",
            "Two attendance records must MATCH: both present or both "
            "absent. Choose the right gate yourself.",
            "XNOR gives 1 when the inputs are the same. It is XOR followed "
            "by NOT. Boolean: Y = AB + A'B'.",
            "Place ONE gate from the palette that makes the lamp light on "
            "00 and 11 only. Wire it and test.",
            ["The lamp must be on for 00 and 11 only.",
             "Which gate checks for matching inputs?"],
            ["A", "B"], [("Y", ("XNOR", "A", "B"), ("XNOR", "A", "B"),
                          "MATCH")],
            PALETTE_ALL, 1, names={"A": "RECORD 1", "B": "RECORD 2"},
            why="XNOR is 1 when the inputs are equal."),
    ],
    card=dict(
        rule="AND: 1 when both inputs are 1.  OR: 1 when at least one is 1."
             "  NOT flips.  NAND and NOR are AND and OR followed by NOT.  "
             "XOR: 1 when inputs differ.  XNOR: 1 when they match.",
        lesson_label="CIRCUIT LESSON",
        lesson="Choose the gate from the wording of the requirement: both, "
               "either, not, not both, neither, exactly one, same.",
        remember="OR allows both inputs to be 1, XOR does not. At 11, OR "
                 "gives 1 and XOR gives 0. XNOR checks that inputs match.",
        visual=dict(type="gatetable")),
    notes=["AND both 1. OR at least one 1. NOT flips. NAND/NOR invert.",
           "XOR: inputs differ (11 gives 0). XNOR: inputs match."],
))

# ---------------------------------------------------------------- STAGE 2
STAGES.append(dict(
    title="FROM WORDS TO GATES",
    sub="Read the requirement before choosing the symbol",
    acts=[
        choose(
            "KEYWORDS: WHICH GATE?", "REFLECT",
            "Requirements are written in ordinary words. Certain keywords "
            "point to one particular gate.",
            "Spot the keyword first: BOTH, EITHER, NOT, NOT BOTH, "
            "NEITHER, EXACTLY ONE, SAME.",
            "Click each line to cycle through the gates. Match every "
            "requirement with the gate that does the job, then CHECK.",
            ["Underline the keyword in each line.",
             "'Not both' is NAND but 'neither' is NOR."],
            [("BOTH the key AND the badge are needed", 0),
             ("EITHER the front OR the back door is open", 1),
             ("NEITHER sensor may be triggered", 4),
             ("Exactly ONE of the two switches is up", 5),
             ("The two codes must be the SAME", 6),
             ("The lamp is on when it is NOT raining", 2)],
            GATES7,
            why="Keywords map to gates: both=AND, either=OR, "
                "neither=NOR, exactly one=XOR, same=XNOR, not=NOT."),
        explore(
            "PREDICT FIRST, THEN TEST", "PREDICT",
            "A hall ticket is issued if attendance is at least 75% OR a "
            "medical certificate is approved. Y = A + B.",
            "Always predict before you test. A prediction forces you to "
            "use the rule, and the test shows whether you understood.",
            "Predict the output when attendance is LOW (A=0) and the "
            "medical certificate is approved (B=1). Then test it.",
            ["OR needs only one input at 1.",
             "Which input is 1 in this case?"],
            ["A", "B"], [("Y", ("OR", "A", "B"), "TICKET")],
            names={"A": "ATTEND", "B": "MEDICAL"},
            ask=dict(q="Predict Y for A=0 (low attendance), B=1 "
                       "(certificate).",
                     opts=["0", "1"], answer=1,
                     why="OR is 1 when at least one input is 1, so the "
                         "certificate alone issues the ticket."),
            need_visit=False, lock=True,
            why="Predict, test, compare. Do it every time."),
        build(
            "BUILD AN AND CIRCUIT", "BUILD",
            "Exam hall entry: allow a student only if the ID CARD is shown "
            "AND the HALL TICKET is shown.",
            "'Only if both' is the AND keyword. Boolean: Y = A·B.",
            "Pick the right gate from the palette, wire both switches "
            "into it, wire it to the lamp, and test all four rows.",
            ["Both conditions are required.",
             "Which gate is 1 only on row 11?"],
            ["A", "B"], [("Y", ("AND", "A", "B"), ("AND", "A", "B"),
                          "ENTRY")],
            PALETTE_ALL, 1, names={"A": "ID CARD", "B": "TICKET"},
            why="Only row 11 admits the student."),
        build(
            "BUILD AN OR CIRCUIT", "BUILD",
            "The emergency exit sign must light if MAINS power fails OR "
            "the TEST button is pressed.",
            "'Either one is enough' is the OR keyword. Boolean: Y = A + B.",
            "Choose the gate, wire it up and test every row. The sign "
            "must light on 01, 10 and 11.",
            ["Any single active signal lights the sign.",
             "Which gate is 0 only on row 00?"],
            ["A", "B"], [("Y", ("OR", "A", "B"), ("OR", "A", "B"), "SIGN")],
            PALETTE_ALL, 1, names={"A": "FAIL", "B": "TEST"},
            why="OR lights the sign if at least one signal is on."),
        explore(
            "XOR OR XNOR?", "COMPARE",
            "XOR checks that two inputs DIFFER. XNOR checks that they "
            "MATCH. Each is the opposite of the other.",
            "XNOR = XOR followed by NOT, so the two lamps are always "
            "opposite. Pick by the wording: different or same.",
            "Toggle every row and watch both lamps, then answer.",
            ["Look at row 00 on both lamps.",
             "When one lamp is on, the other is off."],
            ["A", "B"], [("XOR", ("XOR", "A", "B"), ""),
                         ("XNOR", ("XNOR", "A", "B"), "")],
            ask=dict(q="On row 00 (both inputs equal), which gate "
                       "outputs 1?",
                     opts=["XOR", "XNOR"], answer=1,
                     why="The inputs match, and matching is exactly what "
                         "XNOR detects."),
            why="XOR and XNOR give opposite results on every row."),
        build(
            "REPAIR THE WRONG GATE", "REPAIR",
            "The alarm should ring when the DOOR OR the WINDOW is open, "
            "but a technician fitted an AND gate by mistake.",
            "A wrong gate type looks fine on some rows and fails on "
            "others. Compare each row with the requirement.",
            "Right-click the gate to delete it, place the correct one "
            "and re-wire it.",
            ["Test row 01. Does the alarm ring?",
             "The wording says OR."],
            ["A", "B"], [("Y", ("OR", "A", "B"), ("OR", "A", "B"),
                          "ALARM")],
            PALETTE_ALL, 1, names={"A": "DOOR", "B": "WINDOW"},
            preset=("OR", "A", "B"), faults=[("kind", "g1", "AND")],
            why="Swapping the gate type repaired the logic."),
    ],
    card=dict(
        rule="Read the keywords: BOTH -> AND, EITHER -> OR, NOT -> NOT, "
             "NOT BOTH -> NAND, NEITHER -> NOR, EXACTLY ONE -> XOR, "
             "SAME -> XNOR.",
        lesson_label="CIRCUIT LESSON",
        lesson="Predict the output first, then test every row. A wrong "
               "gate can look correct on a few rows.",
        remember="Test all input combinations: a circuit that works for "
                 "one row can still be wrong.",
        visual=dict(type="lines", title="WORD -> GATE", lines=[
            "BOTH ................ AND",
            "EITHER .............. OR",
            "NOT ................. NOT",
            "NOT BOTH ............ NAND",
            "NEITHER ............. NOR",
            "EXACTLY ONE ......... XOR",
            "SAME / MATCH ........ XNOR"])),
    notes=["Keywords: both=AND, either=OR, not=NOT, not both=NAND.",
           "Neither=NOR, exactly one=XOR, same=XNOR. Predict, then test."],
))

# ---------------------------------------------------------------- STAGE 3
STAGES.append(dict(
    title="JOINING GATES",
    sub="One output becomes the next input",
    acts=[
        explore(
            "TRACE LEFT TO RIGHT (1)", "TRACE",
            "Inspect the circuit Y = (A·B) + C'. Follow the signal from "
            "the switches to the lamp.",
            "Work out the inner gates first: the AND gate and the NOT "
            "gate. Their outputs become the inputs of the OR gate.",
            "Predict the output for A=1, B=0, C=1 and commit it. The "
            "switches unlock after you answer.",
            ["AND of 1 and 0 is?",
             "NOT of C=1 is 0, so the OR gate sees 0 and 0."],
            ["A", "B", "C"], [("Y", OR_AB, "")],
            ask=dict(q="Predict Y for A=1, B=0, C=1.",
                     opts=["0", "1"], answer=0,
                     why="A·B = 0 and C' = 0, so OR(0,0) = 0."),
            need_visit=False, lock=True,
            why="Evaluate inner gates first, then the final gate."),
        explore(
            "TRACE LEFT TO RIGHT (2)", "TRACE",
            "Same circuit, different inputs. A wire carries a binary "
            "signal; a gate's output is the next gate's input.",
            "Brackets show what is grouped first. In (A·B) + C' the AND "
            "term and the NOT term are computed before the OR.",
            "Predict the output for A=0, B=1, C=0 and commit it.",
            ["A·B with A=0 gives?",
             "C' with C=0 gives 1."],
            ["A", "B", "C"], [("Y", OR_AB, "")],
            ask=dict(q="Predict Y for A=0, B=1, C=0.",
                     opts=["0", "1"], answer=1,
                     why="A·B = 0 but C' = 1, so OR(0,1) = 1."),
            need_visit=False, lock=True,
            why="One active branch is enough for the OR gate."),
        build(
            "BUILD Y = (A·B) + C'", "BUILD",
            "Build the circuit you just traced, starting from an empty "
            "bench.",
            "Gates needed: AND, NOT, OR. The AND and NOT outputs go "
            "into the OR. The OR output drives the lamp.",
            "Place the gates, wire A and B into the AND, C into the "
            "NOT, both outputs into the OR, and the OR into the lamp.",
            ["Three gates: one AND, one NOT, one OR.",
             "The OR gate is the last gate before the lamp."],
            ["A", "B", "C"], [("Y", OR_AB, OR_AB, "OUT")],
            ["NOT", "AND", "OR"], 3,
            why="Inner operations first, final gate last."),
        build(
            "BUILD Y = (A+B)·C", "BUILD",
            "A vault opens when the KEYCARD or the PIN is correct AND "
            "the guard APPROVES.",
            "The bracket (A+B) is evaluated first, so the OR gate comes "
            "before the AND gate.",
            "Build it with two gates. Wire A and B into the OR, then the "
            "OR and C into the AND, then the AND into the lamp.",
            ["The OR gate is the first gate.",
             "Which gate takes C as an input?"],
            ["A", "B", "C"], [("Y", ("AND", ("OR", "A", "B"), "C"),
                               ("AND", ("OR", "A", "B"), "C"), "VAULT")],
            ["AND", "OR"], 2,
            names={"A": "CARD", "B": "PIN", "C": "GUARD"},
            why="The brackets decide the order of the gates."),
        build(
            "REPAIR A MISSING WIRE", "REPAIR",
            "A technician left a wire out of Y = (A·B) + C'. Find the "
            "unconnected pin and fix it.",
            "A disconnected input means the circuit is incomplete, and "
            "the lamp cannot show a real output.",
            "Look for a pin that is not wired and connect the correct "
            "signal to it.",
            ["Which gate has an empty input pin?",
             "The NOT gate's output must reach the OR gate."],
            ["A", "B", "C"], [("Y", OR_AB, OR_AB, "OUT")],
            ["NOT", "AND", "OR"], 3, preset=OR_AB,
            faults=[("drop", "g3", 1)],
            why="Every gate input must be connected to something."),
        explore(
            "TWO CIRCUITS, ONE FUNCTION", "COMPARE",
            "Top: (A·B) + C'.  Bottom: NAND( NAND(A,B), C ). The "
            "designs differ, but do the lamps always agree?",
            "Different circuits can compute the same Boolean function. "
            "The only way to be sure is to test every row.",
            "Toggle all eight rows, compare the two lamps, then answer.",
            ["Test all 8 combinations of A, B and C.",
             "Watch for any row where the lamps disagree."],
            ["A", "B", "C"],
            [("A·B+C'", OR_AB, ""),
             ("NAND-NAND", ("NAND", ("NAND", "A", "B"), "C"), "")],
            ask=dict(q="Do the two circuits behave the same?",
                     opts=YN, answer=0,
                     why="They match on all 8 rows. The NAND form is "
                         "De Morgan's law at work."),
            why="Same truth table, so the same function."),
    ],
    card=dict(
        rule="Evaluate the inner brackets first. A gate's output is the "
             "next gate's input. Y = (A·B) + C' means AND, NOT, then OR.",
        lesson_label="CIRCUIT LESSON",
        lesson="Trace left to right. An unconnected input makes the "
               "circuit incomplete. The last gate drives the output lamp.",
        remember="Two different circuits can have the same Boolean "
                 "function, as with the AND-NOT-OR and NAND-NAND forms.",
        visual=dict(type="circuit", inputs=["A", "B", "C"],
                    outs=[("Y", OR_AB, "A·B + C'")],
                    values={"A": 1, "B": 1, "C": 1},
                    caption="Y = (A·B) + C'  -  AND, NOT, then OR")),
    notes=["Evaluate inner brackets first; a gate output feeds the next.",
           "Y=(A·B)+C' = AND + NOT then OR. Unwired input = incomplete."],
))

# ---------------------------------------------------------------- STAGE 4
STAGES.append(dict(
    title="FROM TRUTH TABLE TO CIRCUIT",
    sub="Build a circuit from its required outputs",
    acts=[
        choose(
            "STEP 1: FIND THE 1-ROWS", "REFLECT",
            "Required table (XOR): Y is 0 on 00, 1 on 01, 1 on 10 and 0 "
            "on 11.",
            "Sum-of-products starts by picking only the rows where "
            "Y = 1. Those rows each get their own AND term.",
            "For each row decide: USE it (Y is 1) or SKIP it (Y is 0).",
            ["Which rows have Y = 1?",
             "XOR is 1 when the inputs differ."],
            [("Row 00 :  A=0  B=0   ->  Y = 0", 1),
             ("Row 01 :  A=0  B=1   ->  Y = 1", 0),
             ("Row 10 :  A=1  B=0   ->  Y = 1", 0),
             ("Row 11 :  A=1  B=1   ->  Y = 0", 1)],
            ["USE THIS ROW", "SKIP"],
            why="Only the rows where Y = 1 contribute terms."),
        build(
            "STEP 2: ONE ROW, ONE AND TERM", "BUILD",
            "Build the term for row 01 (A=0, B=1). It must be 1 on that "
            "row and 0 on every other row.",
            "Use A for an input of 1 and A' for an input of 0. Row 01 "
            "gives the term A'·B.",
            "Place NOT and AND gates and build Y = A'·B. Test all rows.",
            ["A must be inverted. B is used as it is.",
             "NOT A and B go into an AND gate."],
            ["A", "B"], [("Y", ("AND", ("NOT", "A"), "B"),
                          ("AND", ("NOT", "A"), "B"), "ROW 01")],
            ["NOT", "AND"], 2, show_goal=True,
            why="The term A'·B is 1 only when A=0 and B=1."),
        choose(
            "STEP 3: WRITE THE SOP", "REFLECT",
            "Turn each chosen row into an AND term and combine the terms.",
            "Input 1 -> plain variable. Input 0 -> complemented variable. "
            "Then OR all the terms together.",
            "Click each line to choose the right term, then the "
            "operation that joins them.",
            ["Row 01: A is 0 (A'), B is 1 (B).",
             "Row 10: A is 1 (A), B is 0 (B')."],
            [("Row 01 (A=0, B=1) needs the term:", 1),
             ("Row 10 (A=1, B=0) needs the term:", 2),
             ("The terms are joined with:", 4)],
            ["A'·B'", "A'·B", "A·B'", "A·B", "OR", "AND"],
            why="Y = A'B + AB'. That is the XOR function."),
        build(
            "STEP 4: BUILD THE SOP CIRCUIT", "BUILD",
            "Build XOR as sum-of-products: Y = A'B + AB'. The GOAL "
            "column shows the required output.",
            "Two AND terms feed one OR gate. Each term needs one "
            "inverted input, so you also need two NOT gates.",
            "Build it with NOT, AND, AND and OR gates, then compare your "
            "OUTPUT column with the GOAL column.",
            ["You need 2 NOT, 2 AND and 1 OR gate.",
             "Each AND gets one plain input and one inverted input."],
            ["A", "B"], [("Y", XOR_SOP, XOR_SOP, "XOR")],
            ["NOT", "AND", "OR"], 5, show_goal=True,
            why="Five gates reproduce the XOR table exactly."),
        build(
            "STEP 5: DIAGNOSE THE LITERAL", "REPAIR",
            "This SOP circuit has a missing inverter: the A'·B term is "
            "using A instead of A'.",
            "Using A instead of A' selects the wrong row. The output "
            "mismatches on some rows of the table.",
            "Find the AND gate fed directly by A where A' is needed and "
            "re-wire it from the NOT gate.",
            ["Compare OUTPUT with GOAL: which rows are wrong?",
             "The upper AND must receive NOT A."],
            ["A", "B"], [("Y", XOR_SOP, XOR_SOP, "XOR")],
            ["NOT", "AND", "OR"], 5, preset=XOR_SOP,
            faults=[("rewire", "g2", 0, "A")], show_goal=True,
            why="A missing inverter changes which row a term selects."),
        explore(
            "VERIFY EVERY ROW", "VERIFY",
            "Top: your SOP circuit. Bottom: the XOR gate. Check them "
            "against each other on every row.",
            "The last step of the recipe is to verify the circuit "
            "against the original table.",
            "Toggle all four rows, compare the lamps, then answer.",
            ["Test all four rows.",
             "Look for a row where the lamps differ."],
            ["A", "B"], [("SOP", XOR_SOP, ""),
                         ("XOR", ("XOR", "A", "B"), "")],
            ask=dict(q="Does the SOP circuit match the XOR table on "
                       "all rows?", opts=YN, answer=0,
                     why="Yes. Y = A'B + AB' is XOR written as "
                         "NOT, AND and OR."),
            why="Always verify every row before trusting a design."),
    ],
    card=dict(
        rule="SOP recipe: 1) pick rows where Y = 1  2) write an AND term "
             "per row  3) input 1 = A, input 0 = A'  4) OR the terms  "
             "5) verify every row.",
        lesson_label="CIRCUIT LESSON",
        lesson="XOR: Y = A'B + AB' needs two NOT gates, two AND gates "
               "and one OR gate.",
        remember="A missing inverter changes the literal: A instead of "
                 "A' makes the term select the wrong row.",
        visual=dict(type="circuit", inputs=["A", "B"],
                    outs=[("Y", XOR_SOP, "XOR")], values={"A": 1, "B": 0},
                    caption="Y = A'B + AB'  (XOR as sum-of-products)")),
    notes=["SOP: pick rows where Y=1, AND term per row, OR the terms.",
           "Input 1 = A, input 0 = A'. XOR: Y = A'B + AB'. Verify rows."],
))

# ---------------------------------------------------------------- STAGE 5
STAGES.append(dict(
    title="BOOLEAN LAWS: THE BASICS",
    sub="Simplify without changing the answer",
    acts=[
        explore(
            "IDENTITY LAWS", "EXPLORE",
            "A·1 = A  and  A + 0 = A. A constant HIGH on an AND gate "
            "and a constant LOW on an OR gate change nothing.",
            "Three lamps: A·1, A+0 and plain A. If the first two always "
            "copy the third, the constant gate is useless hardware.",
            "Toggle A and compare the three lamps, then answer.",
            ["Set A to 0 then to 1 and watch all three lamps.",
             "The constant never changes the result."],
            ["A"], [("A·1", ("AND", "A", "1"), ""),
                    ("A+0", ("OR", "A", "0"), ""), ("A", "A", "")],
            ask=dict(q="What does ANDing A with 1 do to A?",
                     opts=["A stays A", "Output is 0", "Output is 1"],
                     answer=0,
                     why="1 is the identity for AND, 0 is the identity "
                         "for OR. The gate can be removed."),
            why="Identity: A·1 = A and A + 0 = A."),
        explore(
            "DOMINATION LAWS", "EXPLORE",
            "A·0 = 0  and  A + 1 = 1. A constant can force the output "
            "whatever A is.",
            "A·0 is stuck at 0 and A+1 is stuck at 1. The input A no "
            "longer matters.",
            "Toggle A and watch both lamps, then answer.",
            ["Does either lamp ever change?",
             "One input is a constant, so A cannot decide the output."],
            ["A"], [("A·0", ("AND", "A", "0"), ""),
                    ("A+1", ("OR", "A", "1"), "")],
            ask=dict(q="What is A + 1 for every value of A?",
                     opts=["0", "1", "A"], answer=1,
                     why="OR with a 1 is always 1, so the whole gate "
                         "can be replaced by a constant 1."),
            why="Domination: A·0 = 0 and A + 1 = 1."),
        explore(
            "IDEMPOTENT LAWS", "EXPLORE",
            "A·A = A  and  A + A = A. Feeding the same signal into both "
            "inputs adds nothing.",
            "Both inputs carry the same value, so the gate output "
            "cannot differ from that value.",
            "Toggle A and compare A·A, A+A and A, then answer.",
            ["Compare all three lamps on both rows.",
             "Repeating a signal does not change it."],
            ["A"], [("A·A", ("AND", "A", "A"), ""),
                    ("A+A", ("OR", "A", "A"), ""), ("A", "A", "")],
            ask=dict(q="Does repeating the same input change the "
                       "result?", opts=YN, answer=1,
                     why="No. A·A = A and A + A = A, so the extra gate "
                         "is redundant."),
            why="Idempotent: A·A = A and A + A = A."),
        explore(
            "COMPLEMENT LAWS", "EXPLORE",
            "A·A' = 0  and  A + A' = 1. A signal and its opposite are "
            "never 1 together, and are never both 0.",
            "Exactly one of A and A' is 1. AND needs both to be 1, so it "
            "is always 0. OR needs only one, so it is always 1.",
            "Toggle A and watch both lamps, then answer.",
            ["Is A·A' ever 1?",
             "A' is the NOT of A, one of them is always 0."],
            ["A"], [("A·A'", ("AND", "A", ("NOT", "A")), ""),
                    ("A+A'", ("OR", "A", ("NOT", "A")), "")],
            ask=dict(q="What is A·A' for every value of A?",
                     opts=["0", "1", "A"], answer=0,
                     why="A and A' are never 1 at the same time, so AND "
                         "is always 0."),
            why="Complement: A·A' = 0 and A + A' = 1."),
        explore(
            "DOUBLE NEGATION", "EXPLORE",
            "(A')' = A. Two NOT gates in a row cancel each other out.",
            "The first NOT flips A, the second flips it back. The "
            "result is A again.",
            "Toggle A and compare the lamps, then answer.",
            ["Follow the signal through both NOT gates.",
             "Flipping twice returns the original value."],
            ["A"], [("(A')'", ("NOT", ("NOT", "A")), ""), ("A", "A", "")],
            ask=dict(q="Two NOT gates in a row give:",
                     opts=["A", "A'", "0"], answer=0,
                     why="Each NOT inverts. Two inversions restore A, "
                         "so both gates can be removed."),
            why="Double negation: (A')' = A."),
        explore(
            "ABSORPTION LAWS", "EXPLORE",
            "A + AB = A  and  A(A + B) = A. The B logic is absorbed: "
            "A already decides the output.",
            "If A = 1, the OR term is already 1. If A = 0, the AND "
            "term is stuck at 0. B never matters.",
            "Toggle A and B through all rows and compare the lamps with "
            "plain A, then answer.",
            ["Does B ever change the result?",
             "Try A=1 with both values of B, then A=0."],
            ["A", "B"],
            [("A+AB", ("OR", "A", ("AND", "A", "B")), ""),
             ("A(A+B)", ("AND", "A", ("OR", "A", "B")), ""),
             ("A", "A", "")],
            ask=dict(q="Can the B logic be removed without changing the "
                       "output?", opts=YN, answer=0,
                     why="Yes. Absorption says the output is just A, so "
                         "the whole circuit is one wire."),
            why="Absorption: A + AB = A and A(A + B) = A."),
    ],
    card=dict(
        rule="A·1=A  A+0=A  |  A·0=0  A+1=1  |  A·A=A  A+A=A  |  "
             "A·A'=0  A+A'=1  |  (A')'=A  |  A+AB=A  A(A+B)=A.",
        lesson_label="MATH LINK",
        lesson="Every law removes hardware: a gate with a fixed, repeated "
               "or absorbed input can be deleted.",
        remember="A+A' is always 1 and A·A' is always 0. Do not mix "
                 "up the two complement laws.",
        visual=dict(type="lines", title="SIX LAW FAMILIES", lines=[
            "IDENTITY ....... A·1 = A       A + 0 = A",
            "DOMINATION ..... A·0 = 0       A + 1 = 1",
            "IDEMPOTENT ..... A·A = A       A + A = A",
            "COMPLEMENT ..... A·A' = 0      A + A' = 1",
            "DOUBLE NOT ..... (A')' = A",
            "ABSORPTION ..... A + AB = A    A(A+B) = A"])),
    notes=["Identity A·1=A, A+0=A. Domination A·0=0, A+1=1.",
           "Idempotent A·A=A. Complement A·A'=0, A+A'=1. Absorb A+AB=A."],
))

# ---------------------------------------------------------------- STAGE 6
STAGES.append(dict(
    title="BOOLEAN LAWS: GROUPING AND SHARING",
    sub="Rearrange expressions safely",
    acts=[
        explore(
            "COMMUTATIVE LAWS", "COMPARE",
            "A + B = B + A  and  AB = BA. Swapping the two inputs of a "
            "gate does not change its output.",
            "The order of the inputs does not matter for AND and OR. "
            "The same gate gives the same output either way round.",
            "Toggle all rows and compare each swapped pair, then answer.",
            ["Compare A+B with B+A, then A·B with B·A.",
             "Each pair of lamps should match."],
            ["A", "B"], [("A+B", ("OR", "A", "B"), ""),
                         ("B+A", ("OR", "B", "A"), ""),
                         ("A·B", ("AND", "A", "B"), ""),
                         ("B·A", ("AND", "B", "A"), "")],
            ask=dict(q="Does swapping the inputs change the output?",
                     opts=YN, answer=1,
                     why="No. AND and OR treat their inputs equally."),
            why="Commutative: the order of inputs does not matter."),
        explore(
            "ASSOCIATIVE LAWS", "COMPARE",
            "(A+B)+C = A+(B+C)  and  (AB)C = A(BC). Regrouping a chain "
            "of the same gate does not change the result.",
            "With one kind of gate, the grouping does not matter. Mixing "
            "AND with OR is different: there the brackets matter.",
            "Test all eight rows and compare the two lamps, then answer.",
            ["Compare the two lamps on all eight rows.",
             "Regrouping the same operator is always safe."],
            ["A", "B", "C"],
            [("(A+B)+C", ("OR", ("OR", "A", "B"), "C"), ""),
             ("A+(B+C)", ("OR", "A", ("OR", "B", "C")), "")],
            ask=dict(q="Are the two groupings equivalent?", opts=YN,
                     answer=0,
                     why="Yes. A chain of ORs gives 1 if any input is 1."),
            why="Associative: regroup a chain of one operator freely."),
        explore(
            "DISTRIBUTIVE LAW (AND OVER OR)", "COMPARE",
            "A(B + C) = AB + AC. AND distributes over OR, like "
            "multiplying out brackets.",
            "Left: one OR gate then one AND gate. Right: two AND gates "
            "then an OR gate. Same function, different hardware.",
            "Test all eight rows, then answer.",
            ["Compare the two lamps on all eight rows.",
             "Count the gates in each version."],
            ["A", "B", "C"],
            [("A(B+C)", ("AND", "A", ("OR", "B", "C")), ""),
             ("AB+AC", ("OR", ("AND", "A", "B"), ("AND", "A", "C")), "")],
            ask=dict(q="Are A(B+C) and AB + AC equivalent?", opts=YN,
                     answer=0,
                     why="Yes. They match on every row, but A(B+C) uses "
                         "fewer gates."),
            why="Distributive: A(B+C) = AB + AC."),
        explore(
            "DISTRIBUTIVE LAW (OR OVER AND)", "COMPARE",
            "A + BC = (A+B)(A+C). This second form looks strange but "
            "it is also true in Boolean algebra.",
            "In ordinary arithmetic, a+bc is not (a+b)(a+c). In Boolean "
            "algebra it is, and the truth table proves it.",
            "Test all eight rows, then answer.",
            ["Try A=0 first, then A=1.",
             "Do the lamps ever differ?"],
            ["A", "B", "C"],
            [("A+BC", ("OR", "A", ("AND", "B", "C")), ""),
             ("(A+B)(A+C)", ("AND", ("OR", "A", "B"), ("OR", "A", "C")),
              "")],
            ask=dict(q="Are A + BC and (A+B)(A+C) equivalent?", opts=YN,
                     answer=0,
                     why="Yes. When A=1 both are 1. When A=0 both "
                         "reduce to B·C."),
            why="Boolean algebra has two distributive laws."),
        explore(
            "SHARING GATES", "COMPARE",
            "Chip designers want fewer gates. Compare A·B + A·C with "
            "A·(B+C).",
            "Pulling out the common factor A lets one AND gate be shared "
            "by both terms.",
            "Check both circuits on all rows, then answer.",
            ["Both circuits have the same truth table.",
             "Count the gates: 3 against 2."],
            ["A", "B", "C"],
            [("AB+AC", ("OR", ("AND", "A", "B"), ("AND", "A", "C")), ""),
             ("A(B+C)", ("AND", "A", ("OR", "B", "C")), "")],
            ask=dict(q="Which version uses fewer gates?",
                     opts=["A·B + A·C (3 gates)", "A·(B+C) (2 gates)"],
                     answer=1,
                     why="Factoring A out shares one AND gate, saving a "
                         "gate with identical behaviour."),
            why="Factor out common terms to save gates."),
        choose(
            "SPOT THE WRONG REARRANGEMENT", "REFLECT",
            "Some rearrangements are valid and some break the circuit. "
            "Judge each line.",
            "Changing AND to OR, or ignoring brackets, changes the "
            "function. Reordering or regrouping one operator does not.",
            "Mark each line VALID or WRONG, then CHECK.",
            ["Try A=1, B=0, C=0 on the suspicious lines.",
             "Brackets decide which operator goes first."],
            [("A + BC  =  (A+B)·C", 1),
             ("A·(B+C)  =  AB + C", 1),
             ("A·B·C  =  C·B·A", 0),
             ("(A+B)+C  =  A+(B+C)", 0)],
            ["VALID", "WRONG"],
            why="Test suspicious equations with a row where they differ."),
    ],
    card=dict(
        rule="Commutative: AB = BA, A+B = B+A.  Associative: (AB)C = "
             "A(BC), (A+B)+C = A+(B+C).  Distributive: A(B+C) = AB+AC "
             "and A+BC = (A+B)(A+C).",
        lesson_label="CIRCUIT LESSON",
        lesson="Factoring shares gates: A·B + A·C needs 3 gates but "
               "A·(B+C) needs 2.",
        remember="A + BC is NOT (A+B)·C. Swapping AND and OR or ignoring "
                 "brackets changes the function.",
        visual=dict(type="lines", title="REARRANGING", lines=[
            "COMMUTATIVE  A·B = B·A      A+B = B+A",
            "ASSOCIATIVE  (A·B)·C = A·(B·C)",
            "             (A+B)+C = A+(B+C)",
            "DISTRIBUTIVE A·(B+C) = A·B + A·C",
            "             A+B·C = (A+B)·(A+C)",
            "SHARING      A·B + A·C  ->  A·(B+C)",
            "             3 gates    ->  2 gates"])),
    notes=["Commutative AB=BA. Associative (AB)C=A(BC). Regroup safely.",
           "Distributive A(B+C)=AB+AC and A+BC=(A+B)(A+C). Factor to share."],
))

# ---------------------------------------------------------------- STAGE 7
STAGES.append(dict(
    title="PROVE TWO CIRCUITS ARE EQUIVALENT",
    sub="Check every possible input",
    acts=[
        explore(
            "ONE ROW IS NOT ENOUGH", "EXPLORE",
            "Compare NOR(A,B) with A'·B'. Look at the starting row "
            "A=0, B=0 first.",
            "Two circuits are equivalent only if their outputs match on "
            "EVERY input row. A single matching row proves nothing.",
            "Look at row 00 on both lamps, then answer.",
            ["Both switches are 0 right now.",
             "Matching on one row is only a start."],
            ["A", "B"], [("NOR", ("NOR", "A", "B"), ""),
                         ("A'B'", ("AND", ("NOT", "A"), ("NOT", "B")), "")],
            ask=dict(q="At A=0, B=0 do the two lamps agree?", opts=YN,
                     answer=0,
                     why="They agree here, but one row proves nothing. "
                         "The next activities check all of them."),
            need_visit=False,
            why="Equivalence needs every row, not just one."),
        table(
            "PROVE IT WITH A TABLE", "PROVE",
            "Left: A'B + AB' built from NOT, AND, OR. Right: a plain "
            "XOR gate. Are they equal?",
            "A proof table lists every row, the left output, the right "
            "output, and whether they match. All rows must match.",
            "Fill LEFT, RIGHT and SAME? for every row. Use the switches "
            "to read the lamps.",
            ["Set the switches to a row and read both lamps.",
             "If every row says YES, the circuits are equivalent."],
            ["A", "B"], [("LEFT", XOR_SOP, ""),
                         ("RIGHT", ("XOR", "A", "B"), "")],
            match=True,
            why="All four rows match, so the two circuits are equivalent."),
        explore(
            "FIND THE COUNTEREXAMPLE", "PROVE",
            "A tempting claim: A + B = A XOR B. They look similar. "
            "Is it true?",
            "To disprove an equivalence, one differing row is enough. "
            "That row is the counterexample.",
            "Toggle all four rows, find where the lamps differ, then "
            "answer.",
            ["Compare the lamps on rows 00, 01 and 10 first.",
             "OR and XOR disagree exactly where both inputs are 1."],
            ["A", "B"], [("A+B", ("OR", "A", "B"), ""),
                         ("A XOR B", ("XOR", "A", "B"), "")],
            ask=dict(q="Which row disproves A+B = A XOR B?",
                     opts=ROWS2, answer=3,
                     why="At 11, OR gives 1 and XOR gives 0. One "
                         "mismatching row ends the argument."),
            why="One row where the outputs differ disproves equivalence."),
        table(
            "TEST A FALSE CLAIM", "PROVE",
            "Claim: A·B' = A. Test it row by row and decide whether "
            "the two circuits are equal.",
            "Mark SAME? as NO on any row where LEFT and RIGHT differ. A "
            "single NO means the claim is false.",
            "Fill LEFT, RIGHT and SAME? for all four rows.",
            ["The right circuit is just A.",
             "Check row 11: A·B' is 0 but A is 1."],
            ["A", "B"], [("LEFT", ("AND", "A", ("NOT", "B")), ""),
                         ("RIGHT", "A", "")],
            match=True,
            why="Row 11 gives 0 on the left and 1 on the right, so the "
                "claim is false."),
        choose(
            "A GUIDED ALGEBRA PROOF", "PROVE",
            "Prove  A + AB = A  by algebra. Each line is justified by a "
            "law. Name the law used at each step.",
            "Boolean algebra proves equivalence without a table. Each "
            "step rewrites the expression using one law.",
            "Click each step to choose the law used.",
            ["Step 1 writes A as A·1.",
             "Step 3: 1 + B is always 1."],
            [("A + AB = A·1 + AB", 2),
             ("A·1 + AB = A·(1 + B)", 0),
             ("A·(1 + B) = A·1", 3),
             ("A·1 = A", 2)],
            LAWS,
            why="Identity, distributive, domination, identity: every "
                "step names its law."),
        choose(
            "REPAIR THE PROOF", "PROVE",
            "A proof of  A + A'B = A + B  has been written, but one "
            "step is wrong. Find it.",
            "Every step must follow from the previous one by a law. A "
            "wrong result breaks the whole chain.",
            "Mark each line VALID or WRONG.",
            ["Check whether 1·(A + B) really equals A·B.",
             "Identity says 1·X = X."],
            [("A + A'B = (A + A')(A + B)", 0),
             ("(A + A')(A + B) = 1·(A + B)", 0),
             ("1·(A + B) = A·B", 1),
             ("so  A + A'B = A·B", 1)],
            ["VALID", "WRONG"],
            why="1·(A+B) = A+B by the identity law. The corrected proof "
                "gives A + A'B = A + B."),
    ],
    card=dict(
        rule="Two circuits are equivalent only if their outputs match "
             "for EVERY possible input combination.",
        lesson_label="MATH LINK",
        lesson="Proof table: list every row, the left output, the right "
               "output and whether they match. Or rewrite step by step "
               "with named laws.",
        remember="Three matching rows out of four is not a proof. One "
                 "mismatch is a counterexample.",
        visual=dict(type="lines", title="PROOF TEMPLATE", lines=[
            "A  B | LEFT | RIGHT | SAME?",
            "0  0 |  ?   |   ?   |  ?",
            "0  1 |  ?   |   ?   |  ?",
            "1  0 |  ?   |   ?   |  ?",
            "1  1 |  ?   |   ?   |  ?",
            "",
            "All rows YES  ->  equivalent",
            "Any row NO    ->  counterexample"])),
    notes=["Equivalent = same output on EVERY input row.",
           "Proof table: A|B|Left|Right|Same?  One NO row disproves."],
))

# ---------------------------------------------------------------- STAGE 8
STAGES.append(dict(
    title="MAKE THE CIRCUIT SMALLER",
    sub="Same behaviour, fewer gates",
    acts=[
        choose(
            "REDUCE  AB + AB'", "PROVE",
            "Simplify A·B + A·B' step by step. Name the law behind "
            "each step.",
            "Factor out the common A, then use the complement law, then "
            "the identity law.",
            "Click each step to choose the law used.",
            ["Factor out the common A first.",
             "B + B' is always 1."],
            [("AB + AB' = A(B + B')", 0),
             ("A(B + B') = A·1", 1),
             ("A·1 = A", 2)],
            LAWS,
            why="AB + AB' = A(B+B') = A·1 = A."),
        choose(
            "REDUCE  A + A'B", "PROVE",
            "Simplify A + A'B step by step. This one uses the second "
            "distributive law.",
            "A + A'B = (A+A')(A+B). The first bracket is 1, so only "
            "(A+B) remains.",
            "Click each step to choose the law used.",
            ["Distribute A over A'B using the OR-over-AND law.",
             "A + A' is always 1."],
            [("A + A'B = (A + A')(A + B)", 0),
             ("(A + A')(A + B) = 1·(A + B)", 1),
             ("1·(A + B) = A + B", 2)],
            LAWS,
            why="A + A'B = A + B."),
        explore(
            "COUNT THE GATES", "COMPARE",
            "Top: AB + AB' built with two AND gates, a NOT and an OR. "
            "Bottom: the simplified A.",
            "Both lamps behave identically, but the first uses lots of "
            "hardware and the second uses none.",
            "Toggle all rows and compare the lamps, then answer.",
            ["Count the gate symbols in the top circuit.",
             "NOT, AND, AND, OR."],
            ["A", "B"], [("AB+AB'", ("OR", ("AND", "A", "B"),
                                     ("AND", "A", ("NOT", "B"))), ""),
                         ("A", "A", "")],
            ask=dict(q="How many gates does the top circuit use?",
                     opts=["2", "3", "4"], answer=2,
                     why="NOT + AND + AND + OR = 4 gates, replaced by a "
                         "plain wire."),
            why="Simplifying saved 4 gates."),
        build(
            "SHRINK THE CIRCUIT", "BUILD",
            "The bench holds AB + AB'. Remove the redundant hardware so "
            "that Y still equals A.",
            "AB + AB' simplifies to A, so the output only needs a wire "
            "from A to the lamp.",
            "Right-click each gate to delete it. Then wire A straight "
            "to the lamp.",
            ["Delete every gate.",
             "Wire A's right pin to the lamp."],
            ["A", "B"], [("Y", "A", "A", "OUT")], [], 0,
            preset=("OR", ("AND", "A", "B"), ("AND", "A", ("NOT", "B"))),
            why="The smaller circuit has zero gates and the same output."),
        build(
            "GATE BUDGET: ONE GATE", "BUILD",
            "A + A'B uses 3 gates (NOT, AND, OR). Rebuild the same "
            "behaviour with a single gate.",
            "The simplified form is A + B. Which gate computes A + B?",
            "Place ONE gate that matches the original behaviour, wire "
            "it and test.",
            ["A + A'B simplifies to A + B.",
             "Which one gate gives 1 unless both inputs are 0?"],
            ["A", "B"], [("Y", ("OR", "A", "B"), ("OR", "A", "B"), "OUT")],
            PALETTE_ALL, 1,
            why="One OR gate replaces three gates."),
        table(
            "VERIFY THE SMALLER CIRCUIT", "VERIFY",
            "Left: AB + AB' (4 gates). Right: plain A. Prove the "
            "reduction really matches.",
            "A reduction is only trusted after the original and the "
            "reduced circuit agree on every row.",
            "Fill LEFT, RIGHT and SAME? for all four rows.",
            ["Read both lamps on each row.",
             "All four SAME? cells should read YES."],
            ["A", "B"], [("LEFT", ("OR", ("AND", "A", "B"),
                                   ("AND", "A", ("NOT", "B"))), ""),
                         ("RIGHT", "A", "")],
            match=True,
            why="Every row matches, so the reduction is safe."),
    ],
    card=dict(
        rule="AB + AB' = A(B+B') = A·1 = A.   A + A'B = (A+A')(A+B) = "
             "1·(A+B) = A + B.",
        lesson_label="MATH LINK",
        lesson="Factor, apply the complement law, then the identity law. "
               "Each step removes hardware.",
        remember="Always verify the smaller circuit against the original "
                 "on every row before replacing it.",
        visual=dict(type="lines", title="REDUCTIONS", lines=[
            "AB + AB'   =  A(B + B')",
            "           =  A·1",
            "           =  A            (4 gates -> 0)",
            "",
            "A + A'B    =  (A + A')(A + B)",
            "           =  1·(A + B)",
            "           =  A + B        (3 gates -> 1)"])),
    notes=["AB+AB' = A(B+B') = A·1 = A (4 gates to 0).",
           "A+A'B = (A+A')(A+B) = A+B (3 gates to 1). Verify every row."],
))

# ---------------------------------------------------------------- STAGE 9
STAGES.append(dict(
    title="DE MORGAN'S LAWS",
    sub="Push NOT through AND and OR",
    acts=[
        explore(
            "NOT BOTH OR NEITHER?", "EXPLORE",
            "NAND says 'NOT both'. NOR says 'NEITHER'. Different "
            "wording, different gates.",
            "De Morgan's laws connect these ideas: pushing a NOT "
            "through AND or OR swaps the operator and inverts each input.",
            "Toggle all four rows and compare the lamps, then answer.",
            ["Compare the lamps on rows 01 and 10.",
             "NAND is 1 there but NOR is 0."],
            ["A", "B"], [("NAND", ("NAND", "A", "B"), ""),
                         ("NOR", ("NOR", "A", "B"), "")],
            ask=dict(q="Do NAND and NOR always give the same output?",
                     opts=YN, answer=1,
                     why="No. They differ on 01 and 10. De Morgan "
                         "relates each to a different expression."),
            why="Not both and neither are different conditions."),
        explore(
            "NAND = OR OF INVERTED INPUTS", "COMPARE",
            "Top: NAND(A,B). Bottom: NOT A OR NOT B. Do they behave "
            "the same?",
            "First law: (AB)' = A' + B'. Break the bar over AND, change "
            "AND to OR and complement each variable.",
            "Test all rows, then answer.",
            ["Test all four rows.",
             "Check the lamps on 11 and on 00."],
            ["A", "B"], [("(AB)'", ("NAND", "A", "B"), ""),
                         ("A'+B'", ("OR", ("NOT", "A"), ("NOT", "B")), "")],
            ask=dict(q="Are (AB)' and A' + B' the same function?",
                     opts=YN, answer=0,
                     why="Yes, they match on every row. That is the "
                         "first De Morgan law."),
            why="(AB)' = A' + B'."),
        table(
            "PROVE (AB)' = A' + B'", "PROVE",
            "Use a truth table to prove De Morgan's first law.",
            "Fill LEFT = (AB)' and RIGHT = A'+B' from the live lamps "
            "and mark whether they are the same.",
            "Complete the table for all four rows.",
            ["Row 11: (AB)' is 0 and A'+B' is 0.",
             "Every row should read YES."],
            ["A", "B"], [("(AB)'", ("NOT", ("AND", "A", "B")), ""),
                         ("A'+B'", ("OR", ("NOT", "A"), ("NOT", "B")), "")],
            match=True,
            why="All rows match: (AB)' = A' + B'."),
        table(
            "PROVE (A+B)' = A'·B'", "PROVE",
            "Use a truth table to prove De Morgan's second law.",
            "Second law: (A+B)' = A'B'. Break the bar over OR, change "
            "OR to AND and complement each variable.",
            "Complete the table for all four rows.",
            ["Only row 00 makes (A+B)' equal to 1.",
             "A'·B' is also 1 only on row 00."],
            ["A", "B"], [("(A+B)'", ("NOT", ("OR", "A", "B")), ""),
                         ("A'B'", ("AND", ("NOT", "A"), ("NOT", "B")), "")],
            match=True,
            why="All rows match: (A+B)' = A'·B'."),
        build(
            "TRANSFORM A CIRCUIT", "BUILD",
            "NOR(A,B) is hard to find in stock. Rebuild it using only "
            "NOT and AND gates.",
            "By De Morgan, (A+B)' = A'·B'. Invert each input and then "
            "AND them.",
            "Place NOT, NOT and AND gates and build Y = A'·B'. Test it.",
            ["Two NOT gates, one AND gate.",
             "Each NOT output goes into the AND gate."],
            ["A", "B"], [("Y", ("NOR", "A", "B"),
                          ("AND", ("NOT", "A"), ("NOT", "B")), "NOR")],
            ["NOT", "AND"], 3,
            why="A'·B' is 1 only when both inputs are 0, exactly NOR."),
        build(
            "THREE VARIABLES", "BUILD",
            "(A·B·C)' = A' + B' + C'. Build the right-hand side using "
            "only NOT and OR gates.",
            "De Morgan works for any number of variables. Invert every "
            "variable and change AND to OR.",
            "Use three NOT gates and two OR gates. Check all 8 rows.",
            ["Three NOT gates, then OR them together.",
             "Chain two OR gates: (A' + B') + C'."],
            ["A", "B", "C"], [("Y", ("NOT", ("AND", ("AND", "A", "B"),
                                              "C")),
                               ("OR", ("OR", ("NOT", "A"), ("NOT", "B")),
                                ("NOT", "C")), "NAND3")],
            ["NOT", "OR"], 5,
            why="Y is 0 only when A, B and C are all 1."),
    ],
    card=dict(
        rule="(AB)' = A' + B'   and   (A+B)' = A'·B'.",
        lesson_label="MATH LINK",
        lesson="Break the bar, change the operator, complement each "
               "variable. NAND = OR of inverted inputs. NOR = AND of "
               "inverted inputs.",
        remember="Do not complement only one variable, and do not forget "
                 "to swap AND and OR.",
        visual=dict(type="circuit", inputs=["A", "B"],
                    outs=[("(AB)'", ("NAND", "A", "B"), ""),
                          ("A'+B'", ("OR", ("NOT", "A"), ("NOT", "B")),
                           "")],
                    values={"A": 1, "B": 0},
                    caption="NAND(A,B) = A' + B'  (same lamp, same rows)")),
    notes=["(AB)' = A' + B'.  (A+B)' = A'·B'.  Break bar, swap operator.",
           "Complement every variable. Prove with all rows, not one."],
))

# --------------------------------------------------------------- STAGE 10
STAGES.append(dict(
    title="UNIVERSAL GATES: NAND AND NOR ONLY",
    sub="Build any logic function from one gate type",
    acts=[
        build(
            "NOT FROM NAND", "BUILD",
            "A factory only stocks NAND gates. Build a NOT gate from "
            "one NAND.",
            "A NAND B is 1 unless both inputs are 1. Feed the same "
            "signal into both inputs: A NAND A = A'.",
            "Place ONE NAND gate, wire A into both input pins, wire it "
            "to the lamp.",
            ["Both NAND inputs come from A.",
             "When A=1 both inputs are 1, so the output is 0."],
            ["A"], [("Y", ("NOT", "A"), ("NAND", "A", "A"), "NOT")],
            ["NAND"], 1,
            why="NAND with tied inputs inverts the signal."),
        build(
            "AND FROM NAND", "BUILD",
            "Build AND using only NAND gates (two gates).",
            "NAND is AND followed by NOT. Add another NAND with tied "
            "inputs to invert it back: (A NAND B) NAND (A NAND B) = AB.",
            "Place two NAND gates. The first takes A and B. The second "
            "takes the first's output on both pins.",
            ["The first NAND takes A and B.",
             "Feed its output into both pins of the second NAND."],
            ["A", "B"], [("Y", ("AND", "A", "B"),
                          ("NAND", ("NAND", "A", "B"), ("NAND", "A", "B")),
                          "AND")],
            ["NAND"], 2,
            why="NAND then NOT is AND."),
        build(
            "OR FROM NAND", "BUILD",
            "Build OR using only NAND gates (three gates).",
            "Invert each input with a NAND, then NAND them: "
            "A' NAND B' = A + B (De Morgan).",
            "Place three NAND gates: one with A tied, one with B tied, "
            "one combining both outputs.",
            ["Two NAND gates act as NOT gates for A and B.",
             "A third NAND combines the two inverted signals."],
            ["A", "B"], [("Y", ("OR", "A", "B"),
                          ("NAND", ("NAND", "A", "A"), ("NAND", "B", "B")),
                          "OR")],
            ["NAND"], 3,
            why="De Morgan: A' NAND B' = A + B."),
        build(
            "NOT FROM NOR", "BUILD",
            "Now the other universal gate. Build a NOT gate from one "
            "NOR.",
            "A NOR A = A'. With both inputs tied together, NOR only "
            "outputs 1 when A is 0.",
            "Place ONE NOR gate, tie both inputs to A, wire it to the "
            "lamp.",
            ["Both NOR inputs come from A.",
             "NOR(0,0) = 1 and NOR(1,1) = 0."],
            ["A"], [("Y", ("NOT", "A"), ("NOR", "A", "A"), "NOT")],
            ["NOR"], 1,
            why="NOR with tied inputs also inverts the signal."),
        build(
            "OR AND AND FROM NOR", "BUILD",
            "Build both an OR (top lamp) and an AND (bottom lamp) using "
            "only NOR gates. Five gates in total.",
            "OR = (A NOR B) NOR (A NOR B). AND = (A NOR A) NOR "
            "(B NOR B): invert, then NOR.",
            "Build the OR with two NOR gates and the AND with three. "
            "Both lamps must be correct.",
            ["Do one lamp at a time.",
             "AND needs two inverters and a third NOR."],
            ["A", "B"], [("OR", ("OR", "A", "B"),
                          ("NOR", ("NOR", "A", "B"), ("NOR", "A", "B")),
                          ""),
                         ("AND", ("AND", "A", "B"),
                          ("NOR", ("NOR", "A", "A"), ("NOR", "B", "B")),
                          "")],
            ["NOR"], 5,
            why="NOR alone builds both OR and AND."),
        build(
            "FINAL BOSS: XOR FROM NAND", "BOSS",
            "Build XOR using only four NAND gates. The GOAL column "
            "shows the required output.",
            "Let T = A NAND B. Then XOR = (A NAND T) NAND (B NAND T). "
            "T is shared by both of the last two gates.",
            "Place four NAND gates, wire the shared T gate carefully and "
            "check all rows against GOAL.",
            ["First gate: A NAND B. Call it T.",
             "Gates 2 and 3 each take T and one of A or B."],
            ["A", "B"], [("Y", ("XOR", "A", "B"),
                          ("NAND", ("NAND", "A", ("NAND", "A", "B")),
                           ("NAND", "B", ("NAND", "A", "B"))), "XOR")],
            ["NAND"], 4, show_goal=True,
            why="Four NAND gates reproduce the XOR table: any "
                "function can be built from NAND alone."),
    ],
    card=dict(
        rule="NAND and NOR are UNIVERSAL: every gate can be built from "
             "only one of them.",
        lesson_label="CIRCUIT LESSON",
        lesson="NAND: NOT = A NAND A, AND = NAND then NAND, OR = A' NAND "
               "B'.  NOR: NOT = A NOR A, OR = NOR then NOR, AND = A' NOR "
               "B'.",
        remember="Universal gates make real chips cheap: one repeated "
                 "gate type is easier to make. Next level: Karnaugh "
                 "maps simplify expressions visually.",
        visual=dict(type="circuit", inputs=["A", "B"],
                    outs=[("AND", ("NAND", ("NAND", "A", "B"),
                                   ("NAND", "A", "B")), "")],
                    values={"A": 1, "B": 1},
                    caption="AND built from two NAND gates")),
    notes=["NAND-only: NOT=A NAND A. AND=NAND then NAND. OR=A' NAND B'.",
           "NOR-only: NOT=A NOR A. OR=NOR then NOR. AND=A' NOR B'."],
))

assert len(STAGES) == 10


# ---------------------------------------------------------------------------
# FINAL REVISION SHEET
# ---------------------------------------------------------------------------

REVISION_SHEET = [
    "#1  THE SEVEN GATES AND THEIR EXPRESSIONS",
    "AND  Y = A·B        OR  Y = A + B        NOT  Y = A'",
    "NAND Y = (A·B)'     NOR Y = (A + B)'",
    "XOR  Y = A'B + AB'  XNOR Y = AB + A'B'",
    "#2  TRUTH TABLES  (output for AB = 00 01 10 11)",
    "AND 0001   OR 0111   NAND 1110   NOR 1000   XOR 0110   XNOR 1001",
    "NOT: A=0 gives 1, A=1 gives 0",
    "#3  CHOOSING A GATE FROM THE WORDS",
    "BOTH -> AND (ID AND hall ticket)    EITHER -> OR (fire OR smoke)",
    "NOT -> NOT (door NOT closed)        NOT BOTH -> NAND",
    "NEITHER -> NOR                      EXACTLY ONE -> XOR",
    "SAME / MATCH -> XNOR",
    "#4  ROW COUNTS",
    "n inputs give 2^n rows:  2 inputs = 4 rows,  3 inputs = 8 rows",
    "#5  WIRING RULES",
    "Drag from an OUTPUT pin (right) to an INPUT pin (left).",
    "An input pin takes one wire. One output may feed many pins.",
    "An unconnected input means the circuit is incomplete.",
    "Right-click an input pin to remove its wire.",
    "#6  SUM-OF-PRODUCTS RECIPE",
    "1 Pick each row where Y = 1.   2 Write an AND term per row.",
    "3 Input 1 -> A, input 0 -> A'.  4 OR the terms together.",
    "5 Verify every row against the original table.",
    "XOR example:  Y = A'B + AB'",
    "#7  BASIC LAWS",
    "A·1 = A   A + 0 = A   |   A·0 = 0   A + 1 = 1",
    "A·A = A   A + A = A   |   A·A' = 0  A + A' = 1",
    "(A')' = A   |   A + AB = A   A(A + B) = A",
    "#8  GROUPING LAWS",
    "AB = BA   A + B = B + A        (AB)C = A(BC)   (A+B)+C = A+(B+C)",
    "A(B + C) = AB + AC             A + BC = (A + B)(A + C)",
    "#9  EQUIVALENCE PROOF TEMPLATE",
    "A | B | LEFT | RIGHT | SAME?  - every row must say YES.",
    "One NO row is a counterexample. Three of four rows is not a proof.",
    "#10  WORKED REDUCTIONS",
    "AB + AB' = A(B + B') = A·1 = A",
    "A + A'B = (A + A')(A + B) = 1·(A + B) = A + B",
    "#11  DE MORGAN",
    "(AB)' = A' + B'      (A + B)' = A'B'",
    "Break the bar, change the operator, complement each variable.",
    "#12  NAND-ONLY CONSTRUCTIONS",
    "NOT: A NAND A = A'",
    "AND: (A NAND B) NAND (A NAND B) = AB",
    "OR: (A NAND A) NAND (B NAND B) = A + B",
    "#13  NOR-ONLY CONSTRUCTIONS",
    "NOT: A NOR A = A'",
    "OR: (A NOR B) NOR (A NOR B) = A + B",
    "AND: (A NOR A) NOR (B NOR B) = AB",
    "#14  COMMON EXAM MISTAKES",
    "Confusing XOR with OR (they differ on 11).",
    "Confusing NAND (not both) with NOR (neither).",
    "Forgetting to complement every variable in De Morgan.",
    "Writing A instead of A' in a product term.",
    "Ignoring brackets: A + BC is not (A + B)C.",
    "Declaring two circuits equal after testing only some rows.",
    "#15  GATE-CHOICE GUIDE",
    "Need ALL conditions? AND.        Need AT LEAST ONE? OR.",
    "Need the OPPOSITE? NOT.          Need NOT BOTH? NAND.",
    "Need NONE? NOR.                  Need DIFFERENT? XOR.",
    "Need EQUAL? XNOR.",
]


# ---------------------------------------------------------------------------
# THE PUZZLE
# ---------------------------------------------------------------------------

class BasicCircuitLabPuzzle(BasePuzzle):
    """Basic Level 2: Circuit Lab (ten stages)."""

    NAME = "Basic Level 2: Circuit Lab"
    LETTER_KEYS = {pygame.K_a: "A", pygame.K_b: "B",
                   pygame.K_c: "C", pygame.K_d: "D"}

    def __init__(self, notebook=None):
        try:
            super().__init__()
        except TypeError:
            pass
        self.solved = False
        self.wants_exit = False
        self.notebook = notebook
        self.mode = "ACTIVITY"          # ACTIVITY | CARD | FINAL
        self.stage = 0
        self.act = 0
        self.stage_done = [False] * len(STAGES)
        self.final_scroll = 0
        self._card_bench = {}
        self._scale_cache = {}
        self.btn = {}
        self._load_activity()

    # ---------------------------------------------------------------- setup

    def attach_notebook(self, notebook):
        self.notebook = notebook

    def _load_activity(self):
        a = self.cur = STAGES[self.stage]["acts"][self.act]
        self.hint_level = 0
        self.sel = None
        self.visited = set()
        self.cells = {}
        self.choices = [None] * len(a.get("rows", []))
        self.wrong_cells, self.wrong_rows = set(), set()
        self.act_done = False
        self.locked = bool(a.get("lock"))
        self.msg = ""
        self.msg_col = CYAN
        self.ghost_text = ""
        self.ask_rects, self.cell_rects, self.row_rects = [], [], []
        self.palette_rects = []
        self.bench = None
        self.ask_keys = {}
        kind = a["kind"]

        if kind in ("explore", "table"):
            c = build_circuit(a["inputs"], self._out_defs(),
                              a.get("names"))
            self.bench = LabBench(c, allow_wiring=False, allow_moving=True)
        elif kind == "build":
            outs = a["outs"]
            if a.get("preset") is not None:
                oid, (label, _t, _s, cap) = "Y", outs[0]
                c = build_circuit(a["inputs"],
                                  [(oid, a["preset"], cap, label)],
                                  a.get("names"), deletable=True)
                for fault in a["faults"]:
                    apply_fault(c, fault)
            else:
                c = build_circuit(a["inputs"], self._out_defs(),
                                  a.get("names"), deletable=True)
            self.bench = LabBench(c, allow_wiring=True, allow_placing=True,
                                  allow_moving=True)

        ask = a.get("ask")
        if ask:
            if ask["opts"] == ["0", "1"]:
                keys = [pygame.K_0, pygame.K_1]
            else:
                keys = [pygame.K_1, pygame.K_2, pygame.K_3,
                        pygame.K_4][:len(ask["opts"])]
            self.ask_keys = {k: i for i, k in enumerate(keys)}

        if kind == "explore" and a.get("lock"):
            self._say("Predict first. The switches unlock after you "
                      "answer.", YELLOW)
        elif kind == "build":
            self._say("Place gates from the palette, drag them, then wire "
                      "them.", CYAN)
        self._track()

    def _out_defs(self):
        """[(out_id, expr, caption, label)] - same order build_circuit()
        expects. BUILD activities return expr=None (an unwired lamp)."""
        a = self.cur
        outs = a["outs"]
        if a["kind"] == "build":
            return [("Y" if len(outs) == 1 else f"Y{i + 1}", None, o[3], o[0])
                    for i, o in enumerate(outs)]
        if len(outs) == 1:
            return [("Y", outs[0][1], outs[0][2], outs[0][0])]
        return [(f"Y{i + 1}", o[1], o[2], o[0]) for i, o in enumerate(outs)]

    def _say(self, text, colour=CYAN):
        self.msg, self.msg_col = text, colour

    def _track(self):
        if self.bench and self.cur["inputs"]:
            comps = self.bench.circuit.comps
            self.visited.add(tuple(comps[i].value
                                   for i in self.cur["inputs"]))

    # --------------------------------------------------------------- events

    def handle_event(self, event):
        if self.mode == "ACTIVITY":
            self._ev_activity(event)
        elif self.mode == "CARD":
            self._ev_card(event)
        else:
            self._ev_final(event)

    def _ev_card(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.wants_exit = True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._next_stage()
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and "next" in self.btn
              and self.btn["next"].collidepoint(event.pos)):
            self._next_stage()

    def _next_stage(self):
        self.stage += 1
        if self.stage >= len(STAGES):
            self.stage = len(STAGES) - 1
            self.mode = "FINAL"
            self.final_scroll = 0
            self._save_sheet()
        else:
            self.act = 0
            self.mode = "ACTIVITY"
            self._load_activity()

    def _ev_final(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.wants_exit = True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.solved = True
            elif event.key == pygame.K_UP:
                self.final_scroll = max(0, self.final_scroll - 1)
            elif event.key == pygame.K_DOWN:
                self.final_scroll += 1
            elif event.key == pygame.K_PAGEUP:
                self.final_scroll = max(0, self.final_scroll - 12)
            elif event.key == pygame.K_PAGEDOWN:
                self.final_scroll += 12
        elif event.type == pygame.MOUSEWHEEL:
            self.final_scroll = max(0, self.final_scroll - event.y * 2)
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and "finish" in self.btn
              and self.btn["finish"].collidepoint(event.pos)):
            self.solved = True

    def _ev_activity(self, event):
        a = self.cur
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self.wants_exit = True
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._on_check()
            elif k == pygame.K_h:
                self._on_hint()
            elif self.act_done:
                pass
            elif k in self.ask_keys:
                self._select(self.ask_keys[k])
            elif k in self.LETTER_KEYS and self.bench:
                self._toggle_switch(self.LETTER_KEYS[k])
            self._track()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._ui_click(pos):
                self._track()
                return
            if self.locked and self.bench:
                for comp in self.bench.circuit.comps.values():
                    if (comp.kind == "SWITCH"
                            and self.bench.rect_of(comp).collidepoint(pos)):
                        self._say("Commit your prediction first (click an "
                                  "answer), then test it.", YELLOW)
                        return

        if self.bench and event.type in (
                pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION):
            msg = self.bench.handle_event(event)
            if msg:
                self._say(msg, CYAN)
            self._track()

    def _toggle_switch(self, letter):
        comps = self.bench.circuit.comps
        if letter not in comps or comps[letter].kind != "SWITCH":
            return
        if self.locked:
            self._say("Commit your prediction first, then test it.", YELLOW)
            return
        comps[letter].value ^= 1
        self._say(f"Switch {letter} = {comps[letter].value}", CYAN)

    def _ui_click(self, pos):
        """Handle clicks on buttons / palette / answers. True if used."""
        if "check" in self.btn and self.btn["check"].collidepoint(pos):
            self._on_check()
            return True
        if "hint" in self.btn and self.btn["hint"].collidepoint(pos):
            self._on_hint()
            return True
        if self.act_done:
            return False
        for kind, rect in self.palette_rects:
            if rect.collidepoint(pos):
                msg = self.bench.add_gate(kind, self.cur["max_gates"])
                self._say(msg, CYAN)
                return True
        for i, rect in enumerate(self.ask_rects):
            if rect.collidepoint(pos):
                self._select(i)
                return True
        for key, rect in self.cell_rects:
            if rect.collidepoint(pos):
                self._cycle_cell(key)
                return True
        for i, rect in enumerate(self.row_rects):
            if rect.collidepoint(pos):
                self._cycle_row(i)
                return True
        return False

    def _select(self, idx):
        self.sel = idx
        self.locked = False
        self._say("Answer chosen. Test it with the switches, then press "
                  "CHECK.", CYAN)

    def _cycle_cell(self, key):
        row, col = key
        cur = self.cells.get(key)
        if col == "match":
            self.cells[key] = "Y" if cur != "Y" else "N"
        else:
            self.cells[key] = 0 if cur is None else 1 - cur
        self.wrong_cells.discard(key)

    def _cycle_row(self, i):
        n = len(self.cur["options"])
        cur = self.choices[i]
        self.choices[i] = 0 if cur is None else (cur + 1) % n
        self.wrong_rows.discard(i)

    # ----------------------------------------------------------- checking

    def _on_check(self):
        if self.act_done:
            self._advance()
            return
        k = self.cur["kind"]
        ok, msg = {"explore": self._check_explore,
                   "build": self._check_build,
                   "table": self._check_table,
                   "choose": self._check_choose}[k]()
        if ok:
            self.act_done = True
            self.hint_level = 0
            if self.bench:
                self.bench.ghost = None
            last = self.act + 1 >= len(STAGES[self.stage]["acts"])
            tail = ("Press ENTER to finish the stage." if last
                    else "Press ENTER for the next activity.")
            self._say(f"CORRECT!  {msg}  {tail}", GREEN)
        else:
            self._say(msg, RED)

    def _check_explore(self):
        a = self.cur
        need = 2 ** len(a["inputs"])
        if a.get("need_visit", True) and len(self.visited) < need:
            return False, (f"Test every input row first: "
                           f"{len(self.visited)} of {need} rows tested.")
        ask = a.get("ask")
        if ask:
            if self.sel is None:
                return False, "Choose an answer to the question first."
            if self.sel != ask["answer"]:
                return False, ("Not quite. Toggle the switches again and "
                               "watch the lamps closely.")
            return True, ask.get("why", "") or a.get("why", "")
        return True, a.get("why", "")

    def _check_build(self):
        a = self.cur
        c = self.bench.circuit
        gates = c.count_gates()
        if gates == 0 and a["max_gates"] > 0:
            return False, "Place at least one gate from the palette."
        for comp in c.comps.values():
            if comp.kind in ("LED",) or comp.kind in GNAME:
                for pin in range(comp.n_inputs):
                    if c.source_of(comp.id, pin) is None:
                        name = comp.sub or comp.label or comp.id
                        return False, (f"Incomplete: input {pin + 1} of "
                                       f"{name} is not wired.")
        if gates > a["max_gates"]:
            return False, (f"Too many gates: {gates} used, the limit is "
                           f"{a['max_gates']}.")
        defs = self._out_defs()
        table_rows = c.truth_table_multi(a["inputs"], [d[0] for d in defs])
        for bits, vals in table_rows:
            env = dict(zip(a["inputs"], bits))
            for (oid, _e, _c, label), got, spec in zip(defs, vals, a["outs"]):
                want = ev(spec[1], env)
                if got != want:
                    return False, (f"At {row_text(a['inputs'], bits)} your "
                                   f"{label or 'output'} is {got} but the "
                                   f"requirement needs {want}.")
        return True, (f"Circuit verified on all {len(table_rows)} rows. "
                      + a.get("why", ""))

    def _check_table(self):
        a = self.cur
        defs = self._out_defs()
        rows = rows_of(len(a["inputs"]))
        cols = list(range(len(defs))) + (["match"] if a.get("match") else [])
        total = len(rows) * len(cols)
        filled = sum(1 for r in range(len(rows)) for cl in cols
                     if (r, cl) in self.cells)
        if filled < total:
            return False, (f"Fill every cell first ({filled}/{total}). "
                           "Click a cell to set it.")
        self.wrong_cells = set()
        first = None
        for r, bits in enumerate(rows):
            env = dict(zip(a["inputs"], bits))
            vals = [ev(d[1], env) for d in defs]
            for j, v in enumerate(vals):
                if self.cells[(r, j)] != v:
                    self.wrong_cells.add((r, j))
                    first = first or bits
            if a.get("match"):
                want = "Y" if len(set(vals)) == 1 else "N"
                if self.cells[(r, "match")] != want:
                    self.wrong_cells.add((r, "match"))
                    first = first or bits
        if self.wrong_cells:
            return False, (f"{len(self.wrong_cells)} cell(s) are wrong "
                           f"(outlined in red). First problem at "
                           f"{row_text(a['inputs'], first)}: set the "
                           "switches to that row and read the lamps.")
        return True, a.get("why", "")

    def _check_choose(self):
        a = self.cur
        if any(c is None for c in self.choices):
            left = sum(1 for c in self.choices if c is None)
            return False, f"Choose an option for every line first ({left} left)."
        self.wrong_rows = {i for i, (_t, ans) in enumerate(a["rows"])
                           if self.choices[i] != ans}
        if self.wrong_rows:
            nums = ", ".join(str(i + 1) for i in sorted(self.wrong_rows))
            return False, (f"Line(s) {nums} need another look (outlined in "
                           "red). Press H if you are stuck.")
        return True, a.get("why", "")

    def _advance(self):
        self.act += 1
        if self.act >= len(STAGES[self.stage]["acts"]):
            self.act -= 1
            self.stage_done[self.stage] = True
            self._save_notes(self.stage)
            self.mode = "CARD"
            return
        self._load_activity()

    # --------------------------------------------------------------- hints

    def _on_hint(self):
        if self.act_done:
            return
        self.hint_level = min(3, self.hint_level + 1)

    def _flatten_solution(self, outs):
        """Memoised post-order list of solution gates: (nid, kind, kids)."""
        nodes, memo = [], {}

        def walk(e):
            if isinstance(e, str):
                return e
            if e in memo:
                return memo[e]
            kids = [walk(x) for x in e[1:]]
            nid = f"n{len(nodes)}"
            nodes.append((nid, e[0], kids))
            memo[e] = nid
            return nid

        roots = [walk(o[2]) for o in outs]
        return nodes, roots

    def _ghost_target(self):
        """Next missing connection for a build activity.
        Returns ("wire", src, dst, pin) / ("place", kind) / None."""
        a, c = self.cur, self.bench.circuit
        inputs = a["inputs"]
        nodes, roots = self._flatten_solution(a["outs"])
        mapped, used = {}, set()
        for nid, kind, kids in nodes:
            cands = [g for g in c.comps.values()
                     if g.kind == kind and g.id not in used]
            if not cands:
                return ("place", kind)

            def score(g, kids=kids):
                srcs = [c.source_of(g.id, p) for p in range(g.n_inputs)]
                s = 0
                for kid in kids:
                    want = kid if kid in inputs else mapped.get(kid)
                    if want in srcs:
                        s += 1
                return -s

            g = min(cands, key=score)
            mapped[nid] = g.id
            used.add(g.id)

        for nid, kind, kids in nodes:
            gid = mapped[nid]
            wants = [kid if kid in inputs else mapped[kid] for kid in kids]
            have = [c.source_of(gid, p) for p in range(len(kids))]
            pool, matched = list(wants), set()
            for p, h in enumerate(have):
                if h in pool:
                    pool.remove(h)
                    matched.add(p)
            if pool:
                free = [p for p in range(len(kids)) if p not in matched]
                return ("wire", pool[0], gid, free[0] if free else 0)

        for k, root in enumerate(roots):
            oid = "Y" if len(a["outs"]) == 1 else f"Y{k + 1}"
            want = root if root in inputs else mapped[root]
            if c.source_of(oid, 0) != want:
                return ("wire", want, oid, 0)
        return None

    def _update_ghost(self):
        self.ghost_text = ""
        if self.cur["kind"] != "build" or self.bench is None:
            return
        self.bench.ghost = None
        if self.hint_level < 3 or self.act_done:
            return
        if self.cur["max_gates"] == 0 and self.cur.get("preset") is not None:
            # SHRINK: needs deletion first, then a straight wire A -> lamp
            if self.bench.circuit.count_gates() > 0:
                self.ghost_text = ("Delete the gates first (right-click), "
                                   "then wire A straight to the lamp.")
                return
        target = self._ghost_target()
        if target is None:
            self.ghost_text = "Every wire is in place. Press CHECK."
        elif target[0] == "place":
            self.ghost_text = (f"You still need another gate: "
                               f"{GNAME[target[1]]}. Place it from the palette.")
        else:
            _t, src, dst, pin = target
            self.bench.ghost = (src, dst, pin)
            comps = self.bench.circuit.comps
            nm = lambda cid: (comps[cid].sub or comps[cid].label or cid)
            self.ghost_text = (f"Ghost wire: connect {nm(src)} (output pin) "
                               f"to {nm(dst)} (input pin {pin + 1}).")

    # --------------------------------------------------------------- notes

    def _save_notes(self, si):
        nb = self.notebook
        if nb is None:
            return
        try:
            st = STAGES[si]
            header = f"== STAGE {si + 1}: {st['title']} =="
            lines = [header] + list(st["notes"])
            if hasattr(nb, "add_basic_note"):
                # Full game: feed the shared MY BASIC NOTES revision sheet.
                nb.add_basic_note(f"b{si + 1:02d}", lines)
                return
            topic = nb.reference_notes.setdefault(NOTEBOOK_TOPIC, [])
            if NOTEBOOK_TOPIC not in nb.reference_topics:
                nb.reference_topics.append(NOTEBOOK_TOPIC)
            if header in topic:
                return                      # never overwrite / duplicate
            topic.extend(lines)
        except Exception:                    # never crash the game on notes
            pass

    def _save_sheet(self):
        nb = self.notebook
        if nb is None:
            return
        try:
            lines = [ln.lstrip("#") for ln in REVISION_SHEET]
            if hasattr(nb, "add_basic_note"):
                nb.add_basic_note("b99_revision",
                                  ["== LEVEL 2 REVISION SHEET =="] + lines)
                return
            nb.reference_notes[SHEET_TOPIC] = lines
            if SHEET_TOPIC not in nb.reference_topics:
                nb.reference_topics.append(SHEET_TOPIC)
        except Exception:
            pass

    # ------------------------------------------------------------- drawing

    def draw(self, screen):
        screen.fill(DARK_BLUE)
        lay = Lay(draw_pixel_monitor(screen))
        self.btn = {}
        if self.mode == "ACTIVITY":
            self._draw_activity(screen, lay)
        elif self.mode == "CARD":
            self._draw_card(screen, lay)
        else:
            self._draw_final(screen, lay)
        self._draw_legend(screen, lay)

    def _draw_legend(self, screen, lay):
        txt = ("ENTER = Check your answer | H = Hint | N = Open Notebook | "
               "ESC = Exit the level")
        f = fit_font(txt, lay.W(1330), int(14 * lay.scale) + 1, 10)
        img = f.render(txt, True, GREY)
        screen.blit(img, img.get_rect(midtop=(lay.X(700), lay.Y(849))))

    def _draw_header(self, screen, lay, right_note):
        blink = (pygame.time.get_ticks() // 450) % 2 == 0
        txt = "■ CIRCUITS AND UNDERSTANDING BOOLEAN ALGEBRA // LEVEL TWO"
        f = fit_font(txt, lay.W(1320), int(19 * lay.scale) + 1, 11)
        screen.blit(f.render(txt, True, RED if blink else DIM_RED),
                    (lay.X(35), lay.Y(20)))

        st = STAGES[self.stage]
        title = f"STAGE {self.stage + 1}/{len(STAGES)}: {st['title']}"
        f = fit_font(title, lay.W(900), int(22 * lay.scale) + 1, 12)
        screen.blit(f.render(title, True, CYAN), (lay.X(35), lay.Y(47)))
        f = fit_font(st["sub"], lay.W(900), int(15 * lay.scale) + 1, 10)
        screen.blit(f.render(st["sub"], True, GREY), (lay.X(35), lay.Y(77)))

        r = max(9, int(13 * lay.scale))
        for i in range(len(STAGES)):
            cx, cy = lay.X(995 + i * 38), lay.Y(64)
            done = self.stage_done[i]
            cur = i == self.stage
            if done:
                pygame.draw.circle(screen, GREEN, (cx, cy), r)
            else:
                pygame.draw.circle(screen, PANEL_BLUE, (cx, cy), r)
            pygame.draw.circle(
                screen, CYAN if cur else (GREEN if done else TEAL),
                (cx, cy), r, 3 if cur else 2)
            f = font(max(9, int(12 * lay.scale)))
            img = f.render(str(i + 1), True, INK if done else (
                CYAN if cur else GREY))
            screen.blit(img, img.get_rect(center=(cx, cy)))
        if right_note:
            f = font(max(10, int(13 * lay.scale)))
            img = f.render(right_note, True, GREY)
            screen.blit(img, img.get_rect(topright=(lay.X(1350), lay.Y(86))))
        pygame.draw.line(screen, TEAL, (lay.X(35), lay.Y(108)),
                         (lay.X(1365), lay.Y(108)), 1)

    # ----- activity screen

    def _parts_collide(self, b=None):
        """True if any two parts (with caption room) overlap or leave the
        bench. Used to pick the biggest part size that fits."""
        b = b or self.bench
        area = b.area
        rects = []
        for comp in b.circuit.comps.values():
            r = b.rect_of(comp)
            cap = 16 if (comp.sub or comp.kind == "LED") else 0
            full = pygame.Rect(r.x - 4, r.y, r.w + 8, r.h + cap)
            if (r.x < area.x or r.right > area.right or r.y < area.y
                    or r.bottom + cap > area.bottom):
                return True
            rects.append(full)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                p, q = rects[i], rects[j]
                if (p.x < q.right and q.x < p.right
                        and p.y < q.bottom and q.y < p.bottom):
                    return True
        return False

    def _apply_scale(self, lay, bench=None, tag="act"):
        """Largest part size (down to 0.4) at which the starting layout has
        no overlaps. Computed once per activity and window size."""
        bench = bench or self.bench
        base = 0.72 * max(0.85, min(1.15, lay.scale))
        c = bench.circuit
        key = (tag, self.stage, self.act, bench.area.w, bench.area.h)
        if key not in self._scale_cache:
            size, stripped = base, False
            while True:
                c.size_scale = size
                if not self._parts_collide(bench):
                    break
                if size <= 0.4:
                    if tag == "card" and not stripped:
                        # last resort on the small stage-card diagrams only:
                        # drop the gate captions so everything fits
                        for comp in c.comps.values():
                            if comp.kind in GNAME:
                                comp.sub = ""
                        stripped, size = True, base
                        continue
                    break
                size -= 0.03
            self._scale_cache[key] = size
        size = self._scale_cache[key]
        c.size_scale = size
        c.font_scale = 0.8 * size / 0.72

    def _draw_activity(self, screen, lay):
        a = self.cur
        st = STAGES[self.stage]
        self._draw_header(screen, lay,
                          f"Activity {self.act + 1} of {len(st['acts'])}")
        self._update_ghost()
        R = lay.R
        left, right = R(35, 118, 880, 654), R(930, 118, 435, 654)
        panel(screen, left)
        panel(screen, right)

        # left: title + story
        head = f"{a['tag']}:  {a['title']}"
        screen.blit(fit_font(head, left.w - 24, int(15 * lay.scale) + 1, 10)
                    .render(head, True, YELLOW), (lay.X(47), lay.Y(124)))
        fit_text(screen, a["story"], R(47, 146, 856, 34), WHITE,
                 int(14 * lay.scale) + 1, 10)

        kind = a["kind"]
        if kind == "choose":
            self._draw_choose(screen, lay)
        else:
            top = 186
            if kind == "build":
                self._draw_palette(screen, lay, R(47, 186, 856, 34))
                top = 224
            self.bench.area = R(47, top, 560, 690 - top)
            self._apply_scale(lay)
            self.bench.draw(screen)
            self._draw_table(screen, lay, R(617, 186, 286, 504))
            if a.get("ask"):
                self._draw_ask(screen, lay, R(47, 696, 856, 44))
            else:
                self.ask_rects = []

        # status line
        fit_text(screen, self.msg, R(47, 742, 856, 28), self.msg_col,
                 int(14 * lay.scale) + 1, 10)

        self._draw_right_panel(screen, lay, a)
        self._draw_bottom_buttons(screen, lay)

    def _draw_right_panel(self, screen, lay, a):
        R = lay.R
        h = lambda t, col, y: screen.blit(
            font(max(11, int(16 * lay.scale))).render(t, True, col),
            (lay.X(944), lay.Y(y)))
        h("BRIEFING", CYAN, 126)
        fit_text(screen, a["brief"], R(944, 150, 411, 148), WHITE,
                 int(14 * lay.scale) + 1, 10)
        h("YOUR TASK", GREEN, 304)
        fit_text(screen, a["task"], R(944, 328, 411, 120), WHITE,
                 int(14 * lay.scale) + 1, 10)

        box = R(944, 458, 411, 302)
        pygame.draw.rect(screen, PANEL_BLUE, box, border_radius=6)
        pygame.draw.rect(screen, ORANGE, box, 3, border_radius=6)
        lvl = self.hint_level
        title = f"HINT  (level {lvl}/3)" if lvl else "HINT"
        screen.blit(font(max(11, int(16 * lay.scale))).render(
            title, True, ORANGE), (box.x + 12, box.y + 8))
        if lvl == 0:
            text, col = ("Stuck? Press H or click HINT. Press it again "
                         "for a stronger hint.", GREY)
        else:
            text, col = a["hints"][lvl - 1], WHITE
        body = pygame.Rect(box.x + 12, box.y + 34, box.w - 24, box.h - 120)
        fit_text(screen, text, body, col, int(14 * lay.scale) + 1, 10)
        if self.ghost_text:
            fit_text(screen, self.ghost_text,
                     pygame.Rect(box.x + 12, box.bottom - 82, box.w - 24, 36),
                     YELLOW, int(13 * lay.scale) + 1, 10)
        key = ("WIRES: A cyan  B orange  C purple  D pink  "
               "gate outputs green/yellow/blue/coral")
        if a["kind"] in ("build", "explore", "table"):
            fit_text(screen, key,
                     pygame.Rect(box.x + 12, box.bottom - 40, box.w - 24, 34),
                     GREY, int(11 * lay.scale) + 1, 9)

    def _draw_bottom_buttons(self, screen, lay):
        R = lay.R
        mouse = pygame.mouse.get_pos()
        tip = ("Click a switch to flip it (or press A-D). Drag parts to "
               "move them." if self.cur["kind"] in ("explore", "table")
               else "Right-click a gate to delete it. Right-click an input "
                    "pin to remove a wire."
               if self.cur["kind"] == "build"
               else "Click a line to cycle its options.")
        fit_text(screen, tip, R(35, 792, 1030, 28), GREY,
                 int(13 * lay.scale) + 1, 10)
        chk = R(1085, 782, 135, 40)
        hnt = R(1230, 782, 135, 40)
        self.btn["check"], self.btn["hint"] = chk, hnt
        button(screen, chk, "NEXT" if self.act_done else "CHECK",
               GREEN if self.act_done else CYAN, chk.collidepoint(mouse),
               int(16 * lay.scale) + 1)
        button(screen, hnt, "HINT", ORANGE, hnt.collidepoint(mouse),
               int(16 * lay.scale) + 1)

    # ----- palette / ask / table / choose widgets

    def _draw_palette(self, screen, lay, rect):
        a = self.cur
        panel(screen, rect, fill=(7, 18, 30), width=1, radius=6)
        f = font(max(10, int(12 * lay.scale)))
        screen.blit(f.render("GATE PALETTE:", True, GREY),
                    (rect.x + 10, rect.centery - f.get_linesize() // 2))
        self.palette_rects = []
        x = rect.x + lay.W(130)
        bw, gap = lay.W(72), lay.W(6)
        mouse = pygame.mouse.get_pos()
        for kind in a["palette"]:
            r = pygame.Rect(x, rect.y + 4, bw, rect.h - 8)
            self.palette_rects.append((kind, r))
            hov = r.collidepoint(mouse)
            pygame.draw.rect(screen, (20, 48, 68) if hov else (12, 28, 42),
                             r, border_radius=4)
            pygame.draw.rect(screen, CYAN if hov else CYAN_DIM, r, 1,
                             border_radius=4)
            img = fit_font(kind, r.w - 6, 13, 9).render(
                kind, True, WHITE if hov else GREY)
            screen.blit(img, img.get_rect(center=r.center))
            x += bw + gap
        used = self.bench.circuit.count_gates()
        txt = f"|  GATES: {used}/{a['max_gates']}"
        col = RED if used > a["max_gates"] else (GREEN if used else GREY)
        fnt = fit_font(txt, max(40, rect.right - x - 6), 13, 9)
        screen.blit(fnt.render(txt, True, col),
                    (x + 4, rect.centery - fnt.get_linesize() // 2))

    def _draw_ask(self, screen, lay, rect):
        ask = self.cur["ask"]
        fit_text(screen, ask["q"], pygame.Rect(rect.x, rect.y, rect.w, 18),
                 YELLOW, int(14 * lay.scale) + 1, 10)
        n = len(ask["opts"])
        gap = lay.W(10)
        bw = min(lay.W(210), (rect.w - gap * (n - 1)) // n)
        mouse = pygame.mouse.get_pos()
        self.ask_rects = []
        binary = ask["opts"] == ["0", "1"]
        for i, text in enumerate(ask["opts"]):
            r = pygame.Rect(rect.x + i * (bw + gap), rect.y + 22, bw, 22)
            self.ask_rects.append(r)
            chosen = self.sel == i
            col = GREEN if (chosen and self.act_done) else (
                CYAN if chosen else CYAN_DIM)
            pygame.draw.rect(screen, (16, 56, 74) if chosen else PANEL_BLUE,
                             r, border_radius=4)
            pygame.draw.rect(screen, WHITE if r.collidepoint(mouse) else col,
                             r, 3 if chosen else 1, border_radius=4)
            label = text if binary else f"[{i + 1}] {text}"
            img = fit_font(label, r.w - 8, 13, 9).render(
                label, True, WHITE if chosen else GREY)
            screen.blit(img, img.get_rect(center=r.center))

    def _draw_table(self, screen, lay, rect):
        a = self.cur
        c = self.bench.circuit
        kind = a["kind"]
        editable = kind == "table"
        defs = self._out_defs()
        inputs = a["inputs"]
        rows = rows_of(len(inputs))
        cols = [(l, "in", l) for l in inputs]
        cols += [(d[3] or "Y", "out", j) for j, d in enumerate(defs)]
        if editable and a.get("match"):
            cols.append(("SAME?", "match", "match"))
        if kind == "build" and a.get("show_goal"):
            cols.append(("GOAL", "goal", 0))

        panel(screen, rect, fill=(7, 18, 30), width=1, radius=6)
        title = "FILL THE TRUTH TABLE" if editable else "LIVE TRUTH TABLE"
        screen.blit(fit_font(title, rect.w - 16, 13, 9).render(
            title, True, CYAN), (rect.x + 8, rect.y + 6))

        live = None
        if not editable:
            live = c.truth_table_multi(inputs, [d[0] for d in defs])
        cur = tuple(c.comps[i].value for i in inputs)
        weights = [0.55 if c[1] == "in" else 1.0 for c in cols]
        total_w = sum(weights)
        ws = [int(rect.w * w / total_w) for w in weights]
        xs = [rect.x + sum(ws[:i]) for i in range(len(ws))]
        rh = max(14, min(30, (rect.h - 44) // (len(rows) + 1)))
        fs = 13 if rh >= 22 else 11
        fcell = fit_font("WWW", min(ws) - 4, fs, 8)
        y0 = rect.y + 28
        self.cell_rects = []

        for ci, (label, role, _k) in enumerate(cols):
            r = pygame.Rect(xs[ci], y0, ws[ci], rh)
            pygame.draw.rect(screen, ROW_LINE, r, 1)
            img = fit_font(label, ws[ci] - 4, fs, 8).render(label, True, ORANGE)
            screen.blit(img, img.get_rect(center=r.center))

        for ri, bits in enumerate(rows):
            env = dict(zip(inputs, bits))
            hot = bits == cur
            for ci, (label, role, k) in enumerate(cols):
                r = pygame.Rect(xs[ci], y0 + (ri + 1) * rh, ws[ci], rh)
                pygame.draw.rect(screen, ROW_ON if hot else (7, 18, 30), r)
                pygame.draw.rect(screen, CYAN if hot else ROW_LINE, r,
                                 2 if hot else 1)
                text, col = "", WHITE
                if role == "in":
                    text = str(bits[inputs.index(k)])
                elif role == "out":
                    if editable:
                        v = self.cells.get((ri, k))
                        text = "?" if v is None else str(v)
                        col = GREY if v is None else CYAN
                        self.cell_rects.append(((ri, k), r))
                    else:
                        v = live[ri][1][k]
                        text = "—" if v is None else str(v)
                        col = GREY if v is None else (
                            GREEN if v else WHITE)
                elif role == "match":
                    v = self.cells.get((ri, "match"))
                    text = "?" if v is None else ("YES" if v == "Y"
                                                  else "NO")
                    col = GREY if v is None else CYAN
                    self.cell_rects.append(((ri, "match"), r))
                elif role == "goal":
                    text = str(ev(a["outs"][0][1], env))
                    col = ORANGE
                img = fcell.render(text, True, col)
                screen.blit(img, img.get_rect(center=r.center))
                if (ri, k if role in ("out", "match") else None) \
                        in self.wrong_cells:
                    pygame.draw.rect(screen, RED, r, 3)

    def _draw_choose(self, screen, lay):
        a = self.cur
        R = lay.R
        area = R(47, 190, 856, 540)
        n = len(a["rows"])
        rh = min(lay.H(78), area.h // max(1, n))
        mouse = pygame.mouse.get_pos()
        self.row_rects = []
        for i, (text, _ans) in enumerate(a["rows"]):
            y = area.y + i * rh
            line = pygame.Rect(area.x, y + 4, area.w, rh - 8)
            panel(screen, line, fill=(7, 18, 30),
                  border=RED if i in self.wrong_rows else ROW_LINE,
                  width=3 if i in self.wrong_rows else 1, radius=6)
            num = font(max(11, int(15 * lay.scale))).render(
                f"{i + 1}.", True, ORANGE)
            screen.blit(num, (line.x + 10, line.centery - num.get_height() // 2))
            fit_text(screen, text,
                     pygame.Rect(line.x + 44, line.y + 6, int(line.w * 0.55),
                                 line.h - 12), WHITE,
                     int(15 * lay.scale) + 1, 10)
            br = pygame.Rect(line.right - lay.W(290), line.y + 8,
                             lay.W(278), line.h - 16)
            self.row_rects.append(br)
            sel = self.choices[i]
            label = "CLICK TO CHOOSE" if sel is None else a["options"][sel]
            ok = self.act_done
            button(screen, br, label,
                   GREEN if ok else (CYAN if sel is not None else GREY),
                   br.collidepoint(mouse), int(15 * lay.scale) + 1)

    # ----- stage complete card

    def _card_circuit(self, spec):
        key = self.stage
        if key not in self._card_bench:
            outs = [(f"Y{i + 1}" if len(spec["outs"]) > 1 else "Y",
                     o[1], o[2], o[0]) for i, o in enumerate(spec["outs"])]
            c = build_circuit(spec["inputs"], outs)
            for letter, v in spec.get("values", {}).items():
                c.comps[letter].value = v
            self._card_bench[key] = LabBench(c, allow_wiring=False)
        return self._card_bench[key]

    def _draw_card(self, screen, lay):
        st = STAGES[self.stage]
        card = st["card"]
        R = lay.R
        self._draw_header(screen, lay, "")
        box = R(35, 118, 1330, 654)
        pygame.draw.rect(screen, PANEL_BLUE, box, border_radius=10)
        pygame.draw.rect(screen, GREEN, box, 3, border_radius=10)

        f = fit_font(f"STAGE {self.stage + 1} COMPLETE", lay.W(700),
                     int(40 * lay.scale) + 2, 16)
        screen.blit(f.render(f"STAGE {self.stage + 1} COMPLETE", True, GREEN),
                    (lay.X(60), lay.Y(130)))
        sub = f"{st['title']}  -  {st['sub']}"
        screen.blit(fit_font(sub, lay.W(1240), int(18 * lay.scale) + 1, 11)
                    .render(sub, True, WHITE), (lay.X(60), lay.Y(184)))

        vis = card["visual"]
        vr = R(60, 222, 560, 450)
        panel(screen, vr, fill=(7, 18, 30), border=ROW_LINE, width=1)
        if vis["type"] == "gatetable":
            self._visual_gates(screen, lay, vr)
        elif vis["type"] == "circuit":
            bench = self._card_circuit(vis)
            bench.area = pygame.Rect(vr.x + 4, vr.y + 4, vr.w - 8,
                                     vr.h - 56)
            self._apply_scale(lay, bench, tag="card")
            bench.draw(screen)
            fit_text(screen, vis.get("caption", ""),
                     pygame.Rect(vr.x + 12, vr.bottom - 46, vr.w - 24, 40),
                     YELLOW, int(15 * lay.scale) + 1, 10)
        else:
            self._visual_lines(screen, lay, vr, vis)

        sections = [("RULE", CYAN, card["rule"]),
                    (card["lesson_label"], GREEN, card["lesson"]),
                    ("REMEMBER", ORANGE, card["remember"])]
        y = 222
        for head, col, text in sections:
            screen.blit(font(max(12, int(17 * lay.scale))).render(
                head, True, col), (lay.X(650), lay.Y(y)))
            fit_text(screen, text, R(650, y + 26, 690, 100), WHITE,
                     int(15 * lay.scale) + 1, 10)
            y += 148

        saved = (f"Saved to NOTEBOOK [N] > TEST THE LOGIC > "
                 f"{NOTEBOOK_TOPIC}")
        fit_text(screen, saved, R(60, 724, 860, 30), ORANGE,
                 int(15 * lay.scale) + 1, 10)
        nb = R(1085, 716, 255, 44)
        self.btn["next"] = nb
        label = ("NEXT STAGE [ENTER]" if self.stage + 1 < len(STAGES)
                 else "FINISH [ENTER]")
        button(screen, nb, label, GREEN, nb.collidepoint(pygame.mouse.get_pos()),
               int(16 * lay.scale) + 1)

    def _visual_gates(self, screen, lay, rect):
        screen.blit(font(max(11, int(14 * lay.scale))).render(
            "GATE        Y  (00 01 10 11)", True, ORANGE),
            (rect.x + 14, rect.y + 8))
        rh = (rect.h - 36) // 7
        for i, g in enumerate(["NOT", "AND", "OR", "XOR", "NAND", "NOR",
                               "XNOR"]):
            y = rect.y + 34 + i * rh
            sym = pygame.Rect(rect.x + 12, y + 2, lay.W(96), rh - 6)
            draw_pixel_gate_symbol(screen, g, sym, CYAN)
            if g == "NOT":
                pat = "1 0"
            else:
                pat = " ".join(str(ev((g, "A", "B"), {"A": a, "B": b}))
                               for a, b in rows_of(2))
            f = font(max(12, int(17 * lay.scale)))
            screen.blit(f.render(g, True, WHITE),
                        (rect.x + lay.W(122), y + rh // 2 - 10))
            screen.blit(f.render(pat, True, GREEN),
                        (rect.x + lay.W(250), y + rh // 2 - 10))

    def _visual_lines(self, screen, lay, rect, vis):
        screen.blit(font(max(11, int(15 * lay.scale))).render(
            vis["title"], True, ORANGE), (rect.x + 14, rect.y + 10))
        n = max(1, len(vis["lines"]))
        lh = min(lay.H(44), (rect.h - 50) // n)
        for i, ln in enumerate(vis["lines"]):
            f = fit_font(ln, rect.w - 28, int(17 * lay.scale) + 1, 9)
            screen.blit(f.render(ln, True, WHITE),
                        (rect.x + 14, rect.y + 44 + i * lh))

    # ----- final revision sheet

    def _draw_final(self, screen, lay):
        R = lay.R
        self._draw_header(screen, lay, "")
        box = R(35, 118, 1330, 654)
        pygame.draw.rect(screen, PANEL_BLUE, box, border_radius=10)
        pygame.draw.rect(screen, GREEN, box, 3, border_radius=10)
        t = "LEVEL TWO COMPLETE: CIRCUIT LAB REVISION SHEET"
        screen.blit(fit_font(t, lay.W(1240), int(30 * lay.scale) + 2, 14)
                    .render(t, True, GREEN), (lay.X(60), lay.Y(130)))
        fit_text(screen, "All ten stages are saved in your notebook. Scroll "
                 "with UP / DOWN or the mouse wheel.",
                 R(60, 176, 1240, 24), GREY, int(14 * lay.scale) + 1, 10)

        area = R(60, 210, 1240, 480)
        panel(screen, area, fill=(7, 18, 30), border=ROW_LINE, width=1)
        f = font(max(11, int(15 * lay.scale)))
        lh = f.get_linesize() + 5
        visible = max(1, (area.h - 16) // lh)
        self.final_scroll = min(self.final_scroll,
                                max(0, len(REVISION_SHEET) - visible))
        old = screen.get_clip()
        screen.set_clip(area)
        y = area.y + 8
        for ln in REVISION_SHEET[self.final_scroll:]:
            if y + lh > area.bottom:
                break
            head = ln.startswith("#")
            screen.blit(f.render(ln.lstrip("#"), True,
                                 CYAN if head else WHITE),
                        (area.x + 14, y))
            y += lh
        screen.set_clip(old)
        if len(REVISION_SHEET) > visible:
            frac = self.final_scroll / max(1, len(REVISION_SHEET) - visible)
            th = max(24, int(area.h * visible / len(REVISION_SHEET)))
            ty = area.y + int((area.h - th) * frac)
            pygame.draw.rect(screen, CYAN_DIM, (area.right - 8, ty, 5, th))

        fb = R(1085, 716, 255, 44)
        self.btn["finish"] = fb
        button(screen, fb, "FINISH LEVEL [ENTER]", GREEN,
               fb.collidepoint(pygame.mouse.get_pos()),
               int(16 * lay.scale) + 1)
        fit_text(screen, f"Saved to NOTEBOOK [N] > TEST THE LOGIC > "
                 f"{SHEET_TOPIC}", R(60, 724, 860, 30), ORANGE,
                 int(15 * lay.scale) + 1, 10)


PUZZLE_CLASS = BasicCircuitLabPuzzle