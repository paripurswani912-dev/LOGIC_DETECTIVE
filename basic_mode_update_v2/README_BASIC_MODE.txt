BASIC MODE UPDATE v2  (drop these files into your LOGIC_DETECTIVE folder, same paths)

  puzzles/basic_gates.py        Basic Level 1: logic gates from zero (8 stages)  [updated, reusable engine]
  puzzles/basic_kmap.py   NEW   Basic Karnaugh Maps (8 stages: neighbours ... SOP, POS, don't cares, 7-segment boss)
  main.py                       BASIC / INTERMEDIATE choice; BASIC terminals open the Basic puzzles
  notebook.py                   per-mode clue text, MY BASIC NOTES autofill (gates first, then K-maps)

  tests/test_basic_gates.py, test_basic_flow_in_main.py        Level 1 tests
  tests/test_basic_kmap.py, test_basic_kmap_in_main.py         K-map tests (engine, content, full playthrough)
  tests/preview_basic.py        play a Basic course directly, no unlocking needed

Play the K-map course right now:   python tests/preview_basic.py kmap
Play the gates course:             python tests/preview_basic.py gates
Play the whole game:               python main.py   (choose BASIC on the title screen)
Run every test:                    python tests/test_basic_kmap.py   (etc.)

BASIC path terminals:   Logic Lock terminal   -> Basic gates course
                        Logic Architect terminal -> Basic Karnaugh course
INTERMEDIATE path is unchanged.
