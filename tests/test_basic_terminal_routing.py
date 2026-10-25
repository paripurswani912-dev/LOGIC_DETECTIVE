"""Which puzzle opens on which terminal, for each path.   Run: python tests/test_basic_terminal_routing.py

BASIC path:        terminal 1 -> Basic gates, terminal 4 -> Basic Karnaugh maps,
                   every other terminal -> the original (intermediate) puzzle for now
INTERMEDIATE path: every terminal -> the original puzzle (nothing changed)
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pygame
import main as game_main
import game_state, interactions, progress

opened = []
_open = game_state.GameState.open_puzzle
def _record(self, puzzle):
    opened.append(type(puzzle).__name__); return _open(self, puzzle)
game_state.GameState.open_puzzle = _record
progress.ProgressManager.is_unlocked = lambda self, pid: True

target = {"id": None}
def _near(self, player, objects, completed_puzzles=None):
    for o in objects:
        if o.get("puzzle_id") == target["id"]:
            self.nearby_object = o; return o
    self.nearby_object = None
interactions.InteractionManager.find_nearby_object = _near

def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")

CASES = [
    ("basic", "logic_lock", "BasicGatesPuzzle"),
    ("basic", "hidden_transmission", "HiddenTransmissionPuzzle"),
    ("basic", "memory_protocol", "MemoryProtocolPuzzle"),
    ("basic", "final_override", "BasicKarnaughPuzzle"),
    ("basic", "logic_architect", "LogicArchitectPuzzle"),
    ("basic", "signal_breaker", "SignalBreakerPuzzle"),
    ("intermediate", "logic_lock", "LogicLockPuzzle"),
    ("intermediate", "final_override", "FinalOverridePuzzle"),
    ("intermediate", "logic_architect", "LogicArchitectPuzzle"),
]

for mode, pid, expected in CASES:
    opened.clear(); target["id"] = pid
    script = iter([[], [key(pygame.K_LEFT if mode == "basic" else pygame.K_RIGHT)],
                   [key(pygame.K_RETURN)], [key(pygame.K_e)], [], [], [pygame.event.Event(pygame.QUIT)]])
    pygame.event.get = lambda *a, **k: next(script, [pygame.event.Event(pygame.QUIT)])
    game_main.main()
    assert opened and opened[0] == expected, (mode, pid, opened, expected)
    print(f"  {mode:12s} {pid:20s} -> {opened[0]}")
print("TERMINAL ROUTING PASSED")
