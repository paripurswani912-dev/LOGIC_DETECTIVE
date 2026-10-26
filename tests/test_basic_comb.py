"""Tests for the Basic Level 5 course (combinational circuits) and the notebook lab.

Run from the project folder:
    python tests/test_basic_comb.py
Screenshots are written to tests/comb_shots/.
"""
import itertools
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import settings  # noqa: E402
from notebook import DetectiveNotebook, BASIC_LEVEL_FIVE_NOTES  # noqa: E402
from puzzles import comb_lab as CL  # noqa: E402
from puzzles.basic_comb import (  # noqa: E402
    BasicCombinationalPuzzle, build_comb_stages, mux_expected, NOTES, EXAM, SYLL,
)
from puzzles.basic_gates import SIDE, FULL, WORK  # noqa: E402

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comb_shots")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


DIGITS = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
          pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]


def digit_key(i):
    """Key that flips input number i (0-based): 1..9, 0, then minus."""
    if i < 9:
        return DIGITS[i + 1]
    return pygame.K_0 if i == 9 else pygame.K_MINUS


def shot(puz, screen, name):
    puz.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, name + ".png"))


def all_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            all_strings(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            all_strings(v, out)
    return out


# ------------------------------------------------------------------
# 1. ENGINE (the circuits themselves)
# ------------------------------------------------------------------
def test_engine():
    assert len(CL.SIMS) == 20 and len({s["id"] for s in CL.SIMS}) == 20

    # every drawn gate netlist behaves exactly like its Python function
    nets = 0
    for s in CL.SIMS:
        if s["net"] is None:
            continue
        nets += 1
        names = [i["name"] for i in s["net"].inputs]
        assert set(names) <= set(s["inputs"])
        for combo in itertools.product((0, 1), repeat=len(names)):
            v = dict(zip(names, combo))
            full = {k: v.get(k, 0) for k in s["inputs"]}
            full.update({k: x for k, x in s["init"].items() if k not in v})
            assert s["net"].out_values(v) == CL.sim_outs(s, {**s["init"], **v}), (s["id"], v)
    assert nets == 16, nets

    # minterm lists quoted in the course
    m = lambda sid, out: CL.minterms(CL.BY_ID[sid], out)
    assert m("fa", "Sum") == [1, 2, 4, 7] and m("fa", "Cout") == [3, 5, 6, 7]
    assert m("fs", "Diff") == [1, 2, 4, 7] and m("fs", "Bout") == [1, 2, 3, 7]
    assert m("par3", "P") == [1, 2, 4, 7]
    assert m("par4", "P") == [1, 2, 4, 7, 8, 11, 13, 14]
    assert m("ha", "Sum") == [1, 2] and m("ha", "Carry") == [3]
    assert m("hs", "Diff") == [1, 2] and m("hs", "Borrow") == [1]

    # decoders are one-hot minterm generators
    for sid, n in (("dec2", 2), ("dec3", 3)):
        s = CL.BY_ID[sid]
        for k in range(1 << n):
            v = {nm: (k >> (n - 1 - i)) & 1 for i, nm in enumerate("ABC"[:n])}
            o = CL.sim_outs(s, v)
            assert sum(o.values()) == 1 and o[f"Y{k}"] == 1

    # multiplexers copy the selected input
    for sid, n in (("mux4", 2), ("mux8", 3)):
        s = CL.BY_ID[sid]
        sel = [f"S{i}" for i in range(n - 1, -1, -1)]
        for k in range(1 << n):
            v = {nm: (k >> (n - 1 - i)) & 1 for i, nm in enumerate(sel)}
            for d in range(1 << n):
                v[f"I{d}"] = 1 if d == k else 0
            assert CL.sim_outs(s, v)["Y"] == 1
            v[f"I{k}"] = 0
            assert CL.sim_outs(s, v)["Y"] == 0

    # adder chain and adder-subtractor against real arithmetic
    add, sub = CL.BY_ID["add4"], CL.BY_ID["addsub"]
    for a in range(16):
        for b in range(16):
            va = {f"A{i}": (a >> i) & 1 for i in range(4)}
            vb = {f"B{i}": (b >> i) & 1 for i in range(4)}
            for c in (0, 1):
                o = CL.sim_outs(add, {**va, **vb, "Cin": c})
                t = a + b + c
                assert [o[f"S{i}"] for i in range(4)] == [(t >> i) & 1 for i in range(4)]
                assert o["Cout"] == t >> 4
            o = CL.sim_outs(sub, {**va, **vb, "M": 0})
            assert sum(o[f"S{i}"] << i for i in range(4)) == (a + b) % 16
            o = CL.sim_outs(sub, {**va, **vb, "M": 1})
            assert sum(o[f"S{i}"] << i for i in range(4)) == (a - b) % 16
            assert o["Cout"] == int(a >= b)         # 1 = no borrow

    # Gray code: round trip, and neighbours differ in exactly one bit
    b2g, g2b = CL.BY_ID["b2g"], CL.BY_ID["g2b"]
    prev = None
    for n in range(16):
        vb = {f"B{i}": (n >> i) & 1 for i in range(4)}
        g = CL.sim_outs(b2g, vb)
        back = CL.sim_outs(g2b, {k: v for k, v in g.items()})
        assert back == vb, n
        code = sum(g[f"G{i}"] << i for i in range(4))
        if prev is not None:
            assert bin(code ^ prev).count("1") == 1
        prev = code

    # comparator, encoder, demux, parity checker
    c2 = CL.BY_ID["cmp2"]
    for a in range(4):
        for b in range(4):
            o = CL.sim_outs(c2, {"A1": a >> 1, "A0": a & 1, "B1": b >> 1, "B0": b & 1})
            assert (o["A>B"], o["A=B"], o["A<B"]) == (int(a > b), int(a == b), int(a < b))
    e8 = CL.BY_ID["enc8"]
    for k in range(8):
        o = CL.sim_outs(e8, {f"D{i}": int(i == k) for i in range(8)})
        assert o["Y2"] * 4 + o["Y1"] * 2 + o["Y0"] == k
    dm = CL.BY_ID["demux4"]
    for k in range(4):
        o = CL.sim_outs(dm, {"D": 1, "S1": k >> 1, "S0": k & 1})
        assert [o[f"Y{i}"] for i in range(4)] == [int(i == k) for i in range(4)]
    pc = CL.BY_ID["parchk"]
    for msg in range(16):
        bits = [(msg >> i) & 1 for i in range(4)]
        p = sum(bits) & 1                          # even parity bit
        v = dict(zip("ABCD", bits))
        assert CL.sim_outs(pc, {**v, "P": p})["Error"] == 0
        assert CL.sim_outs(pc, {**v, "P": 1 - p})["Error"] == 1
    print("  engine OK (20 circuits; 16 gate netlists match their functions on every input)")


def test_past_paper_numbers():
    """The two exam functions (and the practice one) really give the data inputs we teach."""
    def mux_works(ones, nvars, n_sel, last, expect):
        got = mux_expected(ones, nvars, n_sel, last)
        assert got == expect, (got, expect)
        for m in range(1 << nvars):
            sel = m >> (nvars - n_sel) if nvars > n_sel else m
            lastbit = m & 1 if nvars > n_sel else 0
            opt = got[sel]
            val = {"0": 0, "1": 1, last: lastbit, last + "'": 1 - lastbit}[opt]
            assert val == int(m in ones), (m, opt)

    # Sep 2026 mid-sem: 4*1 MUX, F = Sum m(1,2,4,7)
    mux_works({1, 2, 4, 7}, 3, 2, "C", ["C", "C'", "C'", "C"])
    # Nov 2024 end-sem and Apr 2026 mid-sem: 8*1 MUX, F = Sum m(1,3,4,11,12,13,14,15)
    mux_works({1, 3, 4, 11, 12, 13, 14, 15}, 4, 3, "D", ["D", "D", "D'", "0", "0", "D", "1", "1"])
    # warm-up: same function on an 8:1 MUX with 3 variables
    mux_works({1, 2, 4, 7}, 3, 3, "", ["0", "1", "1", "0", "1", "0", "0", "1"])
    # boss practice function
    mux_works({3, 5, 6, 7}, 3, 2, "C", ["0", "C", "C", "1"])
    print("  past-paper MUX numbers OK (4:1 -> C,C',C',C   8:1 -> D,D,D',0,0,D,1,1)")


# ------------------------------------------------------------------
# 2. CONTENT
# ------------------------------------------------------------------
def col_from_text(text, label):
    m = re.search(re.escape(label) + r"[^:]*:\s*((?:[01] ?)+)", text)
    assert m, (label, text)
    return [int(x) for x in m.group(1).split()]


def test_content(screen):
    stages = build_comb_stages()
    assert len(stages) == 9
    ids = [s["id"] for s in stages]
    assert ids == ["c1_half", "c2_full", "c3_sub", "c4_chain", "c5_parity", "c6_gray",
                   "c7_decoder", "c8_mux", "c9_boss"]
    kinds = set()
    for st in stages:
        assert st["brief"] and st["items"] and st["done"]
        for step in st["steps"]:
            kinds.add(step["kind"])
            hints = step["hints"]
            assert len(hints) == 3 and all(isinstance(h, str) and h for h in hints), (st["id"], step)
            assert step["task"]
            assert step.get("tag") in (None, EXAM, SYLL)
            if step["kind"] == "choice":
                assert step["correct"] in [v for _l, v in step["options"]], step["q"]
                assert len({v for _l, v in step["options"]}) == len(step["options"])
            if step["kind"] == "cslots":
                sim = CL.BY_ID[step["sim"]]
                assert set(step["hidden"]) <= {n["id"] for n in sim["net"].nodes}
                assert set(step["hidden"]) == set(step["labels"]) == set(step["reasons"])
                for nid, gate in step["hidden"].items():
                    assert gate in step["options"]
                # the authored gates really build the circuit
                types = dict(step["hidden"])
                for combo in itertools.product((0, 1), repeat=len(sim["net"].inputs)):
                    v = dict(zip([i["name"] for i in sim["net"].inputs], combo))
                    assert sim["net"].out_values(v, types) == CL.sim_outs(sim, {**sim["init"], **v}), (st["id"], v)
    assert kinds == {"cframes", "csee", "ctable", "cslots", "cmux", "cbits", "choice"}, kinds

    # exam-style steps exist for every past-paper topic
    exam_count = {st["id"]: sum(1 for s in st["steps"] if s.get("tag") == EXAM) for st in stages}
    for sid in ("c2_full", "c3_sub", "c5_parity", "c6_gray", "c7_decoder", "c8_mux", "c9_boss"):
        assert exam_count[sid] >= 1, sid
    assert all(s.get("tag") == SYLL for s in stages[3]["steps"]), "stage 4 is syllabus-only"
    papers = " ".join(s["text"] if isinstance(s, dict) and "text" in s else str(s) for s in stages)
    for wording in ("Design full adder with truth table & logic diagram.",
                    "Design full subtractor with truth table & logic diagram.",
                    "Design an even parity bit generator for 4 bit input.",
                    "Design 3 to 8 line decoder with logic diagram and truth table.",
                    "Use 4*1 Mux to implement the logic function F = Sum m(1, 2, 4, 7).",
                    "Use 8*1 MUX to implement the logic function F = Sum m(1, 3, 4, 11, 12, 13, 14, 15).",
                    "Design a 4-bit binary to Gray code converter.",
                    "Explain 2 to 4 line Decoder with logic diagram and truth table."):
        assert wording in papers, wording

    # authored answers quoted in hints are checked against the engine
    S = {s["id"]: s for s in stages}
    def hint3(stage, idx):
        return S[stage]["steps"][idx]["hints"][2]
    assert col_from_text(hint3("c1_half", 2), "Sum") == [o[0] for _c, o in CL.table_rows(CL.BY_ID["ha"])]
    assert col_from_text(hint3("c1_half", 2), "Carry") == [o[1] for _c, o in CL.table_rows(CL.BY_ID["ha"])]
    assert col_from_text(hint3("c2_full", 2), "Sum") == [o[0] for _c, o in CL.table_rows(CL.BY_ID["fa"])]
    assert col_from_text(hint3("c2_full", 2), "Cout") == [o[1] for _c, o in CL.table_rows(CL.BY_ID["fa"])]
    assert col_from_text(hint3("c3_sub", 2), "Diff") == [o[0] for _c, o in CL.table_rows(CL.BY_ID["hs"])]
    assert col_from_text(hint3("c3_sub", 2), "Borrow") == [o[1] for _c, o in CL.table_rows(CL.BY_ID["hs"])]
    assert col_from_text(hint3("c3_sub", 4), "Diff") == [o[0] for _c, o in CL.table_rows(CL.BY_ID["fs"])]
    assert col_from_text(hint3("c3_sub", 4), "Bout") == [o[1] for _c, o in CL.table_rows(CL.BY_ID["fs"])]
    g = CL.BY_ID["b2g"]
    pairs = re.findall(r"(\d{4}) -> (\d{4})", hint3("c6_gray", 2))
    assert len(pairs) == 6
    for b, gc in pairs:
        o = CL.sim_outs(g, {f"B{3 - i}": int(ch) for i, ch in enumerate(b)})
        assert "".join(str(o[f"G{3 - i}"]) for i in range(4)) == gc, (b, gc)
    # gray stage: ctable rows are the six numbers in the hint
    rows = S["c6_gray"]["steps"][2]["rows"]
    assert ["".join(map(str, r)) for r in rows] == [p[0] for p in pairs]
    # mux hints state the authored data inputs
    assert hint3("c8_mux", 4).endswith("0 1 1 0 1 0 0 1.")
    assert hint3("c8_mux", 5).endswith("I0 = C, I1 = C', I2 = C', I3 = C.")
    assert hint3("c8_mux", 6) == "I0..I7 = D, D, D', 0, 0, D, 1, 1."
    # 4-bit adder demos: A=0110, B=0011
    add = CL.BY_ID["add4"]
    o = CL.sim_outs(add, dict(A3=0, A2=1, A1=1, A0=0, B3=0, B2=0, B1=1, B0=1, Cin=0))
    assert (o["S3"], o["S2"], o["S1"], o["S0"], o["Cout"]) == (1, 0, 0, 1, 0)       # 9
    o = CL.sim_outs(add, dict(A3=0, A2=1, A1=0, A0=1, B3=0, B2=1, B1=1, B0=1, Cin=0))
    assert (o["Cout"], o["S3"], o["S2"], o["S1"], o["S0"]) == (0, 1, 1, 0, 0)       # 5+7=12
    sub = CL.BY_ID["addsub"]
    o = CL.sim_outs(sub, dict(A3=1, A2=0, A1=0, A0=1, B3=0, B2=1, B1=0, B0=0, M=1))
    assert (o["Cout"], o["S3"], o["S2"], o["S1"], o["S0"]) == (1, 0, 1, 0, 1)       # 9-4=5
    print("  content OK (9 stages, 64 steps, 3 hints each, authored answers match the engine)")


def test_text_fits(screen):
    stages = build_comb_stages()
    strings = all_strings(stages, [])
    strings += all_strings(NOTES, [])
    strings += all_strings([[s["name"], s["purpose"], s["equations"], s["notes"]] for s in CL.SIMS], [])
    strings += CL.notes_lines()
    for s in strings:
        assert all(ord(c) < 128 for c in s), s
    for lines in NOTES.values():
        assert lines[0].isupper() or not any(c.islower() for c in lines[0]), lines[0]
        assert all(l.startswith("- ") for l in lines[1:])
    for l in CL.notes_lines():
        if not l.startswith("- "):
            assert not any(c.islower() for c in l), l

    puz = BasicCombinationalPuzzle()
    for si in range(len(puz.stages)):
        puz.stage_i = si
        puz.step_i = 0
        for ti in range(len(puz.stage["steps"])):
            puz.step_i = ti
            puz._enter_step()
            need = puz.side_needed_height()
            room = SIDE.height - 168 - 4
            assert need <= room, f"stage {si + 1} step {ti + 1}: side text {need} > {room}"
        assert puz._done_text_height(puz.stage) <= 300, f"stage {si + 1} done card too tall"
    print("  text fits (briefing + task above the hint box, done cards, ASCII only)")


# ------------------------------------------------------------------
# 3. HINTS AND WRONG ANSWERS
# ------------------------------------------------------------------
def test_hints(screen):
    puz = BasicCombinationalPuzzle()
    # tiers: nudge, stronger, answer; three wrong tries also reveal the answer
    puz.handle_event(key(pygame.K_h))
    assert puz.st["tier"] == 1
    puz.handle_event(key(pygame.K_h))
    puz.handle_event(key(pygame.K_h))
    puz.handle_event(key(pygame.K_h))
    assert puz.st["tier"] == 3 and puz._hint_text() == puz.step["hints"][2]

    # table: wrong cells are marked and explained, three tries show the answer
    puz = BasicCombinationalPuzzle()
    puz.stage_i, puz.step_i = 0, 2
    puz._enter_step()
    assert puz.step["kind"] == "ctable"
    for _ in range(3):
        puz.st["cells"] = {k: 1 for k in puz.st["cells"]}      # all ones: wrong
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.st["tier"] == 3 and puz.st["wrong"] == 3 and puz.st["bad"]
    assert "wrong" in puz.toast

    # slots: empty -> message, wrong gate -> reason
    puz = BasicCombinationalPuzzle()
    puz.stage_i, puz.step_i = 0, 3
    puz._enter_step()
    puz.handle_event(key(pygame.K_RETURN))
    assert "left" in puz.toast
    puz.handle_event(key(pygame.K_1))          # slot 1 = AND (wrong: SUM needs XOR)
    puz.handle_event(key(pygame.K_TAB))
    puz.handle_event(key(pygame.K_1))
    puz.handle_event(key(pygame.K_RETURN))
    assert puz.st["bad"] == {"s"} and "DIFFERENT" in puz.toast and puz.st["wrong"] == 1

    # mux: wrong slot explains the pair trick
    puz = BasicCombinationalPuzzle()
    puz.stage_i, puz.step_i = 7, 5
    puz._enter_step()
    for k in range(4):
        puz.handle_event(key(pygame.K_1))      # all "0"
        puz.handle_event(key(pygame.K_DOWN))
    puz.handle_event(key(pygame.K_RETURN))
    assert puz.st["bad"] and "Pairs:" in puz.toast

    # frames: cannot finish before every picture was seen
    puz = BasicCombinationalPuzzle()
    puz.handle_event(key(pygame.K_RETURN))
    assert puz.step_i == 0 and "every picture" in puz.toast
    print("  hints OK (3 tiers, auto-reveal after 3 wrong tries, reasons for wrong gates and slots)")


# ------------------------------------------------------------------
# 4. FULL PLAYTHROUGH WITH REAL EVENTS
# ------------------------------------------------------------------
def solve_step(puz):
    """Answer the current step with real key events. Returns the kind."""
    step, kind = puz.step, puz.step["kind"]
    ev = puz.handle_event
    if kind == "cframes":
        for _ in range(len(step["frames"]) - 1):
            ev(key(pygame.K_RIGHT))
    elif kind == "csee":
        names = puz._key_names()
        n = len(names)
        for i in range(1, 1 << n):
            if len(puz.st["done"]) == len(step["goals"]):
                break
            low = (i & -i).bit_length() - 1             # gray-code walk: flip one input at a time
            ev(key(digit_key(low)))
        assert len(puz.st["done"]) == len(step["goals"]), step["goals"]
    elif kind == "ctable":
        sim, rows, cols, exp = puz._table_spec(step)
        for c in range(len(cols)):
            for r in range(len(rows)):
                ev(key(DIGITS[exp[r][c]]))
    elif kind == "cslots":
        for nid in step["hidden"]:
            ev(key(DIGITS[step["options"].index(step["hidden"][nid]) + 1]))
            ev(key(pygame.K_TAB))
    elif kind == "cmux":
        exp = puz._mux_expect()
        for k in range(len(exp)):
            ev(key(DIGITS[step["options"].index(exp[k]) + 1]))
            ev(key(pygame.K_DOWN))
    elif kind == "cbits":
        for i, v in enumerate(step["target"]):
            if v:
                ev(key(DIGITS[i + 1]))
    elif kind == "choice":
        idx = [v for _l, v in step["options"]].index(step["correct"])
        ev(key(DIGITS[idx + 1]))
    else:
        raise AssertionError(kind)
    return kind


def test_playthrough(screen):
    nb = DetectiveNotebook()
    nb.set_mode("basic")
    puz = BasicCombinationalPuzzle(notebook=nb)
    seen_kinds, tags = set(), set()
    shot(puz, screen, "s1_t1_cframes")
    for si in range(9):
        assert puz.stage_i == si
        for ti in range(len(puz.stage["steps"])):
            assert puz.phase == "play" and puz.step_i == ti
            kind = puz.step["kind"]
            tag = puz.step.get("tag")
            seen_kinds.add(kind)
            if tag:
                tags.add(tag)
            if ti in (0, 1, 2, 3) or kind in ("cmux", "cbits", "choice"):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{kind}")
            solve_step(puz)
            if kind in ("ctable", "cslots", "cmux", "cbits"):
                shot(puz, screen, f"s{si + 1}_t{ti + 1}_{kind}_solved")
            puz.handle_event(key(pygame.K_RETURN))
        assert puz.phase == "done", f"stage {si + 1} should be finished"
        shot(puz, screen, f"s{si + 1}_done")
        assert puz.stage["id"] in puz.saved_stages
        puz.handle_event(key(pygame.K_RETURN))
    assert puz.is_solved()
    assert seen_kinds == {"cframes", "csee", "ctable", "cslots", "cmux", "cbits", "choice"}
    assert tags == {EXAM, SYLL}
    text = "\n".join(nb.reference_notes["MY BASIC NOTES"])
    for needle in ("COMBINATIONAL 1: HALF ADDER", "COMBINATIONAL 2: FULL ADDER", "Sum m(3, 5, 6, 7)",
                   "COMBINATIONAL 4: ADDER CHAINS", "ADDER-SUBTRACTOR", "COMBINATIONAL 5: PARITY",
                   "COMBINATIONAL 6: GRAY CODE", "COMBINATIONAL 7: DECODER", "COMBINATIONAL 8: MULTIPLEXER",
                   "I0..I7 = D, D, D', 0, 0, D, 1, 1", "COMBINATIONAL CHEAT SHEET"):
        assert needle in text, needle
    nb.toggle()
    nb._open_topic("MY BASIC NOTES")
    nb.draw(screen)
    pygame.image.save(screen, os.path.join(SHOTS, "notebook_comb_notes.png"))
    print("  playthrough OK (9 stages, every step kind, real key events, notebook autofilled)")


def test_mouse_and_leave(screen):
    """Buttons work with the mouse, and leaving mid-stage keeps progress."""
    puz = BasicCombinationalPuzzle()
    puz.draw(screen)
    nxt = [r for r, a in puz.buttons if a == ("frame", 1)][0]
    for _ in range(3):
        puz.handle_event(click(nxt.center))
        puz.draw(screen)
    chk = [r for r, a in puz.buttons if a == ("check",)][0]
    puz.handle_event(click(chk.center))
    assert puz.step_i == 1                                # moved to the sandbox
    puz.draw(screen)
    sw = [r for r, a in puz.buttons if a == ("in", "A")][0]
    puz.handle_event(click(sw.center))
    assert puz.st["vals"]["A"] == 1
    # slot: click cycles gates, hover tooltip draws without crashing
    puz.stage_i, puz.step_i = 0, 3
    puz._enter_step()
    puz.draw(screen)
    slot = [r for r, a in puz.buttons if a == ("slot", "s")][0]
    pygame.mouse.set_pos(slot.center)
    puz.handle_event(click(slot.center))
    assert puz.st["types"]["s"] == "AND"
    puz.handle_event(click(slot.center))
    assert puz.st["types"]["s"] == "OR"
    puz.draw(screen)
    # choice: click an option
    puz.stage_i, puz.step_i = 0, 4
    puz._enter_step()
    puz.draw(screen)
    opt = [r for r, a in puz.buttons if a == ("opt", 2)][0]
    puz.handle_event(click(opt.center))
    puz.handle_event(click([r for r, a in puz.buttons if a == ("check",)][0].center))
    assert puz.step_i == 5
    print("  mouse OK (frames, switches, slots, answers, CHECK)")


# ------------------------------------------------------------------
# 5. NOTEBOOK
# ------------------------------------------------------------------
def test_notebook(screen):
    nb = DetectiveNotebook()
    assert "COMBINATIONAL CIRCUITS" in nb.reference_topics            # shared: intermediate too
    base = {n: getattr(DetectiveNotebook, n) for n in
            ("SCIENTIST_NOTES", "LEVEL_GOALS", "LEVEL_HINTS", "DEFAULT_FINDINGS", "LEVEL_PRACTICE")}

    # BASIC: scientist notes for Level 5 are the beginner copy
    nb.set_mode("basic")
    assert nb.SCIENTIST_NOTES["level_five"] == BASIC_LEVEL_FIVE_NOTES
    assert nb.LEVEL_PRACTICE["level_five"] == "COMBINATIONAL CIRCUITS"
    assert nb.LEVEL_GOALS["level_five"] != base["LEVEL_GOALS"]["level_five"]
    for other in ("level_one", "level_four"):
        assert nb.SCIENTIST_NOTES[other] != base["SCIENTIST_NOTES"][other]
    for other in ("level_two", "level_three"):   # level_six is now the Basic sequential course
        assert nb.SCIENTIST_NOTES[other] == base["SCIENTIST_NOTES"][other]
    # INTERMEDIATE: scientist text untouched (only the shared lab was added)
    nb.set_mode("intermediate")
    for name, val in base.items():
        assert getattr(nb, name) == val, name
    assert nb.LEVEL_PRACTICE["level_five"] == "KARNAUGH MAPS"
    assert "MY BASIC NOTES" not in nb.reference_topics
    assert "COMBINATIONAL CIRCUITS" in nb.reference_topics

    # note order: gates, then K-maps, then combinational
    nb.set_mode("basic")
    nb.add_basic_note("c1_half", ["COMBINATIONAL 1: X"])
    nb.add_basic_note("k1_neighbours", ["KARNAUGH 1: X"])
    nb.add_basic_note("s3_not", ["STAGE 3: NOT GATE"])
    notes = nb.reference_notes["MY BASIC NOTES"]
    assert notes.index("STAGE 3: NOT GATE") < notes.index("KARNAUGH 1: X") < notes.index("COMBINATIONAL 1: X")

    # the lab, on both paths
    for mode in ("intermediate", "basic"):
        nb = DetectiveNotebook()
        nb.set_mode(mode)
        nb.toggle()
        nb._open_topic("COMBINATIONAL CIRCUITS")
        nb.draw(screen)
        assert nb.comb.sim["id"] == "ha"
        for i in range(len(CL.SIMS)):
            nb.draw(screen)
            if mode == "basic":
                pygame.image.save(screen, os.path.join(SHOTS, f"notebook_lab_{i + 1:02d}_{nb.comb.sim['id']}.png"))
            nb.handle_event(key(pygame.K_RIGHT))
        assert nb.comb.sim["id"] == "ha"                               # wrapped round
        nb.handle_event(key(pygame.K_LEFT))
        assert nb.comb.sim["id"] == "demux4"
        nb.handle_event(key(pygame.K_RIGHT))
        # keys flip inputs; B / ESC still go back
        nb.handle_event(key(pygame.K_1))
        assert nb.comb.vals["A"] == 1
        nb.handle_event(key(pygame.K_r))
        assert nb.comb.vals["A"] == 0
        # mouse: click the A switch
        nb.draw(screen)
        sw = [r for r, a in nb.comb.hits if a == ("in", "A")][0]
        nb.handle_event(click(sw.center))
        assert nb.comb.vals["A"] == 1
        nb.handle_event(click(nb.comb.nav[1][0].center))
        assert nb.comb.sim["id"] == "fa"
        # notes toggle with T, and the notes text page draws
        nb.handle_event(key(pygame.K_t))
        assert nb.comb_notes
        nb.draw(screen)
        if mode == "basic":
            pygame.image.save(screen, os.path.join(SHOTS, "notebook_comb_text.png"))
        nb.handle_event(key(pygame.K_t))
        assert not nb.comb_notes
        nb.handle_event(key(pygame.K_b))
        assert nb.page == "reference_index"
        nb.draw(screen)                                               # index with every topic fits
        if mode == "basic":
            pygame.image.save(screen, os.path.join(SHOTS, "notebook_index_basic.png"))
            rects = [r for r, _a in nb.buttons]
            assert max(r.bottom for r in rects) < nb.back_button.y, "topic buttons overlap BACK"
        else:
            rects = [r for r, _a in nb.buttons]
            assert max(r.bottom for r in rects) < nb.back_button.y
    # other labs still work after adding the new one
    nb = DetectiveNotebook()
    nb.toggle()
    for topic in ("KARNAUGH MAPS", "BOOLEAN ALGEBRA", "STATE MACHINES", "NUMBER SYSTEMS", "LOGIC GATES"):
        nb._open_topic(topic)
        nb.draw(screen)
        nb.handle_event(key(pygame.K_t))
        nb.draw(screen)
    print("  notebook OK (shared lab on both paths, per-path scientist notes, note order, other labs intact)")


def main():
    os.makedirs(SHOTS, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    print("Level 5 (combinational circuits) tests")
    test_engine()
    test_past_paper_numbers()
    test_content(screen)
    test_text_fits(screen)
    test_hints(screen)
    test_playthrough(screen)
    test_mouse_and_leave(screen)
    test_notebook(screen)
    print("ALL BASIC LEVEL 5 TESTS PASSED")


if __name__ == "__main__":
    main()