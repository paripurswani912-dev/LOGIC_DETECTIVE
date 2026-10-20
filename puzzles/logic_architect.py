# Level 5: Logic Architect — 4-variable K-map with don't-cares and wrap-around
#
# Phase 1 (RECONSTRUCT): the player gets a case file of alarm scenes in plain
#   sensor form (A=1 B=0 ...). They must place each scene on a Gray-coded K-map
#   themselves (1 = alarm, X = unknown/don't care, 0 = silent).
# Phase 2 (SIMPLIFY): select groups on the map. Groups may wrap around edges and
#   may use X cells. The final cover must use maximal groups and a MINIMAL
#   number of groups. The solved expression is generated automatically.
import itertools
import pygame
from .base_puzzle import BasePuzzle
import settings


class LogicArchitectPuzzle(BasePuzzle):
    """Reconstruct a 4-variable alarm function from evidence, then simplify it."""

    GRAY = [0, 1, 3, 2]                      # 00, 01, 11, 10
    LABELS = ["00", "01", "11", "10"]
    VARS = "ABCD"

    # F(A,B,C,D) = sum m(0,2,4,5,7,8,10,13,15) + d(12)   ->  e.g. C'D' + B'D' + BD
    ONES = {0, 2, 4, 5, 7, 8, 10, 13, 15}
    DONT_CARE = {12}
    EVIDENCE_ORDER = [13, 2, 7, 0, 10, 4, 15, 5, 8]   # scrambled on purpose

    GROUP_COLORS = [
        (255, 90, 90), (255, 200, 60), (120, 220, 255),
        (190, 130, 255), (120, 255, 160), (255, 150, 220),
    ]

    HINTS = [
        "Hint: rows are AB and columns are CD in Gray order 00, 01, 11, 10 (not 00, 01, 10, 11).",
        "Hint: the map wraps. Left and right columns touch, top and bottom rows touch.",
        "Hint: the four corners form one group. An X cell may join a group if it makes it bigger.",
    ]

    def __init__(self):
        super().__init__()
        self.grid_x, self.grid_y = 450, 170
        self.cell_width, self.cell_height = 120, 80
        self.phase = "FILL"
        self.player = [[0] * 4 for _ in range(4)]   # 0, 1, 2 (=X)
        self.selected = set()
        self.groups = []
        self.hint_index = 0
        self.message = "Place every scene from the case file on the map. Click a cell: 0 > 1 > X."

        self.ones_cells = {c for c in self.all_cells() if self.minterm(*c) in self.ONES}
        self.dc_cells = {c for c in self.all_cells() if self.minterm(*c) in self.DONT_CARE}
        self.all_rects = self.build_rects()
        usable = self.ones_cells | self.dc_cells
        valid = [g for g in self.all_rects if g <= usable and g & self.ones_cells]
        self.primes = {g for g in valid if not any(g < h for h in valid)}
        self.min_cover = self.compute_min_cover()

    # ------------------------------------------------------------ geometry
    def minterm(self, r, c):
        return (self.GRAY[r] << 2) | self.GRAY[c]

    @staticmethod
    def all_cells():
        return [(r, c) for r in range(4) for c in range(4)]

    def cell_rect(self, r, c):
        return pygame.Rect(self.grid_x + c * self.cell_width,
                           self.grid_y + r * self.cell_height,
                           self.cell_width, self.cell_height)

    def target_value(self, r, c):
        m = self.minterm(r, c)
        if m in self.ONES:
            return 1
        if m in self.DONT_CARE:
            return 2
        return 0

    def build_rects(self):
        """Every legal K-map rectangle on a 4x4 torus (sizes 1,2,4 per side)."""
        rects = set()
        for h in (1, 2, 4):
            for w in (1, 2, 4):
                for r0 in range(4):
                    for c0 in range(4):
                        rects.add(frozenset(((r0 + i) % 4, (c0 + j) % 4)
                                            for i in range(h) for j in range(w)))
        return rects

    def compute_min_cover(self):
        primes = list(self.primes)
        for k in range(1, len(primes) + 1):
            for combo in itertools.combinations(primes, k):
                if set().union(*combo) >= self.ones_cells:
                    return k
        return len(primes)

    def term_for(self, group):
        minterms = [self.minterm(r, c) for r, c in group]
        text = ""
        for bit in (3, 2, 1, 0):
            values = {(m >> bit) & 1 for m in minterms}
            if values == {1}:
                text += self.VARS[3 - bit]
            elif values == {0}:
                text += self.VARS[3 - bit] + "'"
        return text or "1"

    # --------------------------------------------------------------- logic
    def verify_map(self):
        wrong = sum(1 for r, c in self.all_cells()
                    if self.player[r][c] != self.target_value(r, c))
        if wrong:
            self.message = f"{wrong} cell(s) contradict the case file. Re-read each scene carefully."
            return
        self.phase = "GROUP"
        self.message = "Map verified! Now select groups (click cells), SPACE to save each group."

    def add_group(self):
        if not self.selected:
            self.message = "Select cells first."
            return
        group = frozenset(self.selected)
        if group not in self.all_rects:
            self.message = "Invalid shape: groups are rectangles of 1, 2, 4, 8 or 16 cells (wrap allowed)."
        elif not group <= (self.ones_cells | self.dc_cells):
            self.message = "A group may not contain a 0 cell."
        elif not group & self.ones_cells:
            self.message = "A group made only of X cells is useless: include at least one 1."
        else:
            if group not in [g for g in self.groups]:
                self.groups.append(group)
            self.selected.clear()
            self.message = f"Group saved ({len(self.groups)}). Cover every 1, then press ENTER."

    def check_solution(self):
        covered = set().union(*self.groups) if self.groups else set()
        missing = sorted(self.minterm(r, c) for r, c in self.ones_cells - covered)
        if missing:
            self.message = "Still uncovered: " + ", ".join(f"m{m}" for m in missing)
            return
        for i, g in enumerate(self.groups, 1):
            if g not in self.primes:
                self.message = f"Group {i} can still grow. K-map groups must be as large as possible."
                return
        if len(self.groups) > self.min_cover:
            self.message = "Everything is covered, but a smaller set of groups exists. Remove a redundant group."
            return
        terms = sorted(self.term_for(g) for g in self.groups)
        literals = sum(sum(ch.isalpha() for ch in t) for t in terms)
        self.solved = True
        self.message = f"SOLVED!  F = {' + '.join(terms)}    |    Sector key = {literals}"

    # -------------------------------------------------------------- events
    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, c in self.all_cells():
                if not self.cell_rect(r, c).collidepoint(event.pos):
                    continue
                if self.phase == "FILL":
                    self.player[r][c] = (self.player[r][c] + 1) % 3
                    self.message = f"m{self.minterm(r, c)} set to {'0 1 X'.split()[self.player[r][c]]}."
                else:
                    if (r, c) not in (self.ones_cells | self.dc_cells):
                        self.message = f"m{self.minterm(r, c)} is 0: it cannot be in a group."
                    elif (r, c) in self.selected:
                        self.selected.remove((r, c))
                    else:
                        self.selected.add((r, c))
                    if (r, c) in (self.ones_cells | self.dc_cells):
                        self.message = f"{len(self.selected)} cell(s) selected. SPACE saves the group."
                return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.message = self.HINTS[self.hint_index % len(self.HINTS)]
                self.hint_index += 1
            elif self.phase == "FILL":
                if event.key == pygame.K_RETURN:
                    self.verify_map()
            else:
                if event.key == pygame.K_SPACE:
                    self.add_group()
                elif event.key == pygame.K_RETURN:
                    self.check_solution()
                elif event.key == pygame.K_BACKSPACE:
                    if self.selected:
                        self.selected.clear()
                        self.message = "Selection cleared."
                    elif self.groups:
                        self.groups.pop()
                        self.message = "Removed the last group."

    # ---------------------------------------------------------------- draw
    def draw(self, screen):
        screen.fill(settings.DARK_BLUE)
        title = pygame.font.Font(None, 42)
        heading = pygame.font.Font(None, 28)
        body = pygame.font.Font(None, 22)
        small = pygame.font.Font(None, 19)

        def write(text, font, color, x, y, center=False):
            image = font.render(text, True, color)
            rect = image.get_rect()
            if center:
                rect.center = (x, y)
            else:
                rect.topleft = (x, y)
            screen.blit(image, rect)

        write("LEVEL 5: LOGIC ARCHITECT", title, settings.CYAN, 35, 25)
        write("KARNAUGH MAP / 4 VARIABLES / DON'T-CARES", body, settings.GREY, 38, 70)

        # Case file
        pygame.draw.rect(screen, settings.PANEL_BLUE, (30, 100, 340, 400), border_radius=10)
        write("CASE FILE: VAULT ALARM", heading, settings.CYAN, 45, 110)
        write("A=DOOR  B=MOTION  C=LASER  D=CAMERA  (1 = tripped)", small, settings.GREY, 45, 142)
        write("Alarm RANG in these scenes:", small, settings.WHITE, 45, 168)
        for i, m in enumerate(self.EVIDENCE_ORDER):
            a, b, c, d = ((m >> 3) & 1, (m >> 2) & 1, (m >> 1) & 1, m & 1)
            write(f"{i + 1}.  A={a}  B={b}  C={c}  D={d}", small, settings.WHITE, 60, 192 + i * 21)
        write("Footage corrupted (unknown): A=1 B=1 C=0 D=0", small, settings.YELLOW, 45, 192 + 9 * 21 + 8)
        write("Every other scene: alarm stayed SILENT.", small, settings.WHITE, 45, 192 + 10 * 21 + 12)
        write("Press H for a hint.", small, settings.GREY, 45, 192 + 11 * 21 + 20)

        # Map axes
        write("AB\\CD", small, settings.CYAN, 372, 148)
        for i, label in enumerate(self.LABELS):
            write(label, body, settings.CYAN, self.grid_x + i * self.cell_width + self.cell_width // 2, 150, True)
            write(label, body, settings.CYAN, 425, self.grid_y + i * self.cell_height + self.cell_height // 2, True)

        # Map cells
        usable = self.ones_cells | self.dc_cells
        for r, c in self.all_cells():
            rect = self.cell_rect(r, c)
            m = self.minterm(r, c)
            value = self.player[r][c]
            if (r, c) in self.selected:
                fill, ink = settings.CYAN, settings.DARK_BLUE
            elif value == 1:
                fill, ink = (30, 90, 60), settings.WHITE
            elif value == 2:
                fill, ink = (95, 85, 30), settings.WHITE
            else:
                fill, ink = settings.PANEL_BLUE, settings.WHITE
            pygame.draw.rect(screen, fill, rect, border_radius=5)
            pygame.draw.rect(screen, settings.GREY, rect, 2, border_radius=5)
            write("0 1 X".split()[value], title, ink, rect.centerx, rect.centery - 9, True)
            write(f"m{m}", small, ink, rect.centerx, rect.bottom - 16, True)

        for gi, group in enumerate(self.groups):
            color = self.GROUP_COLORS[gi % len(self.GROUP_COLORS)]
            for r, c in group:
                inset = 8 + gi * 5
                rect = self.cell_rect(r, c).inflate(-inset, -inset)
                pygame.draw.rect(screen, color, rect, 3, border_radius=4)

        # Status
        if self.phase == "FILL":
            write("PHASE 1: RECONSTRUCT THE MAP", body, settings.GREEN, 450, 500)
            write("Click cells: 0 > 1 > X.   ENTER verifies the map.", small, settings.WHITE, 450, 525)
        else:
            write("PHASE 2: SIMPLIFY", body, settings.GREEN, 450, 500)
            write("Click cells to select, SPACE saves group, BACKSPACE undoes, ENTER checks.",
                  small, settings.WHITE, 450, 525)
            write(f"Groups saved: {len(self.groups)}", body, settings.CYAN, 450, 548)
        write(self.message, small, settings.YELLOW, 30, 585)
        if self.solved:
            write("LEVEL COMPLETE", heading, settings.GREEN, settings.SCREEN_WIDTH // 2, 625, True)