
# progress.py
# Tracks puzzle completion and level progression.

class ProgressManager:
    def __init__(self):
        self.puzzle_order = [
            "logic_lock",
            "hidden_transmission",
            "memory_protocol",
            "final_override"
        ]

        self.completed_puzzles = set()

    def is_completed(self, puzzle_id):
        return puzzle_id in self.completed_puzzles

    def is_unlocked(self, puzzle_id):
        if puzzle_id not in self.puzzle_order:
            return False

        index = self.puzzle_order.index(puzzle_id)

        # The first puzzle is available from the beginning.
        if index == 0:
            return True

        # Every later puzzle requires the previous puzzle.
        previous_puzzle = self.puzzle_order[index - 1]

        return previous_puzzle in self.completed_puzzles

    def complete_puzzle(self, puzzle_id):
        if puzzle_id not in self.puzzle_order:
            return False

        if not self.is_unlocked(puzzle_id):
            return False

        self.completed_puzzles.add(puzzle_id)
        return True

    def get_completed_count(self):
        return len(self.completed_puzzles)

    def is_game_completed(self):
        return len(self.completed_puzzles) == len(self.puzzle_order)
