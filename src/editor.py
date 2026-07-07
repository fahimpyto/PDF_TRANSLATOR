import json
import hashlib
import logging
from src import config
from src.translator import _call_llm, _load_cache, _save_cache

logger = logging.getLogger(__name__)

STYLE_GUIDE_PATH = "references/style.md"


def _load_style_guide():
    try:
        with open(STYLE_GUIDE_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("style guide not found at %s", STYLE_GUIDE_PATH)
        return ""


def _text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def literary_edit(faithful_bn, original_en):
    if not faithful_bn or not faithful_bn.strip():
        return faithful_bn

    cache = _load_cache()
    key = _text_hash(faithful_bn)
    cache_key = f"literary:{key}"

    if cache_key in cache:
        logger.info("  literary edit cached")
        return cache[cache_key]

    style_guide = _load_style_guide()
    user_message = config.LITERARY_EDITOR_PROMPT.format(
        original_en=original_en,
        style_guide=style_guide,
    ) + f"\n\nTEXT TO EDIT:\n{faithful_bn}"

    logger.info("  literary editing...")
    result = _call_llm(
        "You are a Bengali literary editor. Follow the style guide and rewrite the text.",
        user_message,
    )
    if result:
        cache[cache_key] = result
        _save_cache(cache)
        return result

    logger.warning("literary edit FAILED, using faithful translation")
    return faithful_bn
