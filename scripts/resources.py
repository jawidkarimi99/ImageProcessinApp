# scripts/resources.py
# Collect CPU, memory, and disk I/O while running the batch pipeline.
# Writes a CSV you can plot with plot_resources_from_csv.py

from __future__ import annotations
import argparse
import csv
import os
import sys
import time
from pathlib import Path

import psutil
from PIL import Image

# --- Make src/ importable (so "import batch" works) ---
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import batch as batch_mod  # noqa: E402


def make_inputs(n: int, w: int, h: int, input_dir: Path) -> list[str]:
    """Create n synthetic images for reproducible tests and return their paths."""
    input_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i in range(n):
        p = input_dir / f"in_{i:04d}.jpg"
        if not p.exists():
            img = Image.new("RGB", (w, h), (120, 120, 160))
            img.save(p, "JPEG", quality=85, optimize=True)
        paths.append(str(p))
    return paths


def run_pipeline(paths: list[str], out_dir: Path, workers: int) -> float:
    """Run a representative pipeline and return elapsed seconds."""
    steps = [
        ("resize", {"width": 1920}),      # maintain aspect ratio inside image_ops
        ("blur", {"radius": 1.5}),
        ("sharpen", {}),
        ("rotate", {"degrees": 90}),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    batch_mod.apply_pipeline(paths, str(out_dir), steps, workers=workers)
    return time.perf_counter() - t0


def sampler(proc: psutil.Process, interval: float, rows_out: list[dict]):
    """
    Sample CPU%, RSS MB, and disk read/write (as absolute bytes; rates computed later).
    Appends rows to rows_out as dicts with keys: t_sec, cpu_percent, rss_mb, read_abs, write_abs.
    """
    # prime CPU measurement
    proc.cpu_percent(None)

    # Try per-process IO counters first; if unavailable, fall back to system counters
    per_process_io_ok = True
    last_r = last_w = None
    sys_last_r = sys_last_w = None

    t0 = time.perf_counter()
    while True:
        now = time.perf_counter()
        t = now - t0
        try:
            cpu = proc.cpu_percent(None)          # % over interval
            rss = proc.memory_info().rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):  # process ended
            break

        read_abs = write_abs = 0.0
        if per_process_io_ok:
            try:
                io = proc.io_counters()
                read_abs = float(getattr(io, "read_bytes", 0))
                write_abs = float(getattr(io, "write_bytes", 0))
            except Exception:
                per_process_io_ok = False

        if not per_process_io_ok:
            try:
                d = psutil.disk_io_counters()
                read_abs = float(d.read_bytes)
                write_abs = float(d.write_bytes)
            except Exception:
                read_abs = write_abs = 0.0

        rows_out.append(
            {
                "t_sec": f"{t:.3f}",
                "cpu_percent": f"{cpu:.2f}",
                "rss_mb": f"{rss:.2f}",
                # store absolute counters; plotter will compute MB/s via diffs
                "read_mb": f"{read_abs}",   # (bytes; unit detected later)
                "write_mb": f"{write_abs}", # (bytes; unit detected later)
            }
        )
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description="Measure CPU/Mem/Disk while running batch pipeline.")
    ap.add_argument("--n", type=int, default=60, help="number of images")
    ap.add_argument("--width", type=int, default=1920, help="synthetic input width")
    ap.add_argument("--height", type=int, default=1080, help="synthetic input height")
    ap.add_argument("--workers", type=int, default=0, help="parallel workers (0 = single-threaded)")
    ap.add_argument("--interval", type=float, default=0.25, help="sampling interval (seconds)")
    ap.add_argument("--csv", type=str, default="perf_resources.csv", help="output CSV filename")
    ap.add_argument("--outdir", type=str, default="tmp_metrics_out", help="output images directory")
    args = ap.parse_args()

    # Prepare inputs/outputs
    tmp_in = ROOT / "tmp_metrics_inputs"
    out_dir = ROOT / args.outdir
    paths = make_inputs(args.n, args.width, args.height, tmp_in)

    # Process object for current Python
    proc = psutil.Process(os.getpid())

    # Collect samples in a background thread while the pipeline runs
    import threading
    rows: list[dict] = []

    sampling = True

    def run_sampling():
        # sample until the pipeline finishes (main thread will stop by toggling sampling flag)
        while sampling:
            sampler(proc, args.interval, rows)
            # sampler returns only if process ended; keep short sleep to avoid busy loop
            time.sleep(args.interval)

    th = threading.Thread(target=run_sampling, daemon=True)
    th.start()

    # Run workload
    try:
        elapsed = run_pipeline(paths, out_dir, workers=args.workers)
    finally:
        # stop sampling and join
        sampling = False
        th.join(timeout=1.0)

    # Ensure at least one row
    if not rows:
        # take a one-off sample
        cpu = proc.cpu_percent(None)
        rss = proc.memory_info().rss / (1024 * 1024)
        rows.append({"t_sec": "0.000", "cpu_percent": f"{cpu:.2f}", "rss_mb": f"{rss:.2f}", "read_mb": "0", "write_mb": "0"})

    # Write CSV
    csv_path = ROOT / args.csv
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["t_sec", "cpu_percent", "rss_mb", "read_mb", "write_mb"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[metrics] wrote {csv_path} ({len(rows)} samples). Pipeline elapsed={elapsed:.2f}s. Outputs in {out_dir}")


if __name__ == "__main__":
    main()
