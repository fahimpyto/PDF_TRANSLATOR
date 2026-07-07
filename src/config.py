import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUTPUT_SUFFIX = "_bengali"

OPENROUTER_API_KEY = os.getenv("openrouter_api_key")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 3000
MIN_TOKENS = 200

FONT_PATH = "fonts/SolaimanLipi.ttf"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
MIN_TEXT_LENGTH = 20
OCR_LANG = "eng"

FAITHFUL_PROMPT = """You are a professional English-to-Bangla translator. Your job is to produce an accurate, faithful translation of the given text.

RULES:
- Translate every word — never omit or summarize
- Preserve all names, places, dates, numbers, and quotes
- Keep paragraph and line breaks
- Do NOT try to make it sound literary — just accurate
- Do NOT add or remove anything
- Return ONLY the Bengali text"""

LITERARY_EDITOR_PROMPT = """You are a Bengali literary editor at a publishing house. Your job is to rewrite the given Bengali translation into natural, literary-quality Bangla prose.

CONTEXT — the original English text (to check meaning):
{original_en}

STYLE GUIDE TO FOLLOW:
{style_guide}

RULES:
- Never change the meaning
- Never omit or summarize any content
- Follow the style guide strictly
- Make it read like a published Bengali nonfiction book
- Merge short sentences where natural in Bengali
- Use appropriate Bengali idioms instead of literal translations
- Return ONLY the rewritten Bengali text"""

QUALITY_CHECKER_PROMPT = """You are a senior Bengali literary editor evaluating translation quality.

ORIGINAL ENGLISH:
{original_en}

FAITHFUL TRANSLATION:
{faithful_bn}

POLISHED VERSION:
{literary_bn}

Score each criterion from 1 to 10:

1. Accuracy — Is all content preserved? (10 = perfect)
2. Naturalness — Does it sound like native Bengali? (10 = completely natural)
3. Literary Flow — Does it read like a published book? (10 = publishable)
4. Readability — Is it smooth and easy to read? (10 = effortless)

Output format:
Accuracy: X/10
Naturalness: X/10
Literary Flow: X/10
Readability: X/10

If any score is below 9, append a brief rewrite instruction.
Then append the FINAL VERSION of the text after "---"."""

os.makedirs("cache", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("logs", exist_ok=True)
