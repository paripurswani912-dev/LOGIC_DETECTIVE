# notebook.py
# Logic Detective — NEXUS-9 Investigation Notebook
#
# Controls:
#   N                 Open / close notebook (game loops must forward N)
#   UP / DOWN         Select a notebook button
#   ENTER             Open selected page
#   ESC / BACKSPACE   Return to index / close notebook
#   Mouse click       Select buttons and open pages
#   H                 (on a level page) reveal the next hint
#   P                 (on a level page) open the matching practice lab
#
# STATE MACHINES lab keys:
#   A B C             press that button        1-4  pick a state (PREDICT)
#   R                 reset                    P    PREDICT mode
#   V                 diagram <-> circuit      T    lab <-> notes
#   UP / DOWN / WHEEL scroll the lab           ESC / BACKSPACE  go back
#
# Integration:
#   notebook = DetectiveNotebook()
#   notebook.handle_event(event)
#   notebook.draw(screen)
#   notebook.complete_level(level_id, notes)

import itertools
import math
import random
import pygame

from puzzles.comb_lab import CombLab, notes_lines as _comb_notes_lines

# The Boolean Algebra lab reuses the circuit simulator + mouse workbench.
try:
    from puzzles.circuit_engine import Circuit, Component, Workbench
except ImportError:
    from circuit_engine import Circuit, Component, Workbench


# ------------------------------------------------------------
# COLOURS
# ------------------------------------------------------------

BLACK = (0, 0, 0)
INK = (35, 29, 31)
PAPER = (190, 194, 198)
PAPER_LIGHT = (215, 217, 218)
PAPER_SHADOW = (57, 44, 43)
SPIRAL_DARK = (65, 47, 43)
SPIRAL_LIGHT = (226, 220, 203)
MUTED = (105, 111, 119)
CYAN = (0, 210, 224)
DARK_GREEN = (30, 92, 58)
MAROON = (112, 35, 48)
GOLD = DARK_GREEN
WHITE = (242, 241, 231)
LOCKED = (99, 103, 111)
PAGE_LINE = (156, 163, 168)
TEAL = (0, 91, 103)


# ------------------------------------------------------------
# BASIC MODE TEXT (Level One for players new to digital electronics)
# ------------------------------------------------------------

BASIC_LEVEL_ONE_NOTES = [
    "Lab log: Entry 01 (beginner copy)",
    "Everything in this lab is built from switches. A switch is either ON (1) or OFF (0). That is all a computer really knows.",
    "A LOGIC GATE looks at switches and decides if its bulb is ON or OFF. NOT flips it. AND wants both ON. OR wants at least one ON. XOR wants them different.",
    "Work through the 8 stages on the lock terminal. Every rule you learn is copied for you into TEST THE LOGIC > MY BASIC NOTES.",
    "Stuck? Press H on the terminal. Press it again for a stronger hint, and a third time for the answer.",
]

BASIC_LEVEL_ONE_GOAL = (
    "Learn what 0 and 1 mean, then learn the gates NOT, AND, OR and XOR well "
    "enough to fix the lock."
)

BASIC_LEVEL_ONE_HINTS = [
    "Start with the bulbs. A glowing bulb is 1 (ON). A dark bulb is 0 (OFF). Everything else is built on that.",
    "Each gate has a one-line rule. AND: both ON. OR: at least one ON. XOR: inputs different. NOT: flips the input.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_ONE_FINDINGS = [
    "I learned that 0 means OFF and 1 means ON, and how NOT, AND, OR, XOR, NAND and NOR behave.",
    "Recorded answer: AND truth table output 0001 (for inputs 00, 01, 10, 11).",
]


BASIC_LEVEL_TWO_NOTES = [
    "Lab log: Entry 02 (beginner copy)",
    "The transmission relay is a CIRCUIT: gates joined by wires, so the output of one gate becomes the input of the next. Level One taught you the single gates. Now you build with them.",
    "A BOOLEAN EXPRESSION is a circuit written as maths. AND is A.B, OR is A + B, NOT is A'. Brackets work first, just like in school algebra: A + BC is NOT the same as (A + B)C.",
    "To build a circuit from a TRUTH TABLE: pick the rows where the output is 1, write one AND term for each row, then OR the terms together. That is called SOP (sum of products).",
    "BOOLEAN LAWS let you make a circuit smaller without changing its answer, e.g. AB + AB' = A. DE MORGAN'S LAWS: (AB)' = A' + B' and (A + B)' = A'B'. Break the bar, swap the operator.",
    "Two circuits are EQUIVALENT only if they give the same output on EVERY input row. NAND and NOR are UNIVERSAL: either one alone can build any other gate.",
    "Work through the 10 stages on the Circuit Lab terminal. Each finished stage is copied for you into TEST THE LOGIC > MY BASIC NOTES. Stuck? Press H on the terminal for a hint.",
]

BASIC_LEVEL_TWO_GOAL = (
    "Learn to join gates into circuits, turn truth tables into circuits, and use "
    "Boolean algebra to simplify and prove circuits equal."
)

BASIC_LEVEL_TWO_HINTS = [
    "Wires carry 1 or 0. When two gates are joined, work out the inner gate first, then feed its answer into the next gate.",
    "Turning a truth table into a circuit: look only at the rows where the output is 1. Each one becomes an AND term. Join the terms with OR.",
    "Simplifying: look for AB + AB' (that is A), A + A' (that is 1) and A.A' (that is 0). To prove two circuits equal, check every input row, not just some.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_TWO_FINDINGS = [
    "I learned how to read, build and simplify circuits, how De Morgan's laws work, and how NAND or NOR alone can build every gate.",
    "Recorded answer: truth tables (inputs 00, 01, 10, 11): AND 0001, OR 0111, NAND 1110, NOR 1000, XOR 0110, XNOR 1001.",
]


BASIC_LEVEL_FOUR_NOTES = [
    "Lab log: Entry 04 (beginner copy)",
    "The override formula is long and messy. A KARNAUGH MAP (K-map) shrinks it with a picture instead of algebra.",
    "A K-map is a truth table drawn as a grid. Its rows and columns use GRAY CODE (00, 01, 11, 10) so that touching cells differ in only ONE variable. Two touching 1s merge and that variable disappears.",
    "Draw LOOPS round neighbouring 1s: a rectangle of 1, 2, 4 or 8 cells, as big as possible. The map wraps round its edges, so the four corners are one loop.",
    "Read each loop as a short term. Add the terms for SOP, or loop the 0s and multiply sums for POS. X cells (don't cares) can help make loops bigger. Your notes are saved in MY BASIC NOTES.",
]

BASIC_LEVEL_FOUR_GOAL = (
    "Learn to group neighbouring cells on a Karnaugh map and read the loops "
    "as a short SOP or POS formula."
)

BASIC_LEVEL_FOUR_HINTS = [
    "Touching cells on a K-map differ in only one variable, so two touching 1s merge into a shorter term.",
    "A loop must hold 1, 2, 4 or 8 cells, form a rectangle (edges wrap round), and hold only 1s or X's. Make loops as big as you can.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_FOUR_FINDINGS = [
    "I learned the grouping rules for Karnaugh maps and how to read loops as SOP and POS terms.",
    "Recorded answer: 7-segment segment e = B'D' + CD' (using the don't-care cells 10 to 15).",
]

BASIC_LEVEL_FIVE_NOTES = [
    "Lab log: Entry 05 (beginner copy)",
    "The alarm is built from circuits that decide straight from their inputs, with no memory. They are called COMBINATIONAL circuits: adders, subtractors, parity checkers, decoders and multiplexers.",
    "To add two bits you need a SUM and a CARRY (1 + 1 = 10 in binary). Chain full adders to add whole numbers. One XOR gate on the second number turns the adder into a subtractor.",
    "A DECODER turns a code into ONE chosen wire. A MULTIPLEXER (MUX) is a selector: many inputs in, one chosen output. A PARITY bit lets a receiver notice a damaged bit.",
    "Each finished stage is saved in MY BASIC NOTES. Replay any circuit in TEST THE LOGIC > COMBINATIONAL CIRCUITS.",
]

BASIC_LEVEL_FIVE_GOAL = (
    "Understand what adders, subtractors, parity circuits, decoders and multiplexers "
    "are for, and build each one from its truth table."
)

BASIC_LEVEL_FIVE_HINTS = [
    "Every circuit here has NO memory: change the inputs and the output changes at once.",
    "Adders and subtractors use XOR for the Sum or Diff. A decoder lights one output per input code. A MUX copies the one input chosen by its select lines.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_FIVE_FINDINGS = [
    "I learned how adders, subtractors, parity generators, decoders and multiplexers are built from gates.",
    "Recorded answer: full adder Sum = Sum m(1, 2, 4, 7) and Cout = Sum m(3, 5, 6, 7).",
]


BASIC_LEVEL_SIX_NOTES = [
    "Lab log: Entry 06 (beginner copy)",
    "The last terminal scrambles a signal over time. To fix it you need circuits that REMEMBER. A FLIP-FLOP stores one bit and updates only at the clock pulse.",
    "Put flip-flops in a row and you get a SHIFT REGISTER: bits move one place at every pulse. Make them toggle and you get a COUNTER that counts pulses in binary.",
    "A TIMING DIAGRAM draws the clock and every signal against time. Inputs change before the rising edge, and the output changes AT the edge.",
    "Ripple counters pass the clock along and are slow. Synchronous counters give every flip-flop the same clock. Your notes are saved in MY BASIC NOTES.",
]

BASIC_LEVEL_SIX_GOAL = (
    "Learn how flip-flops remember a bit, then use them to read timing diagrams "
    "and to build shift registers and counters."
)

BASIC_LEVEL_SIX_HINTS = [
    "A flip-flop stores one bit and only changes at the rising edge of the clock. Between edges it holds its value.",
    "A shift register moves every bit one place per pulse, so n bits need n pulses to cross. A counter is a row of T flip-flops that toggle.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_SIX_FINDINGS = [
    "I learned how SR, D, T and JK flip-flops work, and how shift registers and counters are built from them.",
    "Recorded answer: a synchronous 3-bit counter has T0 = 1, T1 = Q0 and T2 = Q0 AND Q1.",
]


BASIC_LEVEL_THREE_NOTES = [
    "Lab log: Entry 03 (beginner copy)",
    "The memory vault stores its codes as numbers, but not the ones you count with. Computers use only two digits, so you must switch between BINARY, OCTAL, DECIMAL and HEXADECIMAL.",
    "Place values are powers of the base. Decimal to binary: subtract powers of two, or divide by 2 and read the remainders from the bottom up. Group bits in 3s for octal and 4s for hex.",
    "Negative numbers use a SIGN BIT. 2's complement (flip every bit, add 1) lets one adder add and subtract. A result outside the range is OVERFLOW.",
    "Other codes: BCD (each digit as 4 bits), EXCESS-3 and GRAY code (one bit changes per step). Every stage and the exam revision sheet are saved in MY BASIC NOTES.",
]

BASIC_LEVEL_THREE_GOAL = (
    "Convert between binary, octal, decimal and hex, write negative numbers in 2's complement, "
    "add and subtract in binary, and use BCD, excess-3 and Gray code."
)

BASIC_LEVEL_THREE_HINTS = [
    "Every number system works the same way: place value = base to the power of the position.",
    "Decimal to binary: divide by 2 and read the remainders bottom to top. Negative numbers: flip the bits and add 1.",
    "Stuck on a stage? Press H on the terminal. First press = a nudge, second = a stronger hint, third = the answer.",
]

BASIC_LEVEL_THREE_FINDINGS = [
    "I learned how to convert between number systems and how signed numbers, BCD, excess-3 and Gray code work.",
    "Recorded answer: -75 in 8-bit 2's complement is 10110101.",
]


# ------------------------------------------------------------
# SEQUENTIAL LABS (FLIP-FLOPS / SHIFT REGISTERS / COUNTERS)
# ------------------------------------------------------------
INK_ = INK
WIRE = (55, 125, 151)
LIT = (40, 205, 130)
DARK = (7, 27, 39)
PANEL = (198, 202, 205)
AMBER = (214, 140, 20)
OFF_LAMP = (48, 42, 43)
HILITE = (185, 224, 226)


def _fmt(v):
    return "?" if v is None else str(v)


def _arrow(screen, color, x0, x1, y, width=3):
    pygame.draw.line(screen, color, (x0, y), (x1 - 6, y), width)
    pygame.draw.polygon(screen, color, [(x1, y), (x1 - 8, y - 5), (x1 - 8, y + 5)])


def _varrow(screen, color, x, y0, y1, width=3):
    pygame.draw.line(screen, color, (x, y0), (x, y1 - 6), width)
    pygame.draw.polygon(screen, color, [(x, y1), (x - 5, y1 - 8), (x + 5, y1 - 8)])


def _level_y(row_y, row_h, v):
    hi, lo = row_y + 3, row_y + row_h - 4
    if v is None:
        return (hi + lo) // 2
    return hi if v else lo


def _wave(screen, x0, row_y, row_h, step_w, values, color):
    pts = []
    for k, v in enumerate(values):
        y = _level_y(row_y, row_h, v)
        pts += [(x0 + k * step_w, y), (x0 + (k + 1) * step_w, y)]
    if len(pts) >= 2:
        pygame.draw.lines(screen, color, False, pts, 2)


def _clock_wave(screen, x0, row_y, row_h, step_w, first_pulse, columns, color):
    hi, lo = row_y + 3, row_y + row_h - 4
    pts = []
    for k in range(columns):
        xs = x0 + k * step_w
        xm = xs + step_w // 2
        xe = xs + step_w
        if first_pulse + k == 0:              # before the first pulse
            pts += [(xs, lo), (xe, lo)]
        else:                                 # rising edge at column start
            pts += [(xs, lo), (xs, hi), (xm, hi), (xm, lo), (xe, lo)]
    if len(pts) >= 2:
        pygame.draw.lines(screen, color, False, pts, 2)


def _timing_frame(screen, ui, content, top, n_rows, row_h, columns,
                  first_index, max_cols=12, label_w=60):
    """Draw the grey frame, grid and column numbers of a timing diagram.
    Returns (wave_x0, step_w, first_row_y)."""
    wave_x0 = content.x + label_w
    step_w = (content.width - 6 - label_w - 6) // max_cols
    frame = pygame.Rect(content.x + 3, top, content.width - 6, n_rows * row_h + 4)
    pygame.draw.rect(screen, PANEL, frame)
    pygame.draw.rect(screen, PAGE_LINE, frame, 2)
    last_x = wave_x0 + (columns - 1) * step_w
    pygame.draw.rect(screen, HILITE, (last_x, frame.y + 2, step_w, frame.height - 4))
    for k in range(columns + 1):
        gx = wave_x0 + k * step_w
        pygame.draw.line(screen, PAGE_LINE, (gx, frame.y + 2), (gx, frame.bottom - 3), 1)
    for k in range(columns):
        num = ui["tiny"].render(str(first_index + k), False, MUTED)
        screen.blit(num, num.get_rect(
            midbottom=(wave_x0 + k * step_w + step_w // 2, frame.y - 1)))
    return wave_x0, step_w, top + 2


def minimal_sop(ones, dc, nb):
    """Minimal sum-of-products over nb variables Q(nb-1)..Q0 with don't cares."""
    ones = frozenset(ones)
    dc = frozenset(dc) - ones
    if not ones:
        return "0"
    usable = ones | dc
    names = [f"Q{nb - 1 - i}" for i in range(nb)]
    cubes = []
    for pattern in itertools.product((0, 1, None), repeat=nb):
        cover = frozenset(
            m for m in range(2 ** nb)
            if all(p is None or ((m >> (nb - 1 - i)) & 1) == p
                   for i, p in enumerate(pattern)))
        if cover <= usable and cover & ones:
            cubes.append((pattern, cover))
    primes = [c for c in cubes if not any(c[1] < o[1] for o in cubes)]
    best = None
    for count in range(1, len(primes) + 1):
        for combo in itertools.combinations(primes, count):
            if frozenset().union(*(c[1] for c in combo)) >= ones:
                lits = sum(1 for c in combo for p in c[0] if p is not None)
                if best is None or lits < best[0]:
                    best = (lits, combo)
        if best:
            break
    terms = []
    for pattern, _cover in best[1]:
        lits = [names[i] + ("" if p else "'")
                for i, p in enumerate(pattern) if p is not None]
        terms.append("·".join(lits) if lits else "1")
    terms.sort()
    return " + ".join(terms)


# ------------------------------------------------------------
# FLIP-FLOP BEHAVIOUR
# ------------------------------------------------------------

def ff_next(kind, ins, q):
    """Next state of a flip-flop. q and the result are 0, 1 or None (unknown)."""
    if kind == "SR":
        s, r = ins
        if s and r:
            return None
        if s:
            return 1
        if r:
            return 0
        return q
    if kind == "JK":
        j, k = ins
        if j and k:
            return None if q is None else 1 - q
        if j:
            return 1
        if k:
            return 0
        return q
    if kind == "D":
        return ins[0]
    if kind == "T":
        if ins[0]:
            return None if q is None else 1 - q
        return q
    raise ValueError(kind)


FF_INPUT_NAMES = {"SR": ("S", "R"), "JK": ("J", "K"), "D": ("D",), "T": ("T",)}

# (flip-flop you HAVE, flip-flop you WANT) -> (function, equations)
# function(want_inputs, q) -> the inputs to feed the flip-flop you have.
CONV = {
    ("SR", "JK"): (lambda w, q: (w[0] & (1 - q), w[1] & q),
                   ["S = J·Q'", "R = K·Q"]),
    ("SR", "D"): (lambda w, q: (w[0], 1 - w[0]),
                  ["S = D", "R = D'"]),
    ("SR", "T"): (lambda w, q: (w[0] & (1 - q), w[0] & q),
                  ["S = T·Q'", "R = T·Q"]),
    ("JK", "SR"): (lambda w, q: (w[0], w[1]),
                   ["J = S", "K = R", "(S = R = 1 stays forbidden)"]),
    ("JK", "D"): (lambda w, q: (w[0], 1 - w[0]),
                  ["J = D", "K = D'"]),
    ("JK", "T"): (lambda w, q: (w[0], w[0]),
                  ["J = T", "K = T"]),
    ("D", "SR"): (lambda w, q: (w[0] | ((1 - w[1]) & q),),
                  ["D = S + R'·Q"]),
    ("D", "JK"): (lambda w, q: ((w[0] & (1 - q)) | ((1 - w[1]) & q),),
                  ["D = J·Q' + K'·Q"]),
    ("D", "T"): (lambda w, q: (w[0] ^ q,),
                 ["D = T XOR Q"]),
    ("T", "SR"): (lambda w, q: ((w[0] & (1 - q)) | (w[1] & q),),
                  ["T = S·Q' + R·Q"]),
    ("T", "JK"): (lambda w, q: ((w[0] & (1 - q)) | (w[1] & q),),
                  ["T = J·Q' + K·Q"]),
    ("T", "D"): (lambda w, q: (w[0] ^ q,),
                 ["T = D XOR Q"]),
}


# ------------------------------------------------------------
# BASE CLASS
# ------------------------------------------------------------

class _Lab:
    def __init__(self):
        self.buttons = []
        self.msg = ""
        self.msg_ok = True
        self.auto = False
        self._auto_t = 0

    def say(self, text, ok=True):
        self.msg = text
        self.msg_ok = ok

    def handle_click(self, pos):
        for rect, fn in self.buttons:
            if rect.collidepoint(pos):
                fn()
                return True
        return False

    def toggle_auto(self):
        self.auto = not self.auto
        self._auto_t = pygame.time.get_ticks()

    def _tick_auto(self, step, period=650):
        if self.auto:
            now = pygame.time.get_ticks()
            if now - self._auto_t >= period:
                self._auto_t = now
                step()

    def _hit(self, rect, fn):
        self.buttons.append((rect, fn))

    def _button(self, screen, ui, rect, label, fn, selected=False, enabled=True):
        ui["button"](screen, rect, label, selected, enabled)
        if enabled:
            self._hit(rect, fn)

    def _header(self, screen, ui, content, title, tag, tag_color):
        t = ui["fit"](title, content.width - 230, 20, INK)
        screen.blit(t, (content.x + 3, content.y + 2))
        s = ui["small"].render(tag, False, tag_color)
        screen.blit(s, s.get_rect(topright=(content.right - 3, content.y + 8)))
        pygame.draw.line(screen, PAGE_LINE, (content.x + 2, content.y + 35),
                         (content.right - 2, content.y + 35), 2)

    def _tabs(self, screen, ui, content, labels, current, on_pick, y):
        n = len(labels)
        gap = 4
        w = (content.width - 6 - gap * (n - 1)) // n
        for i, label in enumerate(labels):
            rect = pygame.Rect(content.x + 3 + i * (w + gap), y, w, 26)
            self._button(screen, ui, rect, label,
                         (lambda i=i: on_pick(i)), i == current)

    def _row_buttons(self, screen, ui, x, y, specs, h=28):
        """specs: (label, fn, width, selected). Returns x after the last."""
        for label, fn, width, sel in specs:
            self._button(screen, ui, pygame.Rect(x, y, width, h), label, fn, sel)
            x += width + 8
        return x

    def _input_box(self, screen, ui, rect, label, value, fn):
        pygame.draw.rect(screen, DARK, rect)
        pygame.draw.rect(screen, CYAN, rect, 3)
        s = ui["small"].render(f"{label} = {value}", False, WHITE)
        screen.blit(s, s.get_rect(center=rect.center))
        self._hit(rect, fn)

    def _lamp(self, screen, ui, center, value, r=15):
        col = LIT if value == 1 else AMBER if value is None else OFF_LAMP
        pygame.draw.circle(screen, col, center, r)
        pygame.draw.circle(screen, WHITE, center, r + 1, 3)
        if value is None:
            q = ui["small"].render("?", False, INK)
            screen.blit(q, q.get_rect(center=center))

    def _box(self, screen, ui, rect, big, fill=DARK, edge=CYAN, big_color=WHITE):
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, edge, rect, 3)
        if big:
            s = ui["big"].render(big, False, big_color)
            screen.blit(s, s.get_rect(center=rect.center))

    def _clock_pin(self, screen, x, y, color=WHITE):
        pygame.draw.polygon(screen, color, [(x, y - 6), (x + 10, y), (x, y + 6)], 2)

    def _message(self, screen, ui, content, y, limit, text=None, color=None):
        text = self.msg if text is None else text
        if not text:
            return y
        color = color or (DARK_GREEN if self.msg_ok else MAROON)
        for line in ui["wrap"](text, content.width - 10, ui["small"]):
            if y + 21 > limit:
                break
            screen.blit(ui["small"].render(line, False, color), (content.x + 5, y))
            y += 21
        return y

    def _clip(self, screen, content, limit_y):
        screen.set_clip(pygame.Rect(content.x - 4, content.y - 4,
                                    content.width + 8, limit_y - content.y + 4))


# ============================================================
# 1. FLIP-FLOP LAB
# ============================================================

class FlipFlopLab(_Lab):
    VIEWS = ["SR", "JK", "D", "T", "MASTER-SLAVE", "CONVERSION"]
    TABS = ["S-R", "J-K", "D", "T", "MASTER-SLAVE", "CONVERSION"]
    TAGS = ["S-R FLIP-FLOP", "J-K FLIP-FLOP", "D FLIP-FLOP", "T FLIP-FLOP",
            "MASTER-SLAVE J-K", "CONVERSION"]
    TYPES = ["SR", "JK", "D", "T"]
    TYPE_LABELS = {"SR": "S-R", "JK": "J-K", "D": "D", "T": "T"}

    def __init__(self):
        super().__init__()
        self.view = 0
        self.ins = {k: [0] * len(v) for k, v in FF_INPUT_NAMES.items()}
        self.have = "JK"
        self.want = "D"
        self.cv_ins = [0, 0]
        self.reset()

    # ---- state ----------------------------------------------------
    def _kind_ins(self):
        v = self.VIEWS[self.view]
        if v in FF_INPUT_NAMES:
            return v, self.ins[v]
        if v == "MASTER-SLAVE":
            return "JK", self.ins["JK"]
        return self.want, self.cv_ins[:len(FF_INPUT_NAMES[self.want])]

    def _snap(self):
        _k, ins = self._kind_ins()
        return {"ins": tuple(ins), "q": self.q, "clk": self.clk, "m": self.m}

    def _intro(self):
        v = self.VIEWS[self.view]
        if v == "MASTER-SLAVE":
            return ("Set J and K, then press CLOCK twice: once for CLK = 1 "
                    "(master copies), once for CLK = 0 (slave copies).")
        if v == "CONVERSION":
            return ("Pick the flip-flop you HAVE and the one you WANT. The logic "
                    "box makes the one you have behave like the one you want.")
        return ("Click the input boxes to set 0 or 1, then press CLOCK. "
                "The flip-flop only looks at its inputs at the clock edge.")

    def reset(self, msg=None):
        self.q = 0
        self.clk = 0
        self.m = 0
        self.steps = 0
        self.hist = [self._snap()]
        self.say(self._intro() if msg is None else msg)

    def set_view(self, i):
        self.view = i % len(self.VIEWS)
        self.reset()

    def toggle(self, i):
        v = self.VIEWS[self.view]
        kind, ins = self._kind_ins()
        if i >= len(ins):
            return
        if v == "CONVERSION":
            self.cv_ins[i] ^= 1
        else:
            self.ins[kind][i] ^= 1
        if v == "MASTER-SLAVE" and self.clk:
            self.m = ff_next("JK", tuple(self.ins["JK"]), self.q)
            self.say("CLK is 1, so the MASTER is open and follows J and K: "
                     f"M = {_fmt(self.m)}. Q will copy it when CLK falls.")

    def pick_have(self, name):
        self.have = name
        self.reset(self._same_msg())

    def pick_want(self, name):
        self.want = name
        self.reset(self._same_msg())

    def _same_msg(self):
        if self.have == self.want:
            return "Both flip-flops are the same type: nothing to convert. Pick two different ones."
        return self._intro()

    # ---- clocking ---------------------------------------------------
    def clock(self):
        v = self.VIEWS[self.view]
        if v == "MASTER-SLAVE":
            return self._clock_ms()
        if v == "CONVERSION":
            return self._clock_conv()
        kind, ins = self._kind_ins()
        ins = tuple(ins)
        before = self.q
        self.q = ff_next(kind, ins, before)
        self.steps += 1
        self.hist.append(self._snap())
        self.hist = self.hist[-40:]
        self.say(f"CLOCK {self.steps}: " + self._explain(kind, ins, before, self.q),
                 self.q is not None)

    def _explain(self, kind, ins, qb, qa):
        move = f" Q: {_fmt(qb)} -> {_fmt(qa)}."
        if kind == "SR":
            s, r = ins
            if s and r:
                why = ("S = 1 and R = 1 is FORBIDDEN: set and reset at once, so Q is "
                       "unknown (?). Use S = 1 or R = 1 to recover.")
            elif s:
                why = "S = 1, R = 0 SETS the flip-flop: Q becomes 1."
            elif r:
                why = "S = 0, R = 1 RESETS the flip-flop: Q becomes 0."
            else:
                why = "S = 0, R = 0 means HOLD: Q keeps its old value."
        elif kind == "JK":
            j, k = ins
            if j and k:
                why = "J = 1, K = 1 TOGGLES: Q flips to the opposite of its old value."
            elif j:
                why = "J = 1, K = 0 SETS: Q becomes 1."
            elif k:
                why = "J = 0, K = 1 RESETS: Q becomes 0."
            else:
                why = "J = 0, K = 0 means HOLD: Q keeps its old value."
        elif kind == "D":
            why = f"D = {ins[0]}: Q simply copies D at the clock edge (Q+ = D)."
        else:
            why = ("T = 1 TOGGLES: Q flips." if ins[0]
                   else "T = 0 means HOLD: Q keeps its old value.")
        return why + move

    def _clock_ms(self):
        ins = tuple(self.ins["JK"])
        if self.clk == 0:
            self.clk = 1
            self.m = ff_next("JK", ins, self.q)
            text = ("CLK rises to 1: the MASTER opens and works out the J-K result "
                    f"(M = {_fmt(self.m)}). The SLAVE is locked, so Q has not changed yet.")
        else:
            self.clk = 0
            self.q = self.m
            text = ("CLK falls to 0: the MASTER locks and the SLAVE copies it, so "
                    f"Q = M = {_fmt(self.q)}. Q changes only on the falling edge, so "
                    "J = K = 1 toggles once (no race-around).")
        self.steps += 1
        self.hist.append(self._snap())
        self.hist = self.hist[-40:]
        self.say(text, self.q is not None)

    def _clock_conv(self):
        if self.have == self.want:
            self.say(self._same_msg(), False)
            return
        if self.q is None:
            self.say("Q is unknown (?). Press RESET first.", False)
            return
        names_w = FF_INPUT_NAMES[self.want]
        names_h = FF_INPUT_NAMES[self.have]
        wi = tuple(self.cv_ins[:len(names_w)])
        fn = CONV[(self.have, self.want)][0]
        hi = tuple(fn(wi, self.q))
        expected = ff_next(self.want, wi, self.q)
        got = ff_next(self.have, hi, self.q)
        qb = self.q
        self.steps += 1
        w_txt = " ".join(f"{n}={v}" for n, v in zip(names_w, wi))
        h_txt = " ".join(f"{n}={v}" for n, v in zip(names_h, hi))
        if expected is None:
            self.q = None
            self.say(f"CLOCK {self.steps}: {w_txt} is forbidden for this flip-flop "
                     "(S and R both 1), so Q is unknown.", False)
        else:
            self.q = got
            ok = got == expected
            self.say(
                f"CLOCK {self.steps}: the logic turns {w_txt} into {h_txt} for the "
                f"{self.TYPE_LABELS[self.have]} flip-flop. It gives Q = {_fmt(got)}; a real "
                f"{self.TYPE_LABELS[self.want]} flip-flop would give {_fmt(expected)}. "
                + ("They MATCH." if ok else "MISMATCH!"), ok)
        self.hist.append(self._snap())
        self.hist = self.hist[-40:]

    # ---- keys -----------------------------------------------------------
    def handle_key(self, event):
        key = event.key
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.clock()
            return True
        if key == pygame.K_r:
            self.reset()
            return True
        if key == pygame.K_LEFT:
            self.set_view(self.view - 1)
            return True
        if key == pygame.K_RIGHT:
            self.set_view(self.view + 1)
            return True
        if key in (pygame.K_1, pygame.K_2):
            self.toggle(0 if key == pygame.K_1 else 1)
            return True
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            return True
        return False

    # ---- drawing ---------------------------------------------------------
    def draw(self, screen, content, limit_y, ui):
        self.buttons = []
        self._clip(screen, content, limit_y)
        v = self.VIEWS[self.view]
        X, Y = content.x, content.y
        self._header(screen, ui, content, "FLIP-FLOPS", self.TAGS[self.view],
                     MAROON if v in ("MASTER-SLAVE", "CONVERSION") else DARK_GREEN)
        self._tabs(screen, ui, content, self.TABS, self.view, self.set_view, Y + 40)

        if v in FF_INPUT_NAMES:
            self._draw_basic(screen, ui, content, limit_y)
        elif v == "MASTER-SLAVE":
            self._draw_ms(screen, ui, content, limit_y)
        else:
            self._draw_conv(screen, ui, content, limit_y)
        screen.set_clip(None)

    def _controls(self, screen, ui, X, y):
        return self._row_buttons(screen, ui, X + 3, y, (
            ("CLOCK [SPACE]", self.clock, 150, False),
            ("RESET [R]", self.reset, 112, False)))

    # -- S-R / J-K / D / T -----------------------------------------------
    def _draw_basic(self, screen, ui, content, limit_y):
        X, Y, w = content.x, content.y, content.width
        kind = self.VIEWS[self.view]
        names = FF_INPUT_NAMES[kind]
        n_in = len(names)
        ins = self.ins[kind]

        panel = pygame.Rect(X + 3, Y + 72, int(w * 0.56), 164)
        pygame.draw.rect(screen, PANEL, panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)

        box = pygame.Rect(panel.x + int(panel.width * 0.40), panel.y + 14, 96, 130)
        pin_ys = ([box.y + 40, box.y + 76] if n_in == 2 else [box.y + 58])
        clk_y = box.y + 112
        qy, qby = box.y + 40, box.y + 76

        # input boxes + wires
        for i, py in enumerate(pin_ys):
            r = pygame.Rect(panel.x + 10, py - 14, 76, 28)
            pygame.draw.line(screen, WIRE, (r.right, py), (box.x, py), 4)
            self._input_box(screen, ui, r, names[i], ins[i],
                            (lambda i=i: self.toggle(i)))
        clk_r = pygame.Rect(panel.x + 10, clk_y - 14, 76, 28)
        pygame.draw.line(screen, WIRE, (clk_r.right, clk_y), (box.x, clk_y), 4)
        pygame.draw.rect(screen, DARK, clk_r)
        pygame.draw.rect(screen, CYAN, clk_r, 3)
        s = ui["small"].render("CLK", False, WHITE)
        screen.blit(s, s.get_rect(center=clk_r.center))
        self._hit(clk_r, self.clock)

        # flip-flop body
        self._box(screen, ui, box, "")
        title = ui["big"].render(self.TYPE_LABELS[kind], False, WHITE)
        screen.blit(title, title.get_rect(center=(box.centerx, box.y + 22)))
        for name, py in zip(names, pin_ys):
            screen.blit(ui["tiny"].render(name, False, WHITE), (box.x + 6, py - 6))
        self._clock_pin(screen, box.x, clk_y)
        qv = ui["tiny"].render("Q", False, WHITE)
        screen.blit(qv, qv.get_rect(topright=(box.right - 6, qy - 6)))
        qn = ui["tiny"].render("Q'", False, WHITE)
        screen.blit(qn, qn.get_rect(topright=(box.right - 6, qby - 6)))

        # outputs
        lamp_x = panel.right - 34
        qprime = None if self.q is None else 1 - self.q
        pygame.draw.line(screen, WIRE, (box.right, qy), (lamp_x - 17, qy), 4)
        pygame.draw.line(screen, WIRE, (box.right, qby), (lamp_x - 17, qby), 4)
        self._lamp(screen, ui, (lamp_x, qy), self.q)
        self._lamp(screen, ui, (lamp_x, qby), qprime)
        screen.blit(ui["tiny"].render("Q", False, INK), (lamp_x + 19, qy - 6))
        screen.blit(ui["tiny"].render("Q'", False, INK), (lamp_x + 19, qby - 6))

        # characteristic table
        tx = panel.right + 12
        tw = content.right - tx - 3
        screen.blit(ui["tiny"].render("CHARACTERISTIC TABLE", False, MUTED),
                    (tx, panel.y))
        heads = list(names) + ["Q", "Q+"]
        cw = max(1, tw // len(heads))
        rh = 17
        ty = panel.y + 16
        for c, head in enumerate(heads):
            cell = pygame.Rect(tx + c * cw, ty, cw, rh)
            pygame.draw.rect(screen, PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)
            s = ui["tiny"].render(head, False, INK)
            screen.blit(s, s.get_rect(center=cell.center))
        row = 0
        for combo in itertools.product((0, 1), repeat=n_in):
            for q in (0, 1):
                nxt = ff_next(kind, combo, q)
                active = (list(combo) == list(ins) and q == self.q)
                vals = list(combo) + [q, "X" if nxt is None else nxt]
                for c, val in enumerate(vals):
                    cell = pygame.Rect(tx + c * cw, ty + (row + 1) * rh, cw, rh)
                    pygame.draw.rect(screen, HILITE if active else PAPER, cell)
                    pygame.draw.rect(screen, CYAN if active else PAGE_LINE, cell,
                                     2 if active else 1)
                    col = MAROON if val == "X" else INK
                    s = ui["tiny"].render(str(val), False, col)
                    screen.blit(s, s.get_rect(center=cell.center))
                row += 1

        # controls + equation
        cy = panel.bottom + 8
        xend = self._controls(screen, ui, X, cy)
        eq = {"SR": "Q+ = S + R'·Q  (S·R = 0)", "JK": "Q+ = J·Q' + K'·Q",
              "D": "Q+ = D", "T": "Q+ = T XOR Q"}[kind]
        screen.blit(ui["small"].render(eq, False, DARK_GREEN), (xend + 6, cy + 6))

        # timing diagram
        ty0 = cy + 36
        screen.blit(ui["tiny"].render(
            "TIMING DIAGRAM: inputs are read at the rising edge of each pulse",
            False, INK), (X + 3, ty0))
        rows = 2 + n_in
        row_h = 17
        show = self.hist[-12:]
        cols = len(show)
        first = self.steps - (cols - 1)
        wx0, step_w, ry0 = _timing_frame(screen, ui, content, ty0 + 26, rows,
                                         row_h, cols, first)
        labels = ["CLK"] + list(names) + ["Q"]
        colors = [(0, 120, 140)] + [DARK_GREEN] * n_in + [MAROON]
        for r, name in enumerate(labels):
            ry = ry0 + r * row_h
            screen.blit(ui["tiny"].render(name, False, colors[r]), (X + 8, ry + 3))
            if r == 0:
                _clock_wave(screen, wx0, ry, row_h, step_w, first, cols, colors[0])
            elif r <= n_in:
                _wave(screen, wx0, ry, row_h, step_w,
                      [h["ins"][r - 1] for h in show], colors[r])
            else:
                _wave(screen, wx0, ry, row_h, step_w, [h["q"] for h in show],
                      colors[r])
        self._message(screen, ui, content, ty0 + 26 + rows * row_h + 12, limit_y)

    # -- master-slave ------------------------------------------------------
    def _draw_ms(self, screen, ui, content, limit_y):
        X, Y, w = content.x, content.y, content.width
        ins = self.ins["JK"]
        panel = pygame.Rect(X + 3, Y + 72, int(w * 0.56), 164)
        pygame.draw.rect(screen, PANEL, panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)

        master = pygame.Rect(panel.x + 100, panel.y + 14, 84, 110)
        slave = pygame.Rect(panel.x + 214, panel.y + 14, 84, 110)
        clk_y = panel.y + 110
        mid_y = master.y + 55
        for i, name in enumerate(("J", "K")):
            py = master.y + 20 + i * 40
            r = pygame.Rect(panel.x + 10, py - 14, 76, 28)
            pygame.draw.line(screen, WIRE, (r.right, py), (master.x, py), 4)
            self._input_box(screen, ui, r, name, ins[i], (lambda i=i: self.toggle(i)))

        open_master = self.clk == 1
        pygame.draw.line(screen, WIRE, (master.right, mid_y), (slave.x, mid_y), 4)
        self._box(screen, ui, master, _fmt(self.m),
                  edge=LIT if open_master else CYAN)
        self._box(screen, ui, slave, _fmt(self.q),
                  edge=LIT if not open_master else CYAN)
        for rect, name, is_open in ((master, "MASTER", open_master),
                                    (slave, "SLAVE", not open_master)):
            s = ui["tiny"].render(name, False, WHITE)
            screen.blit(s, s.get_rect(midtop=(rect.centerx, rect.y + 4)))
            s = ui["tiny"].render("OPEN" if is_open else "LOCKED", False,
                                  LIT if is_open else AMBER)
            screen.blit(s, s.get_rect(midbottom=(rect.centerx, rect.bottom - 4)))
        self._clock_pin(screen, master.x, clk_y)
        self._clock_pin(screen, slave.x, clk_y)
        pygame.draw.circle(screen, WHITE, (slave.x - 5, clk_y), 4, 2)   # inverter bubble

        # clock button and wiring to master (direct) and slave (inverted)
        clk_r = pygame.Rect(panel.x + 10, clk_y - 14, 76, 28)
        pygame.draw.rect(screen, DARK, clk_r)
        pygame.draw.rect(screen, LIT if self.clk else CYAN, clk_r, 3)
        s = ui["small"].render(f"CLK={self.clk}", False, WHITE)
        screen.blit(s, s.get_rect(center=clk_r.center))
        self._hit(clk_r, self.clock)
        pygame.draw.line(screen, WIRE, (clk_r.right, clk_y), (master.x, clk_y), 3)
        low = panel.bottom - 14
        pygame.draw.lines(screen, WIRE, False,
                          [(clk_r.right + 8, clk_y), (clk_r.right + 8, low),
                           (slave.x - 16, low), (slave.x - 16, clk_y),
                           (slave.x - 9, clk_y)], 3)

        lamp_x = panel.right - 34
        pygame.draw.line(screen, WIRE, (slave.right, mid_y), (lamp_x - 17, mid_y), 4)
        self._lamp(screen, ui, (lamp_x, mid_y), self.q)
        screen.blit(ui["tiny"].render("Q", False, INK), (lamp_x - 4, mid_y + 20))

        # explanation column
        tx = panel.right + 12
        tw = content.right - tx - 3
        screen.blit(ui["tiny"].render("TWO PHASES OF ONE PULSE", False, MUTED),
                    (tx, panel.y))
        ty = panel.y + 20
        for line_txt, active in (
            ("CLK = 1: MASTER open (copies J, K and Q). SLAVE locked.", self.clk == 1),
            ("CLK = 0: MASTER locked. SLAVE copies the MASTER.", self.clk == 0),
        ):
            for line in ui["wrap"](line_txt, tw, ui["small"]):
                screen.blit(ui["small"].render(line, False,
                                               DARK_GREEN if active else MUTED),
                            (tx, ty))
                ty += 20
            ty += 6
        for line in ui["wrap"]("Q only changes when CLK falls, and the new Q "
                               "cannot reach the master until the next pulse.",
                               tw, ui["small"]):
            screen.blit(ui["small"].render(line, False, INK), (tx, ty))
            ty += 20

        cy = panel.bottom + 8
        xend = self._controls(screen, ui, X, cy)
        screen.blit(ui["small"].render("Q+ = J·Q' + K'·Q on the falling edge",
                                       False, DARK_GREEN), (xend + 6, cy + 6))

        ty0 = cy + 36
        screen.blit(ui["tiny"].render(
            "TIMING DIAGRAM: one column per phase (CLK up, CLK down)", False, INK),
            (X + 3, ty0))
        rows, row_h = 5, 17
        show = self.hist[-12:]
        cols = len(show)
        first = self.steps - (cols - 1)
        wx0, step_w, ry0 = _timing_frame(screen, ui, content, ty0 + 26, rows,
                                         row_h, cols, first)
        data = [("CLK", [h["clk"] for h in show], (0, 120, 140)),
                ("J", [h["ins"][0] for h in show], DARK_GREEN),
                ("K", [h["ins"][1] for h in show], DARK_GREEN),
                ("M", [h["m"] for h in show], AMBER),
                ("Q", [h["q"] for h in show], MAROON)]
        for r, (name, vals, col) in enumerate(data):
            ry = ry0 + r * row_h
            screen.blit(ui["tiny"].render(name, False, col), (X + 8, ry + 3))
            _wave(screen, wx0, ry, row_h, step_w, vals, col)
        self._message(screen, ui, content, ty0 + 26 + rows * row_h + 12, limit_y)

    # -- conversion ----------------------------------------------------------
    def _draw_conv(self, screen, ui, content, limit_y):
        X, Y, w = content.x, content.y, content.width
        have, want = self.have, self.want
        same = have == want

        for row, (label, current, fn) in enumerate((
                ("I HAVE:", have, self.pick_have),
                ("I WANT:", want, self.pick_want))):
            ry = Y + 72 + row * 32
            screen.blit(ui["small"].render(label, False, INK), (X + 3, ry + 5))
            bx = X + 100
            for t in self.TYPES:
                self._button(screen, ui, pygame.Rect(bx, ry, 76, 26),
                             self.TYPE_LABELS[t] + " FF",
                             (lambda t=t: fn(t)), t == current)
                bx += 82

        top = Y + 140
        panel = pygame.Rect(X + 3, top, int(w * 0.52), 128)
        pygame.draw.rect(screen, PANEL, panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)

        names_w = FF_INPUT_NAMES[want]
        names_h = FF_INPUT_NAMES[have]
        wi = tuple(self.cv_ins[:len(names_w)])
        q = self.q if self.q is not None else 0
        hi = ()
        if not same:
            hi = tuple(CONV[(have, want)][0](wi, q))

        ff = pygame.Rect(panel.x + 228, panel.y + 12, 84, 92)
        logic = pygame.Rect(panel.x + 106, panel.y + 22, 84, 66)
        pin_ys = ([ff.y + 28, ff.y + 58] if len(names_h) == 2 else [ff.y + 43])
        clk_y = ff.y + 82
        in_ys = ([logic.y + 16, logic.y + 46] if len(names_w) == 2
                 else [logic.centery])

        # want inputs
        for i, py in enumerate(in_ys):
            r = pygame.Rect(panel.x + 8, py - 13, 70, 26)
            pygame.draw.line(screen, WIRE, (r.right, py), (logic.x, py), 3)
            self._input_box(screen, ui, r, names_w[i], wi[i],
                            (lambda i=i: self.toggle(i)))
        # logic box
        pygame.draw.rect(screen, (20, 52, 70), logic)
        pygame.draw.rect(screen, CYAN, logic, 3)
        s = ui["tiny"].render("LOGIC", False, WHITE)
        screen.blit(s, s.get_rect(center=logic.center))
        # logic -> flip-flop
        for i, py in enumerate(pin_ys):
            y_from = logic.centery if len(pin_ys) == 1 else (logic.y + 16 + i * 30)
            pygame.draw.lines(screen, WIRE, False,
                              [(logic.right, y_from), ((logic.right + ff.x) // 2, y_from),
                               ((logic.right + ff.x) // 2, py), (ff.x, py)], 3)
            if not same:
                t = ui["tiny"].render(f"{names_h[i]}={hi[i]}", False, DARK_GREEN)
                screen.blit(t, (logic.right + 3, min(y_from, py) - 15))
        # Q feedback to the logic box
        qx = ff.right + 12
        pygame.draw.lines(screen, WIRE, False,
                          [(qx, ff.y + 43), (qx, panel.y + 6),
                           (logic.centerx, panel.y + 6), (logic.centerx, logic.y)], 2)
        screen.blit(ui["tiny"].render("Q feedback", False, MUTED),
                    (logic.centerx + 6, panel.y + 8))
        # flip-flop body
        self._box(screen, ui, ff, "")
        s = ui["big"].render(self.TYPE_LABELS[have], False, WHITE)
        screen.blit(s, s.get_rect(center=(ff.centerx, ff.y + 12)))
        for name, py in zip(names_h, pin_ys):
            screen.blit(ui["tiny"].render(name, False, WHITE), (ff.x + 6, py - 6))
        self._clock_pin(screen, ff.x, clk_y)
        # clock button
        clk_r = pygame.Rect(panel.x + 8, clk_y - 13, 70, 26)
        pygame.draw.line(screen, WIRE, (clk_r.right, clk_y), (ff.x, clk_y), 3)
        pygame.draw.rect(screen, DARK, clk_r)
        pygame.draw.rect(screen, CYAN, clk_r, 3)
        s = ui["small"].render("CLK", False, WHITE)
        screen.blit(s, s.get_rect(center=clk_r.center))
        self._hit(clk_r, self.clock)
        # Q lamp
        pygame.draw.line(screen, WIRE, (ff.right, ff.y + 43), (qx + 14, ff.y + 43), 3)
        self._lamp(screen, ui, (panel.right - 22, ff.y + 43), self.q, r=13)
        screen.blit(ui["tiny"].render("Q", False, INK),
                    (panel.right - 26, ff.y + 62))

        # excitation table
        tx = panel.right + 12
        tw = content.right - tx - 3
        screen.blit(ui["tiny"].render(
            "EXCITATION TABLE (what the logic must send)", False, MUTED), (tx, top - 2))
        if not same:
            heads = list(names_w) + ["Q", "Q+"] + list(names_h)
            cw = max(1, tw // len(heads))
            rh = 16
            ty = top + 14
            for c, head in enumerate(heads):
                cell = pygame.Rect(tx + c * cw, ty, cw, rh)
                pygame.draw.rect(screen, HILITE if c >= len(names_w) + 2 else PAPER_LIGHT,
                                 cell)
                pygame.draw.rect(screen, PAGE_LINE, cell, 2)
                s = ui["tiny"].render(head, False, INK)
                screen.blit(s, s.get_rect(center=cell.center))
            row = 0
            for combo in itertools.product((0, 1), repeat=len(names_w)):
                nxt_any = ff_next(want, combo, 0)
                if nxt_any is None:                 # forbidden S-R row
                    continue
                for qq in (0, 1):
                    nxt = ff_next(want, combo, qq)
                    h_ins = CONV[(have, want)][0](combo, qq)
                    active = (combo == wi and qq == self.q)
                    vals = list(combo) + [qq, nxt] + list(h_ins)
                    for c, val in enumerate(vals):
                        cell = pygame.Rect(tx + c * cw, ty + (row + 1) * rh, cw, rh)
                        pygame.draw.rect(screen, HILITE if active else PAPER, cell)
                        pygame.draw.rect(screen, CYAN if active else PAGE_LINE, cell,
                                         2 if active else 1)
                        s = ui["tiny"].render(str(val), False, INK)
                        screen.blit(s, s.get_rect(center=cell.center))
                    row += 1
        else:
            for i, line in enumerate(ui["wrap"](
                    "Choose two different flip-flops to see the conversion.",
                    tw, ui["small"])):
                screen.blit(ui["small"].render(line, False, MAROON),
                            (tx, top + 20 + i * 20))

        cy = panel.bottom + 8
        xend = self._controls(screen, ui, X, cy)
        y = cy + 36
        if not same:
            screen.blit(ui["tiny"].render(
                "DESIGN EQUATIONS (from the excitation table):", False, MUTED), (X + 3, y))
            y += 16
            for eq in CONV[(have, want)][1]:
                screen.blit(ui["small"].render(eq, False, DARK_GREEN), (X + 12, y))
                y += 20
            y += 4
        self._message(screen, ui, content, y, limit_y)


# ============================================================
# 2. SHIFT REGISTER LAB
# ============================================================

class ShiftLab(_Lab):
    KINDS = ["SISO", "SIPO", "PISO", "PIPO"]
    FULL = {"SISO": "SERIAL-IN SERIAL-OUT", "SIPO": "SERIAL-IN PARALLEL-OUT",
            "PISO": "PARALLEL-IN SERIAL-OUT", "PIPO": "PARALLEL-IN PARALLEL-OUT"}
    N = 4

    def __init__(self):
        super().__init__()
        self.kind = 0
        self.si = 1
        self.p = [1, 0, 1, 1]
        self.load = 1
        self.reset()

    def _aux(self):
        k = self.KINDS[self.kind]
        if k in ("SISO", "SIPO"):
            return self.si
        if k == "PISO":
            return self.load
        return None

    def _snap(self):
        return {"aux": self._aux(), "bits": tuple(self.bits)}

    def reset(self, msg=None):
        self.bits = [0] * self.N
        self.steps = 0
        self.stream = []
        self.hist = [self._snap()]
        self.say(msg if msg is not None else self._intro())

    def _intro(self):
        k = self.KINDS[self.kind]
        return {
            "SISO": "Click SI to choose the input bit, then press CLOCK. Bits enter Q0 and move right; only Q3 is the output.",
            "SIPO": "Same shifting as SISO, but all four outputs Q0-Q3 can be read together once the word is in.",
            "PISO": "Click P0-P3 to set a word. With MODE = LOAD, one clock loads it. Switch to SHIFT and the bits leave one per clock.",
            "PIPO": "Click P0-P3 to set a word. One clock loads all four bits at once; there is no shifting.",
        }[k]

    def set_kind(self, i):
        self.kind = i % len(self.KINDS)
        self.reset()

    def toggle_p(self, i):
        self.p[i] ^= 1

    def toggle_si(self):
        self.si ^= 1

    def toggle_load(self):
        self.load ^= 1
        self.say("MODE = LOAD: the next clock loads P0-P3." if self.load
                 else "MODE = SHIFT: the next clock shifts every bit one place right.")

    def clock(self):
        k = self.KINDS[self.kind]
        before = list(self.bits)
        n = self.steps + 1
        bits_txt = lambda b: "".join(map(str, b))
        if k in ("SISO", "SIPO"):
            out = before[3]
            self.bits = [self.si] + before[:3]
            text = (f"CLOCK {n}: SI = {self.si} enters Q0, every bit moves one place right "
                    f"and the old Q3 ({out}) leaves. Q0-Q3 = {bits_txt(self.bits)}.")
            if k == "SISO":
                text += " A 4-bit word needs 4 clocks to go in and 4 more to come out."
            else:
                text += f" Parallel output word = {bits_txt(self.bits)}."
        elif k == "PISO":
            if self.load:
                self.bits = list(self.p)
                text = (f"CLOCK {n}: LOAD = 1, so the whole word P0-P3 = {bits_txt(self.p)} is "
                        "loaded in ONE clock. Now set MODE = SHIFT.")
            else:
                self.bits = [0] + before[:3]
                text = (f"CLOCK {n}: SHIFT mode. Bits move one place right and SERIAL OUT "
                        f"(Q3) is now {self.bits[3]}. One bit leaves per clock.")
        else:
            self.bits = list(self.p)
            text = (f"CLOCK {n}: all four bits are loaded together: Q0-Q3 = "
                    f"{bits_txt(self.bits)}. One clock moves the whole word.")
        self.steps = n
        if k in ("SISO", "PISO"):
            self.stream.append(self.bits[3])
            self.stream = self.stream[-24:]
        self.hist.append(self._snap())
        self.hist = self.hist[-40:]
        self.say(text)

    def handle_key(self, event):
        key = event.key
        k = self.KINDS[self.kind]
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.clock()
            return True
        if key == pygame.K_r:
            self.reset()
            return True
        if key == pygame.K_a:
            self.toggle_auto()
            return True
        if key == pygame.K_LEFT:
            self.set_kind(self.kind - 1)
            return True
        if key == pygame.K_RIGHT:
            self.set_kind(self.kind + 1)
            return True
        if key == pygame.K_l and k == "PISO":
            self.toggle_load()
            return True
        digits = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
        if key in digits:
            i = digits.index(key)
            if k in ("PISO", "PIPO"):
                self.toggle_p(i)
            elif i == 0:
                self.toggle_si()
            return True
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            return True
        return False

    def draw(self, screen, content, limit_y, ui):
        self.buttons = []
        self._tick_auto(self.clock)
        self._clip(screen, content, limit_y)
        X, Y, w = content.x, content.y, content.width
        k = self.KINDS[self.kind]
        parallel_in = k in ("PISO", "PIPO")
        parallel_out = k in ("SIPO", "PIPO")

        self._header(screen, ui, content, "SHIFT REGISTERS", self.FULL[k], DARK_GREEN)
        self._tabs(screen, ui, content, self.KINDS, self.kind, self.set_kind, Y + 40)

        panel = pygame.Rect(X + 3, Y + 70, w - 6, 154)
        pygame.draw.rect(screen, PANEL, panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)

        bw, bh, gap = 70, 44, 40
        x0 = panel.x + 118
        box_y = panel.y + 68
        ffs = [pygame.Rect(x0 + i * (bw + gap), box_y, bw, bh) for i in range(self.N)]
        cy = box_y + bh // 2
        rail = panel.y + 140

        # wires first
        for i in range(self.N - 1):
            _arrow(screen, WIRE, ffs[i].right, ffs[i + 1].x, cy)
        if not parallel_in:
            r = pygame.Rect(panel.x + 14, cy - 14, 70, 28)
            _arrow(screen, WIRE, r.right, ffs[0].x, cy)
        for i, f in enumerate(ffs):
            sx = f.x + 8
            pygame.draw.line(screen, WIRE, (sx, rail), (sx, f.bottom), 3)
        pygame.draw.line(screen, WIRE, (panel.x + 82, rail), (ffs[-1].x + 8, rail), 3)

        # inputs
        if not parallel_in:
            self._input_box(screen, ui, pygame.Rect(panel.x + 14, cy - 14, 70, 28),
                            "SI", self.si, self.toggle_si)
        else:
            for i, f in enumerate(ffs):
                pb = pygame.Rect(f.x, panel.y + 8, bw, 24)
                self._input_box(screen, ui, pb, f"P{i}", self.p[i],
                                (lambda i=i: self.toggle_p(i)))
                cx = f.centerx
                if k == "PISO":
                    mux = pygame.Rect(f.x + 12, panel.y + 40, bw - 24, 20)
                    pygame.draw.line(screen, WIRE, (cx, pb.bottom), (cx, mux.y), 3)
                    pygame.draw.line(screen, WIRE, (cx, mux.bottom), (cx, f.y), 3)
                    pygame.draw.rect(screen, (20, 52, 70), mux)
                    pygame.draw.rect(screen, CYAN, mux, 2)
                    s = ui["tiny"].render("MUX", False, WHITE)
                    screen.blit(s, s.get_rect(center=mux.center))
                    if i == 0:
                        screen.blit(ui["tiny"].render("0", False, INK),
                                    (mux.x - 12, mux.centery - 6))
                        pygame.draw.line(screen, WIRE, (mux.x - 3, mux.centery),
                                         (mux.x, mux.centery), 2)
                    else:
                        pf = ffs[i - 1]
                        pygame.draw.lines(screen, WIRE, False,
                                          [(pf.right, cy), (pf.right + 14, cy),
                                           (pf.right + 14, mux.centery),
                                           (mux.x, mux.centery)], 2)
                else:
                    pygame.draw.line(screen, WIRE, (cx, pb.bottom), (cx, f.y), 3)
            if k == "PISO":
                s = ui["tiny"].render("LOAD" if self.load else "SHIFT", False,
                                      MAROON if self.load else DARK_GREEN)
                screen.blit(s, (panel.x + 14, panel.y + 42))

        # flip-flops
        for i, f in enumerate(ffs):
            bit = self.bits[i]
            edge = LIT if (parallel_out or (i == 3)) else CYAN
            self._box(screen, ui, f, str(bit), fill=LIT if bit else DARK, edge=edge,
                      big_color=INK if bit else WHITE)
            screen.blit(ui["tiny"].render(f"Q{i}", False, INK if bit else WHITE),
                        (f.x + 5, f.y + 3))
            self._clock_pin(screen, f.x, f.bottom - 7, INK if bit else WHITE)

        # outputs
        if parallel_out:
            for i, f in enumerate(ffs):
                _varrow(screen, WIRE, f.centerx, f.bottom, panel.y + 117)
                self._lamp(screen, ui, (f.centerx, panel.y + 126), self.bits[i], r=8)
                screen.blit(ui["tiny"].render(f"Q{i}", False, INK),
                            (f.centerx + 12, panel.y + 120))
        else:
            lamp = (ffs[-1].right + 58, cy)
            _arrow(screen, WIRE, ffs[-1].right, lamp[0] - 18, cy)
            self._lamp(screen, ui, lamp, self.bits[3], r=15)
            s = ui["tiny"].render("SERIAL OUT", False, MUTED)
            screen.blit(s, s.get_rect(midtop=(lamp[0], lamp[1] + 20)))

        # clock button
        clk_r = pygame.Rect(panel.x + 14, rail - 12, 66, 24)
        pygame.draw.rect(screen, DARK, clk_r)
        pygame.draw.rect(screen, CYAN, clk_r, 3)
        s = ui["small"].render("CLK", False, WHITE)
        screen.blit(s, s.get_rect(center=clk_r.center))
        self._hit(clk_r, self.clock)

        # controls
        cy2 = panel.bottom + 6
        specs = [("CLOCK [SPACE]", self.clock, 150, False),
                 ("RESET [R]", self.reset, 112, False),
                 ("AUTO [A]", self.toggle_auto, 110, self.auto)]
        if k == "PISO":
            specs.append((f"MODE: {'LOAD' if self.load else 'SHIFT'} [L]",
                          self.toggle_load, 190, False))
        self._row_buttons(screen, ui, X + 3, cy2, specs)

        # readout
        ry = cy2 + 34
        word = "".join(map(str, self.bits))
        if parallel_out:
            txt = f"PARALLEL OUT  Q0 Q1 Q2 Q3 = {' '.join(word)}"
        else:
            stream = " ".join(map(str, self.stream[-16:])) or "(none yet)"
            txt = f"SERIAL OUT STREAM: {stream}"
        screen.blit(ui["small"].render(txt, False, MAROON), (X + 5, ry))

        # timing diagram
        ty0 = ry + 24
        screen.blit(ui["tiny"].render("TIMING DIAGRAM: each column is one clock pulse",
                                      False, INK), (X + 3, ty0))
        aux_name = {"SISO": "SI", "SIPO": "SI", "PISO": "LOAD", "PIPO": None}[k]
        labels = ["CLK"] + ([aux_name] if aux_name else []) + [f"Q{i}" for i in range(4)]
        row_h = 15
        show = self.hist[-12:]
        cols = len(show)
        first = self.steps - (cols - 1)
        wx0, step_w, ry0 = _timing_frame(screen, ui, content, ty0 + 26, len(labels),
                                         row_h, cols, first)
        colors = ([(0, 120, 140)] + ([AMBER] if aux_name else [])
                  + [DARK_GREEN] * 3 + [MAROON])
        for r, name in enumerate(labels):
            ry_r = ry0 + r * row_h
            screen.blit(ui["tiny"].render(name, False, colors[r]), (X + 8, ry_r + 2))
            if r == 0:
                _clock_wave(screen, wx0, ry_r, row_h, step_w, first, cols, colors[0])
            elif aux_name and r == 1:
                _wave(screen, wx0, ry_r, row_h, step_w, [h["aux"] for h in show],
                      colors[r])
            else:
                bit = r - 1 - (1 if aux_name else 0)
                _wave(screen, wx0, ry_r, row_h, step_w,
                      [h["bits"][bit] for h in show], colors[r])
        self._message(screen, ui, content, ty0 + 26 + len(labels) * row_h + 12, limit_y)
        screen.set_clip(None)


# ============================================================
# 3. COUNTER LAB
# ============================================================

class CounterLab(_Lab):
    VIEWS = ["ASYNC UP", "ASYNC DOWN", "SYNC UP", "SYNC DOWN", "MOD-N ASYNC",
             "MOD-N SYNC"]
    N_MIN, N_MAX = 3, 10
    JK_EXC = {(0, 0): ("0", "X"), (0, 1): ("1", "X"),
              (1, 0): ("X", "1"), (1, 1): ("X", "0")}

    def __init__(self):
        super().__init__()
        self.view = 0
        self.N = 10
        self.ff = "T"
        self._design_cache = {}
        self.reset()

    # ---- derived properties -------------------------------------------
    def is_sync(self):
        return self.view in (2, 3, 5)

    def is_down(self):
        return self.view in (1, 3)

    def modulus(self):
        return self.N if self.view >= 4 else 16

    def nb(self):
        return 4 if self.view < 4 else max(2, (self.N - 1).bit_length())

    def natural(self):
        return self.N == 2 ** self.nb()

    def reset(self, msg=None):
        self.cnt = 0
        self.steps = 0
        self.last = None
        self.hist = [0]
        self.say(msg if msg is not None else self._intro())

    def _intro(self):
        return {
            0: "Press CLOCK. Q0 toggles every pulse; each later stage is clocked by the one before it, so the change RIPPLES along.",
            1: "A down counter clocks each stage from the Q' output of the stage before it. Press CLOCK and watch it count backwards.",
            2: "All flip-flops share ONE clock. T inputs decide who toggles: T0 = 1, T1 = Q0, T2 = Q0·Q1, and so on.",
            3: "Like the up counter but the T inputs use Q': a stage toggles when every lower bit is 0.",
            4: f"MOD-{self.N}: a ripple counter that is cleared by a gate when it reaches {self.N}. Change N with UP / DOWN.",
            5: f"DESIGN a MOD-{self.N} synchronous counter. The state table gives the flip-flop inputs, the equations come from simplifying them.",
        }[self.view]

    def set_view(self, i):
        self.view = i % len(self.VIEWS)
        self.reset()

    def change_n(self, d):
        if self.view < 4:
            return
        self.N = max(self.N_MIN, min(self.N_MAX, self.N + d))
        self.reset()

    def toggle_ff(self):
        if self.view == 5:
            self.ff = "JK" if self.ff == "T" else "T"
            self.reset(f"Now designing with {self.ff} flip-flops.")

    # ---- counting -----------------------------------------------------------
    def clock(self):
        prev = self.cnt
        mod = self.modulus()
        self.cnt = (prev - 1) % mod if self.is_down() else (prev + 1) % mod
        self.steps += 1
        self.last = (prev, self.cnt)
        self.hist.append(self.cnt)
        self.hist = self.hist[-40:]
        self.say(self._explain(prev, self.cnt))

    def _ripple(self, prev, new):
        cur, seq = prev, []
        for i in range(self.nb() + 1):
            if ((prev >> i) & 1) != ((new >> i) & 1):
                cur ^= 1 << i
                seq.append(cur)
            else:
                break
        return seq

    def _explain(self, prev, new):
        v, nb, n = self.view, self.nb(), self.steps
        b = lambda s: format(s, f"0{nb}b")
        head = f"CLOCK {n}: {prev} ({b(prev)}) -> {new} ({b(new)})."
        if v in (0, 1, 4):
            if v == 4 and not self.natural() and prev == self.N - 1:
                trans = self._ripple(prev, self.N)
                path = ", ".join(format(t, f"0{nb}b") for t in trans)
                ones = [f"Q{i}" for i in range(nb) if (self.N >> i) & 1][::-1]
                return (head + f" The count ripples up to {self.N} ({path}). For a moment the "
                        f"state is {self.N}: the NAND of {', '.join(ones)} goes low and CLEARS "
                        "every flip-flop to 0. That brief extra state is a glitch.")
            trans = self._ripple(prev, new)
            if v == 1:
                rule = (" Down count: the next clock is Q', so a stage toggles when "
                        "the one before it rises from 0 to 1 (a borrow).")
            else:
                rule = (" Q0 toggles every pulse. A later stage toggles when the stage "
                        "before it falls from 1 to 0.")
            if len(trans) > 1:
                path = ", ".join(format(t, f"0{nb}b") for t in trans[:-1])
                rip = (f" RIPPLE: the outputs pass through {path} before settling at "
                       f"{b(new)}, one stage delay at a time.")
            else:
                rip = " Only Q0 changed, so there is no ripple."
            return head + rule + rip
        if v in (2, 3):
            word = "0" if self.is_down() else "1"
            return (head + " Every flip-flop sees the clock at the same instant. A stage "
                    f"toggles only if its T input is 1, which needs all lower bits to be "
                    f"{word}. No ripple, so no in-between states.")
        # design view
        row = self.design()["rows"][prev]
        parts = []
        for i in range(nb - 1, -1, -1):
            val = row[2][i]
            parts.append(f"T{i}={val}" if self.ff == "T" else f"J{i}={val[0]} K{i}={val[1]}")
        extra = ("Only flip-flops with T = 1 toggle." if self.ff == "T"
                 else "J = 1 sets, K = 1 resets, X means don't care.")
        return head + " Inputs from the table: " + ", ".join(parts) + ". " + extra

    # ---- design view -------------------------------------------------------------
    def design(self):
        key = (self.N, self.ff)
        if key in self._design_cache:
            return self._design_cache[key]
        N, nb = self.N, max(2, (self.N - 1).bit_length())
        rows = []
        for s in range(N):
            nxt = (s + 1) % N
            per = []
            for i in range(nb):
                q, qn = (s >> i) & 1, (nxt >> i) & 1
                per.append(str(q ^ qn) if self.ff == "T" else self.JK_EXC[(q, qn)])
            rows.append((s, nxt, per))
        unused = set(range(N, 2 ** nb))
        eqs = []
        for i in range(nb - 1, -1, -1):
            if self.ff == "T":
                ones = {s for s, _n, per in rows if per[i] == "1"}
                dc = unused
                eqs.append((f"T{i}", minimal_sop(ones, dc, nb)))
            else:
                for pos, name in ((0, "J"), (1, "K")):
                    ones = {s for s, _n, per in rows if per[i][pos] == "1"}
                    dc = {s for s, _n, per in rows if per[i][pos] == "X"} | unused
                    eqs.append((f"{name}{i}", minimal_sop(ones, dc, nb)))
        result = {"rows": rows, "eqs": eqs, "nb": nb}
        self._design_cache[key] = result
        return result

    # ---- keys ---------------------------------------------------------------------
    def handle_key(self, event):
        key = event.key
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.clock()
            return True
        if key == pygame.K_r:
            self.reset()
            return True
        if key == pygame.K_a:
            self.toggle_auto()
            return True
        if key == pygame.K_LEFT:
            self.set_view(self.view - 1)
            return True
        if key == pygame.K_RIGHT:
            self.set_view(self.view + 1)
            return True
        if key in (pygame.K_UP, pygame.K_w):
            self.change_n(1)
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self.change_n(-1)
            return True
        if key == pygame.K_f:
            self.toggle_ff()
            return True
        return False

    # ---- drawing --------------------------------------------------------------------
    def draw(self, screen, content, limit_y, ui):
        self.buttons = []
        self._tick_auto(self.clock)
        self._clip(screen, content, limit_y)
        X, Y, w = content.x, content.y, content.width
        v = self.view

        tag = ["ASYNCHRONOUS (RIPPLE) UP", "ASYNCHRONOUS (RIPPLE) DOWN",
               "SYNCHRONOUS UP", "SYNCHRONOUS DOWN",
               f"MOD-{self.N} ASYNCHRONOUS", f"MOD-{self.N} SYNC DESIGN"][v]
        self._header(screen, ui, content, "COUNTERS", tag,
                     MAROON if v >= 4 else DARK_GREEN)
        self._tabs(screen, ui, content, self.VIEWS, v, self.set_view, Y + 40)

        panel = pygame.Rect(X + 3, Y + 70, w - 6, 156)
        pygame.draw.rect(screen, PANEL, panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)
        self._draw_panel(screen, ui, panel)

        # controls
        cy = panel.bottom + 6
        specs = [("CLOCK [SPACE]", self.clock, 140, False),
                 ("RESET [R]", self.reset, 104, False),
                 ("AUTO [A]", self.toggle_auto, 96, self.auto)]
        x = self._row_buttons(screen, ui, X + 3, cy, specs)
        if v >= 4:
            self._button(screen, ui, pygame.Rect(x, cy, 40, 28), "N-",
                         (lambda: self.change_n(-1)))
            s = ui["small"].render(f"N = {self.N}", False, INK)
            screen.blit(s, (x + 46, cy + 6))
            self._button(screen, ui, pygame.Rect(x + 122, cy, 40, 28), "N+",
                         (lambda: self.change_n(1)))
            x += 170
        if v == 5:
            self._button(screen, ui, pygame.Rect(x, cy, 130, 28),
                         f"FF: {self.ff} [F]", self.toggle_ff)

        top = cy + 36
        if v == 5:
            self._draw_design_lower(screen, ui, content, top, limit_y)
        else:
            self._draw_waves(screen, ui, content, top, limit_y)
        screen.set_clip(None)

    def _terms(self, nb):
        """T input of every stage (sync up / down)."""
        bits = [(self.cnt >> i) & 1 for i in range(nb)]
        out = []
        for i in range(nb):
            if self.is_down():
                out.append(int(all(b == 0 for b in bits[:i])))
            else:
                out.append(int(all(b == 1 for b in bits[:i])))
        return out

    def _draw_panel(self, screen, ui, panel):
        v, nb = self.view, self.nb()
        sync, down = self.is_sync(), self.is_down()
        bits = [(self.cnt >> i) & 1 for i in range(nb)]
        changed = set()
        if self.last:
            changed = {i for i in range(nb)
                       if ((self.last[0] >> i) & 1) != ((self.last[1] >> i) & 1)}

        bw, bh, gap = 72, 52, 44
        x0 = panel.x + 96
        by = panel.y + 40
        boxes = [pygame.Rect(x0 + i * (bw + gap), by, bw, bh) for i in range(nb)]
        pin_in, pin_clk = by + 14, by + 40
        clk = pygame.Rect(panel.x + 10, by + 28, 56, 24)

        # top labels (the T / J K inputs)
        if v == 5:
            row = self.design()["rows"][self.cnt][2]
            labels = [f"T{i}={row[i]}" if self.ff == "T"
                      else f"J{i}={row[i][0]} K{i}={row[i][1]}" for i in range(nb)]
        elif sync:
            t = self._terms(nb)
            labels = [f"T{i}={t[i]}" for i in range(nb)]
        else:
            labels = ["T=1"] * nb

        # wires
        if sync:
            rail = by + bh + 20
            pygame.draw.line(screen, WIRE, (clk.right, pin_clk),
                             (boxes[0].x - 12, pin_clk), 3)
            for b in boxes:
                sx = b.x - 12
                pygame.draw.line(screen, WIRE, (sx, rail), (sx, pin_clk), 3)
                pygame.draw.line(screen, WIRE, (sx, pin_clk), (b.x, pin_clk), 3)
            pygame.draw.line(screen, WIRE, (boxes[0].x - 12, rail),
                             (boxes[-1].x - 12, rail), 3)
        else:
            pygame.draw.line(screen, WIRE, (clk.right, pin_clk), (boxes[0].x, pin_clk), 3)
            for i in range(nb - 1):
                b = boxes[i]
                mx = b.right + gap // 2
                pygame.draw.lines(screen, WIRE, False,
                                  [(b.right, pin_in), (mx, pin_in), (mx, pin_clk),
                                   (boxes[i + 1].x, pin_clk)], 3)
                s = ui["tiny"].render("Q'" if down else "Q", False, MUTED)
                screen.blit(s, (b.right + 3, pin_in - 15))
        for b in boxes:
            pygame.draw.line(screen, WIRE, (b.x - 12, pin_in), (b.x, pin_in), 3)

        # clock button
        pygame.draw.rect(screen, DARK, clk)
        pygame.draw.rect(screen, CYAN, clk, 3)
        s = ui["small"].render("CLK", False, WHITE)
        screen.blit(s, s.get_rect(center=clk.center))
        self._hit(clk, self.clock)

        # flip-flops
        for i, b in enumerate(boxes):
            on = bits[i]
            tc = INK if on else WHITE
            self._box(screen, ui, b, str(on), fill=LIT if on else DARK,
                      edge=(AMBER if i in changed else CYAN), big_color=tc)
            if i in changed:
                pygame.draw.rect(screen, AMBER, b, 4)
            screen.blit(ui["tiny"].render("T" if self.ff == "T" or v != 5 else "JK",
                                          False, tc), (b.x + 5, pin_in - 6))
            self._clock_pin(screen, b.x, pin_clk, tc)
            s = ui["tiny"].render("Q", False, tc)
            screen.blit(s, s.get_rect(topright=(b.right - 5, pin_in - 6)))
            screen.blit(ui["tiny"].render(labels[i], False, INK), (b.x - 6, by - 17))
            s = ui["tiny"].render(f"Q{i}", False, INK)
            screen.blit(s, s.get_rect(midtop=(b.centerx, b.bottom + 3)))

        # readout
        rx = boxes[-1].right + 34
        screen.blit(ui["tiny"].render("COUNT", False, MUTED), (rx, panel.y + 12))
        big = ui["fit"](str(self.cnt), panel.right - rx - 8, 34, INK)
        screen.blit(big, (rx, panel.y + 28))
        word = format(self.cnt, f"0{nb}b")
        screen.blit(ui["tiny"].render(
            "Q" + str(nb - 1) + "..Q0 = " + word, False, MAROON), (rx, panel.y + 74))

        # info text
        if v == 0:
            info = "Every stage toggles (T = 1). Clock of each stage = Q of the stage before."
        elif v == 1:
            info = "Every stage toggles (T = 1). Clock of each stage = Q' of the stage before."
        elif v in (2, 3):
            parts = ["T0 = 1"]
            for i in range(1, nb):
                lits = [f"Q{j}'" if down else f"Q{j}" for j in range(i)]
                parts.append(f"T{i} = " + "·".join(lits))
            info = "   ".join(parts)
        elif v == 4:
            if self.natural():
                info = (f"{self.N} = 2^{nb}: the counter wraps by itself, so no reset "
                        "gate is needed. Try another N.")
            else:
                ones = [f"Q{i}" for i in range(nb) if (self.N >> i) & 1][::-1]
                info = (f"Counts 0 to {self.N - 1}. CLEAR = ({'·'.join(ones)})': when the "
                        f"count reaches {self.N} ({format(self.N, f'0{nb}b')}) it resets all stages.")
        else:
            info = (f"MOD-{self.N} needs {nb} flip-flops (2^{nb} >= {self.N}). Inputs shown "
                    "above are for the CURRENT state.")
        yy = panel.y + 122
        for line in ui["wrap"](info, panel.width - 20, ui["tiny"])[:2]:
            screen.blit(ui["tiny"].render(line, False, DARK_GREEN), (panel.x + 10, yy))
            yy += 15

    def _draw_waves(self, screen, ui, content, top, limit_y):
        X = content.x
        nb = self.nb()
        screen.blit(ui["tiny"].render(
            "TIMING DIAGRAM: " + ("each stage changes a little later (ripple delay)"
                                  if not self.is_sync()
                                  else "all stages change together"),
            False, INK), (X + 3, top))
        rows, row_h = 1 + nb, 17
        show = self.hist[-12:]
        cols = len(show)
        first = self.steps - (cols - 1)
        wx0, step_w, ry0 = _timing_frame(screen, ui, content, top + 26, rows, row_h,
                                         cols, first)
        _clock_wave(screen, wx0, ry0, row_h, step_w, first, cols, (0, 120, 140))
        screen.blit(ui["tiny"].render("CLK", False, (0, 120, 140)), (X + 8, ry0 + 3))
        for i in range(nb):
            ry = ry0 + (1 + i) * row_h
            col = MAROON if i == nb - 1 else DARK_GREEN
            screen.blit(ui["tiny"].render(f"Q{i}", False, col), (X + 8, ry + 3))
            delay = 5 if self.is_sync() else 5 * (i + 1)
            vals = [(c >> i) & 1 for c in show]
            pts = [(wx0, _level_y(ry, row_h, vals[0]))]
            for k in range(1, cols):
                if vals[k] != vals[k - 1]:
                    ex = wx0 + k * step_w + delay
                    pts += [(ex, _level_y(ry, row_h, vals[k - 1])),
                            (ex, _level_y(ry, row_h, vals[k]))]
            pts.append((wx0 + cols * step_w, _level_y(ry, row_h, vals[-1])))
            pygame.draw.lines(screen, col, False, pts, 2)
        self._message(screen, ui, content, top + 26 + rows * row_h + 12, limit_y)

    def _draw_design_lower(self, screen, ui, content, top, limit_y):
        X = content.x
        d = self.design()
        nb, rows = d["nb"], d["rows"]
        screen.blit(ui["tiny"].render(
            f"STATE TABLE ({self.ff} flip-flops). X = don't care", False, MUTED), (X + 3, top))
        avail = limit_y - (top + 18) - 18
        rh = max(12, min(16, avail // (len(rows) + 1)))
        cols_w = [70, 70] + [(46 if self.ff == "JK" else 40)] * nb
        heads = ["Q" + str(nb - 1) + "..Q0", "NEXT"]
        for i in range(nb - 1, -1, -1):
            heads.append(f"T{i}" if self.ff == "T" else f"J{i}K{i}")
        ty = top + 16
        tx = X + 3
        for c, head in enumerate(heads):
            cell = pygame.Rect(tx + sum(cols_w[:c]), ty, cols_w[c], rh)
            pygame.draw.rect(screen, HILITE if c >= 2 else PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)
            s = ui["tiny"].render(head, False, INK)
            screen.blit(s, s.get_rect(center=cell.center))
        for r, (s_, nxt, per) in enumerate(rows):
            active = s_ == self.cnt
            vals = [format(s_, f"0{nb}b"), format(nxt, f"0{nb}b")]
            for i in range(nb - 1, -1, -1):
                vals.append(per[i] if self.ff == "T" else per[i][0] + " " + per[i][1])
            for c, val in enumerate(vals):
                cell = pygame.Rect(tx + sum(cols_w[:c]), ty + (r + 1) * rh, cols_w[c], rh)
                pygame.draw.rect(screen, HILITE if active else PAPER, cell)
                pygame.draw.rect(screen, CYAN if active else PAGE_LINE, cell,
                                 2 if active else 1)
                s = ui["tiny"].render(val, False, INK)
                screen.blit(s, s.get_rect(center=cell.center))
        used = ty + (len(rows) + 1) * rh + 3
        if self.N < 2 ** nb:
            note = f"States {self.N}-{2 ** nb - 1} never occur: don't cares."
            screen.blit(ui["tiny"].render(note, False, MUTED), (tx, used))

        # equations + message on the right
        ex = tx + sum(cols_w) + 18
        ew = content.right - ex - 3
        screen.blit(ui["tiny"].render("SIMPLIFIED EQUATIONS", False, MUTED), (ex, top))
        yy = top + 16
        for name, expr in d["eqs"]:
            if yy + 17 > limit_y:
                break
            line = ui["fit"](f"{name} = {expr}", ew, 16, DARK_GREEN)
            screen.blit(line, (ex, yy))
            yy += 18
        yy += 6
        for line in ui["wrap"](self.msg, ew, ui["tiny"]):
            if yy + 15 > limit_y:
                break
            screen.blit(ui["tiny"].render(line, False, DARK_GREEN), (ex, yy))
            yy += 15


# ============================================================
# NOTES (text pages, same format as the other topics)
# ============================================================

def flipflop_notes_lines():
    return [
        "WHAT IS A FLIP-FLOP?",
        "- A memory cell that stores ONE bit (Q) and updates only at the clock edge.",
        "- Q' is always the opposite of Q.",
        "- Between clock edges it ignores its inputs and holds its value.",
        "- The next value is called Q+ (Q after the clock).",
        "S-R FLIP-FLOP",
        "- S = 0, R = 0: HOLD (Q+ = Q).",
        "- S = 0, R = 1: RESET (Q+ = 0).",
        "- S = 1, R = 0: SET (Q+ = 1).",
        "- S = 1, R = 1: FORBIDDEN, the result is undefined.",
        "- Equation: Q+ = S + R'Q, with S·R = 0.",
        "J-K FLIP-FLOP",
        "- J acts like S and K acts like R, but J = K = 1 is allowed.",
        "- J = K = 1 TOGGLES: Q+ = Q'.",
        "- Equation: Q+ = JQ' + K'Q.",
        "- Problem: with the clock held high, a toggling J-K can toggle again and again. This is RACE-AROUND.",
        "D FLIP-FLOP",
        "- Q+ = D. It just copies D at the clock edge.",
        "- Used as the basic building block of registers.",
        "T FLIP-FLOP",
        "- T = 0: HOLD. T = 1: TOGGLE.",
        "- Equation: Q+ = T XOR Q = TQ' + T'Q.",
        "- It is a J-K with J and K tied together. It is the heart of counters.",
        "MASTER-SLAVE J-K",
        "- Two latches in a row. The MASTER is open while CLK = 1. The SLAVE is open while CLK = 0.",
        "- The master works out the J-K result, the slave passes it to Q on the falling edge.",
        "- Q changes only once per pulse, which cures race-around.",
        "EXCITATION TABLES (what inputs you need for Q -> Q+)",
        "- S-R: 0->0 is S=0 R=X, 0->1 is S=1 R=0, 1->0 is S=0 R=1, 1->1 is S=X R=0.",
        "- J-K: 0->0 is J=0 K=X, 0->1 is J=1 K=X, 1->0 is J=X K=1, 1->1 is J=X K=0.",
        "- D: D = Q+.     T: T = Q XOR Q+.",
        "- X means don't care: the input can be 0 or 1.",
        "CONVERSION OF FLIP-FLOPS",
        "- Goal: make the flip-flop you HAVE behave like the one you WANT.",
        "- Step 1: write the truth table of the WANTED flip-flop (inputs, Q, Q+).",
        "- Step 2: for every Q -> Q+ move, look up the inputs the flip-flop you HAVE needs (excitation table).",
        "- Step 3: simplify (K-map) to get the equations of the logic between them.",
        "- Examples: J-K to T is J = K = T. J-K to D is J = D and K = D'. S-R to D is S = D and R = D'.",
        "- D to T is D = T XOR Q. T to D is T = D XOR Q.",
        "TIP",
        "- Open the lab (T). Set inputs by clicking them, press CLOCK and watch the table row light up.",
    ]


def shift_notes_lines():
    return [
        "WHAT IS A SHIFT REGISTER?",
        "- A row of flip-flops sharing one clock. Each clock pulse moves every bit one place.",
        "- This lab uses 4 D flip-flops Q0 Q1 Q2 Q3 and shifts to the RIGHT.",
        "- D0 = serial input, D1 = Q0, D2 = Q1, D3 = Q2.",
        "SERIAL-IN SERIAL-OUT (SISO)",
        "- One bit goes in per clock at Q0, one bit comes out per clock at Q3.",
        "- A 4-bit word needs 4 clocks to go in and 4 more to come out.",
        "- Use: a delay line. The output is the input, 4 clocks later.",
        "SERIAL-IN PARALLEL-OUT (SIPO)",
        "- Bits enter one at a time, but all of Q0..Q3 are available together.",
        "- After 4 clocks the whole word can be read at once.",
        "- Use: turning a serial line into a parallel word (receiver).",
        "PARALLEL-IN SERIAL-OUT (PISO)",
        "- Each flip-flop has a MUX in front: D = LOAD·P + LOAD'·(previous Q).",
        "- LOAD = 1: all four bits are loaded in ONE clock.",
        "- LOAD = 0: the register shifts and the word leaves one bit per clock at Q3.",
        "- Use: turning a parallel word into a serial line (transmitter).",
        "PARALLEL-IN PARALLEL-OUT (PIPO)",
        "- All four bits load at the same clock and appear at Q0..Q3 together.",
        "- No shifting is needed. It is simply a 4-bit storage register.",
        "COMPARING THE FOUR",
        "- Speed to load a word: PIPO and PISO 1 clock, SISO and SIPO 4 clocks.",
        "- Speed to read a word: PIPO and SIPO instantly, SISO and PISO 4 clocks.",
        "TIMING",
        "- Each column of the timing diagram is one pulse. The bit at Q0 appears at Q1 one pulse later, at Q2 two pulses later and so on.",
        "TIP",
        "- Open the lab (T). Click SI or P0-P3, press CLOCK or turn AUTO on, and watch the bits travel.",
    ]


def counter_notes_lines():
    return [
        "WHAT IS A COUNTER?",
        "- Flip-flops wired so that the Q outputs count clock pulses in binary.",
        "- n flip-flops count 2^n states: 0 to 2^n - 1. This is a MOD-2^n counter.",
        "ASYNCHRONOUS (RIPPLE) UP COUNTER",
        "- Every flip-flop is a T flip-flop with T = 1 (or a J-K with J = K = 1).",
        "- The clock goes only to Q0. Each later flip-flop is clocked by the Q of the one before it.",
        "- Q0 toggles every pulse, Q1 toggles when Q0 falls, and so on.",
        "- The change ripples, so each stage adds one propagation delay.",
        "- Fast clocks cause wrong in-between values (for example 0111 -> 0110 -> 0100 -> 0000 -> 1000).",
        "ASYNCHRONOUS DOWN COUNTER",
        "- Same circuit but each stage is clocked by Q' of the stage before.",
        "- It counts 15, 14, 13 ... 0 and then wraps back to 15.",
        "DESIGN OF AN ASYNCHRONOUS MOD-N COUNTER",
        "- Choose n so that 2^n >= N.",
        "- Build an n-bit ripple counter.",
        "- Find the first count equal to N and write it in binary.",
        "- AND (NAND) the flip-flops that are 1 in N. Connect the NAND output to every CLEAR input.",
        "- When the count reaches N, the NAND goes low, clears the counter to 0 and the counter keeps going.",
        "- Example, MOD-10: N = 10 = 1010, so CLEAR = (Q3·Q1)'.",
        "- State N appears for a very short time (a glitch).",
        "SYNCHRONOUS COUNTERS",
        "- All flip-flops get the SAME clock, so they change together and there is no ripple.",
        "- With T flip-flops (up): T0 = 1, T1 = Q0, T2 = Q0·Q1, T3 = Q0·Q1·Q2.",
        "- Down counter: use the complements: T1 = Q0', T2 = Q0'·Q1' and so on.",
        "- It can run faster than a ripple counter, but needs extra AND gates.",
        "DESIGN OF A SYNCHRONOUS COUNTER",
        "- Step 1: list the present states and the next states (the count sequence).",
        "- Step 2: for each flip-flop, write the inputs needed for each Q -> Q+ move (excitation table).",
        "- Step 3: states that never occur are DON'T CARES.",
        "- Step 4: simplify each input with a K-map to get its equation.",
        "- Step 5: draw the circuit: flip-flops, one common clock, and the gates for the equations.",
        "- T flip-flop: T = Q XOR Q+. J-K flip-flop: use J K = 0X, 1X, X1, X0 for 0->0, 0->1, 1->0, 1->1.",
        "TIP",
        "- Open the lab (T). Compare ASYNC and SYNC timing diagrams, then try MOD-N SYNC and switch between T and JK flip-flops.",
    ]


class DetectiveNotebook:

    LEVELS = [
        ("level_one", "LEVEL ONE", "Logic Lock"),
        ("level_two", "LEVEL TWO", "Hidden Transmission"),
        ("level_three", "LEVEL THREE", "Memory Protocol"),
        ("level_four", "LEVEL FOUR", "Final Override"),
        ("level_five", "LEVEL FIVE", "Logic Architect"),
        ("level_six", "LEVEL SIX", "Signal Breaker"),
    ]

    # Plain-language excerpts from the scientist's case notes. They are shown
    # when the relevant level becomes unlocked, before the detective solves it.
    # Every new word is explained the first time it is used.
    SCIENTIST_NOTES = {
        "level_one": [
            "Lab log: Entry 01",
            "A LOGIC GATE is a tiny decision box. It gets switches that are ON (1) or OFF (0), and decides if its answer is ON or OFF.",
            "Think of a door that opens only if BOTH keys are turned. That rule is called an AND gate.",
            "The lock should work like AND, but the AI says DENIED. Test all 4 switch combinations (00, 01, 10, 11) and write down the lock's answer each time.",
            "A list of every input and its answer is called a TRUTH TABLE. Practise one in TEST THE LOGIC > LOGIC GATES.",
        ],
        "level_two": [
            "Lab log: Entry 02",
            "Computers write numbers with only 0 and 1. That is called BINARY. Each 0 or 1 is one BIT. Example: 101 means 4 + 0 + 1 = 5.",
            "Some numbers on the terminal are in GRAY CODE. It is binary written a special way, so each number differs from the next in only ONE bit.",
            "To read the message: first turn each Gray code into normal binary, then turn that binary into a normal number. Keep the original order.",
            "Do not do it in your head. TEST THE LOGIC > NUMBER SYSTEMS shows every step. Forgot a word? See WORDS TO KNOW.",
        ],
        "level_three": [
            "Lab log: Entry 03",
            "A STATE is where the machine is right now, like a traffic light being RED or GREEN. This machine has states named A, B, C and D.",
            "It works like a board game. You stand on a square (the state). You get an INPUT (0 or 1). A rule table says which square to move to next.",
            "For every step write three things: where am I, what is the input, where do I go next. Follow the table row by row.",
            "One wrong step and the machine never reaches the safe state. Read about it in TEST THE LOGIC > STATE MACHINES.",
        ],
        "level_four": [
            "Lab log: Entry 04",
            "A BOOLEAN EXPRESSION is a short sentence about switches, like 'A AND B'. Two expressions can look different but do exactly the same job.",
            "The AI shows me an expression that looks right, but I do not trust it. It may only look similar.",
            "To check, try EVERY switch combination and compare the results with the original. If even one row is different, it is a fake.",
            "The rules for rewriting an expression (like DE MORGAN'S LAW) are in TEST THE LOGIC > BOOLEAN ALGEBRA. You can also build it there.",
        ],
        "level_five": [
            "Lab log: Entry 05",
            "A CIRCUIT is gates joined by wires. The alarm needs one. The formula F = ... is the recipe that says when the alarm should turn ON.",
            "Build it like LEGO: switches on the left, gates in the middle, the last gate wired into the alarm lamp on the right.",
            "Then flip the switches and check the lamp against the formula. Fewer gates is better. A Karnaugh map (see the notebook) can make the formula shorter first.",
        ],
        "level_six": [
            "Lab log: Entry 06",
            "The last message is SCRAMBLED, which means hidden with a secret code. To scramble, flip some bits using a secret pattern. Flip again with the SAME pattern and the message comes back.",
            "The machine makes that secret pattern. It is a row of 5 boxes (a REGISTER), each holding 0 or 1. On every CLOCK pulse, all bits move one box right and a new bit enters on the left.",
            "The new bit comes from the boxes marked TAP. Their bits are mixed with XOR (same = 0, different = 1). The 5 bits the machine starts with are the SEED.",
            "A short test message shows if the machine is set up correctly. Pulse one step at a time and match it first. Only then unscramble the real message.",
            "Scramble example: 1011 XOR 0110 = 1101. Then 1101 XOR 0110 = 1011. Practise in TEST THE LOGIC > REGISTERS AND LFSRs.",
        ],
    }

    # One plain sentence: what the player has to achieve.
    LEVEL_GOALS = {
        "level_one": "Find out what the lock really does for all 4 switch combinations, and make it behave like AND.",
        "level_two": "Turn the Gray-code numbers into normal decimal numbers, in the right order.",
        "level_three": "Follow the machine one step at a time until it reaches the safe state.",
        "level_four": "Find which expression gives the SAME answers as the original on every row.",
        "level_five": "Build the alarm circuit so the lamp matches the formula F for every switch combination.",
        "level_six": "Set the SEED and TAPS so the machine matches the test message, then unscramble the real message.",
    }

    # Hints go from gentle to strong. The player reveals them one at a time.
    LEVEL_HINTS = {
        "level_one": [
            "Start small. A gate has 2 switches, so there are only 4 combinations. Write them in a list: 00, 01, 10, 11.",
            "For each combination ask: is the lock ON? An AND gate is ON only when BOTH switches are 1.",
            "Your 4 answers, in order, make a pattern of 0s and 1s. For AND, only the LAST answer is 1.",
        ],
        "level_two": [
            "Take the numbers one at a time. Look at the Gray code first and convert it. Ignore the rest until that works.",
            "Gray to binary: copy the first bit. Each next binary bit = the previous binary bit XOR this Gray bit. (XOR: same = 0, different = 1.)",
            "Example: Gray 1000 gives 1, then 1^0=1, 1^0=1, 1^0=1, so binary 1111 = 15. Now do yours and keep the original order.",
        ],
        "level_three": [
            "Find the row for your current state in the table. Then look at the column for the input. That cell is the next state.",
            "Write each step like this: A, input 1, go to B. Keep the list of states you visit, in order.",
            "If a state has no rule for the input, you took a wrong turn earlier. Go back one step and check it again.",
        ],
        "level_four": [
            "Do not judge by how an expression looks. Make a table with one row for every input combination.",
            "Work out the original expression on each row first. Then do the same for the other one. The laws in BOOLEAN ALGEBRA help you simplify.",
            "De Morgan's law: break the bar and swap AND with OR. (AB)' = A' + B' and (A+B)' = A'B'. Use it when a bar covers a whole bracket.",
            "XNOR is the opposite of XOR: it is 1 when two inputs MATCH, so A XNOR B = AB + A'B'. If even one row differs, that expression is a fake.",
        ],
        "level_five": [
            "First list every input combination where the alarm must be ON. Mark those cells 1 on the Karnaugh map.",
            "Circle the 1s in the biggest rectangles of 1, 2, 4 or 8 cells. The map wraps around the edges. Fewer, bigger groups mean fewer gates.",
            "Each group is one term. A letter that stays 1 is kept, one that stays 0 gets a bar ('), and one that changes is dropped. Join the terms with OR.",
        ],
        "level_six": [
            "Do not decode the real message yet. First make the machine produce the test message pattern.",
            "Each pulse: XOR the TAP cells, shift every bit one cell to the right, put the new bit in CELL 1. The bit leaving CELL 5 is the OUTPUT.",
            "Write the 5 cells down after every pulse. If the output does not match the test message, change the SEED or the TAPS and start again.",
            "When it matches, XOR the real scrambled message with the same output bits, one bit at a time.",
        ],
    }

    # Which TEST THE LOGIC topic belongs to each level.
    LEVEL_PRACTICE = {
        "level_one": "LOGIC GATES",
        "level_two": "NUMBER SYSTEMS",
        "level_three": "STATE MACHINES",
        "level_four": "BOOLEAN ALGEBRA",
        "level_five": "KARNAUGH MAPS",
        "level_six": "REGISTERS AND LFSRs",
    }

    DEFAULT_FINDINGS = {
        "level_one": [
            "The lock was built from basic logic gates. I checked the truth table and restored the required AND behaviour.",
            "Recorded answer: AND truth table output 0001 (for inputs 00, 01, 10, 11).",
        ],
        "level_two": [
            "I decoded the intercepted number sequence by checking the number-system conversions and preserving the recovered order.",
            "Recorded sequence: 3, 5, 9, 14, 3, 5, 8, 12.",
        ],
        "level_three": [
            "I traced the memory protocol one transition at a time and compared each state against the required sequence until the state machine advanced correctly.",
            "Recorded state sequence: A-B-A-C-D-C.",
        ],
        "level_four": [
            "I tested the override expression against the original Boolean function instead of trusting the terminal's claim. The accepted form had to match for every required input combination.",
            "Recorded bomb-risk value: 10.",
            "Recorded equivalent expression: Y = A'B' + (C XNOR D) (as written in the recovered clue).",
        ],
        "level_five": [
            "I rebuilt the vault-alarm logic using the available two-input gates, then checked the output against the required function rather than relying on the wire layout.",
            "Required function: F = B'D' + BD + C'D'.",
        ],
        "level_six": [
            "I restored the five-cell signal register, set the seed, connected the feedback path, and checked the generated stream against the intercepted header before unscrambling the message.",
            "Recovered key: K7. Register seed: 01101.",
        ],
    }

    # Goal expressions for the Boolean Algebra lab (TEST mode). "f" takes the
    # input bits in the order of "vars" and returns the required output.
    BOOL_GOALS = [
        {"expr": "A'B + AB'", "vars": ["A", "B"],
         "f": lambda a, b: ((1 - a) & b) | (a & (1 - b))},
        {"expr": "(A·B)'", "vars": ["A", "B"],
         "f": lambda a, b: 1 - (a & b)},
        {"expr": "A + A'B", "vars": ["A", "B"],
         "f": lambda a, b: a | ((1 - a) & b)},
        {"expr": "A'B' + AB", "vars": ["A", "B"],
         "f": lambda a, b: ((1 - a) & (1 - b)) | (a & b)},
        {"expr": "(A + B)·C'", "vars": ["A", "B", "C"],
         "f": lambda a, b, c: (a | b) & (1 - c)},
        {"expr": "AB + C", "vars": ["A", "B", "C"],
         "f": lambda a, b, c: (a & b) | c},
        {"expr": "(A XOR B)·C", "vars": ["A", "B", "C"],
         "f": lambda a, b, c: (a ^ b) & c},
        {"expr": "A'B'C + ABC'", "vars": ["A", "B", "C"],
         "f": lambda a, b, c: ((1 - a) & (1 - b) & c) | (a & b & (1 - c))},
    ]
    BOOL_PALETTE = ["AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR"]
    BOOL_MAX_GATES = 10
    # SIMULATE mode: the player picks how many input switches (A, B, C, D).
    BOOL_MIN_VARS = 2
    BOOL_MAX_VARS = 4
    BOOL_VAR_NAMES = "ABCD"

    # Karnaugh map lab: rows are AB and columns are CD in Gray-code order.
    KM_GRAY = [0, 1, 3, 2]
    KM_LABELS = ["00", "01", "11", "10"]
    KM_VARS = "ABCD"
    KM_COLOURS = [
        (200, 40, 60), (210, 140, 0), (0, 130, 190),
        (130, 60, 200), (30, 150, 80), (210, 60, 150),
    ]
    # Simulate-mode examples: (name, ones, don't-cares)
    KM_EXAMPLES = [
        ("1s at m13, m14, m15", {13, 14, 15}, set()),
        ("A=1, B=1, C=1 (m14, m15)", {14, 15}, set()),
        ("the four corners (wraparound)", {0, 2, 8, 10}, set()),
        ("whole bottom half: A=1", {8, 9, 10, 11, 12, 13, 14, 15}, set()),
        ("two separate groups", {0, 1, 8, 9, 6, 7, 14, 15}, set()),
        ("using X (don't-care) cells", {3, 7, 11}, {15, 2}),
    ]
    # Test-mode maps: the player groups them. (None of these is Level 5.)
    KM_TESTS = [
        {"ones": {5, 7, 13, 15}, "dc": set()},
        {"ones": {0, 2, 8, 10}, "dc": set()},
        {"ones": {12, 13, 14, 15}, "dc": set()},
        {"ones": {1, 3, 5, 7, 9, 11}, "dc": set()},
        {"ones": {2, 3, 6, 7, 10}, "dc": {11, 14}},
        {"ones": {0, 1, 4, 5, 6, 14}, "dc": {7}},
    ]

    # --------------------------------------------------------
    # STATE MACHINE LAB DATA
    # --------------------------------------------------------
    # A tiny machine that works exactly like the Level 3 lock:
    #   RED (start) --A--> AMBER --B--> BLUE --C--> GREEN
    # Pressing A always starts a fresh ball at AMBER. Any other wrong
    # button drops the machine back to RED.
    SM_STATES = ["RED", "AMBER", "BLUE", "GREEN"]
    SM_COLOURS = {
        "RED": (200, 50, 60),
        "AMBER": (214, 140, 20),
        "BLUE": (45, 110, 205),
        "GREEN": (40, 165, 100),
    }
    # (state the ball must be in, button needed, state it hops to)
    SM_STEPS = [
        ("RED", "A", "AMBER"),
        ("AMBER", "B", "BLUE"),
        ("BLUE", "C", "GREEN"),
    ]
    SM_BUTTONS = "ABC"
    SM_SCROLL_STEP = 30               # pixels per key press / wheel notch

    def __init__(self):
        # One source of truth for the open state.
        self.open = False

        # Compatibility with existing code that checks is_open.
        # Both attributes are kept synchronised by toggle() and close().
        self.is_open = False

        self.page = "index"
        self.selected_index = 0
        self.selected_level = None
        self.notes_scroll = 0

        self.level_status = {
            level_id: {
                "unlocked": index == 0,
                "solved": False,
                "notes": [],
            }
            for index, (level_id, _, _) in enumerate(self.LEVELS)
        }

        # Hints the player has revealed so far, per level.
        self.hints_shown = {level_id: 0 for level_id, _, _ in self.LEVELS}
        self._jump_to_hints = False

        self.reference_topics = [
            "WORDS TO KNOW",
            "LOGIC GATES",
            "NUMBER SYSTEMS",
            "STATE MACHINES",
            "BOOLEAN ALGEBRA",
            "KARNAUGH MAPS",
            "COMBINATIONAL CIRCUITS",
            "FLIP-FLOPS",
            "SHIFT REGISTERS",
            "COUNTERS",
            "REGISTERS AND LFSRs",
        ]

        # BASIC mode: stage notes are written here as the player finishes them.
        self.basic_notes_by_stage = {}
        self.game_mode = "intermediate"

        self.reference_notes = {
            # Plain-words glossary for players who are new to all of this.
            "WORDS TO KNOW": [
                "BIT",
                "- One 0 or 1. The smallest piece of information.",
                "BINARY",
                "- Writing numbers with only 0 and 1. Example: 101 = 4 + 0 + 1 = 5.",
                "INPUT AND OUTPUT",
                "- INPUT is what goes in (a switch). OUTPUT is the answer that comes out (a lamp).",
                "ON AND OFF",
                "- ON = 1 = true. OFF = 0 = false.",
                "LOGIC GATE",
                "- A tiny decision box. Inputs go in, one output comes out.",
                "- AND: ON only if ALL inputs are ON.",
                "- OR: ON if ANY input is ON.",
                "- NOT: flips ON to OFF and OFF to ON.",
                "- XOR: ON only if the two inputs are DIFFERENT.",
                "- XNOR: ON only if the two inputs MATCH.",
                "TRUTH TABLE",
                "- A list of every input combination and the output for each one.",
                "CIRCUIT",
                "- Gates joined by wires, from the switches to a lamp.",
                "GRAY CODE",
                "- Binary written so each number differs from the next by only one bit.",
                "STATE",
                "- Where a machine is right now, like RED or GREEN on a traffic light.",
                "TRANSITION",
                "- A move from one state to the next, caused by an input.",
                "CLOCK",
                "- A regular beat. Each pulse makes the machine take one step.",
                "BOOLEAN EXPRESSION",
                "- A short formula about 0s and 1s.",
                "- A' means NOT A. AB means A AND B. A+B means A OR B.",
                "EQUIVALENT",
                "- Two expressions are equivalent if they give the same output on EVERY row.",
                "DE MORGAN'S LAW",
                "- A rule for moving a NOT bar. Break the bar and swap AND with OR.",
                "- (AB)' = A' + B'   and   (A+B)' = A'B'.",
                "SIMPLIFY",
                "- Rewrite an expression with fewer gates, but the same answers.",
                "REGISTER",
                "- A row of boxes. Each box holds one bit.",
                "SEED",
                "- The 5 bits a register starts with.",
                "TAP",
                "- A box whose bit is sent into the XOR gate.",
                "FEEDBACK",
                "- The XOR result. It enters CELL 1 on the next pulse.",
                "SCRAMBLING (SECRET CODE)",
                "- Hiding a message by flipping its bits with a secret pattern.",
                "- Flip again with the same pattern and the message comes back.",
                "- The real name is CIPHER. You do not need that word to play.",
            ],
            # Keep the existing interactive Logic Gates prototype unchanged.
            "LOGIC GATES": [
                "AND: output is 1 when both inputs are 1.",
                "OR: output is 1 when at least one input is 1.",
                "NOT: output is the inverse of its input.",
                "NAND: inverse of AND.",
                "NOR: inverse of OR.",
                "XOR: output is 1 when inputs differ.",
                "XNOR: output is 1 when inputs match.",
            ],
            "NUMBER SYSTEMS": [
                "WHAT IS A NUMBER SYSTEM?",
                "- A way of writing numbers using a fixed set of digits.",
                "- The BASE is how many different digits it uses.",
                "- DECIMAL (base 10) uses 0-9. We use it every day.",
                "- BINARY (base 2) uses only 0 and 1.",
                "- HEX (base 16) uses 0-9 and A-F (A=10 ... F=15).",
                "WHAT IS BINARY?",
                "- Computers use it: a wire is OFF (0) or ON (1).",
                "- One binary digit is a BIT.",
                "- Each position has a place value, doubling to the left:",
                "  1, 2, 4, 8, 16, 32, 64, 128.",
                "- 4 bits hold 0 to 15. 8 bits hold 0 to 255.",
                "BINARY TO DECIMAL",
                "- Write the place value above each bit.",
                "- Add the place values where the bit is 1.",
                "- Example: 1010 = 8 + 2 = 10.",
                "DECIMAL TO BINARY",
                "- Divide by 2 again and again. Note each remainder.",
                "- Stop when the number reaches 0.",
                "- Read the remainders from LAST to FIRST.",
                "- Example: 13 gives remainders 1,0,1,1 -> 1101.",
                "BINARY AND HEX",
                "- Group the bits in fours. Each group is one hex digit.",
                "- Example: 1111 0101 = F5 (1111 = 15 = F, 0101 = 5).",
                "GRAY CODE",
                "- Neighbouring numbers differ by only ONE bit.",
                "- Used where a change of many bits at once is risky.",
                "GRAY TO BINARY",
                "- Copy the first bit.",
                "- Each next BINARY bit = the previous BINARY bit",
                "  XOR this GRAY bit.",
                "- Example: Gray 0110 -> 0, 0^1=1, 1^1=0, 0^0=0",
                "  -> binary 0100 = 4.",
                "BINARY TO GRAY",
                "- Copy the first bit.",
                "- Each next GRAY bit = this BINARY bit XOR the",
                "  BINARY bit before it.",
                "TIP",
                "- Open the lab (T) and convert any value to see",
                "  every step worked out for you.",
            ],
            "STATE MACHINES": [
                "WHAT IS A STATE MACHINE?",
                "- It is a machine that is always in ONE state, like a lamp that is RED, AMBER, BLUE or GREEN.",
                "- You press a button. The machine looks at its rule table and moves to its next state.",
                "THE THREE WORDS",
                "- STATE: where the machine is right now (the lamp colour).",
                "- INPUT: what you do to it (press A, B or C).",
                "- TRANSITION: the move from one state to the next.",
                "READING THE RULE TABLE",
                "- Find the row for the state you are in.",
                "- Find the column for the button you pressed.",
                "- The box where they meet is the next state.",
                "FINDING THE CODE (LEVEL 3 PROBE)",
                "- Press every button in every state and write down what happens.",
                "- Draw each result as an arrow between two states.",
                "- The shortest path of arrows from the start to the goal is the secret code.",
                "BUILDING IT WITH CIRCUITS (LEVEL 3 BUILD)",
                "- Use one memory box (a flip-flop) for each state. Only one box holds the ball at a time.",
                "- Each forward arrow becomes one AND gate. Think of it as a door guard: is the ball here, AND is the right button pressed?",
                "- If both are yes, the guard lets the ball hop into the next box.",
                "- The clock tick tells every box to update at the same moment.",
                "- A wrong button: no guard says yes, the ball vanishes, and we are back at the start.",
                "TIP",
                "- Open the lab (T). Use PREDICT to test yourself, and CIRCUIT (V) to see the guards at work.",
            ],
            "BOOLEAN ALGEBRA": [
                "BASICS",
                "- Boolean variables can only be 0 (false) or 1 (true).",
                "- AND: A·B (or AB) is 1 only when both A and B are 1.",
                "- OR: A+B is 1 when at least one input is 1.",
                "- NOT: A' reverses A; 0 becomes 1 and 1 becomes 0.",
                "- XOR: A⊕B is 1 when the inputs differ.",
                "- XNOR: A⊙B is 1 when the inputs match.",
                "- XNOR is the opposite of XOR: (A⊕B)' = A⊙B.",
                "- NAND is AND followed by NOT. NOR is OR followed by NOT.",
                "ORDER OF OPERATIONS",
                "- Brackets first, then NOT, then AND, then OR.",
                "BASIC LAWS",
                "- Identity: A+0 = A and A·1 = A.",
                "- Null: A+1 = 1 and A·0 = 0.",
                "- Idempotent: A+A = A and A·A = A.",
                "- Complement: A+A' = 1 and A·A' = 0.",
                "- Double negation: (A')' = A.",
                "- Commutative: A+B = B+A and AB = BA.",
                "- Associative: (A+B)+C = A+(B+C), same for AND.",
                "- Distributive: A(B+C) = AB + AC.",
                "- Distributive: A+BC = (A+B)(A+C).",
                "ABSORPTION LAWS",
                "- A + AB = A.",
                "- A(A + B) = A.",
                "- A + A'B = A + B.",
                "- A(A' + B) = AB.",
                "DE MORGAN'S LAWS",
                "- (A·B)' = A' + B'   (NAND = NOT A OR NOT B).",
                "- (A+B)' = A'·B'   (NOR = NOT A AND NOT B).",
                "- Break the bar, and swap AND with OR.",
                "XOR AND XNOR IN ALGEBRA",
                "- A⊕B = A'B + AB'.",
                "- A⊙B = AB + A'B'.",
                "- A⊕0 = A, A⊕1 = A', A⊕A = 0, A⊕A' = 1.",
                "FORMING A CIRCUIT FROM AN EXPRESSION",
                "- Every variable is an input switch.",
                "- Every operator in the expression becomes one gate.",
                "- Start with the innermost brackets and work outward.",
                "- The last operation feeds the output Y.",
                "- A product term like A'B is a NOT on A feeding an AND with B.",
                "- A sum of products (AB + CD) is ANDs feeding one OR.",
                "- A bar over a whole bracket is a NOT, NAND or NOR gate.",
                "CHECKING YOUR WORK",
                "- Equivalent expressions must produce the same output",
                "  for every possible input combination.",
                "- Test every row of the truth table, not just one.",
                "TIP",
                "- Open the lab (T). In SIMULATE, pick 2, 3 or 4 variables,",
                "  build any circuit and watch its equation appear. In TEST",
                "  MODE, build the circuit for each goal expression.",
            ],
            "KARNAUGH MAPS": [
                "WHAT IS A K-MAP?",
                "- A K-map is a truth table drawn as a grid.",
                "- It lets you SEE which terms can be merged,",
                "  so the equation gets shorter.",
                "- This notebook uses 4 variables: A, B, C, D (16 cells).",
                "THE GRID",
                "- Rows are AB. Columns are CD.",
                "- The order is 00, 01, 11, 10 (NOT 00, 01, 10, 11).",
                "- Why: neighbouring cells then differ by only ONE variable.",
                "- Every cell has a number, m0 to m15: the ABCD bits read",
                "  as a binary number.",
                "- Example: A=1 B=1 C=0 D=1 is 1101 = 13, so cell m13.",
                "FILLING THE MAP",
                "- Write 1 where the output is 1, and 0 everywhere else.",
                "- X means DON'T CARE: you may use it as a 1, or ignore it.",
                "GROUPING RULES",
                "- Group only 1s (and Xs). NEVER put a 0 in a group.",
                "- A group has 1, 2, 4, 8 or 16 cells. Never 3, 5, 6 or 7.",
                "- A group is a straight rectangle: no diagonals, no L-shapes.",
                "- Make every group as BIG as possible.",
                "- Groups may overlap.",
                "- The map WRAPS: left edge touches right edge, top touches",
                "  bottom, and the four corners touch each other.",
                "- Cover every 1 using as FEW groups as possible.",
                "- Xs never have to be covered.",
                "READING ONE GROUP",
                "- Look at each variable (A, B, C, D) inside the group.",
                "- It STAYS 1 in the whole group: write the letter, A.",
                "- It STAYS 0 in the whole group: write the letter with a",
                "  bar, A'.",
                "- It CHANGES inside the group: leave it out.",
                "- A group of 2 drops 1 variable, 4 drops 2, 8 drops 3,",
                "  and 16 drops all 4 (F = 1).",
                "- Bigger group = fewer letters = simpler term.",
                "BUILDING THE EQUATION",
                "- Write one term for each group.",
                "- Join the terms with OR (+).",
                "EXAMPLE: 1s AT m13, m14, m15",
                "- Group {m13, m15}: A=1, B=1, D=1 stay. C changes.",
                "  Term = ABD.",
                "- Group {m14, m15}: A=1, B=1, C=1 stay. D changes.",
                "  Term = ABC.",
                "- F = ABD + ABC. (m15 is used twice. Overlap is fine.)",
                "EXAMPLE: THE FOUR CORNERS",
                "- m0, m2, m8, m10 wrap around to form ONE group of 4.",
                "- B=0 and D=0 stay. A and C change.",
                "- F = B'D'.",
                "COMMON MISTAKES",
                "- Using the order 00, 01, 10, 11 on the edges.",
                "- Drawing a diagonal group, or a group of 3 or 6.",
                "- Forgetting that the edges wrap around.",
                "- Stopping at a small group when a bigger one exists.",
                "- Using more groups than needed.",
                "TIP",
                "- Open the lab (T). In SIMULATE, click cells to make a map",
                "  and see the groups and equation. In TEST MODE, find the",
                "  groups yourself.",
            ],
            "REGISTERS AND LFSRs": [
                "THE REGISTER",
                "- A flip-flop is a memory cell that stores one bit.",
                "- A register is a row of cells (here: 5 cells).",
                "- A CLOCK pulse moves every bit one cell to the RIGHT.",
                "- The bit leaving CELL 5 is the OUTPUT bit.",
                "THE NEW BIT",
                "- A TAP is a cell whose bit is sent to the XOR gate.",
                "- XOR gives 1 if its inputs differ, 0 if they match.",
                "- The XOR result (FEEDBACK) enters CELL 1.",
                "SEED, TAPS AND THE STREAM",
                "- SEED = the starting pattern of the 5 cells.",
                "- Same seed + same taps = the same output stream.",
                "SECRET CODE (SCRAMBLING)",
                "- To hide a message: message XOR key bit = scrambled bit.",
                "- To get it back: scrambled bit XOR the same key bit",
                "  = message bit again.",
                "- Example: 1011 XOR 0110 = 1101. Then 1101 XOR 0110 = 1011.",
                "- The real name for this is a stream cipher.",
            ],
        }

        if not pygame.font.get_init():
            pygame.font.init()

        available = {name.lower() for name in pygame.font.get_fonts()}
        candidates = [
            "press start 2p",
            "pixeloid sans",
            "pixel operator",
            "monospace",
        ]

        self.font_name = next(
            (name for name in candidates if name in available),
            "monospace",
        )

        self.title_font = self._font(25)
        self.button_font = self._font(17)
        self.body_font = self._font(18)
        self.small_font = self._font(16)
        self.notes_font = self._font(17)

        self.buttons = []
        self.back_button = None

        # Interactive Logic Gates reference
        self.gate_names = [
            "AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT"
        ]
        self.selected_gate = "AND"
        self.gate_a = 0
        self.gate_b = 0

        # Interactive LFSR lab (REGISTERS AND LFSRs page).
        # Same convention as Level 6: 5 cells, shift RIGHT, output = CELL 5,
        # feedback (XOR of the tapped cells) enters CELL 1.
        self.tiny_font = self._font(12)
        self.comb = CombLab()                 # COMBINATIONAL CIRCUITS lab (both paths)
        self.comb_notes = False
        self.reference_notes["COMBINATIONAL CIRCUITS"] = _comb_notes_lines()

        # Sequential-circuit labs (flip-flops, shift registers, counters)
        self._seq_labs = {"FLIP-FLOPS": FlipFlopLab(),
                          "SHIFT REGISTERS": ShiftLab(),
                          "COUNTERS": CounterLab()}
        self.seq_notes = {t: False for t in self._seq_labs}
        self.reference_notes["FLIP-FLOPS"] = flipflop_notes_lines()
        self.reference_notes["SHIFT REGISTERS"] = shift_notes_lines()
        self.reference_notes["COUNTERS"] = counter_notes_lines()
        self.lfsr_seed = [1, 0, 0, 1, 0]      # demo values, not the puzzle's
        self.lfsr_taps = {1, 4}               # CELL 2 and CELL 5
        self.lfsr_hist = [list(self.lfsr_seed)]
        self.lfsr_out = []
        self.lfsr_count = 0
        self.lfsr_predict = False
        self.lfsr_streak = 0
        self.lfsr_passed = False              # True after 5 correct predictions
        self.lfsr_msg = ""
        self.lfsr_msg_ok = True
        self.lfsr_notes = False               # False = lab, True = text notes

        # Number-systems converter lab (NUMBER SYSTEMS page).
        # 0 = BINARY, 1 = DECIMAL, 2 = GRAY, 3 = HEX
        self.num_from = 0
        self.num_to = 1
        self.num_text = "1011"                # demo value, not a puzzle value
        self.num_msg = ""
        self.num_notes = False                # False = lab, True = text notes
        self.topic_scroll = 0                 # scroll for long text notes

        # Boolean Algebra circuit lab (BOOLEAN ALGEBRA page).
        # SIMULATE = build any circuit with 2-4 variables and watch its
        # equation. TEST = rebuild a given goal expression.
        self.bool_test = False                # False = simulate, True = test
        self.bool_nvars = 3                   # SIMULATE: 2, 3 or 4 variables
        self.bool_idx = 0                     # TEST: which goal expression
        self.bool_notes = False               # False = lab, True = text notes
        self.bool_benches = {}                # key -> (Circuit, Workbench)
        self.bool_solved = set()              # TEST: goal indices matched
        self.bool_msg = ""
        self.bool_eq_cache = {}               # truth table -> simplest form

        # Karnaugh map lab (KARNAUGH MAPS page).
        self.km_all_groups = self._km_build_rects()
        self.km_cache = {}
        self.km_test = False                  # False = simulate, True = test
        self.km_notes = False                 # False = lab, True = text notes
        self.km_vals = [0] * 16               # 0, 1, 2 = X (simulate mode)
        self.km_ex = 0
        self.km_label = ""
        self._km_load_example(0)
        self.km_sel = set()                   # selected cells (test mode)
        self.km_groups = []                   # saved groups (test mode)
        self.km_test_idx = 0
        self.km_streak = 0
        self.km_passed = False
        self.km_msg = ""
        self.km_msg_ok = True

        # Interactive STATE MACHINES lab
        self.sm_notes = False          # False = lab, True = text notes
        self.sm_predict = False        # PREDICT mode
        self.sm_circuit = False        # False = diagram, True = circuit view
        self.sm_q_state = "RED"        # state asked about in PREDICT mode
        self.sm_q_btn = "A"            # button asked about in PREDICT mode
        self.sm_scroll = 0             # pixel scroll of the lab's lower area
        self.sm_max_scroll = 0         # measured while drawing
        self._sm_reset("")

    # --------------------------------------------------------
    # FONTS AND TEXT
    # --------------------------------------------------------

    def _font(self, size):
        if not pygame.font.get_init():
            pygame.font.init()

        return pygame.font.SysFont(
            self.font_name,
            size,
            bold=True,
        )

    def _fit_text(self, text, max_width, preferred_size, color):
        size = preferred_size

        while size >= 9:
            font = self._font(size)
            surface = font.render(text, False, color)

            if surface.get_width() <= max_width:
                return surface

            size -= 1

        return self._font(9).render(text, False, color)

    def _text(self, screen, text, x, y, color, font=None):
        font = font or self.body_font
        surface = font.render(text, False, color)
        screen.blit(surface, (x, y))
        return surface.get_rect(topleft=(x, y))

    # --------------------------------------------------------
    # LEVEL PROGRESSION
    # --------------------------------------------------------

    def complete_level(self, level_id, notes=None):
        """Record detective findings and unlock the following case file."""
        if level_id not in self.level_status:
            return

        status = self.level_status[level_id]
        status["solved"] = True
        status["unlocked"] = True
        findings = notes if notes else self.DEFAULT_FINDINGS.get(level_id, [])
        status["notes"] = list(findings)

        level_ids = [item[0] for item in self.LEVELS]
        index = level_ids.index(level_id)

        if index + 1 < len(level_ids):
            next_id = level_ids[index + 1]
            self.level_status[next_id]["unlocked"] = True

    def set_level_unlocked(self, level_id, unlocked=True):
        if level_id in self.level_status:
            self.level_status[level_id]["unlocked"] = unlocked

    # --------------------------------------------------------
    # BASIC / INTERMEDIATE MODE
    # --------------------------------------------------------

    def set_mode(self, mode):
        """Switch the scientist clues for Level One between the two paths.

        The notebook, its labs and every other level stay common.
        """
        self.game_mode = mode
        for name in ("SCIENTIST_NOTES", "LEVEL_GOALS", "LEVEL_HINTS",
                     "DEFAULT_FINDINGS", "LEVEL_PRACTICE"):
            self.__dict__.pop(name, None)          # back to the class defaults

        if mode == "basic":
            notes = dict(DetectiveNotebook.SCIENTIST_NOTES)
            notes["level_one"] = list(BASIC_LEVEL_ONE_NOTES)
            goals = dict(DetectiveNotebook.LEVEL_GOALS)
            goals["level_one"] = BASIC_LEVEL_ONE_GOAL
            hints = dict(DetectiveNotebook.LEVEL_HINTS)
            hints["level_one"] = list(BASIC_LEVEL_ONE_HINTS)
            findings = dict(DetectiveNotebook.DEFAULT_FINDINGS)
            findings["level_one"] = list(BASIC_LEVEL_ONE_FINDINGS)
            # BASIC path: the Circuit Lab (circuits + Boolean algebra) sits on terminal 2.
            notes["level_two"] = list(BASIC_LEVEL_TWO_NOTES)
            goals["level_two"] = BASIC_LEVEL_TWO_GOAL
            hints["level_two"] = list(BASIC_LEVEL_TWO_HINTS)
            findings["level_two"] = list(BASIC_LEVEL_TWO_FINDINGS)
            # BASIC path: number systems and codes sit on terminal 3.
            notes["level_three"] = list(BASIC_LEVEL_THREE_NOTES)
            goals["level_three"] = BASIC_LEVEL_THREE_GOAL
            hints["level_three"] = list(BASIC_LEVEL_THREE_HINTS)
            findings["level_three"] = list(BASIC_LEVEL_THREE_FINDINGS)
            # BASIC path: the Karnaugh-map course sits on terminal 4 (Final Override).
            notes["level_four"] = list(BASIC_LEVEL_FOUR_NOTES)
            goals["level_four"] = BASIC_LEVEL_FOUR_GOAL
            hints["level_four"] = list(BASIC_LEVEL_FOUR_HINTS)
            findings["level_four"] = list(BASIC_LEVEL_FOUR_FINDINGS)
            # BASIC path: the combinational-circuits course sits on terminal 5.
            notes["level_five"] = list(BASIC_LEVEL_FIVE_NOTES)
            goals["level_five"] = BASIC_LEVEL_FIVE_GOAL
            hints["level_five"] = list(BASIC_LEVEL_FIVE_HINTS)
            findings["level_five"] = list(BASIC_LEVEL_FIVE_FINDINGS)
            # BASIC path: flip-flops, shift registers and counters sit on terminal 6.
            notes["level_six"] = list(BASIC_LEVEL_SIX_NOTES)
            goals["level_six"] = BASIC_LEVEL_SIX_GOAL
            hints["level_six"] = list(BASIC_LEVEL_SIX_HINTS)
            findings["level_six"] = list(BASIC_LEVEL_SIX_FINDINGS)
            practice = dict(DetectiveNotebook.LEVEL_PRACTICE)
            practice["level_two"] = "BOOLEAN ALGEBRA"
            practice["level_three"] = "NUMBER SYSTEMS AND CODES"
            practice["level_four"] = "KARNAUGH MAPS"
            practice["level_five"] = "COMBINATIONAL CIRCUITS"
            practice["level_six"] = "FLIP-FLOPS"
            self.LEVEL_PRACTICE = practice
            self.SCIENTIST_NOTES = notes
            self.LEVEL_GOALS = goals
            self.LEVEL_HINTS = hints
            self.DEFAULT_FINDINGS = findings
            self.enable_basic_notes()
        else:
            if "MY BASIC NOTES" in self.reference_topics:
                self.reference_topics.remove("MY BASIC NOTES")

    def enable_basic_notes(self):
        """Show the MY BASIC NOTES page in TEST THE LOGIC."""
        if "MY BASIC NOTES" not in self.reference_topics:
            self.reference_topics.insert(0, "MY BASIC NOTES")
        if "MY BASIC NOTES" not in self.reference_notes:
            self._rebuild_basic_notes()

    def add_basic_note(self, stage_id, lines):
        """Auto-fill: called by the Basic puzzle when a stage is finished."""
        self.enable_basic_notes()
        self.basic_notes_by_stage[stage_id] = list(lines)
        self._rebuild_basic_notes()

    def _rebuild_basic_notes(self):
        if not self.basic_notes_by_stage:
            self.reference_notes["MY BASIC NOTES"] = [
                "MY REVISION SHEET",
                "- Finish a stage on the BASIC lock terminal and its notes are written here for you.",
                "- Each stage adds the rule, the truth table, the symbol and the maths behind it.",
            ]
            return
        notes = ["MY REVISION SHEET (AUTO-SAVED)"]
        # Logic-gate stages (s1..s8), circuit lab (b01..b10, b99), number systems (n01..n11), Karnaugh (k1..k9), combinational (c1..c9), flip-flops (q).
        order = sorted(self.basic_notes_by_stage,
                       key=lambda sid: ("sbnkcq".find(sid[0]), sid))
        for stage_id in order:
            notes.extend(self.basic_notes_by_stage[stage_id])
        self.reference_notes["MY BASIC NOTES"] = notes

    # --------------------------------------------------------
    # OPEN / CLOSE
    # --------------------------------------------------------

    def toggle(self):
        """Toggle the notebook without changing the game scene."""
        if self.open:
            self.close()
            return

        self.open = True
        self.is_open = True
        self.page = "index"
        self.selected_index = 0
        self.selected_level = None
        self.buttons = []
        self.back_button = None

    def close(self):
        """Close the notebook overlay."""
        self.open = False
        self.is_open = False
        self.buttons = []
        self.back_button = None

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    def handle_event(self, event):
        """Handle notebook input before the game's normal controls."""

        if not self.open:
            return False

        # Boolean lab: the mouse drives the circuit workbench.
        if self._on_bool_lab() and event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            if self._bool_mouse(event):
                return True

        # Combinational lab: clicking a switch or the PREV / NEXT buttons.
        if (self._on_comb_page() and not self.comb_notes
                and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.comb.handle_click(event.pos)):
            return True

        # Sequential labs: clicks on inputs, CLK boxes and buttons.
        seq = self._seq_lab()
        if (seq and not seq[1] and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1 and seq[0].handle_click(event.pos)):
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                self.close()
                return True

            # Level page: H reveals the next hint, P opens the practice lab.
            if self.page == "level":
                if event.key == pygame.K_h:
                    self._reveal_hint()
                    return True
                if event.key == pygame.K_p:
                    self._practise_level()
                    return True

            if self._on_numbers_page() and self._num_handle_key(event):
                return True

            if self._on_bool_page() and self._bool_handle_key(event):
                return True

            if self._on_km_page() and self._km_handle_key(event):
                return True

            if self._on_comb_page() and self._comb_handle_key(event):
                return True

            if self._seq_lab() and self._seq_handle_key(event):
                return True

            # STATE MACHINES lab: A/B/C are the machine's buttons, so these
            # keys must be read before the notebook's own B = "back" key.
            if self._on_sm_page() and self._sm_handle_key(event):
                return True

            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE,
                             pygame.K_b):
                if self.page == "reference_topic":
                    self.page = "reference_index"
                elif self.page == "reference_index":
                    self.page = "index"
                elif self.page == "level":
                    self.page = "index"
                else:
                    self.close()
                return True

            if self._on_lfsr_page() and self._lfsr_handle_key(event):
                return True

            if event.key in (pygame.K_UP, pygame.K_w):
                if self.page == "level":
                    self.notes_scroll = max(0, self.notes_scroll - 1)
                elif self._topic_is_text():
                    self.topic_scroll = max(0, self.topic_scroll - 1)
                else:
                    self._move_selection(-1)
                return True

            if event.key in (pygame.K_DOWN, pygame.K_s):
                if self.page == "level":
                    self.notes_scroll += 1
                elif self._topic_is_text():
                    self.topic_scroll += 1
                else:
                    self._move_selection(1)
                return True

            if event.key == pygame.K_a and self.page == "reference_topic" and self.selected_level == "LOGIC GATES":
                self.gate_a = 1 - self.gate_a
                return True

            if event.key == pygame.K_LEFT:
                if self.page == "reference_topic" and self.selected_level == "LOGIC GATES":
                    self._move_gate(-1)
                    return True

            if event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.page == "reference_topic" and (
                    self.selected_level == "LOGIC GATES"
                ):
                    self._move_gate(1)
                    return True

            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                             pygame.K_SPACE):
                self._activate_selection()
                return True

            return True

        if event.type == pygame.MOUSEWHEEL and self.page == "level":
            self.notes_scroll = max(0, self.notes_scroll - event.y)
            return True

        # STATE MACHINES lab: wheel scrolls the lower area in pixels.
        if event.type == pygame.MOUSEWHEEL and self._on_sm_page() \
                and not self.sm_notes:
            self._sm_scroll_by(-event.y * self.SM_SCROLL_STEP)
            return True

        if event.type == pygame.MOUSEWHEEL and self._topic_is_text():
            self.topic_scroll = max(0, self.topic_scroll - event.y)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, item in enumerate(self.buttons):
                rect, action = item

                if rect.collidepoint(event.pos):
                    self.selected_index = index
                    self._activate_selection()
                    return True

            if self.back_button and self.back_button.collidepoint(event.pos):
                self._go_back()
                return True

            return True

        return True

    def _move_selection(self, direction):
        """Move keyboard selection through the buttons on the current page."""
        if not self.buttons:
            return

        self.selected_index = (
            self.selected_index + direction
        ) % len(self.buttons)

    def _go_back(self):
        if self.page == "reference_topic":
            self.page = "reference_index"
        elif self.page == "reference_index":
            self.page = "index"
        elif self.page == "level":
            self.page = "index"
        else:
            self.close()

        self.buttons = []
        self.selected_index = 0

    def _move_gate(self, direction):
        index = self.gate_names.index(self.selected_gate)
        index = (index + direction) % len(self.gate_names)
        self.selected_gate = self.gate_names[index]

    def _open_topic(self, topic):
        """Open a TEST THE LOGIC page, with every lab on its lab view."""
        self.selected_level = topic
        self.page = "reference_topic"
        self.selected_index = 0
        self.lfsr_notes = False
        self.num_notes = False
        self.bool_notes = False
        self.bool_test = False
        self.bool_msg = ""
        self.comb_notes = False
        self.km_notes = False
        for _t in self.seq_notes:
            self.seq_notes[_t] = False
        self.km_test = False
        self.km_sel.clear()
        self.km_groups.clear()
        self.topic_scroll = 0
        self.buttons = []
        if topic == "STATE MACHINES":
            self.sm_notes = False
            self.sm_predict = False
            self.sm_circuit = False
            self._sm_reset("")

    def _reveal_hint(self):
        """Show the next hint for the open level (one at a time)."""
        level_id = self.selected_level
        status = self.level_status.get(level_id)
        if not status or not status["unlocked"]:
            return

        total = len(self.LEVEL_HINTS.get(level_id, []))
        if self.hints_shown.get(level_id, 0) < total:
            self.hints_shown[level_id] = self.hints_shown.get(level_id, 0) + 1
            self._jump_to_hints = True

    def _practise_level(self):
        """Jump from a level page to the lab that teaches that level."""
        topic = self.LEVEL_PRACTICE.get(self.selected_level)
        if topic:
            self._open_topic(topic)

    def _activate_selection(self):
        if not self.buttons:
            return

        self.selected_index = max(
            0, min(self.selected_index, len(self.buttons) - 1)
        )

        _, action = self.buttons[self.selected_index]
        action_type, value = action

        if action_type == "level":
            status = self.level_status[value]
            if not status["unlocked"]:
                return

            self.selected_level = value
            self.notes_scroll = 0
            self.selected_index = 0
            self.page = "level"

        elif action_type == "reference":
            self.page = "reference_index"
            self.selected_index = 0

        elif action_type == "topic":
            self._open_topic(value)

        elif action_type == "hint":
            self._reveal_hint()

        elif action_type == "practice":
            self._practise_level()

        elif action_type == "lfsr_cell":
            self._lfsr_toggle_seed(value)

        elif action_type == "lfsr_tap":
            self._lfsr_toggle_tap(value)

        elif action_type == "lfsr_clock":
            self._lfsr_clock()

        elif action_type == "lfsr_guess":
            self._lfsr_guess(value)

        elif action_type == "lfsr_reset":
            self._lfsr_restart("Register reset to the seed.")

        elif action_type == "lfsr_predict":
            self._lfsr_toggle_predict()

        elif action_type == "lfsr_notes":
            self.lfsr_notes = not self.lfsr_notes
            self.topic_scroll = 0

        elif action_type == "sm_press":
            self._sm_press(value)

        elif action_type == "sm_pick":
            self._sm_pick(value)

        elif action_type == "sm_reset":
            self._sm_reset("Reset: the lamp is back at RED.")

        elif action_type == "sm_predict":
            self._sm_toggle_predict()

        elif action_type == "sm_circuit":
            self._sm_toggle_circuit()

        elif action_type == "sm_notes":
            self.sm_notes = not self.sm_notes
            self.topic_scroll = 0
            self.sm_scroll = 0

        elif action_type == "num_from":
            self._num_set_from(value)

        elif action_type == "num_to":
            self.num_to = value
            self.num_msg = ""

        elif action_type == "num_swap":
            self._num_swap()

        elif action_type == "num_plus":
            self._num_step(1)

        elif action_type == "num_minus":
            self._num_step(-1)

        elif action_type == "num_clear":
            self.num_text = ""
            self.num_msg = ""

        elif action_type == "num_notes":
            self.num_notes = not self.num_notes
            self.topic_scroll = 0

        elif action_type == "bool_add":
            self._bool_add(value)

        elif action_type == "bool_prev":
            self._bool_goto(self.bool_idx - 1)

        elif action_type == "bool_next":
            self._bool_goto(self.bool_idx + 1)

        elif action_type == "bool_reset":
            self._bool_reset()

        elif action_type == "bool_mode":
            self._bool_toggle_mode()

        elif action_type == "bool_vars":
            self._bool_set_vars(value)

        elif action_type == "bool_notes":
            self.bool_notes = not self.bool_notes
            self.topic_scroll = 0

        elif action_type == "km_cell":
            self._km_cell(value)

        elif action_type == "km_mode":
            self._km_toggle_mode()

        elif action_type == "km_clear":
            self._km_clear()

        elif action_type == "km_example":
            self._km_load_example(self.km_ex + 1)

        elif action_type == "km_save":
            self._km_save()

        elif action_type == "km_check":
            self._km_check()

        elif action_type == "km_undo":
            self._km_undo()

        elif action_type == "km_notes":
            self.km_notes = not self.km_notes
            self.topic_scroll = 0

        elif action_type == "comb_notes":
            self.comb_notes = not self.comb_notes
            self.topic_scroll = 0

        elif action_type == "seq_notes":
            self.seq_notes[value] = not self.seq_notes[value]
            self.topic_scroll = 0

        elif action_type == "back":
            self._go_back()

        elif action_type == "gate":
            self.selected_gate = value

        elif action_type == "input_a":
            self.gate_a = 1 - self.gate_a

        elif action_type == "input_b":
            self.gate_b = 1 - self.gate_b


    # --------------------------------------------------------
    # NOTEBOOK FRAME
    # --------------------------------------------------------

    def _draw_spiral(self, screen, page_rect):
        """Draw larger pixel-art spiral binding across the notebook."""

        spacing = 34
        ring_width = 18
        ring_height = 25

        count = max(
            4,
            (page_rect.width - 40) // spacing
        )

        for index in range(count):
            x = page_rect.x + 16 + index * spacing
            y = page_rect.y - 7

            # Keep every ring within the notebook's top edge.
            if x + ring_width > page_rect.right - 10:
                break

            # Dark pixel shadow.
            pygame.draw.rect(
                screen,
                (35, 27, 28),
                (x, y + 5, ring_width, ring_height),
            )

            pygame.draw.rect(
                screen,
                SPIRAL_DARK,
                (x + 3, y, ring_width - 6, 8),
            )

            # Main binding.
            pygame.draw.rect(
                screen,
                SPIRAL_DARK,
                (x, y + 5, ring_width, ring_height - 5),
            )

            # Light centre pixels.
            pygame.draw.rect(
                screen,
                SPIRAL_LIGHT,
                (x + 4, y + 8, ring_width - 8, 7),
            )

            pygame.draw.rect(
                screen,
                (122, 100, 91),
                (x + 4, y + 16, ring_width - 8, 7),
            )

            # Highlight the top of each spiral.
            pygame.draw.rect(
                screen,
                (235, 228, 211),
                (x + 5, y + 2, ring_width - 10, 4),
            )

    def _draw_frame(self, screen):
        width, height = screen.get_size()

        # Faded black overlay; the current room remains visible.
        shade = pygame.Surface((width, height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 175))
        screen.blit(shade, (0, 0))

        page_w = min(int(width * 0.76), 760)
        page_h = min(int(height * 0.86), 850)

        page_w = min(page_w, width - 32)
        page_h = min(page_h, height - 36)

        x = (width - page_w) // 2
        y = (height - page_h) // 2 + 5

        pygame.draw.rect(
            screen,
            (18, 15, 17),
            (x - 6, y + 7, page_w + 12, page_h + 3),
        )
        pygame.draw.rect(
            screen,
            SPIRAL_DARK,
            (x - 5, y - 2, page_w + 10, page_h + 5),
        )
        pygame.draw.rect(screen, PAPER, (x, y, page_w, page_h))

        pygame.draw.rect(
            screen,
            PAPER_LIGHT,
            (x + 6, y + 8, page_w - 12, 5),
        )
        pygame.draw.rect(
            screen,
            (167, 173, 178),
            (x + page_w - 5, y + 18, 4, page_h - 35),
        )

        self._draw_spiral(
            screen, pygame.Rect(x, y, page_w, page_h)
        )

        content = pygame.Rect(
            x + 25,
            y + 43,
            page_w - 50,
            page_h - 65,
        )

        self.back_button = pygame.Rect(
            content.x,
            content.bottom - 30,
            min(150, content.width),
            26,
        )

        return pygame.Rect(x, y, page_w, page_h), content

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    def _draw_button(self, screen, rect, label, selected, enabled=True):
        fill = (205, 208, 210) if enabled else (174, 177, 180)
        text_color = INK if enabled else LOCKED

        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, INK, rect, 3)

        if selected and enabled:
            pygame.draw.rect(screen, CYAN, rect, 3)
            text_color = (0, 91, 103)

        label_surface = self._fit_text(
            label, rect.width - 12, 16, text_color
        )
        screen.blit(
            label_surface,
            label_surface.get_rect(center=rect.center),
        )

    # --------------------------------------------------------
    # INDEX PAGE
    # --------------------------------------------------------

    def _draw_index(self, screen, content):
        self.buttons = []

        title = self._fit_text(
            "NOTEBOOK", content.width, 28, INK
        )
        screen.blit(
            title,
            title.get_rect(
                midtop=(content.centerx, content.y + 1)
            ),
        )

        # Wider buttons, aligned evenly inside the original page.
        side_margin = 3
        button_x = content.x + side_margin
        button_width = content.width - (side_margin * 2)

        button_h = 39
        gap = 12
        y = content.y + 51

        for level_id, heading, _subtitle in self.LEVELS:
            status = self.level_status[level_id]
            unlocked = status["unlocked"]

            if not unlocked:
                label = f"{heading}  [SEALED]"
            elif status["solved"]:
                label = f"{heading}  [RECORDED]"
            else:
                label = heading

            rect = pygame.Rect(
                button_x, y, button_width, button_h
            )

            selected = len(self.buttons) == self.selected_index

            self._draw_button(
                screen,
                rect,
                label,
                selected,
                enabled=unlocked,
            )

            self.buttons.append(
                (rect, ("level", level_id))
            )

            y += button_h + gap

        # Test the Logic button
        y += 3

        reference_rect = pygame.Rect(
            button_x,
            y,
            button_width,
            button_h,
        )

        # New players are pointed to the lab and glossary first.
        any_solved = any(s["solved"] for s in self.level_status.values())
        test_label = ("TEST THE LOGIC" if any_solved
                      else "TEST THE LOGIC  [START HERE]")

        self._draw_button(
            screen,
            reference_rect,
            test_label,
            len(self.buttons) == self.selected_index,
        )

        self.buttons.append(
            (reference_rect, ("reference", None))
        )

        # Keyboard instructions
        hint = "UP / DOWN: SELECT     ENTER: OPEN     N: CLOSE"
        hint_surface = self._fit_text(
            hint, content.width, 11, MUTED
        )

        screen.blit(
            hint_surface,
            hint_surface.get_rect(
                center=(
                    content.centerx,
                    content.bottom - 45,
                )
            ),
        )

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # LEVEL NOTES
    # --------------------------------------------------------

    def _draw_level_page(self, screen, content):
        self.buttons = []        # no stale index buttons on this page
        level_id = self.selected_level

        if level_id not in self.level_status:
            self.page = "index"
            return

        status = self.level_status[level_id]
        _, heading, subtitle = next(
            item for item in self.LEVELS if item[0] == level_id
        )

        title = self._fit_text(heading, content.width, 24, INK)
        screen.blit(title, (content.x + 3, content.y + 2))

        subtitle_surface = self._fit_text(
            subtitle, content.width, 17, MUTED
        )
        screen.blit(subtitle_surface, (content.x + 3, content.y + 32))

        pygame.draw.line(
            screen, PAGE_LINE,
            (content.x + 2, content.y + 58),
            (content.right - 2, content.y + 58), 2,
        )

        top_y = content.y + 70
        action_y = self.back_button.y - 34
        max_y = action_y - 8
        text_area = pygame.Rect(
            content.x + 3, top_y, content.width - 12, max(0, max_y - top_y)
        )

        if not status["unlocked"]:
            self._text(screen, "THIS CASE FILE IS SEALED.",
                       content.x + 3, top_y, LOCKED, self.body_font)
            self._text(screen, "Resolve the previous investigation to access it.",
                       content.x + 3, top_y + 32, MUTED, self.small_font)
            self._draw_back_button(screen)
            return

        # Sections: your job, scientist notes, hints, detective findings.
        # Hints appear one at a time. Findings appear only after the solve.
        entries = []

        goal = self.LEVEL_GOALS.get(level_id)
        if goal:
            entries.append(("YOUR JOB", TEAL, True))
            entries.append((goal, INK, False))

        entries.append(("SCIENTIST'S NOTES", DARK_GREEN, True))
        entries.extend((line, INK, False) for line in self.SCIENTIST_NOTES.get(level_id, []))

        hints = self.LEVEL_HINTS.get(level_id, [])
        shown = self.hints_shown.get(level_id, 0)
        entries.append(("HINTS", TEAL, True))
        if shown == 0:
            entries.append(("Stuck? Press H to reveal a hint. They come one at a time, gentle first.",
                            MUTED, False))
        for i in range(min(shown, len(hints))):
            entries.append((f"Hint {i + 1}: {hints[i]}", TEAL, False))

        if status["solved"]:
            entries.append(("DETECTIVE'S FINDINGS", MAROON, True))
            findings = status["notes"] or self.DEFAULT_FINDINGS.get(level_id, [])
            entries.extend((line, MAROON, False) for line in findings)
        else:
            entries.append(("DETECTIVE'S FINDINGS", MUTED, True))
            entries.append(("Findings will be recorded after this level is solved.", MUTED, False))

        rendered_lines = []
        hint_start = 0
        for text, color, is_heading in entries:
            if is_heading and text == "HINTS":
                hint_start = len(rendered_lines)
            font = self.body_font if is_heading else self.notes_font
            wrapped = self._wrap_text(str(text), text_area.width - 12, font)
            for line in wrapped:
                rendered_lines.append((line, color, font, is_heading))
            rendered_lines.append(("", INK, font, False))

        line_gap = 25
        max_scroll = max(0, len(rendered_lines) - max(1, text_area.height // line_gap))
        if self._jump_to_hints:
            self.notes_scroll = hint_start
            self._jump_to_hints = False
        self.notes_scroll = min(self.notes_scroll, max_scroll)
        visible_lines = rendered_lines[self.notes_scroll:]

        screen.set_clip(text_area)
        y = text_area.y
        for line, color, font, is_heading in visible_lines:
            if y + line_gap > text_area.bottom:
                break
            if line:
                self._text(screen, line, text_area.x + 5, y, color, font)
            y += line_gap if line else 10
        screen.set_clip(None)

        if max_scroll > 0:
            hint = "UP / DOWN OR MOUSE WHEEL: SCROLL NOTES"
            hint_surface = self._fit_text(hint, text_area.width, 13, MUTED)
            screen.blit(hint_surface, (text_area.x + 5, max_y - 3))

        # Action buttons: reveal a hint, or jump to the practice lab.
        more = shown < len(hints)
        hint_label = f"HINT [H] {shown}/{len(hints)}" if more else "NO MORE HINTS"
        hint_rect = pygame.Rect(content.x + 3, action_y, 230, 26)
        self._draw_button(screen, hint_rect, hint_label,
                          len(self.buttons) == self.selected_index,
                          enabled=more)
        self.buttons.append((hint_rect, ("hint", level_id)))

        practise_rect = pygame.Rect(hint_rect.right + 8, action_y, 210, 26)
        self._draw_button(screen, practise_rect, "PRACTISE [P]", False)
        self.buttons.append((practise_rect, ("practice", level_id)))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # FIELD REFERENCE
    # --------------------------------------------------------

    def _draw_reference_index(self, screen, content):
        self.buttons = []

        title = self._fit_text(
            "TEST THE LOGIC", content.width, 22, INK
        )
        screen.blit(title, (content.x + 3, content.y + 2))

        button_x = content.x + 3
        button_width = content.width - 6
        button_h = 39
        gap = 12
        n_topics = len(self.reference_topics)    # 12 topics in BASIC mode: shrink to fit
        avail = (self.back_button.y - 8) - (content.y + 49)
        gap = 7 if n_topics > 8 else 12
        button_h = max(24, min(39, (avail - gap * (n_topics - 1)) // n_topics))
        y = content.y + 49

        for topic in self.reference_topics:
            rect = pygame.Rect(
                button_x, y, button_width, button_h
            )

            selected = len(self.buttons) == self.selected_index

            self._draw_button(
                screen, rect, topic, selected
            )

            self.buttons.append((rect, ("topic", topic)))
            y += button_h + gap

        self._draw_back_button(screen)

    def _gate_output(self, gate, a, b):
        if gate == "AND":
            return int(a and b)
        if gate == "OR":
            return int(a or b)
        if gate == "XOR":
            return int(a != b)
        if gate == "NAND":
            return int(not (a and b))
        if gate == "NOR":
            return int(not (a or b))
        if gate == "XNOR":
            return int(a == b)
        if gate == "NOT":
            return 1 - int(a)
        return 0

    def _draw_gate_symbol(self, screen, gate, rect, color):
        """Thin-line pixel-art logic gate symbols (reference style)."""
        x, y, w, h = pygame.Rect(rect)

        stroke = 2 if h < 45 else 3              # line thickness
        mid = y + h // 2
        top = y + int(h * 0.12)
        bottom = y + int(h * 0.88)
        in_top = y + h // 3                      # input pin heights
        in_bot = y + (2 * h) // 3                # (match the circuit pins)

        def poly(points, close=False):
            pts = [(int(round(px)), int(round(py))) for px, py in points]
            if close:
                pts.append(pts[0])
            for a, b in zip(pts, pts[1:]):
                pygame.draw.line(screen, color, a, b, stroke)
            for px, py in (pts[0], pts[-1]):     # square pixel end-caps
                pygame.draw.rect(screen, color,
                                 (px - stroke // 2, py - stroke // 2,
                                  stroke, stroke))

        def hline(x0, x1, yy):
            x0, x1 = int(x0), int(x1)
            if x1 > x0:
                pygame.draw.rect(screen, color,
                                 (x0, int(yy) - stroke // 2, x1 - x0, stroke))

        def bezier(p0, p1, p2, steps=14):
            pts = []
            for i in range(steps + 1):
                t = i / steps
                a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
                pts.append((a * p0[0] + b * p1[0] + c * p2[0],
                            a * p0[1] + b * p1[1] + c * p2[1]))
            return pts

        # ---- horizontal layout -------------------------------------
        bubble_size = max(5, stroke * 2 + 2)     # small hollow square bubble
        has_bubble = gate in ("NAND", "NOR", "XNOR", "NOT")
        out_len = max(6, int(w * 0.14))
        gap = max(5, int(w * 0.05)) if gate in ("XOR", "XNOR") else 0

        left = x + int(w * 0.14) + gap
        right = x + w - out_len - (bubble_size if has_bubble else 0)

        # Keep the body from stretching too long in wide, short boxes.
        max_body = int((bottom - top) * 3.2)
        if right - left > max_body:
            extra = (right - left - max_body) // 2
            left += extra
            right -= extra
        bw = max(10, right - left)

        # ---- NOT ----------------------------------------------------
        if gate == "NOT":
            poly([(left, top), (right, mid), (left, bottom)], close=True)
            hline(x, left, mid)
            pygame.draw.rect(screen, color,
                             (right, mid - bubble_size // 2,
                              bubble_size, bubble_size), stroke)
            hline(right + bubble_size, x + w, mid)
            return

        # ---- AND / NAND --------------------------------------------
        if gate in ("AND", "NAND"):
            xc = left + bw * 0.5
            upper = bezier((xc, top), (right, top), (right, mid))
            lower = bezier((right, mid), (right, bottom), (xc, bottom))
            poly([(left, top)] + upper + lower[1:] + [(left, bottom)],
                 close=True)
            hline(x, left, in_top)
            hline(x, left, in_bot)

        # ---- OR / NOR / XOR / XNOR ---------------------------------
        else:
            depth = bw * 0.36

            def back_curve(base):
                return bezier((base, top), (base + depth, mid), (base, bottom))

            def back_x(base, yy):                # where a pin meets the curve
                t = (yy - top) / (bottom - top)
                return base + 2 * t * (1 - t) * depth

            poly(bezier((left, top), (left + bw * 0.55, top), (right, mid)))
            poly(bezier((left, bottom), (left + bw * 0.55, bottom), (right, mid)))
            poly(back_curve(left))

            base = left
            if gate in ("XOR", "XNOR"):
                base = left - gap
                poly(back_curve(base))           # extra XOR curve

            hline(x, back_x(base, in_top), in_top)
            hline(x, back_x(base, in_bot), in_bot)

        # ---- output bubble + output wire ----------------------------
        if has_bubble:
            pygame.draw.rect(screen, color,
                             (right, mid - bubble_size // 2,
                              bubble_size, bubble_size), stroke)
            hline(right + bubble_size, x + w, mid)
        else:
            hline(right, x + w, mid)

    def _draw_logic_gates_page(self, screen, content):
        self.buttons = []
        title = self._fit_text("LOGIC GATES", content.width, 22, INK)
        screen.blit(title, (content.x + 3, content.y + 2))
        pygame.draw.line(screen, PAGE_LINE,
                         (content.x + 2, content.y + 35),
                         (content.right - 2, content.y + 35), 2)
        self._text(screen, "TYPES OF GATES AVAILABLE FOR 2 INPUTS:",
                   content.x + 3, content.y + 44, INK, self.body_font)

        # Four columns over two rows: all seven reference symbols stay visible.
        # NOT is a one-input gate, included alongside the six two-input gates.
        columns, gap_x, gap_y = 4, 8, 7
        button_w = (content.width - 6 - gap_x * (columns - 1)) // columns
        button_h = 49
        start_x, start_y = content.x + 3, content.y + 70
        for index, gate in enumerate(self.gate_names):
            row, col = divmod(index, columns)
            rect = pygame.Rect(start_x + col*(button_w+gap_x),
                               start_y + row*(button_h+gap_y), button_w, button_h)
            selected = gate == self.selected_gate
            pygame.draw.rect(screen, PAPER, rect)
            pygame.draw.rect(screen, CYAN if selected else INK, rect, 3)
            symbol_rect = pygame.Rect(rect.x+5, rect.y+2,
                                      rect.width-10, 29)
            self._draw_gate_symbol(screen, gate, symbol_rect,
                                   CYAN if selected else INK)
            label = self._fit_text(gate, rect.width-8, 12,
                                   (0, 91, 103) if selected else INK)
            screen.blit(label, label.get_rect(center=(rect.centerx, rect.bottom-9)))
            self.buttons.append((rect, ("gate", gate)))

        # Circuit begins below both rows of gate choices; no overlap with NOT.
        circuit_y = start_y + 2*(button_h+gap_y) + 8
        bottom_limit = self.back_button.y - 42
        available_h = max(135, bottom_limit - circuit_y)
        circuit_w = int(content.width * 0.63)
        circuit_rect = pygame.Rect(content.x+3, circuit_y, circuit_w, available_h)
        pygame.draw.rect(screen, (198, 202, 205), circuit_rect)
        pygame.draw.rect(screen, PAGE_LINE, circuit_rect, 2)

        wire = (55, 125, 151)
        cyan = CYAN
        pad = 10                                   # blue mini-square size
        input_w = min(94, max(75, int(circuit_w * 0.19)))
        input_h = 35
        ax = circuit_rect.x + 14
        ay = circuit_rect.y + int(available_h * 0.23)
        by = circuit_rect.y + int(available_h * 0.64)
        a_rect = pygame.Rect(ax, ay, input_w, input_h)
        b_rect = pygame.Rect(ax, by, input_w, input_h)

        # Put A/B values inside the actual circuit input blocks.
        pygame.draw.rect(screen, (7, 27, 39), a_rect)
        pygame.draw.rect(screen, cyan, a_rect, 3)
        self._text(screen, f"A = {self.gate_a}", a_rect.x+8, a_rect.y+8,
                   WHITE, self.body_font)
        self.buttons.append((a_rect, ("input_a", None)))

        is_not = self.selected_gate == "NOT"
        if not is_not:
            pygame.draw.rect(screen, (7, 27, 39), b_rect)
            pygame.draw.rect(screen, cyan, b_rect, 3)
            self._text(screen, f"B = {self.gate_b}", b_rect.x+8, b_rect.y+8,
                       WHITE, self.body_font)
            self.buttons.append((b_rect, ("input_b", None)))

        gate_x = circuit_rect.x + int(circuit_w * 0.43)
        gate_y = circuit_rect.y + int(available_h * 0.31)
        gate_w = max(68, int(circuit_w * 0.22))
        gate_h = max(48, int(available_h * 0.38))
        symbol_rect = pygame.Rect(gate_x, gate_y, gate_w, gate_h)
        pin_mid = gate_y + gate_h // 2

        # Which input boxes feed which gate pins (NOT: A only, one pin).
        if is_not:
            input_pins = [(a_rect, pin_mid)]
        else:
            pin1 = gate_y + gate_h // 3
            pin2 = gate_y + (2 * gate_h) // 3
            input_pins = [(a_rect, pin1), (b_rect, pin2)]

        # Wires from the input boxes to the gate pins.
        mid_x = gate_x - 15
        for input_rect, pin_y in input_pins:
            pygame.draw.lines(screen, wire, False,
                              [(input_rect.right, input_rect.centery),
                               (mid_x, input_rect.centery),
                               (mid_x, pin_y), (gate_x, pin_y)], 5)

        self._draw_gate_symbol(screen, self.selected_gate, symbol_rect, cyan)

        # Blue mini squares, drawn after wires/symbol so they stay on top:
        # one at the edge of each input box, one at each gate input pin.
        for input_rect, pin_y in input_pins:
            pygame.draw.rect(screen, cyan,
                             (input_rect.right - pad // 2,
                              input_rect.centery - pad // 2, pad, pad))
            pygame.draw.rect(screen, cyan,
                             (gate_x - pad // 2, pin_y - pad // 2, pad, pad))

        # Output wire, output square and lamp.
        output = self._gate_output(self.selected_gate, self.gate_a, self.gate_b)
        lamp_x = circuit_rect.right - 31
        lamp_y = pin_mid                       # lamp sits level with gate output
        out_start = gate_x + gate_w
        pygame.draw.line(screen, wire, (out_start, pin_mid),
                         (lamp_x - 17, pin_mid), 5)
        pygame.draw.rect(screen, cyan,
                         (out_start - pad // 2, pin_mid - pad // 2, pad, pad))
        pygame.draw.circle(screen, (40, 205, 130) if output else (48, 42, 43),
                           (lamp_x, lamp_y), 17)
        pygame.draw.circle(screen, WHITE, (lamp_x, lamp_y), 18, 3)
        out_label = self.small_font.render("OUTPUT", False, MUTED)
        screen.blit(out_label,
                    out_label.get_rect(midtop=(lamp_x, lamp_y + 22)))

        # Compact truth table: NOT has A/Y and exactly two rows.
        table_x = circuit_rect.right + 13
        table_w = content.right - table_x - 3
        self._text(screen, "LIVE TRUTH TABLE", table_x, circuit_y+1,
                   INK, self.small_font)
        headers = ["A", "Y"] if is_not else ["A", "B", "Y"]
        col_w = max(1, table_w // len(headers))
        row_h = min(29, max(21, (available_h-32)//(3 if is_not else 5)))
        table_top = circuit_y + 25
        for col, head in enumerate(headers):
            cell = pygame.Rect(table_x+col*col_w, table_top, col_w, row_h)
            pygame.draw.rect(screen, PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)
            self._text(screen, head, cell.x+4, cell.y+4, INK, self.small_font)

        combos = [(0, None), (1, None)] if is_not else [(0,0),(0,1),(1,0),(1,1)]
        for row, (a, b) in enumerate(combos):
            yval = self._gate_output(self.selected_gate, a, 0 if b is None else b)
            vals = [a, yval] if is_not else [a, b, yval]
            active = (a == self.gate_a) if is_not else ((a,b) == (self.gate_a,self.gate_b))
            for col, val in enumerate(vals):
                cell = pygame.Rect(table_x+col*col_w,
                                   table_top+(row+1)*row_h, col_w, row_h)
                pygame.draw.rect(screen, (185, 224, 226) if active else PAPER, cell)
                pygame.draw.rect(screen, CYAN if active else PAGE_LINE, cell,
                                 2 if active else 1)
                self._text(screen, str(val), cell.x+4, cell.y+4, INK, self.small_font)

        summary_y = table_top + (len(combos)+1)*row_h + 7
        self._text(screen, f"SELECTED: {self.selected_gate}", table_x,
                   summary_y, INK, self.small_font)
        self._text(screen, f"OUTPUT: {output}", table_x,
                   summary_y+18, INK, self.small_font)
        self._text(screen, "Click A box to toggle. [B] BACK" if is_not else
                   "Click A/B boxes to toggle. [B] BACK",
                   content.x+3, circuit_rect.bottom+2, MUTED, self.small_font)
        self._draw_back_button(screen)

    def _draw_reference_topic(self, screen, content):
        if self.selected_level == "LOGIC GATES":
            self._draw_logic_gates_page(screen, content)
            return
        topic = self.selected_level

        if topic == "REGISTERS AND LFSRs" and not self.lfsr_notes:
            self._draw_lfsr_page(screen, content)
            return

        if topic == "NUMBER SYSTEMS" and not self.num_notes:
            self._draw_numbers_page(screen, content)
            return

        if topic == "STATE MACHINES" and not self.sm_notes:
            self._draw_sm_lab(screen, content)
            return

        if topic == "BOOLEAN ALGEBRA" and not self.bool_notes:
            self._draw_bool_lab(screen, content)
            return

        if topic == "KARNAUGH MAPS" and not self.km_notes:
            self._draw_kmap_lab(screen, content)
            return

        if topic == "COMBINATIONAL CIRCUITS" and not self.comb_notes:
            self._draw_comb_lab(screen, content)
            return

        if topic in self._seq_labs and not self.seq_notes[topic]:
            self._draw_seq_lab(screen, content, topic)
            return

        title = self._fit_text(topic, content.width, 20, INK)
        screen.blit(title, (content.x + 3, content.y + 2))

        pygame.draw.line(
            screen,
            PAGE_LINE,
            (content.x + 2, content.y + 35),
            (content.right - 2, content.y + 35),
            2,
        )

        self.buttons = []
        text_top = content.y + 49
        line_gap = 22
        max_y = self.back_button.y - 10

        # Build every wrapped line first so long notes can be scrolled.
        rows = []
        for note in self.reference_notes.get(topic, []):
            is_head = note.isupper() and not note.startswith(("-", " "))
            lead = note[:len(note) - len(note.lstrip(" "))]
            wrapped = self._wrap_text(
                note, content.width - 10, self.small_font
            )
            for index, line in enumerate(wrapped):
                last = index == len(wrapped) - 1
                rows.append((
                    lead + line,
                    DARK_GREEN if is_head else INK,
                    4 if last else 0,
                ))

        visible_h = max_y - text_top
        max_scroll = 0
        while max_scroll < len(rows) - 1:
            needed = sum(line_gap + extra for _l, _c, extra in rows[max_scroll:])
            if needed <= visible_h + 4:
                break
            max_scroll += 1

        self.topic_scroll = max(0, min(self.topic_scroll, max_scroll))

        y = text_top
        for line, color, extra in rows[self.topic_scroll:]:
            if y + line_gap > max_y:
                break
            self._text(screen, line, content.x + 5, y, color, self.small_font)
            y += line_gap + extra

        if max_scroll > 0:
            hint = self.tiny_font.render(
                "UP / DOWN OR WHEEL: SCROLL", False, MUTED
            )
            screen.blit(hint, (self.back_button.right + 14,
                               self.back_button.y + 8))

        lab_actions = {
            "REGISTERS AND LFSRs": "lfsr_notes",
            "NUMBER SYSTEMS": "num_notes",
            "STATE MACHINES": "sm_notes",
            "BOOLEAN ALGEBRA": "bool_notes",
            "KARNAUGH MAPS": "km_notes",
            "COMBINATIONAL CIRCUITS": "comb_notes",
            "FLIP-FLOPS": "seq_notes",
            "SHIFT REGISTERS": "seq_notes",
            "COUNTERS": "seq_notes",
        }
        if topic in lab_actions:
            lab_rect = pygame.Rect(content.right - 190, self.back_button.y,
                                   190, self.back_button.height)
            self._draw_button(screen, lab_rect, "OPEN LAB [T]", True)
            self.buttons.append((lab_rect, (lab_actions[topic],
                                 topic if lab_actions[topic] == "seq_notes" else None)))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # STATE MACHINES LAB
    # --------------------------------------------------------
    # One tiny machine, shown three ways at once and always in sync:
    #   - the lamp / state diagram (circles and arrows)
    #   - the rule table (row = where you are, column = button you press)
    #   - the circuit (memory boxes + AND guards, like Level 3's build step)
    #
    # EXPLORE  press A, B or C freely and read the explanation.
    # PREDICT  the lab names a state and a button; click the lamp that comes
    #          next. 5 correct in a row passes.
    #
    # Layout: the diagram/circuit and the control buttons are fixed at the
    # top. Everything below them (explanation, rule table, goal, history)
    # lives in a clipped area that scrolls with UP/DOWN or the mouse wheel.

    def _on_sm_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "STATE MACHINES")

    def _sm_scroll_by(self, amount):
        self.sm_scroll = max(0, min(self.sm_scroll + amount,
                                    self.sm_max_scroll))

    def _sm_next(self, state, btn):
        """Returns (next_state, fired_step_index or None).

        A step fires when the ball is in the step's start state AND the
        button matches. RED is the always-ready start, so pressing A always
        starts a fresh ball at AMBER. With no step firing the ball vanishes
        and the machine is back at RED.
        """
        for index, (frm, need, to) in enumerate(self.SM_STEPS):
            if btn == need and (state == frm or frm == "RED"):
                return to, index
        return "RED", None

    def _sm_reset(self, message=""):
        self.sm_state = "RED"
        self.sm_last = None            # (from, button, to, step index)
        self.sm_presses = 0
        self.sm_seq = []
        self.sm_press_time = -10000
        self.sm_flash_btn = None
        self.sm_msg = message
        self.sm_msg_ok = True
        self.sm_scroll = 0

    def _sm_apply(self, btn):
        frm = self.sm_state
        to, step = self._sm_next(frm, btn)
        self.sm_state = to
        self.sm_last = (frm, btn, to, step)
        self.sm_presses += 1
        self.sm_seq.append(btn)
        self.sm_seq = self.sm_seq[-16:]
        self.sm_press_time = pygame.time.get_ticks()
        self.sm_flash_btn = btn
        self.sm_scroll = 0             # show the new explanation
        return frm, to, step

    def _sm_explain(self, frm, btn, to, step):
        if step is None:
            if frm == "RED":
                text = (f"RED + {btn} is not a forward step, so nothing "
                        "happens. You are still in RED. Start with A.")
            else:
                text = (f"{frm} + {btn} is not a forward step, so the "
                        "machine drops back to RED. A wrong button costs "
                        "you your progress.")
        elif step == 0 and frm != "RED":
            text = ("You pressed A. A always starts a fresh ball at the "
                    "beginning, so the lamp goes to AMBER.")
        else:
            text = f"{frm} + {btn} = {to}. The lamp moves to {to}."
        if to == "GREEN":
            text += " GREEN! The secret code is A, B, C."

        if self.sm_circuit:
            if step is not None:
                src = self.SM_STEPS[step][0]
                text += (f" In the circuit, the STEP {step + 1} guard saw "
                         f"the ball at {src} AND button {btn}. Both were "
                         f"ON, so the {to} box now remembers the ball.")
            else:
                text += (" In the circuit, every guard said NO, so no box "
                         "remembers the ball.")
        return text

    def _sm_press(self, btn):
        if self.sm_predict:
            self.sm_msg = ("PREDICT mode: click the lamp you think comes "
                           "next (or press 1-4).")
            self.sm_msg_ok = False
            self.sm_scroll = 0
            return
        frm, to, step = self._sm_apply(btn)
        self.sm_msg = self._sm_explain(frm, btn, to, step)
        self.sm_msg_ok = step is not None

    def _sm_new_question(self):
        """Pick a random (state, button) pair, different from the last one."""
        old = (self.sm_q_state, self.sm_q_btn)
        while True:
            pair = (random.choice(self.SM_STATES),
                    random.choice(self.SM_BUTTONS))
            if pair != old:
                break
        self.sm_q_state, self.sm_q_btn = pair
        # Show the asked state on the diagram; no arrows from earlier moves.
        self.sm_state = self.sm_q_state
        self.sm_last = None

    def _sm_toggle_predict(self):
        self.sm_predict = not self.sm_predict
        self.sm_scroll = 0
        if self.sm_predict:
            self.sm_circuit = False
            self._sm_new_question()
            self.sm_msg = ("PREDICT: read the rule table, then click the "
                           "lamp that comes next.")
            self.sm_msg_ok = True
        else:
            self._sm_reset("Predict mode off. Press A, B or C to explore.")

    def _sm_toggle_circuit(self):
        self.sm_circuit = not self.sm_circuit
        self.sm_scroll = 0
        if self.sm_circuit:
            if self.sm_predict:
                self.sm_predict = False
                self._sm_reset("")
            self.sm_msg = ("Same machine, built from memory boxes and "
                           "guards. A glowing box holds the ball.")
        else:
            self.sm_msg = "Back to the lamp diagram."
        self.sm_msg_ok = True

    def _sm_pick(self, name):
        if not self.sm_predict:
            return
        btn = self.sm_q_btn
        frm = self.sm_q_state
        to, _step = self._sm_next(frm, btn)
        self.sm_scroll = 0
        if name == to:
            self.sm_msg = f"CORRECT! {frm} + {btn} = {to}."
            self.sm_msg_ok = True
            self._sm_new_question()
        else:
            self.sm_msg = (f"NOT QUITE. Row {frm}, column {btn} of the table "
                           f"says {to}, not {name}. Try again.")
            self.sm_msg_ok = False

    def _sm_handle_key(self, event):
        """STATE MACHINES keys. Returns True when the key was used."""
        key = event.key
        if key == pygame.K_t:
            self.sm_notes = not self.sm_notes
            self.topic_scroll = 0
            self.sm_scroll = 0
            return True
        if self.sm_notes:
            return False

        # Scrolling the lab's lower area.
        if key in (pygame.K_UP, pygame.K_w):
            self._sm_scroll_by(-self.SM_SCROLL_STEP)
            return True
        if key in (pygame.K_DOWN, pygame.K_s):
            self._sm_scroll_by(self.SM_SCROLL_STEP)
            return True
        if key == pygame.K_PAGEUP:
            self._sm_scroll_by(-self.SM_SCROLL_STEP * 4)
            return True
        if key == pygame.K_PAGEDOWN:
            self._sm_scroll_by(self.SM_SCROLL_STEP * 4)
            return True

        letters = {pygame.K_a: "A", pygame.K_b: "B", pygame.K_c: "C"}
        if key in letters:
            self._sm_press(letters[key])
            return True

        digits = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
        if key in digits:
            self._sm_pick(self.SM_STATES[digits.index(key)])
            return True
        if key == pygame.K_r:
            self._sm_reset("Reset: the lamp is back at RED.")
            return True
        if key == pygame.K_p:
            self._sm_toggle_predict()
            return True
        if key == pygame.K_v:
            self._sm_toggle_circuit()
            return True
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_d,
                   pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return True
        return False                         # ESC / BACKSPACE go back

    # ---- small drawing helpers ------------------------------------

    @staticmethod
    def _arrow_head(screen, colour, p_from, p_to, size=10):
        dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        left = (p_to[0] - ux * size - uy * size * 0.5,
                p_to[1] - uy * size + ux * size * 0.5)
        right = (p_to[0] - ux * size + uy * size * 0.5,
                 p_to[1] - uy * size - ux * size * 0.5)
        pygame.draw.polygon(screen, colour, [p_to, left, right])

    @staticmethod
    def _bezier(p0, p1, p2, steps=24):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            pts.append((a * p0[0] + b * p1[0] + c * p2[0],
                        a * p0[1] + b * p1[1] + c * p2[1]))
        return pts

    @staticmethod
    def _glow_rect(screen, rect, colour, strength=1.0):
        """Soft glowing outline around rect; the part underneath stays visible."""
        pad = 30
        surf = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2),
                              pygame.SRCALPHA)
        for i in range(5, 0, -1):
            grow = i * 4
            alpha = int(min(255, (25 + (6 - i) * 25) * strength))
            ring = pygame.Rect(pad - grow, pad - grow,
                               rect.w + grow * 2, rect.h + grow * 2)
            pygame.draw.rect(surf, (*colour, alpha), ring, 4,
                             border_radius=6 + grow)
        screen.blit(surf, (rect.x - pad, rect.y - pad))

    # ---- diagram view ----------------------------------------------

    def _sm_draw_diagram(self, screen, pnl):
        state = self.sm_state
        last = self.sm_last
        r = 28
        y = pnl.y + 62
        xs = [pnl.x + int(pnl.width * (2 * i + 1) / 8) for i in range(4)]
        pos = {name: (xs[i], y) for i, name in enumerate(self.SM_STATES)}
        idx = {name: i for i, name in enumerate(self.SM_STATES)}
        base = (95, 110, 122)

        # Which forward arrow (if any) did the last press walk along?
        last_forward = None
        if last and last[3] is not None and last[0] == self.SM_STEPS[last[3]][0]:
            last_forward = last[3]

        # forward arrows (the correct path)
        for k, (frm, btn, to) in enumerate(self.SM_STEPS):
            x0, x1 = pos[frm][0], pos[to][0]
            a, b = (x0 + r + 4, y), (x1 - r - 4, y)
            on = last_forward == k
            colour = DARK_GREEN if on else base
            pygame.draw.line(screen, colour, a, b, 4 if on else 3)
            self._arrow_head(screen, colour, a, b)
            lab = self.small_font.render(btn, False, colour)
            screen.blit(lab, lab.get_rect(midbottom=((x0 + x1) // 2, y - 6)))

        # the last press when it was NOT a plain forward step
        if last and last_forward is None:
            frm, btn, to, step = last
            colour = DARK_GREEN if step is not None else MAROON
            x0, x1 = pos[frm][0], pos[to][0]
            if frm == to:
                cx, cy = x0, y - r - 10
                pygame.draw.circle(screen, colour, (cx, cy), 12, 3)
                lab = self.small_font.render(btn, False, colour)
                screen.blit(lab, (cx + 15, cy - 20))
            else:
                span = abs(idx[frm] - idx[to])
                s = 1 if x1 > x0 else -1
                p0 = (x0 + s * 8, y + r)
                p2 = (x1 - s * 8, y + r)
                p1 = ((x0 + x1) // 2, y + r + 28 + span * 20)
                pts = self._bezier(p0, p1, p2)
                pygame.draw.lines(screen, colour, False, pts, 4)
                self._arrow_head(screen, colour, pts[-2], pts[-1])
                mx, my = pts[len(pts) // 2]
                lab = self.small_font.render(btn, False, colour)
                screen.blit(lab, (int(mx) - 5, int(my) + 4))

        # state circles
        for name, (x, cy) in pos.items():
            colour = self.SM_COLOURS[name]
            pygame.draw.circle(screen, colour, (x, cy), r)
            pygame.draw.circle(screen, INK, (x, cy), r, 3)
            if name == state:
                pygame.draw.circle(screen, CYAN, (x, cy), r + 6, 3)
            lab = self.tiny_font.render(name, False, WHITE)
            screen.blit(lab, lab.get_rect(center=(x, cy)))
            if self.sm_predict:
                num = self.small_font.render(
                    str(self.SM_STATES.index(name) + 1), False, INK)
                screen.blit(num, (x - r - 8, cy - r - 12))
                rect = pygame.Rect(x - r, cy - r, r * 2, r * 2)
                self.buttons.append((rect, ("sm_pick", name)))

        now = self.tiny_font.render(f"NOW: {state}", False, INK)
        screen.blit(now, (pnl.x + 8, pnl.y + 6))

    # ---- circuit view ----------------------------------------------

    def _sm_draw_circuit(self, screen, pnl):
        wire = (55, 125, 151)
        dark = (7, 27, 39)
        lit_green = (40, 205, 130)
        state = self.sm_state
        last = self.sm_last
        now = pygame.time.get_ticks()
        recent = now - self.sm_press_time < 700

        GW, GH, FW, FH, gap = 56, 44, 50, 50, 26
        gy = pnl.y + 32
        stride = (pnl.width - 140 - 20) // 3

        # RED: the always-ready start
        red = pygame.Rect(pnl.x + 14, gy + 15, 84, 30)
        red_on = state == "RED"
        pygame.draw.rect(screen, self.SM_COLOURS["RED"] if red_on else dark, red)
        pygame.draw.rect(screen, self.SM_COLOURS["RED"], red, 3)
        lab = self.small_font.render("RED = 1", False, WHITE)
        screen.blit(lab, lab.get_rect(center=red.center))
        cap = self.tiny_font.render("ALWAYS READY", False, MUTED)
        screen.blit(cap, cap.get_rect(midtop=(red.centerx, red.bottom + 3)))
        if red_on:
            self._glow_rect(screen, red, self.SM_COLOURS["RED"], 0.9)

        prev_out = None                         # right edge of previous box
        for k, (frm, btn, to) in enumerate(self.SM_STEPS):
            gx = pnl.x + 140 + k * stride
            gate = pygame.Rect(gx, gy, GW, GH)
            ff = pygame.Rect(gx + GW + gap, gy - 3, FW, FH)
            upper = gy + GH // 3
            lower = gy + (2 * GH) // 3
            fired = last is not None and last[3] == k

            # upper input: where the ball is
            if k == 0:
                pts = [(red.right, red.centery),
                       (red.right + 10, red.centery),
                       (red.right + 10, upper), (gx, upper)]
            else:
                px, py = prev_out
                pts = [(px, py), (px + 12, py), (px + 12, upper), (gx, upper)]
            pygame.draw.lines(screen, wire, False, pts, 3)

            # lower input: the button
            bb = pygame.Rect(gx - 44, pnl.y + 104, 38, 26)
            pygame.draw.lines(screen, wire, False,
                              [(bb.centerx, bb.y), (bb.centerx, lower),
                               (gx, lower)], 3)

            # gate -> memory box
            pygame.draw.line(screen, wire, (gx + GW, gy + GH // 2),
                             (ff.x, ff.centery), 3)
            self._draw_gate_symbol(screen, "AND", gate,
                                   lit_green if fired else CYAN)
            cap = self.tiny_font.render(f"STEP {k + 1}", False, INK)
            screen.blit(cap, cap.get_rect(midtop=(gate.centerx, gate.bottom + 4)))

            # memory box
            holds = state == to
            pygame.draw.rect(screen, self.SM_COLOURS[to] if holds else dark, ff)
            pygame.draw.rect(screen, CYAN, ff, 3)
            q = self.title_font.render("1" if holds else "0", False, WHITE)
            screen.blit(q, q.get_rect(center=ff.center))
            name = self.tiny_font.render(to, False, INK)
            screen.blit(name, name.get_rect(midbottom=(ff.centerx, ff.y - 3)))
            if holds:
                self._glow_rect(screen, ff, self.SM_COLOURS[to],
                                0.75 + 0.25 * math.sin(now / 180))

            # button box
            flash = recent and self.sm_flash_btn == btn
            pygame.draw.rect(screen, dark, bb)
            pygame.draw.rect(screen, lit_green if flash else CYAN, bb,
                             4 if flash else 3)
            bl = self.small_font.render(btn, False, WHITE)
            screen.blit(bl, bl.get_rect(center=bb.center))
            if flash:
                self._glow_rect(screen, bb, lit_green, 0.8)
            if not self.sm_predict:
                self.buttons.append((bb, ("sm_press", btn)))

            prev_out = (ff.right, ff.centery)

        note = self.tiny_font.render("EACH PRESS = ONE CLOCK TICK", False, MUTED)
        screen.blit(note, note.get_rect(bottomright=(pnl.right - 8, pnl.bottom - 6)))

    # ---- rule table / equations (each returns its bottom y) -------

    def _sm_draw_table(self, screen, x, y):
        col_w = [112, 86, 86, 86]
        row_h = 22
        heads = ["NOW IN", "+ A", "+ B", "+ C"]

        title = self.tiny_font.render(
            "RULE TABLE: row = where you are, column = button", False, MUTED)
        screen.blit(title, (x, y))
        y += 20

        cx = x
        for col, head in enumerate(heads):
            cell = pygame.Rect(cx, y, col_w[col], row_h)
            pygame.draw.rect(screen, PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)
            surf = self.tiny_font.render(head, False, INK)
            screen.blit(surf, surf.get_rect(center=cell.center))
            cx += col_w[col]

        for r, state in enumerate(self.SM_STATES):
            ry = y + (r + 1) * row_h
            name_cell = pygame.Rect(x, ry, col_w[0], row_h)
            pygame.draw.rect(screen, self.SM_COLOURS[state], name_cell)
            pygame.draw.rect(screen, PAGE_LINE, name_cell, 2)
            surf = self.tiny_font.render(state, False, WHITE)
            screen.blit(surf, surf.get_rect(center=name_cell.center))
            cx = x + col_w[0]
            for c, btn in enumerate(self.SM_BUTTONS):
                to, _step = self._sm_next(state, btn)
                cell = pygame.Rect(cx, ry, col_w[c + 1], row_h)
                fired = (self.sm_last is not None
                         and (self.sm_last[0], self.sm_last[1]) == (state, btn))
                asked = (self.sm_predict
                         and (state, btn) == (self.sm_q_state, self.sm_q_btn))
                if asked:
                    pygame.draw.rect(screen, (185, 224, 226), cell)
                    pygame.draw.rect(screen, CYAN, cell, 3)
                elif fired:
                    pygame.draw.rect(screen, (190, 228, 205), cell)
                    pygame.draw.rect(screen, DARK_GREEN, cell, 3)
                else:
                    pygame.draw.rect(screen, PAPER, cell)
                    pygame.draw.rect(screen, PAGE_LINE, cell, 1)
                surf = self.tiny_font.render(to, False, INK)
                screen.blit(surf, surf.get_rect(center=cell.center))
                cx += col_w[c + 1]

        return y + (len(self.SM_STATES) + 1) * row_h

    def _sm_draw_equations(self, screen, x, y, width):
        title = self.tiny_font.render(
            "WHAT EACH GUARD CHECKS", False, MUTED)
        screen.blit(title, (x, y))
        sub = self.tiny_font.render(
            "(a box gets 1 only if both inputs are 1)", False, MUTED)
        screen.blit(sub, (x, y + 15))
        ty = y + 38
        last = self.sm_last
        for k, (frm, btn, to) in enumerate(self.SM_STEPS):
            fired = last is not None and last[3] == k
            colour = DARK_GREEN if fired else INK
            line = f"STEP {k + 1}: {to} = {frm} AND {btn}"
            self._text(screen, line, x, ty, colour, self.small_font)
            ty += 24
        ty += 4
        for note in ("RED is always ON: it is the ball's start.",
                     "No box holds the ball = back at RED."):
            for line in self._wrap_text(note, width, self.tiny_font):
                self._text(screen, line, x, ty, MUTED, self.tiny_font)
                ty += 16
        return ty

    def _sm_draw_side(self, screen, x, y, width):
        """Goal / question / history column. Returns its bottom y."""
        state = self.sm_state
        if self.sm_predict:
            self._text(screen, "WHAT HAPPENS NEXT?", x, y, DARK_GREEN,
                       self.small_font)
            q = self._fit_text(f"{self.sm_q_state} + {self.sm_q_btn} = ?",
                               width, 25, INK)
            screen.blit(q, (x, y + 28))
            return y + 66

        self._text(screen, "GOAL: REACH GREEN", x, y, DARK_GREEN,
                   self.small_font)
        self._text(screen, f"PRESSES: {self.sm_presses}", x, y + 26,
                   INK, self.small_font)
        self._text(screen, "BUTTONS PRESSED:", x, y + 54, MUTED,
                   self.tiny_font)

        seq = " ".join(self.sm_seq) if self.sm_seq else "(none yet)"
        yy = y + 72
        for line in self._wrap_text(seq, width, self.small_font) or [seq]:
            self._text(screen, line, x, yy, INK, self.small_font)
            yy += 21

        if state == "GREEN":
            tip = "You reached GREEN! The shortest possible code is 3 presses."
            colour = DARK_GREEN
        else:
            tip = "Tip: the arrows on the map show the way forward."
            colour = MUTED
        yy += 8
        for line in self._wrap_text(tip, width, self.tiny_font):
            self._text(screen, line, x, yy, colour, self.tiny_font)
            yy += 16
        return yy

    # ---- the whole lab -------------------------------------------

    def _draw_sm_lab(self, screen, content):
        self.buttons = []
        X, Y, W = content.x, content.y, content.width
        state = self.sm_state
        now = pygame.time.get_ticks()

        # ---- title / tag / info -------------------------------------
        title = self._fit_text("STATE MACHINES", W, 20, INK)
        screen.blit(title, (X + 3, Y + 2))
        if self.sm_predict:
            tag = "PREDICT"
        elif self.sm_circuit:
            tag = "CIRCUIT VIEW"
        else:
            tag = "EXPLORE"
        tag_s = self.small_font.render(tag, False,
                                       MAROON if self.sm_predict else DARK_GREEN)
        screen.blit(tag_s, tag_s.get_rect(topright=(content.right - 3, Y + 8)))
        pygame.draw.line(screen, PAGE_LINE, (X + 2, Y + 35),
                         (content.right - 2, Y + 35), 2)

        if self.sm_predict:
            info = ("PREDICT: read the table, then click the lamp that comes "
                    "next (or press 1-4).")
        elif self.sm_circuit:
            info = ("The same machine as memory boxes and guards. Press A, "
                    "B or C and watch the ball hop.")
        else:
            info = "Press A, B or C. The lamp moves by the rules. Goal: reach GREEN."
        info_s = self._fit_text(info, W - 6, 16, INK)
        screen.blit(info_s, (X + 3, Y + 41))

        # ---- diagram or circuit (fixed) ----------------------------
        pnl = pygame.Rect(X + 3, Y + 62, W - 6, 150)
        pygame.draw.rect(screen, (198, 202, 205), pnl)
        pygame.draw.rect(screen, PAGE_LINE, pnl, 2)
        if self.sm_circuit:
            self._sm_draw_circuit(screen, pnl)
        else:
            self._sm_draw_diagram(screen, pnl)

        # ---- control buttons (fixed) -------------------------------
        by, bh = Y + 222, 28
        bx = X + 3
        flash_ok = now - self.sm_press_time < 500
        for letter in self.SM_BUTTONS:
            rect = pygame.Rect(bx, by, 46, bh)
            self._draw_button(screen, rect, letter, False,
                              enabled=not self.sm_predict)
            if flash_ok and self.sm_flash_btn == letter:
                pygame.draw.rect(screen, DARK_GREEN, rect, 4)
            if not self.sm_predict:
                self.buttons.append((rect, ("sm_press", letter)))
            bx += 52
        bx += 6
        for label, action, width, sel in (
            ("RESET [R]", "sm_reset", 100, False),
            ("PREDICT [P]", "sm_predict", 124, self.sm_predict),
            ("CIRCUIT [V]" if not self.sm_circuit else "DIAGRAM [V]",
             "sm_circuit", 132, self.sm_circuit),
        ):
            rect = pygame.Rect(bx, by, width, bh)
            self._draw_button(screen, rect, label, sel)
            self.buttons.append((rect, (action, None)))
            bx += width + 8
        notes = pygame.Rect(content.right - 104, by, 100, bh)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("sm_notes", None)))

        # ---- scrollable lower area ---------------------------------
        area_top = by + bh + 10
        area_bottom = self.back_button.y - 8
        area = pygame.Rect(X, area_top, W, max(40, area_bottom - area_top))

        self.sm_scroll = max(0, min(self.sm_scroll, self.sm_max_scroll))
        origin = area.y - self.sm_scroll
        y = origin

        screen.set_clip(area)

        # 1) explanation box
        msg = self.sm_msg
        if not msg:
            if self.sm_predict:
                msg = "Look at the question below, then click a lamp."
            else:
                msg = (f"You are in {state}. "
                       + ("Press A to start the sequence." if state == "RED"
                          else "Press a button to see what happens."))
        colour = DARK_GREEN if self.sm_msg_ok else MAROON
        msg_lines = self._wrap_text(msg, W - 30, self.small_font) or [""]
        line_h = 21
        box_h = len(msg_lines) * line_h + 16
        box = pygame.Rect(X + 3, y + 2, W - 12, box_h)
        pygame.draw.rect(screen, PAPER_LIGHT, box)
        pygame.draw.rect(screen, colour, box, 2)
        ty = box.y + 8
        for line in msg_lines:
            self._text(screen, line, box.x + 8, ty, colour, self.small_font)
            ty += line_h
        y = box.bottom + 14

        # 2) two columns: table / equations on the left, status on the right
        left_w = 370
        left_x = X + 3
        right_x = X + left_w + 24
        right_w = max(120, content.right - right_x - 14)

        if self.sm_circuit:
            left_bottom = self._sm_draw_equations(screen, left_x, y, left_w)
        else:
            left_bottom = self._sm_draw_table(screen, left_x, y)
        right_bottom = self._sm_draw_side(screen, right_x, y, right_w)

        bottom = max(left_bottom, right_bottom) + 6
        screen.set_clip(None)

        # ---- measure + scrollbar -----------------------------------
        total = bottom - origin
        self.sm_max_scroll = max(0, total - area.height)

        if self.sm_max_scroll > 0:
            track = pygame.Rect(area.right - 6, area.y, 4, area.height)
            pygame.draw.rect(screen, PAGE_LINE, track)
            thumb_h = max(20, int(area.height * area.height / total))
            span = area.height - thumb_h
            thumb_y = area.y + int(span * self.sm_scroll / self.sm_max_scroll)
            pygame.draw.rect(screen, INK, (track.x, thumb_y, 4, thumb_h))

            hint = self.tiny_font.render(
                "UP / DOWN OR WHEEL: SCROLL", False, MUTED)
            screen.blit(hint, (self.back_button.right + 14,
                               self.back_button.y + 8))

        self._draw_back_button(screen, "BACK [ESC]")

    # --------------------------------------------------------
    # INTERACTIVE LFSR LAB
    # --------------------------------------------------------

    def _on_lfsr_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "REGISTERS AND LFSRs")

    def _lfsr_feedback(self, state):
        """XOR of the tapped cells (1 if an odd number of them are 1)."""
        fb = 0
        for tap in self.lfsr_taps:
            fb ^= state[tap]
        return fb

    def _lfsr_say(self, text, ok=True):
        self.lfsr_msg = text
        self.lfsr_msg_ok = ok

    def _lfsr_restart(self, message=""):
        self.lfsr_hist = [list(self.lfsr_seed)]
        self.lfsr_out = []
        self.lfsr_count = 0
        self._lfsr_say(message)

    def _lfsr_clock(self):
        state = self.lfsr_hist[-1]
        out = state[-1]
        new_state = [self._lfsr_feedback(state)] + state[:-1]
        self.lfsr_hist.append(new_state)
        self.lfsr_out.append(out)
        self.lfsr_count += 1
        # Keep memory small; the diagram only shows the last 16 states.
        self.lfsr_hist = self.lfsr_hist[-40:]
        self.lfsr_out = self.lfsr_out[-60:]

    def _lfsr_toggle_seed(self, index):
        self.lfsr_seed[index] ^= 1
        self._lfsr_restart("Seed changed, register restarted: "
                           + "".join(map(str, self.lfsr_seed)))

    def _lfsr_toggle_tap(self, index):
        if index in self.lfsr_taps:
            self.lfsr_taps.remove(index)
        else:
            self.lfsr_taps.add(index)
        picked = ", ".join(str(t + 1) for t in sorted(self.lfsr_taps)) or "none"
        self._lfsr_restart(f"Taps changed, register restarted. Taps: {picked}")

    def _lfsr_toggle_predict(self):
        self.lfsr_predict = not self.lfsr_predict
        self.lfsr_streak = 0
        if self.lfsr_predict:
            self._lfsr_say("Predict mode: get 5 right in a row to pass.")
        else:
            self._lfsr_say("Predict mode off. Press CLOCK to step.")

    def _lfsr_guess(self, bit):
        if not self.lfsr_predict:
            return
        if not self.lfsr_taps:
            self._lfsr_say("Select at least one TAP first.", ok=False)
            return
        actual = self._lfsr_feedback(self.lfsr_hist[-1])
        if bit == actual:
            self.lfsr_streak += 1
            self._lfsr_clock()
            if self.lfsr_streak >= 5:
                self.lfsr_passed = True
                self._lfsr_say("CHALLENGE PASSED! You can predict an LFSR step.")
            else:
                self._lfsr_say(f"CORRECT! Streak {self.lfsr_streak}/5.")
        else:
            self.lfsr_streak = 0
            self._lfsr_say("NOT QUITE. XOR is 1 only when the inputs differ "
                           "(an odd number of 1s). Streak reset.", ok=False)

    def _lfsr_handle_key(self, event):
        """LFSR-page keys. Returns True when the key was used."""
        key = event.key
        if key == pygame.K_t:
            self.lfsr_notes = not self.lfsr_notes
            self.topic_scroll = 0
            return True
        if self.lfsr_notes:
            return False

        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.lfsr_predict:
                self._lfsr_say("Predict mode: press LEFT for 0 or RIGHT for 1.",
                               ok=False)
            else:
                self._lfsr_clock()
                self._lfsr_say("")
            return True
        if key == pygame.K_r:
            self._lfsr_restart("Register reset to the seed.")
            return True
        if key == pygame.K_p:
            self._lfsr_toggle_predict()
            return True
        if key == pygame.K_LEFT:
            self._lfsr_guess(0)
            return True
        if key == pygame.K_RIGHT:
            self._lfsr_guess(1)
            return True
        digits = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
        if key in digits:
            index = digits.index(key)
            if event.mod & pygame.KMOD_SHIFT:
                self._lfsr_toggle_seed(index)
            else:
                self._lfsr_toggle_tap(index)
            return True
        return False

    def _lfsr_taps_expr(self, state):
        parts = [f"CELL {t + 1} ({state[t]})" for t in sorted(self.lfsr_taps)]
        return " XOR ".join(parts)

    def _lfsr_explanation(self):
        state = self.lfsr_hist[-1]
        taps = sorted(self.lfsr_taps)

        if self.lfsr_predict:
            if not taps:
                return ("PREDICT: no taps selected. Pick a TAP, then guess "
                        "the bit that enters CELL 1.")
            bits = " and ".join(str(state[t]) for t in taps)
            return (f"PREDICT: the tapped cells hold {bits}. What bit will "
                    f"the XOR send into CELL 1?  [LEFT] = 0   [RIGHT] = 1")

        if len(self.lfsr_hist) == 1:
            seed = "".join(map(str, state))
            if not taps:
                return (f"READY: seed is {seed}. No taps are selected, so "
                        f"the feedback bit will be 0.")
            fb = self._lfsr_feedback(state)
            return (f"READY: seed is {seed}. On the next CLOCK, "
                    f"{self._lfsr_taps_expr(state)} = {fb} will enter CELL 1.")

        prev = self.lfsr_hist[-2]
        fb = state[0]
        left = prev[-1]
        calc = (f"{self._lfsr_taps_expr(prev)} = {fb}" if taps
                else "No taps, so feedback = 0")
        return (f"CLOCK {self.lfsr_count}: {calc}. Every bit moved right: "
                f"{fb} entered CELL 1 and the old CELL 5 bit ({left}) left "
                f"as OUTPUT.")

    def _lfsr_note(self):
        state = self.lfsr_hist[-1]
        if not any(state):
            return "All cells are 0: XOR of zeros is always 0, so it is stuck."
        if self.lfsr_count > 0 and state == self.lfsr_seed:
            return (f"Back at the seed after {self.lfsr_count} clocks: "
                    f"the pattern repeats!")
        return ""

    def _lfsr_wave(self, screen, x0, row_y, row_h, step_w, values, color):
        hi, lo = row_y + 3, row_y + row_h - 4
        points = []
        for k, v in enumerate(values):
            y = hi if v else lo
            points.append((x0 + k * step_w, y))
            points.append((x0 + (k + 1) * step_w, y))
        pygame.draw.lines(screen, color, False, points, 2)

    def _lfsr_clock_wave(self, screen, x0, row_y, row_h, step_w, first_pulse,
                         columns, color):
        hi, lo = row_y + 3, row_y + row_h - 4
        points = []
        for k in range(columns):
            xs = x0 + k * step_w
            xm = xs + step_w // 2
            xe = xs + step_w
            if first_pulse + k == 0:          # before the first pulse
                points += [(xs, lo), (xe, lo)]
            else:                             # rising edge at column start
                points += [(xs, lo), (xs, hi), (xm, hi), (xm, lo), (xe, lo)]
        pygame.draw.lines(screen, color, False, points, 2)

    def _draw_arrow(self, screen, color, x0, x1, y, width=3):
        pygame.draw.line(screen, color, (x0, y), (x1 - 6, y), width)
        pygame.draw.polygon(screen, color,
                            [(x1, y), (x1 - 8, y - 5), (x1 - 8, y + 5)])

    def _draw_lfsr_page(self, screen, content):
        self.buttons = []
        X, Y = content.x, content.y
        state = self.lfsr_hist[-1]
        taps = sorted(self.lfsr_taps)
        fb = self._lfsr_feedback(state)

        wire = (55, 125, 151)
        lit = (40, 205, 130)
        dark = (7, 27, 39)

        # ---- title -----------------------------------------------------
        title = self._fit_text("REGISTERS AND LFSRs", content.width, 20, INK)
        screen.blit(title, (X + 3, Y + 2))
        if self.lfsr_passed:
            self._text(screen, "[CHALLENGE PASSED]", content.right - 190,
                       Y + 8, DARK_GREEN, self.small_font)
        pygame.draw.line(screen, PAGE_LINE, (X + 2, Y + 35),
                         (content.right - 2, Y + 35), 2)

        info = self._fit_text(
            "1 SEED: click cells   2 TAPS: click TAP boxes   3 press CLOCK",
            content.width - 6, 16, INK)
        screen.blit(info, (X + 3, Y + 41))

        # ---- register ----------------------------------------------------
        cell_w, cell_h, gap = 56, 42, 38
        x0 = X + 134
        cell_y = Y + 76
        cy = cell_y + cell_h // 2
        tap_y = Y + 126
        bus_y = Y + 158
        cells = [pygame.Rect(x0 + i * (cell_w + gap), cell_y, cell_w, cell_h)
                 for i in range(5)]
        tap_rects = [pygame.Rect(c.x, tap_y, cell_w, 22) for c in cells]

        circle_c = (X + 34, cy)
        radius = 21

        # feedback wires (drawn first so boxes sit on top)
        if taps:
            xs = [circle_c[0]] + [tap_rects[t].centerx for t in taps]
            for t in taps:
                tx = tap_rects[t].centerx
                pygame.draw.line(screen, lit if state[t] else wire,
                                 (tx, tap_rects[t].bottom), (tx, bus_y), 3)
                pygame.draw.rect(screen, CYAN, (tx - 4, bus_y - 4, 8, 8))
            pygame.draw.line(screen, wire, (min(xs), bus_y), (max(xs), bus_y), 3)
            pygame.draw.line(screen, wire, (circle_c[0], bus_y),
                             (circle_c[0], circle_c[1] + radius), 3)

        # feedback into CELL 1
        self._draw_arrow(screen, lit if fb else wire,
                         circle_c[0] + radius, cells[0].x, cy)

        # shifting arrows between cells
        for i in range(4):
            self._draw_arrow(screen, wire, cells[i].right, cells[i + 1].x, cy)

        # output arrow + lamp
        lamp = (cells[-1].right + 72, cy)
        self._draw_arrow(screen, lit if state[-1] else wire,
                         cells[-1].right, lamp[0] - 19, cy)
        pygame.draw.circle(screen, lit if state[-1] else (48, 42, 43), lamp, 16)
        pygame.draw.circle(screen, WHITE, lamp, 17, 3)
        out_lbl = self.tiny_font.render("OUTPUT", False, MUTED)
        screen.blit(out_lbl, out_lbl.get_rect(midtop=(lamp[0], lamp[1] + 21)))

        # XOR circle
        pygame.draw.circle(screen, dark, circle_c, radius)
        pygame.draw.circle(screen, CYAN, circle_c, radius, 3)
        val = self.title_font.render(str(fb), False, WHITE)
        screen.blit(val, val.get_rect(center=circle_c))
        xl = self.tiny_font.render("XOR", False, INK)
        screen.blit(xl, xl.get_rect(midbottom=(circle_c[0], circle_c[1] - radius - 3)))
        fl = self.tiny_font.render("FEEDBACK", False, MUTED)
        screen.blit(fl, fl.get_rect(
            midbottom=((circle_c[0] + radius + cells[0].x) // 2, cy - 5)))

        # cells + taps
        for i, rect in enumerate(cells):
            bit = state[i]
            pygame.draw.rect(screen, lit if bit else dark, rect)
            pygame.draw.rect(screen, CYAN, rect, 3)
            digit = self.title_font.render(str(bit), False, INK if bit else WHITE)
            screen.blit(digit, digit.get_rect(center=rect.center))
            label = "CELL 5" if i == 4 else f"CELL {i + 1}"
            lbl = self.tiny_font.render(label, False, INK)
            screen.blit(lbl, lbl.get_rect(midbottom=(rect.centerx, rect.y - 4)))
            self.buttons.append((rect, ("lfsr_cell", i)))

            on = i in self.lfsr_taps
            tr = tap_rects[i]
            pygame.draw.rect(screen, CYAN if on else PAPER, tr)
            pygame.draw.rect(screen, INK, tr, 2)
            t_lbl = self.small_font.render("TAP", False, (0, 60, 70) if on else MUTED)
            screen.blit(t_lbl, t_lbl.get_rect(center=tr.center))
            self.buttons.append((tr, ("lfsr_tap", i)))

        # ---- buttons -----------------------------------------------------
        by, bh = Y + 168, 28
        bx = X + 3
        if self.lfsr_predict:
            for bit, key in ((0, "LEFT"), (1, "RIGHT")):
                r = pygame.Rect(bx, by, 108, bh)
                self._draw_button(screen, r, f"GUESS {bit}", False)
                self.buttons.append((r, ("lfsr_guess", bit)))
                bx += 116
        else:
            r = pygame.Rect(bx, by, 150, bh)
            self._draw_button(screen, r, "CLOCK [SPACE]", False)
            self.buttons.append((r, ("lfsr_clock", None)))
            bx += 158
        for label, action, width, sel in (
            ("RESET [R]", ("lfsr_reset", None), 112, False),
            ("PREDICT [P]", ("lfsr_predict", None), 150, self.lfsr_predict),
            ("NOTES [T]", ("lfsr_notes", None), 120, False),
        ):
            r = pygame.Rect(bx, by, width, bh)
            self._draw_button(screen, r, label, sel)
            self.buttons.append((r, action))
            bx += width + 8

        # ---- timing diagram ----------------------------------------------
        self._text(screen, "TIMING DIAGRAM: each column is one clock pulse",
                   X + 3, Y + 202, INK, self.tiny_font)

        hint = self.tiny_font.render("KEYS: 1-5 TAP   SHIFT+1-5 SEED", False, MUTED)
        screen.blit(hint, hint.get_rect(topright=(content.right - 3, Y + 202)))

        show = self.lfsr_hist[-16:]
        columns = len(show)
        first_pulse = self.lfsr_count - (columns - 1)
        wave_x0 = X + 56
        step_w = (content.width - 6 - 56 - 6) // 16
        rows_top = Y + 230
        row_h = 20
        frame = pygame.Rect(X + 3, rows_top - 2, content.width - 6, 6 * row_h + 4)

        pygame.draw.rect(screen, (198, 202, 205), frame)
        pygame.draw.rect(screen, PAGE_LINE, frame, 2)

        last_x = wave_x0 + (columns - 1) * step_w
        pygame.draw.rect(screen, (185, 224, 226),
                         (last_x, frame.y + 2, step_w, frame.height - 4))
        for k in range(columns + 1):
            gx = wave_x0 + k * step_w
            pygame.draw.line(screen, PAGE_LINE, (gx, frame.y + 2),
                             (gx, frame.bottom - 3), 1)
        for k in range(columns):
            num = self.tiny_font.render(str(first_pulse + k), False, MUTED)
            screen.blit(num, num.get_rect(
                midbottom=(wave_x0 + k * step_w + step_w // 2, frame.y - 1)))
        pl = self.tiny_font.render("PULSE", False, MUTED)
        screen.blit(pl, (X + 6, frame.y - 14))

        names = ["CLK", "C1", "C2", "C3", "C4", "C5"]
        colors = [(0, 120, 140)] + [DARK_GREEN] * 4 + [MAROON]
        for r_index, name in enumerate(names):
            ry = rows_top + r_index * row_h
            nl = self.tiny_font.render(name, False, colors[r_index])
            screen.blit(nl, (X + 8, ry + 3))
            if r_index == 0:
                self._lfsr_clock_wave(screen, wave_x0, ry, row_h, step_w,
                                      first_pulse, columns, colors[0])
            else:
                values = [s[r_index - 1] for s in show]
                self._lfsr_wave(screen, wave_x0, ry, row_h, step_w,
                                values, colors[r_index])

        # ---- output stream + explanation ----------------------------------
        stream_y = Y + 358
        bits = self.lfsr_out[-24:]
        self._text(screen, "OUTPUT STREAM:", X + 3, stream_y, INK, self.small_font)
        stream = " ".join(map(str, bits)) if bits else "(press CLOCK)"
        self._text(screen, stream, X + 3 + 160, stream_y, MAROON, self.small_font)

        lines = self._wrap_text(self._lfsr_explanation(),
                                content.width - 10, self.small_font)
        ty = Y + 382
        for line in lines[:2]:
            self._text(screen, line, X + 5, ty, INK, self.small_font)
            ty += 22

        note = self._lfsr_note()
        if note:
            surf = self._fit_text(note, content.width - 10, 16, DARK_GREEN)
            screen.blit(surf, (X + 5, Y + 426))
        if self.lfsr_msg:
            surf = self._fit_text(self.lfsr_msg, content.width - 10, 16,
                                  DARK_GREEN if self.lfsr_msg_ok else MAROON)
            screen.blit(surf, (X + 5, Y + 444))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # NUMBER SYSTEMS CONVERTER LAB
    # --------------------------------------------------------

    NUM_SYSTEMS = ["BINARY", "DECIMAL", "GRAY", "HEX"]
    NUM_MAX_LEN = {0: 8, 1: 3, 2: 8, 3: 2}
    NUM_CHARS = {0: "01", 1: "0123456789", 2: "01", 3: "0123456789ABCDEF"}
    NUM_RULES = {
        0: "BINARY uses only the digits 0 and 1.",
        1: "DECIMAL uses only the digits 0 to 9.",
        2: "GRAY CODE is written with only 0 and 1.",
        3: "HEX uses 0-9 and A-F.",
    }

    # --------------------------------------------------------
    # SEQUENTIAL LABS: hooks
    # --------------------------------------------------------

    def _seq_lab(self):
        """(lab, showing_notes) for the open sequential page, else None."""
        if self.page != "reference_topic":
            return None
        lab = self._seq_labs.get(self.selected_level)
        return (lab, self.seq_notes[self.selected_level]) if lab else None

    def _seq_handle_key(self, event):
        lab, notes = self._seq_lab()
        if event.key == pygame.K_t:
            self.seq_notes[self.selected_level] = not notes
            self.topic_scroll = 0
            return True
        if notes:
            return False
        return lab.handle_key(event)

    def _draw_seq_lab(self, screen, content, topic):
        self.buttons = []
        ui = {"big": self.title_font, "small": self.small_font,
              "tiny": self.tiny_font, "fit": self._fit_text,
              "button": self._draw_button, "wrap": self._wrap_text}
        self._seq_labs[topic].draw(screen, content, self.back_button.y - 6, ui)
        notes = pygame.Rect(content.right - 130, self.back_button.y, 130,
                            self.back_button.height)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("seq_notes", topic)))
        hint = "SPACE: CLOCK   LEFT/RIGHT: VIEW   R: RESET   A: AUTO"
        room = notes.x - (self.back_button.right + 14) - 8
        screen.blit(self._fit_text(hint, room, 12, MUTED),
                    (self.back_button.right + 14, self.back_button.y + 8))
        self._draw_back_button(screen)

    def _topic_is_text(self):
        """True when the open reference page is a scrollable text page."""
        if self.page != "reference_topic":
            return False
        topic = self.selected_level
        if topic == "LOGIC GATES":
            return False
        if topic == "REGISTERS AND LFSRs":
            return self.lfsr_notes
        if topic == "NUMBER SYSTEMS":
            return self.num_notes
        if topic == "STATE MACHINES":
            return self.sm_notes
        if topic == "BOOLEAN ALGEBRA":
            return self.bool_notes
        if topic == "KARNAUGH MAPS":
            return self.km_notes
        if topic == "COMBINATIONAL CIRCUITS":
            return self.comb_notes
        if topic in self.seq_notes:
            return self.seq_notes[topic]
        return True

    def _on_numbers_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "NUMBER SYSTEMS")

    # ---- value helpers ------------------------------------------------

    def _num_value(self):
        """Typed text -> integer 0..255, or None if empty / out of range."""
        text, system = self.num_text, self.num_from
        if not text:
            return None
        try:
            if system == 0:
                n = int(text, 2)
            elif system == 1:
                n = int(text, 10)
            elif system == 2:
                g = int(text, 2)
                n, shifted = g, g >> 1
                while shifted:
                    n ^= shifted
                    shifted >>= 1
            else:
                n = int(text, 16)
        except ValueError:
            return None
        return n if 0 <= n <= 255 else None

    def _num_format(self, system, n, width):
        if system == 0:
            return format(n, "b").zfill(width)
        if system == 1:
            return str(n)
        if system == 2:
            return format(n ^ (n >> 1), "b").zfill(width)
        return format(n, "X").zfill((width + 3) // 4)

    def _num_width(self, n):
        text = self.num_text
        if self.num_from in (0, 2) and text:
            width = len(text)
        elif self.num_from == 3 and text:
            width = 4 * len(text)
        else:
            width = 4 if n < 16 else 8
        return max(width, n.bit_length(), 1)

    def _num_show_value(self, n):
        """Write value n into the input box using the FROM system."""
        width = 4 if n < 16 else 8
        self.num_text = self._num_format(self.num_from, n, width)

    def _num_set_from(self, system):
        n = self._num_value()
        self.num_from = system
        self.num_msg = ""
        if n is None:
            self.num_text = ""
        else:
            self._num_show_value(n)

    def _num_swap(self):
        n = self._num_value()
        self.num_from, self.num_to = self.num_to, self.num_from
        self.num_msg = ""
        if n is None:
            self.num_text = ""
        else:
            self._num_show_value(n)

    def _num_step(self, delta):
        n = self._num_value()
        n = 0 if n is None else n
        self._num_show_value(max(0, min(255, n + delta)))
        self.num_msg = ""

    def _num_handle_key(self, event):
        """Number-lab keys. Returns True when the key was used."""
        key = event.key
        if key == pygame.K_t:
            self.num_notes = not self.num_notes
            self.topic_scroll = 0
            return True
        if self.num_notes:
            return False

        if key == pygame.K_BACKSPACE:
            if self.num_text:
                self.num_text = self.num_text[:-1]
                self.num_msg = ""
                return True
            return False                      # empty box: BACKSPACE = back
        if key == pygame.K_UP:
            self._num_step(1)
            return True
        if key == pygame.K_DOWN:
            self._num_step(-1)
            return True
        if key == pygame.K_TAB:
            self._num_swap()
            return True
        if key == pygame.K_LEFT:
            self.num_to = (self.num_to - 1) % 4
            return True
        if key == pygame.K_RIGHT:
            self.num_to = (self.num_to + 1) % 4
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return True

        # B is the notebook's "back" key unless HEX is being typed.
        if key == pygame.K_b and self.num_from != 3:
            return False

        ch = (getattr(event, "unicode", "") or "").upper()
        if not ch:
            if pygame.K_0 <= key <= pygame.K_9:
                ch = chr(key)
            elif pygame.K_a <= key <= pygame.K_f:
                ch = chr(key).upper()
        if not ch or not (ch.isdigit() or ch in "ABCDEF"):
            return False

        if ch not in self.NUM_CHARS[self.num_from]:
            self.num_msg = self.NUM_RULES[self.num_from]
            return True
        if len(self.num_text) >= self.NUM_MAX_LEN[self.num_from]:
            self.num_msg = "Maximum length reached (values 0 to 255)."
            return True
        self.num_text += ch
        self.num_msg = ""
        return True

    # ---- step builders (one per conversion rule) -----------------------

    def _num_p_bin2dec(self, b):
        weights = [2 ** (len(b) - 1 - i) for i in range(len(b))]
        used = [w for w, bit in zip(weights, b) if bit == "1"]
        on = [bit == "1" for bit in b]
        rows = [
            ("PLACE VALUE", [str(w) for w in weights], None),
            ("BIT", list(b), on),
            ("BIT x VALUE", [str(w) if bit == "1" else "0"
                             for w, bit in zip(weights, b)], on),
        ]
        if used:
            line = ("Add the values where the bit is 1: "
                    + " + ".join(map(str, used)) + f" = {sum(used)}")
        else:
            line = "No bit is 1, so the total is 0."
        return {"title": "BINARY -> DECIMAL: add the place values",
                "rows": rows, "lines": [line]}

    def _num_divide(self, n, base, digits):
        """Repeated-division table shared by DEC->BIN and DEC->HEX."""
        if n == 0:
            return None, "0", ["Zero is simply 0 in every number system."]
        numbers, quotients, remainders = [], [], []
        x = n
        while x > 0:
            numbers.append(str(x))
            quotients.append(str(x // base))
            remainders.append(digits[x % base])
            x //= base
        rows = [
            ("NUMBER", numbers, None),
            (f"DIVIDE BY {base}", quotients, None),
            ("REMAINDER", remainders, [True] * len(remainders)),
        ]
        return rows, "".join(reversed(remainders)), []

    def _num_p_dec2bin(self, n, b):
        rows, raw, lines = self._num_divide(n, 2, "01")
        if rows:
            lines = [f"Read the remainders from LAST to FIRST: {raw}"]
            if raw != b:
                lines.append(f"Add leading zeros to fill {len(b)} bits: {b}")
        return {"title": "DECIMAL -> BINARY: divide by 2",
                "rows": rows, "lines": lines}

    def _num_p_dec2hex(self, n):
        rows, raw, lines = self._num_divide(n, 16, "0123456789ABCDEF")
        if rows:
            lines = [f"Read the remainders from LAST to FIRST: {raw}",
                     "Remainders 10-15 are written A-F."]
        return {"title": "DECIMAL -> HEX: divide by 16",
                "rows": rows, "lines": lines}

    def _num_p_gray2bin(self, g, b):
        rows = [
            ("GRAY", list(g), None),
            ("RULE", ["copy"] + [f"{b[i - 1]}^{g[i]}" for i in range(1, len(g))],
             None),
            ("BINARY", list(b), [True] * len(b)),
        ]
        lines = ["First bit: copy it. Next: previous binary bit XOR this "
                 "Gray bit.", f"Gray {g} = binary {b}"]
        return {"title": "GRAY -> BINARY: XOR down the line",
                "rows": rows, "lines": lines}

    def _num_p_bin2gray(self, b, g):
        rows = [
            ("BINARY", list(b), None),
            ("RULE", ["copy"] + [f"{b[i]}^{b[i - 1]}" for i in range(1, len(b))],
             None),
            ("GRAY", list(g), [True] * len(g)),
        ]
        lines = ["First bit: copy it. Next: this bit XOR the bit before it.",
                 f"Binary {b} = Gray {g}"]
        return {"title": "BINARY -> GRAY: XOR neighbouring bits",
                "rows": rows, "lines": lines}

    def _num_p_hex2bin(self, h):
        groups = [format(int(d, 16), "04b") for d in h]
        rows = [
            ("HEX DIGIT", list(h), None),
            ("DECIMAL", [str(int(d, 16)) for d in h], None),
            ("4 BITS", groups, [True] * len(groups)),
        ]
        lines = ["Each hex digit becomes 4 bits (A=10 B=11 C=12 D=13 E=14 "
                 "F=15).", "Join the groups: " + "".join(groups)]
        return {"title": "HEX -> BINARY: 4 bits per digit",
                "rows": rows, "lines": lines}

    def _num_p_bin2hex(self, b):
        padded = b.zfill(((len(b) + 3) // 4) * 4)
        groups = [padded[i:i + 4] for i in range(0, len(padded), 4)]
        digits = [format(int(g, 2), "X") for g in groups]
        rows = [
            ("4 BITS", groups, None),
            ("DECIMAL", [str(int(g, 2)) for g in groups], None),
            ("HEX DIGIT", digits, [True] * len(digits)),
        ]
        lines = []
        if padded != b:
            lines.append(f"Add leading zeros so the length is a multiple "
                         f"of 4: {padded}")
        lines.append("Convert each group of 4 bits (8,4,2,1): "
                     + "".join(digits))
        return {"title": "BINARY -> HEX: group the bits in fours",
                "rows": rows, "lines": lines}

    def _num_p_hex2dec(self, h):
        weights = [16 ** (len(h) - 1 - i) for i in range(len(h))]
        values = [int(d, 16) for d in h]
        products = [v * w for v, w in zip(values, weights)]
        on = [True] * len(h)
        rows = [
            ("HEX DIGIT", list(h), None),
            ("DIGIT VALUE", [str(v) for v in values], None),
            ("PLACE VALUE", [str(w) for w in weights], None),
            ("VALUE x PLACE", [str(v) for v in products], on),
        ]
        line = ("Add the last row: " + " + ".join(map(str, products))
                + f" = {sum(products)}")
        return {"title": "HEX -> DECIMAL: place values of 16",
                "rows": rows, "lines": [line]}

    def _num_build(self):
        """Returns (error, result_text, steps) for the current input."""
        if not self.num_text:
            return "Type a value, or press UP / the +1 button.", "", []
        n = self._num_value()
        if n is None:
            return ("This lab converts values from 0 to 255 (8 bits).",
                    "", [])

        width = self._num_width(n)
        b = format(n, "b").zfill(width)
        g = format(n ^ (n >> 1), "b").zfill(width)
        h = format(n, "X").zfill((width + 3) // 4)
        frm, to = self.num_from, self.num_to
        result = self._num_format(to, n, width)

        if frm == to:
            same = {"title": "SAME SYSTEM", "rows": None, "lines": [
                "Both sides use the same system, so nothing changes. "
                "Pick a different TO system."]}
            return None, result, [same]

        builders = {
            "dec2bin": lambda: self._num_p_dec2bin(n, b),
            "bin2dec": lambda: self._num_p_bin2dec(b),
            "gray2bin": lambda: self._num_p_gray2bin(g, b),
            "bin2gray": lambda: self._num_p_bin2gray(b, g),
            "hex2bin": lambda: self._num_p_hex2bin(h),
            "bin2hex": lambda: self._num_p_bin2hex(b),
            "hex2dec": lambda: self._num_p_hex2dec(h),
            "dec2hex": lambda: self._num_p_dec2hex(n),
        }
        pipelines = {
            (1, 0): ["dec2bin"], (0, 1): ["bin2dec"],
            (2, 0): ["gray2bin"], (0, 2): ["bin2gray"],
            (3, 0): ["hex2bin"], (0, 3): ["bin2hex"],
            (3, 1): ["hex2dec"], (1, 3): ["dec2hex"],
            (1, 2): ["dec2bin", "bin2gray"],
            (2, 1): ["gray2bin", "bin2dec"],
            (2, 3): ["gray2bin", "bin2hex"],
            (3, 2): ["hex2bin", "bin2gray"],
        }
        names = pipelines[(frm, to)]
        steps = [builders[name]() for name in names]
        if len(steps) > 1:
            for i, step in enumerate(steps):
                step["title"] = f"STEP {i + 1} OF {len(steps)}  " + step["title"]
        return None, result, steps

    # ---- drawing ---------------------------------------------------------

    def _num_draw_table(self, screen, x, y, width, rows):
        label_w = 118
        columns = max(len(cells) for _l, cells, _h in rows)
        cell_w = max(30, min(64, (width - label_w) // max(1, columns)))
        row_h = 21
        for r_index, (label, cells, highlight) in enumerate(rows):
            ry = y + r_index * row_h
            lab = self.tiny_font.render(label, False, INK)
            screen.blit(lab, (x, ry + 4))
            for c_index, text in enumerate(cells):
                rect = pygame.Rect(x + label_w + c_index * cell_w, ry,
                                   cell_w - 2, row_h - 2)
                on = bool(highlight and highlight[c_index])
                pygame.draw.rect(screen, (185, 224, 226) if on else PAPER, rect)
                pygame.draw.rect(screen, CYAN if on else PAGE_LINE, rect, 2)
                font = (self.small_font
                        if self.small_font.size(text)[0] <= cell_w - 8
                        else self.tiny_font)
                surf = font.render(text, False, INK)
                screen.blit(surf, surf.get_rect(center=rect.center))
        return len(rows) * row_h

    def _draw_numbers_page(self, screen, content):
        self.buttons = []
        X, Y = content.x, content.y
        wire = (55, 125, 151)
        lit = (40, 205, 130)
        dark = (7, 27, 39)

        title = self._fit_text("NUMBER SYSTEMS", content.width, 20, INK)
        screen.blit(title, (X + 3, Y + 2))
        pygame.draw.line(screen, PAGE_LINE, (X + 2, Y + 35),
                         (content.right - 2, Y + 35), 2)

        # ---- FROM / TO selectors --------------------------------------
        for row, (label, current, action) in enumerate((
            ("FROM", self.num_from, "num_from"),
            ("TO", self.num_to, "num_to"),
        )):
            ry = Y + 43 + row * 34
            self._text(screen, label, X + 3, ry + 6, INK, self.small_font)
            bx = X + 62
            for i, name in enumerate(self.NUM_SYSTEMS):
                rect = pygame.Rect(bx, ry, 96, 28)
                self._draw_button(screen, rect, name, i == current)
                self.buttons.append((rect, (action, i)))
                bx += 104
        swap = pygame.Rect(X + 62 + 4 * 104 + 8, Y + 43, 150, 62)
        self._draw_button(screen, swap, "SWAP [TAB]", False)
        self.buttons.append((swap, ("num_swap", None)))

        # ---- input / result -----------------------------------------------
        err, result, steps = self._num_build()

        in_lbl = f"INPUT ({self.NUM_SYSTEMS[self.num_from]})"
        out_lbl = f"RESULT ({self.NUM_SYSTEMS[self.num_to]})"
        self._text(screen, in_lbl, X + 3, Y + 110, INK, self.tiny_font)
        self._text(screen, out_lbl, X + 290, Y + 110, INK, self.tiny_font)

        in_box = pygame.Rect(X + 3, Y + 124, 250, 36)
        out_box = pygame.Rect(X + 290, Y + 124, 250, 36)
        pygame.draw.rect(screen, dark, in_box)
        pygame.draw.rect(screen, CYAN, in_box, 3)
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        shown = self.num_text + cursor
        surf = self.title_font.render(shown, False, WHITE)
        screen.blit(surf, surf.get_rect(midleft=(in_box.x + 10, in_box.centery)))

        pygame.draw.rect(screen, dark, out_box)
        pygame.draw.rect(screen, CYAN, out_box, 3)
        res_surf = self.title_font.render(result or "?", False,
                                          lit if result else LOCKED)
        screen.blit(res_surf, res_surf.get_rect(
            midleft=(out_box.x + 10, out_box.centery)))
        self._draw_arrow(screen, wire, in_box.right + 3, out_box.x - 3,
                         in_box.centery)

        bx = X + 552
        for label, width, action in (("-1", 44, "num_minus"),
                                     ("+1", 44, "num_plus"),
                                     ("CLR", 58, "num_clear")):
            rect = pygame.Rect(bx, Y + 124, width, 36)
            self._draw_button(screen, rect, label, False)
            self.buttons.append((rect, (action, None)))
            bx += width + 4

        # ---- how it works ---------------------------------------------------
        self._text(screen, "HOW IT WORKS", X + 3, Y + 168, INK, self.tiny_font)
        if self.num_msg:
            self._text(screen, self.num_msg, X + 130, Y + 168, MAROON,
                       self.tiny_font)

        max_y = self.back_button.y - 6
        panel = pygame.Rect(X + 3, Y + 184, content.width - 6, max_y - (Y + 184))
        pygame.draw.rect(screen, (198, 202, 205), panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)

        screen.set_clip(panel.inflate(-4, -4))
        py = panel.y + 6
        if err:
            self._text(screen, err, panel.x + 8, py, MAROON, self.small_font)
        else:
            for step in steps:
                self._text(screen, step["title"], panel.x + 8, py,
                           DARK_GREEN, self.small_font)
                py += 22
                if step["rows"]:
                    py += self._num_draw_table(screen, panel.x + 8, py,
                                               panel.width - 16,
                                               step["rows"]) + 4
                for line in step["lines"]:
                    for wrapped in self._wrap_text(line, panel.width - 20,
                                                   self.small_font):
                        self._text(screen, wrapped, panel.x + 10, py, INK,
                                   self.small_font)
                        py += 19
                py += 8
        screen.set_clip(None)

        # ---- bottom row ---------------------------------------------------
        notes = pygame.Rect(content.right - 130, self.back_button.y, 130,
                            self.back_button.height)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("num_notes", None)))
        if self.num_from == 3:
            hint = "TYPE 0-9 A-F   UP/DOWN: +1/-1   ESC: BACK"
        else:
            hint = "TYPE A VALUE   UP/DOWN: +1/-1   LEFT/RIGHT: TO"
        h_surf = self.tiny_font.render(hint, False, MUTED)
        screen.blit(h_surf, (self.back_button.right + 14,
                             self.back_button.y + 8))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # BOOLEAN ALGEBRA CIRCUIT LAB
    # --------------------------------------------------------
    # SIMULATE: pick 2, 3 or 4 variables, add gates, wire them up, and the
    #           equation of the circuit you built appears underneath.
    # TEST:     a goal expression is shown. Build a circuit for it; a live
    #           table compares the GOAL output with your circuit row by row.
    #           Solve every goal to pass.

    def _on_bool_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "BOOLEAN ALGEBRA")

    def _on_bool_lab(self):
        return self._on_bool_page() and not self.bool_notes

    def _bool_key(self):
        """Workbench key: ("sim", n_vars) in SIMULATE, goal index in TEST."""
        if self.bool_test:
            return self.bool_idx
        return ("sim", self.bool_nvars)

    def _bool_names(self, key):
        if isinstance(key, tuple):
            return list(self.BOOL_VAR_NAMES[:key[1]])
        return list(self.BOOL_GOALS[key]["vars"])

    def _bool_get(self, key):
        """(Circuit, Workbench) for a key; built the first time it is needed."""
        if key not in self.bool_benches:
            names = self._bool_names(key)
            circuit = Circuit()
            slots = {1: [0.5], 2: [0.30, 0.70], 3: [0.20, 0.50, 0.80],
                     4: [0.14, 0.38, 0.62, 0.86]}[len(names)]
            for name, ry in zip(names, slots):
                circuit.add(Component(name, "SWITCH", 0.10, ry, label=name))
            circuit.add(Component("Y", "LED", 0.93, 0.5, label="Y"))
            circuit.size_scale = 0.75
            circuit.font_scale = 0.85
            circuit.auto_route = True
            bench = Workbench(circuit, allow_wiring=True, allow_placing=True,
                              allow_moving=True)
            self.bool_benches[key] = (circuit, bench)
        return self.bool_benches[key]

    def _bool_bench(self):
        return self._bool_get(self._bool_key())[1]

    def _bool_rows(self, key):
        """[(input_bits, goal_output_or_None, player_output_or_None)]."""
        circuit, _bench = self._bool_get(key)
        names = self._bool_names(key)
        rows = circuit.truth_table(names, "Y")
        if isinstance(key, tuple):                       # SIMULATE: no goal
            return [(bits, None, out) for bits, out in rows]
        goal = self.BOOL_GOALS[key]
        return [(bits, int(goal["f"](*bits)), out) for bits, out in rows]

    # ---- the equation of the circuit ----------------------------------------
    # The equation is read from the WIRING: start at lamp Y and follow every
    # wire back to the switches. An XOR gate on A and B reads "A XOR B".
    # A second line shows the simplified form, worked out from the truth table.

    # How tightly each kind of expression binds (used to place brackets).
    _BOOL_PREC = {"var": 6, "not": 6, "nand": 6, "nor": 6,
                  "and": 4, "xor": 3, "xnor": 3, "or": 2}

    def _bool_not(self, node):
        """NOT of an expression. NOT of a gate becomes the opposite gate
        (NOT of AND is NAND), and NOT of NOT cancels."""
        kind = node[0]
        if kind == "var":
            return ("not", node)
        if kind == "not":
            return node[1]
        flip = {"and": "nand", "nand": "and", "or": "nor", "nor": "or",
                "xor": "xnor", "xnor": "xor"}
        return (flip[kind], node[1], node[2])

    def _bool_expr(self, circuit, cid):
        """Expression tree for a component, or None if any input in its
        cone is still unwired."""
        comp = circuit.comps[cid]
        if comp.kind == "SWITCH":
            return ("var", comp.label or comp.id)
        if comp.kind in ("SOURCE", "DFF"):
            return None
        kids = []
        for pin in range(comp.n_inputs):
            src = circuit.source_of(cid, pin)
            if src is None:
                return None
            sub = self._bool_expr(circuit, src)
            if sub is None:
                return None
            kids.append(sub)
        if comp.kind == "LED":
            return kids[0]
        if comp.kind == "NOT":
            return self._bool_not(kids[0])
        return (comp.kind.lower(), kids[0], kids[1])

    def _bool_is_product(self, node):
        kind = node[0]
        if kind in ("var", "not"):
            return True
        if kind == "and":
            return (self._bool_is_product(node[1])
                    and self._bool_is_product(node[2]))
        return False

    def _bool_fmt(self, node, parent=0):
        """Expression tree -> text. Uses A' for NOT, AB for AND of literals,
        + for OR and the words XOR / XNOR."""
        kind = node[0]
        prec = self._BOOL_PREC[kind]

        if kind == "var":
            return node[1]
        if kind == "not":
            return node[1][1] + "'"
        if kind in ("nand", "nor"):
            inner = "and" if kind == "nand" else "or"
            return "(" + self._bool_fmt((inner, node[1], node[2]), 0) + ")'"

        def child(sub):
            need = prec
            if kind == "or" and sub[0] in ("xor", "xnor"):
                need = 4                       # (A XOR B) + C, clearer
            if (kind in ("xor", "xnor") and sub[0] in ("xor", "xnor")
                    and "xnor" in (kind, sub[0])):
                need = 4                       # never chain around an XNOR
            return self._bool_fmt(sub, need)

        a, b = child(node[1]), child(node[2])
        if kind == "and":
            both = (self._bool_is_product(node[1])
                    and self._bool_is_product(node[2]))
            text = (a + b) if both else (a + "·" + b)
        elif kind == "or":
            text = a + " + " + b
        else:
            text = a + (" XOR " if kind == "xor" else " XNOR ") + b

        return "(" + text + ")" if prec < parent else text

    def _bool_sop(self, ones, n):
        """Minimal sum of products. Returns a list of terms; each term is a
        list of literals. [] means constant 0, [[]] means constant 1."""
        ones = frozenset(ones)
        if not ones:
            return []
        if len(ones) == 2 ** n:
            return [[]]
        names = self.BOOL_VAR_NAMES
        cubes = []
        for pattern in itertools.product((0, 1, None), repeat=n):
            cover = frozenset(
                m for m in range(2 ** n)
                if all(p is None or ((m >> (n - 1 - i)) & 1) == p
                       for i, p in enumerate(pattern)))
            if cover <= ones:
                cubes.append((pattern, cover))
        primes = [c for c in cubes
                  if not any(c[1] < other[1] for other in cubes)]
        primes.sort(key=lambda c: (-len(c[1]), sorted(c[1])))

        chosen = primes
        for count in range(1, len(primes) + 1):
            best = None
            for combo in itertools.combinations(primes, count):
                if frozenset().union(*(c[1] for c in combo)) >= ones:
                    letters = sum(1 for c in combo for p in c[0]
                                  if p is not None)
                    if best is None or letters < best[0]:
                        best = (letters, list(combo))
            if best:
                chosen = best[1]
                break

        terms = []
        for pattern, _cover in chosen:
            terms.append([names[i] + ("" if p else "'")
                          for i, p in enumerate(pattern) if p is not None])
        # Tidy order: AB + C (not C + AB), and A'B + AB' (not AB' + A'B).
        terms.sort(key=lambda t: ([l[0] for l in t],
                                  [not l.endswith("'") for l in t]))
        return terms

    @staticmethod
    def _bool_sop_text(terms):
        if not terms:
            return "0"
        if terms == [[]]:
            return "1"
        return " + ".join("".join(t) for t in terms)

    def _bool_simplest(self, rows, names):
        """Simplest form of the circuit's behaviour, from its truth table:
        XOR / XNOR / NAND / NOR when it is one of those, otherwise the
        minimal sum of products."""
        n = len(names)
        ones = frozenset(
            int("".join(str(int(b)) for b in bits), 2)
            for bits, _w, out in rows if out)
        cache_key = (tuple(names), ones)
        if cache_key in self.bool_eq_cache:
            return self.bool_eq_cache[cache_key]

        full = frozenset(range(2 ** n))
        sop = self._bool_sop(ones, n)
        sop_text = self._bool_sop_text(sop)
        named = None

        # XOR / XNOR of two or more of the inputs.
        for size in range(2, n + 1):
            for subset in itertools.combinations(range(n), size):
                parity = frozenset(
                    m for m in range(2 ** n)
                    if sum((m >> (n - 1 - i)) & 1 for i in subset) % 2)
                if parity == ones or parity == full - ones:
                    invert = parity != ones
                    letters = [names[i] for i in subset]
                    if size == 2:
                        named = (f"{letters[0]} "
                                 f"{'XNOR' if invert else 'XOR'} {letters[1]}")
                    else:
                        body = " XOR ".join(letters)
                        named = f"({body})'" if invert else body
                    break
            if named:
                break

        # NAND / NOR style forms.
        if not named and ones and ones != full:
            comp = self._bool_sop(full - ones, n)
            if (len(comp) == 1 and len(comp[0]) >= 2 and len(sop) > 1
                    and all(not l.endswith("'") for l in comp[0])):
                named = "(" + "·".join(comp[0]) + ")'"
            elif (len(sop) == 1 and len(sop[0]) >= 2
                  and all(l.endswith("'") for l in sop[0])
                  and len(comp) >= 2 and all(len(t) == 1 for t in comp)):
                named = "(" + " + ".join(t[0] for t in comp) + ")'"

        result = named or sop_text
        self.bool_eq_cache[cache_key] = result
        return result

    def _bool_equation(self, circuit, rows, names):
        """(main, extra). main = the equation read from the wiring.
        (None, None) while Y is not fully connected."""
        src = circuit.source_of("Y", 0)
        if src is None:
            return None, None
        tree = self._bool_expr(circuit, src)
        if tree is None:
            return None, None
        main = self._bool_fmt(tree)

        if rows and all(out is not None for _b, _w, out in rows):
            best = self._bool_simplest(rows, names)
            def plain(text):
                return text.replace("·", "").replace(" ", "")
            if plain(best) != plain(main):
                def literals(text):
                    return sum(text.count(v) for v in self.BOOL_VAR_NAMES)
                label = ("Simplified: " if literals(best) < literals(main)
                         else "Sum of products: ")
                return main, label + best
        return main, "This is already the simplest form."

    # ---- actions ----------------------------------------------------------

    def _bool_add(self, kind):
        bench = self._bool_bench()
        self.bool_msg = bench.spawn(kind, max_gates=self.BOOL_MAX_GATES)

    def _bool_goto(self, idx):
        if not self.bool_test:
            return
        self.bool_idx = idx % len(self.BOOL_GOALS)
        self.bool_msg = ""

    def _bool_toggle_mode(self):
        self.bool_test = not self.bool_test
        if self.bool_test:
            self.bool_msg = ("Build a circuit for the goal. Solve every goal "
                             "to pass.")
        else:
            self.bool_msg = ""

    def _bool_set_vars(self, n):
        self.bool_nvars = max(self.BOOL_MIN_VARS, min(self.BOOL_MAX_VARS, n))
        self.bool_msg = ""

    def _bool_reset(self):
        self.bool_benches.pop(self._bool_key(), None)
        self.bool_msg = "Circuit cleared. Switches and lamp are back."

    def _bool_mouse(self, event):
        """Send mouse events to the workbench. True when handled."""
        bench = self._bool_bench()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and any(
                rect.collidepoint(event.pos) for rect, _a in self.buttons
            ):
                return False                  # a palette / control button
            if event.button not in (1, 3):
                return False
            if not bench.area.collidepoint(event.pos):
                return False

        msg = bench.handle_event(event)
        if msg:
            self.bool_msg = msg
        return True

    def _bool_handle_key(self, event):
        """Boolean-lab keys. Returns True when the key was used."""
        key = event.key
        if key == pygame.K_t:
            self.bool_notes = not self.bool_notes
            self.topic_scroll = 0
            return True
        if self.bool_notes:
            return False

        if key == pygame.K_m:
            self._bool_toggle_mode()
            return True
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s,
                   pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return True
        if key == pygame.K_LEFT:
            if self.bool_test:
                self._bool_goto(self.bool_idx - 1)
            else:
                self._bool_set_vars(self.bool_nvars - 1)
            return True
        if key == pygame.K_RIGHT:
            if self.bool_test:
                self._bool_goto(self.bool_idx + 1)
            else:
                self._bool_set_vars(self.bool_nvars + 1)
            return True
        if key == pygame.K_r:
            self._bool_reset()
            return True

        digits = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                  pygame.K_5, pygame.K_6, pygame.K_7)
        if key in digits:
            self._bool_add(self.BOOL_PALETTE[digits.index(key)])
            return True
        return False

    # ---- drawing ------------------------------------------------------------

    def _draw_bool_lab(self, screen, content):
        self.buttons = []
        X, Y = content.x, content.y
        test = self.bool_test
        key = self._bool_key()
        idx = self.bool_idx
        total = len(self.BOOL_GOALS)
        circuit, bench = self._bool_get(key)
        rows = self._bool_rows(key)
        names = self._bool_names(key)

        matches, solved = 0, False
        if test:
            matches = sum(1 for _b, g, m in rows if m == g)
            solved = bool(rows) and matches == len(rows)
            if solved:
                self.bool_solved.add(idx)

        # ---- title / mode tag ---------------------------------------------
        title = self._fit_text("BOOLEAN ALGEBRA", content.width, 20, INK)
        screen.blit(title, (X + 3, Y + 2))
        if test:
            tag = f"TEST MODE  SOLVED {len(self.bool_solved)}/{total}"
            if len(self.bool_solved) == total:
                tag += "  [PASSED]"
            tag_col = MAROON
        else:
            tag, tag_col = "SIMULATE", DARK_GREEN
        tag_s = self.small_font.render(tag, False, tag_col)
        screen.blit(tag_s, tag_s.get_rect(topright=(content.right - 3, Y + 8)))
        pygame.draw.line(screen, PAGE_LINE, (X + 2, Y + 35),
                         (content.right - 2, Y + 35), 2)

        # ---- variables selector (SIMULATE) / goal expression (TEST) --------
        if test:
            goal = self.BOOL_GOALS[idx]
            goal_text = f"GOAL {idx + 1}/{total}:   Y = {goal['expr']}"
            surf = self._fit_text(goal_text, content.width - 130, 22, MAROON)
            screen.blit(surf, (X + 3, Y + 42))
            if solved:
                t = self.small_font.render("[SOLVED]", False, DARK_GREEN)
                screen.blit(t, t.get_rect(topright=(content.right - 3, Y + 46)))
        else:
            self._text(screen, "VARIABLES:", X + 3, Y + 48, INK,
                       self.small_font)
            bx = X + 130
            for n in range(self.BOOL_MIN_VARS, self.BOOL_MAX_VARS + 1):
                rect = pygame.Rect(bx, Y + 42, 100, 28)
                self._draw_button(screen, rect, f"{n} VARS",
                                  n == self.bool_nvars)
                self.buttons.append((rect, ("bool_vars", n)))
                bx += 108
            self._text(screen, "Inputs: " + ", ".join(names), bx + 8, Y + 48,
                       MUTED, self.small_font)

        # ---- gate palette -----------------------------------------------
        gap = 6
        n_gates = len(self.BOOL_PALETTE)
        pal_w = (content.width - 6 - gap * (n_gates - 1)) // n_gates
        for i, kind in enumerate(self.BOOL_PALETTE):
            rect = pygame.Rect(X + 3 + i * (pal_w + gap), Y + 74, pal_w, 28)
            self._draw_button(screen, rect, f"{i + 1} {kind}", False)
            self.buttons.append((rect, ("bool_add", kind)))

        # ---- control row ------------------------------------------------
        if test:
            controls = (("< PREV", "bool_prev", 110),
                        ("NEXT >", "bool_next", 110),
                        ("RESET [R]", "bool_reset", 120),
                        ("SIMULATE [M]", "bool_mode", 170))
        else:
            controls = (("RESET [R]", "bool_reset", 120),
                        ("TEST MODE [M]", "bool_mode", 170))
        bx = X + 3
        for label, action, width in controls:
            rect = pygame.Rect(bx, Y + 108, width, 26)
            self._draw_button(screen, rect, label, False)
            self.buttons.append((rect, (action, None)))
            bx += width + 8
        gates_txt = self.small_font.render(
            f"GATES {circuit.count_gates()}/{self.BOOL_MAX_GATES}", False, INK)
        screen.blit(gates_txt, (bx + 6, Y + 113))

        # ---- workbench ----------------------------------------------------
        top = Y + 142
        eq_h = 0 if test else 34              # room for the equation box
        bench_h = max(140, self.back_button.y - 26 - eq_h - top)
        bench_w = int(content.width * 0.64)
        bench.area = pygame.Rect(X + 3, top, bench_w, bench_h)
        bench.draw(screen)

        # ---- live truth table ---------------------------------------------
        table_x = bench.area.right + 12
        table_w = content.right - table_x - 3
        self._text(screen, "LIVE TRUTH TABLE", table_x, top - 1, INK,
                   self.tiny_font)

        headers = list(names) + (["GOAL", "MINE"] if test else ["Y"])
        col_w = max(1, table_w // len(headers))
        row_h = max(15, min(24, (bench_h - 72) // (len(rows) + 1)))
        table_top = top + 17

        for col, head in enumerate(headers):
            cell = pygame.Rect(table_x + col * col_w, table_top, col_w, row_h)
            pygame.draw.rect(screen, PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)
            surf = self.tiny_font.render(head, False, INK)
            screen.blit(surf, surf.get_rect(center=cell.center))

        good, bad = (190, 228, 205), (232, 190, 195)
        for r_index, (bits, want, got) in enumerate(rows):
            ry = table_top + (r_index + 1) * row_h
            if test:
                if got is None:
                    mine_fill, mine_edge = PAPER, PAGE_LINE
                elif got == want:
                    mine_fill, mine_edge = good, DARK_GREEN
                else:
                    mine_fill, mine_edge = bad, MAROON
                values = list(bits) + [want, "?" if got is None else got]
            else:
                lit_row = got is not None and got == 1
                mine_fill = (185, 224, 226) if lit_row else PAPER
                mine_edge = CYAN if lit_row else PAGE_LINE
                values = list(bits) + ["?" if got is None else got]
            for col, val in enumerate(values):
                cell = pygame.Rect(table_x + col * col_w, ry, col_w, row_h)
                last = col == len(values) - 1
                pygame.draw.rect(screen, mine_fill if last else PAPER, cell)
                pygame.draw.rect(screen, mine_edge if last else PAGE_LINE,
                                 cell, 2 if last else 1)
                surf = self.tiny_font.render(str(val), False, INK)
                screen.blit(surf, surf.get_rect(center=cell.center))

        if test:
            sy = table_top + (len(rows) + 1) * row_h + 8
            self._text(screen, f"ROWS OK: {matches}/{len(rows)}", table_x, sy,
                       DARK_GREEN if solved else INK, self.small_font)

        # ---- equation box (SIMULATE) --------------------------------------
        extra = None
        if not test:
            main, extra = self._bool_equation(circuit, rows, names)
            eq_rect = pygame.Rect(X + 3, bench.area.bottom + 3,
                                  content.width - 6, 30)
            pygame.draw.rect(screen, (7, 27, 39), eq_rect)
            pygame.draw.rect(screen, CYAN, eq_rect, 3)
            if main is None:
                eq_text = "Y = ?   (wire the gates into Y)"
                eq_col = (140, 160, 170)
            else:
                eq_text, eq_col = "Y = " + main, WHITE
            eq_s = self._fit_text(eq_text, eq_rect.width - 20, 22, eq_col)
            screen.blit(eq_s, eq_s.get_rect(
                midleft=(eq_rect.x + 10, eq_rect.centery)))

        # ---- status line ----------------------------------------------------
        if test:
            if solved:
                msg, colour = ("SOLVED! Your circuit matches the goal on every "
                               "row.", DARK_GREEN)
            elif self.bool_msg:
                msg, colour = self.bool_msg, INK
            elif any(m is None for _b, _g, m in rows):
                msg, colour = ("Y is not connected yet. Wire switches into "
                               "gates, then the last gate into Y.", MUTED)
            else:
                msg, colour = ("Red rows do not match the goal yet. Click the "
                               "switches to test.", MUTED)
        elif self.bool_msg:
            msg, colour = self.bool_msg, INK
        elif extra:
            msg, colour = extra, DARK_GREEN
        else:
            msg, colour = ("Add gates, wire the switches into them and the "
                           "last gate into Y. The equation appears above.",
                           MUTED)
        surf = self._fit_text(msg, content.width - 6, 15, colour)
        screen.blit(surf, (X + 3, bench.area.bottom + 5 + eq_h))

        # ---- bottom row -----------------------------------------------------
        notes = pygame.Rect(content.right - 130, self.back_button.y, 130,
                            self.back_button.height)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("bool_notes", None)))
        hint = ("DRAG PIN TO PIN: WIRE   RIGHT-CLICK: DELETE   LEFT/RIGHT: "
                + ("GOAL" if test else "VARIABLES"))
        room = notes.x - (self.back_button.right + 14) - 8
        h_surf = self._fit_text(hint, room, 12, MUTED)
        screen.blit(h_surf, (self.back_button.right + 14,
                             self.back_button.y + 8))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # TEXT WRAPPING
    # --------------------------------------------------------

    def _wrap_text(self, text, max_width, font):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()

            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    # --------------------------------------------------------
    # BACK BUTTON
    # --------------------------------------------------------

    def _draw_back_button(self, screen, label="BACK [B]"):
        if self.back_button is None:
            return

        self._draw_button(
            screen,
            self.back_button,
            label,
            selected=False,
        )

    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

    def draw(self, screen):
        """Draw the notebook overlay when open."""
        if not self.open:
            return

        _, content = self._draw_frame(screen)

        if self.page == "index":
            self._draw_index(screen, content)

        elif self.page == "level":
            self._draw_level_page(screen, content)

        elif self.page == "reference_index":
            self._draw_reference_index(screen, content)

        elif self.page == "reference_topic":
            self._draw_reference_topic(screen, content)

    # --------------------------------------------------------
    # KARNAUGH MAP LAB
    # --------------------------------------------------------
    # SIMULATE: click cells (0 -> 1 -> X). The biggest groups, the minimal
    #           equation and the reason for every term appear on their own.
    # TEST:     a fixed map is given. The player selects cells, saves each
    #           group and checks. Same rules as the Level 5 puzzle: only
    #           1s and Xs, rectangles of 1/2/4/8/16, wraparound, biggest
    #           possible groups, fewest groups. 5 correct in a row passes.

    def _on_km_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "KARNAUGH MAPS")

    def _km_minterm(self, r, c):
        return (self.KM_GRAY[r] << 2) | self.KM_GRAY[c]

    def _km_pos(self, m):
        return self.KM_GRAY.index(m >> 2), self.KM_GRAY.index(m & 3)

    def _km_build_rects(self):
        """Every legal group: straight rectangles with wraparound."""
        groups = set()
        for height in (1, 2, 4):
            for width in (1, 2, 4):
                for r0 in range(4):
                    for c0 in range(4):
                        groups.add(frozenset(
                            self._km_minterm((r0 + dr) % 4, (c0 + dc) % 4)
                            for dr in range(height) for dc in range(width)
                        ))
        return groups

    def _km_term(self, group):
        """(term, stay-list, change-list) for one group of minterms."""
        term, stay, change = "", [], []
        for bit in (3, 2, 1, 0):
            letter = self.KM_VARS[3 - bit]
            values = {(m >> bit) & 1 for m in group}
            if values == {1}:
                term += letter
                stay.append(f"{letter}=1")
            elif values == {0}:
                term += letter + "'"
                stay.append(f"{letter}=0")
            else:
                change.append(letter)
        return term or "1", stay, change

    def _km_detail(self, group):
        _term, stay, change = self._km_term(group)
        text = (" ".join(stay) + " stay") if stay else "nothing stays"
        if change:
            verb = "changes" if len(change) == 1 else "change"
            text += "; " + ",".join(change) + " " + verb + " (dropped)"
        return text

    def _km_wraps(self, group):
        rows = {self._km_pos(m)[0] for m in group}
        cols = {self._km_pos(m)[1] for m in group}
        return any(0 in s and 3 in s and len(s) < 4 for s in (rows, cols))

    def _km_equation(self, groups):
        terms = []
        for group in groups:
            term = self._km_term(group)[0]
            if term not in terms:
                terms.append(term)
        return " + ".join(terms) if terms else "0"

    def _km_primes(self, ones, dc):
        usable = ones | dc
        valid = [g for g in self.km_all_groups if g <= usable and g & ones]
        return {g for g in valid if not any(g < other for other in valid)}

    def _km_cover(self, ones, dc):
        """Fewest prime groups that cover every 1 (then fewest letters)."""
        key = (frozenset(ones), frozenset(dc))
        if key in self.km_cache:
            return self.km_cache[key]
        result = []
        if ones:
            primes = sorted(self._km_primes(ones, dc),
                            key=lambda g: (-len(g), sorted(g)))
            result = primes
            for count in range(1, len(primes) + 1):
                best = None
                for combo in itertools.combinations(primes, count):
                    if set().union(*combo) >= ones:
                        letters = sum(
                            0 if self._km_term(g)[0] == "1"
                            else len(self._km_term(g)[0].replace("'", ""))
                            for g in combo)
                        if best is None or letters < best[0]:
                            best = (letters, list(combo))
                if best:
                    result = best[1]
                    break
        self.km_cache[key] = result
        return result

    def _km_sets(self):
        if self.km_test:
            case = self.KM_TESTS[self.km_test_idx]
            return set(case["ones"]), set(case["dc"])
        ones = {m for m in range(16) if self.km_vals[m] == 1}
        dc = {m for m in range(16) if self.km_vals[m] == 2}
        return ones, dc

    def _km_say(self, text, ok=True):
        self.km_msg = text
        self.km_msg_ok = ok

    def _km_load_example(self, index):
        self.km_ex = index % len(self.KM_EXAMPLES)
        name, ones, dc = self.KM_EXAMPLES[self.km_ex]
        self.km_vals = [1 if m in ones else 2 if m in dc else 0
                        for m in range(16)]
        self.km_label = f"EXAMPLE {self.km_ex + 1}/{len(self.KM_EXAMPLES)}: {name}"
        self._km_say("")

    def _km_clear(self):
        if self.km_test:
            self.km_sel.clear()
            self.km_groups.clear()
            self._km_say("Selection and saved groups cleared.")
        else:
            self.km_vals = [0] * 16
            self.km_label = "YOUR OWN MAP"
            self._km_say("Map cleared. Click cells to make 1s.")

    def _km_toggle_mode(self):
        self.km_test = not self.km_test
        self.km_sel.clear()
        self.km_groups.clear()
        if self.km_test:
            self._km_say("Group all the 1s. Click cells, SPACE saves a "
                         "group, ENTER checks. 5 right in a row to pass.")
        else:
            self._km_say("")

    def _km_cell(self, m):
        if self.km_test:
            if m in self.km_sel:
                self.km_sel.remove(m)
            else:
                self.km_sel.add(m)
            self._km_say(f"{len(self.km_sel)} cell(s) selected. "
                         "Press SPACE to save the group.")
        else:
            self.km_vals[m] = (self.km_vals[m] + 1) % 3
            self.km_label = "YOUR OWN MAP"
            self._km_say("")

    def _km_save(self):
        if not self.km_test:
            return
        ones, dc = self._km_sets()
        if not self.km_sel:
            self._km_say("Select one or more cells first.", ok=False)
            return
        group = frozenset(self.km_sel)
        if group not in self.km_all_groups:
            self._km_say("Invalid shape. Use a rectangle of 1, 2, 4, 8 or 16 "
                         "cells. Wrapping is allowed; diagonals are not.",
                         ok=False)
            return
        if not group <= (ones | dc):
            self._km_say("A group may hold 1s and Xs, never 0s.", ok=False)
            return
        if not group & ones:
            self._km_say("A group needs at least one 1 (Xs alone are not "
                         "enough).", ok=False)
            return
        if group in self.km_groups:
            self.km_sel.clear()
            self._km_say("That group is already saved.", ok=False)
            return
        if group not in self._km_primes(ones, dc):
            self.km_sel.clear()
            self._km_say("This group can be bigger. Look for a larger "
                         "rectangle (use wraparound and Xs).", ok=False)
            return
        self.km_groups.append(group)
        self.km_sel.clear()
        term = self._km_term(group)[0]
        self._km_say(f"Group {len(self.km_groups)} saved: {term}. Groups may "
                     "overlap. Cover every 1, then press ENTER.")

    def _km_undo(self):
        if self.km_sel:
            self.km_sel.clear()
            self._km_say("Selection cleared.")
        elif self.km_groups:
            self.km_groups.pop()
            self._km_say("Last saved group removed.")

    def _km_check(self):
        if not self.km_test:
            return
        ones, dc = self._km_sets()
        if not self.km_groups:
            self._km_say("Save at least one group first.", ok=False)
            return
        covered = set().union(*self.km_groups)
        missing = sorted(ones - covered)
        needed = len(self._km_cover(ones, dc))
        if missing:
            self.km_streak = 0
            self._km_say("Still uncovered: " + ", ".join(f"m{m}" for m in missing)
                         + ". Streak reset.", ok=False)
            return
        if len(self.km_groups) > needed:
            self.km_streak = 0
            self._km_say("Everything is covered, but it is not simplified. "
                         f"Use only {needed} group(s). Streak reset.", ok=False)
            return

        equation = self._km_equation(self.km_groups)
        self.km_streak += 1
        if self.km_streak >= 5:
            self.km_passed = True
            self._km_say(f"CHALLENGE PASSED! F = {equation}. You can simplify "
                         "a K-map.")
        else:
            self._km_say(f"CORRECT! F = {equation}. Streak "
                         f"{self.km_streak}/5. Next map.")
        self.km_test_idx = (self.km_test_idx + 1) % len(self.KM_TESTS)
        self.km_groups.clear()
        self.km_sel.clear()

    def _km_handle_key(self, event):
        """K-map-page keys. Returns True when the key was used."""
        key = event.key
        if key == pygame.K_t:
            self.km_notes = not self.km_notes
            self.topic_scroll = 0
            return True
        if self.km_notes:
            return False
        if key == pygame.K_m:
            self._km_toggle_mode()
            return True
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                   pygame.K_w, pygame.K_s):
            return True

        if self.km_test:
            if key == pygame.K_SPACE:
                self._km_save()
                return True
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._km_check()
                return True
            if key == pygame.K_r:
                self._km_clear()
                return True
            if key == pygame.K_BACKSPACE:
                if self.km_sel or self.km_groups:
                    self._km_undo()
                    return True
                return False                  # nothing to undo: BACKSPACE = back
        else:
            if key == pygame.K_c:
                self._km_clear()
                return True
            if key == pygame.K_e:
                self._km_load_example(self.km_ex + 1)
                return True
            if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                return True
        return False

    def _draw_kmap_lab(self, screen, content):
        self.buttons = []
        X, Y = content.x, content.y
        test = self.km_test
        ones, dc = self._km_sets()
        groups = list(self.km_groups) if test else self._km_cover(ones, dc)
        colours = self.KM_COLOURS

        # ---- title / mode tag ------------------------------------------
        title = self._fit_text("KARNAUGH MAPS", content.width, 20, INK)
        screen.blit(title, (X + 3, Y + 2))
        if test:
            tag = f"TEST MODE  STREAK {self.km_streak}/5"
        else:
            tag = "SIMULATE"
        if self.km_passed:
            tag += "  [PASSED]"
        tag_s = self.small_font.render(tag, False, MAROON if test else DARK_GREEN)
        screen.blit(tag_s, tag_s.get_rect(topright=(content.right - 3, Y + 8)))
        pygame.draw.line(screen, PAGE_LINE, (X + 2, Y + 35),
                         (content.right - 2, Y + 35), 2)

        if test:
            info = (f"TEST {self.km_test_idx + 1}/{len(self.KM_TESTS)}: group "
                    "every 1. Click cells, SPACE saves, ENTER checks.")
        else:
            info = ("Click a cell: 0 -> 1 -> X. The groups and the equation "
                    "appear by themselves.")
        info_s = self._fit_text(info, content.width - 6, 16, INK)
        screen.blit(info_s, (X + 3, Y + 41))

        # ---- grid ----------------------------------------------------------
        lw, lh = 44, 22
        cw = max(36, min(64, (int(content.width * 0.42) - lw) // 4))
        ch = 50 if content.height >= 560 else 40
        gx, gy = X + 3 + lw, Y + 96
        big = self.title_font if ch >= 48 else self.body_font

        corner = self.tiny_font.render("AB\\CD", False, CYAN)
        screen.blit(corner, corner.get_rect(center=(gx - lw // 2, gy - lh // 2)))
        for i, label in enumerate(self.KM_LABELS):
            col = self.tiny_font.render(label, False, (0, 91, 103))
            screen.blit(col, col.get_rect(
                center=(gx + i * cw + cw // 2, gy - lh // 2)))
            row = self.tiny_font.render(label, False, (0, 91, 103))
            screen.blit(row, row.get_rect(
                center=(gx - lw // 2, gy + i * ch + ch // 2)))

        for m in range(16):
            r, c = self._km_pos(m)
            rect = pygame.Rect(gx + c * cw, gy + r * ch, cw, ch)
            if test:
                value = 1 if m in ones else 2 if m in dc else 0
            else:
                value = self.km_vals[m]
            if test and m in self.km_sel:
                fill, ink = CYAN, (0, 45, 55)
            elif value == 1:
                fill, ink = (24, 145, 145), WHITE
            elif value == 2:
                fill, ink = (145, 105, 35), WHITE
            else:
                fill, ink = (17, 35, 52), WHITE
            pygame.draw.rect(screen, fill, rect)
            pygame.draw.rect(screen, PAGE_LINE, rect, 2)
            v_s = big.render(("0", "1", "X")[value], False, ink)
            screen.blit(v_s, v_s.get_rect(
                center=(rect.centerx, rect.y + int(ch * 0.38))))
            m_s = self.tiny_font.render(f"m{m}", False, ink)
            screen.blit(m_s, m_s.get_rect(
                center=(rect.centerx, rect.bottom - 9)))
            self.buttons.append((rect, ("km_cell", m)))

        # Group outlines (inset a little more each time so overlaps show).
        for index, group in enumerate(groups):
            colour = colours[index % len(colours)]
            inset = 5 + (index % 4) * 3
            for m in group:
                r, c = self._km_pos(m)
                rect = pygame.Rect(gx + c * cw, gy + r * ch, cw, ch)
                pygame.draw.rect(screen, colour, rect.inflate(-inset, -inset), 3)

        grid_bottom = gy + 4 * ch

        # ---- groups panel --------------------------------------------------
        px = gx + 4 * cw + 18
        panel = pygame.Rect(px, Y + 70, content.right - px - 3,
                            grid_bottom - (Y + 70))
        pygame.draw.rect(screen, (198, 202, 205), panel)
        pygame.draw.rect(screen, PAGE_LINE, panel, 2)
        head = "SAVED GROUPS" if test else "GROUPS FOUND"
        screen.blit(self.tiny_font.render(head, False, INK),
                    (panel.x + 8, panel.y + 6))
        screen.set_clip(panel.inflate(-4, -4))
        ty = panel.y + 24
        if not groups:
            if test:
                text = "No groups saved yet."
            elif ones:
                text = "No groups."
            else:
                text = "No 1s on the map yet. Click cells to make some."
            for line in self._wrap_text(text, panel.width - 16, self.small_font):
                self._text(screen, line, panel.x + 8, ty, MUTED, self.small_font)
                ty += 20
        for index, group in enumerate(groups):
            colour = colours[index % len(colours)]
            term = self._km_term(group)[0]
            wrap = "  (wraps)" if self._km_wraps(group) else ""
            self._text(screen, f"G{index + 1}: {term}   {len(group)} cells{wrap}",
                       panel.x + 8, ty, colour, self.small_font)
            ty += 19
            cells = " ".join(f"m{m}" for m in sorted(group))
            for line in self._wrap_text(cells, panel.width - 20, self.tiny_font):
                self._text(screen, line, panel.x + 12, ty, INK, self.tiny_font)
                ty += 15
            for line in self._wrap_text(self._km_detail(group),
                                        panel.width - 20, self.tiny_font):
                self._text(screen, line, panel.x + 12, ty, MUTED, self.tiny_font)
                ty += 15
            ty += 6
        screen.set_clip(None)

        # ---- buttons -------------------------------------------------------
        by = grid_bottom + 10
        bx = X + 3
        if test:
            row = (("LAB [M]", "km_mode", 100), ("SAVE [SPACE]", "km_save", 150),
                   ("CHECK [ENTER]", "km_check", 160),
                   ("UNDO [BKSP]", "km_undo", 140))
        else:
            row = (("TEST MODE [M]", "km_mode", 160),
                   ("CLEAR [C]", "km_clear", 120),
                   ("EXAMPLE [E]", "km_example", 140))
        for label, action, width in row:
            rect = pygame.Rect(bx, by, width, 28)
            self._draw_button(screen, rect, label, False)
            self.buttons.append((rect, (action, None)))
            bx += width + 8

        # ---- equation ------------------------------------------------------
        eq_rect = pygame.Rect(X + 3, by + 38, content.width - 6, 36)
        pygame.draw.rect(screen, (7, 27, 39), eq_rect)
        pygame.draw.rect(screen, CYAN, eq_rect, 3)
        if test:
            eq_text = "YOUR F = " + (self._km_equation(groups) if groups else "?")
        elif not ones:
            eq_text = "F = 0"
        else:
            eq_text = "F = " + self._km_equation(groups)
        eq_s = self._fit_text(eq_text, eq_rect.width - 20, 25, WHITE)
        screen.blit(eq_s, eq_s.get_rect(midleft=(eq_rect.x + 10, eq_rect.centery)))

        # ---- explanation / feedback ---------------------------------------
        ty = eq_rect.bottom + 10
        limit = self.back_button.y - 6

        def put(text, colour, font=None, gap=21):
            nonlocal ty
            font = font or self.small_font
            for line in self._wrap_text(text, content.width - 10, font):
                if ty + gap > limit:
                    return
                self._text(screen, line, X + 5, ty, colour, font)
                ty += gap

        if test:
            if self.km_msg:
                put(self.km_msg, DARK_GREEN if self.km_msg_ok else MAROON)
            if self.km_sel:
                put("Selected: " + " ".join(f"m{m}" for m in sorted(self.km_sel)),
                    INK)
        else:
            put(self.km_label, INK)
            put(f"1s: {len(ones)}    Xs: {len(dc)}    Groups: {len(groups)}",
                INK)
            if self.km_msg:
                put(self.km_msg, DARK_GREEN if self.km_msg_ok else MAROON)
            put("Rule: a variable that STAYS the same inside a group is kept. "
                "One that CHANGES is dropped.", MUTED)
            if dc:
                put("X cells are don't-cares: the groups may use them, but they "
                    "never have to be covered.", MUTED)

        # ---- bottom row ----------------------------------------------------
        notes = pygame.Rect(content.right - 130, self.back_button.y, 130,
                            self.back_button.height)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("km_notes", None)))
        hint = ("CLICK CELLS: SELECT   SPACE: SAVE   ENTER: CHECK" if test
                else "CLICK CELLS: 0/1/X   E: EXAMPLE   M: TEST MODE")
        room = notes.x - (self.back_button.right + 14) - 8
        h_surf = self._fit_text(hint, room, 12, MUTED)
        screen.blit(h_surf, (self.back_button.right + 14,
                             self.back_button.y + 8))

        self._draw_back_button(screen)

    # --------------------------------------------------------
    # COMBINATIONAL CIRCUITS LAB (shared by both paths)
    # --------------------------------------------------------
    # The circuits live in puzzles/comb_lab.py (the Level 5 course draws the
    # same ones).  LEFT / RIGHT change circuit, 1-9 flip inputs, T = notes.

    def _on_comb_page(self):
        return (self.page == "reference_topic"
                and self.selected_level == "COMBINATIONAL CIRCUITS")

    def _comb_handle_key(self, event):
        if event.key == pygame.K_t:
            self.comb_notes = not self.comb_notes
            self.topic_scroll = 0
            return True
        if self.comb_notes:
            return False
        return self.comb.handle_key(event)

    def _draw_comb_lab(self, screen, content):
        self.buttons = []
        fonts = {"body": self.small_font, "small": self.small_font,
                 "tiny": self.tiny_font}
        self.comb.draw(screen, content, self.back_button.y - 6, fonts)
        notes = pygame.Rect(content.right - 130, self.back_button.y, 130,
                            self.back_button.height)
        self._draw_button(screen, notes, "NOTES [T]", False)
        self.buttons.append((notes, ("comb_notes", None)))
        hint = "CLICK SWITCHES OR PRESS 1-9   LEFT/RIGHT: CIRCUIT   R: RESET"
        room = notes.x - (self.back_button.right + 14) - 8
        screen.blit(self._fit_text(hint, room, 12, MUTED),
                    (self.back_button.right + 14, self.back_button.y + 8))
        self._draw_back_button(screen)
