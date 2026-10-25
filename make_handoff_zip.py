"""Builds logic_detective_handoff.zip: your project WITHOUT the junk.

Run this from inside your LOGIC_DETECTIVE folder:
    python make_handoff_zip.py

Then attach logic_detective_handoff.zip to the new chat, together with the prompt.
"""
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_NAME = "logic_detective_handoff.zip"

SKIP_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", ".idea", ".vscode",
    "Screenshots", "screenshots", "basic_shots", "kmap_shots",
    "de zip", "basic_mode_update_v2", "basic_mode_update_v3",
}
SKIP_SUFFIX = (".zip", ".pyc", ".pyo")


def main():
    files = []
    for folder, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            if name.endswith(SKIP_SUFFIX) or name == OUT_NAME:
                continue
            files.append(os.path.join(folder, name))

    out_path = os.path.join(ROOT, OUT_NAME)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(files):
            zf.write(path, os.path.relpath(path, ROOT))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Added {len(files)} files -> {OUT_NAME} ({size_kb:.0f} KB)\n")
    for path in sorted(files):
        print("  ", os.path.relpath(path, ROOT))

    needed = ["main.py", "notebook.py", "progress.py", os.path.join("puzzles", "base_puzzle.py"),
              os.path.join("puzzles", "basic_gates.py"), os.path.join("puzzles", "basic_kmap.py")]
    missing = [n for n in needed if not os.path.exists(os.path.join(ROOT, n))]
    if missing:
        print("\nWARNING - these important files were not found:", ", ".join(missing))
    if size_kb > 20000:
        print("\nWARNING - the zip is over 20 MB; check for large files that should be skipped.")


if __name__ == "__main__":
    main()
