"""End-to-end: title screen -> choose BASIC -> open terminal 1 -> finish all 8 stages
through the real main() loop. Run:  python tests/test_basic_flow_in_main.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import pygame
import main as game_main
import interactions
from puzzles import basic_gates
from test_basic_gates import key, click, solve_step

SHOTS = os.path.join(ROOT, "tests", "basic_shots")
os.makedirs(SHOTS, exist_ok=True)
captured = {}
seen_flow = {"title": False, "lab": False, "puzzle": False, "done": False}

# Capture the puzzle instance main() creates.
_orig_init = basic_gates.BasicGatesPuzzle.__init__
def _init(self, *a, **k):
    _orig_init(self, *a, **k); captured["puz"] = self
basic_gates.BasicGatesPuzzle.__init__ = _init

# Pretend the detective stands next to terminal 1 (walking is not under test).
def _near(self, player, objects, completed_puzzles=None):
    for o in objects:
        if o.get("puzzle_id") == "logic_lock":
            self.nearby_object = o; return o
    self.nearby_object = None
_near_orig = interactions.InteractionManager.find_nearby_object
interactions.InteractionManager.find_nearby_object = _near

def script():
    surf = pygame.display.get_surface
    yield []                                   # first frame draws the title
    pygame.image.save(surf(), os.path.join(SHOTS, "title_mode_select.png"))
    yield [key(pygame.K_LEFT)]                 # choose BASIC
    pygame.image.save(surf(), os.path.join(SHOTS, "title_basic_selected.png"))
    yield [key(pygame.K_RETURN)]               # start
    yield [key(pygame.K_e)]                    # open terminal 1
    yield []
    puz = captured["puz"]
    assert puz is not None
    # leave with ESC and come back: progress must be kept
    puz.handle_event(key(pygame.K_h))
    yield [key(pygame.K_ESCAPE)]
    yield [key(pygame.K_e)]
    assert captured["puz"] is puz, "same session must be reused"
    for stage_no in range(1, 9):
        for step_no in range(len(puz.stage["steps"])):
            solve_step(puz, surf(), stage_no, step_no) if False else None
            # solve through the real event pipeline: build events then yield them
            step = puz.step; st = puz.st; kind = step["kind"]
            evs = []
            if kind == "bulbs":
                evs = [key(pygame.K_1 + i) for i, (x, y) in enumerate(zip(st["bulbs"], step["target"])) if x != y]
            elif kind == "read_bits":
                evs = [key(pygame.K_0 + b) for b in step["pattern"]]
            elif kind == "explore":
                evs = [key(pygame.K_a)] if step["gate"] == "NOT" else [key(pygame.K_b), key(pygame.K_a), key(pygame.K_b)]
            elif kind == "combine":
                evs = [key(pygame.K_t), key(pygame.K_2)]
            elif kind == "table":
                evs = [key(pygame.K_0 + v) for v in basic_gates.outputs_for(step["gate"])]
            elif kind == "choice":
                opts = step["options"]
                if all(isinstance(v, int) for _l, v in opts):
                    evs = [key(pygame.K_0 + step["correct"])]
                else:
                    evs = [key(pygame.K_1 + [v for _l, v in opts].index(step["correct"]))]
            yield evs + [key(pygame.K_RETURN)]
        assert puz.phase == "done", stage_no
        yield []
        yield [key(pygame.K_RETURN)]           # next stage / finish
    yield []
    # level solved -> main closes the puzzle and records Level 1 in the notebook
    yield []
    pygame.image.save(surf(), os.path.join(SHOTS, "lab_after_basic.png"))
    seen_flow["done"] = True
    yield [pygame.event.Event(pygame.QUIT)]

gen = script()
def fake_get(*a, **k):
    try:
        return next(gen)
    except StopIteration:
        return [pygame.event.Event(pygame.QUIT)]
pygame.event.get = fake_get

game_main.main()
assert seen_flow["done"]
print("MAIN-LOOP BASIC FLOW PASSED")
