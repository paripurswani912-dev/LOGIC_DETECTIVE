"""merge_into_notebook.py  -  put the FLIP-FLOPS, SHIFT REGISTERS and COUNTERS
labs directly inside notebook.py.

    python merge_into_notebook.py path/to/notebook.py

Makes notebook.py.bak first. Every edit must match exactly once, otherwise
nothing is written.
"""
import shutil
import sys

BLOCK = r'''# ------------------------------------------------------------
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


'''

HELPERS = r'''    # --------------------------------------------------------
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

'''

INIT_ADD = """
        # Sequential-circuit labs (flip-flops, shift registers, counters)
        self._seq_labs = {"FLIP-FLOPS": FlipFlopLab(),
                          "SHIFT REGISTERS": ShiftLab(),
                          "COUNTERS": CounterLab()}
        self.seq_notes = {t: False for t in self._seq_labs}
        self.reference_notes["FLIP-FLOPS"] = flipflop_notes_lines()
        self.reference_notes["SHIFT REGISTERS"] = shift_notes_lines()
        self.reference_notes["COUNTERS"] = counter_notes_lines()
"""

EDITS = [
    # (anchor, replacement)
    ("class DetectiveNotebook:\n", BLOCK + "class DetectiveNotebook:\n"),

    ('            "COMBINATIONAL CIRCUITS",\n            "REGISTERS AND LFSRs",\n        ]',
     '            "COMBINATIONAL CIRCUITS",\n            "FLIP-FLOPS",\n'
     '            "SHIFT REGISTERS",\n            "COUNTERS",\n'
     '            "REGISTERS AND LFSRs",\n        ]'),

    ('        self.reference_notes["COMBINATIONAL CIRCUITS"] = _comb_notes_lines()\n',
     '        self.reference_notes["COMBINATIONAL CIRCUITS"] = _comb_notes_lines()\n'
     + INIT_ADD),

    ("    def _topic_is_text(self):\n", HELPERS + "    def _topic_is_text(self):\n"),

    ("""                and self.comb.handle_click(event.pos)):
            return True
""",
     """                and self.comb.handle_click(event.pos)):
            return True

        # Sequential labs: clicks on inputs, CLK boxes and buttons.
        seq = self._seq_lab()
        if (seq and not seq[1] and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1 and seq[0].handle_click(event.pos)):
            return True
"""),

    ("""            if self._on_comb_page() and self._comb_handle_key(event):
                return True
""",
     """            if self._on_comb_page() and self._comb_handle_key(event):
                return True

            if self._seq_lab() and self._seq_handle_key(event):
                return True
"""),

    ("""        elif action_type == "comb_notes":
            self.comb_notes = not self.comb_notes
            self.topic_scroll = 0
""",
     """        elif action_type == "comb_notes":
            self.comb_notes = not self.comb_notes
            self.topic_scroll = 0

        elif action_type == "seq_notes":
            self.seq_notes[value] = not self.seq_notes[value]
            self.topic_scroll = 0
"""),

    ("        self.comb_notes = False\n        self.km_notes = False\n",
     "        self.comb_notes = False\n        self.km_notes = False\n"
     "        for _t in self.seq_notes:\n            self.seq_notes[_t] = False\n"),

    ("""        if topic == "COMBINATIONAL CIRCUITS":
            return self.comb_notes
        return True""",
     """        if topic == "COMBINATIONAL CIRCUITS":
            return self.comb_notes
        if topic in self.seq_notes:
            return self.seq_notes[topic]
        return True"""),

    ("""        if topic == "COMBINATIONAL CIRCUITS" and not self.comb_notes:
            self._draw_comb_lab(screen, content)
            return
""",
     """        if topic == "COMBINATIONAL CIRCUITS" and not self.comb_notes:
            self._draw_comb_lab(screen, content)
            return

        if topic in self._seq_labs and not self.seq_notes[topic]:
            self._draw_seq_lab(screen, content, topic)
            return
"""),

    ('            "COMBINATIONAL CIRCUITS": "comb_notes",\n        }',
     '            "COMBINATIONAL CIRCUITS": "comb_notes",\n'
     '            "FLIP-FLOPS": "seq_notes",\n'
     '            "SHIFT REGISTERS": "seq_notes",\n'
     '            "COUNTERS": "seq_notes",\n        }'),

    ("            self.buttons.append((lab_rect, (lab_actions[topic], None)))",
     "            self.buttons.append((lab_rect, (lab_actions[topic],\n"
     '                                 topic if lab_actions[topic] == "seq_notes" else None)))'),

    ("""        if len(self.reference_topics) > 8:       # BASIC path: nine topics must still fit
            button_h, gap = 33, 7
""",
     """        n_topics = len(self.reference_topics)    # 12 topics in BASIC mode: shrink to fit
        avail = (self.back_button.y - 8) - (content.y + 49)
        gap = 7 if n_topics > 8 else 12
        button_h = max(24, min(39, (avail - gap * (n_topics - 1)) // n_topics))
"""),

    ('            practice["level_five"] = "COMBINATIONAL CIRCUITS"\n',
     '            practice["level_five"] = "COMBINATIONAL CIRCUITS"\n'
     '            practice["level_six"] = "FLIP-FLOPS"\n'),
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    path = sys.argv[1]
    text = open(path, encoding="utf-8").read()
    if "class FlipFlopLab" in text:
        print("Already merged. Nothing to do.")
        return
    for i, (anchor, new) in enumerate(EDITS, 1):
        n = text.count(anchor)
        if n != 1:
            print(f"STOPPED: edit {i} anchor found {n} times (need 1):\n{anchor}")
            return
        text = text.replace(anchor, new)
    shutil.copyfile(path, path + ".bak")
    open(path, "w", encoding="utf-8").write(text)
    print(f"Done. Backup saved as {path}.bak")


if __name__ == "__main__":
    main()
