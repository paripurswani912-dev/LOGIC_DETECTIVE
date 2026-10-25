"""End-to-end: title screen -> BASIC -> terminal 4 (Final Override) -> all 8 Karnaugh stages
through the real main() loop. (The terminal is force-unlocked; walking and earlier
levels are not under test.)   Run:  python tests/test_basic_kmap_in_main.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import pygame
import main as game_main
import interactions, progress
from puzzles import basic_kmap
from puzzles.basic_kmap import (solution_loops, prime_loops, analyse)
from test_basic_kmap import key, click

SHOTS = os.path.join(ROOT, "tests", "kmap_shots"); os.makedirs(SHOTS, exist_ok=True)
captured = {}
flow = {"finished": False}
import notebook as _nbmod

_init = basic_kmap.BasicKarnaughPuzzle.__init__
def _wrapped(self, *a, **k):
    _init(self, *a, **k); captured["puz"] = self
basic_kmap.BasicKarnaughPuzzle.__init__ = _wrapped

def _near(self, player, objects, completed_puzzles=None):
    for o in objects:
        if o.get("puzzle_id") == "final_override":
            self.nearby_object = o; return o
    self.nearby_object = None
interactions.InteractionManager.find_nearby_object = _near
cls = [c for c in vars(progress).values() if isinstance(c, type) and hasattr(c, "is_unlocked")][0]
cls.is_unlocked = lambda self, puzzle_id: True

def cell_events(puz, ms):
    puz.draw(pygame.display.get_surface())
    evs = []
    for m in ms:
        for rect, action in puz.buttons:
            if action == ("kcell", m):
                evs.append(click(rect.center)); break
    return evs

def step_events(puz):
    step, st, kind = puz.step, puz.st, puz.step["kind"]; n = step.get("n", 3)
    if kind == "kinspect":
        return cell_events(puz, [2, 3, 0, 2, 0, 3])
    if kind == "kfill":
        return cell_events(puz, sorted(step["ones"]))
    if kind == "kpick":
        return cell_events(puz, [step["target"]])
    if kind == "kloops":
        evs = []
        for loop in solution_loops(n, step["vals"], step["mode"]):
            evs += cell_events(puz, sorted(loop)) + [key(pygame.K_l)]
        return evs
    if kind == "kstretch":
        best = max([p for p in prime_loops(n, set(step["ones"]), set(step["ones"])) if step["start"] in p], key=len)
        free = analyse(best, n)["free"]
        return [key(pygame.K_a + i) for i in range(n) if free & (1 << (n - 1 - i))]
    if kind == "kterm":
        evs = []
        for i, want in enumerate(puz._expected_states()):
            evs += [key(pygame.K_a + i)] * {"plain": 1, "bar": 2, "drop": 3}[want]
        return evs
    if kind == "kdemo":
        return [key(pygame.K_RIGHT)] * (len(step["frames"]) - 1)
    opts = step["options"]
    return [key(pygame.K_1 + [v for _l, v in opts].index(step["correct"]))]

def script():
    surf = pygame.display.get_surface
    yield []
    yield [key(pygame.K_LEFT)]                 # BASIC
    yield [key(pygame.K_RETURN)]               # start
    yield [key(pygame.K_e)]                    # open terminal 4 (Final Override)
    yield []
    puz = captured["puz"]
    assert type(puz).__name__ == "BasicKarnaughPuzzle", "BASIC path must open the Karnaugh course"
    for stage in range(len(puz.stages)):
        for _ in range(len(puz.stage["steps"])):
            yield step_events(puz) + [key(pygame.K_RETURN)]
        assert puz.phase == "done", stage
        yield []
        yield [key(pygame.K_RETURN)]
    yield []; yield []
    pygame.image.save(surf(), os.path.join(SHOTS, "lab_after_kmap.png"))
    flow["finished"] = True
    yield [pygame.event.Event(pygame.QUIT)]

gen = script()
pygame.event.get = lambda *a, **k: next(gen, [pygame.event.Event(pygame.QUIT)])
game_main.main()
assert flow["finished"]
print("MAIN-LOOP KARNAUGH FLOW PASSED")
