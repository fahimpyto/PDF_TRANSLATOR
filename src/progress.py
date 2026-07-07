import json
import os

PROGRESS_PATH = "progress.json"


def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return None
    try:
        with open(PROGRESS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return None


def save_progress(progress):
    with open(PROGRESS_PATH, "w") as f:
        json.dump(progress, f, indent=2)


def init_progress(input_pdf, total_pages):
    p = {
        "input_pdf": input_pdf,
        "total_pages": total_pages,
        "completed_pages": [],
        "failed_pages": [],
    }
    save_progress(p)
    return p


def mark_complete(page_no):
    p = load_progress()
    if p is None:
        return
    if page_no not in p["completed_pages"]:
        p["completed_pages"].append(page_no)
    p["failed_pages"] = [f for f in p["failed_pages"] if f != page_no]
    save_progress(p)


def mark_failed(page_no):
    p = load_progress()
    if p is None:
        return
    if page_no not in p["failed_pages"]:
        p["failed_pages"].append(page_no)
    save_progress(p)


def is_complete(page_no):
    p = load_progress()
    if p is None:
        return False
    return page_no in p["completed_pages"]


def is_failed(page_no):
    p = load_progress()
    if p is None:
        return False
    return page_no in p["failed_pages"]
