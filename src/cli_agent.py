import sys
import time
import logging
import threading
from glob import glob
from pathlib import Path

from src import config
from src.pdf_reader import extract_pages
from src.ocr import ocr_page
from src.chunker import chunk_text
from src.translator import translate_chunk
from src.editor import literary_edit
from src.quality import quality_check
from src.pdf_writer import create_bengali_pdf
from src import progress as prog

logger = logging.getLogger(__name__)

STOP_FLAG = False
PAUSED = False


class AgentCLI:
    def __init__(self):
        self.input_pdf = None
        self.output_pdf = None
        self.pages = []
        self.translated_pages = []
        self.running = False

    def _list_pdfs(self):
        pdfs = sorted(glob("*.pdf") + glob("input/*.pdf"))
        pdfs = [f for f in pdfs if config.OUTPUT_SUFFIX not in f]
        if not pdfs:
            print("  No PDF files found.")
        else:
            for i, f in enumerate(pdfs, 1):
                print(f"  [{i}] {f}")
        return pdfs

    def _select_pdf(self, arg):
        pdfs = sorted(glob("*.pdf") + glob("input/*.pdf"))
        pdfs = [f for f in pdfs if config.OUTPUT_SUFFIX not in f]
        if not pdfs:
            print("  No PDF files found.")
            return
        try:
            idx = int(arg) - 1
            if 0 <= idx < len(pdfs):
                self.input_pdf = pdfs[idx]
                stem = Path(self.input_pdf).stem
                self.output_pdf = f"output/{stem}{config.OUTPUT_SUFFIX}.pdf"
                print(f"  Selected: {self.input_pdf}")
                print(f"  Output:   {self.output_pdf}")
            else:
                print(f"  Invalid number. Choose 1-{len(pdfs)}")
        except ValueError:
            print("  Enter a number.")

    def _show_model(self, arg=None):
        if arg:
            config.MODEL = arg
            print(f"  Model set to: {config.MODEL}")
        else:
            print(f"  Current model: {config.MODEL}")

    def _show_progress(self):
        p = prog.load_progress()
        if not p:
            print("  No progress data.")
            return
        done = len(p["completed_pages"])
        failed = len(p["failed_pages"])
        total = p["total_pages"]
        print(f"  Pages: {done}/{total} done, {failed} failed")
        print(f"  Input: {p['input_pdf']}")

    def _show_status(self):
        print(f"  Input PDF:  {self.input_pdf or '(not selected)'}")
        print(f"  Output PDF: {self.output_pdf or '(not selected)'}")
        print(f"  Model:      {config.MODEL}")
        print(f"  Max tokens: {config.MAX_TOKENS}")
        api_key = config.OPENROUTER_API_KEY
        masked = api_key[:8] + "..." if api_key else "NOT SET"
        print(f"  API key:    {masked}")

    def _clear_cache(self):
        import os
        path = "cache/translations.json"
        if os.path.exists(path):
            os.remove(path)
            print("  Cache cleared.")
        else:
            print("  No cache to clear.")

    def _start_translation(self):
        global STOP_FLAG, PAUSED
        STOP_FLAG = False
        PAUSED = False

        if not self.input_pdf:
            print("  No PDF selected. Use /select <n> first.")
            return

        if not config.OPENROUTER_API_KEY:
            print("  API key not found in .env")
            return

        self.running = True

        p = prog.load_progress()
        if p and p.get("input_pdf") == self.input_pdf:
            print(f"  Resuming previous run ({len(p['completed_pages'])} pages done)")
        else:
            pages = extract_pages(self.input_pdf)
            self.pages = pages
            prog.init_progress(self.input_pdf, len(pages))
            self.translated_pages = []
            print(f"  {len(pages)} page(s) found")

        self.pages = extract_pages(self.input_pdf)
        self.translated_pages = []
        prog.init_progress(self.input_pdf, len(self.pages))

        start = time.time()

        for p in self.pages:
            if STOP_FLAG:
                PAUSED = True
                print("\n  Paused.")
                break

            pn = p["page_no"]
            text = p["text"]

            logger.info("[Page %d/%d] (%d chars)%s",
                         pn, len(self.pages), len(text),
                         " [SCANNED]" if p["is_scanned"] else "")

            if p["is_scanned"]:
                logger.info("  running OCR...")
                text = ocr_page(p["_fitz_page"])
                if not text or text.startswith("["):
                    logger.warning("  OCR failed: %s", text)
                    prog.mark_failed(pn)
                    self.translated_pages.append({"page_no": pn, "text": ""})
                    continue
                logger.info("  OCR returned %d chars", len(text))

            if not text.strip():
                logger.info("  (empty, skipping)")
                self.translated_pages.append({"page_no": pn, "text": ""})
                prog.mark_complete(pn)
                continue

            chunks = chunk_text(text)
            logger.info("  %d chunk(s)", len(chunks))

            bengali_chunks = []
            for chunk in chunks:
                if STOP_FLAG:
                    break
                original_en = chunk["text"]

                step1 = translate_chunk(original_en)
                if not step1:
                    logger.warning("  chunk %d: faithful translation FAILED", chunk["idx"])
                    bengali_chunks.append("[Translation failed]")
                    continue

                step2 = literary_edit(step1, original_en)
                step3 = quality_check(original_en, step1, step2)
                bengali_chunks.append(step3)

            if STOP_FLAG:
                break

            full_bengali = "\n\n".join(bengali_chunks)
            self.translated_pages.append({"page_no": pn, "text": full_bengali})
            prog.mark_complete(pn)
            logger.info("  -- Progress: %d/%d pages done --", len(self.translated_pages), len(self.pages))

        elapsed = time.time() - start

        if not STOP_FLAG:
            logger.info("Translation complete in %.1fs", elapsed)
            logger.info("Generating PDF...")
            create_bengali_pdf(self.translated_pages, self.output_pdf, config.FONT_PATH)
            logger.info("Done! Saved to %s", self.output_pdf)

        self.running = False

    def run(self):
        global STOP_FLAG

        print()
        print("  ==========================================")
        print("     PDF Bengali Translation Agent")
        print("  ==========================================")
        print()
        print("  Type /help for commands")
        print()

        pdfs = self._list_pdfs()
        if pdfs:
            print()

        while True:
            try:
                line = input("agent> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                if self.running:
                    STOP_FLAG = True
                    print("  Stopping after current page...")
                    continue
                break

            if not line:
                continue

            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit"):
                if self.running:
                    STOP_FLAG = True
                    print("  Stopping...")
                    time.sleep(1)
                print("  Bye!")
                break

            elif cmd == "/help":
                print("""
  Commands:
    /list              Show available PDFs
    /select <n>        Choose a PDF by number
    /model             Show current model
    /model <name>      Switch model (e.g. /model openai/gpt-4o-mini)
    /start             Begin or resume translation
    /pause             Pause after current page
    /progress          Show page progress
    /status            Show all settings
    /cache clear       Clear translation cache
    /help              Show this help
    /quit              Exit
""")

            elif cmd == "/list":
                self._list_pdfs()

            elif cmd == "/select":
                self._select_pdf(arg)

            elif cmd == "/model":
                self._show_model(arg)

            elif cmd == "/start":
                self._start_translation()

            elif cmd in ("/pause", "/stop"):
                if self.running:
                    STOP_FLAG = True
                    print("  Stopping after current page...")
                else:
                    print("  No translation running.")

            elif cmd == "/progress":
                self._show_progress()

            elif cmd == "/status":
                self._show_status()

            elif cmd == "/cache" and arg == "clear":
                self._clear_cache()

            else:
                print(f"  Unknown: {cmd}. Type /help")
