#!/usr/bin/env python3
"""PuzzlePress desktop shell (tkinter).
Set count/difficulty/layout -> generate a verified Sudoku interior PDF."""
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from puzzle_press import run_puzzlepress


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PuzzlePress — Verified Sudoku Book Interiors")
        self.geometry("680x560")
        self.title_var = tk.StringVar(value="Sudoku")
        self.count_var = tk.StringVar(value="100")
        self.diff_var = tk.StringVar(value="medium")
        self.perpage_var = tk.StringVar(value="1")
        self.trim_var = tk.StringVar(value="8.5x11")
        self.seed_var = tk.StringVar(value="42")

        def field(label, var, values=None):
            tk.Label(self, text=label).pack(anchor="w", padx=12, pady=(8, 2))
            if values:
                ttk.Combobox(self, textvariable=var, values=values, state="readonly").pack(fill="x", padx=12)
            else:
                tk.Entry(self, textvariable=var).pack(fill="x", padx=12)

        field("Book title:", self.title_var)
        field("Number of puzzles:", self.count_var)
        field("Difficulty:", self.diff_var, ["easy", "medium", "hard", "expert"])
        field("Puzzles per page:", self.perpage_var, ["1", "2", "4"])
        field("Trim size (inches):", self.trim_var, ["8.5x11", "8x10"])
        field("Seed (same seed = same book):", self.seed_var)
        self.btn = tk.Button(self, text="Generate & Verify Book", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("PuzzlePress generates a print-ready Sudoku interior and then re-solves every\n"
                   "puzzle from its givens to prove it has exactly one solution — the solution\n"
                   "printed in the back of your book. Everything runs locally.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def run(self):
        try:
            count = int(self.count_var.get())
            per_page = int(self.perpage_var.get())
            seed = int(self.seed_var.get())
            if count < 1 or count > 2000:
                raise ValueError("puzzle count must be 1..2000")
        except ValueError as e:
            messagebox.showerror("PuzzlePress", f"Check the numeric fields: {e}")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, args=(count, per_page, seed), daemon=True).start()

    def _work(self, count, per_page, seed):
        try:
            outdir = os.path.join(os.path.expanduser("~"), "PuzzlePress_output")
            s = run_puzzlepress(outdir, count=count, difficulty=self.diff_var.get(),
                                per_page=per_page, trim=self.trim_var.get(),
                                title=self.title_var.get().strip() or "Sudoku", seed=seed)
            self.write(f"\nDone. {s['puzzles']} {s['difficulty']} puzzles, clues "
                       f"{s['clues_min']}..{s['clues_max']} (avg {s['clues_avg']}), "
                       f"{s['pages']} pages, verification problems: {len(s['problems'])}.\n"
                       f"Interior PDF: {s['pdf_path']}\nPuzzle data: {s['csv_path']}\nReport: {s['report_path']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
