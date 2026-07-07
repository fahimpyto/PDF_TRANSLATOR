import json
import hashlib
import logging
from src import config
from src.translator import _call_llm, _load_cache, _save_cache

logger = logging.getLogger(__name__)


def _text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def quality_check(original_en, faithful_bn, literary_bn):
    if not literary_bn or not literary_bn.strip():
        return literary_bn

    cache = _load_cache()
    key = _text_hash(original_en + "|||" + literary_bn)
    cache_key = f"quality:{key}"

    if cache_key in cache:
        logger.info("  quality check cached")
        return cache[cache_key]

    user_message = config.QUALITY_CHECKER_PROMPT.format(
        original_en=original_en,
        faithful_bn=faithful_bn,
        literary_bn=literary_bn,
    )

    logger.info("  quality check...")
    result = _call_llm(
        "You are a senior Bengali literary editor evaluating translation quality.",
        user_message,
    )

    if not result:
        logger.warning("quality check FAILED, using literary version")
        return literary_bn

    final = _extract_final(result, literary_bn)
    cache[cache_key] = final
    _save_cache(cache)
    return final


def _extract_final(result, fallback):
    lines = result.strip().split("\n")
    after_sep = False
    final_lines = []
    for line in lines:
        if line.strip().startswith("---"):
            after_sep = True
            continue
        if after_sep:
            final_lines.append(line)
    if final_lines:
        text = "\n".join(final_lines).strip()
        if text:
            return text
    if "FINAL VERSION:" in result:
        text = result.split("FINAL VERSION:")[-1].strip()
        if text:
            return text
    return fallback
