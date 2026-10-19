
# puzzles/base_puzzle.py

class BasePuzzle:
    """Common interface for all game puzzles."""

    def __init__(self):
        self.solved = False
        self.message = ""

    def handle_event(self, event):
        """Handle keyboard and mouse input."""
        pass

    def update(self, dt):
        """Update puzzle timers or animations."""
        pass

    def draw(self, screen):
        """Each puzzle must provide its own drawing method."""
        raise NotImplementedError(
            "Each puzzle must implement its own draw() method."
        )

    def is_solved(self):
        return self.solved

    def reset_attempt(self):
        self.solved = False
        self.message = ""
