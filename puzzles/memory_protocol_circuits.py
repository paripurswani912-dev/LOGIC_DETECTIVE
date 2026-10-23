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
#
# WHAT'S NEW IN THIS VERSION (BUILD step)
#   - GLOW: every flip-flop that holds the ball glows in its lamp colour,
#     and the button you press flashes for a moment.
#   - BALL TRACKER: a row of 7 lamps (bottom right) shows where the ball is.
#   - Buttons A-D auto-release after a short moment, like real buttons.
#   - EXPLAIN LINE ("5 year old" style) under the status message:
#       * explains why each wire is needed when you press H
#       * explains what happened after every clock tick
#   - Hints (H) say WHAT to wire and WHY.

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
PURPLE = (190, 120, 255)

STATE_ORDER = ["S0", "S1", "S2", "S3", "S4", "S5", "OPEN"]

# Friendly names used in the explanations.
LAMP_NAME = {
    "S0": "RED", "S1": "AMBER", "S2": "AMBER*", "S3": "BLUE",
    "S4": "BLUE*", "S5": "VIOLET", "OPEN": "GREEN",
}

# Which flip-flop each STEP gate feeds (STEP 1 -> S1, ... STEP 6 -> OPEN).
STAGE_TARGETS = ["S1", "S2", "S3", "S4", "S5", "OPEN"]


def _lamp(state):
    """'AMBER (S1)' style text. The last one reads 'GREEN (OPEN)'."""
    return f"{LAMP_NAME[state]} ({state})"


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


def _glow_rect(screen, rect, colour, strength=1.0):
    """Soft glowing outline around `rect` (rings fade outwards).

    Drawn on a transparent surface so the part underneath stays visible.
    """
    pad = 34
    surf = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
    for i in range(6, 0, -1):               # outer rings first
        grow = i * 4
        alpha = int(min(255, (20 + (7 - i) * 22) * strength))
        ring = pygame.Rect(pad - grow, pad - grow,
                           rect.w + grow * 2, rect.h + grow * 2)
        pygame.draw.rect(surf, (*colour, alpha), ring, 5,
                         border_radius=8 + grow)
    pygame.draw.rect(
        surf, (*colour, 255), pygame.Rect(pad, pad, rect.w, rect.h), 3,
        border_radius=6,
    )
    screen.blit(surf, (rect.x - pad, rect.y - pad))


def _make_lock_circuit():
    c = Circuit()

    # Look: smaller parts, smaller labels, one wire colour.
    c.size_scale = 0.75
    c.font_scale = 0.72
    c.wire_colour = (70, 150, 175)

    # Every wire finds its own free lane. It avoids parts, the captions
    # under them (AMBER, BLUE*, ...) and wires from other buttons.
    c.auto_route = True

    # Constant "idle" state: always 1.
    s0 = c.add(Component("S0", "SOURCE", 0.065, 0.06, "S0", "RED"))
    s0.value = 1

    # The four buttons, evenly spaced below S0.
    for letter, ry in zip("ABCD", (0.24, 0.42, 0.60, 0.78)):
        c.add(Component(letter, "SWITCH", 0.065, ry, letter, "BUTTON"))

    # (flip-flop id, lamp, gate x, row y, flip-flop x)
    stages = [
        ("S1",   "AMBER",  0.20, 0.22, 0.33),
        ("S2",   "AMBER*", 0.46, 0.22, 0.59),
        ("S3",   "BLUE",   0.72, 0.22, 0.85),
        ("S4",   "BLUE*",  0.20, 0.70, 0.33),
        ("S5",   "VIOLET", 0.46, 0.70, 0.59),
        ("OPEN", "GREEN",  0.72, 0.70, 0.85),
    ]
    for i, (name, lamp, gx, ry, fx) in enumerate(stages, start=1):
        gate = f"g{i}"
        # Each gate is captioned STEP 1..6 so it links to the path the
        # player typed (A, B, A, C, D, C).
        c.add(Component(gate, "AND", gx, ry, "", f"STEP {i}"))
        c.add(Component(name, "DFF", fx, ry, name, lamp))
        c.wires.append((gate, name, 0))      # straight: AND -> D

    c.add(Component("LED", "LED", 0.965, 0.70, "OPEN"))
    c.wires.append(("OPEN", "LED", 0))
    return c


# ---------------------------------------------------------
# THE MIXIN
# ---------------------------------------------------------

class MemoryProtocolCircuitMixin:

    SOLUTION = "ABACDC"
    BAD_SEQUENCES = ["ABACDD", "BACDC", "ABACD", "ABAACDC"]

    # (gate, state it listens to, button it needs), in path order A-B-A-C-D-C
    LOCK_WIRES = [
        ("g1", "S0", "A"), ("g2", "S1", "B"), ("g3", "S2", "A"),
        ("g4", "S3", "C"), ("g5", "S4", "D"), ("g6", "S5", "C"),
    ]

    BUILD_INTRO_EXPLAIN = (
        "Think of it like a game with a ball. Each AND gate is a door guard "
        "who only says YES when BOTH of its wires are on. Each box is a "
        "memory box that holds the ball until the next clock tick."
    )

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

        self.bench = Workbench(
            _make_lock_circuit(),
            allow_wiring=True,
            allow_moving=True,
        )
        self.button_rects = {}
        self.build_message = ""
        self.build_color = YELLOW
        self.build_explain = ""         # the "explain it like I'm 5" line
        self.hint_wire = None           # (gate, source, pin) being hinted

        # Glow / feedback state
        self.flash_letter = None        # button that was just pressed
        self.flash_until = 0            # ms timestamp when its glow ends
        self.release_at = 0             # ms timestamp when A-D let go

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
        self.hint_wire = None
        self.flash_letter = None
        self.flash_until = 0
        self.release_at = 0
        self.build_message = (
            "WIRE EVERY AND GATE, THEN PRESS A-D TO CLOCK THE LOCK. "
            "PRESS H FOR A HINT."
        )
        self.build_color = YELLOW
        self.build_explain = self.BUILD_INTRO_EXPLAIN

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
            elif event.key == pygame.K_h:
                self._build_hint()
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

        # The player is using the mouse on the bench (flipping switches,
        # wiring): don't let an old keyboard "button release" undo that.
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.release_at = 0

        msg = self.bench.handle_event(event)
        if msg:
            self.build_message = msg
            self.build_color = CYAN

    # ---- BUILD hints ----

    def _next_missing_wire(self):
        """First wire the player still needs: (gate, source, pin) or None."""
        c = self.bench.circuit
        for gate, state_src, button in self.LOCK_WIRES:
            have = {c.source_of(gate, 0), c.source_of(gate, 1)}
            for src in (state_src, button):
                if src in have:
                    continue
                pin = next((p for p in (0, 1)
                            if c.source_of(gate, p) is None), None)
                if pin is None:   # both pins used: replace a wrong wire
                    pin = next((p for p in (0, 1)
                                if c.source_of(gate, p)
                                not in (state_src, button)), 1)
                return gate, src, pin
        return None

    def _build_hint(self):
        nxt = self._next_missing_wire()
        if nxt is None:
            self.hint_wire = None
            self.build_message = (
                "ALL WIRES ARE IN. PRESS A-D TO CLOCK, THEN ENTER TO TEST."
            )
            self.build_color = GREEN
            self.build_explain = (
                "Everything is connected! Now press the buttons in order "
                "(A, B, A, C, D, C) and watch the glowing ball hop from box "
                "to box. When you are ready, press ENTER to test the lock."
            )
            return

        gate, src, pin = nxt
        n = int(gate[1:])
        _, state_src, button = self.LOCK_WIRES[n - 1]
        target = STAGE_TARGETS[n - 1]
        self.hint_wire = nxt

        if src in "ABCD":
            what = f"BUTTON {src}"
            self.build_explain = (
                f"WHY? This wire is the secret password. The STEP {n} guard "
                f"only lets the ball hop if you press button {button}. "
                f"Press any other button and the guard says NO!"
            )
        else:
            what = f"STATE {src}"
            self.build_explain = (
                f"WHY? This wire tells the STEP {n} guard where the ball "
                f"is right now. The ball must be sitting at {_lamp(state_src)} "
                f"before it is allowed to hop to {_lamp(target)}."
            )

        self.build_message = (
            f"STEP {n}: DRAG FROM THE OUTPUT PIN OF {what} TO THE FLASHING "
            f"DASHED PIN ON THE STEP {n} GATE."
        )
        self.build_color = YELLOW

    def _draw_hint_wire(self, screen):
        if not self.hint_wire:
            return
        c = self.bench.circuit
        gate, src, pin = self.hint_wire
        # Hide the hint once that wire exists.
        if src in {c.source_of(gate, 0), c.source_of(gate, 1)}:
            self.hint_wire = None
            self.build_message = "NICE! THAT WIRE IS IN. PRESS H FOR THE NEXT ONE."
            self.build_color = GREEN
            self.build_explain = (
                "Great job! One more piece of the lock is connected. "
                "Keep going until every guard has two wires."
            )
            return
        p0 = self.bench.out_pin(c.comps[src])
        p1 = self.bench.in_pin(c.comps[gate], pin)

        old_clip = screen.get_clip()
        screen.set_clip(self.bench.area)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        dist = math.hypot(dx, dy) or 1
        d = 0
        while d < dist:
            a, b = d / dist, min(d + 10, dist) / dist
            pygame.draw.line(
                screen, YELLOW,
                (p0[0] + dx * a, p0[1] + dy * a),
                (p0[0] + dx * b, p0[1] + dy * b), 3,
            )
            d += 17
        r = 9 + int(3 * math.sin(pygame.time.get_ticks() / 200))
        for p in (p0, p1):
            pygame.draw.circle(screen, YELLOW, p, r, 2)
        screen.set_clip(old_clip)

    # ---- BUILD simulation ----

    def _press_button(self, letter):
        """Keyboard A-D: hold ONLY that button and give one clock pulse."""
        circuit = self.bench.circuit
        for l in "ABCD":
            circuit.comps[l].value = 1 if l == letter else 0

        # Visual feedback: the button flashes, then lets go by itself.
        now = pygame.time.get_ticks()
        self.flash_letter = letter
        self.flash_until = now + 700
        self.release_at = now + 450

        self._clock_once()

    def _clock_once(self):
        circuit = self.bench.circuit
        held = [l for l in "ABCD" if circuit.comps[l].value == 1]

        if not circuit.clock():
            self.build_message = (
                "CLOCK BLOCKED: EVERY AND GATE NEEDS BOTH INPUTS WIRED."
            )
            self.build_color = RED
            self.build_explain = (
                "A guard with only one wire can't decide anything, so the "
                "clock won't run. Give every STEP gate two wires "
                "(press H and I'll show you which one is missing)."
            )
            return

        active_ids = [f.id for f in circuit.dffs() if f.state == 1]
        active = [f.label for f in circuit.dffs() if f.state == 1]

        if circuit.comps["OPEN"].state == 1:
            self.build_message = (
                f"TICK {circuit.ticks}: OPEN IS HIGH, THE LED IS ON! "
                "PRESS ENTER TO RUN THE FULL TEST."
            )
            self.build_color = GREEN
            self.build_explain = (
                "YOU DID IT! The ball made it all the way to the last box, "
                "so the door unlocks and the lamp turns on. Press ENTER and "
                "I'll check that wrong button patterns can't sneak in."
            )
        elif active:
            self.build_message = (
                f"TICK {circuit.ticks}: ACTIVE STATE: {', '.join(active)}"
            )
            self.build_color = CYAN

            ball = max(active_ids, key=lambda s: STATE_ORDER.index(s)
                       if s in STATE_ORDER else -1)
            if ball in STAGE_TARGETS:
                idx = STAGE_TARGETS.index(ball)
                _, frm, btn = self.LOCK_WIRES[idx]
                text = (
                    f"Yes! The ball was at {_lamp(frm)} and you pressed "
                    f"{btn}, so the guard said OK and the ball hopped to "
                    f"{_lamp(ball)}."
                )
                if idx + 1 < len(self.LOCK_WIRES):
                    text += f" Next, press {self.LOCK_WIRES[idx + 1][2]}."
                self.build_explain = text
            else:
                self.build_explain = "The ball is sitting in a memory box."
        else:
            self.build_message = (
                f"TICK {circuit.ticks}: NO ACTIVE STATE. WRONG BUTTON, "
                "THE SEQUENCE IS LOST. PRESS THE FIRST BUTTON AGAIN."
            )
            self.build_color = YELLOW
            if not held:
                self.build_explain = (
                    "No button was pressed, so every guard said NO and the "
                    "ball vanished. Press a button (A to start) so a guard "
                    "can say YES."
                )
            else:
                self.build_explain = (
                    f"You pressed {held[0]}, but that is not the password "
                    "for where the ball was, so the guard said NO and the "
                    "ball fell off the path. No worries! Press A to put a "
                    "new ball at the start."
                )

    def _reset_build(self):
        circuit = self.bench.circuit
        circuit.reset()
        for letter in "ABCD":
            circuit.comps[letter].value = 0
        self.flash_letter = None
        self.release_at = 0
        self.build_message = "RESET: ALL FLIP-FLOPS CLEARED."
        self.build_color = YELLOW
        self.build_explain = (
            "All the memory boxes forgot the ball. We're back at the "
            "start. Press A to begin the sequence again."
        )

    def verify_build(self):
        circuit = self.bench.circuit

        # Every gate and flip-flop input must be wired.
        for comp in circuit.comps.values():
            if comp.kind in ("AND", "DFF"):
                for pin in range(comp.n_inputs):
                    if circuit.source_of(comp.id, pin) is None:
                        self.build_message = (
                            "CIRCUIT INCOMPLETE: EVERY AND GATE NEEDS "
                            "BOTH INPUTS WIRED. PRESS H FOR A HINT."
                        )
                        self.build_color = RED
                        self.build_explain = (
                            "Some guards are missing a wire. Each STEP gate "
                            "needs one wire for WHERE THE BALL IS and one "
                            "wire for WHICH BUTTON. Press H to be shown."
                        )
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
        explain = ""
        good = run(self.SOLUTION)
        if good is None or not good[0]:
            problem = (
                f"TEST FAILED: {'-'.join(self.SOLUTION)} DID NOT OPEN "
                "THE LOCK. CHECK YOUR WIRES AGAINST THE DIAGRAM."
            )
            explain = (
                "The right password didn't open the door. Maybe a wire "
                "goes to the wrong place. Each STEP gate must listen to the "
                "state BEFORE it and to the right button. Press H for help."
            )
        else:
            for seq in self.BAD_SEQUENCES:
                result = run(seq)
                if result is None or result[1]:
                    problem = (
                        f"TEST FAILED: {'-'.join(seq)} SHOULD NOT "
                        "OPEN THE LOCK."
                    )
                    explain = (
                        "Oh no, the lock opened for the WRONG password! "
                        "That means a guard is listening to the wrong "
                        "button or the wrong state. Check each STEP."
                    )
                    break

        # Put the player's session back exactly as it was.
        circuit.restore_run(saved_run)
        for l, v in saved_switches.items():
            circuit.comps[l].value = v

        if problem:
            self.build_message = problem
            self.build_color = RED
            self.build_explain = explain
            return

        total = len(self.BAD_SEQUENCES) + 1
        self.awaiting_exit_confirmation = True
        self.build_message = (
            f"CIRCUIT VERIFIED! {total}/{total} TESTS PASSED: IT OPENS "
            "ONLY ON THE GUARD'S SEQUENCE."
        )
        self.build_color = GREEN
        self.build_explain = (
            "You built a lock that remembers! The ball only hops forward "
            "on the right button, and any wrong button makes it fall off."
        )

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
            screen, "■ SECURITY NETWORK // LEVEL THREE"
        )
        X, Y, W, H, sc = lay.X, lay.Y, lay.W, lay.H, lay.scale
        drawing = self.diagram_stage == "DRAW"

        intro_font = self._font(max(17, int(25 * sc)), True)
        label_font = self._font(max(13, int(17 * sc)), True)
        state_font = self._font(max(12, int(16 * sc)), True)
        lamp_font = self._font(max(10, int(12 * sc)), True)
        msg_font = self._font(max(13, int(16 * sc)), True)

        intro = (
            "Turn your notes into a map. Click the state an arrow starts "
            "from, click the state it leads to, then press the button "
            "that caused it."
            if drawing else
            "Map complete! Follow the arrows from RED to GREEN and type "
            "the shortest button sequence that gets there."
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

    def _draw_glows(self, screen, lay):
        """Glow every flip-flop that holds the ball + the pressed button."""
        circuit = self.bench.circuit
        now = pygame.time.get_ticks()
        pulse = 0.75 + 0.25 * math.sin(now / 180)

        old_clip = screen.get_clip()
        screen.set_clip(self.bench.area)

        # 1) flip-flops that are holding the ball
        for ff in circuit.dffs():
            if ff.state != 1:
                continue
            p_in = self.bench.in_pin(ff, 0)
            p_out = self.bench.out_pin(ff)
            w = abs(p_out[0] - p_in[0]) + 16
            h = int(w * 0.95)
            cx = (p_in[0] + p_out[0]) // 2
            cy = (p_in[1] + p_out[1]) // 2
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (cx, cy)
            colour = self.LAMPS.get(ff.id, (GREEN, False, ""))[0]
            _glow_rect(screen, rect, colour, pulse)

        # 2) the button that was just pressed
        if self.flash_letter and now < self.flash_until:
            sw = circuit.comps[self.flash_letter]
            p = self.bench.out_pin(sw)
            sc = lay.scale
            w, h = int(90 * sc), int(46 * sc)
            rect = pygame.Rect(p[0] - w, p[1] - h // 2, w, h)
            fade = (self.flash_until - now) / 700
            _glow_rect(screen, rect, YELLOW, 0.4 + 0.8 * fade)
        elif self.flash_letter:
            self.flash_letter = None

        screen.set_clip(old_clip)

    def _draw_ball_tracker(self, screen, lay):
        """Row of 7 lamps: lit lamp = where the ball is right now."""
        X, Y, W, sc = lay.X, lay.Y, lay.W, lay.scale
        circuit = self.bench.circuit
        small = self._font(max(10, int(11 * sc)), True)

        self._text(screen, "WHERE IS THE BALL?", small, GREY,
                   X(1085), Y(672))

        r = max(8, int(12 * sc))
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() / 180)
        for i, name in enumerate(STATE_ORDER):
            cx = X(1100) + i * W(44)
            cy = Y(718)
            if name == "S0":
                lit = True               # S0 is the always-ready start
            else:
                lit = circuit.comps[name].state == 1
            colour = self.LAMPS.get(name, (GREEN, False, ""))[0]
            if lit:
                if name != "S0":
                    glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
                    pygame.draw.circle(
                        glow, (*colour, int(90 * pulse)),
                        (r * 3, r * 3), int(r * 2.2)
                    )
                    screen.blit(glow, (cx - r * 3, cy - r * 3))
                pygame.draw.circle(screen, colour, (cx, cy), r)
                pygame.draw.circle(screen, WHITE, (cx, cy), r, 2)
            else:
                pygame.draw.circle(screen, PANEL_BLUE, (cx, cy), r)
                pygame.draw.circle(screen, TEAL, (cx, cy), r, 2)
            label = small.render(name, True, WHITE if lit else GREY)
            screen.blit(label, label.get_rect(center=(cx, cy + r + 12)))

    # ---- status text helpers ----

    @staticmethod
    def _status_colour(colour):
        """Yellow status messages are shown in purple."""
        return PURPLE if colour == YELLOW else colour

    def _fit_font(self, size):
        if not hasattr(self, "_fit_fonts"):
            self._fit_fonts = {}
        if size not in self._fit_fonts:
            self._fit_fonts[size] = self._font(size, True)
        return self._fit_fonts[size]

    @staticmethod
    def _wrap_to_width(text, font, width):
        lines, current = [], ""
        for word in text.split():
            test = word if not current else current + " " + word
            if font.size(test)[0] <= width or not current:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_fitted_blocks(self, screen, blocks, x, y_top, width,
                            y_bottom, max_size, min_size=12):
        """Draw [(text, colour), ...] one block under the other, using the
        largest font size (max_size down to min_size) that fits the box."""
        blocks = [(t, c) for t, c in blocks if t]
        if not blocks:
            return

        key = (tuple(blocks), width, y_bottom - y_top, max_size)
        if getattr(self, "_fit_key", None) != key:
            avail = y_bottom - y_top
            chosen = None
            for size in range(max_size, min_size - 1, -1):
                font = self._fit_font(size)
                line_h = font.get_linesize() + 2
                gap = line_h // 2
                lines, cur = [], 0
                for text, colour in blocks:
                    for ln in self._wrap_to_width(text, font, width):
                        lines.append((ln, colour, cur))
                        cur += line_h
                    cur += gap
                height = cur - gap
                chosen = (size, lines)
                if height <= avail:
                    break
            self._fit_key = key
            self._fit_result = chosen

        size, lines = self._fit_result
        font = self._fit_font(size)
        for ln, colour, off in lines:
            self._text(screen, ln, font, colour, x, y_top + off)

    def _draw_build(self, screen):
        lay = self._frame(
            screen, "■ SECURITY NETWORK // LEVEL THREE"
        )
        X, Y, W, H, sc = lay.X, lay.Y, lay.W, lay.H, lay.scale

        intro_font = self._font(max(17, int(25 * sc)), True)
        button_font = self._font(max(14, int(17 * sc)), True)
        info_font = self._font(max(14, int(16 * sc)), True)
        done_font = self._font(max(20, int(27 * sc)), True)

        # Keyboard buttons let go by themselves after a moment.
        now = pygame.time.get_ticks()
        if self.release_at and now >= self.release_at:
            for l in "ABCD":
                self.bench.circuit.comps[l].value = 0
            self.release_at = 0

        # Intro text: two lines of 30 design-px each, so it ends by ~Y(125)
        # and never touches the workbench below.
        self._wrapped_text(
            screen,
            "Build the lock. Think of the signal as a ball passed along a "
            "line: each AND gate asks 'is the ball here, and is the right "
            "button pressed?' Press H for a hint.",
            intro_font, CYAN, X(35), Y(60), W(1325), H(30), H(70),
        )

        # Workbench: Y(140) .. Y(660). Starts below the intro text and ends
        # clearly above the CLOCK / RESET / TEST row at Y(685).
        self.bench.area = pygame.Rect(X(15), Y(140), W(1370), H(520))
        self.bench.draw(screen)

        # Glow on top of the parts (active flip-flops + pressed button).
        self._draw_glows(screen, lay)

        # Flashing dashed hint line for the next missing wire (H key).
        self._draw_hint_wire(screen)

        circuit = self.bench.circuit
        active = [f.label for f in circuit.dffs() if f.state == 1]

        # Control buttons
        labels = [("CLOCK", "SPACE"), ("RESET", "R"), ("TEST", "ENTER")]
        bw, bh, gap = W(250), H(52), W(25)
        self.button_rects = {}
        mouse = pygame.mouse.get_pos()
        for i, (name, key) in enumerate(labels):
            rect = pygame.Rect(X(35) + i * (bw + gap), Y(685), bw, bh)
            self.button_rects[name] = rect
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(screen, PANEL_BLUE, rect)
            pygame.draw.rect(screen, CYAN if hover else YELLOW, rect, 3)
            text = button_font.render(f"{name}  {key}", True, YELLOW)
            screen.blit(text, text.get_rect(center=rect.center))

        info_x = X(35) + 3 * (bw + gap) + W(15)
        self._text(
            screen, f"CLOCK TICKS: {circuit.ticks}",
            info_font, WHITE, info_x, Y(690),
        )
        self._text(
            screen, f"ACTIVE: {', '.join(active) if active else 'NONE'}",
            info_font, YELLOW, info_x, Y(690) + H(26),
        )

        # Row of lamps showing where the ball is.
        self._draw_ball_tracker(screen, lay)

        # Status / completion. The text uses the biggest font that still
        # fits between the buttons and the bottom border (it shrinks only
        # when a message is long), so nothing overlaps or runs off screen.
        status_x, status_top = X(35), Y(752)
        status_bottom = Y(864)
        status_w = W(1330)
        max_px = max(15, int(24 * sc))

        if self.awaiting_exit_confirmation:
            self._text(
                screen, "CIRCUIT VERIFIED!", done_font, GREEN,
                status_x, status_top,
            )
            self._draw_fitted_blocks(
                screen,
                [(self.build_message, WHITE),
                 ("PRESS ENTER TO RETURN TO THE LAB", PURPLE)],
                status_x, status_top + H(40), status_w, status_bottom,
                max_px,
            )
        else:
            self._draw_fitted_blocks(
                screen,
                [(self.build_message, self._status_colour(self.build_color)),
                 (self.build_explain, GREEN)],
                status_x, status_top, status_w, status_bottom, max_px,
            )