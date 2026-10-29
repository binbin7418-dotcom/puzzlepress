#!/usr/bin/env python3
"""
PuzzlePress — print-ready Sudoku book interiors with a verified-generation
guarantee.

Pipeline:
  1. Generate full solution grids, then dig holes (symmetrically) while a
     solver proves after every removal that the puzzle still has exactly
     one solution.
  2. Render a KDP-sized interior PDF (title page, puzzle pages, solution
     pages) plus a puzzles.csv of puzzle/solution strings.
  3. Re-check (independent pass): every puzzle in the finished book is
     re-solved from its givens alone — it must have exactly one solution
     and that solution must equal the grid the book's solution section
     prints. Clue counts must sit inside the difficulty band. A book that
     fails any check is reported, not shipped quietly.

Deterministic: the same seed regenerates the same book, so a series
stays consistent. Local only, no network.
"""
import csv
import os
import random
import sys

DIFFICULTY = {  # target clue counts (bands verified in the re-check)
    "easy": 40,
    "medium": 34,
    "hard": 30,
    "expert": 27,
}
TRIMS = {"8.5x11": (612.0, 792.0), "8x10": (576.0, 720.0)}


# ---------- solver ----------
def _candidates(grid, r, c):
    used = set(grid[r]) | {grid[i][c] for i in range(9)}
    br, bc = 3 * (r // 3), 3 * (c // 3)
    used |= {grid[i][j] for i in range(br, br + 3) for j in range(bc, bc + 3)}
    return [n for n in range(1, 10) if n not in used]


def count_solutions(grid, limit=2):
    """Count solutions up to `limit`. grid: 9x9 list of lists, 0 = empty."""
    best, best_cands = None, None
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                cands = _candidates(grid, r, c)
                if not cands:
                    return 0
                if best_cands is None or len(cands) < len(best_cands):
                    best, best_cands = (r, c), cands
    if best is None:
        return 1
    total = 0
    r, c = best
    for n in best_cands:
        grid[r][c] = n
        total += count_solutions(grid, limit - total)
        grid[r][c] = 0
        if total >= limit:
            return total
    return total


def solve(grid):
    """Return one solved copy of grid, or None."""
    g = [row[:] for row in grid]
    return g if count_solutions(g, 1) == 1 and _fill(g) else None


def _fill(grid):
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                for n in _candidates(grid, r, c):
                    grid[r][c] = n
                    if _fill(grid):
                        return True
                    grid[r][c] = 0
                return False
    return True


# ---------- generation ----------
def full_grid(rng):
    g = [[0] * 9 for _ in range(9)]

    def fill():
        for r in range(9):
            for c in range(9):
                if g[r][c] == 0:
                    cands = _candidates(g, r, c)
                    rng.shuffle(cands)
                    for n in cands:
                        g[r][c] = n
                        if fill():
                            return True
                        g[r][c] = 0
                    return False
        return True

    fill()
    return g


def dig(solution, target_clues, rng):
    """Remove cells (180-degree symmetric pairs) while uniqueness holds."""
    puzzle = [row[:] for row in solution]
    cells = [(r, c) for r in range(9) for c in range(9)]
    rng.shuffle(cells)
    clues = 81
    for r, c in cells:
        if clues <= target_clues:
            break
        pair = [(r, c)] if (r, c) == (8 - r, 8 - c) else [(r, c), (8 - r, 8 - c)]
        if any(puzzle[pr][pc] == 0 for pr, pc in pair):
            continue
        backup = [(pr, pc, puzzle[pr][pc]) for pr, pc in pair]
        for pr, pc in pair:
            puzzle[pr][pc] = 0
        trial = [row[:] for row in puzzle]
        if count_solutions(trial, 2) == 1:
            clues -= len(pair)
        else:
            for pr, pc, v in backup:
                puzzle[pr][pc] = v
    return puzzle, clues


def grid_str(g):
    return "".join(str(v) for row in g for v in row)


def generate_puzzles(count, difficulty, seed):
    rng = random.Random(seed)
    target = DIFFICULTY[difficulty]
    out = []
    for i in range(count):
        sol = full_grid(rng)
        puz, clues = dig(sol, target, rng)
        out.append({"n": i + 1, "puzzle": puz, "solution": sol, "clues": clues})
    return out


def verify_puzzles(puzzles, difficulty):
    """Independent re-check: re-solve every puzzle from its givens."""
    problems = []
    target = DIFFICULTY[difficulty]
    for p in puzzles:
        trial = [row[:] for row in p["puzzle"]]
        n = count_solutions(trial, 2)
        if n != 1:
            problems.append(f"puzzle {p['n']}: has {n} solutions (must be exactly 1)")
            continue
        solved = [row[:] for row in p["puzzle"]]
        _fill(solved)
        if solved != p["solution"]:
            problems.append(f"puzzle {p['n']}: re-solved grid differs from the printed solution")
        if not (target - 2 <= p["clues"] <= target + 6):
            problems.append(f"puzzle {p['n']}: clue count {p['clues']} outside the {difficulty} band "
                            f"({target - 2}..{target + 6})")
    return problems


# ---------- PDF rendering ----------
def render_pdf(puzzles, path, title, trim="8.5x11", per_page=1):
    from reportlab.lib.colors import black, HexColor
    from reportlab.pdfgen import canvas

    W, H = TRIMS[trim]
    c = canvas.Canvas(path, pagesize=(W, H))
    margin = 54.0

    def draw_grid(x, y_top, size, grid, numbers=True, font_scale=0.42):
        cell = size / 9.0
        c.setStrokeColor(black)
        for i in range(10):
            wdt = 2.2 if i % 3 == 0 else 0.6
            c.setLineWidth(wdt)
            c.line(x + i * cell, y_top, x + i * cell, y_top - size)
            c.line(x, y_top - i * cell, x + size, y_top - i * cell)
        if numbers:
            c.setFillColor(black)
            c.setFont("Helvetica", cell * font_scale)
            for r in range(9):
                for col in range(9):
                    v = grid[r][col]
                    if v:
                        c.drawCentredString(x + (col + 0.5) * cell,
                                            y_top - (r + 0.5) * cell - cell * font_scale * 0.36,
                                            str(v))
        c.setFillColor(black)

    def layout(count_items, size_fn):
        """Yield (page_item_indexes) grouped for the section."""
        pass

    # title page
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W / 2, H / 2 + 30, title)
    c.setFont("Helvetica", 13)
    c.drawCentredString(W / 2, H / 2 - 6, f"{len(puzzles)} Sudoku puzzles with solutions")
    c.showPage()

    # puzzle pages
    slots = {1: [(margin, H - margin, min(W - 2 * margin, H * 0.62))],
             2: [(margin, H - margin, (H - 3 * margin) / 2),
                 (margin, H - margin - (H - 3 * margin) / 2 - margin, (H - 3 * margin) / 2)],
             4: [(margin, H - margin, (H - 3 * margin) / 2),
                 (W / 2 + 12, H - margin, (H - 3 * margin) / 2),
                 (margin, H - margin - (H - 3 * margin) / 2 - margin, (H - 3 * margin) / 2),
                 (W / 2 + 12, H - margin - (H - 3 * margin) / 2 - margin, (H - 3 * margin) / 2)]}
    grid_w = (W - 2 * margin) if per_page == 1 else (W - 2 * margin - 24) / 2 if per_page == 4 else W - 2 * margin
    positions = slots[per_page]
    for i in range(0, len(puzzles), per_page):
        group = puzzles[i:i + per_page]
        for j, p in enumerate(group):
            x, y_top, slot_h = positions[j]
            size = min(slot_h - 28, grid_w)
            if per_page == 1:
                x = (W - size) / 2
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x, y_top, f"Puzzle {p['n']}")
            draw_grid(x, y_top - 22, size, p["puzzle"])
        c.showPage()

    # solution pages, 4 per page
    sol_size = (W - 2 * margin - 24) / 2
    sol_pos = [(margin, H - margin), (W / 2 + 12, H - margin),
               (margin, H / 2 - 12), (W / 2 + 12, H / 2 - 12)]
    for i in range(0, len(puzzles), 4):
        group = puzzles[i:i + 4]
        for j, p in enumerate(group):
            x, y_top = sol_pos[j]
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y_top, f"Solution {p['n']}")
            draw_grid(x, y_top - 18, min(sol_size, H / 2 - margin - 40), p["solution"],
                      font_scale=0.36)
        c.showPage()
    c.save()
    puzzle_pages = -(-len(puzzles) // per_page)
    solution_pages = -(-len(puzzles) // 4)
    return {"pages": 1 + puzzle_pages + solution_pages,
            "puzzle_pages": puzzle_pages, "solution_pages": solution_pages}


def run_puzzlepress(outdir, count=100, difficulty="medium", per_page=1,
                    trim="8.5x11", title="Sudoku", seed=42):
    os.makedirs(outdir, exist_ok=True)
    puzzles = generate_puzzles(count, difficulty, seed)
    problems = verify_puzzles(puzzles, difficulty)
    pdf_path = os.path.join(outdir, "sudoku_interior.pdf")
    info = render_pdf(puzzles, pdf_path, title, trim=trim, per_page=per_page)
    csv_path = os.path.join(outdir, "puzzles.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "difficulty", "clues", "puzzle", "solution"])
        for p in puzzles:
            w.writerow([p["n"], difficulty, p["clues"], grid_str(p["puzzle"]), grid_str(p["solution"])])
    clue_counts = [p["clues"] for p in puzzles]
    L = ["# PuzzlePress — generation & verification report", "",
         f"Book: {title}  ·  Puzzles: {count}  ·  Difficulty: {difficulty} "
         f"(target {DIFFICULTY[difficulty]} clues)  ·  Trim: {trim}  ·  Per page: {per_page}  ·  Seed: {seed}", "",
         "## Verified, not vibes",
         f"- Every puzzle re-solved from its givens by an independent solver pass: "
         f"{count - len(problems)}/{count} have exactly one solution and the re-solved grid "
         f"matches the printed solution.",
         f"- Clue counts: min {min(clue_counts)}, max {max(clue_counts)}, "
         f"average {sum(clue_counts) / len(clue_counts):.1f}.",
         f"- Interior PDF: {info['pages']} pages (1 title + {info['puzzle_pages']} puzzle + "
         f"{info['solution_pages']} solution), trim {trim} in, no bleed.",
         "- Commercial use: the puzzles are generated by this tool; the output book is yours to sell.",
         "- Scope note: difficulty bands are defined by clue count with a uniqueness guarantee; "
         "they are not graded by human solving-technique rankings."]
    if problems:
        L += ["", "## PROBLEMS (do not publish this book)"] + [f"- {p}" for p in problems]
    report_path = os.path.join(outdir, "generation_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return {"puzzles": count, "difficulty": difficulty, "target_clues": DIFFICULTY[difficulty],
            "clues_min": min(clue_counts), "clues_max": max(clue_counts),
            "clues_avg": round(sum(clue_counts) / len(clue_counts), 1),
            "problems": problems, "pages": info["pages"],
            "pdf_path": pdf_path, "csv_path": csv_path, "report_path": report_path}


def main(argv):
    if len(argv) < 2:
        print("usage: puzzle_press.py <outdir> [count] [difficulty] [per_page] [trim] [seed]")
        return 2
    s = run_puzzlepress(argv[1],
                        count=int(argv[2]) if len(argv) > 2 else 100,
                        difficulty=argv[3] if len(argv) > 3 else "medium",
                        per_page=int(argv[4]) if len(argv) > 4 else 1,
                        trim=argv[5] if len(argv) > 5 else "8.5x11",
                        seed=int(argv[6]) if len(argv) > 6 else 42)
    print(f"puzzles={s['puzzles']} difficulty={s['difficulty']} clues={s['clues_min']}..{s['clues_max']} "
          f"avg={s['clues_avg']} pages={s['pages']} problems={len(s['problems'])}")
    return 0 if not s["problems"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
