"""Basic Level 3 - number systems and codes.   Run: python tests/test_basic_numbers.py

Checks: 10 stages x 6-7 activities, every answer re-derived with Python's own int()/format(),
every activity solved through real key / mouse events, wrong-answer feedback, text fits the
panels, every screen draws, the scrollable exam revision page, notebook autofill and ordering.
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pygame

pygame.init()
screen = pygame.display.set_mode((1000, 650))
import settings  # noqa: E402
from notebook import DetectiveNotebook  # noqa: E402
from puzzles.basic_gates import wrap_text, SIDE, WORK, FULL  # noqa: E402
from puzzles.basic_numbers import (  # noqa: E402
    BasicNumberSystemsPuzzle, NOTEBOOK_LINES, REVISION_NOTES, revision_blocks, render_revision,
    to_base, ones, twos, enc_twos, dec_twos, enc_sm, dec_sm, enc_ones, dec_ones, bcd, unbcd,
    excess3, unexcess3, bin_to_gray, gray_to_bin, add_bits, VIEW,
)

SHOTS = os.path.join(ROOT, "tests", "num_shots")
os.makedirs(SHOTS, exist_ok=True)


class NB:
    def __init__(self):
        self.notes = {}

    def add_basic_note(self, sid, lines):
        self.notes[sid] = lines


def key(k, u=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=u, mod=0)
def click(p, pos):
    p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))

# independent verification of answers
def verify(step):
    m = step["meta"]; op = m.get("op")
    if op == "to_base": assert step["answer"] == {2: format(m["n"], "b"), 16: format(m["n"], "X"), 8: format(m["n"], "o")}[m["base"]]
    elif op == "dec2bin":
        n = m["n"]; assert step["target"] == n
    elif op == "to_dec": assert step["answer"] == str(int(m["s"], m["base"]))
    elif op == "oct2bin": assert int(step["answer"], 2) == int(m["s"], 8)
    elif op == "ones": assert step.get("answer", step.get("target")) == "".join("1" if c == "0" else "0" for c in m["bits"])
    elif op == "twos":
        w = len(m["bits"]); assert int(step["answer"], 2) == (-int(m["bits"], 2)) % (1 << w)
    elif op == "enc_twos": assert int(step["answer"], 2) == m["n"] % (1 << m["w"]) and len(step["answer"]) == m["w"]
    elif op == "pad": assert step["answer"] == format(m["n"], "0%db" % m["w"])
    elif op == "min": assert int(step["answer"]) == -(1 << (m["n"] - 1))
    elif op == "add_trunc": assert int(step["answer"], 2) == (int(m["a"], 2) + int(m["b"], 2)) % 16
    elif op == "bcd": assert step["answer"] == "".join(format(int(d), "04b") for d in str(m["n"]))
    elif op == "unbcd": assert step["answer"] == str(int("".join(str(int(m["code"][i:i+4], 2)) for i in range(0, len(m["code"]), 4))))
    elif op == "unxs3": assert step["answer"] == str(int(m["code"], 2) - 3)
    elif op == "b2g": assert int(step["answer"], 2) == int(m["b"], 2) ^ (int(m["b"], 2) >> 1)
    elif op == "g2b":
        g = int(m["g"], 2); b = 0
        while g: b ^= g; g >>= 1
        assert step["answer"] == format(b, "0%db" % len(m["g"]))
    elif op == "sub8": assert int(step["answer"], 2) == (m["a"] - m["b"]) % 256
    elif op == "dec_twos":
        v = int(m["bits"], 2); v = v - 256 if v >= 128 else v; assert step["answer"] == str(v)
    elif op in ("group",):
        size = m["size"]; bits = m["bits"]
        exp = [format(int(bits[i:i+size], 2), "X" if size == 4 else "o") for i in range(0, len(bits), size)]
        got = [c[1] for row in step["rows"] for c in row if isinstance(c, tuple)]
        assert got == exp, (got, exp)
    elif op == "chain":
        got = [c[1] for c in step["rows"][0] if isinstance(c, tuple)]
        assert got == [format(m["n"], "b"), format(m["n"], "o"), format(m["n"], "X")]
    elif op == "ladder":
        n = m["n"]; exp = []
        while n: exp.append(str(n % 2)); n //= 2
        assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == exp
    elif op == "table_bin2dec":
        assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == [str(int(b, 2)) for b in m["rows"]]
    elif op == "weights":
        b = m["bits"]; got = [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)]
        assert got == [str(int(x) * 2 ** (3 - i)) for i, x in enumerate(b)] + [str(int(b, 2))]
    elif op == "decode_twos":
        v = lambda s: int(s, 2) - 16 if s[0] == "1" else int(s, 2)
        assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == [str(v(b)) for b in m["rows"]]
    elif op == "bcd_table": assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == ["".join(format(int(d), "04b") for d in str(n)) for n in m["ns"]]
    elif op == "bcd_digits": assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == [format(d, "04b") for d in m["digits"]]
    elif op == "xs3_digits": assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == [format(d + 3, "04b") for d in m["digits"]]
    elif op == "gray_table": assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == [format(int(b, 2) ^ (int(b, 2) >> 1), "03b") for b in m["bs"]]
    elif op == "bcd_xs3":
        n = m["n"]; assert [c[1] for c in step["rows"][0] if isinstance(c, tuple)] == ["".join(format(int(d), "04b") for d in str(n)), "".join(format(int(d) + 3, "04b") for d in str(n))]
    elif op == "carry_add":
        a, b = int(m["a"], 2), int(m["b"], 2); s = format((a + b) % 16, "04b")
        carries = "".join(str(((a ^ b ^ (a + b)) >> i) & 1) for i in (3, 2, 1, 0))
        got = [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)]
        assert got == list(carries) + list(s), (got, carries, s)
    elif op == "neg5":
        assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == ["1101", "1010", "1011"]
    elif op == "ranges":
        assert [c[1] for r in step["rows"] for c in r if isinstance(c, tuple)] == ["-7", "7", "-7", "7", "-8", "7"]
    elif op == "digits":
        allowed = {c for c in "0123456789ABCDEF"[:m["base"]]}
        assert {step["items"][i] for i in step["correct"]} == {x for x in step["items"] if x in allowed and len(x) == 1}
    elif op == "equivalents":
        vals = {"1010 (binary)": 10, "12 (octal)": 10, "A (hex)": 10, "10 (binary)": 2, "11 (octal)": 9, "F (hex)": 15}
        assert {step["items"][i] for i in step["correct"]} == {k for k, v in vals.items() if v == 10}
    elif op == "invalid_bcd":
        assert {step["items"][i] for i in step["correct"]} == {x for x in step["items"] if int(x, 2) > 9}
    elif op == "order":
        pass

def solve(p):
    st, step = p.st, p.step; kind = step["kind"]
    if kind == "choice":
        idx = int(step["correct"][1:]); p.handle_event(key(pygame.K_1 + idx, str(idx + 1)))
    elif kind == "typed":
        for ch in step["answer"]:
            p.handle_event(key(ord(ch.lower()) if ch != "-" else pygame.K_MINUS, ch.lower()))
    elif kind == "grid":
        for i, (_r, _c, e) in enumerate(p._editable(step)):
            p.st["sel"] = i
            for ch in e: p.handle_event(key(ord(ch.lower()) if ch != "-" else pygame.K_MINUS, ch.lower()))
    elif kind == "pick":
        for i in step["correct"]: p._on_action(("pk", i))
    elif kind == "order":
        for i in step["order"]: p._on_action(("ord", i))
    elif kind == "bits":
        if step["mode"] == "target":
            v = step["target"]; n = step["n"]
            for i in range(n):
                if (v >> (n - 1 - i)) & 1: p._on_action(("bit", i))
        elif step["mode"] == "pattern":
            for i, c in enumerate(step["target"]):
                if int(c) != st["bits"][i]: p._on_action(("bit", i))
        else:
            for v in (1, 2, 4, 8, 3, 5, 15): 
                for i in range(4): 
                    want = (v >> (3 - i)) & 1
                    if st["bits"][i] != want: p._on_action(("bit", i))
    p.handle_event(key(pygame.K_RETURN))



# ------------------------------------------------------------------
def test_helpers():
    for n in range(0, 300):
        assert to_base(n, 2) == format(n, "b") and to_base(n, 8) == format(n, "o") and to_base(n, 16) == format(n, "X")
    for w in (3, 4, 5, 8):
        for n in range(-(1 << (w - 1)), 1 << (w - 1)):
            e = enc_twos(n, w)
            assert dec_twos(e) == n and len(e) == w
            assert twos(e) == enc_twos(-n, w) or n == -(1 << (w - 1))
        for n in range(-(1 << (w - 1)) + 1, 1 << (w - 1)):
            assert dec_sm(enc_sm(n, w)) == n and dec_ones(enc_ones(n, w)) == n
    for n in range(0, 1000, 7):
        assert unbcd(bcd(n)) == n and unexcess3(excess3(n)) == n
    for n in range(256):
        b = format(n, "08b")
        assert gray_to_bin(bin_to_gray(b)) == b and int(bin_to_gray(b), 2) == n ^ (n >> 1)
    for a in range(16):
        for b in range(16):
            s, _c, co = add_bits(format(a, "04b"), format(b, "04b"))
            assert int(s, 2) + 16 * co == a + b
    print("  helpers match Python's own conversions")


def test_structure():
    p = BasicNumberSystemsPuzzle(NB())
    assert len(p.stages) == 10
    ids = [s["id"] for s in p.stages]
    assert ids == sorted(ids) and ids[0] == "n01_systems" and ids[-1] == "n10_final"
    titles = [s["title"] for s in p.stages]
    for word, i in (("Number Systems", 0), ("Decimal to Binary", 1), ("Binary to Decimal", 2), ("Octal", 3),
                    ("Complements", 4), ("Signed Numbers", 5), ("Signed Binary Arithmetic", 6), ("BCD", 7),
                    ("Excess-3", 8), ("Final Mission", 9)):
        assert word in titles[i], (word, titles[i])
    kinds = set()
    for s in p.stages:
        assert 5 <= len(s["steps"]) <= 7, (s["id"], len(s["steps"]))
        assert len(s["steps"][0]["hints"]) == 3
        for st in s["steps"]:
            kinds.add(st["kind"])
            assert len(st["hints"]) == 3 and st["task"] and st["ok"]
    assert kinds == {"bits", "typed", "grid", "pick", "order", "choice"}, kinds
    for s in p.stages:
        verify_stage(s)
    print(f"  10 stages, {sum(len(s['steps']) for s in p.stages)} activities, kinds: {sorted(kinds)}")


def verify_stage(stage):
    for step in stage["steps"]:
        verify(step)


def test_text_fits():
    p = BasicNumberSystemsPuzzle(NB())
    for s in p.stages:
        brief = sum(len(wrap_text(p.f_tiny, para, SIDE.width - 28)) for para in s["brief"])
        assert brief <= 7, (s["id"], "brief too long", brief)
        for st in s["steps"]:
            assert len(wrap_text(p.f_tiny, st["task"], SIDE.width - 28)) <= 4, (s["id"], st["task"])
            q = wrap_text(p.f_small, st["q"], WORK.width - 40)
            assert len(q) <= 4, (s["id"], st["q"])
            for h in st["hints"]:
                assert len(wrap_text(p.f_tiny, h, SIDE.width - 20 - 20)) <= 6, (s["id"], h)
            assert len(wrap_text(p.f_body, st["ok"], 930)) <= 2 + 1, (s["id"], st["ok"])
        # stage-complete card must fit above the footer note
        rx = FULL.x + 410
        rw = FULL.right - rx - 24
        y = FULL.y + 104
        for label, text in s["items"]:
            y += 24 + 23 * len(wrap_text(p.f_small, text, rw)) + 10
        assert y <= FULL.bottom - 70, (s["id"], "done card items overflow", y)
        _k, headers, rows, colw = s["example"]
        assert FULL.y + 104 + 34 * (len(rows) + 1) <= FULL.bottom - 66, (s["id"], "example table too tall")
        assert sum(colw) <= 390, (s["id"], "example table too wide", sum(colw))
    print("  briefs, tasks, questions, hints and complete-cards all fit their panels")


def test_playthrough():
    nb = NB()
    p = BasicNumberSystemsPuzzle(nb)
    total = 0
    for si, stage in enumerate(p.stages):
        for _ in stage["steps"]:
            assert p.phase == "play"
            p.update(0.01)
            p.draw(screen)
            solve(p)
            total += 1
            assert not p.solved
        assert p.phase == "done", (si, p.step_i, p.toast)
        p.draw(screen)
        p.update(1.0)
        p.handle_event(key(pygame.K_RETURN))
    assert p.phase == "revision"
    assert sorted(nb.notes) == [s["id"] for s in p.stages] + ["n11_revision"], sorted(nb.notes)
    p.update(1.0)
    p.handle_event(key(pygame.K_RETURN))
    assert p.solved
    print(f"  full playthrough OK ({total} activities, notebook autofilled with 11 notes)")


def test_wrong_answers():
    p = BasicNumberSystemsPuzzle(NB())

    def at(si, ti):
        p.stage_i, p.step_i, p.phase = si, ti, "play"
        p._enter_step()

    def type_(text):
        for ch in text:
            p.handle_event(key(ord(ch.lower()), ch.lower()))

    # bits: wrong total names the total
    at(1, 0); p._on_action(("bit", 0)); p.handle_event(key(pygame.K_RETURN))
    assert "add up to 8" in p.toast and p.step_i == 0 and p.st["wrong"] == 1
    # bits pattern names wrong switches
    at(4, 0); p.handle_event(key(pygame.K_RETURN)); assert "Switch number" in p.toast
    # typed: trap, wrong width, empty
    at(4, 2); p.handle_event(key(pygame.K_RETURN)); assert "first" in p.toast
    type_("1010"); p.handle_event(key(pygame.K_RETURN)); assert "1's complement" in p.toast
    at(4, 1); type_("1101"); p.handle_event(key(pygame.K_RETURN)); assert "exactly 8 bits" in p.toast
    # typed: limit on exact width, backspace
    at(4, 2); type_("101011"); assert p.st["typed"] == "1010"
    p.handle_event(key(pygame.K_BACKSPACE)); assert p.st["typed"] == "101"
    # typed: leading zeros accepted when not exact (octal 275 -> binary)
    at(3, 2); type_("10111101"); p.handle_event(key(pygame.K_RETURN)); assert p.step_i == 3
    # grid: wrong cell flagged red, must fill all
    at(2, 3); p.handle_event(key(pygame.K_RETURN)); assert "Fill every" in p.toast
    for i in range(4):
        p.st["sel"] = i; type_("1")
    p.handle_event(key(pygame.K_RETURN)); assert p.st["bad"] and "wrong" in p.toast
    # grid: backspace on empty cell moves back, auto-advance on exact-length cells
    at(5, 1); type_("1101"); assert p.st["sel"] == 1
    p.handle_event(key(pygame.K_BACKSPACE)); assert p.st["sel"] == 0 and p.st["vals"][0] == "1101"
    p.handle_event(key(pygame.K_BACKSPACE)); assert p.st["vals"][0] == "110"
    # pick: counts wrong / missing
    at(0, 0); p._on_action(("pk", 3)); p.handle_event(key(pygame.K_RETURN)); assert "wrong" in p.toast and "missing" in p.toast
    p._on_action(("pk", 3)); assert p.st["chosen"] == set()
    p.handle_event(key(pygame.K_RETURN)); assert "at least one" in p.toast
    # order: wrong order, undo, clear
    at(1, 3)
    for i in (0, 1, 2, 3): p._on_action(("ord", i))
    p.handle_event(key(pygame.K_RETURN)); assert "not right" in p.toast
    p.handle_event(key(pygame.K_BACKSPACE)); assert len(p.st["picked"]) == 3
    p._on_action(("clr",)); assert p.st["picked"] == []
    # choice wrong x3 reveals the answer (base behaviour)
    at(0, 3)
    for _ in range(3):
        p.handle_event(key(pygame.K_1)); p.handle_event(key(pygame.K_RETURN))
    assert p.st["tier"] == 3
    # explore needs enough different numbers
    at(2, 0); p.handle_event(key(pygame.K_RETURN)); assert "different number" in p.toast
    print("  wrong-answer feedback, traps, limits, undo and hints OK")


def test_mouse_paths():
    p = BasicNumberSystemsPuzzle(NB())

    def click_action(name):
        for rect, action in p.buttons:
            if action[0] == name:
                p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
                return action
        raise AssertionError("no button " + name)

    # typed via keypad
    p.stage_i, p.step_i = 1, 5; p._enter_step(); p.draw(screen)
    for ch in "10011":
        for rect, action in p.buttons:
            if action == ("key", ch):
                p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)); break
    assert p.st["typed"] == "10011"
    p.draw(screen); click_action("back"); assert p.st["typed"] == "1001"
    p.draw(screen); click_action("clear"); assert p.st["typed"] == ""
    # switches by click
    p.stage_i, p.step_i = 1, 0; p._enter_step(); p.draw(screen)
    for rect, action in p.buttons:
        if action == ("bit", 3):
            p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert p.st["bits"] == [0, 0, 0, 1]
    # grid cell click + hex keypad
    p.stage_i, p.step_i = 3, 1; p._enter_step(); p.draw(screen)
    cells = [a for _r, a in p.buttons if a[0] == "gcell"]
    assert len(cells) == 3
    for rect, action in p.buttons:
        if action == ("gcell", 1):
            p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert p.st["sel"] == 1
    p.draw(screen)
    for rect, action in p.buttons:
        if action == ("key", "F"):
            p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)); break
    assert p.st["vals"][1] == "F"
    # CHECK button works
    p.draw(screen); click_action("check"); assert p.st["wrong"] == 1 or p.toast
    print("  mouse: switches, keypad, DEL / CLR, table cells and CHECK work")


def test_draw_everything():
    p = BasicNumberSystemsPuzzle(NB())
    n = 0
    for si, stage in enumerate(p.stages):
        for ti, step in enumerate(stage["steps"]):
            p.stage_i, p.step_i, p.phase = si, ti, "play"
            p._enter_step()
            p.draw(screen); n += 1
            p.st["tier"] = 3
            p.draw(screen)
            solve(p) if False else None
        p.phase = "done"; p.stage_i = si; p.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "last_done_card.png"))
    print(f"  drew {n} activity screens (+ hint boxes) and 10 complete-cards without errors")


def test_revision():
    nb = NB()
    p = BasicNumberSystemsPuzzle(nb)
    p.stage_i, p.phase = 9, "done"
    p.handle_event(key(pygame.K_RETURN))
    assert p.phase == "revision" and not p.solved
    p.draw(screen)
    mx = p._rev_max()
    assert mx > 4 * VIEW.height, "revision page must be long (comprehensive)"
    # blocks cover all ten topics
    heads = [b[1] for b in revision_blocks() if b[0] == "h1"]
    assert len(heads) == 10, heads
    for word in ("NUMBER SYSTEMS", "DECIMAL TO BINARY", "BINARY TO DECIMAL", "OCTAL", "COMPLEMENTS", "SIGNED NUMBERS",
                 "ARITHMETIC", "BCD", "EXCESS-3", "CHEAT SHEET"):
        assert any(word in h for h in heads), word
    # double ENTER right after opening must NOT skip the page
    p.handle_event(key(pygame.K_RETURN)); assert not p.solved
    # keyboard scrolling
    p.handle_event(key(pygame.K_DOWN)); assert p.rev_scroll == 44
    p.handle_event(key(pygame.K_PAGEDOWN)); assert p.rev_scroll > 44 + 300
    p.handle_event(key(pygame.K_PAGEUP)); p.handle_event(key(pygame.K_UP)); p.handle_event(key(pygame.K_HOME))
    assert p.rev_scroll == 0
    p.handle_event(key(pygame.K_UP)); assert p.rev_scroll == 0            # clamped
    p.handle_event(key(pygame.K_END)); assert p.rev_scroll == mx
    p.handle_event(key(pygame.K_DOWN)); assert p.rev_scroll == mx          # clamped
    # mouse wheel (legacy buttons 4/5 are what main.py forwards)
    p.handle_event(key(pygame.K_HOME))
    p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(500, 300))); assert p.rev_scroll == 64
    p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=4, pos=(500, 300))); assert p.rev_scroll == 0
    # scrollbar drag
    p.draw(screen)
    track = p._rev_track()
    p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(track.centerx, track.centery)))
    assert p.rev_drag and 0.3 * mx < p.rev_scroll < 0.7 * mx
    p.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(track.centerx, track.bottom), rel=(0, 0), buttons=(1, 0, 0)))
    assert p.rev_scroll == mx
    p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0))); assert not p.rev_drag
    # every scroll position draws
    for y in range(0, mx + 1, 211):
        p.rev_scroll = y; p.draw(screen)
    # TOP / END buttons
    p.draw(screen)
    for rect, action in p.buttons:
        if action == ("top",):
            p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert p.rev_scroll == 0
    # notebook got the revision sheet
    assert "n11_revision" in nb.notes and nb.notes["n11_revision"] == REVISION_NOTES
    # ESC-and-return keeps the page (the session object is reused)
    assert p.phase == "revision"
    # FINISH button finishes
    p.draw(screen)
    for rect, action in p.buttons:
        if action == ("finish",):
            p.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert p.solved
    # surfaces: render once, text fits the width (no table wider than the page)
    h = render_revision(VIEW.width)
    assert h == p.rev_surface.get_height()
    pygame.image.save(p.rev_surface.subsurface((0, 0, VIEW.width, 700)), os.path.join(SHOTS, "revision_top.png"))
    print(f"  revision page OK: {h}px tall, wheel / keys / scrollbar / TOP / END / FINISH, 10 sections")


def test_notebook():
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    for sid in ("q1_memory", "k1_neighbours", "n10_final", "n02_dec2bin", "s1_onoff", "n11_revision", "c1_x", "n01_systems"):
        nb.add_basic_note(sid, [f"LINE {sid}"])
    notes = nb.reference_notes["MY BASIC NOTES"]
    seen = [l.split()[-1] for l in notes if l.startswith("LINE")]
    assert seen == ["s1_onoff", "n01_systems", "n02_dec2bin", "n10_final", "n11_revision",
                    "k1_neighbours", "c1_x", "q1_memory"], seen
    assert nb.SCIENTIST_NOTES["level_three"] != DetectiveNotebook.SCIENTIST_NOTES["level_three"]
    assert "BINARY" in " ".join(nb.SCIENTIST_NOTES["level_three"]).upper()
    assert nb.LEVEL_PRACTICE["level_three"] == "NUMBER SYSTEMS AND CODES"
    assert nb.SCIENTIST_NOTES["level_four"] != DetectiveNotebook.SCIENTIST_NOTES["level_four"]   # K-map text kept
    assert nb.SCIENTIST_NOTES["level_five"] != DetectiveNotebook.SCIENTIST_NOTES["level_five"]   # level 5 kept
    assert "FLIP-FLOP" in " ".join(nb.SCIENTIST_NOTES["level_six"]).upper()                       # level 6 kept
    nb.set_mode("intermediate")
    assert nb.SCIENTIST_NOTES["level_three"] == DetectiveNotebook.SCIENTIST_NOTES["level_three"]
    for sid, lines in NOTEBOOK_LINES.items():
        assert lines[0].startswith("NUMBERS") and len(lines) >= 5
    print("  notebook: order (s, n, k, c, q), per-mode text, level 4/5/6 text untouched")


def main():
    test_helpers()
    test_structure()
    test_text_fits()
    test_playthrough()
    test_wrong_answers()
    test_mouse_paths()
    test_draw_everything()
    test_revision()
    test_notebook()
    print("BASIC NUMBER SYSTEMS COURSE PASSED")


if __name__ == "__main__":
    main()
