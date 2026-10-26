"""End-to-end: title screen -> BASIC -> terminal 6 (Signal Breaker) -> all 8 stages through the
real main() loop. The terminal is force-unlocked (walking and earlier levels are not under test).
Run:  python tests/test_basic_seq_in_main.py"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import pygame
import main as game_main
import interactions, progress
from puzzles import basic_seq
from puzzles.basic_seq import FF_INPUTS, X, input_combos
from test_basic_seq import key

SHOTS = os.path.join(ROOT, "tests", "seq_shots"); os.makedirs(SHOTS, exist_ok=True)
captured, flow = {}, {"finished": False}

_init = basic_seq.BasicSequentialPuzzle.__init__
def _wrapped(self, *a, **k):
    _init(self, *a, **k); captured["puz"] = self
basic_seq.BasicSequentialPuzzle.__init__ = _wrapped

def _near(self, player, objects, completed_puzzles=None):
    for o in objects:
        if o.get("puzzle_id") == "signal_breaker":
            self.nearby_object = o; return o
    self.nearby_object = None
interactions.InteractionManager.find_nearby_object = _near
progress.ProgressManager.is_unlocked = lambda self, puzzle_id: True

def step_events(puz):
    step, st, kind = puz.step, puz.st, puz.step["kind"]
    ev = []
    if kind == "sdemo":
        ev = [key(pygame.K_RIGHT)] * (len(step["frames"]) - 1)
    elif kind == "ffplay":
        cur = list(st["ins"])
        for combo in input_combos(step["ff"]):
            for i, name in enumerate(FF_INPUTS[step["ff"]]):
                if cur[i] != combo[i]:
                    ev.append(key(getattr(pygame, "K_" + name.lower()))); cur[i] = combo[i]
            ev.append(key(pygame.K_SPACE))
    elif kind in ("fftable", "exctable", "wavefill"):
        flat = step["expect"] if kind != "exctable" else [v for row in step["expect"] for v in row]
        ev = [key(pygame.K_x if v == X else pygame.K_0 + v) for v in flat]
    elif kind == "seqtable":
        ev = [key(pygame.K_0 + int(ch)) for row in step["expect"] for ch in row]
    elif kind == "regplay":
        if "target_reg" in step:
            cur = 0
            for bit in reversed(step["target_reg"]):
                if cur != bit: ev.append(key(pygame.K_s)); cur = bit
                ev.append(key(pygame.K_SPACE))
        else:
            ev = [key(pygame.K_1 + i) for i, b in enumerate(step["need_load"]) if b] + [key(pygame.K_l)] + \
                 [key(pygame.K_SPACE)] * len(step["target_out"])
    elif kind == "cntplay":
        ev = [key(pygame.K_SPACE)] * (step["mod"] if step["need"].get("rollover") else 4)
    elif kind == "choice":
        opts = step["options"]
        ev = [key(pygame.K_0 + step["correct"])] if all(isinstance(v, int) for _l, v in opts) else \
             [key(pygame.K_1 + [v for _l, v in opts].index(step["correct"]))]
    return ev + [key(pygame.K_RETURN)]

def script():
    surf = pygame.display.get_surface
    yield []
    yield [key(pygame.K_LEFT)]                 # BASIC
    yield [key(pygame.K_RETURN)]               # start
    yield [key(pygame.K_e)]                    # open terminal 6
    yield []
    puz = captured["puz"]
    assert type(puz).__name__ == "BasicSequentialPuzzle", "BASIC path must open the sequential course on terminal 6"
    for stage in range(len(puz.stages)):
        for _ in range(len(puz.stage["steps"])):
            yield step_events(puz)
        assert puz.phase == "done", stage
        yield []
        yield [key(pygame.K_RETURN)]
    yield []; yield []
    pygame.image.save(surf(), os.path.join(SHOTS, "lab_after_seq.png"))
    flow["finished"] = True
    yield [pygame.event.Event(pygame.QUIT)]

gen = script()
pygame.event.get = lambda *a, **k: next(gen, [pygame.event.Event(pygame.QUIT)])
pygame.mouse.get_pos = lambda: (0, 0)
game_main.main()
assert flow["finished"]
print("MAIN-LOOP SEQUENTIAL FLOW PASSED")
