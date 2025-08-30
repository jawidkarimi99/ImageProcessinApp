# src/image_ops.py
from __future__ import annotations
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageOps

# --- I/O ---
def load_image(path: str) -> Image.Image:
    return Image.open(path)

def save_image(img: Image.Image, path: str) -> None:
    img.save(path)

# --- Resize (aspect aware) ---
def resize_aspect(
    img: Image.Image,
    width: Optional[int] = None,
    height: Optional[int] = None
) -> Image.Image:
    if width is None and height is None:
        return img.copy()
    w0, h0 = img.size
    if width and height:
        return img.resize((int(width), int(height)))
    if width and not height:
        h = int((width / w0) * h0)
        return img.resize((int(width), h))
    if height and not width:
        w = int((height / h0) * w0)
        return img.resize((w, int(height)))
    return img.copy()

# --- Filters ---
def filter_grayscale(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img)

def filter_blur(img: Image.Image, radius: float = 2.0) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius))

def filter_sharpen(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.SHARPEN)

def filter_sepia(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            tr = int(0.393*r + 0.769*g + 0.189*b)
            tg = int(0.349*r + 0.686*g + 0.168*b)
            tb = int(0.272*r + 0.534*g + 0.131*b)
            px[x, y] = (min(tr, 255), min(tg, 255), min(tb, 255))
    return rgb

# --- Transforms ---
def rotate(img: Image.Image, degrees: float) -> Image.Image:
    return img.rotate(degrees, expand=True)

def flip_horizontal(img: Image.Image) -> Image.Image:
    return ImageOps.mirror(img)

def flip_vertical(img: Image.Image) -> Image.Image:
    return ImageOps.flip(img)

def crop_box(img: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    return img.crop(box)
def crop_box_safe(img, box):
    """
    Normalize and clamp a crop box to image bounds.
    Expects box as (L, T, R, B) in any order; returns a valid box or raises ValueError if zero-area.
    """
    w, h = img.size
    l, t, r, b = box

    # normalize order
    l, r = sorted((int(l), int(r)))
    t, b = sorted((int(t), int(b)))

    # clamp to image bounds
    l = max(0, min(l, w))
    r = max(0, min(r, w))
    t = max(0, min(t, h))
    b = max(0, min(b, h))

    # ensure non-zero area
    if r <= l or b <= t:
        raise ValueError(f"Invalid crop area: ({l},{t},{r},{b})")

    return img.crop((l, t, r, b))
