from PIL import Image
import os, sys

# add src/ to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import image_ops


def test_resize_aspect_width_only():
    img = Image.new("RGB", (2000, 1000), "gray")
    out = image_ops.resize_aspect(img, width=1000)
    assert out.size == (1000, 500)


def test_resize_aspect_height_only():
    img = Image.new("RGB", (2000, 1000), "gray")
    out = image_ops.resize_aspect(img, height=500)
    assert out.size == (1000, 500)


def test_grayscale_mode():
    img = Image.new("RGB", (100, 50), "white")
    out = image_ops.filter_grayscale(img)
    assert out.mode in ("L", "LA")  # grayscale mode


def test_flip_horizontal_changes_pixels():
    img = Image.new("RGB", (10, 1), "black")
    img.putpixel((0, 0), (255, 0, 0))  # leftmost pixel red
    out = image_ops.flip_horizontal(img)
    assert out.getpixel((9, 0)) == (255, 0, 0)  # now red on right
