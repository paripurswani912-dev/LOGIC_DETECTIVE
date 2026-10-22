# puzzles/circuit_engine.py
# Reusable circuit simulator + mouse workbench for every level.
#
# Circuit   = components + wires + evaluation (the "simulation").
# Workbench = draws a Circuit inside a rectangle and handles the mouse:
#   - Left-click a switch ........ flip it
#   - Drag (or click, then click)  from an OUTPUT pin (right side)
#     to an INPUT pin (left side) to create a wire
#   - Click an already-wired input pin to pick the wire up again
#   - Right-click an input pin .... delete that wire
#
# allow_placing=True (Level 4+):
#   - workbench.spawn("XOR") ..... add a gate from a palette
#   - Drag a gate body ........... move it
#   - Right-click a gate body .... delete it (and its wires)
#
# allow_moving=True:
#   - Drag ANY part by its body to move it (a plain click still flips
#     switches / sets flip-flop seeds).
#
# Sequential circuits (Level 6+):
#   - "DFF" component: D input, Q output, shared implicit clock.
#   - circuit.clock() ............ updates ALL flip-flops at once.
#   - Flip-flops break combinational loops, so feedback wires are legal.
#   - allow_preset=True .......... click a flip-flop to set its seed bit.
#   - circuit.history ............ Q value of every flip-flop per tick.
#   - "SOURCE" component: a read-only input whose value the level sets.
#
# Optional per-circuit look & routing (all default to the old behaviour):
#   circuit.size_scale  : multiplies every component's size (e.g. 0.75)
#   circuit.font_scale  : multiplies every label font size
#   circuit.wire_colour : one fixed colour for every wire (None = by value)
#   circuit.channels    : {(src_id, dst_id, pin): channel} manual wire routes
#       channel = None   -> run along the source pin's own height
#       channel = "DST"  -> run along the target pin's own height
#       channel = 0..1   -> run along that fraction of the bench height
#   circuit.auto_route  : True = every wire finds its own free lane/channel
#       (avoids parts, captions and other wires; follows moved parts)

import math
import pygame

WIRE_COLOUR = (70, 150, 175)   # default single wire colour


# ------------------------------------------------------------
# Wire drawing helpers
# ------------------------------------------------------------

def route_wire(src, dst, channel_y, pin, lane_gap=14, lane_step=8):
    """
    src, dst   : (x, y) pixel positions of the output pin and input pin
    channel_y  : pixel y of this wire's private horizontal channel
    pin        : 0 or 1, which input pin of the gate (offsets the lane)
    Returns the list of points to draw as one polyline.
    """
    sx, sy = src
    dx, dy = dst

    # Perfectly aligned: one straight line.
    if abs(sy - dy) < 2 and sx < dx:
        return [src, dst]

    lane_out = sx + lane_gap                    # just right of the source pin
    lane_in = dx - lane_gap - lane_step * pin   # just left of the target pin

    pts = [src,
           (lane_out, sy),
           (lane_out, channel_y),
           (lane_in, channel_y),
           (lane_in, dy),
           dst]

    # Drop zero-length segments so corners draw cleanly.
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def draw_wire(screen, pts, colour=WIRE_COLOUR, width=3):
    pygame.draw.lines(screen, colour, False, pts, width)
    for p in pts[1:-1]:                         # round the corners
        pygame.draw.circle(screen, colour, (int(p[0]), int(p[1])),
                           max(1, width // 2))


def draw_pixel_gate_symbol(surface, gate, rect, color, scale=None):
    """Pixel-art logic gate drawn on a tiny grid and scaled up with
    hard pixel edges. Fills `rect`: input stubs reach the left edge,
    the output stub reaches the right edge."""
    rect = pygame.Rect(rect)
    sc = scale or max(1, min(rect.w // 34, rect.h // 22))
    vw, vh = rect.w // sc, rect.h // sc          # tiny-grid size
    g = pygame.Surface((vw, vh), pygame.SRCALPHA)

    cy = vh // 2
    top = round(vh * 0.18)
    bot = 2 * cy - top

    def P(px, py):
        px, py = int(round(px)), int(round(py))
        if 0 <= px < vw and 0 <= py < vh:
            g.set_at((px, py), color)

    def line(x0, y0, x1, y1):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            P(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    def bez(p0, p1, p2):
        for i in range(401):
            t = i / 400
            a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
            P(a*p0[0] + b*p1[0] + c*p2[0], a*p0[1] + b*p1[1] + c*p2[1])

    def arc(cx, cyy, r, a0, a1):
        for i in range(721):
            a = math.radians(a0 + (a1 - a0) * i / 720)
            P(cx + r * math.cos(a), cyy + r * math.sin(a))

    # input pin rows (1/3 and 2/3 of the box, like Workbench.in_pin)
    pin_off = (rect.h / 6) / sc
    in_top = round(cy - pin_off)
    in_bot = 2 * cy - in_top

    xor = gate in ("XOR", "XNOR")
    bubble = gate in ("NAND", "NOR", "XNOR", "NOT")
    left = round(vw * 0.17) + (3 if xor else 0)
    if gate == "NOT":
        left = round(vw * 0.20)

    if gate == "NOT":
        tip = left + 16
        line(left, top, left, bot)
        line(left, top, tip, cy)
        line(left, bot, tip, cy)
        line(0, cy, left, cy)

    elif gate in ("AND", "NAND"):
        r = cy - top
        xc = left + 8
        tip = xc + r
        line(left, top, left, bot)
        line(left, top, xc, top)
        line(left, bot, xc, bot)
        arc(xc, cy, r, -90, 90)
        line(0, in_top, left, in_top)
        line(0, in_bot, left, in_bot)

    else:  # OR family
        tip = left + 16
        bez((left, top), (left + 10, top), (tip, cy))
        bez((left, bot), (left + 10, bot), (tip, cy))
        bez((left, top), (left + 6, cy), (left, bot))

        def back_x(base, yy):
            t = (yy - top) / (bot - top)
            return base + 12 * t * (1 - t)

        base = left
        if xor:
            base = left - 3
            bez((base, top), (base + 6, cy), (base, bot))
        line(0, in_top, back_x(base, in_top), in_top)
        line(0, in_bot, back_x(base, in_bot), in_bot)

    out = tip
    if bubble:                                   # hollow square bubble
        line(tip + 1, cy - 2, tip + 5, cy - 2)
        line(tip + 1, cy + 2, tip + 5, cy + 2)
        line(tip + 1, cy - 2, tip + 1, cy + 2)
        line(tip + 5, cy - 2, tip + 5, cy + 2)
        out = tip + 6
    line(out, cy, vw - 1, cy)

    big = pygame.transform.scale(g, (vw * sc, vh * sc))
    surface.blit(big, (rect.x + (rect.w - vw * sc) // 2,
                       rect.y + (rect.h - vh * sc) // 2))


# ------------------------------------------------------------
# Colours (match the Level 1 monitor look)
# ------------------------------------------------------------
BOX_FILL = (13, 29, 44)
CYAN = (0, 229, 239)
CYAN_DIM = (44, 103, 125)
WHITE = (220, 232, 244)
GREY = (112, 137, 158)
GREEN = (35, 230, 125)
YELLOW = (255, 220, 65)
ORANGE = (255, 184, 72)
RED = (255, 65, 78)
AREA_BG = (6, 16, 28)

GATE_FUNCS = {
    "AND": lambda v: v[0] & v[1],
    "OR": lambda v: v[0] | v[1],
    "XOR": lambda v: v[0] ^ v[1],
    "NAND": lambda v: 1 - (v[0] & v[1]),
    "NOR": lambda v: 1 - (v[0] | v[1]),
    "XNOR": lambda v: 1 - (v[0] ^ v[1]),
    "NOT": lambda v: 1 - v[0],
}

# Where new gates appear (fractions of the workbench area).
SPAWN_SLOTS = [
    (0.38, 0.20), (0.38, 0.50), (0.38, 0.80),
    (0.62, 0.20), (0.62, 0.50), (0.62, 0.80),
    (0.50, 0.35), (0.50, 0.65),
]

_FONTS = {}


def _font(size):
    size = max(8, int(size))
    if size not in _FONTS:
        _FONTS[size] = pygame.font.SysFont("monospace", size, bold=True)
    return _FONTS[size]


# ------------------------------------------------------------
# Components
# ------------------------------------------------------------

class Component:
    """kind is "SWITCH", "LED", "DFF", "SOURCE", or a gate name
    from GATE_FUNCS.

    (rx, ry) is the centre of the component as a fraction (0..1)
    of the workbench area, so layouts scale with the window.

    deletable=True marks parts the player placed (can be moved/deleted).

    value  : switches and sources
    init   : DFF seed bit (what RESET goes back to)
    state  : DFF current Q
    """

    def __init__(self, cid, kind, rx, ry, label="", sub="",
                 deletable=False):
        self.id = cid
        self.kind = kind
        self.rx = rx
        self.ry = ry
        self.label = label
        self.sub = sub
        self.deletable = deletable
        self.value = 0  # switches / sources
        self.init = 0   # DFF preset
        self.state = 0  # DFF Q

    @property
    def n_inputs(self):
        if self.kind in ("SWITCH", "SOURCE"):
            return 0
        if self.kind in ("LED", "NOT", "DFF"):
            return 1
        return 2

    @property
    def has_output(self):
        return self.kind != "LED"

    @property
    def size(self):
        if self.kind == "SWITCH":
            return (80, 46)
        if self.kind == "SOURCE":
            return (104, 46)
        if self.kind == "LED":
            return (66, 66)
        if self.kind == "DFF":
            return (76, 76)
        return (104, 66)


# ------------------------------------------------------------
# Circuit (pure logic, no drawing)
# ------------------------------------------------------------

class Circuit:
    def __init__(self):
        self.comps = {}
        self.wires = []  # (src_id, dst_id, dst_pin)
        self.ticks = 0
        self.history = {}  # dff id -> [Q at tick 0, Q at tick 1, ...]

        # Optional look / routing settings (defaults = old behaviour).
        self.size_scale = 1.0
        self.font_scale = 1.0
        self.wire_colour = None
        self.channels = {}
        self.auto_route = False

    def add(self, comp):
        self.comps[comp.id] = comp
        return comp

    def remove(self, cid):
        """Delete a component and every wire touching it."""
        self.comps.pop(cid, None)
        self.wires = [
            w for w in self.wires if cid != w[0] and cid != w[1]
        ]

    def count_gates(self):
        return sum(
            1 for c in self.comps.values() if c.kind in GATE_FUNCS
        )

    def source_of(self, dst, pin):
        for s, d, p in self.wires:
            if d == dst and p == pin:
                return s
        return None

    def disconnect(self, dst, pin):
        self.wires = [
            w for w in self.wires if not (w[1] == dst and w[2] == pin)
        ]

    def _depends_on(self, start, target):
        """True if `start` is fed COMBINATIONALLY by `target`.

        A D flip-flop's output is stored state, not a function of its
        input, so the search stops there. That is what makes feedback
        loops through flip-flops legal."""
        stack, seen = [start], set()
        while stack:
            cid = stack.pop()
            if self.comps[cid].kind == "DFF":
                continue
            if cid == target:
                return True
            if cid in seen:
                continue
            seen.add(cid)
            for pin in range(self.comps[cid].n_inputs):
                src = self.source_of(cid, pin)
                if src is not None:
                    stack.append(src)
        return False

    def connect(self, src, dst, pin):
        """Returns (ok, message)."""
        if src not in self.comps or dst not in self.comps:
            return False, "That component no longer exists."
        if not 0 <= pin < self.comps[dst].n_inputs:
            return False, "That input pin does not exist."
        if src == dst and self.comps[src].kind != "DFF":
            return False, "A component can't feed itself."
        if not self.comps[src].has_output:
            return False, "That part has no output."
        if src != dst and self._depends_on(src, dst):
            return False, "That would create a loop."
        self.disconnect(dst, pin)
        self.wires.append((src, dst, pin))
        return True, "Wire connected."

    def value(self, cid):
        """0/1 output of a component, or None if an input is unwired."""
        comp = self.comps[cid]
        if comp.kind in ("SWITCH", "SOURCE"):
            return comp.value
        if comp.kind == "DFF":
            return comp.state  # stored bit: never recurses into D

        inputs = []
        for pin in range(comp.n_inputs):
            src = self.source_of(cid, pin)
            if src is None:
                return None
            v = self.value(src)
            if v is None:
                return None
            inputs.append(v)

        if comp.kind == "LED":
            return inputs[0]
        return GATE_FUNCS[comp.kind](inputs)

    def truth_table(self, switch_ids, out_id):
        """Try every switch combination. Returns [(inputs, output)]."""
        saved = [self.comps[s].value for s in switch_ids]
        rows = []
        n = len(switch_ids)
        for combo in range(2 ** n):
            bits = tuple((combo >> (n - 1 - i)) & 1 for i in range(n))
            for s, b in zip(switch_ids, bits):
                self.comps[s].value = b
            rows.append((bits, self.value(out_id)))
        for s, v in zip(switch_ids, saved):
            self.comps[s].value = v
        return rows

    def truth_table_multi(self, switch_ids, out_ids):
        """Like truth_table, but checks several outputs at once.
        Returns [(input_bits, (out0, out1, ...))]; an output is None
        if something upstream of it is unwired."""
        saved = [self.comps[s].value for s in switch_ids]
        rows = []
        n = len(switch_ids)
        for combo in range(2 ** n):
            bits = tuple((combo >> (n - 1 - i)) & 1 for i in range(n))
            for s, b in zip(switch_ids, bits):
                self.comps[s].value = b
            rows.append((bits, tuple(self.value(o) for o in out_ids)))
        for s, v in zip(switch_ids, saved):
            self.comps[s].value = v
        return rows

    # ---- sequential logic ----

    def dffs(self):
        return [c for c in self.comps.values() if c.kind == "DFF"]

    def _ensure_history(self):
        ids = {f.id for f in self.dffs()}
        if set(self.history) != ids:
            self.history = {f.id: [f.state] for f in self.dffs()}

    def reset(self):
        """Every flip-flop goes back to its preset seed bit."""
        self.ticks = 0
        for f in self.dffs():
            f.state = f.init
        self.history = {f.id: [f.state] for f in self.dffs()}

    def clock(self):
        """One clock pulse: every flip-flop samples its D input at the
        same moment (all next values are computed BEFORE any flip-flop
        changes). Returns False if a D input is unwired."""
        ffs = self.dffs()
        if not ffs:
            return False
        self._ensure_history()

        nxt = {}
        for f in ffs:
            src = self.source_of(f.id, 0)
            v = None if src is None else self.value(src)
            if v is None:
                return False
            nxt[f.id] = v

        for f in ffs:
            f.state = nxt[f.id]
            self.history[f.id].append(f.state)
        self.ticks += 1
        return True

    def save_run(self):
        """Snapshot of the running state (for non-destructive checks)."""
        return (
            self.ticks,
            {f.id: f.state for f in self.dffs()},
            {k: list(v) for k, v in self.history.items()},
        )

    def restore_run(self, saved):
        ticks, states, history = saved
        self.ticks = ticks
        for f in self.dffs():
            f.state = states.get(f.id, f.init)
        self.history = history


# ------------------------------------------------------------
# Workbench (drawing + mouse)
# ------------------------------------------------------------

class Workbench:
    PIN = 10        # pin hit radius
    DRAG_PX = 5     # mouse travel that turns a click into a drag

    def __init__(self, circuit, allow_wiring=True, allow_placing=False,
                 allow_preset=False, allow_moving=False):
        self.circuit = circuit
        self.allow_wiring = allow_wiring
        self.allow_placing = allow_placing
        self.allow_preset = allow_preset
        self.allow_moving = allow_moving
        self.area = pygame.Rect(0, 0, 400, 200)
        self.mouse = (0, 0)
        self.drag_from = None
        self.drag_origin = (0, 0)
        self.moving = None          # id of the part being dragged
        self.press = None           # (id, pos) of a body press (click or drag)
        self.move_off = (0, 0)
        self._next_id = 1

    # ---- scaling helpers ----

    def _s(self):
        return getattr(self.circuit, "size_scale", 1.0)

    def _fs(self):
        return getattr(self.circuit, "font_scale", 1.0)

    def _size(self, comp):
        w, h = comp.size
        s = self._s()
        return (int(w * s), int(h * s))

    # ---- geometry ----

    def rect_of(self, comp):
        w, h = self._size(comp)
        cx = self.area.x + comp.rx * self.area.w
        cy = self.area.y + comp.ry * self.area.h
        return pygame.Rect(int(cx - w / 2), int(cy - h / 2), w, h)

    def in_pin(self, comp, i):
        r = self.rect_of(comp)
        n = comp.n_inputs
        return (r.left, int(r.top + r.h * (i + 1) / (n + 1)))

    def out_pin(self, comp):
        r = self.rect_of(comp)
        return (r.right, r.centery)

    def find_pin(self, pos):
        for comp in self.circuit.comps.values():
            if comp.has_output:
                ox, oy = self.out_pin(comp)
                if math.hypot(pos[0] - ox, pos[1] - oy) <= self.PIN:
                    return ("out", comp.id)
            for i in range(comp.n_inputs):
                ix, iy = self.in_pin(comp, i)
                if math.hypot(pos[0] - ix, pos[1] - iy) <= self.PIN:
                    return ("in", comp.id, i)
        return None

    def _gate_at(self, pos):
        """Topmost player-placed part under the mouse, or None."""
        for comp in reversed(list(self.circuit.comps.values())):
            if comp.deletable and self.rect_of(comp).collidepoint(pos):
                return comp
        return None

    def _body_at(self, pos):
        """Topmost part (any kind) under the mouse, or None."""
        for comp in reversed(list(self.circuit.comps.values())):
            if self.rect_of(comp).collidepoint(pos):
                return comp
        return None

    # ---- placing gates ----

    def spawn(self, kind, max_gates=None):
        """Add a gate from the palette. Returns a status message."""
        if max_gates is not None and self.circuit.count_gates() >= max_gates:
            return f"Gate limit reached ({max_gates}). Delete one first."

        spot = SPAWN_SLOTS[-1]
        for sx, sy in SPAWN_SLOTS:
            free = all(
                abs(c.rx - sx) >= 0.08 or abs(c.ry - sy) >= 0.14
                for c in self.circuit.comps.values()
            )
            if free:
                spot = (sx, sy)
                break

        while f"g{self._next_id}" in self.circuit.comps:
            self._next_id += 1
        cid = f"g{self._next_id}"
        self._next_id += 1

        self.circuit.add(
            Component(cid, kind, spot[0], spot[1], deletable=True)
        )
        return f"{kind} gate added. Drag it, then wire it."

    # ---- input ----

    def _connect(self, src, hit):
        ok, msg = self.circuit.connect(src, hit[1], hit[2])
        return msg

    def _click_comp(self, comp):
        """A plain click on a part's body (not a drag)."""
        if comp.kind == "SWITCH":
            comp.value ^= 1
            return f"Switch {comp.label} = {comp.value}"
        if comp.kind == "DFF" and self.allow_preset:
            if self.circuit.ticks > 0:
                return "Seed is locked while running. Press RESET."
            comp.init ^= 1
            self.circuit.reset()
            return f"Seed bit {comp.label} = {comp.init}"
        return ""

    def _drag_to(self, comp, pos):
        """Move `comp` so it follows the mouse, kept inside the bench
        (with room underneath for its caption)."""
        w, h = self._size(comp)
        cx = pos[0] - self.move_off[0]
        cy = pos[1] - self.move_off[1]
        lo_x = (w / 2 + 4) / self.area.w
        lo_y = (h / 2 + 4) / self.area.h
        bottom_pad = 26 if self.allow_moving else 4
        hi_y = 1 - (h / 2 + bottom_pad) / self.area.h
        hi_y = max(hi_y, lo_y)
        comp.rx = min(max((cx - self.area.x) / self.area.w, lo_x), 1 - lo_x)
        comp.ry = min(max((cy - self.area.y) / self.area.h, lo_y), hi_y)

    def handle_event(self, event):
        """Returns a short status message (or "")."""
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos

            # A body press turns into a drag once the mouse travels a bit.
            if self.press is not None and self.moving is None:
                px, py = self.press[1]
                if math.hypot(event.pos[0] - px,
                              event.pos[1] - py) > self.DRAG_PX:
                    self.moving = self.press[0]

            if self.moving in self.circuit.comps and self.area.w > 0:
                self._drag_to(self.circuit.comps[self.moving], event.pos)
            return ""

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            self.mouse = pos
            hit = self.find_pin(pos) if self.allow_wiring else None

            if event.button == 3:
                self.drag_from = None
                self.moving = None
                self.press = None
                if hit and hit[0] == "in":
                    self.circuit.disconnect(hit[1], hit[2])
                    return "Wire removed."
                if self.allow_placing and not hit:
                    comp = self._gate_at(pos)
                    if comp is not None:
                        self.circuit.remove(comp.id)
                        return f"{comp.kind} gate deleted."
                return ""

            if event.button != 1:
                return ""

            if self.drag_from is not None:
                src = self.drag_from
                self.drag_from = None
                if hit and hit[0] == "in":
                    return self._connect(src, hit)

            if hit and hit[0] == "out":
                self.drag_from = hit[1]
                self.drag_origin = pos
                return "Now drop it on an INPUT pin (left side of a part)."

            if hit and hit[0] == "in":
                src = self.circuit.source_of(hit[1], hit[2])
                if src is not None:
                    self.circuit.disconnect(hit[1], hit[2])
                    self.drag_from = src
                    self.drag_origin = pos
                    return "Wire picked up. Drop it on another input pin."

            if self.allow_placing:
                comp = self._gate_at(pos)
                if comp is not None:
                    r = self.rect_of(comp)
                    self.moving = comp.id
                    self.move_off = (pos[0] - r.centerx, pos[1] - r.centery)
                    return ""

            if self.allow_moving:
                comp = self._body_at(pos)
                if comp is not None:
                    r = self.rect_of(comp)
                    self.press = (comp.id, pos)
                    self.move_off = (pos[0] - r.centerx, pos[1] - r.centery)
                    return ""

            for comp in self.circuit.comps.values():
                if self.rect_of(comp).collidepoint(pos):
                    msg = self._click_comp(comp)
                    if msg:
                        return msg
            return ""

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Released a body press: either a click or the end of a drag.
            if self.press is not None:
                pid = self.press[0]
                was_dragging = self.moving is not None
                self.press = None
                self.moving = None
                if not was_dragging and pid in self.circuit.comps:
                    return self._click_comp(self.circuit.comps[pid])
                return ""

            if self.moving is not None:
                self.moving = None
                return ""

            if self.drag_from is not None:
                hit = self.find_pin(event.pos)
                if hit and hit[0] == "in":
                    src = self.drag_from
                    self.drag_from = None
                    return self._connect(src, hit)
                moved = math.hypot(
                    event.pos[0] - self.drag_origin[0],
                    event.pos[1] - self.drag_origin[1],
                )
                if moved > 8:
                    self.drag_from = None  # dropped on empty space
                # otherwise: click-click mode, keep waiting for the target
        return ""

    # ---- drawing ----

    def draw(self, screen, ticks=0):
        pygame.draw.rect(screen, AREA_BG, self.area)
        pygame.draw.rect(screen, CYAN_DIM, self.area, 2)

        old_clip = screen.get_clip()
        screen.set_clip(self.area)

        # grid dots
        for gx in range(self.area.x + 12, self.area.right, 24):
            for gy in range(self.area.y + 12, self.area.bottom, 24):
                screen.set_at((gx, gy), (22, 45, 62))

        self._draw_wires(screen)

        for comp in self.circuit.comps.values():
            self._draw_component(screen, comp)

        if self.drag_from is not None:
            src = self.circuit.comps[self.drag_from]
            pygame.draw.line(
                screen, YELLOW, self.out_pin(src), self.mouse, 3
            )

        screen.set_clip(old_clip)

    def _channel_y(self, spec, y0, y1):
        if spec is None:
            return y0                      # run along the source's height
        if spec == "DST":
            return y1                      # run along the target's height
        return int(self.area.y + spec * self.area.h)

    # ---- automatic wire routing ----
    #
    # Every wire is a polyline of horizontal/vertical pieces. The router
    # keeps lists of the pieces already placed this frame and refuses to
    # reuse a lane where a wire from a DIFFERENT output would lie on top
    # of them. It also refuses lanes that cut through a part or the
    # caption under it. Wires from the same output may share a stub.

    def _obstacle(self, comp):
        """A part's rectangle, padded, with extra room below for its
        caption (so channels never run through the text)."""
        r = self.rect_of(comp)
        return pygame.Rect(r.x - 6, r.y - 6, r.w + 12, r.h + 12 + 20)

    def _h_free(self, y, xa, xb, skip=()):
        lo, hi = (xa, xb) if xa <= xb else (xb, xa)
        for comp in self.circuit.comps.values():
            if comp.id in skip:
                continue
            r = self._obstacle(comp)
            if r.top <= y <= r.bottom and r.right >= lo and r.left <= hi:
                return False
        return True

    def _v_free(self, x, ya, yb, skip=()):
        lo, hi = (ya, yb) if ya <= yb else (yb, ya)
        for comp in self.circuit.comps.values():
            if comp.id in skip:
                continue
            r = self._obstacle(comp)
            if r.left <= x <= r.right and r.bottom >= lo and r.top <= hi:
                return False
        return True

    @staticmethod
    def _h_clash(used, y, xa, xb, src):
        lo, hi = (xa, xb) if xa <= xb else (xb, xa)
        for uy, ulo, uhi, usrc in used:
            if usrc != src and abs(uy - y) < 7 and uhi >= lo and ulo <= hi:
                return True
        return False

    @staticmethod
    def _v_clash(used, x, ya, yb, src):
        lo, hi = (ya, yb) if ya <= yb else (yb, ya)
        for ux, ulo, uhi, usrc in used:
            if usrc != src and abs(ux - x) < 7 and uhi >= lo and ulo <= hi:
                return True
        return False

    @staticmethod
    def _clean(pts):
        out = [pts[0]]
        for p in pts[1:]:
            if p != out[-1]:
                out.append(p)
        return out

    def _record(self, pts, src, used_h, used_v):
        for a, b in zip(pts, pts[1:]):
            if a[1] == b[1]:
                used_h.append((a[1], min(a[0], b[0]), max(a[0], b[0]), src))
            elif a[0] == b[0]:
                used_v.append((a[0], min(a[1], b[1]), max(a[1], b[1]), src))

    def _auto_route(self, src_id, dst_id, p0, p1, used_h, used_v):
        x0, y0 = p0
        x1, y1 = p1
        skip = (src_id, dst_id)

        # 1) dead straight if nothing is in the way
        if (abs(y0 - y1) < 2 and x1 > x0 + 4
                and self._h_free(y0, x0 + 4, x1 - 4, skip)
                and not self._h_clash(used_h, y0, x0, x1, src_id)):
            return [p0, p1]

        # 2) forward wire: one vertical jog in a free column
        if x1 >= x0 + 30:
            mid = (x0 + x1) // 2
            for step in range(0, 200, 8):
                for xm in ((mid,) if step == 0 else (mid + step, mid - step)):
                    if not (x0 + 10 <= xm <= x1 - 10):
                        continue
                    if not self._v_free(xm, y0, y1, skip):
                        continue
                    if self._v_clash(used_v, xm, y0, y1, src_id):
                        continue
                    if self._h_clash(used_h, y0, x0, xm, src_id):
                        continue
                    if self._h_clash(used_h, y1, xm, x1, src_id):
                        continue
                    if not self._h_free(y0, x0 + 4, xm, skip):
                        continue
                    if not self._h_free(y1, xm, x1 - 4, skip):
                        continue
                    return self._clean([p0, (xm, y0), (xm, y1), p1])

        # 3) backward / blocked wire: out of the pin, along a free
        #    channel, in from the left
        lane_out = x0 + 14
        for _ in range(12):
            if not self._v_clash(used_v, lane_out, y0, y0 + 1, src_id):
                break
            lane_out += 8
        lane_in = x1 - 14
        for _ in range(12):
            if not self._v_clash(used_v, lane_in, y1, y1 + 1, dst_id):
                break
            lane_in -= 8

        pref = (y0 + y1) // 2
        ys = sorted(
            range(self.area.y + 10, self.area.bottom - 8, 6),
            key=lambda yy: abs(yy - pref),
        )
        best = None
        for ych in ys:
            xa, xb = lane_out, lane_in
            if not self._h_free(ych, xa, xb):
                continue
            if self._h_clash(used_h, ych, xa, xb, src_id):
                continue
            if not self._v_free(lane_out, y0, ych, skip):
                continue
            if not self._v_free(lane_in, ych, y1, skip):
                continue
            if self._v_clash(used_v, lane_out, y0, ych, src_id):
                continue
            if self._v_clash(used_v, lane_in, ych, y1, dst_id):
                continue
            best = ych
            break
        if best is None:
            best = pref
        return self._clean([
            p0, (lane_out, y0), (lane_out, best),
            (lane_in, best), (lane_in, y1), p1,
        ])

    def _draw_wires(self, screen):
        channels = getattr(self.circuit, "channels", {})
        fixed = getattr(self.circuit, "wire_colour", None)
        auto = getattr(self.circuit, "auto_route", False)
        used_h, used_v = [], []

        for src_id, dst_id, pin in self.circuit.wires:
            src = self.circuit.comps[src_id]
            dst = self.circuit.comps[dst_id]
            x0, y0 = self.out_pin(src)
            x1, y1 = self.in_pin(dst, pin)

            if fixed is not None:
                colour = fixed
            else:
                v = self.circuit.value(src_id)
                colour = GREY if v is None else (
                    GREEN if v else (60, 130, 160))

            key = (src_id, dst_id, pin)
            if key in channels:
                # Hand-routed wire: private channel + private lanes so no
                # two wires ever run on top of each other.
                ch = self._channel_y(channels[key], y0, y1)
                pts = route_wire((x0, y0), (x1, y1), ch, pin)
                draw_wire(screen, pts, colour, 3)
                continue

            if auto:
                pts = self._auto_route(
                    src_id, dst_id, (x0, y0), (x1, y1), used_h, used_v
                )
                self._record(pts, src_id, used_h, used_v)
                draw_wire(screen, pts, colour, 3)
                continue

            if x1 >= x0 + 24:
                xm = (x0 + x1) // 2
                pts = [(x0, y0), (xm, y0), (xm, y1), (x1, y1)]
            else:
                # Feedback / backward wire: leave to the right, run along
                # a lane between the rows, come in from the left.
                if abs(y0 - y1) < 40:
                    ym = max(y0, y1) + 50
                else:
                    ym = (y0 + y1) // 2
                pts = [
                    (x0, y0), (x0 + 14, y0), (x0 + 14, ym),
                    (x1 - 14, ym), (x1 - 14, y1), (x1, y1),
                ]
            pygame.draw.lines(screen, colour, False, pts, 4)

    def _draw_pin(self, screen, pos, wired, hover):
        colour = YELLOW if hover else (CYAN if wired else GREY)
        p = max(5, int(10 * self._s()))
        pygame.draw.rect(
            screen, colour, (pos[0] - p // 2, pos[1] - p // 2, p, p)
        )

    def _draw_component(self, screen, comp):
        r = self.rect_of(comp)
        value = self.circuit.value(comp.id)
        hover = self.find_pin(self.mouse)
        s = self._s()
        fs = self._fs()
        dragging = self.moving == comp.id

        if comp.kind == "SWITCH":
            on = comp.value == 1
            pygame.draw.rect(screen, GREEN if on else BOX_FILL, r)
            pygame.draw.rect(
                screen, YELLOW if dragging else (WHITE if on else CYAN_DIM),
                r, 3,
            )
            text = _font(18 * fs).render(
                f"{comp.label} = {comp.value}", False,
                (4, 20, 30) if on else WHITE,
            )
            screen.blit(text, text.get_rect(center=r.center))

        elif comp.kind == "SOURCE":
            on = comp.value == 1
            pygame.draw.rect(screen, (60, 45, 15) if on else BOX_FILL, r)
            pygame.draw.rect(screen, YELLOW if dragging else ORANGE, r, 3)
            text = _font(15 * fs).render(
                f"{comp.label} = {comp.value}", False,
                YELLOW if on else WHITE,
            )
            screen.blit(text, text.get_rect(center=r.center))

        elif comp.kind == "DFF":
            on = comp.state == 1
            pygame.draw.rect(
                screen, (12, 62, 46) if on else BOX_FILL, r
            )
            pygame.draw.rect(
                screen, YELLOW if dragging else (GREEN if on else CYAN),
                r, 3,
            )
            title = _font(14 * fs).render(comp.label or "D-FF", False, ORANGE)
            screen.blit(
                title, title.get_rect(center=(r.centerx, r.top + int(13 * s)))
            )
            q = _font(26 * fs).render(
                str(comp.state), False, GREEN if on else WHITE
            )
            screen.blit(
                q, q.get_rect(center=(r.centerx, r.centery + int(6 * s)))
            )
            d_lbl = _font(12 * fs).render("D", False, GREY)
            q_lbl = _font(12 * fs).render("Q", False, GREY)
            off = int(11 * s)
            screen.blit(d_lbl, d_lbl.get_rect(center=(r.left + off, r.centery)))
            screen.blit(q_lbl, q_lbl.get_rect(center=(r.right - off, r.centery)))
            # clock-edge triangle (all flip-flops share one clock)
            t = max(4, int(7 * s))
            pygame.draw.polygon(
                screen, CYAN,
                [(r.centerx - t, r.bottom - 2), (r.centerx + t, r.bottom - 2),
                 (r.centerx, r.bottom - 2 - int(10 * s))], 2,
            )

        elif comp.kind == "LED":
            lit = value == 1
            centre = r.center
            if lit:
                pygame.draw.circle(screen, (110, 60, 20), centre,
                                   int(33 * s))
            pygame.draw.circle(
                screen, YELLOW if lit else (45, 38, 40), centre, int(26 * s)
            )
            pygame.draw.circle(
                screen, YELLOW if dragging else WHITE, centre,
                int(26 * s), 3,
            )
            if value is None:
                text = _font(14 * fs).render("?", False, GREY)
                screen.blit(text, text.get_rect(center=centre))

        else:  # gate
            colour = YELLOW if dragging else CYAN
            draw_pixel_gate_symbol(screen, comp.kind, r, colour)

        if comp.sub:
            sub = _font(12 * fs).render(comp.sub, False, GREY)
            screen.blit(sub, sub.get_rect(midtop=(r.centerx, r.bottom + 5)))
        elif comp.kind == "LED" and comp.label:
            sub = _font(12 * fs).render(comp.label, False, GREY)
            screen.blit(sub, sub.get_rect(midtop=(r.centerx, r.bottom + 5)))

        # pins
        if comp.has_output:
            pos = self.out_pin(comp)
            wired = any(w[0] == comp.id for w in self.circuit.wires)
            self._draw_pin(
                screen, pos, wired, hover == ("out", comp.id)
            )
        for i in range(comp.n_inputs):
            pos = self.in_pin(comp, i)
            wired = self.circuit.source_of(comp.id, i) is not None
            self._draw_pin(
                screen, pos, wired, hover == ("in", comp.id, i)
            )