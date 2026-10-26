# puzzles/basic_numbers.py
# BASIC LEVEL 3 - "Number systems and codes" (10 stages + an exam revision page)
#
# Plugs into terminal 3 (puzzle_id memory_protocol, notebook level_three) on the BASIC path.
# It reuses the frame, tiered hints, notebook autofill and answer buttons of
# puzzles/basic_gates.py and adds five small activity types of its own.
#
#   1  Number systems        bases, allowed digits, place values, equivalent numbers
#   2  Decimal to binary     power-of-two switches, repeated division, remainder order
#   3  Binary to decimal     weights, sums, conversion table, round-trip check
#   4  Octal and hex         groups of 3 and 4 bits, decimal conversions
#   5  Complements           1's and 2's complement, fixed bit width, error correction
#   6  Signed numbers        sign-magnitude, 1's, 2's complement, ranges, overflow
#   7  Signed arithmetic     adding, subtracting with 2's complement, carry vs overflow
#   8  BCD                   encode, compare with binary, spot invalid codes
#   9  Excess-3 and Gray     encode, decode, convert, compare
#  10  Final mission         mixed multi-step challenges
#  +   EXAM REVISION PAGE    a long scrollable summary (mouse wheel, UP / DOWN, PAGE UP / DOWN)
#
# Every answer in the course is produced by the small helpers below, and the tests
# re-check each answer with Python's own int() / format(), so no authored answer is wrong.
#
# Activity types
#   bits    click switches (1-8 keys)        typed   type an answer (keypad or keyboard)
#   grid    fill cells of a table            pick    tap every correct item
#   order   tap items in the right order     choice  normal multiple choice (1-4 keys)
#
# Controls
#   mouse                  click switches, cells, keys and buttons
#   0-9 / A-F / -          type into the answer or the selected cell
#   BACKSPACE              delete          UP / DOWN / LEFT / RIGHT / TAB  move between cells
#   ENTER                  check / continue          H  hint (press again for more)

import random

import pygame

import settings
from puzzles.basic_gates import (
    BasicGatesPuzzle, WORK, FULL, wrap_text,
    PANEL, PANEL_EDGE, BG, CYAN, GREEN, RED, YELLOW, GREY, WHITE,
)

if not hasattr(BasicGatesPuzzle, "LEGEND_EXTRA"):
    raise ImportError(
        "puzzles/basic_gates.py is the OLD version. Replace it with the one from "
        "the latest update (basic_numbers.py needs the updated file)."
    )

DIG = "0123456789ABCDEF"
DEC_ALPHA = "0123456789"
NEG_ALPHA = "0123456789-"
BIN_ALPHA = "01"
HEX_ALPHA = DIG


# ------------------------------------------------------------------
# NUMBER HELPERS (the "engine" of the course)
# ------------------------------------------------------------------
def to_base(n, base, width=0):
    """Non-negative integer -> string in the given base (2..16)."""
    if n == 0:
        s = "0"
    else:
        s = ""
        while n:
            s = DIG[n % base] + s
            n //= base
    return s.rjust(width, "0")


def from_base(s, base):
    return int(s, base)


def ones(bits):
    """1's complement: flip every bit."""
    return "".join("1" if b == "0" else "0" for b in bits)


def twos(bits):
    """2's complement: flip every bit and add 1 (same width)."""
    w = len(bits)
    return format((int(ones(bits), 2) + 1) % (1 << w), f"0{w}b")


def enc_twos(n, w):
    """Signed integer -> w-bit 2's complement string."""
    return format(n % (1 << w), f"0{w}b")


def dec_twos(bits):
    """w-bit 2's complement string -> signed integer."""
    v = int(bits, 2)
    return v - (1 << len(bits)) if bits[0] == "1" else v


def enc_sm(n, w):
    """Signed integer -> w-bit sign-magnitude string."""
    return ("1" if n < 0 else "0") + format(abs(n), f"0{w - 1}b")


def dec_sm(bits):
    mag = int(bits[1:], 2)
    return -mag if bits[0] == "1" else mag


def enc_ones(n, w):
    """Signed integer -> w-bit 1's complement string."""
    return format(n, f"0{w}b") if n >= 0 else ones(format(-n, f"0{w}b"))


def dec_ones(bits):
    return -int(ones(bits), 2) if bits[0] == "1" else int(bits, 2)


def bcd(n):
    return "".join(format(int(d), "04b") for d in str(n))


def unbcd(code):
    groups = [code[i:i + 4] for i in range(0, len(code), 4)]
    return int("".join(str(int(g, 2)) for g in groups))


def excess3(n):
    return "".join(format(int(d) + 3, "04b") for d in str(n))


def unexcess3(code):
    groups = [code[i:i + 4] for i in range(0, len(code), 4)]
    return int("".join(str(int(g, 2) - 3) for g in groups))


def bin_to_gray(b):
    return b[0] + "".join(str(int(b[i - 1]) ^ int(b[i])) for i in range(1, len(b)))


def gray_to_bin(g):
    out = g[0]
    for i in range(1, len(g)):
        out += str(int(out[i - 1]) ^ int(g[i]))
    return out


def add_bits(a, b):
    """Column addition. Returns (sum_bits_same_width, carry_into_each_column, carry_out)."""
    w = len(a)
    carry = 0
    carries, out = [], []
    for i in range(w - 1, -1, -1):
        carries.append(carry)
        t = int(a[i]) + int(b[i]) + carry
        out.append(str(t & 1))
        carry = t >> 1
    return "".join(reversed(out)), "".join(reversed([str(c) for c in carries])), carry


def group(s, n=4):
    """'10110101' -> '1011 0101' (display only)."""
    return " ".join(s[i:i + n] for i in range(0, len(s), n))


def same(typed, expected, loose=False):
    typed = typed.replace(" ", "").upper()
    if loose:
        typed = typed.lstrip("0") or "0"
        expected = expected.lstrip("0") or "0"
    return typed == expected.upper()


# ------------------------------------------------------------------
# STEP BUILDERS
# ------------------------------------------------------------------
def _hints(a, b, c):
    return [a, b, c]


def _choice(q, labels, correct, ok, hints, show=None, task="Pick the answer.", meta=None):
    return {
        "kind": "choice", "visual": "num", "q": q, "show": show,
        "options": [(lab, f"o{i}") for i, lab in enumerate(labels)],
        "correct": f"o{correct}", "task": task, "ok": ok, "hints": hints, "meta": meta or {},
    }


def _pick(q, items, correct, ok, hints, task="Tap every right answer, then press CHECK.", meta=None):
    return {
        "kind": "pick", "q": q, "items": items, "correct": set(correct), "task": task,
        "ok": ok, "hints": hints, "meta": meta or {},
        "layout": "list" if max(len(i) for i in items) > 16 else "chips",
    }


def _typed(q, answer, alphabet, hints, ok, show=None, exact=False, label="YOUR ANSWER",
           traps=None, task=None, meta=None):
    return {
        "kind": "typed", "q": q, "show": show, "answer": answer, "alphabet": alphabet,
        "exact": exact, "label": label, "traps": traps or {},
        "task": task or "Type your answer, then press CHECK (or ENTER).",
        "ok": ok, "hints": hints, "meta": meta or {},
    }


def _grid(q, headers, rows, alphabet, hints, ok, loose=False, note=None, task=None, meta=None,
          colw=None):
    return {
        "kind": "grid", "q": q, "headers": headers, "rows": rows, "alphabet": alphabet,
        "loose": loose, "note": note, "colw": colw,
        "task": task or "Click a yellow cell and type. Fill every cell, then press CHECK.",
        "ok": ok, "hints": hints, "meta": meta or {},
    }


def _bits(q, n, mode, hints, ok, target=None, start=None, given=None, need=5, weights=True,
          task=None, meta=None):
    return {
        "kind": "bits", "q": q, "n": n, "mode": mode, "target": target,
        "start": list(start) if start is not None else [0] * n, "given": given,
        "need": need, "weights": weights,
        "task": task or "Click the switches (or press 1-%d), then press CHECK." % n,
        "ok": ok, "hints": hints, "meta": meta or {},
    }


def _order(q, items, order, ok, hints, task="Tap the items in the right order. BACKSPACE undoes.",
           meta=None):
    return {
        "kind": "order", "q": q, "items": items, "order": list(order), "task": task,
        "ok": ok, "hints": hints, "meta": meta or {},
    }


def Q(x):
    """Editable cell: expected answer x."""
    return ("?", x)


def _answer_hints(nudge, method, answer):
    return [nudge, method, f"The answer is {answer}."]


# ------------------------------------------------------------------
# STAGES
# ------------------------------------------------------------------
def _stage_systems():
    steps = [
        _pick("Binary is base 2. Tap EVERY symbol that is allowed in a binary number.",
              ["0", "1", "2", "5", "A", "9"], {0, 1},
              "Binary has only two digits: 0 and 1.",
              _hints("A base-b system has b digits, from 0 up to b - 1.",
                     "Base 2 has two digits, so only 0 and 1 are allowed.",
                     "Tap 0 and 1 only."),
              meta={"op": "digits", "base": 2}),
        _pick("Octal is base 8. Tap every symbol that is allowed in an octal number.",
              ["0", "3", "7", "8", "9", "A"], {0, 1, 2},
              "Octal uses 0 to 7. The digits 8 and 9 do not exist in base 8.",
              _hints("Base 8 has eight digits, counting from 0.",
                     "The biggest digit is one less than the base: 8 - 1 = 7.",
                     "Tap 0, 3 and 7."),
              meta={"op": "digits", "base": 8}),
        _pick("Hexadecimal is base 16. Tap every allowed SINGLE digit.",
              ["0", "9", "A", "F", "G", "10"], {0, 1, 2, 3},
              "Hex digits are 0-9 and then A-F (A = 10 ... F = 15). G does not exist, "
              "and 10 is two digits.",
              _hints("Base 16 needs sixteen different one-character digits.",
                     "After 9 we run out of numbers, so we use letters: A B C D E F.",
                     "Tap 0, 9, A and F."),
              meta={"op": "digits", "base": 16}),
        _choice("Which of these is a valid OCTAL number?",
                ["1289", "4567", "7A12", "3489"], 1,
                "4567 only uses digits 0-7. The others contain 8, 9 or A.",
                _hints("Octal numbers may only use the digits 0 to 7.",
                       "Look for the digits 8, 9 or letters. Those are not allowed.",
                       "The answer is 4567."),
                meta={"op": "valid_octal"}),
        _grid("Place values are powers of the base. Fill the place values of base 8.",
              ["", "8^3", "8^2", "8^1", "8^0"],
              [["Worth", Q("512"), Q("64"), Q("8"), Q("1")]], DEC_ALPHA,
              _hints("Each place is 8 times bigger than the place on its right.",
                     "Start on the right: 1, then 1 x 8 = 8, then 8 x 8 = 64, then 64 x 8.",
                     "The answer is 512, 64, 8, 1."),
              "Place values are powers of the base: 1, 8, 64, 512 for octal.",
              note="Place value = base ^ position, counting from 0 on the right.",
              meta={"op": "place_values", "base": 8}),
        _pick("Tap every number that equals decimal TEN.",
              ["1010 (binary)", "12 (octal)", "A (hex)", "10 (binary)", "11 (octal)", "F (hex)"],
              {0, 1, 2},
              "1010 in binary, 12 in octal and A in hex are all TEN, just written in different bases.",
              _hints("Convert each one to decimal. Which ones give 10?",
                     "1010 = 8 + 2. 12 in octal = 8 + 2. A in hex = 10. But 10 in binary is only 2.",
                     "Tap 1010 (binary), 12 (octal) and A (hex)."),
              meta={"op": "equivalents", "value": 10}),
    ]
    return {
        "id": "n01_systems", "title": "Number Systems", "sub": "bases and digits",
        "brief": ["A number system writes numbers with a fixed set of digits. The BASE is how many digits it has.",
                  "Binary = base 2, octal = base 8, decimal = base 10, hex = base 16 (digits 0-9 then A-F)."],
        "steps": steps,
        "example": ("table", ["Name", "Base", "Digits"],
                    [["Binary", "2", "0 1"], ["Octal", "8", "0 - 7"],
                     ["Decimal", "10", "0 - 9"], ["Hex", "16", "0-9, A-F"]], [110, 70, 150]),
        "items": [("RULE", "A base-b system uses the b digits 0 to b - 1. Nothing bigger is allowed."),
                  ("PLACE VALUE", "Each place is worth base^position, counting from 0 on the right: "
                                  "binary 1, 2, 4, 8 ... octal 1, 8, 64 ... hex 1, 16, 256 ..."),
                  ("REMEMBER", "The same quantity can be written in every base: 10 = 1010 (binary) = 12 (octal) = A (hex).")],
    }


def _stage_dec2bin():
    n = 13
    ladder = []
    x = n
    while x:
        ladder.append((x, x // 2, x % 2))
        x //= 2
    rows = [[f"{a} / 2", str(q), Q(str(r))] for a, q, r in ladder]
    rems = [r for _a, _q, r in ladder]                     # in the order they appear: 1 0 1 1
    ord_items = [f"{i + 1}st: {r}" if i == 0 else f"{i + 1}nd: {r}" if i == 1 else
                 f"{i + 1}rd: {r}" if i == 2 else f"{i + 1}th: {r}" for i, r in enumerate(rems)]
    ord_correct = list(range(len(rems) - 1, -1, -1))
    steps = [
        _bits("Switch ON the places that add up to 13.", 4, "target", target=13,
              ok="13 = 8 + 4 + 1, so the switches read 1101.",
              hints=_hints("Start with the biggest place value that fits into 13.",
                           "8 fits: 13 - 8 = 5. Then 4 fits: 5 - 4 = 1. Then 1.",
                           "Switch ON 8, 4 and 1 (the bits 1101)."),
              meta={"op": "dec2bin", "n": 13}),
        _bits("Make 37. It needs more places: 128, 64, 32 ...", 8, "target", target=37,
              ok="37 = 32 + 4 + 1, so the bits are 00100101.",
              hints=_hints("Skip every place value bigger than 37.",
                           "32 fits into 37 (37 - 32 = 5). Then 4 fits (5 - 4 = 1). Then 1.",
                           "Switch ON 32, 4 and 1 (the bits 00100101)."),
              meta={"op": "dec2bin", "n": 37}),
        _grid("Divide 13 by 2 again and again. Write each remainder.",
              ["Divide", "Quotient", "Remainder"], rows, BIN_ALPHA,
              _hints("The remainder is what is left over: 0 if the number is even, 1 if it is odd.",
                     "13 is odd (remainder 1), 6 is even (0), 3 is odd (1), 1 is odd (1).",
                     "Remainders, top to bottom: " + ", ".join(str(r) for r in rems) + "."),
              "Stop when the quotient reaches 0. The remainders are the bits of the answer.",
              meta={"op": "ladder", "n": 13}),
        _order("The remainders came out in this order. Tap them in the order you WRITE the binary "
               "number, leftmost bit first.", ord_items, ord_correct,
               "The LAST remainder is the leftmost bit, so 13 = 1101.",
               _hints("Which remainder is the biggest place value, the first or the last?",
                      "The first remainder is the right-most bit. The last one is the left-most bit.",
                      "Tap them from the bottom of the ladder to the top: 4th, 3rd, 2nd, 1st."),
               meta={"op": "order", "n": 13}),
        _choice("Ravi converted 19 to binary using repeated division (remainders listed top to bottom). "
                "His answer is wrong. What did he do wrong?",
                ["He read the remainders top to bottom", "He divided by 10 instead of 2",
                 "He forgot the last division", "He added the remainders"], 0,
                "Remainders must be read BOTTOM to TOP, so 19 = 10011.",
                _hints("His remainders are right. Look at the ORDER he wrote them in.",
                       "He wrote the first remainder first. But the first remainder is the right-most bit.",
                       "He read the remainders top to bottom. Read bottom to top: 10011."),
                show=["Remainders: 1 1 0 0 1", "Ravi wrote: 11001"],
                meta={"op": "error_order"}),
        _typed("Now write the correct binary number for 19.", "10011", BIN_ALPHA,
               _hints("Remainders for 19: 1, 1, 0, 0, 1 (top to bottom).",
                      "Read them from the bottom to the top.",
                      "The answer is 10011."),
               "Check: 16 + 2 + 1 = 19. Always check by converting back!",
               show=[("DECIMAL", "19")], label="BINARY",
               traps={"11001": "That is the remainders top to bottom. Read them bottom to top."},
               meta={"op": "to_base", "n": 19, "base": 2}),
    ]
    return {
        "id": "n02_dec2bin", "title": "Decimal to Binary", "sub": "switches and division",
        "brief": ["Binary place values double: 1, 2, 4, 8, 16 ... A switch that is ON adds its value.",
                  "Or divide by 2 again and again. The remainders are the bits. The LAST remainder is the left-most bit."],
        "steps": steps,
        "example": ("table", ["Divide", "Quot.", "Rem."],
                    [[f"{a} / 2", str(q), str(r)] for a, q, r in ladder], [110, 80, 80]),
        "items": [("METHOD 1", "Subtract the biggest power of two that fits, switch that place ON, and repeat."),
                  ("METHOD 2", "Divide by 2 until the quotient is 0. Write the remainders. Read them BOTTOM to TOP: 13 = 1101."),
                  ("REMEMBER", "Reading the remainders top to bottom reverses the number. Check by converting back.")],
    }


def _stage_bin2dec():
    steps = [
        _bits("Flip the switches and watch the total. Make at least five different numbers.", 4,
              "explore", need=5,
              ok="Every switch adds its place value when it is ON: 8, 4, 2, 1.",
              hints=_hints("Click the switches. The number under them changes.",
                           "Try to switch every place ON at least once, and make five different totals.",
                           "For example: 0001, 0010, 0101, 1000 and 1111 give five different totals."),
              task="Click the switches. Make five different numbers, then press CHECK.",
              meta={"op": "explore"}),
        _grid("Binary 1011. Multiply every bit by its weight, then add.",
              ["", "8", "4", "2", "1"],
              [["Bit", "1", "0", "1", "1"],
               ["Bit x weight", Q("8"), Q("0"), Q("2"), Q("1")],
               ["Sum", Q("11"), "", "", ""]], DEC_ALPHA,
              _hints("A bit of 1 keeps its weight. A bit of 0 gives 0.",
                     "Products: 8, 0, 2, 1. Now add them up.",
                     "8 + 0 + 2 + 1 = 11."),
              "1011 = 8 + 0 + 2 + 1 = 11.", loose=True,
              meta={"op": "weights", "bits": "1011"}),
        _typed("Convert binary 110101 to decimal.", "53", DEC_ALPHA,
               _hints("Write the weights over the bits from the right: 1, 2, 4, 8, 16, 32.",
                      "Add the weights where the bit is 1: 32 + 16 + 4 + 1.",
                      "The answer is 53."),
               "110101 = 32 + 16 + 0 + 4 + 0 + 1 = 53.",
               show=[("BINARY", "110101")], label="DECIMAL", meta={"op": "to_dec", "s": "110101", "base": 2}),
        _grid("Fill the decimal value of every binary number.", ["Binary", "Decimal"],
              [["1001", Q("9")], ["1100", Q("12")], ["0111", Q("7")], ["1111", Q("15")]], DEC_ALPHA,
              _hints("Use the weights 8, 4, 2, 1 over each number.",
                     "1001 = 8 + 1.   1100 = 8 + 4.   0111 = 4 + 2 + 1.   1111 = 8 + 4 + 2 + 1.",
                     "The answers are 9, 12, 7, 15."),
              "Four bits can make every number from 0 (0000) to 15 (1111).", loose=True,
              meta={"op": "table_bin2dec", "rows": ["1001", "1100", "0111", "1111"]}),
        _typed("Round trip, part 1. Convert 45 to binary.", "101101", BIN_ALPHA,
               _hints("The biggest power of two that fits in 45 is 32.",
                      "45 - 32 = 13 = 8 + 4 + 1. So the places 32, 8, 4, 1 are ON.",
                      "The answer is 101101."),
               "45 = 32 + 8 + 4 + 1 = 101101. Next: convert back to be sure.",
               show=[("DECIMAL", "45")], label="BINARY", meta={"op": "to_base", "n": 45, "base": 2}),
        _choice("Round trip, part 2. A student says 29 in binary is 11011. Convert 11011 BACK to "
                "decimal. Is the student right?",
                ["Yes: 11011 = 29", "No: 11011 = 27", "No: 11011 = 31", "No: 11011 = 25"], 1,
                "11011 = 16 + 8 + 0 + 2 + 1 = 27, not 29. The correct binary of 29 is 11101.",
                _hints("Add the weights 16, 8, 4, 2, 1 where the bit is 1.",
                       "16 + 8 + 0 + 2 + 1 = ?",
                       "It adds up to 27, so the student is wrong."),
                meta={"op": "roundtrip", "claim": 29, "bits": "11011"}),
    ]
    return {
        "id": "n03_bin2dec", "title": "Binary to Decimal", "sub": "weights and sums",
        "brief": ["Write the place values over the bits: ... 32 16 8 4 2 1. Multiply each bit by its weight.",
                  "Add the results. Zeros add nothing. Check an answer by converting it back (a round trip)."],
        "steps": steps,
        "example": ("table", ["Bit", "1", "0", "1", "1"],
                    [["Weight", "8", "4", "2", "1"], ["Worth", "8", "0", "2", "1"]], [90, 56, 56, 56, 56]),
        "items": [("RULE", "Decimal value = the sum of (bit x weight). Weights from the right: 1, 2, 4, 8, 16 ..."),
                  ("EXAMPLE", "1011 = 8 + 0 + 2 + 1 = 11.     110101 = 32 + 16 + 4 + 1 = 53."),
                  ("ROUND TRIP", "Convert to binary and back. If you do not land on the number you started with, find the slip.")],
    }


def _stage_octhex():
    steps = [
        _grid("Group the bits in threes. Write each group as one octal digit.",
              ["Bits", "110", "101", "011"], [["Octal", Q("6"), Q("5"), Q("3")]], DEC_ALPHA,
              _hints("Three bits make one octal digit. Use the weights 4, 2, 1.",
                     "110 = 4 + 2 = 6.   101 = 4 + 1 = 5.   011 = 2 + 1 = 3.",
                     "The octal number is 653."),
              "110 101 011 (binary) = 653 (octal).",
              meta={"op": "group", "bits": "110101011", "size": 3}),
        _grid("Group the bits in fours. Write each group as one hex digit.",
              ["Bits", "1010", "1111", "0011"], [["Hex", Q("A"), Q("F"), Q("3")]], HEX_ALPHA,
              _hints("Four bits make one hex digit. Use the weights 8, 4, 2, 1.",
                     "1010 = 8 + 2 = 10 = A.   1111 = 15 = F.   0011 = 3.",
                     "The hex number is AF3."),
              "1010 1111 0011 (binary) = AF3 (hex).",
              meta={"op": "group", "bits": "101011110011", "size": 4}),
        _typed("Convert octal 275 to binary. Use three bits for every digit.", "010111101", BIN_ALPHA,
               _hints("Turn each octal digit into three bits: 2, 7 and 5.",
                      "2 = 010,  7 = 111,  5 = 101. Join them together.",
                      "The answer is 010111101 (or 10111101 without the leading 0)."),
               "275 (octal) = 010 111 101 (binary).",
               show=[("OCTAL", "275")], label="BINARY", meta={"op": "oct2bin", "s": "275"}),
        _typed("Convert decimal 171 to hexadecimal.", "AB", HEX_ALPHA,
               _hints("Divide by 16. The remainder is the last hex digit.",
                      "171 / 16 = 10 remainder 11. In hex, 10 = A and 11 = B.",
                      "The answer is AB."),
               "171 = 10 x 16 + 11, and 10 = A, 11 = B, so 171 = AB.",
               show=[("DECIMAL", "171")], label="HEX", meta={"op": "to_base", "n": 171, "base": 16}),
        _typed("Convert hexadecimal 2F to decimal.", "47", DEC_ALPHA,
               _hints("The place values of hex are 1, 16, 256 ...",
                      "2 x 16 + F x 1, and F = 15.",
                      "32 + 15 = 47."),
               "2F = 2 x 16 + 15 = 47.",
               show=[("HEX", "2F")], label="DECIMAL", meta={"op": "to_dec", "s": "2F", "base": 16}),
        _typed("Convert octal 144 to decimal.", "100", DEC_ALPHA,
               _hints("The place values of octal are 1, 8, 64 ...",
                      "1 x 64 + 4 x 8 + 4 x 1.",
                      "64 + 32 + 4 = 100."),
               "144 (octal) = 64 + 32 + 4 = 100.",
               show=[("OCTAL", "144")], label="DECIMAL", meta={"op": "to_dec", "s": "144", "base": 8}),
    ]
    hex_rows = [[str(i), format(i, "04b"), format(i, "o"), DIG[i]] for i in range(10, 16)]
    return {
        "id": "n04_octhex", "title": "Octal and Hexadecimal", "sub": "groups of 3 and 4 bits",
        "brief": ["One octal digit = 3 bits. One hex digit = 4 bits. Group from the RIGHT and pad the left with zeros.",
                  "Hex digits: A = 10, B = 11, C = 12, D = 13, E = 14, F = 15."],
        "steps": steps,
        "example": ("table", ["Dec", "Binary", "Oct", "Hex"], hex_rows, [60, 100, 60, 60]),
        "items": [("BINARY TO OCT / HEX", "Group the bits in 3s (octal) or 4s (hex) from the right and convert each group."),
                  ("OCT / HEX TO BINARY", "Replace each digit by its 3 or 4 bits and join them: 275 (octal) = 010 111 101."),
                  ("DECIMAL", "Hex to decimal: add digit x 16^position. Decimal to hex: divide by 16 and read the remainders bottom to top.")],
    }


def _stage_complements():
    steps = [
        _bits("Flip every switch to make the 1's complement of 0110.", 4, "pattern", target="1001",
              start=[0, 1, 1, 0], given="0110", weights=False,
              ok="The 1's complement just flips every bit: 0110 becomes 1001.",
              hints=_hints("1's complement means: turn every 0 into 1 and every 1 into 0.",
                           "0 becomes 1, 1 becomes 0, 1 becomes 0, 0 becomes 1.",
                           "The answer is 1001."),
              meta={"op": "ones", "bits": "0110"}),
        _typed("Write the 1's complement of this 8-bit number.", "11010010", BIN_ALPHA,
               _hints("Flip every bit, one at a time, from the left.",
                      "0010 1101 becomes 1101 0010.",
                      "The answer is 11010010."),
               "Flipping all 8 bits gives 11010010.",
               show=[("BITS", group("00101101"))], exact=True, label="1'S COMPLEMENT",
               meta={"op": "ones", "bits": "00101101"}),
        _typed("Write the 2's complement of 0101 (4 bits).", "1011", BIN_ALPHA,
               _hints("2's complement = flip every bit, then ADD 1.",
                      "Flip 0101 to 1010. Then 1010 + 1 = ?",
                      "The answer is 1011."),
               "0101 flipped is 1010, plus 1 is 1011. So 1011 stands for -5 in 4 bits.",
               show=[("BITS", "0101")], exact=True, label="2'S COMPLEMENT",
               traps={"1010": "That is only the 1's complement. Now ADD 1."},
               meta={"op": "twos", "bits": "0101"}),
        _typed("Write the 2's complement of this 8-bit number.", "11101100", BIN_ALPHA,
               _hints("First flip all the bits, then add 1 to the result.",
                      "00010100 flips to 11101011. Add 1: 11101011 + 1 = ?",
                      "The answer is 11101100."),
               "Flip: 11101011. Add 1: 11101100. That is -20 in 8 bits.",
               show=[("BITS", group("00010100"))], exact=True, label="2'S COMPLEMENT",
               traps={"11101011": "That is only the 1's complement. Now ADD 1."},
               meta={"op": "twos", "bits": "00010100"}),
        _choice("Mia wants the 2's complement of 0110. She flips the bits and writes 1001. What did she forget?",
                ["To add 1 after flipping", "To flip the bits twice", "To subtract 1", "To remove the leading zero"], 0,
                "Flip, then ADD 1. The right answer is 1001 + 1 = 1010.",
                _hints("1001 is the 1's complement of 0110. Is there one more step for 2's complement?",
                       "2's complement = 1's complement + 1.",
                       "She forgot to add 1. 1001 + 1 = 1010."),
                meta={"op": "error_twos"}),
        _typed("Write 6 as an 8-bit binary number. Use all 8 bits.", "00000110", BIN_ALPHA,
               _hints("A fixed bit width means you must write exactly 8 bits.",
                      "6 = 110 in binary. Pad zeros on the LEFT until there are 8 bits.",
                      "The answer is 00000110."),
               "A fixed width always pads with zeros on the left: 6 = 00000110 in 8 bits.",
               show=[("DECIMAL", "6")], exact=True, label="8-BIT BINARY",
               meta={"op": "pad", "n": 6, "w": 8}),
    ]
    return {
        "id": "n05_complements", "title": "Complements", "sub": "1's and 2's complement",
        "brief": ["1's complement: flip every bit (0 becomes 1, 1 becomes 0).",
                  "2's complement: flip every bit, then ADD 1. Always keep the same number of bits."],
        "steps": steps,
        "example": ("table", ["Number", "1's comp", "2's comp"],
                    [["0101", ones("0101"), twos("0101")], ["0110", ones("0110"), twos("0110")],
                     ["0001", ones("0001"), twos("0001")], ["1000", ones("1000"), twos("1000")]],
                    [96, 100, 100]),
        "items": [("RULES", "1's complement = flip all bits.   2's complement = 1's complement + 1."),
                  ("SHORTCUT", "For 2's complement, copy the bits from the right up to and including the first 1, then flip the rest."),
                  ("REMEMBER", "The bit width is fixed. 6 is 0110 in 4 bits and 00000110 in 8 bits. The 2's complement of x is -x.")],
    }


def _stage_signed():
    steps = [
        _choice("In a signed binary number, what does the left-most bit tell you?",
                ["Whether it is positive or negative", "How big the number is",
                 "How many bits there are", "Whether it is even or odd"], 0,
                "The left-most bit is the SIGN bit: 0 means positive, 1 means negative.",
                _hints("It is a special bit, not part of the size.",
                       "0 means plus (+), 1 means minus (-).",
                       "The sign bit tells you positive or negative."),
                meta={"op": "signbit"}),
        _grid("Write -5 in 4 bits three ways. Start from +5 = 0101.",
              ["Method", "-5 in 4 bits"],
              [["Sign-magnitude", Q(enc_sm(-5, 4))], ["1's complement", Q(enc_ones(-5, 4))],
               ["2's complement", Q(enc_twos(-5, 4))]], BIN_ALPHA,
              _hints("Sign-magnitude: sign bit 1, then the size 5 = 101. 1's: flip all of 0101. 2's: flip and add 1.",
                     "Sign-magnitude 1 101.   1's complement: 0101 flips to 1010.   2's: 1010 + 1 = ?",
                     "The answers are 1101, 1010 and 1011."),
              "Same -5, three different bit patterns. 2's complement is the one computers use.",
              meta={"op": "neg5"}),
        _grid("These are 4-bit 2's complement numbers. Find each decimal value.",
              ["Bits", "Value"],
              [["0111", Q("7")], ["1000", Q("-8")], ["1111", Q("-1")], ["1010", Q("-6")]], NEG_ALPHA,
              _hints("If the left bit is 0, read it as normal. If it is 1, the number is negative.",
                     "A 1 in the left place is worth -8. So 1010 = -8 + 2 = -6.",
                     "The answers are 7, -8, -1, -6."),
              "In 4-bit 2's complement the left bit is worth -8, the others are worth +4, +2, +1.",
              meta={"op": "decode_twos", "rows": ["0111", "1000", "1111", "1010"]}),
        _grid("Fill the smallest and largest value each method can store in 4 bits.",
              ["Method", "Smallest", "Largest"],
              [["Sign-magnitude", Q("-7"), Q("7")], ["1's complement", Q("-7"), Q("7")],
               ["2's complement", Q("-8"), Q("7")]], NEG_ALPHA,
              _hints("With 4 bits only 3 bits are left for the size. 3 bits go up to 7.",
                     "Sign-magnitude and 1's complement: -7 to +7. 2's complement has one extra negative: -8 to +7.",
                     "The answers are -7, 7 / -7, 7 / -8, 7."),
              "For n bits, 2's complement holds -2^(n-1) up to 2^(n-1) - 1.",
              meta={"op": "ranges", "n": 4}),
        _choice("Can 4-bit 2's complement store +9?",
                ["Yes, as 1001", "No. 9 is above the largest value, 7 (overflow)",
                 "Yes, as 0111", "No, because 9 is odd"], 1,
                "The range is -8 to +7. 9 does not fit. 1001 would be read as -7, which is wrong.",
                _hints("What is the largest number 4-bit 2's complement can store?",
                       "The largest is 0111 = +7. Anything bigger overflows.",
                       "9 is bigger than 7, so it cannot be stored."),
                meta={"op": "overflow9"}),
        _typed("Write -3 as an 8-bit 2's complement number.", "11111101", BIN_ALPHA,
               _hints("Write +3 in 8 bits first: 00000011.",
                      "Flip every bit (11111100), then add 1.",
                      "The answer is 11111101."),
               "+3 = 00000011. Flip: 11111100. Add 1: 11111101.",
               show=[("DECIMAL", "-3")], exact=True, label="8-BIT 2'S COMPLEMENT",
               traps={"11111100": "That is only the 1's complement. Now ADD 1."},
               meta={"op": "enc_twos", "n": -3, "w": 8}),
        _typed("What is the SMALLEST value an 8-bit 2's complement number can hold?", "-128", NEG_ALPHA,
               _hints("The smallest value is -2^(n-1) with n = 8.",
                      "2^7 = 128.",
                      "The answer is -128 (bits 10000000)."),
               "8 bits: -128 to +127. In general -2^(n-1) up to 2^(n-1) - 1.",
               show=[("BITS", "8")], label="SMALLEST VALUE", exact=True, meta={"op": "min", "n": 8}),
    ]
    all4 = [[format(i, "04b"),
             "-0" if i == 8 else str(dec_sm(format(i, "04b"))),
             "-0" if i == 15 else str(dec_ones(format(i, "04b"))),
             str(dec_twos(format(i, "04b")))] for i in (0, 1, 7, 8, 9, 14, 15)]
    return {
        "id": "n06_signed", "title": "Signed Numbers", "sub": "negative numbers",
        "brief": ["Left-most bit = sign: 0 is positive, 1 is negative. Three ways to show a negative number.",
                  "Sign-magnitude keeps the size. 1's complement flips all bits. 2's complement flips and adds 1."],
        "steps": steps,
        "example": ("table", ["Bits", "SM", "1's", "2's"], all4, [80, 60, 60, 60]),
        "items": [("RANGES", "n bits. Sign-magnitude and 1's complement: -(2^(n-1) - 1) to +(2^(n-1) - 1). 2's complement: -2^(n-1) to +(2^(n-1) - 1)."),
                  ("OVERFLOW", "A result outside the range cannot be stored. 4 bits: 2's complement holds -8 to +7."),
                  ("REMEMBER", "2's complement has ONE zero. Sign-magnitude and 1's complement have two (+0 and -0).")],
    }


def _stage_arith():
    s, carries, _co = add_bits("0011", "0011")
    steps = [
        _grid("Add 0011 + 0011 (3 + 3). Fill the carry INTO each column and the sum.",
              ["", "bit 3", "bit 2", "bit 1", "bit 0"],
              [["Carry in"] + [Q(c) for c in carries],
               ["A", "0", "0", "1", "1"], ["B", "0", "0", "1", "1"],
               ["Sum"] + [Q(b) for b in s]], BIN_ALPHA,
              _hints("Work from the right. 1 + 1 = 10: write 0 and carry 1 into the next column.",
                     "bit 0: 1+1 = 0 carry 1.  bit 1: 1+1+1 = 1 carry 1.  bit 2: 0+0+1 = 1.  bit 3: 0.",
                     "Carries in: 0, 1, 1, 0.   Sum: 0110."),
              "0011 + 0011 = 0110, which is 3 + 3 = 6.",
              meta={"op": "carry_add", "a": "0011", "b": "0011"}),
        _typed("To do 7 - 3, find the 2's complement of 3 = 0011 (4 bits).", "1101", BIN_ALPHA,
               _hints("Subtracting means adding the 2's complement.",
                      "Flip 0011 to 1100, then add 1.",
                      "The answer is 1101 (that stands for -3)."),
               "1101 is -3 in 4 bits. Now add it to 7.",
               show=[("3 IN 4 BITS", "0011")], exact=True, label="2'S COMPLEMENT OF 3",
               traps={"1100": "That is only the 1's complement. Now ADD 1."},
               meta={"op": "twos", "bits": "0011"}),
        _typed("Now add 0111 + 1101 and keep only 4 bits (throw away the carry out).", "0100", BIN_ALPHA,
               _hints("0111 is 7 and 1101 is -3. Add them like normal binary numbers.",
                      "0111 + 1101 = 10100. That is 5 bits. Keep only the right 4.",
                      "The answer is 0100 = 4."),
               "7 - 3 = 4. The extra carry bit is simply thrown away.",
               show=[("ADD", "0111 + 1101")], exact=True, label="4-BIT RESULT",
               traps={"10100": "Keep only 4 bits. Throw away the carry out on the left."},
               meta={"op": "add_trunc", "a": "0111", "b": "1101"}),
        _typed("Compute 5 - 7 in 4 bits. Add 0101 to the 2's complement of 7 (1001).", "1110", BIN_ALPHA,
               _hints("-7 in 4 bits is 1001 (2's complement of 0111). Add 0101 + 1001.",
                      "0101 + 1001 = 1110 (no carry out).",
                      "The answer is 1110."),
               "1110 is -2 in 2's complement (-8 + 4 + 2). So 5 - 7 = -2. Correct!",
               show=[("ADD", "0101 + 1001")], exact=True, label="4-BIT RESULT",
               meta={"op": "add_trunc", "a": "0101", "b": "1001"}),
        _choice("0101 + 0100 (that is 5 + 4) in 4-bit 2's complement gives 1001. Is there overflow?",
                ["Yes: two positives gave a negative", "No: 5 + 4 = 9 is fine",
                 "No: there was no carry out", "Yes: because the answer is odd"], 0,
                "Overflow! Positive + positive cannot be negative. 9 does not fit in 4 bits (max +7).",
                _hints("Look at the sign bits: both numbers start with 0, the answer starts with 1.",
                       "Two positives must give a positive. A negative answer means the result is wrong.",
                       "Yes, overflow: two positives gave a negative."),
                show=["0101 + 0100 = 1001"], meta={"op": "overflow", "a": "0101", "b": "0100", "yes": True}),
        _choice("1101 + 1100 (that is -3 + -4) gives 11001. Keep 4 bits: 1001 = -7. There was a carry out. "
                "Is there overflow?",
                ["No: negative + negative = negative, which is correct", "Yes: because there was a carry out",
                 "Yes: because the answer is -7", "No: because the carry means the answer is 0"], 0,
                "No overflow. A carry out alone does NOT mean overflow. The sign is right: -3 + -4 = -7.",
                _hints("Compare the signs: both inputs are negative. What is the sign of the answer?",
                       "The answer 1001 is negative, and -7 is the right result. A carry out is not the test.",
                       "No overflow. The sign of the result is correct."),
                show=["1101 + 1100 = 1 1001"], meta={"op": "overflow", "a": "1101", "b": "1100", "yes": False}),
    ]
    return {
        "id": "n07_arith", "title": "Signed Binary Arithmetic", "sub": "add, subtract, overflow",
        "brief": ["Add from the right. 0+0 = 0, 0+1 = 1, 1+1 = 10 (write 0, carry 1), 1+1+1 = 11.",
                  "Subtract by ADDING the 2's complement. Overflow: two numbers with the SAME sign give the OPPOSITE sign."],
        "steps": steps,
        "example": ("table", ["Sum", "Bits", "Result"],
                    [["7 - 3", "0111+1101", "0100"], ["5 - 7", "0101+1001", "1110"],
                     ["5 + 4", "0101+0100", "overflow"], ["-3 + -4", "1101+1100", "1001 ok"]], [90, 130, 100]),
        "items": [("SUBTRACT", "A - B = A + (2's complement of B). Throw away any carry out of the left-most bit."),
                  ("OVERFLOW", "Same-sign inputs and a result with the opposite sign means overflow. Mixed-sign inputs can never overflow."),
                  ("WARNING", "A carry out is not the same as overflow. -3 + -4 has a carry out but is correct.")],
    }


def _stage_bcd():
    steps = [
        _grid("Encode each decimal digit as a 4-bit BCD group.", ["Digit", "BCD"],
              [["4", Q(bcd(4))], ["8", Q(bcd(8))], ["9", Q(bcd(9))]], BIN_ALPHA,
              _hints("BCD uses the ordinary 4-bit binary value of the digit.",
                     "4 = 0100.   8 = 1000.   9 = 1001.",
                     "The answers are 0100, 1000, 1001."),
              "Each digit 0-9 becomes its own 4 bits.", meta={"op": "bcd_digits", "digits": [4, 8, 9]}),
        _typed("Write 259 in BCD (no spaces).", "001001011001", BIN_ALPHA,
               _hints("Encode every digit separately: 2, 5 and 9.",
                      "2 = 0010,  5 = 0101,  9 = 1001. Join the three groups.",
                      "The answer is 001001011001."),
               "259 = 0010 0101 1001 in BCD. Each digit keeps its own 4 bits.",
               show=[("DECIMAL", "259")], exact=True, label="BCD", meta={"op": "bcd", "n": 259}),
        _grid("BCD is NOT ordinary binary. Fill the BCD (8 bits, no spaces) for each number.",
              ["Decimal", "Binary", "BCD"],
              [["12", "1100", Q(bcd(12))], ["45", "101101", Q(bcd(45))], ["90", "1011010", Q(bcd(90))]],
              BIN_ALPHA,
              _hints("Do not convert the whole number. Convert each DIGIT to 4 bits.",
                     "12 = 1 and 2 = 0001 0010. 45 = 0100 0101. 90 = 1001 0000.",
                     "The answers are 00010010, 01000101, 10010000."),
              "BCD uses more bits than ordinary binary, but each digit is easy to read.",
              meta={"op": "bcd_table", "ns": [12, 45, 90]}),
        _typed("Decode the BCD number 0111 0011 into a decimal number.", "73", DEC_ALPHA,
               _hints("Read each group of 4 bits as one decimal digit.",
                      "0111 = 7 and 0011 = 3.",
                      "The answer is 73."),
               "0111 0011 (BCD) = 73.", show=[("BCD", "0111 0011")], label="DECIMAL",
               meta={"op": "unbcd", "code": "01110011"}),
        _pick("Tap every group that is NOT a valid BCD digit.",
              ["0101", "1010", "1001", "1100", "1111", "0000"], {1, 3, 4},
              "BCD digits are 0000 to 1001 only. 1010 (10), 1100 (12) and 1111 (15) are invalid.",
              _hints("A BCD digit must be a decimal digit, 0 to 9.",
                     "1001 = 9 is the biggest valid group. Anything bigger is invalid.",
                     "Tap 1010, 1100 and 1111."),
              meta={"op": "invalid_bcd"}),
        _choice("Which of these is NOT a valid BCD number?",
                ["0001 1001", "0111 0000", "1000 1011", "0100 0010"], 2,
                "1000 1011: the group 1011 is 11, which is not a decimal digit.",
                _hints("Check every group of 4 bits. Each one must be 9 or less.",
                       "1011 = 11. That group is not allowed.",
                       "The answer is 1000 1011."),
                meta={"op": "invalid_bcd_number"}),
    ]
    return {
        "id": "n08_bcd", "title": "BCD", "sub": "binary coded decimal",
        "brief": ["BCD writes EACH decimal digit as its own 4-bit group: 259 = 0010 0101 1001.",
                  "Only 0000 to 1001 (0 to 9) are valid. The groups 1010 to 1111 are INVALID in BCD."],
        "steps": steps,
        "example": ("table", ["Digit", "BCD", "Digit", "BCD"],
                    [[str(i), bcd(i), str(i + 5), bcd(i + 5)] for i in range(5)], [70, 90, 70, 90]),
        "items": [("RULE", "Encode digit by digit. 0-9 use 0000-1001. 1010-1111 are never used."),
                  ("BCD vs BINARY", "25 in binary is 11001. 25 in BCD is 0010 0101. They are different codes."),
                  ("REMEMBER", "BCD needs more bits but converts to and from decimal digit by digit.")],
    }


def _stage_xs3gray():
    steps = [
        _grid("Excess-3: add 3 to the digit, then write 4 bits.", ["Digit", "Excess-3"],
              [["0", Q(excess3(0))], ["5", Q(excess3(5))], ["9", Q(excess3(9))]], BIN_ALPHA,
              _hints("Add 3 to the digit first: 0 + 3, 5 + 3, 9 + 3.",
                     "0 + 3 = 3 = 0011.   5 + 3 = 8 = 1000.   9 + 3 = 12 = 1100.",
                     "The answers are 0011, 1000, 1100."),
              "Excess-3 is binary of (digit + 3), so the code for 0 is 0011.",
              meta={"op": "xs3_digits", "digits": [0, 5, 9]}),
        _typed("Decode the excess-3 code 1001 into a decimal digit.", "6", DEC_ALPHA,
               _hints("Read the code as normal binary first, then subtract 3.",
                      "1001 = 9. Now 9 - 3 = ?",
                      "The answer is 6."),
               "1001 = 9, and 9 - 3 = 6.", show=[("EXCESS-3", "1001")], label="DIGIT",
               meta={"op": "unxs3", "code": "1001"}),
        _choice("What is special about Gray code?",
                ["Only ONE bit changes between neighbouring numbers", "It only uses the digits 0 to 9",
                 "Every code has 3 extra bits", "It adds 3 to every digit"], 0,
                "Gray code changes exactly one bit from one number to the next. That avoids glitches.",
                _hints("Think about counting: from one number to the next, how many bits change?",
                       "In plain binary 0111 to 1000 changes 4 bits. In Gray code only one bit ever changes.",
                       "The answer is: only one bit changes between neighbours."),
                meta={"op": "gray_property"}),
        _typed("Convert binary 1011 to Gray code. Keep the first bit, then XOR each bit with the one before.",
               "1110", BIN_ALPHA,
               _hints("The first Gray bit is the same as the first binary bit.",
                      "Next: 1 XOR 0 = 1.   0 XOR 1 = 1.   1 XOR 1 = 0.",
                      "The answer is 1110."),
               "1011 (binary) = 1110 (Gray).", show=[("BINARY", "1011")], exact=True, label="GRAY",
               meta={"op": "b2g", "b": "1011"}),
        _typed("Convert Gray code 1101 back to binary. Keep the first bit, then XOR with the previous BINARY bit.",
               "1001", BIN_ALPHA,
               _hints("The first binary bit equals the first Gray bit.",
                      "b1 = 1.  b2 = b1 XOR g2 = 1 XOR 1 = 0.  b3 = 0 XOR 0 = 0.  b4 = 0 XOR 1 = 1.",
                      "The answer is 1001."),
               "1101 (Gray) = 1001 (binary).", show=[("GRAY", "1101")], exact=True, label="BINARY",
               meta={"op": "g2b", "g": "1101"}),
        _grid("Compare 3-bit binary with Gray code. Fill the Gray column.", ["Decimal", "Binary", "Gray"],
              [["5", "101", Q(bin_to_gray("101"))], ["6", "110", Q(bin_to_gray("110"))],
               ["7", "111", Q(bin_to_gray("111"))]], BIN_ALPHA,
              _hints("Keep the first bit. Then XOR each bit with the bit to its left.",
                     "101 -> 1, 1 XOR 0 = 1, 0 XOR 1 = 1 -> 111. Do the same for 110 and 111.",
                     "The answers are 111, 101, 100."),
              "Look at the Gray column: neighbouring rows differ by exactly one bit.",
              meta={"op": "gray_table", "bs": ["101", "110", "111"]}),
    ]
    rows = [[str(i), format(i, "04b"), format(i + 3, "04b"), bin_to_gray(format(i, "04b"))] for i in range(10)]
    return {
        "id": "n09_xs3gray", "title": "Excess-3 and Gray Code", "sub": "encode, decode, compare",
        "brief": ["Excess-3 = the 4-bit binary of (digit + 3). Example: 4 + 3 = 7 = 0111.",
                  "Gray code changes only ONE bit between neighbours. Binary to Gray: keep the first bit, then XOR neighbouring bits."],
        "steps": steps,
        "example": ("table", ["Digit", "Binary", "Excess-3", "Gray"], rows[:6], [70, 90, 100, 80]),
        "items": [("EXCESS-3", "Encode: add 3, then write 4 bits. Decode: read as binary, then subtract 3."),
                  ("BINARY TO GRAY", "g1 = b1, then each next Gray bit = previous binary bit XOR this binary bit."),
                  ("GRAY TO BINARY", "b1 = g1, then each next binary bit = previous binary bit XOR this Gray bit.")],
    }


def _stage_final():
    n = 75
    steps = [
        _grid("Mission 1. Fill the row for decimal 75: binary, octal and hex.",
              ["Decimal", "Binary", "Octal", "Hex"],
              [["75", Q(to_base(75, 2)), Q(to_base(75, 8)), Q(to_base(75, 16))]], HEX_ALPHA,
              _hints("Find the binary first. Then group the bits in threes (octal) and fours (hex).",
                     "75 = 64 + 8 + 2 + 1 = 1001011. In threes: 001 001 011. In fours: 0100 1011.",
                     "The answers are 1001011, 113 and 4B."),
              "75 = 1001011 (binary) = 113 (octal) = 4B (hex).", loose=True,
              meta={"op": "chain", "n": 75}),
        _typed("Mission 2. Store -75 in 8-bit 2's complement.", "10110101", BIN_ALPHA,
               _hints("Write +75 in 8 bits (01001011). Then flip and add 1.",
                      "Flip 01001011 to 10110100. Add 1.",
                      "The answer is 10110101."),
               "-75 = 10110101. Check: -128 + 32 + 16 + 4 + 1 = -75.",
               show=[("DECIMAL", "-75")], exact=True, label="8-BIT 2'S COMPLEMENT",
               traps={"10110100": "That is only the 1's complement. Now ADD 1."},
               meta={"op": "enc_twos", "n": -75, "w": 8}),
        _typed("Mission 3. 30 - 45 in 8 bits. Add 30 (00011110) to the 2's complement of 45 (00101101).",
               "11110001", BIN_ALPHA,
               _hints("First find the 2's complement of 00101101 (it is -45).",
                      "Flip: 11010010, add 1: 11010011. Now add 00011110 + 11010011.",
                      "The answer is 11110001."),
               "00011110 + 11010011 = 11110001. Next: what number is that?",
               show=[("30", "00011110"), ("45", "00101101")], exact=True, label="8-BIT RESULT",
               meta={"op": "sub8", "a": 30, "b": 45}),
        _typed("Mission 4. Read 11110001 as an 8-bit 2's complement number. What is its decimal value?",
               "-15", NEG_ALPHA,
               _hints("The left bit is 1, so the number is negative. The left bit is worth -128.",
                      "-128 + 64 + 32 + 16 + 1 = ?",
                      "The answer is -15, which is 30 - 45."),
               "-128 + 113 = -15. So 30 - 45 = -15. Perfect!",
               show=[("BITS", "11110001")], label="DECIMAL VALUE", exact=True,
               meta={"op": "dec_twos", "bits": "11110001"}),
        _grid("Mission 5. Decimal 83: fill the BCD and excess-3 codes (8 bits each, no spaces).",
              ["Decimal", "BCD", "Excess-3"], [["83", Q(bcd(83)), Q(excess3(83))]], BIN_ALPHA,
              _hints("Treat the digits 8 and 3 separately. BCD: the digit itself. Excess-3: digit + 3.",
                     "BCD: 8 = 1000, 3 = 0011.   Excess-3: 11 = 1011, 6 = 0110.",
                     "The answers are 10000011 and 10110110."),
              "BCD 1000 0011, excess-3 1011 0110. Same digits, different code.",
              meta={"op": "bcd_xs3", "n": 83}),
        _typed("Mission 6. Convert binary 0111 to Gray code.", "0100", BIN_ALPHA,
               _hints("Keep the first bit. Then XOR each bit with the one before it.",
                      "0, 0 XOR 1 = 1, 1 XOR 1 = 0, 1 XOR 1 = 0.",
                      "The answer is 0100."),
               "0111 (binary) = 0100 (Gray).", show=[("BINARY", "0111")], exact=True, label="GRAY",
               meta={"op": "b2g", "b": "0111"}),
        _pick("Mission 7. Tap every FALSE statement.",
              ["Hex digit F equals 15", "4-bit 2's complement ranges from -7 to +7",
               "1010 is a valid BCD digit", "Gray code changes one bit between neighbours",
               "Octal numbers may contain the digit 8", "A - B can be done as A + (2's complement of B)"],
              {1, 2, 4},
              "False: the 4-bit 2's complement range is -8 to +7, 1010 is invalid in BCD and octal stops at 7.",
              _hints("Test each statement against what you learned. Three are false.",
                     "Check the range -8 to +7, the valid BCD digits (0-9) and the octal digits (0-7).",
                     "The false statements are the 2nd, the 3rd and the 5th."),
              meta={"op": "false_statements"}),
    ]
    return {
        "id": "n10_final", "title": "Final Mission", "sub": "mixed challenges",
        "brief": ["Last stage: no new ideas, only the old ones combined. Take every conversion one step at a time.",
                  "You will use bases, 2's complement, subtraction, BCD, excess-3 and Gray code."],
        "steps": steps,
        "example": ("table", ["Decimal", "75"],
                    [["Binary", "1001 011"], ["Octal", "113"], ["Hex", "4B"],
                     ["-75 (8 bit)", "1011 0101"], ["BCD of 83", "1000 0011"]], [120, 150]),
        "items": [("YOU CAN NOW", "Convert between decimal, binary, octal and hex, write negative numbers in 2's complement, "
                                  "add and subtract in binary, spot overflow, and use BCD, excess-3 and Gray code."),
                  ("NEXT", "The EXAM REVISION page follows. It collects every rule, table and worked example. "
                           "It is also saved in your notebook.")],
    }


def build_number_stages():
    return [
        _stage_systems(), _stage_dec2bin(), _stage_bin2dec(), _stage_octhex(), _stage_complements(),
        _stage_signed(), _stage_arith(), _stage_bcd(), _stage_xs3gray(), _stage_final(),
    ]


# ------------------------------------------------------------------
# NOTEBOOK AUTO-FILL
# ------------------------------------------------------------------
NOTEBOOK_LINES = {
    "n01_systems": [
        "NUMBERS 1: NUMBER SYSTEMS",
        "- BASE = how many digits the system has. Digits run from 0 to base - 1.",
        "- Binary base 2 (0-1), octal base 8 (0-7), decimal base 10 (0-9), hex base 16 (0-9 and A-F, A = 10 ... F = 15).",
        "- Place value = base ^ position (position 0 on the right). Value = sum of digit x place value.",
        "- The same quantity has many forms: 10 = 1010 (binary) = 12 (octal) = A (hex).",
    ],
    "n02_dec2bin": [
        "NUMBERS 2: DECIMAL TO BINARY",
        "- Powers of two: 1, 2, 4, 8, 16, 32, 64, 128. Switch ON the places that add up to the number.",
        "- Repeated division: divide by 2 until the quotient is 0. The remainders are the bits.",
        "- Read the remainders BOTTOM to TOP (the last remainder is the left-most bit). Example: 13 = 1101.",
        "- Check by converting back to decimal.",
    ],
    "n03_bin2dec": [
        "NUMBERS 3: BINARY TO DECIMAL",
        "- Write the weights over the bits (... 32 16 8 4 2 1) and add the weights where the bit is 1.",
        "- Example: 110101 = 32 + 16 + 4 + 1 = 53.   1011 = 8 + 2 + 1 = 11.",
        "- n bits hold 0 to 2^n - 1 (4 bits: 0-15, 8 bits: 0-255).",
        "- Round trip: convert there and back. You must land on the number you started with.",
    ],
    "n04_octhex": [
        "NUMBERS 4: OCTAL AND HEXADECIMAL",
        "- 1 octal digit = 3 bits. 1 hex digit = 4 bits. Group from the RIGHT, pad the left with zeros.",
        "- Hex digits: A = 10, B = 11, C = 12, D = 13, E = 14, F = 15.",
        "- 110 101 011 = 653 (octal).   1010 1111 0011 = AF3 (hex).   275 (octal) = 010 111 101.",
        "- Decimal to hex: divide by 16 (171 = AB). Hex to decimal: 2F = 2 x 16 + 15 = 47.",
    ],
    "n05_complements": [
        "NUMBERS 5: COMPLEMENTS",
        "- 1's complement = flip every bit.   2's complement = 1's complement + 1.",
        "- Keep the bit width fixed. 6 = 0110 in 4 bits, 00000110 in 8 bits.",
        "- Example: 0101 -> flip 1010 -> add 1 -> 1011.   00010100 -> 11101100.",
        "- Shortcut: copy bits from the right up to and including the first 1, then flip the rest.",
    ],
    "n06_signed": [
        "NUMBERS 6: SIGNED NUMBERS",
        "- Left-most bit = sign (0 positive, 1 negative). Three methods: sign-magnitude, 1's complement, 2's complement.",
        "- -5 in 4 bits: sign-magnitude 1101, 1's complement 1010, 2's complement 1011.",
        "- Ranges for n bits: sign-mag and 1's -(2^(n-1) - 1) to +(2^(n-1) - 1). 2's complement -2^(n-1) to +(2^(n-1) - 1).",
        "- 4 bits 2's complement: -8 to +7. 8 bits: -128 to +127. A result outside the range is OVERFLOW.",
    ],
    "n07_arith": [
        "NUMBERS 7: SIGNED BINARY ARITHMETIC",
        "- Binary add: 0+0 = 0, 0+1 = 1, 1+1 = 10 (carry 1), 1+1+1 = 11.",
        "- A - B = A + (2's complement of B). Discard the carry out of the left-most bit.",
        "- 7 - 3: 0111 + 1101 = 1 0100 -> 0100 = 4.   5 - 7: 0101 + 1001 = 1110 = -2.",
        "- Overflow: same-sign inputs give an opposite-sign result (5 + 4 = 1001 in 4 bits). A carry out is NOT overflow.",
    ],
    "n08_bcd": [
        "NUMBERS 8: BCD",
        "- BCD writes each decimal digit as its own 4 bits: 259 = 0010 0101 1001.",
        "- Valid groups are 0000 to 1001. The groups 1010 to 1111 are INVALID.",
        "- BCD is not binary: 25 = 11001 in binary but 0010 0101 in BCD.",
        "- BCD addition: if a group goes above 9, add 0110 (6) to correct it.",
    ],
    "n09_xs3gray": [
        "NUMBERS 9: EXCESS-3 AND GRAY CODE",
        "- Excess-3 = 4-bit binary of (digit + 3): 0 = 0011, 5 = 1000, 9 = 1100. Decode: read as binary, subtract 3.",
        "- Gray code: only ONE bit changes between neighbouring numbers.",
        "- Binary to Gray: keep the first bit, then XOR each bit with the previous binary bit. 1011 -> 1110.",
        "- Gray to binary: keep the first bit, then XOR each Gray bit with the previous binary bit. 1101 -> 1001.",
    ],
    "n10_final": [
        "NUMBERS 10: FINAL MISSION CHEAT SHEET",
        "- 75 = 1001011 (binary) = 113 (octal) = 4B (hex).   -75 in 8 bits = 10110101.",
        "- 30 - 45 in 8 bits = 00011110 + 11010011 = 11110001 = -15.",
        "- 83 in BCD = 1000 0011.  83 in excess-3 = 1011 0110.   0111 in Gray = 0100.",
        "- False facts to avoid: 4-bit 2's complement is -8 to +7, 1010 is not BCD, octal has no digit 8.",
    ],
}


# ------------------------------------------------------------------
# EXAM REVISION PAGE (content)
# ------------------------------------------------------------------
def _overflow_case(a, b):
    s, _c, co = add_bits(a, b)
    same_sign = a[0] == b[0]
    return s, co, same_sign and s[0] != a[0]


def revision_blocks():
    B = []

    def h1(t):
        B.append(("h1", t))

    def h2(t):
        B.append(("h2", t))

    def p(t):
        B.append(("p", t))

    def b(t):
        B.append(("b", t))

    def formula(t):
        B.append(("formula", t))

    def tip(t):
        B.append(("tip", t))

    def warn(t):
        B.append(("warn", t))

    def tbl(headers, rows, colw=None):
        B.append(("tbl", headers, rows, colw))

    def qa(q, a):
        B.append(("qa", q, a))

    p("Everything from stages 1 to 10 on one page: rules, tables and worked examples. Read it from top "
      "to bottom, then try the self-test at the end. A short copy is saved in your notebook "
      "(NOTEBOOK > TEST THE LOGIC > MY BASIC NOTES).")
    tip("In an exam: write the weights over the bits, work in small steps, and always check by converting back.")

    # ---- 1
    h1("1   NUMBER SYSTEMS: BASES, DIGITS, PLACE VALUES")
    p("A number system writes numbers with a fixed set of digits. The BASE (radix) is the number of digits. "
      "The digits run from 0 up to base - 1.")
    tbl(["System", "Base", "Digits", "Example", "In decimal"],
        [["Binary", "2", "0 1", "1011", str(int("1011", 2))],
         ["Octal", "8", "0 - 7", "17", str(int("17", 8))],
         ["Decimal", "10", "0 - 9", "45", "45"],
         ["Hexadecimal", "16", "0-9, A-F", "2F", str(int("2F", 16))]])
    formula("Value = sum of (digit x base^position).   Position 0 is the right-most digit.\n"
            "Example: 2F (hex) = 2 x 16^1 + 15 x 16^0 = 32 + 15 = 47.")
    h2("Place values (powers of the base)")
    tbl(["Power n"] + [str(n) for n in range(11)],
        [["2^n"] + [str(2 ** n) for n in range(11)]])
    tbl(["Power n", "0", "1", "2", "3", "4"],
        [["8^n"] + [str(8 ** n) for n in range(5)], ["16^n"] + [str(16 ** n) for n in range(5)]])
    h2("Counting 0 to 15 in four bases")
    tbl(["Decimal", "Binary", "Octal", "Hex"],
        [[str(i), format(i, "04b"), format(i, "o"), DIG[i]] for i in range(16)])
    warn("A digit can never be as big as the base. 2 is not a binary digit. 8 and 9 are not octal digits. "
         "In hex the letters A-F stand for 10-15.")

    # ---- 2
    h1("2   DECIMAL TO BINARY")
    h2("Method 1: subtract powers of two (switches)")
    p("Find the biggest power of two that fits, switch that place ON, subtract it and repeat.")
    p("Example 37: 32 fits (5 left), 16 no, 8 no, 4 fits (1 left), 2 no, 1 fits.  So 37 = 32 + 4 + 1 = "
      + to_base(37, 2) + ".")
    h2("Method 2: repeated division by 2")
    ladder, x = [], 37
    while x:
        ladder.append([f"{x} / 2", str(x // 2), str(x % 2)])
        x //= 2
    tbl(["Divide", "Quotient", "Remainder"], ladder)
    formula("Divide by 2 until the quotient is 0. Read the remainders from BOTTOM to TOP.\n"
            "37 -> remainders (top to bottom) 1 0 1 0 0 1 -> read upwards: " + to_base(37, 2) + ".")
    b("To convert to octal or hex, divide by 8 or by 16 instead of 2.")
    warn("Reading the remainders top to bottom reverses the number. 19 is 10011, not 11001.")
    tip("Check your answer: 100101 = 32 + 4 + 1 = 37.")

    # ---- 3
    h1("3   BINARY TO DECIMAL")
    formula("Write the weights ... 32 16 8 4 2 1 above the bits. Add the weights where the bit is 1.")
    tbl(["", "32", "16", "8", "4", "2", "1"],
        [["Bit", "1", "1", "0", "1", "0", "1"], ["Worth", "32", "16", "0", "4", "0", "1"]])
    p("110101 = 32 + 16 + 0 + 4 + 0 + 1 = 53.")
    acc, steps = 0, []
    for ch in "110101":
        acc = acc * 2 + int(ch)
        steps.append(str(acc))
    b("Doubling shortcut: start at 0. For each bit from the left, double and add the bit. "
      "110101 gives " + ", ".join(steps) + ".")
    b("n bits can hold 0 to 2^n - 1. 4 bits: 0-15.   8 bits: 0-255.   16 bits: 0-65535.")
    tip("Round trip: 45 -> " + to_base(45, 2) + " -> back to " + str(int(to_base(45, 2), 2)) +
        ". If you do not land on 45, find the slip.")

    # ---- 4
    h1("4   OCTAL AND HEXADECIMAL")
    b("Octal: 1 digit = 3 bits (weights 4 2 1).  Hex: 1 digit = 4 bits (weights 8 4 2 1).")
    b("Group the bits from the RIGHT. Add zeros on the LEFT if the last group is short.")
    v = "11010111"
    o_groups = group("0" + v if len(v) % 3 == 2 else v.zfill(9), 3)
    tbl(["Binary", "In threes", "Octal", "In fours", "Hex"],
        [[v, o_groups, to_base(int(v, 2), 8), group(v, 4), to_base(int(v, 2), 16)]])
    b("Octal or hex to binary: replace every digit by its 3 or 4 bits. 275 (octal) = 010 111 101.")
    b("Octal <-> hex: go through binary.")
    b("Decimal to hex: divide by 16. 171 / 16 = 10 remainder 11, so 171 = AB.")
    b("Hex to decimal: 2F = 2 x 16 + 15 = 47.   Octal to decimal: 144 = 64 + 32 + 4 = 100.")
    warn("Group from the right, not the left. 1011011 in fours is 0101 1011, not 1011 011.")

    # ---- 5
    h1("5   COMPLEMENTS")
    formula("1's complement = flip every bit.        2's complement = 1's complement + 1.")
    tbl(["Number", "Width", "1's complement", "2's complement"],
        [["0101", "4", ones("0101"), twos("0101")],
         ["0110", "4", ones("0110"), twos("0110")],
         ["1000", "4", ones("1000"), twos("1000")],
         ["00010100", "8", ones("00010100"), twos("00010100")]])
    b("Shortcut for 2's complement: copy the bits from the right up to and including the first 1, "
      "then flip all the bits to the left of it.")
    b("The complement of the complement is the original number. The 2's complement of x stands for -x.")
    b("Fixed width: 6 = 0110 in 4 bits and 00000110 in 8 bits. To widen a signed number copy the sign bit "
      "on the left: 1011 (-5) becomes 11111011 (still -5).")
    warn("Forgetting the +1 is the most common error. 1's complement of 0110 is 1001, but the 2's "
         "complement is 1010.")

    # ---- 6
    h1("6   SIGNED NUMBERS")
    p("The left-most bit is the sign bit: 0 = positive, 1 = negative.")
    tbl(["Bits", "Unsigned", "Sign-magnitude", "1's complement", "2's complement"],
        [[format(i, "04b"), str(i),
          "-0" if i == 8 else str(dec_sm(format(i, "04b"))),
          "-0" if i == 15 else str(dec_ones(format(i, "04b"))),
          str(dec_twos(format(i, "04b")))] for i in range(16)])
    h2("How many values fit in n bits?")
    tbl(["Bits", "Sign-magnitude and 1's complement", "2's complement"],
        [[str(n), f"-{2 ** (n - 1) - 1} to +{2 ** (n - 1) - 1}", f"-{2 ** (n - 1)} to +{2 ** (n - 1) - 1}"]
         for n in (4, 8, 16)])
    formula("Sign-magnitude and 1's complement: -(2^(n-1) - 1) to +(2^(n-1) - 1).\n"
            "2's complement: -2^(n-1) to +(2^(n-1) - 1).")
    b("In n-bit 2's complement the left-most bit is worth -2^(n-1). 1010 = -8 + 2 = -6.")
    b("Sign-magnitude and 1's complement have TWO zeros (+0 and -0). 2's complement has only one, "
      "which is why computers use it.")
    b("OVERFLOW: a result outside the range cannot be stored. +9 does not fit in 4-bit 2's complement (max +7).")

    # ---- 7
    h1("7   SIGNED BINARY ARITHMETIC")
    tbl(["A", "B", "Carry in", "Sum bit", "Carry out"],
        [[str(a), str(c), str(ci), str((a + c + ci) & 1), str((a + c + ci) >> 1)]
         for a in (0, 1) for c in (0, 1) for ci in (0, 1)])
    s3, c3, _co = add_bits("0011", "0011")
    p("Add from the right, one column at a time, carrying into the next column. Example 0011 + 0011: "
      "carries into the columns (left to right) " + " ".join(c3) + ", sum " + s3 + " (3 + 3 = 6).")
    formula("A - B = A + (2's complement of B).   Discard any carry out of the left-most bit.")
    s73, _c, co73 = add_bits("0111", twos("0011"))
    s57, _c, _co = add_bits("0101", twos("0111"))
    b(f"7 - 3: 2's complement of 0011 is {twos('0011')}.  0111 + {twos('0011')} = {co73} {s73}.  "
      f"Drop the carry: {s73} = {int(s73, 2)}.")
    b(f"5 - 7: 2's complement of 0111 is {twos('0111')}.  0101 + {twos('0111')} = {s57} = {dec_twos(s57)}.")
    formula("OVERFLOW rule: the two inputs have the SAME sign and the result has the OPPOSITE sign.\n"
            "Same test: the carry INTO the sign bit differs from the carry OUT of the sign bit.\n"
            "Inputs with different signs can never overflow.")
    rows = []
    for da, db, a, c in ((5, 4, "0101", "0100"), (5, 2, "0101", "0010"), (-3, -4, "1101", "1100"),
                         (-8, -1, "1000", "1111"), (6, -2, "0110", "1110")):
        s, co, ov = _overflow_case(a, c)
        rows.append([f"{da} + ({db})" if db < 0 else f"{da} + {db}", f"{a} + {c}", f"{co} {s}",
                     str(dec_twos(s)), "YES" if ov else "no"])
    tbl(["Sum", "Bits", "Carry + result", "Reads as", "Overflow?"], rows)
    warn("A carry out is NOT the same as overflow. -3 + -4 has a carry out but the answer -7 is correct.")

    # ---- 8
    h1("8   BCD (BINARY CODED DECIMAL)")
    tbl(["Digit", "BCD", "Digit", "BCD"], [[str(i), bcd(i), str(i + 5), bcd(i + 5)] for i in range(5)])
    b("Encode digit by digit: 259 = " + group(bcd(259)) + ". Decode: read each group of 4 bits as one digit.")
    b("BCD is NOT ordinary binary: 25 is 11001 in binary but " + group(bcd(25)) + " in BCD.")
    b("Only 0000 to 1001 are valid. 1010, 1011, 1100, 1101, 1110 and 1111 are INVALID. "
      "6 of the 16 four-bit codes are wasted.")
    s85 = format(8, "04b") + " + " + format(5, "04b")
    raw = 8 + 5
    b(f"BCD addition: if a group is above 9 (or carries), add 0110 to fix it. 8 + 5: {s85} = "
      f"{format(raw, '04b')}, invalid, so add 0110 -> {group(format(raw + 6, '08b'))} = 13.")
    tip("BCD is easy for humans and displays (each digit has its own group) but it needs more bits than binary.")

    # ---- 9
    h1("9   EXCESS-3 AND GRAY CODE")
    tbl(["Digit", "BCD (8421)", "Excess-3", "Gray (4 bits)"],
        [[str(i), format(i, "04b"), format(i + 3, "04b"), bin_to_gray(format(i, "04b"))] for i in range(10)])
    formula("Excess-3 = 4-bit binary of (digit + 3).   Decode: read as binary, then subtract 3.")
    b("Excess-3 is self-complementing: flip every bit of the code of d and you get the code of 9 - d. "
      f"2 = {excess3(2)}, flipped {ones(excess3(2))} = code of 7.")
    formula("Binary to Gray: keep the first bit. Each next Gray bit = previous binary bit XOR this binary bit.\n"
            "Gray to binary: keep the first bit. Each next binary bit = previous binary bit XOR this Gray bit.")
    b(f"1011 -> Gray {bin_to_gray('1011')}.      Gray 1101 -> binary {gray_to_bin('1101')}.")
    b("Gray code: neighbouring codes differ in exactly ONE bit (the last and the first do too). It is used "
      "in rotary encoders and Karnaugh-map labels, to avoid glitches.")
    tbl(["Decimal", "Binary (3 bits)", "Gray (3 bits)"],
        [[str(i), format(i, "03b"), bin_to_gray(format(i, "03b"))] for i in range(8)])

    # ---- 10
    h1("10   CHEAT SHEET, COMMON MISTAKES AND SELF-TEST")
    tbl(["Task", "Method"],
        [["Decimal to binary", "Subtract powers of 2, or divide by 2 and read remainders bottom to top"],
         ["Binary to decimal", "Add the weights (1 2 4 8 ...) where the bit is 1"],
         ["Binary to octal / hex", "Group bits in 3s / 4s from the right"],
         ["Octal / hex to decimal", "Add digit x base^position"],
         ["Decimal to octal / hex", "Divide by 8 / 16, read remainders bottom to top"],
         ["Negative number", "2's complement: flip all bits, add 1 (keep the width)"],
         ["A - B", "A + 2's complement of B, drop the carry out"],
         ["Overflow check", "Same-sign inputs, opposite-sign result"],
         ["Decimal to BCD", "Each digit as its own 4 bits (0000-1001 only)"],
         ["Decimal to excess-3", "Add 3 to each digit, then 4 bits"],
         ["Binary <-> Gray", "XOR neighbouring bits (first bit is copied)"]])
    h2("Mistakes that cost marks")
    warn("Reading division remainders top to bottom.")
    warn("Forgetting +1 for 2's complement, or forgetting the fixed width.")
    warn("Using a digit that is not allowed in the base (8 in octal, 2 in binary).")
    warn("Grouping bits from the left instead of the right.")
    warn("Calling every carry out an overflow. Compare the signs instead.")
    warn("Treating BCD as binary, or accepting 1010-1111 as BCD digits.")
    warn("Forgetting that 4-bit 2's complement goes to -8 but only up to +7.")
    h2("Self-test (cover the green answers and try!)")
    qa("What digits does base 8 allow?", "0 to 7")
    qa("Convert binary 100101 to decimal.", str(int("100101", 2)))
    qa("Convert decimal 58 to binary.", to_base(58, 2))
    qa("Convert binary 11010111 to hexadecimal.", to_base(int("11010111", 2), 16))
    qa("Convert hex 3C to binary (8 bits).", format(int("3C", 16), "08b"))
    qa("Write the 2's complement of 00101100 (8 bits).", twos("00101100"))
    qa("What is the range of 6-bit 2's complement numbers?", "-32 to +31")
    qa("Compute 6 - 4 in 4-bit 2's complement.", add_bits("0110", twos("0100"))[0] + " (= 2)")
    s65 = add_bits("0110", "0101")[0]
    qa("Is 0110 + 0101 an overflow in 4-bit 2's complement?",
       f"Yes. It gives {s65} = {dec_twos(s65)}, but 6 + 5 = 11 does not fit (max +7)")
    qa("Write 704 in BCD.", group(bcd(704)))
    qa("Is 1010 a valid BCD digit?", "No. 1010 is 10, and BCD digits stop at 9")
    qa("Write 6 in excess-3.", excess3(6))
    qa("Convert binary 1000 to Gray code.", bin_to_gray("1000"))
    qa("Convert Gray code 1110 to binary.", gray_to_bin("1110"))

    return B


REVISION_NOTES = [
    "NUMBERS: EXAM REVISION SHEET",
    "- Bases: binary 2, octal 8, decimal 10, hex 16. Digits 0 to base - 1. Value = sum of digit x base^position.",
    "- Dec to bin: subtract powers of 2, or divide by 2 and read remainders BOTTOM to TOP. Check by converting back.",
    "- Bin to octal / hex: group bits in 3s / 4s from the RIGHT. Hex A-F = 10-15.",
    "- 1's complement = flip. 2's complement = flip + 1 (fixed width). 2's complement of x stands for -x.",
    "- Ranges: n-bit 2's complement -2^(n-1) to 2^(n-1) - 1. Sign-mag and 1's: +/-(2^(n-1) - 1). Two zeros in those two.",
    "- A - B = A + 2's complement of B, drop the carry out. Overflow = same-sign inputs, opposite-sign result.",
    "- BCD: each digit as 4 bits, only 0000-1001 valid (25 = 0010 0101). Add 0110 when a BCD group exceeds 9.",
    "- Excess-3 = digit + 3 in 4 bits (self-complementing). Gray: one bit changes per step; b to g: g1 = b1, gi = b(i-1) XOR bi.",
    "- Mistakes: remainders top-down, forgetting +1, illegal digits, grouping from the left, carry out mistaken for overflow.",
]


# ------------------------------------------------------------------
# EXAM REVISION PAGE (renderer)
# ------------------------------------------------------------------
def _revision_fonts():
    return {
        "h1": pygame.font.Font(None, 34), "h2": pygame.font.Font(None, 28),
        "p": pygame.font.Font(None, 23), "t": pygame.font.Font(None, 21),
        "th": pygame.font.Font(None, 21),
    }


def render_revision(width, surface=None, fonts=None):
    """Lay the revision blocks out. Returns the content height. Draws if a surface is given."""
    fonts = fonts or _revision_fonts()
    blocks = revision_blocks()
    y = 6
    LH = 22

    def text_lines(font, text, w):
        out = []
        for para in text.split("\n"):
            out.extend(wrap_text(font, para, w) or [""])
        return out

    for blk in blocks:
        t = blk[0]
        if t == "h1":
            y += 8
            if surface is not None:
                pygame.draw.rect(surface, (24, 70, 100), (0, y, width, 38), border_radius=8)
                img = fonts["h1"].render(blk[1], True, WHITE)
                surface.blit(img, (14, y + 19 - img.get_height() // 2))
            y += 38 + 10
        elif t == "h2":
            if surface is not None:
                surface.blit(fonts["h2"].render(blk[1], True, CYAN), (4, y))
            y += 28 + 4
        elif t == "p":
            for line in text_lines(fonts["p"], blk[1], width - 10):
                if surface is not None:
                    surface.blit(fonts["p"].render(line, True, WHITE), (4, y))
                y += LH
            y += 6
        elif t == "b":
            first = True
            for line in text_lines(fonts["p"], blk[1], width - 40):
                if surface is not None:
                    if first:
                        pygame.draw.circle(surface, CYAN, (16, y + 8), 3)
                    surface.blit(fonts["p"].render(line, True, WHITE), (30, y))
                first = False
                y += LH
            y += 4
        elif t in ("formula", "tip", "warn"):
            colors = {"formula": ((40, 38, 14), YELLOW, ""), "tip": ((16, 44, 30), GREEN, "TIP  "),
                      "warn": ((52, 22, 22), RED, "WATCH OUT  ")}
            fill, edge, tag = colors[t]
            text = tag + blk[1] if t != "formula" else blk[1]
            lines = text_lines(fonts["p"], text, width - 36)
            h = len(lines) * LH + 14
            if surface is not None:
                pygame.draw.rect(surface, fill, (0, y, width, h), border_radius=8)
                pygame.draw.rect(surface, edge, (0, y, width, h), 2, border_radius=8)
                for i, line in enumerate(lines):
                    col = edge if (i == 0 and tag) else WHITE
                    if t == "formula":
                        col = YELLOW
                    surface.blit(fonts["p"].render(line, True, col), (14, y + 7 + i * LH))
            y += h + 8
        elif t == "tbl":
            headers, rows, colw = blk[1], blk[2], blk[3]
            f = fonts["t"]
            ncols = len(headers)
            widths = colw or [max([f.size(str(headers[c]))[0]] + [f.size(str(r[c]))[0] for r in rows]) + 22
                              for c in range(ncols)]
            total = sum(widths)
            if total > width - 8 and colw is None:                     # squeeze evenly
                scale = (width - 8) / total
                widths = [int(w * scale) for w in widths]
            rh = 25
            x0 = 4
            if surface is not None:
                x = x0
                for c in range(ncols):
                    rect = pygame.Rect(x, y, widths[c] - 3, rh - 2)
                    pygame.draw.rect(surface, (30, 60, 84), rect, border_radius=4)
                    img = fonts["th"].render(str(headers[c]), True, YELLOW)
                    surface.blit(img, img.get_rect(center=rect.center))
                    x += widths[c]
                for ri, row in enumerate(rows):
                    x = x0
                    for c in range(ncols):
                        rect = pygame.Rect(x, y + (ri + 1) * rh, widths[c] - 3, rh - 2)
                        pygame.draw.rect(surface, (22, 38, 54) if ri % 2 == 0 else (26, 46, 64), rect,
                                         border_radius=4)
                        img = f.render(str(row[c]), True, CYAN if c == 0 and ncols > 2 else WHITE)
                        surface.blit(img, img.get_rect(center=rect.center))
                        x += widths[c]
            y += (len(rows) + 1) * rh + 10
        elif t == "qa":
            for line in text_lines(fonts["p"], "Q.  " + blk[1], width - 10):
                if surface is not None:
                    surface.blit(fonts["p"].render(line, True, WHITE), (4, y))
                y += LH
            for line in text_lines(fonts["p"], "Answer: " + blk[2], width - 40):
                if surface is not None:
                    surface.blit(fonts["p"].render(line, True, GREEN), (30, y))
                y += LH
            y += 8
    return y + 20


# ------------------------------------------------------------------
# THE PUZZLE
# ------------------------------------------------------------------
OWN_KINDS = ("bits", "typed", "grid", "pick", "order")
VIEW = pygame.Rect(FULL.x + 10, FULL.y + 52, FULL.width - 38, FULL.height - 52 - 56)


class BasicNumberSystemsPuzzle(BasicGatesPuzzle):
    """Ten-stage beginner course on number systems and codes, then an exam revision page."""

    COURSE_TITLE = "BASIC LEVEL 3  -  NUMBER SYSTEMS AND CODES"
    LEGEND_EXTRA = dict(BasicGatesPuzzle.LEGEND_EXTRA, **{
        "bits": "click switches or press 1-8 (left to right)",
        "typed": "type digits / letters, BACKSPACE deletes",
        "grid": "click a cell or use arrows / TAB, then type",
        "pick": "click answers or press 1-8 (click again to undo)",
        "order": "click items in order, BACKSPACE = undo",
        "choice": "click an answer or press 1-4",
    })

    def _make_stages(self):
        return build_number_stages()

    def __init__(self, notebook=None):
        self.rev_scroll = 0
        self.rev_surface = None
        self.rev_drag = False
        self.rev_t0 = 0.0
        super().__init__(notebook)

    # ---------------- helpers ----------------
    @staticmethod
    def _editable(step):
        cells = []
        for r, row in enumerate(step["rows"]):
            for c, cell in enumerate(row):
                if isinstance(cell, tuple):
                    cells.append((r, c, cell[1]))
        return cells

    @staticmethod
    def _bits_value(bits):
        return int("".join(str(b) for b in bits), 2)

    @staticmethod
    def _char(event):
        u = getattr(event, "unicode", "") or ""
        if u and u.isprintable() and not u.isspace():
            return u.upper()
        d = BasicGatesPuzzle._digit(event.key)
        if d is not None:
            return str(d)
        if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            return "-"
        name = pygame.key.name(event.key)
        return name.upper() if len(name) == 1 else ""

    # ---------------- step setup ----------------
    def _enter_step(self):
        super()._enter_step()
        step, st = self.step, self.st
        kind = step["kind"]
        if kind == "bits":
            st["bits"] = list(step["start"])
            st["seen"] = {self._bits_value(st["bits"])}
            st["used"] = {i for i, b in enumerate(st["bits"]) if b}
        elif kind == "typed":
            st["typed"] = ""
        elif kind == "grid":
            cells = self._editable(step)
            st.update(vals=["" for _ in cells], sel=0, bad=set())
        elif kind == "pick":
            st["chosen"] = set()
        elif kind == "order":
            st["picked"] = []

    # ---------------- events ----------------
    def handle_event(self, event):
        if self.phase != "revision":
            return super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            self._rev_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self._scroll(-64)
            elif event.button == 5:
                self._scroll(64)
            elif event.button == 1:
                track = self._rev_track()
                if track.inflate(16, 0).collidepoint(event.pos):
                    self.rev_drag = True
                    self._drag_to(event.pos[1])
                else:
                    for rect, action in self.buttons:
                        if rect.collidepoint(event.pos):
                            self._on_action(action)
                            break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.rev_drag = False
        elif event.type == pygame.MOUSEMOTION and self.rev_drag:
            self._drag_to(event.pos[1])

    def _on_key(self, event):
        key = event.key
        if self.phase == "revision":
            self._rev_key(event)
            return
        kind = self.step["kind"]
        if (self.phase == "play" and kind in OWN_KINDS
                and key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_h)):
            self._own_key(event, kind)
            return
        super()._on_key(event)

    def _own_key(self, event, kind):
        key, st, step = event.key, self.st, self.step
        digit = self._digit(key)
        if kind == "bits":
            if digit is not None and 1 <= digit <= step["n"]:
                self._on_action(("bit", digit - 1))
        elif kind == "typed":
            if key == pygame.K_BACKSPACE:
                self._on_action(("back",))
            else:
                ch = self._char(event)
                if ch:
                    self._on_action(("key", ch))
        elif kind == "grid":
            n = len(st["vals"])
            if key in (pygame.K_UP, pygame.K_LEFT):
                st["sel"] = (st["sel"] - 1) % n
            elif key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB):
                st["sel"] = (st["sel"] + 1) % n
            elif key == pygame.K_BACKSPACE:
                self._on_action(("back",))
            else:
                ch = self._char(event)
                if ch:
                    self._on_action(("key", ch))
        elif kind == "pick":
            if digit is not None and 1 <= digit <= len(step["items"]):
                self._on_action(("pk", digit - 1))
        elif kind == "order":
            if key == pygame.K_BACKSPACE:
                self._on_action(("undo",))
            elif digit is not None and 1 <= digit <= len(step["items"]):
                self._on_action(("ord", digit - 1))

    def _on_action(self, action):
        name = action[0]
        if self.phase == "revision":
            if name == "finish":
                self._finish_revision()
            elif name == "top":
                self.rev_scroll = 0
            elif name == "end":
                self.rev_scroll = self._rev_max()
            return
        st, step = self.st, self.step
        if name == "bit":
            i = action[1]
            st["bits"][i] ^= 1
            st["seen"].add(self._bits_value(st["bits"]))
            if st["bits"][i]:
                st["used"].add(i)
        elif name == "key":
            self._type_char(action[1])
        elif name == "back":
            if step["kind"] == "typed":
                st["typed"] = st["typed"][:-1]
            elif step["kind"] == "grid":
                i = st["sel"]
                if st["vals"][i]:
                    st["vals"][i] = st["vals"][i][:-1]
                elif i > 0:
                    st["sel"] = i - 1
                st["bad"].discard(st["sel"])
        elif name == "clear":
            if step["kind"] == "typed":
                st["typed"] = ""
            elif step["kind"] == "grid":
                st["vals"][st["sel"]] = ""
                st["bad"].discard(st["sel"])
        elif name == "gcell":
            st["sel"] = action[1]
        elif name == "pk":
            st["chosen"] ^= {action[1]}
        elif name == "ord":
            if action[1] not in st["picked"]:
                st["picked"].append(action[1])
        elif name == "undo":
            if st["picked"]:
                st["picked"].pop()
        elif name == "clr":
            st["picked"] = []
        else:
            super()._on_action(action)

    def _type_char(self, ch):
        st, step = self.st, self.step
        if ch not in step["alphabet"]:
            return
        if step["kind"] == "typed":
            limit = len(step["answer"]) + (0 if step["exact"] else 2)
            if len(st["typed"]) < limit:
                st["typed"] += ch
        elif step["kind"] == "grid":
            cells = self._editable(step)
            i = st["sel"]
            expected = cells[i][2]
            limit = len(expected) + (1 if step["loose"] else 0)
            if len(st["vals"][i]) < limit:
                st["vals"][i] += ch
                st["bad"].discard(i)
                if (not step["loose"] and len(st["vals"][i]) == len(expected)
                        and i < len(cells) - 1):
                    st["sel"] = i + 1

    # ---------------- checking ----------------
    def _check(self):
        if self.phase != "play":
            return
        kind = self.step["kind"]
        if kind in OWN_KINDS:
            getattr(self, "_check_" + kind)()
        else:
            super()._check()

    def _check_bits(self):
        step, st = self.step, self.st
        bits = st["bits"]
        mode = step["mode"]
        if mode == "target":
            val = self._bits_value(bits)
            if val == step["target"]:
                self._right(step["ok"])
            else:
                self._wrong(f"Your switches add up to {val}, not {step['target']}. "
                            "Add the place values of the switches that are ON.")
        elif mode == "pattern":
            want = [int(c) for c in step["target"]]
            bad = [i + 1 for i, (a, b) in enumerate(zip(bits, want)) if a != b]
            if not bad:
                self._right(step["ok"])
            else:
                self._wrong("Not yet. Switch number " + ", ".join(str(i) for i in bad) +
                            " (counting from the left) is still wrong.")
        else:
            seen, used, n = len(st["seen"]), len(st["used"]), step["n"]
            if seen >= step["need"] and used == n:
                self._right(step["ok"])
            else:
                self._say(f"You made {seen} different number(s) and used {used} of {n} switches. "
                          f"Make {step['need']} different numbers and switch every place ON once.", False, 6.0)

    def _check_typed(self):
        step, st = self.step, self.st
        t = st["typed"].replace(" ", "")
        if not t:
            self._say("Type your answer first.", False)
            return
        if t in step["traps"]:
            self._wrong(step["traps"][t])
        elif same(t, step["answer"], loose=not step["exact"]):
            self._right(step["ok"])
        elif step["exact"] and step["alphabet"] == BIN_ALPHA and len(t) != len(step["answer"]):
            self._wrong(f"This answer needs exactly {len(step['answer'])} bits. You typed {len(t)}.")
        else:
            self._wrong("Not quite. Work through it again, or press H for a hint.")

    def _check_grid(self):
        step, st = self.step, self.st
        cells = self._editable(step)
        if any(not v for v in st["vals"]):
            self._say("Fill every yellow cell first.", False)
            return
        bad = {i for i, (_r, _c, e) in enumerate(cells)
               if not same(st["vals"][i], e, loose=step["loose"])}
        st["bad"] = bad
        if not bad:
            self._right(step["ok"])
        else:
            self._wrong(f"{len(bad)} cell(s) wrong. Look at the red boxes.")

    def _check_pick(self):
        step, st = self.step, self.st
        if not st["chosen"]:
            self._say("Tap at least one answer first.", False)
            return
        if st["chosen"] == step["correct"]:
            self._right(step["ok"])
        else:
            extra = len(st["chosen"] - step["correct"])
            missing = len(step["correct"] - st["chosen"])
            parts = []
            if extra:
                parts.append(f"{extra} tapped answer(s) are wrong")
            if missing:
                parts.append(f"{missing} right answer(s) are still missing")
            self._wrong("Not yet: " + " and ".join(parts) + ".")

    def _check_order(self):
        step, st = self.step, self.st
        if len(st["picked"]) < len(step["order"]):
            self._say("Tap all the items first.", False)
        elif st["picked"] == step["order"]:
            self._right(step["ok"])
        else:
            self._wrong("That order is not right. Press CLEAR and try again.")

    # ---------------- stage flow ----------------
    def _finish_stage(self):
        super()._finish_stage()

    def _next_stage(self):
        if self.phase != "done":
            return
        if self.stage_i >= len(self.stages) - 1:
            self._open_revision()
            return
        super()._next_stage()

    def notebook_lines(self, stage):
        return list(NOTEBOOK_LINES[stage["id"]])

    def _open_revision(self):
        self.phase = "revision"
        self.rev_scroll = 0
        self.rev_t0 = self.clock
        self.buttons = []
        if self.rev_surface is None:
            fonts = _revision_fonts()
            height = render_revision(VIEW.width, None, fonts)
            self.rev_surface = pygame.Surface((VIEW.width, height))
            self.rev_surface.fill(PANEL)
            render_revision(VIEW.width, self.rev_surface, fonts)
        if "n11_revision" not in self.saved_stages:
            self.saved_stages.add("n11_revision")
            if self.notebook is not None and hasattr(self.notebook, "add_basic_note"):
                self.notebook.add_basic_note("n11_revision", list(REVISION_NOTES))

    def _finish_revision(self):
        self.solved = True

    # ---------------- revision page ----------------
    def _rev_max(self):
        if self.rev_surface is None:
            return 0
        return max(0, self.rev_surface.get_height() - VIEW.height)

    def _scroll(self, dy):
        self.rev_scroll = max(0, min(self._rev_max(), self.rev_scroll + dy))

    def _rev_track(self):
        return pygame.Rect(VIEW.right + 8, VIEW.y, 10, VIEW.height)

    def _thumb(self):
        track = self._rev_track()
        total = self.rev_surface.get_height()
        h = max(36, int(track.height * VIEW.height / total))
        span = track.height - h
        mx = self._rev_max()
        y = track.y + (int(span * self.rev_scroll / mx) if mx else 0)
        return pygame.Rect(track.x, y, track.width, h)

    def _drag_to(self, mouse_y):
        track = self._rev_track()
        thumb = self._thumb()
        span = max(1, track.height - thumb.height)
        frac = (mouse_y - thumb.height / 2 - track.y) / span
        self.rev_scroll = max(0, min(self._rev_max(), int(frac * self._rev_max())))

    def _rev_key(self, event):
        key = event.key
        page = VIEW.height - 40
        if key == pygame.K_DOWN:
            self._scroll(44)
        elif key == pygame.K_UP:
            self._scroll(-44)
        elif key in (pygame.K_PAGEDOWN, pygame.K_SPACE):
            self._scroll(page)
        elif key == pygame.K_PAGEUP:
            self._scroll(-page)
        elif key == pygame.K_HOME:
            self.rev_scroll = 0
        elif key == pygame.K_END:
            self.rev_scroll = self._rev_max()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.clock - self.rev_t0 > 0.7:
                self._finish_revision()

    def _legend(self):
        if self.phase == "revision":
            return ("[MOUSE WHEEL / UP / DOWN / PAGE UP / PAGE DOWN] scroll    [HOME / END] top / bottom    "
                    "[ENTER] finish level    [N] notebook    [ESC] leave")
        return super()._legend()

    def _draw_revision(self, screen):
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, CYAN, FULL, 3, border_radius=10)
        screen.blit(self.f_title.render("EXAM REVISION", True, CYAN), (FULL.x + 20, FULL.y + 12))
        sub = self.f_small.render("Number systems and codes  -  all 10 stages on one page",
                                  True, WHITE)
        screen.blit(sub, (FULL.x + 300, FULL.y + 20))
        pygame.draw.rect(screen, (14, 24, 36), VIEW.inflate(8, 6), border_radius=6)
        screen.blit(self.rev_surface, VIEW.topleft, area=pygame.Rect(0, self.rev_scroll, VIEW.width, VIEW.height))

        track = self._rev_track()
        pygame.draw.rect(screen, (30, 42, 56), track, border_radius=5)
        pygame.draw.rect(screen, CYAN, self._thumb(), border_radius=5)

        mx = self._rev_max()
        pct = 100 if mx == 0 else int(100 * self.rev_scroll / mx)
        screen.blit(self.f_small.render(f"Read {pct}%", True, YELLOW), (FULL.x + 20, FULL.bottom - 38))
        self._button(screen, pygame.Rect(FULL.x + 120, FULL.bottom - 46, 70, 34), "TOP", ("top",), GREY)
        self._button(screen, pygame.Rect(FULL.x + 198, FULL.bottom - 46, 70, 34), "END", ("end",), GREY)
        self._button(screen, pygame.Rect(FULL.right - 240, FULL.bottom - 46, 220, 36),
                     "FINISH LEVEL  [ENTER]", ("finish",), GREEN)

    # ---------------- drawing: frame ----------------
    def draw(self, screen):
        if self.phase != "revision":
            return super().draw(screen)
        self.buttons = []
        screen.fill(BG)
        self._draw_header(screen)
        self._draw_revision(screen)
        self._draw_footer(screen)

    def _draw_header(self, screen):
        pygame.draw.rect(screen, PANEL, (0, 0, settings.SCREEN_WIDTH, 72))
        pygame.draw.line(screen, PANEL_EDGE, (0, 72), (settings.SCREEN_WIDTH, 72), 2)
        screen.blit(self.f_tiny.render(self.COURSE_TITLE, True, CYAN), (30, 10))
        if self.phase == "revision":
            text = "Exam revision  -  all 10 stages complete"
        else:
            text = (f"Stage {self.stage_i + 1}/{len(self.stages)}: "
                    f"{self.stage['title']}  -  {self.stage['sub']}")
        size = 40
        while size > 22:
            font = pygame.font.Font(None, size)
            if font.size(text)[0] <= 610:
                break
            size -= 2
        screen.blit(font.render(text, True, WHITE), (30, 34))
        for i in range(len(self.stages)):
            cx = 700 + i * 29
            if self.phase == "revision" or i < self.stage_i or (i == self.stage_i and self.phase == "done"):
                pygame.draw.circle(screen, GREEN, (cx, 22), 11)
            elif i == self.stage_i:
                pygame.draw.circle(screen, CYAN, (cx, 22), 11, 3)
            else:
                pygame.draw.circle(screen, GREY, (cx, 22), 11, 2)
            done = self.phase == "revision" or i < self.stage_i
            num = self.f_tiny.render(str(i + 1), True, BG if done else WHITE)
            screen.blit(num, num.get_rect(center=(cx, 22)))
        if self.phase == "play":
            total = len(self.stage["steps"])
            screen.blit(self.f_tiny.render(f"Step {self.step_i + 1} of {total}", True, GREY), (700, 46))

    # ---------------- drawing: shared widgets ----------------
    def _question(self, screen, text):
        font = self.f_body
        lines = wrap_text(font, text, WORK.width - 40)
        lh = 28
        if len(lines) > 3:
            font = self.f_small
            lines = wrap_text(font, text, WORK.width - 40)
            lh = 24
        y = WORK.y + 16
        for line in lines:
            screen.blit(font.render(line, True, WHITE), (WORK.x + 20, y))
            y += lh
        return y

    def _fit(self, text, width):
        for font in (self.f_body, self.f_small, self.f_tiny):
            if font.size(text)[0] <= width:
                return font
        return self.f_tiny

    def _keypad(self, screen, alphabet):
        keys = list(alphabet) + ["DEL", "CLR"]
        big = len(keys) <= 4
        w, h, gap = (110, 52, 14) if big else (50, 40, 5)
        n_rows = -(-len(keys) // 10)
        per = -(-len(keys) // n_rows)
        rows = [keys[i:i + per] for i in range(0, len(keys), per)]
        top = WORK.bottom - 14 - (len(rows) * h + (len(rows) - 1) * gap)
        for ri, row in enumerate(rows):
            x0 = WORK.centerx - (len(row) * w + (len(row) - 1) * gap) // 2
            for ci, k in enumerate(row):
                rect = pygame.Rect(x0 + ci * (w + gap), top + ri * (h + gap), w, h)
                action = ("back",) if k == "DEL" else ("clear",) if k == "CLR" else ("key", k)
                hover = rect.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(screen, (28, 56, 80) if hover else (22, 40, 58), rect, border_radius=7)
                pygame.draw.rect(screen, YELLOW if k in ("DEL", "CLR") else CYAN, rect, 2, border_radius=7)
                font = self.f_body if (big or k in ("DEL", "CLR")) and not (k in ("DEL", "CLR") and not big) \
                    else self.f_body
                img = (self.f_tiny if (k in ("DEL", "CLR") and not big) else font).render(k, True, WHITE)
                screen.blit(img, img.get_rect(center=rect.center))
                self.buttons.append((rect, action))
        return top

    # ---------------- drawing: bits ----------------
    def _draw_bits(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"])
        n, bits, mode = step["n"], st["bits"], step["mode"]
        if mode == "target":
            img = self.f_big.render(f"MAKE:  {step['target']}", True, YELLOW)
            screen.blit(img, img.get_rect(center=(WORK.centerx, y + 36)))
            y += 74
        elif mode == "explore":
            y += 14
        if step["given"]:
            lab = self.f_small.render("ORIGINAL NUMBER", True, CYAN)
            screen.blit(lab, lab.get_rect(center=(WORK.centerx, y + 14)))
            for i, ch in enumerate(step["given"]):
                cx = int(WORK.centerx + (i - (n - 1) / 2) * 70)
                rect = pygame.Rect(0, 0, 54, 46)
                rect.center = (cx, y + 56)
                pygame.draw.rect(screen, (30, 42, 56), rect, border_radius=8)
                pygame.draw.rect(screen, GREY, rect, 2, border_radius=8)
                img = self.f_big.render(ch, True, WHITE)
                screen.blit(img, img.get_rect(center=rect.center))
            y += 88
            lab2 = self.f_small.render("FLIP THE SWITCHES BELOW", True, GREEN)
            screen.blit(lab2, lab2.get_rect(center=(WORK.centerx, y + 4)))
            y += 14
        gap = min(104, (WORK.width - 40) // n)
        sw = min(84, gap - 12)
        cy_w, cy_s = y + 24, y + 86
        for i in range(n):
            cx = int(WORK.centerx + (i - (n - 1) / 2) * gap)
            if step["weights"]:
                wv = 2 ** (n - 1 - i)
                img = self.f_body.render(str(wv), True, YELLOW)
                screen.blit(img, img.get_rect(center=(cx, cy_w)))
            rect = pygame.Rect(0, 0, sw, 70)
            rect.center = (cx, cy_s)
            on = bits[i]
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (22, 84, 54) if on else ((38, 50, 66) if hover else (30, 40, 54)),
                             rect, border_radius=12)
            pygame.draw.rect(screen, GREEN if on else GREY, rect, 3, border_radius=12)
            img = self.f_big.render(str(on), True, WHITE)
            screen.blit(img, img.get_rect(center=rect.center))
            key = self.f_tiny.render(f"key {i + 1}", True, GREY)
            screen.blit(key, key.get_rect(center=(cx, cy_s + 50)))
            self.buttons.append((rect, ("bit", i)))
        base = cy_s + 84
        if mode in ("target", "explore"):
            on_w = [2 ** (n - 1 - i) for i in range(n) if bits[i]]
            expr = " + ".join(str(v) for v in on_w) if on_w else "0"
            val = self._bits_value(bits)
            img = self.f_big.render(f"{expr} = {val}" if len(on_w) > 1 else f"= {val}", True, WHITE)
            if img.get_width() > WORK.width - 40:
                img = self.f_body.render(f"{expr} = {val}", True, WHITE)
            screen.blit(img, img.get_rect(center=(WORK.centerx, base + 10)))
        if mode == "explore":
            seen, used = len(st["seen"]), len(st["used"])
            msg = self.f_body.render(f"Different numbers made: {seen} / {step['need']}     "
                                     f"Switches used: {used} / {n}", True, CYAN)
            screen.blit(msg, msg.get_rect(center=(WORK.centerx, base + 62)))
        elif mode == "pattern":
            now = "".join(str(b) for b in bits)
            img = self.f_big.render(now, True, YELLOW)
            screen.blit(img, img.get_rect(center=(WORK.centerx, base + 10)))
            lab = self.f_small.render("YOUR 1'S COMPLEMENT", True, CYAN)
            screen.blit(lab, lab.get_rect(center=(WORK.centerx, base + 52)))

    # ---------------- drawing: typed ----------------
    def _draw_typed(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"]) + 6
        for label, text in step["show"] or []:
            card = pygame.Rect(WORK.centerx - 270, y, 540, 74)
            pygame.draw.rect(screen, (18, 34, 50), card, border_radius=8)
            pygame.draw.rect(screen, PANEL_EDGE, card, 2, border_radius=8)
            screen.blit(self.f_tiny.render(label, True, CYAN), (card.x + 12, card.y + 6))
            font = self.f_big if self.f_big.size(text)[0] <= 510 else self.f_body
            img = font.render(text, True, WHITE)
            screen.blit(img, img.get_rect(center=(card.centerx, card.y + 46)))
            y += 84
        y += 8
        screen.blit(self.f_tiny.render(step["label"], True, CYAN), (WORK.centerx - 270, y))
        box = pygame.Rect(WORK.centerx - 270, y + 22, 540, 64)
        pygame.draw.rect(screen, (14, 26, 40), box, border_radius=8)
        pygame.draw.rect(screen, YELLOW, box, 3, border_radius=8)
        typed = st["typed"]
        if step["exact"] and len(step["answer"]) <= 12 and step["alphabet"] == BIN_ALPHA:
            shown = typed + "_" * (len(step["answer"]) - len(typed))
            shown = group(shown) if len(shown) >= 8 else shown
            img = self.f_big.render(shown, True, YELLOW)
        else:
            cursor = "|" if int(self.clock * 2) % 2 == 0 else " "
            img = self.f_big.render((typed + cursor) if typed else cursor, True, YELLOW)
        if img.get_width() > box.width - 20:
            img = pygame.transform.smoothscale(img, (box.width - 20, int(img.get_height() * (box.width - 20) / img.get_width())))
        screen.blit(img, img.get_rect(center=box.center))
        if step["exact"] and step["alphabet"] == BIN_ALPHA:
            note = self.f_tiny.render(f"{len(step['answer'])} bits needed  -  typed {len(typed)}", True, GREY)
            screen.blit(note, (box.x + 4, box.bottom + 6))
        self._keypad(screen, step["alphabet"])

    # ---------------- drawing: grid ----------------
    def _draw_grid(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"]) + 14
        headers, rows = step["headers"], step["rows"]
        font = self.f_body
        ncols = len(headers)

        def text_of(cell):
            return cell[1] if isinstance(cell, tuple) else cell

        def widths_for(f):
            if step["colw"]:
                return list(step["colw"])
            out = []
            for c in range(ncols):
                texts = [headers[c]] + [text_of(r[c]) for r in rows]
                out.append(max(66, max(f.size(t)[0] for t in texts) + 30))
            return out

        widths = widths_for(font)
        if sum(widths) > WORK.width - 30:
            font = self.f_small
            widths = widths_for(font)
        total = sum(widths)
        x0 = WORK.centerx - total // 2
        rh = 46 if len(rows) <= 4 else 40
        cells = self._editable(step)
        index = {(r, c): i for i, (r, c, _e) in enumerate(cells)}

        for c, h in enumerate(headers):
            rect = pygame.Rect(x0 + sum(widths[:c]), y, widths[c] - 4, rh - 4)
            pygame.draw.rect(screen, (30, 60, 84), rect, border_radius=5)
            img = font.render(h, True, YELLOW)
            screen.blit(img, img.get_rect(center=rect.center))
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                rect = pygame.Rect(x0 + sum(widths[:c]), y + (r + 1) * rh, widths[c] - 4, rh - 4)
                if isinstance(cell, tuple):
                    i = index[(r, c)]
                    sel = st["sel"] == i
                    bad = i in st["bad"]
                    hover = rect.collidepoint(pygame.mouse.get_pos())
                    pygame.draw.rect(screen, (46, 44, 18) if sel else ((30, 44, 60) if hover else (20, 32, 46)),
                                     rect, border_radius=5)
                    edge = RED if bad else (YELLOW if sel else (150, 150, 90))
                    pygame.draw.rect(screen, edge, rect, 3 if (sel or bad) else 2, border_radius=5)
                    val = st["vals"][i]
                    if sel and not val and int(self.clock * 2) % 2 == 0:
                        val = "|"
                    img = font.render(val, True, WHITE)
                    screen.blit(img, img.get_rect(center=rect.center))
                    self.buttons.append((rect, ("gcell", i)))
                else:
                    pygame.draw.rect(screen, (22, 38, 54), rect, border_radius=5)
                    col = CYAN if c == 0 and cell else WHITE
                    img = font.render(cell, True, col)
                    screen.blit(img, img.get_rect(center=rect.center))
        bottom = y + (len(rows) + 1) * rh
        if step["note"]:
            for i, line in enumerate(wrap_text(self.f_small, step["note"], WORK.width - 50)[:2]):
                screen.blit(self.f_small.render(line, True, GREY), (WORK.x + 24, bottom + 6 + i * 22))
        self._keypad(screen, step["alphabet"])

    # ---------------- drawing: pick ----------------
    def _draw_pick(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"]) + 14
        items = step["items"]
        if step["layout"] == "list":
            h, gap, w = 44, 8, WORK.width - 60
            for i, text in enumerate(items):
                rect = pygame.Rect(WORK.x + 30, y + i * (h + gap), w, h)
                self._pick_box(screen, rect, f"{i + 1}  {text}", i in st["chosen"], i)
        else:
            cols, w, h, gap = 3, 170, 56, 14
            rows = -(-len(items) // cols)
            for i, text in enumerate(items):
                r, c = divmod(i, cols)
                in_row = min(cols, len(items) - r * cols)
                x0 = WORK.centerx - (in_row * w + (in_row - 1) * gap) // 2
                rect = pygame.Rect(x0 + c * (w + gap), y + 10 + r * (h + gap), w, h)
                self._pick_box(screen, rect, text, i in st["chosen"], i)
            y += 10 + rows * (h + gap)
            msg = self.f_small.render(f"Tapped so far: {len(st['chosen'])}", True, GREY)
            screen.blit(msg, msg.get_rect(center=(WORK.centerx, y + 12)))

    def _pick_box(self, screen, rect, text, on, i):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (24, 90, 55) if on else ((30, 48, 68) if hover else (22, 36, 52)),
                         rect, border_radius=8)
        pygame.draw.rect(screen, GREEN if on else GREY, rect, 3 if on else 2, border_radius=8)
        font = self._fit(text, rect.width - 16)
        img = font.render(text, True, WHITE)
        screen.blit(img, img.get_rect(center=rect.center))
        self.buttons.append((rect, ("pk", i)))

    # ---------------- drawing: order ----------------
    def _draw_order(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"]) + 18
        items, picked = step["items"], st["picked"]
        n = len(items)
        w, h, gap = 126, 50, 14
        x0 = WORK.centerx - (n * w + (n - 1) * gap) // 2
        screen.blit(self.f_tiny.render("TAP IN THE RIGHT ORDER", True, CYAN), (x0, y - 4))
        for i, text in enumerate(items):
            rect = pygame.Rect(x0 + i * (w + gap), y + 20, w, h)
            used = i in picked
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (22, 28, 36) if used else ((30, 48, 68) if hover else (22, 38, 56)),
                             rect, border_radius=8)
            pygame.draw.rect(screen, (70, 78, 90) if used else CYAN, rect, 2, border_radius=8)
            img = self.f_body.render(text, True, GREY if used else WHITE)
            screen.blit(img, img.get_rect(center=rect.center))
            self.buttons.append((rect, ("ord", i)))
        y += 20 + h + 30
        screen.blit(self.f_tiny.render("YOUR ORDER  (left to right)", True, CYAN), (x0, y))
        for k in range(n):
            rect = pygame.Rect(x0 + k * (w + gap), y + 22, w, h)
            pygame.draw.rect(screen, (14, 26, 40), rect, border_radius=8)
            filled = k < len(picked)
            pygame.draw.rect(screen, YELLOW if filled else GREY, rect, 3 if filled else 2, border_radius=8)
            if filled:
                img = self.f_body.render(items[picked[k]], True, YELLOW)
                screen.blit(img, img.get_rect(center=rect.center))
        y += 22 + h + 20
        if picked:
            bits_txt = " ".join(items[i].split(": ")[-1] for i in picked)
            img = self.f_big.render(bits_txt, True, WHITE)
            screen.blit(img, img.get_rect(center=(WORK.centerx, y + 18)))
            y += 52
        self._button(screen, pygame.Rect(WORK.centerx - 130, y + 6, 120, 38), "UNDO", ("undo",), YELLOW)
        self._button(screen, pygame.Rect(WORK.centerx + 10, y + 6, 120, 38), "CLEAR", ("clr",), YELLOW)

    # ---------------- drawing: choice ----------------
    def _option_rects(self, opts, int_opts):
        n = len(opts)
        height, gap = 40, 8
        top = WORK.bottom - 14 - (n * height + (n - 1) * gap)
        return [pygame.Rect(WORK.x + 30, top + i * (height + gap), WORK.width - 60, height)
                for i in range(n)]

    def _draw_choice(self, screen):
        step, st = self.step, self.st
        y = self._question(screen, step["q"])
        opts = step["options"]
        rects = self._option_rects(opts, False)
        top = min(r.y for r in rects)
        self._draw_extra_visual(screen, step, y, top - 8)
        for i, ((label, _val), rect) in enumerate(zip(opts, rects)):
            selected = st["sel"] == i
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (30, 70, 56) if selected else ((24, 46, 66) if hover else (20, 34, 50)),
                             rect, border_radius=8)
            pygame.draw.rect(screen, GREEN if selected else GREY, rect, 3, border_radius=8)
            text = f"{i + 1}   {label}"
            font = self._fit(text, rect.width - 20)
            img = font.render(text, True, WHITE)
            screen.blit(img, img.get_rect(center=rect.center))
            self.buttons.append((rect, ("opt", i)))

    def _draw_extra_visual(self, screen, step, top, bottom):
        lines = step.get("show") or []
        if not lines:
            return
        mid = (top + bottom) // 2
        h = 50
        y = mid - (len(lines) * h) // 2
        for line in lines:
            font = self.f_big if self.f_big.size(line)[0] <= WORK.width - 60 else self.f_body
            img = font.render(line, True, YELLOW)
            screen.blit(img, img.get_rect(center=(WORK.centerx, y + h // 2)))
            y += h

    # ---------------- drawing: stage-complete card ----------------
    def _draw_done(self, screen):
        stage = self.stage
        pygame.draw.rect(screen, PANEL, FULL, border_radius=10)
        pygame.draw.rect(screen, GREEN, FULL, 3, border_radius=10)
        n = self.stage_i + 1
        screen.blit(self.f_big.render(f"STAGE {n} COMPLETE", True, GREEN), (FULL.x + 24, FULL.y + 14))
        sub = self.f_body.render(f"{stage['title']}  -  {stage['sub']}", True, WHITE)
        screen.blit(sub, (FULL.x + 24, FULL.y + 62))

        _kind, headers, rows, colw = stage["example"]
        self._done_table(screen, FULL.x + 24, FULL.y + 104, headers, rows, colw, rowh=34)

        rx = FULL.x + 410
        rw = FULL.right - rx - 24
        y = FULL.y + 104
        for label, text in stage["items"]:
            screen.blit(self.f_small.render(label, True, CYAN), (rx, y))
            y += 24
            for line in wrap_text(self.f_small, text, rw):
                screen.blit(self.f_small.render(line, True, WHITE), (rx, y))
                y += 23
            y += 10

        note = self.f_small.render("Saved to NOTEBOOK [N]  >  TEST THE LOGIC  >  MY BASIC NOTES", True, YELLOW)
        screen.blit(note, (FULL.x + 24, FULL.bottom - 62))
        last = self.stage_i >= len(self.stages) - 1
        rect = pygame.Rect(FULL.right - 270, FULL.bottom - 52, 250, 38)
        self._button(screen, rect, "EXAM REVISION  [ENTER]" if last else "NEXT STAGE  [ENTER]",
                     ("next",), GREEN)

    def _done_table(self, screen, x, y, headers, rows, colw, rowh=36):
        widths = list(colw) if isinstance(colw, (list, tuple)) else [colw] * len(headers)
        xs = [x + sum(widths[:j]) for j in range(len(widths))]
        for j, h in enumerate(headers):
            rect = pygame.Rect(xs[j], y, widths[j] - 4, rowh - 2)
            pygame.draw.rect(screen, (30, 60, 84), rect, border_radius=4)
            img = self.f_small.render(h, True, YELLOW)
            screen.blit(img, img.get_rect(center=rect.center))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                rect = pygame.Rect(xs[j], y + (i + 1) * rowh, widths[j] - 4, rowh - 2)
                pygame.draw.rect(screen, (22, 38, 54), rect, border_radius=4)
                font = self.f_small if self.f_small.size(v)[0] <= rect.width - 6 else self.f_tiny
                img = font.render(v, True, CYAN if j == 0 and len(headers) > 2 else WHITE)
                screen.blit(img, img.get_rect(center=rect.center))