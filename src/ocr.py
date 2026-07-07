from PIL import Image
import pytesseract
from src import deps, config


def ocr_page(page):
    if not deps.check_tesseract():
        return "[Tesseract not found]"

    ok, missing = deps.check_tesseract_langs(config.OCR_LANG)
    if not ok:
        return f"[Missing Tesseract language pack(s): {', '.join(missing)}]"

    pixmap = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    text = pytesseract.image_to_string(img, lang=config.OCR_LANG)
    return text.strip()
