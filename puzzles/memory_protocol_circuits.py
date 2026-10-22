# puzzles/memory_protocol_circuits.py
# Level 3 add-on. Adds two steps AFTER the original "probe" step:
#
#   PROBE    (memory_protocol.py: map the lamp with A/B/C/D)
#   DIAGRAM  the player DRAWS their notebook as a state diagram
#            (click state, click target state, press the button letter),
#            then types the SHORTEST button sequence from RED to GREEN
#   BUILD    wire a one-hot sequence lock (AND gates + D flip-flops),
#            clock it by hand, then TEST it against several sequences
#
# Used as a mixin by MemoryProtocolPuzzle. It relies on these members
# of that class:
#   KEYMAP, LAMPS, TRANSITIONS, known, solved, awaiting_exit_confirmation,
#   name(), _font, _text, _wrapped_text, _draw_probe
#
# THE CIRCUIT (one-hot "token" lock)
#   S0 is a constant 1 (the idle RED lamp, always ready).
#   S1.D   = S0 AND A
#   S2.D   = S1 AND B
#   S3.D   = S2 AND A
#   S4.D   = S3 AND C
#   S5.D   = S4 AND D
#   OPEN.D = S5 AND C
# A "token" (a 1) moves one flip-flop per clock tick, but only when the
# right button is held. A wrong button lets the token die. Pressing A
# again restarts it from S0.

import math
import pygame

from puzzles.circuit_engine import Circuit, Component, Workbench
from screen_borders import draw_pixel_monitor

# ---------------------------------------------------------
# COLOURS
# ---------------------------------------------------------

DARK_BLUE = (4, 10, 22)
PANEL_BLUE = (9, 24, 39)
CYAN = (0, 235, 245)
TEAL = (39, 91, 113)
RED = (255, 57, 70)
GREEN = (55, 245, 135)
WHITE = (220, 233, 245)
GREY = (132, 151, 174)
YELLOW = (255, 195, 50)
EDGE = (70, 150, 175)

STATE_ORDER = ["S0", "S1", "S2", "S3", "S4", "S5", "OPEN"]


# ---------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------

class _Layout:
    """Maps the 1400 x 880 design grid onto the monitor panel."""

    def __init__(self, panel):
        self.panel = panel
        self.sx = panel.width / 1400
        self.sy = panel.height / 880
        self.scale = max(0.65, min(self.sx, self.sy, 1.2))

    def X(self, v):
        return int(self.panel.x + v * self.sx)

    def Y(self, v):
        return int(self.panel.y + v * self.sy)

    def W(self, v):
        return max(1, int(v * self.sx))

    def H(self, v):
        return max(1, int(v * self.sy))


def _arrowhead(screen, colour, p_from, p_to, size=11):
    dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
    d = math.hypot(dx, dy) or 1
    ux, uy = dx / d, dy / d
    left = (p_to[0] - ux * size - uy * size * 0.5,
            p_to[1] - uy * size + ux * size * 0.5)
    right = (p_to[0] - ux * size + uy * size * 0.5,
             p_to[1] - uy * size - ux * size * 0.5)
    pygame.draw.polygon(screen, colour, [p_to, left, right])


def _bezier(p0, p1, p2, steps=24):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0],
                    a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def _make_lock_circuit():
    c = Circuit()

    # Constant "idle" state: always 1.
    s0 = c.add(Component("S0", "SOURCE", 0.07, 0.10, "S0", "RED"))
    s0.value = 1

    # The four keypad buttons.
    for letter, ry in zip("ABCD", (0.32, 0.50, 0.68, 0.86)):
        c.add(Component(letter, "SWITCH", 0.07, ry, letter, "BUTTON"))

    # (flip-flop id, lamp colour, x of AND gate, y)
    stages = [
        ("S1", "AMBER", 0.22, 0.27),
        ("S2", "AMBER*", 0.46, 0.27),
        ("S3", "BLUE", 0.70, 0.27),
        ("S4", "BLUE*", 0.22, 0.73),
        ("S5", "VIOLET", 0.46, 0.73),
        ("OPEN", "GREEN", 0.70, 0.73),
    ]
    for i, (name, lamp, rx, ry) in enumerate(stages, start=1):
        gate = f"g{i}"
        c.add(Component(gate, "AND", rx, ry))
        c.add(Component(name, "DFF", rx + 0.12, ry, name, lamp))
        # Pre-wired: AND output -> flip-flop D input.
        c.wires.append((gate, name, 0))

    c.add(Component("LED", "LED", 0.93, 0.73, "OPEN"))
    c.wires.append(("OPEN", "LED", 0))
    return c


# ---------------------------------------------------------
# THE MIXIN
# ---------------------------------------------------------

class MemoryProtocolCircuitMixin:

    SOLUTION = "ABACDC"
    BAD_SEQUENCES = ["ABACDD", "BACDC", "ABACD", "ABAACDC"]

    # ---------------------------------------------------------
    # SETUP
    # ---------------------------------------------------------

    def _init_circuits(self):
        self.phase = "PROBE"            # PROBE -> DIAGRAM -> BUILD
        self.path_input = ""
        self.diagram_message = ""
        self.diagram_color = YELLOW
        self.clue_fragment = None       # for the shared clue notebook

        # DIAGRAM step: drawing sub-stage
        self.diagram_stage = "DRAW"     # DRAW -> PATH
        self.drawn = []                 # [(from_state, letter, to_state)]
        self.pending_from = None
        self.pending_to = None
        self._node_pos = {}
        self._node_r = 30

        self.bench = Workbench(_make_lock_circuit(), allow_wiring=True)
        self.button_rects = {}
        self.build_message = ""
        self.build_color = YELLOW

    def start_diagram_phase(self):
        """Called by press() when the lamp turns GREEN."""
        self.phase = "DIAGRAM"
        self.diagram_stage = "DRAW"
        self.drawn = []
        self.pending_from = None
        self.pending_to = None
        self.path_input = ""
        self.diagram_message = (
            "DRAW YOUR NOTEBOOK: CLICK A STATE, CLICK WHERE THE ARROW "
            "GOES, THEN PRESS ITS BUTTON LETTER."
        )
        self.diagram_color = YELLOW

    def start_build_phase(self):
        self.phase = "BUILD"
        self.clue_fragment = "-".join(self.SOLUTION)
        self.bench.circuit.reset()
        for letter in "ABCD":
            self.bench.circuit.comps[letter].value = 0
        self.build_message = (
            "WIRE EVERY AND GATE, THEN PRESS A-D TO CLOCK THE LOCK."
        )
        self.build_color = YELLOW

    # ---------------------------------------------------------
    # EVENTS (returns True when the event was consumed)
    # ---------------------------------------------------------

    def circuit_handle_event(self, event):
        if (
            self.phase == "PROBE"
            or self.solved
            or self.awaiting_exit_confirmation
        ):
            return False

        if self.phase == "DIAGRAM":
            self._diagram_event(event)
        else:
            self._build_event(event)
        return True

    # ---- DIAGRAM ----

    def _trace(self, path):
        """Follow `path` through the hidden rules. Returns (edges, state)."""
        state = "S0"
        edges = []
        for ch in path:
            if state not in self.TRANSITIONS:
                break
            nxt = self.TRANSITIONS[state][ch]
            edges.append((state, ch, nxt))
            state = nxt
        return edges, state

    def _diagram_event(self, event):
        if self.diagram_stage == "DRAW":
            self._draw_stage_event(event)
        else:
            self._path_event(event)

    def _node_at(self, pos):
        for name, (x, y) in self._node_pos.items():
            if math.hypot(pos[0] - x, pos[1] - y) <= self._node_r:
                return name
        return None

    def _draw_stage_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._node_at(event.pos)
            self.diagram_color = YELLOW
            if hit is None:
                self.pending_from = self.pending_to = None
                self.diagram_message = "CLICK A STATE TO START AN ARROW."
            elif self.pending_from is None or self.pending_to is not None:
                self.pending_from, self.pending_to = hit, None
                self.diagram_message = (
                    f"FROM {self.name(hit)}. NOW CLICK THE STATE THE ARROW "
                    "POINTS TO (SAME STATE AGAIN = LOOP)."
                )
            else:
                self.pending_to = hit
                self.diagram_message = (
                    f"{self.name(self.pending_from)} -> {self.name(hit)}. "
                    "PRESS A, B, C OR D TO LABEL THE ARROW."
                )
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in self.KEYMAP:
            if self.pending_from and self.pending_to:
                edge = (self.pending_from, self.KEYMAP[event.key],
                        self.pending_to)
                # a state has only one arrow per button
                self.drawn = [e for e in self.drawn
                              if not (e[0] == edge[0] and e[1] == edge[1])]
                self.drawn.append(edge)
                self.pending_from = self.pending_to = None
                self.diagram_message = (
                    "ARROW ADDED. DRAW MORE, OR PRESS ENTER TO CHECK."
                )
            else:
                self.diagram_message = "CLICK TWO STATES FIRST."
            self.diagram_color = YELLOW
        elif event.key == pygame.K_BACKSPACE:
            if self.drawn:
                self.drawn.pop()
            self.pending_from = self.pending_to = None
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._check_drawing()

    def _check_drawing(self):
        need = {(f, l, t) for (f, l), t in self.known.items()
                if t != "ALARM"}
        have = set(self.drawn)
        wrong = have - need
        missing = need - have
        self.diagram_color = RED
        if wrong:
            f, l, t = sorted(wrong)[0]
            self.diagram_message = (
                f"{self.name(f)} --{l}--> {self.name(t)} IS NOT IN YOUR "
                "NOTEBOOK. BACKSPACE REMOVES THE LAST ARROW."
            )
        elif missing:
            self.diagram_message = (
                f"{len(missing)} ARROW(S) FROM YOUR NOTEBOOK ARE STILL "
                "MISSING."
            )
        else:
            self.diagram_stage = "PATH"
            self.diagram_message = (
                "DIAGRAM COMPLETE! NOW TYPE THE SHORTEST BUTTON SEQUENCE "
                "FROM RED TO GREEN, THEN PRESS ENTER."
            )
            self.diagram_color = GREEN

    def _path_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in self.KEYMAP:
            if len(self.path_input) < 12:
                self.path_input += self.KEYMAP[event.key]
        elif event.key == pygame.K_BACKSPACE:
            self.path_input = self.path_input[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm_path()

    def _confirm_path(self):
        self.diagram_color = RED

        if not self.path_input:
            self.diagram_message = "TYPE A SEQUENCE FIRST."
            self.diagram_color = YELLOW
        elif self.path_input == self.SOLUTION:
            self.start_build_phase()
        else:
            _, end = self._trace(self.path_input)
            if end == "OPEN":
                self.diagram_message = (
                    "THAT OPENS THE LOCK, BUT IT ISN'T THE SHORTEST ROUTE. "
                    "REMOVE THE DETOURS."
                )
            elif end == "ALARM":
                self.diagram_message = (
                    "THAT PATH TRIPS THE ALARM. FOLLOW THE ARROWS."
                )
            else:
                self.diagram_message = (
                    f"THAT PATH ENDS AT {self.name(end)}, NOT GREEN."
                )

    # ---- BUILD ----

    def _build_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.KEYMAP:
                self._press_button(self.KEYMAP[event.key])
            elif event.key == pygame.K_SPACE:
                self._clock_once()
            elif event.key == pygame.K_r:
                self._reset_build()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.verify_build()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.button_rects.items():
                if rect.collidepoint(event.pos):
                    if name == "CLOCK":
                        self._clock_once()
                    elif name == "RESET":
                        self._reset_build()
                    else:
                        self.verify_build()
                    return

        msg = self.bench.handle_event(event)
        if msg:
            self.build_message = msg
            self.build_color = CYAN

    def _press_button(self, letter):
        """Keyboard A-D: hold ONLY that button and give one clock pulse."""
        circuit = self.bench.circuit
        for l in "ABCD":
            circuit.comps[l].value = 1 if l == letter else 0
        self._clock_once()

    def _clock_once(self):
        circuit = self.bench.circuit
        if not circuit.clock():
            self.build_message = (
                "CLOCK BLOCKED: EVERY AND GATE NEEDS BOTH INPUTS WIRED."
            )
            self.build_color = RED
            return

        active = [f.label for f in circuit.dffs() if f.state == 1]
        if circuit.comps["OPEN"].state == 1:
            self.build_message = (
                f"TICK {circuit.ticks}: OPEN IS HIGH, THE LED IS ON! "
                "PRESS ENTER TO RUN THE FULL TEST."
            )
            self.build_color = GREEN
        elif active:
            self.build_message = (
                f"TICK {circuit.ticks}: ACTIVE STATE: {', '.join(active)}"
            )
            self.build_color = CYAN
        else:
            self.build_message = (
                f"TICK {circuit.ticks}: NO ACTIVE STATE. WRONG BUTTON, "
                "THE SEQUENCE IS LOST. PRESS THE FIRST BUTTON AGAIN."
            )
            self.build_color = YELLOW

    def _reset_build(self):
        circuit = self.bench.circuit
        circuit.reset()
        for letter in "ABCD":
            circuit.comps[letter].value = 0
        self.build_message = "RESET: ALL FLIP-FLOPS CLEARED."
        self.build_color = YELLOW

    def verify_build(self):
        circuit = self.bench.circuit

        # Every gate and flip-flop input must be wired.
        for comp in circuit.comps.values():
            if comp.kind in ("AND", "DFF"):
                for pin in range(comp.n_inputs):
                    if circuit.source_of(comp.id, pin) is None:
                        self.build_message = (
                            "CIRCUIT INCOMPLETE: EVERY AND GATE NEEDS "
                            "BOTH INPUTS WIRED."
                        )
                        self.build_color = RED
                        return

        saved_run = circuit.save_run()
        saved_switches = {l: circuit.comps[l].value for l in "ABCD"}

        def run(seq):
            """Returns (open_at_end, ever_open) or None if unwired."""
            circuit.reset()
            ever = False
            last = 0
            for ch in seq:
                for l in "ABCD":
                    circuit.comps[l].value = 1 if l == ch else 0
                if not circuit.clock():
                    return None
                last = circuit.comps["OPEN"].state
                ever = ever or last == 1
            return last == 1, ever

        problem = None
        good = run(self.SOLUTION)
        if good is None or not good[0]:
            problem = (
                f"TEST FAILED: {'-'.join(self.SOLUTION)} DID NOT OPEN "
                "THE LOCK. CHECK YOUR WIRES AGAINST THE DIAGRAM."
            )
        else:
            for seq in self.BAD_SEQUENCES:
                result = run(seq)
                if result is None or result[1]:
                    problem = (
                        f"TEST FAILED: {'-'.join(seq)} SHOULD NOT "
                        "OPEN THE LOCK."
                    )
                    break

        # Put the player's session back exactly as it was.
        circuit.restore_run(saved_run)
        for l, v in saved_switches.items():
            circuit.comps[l].value = v

        if problem:
            self.build_message = problem
            self.build_color = RED
            return

        total = len(self.BAD_SEQUENCES) + 1
        self.awaiting_exit_confirmation = True
        self.build_message = (
            f"CIRCUIT VERIFIED! {total}/{total} TESTS PASSED: IT OPENS "
            "ONLY ON THE GUARD'S SEQUENCE."
        )
        self.build_color = GREEN

    # ---------------------------------------------------------
    # DRAWING
    # ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "DIAGRAM":
            self._draw_diagram(screen)
        elif self.phase == "BUILD":
            self._draw_build(screen)
        else:
            self._draw_probe(screen)

    def _frame(self, screen, title):
        screen.fill(DARK_BLUE)
        panel = draw_pixel_monitor(screen)
        lay = _Layout(panel)

        blink_on = (pygame.time.get_ticks() // 450) % 2 == 0
        colour = RED if blink_on else (135, 35, 48)
        font = self._font(max(14, int(19 * lay.scale)), True)
        self._text(screen, title, font, colour, lay.X(35), lay.Y(25))
        return lay

    # ---- DIAGRAM screen ----

    def _draw_diagram(self, screen):
        lay = self._frame(
            screen, "■ SECURITY NETWORK // LEVEL THREE // STEP 2 OF 3"
        )
        X, Y, W, H, sc = lay.X, lay.Y, lay.W, lay.H, lay.scale
        drawing = self.diagram_stage == "DRAW"

        intro_font = self._font(max(17, int(25 * sc)), True)
        label_font = self._font(max(13, int(17 * sc)), True)
        state_font = self._font(max(12, int(16 * sc)), True)
        lamp_font = self._font(max(10, int(12 * sc)), True)
        msg_font = self._font(max(13, int(16 * sc)), True)

        intro = (
            "Draw your notebook as a state diagram. Click a state, click "
            "the state it leads to, then press the button letter."
            if drawing else
            "Your diagram is complete. Now find the SHORTEST button "
            "sequence from RED to GREEN."
        )
        self._wrapped_text(
            screen, intro, intro_font, CYAN,
            X(35), Y(67), W(1325), H(33), H(75),
        )

        # In the path stage, highlight the arrows the typed path walks.
        walked, _ = self._trace(self.path_input)
        path_edges = set() if drawing else {(a, ch) for a, ch, _b in walked}

        r = max(30, int(38 * sc))
        ny = Y(330)
        idx = {name: i for i, name in enumerate(STATE_ORDER)}
        pos = {n: (X(120 + i * 193), ny) for i, n in enumerate(STATE_ORDER)}
        self._node_pos, self._node_r = pos, r

        # ---- arrows the player has drawn (nodes go on top) ----
        for frm, ch, to in self.drawn:
            colour = GREEN if (frm, ch) in path_edges else EDGE
            i, j = idx[frm], idx[to]
            x0, y0 = pos[frm]
            x1, y1 = pos[to]

            if i == j:  # self loop above the node
                cx, cy = x0, y0 - r - 14
                pygame.draw.circle(screen, colour, (cx, cy), 16, 3)
                self._text(screen, ch, label_font, colour, cx - 5, cy - 40)

            elif j == i + 1:  # straight forward arrow
                a = (x0 + r + 2, y0 - 8)
                b = (x1 - r - 2, y0 - 8)
                pygame.draw.line(screen, colour, a, b, 3)
                _arrowhead(screen, colour, a, b)
                self._text(
                    screen, ch, label_font, colour,
                    (x0 + x1) // 2 - 5, y0 - 34,
                )

            else:  # arc below the row (back edges / skips)
                span = abs(i - j)
                s = 1 if j > i else -1
                p0 = (x0 + s * 10, y0 + r)
                p2 = (x1 - s * 10, y1 + r)
                p1 = ((x0 + x1) // 2, y0 + r + H(40) + span * H(34))
                pts = _bezier(p0, p1, p2)
                pygame.draw.lines(screen, colour, False, pts, 3)
                _arrowhead(screen, colour, pts[-2], pts[-1])
                mx, my = pts[len(pts) // 2]
                self._text(
                    screen, ch, label_font, colour, int(mx) - 5, int(my) + 4
                )

        # ---- state circles ----
        for name, (x, y) in pos.items():
            lamp_colour, pulsing, lamp_label = self.LAMPS[name]
            pygame.draw.circle(screen, lamp_colour, (x, y), r)
            pygame.draw.circle(screen, WHITE, (x, y), r, 3)
            if pulsing:
                pygame.draw.circle(screen, lamp_colour, (x, y), r + 6, 2)
            if name == self.pending_from:
                pygame.draw.circle(screen, YELLOW, (x, y), r + 12, 3)
            if name == self.pending_to:
                pygame.draw.circle(screen, CYAN, (x, y), r + 12, 3)

            top = state_font.render(name, True, DARK_BLUE)
            low = lamp_font.render(lamp_label, True, DARK_BLUE)
            screen.blit(top, top.get_rect(center=(x, y - 8)))
            screen.blit(low, low.get_rect(center=(x, y + 12)))

        if drawing:
            # ---- the player's notebook, as reference ----
            self._text(
                screen, "YOUR NOTEBOOK (what you observed):",
                label_font, YELLOW, X(35), Y(470),
            )
            lines = []
            for (f, l), t in self.known.items():
                lines.append((
                    f"{self.name(f)} --{l}--> {self.name(t)}",
                    GREY if t == "ALARM" else WHITE,
                ))
            rows = 8
            for n, (text, col) in enumerate(lines[:rows * 3]):
                cx = X(35) + (n // rows) * W(440)
                cy = Y(505) + (n % rows) * H(26)
                self._text(screen, text, lamp_font, col, cx, cy)
            self._text(
                screen, "(Grey lines go to ALARM. Don't draw those.)",
                lamp_font, GREY, X(35), Y(725),
            )
        else:
            self._text(
                screen,
                "(Transitions into ALARM are hidden. Any other button "
                "trips it.)",
                lamp_font, GREY, X(35), Y(515),
            )
            box = pygame.Rect(X(300), Y(560), W(760), H(62))
            pygame.draw.rect(screen, PANEL_BLUE, box)
            pygame.draw.rect(screen, CYAN, box, 3)
            self._text(
                screen, "YOUR PATH:", intro_font, WHITE, X(35), Y(578)
            )
            typed = " - ".join(self.path_input)
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                typed += " _"
            self._text(
                screen, typed, intro_font, YELLOW, box.x + 16, box.y + H(16)
            )

        self._wrapped_text(
            screen, self.diagram_message, msg_font, self.diagram_color,
            X(35), Y(765) if drawing else Y(665),
            W(1330), H(23), H(60),
        )
        hint = (
            "CLICK STATE, CLICK TARGET, PRESS A-D    "
            "BACKSPACE: undo last arrow    ENTER: check"
            if drawing else
            "A-D: type a button    BACKSPACE: delete    ENTER: confirm"
        )
        self._text(screen, hint, lamp_font, GREY, X(35), Y(830))

    # ---- BUILD screen ----

    def _draw_build(self, screen):
        lay = self._frame(
            screen, "■ SECURITY NETWORK // LEVEL THREE // STEP 3 OF 3"
        )
        X, Y, W, H, sc = lay.X, lay.Y, lay.W, lay.H, lay.scale

        intro_font = self._font(max(17, int(25 * sc)), True)
        button_font = self._font(max(14, int(17 * sc)), True)
        info_font = self._font(max(14, int(16 * sc)), True)
        msg_font = self._font(max(13, int(16 * sc)), True)
        small_font = self._font(max(11, int(13 * sc)), True)
        done_font = self._font(max(20, int(27 * sc)), True)

        self._wrapped_text(
            screen,
            "Now BUILD the machine. Each AND gate moves the token to the "
            "next state when the right button is pressed.",
            intro_font, CYAN, X(35), Y(67), W(1325), H(33), H(75),
        )

        # Workbench
        self.bench.area = pygame.Rect(X(35), Y(150), W(1330), H(450))
        self.bench.draw(screen)

        circuit = self.bench.circuit
        active = [f.label for f in circuit.dffs() if f.state == 1]

        # Control buttons
        labels = [("CLOCK", "SPACE"), ("RESET", "R"), ("TEST", "ENTER")]
        bw, bh, gap = W(250), H(52), W(25)
        self.button_rects = {}
        mouse = pygame.mouse.get_pos()
        for i, (name, key) in enumerate(labels):
            rect = pygame.Rect(X(35) + i * (bw + gap), Y(625), bw, bh)
            self.button_rects[name] = rect
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(screen, PANEL_BLUE, rect)
            pygame.draw.rect(screen, CYAN if hover else YELLOW, rect, 3)
            text = button_font.render(f"{name}  {key}", True, YELLOW)
            screen.blit(text, text.get_rect(center=rect.center))

        info_x = X(35) + 3 * (bw + gap) + W(15)
        self._text(
            screen, f"CLOCK TICKS: {circuit.ticks}",
            info_font, WHITE, info_x, Y(630),
        )
        self._text(
            screen, f"ACTIVE: {', '.join(active) if active else 'NONE'}",
            info_font, YELLOW, info_x, Y(630) + H(26),
        )

        # Status / completion
        status_x, status_y = X(35), Y(700)
        if self.awaiting_exit_confirmation:
            self._text(
                screen, "CIRCUIT VERIFIED!", done_font, GREEN,
                status_x, status_y,
            )
            self._wrapped_text(
                screen, self.build_message, msg_font, WHITE,
                status_x, status_y + H(38), W(1330), H(23), H(45),
            )
            self._text(
                screen, "PRESS ENTER TO RETURN TO THE LAB",
                msg_font, YELLOW, status_x, status_y + H(88),
            )
        else:
            self._wrapped_text(
                screen, self.build_message, msg_font, self.build_color,
                status_x, status_y, W(1330), H(23), H(80),
            )
            self._wrapped_text(
                screen,
                "A-D: press that button (one clock tick)   Click a switch "
                "to flip it   Drag from a pin to a pin to wire   "
                "Right-click an input pin to remove a wire",
                small_font, GREY, status_x, Y(800), W(1330), H(18), H(45),
            )