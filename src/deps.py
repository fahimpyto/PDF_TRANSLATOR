import os
import subprocess
import pytesseract

TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _find_tesseract():
    for p in TESSERACT_PATHS:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return p
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True)
        return "tesseract"
    except FileNotFoundError:
        return None


def check_tesseract():
    path = _find_tesseract()
    if path:
        return True
    return False


def check_tesseract_langs(lang="eng"):
    if not check_tesseract():
        return False, [lang]
    result = subprocess.run(
        [pytesseract.pytesseract.tesseract_cmd, "--list-langs"],
        capture_output=True, text=True,
    )
    available = set()
    for line in result.stderr.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("List"):
            available.add(line)
    requested = set(lang.split("+"))
    missing = [l for l in requested if l not in available]
    return len(missing) == 0, missing
