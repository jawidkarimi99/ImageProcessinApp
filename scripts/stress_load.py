# scripts/stress_load.py
import csv, time
from pathlib import Path
import os, sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))
import batch as batch_mod  # noqa: E402

def make_synth_images(tmp_dir: Path, n: int, size):
    tmp_dir.mkdir(exist_ok=True, parents=True)
    paths = []
    for i in range(n):
        p = tmp_dir / f"load_{size[0]}x{size[1]}_{i:04d}.jpg"
        if not p.exists():
            Image.new("RGB", size, (110, 120, 150)).save(p, "JPEG", quality=90, optimize=True)
        paths.append(str(p))
    return paths

def run_case(n_imgs, resize_w, workers):
    tmp = ROOT / "tmp_imgs"
    out_dir = ROOT / "output"
    paths = make_synth_images(tmp, n_imgs, size=(resize_w*2, int(resize_w*2*9/16)))  # create larger than target
    steps = [("resize", {"width": resize_w}),
             ("blur", {"radius": 1.0}),
             ("sharpen", {}),
             ("rotate", {"degrees": 90})]
    t0 = time.perf_counter()
    batch_mod.apply_pipeline(paths, str(out_dir), steps, workers=workers)
    dt = time.perf_counter() - t0
    return dt, n_imgs / dt

def main():
    batch_sizes = [10, 25, 50, 100]
    resize_ws   = [1280, 1920, 3840]  # HD, FHD, 4K width targets
    workers     = int(os.getenv("WORKERS", "0"))

    out_csv = ROOT / "perf_load_curve.csv"
    with out_csv.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["batch_size", "resize_w", "workers", "seconds", "images_per_sec"])
        for w in resize_ws:
            for n in batch_sizes:
                sec, ips = run_case(n, w, workers)
                wr.writerow([n, w, workers, f"{sec:.2f}", f"{ips:.2f}"])
                f.flush()
                print(f"[load] resize_w={w} batch={n} workers={workers}: {ips:.2f} img/s ({sec:.2f}s)")

    print(f"[load] wrote {out_csv}")

if __name__ == "__main__":
    main()
