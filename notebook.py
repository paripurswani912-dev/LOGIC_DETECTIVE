
# notebook.py
# Logic Detective — NEXUS-9 Investigation Notebook
#
# Controls:
#   N                 Open / close notebook (game loops must forward N)
#   UP / DOWN         Select a notebook button
#   ENTER             Open selected page
#   ESC / BACKSPACE   Return to index / close notebook
#   Mouse click       Select buttons and open pages
#
# Integration:
#   notebook = DetectiveNotebook()
#   notebook.handle_event(event)
#   notebook.draw(screen)
#   notebook.complete_level(level_id, notes)

import pygame


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
GOLD = (229, 174, 74)
WHITE = (242, 241, 231)
LOCKED = (99, 103, 111)
PAGE_LINE = (156, 163, 168)


class DetectiveNotebook:

    LEVELS = [
        ("level_one", "LEVEL ONE", "Logic Lock"),
        ("level_two", "LEVEL TWO", "Hidden Transmission"),
        ("level_three", "LEVEL THREE", "Memory Protocol"),
        ("level_four", "LEVEL FOUR", "Final Override"),
        ("level_five", "LEVEL FIVE", "Logic Architect"),
        ("level_six", "LEVEL SIX", "Signal Breaker"),
    ]

    def __init__(self):
        # One source of truth for the open state.
        self.open = False

        # Compatibility with existing code that checks is_open.
        # Both attributes are kept synchronised by toggle() and close().
        self.is_open = False

        self.page = "index"
        self.selected_index = 0
        self.selected_level = None

        self.level_status = {
            level_id: {
                "unlocked": index == 0,
                "solved": False,
                "notes": [],
            }
            for index, (level_id, _, _) in enumerate(self.LEVELS)
        }

        self.reference_topics = [
            "LOGIC GATES",
            "NUMBER SYSTEMS",
            "STATE MACHINES",
            "BOOLEAN ALGEBRA",
            "KARNAUGH MAPS",
            "REGISTERS AND LFSRs",
        ]

        self.reference_notes = {
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
                "Binary uses the digits 0 and 1.",
                "Binary place values are powers of two.",
                "Gray code changes one bit between adjacent values.",
                "For Gray-to-binary conversion, the first binary bit",
                "matches the first Gray bit. Each next binary bit is",
                "the previous binary bit XOR the current Gray bit.",
            ],
            "STATE MACHINES": [
                "A state machine changes state according to its input.",
                "A transition describes movement from one state to another.",
                "Track the current state, input, and resulting state.",
            ],
            "BOOLEAN ALGEBRA": [
                "Boolean variables take values 0 or 1.",
                "AND is commonly written as A·B.",
                "OR is commonly written as A+B.",
                "NOT is written as A' or ¬A.",
                "Evaluate parentheses before surrounding operations.",
            ],
            "KARNAUGH MAPS": [
                "Adjacent cells differ in one variable.",
                "Group adjacent 1s in powers of two.",
                "Use the largest valid groups where possible.",
                "Groups may wrap across opposite edges.",
                "A variable that changes within a group is eliminated.",
            ],
            "REGISTERS AND LFSRs": [
                "A register stores a sequence of binary bits.",
                "A shift moves the stored bits to new positions.",
                "An LFSR uses feedback, commonly formed with XOR.",
                "The seed and feedback taps affect the generated sequence.",
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
        self.body_font = self._font(15)
        self.small_font = self._font(12)

        self.buttons = []
        self.back_button = None

        # Interactive Logic Gates reference
        self.gate_names = [
            "AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT"
        ]
        self.selected_gate = "AND"
        self.gate_a = 0
        self.gate_b = 0

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

    def complete_level(self, level_id, notes):
        """Save the detective's findings and unlock the next level."""
        if level_id not in self.level_status:
            return

        status = self.level_status[level_id]
        status["solved"] = True
        status["unlocked"] = True
        status["notes"] = list(notes)

        level_ids = [item[0] for item in self.LEVELS]
        index = level_ids.index(level_id)

        if index + 1 < len(level_ids):
            next_id = level_ids[index + 1]
            self.level_status[next_id]["unlocked"] = True

    def set_level_unlocked(self, level_id, unlocked=True):
        if level_id in self.level_status:
            self.level_status[level_id]["unlocked"] = unlocked

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

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                self.close()
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

            if event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)
                return True

            if event.key in (pygame.K_DOWN, pygame.K_s):
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
            self.page = "level"

        elif action_type == "reference":
            self.page = "reference_index"
            self.selected_index = 0

        elif action_type == "topic":
            self.selected_level = value
            self.page = "reference_topic"
            self.selected_index = 0

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

        # Make the notebook fill more of the screen.
        # Original notebook size — restore this
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

        self._draw_button(
            screen,
            reference_rect,
            "TEST THE LOGIC",
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
        level_id = self.selected_level

        if level_id not in self.level_status:
            self.page = "index"
            return

        status = self.level_status[level_id]
        _, heading, subtitle = next(
            item for item in self.LEVELS if item[0] == level_id
        )

        title = self._fit_text(heading, content.width, 22, INK)
        screen.blit(title, (content.x + 3, content.y + 2))

        subtitle_surface = self._fit_text(
            subtitle, content.width, 14, MUTED
        )
        screen.blit(subtitle_surface, (content.x + 3, content.y + 32))

        pygame.draw.line(
            screen,
            PAGE_LINE,
            (content.x + 2, content.y + 55),
            (content.right - 2, content.y + 55),
            2,
        )

        y = content.y + 69
        max_y = self.back_button.y - 12

        if not status["unlocked"]:
            self._text(
                screen, "THIS CASE FILE IS SEALED.",
                content.x + 3, y, LOCKED, self.body_font,
            )
            self._text(
                screen,
                "Resolve the previous investigation to access it.",
                content.x + 3, y + 28, MUTED, self.small_font,
            )

        elif not status["solved"]:
            self._text(
                screen, "NO NOTES RECORDED YET.",
                content.x + 3, y, INK, self.body_font,
            )
            self._text(
                screen,
                "Solve this level to record your discovery.",
                content.x + 3, y + 30, MUTED, self.small_font,
            )

        else:
            self._text(
                screen, "DETECTIVE'S FINDINGS",
                content.x + 3, y, INK, self.body_font,
            )
            y += 29
            line_gap = 20

            for note in status["notes"]:
                wrapped = self._wrap_text(
                    str(note), content.width - 12, self.small_font
                )

                for line in wrapped:
                    if y + line_gap > max_y:
                        break

                    self._text(
                        screen, line,
                        content.x + 7, y, INK, self.small_font,
                    )
                    y += line_gap

                y += 5

                if y >= max_y:
                    break

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

        title = self._fit_text(topic, content.width, 20, INK)
        screen.blit(title, (content.x + 3, content.y + 2))

        pygame.draw.line(
            screen,
            PAGE_LINE,
            (content.x + 2, content.y + 35),
            (content.right - 2, content.y + 35),
            2,
        )

        y = content.y + 49
        line_gap = 22
        max_y = self.back_button.y - 10

        for note in self.reference_notes.get(topic, []):
            wrapped = self._wrap_text(
                note, content.width - 10, self.small_font
            )

            for line in wrapped:
                if y + line_gap > max_y:
                    break

                self._text(
                    screen, line,
                    content.x + 5, y, INK, self.small_font,
                )
                y += line_gap

            y += 4

            if y >= max_y:
                break

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

    def _draw_back_button(self, screen):
        if self.back_button is None:
            return

        self._draw_button(
            screen,
            self.back_button,
            "BACK [B]",
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
