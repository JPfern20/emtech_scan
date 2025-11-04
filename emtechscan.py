# ...existing code...
#!/usr/bin/env python3
"""
EmTechScan – Classical OCR (External Engines: GOCR / Cuneiform)
-------------------------------------------------
- Uses external CLI OCR engines (gocr or cuneiform) instead of template/ML
- Supports image and PDF input
- Saves recognized text to Word (.docx) or Text (.txt)
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageTk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
from docx import Document
from pdf2image import convert_from_path

import subprocess
import tempfile
import shutil

# ...existing code...

class ExternalOCREngine:
    """
    Wrap calls to external OCR engines (gocr or cuneiform).
    The class preprocesses/deskews the image, writes a temp PNG,
    invokes the selected engine and returns the extracted text.
    """
    def __init__(self, engine='gocr', language='eng'):
        self.engine = engine
        self.language = language

    def engine_available(self):
        return shutil.which(self.engine) is not None

    def _preprocess_image(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Invalid image file")

        img = cv2.GaussianBlur(img, (3, 3), 0)
        _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Deskew
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            (h, w) = thresh.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w, h),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE)
        return thresh

    def _save_temp_png(self, img_path):
        thresh = self._preprocess_image(img_path)
        fd, tmp = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        cv2.imwrite(tmp, thresh)
        return tmp

    def recognize(self, img_path):
        """
        Recognize text using the chosen external engine.
        Returns recognized text as a string.
        """
        if not self.engine_available():
            raise FileNotFoundError(f"Engine '{self.engine}' not found in PATH. Install it or choose another engine.")

        tmp_img = self._save_temp_png(img_path)
        try:
            if self.engine == "gocr":
                # gocr outputs to stdout; pass the image file path
                proc = subprocess.run([self.engine, tmp_img],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
                text = proc.stdout.strip()
                # gocr may print warnings on stderr; ignore or include if helpful
            elif self.engine == "cuneiform":
                # cuneiform typically writes to a file; create a temp output file
                out_fd, out_path = tempfile.mkstemp(suffix='.txt')
                os.close(out_fd)
                cmd = [self.engine, "-l", self.language, "-f", "text", "-o", out_path, tmp_img]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Read output file contents
                try:
                    with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read().strip()
                finally:
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
            else:
                raise ValueError(f"Unsupported engine: {self.engine}")
        finally:
            try:
                os.remove(tmp_img)
            except OSError:
                pass

        return text

# ...existing code...

class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EmTechScan – External OCR (gocr / cuneiform)")
        # Use external OCR wrapper
        self.ocr = ExternalOCREngine(engine='gocr', language='eng')
        self.image_path = None
        self.tk_img = None
        self.result_text = ""
        self.setup_ui()

    # --- UI ---
    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="EmTechScan OCR (gocr / cuneiform)", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=8)
        self.canvas = tk.Canvas(frm, width=480, height=360, bg="gray20")
        self.canvas.grid(row=1, column=0, columnspan=4, pady=5)

        ttk.Button(frm, text="(No Training Required) Select Folder (optional)", command=self.select_training).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(frm, text="Select Image/PDF", command=self.select_image).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Button(frm, text="Run OCR", command=self.run_ocr).grid(row=2, column=2, sticky="ew", pady=4)
        ttk.Button(frm, text="Train (N/A)", command=self.train_ml).grid(row=2, column=3, sticky="ew", pady=4)

        ttk.Label(frm, text="Recognition Mode:").grid(row=3, column=0, sticky="w", pady=3)
        self.mode_var = tk.StringVar(value="Engine")
        mode_menu = ttk.Combobox(frm, textvariable=self.mode_var,
                         values=["Engine"], state="readonly")
        mode_menu.grid(row=3, column=1, sticky="ew", pady=3)

        ttk.Label(frm, text="Engine:").grid(row=3, column=2, sticky="w", pady=3)
        self.engine_var = tk.StringVar(value="gocr")
        engine_menu = ttk.Combobox(frm, textvariable=self.engine_var,
                                   values=["gocr", "cuneiform"], state="readonly")
        engine_menu.grid(row=3, column=3, sticky="ew", pady=3)

        ttk.Label(frm, text="Language (cuneiform):").grid(row=4, column=0, sticky="w", pady=3)
        self.lang_var = tk.StringVar(value="eng")
        lang_entry = ttk.Entry(frm, textvariable=self.lang_var)
        lang_entry.grid(row=4, column=1, sticky="ew", pady=3, columnspan=1)

        ttk.Button(frm, text="Save Output", command=self.save_output).grid(row=4, column=2, columnspan=2, sticky="ew", pady=5)

        self.status = ttk.Label(frm, text="Status: Ready")
        self.status.grid(row=5, column=0, columnspan=4, sticky="w", pady=3)

        self.text_box = tk.Text(frm, wrap="word", width=70, height=12)
        self.text_box.grid(row=6, column=0, columnspan=4, pady=5)

        frm.columnconfigure((0, 1, 2, 3), weight=1)

    def select_training(self):
        # External engines do not require training; keep option for compatibility
        messagebox.showinfo("No training", "gocr and cuneiform are pre-built OCR engines and do not require training here. Choose engine from the UI.")

    def select_image(self):
        path = filedialog.askopenfilename(
            title="Select Image or PDF",
            filetypes=[("Supported files", "*.png *.jpg *.jpeg *.bmp *.pdf")]
        )
        if not path:
            return
        self.image_path = path
        if path.lower().endswith(".pdf"):
            pages = convert_from_path(path)
            temp = "page_temp.png"
            pages[0].save(temp, "PNG")
            path = temp
            self.image_path = path
        self.show_preview(path)
        self.status.config(text=f"Loaded: {os.path.basename(path)}")

    def show_preview(self, path):
        img = Image.open(path)
        img.thumbnail((480, 360))
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

    def train_ml(self):
        # Not applicable for external engines
        messagebox.showinfo("Not applicable", "Training is not applicable for external engines (gocr / cuneiform).")

    def run_ocr(self):
        if not self.image_path:
            messagebox.showwarning("No image", "Please select an image or PDF first.")
            return

        selected_engine = self.engine_var.get()
        selected_lang = self.lang_var.get().strip() or "eng"
        self.ocr.engine = selected_engine
        self.ocr.language = selected_lang

        try:
            if not self.ocr.engine_available():
                messagebox.showerror("Engine not found", f"Selected engine '{selected_engine}' not found in PATH. Install it (e.g., sudo apt install gocr cuneiform) or choose another engine.")
                return

            self.status.config(text=f"Running OCR with {selected_engine}...")
            self.root.update()

            result = self.ocr.recognize(self.image_path)
            self.result_text = result
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert("1.0", result)
            self.status.config(text=f"OCR complete ({selected_engine}). {len(result)} characters recognized.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_output(self):
        if not self.result_text.strip():
            messagebox.showwarning("No text", "Please run OCR before saving.")
            return

        filetypes = [("Word Document", "*.docx"), ("Text File", "*.txt")]
        save_path = filedialog.asksaveasfilename(
            title="Save OCR Output",
            defaultextension=".docx",
            filetypes=filetypes
        )
        if not save_path:
            return

        try:
            if save_path.endswith(".docx"):
                doc = Document()
                doc.add_paragraph(self.result_text)
                doc.save(save_path)
            else:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.result_text)

            self.status.config(text=f"Saved output: {os.path.basename(save_path)}")
            messagebox.showinfo("Saved", f"OCR output saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

def main():
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
# ...existing code...