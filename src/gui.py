# src/gui.py
from __future__ import annotations
import os, sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Ensure local imports
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import image_ops
import batch as batch_mod

from PIL import Image, ImageTk, ImageDraw

APP_TITLE = "Image Processing App (Tkinter)"
PREVIEW_BG = "#2b2b2b"
PREVIEW_MAX_W, PREVIEW_MAX_H = 900, 600
DEFAULT_OUT = os.path.abspath(os.path.join(THIS_DIR, "..", "output"))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)

        # State
        self.current_img: Image.Image | None = None      # full-res working image
        self.original_img: Image.Image | None = None
        self.current_path: str | None = None
        self.batch_paths: list[str] = []

        # Preview state
        self.tkimg = None                    # strong reference to keep PhotoImage alive
        self._img_draw_info = None           # dict with scale, x, y, disp_size, img_size

        # Crop state (canvas selection)
        self.crop_mode = tk.BooleanVar(value=False)
        self._sel_rect_id = None
        self._sel_start = None   # (x, y) in canvas coords
        self._sel_end = None     # (x, y) in canvas coords

        # --------- Top bar ---------
        top = tk.Frame(root); top.pack(fill="x", padx=10, pady=8)
        tk.Button(top, text="Upload Image", command=self.upload_single).pack(side="left")
        tk.Button(top, text="Upload Batch", command=self.upload_batch).pack(side="left", padx=6)
        tk.Button(top, text="Reset", command=self.reset_original).pack(side="left", padx=6)
        tk.Button(top, text="Save As…", command=self.save_current).pack(side="left", padx=6)
        tk.Button(top, text="Apply to Batch → Output", command=self.apply_to_batch).pack(side="left", padx=6)
        tk.Button(top, text="Test Pattern", command=self._test_pattern).pack(side="left", padx=6)

        # --------- Operations ---------
        opts = tk.LabelFrame(root, text="Operations"); opts.pack(fill="x", padx=10, pady=8)

        # Resize
        self.keep_aspect = tk.BooleanVar(value=True)
        tk.Label(opts, text="Resize W×H:").grid(row=0, column=0, sticky="w")
        self.w_entry = tk.Entry(opts, width=7); self.w_entry.grid(row=0, column=1, padx=2)
        self.h_entry = tk.Entry(opts, width=7); self.h_entry.grid(row=0, column=2, padx=2)
        tk.Checkbutton(opts, text="Keep aspect (one side ok)", variable=self.keep_aspect)\
            .grid(row=0, column=3, sticky="w")
        tk.Button(opts, text="Apply Resize", command=self.do_resize).grid(row=0, column=4, padx=6)

        # Filters
        tk.Label(opts, text="Filter:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.filter_choice = ttk.Combobox(
            opts, values=["grayscale", "blur", "sharpen", "sepia"], width=12, state="readonly"
        )
        self.filter_choice.current(0)
        self.filter_choice.grid(row=1, column=1, sticky="w", pady=(6, 0))
        tk.Label(opts, text="Blur radius").grid(row=1, column=2, sticky="e", pady=(6, 0))
        self.blur_radius = tk.Entry(opts, width=6); self.blur_radius.insert(0, "2")
        self.blur_radius.grid(row=1, column=3, sticky="w", pady=(6, 0))
        tk.Button(opts, text="Apply Filter", command=self.do_filter).grid(row=1, column=4, padx=6, pady=(6, 0))

        # Rotate / Flip
        tk.Label(opts, text="Rotate (deg):").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.rotate_entry = tk.Entry(opts, width=7); self.rotate_entry.insert(0, "90")
        self.rotate_entry.grid(row=2, column=1, sticky="w", pady=(6, 0))
        tk.Button(opts, text="Rotate", command=self.do_rotate).grid(row=2, column=2, padx=6, pady=(6, 0))
        tk.Button(opts, text="Flip H", command=self.do_flip_h).grid(row=2, column=3, pady=(6, 0))
        tk.Button(opts, text="Flip V", command=self.do_flip_v).grid(row=2, column=4, pady=(6, 0))

        # Mouse-drag Crop UI
        crop_row = 3
        tk.Checkbutton(opts, text="Crop Mode (click & drag on image)", variable=self.crop_mode,
                       command=self._toggle_crop_mode).grid(row=crop_row, column=0, columnspan=3, sticky="w", pady=(6, 0))
        tk.Button(opts, text="Apply Crop", command=self.apply_crop_from_selection)\
            .grid(row=crop_row, column=3, padx=6, pady=(6, 0))
        tk.Button(opts, text="Clear Selection", command=self._clear_selection)\
            .grid(row=crop_row, column=4, padx=6, pady=(6, 0))

        # --------- Preview (Canvas) ---------
        self.preview = tk.Canvas(root, bd=1, relief="sunken", background=PREVIEW_BG,
                                 width=PREVIEW_MAX_W, height=PREVIEW_MAX_H)
        self.preview.pack(fill="both", expand=True, padx=10, pady=8)
        self.preview.bind("<Configure>", lambda e: self._refresh_preview())  # rerender on resize

        # Crop event bindings (enabled/disabled by crop mode toggle)
        self._bind_crop_events(False)

        os.makedirs(DEFAULT_OUT, exist_ok=True)

    # ====================== Core Preview ======================
    def _flatten_if_needed(self, img: Image.Image) -> Image.Image:
        """Flatten transparency to white for display (so RGBA screenshots show)."""
        needs = (img.mode in ("RGBA", "LA")) or ("transparency" in getattr(img, "info", {}))
        if not needs:
            return img
        bg = Image.new("RGB", img.size, "#ffffff")
        return Image.alpha_composite(bg.convert("RGBA"), img.convert("RGBA")).convert("RGB")

    def _show_img_on_canvas(self, img: Image.Image):
        """Render current image onto the canvas and record mapping info for crop mapping."""
        if img is None:
            return
        disp_src = self._flatten_if_needed(img)
        if disp_src.mode not in ("RGB", "RGBA"):
            disp_src = disp_src.convert("RGB")

        # Canvas size and fit
        self.root.update_idletasks()
        cw = max(self.preview.winfo_width(), 1)
        ch = max(self.preview.winfo_height(), 1)
        margin = 10
        max_w = max(cw - 2 * margin, 1)
        max_h = max(ch - 2 * margin, 1)

        iw, ih = disp_src.size
        scale = min(max_w / iw, max_h / ih, 1.0)
        dw, dh = (int(iw * scale), int(ih * scale))
        disp = disp_src if scale >= 1.0 else disp_src.resize((dw, dh))

        # Position top-left inside canvas (keep a margin)
        ox = margin + (max_w - dw) // 2  # center within available area
        oy = margin + (max_h - dh) // 2

        # Draw
        tkimg = ImageTk.PhotoImage(disp)
        self.tkimg = tkimg
        self.preview.delete("all")
        self.preview.create_rectangle(0, 0, cw, ch, fill=PREVIEW_BG, outline=PREVIEW_BG)
        self.preview.create_image(ox, oy, image=tkimg, anchor="nw")
        self.preview.create_rectangle(ox, oy, ox + dw, oy + dh, outline="#888")

        # Record draw info for mapping canvas->image coords
        self._img_draw_info = {
            "scale": scale,
            "canvas_x": ox,
            "canvas_y": oy,
            "disp_size": (dw, dh),
            "img_size": (iw, ih),
        }

        # Repaint selection (if any) on top
        if self._sel_start and self._sel_end:
            self._draw_selection_rect()

        print(f"[Canvas {cw}x{ch}] image orig={iw}x{ih} disp={dw}x{dh} scale={scale:.3f} at ({ox},{oy})")

    def _refresh_preview(self):
        if self.current_img:
            self._show_img_on_canvas(self.current_img)

    # ====================== Upload / Save / Reset ======================
    def upload_single(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")]
        )
        if not path:
            return
        img = image_ops.load_image(path); img.load()
        print(f"Loaded: {path} | mode={img.mode}, size={img.size}")
        self.current_path = path
        self.current_img = img
        self.original_img = img.copy()
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    def upload_batch(self):
        paths = filedialog.askopenfilenames(
            title="Choose multiple images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")]
        )
        if paths:
            self.batch_paths = list(paths)
            messagebox.showinfo("Batch loaded", f"{len(self.batch_paths)} images ready for batch processing.")

    def reset_original(self):
        if self.original_img is None:
            messagebox.showinfo("No Original", "Upload an image first.")
            return
        self.current_img = self.original_img.copy()
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    def save_current(self):
        if not self.current_img:
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("WEBP", "*.webp")]
        )
        if out:
            image_ops.save_image(self.current_img, out)
            messagebox.showinfo("Saved", f"Saved to:\n{out}")

    # ====================== Ops: Resize / Filters / Rotate / Flip ======================
    def do_resize(self):
        if not self.current_img:
            return
        w_txt = self.w_entry.get().strip()
        h_txt = self.h_entry.get().strip()
        width = int(w_txt) if w_txt else None
        height = int(h_txt) if h_txt else None

        if self.keep_aspect.get():
            self.current_img = image_ops.resize_aspect(self.current_img, width=width, height=height)
        else:
            ow, oh = self.current_img.size
            self.current_img = self.current_img.resize((width or ow, height or oh))

        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    def do_filter(self):
        if not self.current_img:
            return
        choice = self.filter_choice.get()
        try:
            if choice == "grayscale":
                self.current_img = image_ops.filter_grayscale(self.current_img)
            elif choice == "blur":
                try:
                    r = float(self.blur_radius.get())
                except Exception:
                    r = 2.0
                self.current_img = image_ops.filter_blur(self.current_img, radius=r)
            elif choice == "sharpen":
                self.current_img = image_ops.filter_sharpen(self.current_img)
            elif choice == "sepia":
                self.current_img = image_ops.filter_sepia(self.current_img)
            self._clear_selection()
            self._show_img_on_canvas(self.current_img)
        except Exception as e:
            print("Filter error:", e)
            messagebox.showerror("Filter error", f"Failed to apply filter:\n{e}")

    def do_rotate(self):
        if not self.current_img:
            return
        try:
            deg = float(self.rotate_entry.get())
        except Exception:
            deg = 90.0
        self.current_img = image_ops.rotate(self.current_img, deg)
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    def do_flip_h(self):
        if not self.current_img:
            return
        self.current_img = image_ops.flip_horizontal(self.current_img)
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    def do_flip_v(self):
        if not self.current_img:
            return
        self.current_img = image_ops.flip_vertical(self.current_img)
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)

    # ====================== Batch ======================
    def apply_to_batch(self):
        if not self.batch_paths:
            messagebox.showinfo("No Batch", "Load a batch first (Upload Batch).")
            return

        steps = []
        # Resize
        wtxt, htxt = self.w_entry.get().strip(), self.h_entry.get().strip()
        width = int(wtxt) if wtxt else None
        height = int(htxt) if htxt else None
        if width or height:
            steps.append(("resize", {"width": width, "height": height}))
        # Filter
        f = self.filter_choice.get()
        if f == "grayscale":
            steps.append(("grayscale", {}))
        elif f == "blur":
            try:
                r = float(self.blur_radius.get())
            except Exception:
                r = 2.0
            steps.append(("blur", {"radius": r}))
        elif f == "sharpen":
            steps.append(("sharpen", {}))
        elif f == "sepia":
            steps.append(("sepia", {}))
        # Rotate (optional)
        try:
            deg = float(self.rotate_entry.get())
            if deg != 0:
                steps.append(("rotate", {"degrees": deg}))
        except Exception:
            pass

        try:
            outputs = batch_mod.apply_pipeline(self.batch_paths, DEFAULT_OUT, steps)
            messagebox.showinfo("Batch complete", f"Saved {len(outputs)} files to:\n{DEFAULT_OUT}")
        except Exception as e:
            print("Batch error:", e)
            messagebox.showerror("Batch error", f"Failed to process batch:\n{e}")

    # ====================== Crop (Mouse-Drag) ======================
    def _toggle_crop_mode(self):
        self._bind_crop_events(self.crop_mode.get())
        if not self.crop_mode.get():
            self._clear_selection()

    def _bind_crop_events(self, enable: bool):
        if enable:
            self.preview.bind("<Button-1>", self._on_mouse_down)
            self.preview.bind("<B1-Motion>", self._on_mouse_drag)
            self.preview.bind("<ButtonRelease-1>", self._on_mouse_up)
        else:
            self.preview.unbind("<Button-1>")
            self.preview.unbind("<B1-Motion>")
            self.preview.unbind("<ButtonRelease-1>")

    def _on_mouse_down(self, event):
        if not self.current_img or not self._img_draw_info:
            return
        self._sel_start = (event.x, event.y)
        self._sel_end = (event.x, event.y)
        self._draw_selection_rect()

    def _on_mouse_drag(self, event):
        if self._sel_start is None:
            return
        self._sel_end = (event.x, event.y)
        self._draw_selection_rect()

    def _on_mouse_up(self, event):
        if self._sel_start is None:
            return
        self._sel_end = (event.x, event.y)
        self._draw_selection_rect()

    def _draw_selection_rect(self):
        """Draw or update the selection rectangle on the canvas."""
        # Remove previous rect
        if self._sel_rect_id:
            try:
                self.preview.delete(self._sel_rect_id)
            except Exception:
                pass
            self._sel_rect_id = None

        if not (self._sel_start and self._sel_end):
            return

        x0, y0 = self._sel_start
        x1, y1 = self._sel_end
        # draw overlay rect
        self._sel_rect_id = self.preview.create_rectangle(
            x0, y0, x1, y1, outline="#ff6", width=2
        )

    def _clear_selection(self):
        self._sel_start = None
        self._sel_end = None
        if self._sel_rect_id:
            try:
                self.preview.delete(self._sel_rect_id)
            except Exception:
                pass
            self._sel_rect_id = None

    def apply_crop_from_selection(self):
        """Map selection rectangle from canvas coords to image coords and crop safely."""
        if not self.current_img or not self._img_draw_info:
            messagebox.showinfo("No Image", "Upload an image first.")
            return
        if not (self._sel_start and self._sel_end):
            messagebox.showinfo("No Selection", "Enable Crop Mode and drag to select an area.")
            return

        x0, y0 = self._sel_start
        x1, y1 = self._sel_end
        # Normalize canvas rect
        cx0, cx1 = sorted((x0, x1))
        cy0, cy1 = sorted((y0, y1))

        # Map canvas -> image
        info = self._img_draw_info
        s = info["scale"]
        ox, oy = info["canvas_x"], info["canvas_y"]
        iw, ih = info["img_size"]

        # convert by subtracting image origin and dividing by scale
        l = int((cx0 - ox) / s)
        t = int((cy0 - oy) / s)
        r = int((cx1 - ox) / s)
        b = int((cy1 - oy) / s)

        # Clamp and validate
        l = max(0, min(l, iw))
        r = max(0, min(r, iw))
        t = max(0, min(t, ih))
        b = max(0, min(b, ih))

        if r <= l or b <= t:
            messagebox.showerror("Crop error", "Selection area is empty or outside the image.")
            return

        # Perform safe crop directly with Pillow
        try:
            self.current_img = self.current_img.crop((l, t, r, b))
            self._clear_selection()
            self._show_img_on_canvas(self.current_img)
        except Exception as e:
            messagebox.showerror("Crop error", f"Failed to crop:\n{e}")

    # ====================== Test Pattern ======================
    def _test_pattern(self):
        img = Image.new("RGB", (1000, 600), "#202830")
        d = ImageDraw.Draw(img)
        # outer frame
        d.rectangle([20, 20, 980, 580], outline="#66ccff", width=5)
        # grid
        for x in range(40, 980, 80):
            d.line([x, 40, x, 560], fill="#3a6", width=1)
        for y in range(40, 580, 80):
            d.line([40, y, 960, y], fill="#3a6", width=1)
        d.text((50, 50), "Canvas Preview & Crop Test", fill="#ffffff")
        self.current_img = img
        self.original_img = img.copy()
        self._clear_selection()
        self._show_img_on_canvas(self.current_img)


def main():
    os.makedirs(DEFAULT_OUT, exist_ok=True)
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
