
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
            "AND", "OR", "XOR", "NAND", "NOR", "XNOR"
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

            if event.key in (pygame.K_LEFT, pygame.K_a):
                if self.page == "reference_topic" and (
                    self.selected_level == "LOGIC GATES"
                ):
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
        return 0


    def _draw_logic_gates_page(self, screen, content):
        self.buttons = []

        title = self._fit_text(
            "LOGIC GATES", content.width, 22, INK
        )
        screen.blit(title, (content.x + 3, content.y + 2))

        pygame.draw.line(
            screen, PAGE_LINE,
            (content.x + 2, content.y + 35),
            (content.right - 2, content.y + 35),
            2,
        )

        self._text(
            screen,
            "Select a gate, then change inputs A and B.",
            content.x + 3, content.y + 45, INK, self.small_font,
        )

        # Six selectable gate buttons arranged in two rows.
        columns = 3
        gap_x = 10
        gap_y = 9
        button_w = (content.width - 6 - gap_x * 2) // columns
        button_h = 35
        start_x = content.x + 3
        start_y = content.y + 75

        for index, gate in enumerate(self.gate_names):
            row = index // columns
            col = index % columns

            rect = pygame.Rect(
                start_x + col * (button_w + gap_x),
                start_y + row * (button_h + gap_y),
                button_w,
                button_h,
            )

            selected = gate == self.selected_gate

            self._draw_button(
                screen, rect, gate, selected
            )

            self.buttons.append((rect, ("gate", gate)))

        controls_y = start_y + 2 * (button_h + gap_y) + 12

        self._text(
            screen, "INPUT SWITCHES",
            content.x + 3, controls_y, INK, self.body_font,
        )

        switch_y = controls_y + 29
        switch_w = (content.width - 16) // 2
        switch_h = 43

        a_rect = pygame.Rect(
            content.x + 3, switch_y, switch_w, switch_h
        )
        b_rect = pygame.Rect(
            content.x + 10 + switch_w, switch_y,
            switch_w, switch_h
        )

        self._draw_button(
            screen, a_rect, f"[A] INPUT: {self.gate_a}",
            len(self.buttons) == self.selected_index,
        )
        self.buttons.append((a_rect, ("input_a", None)))

        self._draw_button(
            screen, b_rect, f"[B] INPUT: {self.gate_b}",
            len(self.buttons) == self.selected_index,
        )
        self.buttons.append((b_rect, ("input_b", None)))

        output = self._gate_output(
            self.selected_gate, self.gate_a, self.gate_b
        )

        output_y = switch_y + switch_h + 17

        self._text(
            screen, f"SELECTED GATE: {self.selected_gate}",
            content.x + 3, output_y, INK, self.body_font,
        )

        self._text(
            screen, f"OUTPUT: {output}",
            content.x + 3, output_y + 29, INK, self.body_font,
        )

        # Truth table
        table_y = output_y + 68
        self._text(
            screen, "TRUTH TABLE",
            content.x + 3, table_y, INK, self.body_font,
        )

        table_x = content.x + 3
        table_y += 28
        table_w = content.width - 6
        col_w = table_w // 3
        row_h = 30

        headers = ["A", "B", "Y"]

        for col, heading in enumerate(headers):
            cell = pygame.Rect(
                table_x + col * col_w, table_y, col_w, row_h
            )
            pygame.draw.rect(screen, PAPER_LIGHT, cell)
            pygame.draw.rect(screen, PAGE_LINE, cell, 2)

            self._text(
                screen, heading,
                cell.x + 8, cell.y + 5, INK, self.small_font,
            )

        for row, (a, b) in enumerate(
            [(0, 0), (0, 1), (1, 0), (1, 1)]
        ):
            y_value = self._gate_output(self.selected_gate, a, b)
            y = table_y + (row + 1) * row_h

            values = [a, b, y_value]

            for col, value in enumerate(values):
                cell = pygame.Rect(
                    table_x + col * col_w, y, col_w, row_h
                )

                pygame.draw.rect(screen, PAPER, cell)
                pygame.draw.rect(screen, PAGE_LINE, cell, 1)

                self._text(
                    screen, str(value),
                    cell.x + 8, cell.y + 5, INK, self.small_font,
                )

        self._text(
            screen,
            "Click the buttons or use UP/DOWN and ENTER.",
            content.x + 3, table_y + 5 * row_h + 8,
            MUTED, self.small_font,
        )

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
