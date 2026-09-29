import io
import os
import numpy as np
import fitz  # PyMuPDF
from PIL import Image
from typing import List
from app.core.logging import logger

# Disable oneDNN and PIR instruction attribute conflict on Windows
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

_paddle_ocr_engine = None


def get_ocr_engine():
    """
    Lazy initializes the PaddleOCR engine with Windows-compatible oneDNN settings.
    """
    global _paddle_ocr_engine
    if _paddle_ocr_engine is None:
        try:
            from paddleocr import PaddleOCR

            _paddle_ocr_engine = PaddleOCR(
                use_textline_orientation=True,
                lang="en",
                enable_mkldnn=False,
            )
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            raise RuntimeError(f"PaddleOCR engine unavailable: {e}")
    return _paddle_ocr_engine


def extract_text_via_ocr(pdf_bytes: bytes) -> str:
    """
    Fallback OCR extractor for scanned or non-machine-readable PDFs (GUARDIAN SPEC §2, §3.4).
    Converts PDF pages to RGB numpy arrays and runs PaddleOCR.
    """
    ocr = get_ocr_engine()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_text_lines: List[str] = []

    page_count = len(doc)
    try:
        for page_idx in range(page_count):
            page = doc[page_idx]
            # Render page at 200 DPI for high-accuracy OCR
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            img_np = np.array(img)

            # Perform OCR on page image
            predict_results = list(ocr.predict(img_np))
            for res in predict_results:
                if isinstance(res, dict):
                    rec_texts = res.get("rec_texts", [])
                    all_text_lines.extend([str(t) for t in rec_texts])
                elif isinstance(res, list):
                    for line in res:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            all_text_lines.append(str(line[1][0]))
    finally:
        doc.close()

    full_text = "\n".join(all_text_lines)
    logger.info(
        f"PaddleOCR fallback extracted {len(all_text_lines)} lines across {page_count} pages."
    )
    return full_text
