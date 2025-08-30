# src/batch.py
from __future__ import annotations
import os
from typing import Callable, Iterable, List, Tuple, Dict, Any
from PIL import Image
import image_ops

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def list_images(folder: str) -> List[str]:
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]

def apply_pipeline(
    input_paths: Iterable[str],
    output_folder: str,
    steps: List[Tuple[str, Dict[str, Any]]]
) -> List[str]:
    """
    steps: list of (operation_name, kwargs)
      operation_name in {"resize","grayscale","blur","sharpen","sepia","rotate","flip_h","flip_v","crop"}
    """
    ensure_dir(output_folder)
    outputs = []
    for p in input_paths:
        img = image_ops.load_image(p)
        for op, kwargs in steps:
            if op == "resize":
                img = image_ops.resize_aspect(img, **kwargs)
            elif op == "grayscale":
                img = image_ops.filter_grayscale(img)
            elif op == "blur":
                img = image_ops.filter_blur(img, **kwargs)
            elif op == "sharpen":
                img = image_ops.filter_sharpen(img)
            elif op == "sepia":
                img = image_ops.filter_sepia(img)
            elif op == "rotate":
                img = image_ops.rotate(img, **kwargs)
            elif op == "flip_h":
                img = image_ops.flip_horizontal(img)
            elif op == "flip_v":
                img = image_ops.flip_vertical(img)
            elif op == "crop":
                img = image_ops.crop_box(img, **kwargs)
            else:
                raise ValueError(f"Unknown step: {op}")
        base = os.path.basename(p)
        out_path = os.path.join(output_folder, f"processed_{base}")
        image_ops.save_image(img, out_path)
        outputs.append(out_path)
    return outputs
