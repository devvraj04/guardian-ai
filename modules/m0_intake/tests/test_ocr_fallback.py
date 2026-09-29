import fitz
from PIL import Image, ImageDraw
import io
from modules.m0_intake.extraction import extract_raw_text_from_pdf


def generate_scanned_image_pdf() -> bytes:
    """
    Generates a PDF where the content is a pure raster image (no selectable text),
    simulating a scanned loan document.
    """
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 50), "LOAN AGREEMENT SUMMARY", fill=(0, 0, 0))
    draw.text((30, 100), "Principal Amount: 75000", fill=(0, 0, 0))
    draw.text((30, 150), "Interest Rate: 12.0%", fill=(0, 0, 0))
    draw.text((30, 200), "Tenure: 18 Months", fill=(0, 0, 0))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    doc = fitz.open()
    page = doc.new_page(width=600, height=300)
    page.insert_image(page.rect, stream=img_bytes.getvalue())
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_paddleocr_triggers_on_scanned_pdf():
    scanned_pdf_bytes = generate_scanned_image_pdf()

    # Verify that pdfplumber/fitz alone finds 0 text on this image PDF
    doc = fitz.open(stream=scanned_pdf_bytes, filetype="pdf")
    assert doc[0].get_text().strip() == ""
    doc.close()

    # Now verify that our dual-path extractor triggers PaddleOCR fallback
    extracted_text, method = extract_raw_text_from_pdf(scanned_pdf_bytes)

    assert method == "paddleocr"
    assert "75000" in extracted_text or "LOAN" in extracted_text.upper()
