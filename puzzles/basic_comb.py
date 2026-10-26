# puzzles/basic_seq.py
# BASIC LEVEL 6 - "Flip-flops, shift registers and counters" (8 stages)
#
# Plugs into terminal 6 (puzzle_id signal_breaker, notebook level_six) on the BASIC path.
# It reuses the frame, tiered hints, notebook autofill and answer buttons of
# puzzles/basic_gates.py and adds a small sequential-logic engine.
#
#   1  Memory (SR)          a flip-flop remembers one bit; set / reset / hold / not allowed
#   2  Clock + D            rising edge, D copies to Q, reading and drawing timing diagrams
#   3  T and JK             toggle, JK table, master-slave idea
#   4  Conversion           excitation table, JK->T, JK->D, D->T, SR->D
#   5  Shift registers      SISO, SIPO, PISO, PIPO and what the register holds after k clocks
#   6  Ripple counters      T flip-flops in a chain, mod-N, how many flip-flops
#   7  Synchronous counters same clock for all, T inputs, a small design
#   8  Boss                 exam-style timing diagrams, registers and counters
#
# Every answer in the course is produced or checked by the tiny engine below, so the
# tests can prove that no authored answer is wrong.
#
# Controls
#   mouse                    click switches, cells and buttons
#   SPACE or C               clock pulse        H  hint (press again for more)
#   0 / 1 / X                fill a cell        UP / DOWN / LEFT / RIGHT  move
#   ENTER                    check / continue

import random

import pygame

from puzzles.basic_gates import (
    BasicGatesPuzzle, WORK, FULL, wrap_text, draw_gate, draw_bulb,
    PANEL, PANEL_EDGE, CYAN, GREEN, RED, YELLOW, GREY, WHITE, WIRE_ON, WIRE_OFF,
)

if not hasattr(BasicGatesPuzzle, "LEGEND_EXTRA"):
    raise ImportError(
        "puzzles/basic_gates.py is the OLD version. Replace it with the one from "
        "the latest update zip (basic_seq.py needs the updated file)."
    )

X = 2                                  # "don't care" / "not allowed"
FF_INPUTS = {"SR": ("S", "R"), "D": ("D",), "T": ("T",), "JK": ("J", "K")}
SIGNAL_COLORS = [(110, 200, 255), (255, 170, 96), (170, 140, 255), (110, 240, 152)]


# ------------------------------------------------------------------
# ENGINE
# ------------------------------------------------------------------
def ff_next(kind, q, *inp):
    """Next value of Q after a clock edge. None = not allowed / unpredictable."""
    if kind == "SR":
        s, r = inp
        if s and r:
            return None
        if s:
            return 1
        if r:
            return 0
        return q
    if kind == "D":
        return inp[0]
    if kind == "T":
        if q is None:
            return None
        return 1 - q if inp[0] else q
    if kind == "JK":
        j, k = inp
        if j and k:
            return None if q is None else 1 - q
        if j:
            return 1
        if k:
            return 0
        return q
    raise ValueError(kind)


def input_combos(kind):
    n = len(FF_INPUTS[kind])
    return [tuple((v >> (n - 1 - i)) & 1 for i in range(n)) for v in range(1 << n)]


def char_rows(kind):
    """Rows of the characteristic table: (inputs, Qn)."""
    return [(c, q) for c in input_combos(kind) for q in (0, 1)]


def char_next(kind):
    out = []
    for c, q in char_rows(kind):
        nxt = ff_next(kind, q, *c)
        out.append(X if nxt is None else nxt)
    return out


def excitation(kind):
    """{(Q, Qnext): (needed input values, X where either value works)}."""
    table = {}
    for q in (0, 1):
        for qn in (0, 1):
            combos = [c for c in input_combos(kind) if ff_next(kind, q, *c) == qn]
            vals = []
            for i in range(len(FF_INPUTS[kind])):
                seen = {c[i] for c in combos}
                vals.append(seen.pop() if len(seen) == 1 else X)
            table[(q, qn)] = tuple(vals)
    return table


def simulate_ff(kind, q0, per_period_inputs):
    """Q after each rising edge. per_period_inputs: list of input tuples."""
    q, out = q0, []
    for inp in per_period_inputs:
        q = ff_next(kind, q, *inp)
        out.append(q)
    return out


def shift_right(reg, serial_in):
    return [serial_in] + list(reg[:-1])


def count_states(nbits, mod, start, pulses):
    states, s = [start], start
    for _ in range(pulses):
        s = (s + 1) % mod
        states.append(s)
    return states


def bit_of(state, i):
    return (state >> i) & 1


def t_inputs(state, nbits):
    """Synchronous up-counter: T0 = 1, Ti = Q0 AND ... AND Q(i-1)."""
    t, run = [], 1
    for i in range(nbits):
        t.append(run)
        run &= bit_of(state, i)
    return t


def bits_str(state, nbits):
    return format(state, f"0{nbits}b")


# ------------------------------------------------------------------
# DRAWING HELPERS
# ------------------------------------------------------------------
def dashed_vline(screen, x, y0, y1, color, dash=6, gap=5):
    y = y0
    while y < y1:
        pygame.draw.line(screen, color, (x, y), (x, min(y + dash, y1)), 1)
        y += dash + gap


def draw_arrow(screen, p0, p1, color, width=3):
    pygame.draw.line(screen, color, p0, p1, width)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    left = (p1[0] - 9 * ux + 5 * uy, p1[1] - 9 * uy - 5 * ux)
    right = (p1[0] - 9 * ux - 5 * uy, p1[1] - 9 * uy + 5 * ux)
    pygame.draw.polygon(screen, color, [p1, left, right])


def draw_waveforms(screen, fonts, x0, y0, per_w, n, rows, row_h=60, mark_edge=None):
    """Timing diagram. rows: dicts {name, kind: clk|input|out, vals, init, delay, upto, color}.

    Convention: the rising clock edge is in the MIDDLE of every period.
    Inputs change at the START of a period (so they are stable at the edge).
    Outputs change AT the rising edge.
    """
    f_small, f_tiny = fonts[1], fonts[2]
    amp = 24
    total_h = len(rows) * row_h
    for k in range(n):
        x = x0 + k * per_w + per_w // 2
        color = YELLOW if mark_edge == k else (62, 84, 104)
        dashed_vline(screen, x, y0 - 6, y0 + total_h - 8, color)
    for r, row in enumerate(rows):
        base = y0 + r * row_h + amp + 14
        color = row.get("color", WHITE)
        label = f_small.render(row["name"], True, color)
        screen.blit(label, label.get_rect(midright=(x0 - 12, base - amp // 2)))

        def level(v):
            return base - amp if v else base

        kind = row["kind"]
        pts = []
        if kind == "clk":
            pts = [(x0, base)]
            for k in range(n):
                mid = x0 + k * per_w + per_w // 2
                end = x0 + (k + 1) * per_w
                pts += [(mid, base), (mid, base - amp), (end, base - amp), (end, base)]
        else:
            vals = row["vals"]
            upto = row.get("upto", len(vals))
            cur = row.get("init", 0)
            if cur is None:
                continue
            pts = [(x0, level(cur))]
            shift = row.get("delay", 0)
            for k, v in enumerate(vals):
                if k >= upto or v is None:
                    break
                tx = x0 + k * per_w + (per_w // 2 + shift if kind == "out" else 0)
                if v != cur:
                    pts += [(tx, level(cur)), (tx, level(v))]
                    cur = v
            end_k = min(upto, n)
            for k, v in enumerate(vals[:end_k]):
                if v is None:
                    end_k = k
                    break
            pts.append((x0 + end_k * per_w, level(cur)))
        if len(pts) >= 2:
            pygame.draw.lines(screen, color, False, pts, 3)


def draw_flipflop(screen, fonts, rect, kind, q, ins=None, show_values=True):
    """A flip-flop block with input pins, a clock triangle and Q / Q' outputs."""
    f_body, f_small, f_tiny = fonts
    pygame.draw.rect(screen, (22, 40, 58), rect, border_radius=6)
    pygame.draw.rect(screen, WHITE, rect, 3, border_radius=6)
    names = FF_INPUTS[kind]
    pins = _input_pins(rect, len(names))
    for name, (px, py) in zip(names, pins):
        lab = f_body.render(name, True, YELLOW)
        screen.blit(lab, lab.get_rect(midleft=(rect.x + 10, py)))
        value = (ins or {}).get(name)
        on = bool(value)
        if show_values and value is not None:
            vt = f_small.render(str(value), True, GREEN if on else GREY)
            screen.blit(vt, vt.get_rect(midright=(rect.x - 42, py)))
        pygame.draw.line(screen, WIRE_ON if on else WIRE_OFF, (rect.x - 36, py), (rect.x, py), 4)
    cy = rect.y + int(rect.h * 0.85)
    tri = [(rect.x, cy - 12), (rect.x + 16, cy), (rect.x, cy + 12)]
    pygame.draw.lines(screen, WHITE, True, tri, 3)
    pygame.draw.line(screen, WIRE_OFF, (rect.x - 36, cy), (rect.x, cy), 4)
    clk = f_tiny.render("CLK", True, GREY)
    screen.blit(clk, clk.get_rect(midleft=(rect.x + 22, cy)))
    for label, frac, val in (("Q", 0.28, q), ("Q'", 0.72, None if q is None else 1 - q)):
        py = rect.y + int(rect.h * frac)
        pygame.draw.line(screen, WIRE_ON if val else WIRE_OFF, (rect.right, py), (rect.right + 36, py), 4)
        lab = f_body.render(label, True, WHITE)
        screen.blit(lab, lab.get_rect(midright=(rect.right - 10, py)))
    title = f_small.render(f"{kind} flip-flop", True, CYAN)
    screen.blit(title, title.get_rect(midbottom=(rect.centerx, rect.y - 6)))


def _input_pins(rect, n):
    if n == 1:
        return [(rect.x, rect.y + int(rect.h * 0.42))]
    return [(rect.x, rect.y + int(rect.h * 0.22)), (rect.x, rect.y + int(rect.h * 0.5))]


def ff_pin_ys(rect, n):
    return [py for _px, py in _input_pins(rect, n)]


def draw_register(screen, fonts, x0, y0, bits, box=62, gap=28, serial_in=False, parallel_in=False,
                  serial_out=False, parallel_out=False, si_value=None):
    """A row of flip-flop boxes. Returns the list of box rects."""
    f_body, f_small, f_tiny = fonts
    rects = []
    n = len(bits) if bits is not None else 4
    for i in range(n):
        rect = pygame.Rect(x0 + i * (box + gap), y0, box, box)
        rects.append(rect)
        v = None if bits is None else bits[i]
        pygame.draw.rect(screen, (30, 70, 56) if v else (22, 40, 58), rect, border_radius=6)
        pygame.draw.rect(screen, GREEN if v else WHITE, rect, 3, border_radius=6)
        if v is not None:
            img = f_body.render(str(v), True, WHITE)
            screen.blit(img, img.get_rect(center=rect.center))
        tri = [(rect.x, rect.bottom - 22), (rect.x + 10, rect.bottom - 14), (rect.x, rect.bottom - 6)]
        pygame.draw.lines(screen, GREY, True, tri, 2)
        if i:
            draw_arrow(screen, (rects[i - 1].right + 2, rect.centery), (rect.x - 2, rect.centery), CYAN)
    if serial_in:
        draw_arrow(screen, (x0 - 52, rects[0].centery), (x0 - 2, rects[0].centery), YELLOW)
        lab = f_tiny.render("SERIAL IN", True, YELLOW)
        screen.blit(lab, lab.get_rect(midright=(x0 - 56, rects[0].centery)))
        if si_value is not None:
            img = f_small.render(str(si_value), True, WHITE)
            screen.blit(img, img.get_rect(midbottom=(x0 - 28, rects[0].centery - 4)))
    if parallel_in:
        for r in rects:
            draw_arrow(screen, (r.centerx, y0 - 40), (r.centerx, y0 - 2), YELLOW)
        lab = f_tiny.render("PARALLEL IN", True, YELLOW)
        screen.blit(lab, lab.get_rect(midbottom=((rects[0].centerx + rects[-1].centerx) // 2, y0 - 42)))
    if serial_out:
        r = rects[-1]
        draw_arrow(screen, (r.right + 2, r.centery), (r.right + 52, r.centery), GREEN)
        lab = f_tiny.render("SERIAL OUT", True, GREEN)
        screen.blit(lab, lab.get_rect(midleft=(r.right + 56, r.centery)))
    if parallel_out:
        for r in rects:
            draw_arrow(screen, (r.centerx, r.bottom + 2), (r.centerx, r.bottom + 42), GREEN)
        lab = f_tiny.render("PARALLEL OUT", True, GREEN)
        screen.blit(lab, lab.get_rect(midtop=((rects[0].centerx + rects[-1].centerx) // 2, rects[0].bottom + 46)))
    return rects


def draw_counter_chain(screen, fonts, x0, y0, n, mode, qvals=None, tvals=None, box_w=80, gap=44):
    """n T flip-flops. ripple: each clocked by the one before. sync: one shared clock."""
    f_body, f_small, f_tiny = fonts
    box_h = 74
    rects = []
    for i in range(n):
        rect = pygame.Rect(x0 + i * (box_w + gap), y0, box_w, box_h)
        rects.append(rect)
        pygame.draw.rect(screen, (22, 40, 58), rect, border_radius=6)
        pygame.draw.rect(screen, WHITE, rect, 3, border_radius=6)
        t = f_tiny.render("T", True, YELLOW)
        screen.blit(t, t.get_rect(topleft=(rect.x + 8, rect.y + 6)))
        cy = rect.bottom - 18
        tri = [(rect.x, cy - 9), (rect.x + 12, cy), (rect.x, cy + 9)]
        pygame.draw.lines(screen, WHITE, True, tri, 2)
        name = f_tiny.render(f"FF{i}", True, CYAN)
        screen.blit(name, name.get_rect(midbottom=(rect.centerx, rect.y - 4)))
        q = None if qvals is None else qvals[i]
        val = "?" if q is None else str(q)
        qlab = f_body.render(val, True, GREEN if q else WHITE)
        screen.blit(qlab, qlab.get_rect(center=(rect.centerx + 8, rect.y + 36)))
    clk_y = y0 + box_h - 18
    if mode == "ripple":
        pygame.draw.line(screen, YELLOW, (x0 - 34, clk_y), (x0, clk_y), 3)
        lab = f_tiny.render("CLOCK", True, YELLOW)
        screen.blit(lab, lab.get_rect(midright=(x0 - 38, clk_y)))
        for i in range(1, n):
            a, b = rects[i - 1], rects[i]
            pts = [(a.right + 2, a.y + 60), (a.right + gap // 2, a.y + 60),
                   (a.right + gap // 2, clk_y), (b.x, clk_y)]
            pygame.draw.lines(screen, CYAN, False, pts, 3)
        note = "Each flip-flop is clocked by the one before it"
    else:
        bus_y = y0 + box_h + 26
        pygame.draw.line(screen, YELLOW, (x0 - 34, bus_y), (rects[-1].x - 8, bus_y), 3)
        lab = f_tiny.render("CLOCK", True, YELLOW)
        screen.blit(lab, lab.get_rect(midright=(x0 - 38, bus_y)))
        for r in rects:
            pygame.draw.line(screen, YELLOW, (r.x - 8, bus_y), (r.x - 8, clk_y), 3)
            pygame.draw.line(screen, YELLOW, (r.x - 8, clk_y), (r.x, clk_y), 3)
        note = "ONE clock wire goes to every flip-flop"
    if tvals is not None:
        for i, r in enumerate(rects):
            expr = "T0 = 1" if i == 0 else "T%d = %s" % (i, " AND ".join(f"Q{j}" for j in range(i)))
            on = bool(tvals[i])
            img = f_tiny.render(f"{expr} ({tvals[i]})", True, GREEN if on else GREY)
            screen.blit(img, img.get_rect(midbottom=(r.centerx, y0 - 14)))
    img = f_tiny.render(note, True, GREY)
    screen.blit(img, (x0, y0 + box_h + 44))
    return rects


def draw_counter_timing(screen, fonts, x0, y0, per_w, nbits, states, mode, row_h=44, upto=None, mark_edge=None,
                        delay_step=6):
    """CLK + Q0..Q(n-1) for the pulses in states[1:]. ripple adds a small delay per stage."""
    pulses = len(states) - 1
    rows = [{"name": "CLK", "kind": "clk", "color": YELLOW}]
    for i in range(nbits):
        rows.append({
            "name": f"Q{i}", "kind": "out", "init": bit_of(states[0], i),
            "vals": [bit_of(s, i) for s in states[1:]],
            "delay": (i * delay_step if mode == "ripple" else 0),
            "upto": pulses if upto is None else upto,
            "color": SIGNAL_COLORS[i % len(SIGNAL_COLORS)],
        })
    draw_waveforms(screen, fonts, x0, y0, per_w, pulses, rows, row_h=row_h, mark_edge=mark_edge)


# ------------------------------------------------------------------
# STAGE DATA
# ------------------------------------------------------------------
def _vtxt(vals):
    return ", ".join("X" if v == X else str(v) for v in vals)


def _sdemo(frames):
    n = len(frames)
    return {
        "kind": "sdemo", "frames": frames,
        "task": f"Watch all {n} views (LEFT / RIGHT), then press ENTER.",
        "hints": ["Use LEFT and RIGHT to move between the views.",
                  "Look at every view, then press ENTER.",
                  f"Press RIGHT until all {n} dots are lit, then ENTER."],
    }


def _q(q, labels, correct, ok, hints, task="Pick the answer.", visual="none", seed=None, **extra):
    opts = [(l, l) for l in labels]
    if seed is not None:
        random.Random(seed).shuffle(opts)
    step = {"kind": "choice", "visual": visual, "q": q, "options": opts, "correct": correct,
            "task": task, "ok": ok, "hints": hints}
    step.update(extra)
    return step


def _q01(q, correct, ok, hints, task="Pick the answer.", labels=("Q = 0", "Q = 1")):
    return {"kind": "choice", "visual": "none", "q": q,
            "options": [(labels[0], 0), (labels[1], 1)], "correct": correct,
            "task": task, "ok": ok, "hints": hints}


def _ffplay(kind, task):
    def reveal(p):
        m = p.missing_combo_text()
        return "You have tried every combination. Press ENTER." if m is None else f"Still untried: {m}."
    return {"kind": "ffplay", "ff": kind, "task": task,
            "hints": ["Click a switch to turn it ON (green) or OFF. Those are the inputs.",
                      "Press CLOCK (or SPACE). The box only reads its switches at that moment.",
                      reveal]}


FFTABLE_HINTS = {
    "SR": ["Qn is the stored bit BEFORE the clock. Qn+1 is the stored bit AFTER the clock.",
           "S = 0, R = 0: nothing changes. S = 0, R = 1: Qn+1 = 0. S = 1, R = 0: Qn+1 = 1. S = 1, R = 1: not allowed, type X."],
    "D": ["D is copied into Q at the clock pulse.",
          "Qn+1 = D, whatever Qn was. So the answer column equals the D column."],
    "T": ["T = 0 means hold. T = 1 means flip.",
          "T = 0: Qn+1 is the same as Qn. T = 1: Qn+1 is the opposite of Qn."],
    "JK": ["J acts like S (set) and K acts like R (reset). J = K = 1 flips the bit.",
           "J = 0, K = 0: same as before. J = 0, K = 1: 0. J = 1, K = 0: 1. J = 1, K = 1: the opposite of Qn."],
}


def _fftable(kind, task):
    ans = char_next(kind)
    return {"kind": "fftable", "ff": kind, "expect": ans, "task": task,
            "hints": FFTABLE_HINTS[kind] + ["Answers, top to bottom: " + _vtxt(ans) + "."]}


def _wavefill(kind, q0, inputs, task=None, given=None):
    names = FF_INPUTS[kind]
    n = len(inputs[names[0]])
    per = [tuple(inputs[nm][k] for nm in names) for k in range(n)]
    expect = simulate_ff(kind, q0, per)
    assert None not in expect
    signals = [{"name": nm, "kind": "input", "vals": inputs[nm], "init": inputs[nm][0],
                "color": SIGNAL_COLORS[i]} for i, nm in enumerate(names)]
    first = {"D": "Look at D at each dashed line. Q copies it.",
             "T": "Look at T at each dashed line. T = 1 flips Q. T = 0 keeps Q.",
             "JK": "Look at J and K at each dashed line. Use the JK table you filled in.",
             "SR": "Look at S and R at each dashed line."}[kind]
    return {"kind": "wavefill", "periods": n, "signals": signals, "q0": q0, "expect": expect,
            "ans_name": "Q", "exam": True,
            "task": task or "Fill in Q after each rising edge. Q starts at %d." % q0,
            "hints": [first,
                      "Go one dashed line at a time. Q only changes at a dashed line and stays the same until the next one.",
                      "Q after each edge: " + _vtxt(expect) + "."]}


def _seqtable(cols, rows, width, start, task, hints, answer_head, exam=False):
    return {"kind": "seqtable", "cols": cols, "rows": [r[0] for r in rows],
            "expect": [r[1] for r in rows], "width": width, "start": start,
            "answer_head": answer_head, "task": task, "exam": exam,
            "hints": hints + ["Rows, top to bottom: " + ", ".join(r[1] for r in rows) + "."]}


def _cntplay(nbits, mod, mode, need, task, hints, show_wave=True):
    return {"kind": "cntplay", "nbits": nbits, "mod": mod, "mode": mode, "need": need,
            "task": task, "hints": hints, "show_wave": show_wave}


# ----- stage 1 -----
def _stage_memory():
    ff = lambda q, s, r, cap: {"draw": ("ff", {"kind": "SR", "q": q, "ins": {"S": s, "R": r}}), "caption": cap}
    frames = [
        ff(0, 0, 0, "Everything so far FORGETS: change the input and the output changes at once. "
                    "A FLIP-FLOP is a box that REMEMBERS one bit. Q is the stored bit and Q' is its opposite."),
        ff(1, 1, 0, "SET: put S = 1 and the stored bit becomes 1 (Q = 1)."),
        ff(1, 0, 0, "Now S goes back to 0, but Q STAYS 1. That is memory: with S = 0 and R = 0 the box HOLDS its value."),
        ff(0, 0, 1, "RESET: put R = 1 and the stored bit becomes 0 (Q = 0)."),
        ff(None, 1, 1, "S = 1 and R = 1 together is NOT ALLOWED: the box cannot set and reset at once. "
                       "Q is unpredictable (shown as ?). Never use it."),
        ff(0, 0, 0, "The little triangle is the CLOCK input. The box only looks at S and R at the clock pulse. "
                    "In the next step you press CLOCK yourself."),
    ]
    return {
        "id": "q1_memory", "title": "Memory", "sub": "the SR flip-flop",
        "brief": ["A flip-flop stores ONE bit. That is how a computer remembers anything.",
                  "SR means SET and RESET. S makes the stored bit 1, R makes it 0, and if both are 0 it keeps what it had."],
        "steps": [
            _sdemo(frames),
            _ffplay("SR", "Set S and R with the switches, then press CLOCK. Try all four combinations."),
            _fftable("SR", "Fill in Qn+1 (the bit stored AFTER the clock). Use X for the case that is not allowed."),
            _q("S = 0 and R = 0 at the clock pulse. The box stored 1 before. What does it store now?",
               ["Still 1 (it holds)", "0", "Unpredictable"], "Still 1 (it holds)",
               "S = 0, R = 0 means HOLD: Qn+1 = Qn.",
               ["Look at the SR table row S = 0, R = 0.", "Neither SET nor RESET is asked, so nothing changes.",
                "The answer is: still 1, it holds."], seed=3),
            _q("Which input combination must NEVER be used on an SR flip-flop?",
               ["S=0 R=0", "S=0 R=1", "S=1 R=0", "S=1 R=1"], "S=1 R=1",
               "S = 1 and R = 1 asks for SET and RESET at once, so Q is unpredictable (X).",
               ["Which row of your table had an X?", "SET and RESET together contradict each other.",
                "The answer is S=1 R=1."]),
        ],
        "example": ("ff", {"kind": "SR", "q": 1, "ins": {"S": 0, "R": 0}}),
        "items": [
            ("RULE", "A flip-flop stores one bit (Q). It changes only at the clock pulse and HOLDS it in between."),
            ("SR TABLE", "S R: 00 hold, 01 reset (0), 10 set (1), 11 not allowed (X)."),
            ("MATH LINK", "n flip-flops store n bits, so 2^n different values (3 flip-flops: 8 values)."),
        ],
    }


# ----- stage 2 -----
def _stage_clock():
    d = [1, 0, 1, 1]
    rows = lambda upto: [
        {"name": "CLK", "kind": "clk", "color": YELLOW},
        {"name": "D", "kind": "input", "vals": d, "init": d[0], "color": SIGNAL_COLORS[0]},
        {"name": "Q", "kind": "out", "vals": d, "init": 0, "upto": upto, "color": GREEN},
    ]
    wave = lambda upto, mark, cap: {"draw": ("wave", {"periods": 4, "rows": rows(upto), "mark": mark}), "caption": cap}
    frames = [
        {"draw": ("wave", {"periods": 4, "rows": [{"name": "CLK", "kind": "clk", "color": YELLOW}], "mark": None,
                           "arrows": True}),
         "caption": "The CLOCK is a steady 0, 1, 0, 1 signal, like a heartbeat. The moment it goes from 0 to 1 is "
                    "the RISING EDGE (arrows). A flip-flop only listens at that moment."},
        wave(0, 0, "A D flip-flop has one input, D. During the first period D = 1. Watch the rising edge (dashed line)."),
        wave(1, 0, "At edge 1 the flip-flop copies D (1) into Q. Q becomes 1 and STAYS 1 until the next edge."),
        wave(2, 1, "Edge 2: D = 0, so Q becomes 0."),
        wave(4, None, "Q = D delayed by one clock: Qn+1 = D. Q only changes at a rising edge, never in between."),
    ]
    return {
        "id": "q2_clock", "title": "Clock and D", "sub": "timing diagrams",
        "brief": ["A flip-flop listens only at the RISING EDGE of the clock (0 to 1). Between edges it ignores its inputs.",
                  "The D flip-flop is the simplest: at the edge it copies D into Q. A TIMING DIAGRAM draws signals against time."],
        "steps": [
            _sdemo(frames),
            _ffplay("D", "Set D, then press CLOCK. Try D = 0 and D = 1."),
            _fftable("D", "Fill in Qn+1 for each row."),
            _wavefill("D", 0, {"D": [1, 0, 0, 1, 1, 0]}),
            _q("At which moment does a rising-edge flip-flop update?",
               ["When the clock goes 0 to 1", "When the clock goes 1 to 0", "Whenever D changes", "While the clock is 1"],
               "When the clock goes 0 to 1", "Rising edge = the clock going from 0 to 1.",
               ["Think of the name: RISING edge.", "The clock rises from 0 to 1.", "The answer is: when the clock goes 0 to 1."],
               seed=4),
            _q01("D = 1 at the edge, then D goes back to 0 before the next edge. What is Q?", 1,
                 "Q stored the 1 at the edge and holds it. Q only changes at the next edge.",
                 ["Q only looks at D at the edge.", "Between edges Q holds what it stored.", "The answer is Q = 1."]),
        ],
        "example": ("wave", {"periods": 4, "rows": rows(4), "mark": None}),
        "items": [
            ("CLOCK", "The clock is a steady 0 / 1 signal. The RISING EDGE is the moment it goes 0 to 1."),
            ("D RULE", "Qn+1 = D. At the rising edge Q copies D and holds it until the next edge."),
            ("TIMING DIAGRAM", "Q changes at the edge (middle of the period), inputs change before it."),
            ("MATH LINK", "Q is D delayed by ONE clock. Remember this: it is how shift registers work."),
        ],
    }


# ----- stage 3 -----
def _stage_tjk():
    ff = lambda kind, q, ins, cap: {"draw": ("ff", {"kind": kind, "q": q, "ins": ins}), "caption": cap}
    frames = [
        ff("T", 0, {"T": 1}, "T flip-flop: with T = 1 every clock pulse TOGGLES Q. Here Q = 0 becomes 1."),
        ff("T", 1, {"T": 1}, "Next pulse: 1 becomes 0. It flips every time. With T = 0 it simply holds."),
        ff("JK", 0, {"J": 1, "K": 0}, "JK flip-flop: J works like SET and K like RESET (J = 1, K = 0 gives Q = 1)."),
        ff("JK", 1, {"J": 1, "K": 1}, "J = K = 1 TOGGLES. This is the case that was forbidden in SR: JK makes it useful."),
        ff("JK", 1, {"J": 1, "K": 1}, "Problem: if the clock stays high a long time, J = K = 1 could toggle again and "
                                        "again (race-around). A MASTER-SLAVE JK uses two latches so Q changes only ONCE per pulse."),
    ]
    inputs = {"J": [1, 0, 1, 1, 0, 1], "K": [0, 0, 1, 1, 1, 0]}
    return {
        "id": "q3_tjk", "title": "T and JK", "sub": "toggling flip-flops",
        "brief": ["JK fixes the forbidden case of SR: J = K = 1 makes Q TOGGLE (flip).",
                  "T is a JK with J and K tied together: T = 1 toggles, T = 0 holds. T flip-flops are the heart of counters."],
        "steps": [
            _sdemo(frames),
            _ffplay("T", "Set T, then press CLOCK. Watch Q."),
            _ffplay("JK", "Try all four J K combinations (press CLOCK each time)."),
            _fftable("JK", "Fill in Qn+1 for all 8 rows."),
            _wavefill("JK", 0, inputs),
            _q01("J = 1, K = 1 and Q = 1 before the clock. What is Q after?", 0,
                 "J = K = 1 toggles, so 1 becomes 0.",
                 ["Which JK combination is this?", "J = K = 1 means toggle (flip).", "The answer is Q = 0."]),
        ],
        "example": ("ff", {"kind": "JK", "q": 1, "ins": {"J": 1, "K": 1}}),
        "items": [
            ("T RULE", "T = 0 holds, T = 1 toggles: Qn+1 = T XOR Qn."),
            ("JK TABLE", "J K: 00 hold, 01 reset, 10 set, 11 toggle."),
            ("MATH LINK", "Toggle is XOR (Level 1): Qn+1 = T XOR Qn."),
            ("MASTER-SLAVE", "Two latches in a row stop Q toggling more than once per clock pulse."),
        ],
    }


# ----- stage 4 -----
def _stage_convert():
    exc = excitation("JK")
    rows = [[f"{q}", f"{qn}"] for (q, qn) in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    expect = [list(exc[(q, qn)]) for (q, qn) in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    frames = [
        {"draw": ("ff", {"kind": "JK", "q": 0, "ins": {"J": 1, "K": 0}}),
         "caption": "Sometimes you have one kind of flip-flop but need another. The tool is the EXCITATION table: "
                    "you choose the change you WANT (Q to Qn+1) and ask which J and K make it happen."},
        {"draw": ("ff", {"kind": "JK", "q": 0, "ins": {"J": 1, "K": 0}}),
         "caption": "Example: Q = 0 and you want Qn+1 = 1. From the JK table: J = 1 works, and K can be 0 OR 1. "
                    "So J = 1 and K = X. X means don't care, just like in K-maps."},
        {"draw": ("ff", {"kind": "JK", "q": 1, "ins": {"J": 1, "K": 1}}),
         "caption": "Recipe: 1) write the table of the NEW flip-flop's input and Q. 2) add the wanted Qn+1. "
                    "3) read the J and K needed from the excitation table. 4) simplify (a K-map helps!)."},
        {"draw": ("ff", {"kind": "JK", "q": 1, "ins": {"J": 1, "K": 1}}),
         "caption": "Results you will use: JK to T: J = K = T.  JK to D: J = D, K = D'.  D to T: D = T XOR Q.  "
                    "SR to D: S = D, R = D'."},
    ]
    return {
        "id": "q4_convert", "title": "Conversion", "sub": "one flip-flop from another",
        "brief": ["Exams ask: 'convert flip-flop A into flip-flop B'. You do it with the EXCITATION table and a few gates.",
                  "The excitation table lists the inputs you need to make Q change from 0 or 1 to a wanted next value."],
        "steps": [
            _sdemo(frames),
            {"kind": "exctable", "title": "JK excitation table", "left_heads": ["Q", "Qn+1"], "left": rows,
             "in_heads": ["J", "K"], "expect": expect, "allow_x": True,
             "task": "For each change Q to Qn+1, which J and K do you need? Use X when either value works.",
             "hints": ["Use the JK table: which J K pairs make Q go from this value to that value?",
                       "0 to 0: J = 0 and K can be anything (X). 0 to 1: J = 1 and K = X. "
                       "1 to 0: J = X and K = 1. 1 to 1: J = X and K = 0.",
                       "Answers (J K): " + "; ".join(f"{_vtxt(e)}" for e in expect) + "."]},
            _q("Convert a JK flip-flop into a T flip-flop. Which wiring works?",
               ["J = K = T", "J = T, K = 0", "J = K = 1", "J = T, K = T'"], "J = K = T",
               "J = K = T: T = 0 holds, T = 1 toggles.",
               ["A T flip-flop holds when T = 0 and toggles when T = 1.", "Which JK pair holds, and which toggles? Tie both to T.",
                "The answer is J = K = T."], seed=7),
            _q("Convert a JK flip-flop into a D flip-flop: J = D and K = ?",
               ["D", "D'", "0", "1"], "D'",
               "J = D, K = D': D = 1 gives J=1, K=0 (set); D = 0 gives J=0, K=1 (reset).",
               ["A D flip-flop sets when D = 1 and resets when D = 0.", "Set needs J=1, K=0. Reset needs J=0, K=1. So K is the opposite of D.",
                "The answer is D'."], seed=8),
            _q("Convert a D flip-flop into a T flip-flop: D = ?",
               ["T", "T'", "T OR Q", "T XOR Q"], "T XOR Q",
               "Toggle is XOR: Qn+1 = T XOR Qn, and a D flip-flop copies D into Q.",
               ["A D flip-flop gives Qn+1 = D. What must Qn+1 be for a T flip-flop?",
                "A T flip-flop gives Qn+1 = T XOR Qn.", "The answer is D = T XOR Q."], seed=9),
            _q("EXAM STYLE: convert an SR flip-flop into a D flip-flop: S = D and R = ?",
               ["D", "D'", "0", "1"], "D'",
               "S = D, R = D' never makes S = R = 1, so it is always allowed.",
               ["A D flip-flop sets when D = 1 and resets when D = 0.", "Set is S=1, R=0. Reset is S=0, R=1.",
                "The answer is D'."], seed=10),
        ],
        "example": ("ff", {"kind": "JK", "q": 1, "ins": {"J": 1, "K": 1}}),
        "items": [
            ("EXCITATION (JK)", "Q 0 to 0: J=0 K=X.  0 to 1: J=1 K=X.  1 to 0: J=X K=1.  1 to 1: J=X K=0."),
            ("CONVERSIONS", "JK to T: J = K = T.  JK to D: J = D, K = D'.  D to T: D = T XOR Q.  SR to D: S = D, R = D'."),
            ("RECIPE", "New inputs + Q, wanted Qn+1, read the old flip-flop's inputs from its excitation table, simplify."),
        ],
    }


# ----- stage 5 -----
def _regf(bits, cap, **flags):
    return {"draw": ("reg", dict(bits=bits, **flags)), "caption": cap}


def _regdiag_q(kind, seed):
    flags = {"SISO": dict(serial_in=True, serial_out=True), "SIPO": dict(serial_in=True, parallel_out=True),
             "PISO": dict(parallel_in=True, serial_out=True), "PIPO": dict(parallel_in=True, parallel_out=True)}[kind]
    return _q("Which kind of shift register is this?", ["SISO", "SIPO", "PISO", "PIPO"], kind,
              f"{kind}: data goes IN " + ("serially" if flags.get("serial_in") else "in parallel") + " and comes OUT "
              + ("serially." if flags.get("serial_out") else "in parallel."),
              ["The name says how data goes IN first, then OUT. S = serial (one bit at a time), P = parallel (all at once).",
               "Look at the arrows: one arrow = serial, one arrow per box = parallel. First the IN side, then the OUT side.",
               f"The answer is {kind}."], visual="regdiag", flags=flags)


def _stage_shift():
    frames_a = [
        _regf([0, 0, 0, 0], "Four D flip-flops in a row. At every clock pulse each bit moves ONE place to the RIGHT "
                            "and the serial input enters the first box. Here the serial input is 1.",
              serial_in=True, si=1),
        _regf([1, 0, 0, 0], "After pulse 1 the 1 sits in the first box. The new serial input is 0.", serial_in=True, si=0),
        _regf([0, 1, 0, 0], "After pulse 2 it has moved one place on.", serial_in=True, si=0),
        _regf([0, 0, 1, 0], "After pulse 3 it is in the third box.", serial_in=True, si=0),
        _regf([0, 0, 0, 1], "After pulse 4 it has crossed all four boxes and reaches the output. "
                            "A bit needs n clock pulses to cross an n-bit register.", serial_in=True, serial_out=True, si=0),
    ]
    frames_b = [
        _regf([1, 0, 1, 1], "SISO: Serial In, Serial Out. Bits go in one at a time and come out one at a time. "
                            "Slow, but it needs only two wires.", serial_in=True, serial_out=True),
        _regf([1, 0, 1, 1], "SIPO: Serial In, Parallel Out. Bits go in one at a time; after n pulses ALL bits can be "
                            "read at once. It turns a serial signal into parallel data.", serial_in=True, parallel_out=True),
        _regf([1, 0, 1, 1], "PISO: Parallel In, Serial Out. Load all bits at once, then shift them out one by one. "
                            "It sends parallel data down a single wire.", parallel_in=True, serial_out=True),
        _regf([1, 0, 1, 1], "PIPO: Parallel In, Parallel Out. Load all bits at once and read them all at once. "
                            "It is just a storage register.", parallel_in=True, parallel_out=True),
    ]
    si_seq = [1, 1, 0, 1]
    reg, rows = [0, 0, 0, 0], []
    for k, si in enumerate(si_seq, 1):
        reg = shift_right(reg, si)
        rows.append(([str(k), str(si)], "".join(map(str, reg))))
    return {
        "id": "q5_shift", "title": "Shift registers", "sub": "SISO, SIPO, PISO, PIPO",
        "brief": ["A SHIFT REGISTER is a row of D flip-flops that passes bits along at every clock pulse, like people "
                  "passing buckets down a line.",
                  "Four kinds, named by how data goes IN and then OUT: Serial (one bit at a time) or Parallel (all at once)."],
        "steps": [
            _sdemo(frames_a),
            {"kind": "regplay", "controls": ["serial"], "target_reg": [1, 0, 1, 1], "min_clocks": 4,
             "task": "Make the register show 1 0 1 1 (left to right). Set the serial input, press CLOCK, repeat. "
                     "Careful: the FIRST bit you enter travels furthest.",
             "hints": ["Each CLOCK moves every bit one place right and puts the serial input into the first box.",
                       "The first bit you enter ends up in the LAST box, so enter the bits in the opposite order.",
                       "Enter 1, then 1, then 0, then 1 (pressing CLOCK after each one)."]},
            _sdemo(frames_b),
            _regdiag_q("SIPO", 1),
            _regdiag_q("PISO", 2),
            {"kind": "regplay", "controls": ["parallel", "load"], "need_load": [1, 0, 1, 1], "target_out": [1, 1, 0, 1],
             "task": "PISO: click the P chips to make 1 0 1 1, press LOAD, then press CLOCK four times. "
                     "Watch SERIAL OUT: bits leave from the RIGHT end.",
             "hints": ["Click the P chips until they read 1 0 1 1 (left to right), then LOAD.",
                       "After LOAD, each CLOCK pushes the right-most bit out. Press CLOCK four times.",
                       "The bits come out in the order 1, 1, 0, 1."]},
            _seqtable(["Pulse", "Serial in"], rows, 4, "0000",
                      "EXAM STYLE: a 4-bit SISO register starts at 0000. The serial input is 1, 1, 0, 1 on pulses 1 to 4. "
                      "Type the register after each pulse.",
                      ["Each pulse: everything moves one place right and the serial input enters on the left.",
                       "Start from the row above. For example 0000 with serial input 1 becomes 1000."],
                      "Q0 Q1 Q2 Q3", exam=True),
            _q("EXAM STYLE: an 8-bit SISO register. How many clock pulses move the first bit from the input to the output?",
               ["1", "4", "8", "16"], "8", "A bit moves one place per pulse, so it needs n = 8 pulses.",
               ["How far does a bit move at each pulse?", "It must cross all 8 flip-flops.", "The answer is 8."], seed=5),
        ],
        "example": ("reg", {"bits": [1, 0, 1, 1], "serial_in": True, "parallel_out": True}),
        "items": [
            ("RULE", "A shift register passes every bit one place per clock pulse. n bits need n pulses to cross."),
            ("THE FOUR KINDS", "SISO, SIPO, PISO, PIPO: first how data goes IN, then how it comes OUT."),
            ("USES", "SIPO turns serial data into parallel data. PISO does the opposite."),
            ("MATH LINK", "Each box is a D flip-flop, so it delays a bit by one clock: n boxes = n clocks of delay."),
        ],
    }


# ----- counters -----
def _cframe(nbits, mode, pulses, upto, cap, **kw):
    spec = dict(nbits=nbits, mode=mode, pulses=pulses, upto=upto, chain=True, timing=True)
    spec.update(kw)
    return {"draw": ("counter", spec), "caption": cap}


def _wavefill_counter(nbits, pulses, given_bit, ask_bit):
    states = count_states(nbits, 1 << nbits, 0, pulses)
    given = {"name": f"Q{given_bit}", "kind": "out", "vals": [bit_of(s, given_bit) for s in states[1:]],
             "init": bit_of(states[0], given_bit), "color": SIGNAL_COLORS[0]}
    expect = [bit_of(s, ask_bit) for s in states[1:]]
    return {"kind": "wavefill", "periods": pulses, "signals": [given], "q0": bit_of(states[0], ask_bit),
            "expect": expect, "ans_name": f"Q{ask_bit}", "exam": True,
            "task": f"Q{given_bit} is shown. Fill in Q{ask_bit} after each rising edge (the counter starts at 0).",
            "hints": [f"Q{given_bit} toggles at every edge. Q{ask_bit} toggles only when Q{given_bit} falls (goes 1 to 0).",
                      f"Look at Q{given_bit} before and after each edge. When it goes 1 to 0, flip Q{ask_bit}.",
                      f"Q{ask_bit} after each edge: " + _vtxt(expect) + "."]}


def _stage_ripple():
    n = 3
    frames = [
        _cframe(n, "ripple", 8, 0, "A COUNTER counts clock pulses in binary. It is a row of T flip-flops that always "
                                    "toggle (T = 1). In a RIPPLE counter only FF0 gets the clock; FF1 is clocked by Q0 "
                                    "and FF2 by Q1.", timing=False),
        _cframe(n, "ripple", 8, 1, "Pulse 1: Q0 toggles from 0 to 1. The count is 001 = 1.", mark=0),
        _cframe(n, "ripple", 8, 2, "Pulse 2: Q0 falls from 1 to 0. That FALLING edge clocks FF1, so Q1 toggles to 1. "
                                   "The count is 010 = 2.", mark=1),
        _cframe(n, "ripple", 8, 4, "Q0 toggles every pulse, Q1 every 2nd pulse, Q2 every 4th. That is exactly how "
                                   "binary counting works. Pulse 4: count 100 = 4.", mark=3),
        _cframe(n, "ripple", 8, 8, "After 8 pulses the count is back at 000: 3 flip-flops have 2^3 = 8 states. "
                                   "Each flip-flop waits for the one before, so the change RIPPLES along, with a "
                                   "small delay at every stage.", mark=None, delay=8),
    ]
    mod_hints = ["This counter resets itself when it reaches 6 (110). Press CLOCK and watch the states.",
                 "Keep pressing CLOCK. After 101 the count is 110 for a moment, then it resets to 000.",
                 "Press CLOCK six times: 001, 010, 011, 100, 101, then back to 000."]
    seq_rows = []
    s = 0
    for k in range(1, 7):
        s = (s + 1) % 8
        seq_rows.append(([str(k)], bits_str(s, 3)))
    return {
        "id": "q6_ripple", "title": "Ripple counters", "sub": "counting with T flip-flops",
        "brief": ["A counter counts clock pulses in binary. Build it from T flip-flops that always toggle.",
                  "In a RIPPLE (asynchronous) counter only the first flip-flop gets the clock. "
                  "Each next one is clocked by the output of the one before."],
        "steps": [
            _sdemo(frames),
            _cntplay(3, 8, "ripple", {"rollover": True},
                     "Press CLOCK until the count passes 111 and wraps back to 000.",
                     ["Press CLOCK (or SPACE) again and again and watch the three bulbs and the timing diagram.",
                      "After 111 the next pulse sends every bit back to 0. You need 8 pulses.",
                      "Press CLOCK 8 times."]),
            _seqtable(["Pulse"], seq_rows, 3, "000",
                      "EXAM STYLE: a 3-bit up counter starts at 000. Type the count (Q2 Q1 Q0) after each pulse.",
                      ["Count in binary: 001, 010, 011 ...", "After 011 comes 100, then 101, 110, 111, and back to 000."],
                      "Q2 Q1 Q0", exam=True),
            _wavefill_counter(3, 8, 0, 1),
            _cntplay(3, 6, "ripple", {"rollover": True},
                     "A MOD-6 counter: a gate detects 110 and resets it. Press CLOCK until it wraps to 000.",
                     mod_hints),
            _q("A mod-6 counter counts which states?", ["0 to 5", "0 to 6", "1 to 6", "0 to 7"], "0 to 5",
               "Mod-6 has 6 states: 0, 1, 2, 3, 4, 5, and then it resets (at 6).",
               ["A mod-N counter has N different states.", "It counts from 0, so the last state is N - 1.",
                "The answer is 0 to 5."], seed=6),
            _q("EXAM STYLE: how many flip-flops does a mod-12 counter need?", ["2", "3", "4", "5"], "4",
               "n flip-flops give 2^n states. 2^3 = 8 is too small, 2^4 = 16 is enough for 12.",
               ["n flip-flops give 2^n states.", "Find the smallest n with 2^n at least 12.", "The answer is 4."], seed=7),
            _q("EXAM STYLE: a mod-10 (decade) counter resets when it reaches 1010. Which outputs feed the reset NAND gate?",
               ["Q3 and Q1", "Q2 and Q0", "Q3 and Q0", "Q3 only"], "Q3 and Q1",
               "1010 is the first state where Q3 and Q1 are both 1 (1000 and 1001 have only Q3).",
               ["Write 1010 as Q3 Q2 Q1 Q0.", "Use only the bits that are 1 in 1010.", "The answer is Q3 and Q1."], seed=8),
        ],
        "example": ("counter", {"nbits": 3, "mode": "ripple", "pulses": 8, "upto": 8, "chain": False, "timing": True}),
        "items": [
            ("RULE", "T flip-flops with T = 1 toggle at every clock. In a ripple counter each one is clocked by the one before."),
            ("COUNTING", "Q0 toggles every pulse, Q1 every 2nd, Q2 every 4th: that is binary counting."),
            ("MOD-N", "A mod-N counter has N states (0 to N-1). Detect N and reset. Flip-flops needed: smallest n with 2^n at least N."),
            ("DRAWBACK", "The change ripples through, so the delays add up."),
        ],
    }


# ----- stage 7 -----
def _stage_sync():
    frames = [
        _cframe(3, "ripple", 8, 8, "Ripple counters are slow: every flip-flop waits for the one before, so the delays "
                                   "add up (see the staggered edges). More flip-flops, more waiting.",
                chain=False, delay=14),
        {"draw": ("counter", {"nbits": 3, "mode": "sync", "chain": True, "timing": False, "state": 0}),
         "caption": "In a SYNCHRONOUS counter ONE clock wire goes to every flip-flop, so they all change together. "
                    "Now something must decide WHO toggles: the T inputs."},
        {"draw": ("counter", {"nbits": 3, "mode": "sync", "chain": True, "timing": False, "state": 1, "tvals": True}),
         "caption": "Count = 001. T0 = 1 always. T1 = Q0 = 1. T2 = Q0 AND Q1 = 0. So only Q0 and Q1 toggle: "
                    "001 becomes 010."},
        {"draw": ("counter", {"nbits": 3, "mode": "sync", "chain": True, "timing": False, "state": 3, "tvals": True}),
         "caption": "Count = 011. Q0 = 1 and Q1 = 1, so all three T inputs are 1 and all three bits toggle: "
                    "011 becomes 100."},
        {"draw": ("counter", {"nbits": 3, "mode": "sync", "chain": True, "timing": False, "state": 3, "tvals": True}),
         "caption": "Rule: a bit toggles only when ALL the bits below it are 1. T0 = 1, T1 = Q0, T2 = Q0 AND Q1."},
    ]
    t_rows, expect = [], []
    for s in range(4):
        nxt = (s + 1) % 4
        t_rows.append([bits_str(s, 2), bits_str(nxt, 2)])
        expect.append([bit_of(s, 1) ^ bit_of(nxt, 1), bit_of(s, 0) ^ bit_of(nxt, 0)])
    return {
        "id": "q7_sync", "title": "Synchronous counters", "sub": "one clock for all",
        "brief": ["Ripple counters are slow. In a SYNCHRONOUS counter every flip-flop gets the SAME clock at the same moment.",
                  "The T inputs decide who toggles: a bit toggles when all the bits below it are 1."],
        "steps": [
            _sdemo(frames),
            _cntplay(3, 8, "sync", {"t_seen": 2},
                     "Press CLOCK and watch the T inputs. Find a count where T2 = 1.",
                     ["Press CLOCK and read the T inputs above the flip-flops.",
                      "T2 is 1 only when Q0 and Q1 are both 1. Which count is that?",
                      "Press CLOCK three times (count 011). Then T2 = 1."]),
            {"kind": "exctable", "title": "2-bit counter design", "left_heads": ["Q1 Q0", "Next"], "left": t_rows,
             "in_heads": ["T1", "T0"], "expect": expect, "allow_x": False,
             "task": "DESIGN: for each count, which T inputs make it go to the next count? T = 1 if that bit must change.",
             "hints": ["A T input is 1 exactly when its bit has to CHANGE.",
                       "Compare the present and next count bit by bit. 00 to 01: Q0 changes, Q1 does not.",
                       "Answers (T1 T0): " + "; ".join(f"{a} {b}" for a, b in expect) + "."]},
            _q("From your table: T1 equals what?", ["1", "Q0", "Q0'", "Q1"], "Q0",
               "T1 is 1 exactly when Q0 is 1, so T1 = Q0. (T0 = 1 always.)",
               ["Look at the T1 column and the Q0 bit of the present count.", "T1 is 1 in the rows where Q0 = 1.",
                "The answer is Q0."], seed=1),
            _q("EXAM STYLE: for a 3-bit synchronous up counter, T2 = ?",
               ["Q0", "Q1", "Q0 AND Q1", "Q0 OR Q1"], "Q0 AND Q1",
               "Q2 toggles only when Q0 and Q1 are both 1.",
               ["A bit toggles when ALL the bits below it are 1.", "The bits below Q2 are Q0 and Q1.",
                "The answer is Q0 AND Q1."], seed=2),
            _q("Which counter can run at a higher clock speed?",
               ["Synchronous: no ripple delay", "Ripple: it has fewer wires", "They are the same"],
               "Synchronous: no ripple delay", "All flip-flops change together, so no delays add up.",
               ["Think about what slows a ripple counter down.", "Each flip-flop waits for the one before it.",
                "The answer is synchronous."], seed=3),
            _q("EXAM STYLE: for a 4-bit synchronous up counter, T3 = ?",
               ["Q0 Q1 Q2", "Q3", "Q0 + Q1 + Q2", "Q2"], "Q0 Q1 Q2",
               "T3 is the AND of all lower bits: T3 = Q0 Q1 Q2.",
               ["Same rule as before: all lower bits must be 1.", "Write the AND of Q0, Q1 and Q2.",
                "The answer is Q0 Q1 Q2."], seed=4),
        ],
        "example": ("counter", {"nbits": 3, "mode": "sync", "chain": True, "timing": False, "state": 3, "tvals": True}),
        "items": [
            ("RULE", "Synchronous: one shared clock. A bit toggles only when ALL the bits below it are 1."),
            ("T INPUTS", "T0 = 1, T1 = Q0, T2 = Q0 Q1, T3 = Q0 Q1 Q2."),
            ("DESIGN", "T = 1 exactly when that bit must change from the present count to the next count."),
            ("WHY", "No ripple delay, so synchronous counters run faster than ripple counters."),
        ],
    }


# ----- stage 8 -----
def _stage_boss():
    _verify_equations()
    rows2, reg = [], [1, 0, 1, 1]
    for k, si in enumerate([0, 1, 1], 1):
        reg = shift_right(reg, si)
        rows2.append(([str(k), str(si)], "".join(map(str, reg))))
    cnt_rows, s = [], 5
    for k in range(1, 4):
        s = (s + 1) % 8
        cnt_rows.append(([str(k)], bits_str(s, 3)))
    return {
        "id": "q8_boss", "title": "Boss: Signal breaker", "sub": "exam-style mix",
        "brief": ["NEXUS-9's signal is scrambled. Fix it with everything you know: timing diagrams, shift registers "
                  "and counters.",
                  "Every question here is in past-paper style."],
        "steps": [
            _wavefill("D", 0, {"D": [0, 1, 1, 0, 1, 0]}),
            _wavefill("T", 0, {"T": [1, 1, 0, 1, 1, 0]}),
            _seqtable(["Pulse", "Serial in"], rows2, 4, "1011",
                      "EXAM STYLE: a 4-bit SISO register holds 1011. The serial input is 0, 1, 1 on pulses 1 to 3. "
                      "Type the register after each pulse.",
                      ["Every pulse: bits move one place right, the serial input enters on the left.",
                       "1011 with serial input 0 becomes 0101 (the last bit falls out)."],
                      "Q0 Q1 Q2 Q3", exam=True),
            _seqtable(["Pulse"], cnt_rows, 3, "101",
                      "EXAM STYLE: a 3-bit up counter is at 101. Type the next three counts (Q2 Q1 Q0).",
                      ["Add one in binary each pulse.", "101 + 1 = 110. Then 111, then it wraps."],
                      "Q2 Q1 Q0", exam=True),
            _q("EXAM STYLE: how many flip-flops does a mod-100 counter need?", ["5", "6", "7", "8"], "7",
               "2^6 = 64 is too small, 2^7 = 128 is enough for 100.",
               ["n flip-flops give 2^n states.", "Find the smallest n with 2^n at least 100.", "The answer is 7."], seed=11),
            _q("EXAM STYLE: you have a JK flip-flop and need a T flip-flop. Which wiring?",
               ["J = K = T", "J = T, K = 0", "J = K = 1", "J = T, K = T'"], "J = K = T",
               "J = K = T: T = 0 holds and T = 1 toggles.", ["Which JK pair holds, and which toggles?",
               "Both inputs must follow T.", "The answer is J = K = T."], seed=12),
            _q("EXAM STYLE: which circuit moves a bit one place per clock pulse and needs n pulses to cross n flip-flops?",
               ["Shift register", "Decoder", "Adder", "Multiplexer"], "Shift register",
               "A shift register passes bits along one flip-flop per pulse.",
               ["It is built from D flip-flops in a row.", "Which circuit did you meet in stage 5?",
                "The answer is the shift register."], seed=13),
        ],
        "example": ("none", {}),
        "items": [
            ("FLIP-FLOP EQUATIONS", "D: Qn+1 = D.  T: Qn+1 = T XOR Qn.  JK: Qn+1 = J Qn' + K' Qn.  SR: Qn+1 = S + R' Qn."),
            ("COUNTERS", "Mod-N needs the smallest n with 2^n at least N. Sync counter: T_k = AND of all lower bits."),
            ("REGISTERS", "n bits need n pulses to cross. SISO, SIPO, PISO, PIPO = IN then OUT."),
            ("TIMING", "Inputs change before the edge. Q changes AT the rising edge and holds until the next one."),
        ],
    }


def _verify_equations():
    """Brute-force check of the characteristic equations printed on the boss card."""
    for q in (0, 1):
        for d in (0, 1):
            assert ff_next("D", q, d) == d
        for t in (0, 1):
            assert ff_next("T", q, t) == t ^ q
        for j in (0, 1):
            for k in (0, 1):
                assert ff_next("JK", q, j, k) == ((j & (1 - q)) | ((1 - k) & q))
        for s in (0, 1):
            for r in (0, 1):
                if not (s and r):
                    assert ff_next("SR", q, s, r) == (s | ((1 - r) & q))
    return True


def build_seq_stages():
    return [_stage_memory(), _stage_clock(), _stage_tjk(), _stage_convert(),
            _stage_shift(), _stage_ripple(), _stage_sync(), _stage_boss()]


# ------------------------------------------------------------------
# THE PUZZLE
# ------------------------------------------------------------------
class BasicSequentialPuzzle(BasicGatesPuzzle):
    """Eight-stage beginner course: flip-flops, shift registers and counters."""

    COURSE_TITLE = "BASIC LEVEL  -  FLIP-FLOPS, REGISTERS AND COUNTERS"
    LEGEND_EXTRA = dict(BasicGatesPuzzle.LEGEND_EXTRA, **{
        "sdemo": "LEFT / RIGHT to move, ENTER when you've seen all",
        "ffplay": "click switches or press their letters, SPACE = CLOCK",
        "fftable": "click a cell or UP/DOWN, then 0 / 1 (X = not allowed)",
        "wavefill": "click a box or LEFT/RIGHT, then 0 / 1",
        "regplay": "S serial, 1-4 inputs, SPACE clock, L load, R reset",
        "seqtable": "UP/DOWN to pick a row, type 0 / 1, BACKSPACE deletes",
        "cntplay": "SPACE = clock pulse, R = reset",
        "exctable": "click a cell or arrows, then 0 / 1 / X",
    })

    def _make_stages(self):
        return build_seq_stages()

    def __init__(self, notebook=None):
        self.demo_clock = 0.0
        super().__init__(notebook)
        self.fonts = (self.f_body, self.f_small, self.f_tiny)

    # ---------------- state ----------------
    def _enter_step(self):
        super()._enter_step()
        step, st = self.step, self.st
        kind = step["kind"]
        if kind == "sdemo":
            st.update(frame=0, seen=1)
            self.demo_clock = 0.0
        elif kind == "ffplay":
            st.update(ins=[0] * len(FF_INPUTS[step["ff"]]), q=0, seen=set(), log=[], pulses=0)
        elif kind == "fftable":
            st.update(cells=[None] * len(step["expect"]), sel=0, bad=set())
        elif kind == "wavefill":
            st.update(vals=[None] * step["periods"], sel=0, bad=set())
        elif kind == "regplay":
            st.update(reg=[0, 0, 0, 0], si=0, par=[0, 0, 0, 0], out=[], out_since=[], last_load=None,
                      clocks=0, shifts=0, msg="")
        elif kind == "seqtable":
            st.update(typed=["" for _ in step["rows"]], sel=0, bad=set())
        elif kind == "cntplay":
            st.update(state=0, hist=[0], t_seen=set(), rolled=False, msg="", pulses=0)
            self._note_t()
        elif kind == "exctable":
            ncols = len(step["in_heads"])
            st.update(cells=[[None] * ncols for _ in step["expect"]], sel=(0, 0), bad=set())

    def missing_combo_text(self):
        step, st = self.step, self.st
        if step["kind"] != "ffplay":
            return None
        names = FF_INPUTS[step["ff"]]
        for combo in input_combos(step["ff"]):
            if combo not in st["seen"]:
                return ", ".join(f"{n} = {v}" for n, v in zip(names, combo))
        return None

    def _note_t(self):
        st, step = self.st, self.step
        for i, t in enumerate(t_inputs(st["state"], step["nbits"])):
            if t:
                st["t_seen"].add(i)

    # ---------------- events ----------------
    def _on_key(self, event):
        key = event.key
        if self.phase == "done" or key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_h):
            return super()._on_key(event)
        kind = self.step["kind"]
        st = self.st
        digit = self._digit(key)
        clock = key in (pygame.K_SPACE, pygame.K_c)

        if kind == "sdemo":
            if key in (pygame.K_RIGHT, pygame.K_LEFT):
                self._on_action(("sframe", 1 if key == pygame.K_RIGHT else -1))
            return
        if kind == "ffplay":
            if clock:
                self._on_action(("fclock",))
            else:
                for i, name in enumerate(FF_INPUTS[self.step["ff"]]):
                    if key == getattr(pygame, "K_" + name.lower()):
                        self._on_action(("fin", i))
            return
        if kind == "fftable":
            n = len(st["cells"])
            if key == pygame.K_UP:
                st["sel"] = (st["sel"] - 1) % n
            elif key == pygame.K_DOWN:
                st["sel"] = (st["sel"] + 1) % n
            elif digit in (0, 1) or (key == pygame.K_x and self.step["ff"] == "SR"):
                st["cells"][st["sel"]] = X if key == pygame.K_x else digit
                st["bad"].discard(st["sel"])
                if st["sel"] < n - 1:
                    st["sel"] += 1
            return
        if kind == "wavefill":
            n = len(st["vals"])
            if key == pygame.K_LEFT:
                st["sel"] = (st["sel"] - 1) % n
            elif key == pygame.K_RIGHT:
                st["sel"] = (st["sel"] + 1) % n
            elif digit in (0, 1):
                st["vals"][st["sel"]] = digit
                if st["sel"] < n - 1:
                    st["sel"] += 1
            elif key == pygame.K_BACKSPACE:
                st["vals"][st["sel"]] = None
            return
        if kind == "regplay":
            ctl = self.step["controls"]
            if clock:
                self._on_action(("rclock",))
            elif key == pygame.K_s and "serial" in ctl:
                self._on_action(("rser",))
            elif digit is not None and 1 <= digit <= 4 and "parallel" in ctl:
                self._on_action(("rpar", digit - 1))
            elif key == pygame.K_l and "load" in ctl:
                self._on_action(("rload",))
            elif key == pygame.K_r:
                self._on_action(("rreset",))
            return
        if kind == "seqtable":
            n = len(st["typed"])
            width = self.step["width"]
            if key == pygame.K_UP:
                st["sel"] = (st["sel"] - 1) % n
            elif key == pygame.K_DOWN:
                st["sel"] = (st["sel"] + 1) % n
            elif digit in (0, 1) and len(st["typed"][st["sel"]]) < width:
                st["typed"][st["sel"]] += str(digit)
                st["bad"].discard(st["sel"])
                if len(st["typed"][st["sel"]]) == width and st["sel"] < n - 1:
                    st["sel"] += 1
            elif key == pygame.K_BACKSPACE:
                st["typed"][st["sel"]] = st["typed"][st["sel"]][:-1]
            return
        if kind == "cntplay":
            if clock:
                self._on_action(("cclock",))
            elif key == pygame.K_r:
                self._on_action(("creset",))
            return
        if kind == "exctable":
            r, c = st["sel"]
            rows, cols = len(st["cells"]), len(st["cells"][0])
            if key == pygame.K_UP:
                st["sel"] = ((r - 1) % rows, c)
            elif key == pygame.K_DOWN:
                st["sel"] = ((r + 1) % rows, c)
            elif key == pygame.K_LEFT:
                st["sel"] = (r, (c - 1) % cols)
            elif key == pygame.K_RIGHT:
                st["sel"] = (r, (c + 1) % cols)
            elif digit in (0, 1) or (key == pygame.K_x and self.step["allow_x"]):
                st["cells"][r][c] = X if key == pygame.K_x else digit
                st["bad"].discard(r)
                st["sel"] = (r, c + 1) if c + 1 < cols else ((r + 1, 0) if r + 1 < rows else (r, c))
            return
        return super()._on_key(event)

    def _on_action(self, action):
        name = action[0]
        st = self.st
        if self.phase != "play":
            return super()._on_action(action)
        step = self.step
        if name == "sframe":
            frames = len(step["frames"])
            st["frame"] = (st["frame"] + action[1]) % frames
            st["seen"] = max(st["seen"], st["frame"] + 1)
            self.demo_clock = 0.0
        elif name == "fin":
            st["ins"][action[1]] ^= 1
        elif name == "fclock":
            self._ff_clock()
        elif name == "fcell":
            i = action[1]
            st["sel"] = i
            order = [None, 0, 1, X] if step["ff"] == "SR" else [None, 0, 1]
            st["cells"][i] = order[(order.index(st["cells"][i]) + 1) % len(order)]
            st["bad"].discard(i)
        elif name == "wcell":
            k = action[1]
            st["sel"] = k
            order = [None, 0, 1]
            st["vals"][k] = order[(order.index(st["vals"][k]) + 1) % 3]
        elif name == "rser":
            st["si"] ^= 1
        elif name == "rpar":
            st["par"][action[1]] ^= 1
        elif name == "rclock":
            out = st["reg"][-1]
            st["reg"] = shift_right(st["reg"], st["si"])
            st["out"].append(out)
            st["out_since"].append(out)
            st["clocks"] += 1
            st["shifts"] += 1
            st["msg"] = "Every bit moved one place right. The bit that fell off is the serial output."
        elif name == "rload":
            st["reg"] = list(st["par"])
            st["last_load"] = list(st["par"])
            st["out_since"] = []
            st["clocks"] += 1
            st["msg"] = "LOAD: all four parallel inputs were copied into the register at once."
        elif name == "rreset":
            st.update(reg=[0, 0, 0, 0], out=[], out_since=[], last_load=None, clocks=0, shifts=0,
                      msg="Register cleared.")
        elif name == "srow":
            st["sel"] = action[1]
        elif name == "cclock":
            self._cnt_clock()
        elif name == "creset":
            st.update(state=0, hist=[0], msg="Counter reset to 0.")
            self._note_t()
        elif name == "ecell":
            r, c = action[1], action[2]
            st["sel"] = (r, c)
            order = [None, 0, 1, X] if step["allow_x"] else [None, 0, 1]
            st["cells"][r][c] = order[(order.index(st["cells"][r][c]) + 1) % len(order)]
            st["bad"].discard(r)
        else:
            return super()._on_action(action)

    def _ff_clock(self):
        step, st = self.step, self.st
        kind = step["ff"]
        ins = tuple(st["ins"])
        st["seen"].add(ins)
        old = st["q"]
        new = ff_next(kind, old, *ins)
        st["pulses"] += 1
        st["q"] = new
        desc = ", ".join(f"{n}={v}" for n, v in zip(FF_INPUTS[kind], ins))
        if new is None and ins == (1, 1) and kind == "SR":
            txt = "NOT ALLOWED: Q is unpredictable (?)"
        elif new is None:
            txt = "Q is still unknown. SET or RESET it to fix it"
        elif old is None:
            txt = f"Q = {new}"
        elif new == old:
            txt = f"Q holds at {new}"
        else:
            txt = f"Q changes {old} to {new}"
        st["log"] = (st["log"] + [f"Pulse {st['pulses']}:  {desc}  ->  {txt}"])[-4:]

    def _cnt_clock(self):
        step, st = self.step, self.st
        nbits, mod = step["nbits"], step["mod"]
        nxt = st["state"] + 1
        st["msg"] = ""
        if nxt >= mod:
            if mod == (1 << nbits):
                st["msg"] = f"{bits_str(st['state'], nbits)} + 1 overflows: every bit returns to 0."
            else:
                st["msg"] = (f"The count reached {bits_str(mod, nbits)}. The reset gate fires and the counter "
                             f"returns to {bits_str(0, nbits)}.")
            nxt = 0
            st["rolled"] = True
        st["state"] = nxt
        st["hist"] = (st["hist"] + [nxt])[-20:]
        st["pulses"] += 1
        self._note_t()

    # ---------------- checking ----------------
    def _check(self):
        step, st = self.step, self.st
        kind = step["kind"]

        if kind == "sdemo":
            if st["seen"] >= len(step["frames"]):
                self._advance("")
            else:
                self._say(f"Watch every view first ({st['seen']}/{len(step['frames'])}).", False)
        elif kind == "ffplay":
            need = len(input_combos(step["ff"]))
            if len(st["seen"]) >= need:
                self._right("You tried every combination.")
            else:
                self._say(f"Try every combination first ({len(st['seen'])}/{need}).", False)
        elif kind == "fftable":
            if None in st["cells"]:
                self._say("Fill every Qn+1 cell first.", False)
                return
            bad = {i for i, (a, b) in enumerate(zip(st["cells"], step["expect"])) if a != b}
            st["bad"] = bad
            if not bad:
                self._right()
            else:
                self._wrong(f"{len(bad)} row(s) wrong (marked red). Check row {min(bad) + 1} first.")
        elif kind == "wavefill":
            if None in st["vals"]:
                self._say("Fill in every box first.", False)
                return
            bad = {i for i, (a, b) in enumerate(zip(st["vals"], step["expect"])) if a != b}
            st["bad"] = bad
            if not bad:
                self._right()
            else:
                self._wrong(f"Edge {min(bad) + 1} is wrong. Look at the inputs at that dashed line.")
        elif kind == "regplay":
            self._check_reg()
        elif kind == "seqtable":
            if any(len(t) < step["width"] for t in st["typed"]):
                self._say("Type all the bits in every row first.", False)
                return
            bad = {i for i, (a, b) in enumerate(zip(st["typed"], step["expect"])) if a != b}
            st["bad"] = bad
            if not bad:
                self._right()
            else:
                self._wrong(f"Row {min(bad) + 1} is wrong. Work from the row above it.")
        elif kind == "cntplay":
            need = step["need"]
            if need.get("rollover") and not st["rolled"]:
                self._say("Keep pressing CLOCK until the counter wraps back to 0.", False)
            elif "t_seen" in need and need["t_seen"] not in st["t_seen"]:
                self._say(f"Keep pressing CLOCK until T{need['t_seen']} = 1.", False)
            else:
                self._right()
        elif kind == "exctable":
            if any(None in row for row in st["cells"]):
                self._say("Fill every cell first.", False)
                return
            bad = {i for i, (a, b) in enumerate(zip(st["cells"], step["expect"])) if a != b}
            st["bad"] = bad
            if not bad:
                self._right()
            else:
                self._wrong(f"{len(bad)} row(s) wrong (marked red). Check row {min(bad) + 1} first.")
        else:
            super()._check()

    def _check_reg(self):
        step, st = self.step, self.st
        if "target_reg" in step:
            if st["reg"] == step["target_reg"] and st["shifts"] >= step["min_clocks"]:
                self._right()
            elif st["reg"] == step["target_reg"]:
                self._say("Shift the bits in one at a time with CLOCK.", False)
            else:
                self._wrong("The register does not show the pattern yet. Remember the first bit travels furthest.")
        else:
            want = step["target_out"]
            if st["last_load"] != step["need_load"]:
                self._wrong("First click the P chips to make 1 0 1 1 and press LOAD.")
            elif len(st["out_since"]) < len(want):
                self._say("Now press CLOCK four times and watch SERIAL OUT.", False)
            elif st["out_since"][:len(want)] == want:
                self._right("The bits left from the right end.")
            else:
                self._wrong("The output order is not right. Load 1 0 1 1 and clock it out again.")

    # ---------------- update ----------------
    def update(self, dt):
        super().update(dt)
        if self.phase == "play" and self.step["kind"] == "sdemo":
            self.demo_clock += dt
            if self.demo_clock >= 4.5:
                self.demo_clock = 0.0
                self._on_action(("sframe", 1))

    # ---------------- drawing ----------------
    def draw(self, screen):
        super().draw(screen)
        if self.phase == "play" and self.step.get("exam"):
            tag = pygame.Rect(WORK.right - 112, WORK.y + 8, 100, 24)
            pygame.draw.rect(screen, (60, 46, 14), tag, border_radius=6)
            pygame.draw.rect(screen, YELLOW, tag, 2, border_radius=6)
            img = self.f_tiny.render("EXAM STYLE", True, YELLOW)
            screen.blit(img, img.get_rect(center=tag.center))

    def _intro(self, screen, text):
        """Draws the task text at the top and returns the y just below it."""
        width = WORK.width - 40 - (110 if self.step.get("exam") else 0)
        y = WORK.y + 12
        for line in wrap_text(self.f_small, text, width)[:3]:
            screen.blit(self.f_small.render(line, True, CYAN), (WORK.x + 20, y))
            y += 22
        return y

    def _caption(self, screen, text, top):
        """Draws a caption starting at `top` and returns the y just below it."""
        y = top
        for line in wrap_text(self.f_body, text, WORK.width - 40)[:4]:
            screen.blit(self.f_body.render(line, True, WHITE), (WORK.x + 20, y))
            y += 26
        return y

    def _cell(self, screen, rect, text, selected=False, bad=False, filled=True, color=WHITE):
        pygame.draw.rect(screen, (28, 54, 40) if filled else (30, 34, 44), rect, border_radius=6)
        edge = RED if bad else (YELLOW if selected else GREY)
        pygame.draw.rect(screen, edge, rect, 3, border_radius=6)
        img = self.f_body.render(text, True, color)
        screen.blit(img, img.get_rect(center=rect.center))

    def _static_cell(self, screen, rect, text, color=WHITE):
        pygame.draw.rect(screen, (24, 40, 58), rect, border_radius=6)
        img = self.f_body.render(text, True, color)
        screen.blit(img, img.get_rect(center=rect.center))

    def _head(self, screen, rect, text, color=YELLOW):
        pygame.draw.rect(screen, (30, 60, 84), rect, border_radius=6)
        img = self.f_small.render(text, True, color)
        screen.blit(img, img.get_rect(center=rect.center))

    def _inline_switch(self, screen, cx, cy, label, value, action):
        """Compact switch with its label on the left (two fit above each other)."""
        rect = pygame.Rect(0, 0, 88, 40)
        rect.center = (cx, cy)
        pygame.draw.rect(screen, (22, 80, 52) if value else (36, 44, 58), rect, border_radius=20)
        pygame.draw.rect(screen, GREEN if value else GREY, rect, 3, border_radius=20)
        knob_x = rect.right - 20 if value else rect.left + 20
        pygame.draw.circle(screen, WHITE, (knob_x, cy), 15)
        img = self.f_body.render(f"{label}", True, YELLOW)
        screen.blit(img, img.get_rect(midright=(rect.left - 10, cy)))
        self.buttons.append((rect.inflate(60, 8), action))

    def _draw_ffout(self, screen, rect, q):
        """Bulbs on the Q and Q' pins."""
        for frac, val in ((0.28, q), (0.72, None if q is None else 1 - q)):
            py = rect.y + int(rect.h * frac)
            if val is None:
                img = self.f_title.render("?", True, RED)
                screen.blit(img, img.get_rect(center=(rect.right + 70, py)))
            else:
                draw_bulb(screen, rect.right + 70, py, 14, val)

    # --- demos ---
    def _draw_sdemo(self, screen):
        step, st = self.step, self.st
        frame = step["frames"][st["frame"]]
        kind, spec = frame["draw"]
        top = WORK.y + 56
        if kind == "ff":
            rect = pygame.Rect(WORK.centerx - 70, top + 10, 140, 160)
            draw_flipflop(screen, self.fonts, rect, spec["kind"], spec["q"], spec.get("ins"))
            self._draw_ffout(screen, rect, spec["q"])
        elif kind == "wave":
            n = spec["periods"]
            per_w = min(110, 440 // n)
            x0 = WORK.x + 100
            rows = spec["rows"]
            draw_waveforms(screen, self.fonts, x0, top, per_w, n, rows, row_h=48, mark_edge=spec.get("mark"))
            if spec.get("arrows"):
                for k in range(n):
                    ax = x0 + k * per_w + per_w // 2
                    draw_arrow(screen, (ax, top + 48 - 6), (ax, top + 16), YELLOW, 3)
        elif kind == "reg":
            width = 4 * 62 + 3 * 28
            x0 = WORK.centerx - width // 2 + 20
            draw_register(screen, self.fonts, x0, top + 60, spec["bits"], serial_in=spec.get("serial_in", False),
                          parallel_in=spec.get("parallel_in", False), serial_out=spec.get("serial_out", False),
                          parallel_out=spec.get("parallel_out", False), si_value=spec.get("si"))
        elif kind == "counter":
            self._draw_counter_frame(screen, spec, top)
        self._caption(screen, frame["caption"], WORK.bottom - 150)
        total = len(step["frames"])
        dots_y = WORK.bottom - 170
        for i in range(total):
            cx = WORK.centerx - (total - 1) * 14 + i * 28
            if i == st["frame"]:
                pygame.draw.circle(screen, CYAN, (cx, dots_y), 8)
            elif i < st["seen"]:
                pygame.draw.circle(screen, GREEN, (cx, dots_y), 6)
            else:
                pygame.draw.circle(screen, GREY, (cx, dots_y), 6, 2)
        self._button(screen, pygame.Rect(WORK.x + 20, WORK.bottom - 54, 110, 36), "< BACK", ("sframe", -1), CYAN)
        self._button(screen, pygame.Rect(WORK.right - 130, WORK.bottom - 54, 110, 36), "NEXT >", ("sframe", 1), CYAN)

    def _draw_counter_frame(self, screen, spec, top):
        n = spec["nbits"]
        pulses = spec.get("pulses", 8)
        upto = spec.get("upto", pulses)
        states = count_states(n, 1 << n, 0, pulses)
        if spec.get("chain"):
            state = spec.get("state", states[min(upto, pulses)])
            qvals = [bit_of(state, i) for i in range(n)]
            tvals = t_inputs(state, n) if spec.get("tvals") else None
            draw_counter_chain(screen, self.fonts, WORK.x + 110, top + 20, n, spec["mode"], qvals, tvals)
            top += 136 if spec["mode"] == "ripple" else 150
        if spec.get("timing"):
            rows_h = 33 if spec.get("chain") else 56
            per_w = 56 if pulses == 8 else 440 // max(1, pulses)
            draw_counter_timing(screen, self.fonts, WORK.x + 90, top, per_w, n, states, spec["mode"], row_h=rows_h,
                                upto=upto, mark_edge=spec.get("mark"), delay_step=spec.get("delay", 6))

    # --- flip-flop sandbox ---
    def _draw_ffplay(self, screen):
        step, st = self.step, self.st
        kind = step["ff"]
        names = FF_INPUTS[kind]
        y = self._intro(screen, step["task"]) + 10
        rx = WORK.x + int(WORK.width * 0.42)
        rect = pygame.Rect(rx, y + 20, 150, 150)
        draw_flipflop(screen, self.fonts, rect, kind, st["q"], dict(zip(names, st["ins"])))
        self._draw_ffout(screen, rect, st["q"])
        for i, py in enumerate(ff_pin_ys(rect, len(names))):
            on = st["ins"][i]
            cx = WORK.x + 150
            self._inline_switch(screen, cx, py, names[i], on, ("fin", i))
            pygame.draw.line(screen, WIRE_ON if on else WIRE_OFF, (cx + 44, py), (rect.x - 36, py), 4)
        cy = rect.y + int(rect.h * 0.85)
        self._button(screen, pygame.Rect(WORK.x + 20, cy - 18, 130, 36), "CLOCK [SPACE]", ("fclock",), YELLOW)
        qtxt = "?" if st["q"] is None else str(st["q"])
        img = self.f_body.render(f"Q = {qtxt}", True, RED if st["q"] is None else (BULB_YELLOW if st["q"] else GREY))
        screen.blit(img, img.get_rect(center=(rect.right + 70, rect.bottom + 22)))
        ly = rect.bottom + 46
        for line in st["log"]:
            screen.blit(self.f_tiny.render(line, True, WHITE), (WORK.x + 20, ly))
            ly += 20
        screen.blit(self.f_tiny.render("COMBINATIONS TRIED", True, GREY), (WORK.x + 24, WORK.bottom - 74))
        for i, c in enumerate(input_combos(kind)):
            self._chip(screen, WORK.x + 80 + i * 100, WORK.bottom - 32, "".join(map(str, c)), c in st["seen"], w=84)

    def _draw_fftable(self, screen):
        step, st = self.step, self.st
        kind = step["ff"]
        names = FF_INPUTS[kind]
        self._intro(screen, step["task"])
        x0, y0, cw = WORK.x + 50, 182, 76
        heads = list(names) + ["Qn", "Qn+1"]
        for j, h in enumerate(heads):
            self._head(screen, pygame.Rect(x0 + j * cw, y0, cw - 6, 32), h, YELLOW if h == "Qn+1" else WHITE)
        for i, (combo, q) in enumerate(char_rows(kind)):
            ry = y0 + 40 + i * 41
            vals = list(combo) + [q]
            for j, v in enumerate(vals):
                self._static_cell(screen, pygame.Rect(x0 + j * cw, ry, cw - 6, 36), str(v))
            rect = pygame.Rect(x0 + len(vals) * cw, ry, cw - 6, 36)
            v = st["cells"][i]
            txt = "?" if v is None else ("X" if v == X else str(v))
            self._cell(screen, rect, txt, i == st["sel"], i in st["bad"], v is not None,
                       GREY if v is None else (YELLOW if v == X else GREEN))
            self.buttons.append((rect, ("fcell", i)))
        box = pygame.Rect(WORK.right - 190, 250, 110, 150)
        draw_flipflop(screen, self.fonts, box, kind, None, None, show_values=False)

    def _draw_wavefill(self, screen):
        step, st = self.step, self.st
        n = step["periods"]
        y = self._intro(screen, step["task"]) + 10
        per_w = min(84, 480 // n)
        x0, row_h = WORK.x + 80, 50
        rows = [{"name": "CLK", "kind": "clk", "color": YELLOW}] + list(step["signals"])
        rows.append({"name": step["ans_name"], "kind": "out", "init": step["q0"], "vals": st["vals"], "color": GREEN})
        draw_waveforms(screen, self.fonts, x0, y, per_w, n, rows, row_h=row_h)
        by = y + len(rows) * row_h + 14
        screen.blit(self.f_tiny.render(f"{step['ans_name']} after each edge:", True, GREY), (WORK.x + 20, by))
        for k in range(n):
            rect = pygame.Rect(0, 0, min(per_w - 14, 46), 34)
            rect.center = (x0 + k * per_w + per_w // 2, by + 30)
            v = st["vals"][k]
            self._cell(screen, rect, "?" if v is None else str(v), k == st["sel"], k in st["bad"], v is not None,
                       GREY if v is None else GREEN)
            self.buttons.append((rect, ("wcell", k)))

    # --- shift register sandbox ---
    def _draw_regplay(self, screen):
        step, st = self.step, self.st
        ctl = step["controls"]
        y = self._intro(screen, step["task"]) + 10
        if "parallel" in ctl:
            y += 50
        x0 = WORK.x + (190 if "serial" in ctl else 110)
        y0 = y + 20
        rects = draw_register(screen, self.fonts, x0, y0, st["reg"])
        if "serial" in ctl:
            self._switch(screen, WORK.x + 80, y0 + 31, "SI", st["si"], ("rser",))
            draw_arrow(screen, (WORK.x + 130, y0 + 31), (x0 - 2, y0 + 31), WIRE_ON if st["si"] else WIRE_OFF)
        r = rects[-1]
        draw_arrow(screen, (r.right + 2, r.centery), (r.right + 44, r.centery), GREEN)
        screen.blit(self.f_tiny.render("OUT", True, GREEN), (r.right + 48, r.centery - 8))
        if "parallel" in ctl:
            for i, rc in enumerate(rects):
                self._chip(screen, rc.centerx, y0 - 30, f"P{i + 1} = {st['par'][i]}", st["par"][i], w=76, h=28)
                self.buttons.append((pygame.Rect(rc.centerx - 38, y0 - 44, 76, 28), ("rpar", i)))
        ty = y0 + 84
        screen.blit(self.f_tiny.render("bits move RIGHT at every clock pulse", True, GREY), (WORK.x + 24, ty))
        out = " ".join(map(str, st["out"][-8:])) if st["out"] else "-"
        screen.blit(self.f_small.render(f"Clock pulses: {st['clocks']}    Serial output: {out}", True, WHITE),
                    (WORK.x + 24, ty + 26))
        for i, line in enumerate(wrap_text(self.f_small, st["msg"], WORK.width - 48)[:2]):
            screen.blit(self.f_small.render(line, True, YELLOW), (WORK.x + 24, ty + 54 + i * 22))
        bx, by = WORK.x + 20, WORK.bottom - 54
        self._button(screen, pygame.Rect(bx, by, 160, 36), "CLOCK [SPACE]", ("rclock",), YELLOW)
        bx += 172
        if "load" in ctl:
            self._button(screen, pygame.Rect(bx, by, 110, 36), "LOAD [L]", ("rload",), CYAN)
            bx += 122
        self._button(screen, pygame.Rect(bx, by, 120, 36), "RESET [R]", ("rreset",), GREY)

    def _draw_seqtable(self, screen):
        step, st = self.step, self.st
        y = self._intro(screen, step["task"]) + 8
        cols = step["cols"]
        x0, cw = WORK.x + 24, 92
        for j, c in enumerate(cols):
            self._head(screen, pygame.Rect(x0 + j * cw, y, cw - 6, 30), c, WHITE)
        ax = x0 + len(cols) * cw + 8
        self._head(screen, pygame.Rect(ax, y, step["width"] * 40 + 8, 30), step["answer_head"], YELLOW)
        ry = y + 36
        self._static_cell(screen, pygame.Rect(x0, ry, cw - 6, 34), "Start", GREY)
        for b, ch in enumerate(step["start"]):
            self._static_cell(screen, pygame.Rect(ax + 4 + b * 40, ry, 34, 34), ch, GREY)
        for i, left in enumerate(step["rows"]):
            ry = y + 36 + (i + 1) * 40
            for j, text in enumerate(left):
                self._static_cell(screen, pygame.Rect(x0 + j * cw, ry, cw - 6, 34), text)
            typed = st["typed"][i]
            for b in range(step["width"]):
                rect = pygame.Rect(ax + 4 + b * 40, ry, 34, 34)
                ch = typed[b] if b < len(typed) else ""
                self._cell(screen, rect, ch or "_", i == st["sel"] and b == len(typed), i in st["bad"], bool(ch),
                           GREEN if ch else GREY)
            self.buttons.append((pygame.Rect(x0, ry, ax + step["width"] * 40 - x0, 34), ("srow", i)))

    # --- counter sandbox ---
    def _draw_cntplay(self, screen):
        step, st = self.step, self.st
        n, mode = step["nbits"], step["mode"]
        y = self._intro(screen, step["task"]) + 10
        state = st["state"]
        qvals = [bit_of(state, i) for i in range(n)]
        tvals = t_inputs(state, n) if mode == "sync" else None
        top = y + (30 if mode == "sync" else 0)
        draw_counter_chain(screen, self.fonts, WORK.x + 90, top + 10, n, mode, qvals, tvals)
        by = top + (190 if mode == "sync" else 150)
        for i in range(n - 1, -1, -1):
            cx = WORK.x + 60 + (n - 1 - i) * 62
            draw_bulb(screen, cx, by, 18, qvals[i])
            lab = self.f_tiny.render(f"Q{i}", True, WHITE)
            screen.blit(lab, lab.get_rect(center=(cx, by + 30)))
        screen.blit(self.f_body.render(f"Count = {state}  ({bits_str(state, n)})", True, YELLOW),
                    (WORK.x + 20, by + 52))
        for i, line in enumerate(wrap_text(self.f_small, st["msg"], 260)[:3]):
            screen.blit(self.f_small.render(line, True, GREEN), (WORK.x + 20, by + 84 + i * 22))
        if step["show_wave"]:
            window = st["hist"][-7:]
            if len(window) > 1:
                draw_counter_timing(screen, self.fonts, WORK.x + 330, by - 20, 40, n, window, mode, row_h=30)
        bx, by2 = WORK.x + 20, WORK.bottom - 54
        self._button(screen, pygame.Rect(bx, by2, 220, 36), "CLOCK PULSE [SPACE]", ("cclock",), YELLOW)
        self._button(screen, pygame.Rect(bx + 232, by2, 120, 36), "RESET [R]", ("creset",), GREY)
        if mode == "sync":
            seen = "T2 = 1 seen: " + ("yes" if 2 in st["t_seen"] else "not yet")
            screen.blit(self.f_tiny.render(seen, True, GREY), (WORK.right - 130, by2 - 20))

    def _draw_exctable(self, screen):
        step, st = self.step, self.st
        y = self._intro(screen, step["task"]) + 8
        lh = step["left_heads"]
        ih = step["in_heads"]
        x0, cw = WORK.x + 40, 84
        for j, h in enumerate(lh):
            self._head(screen, pygame.Rect(x0 + j * cw, y, cw - 6, 32), h, WHITE)
        for j, h in enumerate(ih):
            self._head(screen, pygame.Rect(x0 + (len(lh) + j) * cw + 12, y, cw - 6, 32), h, YELLOW)
        for i, left in enumerate(step["left"]):
            ry = y + 40 + i * 42
            for j, text in enumerate(left):
                self._static_cell(screen, pygame.Rect(x0 + j * cw, ry, cw - 6, 36), text)
            for c in range(len(ih)):
                rect = pygame.Rect(x0 + (len(lh) + c) * cw + 12, ry, cw - 6, 36)
                v = st["cells"][i][c]
                txt = "?" if v is None else ("X" if v == X else str(v))
                self._cell(screen, rect, txt, st["sel"] == (i, c), i in st["bad"], v is not None,
                           GREY if v is None else (YELLOW if v == X else GREEN))
                self.buttons.append((rect, ("ecell", i, c)))

    # --- extra visuals for choice steps ---
    def _draw_extra_visual(self, screen, step, top, bottom):
        if step["visual"] == "regdiag":
            width = 4 * 62 + 3 * 28
            draw_register(screen, self.fonts, WORK.centerx - width // 2, top + 78, None, **step["flags"])

    # ---------------- stage-complete card ----------------
    def _draw_done(self, screen):
        stage = self.stage
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, GREEN, FULL, 3, border_radius=10)
        screen.blit(self.f_big.render(f"STAGE {self.stage_i + 1} COMPLETE", True, GREEN), (FULL.x + 24, FULL.y + 14))
        screen.blit(self.f_body.render(f"{stage['title']}  -  {stage['sub']}", True, WHITE), (FULL.x + 24, FULL.y + 62))
        self._draw_example(screen, stage["example"])
        rx = FULL.x + 400
        rw = FULL.right - rx - 24
        y = FULL.y + 104
        for label, text in stage["items"]:
            screen.blit(self.f_small.render(label, True, CYAN), (rx, y))
            y += 24
            for line in wrap_text(self.f_small, text, rw):
                screen.blit(self.f_small.render(line, True, WHITE), (rx, y))
                y += 23
            y += 8
        screen.blit(self.f_small.render("Saved to NOTEBOOK [N]  >  TEST THE LOGIC  >  MY BASIC NOTES", True, YELLOW),
                    (FULL.x + 24, FULL.bottom - 62))
        last = self.stage_i >= len(self.stages) - 1
        self._button(screen, pygame.Rect(FULL.right - 230, FULL.bottom - 52, 210, 38),
                     "FINISH LEVEL" if last else "NEXT STAGE  [ENTER]", ("next",), GREEN)

    def _draw_example(self, screen, example):
        kind, spec = example
        ox, oy = FULL.x + 30, FULL.y + 120
        if kind == "ff":
            rect = pygame.Rect(ox + 100, oy + 50, 120, 170)
            draw_flipflop(screen, self.fonts, rect, spec["kind"], spec["q"], spec.get("ins"))
            self._draw_ffout(screen, rect, spec["q"])
        elif kind == "wave":
            draw_waveforms(screen, self.fonts, ox + 40, oy + 20, 70, spec["periods"], spec["rows"], row_h=62)
        elif kind == "reg":
            draw_register(screen, self.fonts, ox + 112, oy + 80, spec["bits"], box=44, gap=18,
                          serial_in=spec.get("serial_in", False), parallel_out=spec.get("parallel_out", False))
        elif kind == "counter":
            n = spec["nbits"]
            if spec.get("chain"):
                state = spec.get("state", 0)
                qv = [bit_of(state, i) for i in range(n)]
                tv = t_inputs(state, n) if spec.get("tvals") else None
                draw_counter_chain(screen, self.fonts, ox + 70, oy + 60, n, spec["mode"], qv, tv, box_w=58, gap=40)
            if spec.get("timing"):
                states = count_states(n, 1 << n, 0, spec["pulses"])
                draw_counter_timing(screen, self.fonts, ox + 50, oy + 20, 36, n, states, spec["mode"], row_h=50)
        elif kind == "none":
            for i, g in enumerate(("T", "JK", "D", "SR")):
                self._chip(screen, ox + 60 + (i % 2) * 130, oy + 70 + (i // 2) * 70, g, True, w=100, h=48)

    # ---------------- notebook autofill ----------------
    def notebook_lines(self, stage):
        return NOTEBOOK_LINES[stage["id"]]


BULB_YELLOW = (255, 218, 92)

NOTEBOOK_LINES = {
    "q1_memory": [
        "SEQUENTIAL 1: MEMORY AND THE SR FLIP-FLOP",
        "- A flip-flop stores ONE bit. Q is the stored bit, Q' is its opposite.",
        "- It changes only at the clock pulse. Between pulses it HOLDS its value (that is memory).",
        "- SR table (S R gives next Q): 00 hold, 01 reset (0), 10 set (1), 11 not allowed (X).",
        "- n flip-flops store n bits = 2^n different values.",
    ],
    "q2_clock": [
        "SEQUENTIAL 2: CLOCK AND THE D FLIP-FLOP",
        "- The clock is a steady 0 / 1 signal. A flip-flop updates at the RISING EDGE (0 to 1).",
        "- D flip-flop: Qn+1 = D. At the edge Q copies D and holds it until the next edge.",
        "- Timing diagram: inputs change before the edge, Q changes AT the edge and then holds.",
        "- Q is D delayed by one clock. A chain of D flip-flops is a shift register.",
    ],
    "q3_tjk": [
        "SEQUENTIAL 3: T AND JK FLIP-FLOPS",
        "- T flip-flop: T = 0 holds, T = 1 toggles. Qn+1 = T XOR Qn.",
        "- JK table (J K gives next Q): 00 hold, 01 reset, 10 set, 11 toggle.",
        "- JK removes the forbidden case of SR: J = K = 1 simply toggles.",
        "- Race-around: J = K = 1 with a long clock could toggle repeatedly. A MASTER-SLAVE JK (two latches) changes Q only once per pulse.",
    ],
    "q4_convert": [
        "SEQUENTIAL 4: FLIP-FLOP CONVERSION",
        "- Excitation table (JK): Q 0 to 0: J=0 K=X. 0 to 1: J=1 K=X. 1 to 0: J=X K=1. 1 to 1: J=X K=0.",
        "- Recipe: new inputs and Q, wanted Qn+1, read the old flip-flop's inputs from its excitation table, simplify.",
        "- JK to T: J = K = T.   JK to D: J = D, K = D'.   D to T: D = T XOR Q.   SR to D: S = D, R = D'.",
    ],
    "q5_shift": [
        "SEQUENTIAL 5: SHIFT REGISTERS",
        "- A shift register is a row of D flip-flops. Every clock pulse moves each bit one place.",
        "- Four kinds, named IN then OUT: SISO, SIPO, PISO, PIPO (S = serial, P = parallel).",
        "- n bits need n clock pulses to cross an n-bit register. The FIRST bit entered ends up furthest along.",
        "- SIPO turns serial data into parallel data. PISO does the opposite.",
    ],
    "q6_ripple": [
        "SEQUENTIAL 6: RIPPLE COUNTERS",
        "- A counter is a row of T flip-flops with T = 1. In a ripple (asynchronous) counter each one is clocked by the one before.",
        "- Q0 toggles every pulse, Q1 every 2nd, Q2 every 4th: that is binary counting. 3 flip-flops give 2^3 = 8 states.",
        "- Mod-N counter: N states (0 to N-1). Detect N and reset. Flip-flops needed: smallest n with 2^n at least N.",
        "- Mod-10 (decade) counter: reset when the count reaches 1010 (NAND of Q3 and Q1).",
        "- Drawback: the change ripples through, so the delays add up.",
    ],
    "q7_sync": [
        "SEQUENTIAL 7: SYNCHRONOUS COUNTERS",
        "- All flip-flops share ONE clock, so they change together (no ripple delay, so it runs faster).",
        "- A bit toggles only when ALL the bits below it are 1: T0 = 1, T1 = Q0, T2 = Q0 Q1, T3 = Q0 Q1 Q2.",
        "- Design: T = 1 exactly when that bit must change from the present count to the next count.",
    ],
    "q8_boss": [
        "SEQUENTIAL 8: CHEAT SHEET",
        "- Characteristic equations: D: Qn+1 = D.  T: Qn+1 = T XOR Qn.  JK: Qn+1 = J Qn' + K' Qn.  SR: Qn+1 = S + R' Qn.",
        "- Timing: inputs change before the rising edge. Q changes AT the edge and holds until the next one.",
        "- Registers: n pulses for a bit to cross n flip-flops. Counters: mod-N needs smallest n with 2^n at least N.",
        "- Synchronous counter: T_k = AND of all lower bits.",
    ],
}