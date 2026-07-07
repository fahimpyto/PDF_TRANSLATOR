import re
import fitz
from src import config


def extract_pages(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for page_no in range(len(doc)):
        page = doc.load_page(page_no)
        raw_text = page.get_text()
        text = clean_text(raw_text)
        is_scanned = len(text.strip()) < config.MIN_TEXT_LENGTH
        pages.append({
            "page_no": page_no + 1,
            "text": text,
            "is_scanned": is_scanned,
            "_fitz_page": page if is_scanned else None,
        })
    doc.close()
    return pages


def clean_text(text):
    text = text.replace("\r", "")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +", " ", text)
    text = text.strip()
    return text
