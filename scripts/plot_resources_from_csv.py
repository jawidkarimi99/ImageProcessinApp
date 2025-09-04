# scripts/plot_resources_from_csv.py
# Plots CPU %, Memory (MB), and Disk I/O (MB/s) from perf_resources.csv

import csv, argparse
from pathlib import Path
import matplotlib.pyplot as plt

def to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def load(path):
    t, cpu, rss, r_abs, w_abs = [], [], [], [], []
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        # Accept flexible column names
        cols = {k.lower(): k for k in rd.fieldnames or []}
        def get(row, *names):
            for n in names:
                k = cols.get(n.lower())
                if k and row.get(k, "") != "":
                    return row[k]
            return None
        for r in rd:
            ts = get(r, "t_sec", "time", "t", "seconds")
            t.append(to_float(ts))
            cpu.append(to_float(get(r, "cpu_percent", "cpu", "cpu_pct")))
            rss.append(to_float(get(r, "rss_mb", "rss", "mem_mb", "memory_mb")))
            # disk values may be absolute bytes or already MB; we’ll diff into rates
            r_abs.append(to_float(get(r, "read_mb", "read_bytes", "disk_read")))
            w_abs.append(to_float(get(r, "write_mb", "write_bytes", "disk_write")))
    return t, cpu, rss, r_abs, w_abs

def to_rate_mb(abs_vals, times):
    if not abs_vals or not times:
        return [0.0]*len(times)
    # Detect units: if largest is huge, assume bytes and convert to MB.
    scale = 1.0/(1024*1024) if max(abs_vals) > 10000 else 1.0
    mb = [v*scale for v in abs_vals]
    rates = [0.0]
    for i in range(1, len(mb)):
        dt = max(times[i] - times[i-1], 1e-6)
        rates.append(max((mb[i] - mb[i-1]) / dt, 0.0))
    return rates

def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"[ok] saved {path.resolve()}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--outdir", default="reports")
    ap.add_argument("--prefix", default="resources_")
    args = ap.parse_args()

    t, cpu, rss, r_abs, w_abs = load(args.csv)
    if not t:
        raise SystemExit(f"No data in {args.csv}. Check with: head -5 {args.csv}")

    r_rate = to_rate_mb(r_abs, t)
    w_rate = to_rate_mb(w_abs, t)

    outdir = Path(args.outdir)

    # CPU
    fig = plt.figure()
    plt.plot(t, cpu)
    plt.xlabel("Time (s)"); plt.ylabel("CPU (%)"); plt.title("CPU Utilization")
    save(fig, outdir / f"{args.prefix}cpu.png"); plt.close(fig)

    # Memory
    fig = plt.figure()
    plt.plot(t, rss)
    plt.xlabel("Time (s)"); plt.ylabel("RSS (MB)"); plt.title("Memory Usage")
    save(fig, outdir / f"{args.prefix}mem.png"); plt.close(fig)

    # Disk
    fig = plt.figure()
    plt.plot(t, r_rate, label="Read MB/s")
    plt.plot(t, w_rate, label="Write MB/s")
    plt.xlabel("Time (s)"); plt.ylabel("MB/s"); plt.title("Disk I/O Rate")
    plt.legend()
    save(fig, outdir / f"{args.prefix}disk.png"); plt.close(fig)

if __name__ == "__main__":
    main()
