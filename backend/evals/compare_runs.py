"""Compare two eval runs and print a before/after scorecard.

Usage:
  python evals/compare_runs.py                                  # before vs after (defaults)
  python evals/compare_runs.py results_before.json results_after.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIMS = ["grounded", "relevant", "tone", "instruction_following"]


def load(path):
    p = Path(path)
    if not p.is_absolute():
        p = HERE / p
    return json.loads(p.read_text())


def avg(rows, dim):
    vals = [r["scores"].get(dim) for r in rows if isinstance(r.get("scores", {}).get(dim), (int, float))]
    return sum(vals) / len(vals) if vals else None


def em_dash_rate(rows):
    return sum(r["checks"]["has_em_dash"] for r in rows) / len(rows) if rows else 0


def main():
    before_path = sys.argv[1] if len(sys.argv) > 1 else "results_before.json"
    after_path = sys.argv[2] if len(sys.argv) > 2 else "results_after.json"
    before, after = load(before_path), load(after_path)

    print("=" * 56)
    print(f"{'dimension':<24}{'before':>9}{'after':>9}{'delta':>10}")
    print("=" * 56)
    for dim in DIMS:
        b, a = avg(before, dim), avg(after, dim)
        if b is None or a is None:
            continue
        delta = a - b
        arrow = "up" if delta > 0 else ("down" if delta < 0 else "same")
        print(f"{dim:<24}{b:>9.2f}{a:>9.2f}{delta:>+8.2f} {arrow}")
    print("-" * 56)
    print(f"{'em-dash violations':<24}{em_dash_rate(before):>8.0%}{em_dash_rate(after):>9.0%}")
    print("=" * 56)


if __name__ == "__main__":
    main()
