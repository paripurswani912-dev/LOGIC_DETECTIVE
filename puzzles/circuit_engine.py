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
# NEW for sequential circuits (Level 6+):
#   - "DFF" component: D input, Q output, shared implicit clock.
#   - circuit.clock() ............ updates ALL flip-flops at once.
#   - Flip-flops break combinational loops, so feedback wires
#     (Q5 -> XOR -> D1) are legal.
#   - allow_preset=True .......... click a flip-flop to set its seed bit
#     (only before the first clock pulse).
#   - circuit.history ............ Q value of every flip-flop per tick,
#     used for the timing diagram.
#   - "SOURCE" component: a read-only input whose value the level sets
#     from code (e.g. the ciphertext bit stream).

import math
import pygame

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
            if cid == target:
                return True
            if cid in seen:
                continue
            seen.add(cid)
            if self.comps[cid].kind == "DFF":
                continue
            for pin in range(self.comps[cid].n_inputs):
                src = self.source_of(cid, pin)
                if src is not None:
                    stack.append(src)
        return False

    def connect(self, src, dst, pin):
        """Returns (ok, message)."""
        if src == dst and self.comps[src].kind != "DFF":
            return False, "A component can't feed itself."
        if not self.comps[src].has_output:
            return False, "That part has no output."
        if self._depends_on(src, dst):
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
    PIN = 10  # pin hit radius

    def __init__(self, circuit, allow_wiring=True, allow_placing=False,
                 allow_preset=False):
        self.circuit = circuit
        self.allow_wiring = allow_wiring
        self.allow_placing = allow_placing
        self.allow_preset = allow_preset
        self.area = pygame.Rect(0, 0, 400, 200)
        self.mouse = (0, 0)
        self.drag_from = None
        self.drag_origin = (0, 0)
        self.moving = None          # id of the gate being dragged
        self.move_off = (0, 0)
        self._next_id = 1

    # ---- geometry ----

    def rect_of(self, comp):
        w, h = comp.size
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

    def handle_event(self, event):
        """Returns a short status message (or "")."""
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            if self.moving in self.circuit.comps and self.area.w > 0:
                comp = self.circuit.comps[self.moving]
                w, h = comp.size
                cx = event.pos[0] - self.move_off[0]
                cy = event.pos[1] - self.move_off[1]
                lo_x = (w / 2 + 4) / self.area.w
                lo_y = (h / 2 + 4) / self.area.h
                comp.rx = min(max((cx - self.area.x) / self.area.w, lo_x),
                              1 - lo_x)
                comp.ry = min(max((cy - self.area.y) / self.area.h, lo_y),
                              1 - lo_y)
            return ""

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            self.mouse = pos
            hit = self.find_pin(pos) if self.allow_wiring else None

            if event.button == 3:
                self.drag_from = None
                self.moving = None
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

            for comp in self.circuit.comps.values():
                if not self.rect_of(comp).collidepoint(pos):
                    continue
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

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
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

    def _draw_wires(self, screen):
        for src_id, dst_id, pin in self.circuit.wires:
            src = self.circuit.comps[src_id]
            dst = self.circuit.comps[dst_id]
            x0, y0 = self.out_pin(src)
            x1, y1 = self.in_pin(dst, pin)
            v = self.circuit.value(src_id)
            colour = GREY if v is None else (GREEN if v else (60, 130, 160))

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
        pygame.draw.rect(screen, colour, (pos[0] - 5, pos[1] - 5, 10, 10))

    def _draw_component(self, screen, comp):
        r = self.rect_of(comp)
        value = self.circuit.value(comp.id)
        hover = self.find_pin(self.mouse)

        if comp.kind == "SWITCH":
            on = comp.value == 1
            pygame.draw.rect(screen, GREEN if on else BOX_FILL, r)
            pygame.draw.rect(screen, WHITE if on else CYAN_DIM, r, 3)
            text = _font(18).render(
                f"{comp.label} = {comp.value}", False,
                (4, 20, 30) if on else WHITE,
            )
            screen.blit(text, text.get_rect(center=r.center))

        elif comp.kind == "SOURCE":
            on = comp.value == 1
            pygame.draw.rect(screen, (60, 45, 15) if on else BOX_FILL, r)
            pygame.draw.rect(screen, ORANGE, r, 3)
            text = _font(15).render(
                f"{comp.label} {comp.value}", False,
                YELLOW if on else WHITE,
            )
            screen.blit(text, text.get_rect(center=r.center))

        elif comp.kind == "DFF":
            on = comp.state == 1
            pygame.draw.rect(
                screen, (12, 62, 46) if on else BOX_FILL, r
            )
            pygame.draw.rect(screen, GREEN if on else CYAN, r, 3)
            title = _font(14).render(comp.label or "D-FF", False, ORANGE)
            screen.blit(title, title.get_rect(center=(r.centerx, r.top + 13)))
            q = _font(26).render(
                str(comp.state), False, GREEN if on else WHITE
            )
            screen.blit(q, q.get_rect(center=(r.centerx, r.centery + 6)))
            d_lbl = _font(12).render("D", False, GREY)
            q_lbl = _font(12).render("Q", False, GREY)
            screen.blit(d_lbl, d_lbl.get_rect(center=(r.left + 11, r.centery)))
            screen.blit(q_lbl, q_lbl.get_rect(center=(r.right - 11, r.centery)))
            # clock-edge triangle (all flip-flops share one clock)
            pygame.draw.polygon(
                screen, CYAN,
                [(r.centerx - 7, r.bottom - 2), (r.centerx + 7, r.bottom - 2),
                 (r.centerx, r.bottom - 12)], 2,
            )

        elif comp.kind == "LED":
            lit = value == 1
            centre = r.center
            if lit:
                pygame.draw.circle(screen, (110, 60, 20), centre, 33)
            pygame.draw.circle(
                screen, YELLOW if lit else (45, 38, 40), centre, 26
            )
            pygame.draw.circle(screen, WHITE, centre, 26, 3)
            if value is None:
                text = _font(14).render("?", False, GREY)
                screen.blit(text, text.get_rect(center=centre))

        else:  # gate
            border = YELLOW if self.moving == comp.id else CYAN
            pygame.draw.rect(screen, BOX_FILL, r)
            pygame.draw.rect(screen, border, r, 3)
            text = _font(20).render(comp.kind, False, ORANGE)
            screen.blit(text, text.get_rect(center=r.center))

        if comp.sub:
            sub = _font(12).render(comp.sub, False, GREY)
            screen.blit(sub, sub.get_rect(midtop=(r.centerx, r.bottom + 6)))
        elif comp.kind == "LED" and comp.label:
            sub = _font(12).render(comp.label, False, GREY)
            screen.blit(sub, sub.get_rect(midtop=(r.centerx, r.bottom + 6)))

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