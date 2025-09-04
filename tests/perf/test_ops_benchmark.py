# tests/perf/test_ops_benchmark.py
import os, sys, pytest
from PIL import Image

# add src/ to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import image_ops


def _img(w=1920, h=1080):
    return Image.new("RGB", (w, h), "#7788aa")


@pytest.mark.perf
def test_resize_maintain_aspect(benchmark):
    img = _img()
    # enforce at least 10 runs explicitly
    benchmark.pedantic(lambda: image_ops.resize_aspect(img, width=800),
                       rounds=10, iterations=1)


@pytest.mark.perf
@pytest.mark.parametrize("filter_name", ["grayscale", "blur", "sharpen", "sepia"])
def test_filters(benchmark, filter_name):
    img = _img()

    def work():
        if filter_name == "grayscale":
            image_ops.filter_grayscale(img)
        elif filter_name == "blur":
            image_ops.filter_blur(img, radius=2.5)
        elif filter_name == "sharpen":
            image_ops.filter_sharpen(img)
        elif filter_name == "sepia":
            image_ops.filter_sepia(img)

    benchmark.pedantic(work, rounds=10, iterations=1)


@pytest.mark.perf
def test_rotate_flip_crop(benchmark):
    img = _img()

    def work():
        r = image_ops.rotate(img, 90)
        r = image_ops.flip_horizontal(r)
        image_ops.crop_box(r, (100, 100, 1000, 800))

    benchmark.pedantic(work, rounds=10, iterations=1)
