import pygame


class ScrollBox:
    """Scrollable paragraph box. UP/DOWN keys and the mouse wheel scroll
    it. A thin scrollbar appears only when the text doesn't fit."""

    STEP = 24

    def __init__(self):
        self.offset = 0
        self.max_offset = 0

    def reset(self):
        self.offset = 0

    def handle_event(self, event, rect):
        """Returns True if the event scrolled the box."""
        if event.type == pygame.MOUSEWHEEL:
            if rect.collidepoint(pygame.mouse.get_pos()):
                self.offset -= event.y * self.STEP
                self._clamp()
                return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.offset -= self.STEP
            elif event.key == pygame.K_DOWN:
                self.offset += self.STEP
            elif event.key == pygame.K_PAGEUP:
                self.offset -= rect.height - self.STEP
            elif event.key == pygame.K_PAGEDOWN:
                self.offset += rect.height - self.STEP
            else:
                return False
            self._clamp()
            return True
        return False

    def _clamp(self):
        self.offset = max(0, min(self.offset, self.max_offset))

    @staticmethod
    def _wrap(text, font, width):
        lines, line = [], ""
        for word in text.split():
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def draw(self, screen, rect, paragraphs, font, colour,
             line_h=None, para_gap=8, scroll_colour=(70, 150, 175)):
        """Draw `paragraphs` (list of strings) clipped inside `rect`."""
        line_h = line_h or font.get_linesize()
        text_w = rect.width - 14            # room for the scrollbar

        lines = []
        for para in paragraphs:
            lines.extend(self._wrap(para, font, text_w))
            lines.append(None)              # gap between paragraphs
        total_h = sum(para_gap if ln is None else line_h for ln in lines)

        self.max_offset = max(0, total_h - rect.height)
        self._clamp()

        old_clip = screen.get_clip()
        screen.set_clip(rect)
        y = rect.y - self.offset
        for ln in lines:
            if ln is None:
                y += para_gap
                continue
            if rect.y - line_h < y < rect.bottom:
                screen.blit(font.render(ln, True, colour), (rect.x, y))
            y += line_h
        screen.set_clip(old_clip)

        # Scrollbar: only drawn when the text overflows.
        if self.max_offset > 0:
            track = pygame.Rect(rect.right - 5, rect.y, 4, rect.height)
            pygame.draw.rect(screen, (20, 45, 62), track)
            thumb_h = max(24, int(rect.height * rect.height / total_h))
            ratio = self.offset / self.max_offset
            thumb_y = rect.y + int((rect.height - thumb_h) * ratio)
            pygame.draw.rect(
                screen, scroll_colour, (track.x, thumb_y, 4, thumb_h)
            )