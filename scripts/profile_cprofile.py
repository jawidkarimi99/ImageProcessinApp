# scripts/profile_cprofile.py
import cProfile, pstats, io, argparse, time
from pathlib import Path
from PIL import Image
import os, sys

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.append(str(SRC))
import image_ops
import batch as batch_mod

def make_img(w=3840, h=2160, color="#446688"):
    return Image.new("RGB", (w, h), color)

def profile_single():
    """Profile individual operations to see their cost."""
    img = make_img()
    img = image_ops.resize_aspect(img, width=1200)
    img = image_ops.filter_blur(img, radius=2.5)
    img = image_ops.filter_sharpen(img)
    img = image_ops.rotate(img, 90)
    img = image_ops.crop_box(img, (50, 50, 1000, 700))
    return img

def profile_pipeline(n=50, width=800, workers=0):
    """Profile batch pipeline over n synthetic images."""
    tmp = Path("tmp_imgs"); tmp.mkdir(exist_ok=True)
    paths = []
    for i in range(n):
        p = tmp / f"img_{i:03d}.jpg"
        if not p.exists():
            Image.new("RGB", (2560, 1440), (120, 120, 160)).save(p, "JPEG", quality=90)
        paths.append(str(p))
    steps = [("resize", {"width": width}),
             ("blur", {"radius": 1.5}),
             ("sharpen", {}),
             ("rotate", {"degrees": 90})]
    out_dir = Path("output"); out_dir.mkdir(exist_ok=True)
    batch_mod.apply_pipeline(paths, str(out_dir), steps, workers=workers)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["single","pipeline"], default="single")
    ap.add_argument("--n", type=int, default=50, help="num images for pipeline")
    ap.add_argument("--width", type=int, default=800, help="resize width for pipeline")
    ap.add_argument("--workers", type=int, default=0, help="thread workers for pipeline")
    ap.add_argument("--top", type=int, default=30, help="how many rows to print")
    args = ap.parse_args()

    func = profile_single if args.mode == "single" else (lambda: profile_pipeline(args.n, args.width, args.workers))

    pr = cProfile.Profile()
    pr.enable()
    t0 = time.perf_counter()
    func()
    dt = time.perf_counter() - t0
    pr.disable()

    # text stats
    s = io.StringIO()
    p = pstats.Stats(pr, stream=s).sort_stats("cumtime")
    p.print_stats(args.top)
    Path("perf_cprofile.txt").write_text(s.getvalue())
    print(f"[cProfile] elapsed={dt:.2f}s  wrote perf_cprofile.txt")

    # binary stats for Snakeviz
    pr.dump_stats("perf_cprofile.prof")
    print("Open with: snakeviz perf_cprofile.prof")

if __name__ == "__main__":
    main()
