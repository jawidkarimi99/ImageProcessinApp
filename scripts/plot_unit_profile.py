# scripts/plot_unit_profile.py
import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
J = ROOT / "perf_results.json"
OUT = ROOT / "unit_profile.png"

def main():
    if not J.exists():
        raise SystemExit("perf_results.json not found. Run:\n"
                         "  pytest tests/perf -m perf --benchmark-json perf_results.json")
    data = json.loads(J.read_text())
    rows = []
    for b in data.get("benchmarks", []):
        name = b.get("name", "")
        # only keep our unit benchmarks (filter by your test name prefix if needed)
        stats = b.get("stats", {})
        mean_ms = (stats.get("mean") or 0) * 1000.0
        rows.append((mean_ms, name))
    rows.sort()
    means, names = zip(*rows) if rows else ([], [])
    plt.figure()
    plt.barh(names, means)
    plt.xlabel("Mean time (ms)")
    plt.title("Unit Profiling — per-function mean runtime (pytest-benchmark)")
    plt.tight_layout()
    plt.savefig(OUT, dpi=150)
    print(f"[plot] saved {OUT}")

if __name__ == "__main__":
    main()
