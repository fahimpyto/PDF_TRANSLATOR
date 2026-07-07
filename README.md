# PDF Translator

English → Bengali literary PDF translation agent powered by OpenRouter LLMs.

## Features

- Page-by-page translation with 3-step quality pipeline
  - **Faithful Translation** — accurate, no omissions
  - **Literary Editing** — style-guide-driven natural Bengali prose
  - **Quality Check** — scores accuracy/naturalness/flow/readability
- OCR fallback for scanned PDFs (Tesseract)
- Resume/pause — stop mid-translation and continue later
- Translation cache — avoids re-translating identical content
- Interactive CLI agent with command control

## Setup

1. **Clone and install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up OpenRouter API key**
```bash
cp .env.example .env
# Edit .env with your key from https://openrouter.ai/keys
```

3. **Download Bengali font**
```bash
python setup_font.py
```

4. **Place your PDFs** in the project folder or `input/`

5. **Run the agent**
```bash
python main.py
```

## Usage

```
agent> /list              Show available PDFs
agent> /select 1          Choose a PDF
agent> /model             Show current model
agent> /model <name>      Switch model
agent> /start             Begin or resume translation
agent> /pause             Pause after current page
agent> /progress          Show page progress
agent> /status            Show all settings
agent> /help              Show all commands
agent> /quit              Exit
```

## Architecture

```
PDF → extract pages → detect scanned → (OCR if needed)
   → chunk paragraphs → [Faithful → Literary Edit → Quality Check]
   → generate PDF
```

## Folder Structure

```
pdf-translator/
├── src/
│   ├── __init__.py
│   ├── config.py         Settings & prompts
│   ├── cli_agent.py      Interactive CLI agent
│   ├── pdf_reader.py     Text extraction
│   ├── ocr.py            Tesseract OCR
│   ├── chunker.py        Paragraph chunking
│   ├── translator.py     Faithful LLM translation
│   ├── editor.py         Literary style editing
│   ├── quality.py        Quality scoring & rewrite
│   ├── pdf_writer.py     PDF generation (PyMuPDF)
│   └── progress.py       Resume tracker
├── references/
│   └── style.md          Bengali literary style guide
├── input/                Place PDFs here
├── output/               Generated Bengali PDFs
├── fonts/                SolaimanLipi.ttf
├── main.py               Entry point
├── setup_font.py         Font downloader
├── requirements.txt
└── .env                  API key (not tracked)
```

## Credits

Requires an [OpenRouter](https://openrouter.ai/) API key with at least a small credit balance for `openai/gpt-4o-mini`.
