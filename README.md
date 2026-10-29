# PuzzlePress

Generate print-ready Sudoku book interiors for KDP — where every puzzle
is **proven** to have exactly one solution before the book is rendered.

## What it does

- Generates full Sudoku books: title page, puzzle pages (1, 2 or 4 per
  page), and a solutions section, at 8.5×11in or 8×10in trim, no bleed.
- Four difficulty bands by clue count (Easy 40, Medium 34, Hard 30,
  Expert 27 target clues), with holes dug symmetrically.
- Uniqueness is enforced during generation (a solver re-checks the
  puzzle after every removal) and then verified again in an independent
  pass: every puzzle is re-solved from its givens and the result must
  equal the solution printed in the book.
- Deterministic seeds: the same seed regenerates the identical book.
- Also exports `puzzles.csv` (puzzle + solution strings) and a
  `generation_report.md` with clue-count statistics and the verdict.
- Commercial use: the books you generate are yours to sell.

100% local. No account, no subscription, no upload.

## Run from source

```bash
python puzzle_press.py out/ 100 medium 1 8.5x11 42
python gui.py
```

## Acceptance

`test/acceptance_test.py` generates books at three difficulties and
asserts unique solutions, solution equality, clue bands, exact PDF page
count and trim size (read back with PyMuPDF), and seed determinism.
A full 100-puzzle Medium book (seed 42) generates and verifies with
0 problems. See `test/ACCEPTANCE.md`.
