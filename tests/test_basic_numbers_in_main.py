"""End-to-end: title screen -> BASIC -> terminal 3 (Memory Protocol slot) -> all 10 stages ->
exam revision page -> finish, through the real main() loop. The terminal is force-unlocked.
Run:  python tests/test_basic_numbers_in_main.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import pygame
import main as game_main
import interactions, progress
from puzzles import basic_numbers
from test_basic_numbers import key, solve

SHOTS = os.path.join(ROOT, "tests", "num_shots"); os.makedirs(SHOTS, exist_ok=True)
captured, flow = {}, {"finished": False}

_init = basic_numbers.BasicNumberSystemsPuzzle.__init__
def _wrapped(self, *a, **k):
    _init(self, *a, **k); captured["puz"] = self
basic_numbers.BasicNumberSystemsPuzzle.__init__ = _wrapped

def _near(self, player, objects, completed_puzzles=None):
    for o in objects:
        if o.get("puzzle_id") == "memory_protocol":
            self.nearby_object = o; return o
    self.nearby_object = None
interactions.InteractionManager.find_nearby_object = _near
progress.ProgressManager.is_unlocked = lambda self, puzzle_id: True

def script():
    surf = pygame.display.get_surface
    yield []
    yield [key(pygame.K_LEFT)]                 # BASIC
    yield [key(pygame.K_RETURN)]               # start
    yield [key(pygame.K_e)]                    # open terminal 3
    yield []
    puz = captured["puz"]
    assert type(puz).__name__ == "BasicNumberSystemsPuzzle", "BASIC path must open the number-systems course on terminal 3"
    for stage in range(len(puz.stages)):
        for _ in range(len(puz.stage["steps"])):
            solve(puz)                          # real key events inside solve(); main loop draws every frame
            yield []
        assert puz.phase == "done", (stage, puz.phase)
        yield []
        yield [key(pygame.K_RETURN)]
        yield []
    assert puz.phase == "revision", puz.phase
    pygame.image.save(surf(), os.path.join(SHOTS, "revision_in_main.png"))
    yield [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(500, 300))] * 5
    assert puz.rev_scroll == 320, puz.rev_scroll
    puz.clock += 5
    yield [key(pygame.K_RETURN)]               # finish the level
    yield []; yield []
    assert puz.solved
    flow["finished"] = True
    yield [pygame.event.Event(pygame.QUIT)]

gen = script()
pygame.event.get = lambda *a, **k: next(gen, [pygame.event.Event(pygame.QUIT)])
pygame.mouse.get_pos = lambda: (0, 0)
game_main.main()
assert flow["finished"]
print("MAIN-LOOP NUMBER SYSTEMS FLOW PASSED")
