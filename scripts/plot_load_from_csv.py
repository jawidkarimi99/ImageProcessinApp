# scripts/plot_load_from_csv.py
# Robust loader for load/stress CSVs. Creates reports/load_curve.png

import csv, argparse
from pathlib import Path
import matplotlib.pyplot as plt

def pick(r, *keys, default=None):
    for k in keys:
        if k in r and r[k] != "":
            return r[k]
    return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="reports/load_curve.png")
    ap.add_argument("--title", default="Load Curve: Batch Size vs Images/sec")
    args = ap.parse_args()

    x, y = [], []
    with open(args.csv, newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            # Try common column names
            bs = pick(r, "batch_size", "n", "batch", "images", "count")
            ips = pick(r, "imgs_per_sec", "throughput", "ops", "images_per_sec")
            # Or compute throughput from elapsed/count if needed
            if ips is None:
                elapsed = pick(r, "elapsed_sec", "elapsed", "time_s", "seconds")
                if bs is not None and elapsed not in (None, "", "0"):
                    try:
                        ips = float(bs) / float(elapsed)
                    except Exception:
                        ips = None
            if bs is None or ips is None:
                continue
            try:
                x.append(int(float(bs)))
                y.append(float(ips))
            except Exception:
                pass

    if not x:
        raise SystemExit(f"No usable data parsed from {args.csv}. Check headers with: head -5 {args.csv}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.plot(x, y, marker="o")
    plt.xlabel("Batch size (images)")
    plt.ylabel("Images per second")
    plt.title(args.title)
    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    print(f"[ok] saved {Path(args.out).resolve()}")

if __name__ == "__main__":
    main()
