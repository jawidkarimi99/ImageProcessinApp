# tests/perf/test_unit_profile.py
import os, time, statistics
import pytest
from PIL import Image

# Import the project code
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
import image_ops  # noqa: E402

# ---- Config ----
# Use stricter thresholds if you set MODE_FAST=1; otherwise generous defaults.
FAST = os.getenv("MODE_FAST", "0") == "1"

# Test image size (synthetic, deterministic)
W, H = 2560, 1440

# Per-operation max allowed mean time in milliseconds (tune if needed)
MAX_MS_DEFAULT = {
    "resize_aspect": 25.0,   # 2560x1440 -> width=1200
    "filter_grayscale": 6.0,
    "filter_blur": 40.0,     # radius=1.5
    "filter_sharpen": 20.0,
    "filter_sepia": 900.0,   # change to ~20.0 if you use the optimized sepia
    "rotate": 8.0,           # 90 degrees
    "flip_horizontal": 4.0,
    "flip_vertical": 4.0,
    "crop_box": 6.0,
}
MAX_MS_FAST = {
    "resize_aspect": 18.0,
    "filter_grayscale": 4.0,
    "filter_blur": 30.0,
    "filter_sharpen": 12.0,
    "filter_sepia": 25.0,    # assume optimized sepia
    "rotate": 5.0,
    "flip_horizontal": 3.0,
    "flip_vertical": 3.0,
    "crop_box": 4.0,
}
MAX_MS = MAX_MS_FAST if FAST else MAX_MS_DEFAULT

# Operations under test (name, callable(img))
OPS = [
    ("resize_aspect", lambda img: image_ops.resize_aspect(img, width=1200)),
    ("filter_grayscale", image_ops.filter_grayscale),
    ("filter_blur", lambda img: image_ops.filter_blur(img, radius=1.5)),
    ("filter_sharpen", image_ops.filter_sharpen),
    ("filter_sepia", image_ops.filter_sepia),
    ("rotate", lambda img: image_ops.rotate(img, degrees=90)),
    ("flip_horizontal", image_ops.flip_horizontal),
    ("flip_vertical", image_ops.flip_vertical),
    ("crop_box", lambda img: image_ops.crop_box(img, box=(50, 50, 1200, 700))),
]

@pytest.fixture(scope="module")
def base_img():
    # Synthetic, stable test image
    return Image.new("RGB", (W, H), (120, 120, 160))

# ---------- A) Benchmark (for nice pytest-benchmark tables) ----------
@pytest.mark.perf
@pytest.mark.parametrize("name,fn", OPS, ids=[n for n, _ in OPS])
def test_unit_benchmark(benchmark, base_img, name, fn):
    # Use pedantic to control rounds/iterations = "execute 10× and average"
    result = benchmark.pedantic(lambda: fn(base_img), iterations=1, rounds=10)
    # Nothing to assert here—pytest-benchmark reports stats.
    # Threshold assertions are in the next test.

# ---------- B) Threshold assertions (max/min acceptable times) ----------
@pytest.mark.perf
@pytest.mark.parametrize("name,fn", OPS, ids=[n for n, _ in OPS])
def test_unit_time_thresholds(name, fn, base_img):
    runs = 10
    times_ms = []
    for _ in range(runs):
        t0 = time.perf_counter()
        _ = fn(base_img)
        dt = (time.perf_counter() - t0) * 1000.0
        times_ms.append(dt)
    mean_ms = statistics.mean(times_ms)
    min_ms = min(times_ms)
    max_ms = max(times_ms)

    # Basic sanity and SLA check
    assert min_ms >= 0.0
    assert mean_ms <= MAX_MS[name], (
        f"{name}: mean {mean_ms:.2f} ms exceeded limit {MAX_MS[name]:.2f} ms "
        f"(min={min_ms:.2f}, max={max_ms:.2f}). "
        f"Hint: set MODE_FAST=1 for stricter targets or tune MAX_MS."
    )
