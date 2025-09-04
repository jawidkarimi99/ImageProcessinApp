# scripts/plot_metrics.py
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "perf_resource_metrics.csv"

def read_csv(path: Path):
    t, cpu, rss, rkb, wkb = [], [], [], [], []
    with path.open() as f:
        rd = csv.DictReader(f)
        for row in rd:
            t.append(float(row["t_sec"]))
            cpu.append(float(row["cpu_percent"]))
            rss.append(float(row["rss_mb"]))
            rkb.append(float(row["read_kb"]))
            wkb.append(float(row["write_kb"]))
    return t, cpu, rss, rkb, wkb

def save_plot(x, y, ylabel, out_png):
    plt.figure()
    plt.plot(x, y)
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.title(ylabel + " over time")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"[plot] saved {out_png}")

def main():
    if not CSV.exists():
        raise SystemExit(f"CSV not found: {CSV}. Run scripts/measure_resources.py first.")
    t, cpu, rss, rkb, wkb = read_csv(CSV)
    save_plot(t, cpu, "CPU %", ROOT / "plot_cpu.png")
    save_plot(t, rss, "RSS Memory (MB)", ROOT / "plot_mem.png")
    save_plot(t, rkb, "Disk Read (KB since start)", ROOT / "plot_disk_read.png")
    save_plot(t, wkb, "Disk Write (KB since start)", ROOT / "plot_disk_write.png")

if __name__ == "__main__":
    main()
