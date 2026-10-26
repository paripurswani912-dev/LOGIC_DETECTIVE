# puzzles/comb_lab.py
# COMBINATIONAL CIRCUITS - shared engine, simulators and notebook lab.
#
# Used by two things:
#   * NOTEBOOK > TEST THE LOGIC > COMBINATIONAL CIRCUITS  (both paths)
#   * puzzles/basic_comb.py  (BASIC Level 5 course)
#
# Everything here is plain pygame and text, no images.  Each simulator has
#   - a PURPOSE sentence (what is it for?)
#   - input switches the player flips (mouse or number keys)
#   - a drawn circuit whose wires light up
#   - a truth table (current row highlighted) or a plain-words readout
#   - notes (formulas, minterm lists "Sum m(...)")
#
# Notebook keys:  LEFT / RIGHT = previous / next circuit,
#                 1-9, 0, - = flip that input,  R = reset inputs,  T = notes

import itertools

import pygame

# ------------------------------------------------------------------
# PALETTES (the lab is drawn on paper, the course on the dark panel)
# ------------------------------------------------------------------
DARK = {
    "bg": (15, 31, 47), "ink": (240, 244, 248), "dim": (128, 146, 162),
    "wire_on": (70, 235, 130), "wire_off": (78, 98, 118), "wire_unk": (110, 140, 175),
    "bulb_on": (255, 218, 92), "bulb_off": (36, 46, 60), "bulb_edge": (200, 210, 220),
    "sw_on": (22, 80, 52), "sw_off": (36, 44, 58), "sw_edge_on": (70, 235, 130),
    "sw_edge_off": (128, 146, 162), "knob": (240, 244, 248),
    "accent": (255, 214, 86), "good": (70, 235, 130), "bad": (240, 90, 90),
    "row_hl": (36, 78, 62), "head": (30, 60, 84), "cell": (22, 38, 54),
    "slot": (255, 214, 86),
}
PAPER = {
    "bg": (190, 194, 198), "ink": (35, 29, 31), "dim": (105, 111, 119),
    "wire_on": (30, 120, 70), "wire_off": (135, 141, 148), "wire_unk": (110, 120, 135),
    "bulb_on": (255, 205, 40), "bulb_off": (120, 126, 134), "bulb_edge": (35, 29, 31),
    "sw_on": (170, 214, 182), "sw_off": (205, 208, 210), "sw_edge_on": (30, 92, 58),
    "sw_edge_off": (35, 29, 31), "knob": (35, 29, 31),
    "accent": (0, 91, 103), "good": (30, 92, 58), "bad": (112, 35, 48),
    "row_hl": (176, 212, 190), "head": (160, 168, 176), "cell": (215, 217, 218),
    "slot": (0, 91, 103),
}


# ------------------------------------------------------------------
# GATE LOGIC (n inputs, None = unknown)
# ------------------------------------------------------------------
def gate_eval(gate, bits):
    if any(b is None for b in bits):
        return None
    if gate == "NOT":
        return 1 - bits[0]
    if gate == "AND":
        return int(all(bits))
    if gate == "OR":
        return int(any(bits))
    if gate == "NAND":
        return 1 - int(all(bits))
    if gate == "NOR":
        return 1 - int(any(bits))
    if gate == "XOR":
        return sum(bits) & 1
    if gate == "XNOR":
        return 1 - (sum(bits) & 1)
    raise ValueError(gate)


# ------------------------------------------------------------------
# GATE SYMBOLS (n input pins)
# ------------------------------------------------------------------
def _bez(p0, p1, p2, steps=14):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def pin_ys(rect, n, gate="AND"):
    x, y, w, h = rect
    if gate == "NOT" or n == 1:
        return [y + h // 2]
    return [y + int(h * (i + 1) / (n + 1)) for i in range(n)]


def draw_gate_n(screen, gate, rect, color, n=2, stroke=2, bg=None):
    """Standard gate symbol with n input pins on the left edge of rect."""
    x, y, w, h = [int(v) for v in rect]
    mid = y + h // 2
    top = y + int(h * 0.12)
    bot = y + int(h * 0.88)
    inv = gate in ("NAND", "NOR", "XNOR", "NOT")
    bubble = max(6, stroke * 2 + 2)
    out_len = max(5, int(w * 0.12))
    gap = max(4, int(w * 0.07)) if gate in ("XOR", "XNOR") else 0
    left = x + int(w * 0.14) + gap
    right = x + w - out_len - (bubble if inv else 0)
    bw = max(10, right - left)
    pins = pin_ys((x, y, w, h), n, gate)

    def ln(p, q):
        pygame.draw.line(screen, color, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), stroke)

    def poly(points, close=False):
        pts = [(int(a), int(b)) for a, b in points]
        pygame.draw.lines(screen, color, close, pts, stroke)

    def fill(points):
        if bg is not None:
            pygame.draw.polygon(screen, bg, [(int(a), int(b)) for a, b in points])

    if gate == "NOT":
        tri = [(left, top), (right, mid), (left, bot)]
        fill(tri)
        poly(tri, True)
        ln((x, mid), (left, mid))
    elif gate in ("AND", "NAND"):
        xc = left + bw * 0.5
        upper = _bez((xc, top), (right, top), (right, mid))
        lower = _bez((right, mid), (right, bot), (xc, bot))
        body = [(left, top)] + upper + lower[1:] + [(left, bot)]
        fill(body)
        poly(body, True)
        for py in pins:
            ln((x, py), (left, py))
    else:
        depth = bw * 0.36

        def back(base):
            return _bez((base, top), (base + depth, mid), (base, bot))

        def back_x(base, yy):
            t = (yy - top) / float(bot - top)
            t = max(0.0, min(1.0, t))
            return base + 2 * t * (1 - t) * depth

        up = _bez((left, top), (left + bw * 0.55, top), (right, mid))
        lo = _bez((right, mid), (left + bw * 0.55, bot), (left, bot))
        bk = back(left)
        fill(up + lo[1:] + list(reversed(bk)))
        poly(up)
        poly(lo)
        poly(bk)
        base = left
        if gate in ("XOR", "XNOR"):
            base = left - gap
            poly(back(base))
        for py in pins:
            ln((x, py), (back_x(base, py), py))
    if inv:
        pygame.draw.circle(screen, color, (right + bubble // 2, mid), bubble // 2, max(1, stroke - 1))
        ln((right + bubble, mid), (x + w, mid))
    else:
        ln((right, mid), (x + w, mid))


# ------------------------------------------------------------------
# NETLISTS
# ------------------------------------------------------------------
def IN(name, y, x=0):
    return {"name": name, "x": x, "y": y}


def G(nid, gate, ins, x, y, label=None):
    return {"id": nid, "type": gate, "ins": list(ins), "x": x, "y": y, "label": label}


def BOX(nid, label, ins, outs, fn, x, y, h=3):
    return {"id": nid, "type": "BOX", "ins": list(ins), "outs": list(outs), "fn": fn,
            "x": x, "y": y, "h": h, "label": label}


def OUT(name, ref, x, y):
    return {"name": name, "ref": ref, "x": x, "y": y}


class Net:
    def __init__(self, inputs, nodes, outputs):
        self.inputs, self.nodes, self.outputs = inputs, nodes, outputs
        self.by_id = {n["id"]: n for n in nodes}

    def evaluate(self, invals, types=None):
        """Return {ref: bit or None}. types overrides node gate types (None = hidden)."""
        types = types or {}
        vals = dict(invals)

        def get(ref):
            if ref in vals:
                return vals[ref]
            nid = ref.split(".")[0]
            node = self.by_id[nid]
            ins = [get(r) for r in node["ins"]]
            if node["type"] == "BOX":
                if any(b is None for b in ins):
                    res = [None] * len(node["outs"])
                else:
                    res = list(node["fn"](*ins))
                for pin, v in zip(node["outs"], res):
                    vals[nid + "." + pin] = v
                return vals[ref]
            gate = types.get(nid, node["type"])
            vals[nid] = None if gate is None else gate_eval(gate, ins)
            return vals[nid]

        for n in self.nodes:
            if n["type"] == "BOX":
                get(n["id"] + "." + n["outs"][0])
            else:
                get(n["id"])
        return vals

    def out_values(self, invals, types=None):
        vals = self.evaluate(invals, types)
        return {o["name"]: vals[o["ref"]] for o in self.outputs}


# ------------------------------------------------------------------
# DRAWING THE NETLIST
# ------------------------------------------------------------------
def _bulb(screen, cx, cy, r, v, pal):
    if v is None:
        pygame.draw.circle(screen, pal["bg"], (cx, cy), r)
        pygame.draw.circle(screen, pal["wire_unk"], (cx, cy), r, 2)
        return
    if v:
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 214, 80, 70), (r * 2, r * 2), int(r * 1.7))
        screen.blit(glow, (cx - r * 2, cy - r * 2))
    pygame.draw.circle(screen, pal["bulb_on"] if v else pal["bulb_off"], (cx, cy), r)
    pygame.draw.circle(screen, pal["bulb_edge"], (cx, cy), r, 2)


def _switch(screen, cx, cy, value, pal, w=40, h=20):
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (cx, cy)
    pygame.draw.rect(screen, pal["sw_on"] if value else pal["sw_off"], rect, border_radius=h // 2)
    pygame.draw.rect(screen, pal["sw_edge_on"] if value else pal["sw_edge_off"], rect, 2,
                     border_radius=h // 2)
    kx = rect.right - h // 2 if value else rect.left + h // 2
    pygame.draw.circle(screen, pal["knob"], (kx, cy), h // 2 - 3)
    return rect


def _text(screen, font, txt, color, **place):
    img = font.render(str(txt), True, color)
    screen.blit(img, img.get_rect(**place))
    return img


def wrap(font, text, width):
    words, lines, cur = text.split(), [], ""
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


def _wire_col(v, pal):
    return pal["wire_unk"] if v is None else (pal["wire_on"] if v else pal["wire_off"])


def draw_net(screen, net, area, vals, pal, fonts, hits=None, types=None,
             mask_outputs=False, in_keys=True, out_labels=True, slot_hover=None,
             on_dot=True):
    """Draw net into area.  vals = net.evaluate(...) result.  Returns {node_id: rect}."""
    f_small, f_tiny = fonts["small"], fonts["tiny"]
    types = types or {}
    ents = list(net.inputs) + list(net.nodes) + list(net.outputs)
    xs = [e["x"] for e in ents]
    ys = [e["y"] for e in ents]
    for n in net.nodes:
        if n["type"] == "BOX":
            ys.append(n["y"] - n["h"] / 2.0)
            ys.append(n["y"] + n["h"] / 2.0)
    C = max(xs) + 1
    ymin, ymax = min(ys), max(ys)
    rows = (ymax - ymin) + 1.0
    padx, pady = 10, 12
    colw = min((area.w - 2 * padx) / C, 120)
    rowh = min((area.h - 2 * pady) / rows, 74)
    ox = area.x + (area.w - colw * C) / 2.0
    oy = area.y + (area.h - rowh * rows) / 2.0
    gw = max(26, min(colw * 0.5, 62))
    gh0 = max(16, min(rowh * 0.78, 40))

    def cx(x):
        return ox + (x + 0.5) * colw

    def cy(y):
        return oy + (y - ymin + 0.5) * rowh

    # ---- geometry of every node --------------------------------------
    geo = {}
    for n in net.nodes:
        if n["type"] == "BOX":
            bw, bh = max(gw * 2.1, 92), rowh * n["h"]
            r = pygame.Rect(0, 0, bw, bh)
            r.center = (cx(n["x"]), cy(n["y"]))
            m = len(n["ins"])
            ins = [(r.x, r.y + bh * (i + 1) / (m + 1)) for i in range(m)]
            k = len(n["outs"])
            outs = {p: (r.right, r.y + bh * (i + 1) / (k + 1)) for i, p in enumerate(n["outs"])}
            geo[n["id"]] = {"rect": r, "ins": ins, "outs": outs}
        else:
            k = len(n["ins"])
            h = gh0 * (1 + 0.28 * (k - 2)) if k > 2 else gh0
            r = pygame.Rect(0, 0, gw, h)
            r.center = (cx(n["x"]), cy(n["y"]))
            ys_ = pin_ys(r, k, n["type"] if n["type"] != "?" else "AND")
            geo[n["id"]] = {"rect": r, "ins": [(r.x, py) for py in ys_],
                            "outs": {"": (r.right, r.centery)}}
    sw_w = min(40, colw * 0.7)
    src_pt = {}
    for i in net.inputs:
        px, py = cx(i["x"]), cy(i["y"])
        src_pt[i["name"]] = (px + sw_w / 2.0 + 2, py)
    for n in net.nodes:
        if n["type"] == "BOX":
            for p, pt in geo[n["id"]]["outs"].items():
                src_pt[n["id"] + "." + p] = pt
        else:
            src_pt[n["id"]] = geo[n["id"]]["outs"][""]

    # ---- edges: (src_ref, dst_x, dst_y, dst_col) ------------------------
    edges = []
    for n in net.nodes:
        for pt, ref in zip(geo[n["id"]]["ins"], n["ins"]):
            edges.append((ref, pt[0], pt[1], n["x"]))
    out_pt = {}
    for o in net.outputs:
        bx, by = cx(o["x"]) - 14, cy(o["y"])
        out_pt[o["name"]] = (bx, by)
        edges.append((o["ref"], bx - 10, by, o["x"]))

    # trunk x per (dst column, src): spread the vertical runs inside the channel
    chan = {}
    for ref, dx, dy, dc in edges:
        chan.setdefault(dc, [])
        if ref not in chan[dc]:
            chan[dc].append(ref)
    trunk_x = {}
    for dc, refs in chan.items():
        refs.sort(key=lambda r: src_pt[r][1])
        k = len(refs)
        left_edge = cx(dc) - gw / 2.0 - 4
        if dc == C - 1:
            left_edge = cx(dc) - 32
        span = max(8.0, colw - gw - 14)
        step = min(7.0, span / max(1, k))
        for idx, ref in enumerate(refs):
            trunk_x[(dc, ref)] = left_edge - 4 - step * idx

    # ---- wires --------------------------------------------------------
    groups = {}
    for ref, dx, dy, dc in edges:
        groups.setdefault((dc, ref), []).append((dx, dy))
    for (dc, ref), dests in groups.items():
        p = src_pt[ref]
        tx = min(trunk_x[(dc, ref)], min(d[0] for d in dests) - 3)
        tx = max(tx, p[0] + 3)
        col = _wire_col(vals.get(ref), pal)
        ys_ = [p[1]] + [d[1] for d in dests]
        pygame.draw.line(screen, col, (p[0], p[1]), (tx, p[1]), 2)
        if max(ys_) - min(ys_) > 0.5:
            pygame.draw.line(screen, col, (tx, min(ys_)), (tx, max(ys_)), 2)
        for dx, dy in dests:
            pygame.draw.line(screen, col, (tx, dy), (dx, dy), 2)
            if len(dests) > 1 and abs(dy - p[1]) > 0.5 and on_dot:
                pygame.draw.circle(screen, col, (int(tx), int(dy)), 3)
        if len(dests) > 1 or abs(dests[0][1] - p[1]) > 0.5:
            if on_dot:
                pygame.draw.circle(screen, col, (int(tx), int(p[1])), 3)

    # ---- gates and boxes ---------------------------------------------
    info = {}
    for n in net.nodes:
        g = geo[n["id"]]
        r = g["rect"]
        info[n["id"]] = r
        if n["type"] == "BOX":
            pygame.draw.rect(screen, pal["bg"], r, border_radius=6)
            pygame.draw.rect(screen, pal["ink"], r, 2, border_radius=6)
            lines = n["label"].split("|")
            for li, line in enumerate(lines):
                _text(screen, f_tiny, line, pal["ink"],
                      center=(r.centerx, r.centery + (li - (len(lines) - 1) / 2.0) * 14))
            for pin, name in zip(g["ins"], n.get("pin_names", [""] * len(g["ins"]))):
                if name:
                    _text(screen, f_tiny, name, pal["dim"], midleft=(pin[0] + 3, pin[1]))
            for pin, name in zip(g["outs"].values(), n["outs"]):
                _text(screen, f_tiny, name, pal["dim"], midright=(pin[0] - 3, pin[1]))
            continue
        gate = types.get(n["id"], n["type"])
        if gate is None:
            hov = slot_hover == n["id"]
            pygame.draw.rect(screen, pal["bg"], r, border_radius=6)
            pygame.draw.rect(screen, pal["slot"], r, 3 if hov else 2, border_radius=6)
            _text(screen, f_small, "?", pal["slot"], center=r.center)
            for pt in g["ins"]:
                pygame.draw.line(screen, pal["wire_unk"], (r.x - 4, pt[1]), (r.x, pt[1]), 2)
            pygame.draw.line(screen, pal["wire_unk"], (r.right, r.centery), (r.right + 4, r.centery), 2)
            if hits is not None:
                hits.append((r.inflate(10, 10), ("slot", n["id"])))
        else:
            draw_gate_n(screen, gate, r, pal["ink"], n=len(n["ins"]), stroke=2, bg=pal["bg"])
            if n.get("label") and n["id"] not in types:
                _text(screen, f_tiny, n["label"], pal["dim"], midtop=(r.centerx, r.bottom + 1))
            if hits is not None and n["id"] in types:
                hits.append((r.inflate(10, 10), ("slot", n["id"])))
                pygame.draw.rect(screen, pal["slot"], r.inflate(6, 6), 1, border_radius=6)

    # ---- inputs and outputs --------------------------------------------
    for idx, i in enumerate(net.inputs):
        px, py = cx(i["x"]), cy(i["y"])
        v = vals.get(i["name"])
        r = _switch(screen, int(px), int(py), v, pal, w=int(sw_w))
        _text(screen, f_small, i["name"], pal["ink"], midright=(r.x - 3, py))
        if in_keys and idx < 12:
            key = "1234567890-="[idx]
            _text(screen, f_tiny, key, pal["dim"], midbottom=(px, py - 11))
        if hits is not None:
            hits.append((r.inflate(14, 14), ("in", i["name"])))
    for o in net.outputs:
        bx, by = out_pt[o["name"]]
        v = vals.get(o["ref"])
        if mask_outputs:
            v = None
        pygame.draw.line(screen, _wire_col(v, pal), (bx - 10, by), (bx, by), 2)
        _bulb(screen, int(bx + 12), int(by), 11, v, pal)
        if out_labels:
            _text(screen, f_small, o["name"], pal["ink"], midleft=(bx + 28, by))
        if not mask_outputs and v is not None:
            _text(screen, f_tiny, str(v), pal["bg"] if v else pal["bulb_edge"],
                  center=(bx + 12, by))
    return info


# ------------------------------------------------------------------
# CUSTOM BLOCK DRAWINGS (adder chains, multiplexer boxes)
# ------------------------------------------------------------------
def _bits_of(vals, prefix, n):
    return [vals.get(f"{prefix}{i}", 0) for i in range(n - 1, -1, -1)]


def _num(bits):
    out = 0
    for b in bits:
        out = out * 2 + (b or 0)
    return out


def draw_adder_chain(screen, area, vals, pal, fonts, hits=None, sub=False,
                     active=None, mask_outputs=False, results=None):
    """Four full-adder boxes in a row.  sub=True adds the XOR row and the M switch."""
    f_small, f_tiny = fonts["small"], fonts["tiny"]
    n = 4
    left, right = area.x + 52, area.right - 66
    bw = min(78, (right - left) / n * 0.62)
    gap = (right - left - n * bw) / (n - 1)
    a = _bits_of(vals, "A", 4)
    b = _bits_of(vals, "B", 4)
    cin = vals.get("M", 0) if sub else vals.get("Cin", 0)
    bx = [b_ ^ cin for b_ in b] if sub else b
    carries = [0] * 5              # carries[0] enters FA0
    carries[0] = cin
    sums = [0] * 4
    for i in range(4):             # i = 0 is the LSB
        t = a[3 - i] + bx[3 - i] + carries[i]
        sums[i] = t & 1
        carries[i + 1] = t >> 1
    y_a = area.y + 14
    y_b = area.y + 42
    y_x = area.y + 74 if sub else None
    box_top = area.y + (104 if sub else 80)
    bh = 50
    mid_y = box_top + bh // 2
    y_s = box_top + bh + 34
    for col in range(4):           # col 0 is the MSB on the left
        i = 3 - col
        x0 = left + col * (bw + gap)
        cxm = int(x0 + bw / 2)
        box = pygame.Rect(int(x0), box_top, int(bw), bh)
        on = active is None or active == i
        pygame.draw.rect(screen, pal["bg"], box, border_radius=6)
        pygame.draw.rect(screen, pal["accent"] if active == i else pal["ink"], box,
                         3 if active == i else 2, border_radius=6)
        _text(screen, f_small, "FA", pal["ink"], center=(cxm, box_top + 17))
        _text(screen, f_tiny, f"bit {i}", pal["dim"], center=(cxm, box_top + 36))
        # inputs A and B
        for yy, nm, v in ((y_a, f"A{i}", a[col]), (y_b, f"B{i}", b[col])):
            r = _switch(screen, cxm, yy, v, pal, w=36, h=18)
            _text(screen, f_tiny, nm, pal["ink"], midright=(r.x - 2, yy))
            if hits is not None:
                hits.append((r.inflate(10, 6), ("in", nm)))
        wire_from = y_b + 10
        if sub:
            xr = pygame.Rect(0, 0, 36, 20)
            xr.center = (cxm, y_x)
            pygame.draw.rect(screen, pal["bg"], xr, border_radius=10)
            pygame.draw.rect(screen, pal["ink"], xr, 2, border_radius=10)
            _text(screen, f_tiny, "XOR", pal["ink"], center=xr.center)
            pygame.draw.line(screen, _wire_col(b[col], pal), (cxm, y_b + 9), (cxm, xr.y), 2)
            pygame.draw.line(screen, _wire_col(bx[col], pal), (cxm, xr.bottom), (cxm, box_top), 2)
            pygame.draw.line(screen, _wire_col(a[col], pal), (cxm - 14, y_a + 9), (cxm - 14, box_top), 2)
            pygame.draw.line(screen, _wire_col(cin, pal), (cxm + 14, y_x + 1), (cxm + 14, y_x + 1), 2)
        else:
            pygame.draw.line(screen, _wire_col(b[col], pal), (cxm + 6, wire_from), (cxm + 6, box_top), 2)
            pygame.draw.line(screen, _wire_col(a[col], pal), (cxm - 6, y_a + 9), (cxm - 6, box_top), 2)
        # sum bulb
        known = active is None or i <= active          # frames reveal column by column
        sv = None if (mask_outputs or not known) else sums[i]
        pygame.draw.line(screen, _wire_col(sv, pal), (cxm, box_top + bh), (cxm, y_s - 12), 2)
        _bulb(screen, cxm, y_s, 11, sv, pal)
        if sv is not None:
            _text(screen, f_tiny, str(sv), pal["bg"] if sv else pal["bulb_edge"], center=(cxm, y_s))
        _text(screen, f_tiny, f"S{i}", pal["ink"], center=(cxm, y_s + 22))
        # carry arrow into this box from the box on its right (or Cin)
        rx = x0 + bw
        nxt = rx + gap if col < 3 else right + 12
        cv = carries[i] if (active is None or i <= active) else None
        pygame.draw.line(screen, _wire_col(cv, pal), (nxt, mid_y), (rx, mid_y), 2)
        pygame.draw.polygon(screen, _wire_col(cv, pal),
                            [(rx, mid_y), (rx + 7, mid_y - 4), (rx + 7, mid_y + 4)])
        if col < 3:
            _text(screen, f_tiny, f"c{i}", pal["dim"], midbottom=((rx + nxt) / 2, mid_y - 3))
    # carry-in switch / mode switch on the right, carry-out bulb on the left
    sx = right + 36
    nm = "M" if sub else "Cin"
    r = _switch(screen, int(sx), mid_y, cin, pal, w=36, h=18)
    _text(screen, f_tiny, nm, pal["ink"], midbottom=(sx, mid_y - 12))
    if hits is not None:
        hits.append((r.inflate(10, 10), ("in", nm)))
    pygame.draw.line(screen, _wire_col(cin, pal), (r.x, mid_y), (right + 12, mid_y), 2)
    if sub:
        _text(screen, f_tiny, "M = 0: add     M = 1: subtract (M also flips B through the XORs)",
              pal["dim"], midbottom=(area.centerx, area.bottom - 4))
    co = None if (mask_outputs or (active is not None and active < 3)) else carries[4]
    ox_ = left - 28
    pygame.draw.line(screen, _wire_col(co, pal), (left, mid_y), (ox_ + 12, mid_y), 2)
    _bulb(screen, int(ox_), mid_y, 11, co, pal)
    if co is not None:
        _text(screen, f_tiny, str(co), pal["bg"] if co else pal["bulb_edge"], center=(ox_, mid_y))
    _text(screen, f_tiny, "Cout", pal["ink"], midtop=(ox_, mid_y + 14))
    return {"sums": sums, "carries": carries, "a": a, "b": b, "bx": bx, "cin": cin}


def draw_mux_block(screen, area, vals, pal, fonts, hits=None, n_sel=3, mask_outputs=False):
    """Trapezoid multiplexer with 2^n_sel data inputs and n_sel select inputs."""
    f_small, f_tiny = fonts["small"], fonts["tiny"]
    nd = 1 << n_sel
    sel_names = [f"S{i}" for i in range(n_sel - 1, -1, -1)]
    sel = _num([vals.get(s, 0) for s in sel_names])
    top = area.y + 12
    row = min(26, (area.h - 70) / float(nd))
    height = row * nd + 8
    bx0 = area.x + area.w * 0.36
    bx1 = bx0 + 76
    pts = [(bx0, top), (bx1, top + 16), (bx1, top + height - 16), (bx0, top + height)]
    pygame.draw.polygon(screen, pal["bg"], pts)
    pygame.draw.polygon(screen, pal["ink"], pts, 2)
    _text(screen, f_small, f"MUX {nd}:1", pal["ink"], center=((bx0 + bx1) / 2, top + height / 2))
    ys = []
    for k in range(nd):
        yy = top + 4 + row * (k + 0.5)
        ys.append(yy)
        v = vals.get(f"I{k}", 0)
        chosen = (k == sel)
        sw = _switch(screen, int(area.x + 50), int(yy), v, pal, w=34, h=16)
        _text(screen, f_tiny, f"I{k}", pal["ink"], midright=(sw.x - 3, yy))
        col = _wire_col(v, pal)
        pygame.draw.line(screen, col, (sw.right, yy), (bx0, yy), 3 if chosen else 1)
        if chosen:
            _text(screen, f_tiny, "<", pal["accent"], midleft=(bx0 + 3, yy))
        if hits is not None:
            hits.append((sw.inflate(10, 6), ("in", f"I{k}")))
    # selects along the bottom
    base_y = top + height + 24
    sx0 = (bx0 + bx1) / 2 - (n_sel - 1) * 22
    for j, s in enumerate(sel_names):
        sxx = sx0 + j * 44
        v = vals.get(s, 0)
        r = _switch(screen, int(sxx), int(base_y), v, pal, w=34, h=16)
        _text(screen, f_tiny, s, pal["ink"], midtop=(sxx, base_y + 10))
        pygame.draw.line(screen, _wire_col(v, pal), (sxx, base_y - 9),
                         (sxx, top + height - (8 if sxx > bx0 + 30 else 0)), 1)
        if hits is not None:
            hits.append((r.inflate(10, 10), ("in", s)))
    yv = None if mask_outputs else vals.get(f"I{sel}", 0)
    oy = top + height / 2
    pygame.draw.line(screen, _wire_col(yv, pal), (bx1, oy), (bx1 + 40, oy), 3)
    _bulb(screen, int(bx1 + 54), int(oy), 12, yv, pal)
    if yv is not None:
        _text(screen, f_tiny, str(yv), pal["bg"] if yv else pal["bulb_edge"], center=(bx1 + 54, oy))
    _text(screen, f_small, "Y", pal["ink"], midleft=(bx1 + 72, oy))
    _text(screen, f_tiny, f"selects = {sel:0{n_sel}b} -> picks I{sel}", pal["accent"],
          midtop=((bx0 + bx1) / 2 + 20, base_y + 24))
    return {"sel": sel, "ys": ys, "box": (bx0, bx1, top, height)}


# ------------------------------------------------------------------
# TRUTH TABLE PANEL
# ------------------------------------------------------------------
def table_col_width(headers, rows, fonts):
    f_tiny = fonts["tiny"]
    widest = max([f_tiny.size(str(h))[0] for h in headers] +
                 [f_tiny.size(str(v))[0] for r in rows for v in r] + [8])
    return max(20, widest + 8)


def draw_table(screen, rect, headers, rows, cur, pal, fonts, hide_cols=(), marks=None):
    f_tiny = fonts["tiny"]
    ncol = len(headers)
    rh = max(12, min(22, (rect.h - 22) // (len(rows) + 1)))
    cw = min(table_col_width(headers, rows, fonts), rect.w // max(1, ncol))
    width = cw * ncol
    x0 = rect.x + (rect.w - width) // 2
    for j, h in enumerate(headers):
        r = pygame.Rect(x0 + j * cw, rect.y, cw - 2, rh - 1)
        pygame.draw.rect(screen, pal["head"], r)
        _text(screen, f_tiny, h, pal["ink"], center=r.center)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            r = pygame.Rect(x0 + j * cw, rect.y + (i + 1) * rh, cw - 2, rh - 1)
            hl = (i == cur)
            pygame.draw.rect(screen, pal["row_hl"] if hl else pal["cell"], r)
            if j in hide_cols:
                txt = "?"
            else:
                txt = str(v)
            _text(screen, f_tiny, txt, pal["good"] if hl and j >= 0 else pal["ink"], center=r.center)
    if cur is not None and 0 <= cur < len(rows):
        r = pygame.Rect(x0 - 2, rect.y + (cur + 1) * rh - 1, width + 2, rh + 1)
        pygame.draw.rect(screen, pal["accent"], r, 2)
    return rh


# ------------------------------------------------------------------
# THE SIMULATORS
# ------------------------------------------------------------------
SIMS = []
BY_ID = {}


def _add(sid, name, group, purpose, inputs, outs, fn, net=None, draw=None, table="auto",
         readout=None, equations=(), notes=(), tin=None, init=None):
    s = {"id": sid, "name": name, "group": group, "purpose": purpose, "inputs": list(inputs),
         "outs": list(outs), "fn": fn, "net": net, "draw": draw, "table": table,
         "readout": readout, "equations": list(equations), "notes": list(notes),
         "tin": list(tin) if tin else list(inputs), "init": dict(init or {})}
    SIMS.append(s)
    BY_ID[sid] = s
    return s


def sim_outs(sim, vals):
    v = {k: vals.get(k, 0) for k in sim["inputs"]}
    return sim["fn"](v)


def table_rows(sim):
    """List of (input_tuple, output_tuple) over the table inputs (others fixed 0)."""
    rows = []
    for combo in itertools.product((0, 1), repeat=len(sim["tin"])):
        v = {k: 0 for k in sim["inputs"]}
        v.update(sim["init"])
        v.update(dict(zip(sim["tin"], combo)))
        out = sim["fn"](v)
        rows.append((combo, tuple(out[o] for o in sim["outs"])))
    return rows


def minterms(sim, out_name):
    return [i for i, (_c, o) in enumerate(table_rows(sim)) if o[sim["outs"].index(out_name)]]


def row_index(sim, vals):
    key = tuple(vals.get(k, 0) for k in sim["tin"])
    n = 0
    for b in key:
        n = n * 2 + b
    return n


def default_vals(sim):
    v = {k: 0 for k in sim["inputs"]}
    v.update(sim["init"])
    return v


def _b(v, k):
    return v.get(k, 0)


# ---- ARITHMETIC --------------------------------------------------
def _ha(v):
    return {"Sum": _b(v, "A") ^ _b(v, "B"), "Carry": _b(v, "A") & _b(v, "B")}


def _ha_net():
    return Net(
        [IN("A", 0), IN("B", 1)],
        [G("s", "XOR", ["A", "B"], 1, 0, "SUM"), G("c", "AND", ["A", "B"], 1, 1, "CARRY")],
        [OUT("Sum", "s", 2, 0), OUT("Carry", "c", 2, 1)])


def _ha_read(v, o):
    a, b = _b(v, "A"), _b(v, "B")
    t = a + b
    return [f"{a} + {b} = {t}  =  binary {t:02b}",
            f"Carry (the left digit) = {o['Carry']},  Sum (the right digit) = {o['Sum']}"]


_add("ha", "HALF ADDER", "ARITHMETIC",
     "Adds two single bits. 1 + 1 = 2 needs two digits, so it has a SUM bulb and a CARRY bulb.",
     ["A", "B"], ["Sum", "Carry"], _ha, net=_ha_net(), readout=_ha_read,
     equations=["Sum = A xor B", "Carry = A.B  (A AND B)"],
     notes=["Use it to add the lowest column of two numbers (nothing comes in from the right)."])


def _fa(v):
    t = _b(v, "A") + _b(v, "B") + _b(v, "Cin")
    return {"Sum": t & 1, "Cout": t >> 1}


def _fa_net():
    return Net(
        [IN("A", 0), IN("B", 1), IN("Cin", 2.7)],
        [G("x1", "XOR", ["A", "B"], 1, 0.5, "HA 1"), G("a1", "AND", ["A", "B"], 1, 1.5),
         G("x2", "XOR", ["x1", "Cin"], 2, 0.8, "HA 2"), G("a2", "AND", ["x1", "Cin"], 2, 2.1),
         G("o", "OR", ["a1", "a2"], 3, 1.75)],
        [OUT("Sum", "x2", 4, 0.8), OUT("Cout", "o", 4, 1.75)])


def _fa_read(v, o):
    a, b, c = _b(v, "A"), _b(v, "B"), _b(v, "Cin")
    t = a + b + c
    return [f"{a} + {b} + {c} = {t}  =  binary {t:02b}",
            f"Cout (left digit) = {o['Cout']},  Sum (right digit) = {o['Sum']}"]


_add("fa", "FULL ADDER", "ARITHMETIC",
     "Adds THREE bits: A, B and the carry that arrives from the column on the right.",
     ["A", "B", "Cin"], ["Sum", "Cout"], _fa, net=_fa_net(), readout=_fa_read,
     equations=["Sum = A xor B xor Cin", "Cout = AB + A.Cin + B.Cin = AB + Cin(A xor B)"],
     notes=["Built from two half adders and an OR gate."])


def _hs(v):
    a, b = _b(v, "A"), _b(v, "B")
    return {"Diff": a ^ b, "Borrow": (1 - a) & b}


def _hs_net():
    return Net(
        [IN("A", 0.4), IN("B", 2.0)],
        [G("na", "NOT", ["A"], 1, 0), G("d", "XOR", ["A", "B"], 1, 1.2, "DIFF"),
         G("b", "AND", ["na", "B"], 2, 0.7, "BORROW")],
        [OUT("Diff", "d", 3, 1.2), OUT("Borrow", "b", 3, 0.7)])


def _hs_read(v, o):
    a, b = _b(v, "A"), _b(v, "B")
    if a >= b:
        return [f"{a} - {b} = {a - b}   (no borrow needed)"]
    return [f"{a} - {b}: not possible in one column!",
            "Borrow 1 from the left (it is worth 2): 2 - 1 = 1, so Diff = 1, Borrow = 1"]


_add("hs", "HALF SUBTRACTOR", "ARITHMETIC",
     "Subtracts B from A, one column. If A is smaller it borrows from its neighbour.",
     ["A", "B"], ["Diff", "Borrow"], _hs, net=_hs_net(), readout=_hs_read,
     equations=["Diff = A xor B", "Borrow = A'.B"],
     notes=["Same XOR as the half adder; only the second gate changes (A' AND B)."])


def _fs(v):
    a, b, c = _b(v, "A"), _b(v, "B"), _b(v, "Bin")
    d = a ^ b ^ c
    bo = int(((1 - a) & b) | ((1 - a) & c) | (b & c))
    return {"Diff": d, "Bout": bo}


def _fs_net():
    return Net(
        [IN("A", 0.3), IN("B", 2.0), IN("Bin", 4.2)],
        [G("na", "NOT", ["A"], 1, 0), G("d1", "XOR", ["A", "B"], 1, 1.1, "HS 1"),
         G("b1", "AND", ["na", "B"], 2, 0.55),
         G("nd", "NOT", ["d1"], 2, 2.1), G("d2", "XOR", ["d1", "Bin"], 2, 3.4, "HS 2"),
         G("b2", "AND", ["nd", "Bin"], 3, 2.6),
         G("o", "OR", ["b1", "b2"], 4, 1.6)],
        [OUT("Diff", "d2", 5, 3.4), OUT("Bout", "o", 5, 1.6)])


def _fs_read(v, o):
    a, b, c = _b(v, "A"), _b(v, "B"), _b(v, "Bin")
    return [f"{a} - {b} - {c} = {a - b - c}" + ("   (negative, so it borrows)" if a - b - c < 0 else ""),
            f"Diff = {o['Diff']},  Bout (borrow out) = {o['Bout']}"]


_add("fs", "FULL SUBTRACTOR", "ARITHMETIC",
     "Subtracts B and the borrow that came from the right column, from A.",
     ["A", "B", "Bin"], ["Diff", "Bout"], _fs, net=_fs_net(), readout=_fs_read,
     equations=["Diff = A xor B xor Bin", "Bout = A'B + A'Bin + B.Bin"],
     notes=["Built from two half subtractors and an OR gate."])


def _add4(v):
    a = _num(_bits_of(v, "A", 4))
    b = _num(_bits_of(v, "B", 4))
    t = a + b + _b(v, "Cin")
    out = {f"S{i}": (t >> i) & 1 for i in range(4)}
    out["Cout"] = (t >> 4) & 1
    return out


def _add4_read(v, o):
    a = _num(_bits_of(v, "A", 4))
    b = _num(_bits_of(v, "B", 4))
    c = _b(v, "Cin")
    t = a + b + c
    return [f"A = {a:04b} ({a})   B = {b:04b} ({b})   Cin = {c}",
            f"{a} + {b} + {c} = {t}  =  {t:05b}   (Cout S3 S2 S1 S0)"]


_add("add4", "4-BIT PARALLEL ADDER", "ARITHMETIC",
     "Four full adders in a row add two 4-bit numbers. Each carry ripples to the next adder.",
     ["A3", "A2", "A1", "A0", "B3", "B2", "B1", "B0", "Cin"],
     ["S3", "S2", "S1", "S0", "Cout"], _add4,
     draw=lambda *a, **k: draw_adder_chain(*a, sub=False, **k), table=None, readout=_add4_read,
     equations=["Carry out of one full adder = carry in of the next."],
     notes=["Also called a RIPPLE CARRY ADDER: the carry ripples from the right (bit 0) to the left."],
     tin=["A0", "B0", "Cin"])


def _addsub(v):
    m = _b(v, "M")
    a = _num(_bits_of(v, "A", 4))
    b = _num(_bits_of(v, "B", 4))
    bx = b ^ (0b1111 if m else 0)
    t = a + bx + m
    out = {f"S{i}": (t >> i) & 1 for i in range(4)}
    out["Cout"] = (t >> 4) & 1
    return out


def _addsub_read(v, o):
    m = _b(v, "M")
    a = _num(_bits_of(v, "A", 4))
    b = _num(_bits_of(v, "B", 4))
    if m == 0:
        t = a + b
        return [f"M = 0: ADD.  {a} + {b} = {t}  =  {t:05b}"]
    bx = b ^ 0b1111
    t = a + bx + 1
    note = "Cout = 1 means the answer is not negative." if (t >> 4) & 1 else \
        "Cout = 0 means the answer is negative (shown in 2's complement)."
    return [f"M = 1: SUBTRACT.  B {b:04b} flips to {bx:04b}, then +1 (the carry-in)",
            f"{a} + {bx} + 1 = {t:05b}   so  {a} - {b} = {a - b}",
            note]


_add("addsub", "ADDER-SUBTRACTOR", "ARITHMETIC",
     "One circuit that adds when M = 0 and subtracts when M = 1.",
     ["A3", "A2", "A1", "A0", "B3", "B2", "B1", "B0", "M"],
     ["S3", "S2", "S1", "S0", "Cout"], _addsub,
     draw=lambda *a, **k: draw_adder_chain(*a, sub=True, **k), table=None, readout=_addsub_read,
     equations=["B goes through an XOR with M: M = 0 keeps B, M = 1 flips B.",
                "M is also the carry-in: A - B = A + B' + 1."],
     notes=["It is the same adder; only the XOR gates and the carry-in change."],
     tin=["A0", "B0", "M"])


def _cmp2(v):
    a = _b(v, "A1") * 2 + _b(v, "A0")
    b = _b(v, "B1") * 2 + _b(v, "B0")
    return {"A>B": int(a > b), "A=B": int(a == b), "A<B": int(a < b)}


def _cmp_net():
    box = BOX("c", "2-BIT|COMPARATOR", ["A1", "A0", "B1", "B0"], ["G", "E", "L"],
              lambda a1, a0, b1, b0: (int(a1 * 2 + a0 > b1 * 2 + b0), int(a1 * 2 + a0 == b1 * 2 + b0),
                                      int(a1 * 2 + a0 < b1 * 2 + b0)), 1, 1.75, h=3.6)
    box["pin_names"] = ["A1", "A0", "B1", "B0"]
    return Net([IN("A1", 0), IN("A0", 1.2), IN("B1", 2.4), IN("B0", 3.6)], [box],
               [OUT("A>B", "c.G", 2, 0.9), OUT("A=B", "c.E", 2, 1.75), OUT("A<B", "c.L", 2, 2.6)])


def _cmp_read(v, o):
    a = _b(v, "A1") * 2 + _b(v, "A0")
    b = _b(v, "B1") * 2 + _b(v, "B0")
    return [f"A = {a:02b} ({a}),  B = {b:02b} ({b})",
            "A is bigger" if a > b else ("A equals B" if a == b else "B is bigger")]


_add("cmp2", "2-BIT COMPARATOR", "ARITHMETIC",
     "Looks at two 2-bit numbers and says which one is bigger, or if they are equal.",
     ["A1", "A0", "B1", "B0"], ["A>B", "A=B", "A<B"], _cmp2, net=_cmp_net(), readout=_cmp_read,
     equations=["A=B when (A1 xnor B1) and (A0 xnor B0)", "A>B when A1.B1' + (A1 xnor B1).A0.B0'"],
     notes=["Not asked often. Compare the left bits first; only if they match look at the right bits."])


# ---- CODES -------------------------------------------------------
def _par(names):
    def f(v):
        p = 0
        for n in names:
            p ^= _b(v, n)
        return {"P": p}
    return f


def _par_read(names):
    def f(v, o):
        ones = sum(_b(v, n) for n in names)
        return [f"Message has {ones} one(s).  P = {o['P']}",
                f"Message + P has {ones + o['P']} ones: always EVEN"]
    return f


_add("par3", "EVEN PARITY GENERATOR (3 BIT)", "CODES",
     "Adds one extra bit so the total number of 1s is always even. A receiver can then spot errors.",
     ["A", "B", "C"], ["P"], _par(["A", "B", "C"]),
     net=Net([IN("A", 0), IN("B", 1), IN("C", 2.1)],
             [G("x1", "XOR", ["A", "B"], 1, 0.5), G("p", "XOR", ["x1", "C"], 2, 1.2)],
             [OUT("P", "p", 3, 1.2)]),
     readout=_par_read(["A", "B", "C"]),
     equations=["P = A xor B xor C", "P = 1 when the message has an ODD number of 1s."],
     notes=["P = Sum m(1,2,4,7): the same list as the full adder's Sum."])

_add("par4", "EVEN PARITY GENERATOR (4 BIT)", "CODES",
     "Same job for a 4-bit message. This one is asked in the exam.",
     ["A", "B", "C", "D"], ["P"], _par(["A", "B", "C", "D"]),
     net=Net([IN("A", 0), IN("B", 1), IN("C", 2), IN("D", 3)],
             [G("x1", "XOR", ["A", "B"], 1, 0.5), G("x2", "XOR", ["C", "D"], 1, 2.5),
              G("p", "XOR", ["x1", "x2"], 2, 1.5)],
             [OUT("P", "p", 3, 1.5)]),
     readout=_par_read(["A", "B", "C", "D"]),
     equations=["P = A xor B xor C xor D", "P = Sum m(1,2,4,7,8,11,13,14)"],
     notes=["Even parity: message + P must contain an even number of 1s."])


def _pchk(v):
    p = 0
    for n in ("A", "B", "C", "D", "P"):
        p ^= _b(v, n)
    return {"Error": p}


def _pchk_read(v, o):
    ones = sum(_b(v, n) for n in ("A", "B", "C", "D", "P"))
    return [f"Received {ones} one(s) in total (message + P)",
            "EVEN: looks fine." if ones % 2 == 0 else "ODD: a bit was damaged on the way!"]


_add("parchk", "EVEN PARITY CHECKER (4 BIT + P)", "CODES",
     "The receiver XORs everything it got. Error = 1 means an odd count, so a bit was damaged.",
     ["A", "B", "C", "D", "P"], ["Error"], _pchk,
     net=Net([IN("A", 0), IN("B", 1), IN("C", 2), IN("D", 3), IN("P", 4.4)],
             [G("x1", "XOR", ["A", "B"], 1, 0.5), G("x2", "XOR", ["C", "D"], 1, 2.5),
              G("x3", "XOR", ["x1", "x2"], 2, 1.5), G("e", "XOR", ["x3", "P"], 3, 2.9)],
             [OUT("Error", "e", 4, 2.9)]),
     table=None, readout=_pchk_read, tin=["A", "B", "C", "D", "P"],
     equations=["Error = A xor B xor C xor D xor P"],
     notes=["Only ONE flipped bit is caught. Two flipped bits cancel out."])


def _b2g(v):
    b3, b2, b1, b0 = [_b(v, f"B{i}") for i in (3, 2, 1, 0)]
    return {"G3": b3, "G2": b3 ^ b2, "G1": b2 ^ b1, "G0": b1 ^ b0}


def _b2g_read(v, o):
    b = "".join(str(_b(v, f"B{i}")) for i in (3, 2, 1, 0))
    g = "".join(str(o[f"G{i}"]) for i in (3, 2, 1, 0))
    return [f"Binary {b} ({int(b, 2)})  ->  Gray {g}"]


_add("b2g", "BINARY TO GRAY (4 BIT)", "CODES",
     "Gray code changes only ONE bit from one number to the next. Good for position sensors.",
     ["B3", "B2", "B1", "B0"], ["G3", "G2", "G1", "G0"], _b2g,
     net=Net([IN("B3", 0), IN("B2", 1), IN("B1", 2), IN("B0", 3)],
             [G("g2", "XOR", ["B3", "B2"], 1, 0.5), G("g1", "XOR", ["B2", "B1"], 1, 1.5),
              G("g0", "XOR", ["B1", "B0"], 1, 2.5)],
             [OUT("G3", "B3", 2, 0), OUT("G2", "g2", 2, 0.5), OUT("G1", "g1", 2, 1.5),
              OUT("G0", "g0", 2, 2.5)]),
     readout=_b2g_read,
     equations=["G3 = B3", "G2 = B3 xor B2", "G1 = B2 xor B1", "G0 = B1 xor B0"],
     notes=["Keep the left bit, then XOR each bit with the bit on its left."])


def _g2b(v):
    g3, g2, g1, g0 = [_b(v, f"G{i}") for i in (3, 2, 1, 0)]
    b3 = g3
    b2 = b3 ^ g2
    b1 = b2 ^ g1
    b0 = b1 ^ g0
    return {"B3": b3, "B2": b2, "B1": b1, "B0": b0}


def _g2b_read(v, o):
    g = "".join(str(_b(v, f"G{i}")) for i in (3, 2, 1, 0))
    b = "".join(str(o[f"B{i}"]) for i in (3, 2, 1, 0))
    return [f"Gray {g}  ->  binary {b} ({int(b, 2)})"]


_add("g2b", "GRAY TO BINARY (4 BIT)", "CODES",
     "Turns a Gray code back into ordinary binary. The XORs now form a chain.",
     ["G3", "G2", "G1", "G0"], ["B3", "B2", "B1", "B0"], _g2b,
     net=Net([IN("G3", 0), IN("G2", 1), IN("G1", 2), IN("G0", 3)],
             [G("b2", "XOR", ["G3", "G2"], 1, 0.5), G("b1", "XOR", ["b2", "G1"], 2, 1.5),
              G("b0", "XOR", ["b1", "G0"], 3, 2.5)],
             [OUT("B3", "G3", 4, 0), OUT("B2", "b2", 4, 0.5), OUT("B1", "b1", 4, 1.5),
              OUT("B0", "b0", 4, 2.5)]),
     readout=_g2b_read,
     equations=["B3 = G3", "B2 = B3 xor G2", "B1 = B2 xor G1", "B0 = B1 xor G0"],
     notes=["Each new binary bit uses the binary bit you just found (a chain), not the Gray bit."])


def _enc4(v):
    d = [_b(v, f"D{i}") for i in range(4)]
    return {"Y1": d[3] | d[2], "Y0": d[3] | d[1], "V": int(any(d))}


def _enc_read(n):
    def f(v, o):
        on = [i for i in range(n) if _b(v, f"D{i}")]
        if len(on) == 1:
            return [f"Only D{on[0]} is 1  ->  output code = {on[0]:0{(n - 1).bit_length()}b}"]
        if not on:
            return ["No input is 1. (The Valid bit tells us the code means nothing.)" if n == 4
                    else "No input is 1: the code 000 is ambiguous."]
        return [f"{len(on)} inputs are 1 at once. A plain encoder gives a wrong code.",
                "A PRIORITY encoder fixes this by listening to the highest input only."]
    return f


_add("enc4", "ENCODER 4-TO-2", "CODES",
     "The opposite of a decoder: press ONE of 4 keys and it outputs that key's number in binary.",
     ["D3", "D2", "D1", "D0"], ["Y1", "Y0", "V"], _enc4,
     net=Net([IN("D3", 0), IN("D2", 1), IN("D1", 2), IN("D0", 3)],
             [G("y1", "OR", ["D3", "D2"], 1, 0.6), G("y0", "OR", ["D3", "D1"], 1, 1.8),
              G("v", "OR", ["D3", "D2", "D1", "D0"], 1, 3.3)],
             [OUT("Y1", "y1", 2, 0.6), OUT("Y0", "y0", 2, 1.8), OUT("V", "v", 2, 3.3)]),
     table=None, readout=_enc_read(4), tin=["D3", "D2", "D1", "D0"],
     equations=["Y1 = D3 + D2", "Y0 = D3 + D1", "V = D0 + D1 + D2 + D3  (valid)"],
     notes=["Only one input may be 1 at a time. Not asked in the exams so far."])


def _enc8(v):
    d = [_b(v, f"D{i}") for i in range(8)]
    return {"Y2": d[4] | d[5] | d[6] | d[7], "Y1": d[2] | d[3] | d[6] | d[7],
            "Y0": d[1] | d[3] | d[5] | d[7]}


_add("enc8", "ENCODER 8-TO-3", "CODES",
     "Eight keys in, a 3-bit code out. The output is the number of the key that is pressed.",
     [f"D{i}" for i in range(7, -1, -1)], ["Y2", "Y1", "Y0"], _enc8,
     net=Net([IN(f"D{i}", 7 - i) for i in range(7, -1, -1)],
             [G("y2", "OR", ["D7", "D6", "D5", "D4"], 1, 1.5), G("y1", "OR", ["D7", "D6", "D3", "D2"], 1, 3.5),
              G("y0", "OR", ["D7", "D5", "D3", "D1"], 1, 5.5)],
             [OUT("Y2", "y2", 2, 1.5), OUT("Y1", "y1", 2, 3.5), OUT("Y0", "y0", 2, 5.5)]),
     table=None, readout=_enc_read(8), tin=[f"D{i}" for i in range(7, -1, -1)],
     equations=["Y2 = D4 + D5 + D6 + D7", "Y1 = D2 + D3 + D6 + D7", "Y0 = D1 + D3 + D5 + D7"],
     notes=["Each output bit is an OR of the inputs whose number has that bit set."])


# ---- ROUTING -----------------------------------------------------
def _dec_net(n):
    names = "ABC"[:n]
    nodes = []
    k = 1 << n
    inputs = []
    # inputs high up, NOT gates one row under each input
    span = k - 1
    for i, nm in enumerate(names):
        y = span * i / float(max(1, n - 1)) * 0.78 if n > 1 else 0.0
        inputs.append(IN(nm, y + 0.2))
        nodes.append(G("n" + nm, "NOT", [nm], 1, y + 1.25))
    outs = []
    for m in range(k):
        ins = []
        for i, nm in enumerate(names):
            bit = (m >> (n - 1 - i)) & 1
            ins.append(nm if bit else "n" + nm)
        nodes.append(G(f"y{m}", "AND", ins, 2, m, f"m{m}"))
        outs.append(OUT(f"Y{m}", f"y{m}", 3, m))
    return Net(inputs, nodes, outs)


def _dec_fn(n):
    names = "ABC"[:n]

    def f(v):
        idx = 0
        for nm in names:
            idx = idx * 2 + _b(v, nm)
        return {f"Y{m}": int(m == idx) for m in range(1 << n)}
    return f


def _dec_read(n):
    names = "ABC"[:n]

    def f(v, o):
        idx = 0
        for nm in names:
            idx = idx * 2 + _b(v, nm)
        code = format(idx, f"0{n}b")
        return [f"Input {code} = {idx}  ->  only line Y{idx} is ON",
                f"(Y{idx} is minterm m{idx}: you met it in the K-map level)"]
    return f


_add("dec2", "DECODER 2-TO-4", "ROUTING",
     "Turns a 2-bit code into ONE chosen line (like a lift panel lighting one floor lamp).",
     ["A", "B"], ["Y0", "Y1", "Y2", "Y3"], _dec_fn(2), net=_dec_net(2), readout=_dec_read(2),
     equations=["Y0 = A'B'   Y1 = A'B   Y2 = AB'   Y3 = AB"],
     notes=["Each output is ONE minterm: a decoder is a minterm generator."])

_add("dec3", "DECODER 3-TO-8", "ROUTING",
     "Same idea with 3 input bits and 8 output lines (2 x 2 x 2 = 8). Very common in exams.",
     ["A", "B", "C"], [f"Y{m}" for m in range(8)], _dec_fn(3), net=_dec_net(3), readout=_dec_read(3),
     equations=["Ym = minterm m, e.g. Y5 = A B' C  (101 = 5)",
                "n inputs give 2^n output lines."],
     notes=["Any function written as Sum m(...) = OR of those decoder outputs.",
            "Example: full adder Sum = Y1 + Y2 + Y4 + Y7;  Cout = Y3 + Y5 + Y6 + Y7."])


def _mux2(v):
    return {"Y": _b(v, "I1") if _b(v, "S") else _b(v, "I0")}


def _mux_read(n_sel):
    nd = 1 << n_sel
    names = [f"S{i}" for i in range(n_sel - 1, -1, -1)] if n_sel > 1 else ["S"]

    def f(v, o):
        sel = 0
        for s in names:
            sel = sel * 2 + _b(v, s)
        return [f"Select lines = {sel:0{n_sel}b} = {sel}  ->  Y copies I{sel}",
                f"I{sel} = {_b(v, f'I{sel}')},  so Y = {o['Y']}"]
    return f


_add("mux2", "MULTIPLEXER 2:1", "ROUTING",
     "A selector: S chooses which of two inputs reaches the output (like a railway switch).",
     ["S", "I0", "I1"], ["Y"], _mux2,
     net=Net([IN("I0", 0), IN("I1", 1.1), IN("S", 2.1)],
             [G("ns", "NOT", ["S"], 1, 2.9), G("a0", "AND", ["I0", "ns"], 2, 0.4),
              G("a1", "AND", ["I1", "S"], 2, 1.4), G("y", "OR", ["a0", "a1"], 3, 0.9)],
             [OUT("Y", "y", 4, 0.9)]),
     table=None, readout=_mux_read(1), tin=["S", "I0", "I1"],
     equations=["Y = S'.I0 + S.I1"],
     notes=["S = 0 passes I0.  S = 1 passes I1."], init={"I0": 1})


def _muxn(n_sel):
    nd = 1 << n_sel
    names = [f"S{i}" for i in range(n_sel - 1, -1, -1)]

    def f(v):
        sel = 0
        for s in names:
            sel = sel * 2 + _b(v, s)
        return {"Y": _b(v, f"I{sel}")}
    return f


def _mux_table(n_sel):
    nd = 1 << n_sel
    names = [f"S{i}" for i in range(n_sel - 1, -1, -1)]
    rows = [tuple(format(k, f"0{n_sel}b")) + (f"I{k}",) for k in range(nd)]
    return names + ["Y"], rows


_add("mux4", "MULTIPLEXER 4:1", "ROUTING",
     "Two select lines choose one of FOUR data inputs. (2 select lines -> 2^2 = 4 inputs.)",
     ["S1", "S0", "I0", "I1", "I2", "I3"], ["Y"], _muxn(2),
     draw=lambda *a, **k: draw_mux_block(*a, n_sel=2, **k), table=_mux_table(2),
     readout=_mux_read(2), tin=["S1", "S0"],
     equations=["Y = S1'S0'.I0 + S1'S0.I1 + S1S0'.I2 + S1S0.I3"],
     notes=["The data inputs I0..I3 sit where the minterms m0..m3 sit."], init={"I1": 1})

_add("mux8", "MULTIPLEXER 8:1", "ROUTING",
     "Three select lines choose one of EIGHT data inputs. A favourite in the exam.",
     ["S2", "S1", "S0"] + [f"I{k}" for k in range(8)], ["Y"], _muxn(3),
     draw=lambda *a, **k: draw_mux_block(*a, n_sel=3, **k), table=_mux_table(3),
     readout=_mux_read(3), tin=["S2", "S1", "S0"],
     equations=["Y = Sum over k of (m_k . I_k)",
                "Implement F: put 1 on I_k if m_k is in F, else 0."],
     notes=["4 variables on an 8:1 MUX: use A,B,C as selects; each data input gets 0, 1, D or D'."],
     init={"I5": 1})


def _demux(v):
    d = _b(v, "D")
    idx = _b(v, "S1") * 2 + _b(v, "S0")
    return {f"Y{m}": (d if m == idx else 0) for m in range(4)}


def _demux_read(v, o):
    idx = _b(v, "S1") * 2 + _b(v, "S0")
    return [f"Select = {idx:02b} = {idx}: the data bit D = {_b(v, 'D')} goes to line Y{idx} only"]


def _demux_net():
    return Net(
        [IN("D", 0.3), IN("S1", 1.8), IN("S0", 3.0)],
        [G("n1", "NOT", ["S1"], 1, 2.45), G("n0", "NOT", ["S0"], 1, 3.6)]
        + [G(f"y{m}", "AND", ["D", "S1" if m & 2 else "n1", "S0" if m & 1 else "n0"], 2, m * 0.9 + 0.1)
           for m in range(4)],
        [OUT(f"Y{m}", f"y{m}", 3, m * 0.9 + 0.1) for m in range(4)])


_add("demux4", "DEMULTIPLEXER 1-TO-4", "ROUTING",
     "A MUX run backwards: ONE input D is sent to ONE of 4 outputs, chosen by the select lines.",
     ["D", "S1", "S0"], ["Y0", "Y1", "Y2", "Y3"], _demux, net=_demux_net(), readout=_demux_read,
     equations=["Y0 = D.S1'S0'   Y1 = D.S1'S0   Y2 = D.S1S0'   Y3 = D.S1S0"],
     notes=["A decoder with an extra 'data' input D: with D = 1 it IS a decoder."], init={"D": 1})

GROUPS = ["ARITHMETIC", "CODES", "ROUTING"]


# ------------------------------------------------------------------
# NOTES TEXT (shown on the notebook T page; headings ALL CAPS)
# ------------------------------------------------------------------
def notes_lines():
    out = ["COMBINATIONAL CIRCUITS",
           "- Output depends ONLY on the inputs right now. No memory (that is a sequential circuit).",
           "- Open the lab with T. LEFT / RIGHT change circuit, 1-9 flip inputs."]
    for s in SIMS:
        out.append(s["name"])
        out.append("- " + s["purpose"])
        for e in s["equations"]:
            out.append("- " + e)
        if s["table"] == "auto" and len(s["tin"]) <= 4:
            for o in s["outs"][:3]:
                m = minterms(s, o)
                if m and len(m) < (1 << len(s["tin"])):
                    out.append(f"- {o} is 1 for minterms: Sum m(" + ", ".join(str(x) for x in m) + ")")
        for e in s["notes"]:
            out.append("- " + e)
    return out


# ------------------------------------------------------------------
# VIEW HELPERS (used by the lab and by the course)
# ------------------------------------------------------------------
def render_sim(screen, sim, area, vals, pal, fonts, hits=None, types=None,
               mask_outputs=False, slot_hover=None, active=None, in_keys=True):
    """Draw the circuit part of a simulator into area.  Returns draw info."""
    if sim["draw"] is not None:
        kw = {"hits": hits, "mask_outputs": mask_outputs}
        if sim["id"] in ("add4", "addsub"):
            kw["active"] = active
        return sim["draw"](screen, area, vals, pal, fonts, **kw)
    net = sim["net"]
    full = net.evaluate({k: vals.get(k, 0) for k in sim["inputs"]}, types)
    return draw_net(screen, net, area, full, pal, fonts, hits=hits, types=types,
                    mask_outputs=mask_outputs, slot_hover=slot_hover, in_keys=in_keys)


def table_view(sim, vals):
    """headers, rows (strings), current row index."""
    if sim["table"] is None:
        return None
    if sim["table"] != "auto":
        headers, rows = sim["table"]
        sel = 0
        for s in headers[:-1]:
            sel = sel * 2 + _b(vals, s)
        return headers, rows, sel
    rows_ = table_rows(sim)
    headers = list(sim["tin"]) + list(sim["outs"])
    rows = [tuple(c) + tuple(o) for c, o in rows_]
    return headers, rows, row_index(sim, vals)


# ------------------------------------------------------------------
# THE NOTEBOOK LAB
# ------------------------------------------------------------------
class CombLab:
    """State and drawing of the notebook lab. The notebook owns one instance."""

    def __init__(self):
        self.i = 0
        self.vals = default_vals(SIMS[0])
        self.hits = []
        self.nav = []

    @property
    def sim(self):
        return SIMS[self.i]

    def go(self, delta):
        self.i = (self.i + delta) % len(SIMS)
        self.vals = default_vals(self.sim)

    def reset(self):
        self.vals = default_vals(self.sim)

    def toggle(self, name):
        if name in self.vals or name in self.sim["inputs"]:
            self.vals[name] = 1 - self.vals.get(name, 0)

    def handle_key(self, event):
        k = event.key
        if k == pygame.K_LEFT:
            self.go(-1)
            return True
        if k == pygame.K_RIGHT:
            self.go(1)
            return True
        if k == pygame.K_r:
            self.reset()
            return True
        order = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6,
                 pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0, pygame.K_MINUS, pygame.K_EQUALS]
        kp = [pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4, pygame.K_KP5, pygame.K_KP6,
              pygame.K_KP7, pygame.K_KP8, pygame.K_KP9, pygame.K_KP0]
        idx = None
        if k in order:
            idx = order.index(k)
        elif k in kp:
            idx = kp.index(k)
        if idx is not None:
            names = self._key_names()
            if idx < len(names):
                self.toggle(names[idx])
            return True
        return k in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d)

    def _key_names(self):
        sim = self.sim
        if sim["net"] is not None and sim["draw"] is None:
            return [i["name"] for i in sim["net"].inputs]
        if sim["id"] in ("add4", "addsub"):
            return sim["inputs"]
        return sim["inputs"]

    def handle_click(self, pos):
        for rect, action in self.nav:
            if rect.collidepoint(pos):
                self.go(action)
                return True
        for rect, action in self.hits:
            if rect.collidepoint(pos) and action[0] == "in":
                self.toggle(action[1])
                return True
        return False

    def draw(self, screen, content, bottom, fonts, pal=PAPER):
        """content = notebook content rect; bottom = y where the lab must stop."""
        sim = self.sim
        self.hits, self.nav = [], []
        f_body, f_small, f_tiny = fonts["body"], fonts["small"], fonts["tiny"]
        x, y, w = content.x + 3, content.y + 2, content.width - 6
        # title row
        prev_r = pygame.Rect(content.right - 214, y, 100, 24)
        next_r = pygame.Rect(content.right - 108, y, 100, 24)
        for r, lab, d in ((prev_r, "< PREV", -1), (next_r, "NEXT >", 1)):
            pygame.draw.rect(screen, (205, 208, 210), r)
            pygame.draw.rect(screen, pal["ink"], r, 2)
            _text(screen, f_tiny, lab, pal["ink"], center=r.center)
            self.nav.append((r, d))
        title = f_body.render(sim["name"], True, pal["ink"])
        scale = min(1.0, (prev_r.x - x - 8) / max(1, title.get_width()))
        if scale < 1.0:
            title = pygame.transform.smoothscale(title, (int(title.get_width() * scale),
                                                         int(title.get_height() * scale)))
        screen.blit(title, (x, y))
        _text(screen, f_tiny, f"{sim['group']}   {self.i + 1}/{len(SIMS)}", pal["accent"],
              topleft=(x, y + 24))
        pygame.draw.line(screen, (156, 163, 168), (x, y + 38), (x + w, y + 38), 2)
        yy = y + 44
        for line in wrap(f_tiny, "WHAT IS IT FOR?  " + sim["purpose"], w)[:3]:
            _text(screen, f_tiny, line, pal["ink"], topleft=(x, yy))
            yy += 15
        yy += 4
        tv = table_view(sim, self.vals)
        tab_w = 0
        if tv is not None:
            tab_w = min(250, table_col_width(tv[0], tv[1], fonts) * len(tv[0]) + 10)
        circ = pygame.Rect(x, yy, w - tab_w - (8 if tab_w else 0), bottom - yy - 74)
        pygame.draw.rect(screen, (200, 203, 206), circ)
        pygame.draw.rect(screen, (156, 163, 168), circ, 2)
        render_sim(screen, sim, circ.inflate(-4, -4), self.vals, pal, fonts, hits=self.hits)
        if tv is not None:
            headers, rows, cur = tv
            trect = pygame.Rect(circ.right + 8, yy, tab_w, circ.h)
            draw_table(screen, trect, headers, rows, cur, pal, fonts)
        # readout
        o = sim_outs(sim, self.vals)
        ry = circ.bottom + 6
        lines = sim["readout"](self.vals, o) if sim["readout"] else []
        for line in lines[:3]:
            for sub in wrap(f_tiny, line, w)[:2]:
                _text(screen, f_tiny, sub, pal["ink"], topleft=(x, ry))
                ry += 15
        if sim["equations"]:
            eq = "   |   ".join(sim["equations"][:2])
            for sub in wrap(f_tiny, eq, w)[:2]:
                _text(screen, f_tiny, sub, pal["accent"], topleft=(x, ry))
                ry += 15
        return True
