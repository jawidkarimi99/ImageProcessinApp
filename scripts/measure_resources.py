# scripts/measure_resources.py
import csv, time, threading
from pathlib import Path
import os, sys
import psutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))
import batch as batch_mod  # noqa: E402

def make_synth_images(tmp_dir: Path, n: int, size=(2560, 1440)):
    tmp_dir.mkdir(exist_ok=True, parents=True)
    paths = []
    for i in range(n):
        p = tmp_dir / f"res_{i:03d}.jpg"
        if not p.exists():
            Image.new("RGB", size, (120, 120, 160)).save(p, "JPEG", quality=90, optimize=True)
        paths.append(str(p))
    return paths

def sample_resources(csv_path: Path, interval=0.2, stop_flag: list = None):
    proc = psutil.Process(os.getpid())
    # warm up CPU percentage to avoid first call 0.0
    psutil.cpu_percent(interval=None)

    # Disk counters may be None on some systems; guard reads
    def disk_bytes():
        try:
            io = psutil.disk_io_counters()
            return (io.read_bytes, io.write_bytes) if io else (0, 0)
        except Exception:
            return (0, 0)

    r0, w0 = disk_bytes()
    t0 = time.time()
    with csv_path.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["t_sec", "cpu_percent", "rss_mb", "read_kb", "write_kb"])
        while not stop_flag[0]:
            time.sleep(interval)
            now = time.time() - t0
            cpu = psutil.cpu_percent(interval=None)
            rss_mb = proc.memory_info().rss / (1024 * 1024)
            r, w = disk_bytes()
            wr.writerow([f"{now:.2f}", f"{cpu:.1f}", f"{rss_mb:.2f}",
                         f"{(r - r0)/1024:.1f}", f"{(w - w0)/1024:.1f}"])
            f.flush()

def main():
    out_csv = ROOT / "perf_resource_metrics.csv"
    tmp = ROOT / "tmp_imgs"
    out_dir = ROOT / "output"

    n_imgs = int(os.getenv("N_IMGS", "60"))
    width = int(os.getenv("RESIZE_W", "800"))
    workers = int(os.getenv("WORKERS", "0"))
    interval = float(os.getenv("SAMPLE_SEC", "0.2"))

    paths = make_synth_images(tmp, n_imgs)
    steps = [("resize", {"width": width}),
             ("blur", {"radius": 1.5}),
             ("sharpen", {}),
             ("rotate", {"degrees": 90})]

    stop_flag = [False]
    t = threading.Thread(target=sample_resources, args=(out_csv, interval, stop_flag), daemon=True)
    t.start()

    t0 = time.perf_counter()
    batch_mod.apply_pipeline(paths, str(out_dir), steps, workers=workers)
    dt = time.perf_counter() - t0
    stop_flag[0] = True
    t.join()

    print(f"[resources] wrote {out_csv}")
    print(f"[resources] processed {n_imgs} images in {dt:.2f}s -> {n_imgs/dt:.2f} img/s")

if __name__ == "__main__":
    main()
