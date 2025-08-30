# tests/test_perf.py
from __future__ import annotations
import os, time, statistics, cProfile, pstats, io
from typing import Callable
import psutil
import matplotlib.pyplot as plt

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
import image_ops  # noqa

IMG = os.path.join(os.path.dirname(__file__), "..", "images", "sample.jpg")
OUT = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUT, exist_ok=True)

RUNS = 10

def time_avg(fn: Callable[[], None]) -> float:
    times = []
    for _ in range(RUNS):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.mean(times)

def test_resize_perf():
    img = image_ops.load_image(IMG)
    def work():
        _ = image_ops.resize_aspect(img, width=800)
    avg = time_avg(work)
    print(f"Avg resize (800w): {avg:.6f}s")

def test_filters_perf():
    img = image_ops.load_image(IMG)
    def blur():
        _ = image_ops.filter_blur(img, 2.0)
    def gray():
        _ = image_ops.filter_grayscale(img)
    def sepia():
        _ = image_ops.filter_sepia(img)

    results = {
        "blur": time_avg(blur),
        "grayscale": time_avg(gray),
        "sepia": time_avg(sepia),
    }
    # chart
    names = list(results.keys())
    vals = [results[k] for k in names]
    plt.figure()
    plt.bar(names, vals)
    plt.ylabel("Average seconds (10x)")
    plt.title("Filter performance")
    plt.savefig(os.path.join(OUT, "filters_perf.png"))
    plt.close()

def test_cpu_mem_profile():
    proc = psutil.Process(os.getpid())
    img = image_ops.load_image(IMG)
    mem_before = proc.memory_info().rss
    cpu_before = psutil.cpu_percent(interval=None)

    # do some work
    for _ in range(50):
        x = image_ops.filter_blur(img, 2.0)
        x = image_ops.filter_sharpen(x)
        x = image_ops.resize_aspect(x, width=600)

    cpu_after = psutil.cpu_percent(interval=0.1)
    mem_after = proc.memory_info().rss

    with open(os.path.join(OUT, "resource_usage.txt"), "w") as f:
        f.write(f"CPU before: {cpu_before}%\nCPU after (instant): {cpu_after}%\n")
        f.write(f"RSS before: {mem_before} bytes\nRSS after: {mem_after} bytes\n")

def test_cprofile_dump():
    pr = cProfile.Profile()
    img = image_ops.load_image(IMG)

    def pipeline():
        x = image_ops.resize_aspect(img, width=800)
        x = image_ops.filter_grayscale(x)
        x = image_ops.filter_blur(x, 2.0)
        x = image_ops.filter_sepia(x)
        return x

    pr.enable()
    for _ in range(20):
        pipeline()
    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)
    with open(os.path.join(OUT, "cprofile_top.txt"), "w") as f:
        f.write(s.getvalue())
