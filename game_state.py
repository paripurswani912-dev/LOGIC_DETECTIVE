
# game_state.py
# Manages the current mode of Logic Detective


class GameState:
    # Main game modes
    TITLE = "title"
    INTRO = "intro"
    LABORATORY = "laboratory"
    DOCUMENT = "document"
    PUZZLE = "puzzle"
    LEVEL_COMPLETE = "level_complete"
    ENDING = "ending"
    EXIT = "exit"

    def __init__(self):
        # The game starts at the title screen
        self.current_mode = self.TITLE

        # Track the currently active puzzle
        self.active_puzzle = None

        # Track the currently open document
        self.active_document = None

        # Store a message to display to the player
        self.status_message = ""

    def change_mode(self, new_mode):
        """Change the current game mode."""
        self.current_mode = new_mode

    def open_puzzle(self, puzzle):
        """Open a puzzle overlay."""
        self.active_puzzle = puzzle
        self.current_mode = self.PUZZLE

    def close_puzzle(self):
        """Close the puzzle and return to the laboratory."""
        self.active_puzzle = None
        self.current_mode = self.LABORATORY

    def open_document(self, document_id):
        """Open a story do
        cument."""
        self.active_document = document_id
        self.current_mode = self.DOCUMENT

    def close_document(self):
        """Close the document and return to the laboratory."""
        self.active_document = None
        self.current_mode = self.LABORATORY

    def set_status(self, message):
        """Set a message for the player."""
        self.status_message = message
