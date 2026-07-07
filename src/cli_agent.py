import sys
import time
import logging
from glob import glob
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.box import ROUNDED

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
        self.console = Console()
        self.input_pdf = None
        self.output_pdf = None
        self.pages = []
        self.translated_pages = []
        self.running = False

    def _banner(self):
        panel = Panel(
            "[bold bright_magenta]Bengali PDF Translator[/]\n[italic cyan]by Fahim Ahmed[/]",
            title="[bold bright_magenta]SAHITTIK[/]",
            subtitle="[cyan]sahittik[/cyan]",
            box=ROUNDED,
            border_style="bright_cyan",
            padding=(1, 4),
        )
        self.console.print(panel)

    def _list_pdfs(self):
        pdfs = sorted(glob("*.pdf") + glob("input/*.pdf"))
        pdfs = [f for f in pdfs if config.OUTPUT_SUFFIX not in f]
        if not pdfs:
            self.console.print("[yellow]No PDF files found.[/]")
            return pdfs
        table = Table(
            title="[bold yellow]Available PDFs[/]",
            box=ROUNDED,
            header_style="bold cyan",
            border_style="cyan",
        )
        table.add_column("[dim]#[/]", style="dim", width=4)
        table.add_column("Filename", style="white")
        for i, f in enumerate(pdfs, 1):
            table.add_row(str(i), f)
        self.console.print(table)
        return pdfs

    def _select_pdf(self, arg):
        pdfs = sorted(glob("*.pdf") + glob("input/*.pdf"))
        pdfs = [f for f in pdfs if config.OUTPUT_SUFFIX not in f]
        if not pdfs:
            self.console.print("[yellow]No PDF files found.[/]")
            return
        try:
            idx = int(arg) - 1
            if 0 <= idx < len(pdfs):
                self.input_pdf = pdfs[idx]
                stem = Path(self.input_pdf).stem
                self.output_pdf = f"output/{stem}{config.OUTPUT_SUFFIX}.pdf"
                self.console.print(f"[green]>[/] Selected: [bold white]{self.input_pdf}[/]")
                self.console.print(f"  Output:   [cyan]{self.output_pdf}[/]")
            else:
                self.console.print(f"[red]x[/] Invalid number. Choose [bold]1[/]–[bold]{len(pdfs)}[/]")
        except ValueError:
            self.console.print("[red]x[/] Enter a number.")

    def _show_model(self, arg=None):
        if arg:
            config.MODEL = arg
            self.console.print(f"[green]>[/] Model set to: [bold white]{config.MODEL}[/]")
        else:
            self.console.print(f"[cyan]Model:[/] [bold white]{config.MODEL}[/]")

    def _show_progress(self):
        p = prog.load_progress()
        if not p:
            self.console.print("[yellow]No progress data.[/]")
            return
        done = len(p["completed_pages"])
        failed = len(p["failed_pages"])
        total = p["total_pages"]
        table = Table(box=ROUNDED, border_style="cyan", show_header=False)
        table.add_column("", style="cyan", width=14)
        table.add_column("", style="bold white")
        table.add_row("[cyan]Input[/]", p["input_pdf"])
        table.add_row("[cyan]Pages[/]", f"{done}/{total} done, {failed} failed")
        self.console.print(table)

    def _show_status(self):
        api_key = config.OPENROUTER_API_KEY
        masked = f"{api_key[:8]}..." if api_key else "[red]NOT SET[/]"
        table = Table(
            box=ROUNDED,
            border_style="cyan",
            show_header=False,
            title="[bold yellow]* System Status[/]",
            title_justify="left",
        )
        table.add_column("Setting", style="cyan", width=16)
        table.add_column("Value", style="bold white")
        table.add_row("Input PDF", self.input_pdf or "[dim](not selected)[/]")
        table.add_row("Output PDF", self.output_pdf or "[dim](not selected)[/]")
        table.add_row("Model", config.MODEL)
        table.add_row("Max tokens", str(config.MAX_TOKENS))
        table.add_row("API key", masked)
        self.console.print(table)

    def _clear_cache(self):
        import os
        path = "cache/translations.json"
        if os.path.exists(path):
            os.remove(path)
            self.console.print("[green]>[/] Cache cleared.")
        else:
            self.console.print("[yellow]No cache to clear.[/]")

    def _show_help(self):
        nav = Table(box=ROUNDED, border_style="bright_blue", show_header=False, padding=(0, 2))
        nav.add_column(style="bold green", width=20)
        nav.add_column(style="white")
        nav.add_row("/list", "Show available PDFs")
        nav.add_row("/select [i]n[/i]", "Choose a PDF by number")

        tr = Table(box=ROUNDED, border_style="bright_blue", show_header=False, padding=(0, 2))
        tr.add_column(style="bold green", width=20)
        tr.add_column(style="white")
        tr.add_row("/start", "Begin or resume translation")
        tr.add_row("/pause", "Pause after current page")
        tr.add_row("/progress", "Show page progress")

        sysc = Table(box=ROUNDED, border_style="bright_blue", show_header=False, padding=(0, 2))
        sysc.add_column(style="bold green", width=20)
        sysc.add_column(style="white")
        sysc.add_row("/model [i]name[/i]", "Show or switch model")
        sysc.add_row("/status", "Show all settings")
        sysc.add_row("/cache clear", "Clear translation cache")
        sysc.add_row("/help", "Show this help")
        sysc.add_row("/quit", "Exit")

        self.console.print()
        self.console.print(Panel(
            "[bold yellow]NAVIGATION[/]", box=ROUNDED, border_style="bright_blue", padding=(0, 1)
        ))
        self.console.print(nav)
        self.console.print(Panel(
            "[bold yellow]TRANSLATION[/]", box=ROUNDED, border_style="bright_blue", padding=(0, 1)
        ))
        self.console.print(tr)
        self.console.print(Panel(
            "[bold yellow]SYSTEM[/]", box=ROUNDED, border_style="bright_blue", padding=(0, 1)
        ))
        self.console.print(sysc)

    def _start_translation(self):
        global STOP_FLAG, PAUSED
        STOP_FLAG = False
        PAUSED = False

        if not self.input_pdf:
            self.console.print("[red]x[/] No PDF selected. Use [bold]/select <n>[/] first.")
            return

        if not config.OPENROUTER_API_KEY:
            self.console.print("[red]x[/] API key not found in [cyan].env[/]")
            return

        self.running = True

        p = prog.load_progress()
        if p and p.get("input_pdf") == self.input_pdf:
            self.console.print(f"[blue]i[/] Resuming previous run ([bold]{len(p['completed_pages'])}[/] pages done)")
        else:
            pages = extract_pages(self.input_pdf)
            self.pages = pages
            prog.init_progress(self.input_pdf, len(pages))
            self.translated_pages = []
            self.console.print(f"[blue]i[/] [bold]{len(pages)}[/] pages found")

        self.pages = extract_pages(self.input_pdf)
        self.translated_pages = []
        prog.init_progress(self.input_pdf, len(self.pages))

        start = time.time()
        total = len(self.pages)
        BATCH_SIZE = 10
        last_batch_end = 0
        stem = Path(self.input_pdf).stem

        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("[cyan]Starting...", total=total)

            for page in self.pages:
                if STOP_FLAG:
                    PAUSED = True
                    self.console.print("\n[yellow]||  Paused.[/]")
                    break

                pn = page["page_no"]
                text = page["text"]
                total_chars = len(text)
                scanned = page["is_scanned"]

                progress.update(task, description=f"[cyan]Page {pn}/{total}[/]")

                if scanned:
                    progress.update(task, description=f"[cyan]Page {pn}/{total}  •  running OCR...[/]")
                    text = ocr_page(page["_fitz_page"])
                    if not text or text.startswith("["):
                        self.console.log(f"[yellow]! Page {pn}[/] OCR failed: {text}")
                        prog.mark_failed(pn)
                        self.translated_pages.append({"page_no": pn, "text": ""})
                        progress.update(task, advance=1)
                        continue

                if not text.strip():
                    self.console.log(f"[blue]i Page {pn}[/] [dim](empty, skipped)[/]")
                    self.translated_pages.append({"page_no": pn, "text": ""})
                    prog.mark_complete(pn)
                    progress.update(task, advance=1)
                    continue

                chunks = chunk_text(text)

                bengali_chunks = []
                for chunk in chunks:
                    if STOP_FLAG:
                        break
                    original_en = chunk["text"]

                    progress.update(task, description=f"[cyan]Page {pn}/{total}  •  translating...[/]")
                    step1 = translate_chunk(original_en)
                    if not step1:
                        self.console.log(f"[red]x Page {pn}[/] faithful translation failed")
                        bengali_chunks.append("[Translation failed]")
                        continue

                    progress.update(task, description=f"[cyan]Page {pn}/{total}  •  literary editing...[/]")
                    step2 = literary_edit(step1, original_en)
                    if not step2:
                        self.console.log(f"[yellow]! Page {pn}[/] edit failed, using faithful")
                        step2 = step1

                    progress.update(task, description=f"[cyan]Page {pn}/{total}  •  quality check...[/]")
                    step3 = quality_check(original_en, step1, step2)
                    if not step3:
                        self.console.log(f"[yellow]! Page {pn}[/] quality check failed, using edited")
                        step3 = step2

                    bengali_chunks.append(step3)

                if STOP_FLAG:
                    break

                full_bengali = "\n\n".join(bengali_chunks)
                self.translated_pages.append({"page_no": pn, "text": full_bengali})
                prog.mark_complete(pn)
                progress.update(task, advance=1)
                self.console.log(
                    f"[green]>[/] Page {pn}/{total}  "
                    f"[dim]({total_chars} chars, {len(chunks)} chunk(s))[/]"
                )

                done_count = len(self.translated_pages)
                if done_count % BATCH_SIZE == 0:
                    batch_start = last_batch_end + 1
                    batch_end = done_count
                    batch_pdf = f"output/{stem}_{batch_start:03d}-{batch_end:03d}.pdf"
                    batch_pages = self.translated_pages[-BATCH_SIZE:]
                    self.console.log(f"[cyan]Generating batch PDF {batch_start:03d}-{batch_end:03d}...[/]")
                    create_bengali_pdf(batch_pages, batch_pdf, config.FONT_PATH)
                    self.console.log(f"[green]>[/] Saved [bold white]{batch_pdf}[/]")
                    last_batch_end = batch_end

        elapsed = time.time() - start

        if not STOP_FLAG:
            self.console.print(f"\n[bold green]> Translation complete in {elapsed:.1f}s[/]")
            remaining = self.translated_pages[last_batch_end:]
            if remaining:
                batch_start = last_batch_end + 1
                batch_end = len(self.translated_pages)
                batch_pdf = f"output/{stem}_{batch_start:03d}-{batch_end:03d}.pdf"
                self.console.print("[cyan]Generating final batch PDF...[/]")
                create_bengali_pdf(remaining, batch_pdf, config.FONT_PATH)
                self.console.print(f"[green]>[/] Saved [bold white]{batch_pdf}[/]")
            self.console.print("[cyan]Generating full PDF...[/]")
            create_bengali_pdf(self.translated_pages, self.output_pdf, config.FONT_PATH)
            self.console.print(f"[green]>[/] Saved [bold white]{self.output_pdf}[/]")
        else:
            done = len(self.translated_pages)
            self.console.print(f"\n[bold yellow]||  Paused at {done}/{total} pages[/]")
            remaining = self.translated_pages[last_batch_end:]
            if remaining:
                batch_start = last_batch_end + 1
                batch_end = done
                batch_pdf = f"output/{stem}_{batch_start:03d}-{batch_end:03d}.pdf"
                self.console.print("[cyan]Generating partial batch PDF before pause...[/]")
                create_bengali_pdf(remaining, batch_pdf, config.FONT_PATH)
                self.console.print(f"[green]>[/] Saved [bold white]{batch_pdf}[/]")

        self.running = False

    def run(self):
        global STOP_FLAG
        self.console.clear()
        self._banner()

        pdfs = self._list_pdfs()
        if pdfs:
            self.console.print()

        while True:
            try:
                line = Prompt.ask("[bold cyan]sahittik[/bold cyan]").strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                if self.running:
                    STOP_FLAG = True
                    self.console.print("[yellow]Stopping after current page...[/]")
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
                    self.console.print("[yellow]Stopping...[/]")
                    time.sleep(1)
                self.console.print("[dim]Bye![/]")
                break

            elif cmd == "/help":
                self._show_help()

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
                    self.console.print("[yellow]Stopping after current page...[/]")
                else:
                    self.console.print("[yellow]No translation running.[/]")

            elif cmd == "/progress":
                self._show_progress()

            elif cmd == "/status":
                self._show_status()

            elif cmd == "/cache" and arg == "clear":
                self._clear_cache()

            else:
                self.console.print(f"[red]x[/] Unknown: [bold]{cmd}[/]. Type [bold]/help[/]")
