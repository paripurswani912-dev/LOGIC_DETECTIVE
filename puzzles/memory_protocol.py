
import random
import pygame
import settings
from puzzles.base_puzzle import BasePuzzle


class MemoryProtocolPuzzle(BasePuzzle):
    """
    FSM-based security panel.

    - Eight physical-style toggle switches
    - Four randomly selected target colors
    - Randomized switch positions
    - Correct activation advances the FSM
    - Incorrect activation resets the FSM to S0
    """

    def __init__(self):
        super().__init__()

        self.title_font = pygame.font.Font(None, 46)
        self.heading_font = pygame.font.Font(None, 29)
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)

        self.switch_colors = {
            "RED": (235, 75, 75),
            "BLUE": (70, 150, 245),
            "GREEN": (70, 210, 120),
            "YELLOW": (245, 205, 75),
            "PURPLE": (175, 105, 230),
            "ORANGE": (245, 145, 65),
            "CYAN": (70, 220, 230),
            "WHITE": (225, 230, 240),
        }

        self.panel_rect = pygame.Rect(90, 175, 820, 310)
        self.switch_rects = {}
        self.switches = {}
        self.state_number = 0
        self.message_color = settings.WHITE

        self.start_new_attempt()

    def start_new_attempt(self):
        """Generate a new sequence and a new switch arrangement."""

        all_colors = list(self.switch_colors.keys())

        # Four different colors form the required sequence.
        self.sequence = random.sample(all_colors, 4)

        # All eight switches appear in a randomized arrangement.
        self.switch_order = all_colors[:]
        random.shuffle(self.switch_order)

        self.switches = {
            color: False for color in all_colors
        }

        self.switch_rects = {}

        # Four switches per row.
        start_x = 125
        start_y = 225
        switch_w = 165
        switch_h = 105
        gap_x = 30
        gap_y = 35

        for index, color in enumerate(self.switch_order):
            row = index // 4
            column = index % 4

            x = start_x + column * (switch_w + gap_x)
            y = start_y + row * (switch_h + gap_y)

            self.switch_rects[color] = pygame.Rect(
                x, y, switch_w, switch_h
            )

        self.state_number = 0
        self.solved = False
        self.message = (
            "Read the maintenance record, then activate the switches."
        )
        self.message_color = settings.WHITE

    def handle_event(self, event):
        if self.solved:
            return

        # Click a switch with the mouse.
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for color, rect in self.switch_rects.items():
                    if rect.collidepoint(event.pos):
                        self.toggle_switch(color)
                        return

        # Keyboard shortcuts: 1 to 8 correspond to the displayed
        # switch positions, reading left-to-right, top-to-bottom.
        if event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_8:
                index = event.key - pygame.K_1

                if index < len(self.switch_order):
                    color = self.switch_order[index]
                    self.toggle_switch(color)

            elif event.key == pygame.K_r:
                # Retry with a newly randomized sequence and layout.
                self.start_new_attempt()

    def toggle_switch(self, color):
        """Flip a lever and process its ON activation."""

        if self.solved:
            return

        # Turn the physical-style switch ON or OFF.
        self.switches[color] = not self.switches[color]

        # Turning a switch OFF does not count as an FSM input.
        if not self.switches[color]:
            self.message = f"{color} switch turned OFF."
            self.message_color = settings.GREY
            return

        expected_color = self.sequence[self.state_number]

        if color == expected_color:
            self.state_number += 1

            if self.state_number == len(self.sequence):
                self.solved = True
                self.message = (
                    "ACCESS GRANTED! FSM reached the final state."
                )
                self.message_color = settings.GREEN
            else:
                next_color = self.sequence[self.state_number]
                self.message = (
                    f"Correct! FSM advanced to S{self.state_number}. "
                    f"Next required signal: {next_color}."
                )
                self.message_color = settings.GREEN

        else:
            # Incorrect input: FSM returns to its initial state.
            self.state_number = 0

            # Security reset returns every lever to OFF.
            for switch_color in self.switches:
                self.switches[switch_color] = False

            self.message = (
                f"WRONG INPUT: {color}! FSM reset to S0. "
                "All switches reset. Try again."
            )
            self.message_color = settings.RED

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(settings.DARK_BLUE)

        # Title
        title = self.title_font.render(
            "MEMORY PROTOCOL", True, settings.CYAN
        )
        screen.blit(
            title, title.get_rect(center=(500, 45))
        )

        subtitle = self.small_font.render(
            "NEXUS-9 SECURITY CONTROL PANEL",
            True, settings.GREY
        )
        screen.blit(
            subtitle, subtitle.get_rect(center=(500, 82))
        )

        # Temporary maintenance record.
        # Later, this can be moved into the document/notes system.
        record_title = self.heading_font.render(
            "MAINTENANCE RECORD — REQUIRED SIGNALS",
            True, settings.YELLOW
        )
        screen.blit(
            record_title, record_title.get_rect(center=(500, 125))
        )

        record_text = "  ->  ".join(self.sequence)
        record = self.font.render(
            record_text, True, settings.WHITE
        )
        screen.blit(
            record, record.get_rect(center=(500, 153))
        )

        # Control panel
        pygame.draw.rect(
            screen, settings.PANEL_BLUE,
            self.panel_rect, border_radius=12
        )
        pygame.draw.rect(
            screen, settings.GREY,
            self.panel_rect, width=2, border_radius=12
        )

        # Eight switches
        for index, color in enumerate(self.switch_order):
            rect = self.switch_rects[color]
            color_value = self.switch_colors[color]
            is_on = self.switches[color]

            # Switch housing
            pygame.draw.rect(
                screen, settings.DARK_BLUE,
                rect, border_radius=9
            )
            pygame.draw.rect(
                screen, color_value if is_on else settings.GREY,
                rect, width=2, border_radius=9
            )

            # Color indicator
            indicator_center = (rect.centerx, rect.y + 22)
            indicator_color = (
                color_value if is_on else (65, 75, 90)
            )

            pygame.draw.circle(
                screen, indicator_color, indicator_center, 8
            )

            # Lever base
            lever_base = pygame.Rect(
                rect.centerx - 25,
                rect.y + 38,
                50, 36
            )
            pygame.draw.rect(
                screen, (45, 55, 70),
                lever_base, border_radius=6
            )

            # Lever handle tilts according to ON/OFF state.
            if is_on:
                lever_end = (
                    rect.centerx + 13, rect.y + 43
                )
            else:
                lever_end = (
                    rect.centerx - 13, rect.y + 68
                )

            pygame.draw.line(
                screen, color_value,
                (rect.centerx, rect.y + 58),
                lever_end, 7
            )
            pygame.draw.circle(
                screen, color_value, lever_end, 7
            )

            # Switch label and state
            label = self.small_font.render(
                f"{index + 1}. {color}",
                True, settings.WHITE
            )
            screen.blit(
                label,
                label.get_rect(
                    center=(rect.centerx, rect.bottom - 21)
                )
            )

            state_label = "ON" if is_on else "OFF"
            state_color = color_value if is_on else settings.GREY

            state_text = self.small_font.render(
                state_label, True, state_color
            )
            screen.blit(
                state_text,
                state_text.get_rect(
                    center=(rect.centerx, rect.bottom + 12)
                )
            )

        # FSM progress
        fsm_y = 530
        fsm_label = self.font.render(
            "FSM STATE:", True, settings.WHITE
        )
        screen.blit(fsm_label, (110, fsm_y))

        for state in range(5):
            state_rect = pygame.Rect(
                260 + state * 90, fsm_y - 5, 68, 32
            )

            if state < self.state_number:
                state_color = settings.GREEN
            elif state == self.state_number:
                state_color = settings.CYAN
            else:
                state_color = settings.GREY

            pygame.draw.rect(
                screen, state_color,
                state_rect, width=2, border_radius=5
            )

            state_text = self.small_font.render(
                f"S{state}", True, settings.WHITE
            )
            screen.blit(
                state_text,
                state_text.get_rect(center=state_rect.center)
            )

        # Message
        message = self.small_font.render(
            self.message, True, self.message_color
        )
        screen.blit(
            message, message.get_rect(center=(500, 585))
        )

        instructions = self.small_font.render(
            "Click a lever or press 1-8 to toggle it. "
            "Press R for a new attempt.",
            True, settings.GREY
        )
        screen.blit(
            instructions,
            instructions.get_rect(center=(500, 620))
        )

    def reset_attempt(self):
        super().reset_attempt()
        self.start_new_attempt()
