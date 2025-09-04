# scripts/plot_load_curve.py
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "perf_load_curve.csv"

def read_csv(path: Path):
    rows = []
    with path.open() as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append({
                "batch": int(r["batch_size"]),
                "w": int(r["resize_w"]),
                "workers": int(r["workers"]),
                "sec": float(r["seconds"]),
                "ips": float(r["images_per_sec"]),
            })
    return rows

def main():
    if not CSV.exists():
        raise SystemExit(f"CSV not found: {CSV}. Run scripts/stress_load.py first.")
    rows = read_csv(CSV)
    by_w = {}
    for r in rows:
        by_w.setdefault(r["w"], []).append(r)

    for w, arr in by_w.items():
        arr = sorted(arr, key=lambda x: x["batch"])
        x = [r["batch"] for r in arr]
        y = [r["ips"] for r in arr]
        workers = arr[0]["workers"] if arr else 0

        plt.figure()
        plt.plot(x, y, marker="o")
        plt.xlabel("Batch size (images)")
        plt.ylabel("Throughput (images/sec)")
        plt.title(f"Throughput vs Batch Size — target width {w}px (workers={workers})")
        plt.tight_layout()
        out_png = ROOT / f"load_{w}.png"
        plt.savefig(out_png, dpi=150)
        plt.close()
        print(f"[plot] saved {out_png}")

if __name__ == "__main__":
    main()
