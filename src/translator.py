import json
import hashlib
import re
import time
import logging
from src import config
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

client = OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
    max_retries=0,
    default_headers={
        "HTTP-Referer": "https://github.com/mini-agent",
        "X-Title": "pdf-translator",
    },
)

CACHE_PATH = "cache/translations.json"

_last_call_time = 0.0
_RATE_LIMIT_UNTIL = 0.0


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _pace_calls():
    global _last_call_time, _RATE_LIMIT_UNTIL
    now = time.time()
    if now < _RATE_LIMIT_UNTIL:
        time.sleep(_RATE_LIMIT_UNTIL - now)
    elapsed = now - _last_call_time
    if elapsed < 6.0 and _last_call_time > 0:
        time.sleep(6.0 - elapsed)
    _last_call_time = time.time()


def _call_llm(system_prompt, user_message):
    global _RATE_LIMIT_UNTIL
    for attempt in range(1, 6):
        _pace_calls()
        try:
            response = client.chat.completions.create(
                model=config.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=config.MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            wait = 60 if attempt < 3 else 120
            logger.info("  rate limited (attempt %d/5), waiting %ds", attempt, wait)
            time.sleep(wait)
        except Exception as exc:
            err = str(exc)
            if "402" in err and "can only afford" in err:
                m = re.search(r"can only afford (\d+)", err)
                if m:
                    new_max = int(m.group(1)) - 50
                    config.MAX_TOKENS = max(new_max, config.MIN_TOKENS)
                    logger.info("  credits low, reduced max_tokens to %d", config.MAX_TOKENS)
                    if config.MAX_TOKENS <= config.MIN_TOKENS:
                        logger.warning("  minimum tokens reached, giving up")
                        return None
                    continue
            if "402" in err and "Prompt tokens limit exceeded" in err:
                logger.warning("  not enough credits for prompt, skipping")
                return None
            if "402" in err:
                logger.warning("  credit error: %s", exc)
                if attempt < 5:
                    time.sleep(3)
                    continue
            logger.warning("  LLM error: %s", exc)
            if attempt < 5:
                time.sleep(10)
            else:
                logger.warning("  giving up")
    return None


def translate_chunk(text):
    if not text.strip():
        return ""

    cache = _load_cache()
    key = _text_hash(text)
    cache_key = f"faithful:{key}"

    if cache_key in cache:
        logger.info("  faithful cached")
        return cache[cache_key]

    logger.info("  translating %d chars...", len(text))
    result = _call_llm(config.FAITHFUL_PROMPT, text)
    if result:
        cache[cache_key] = result
        _save_cache(cache)
        return result

    logger.warning("faithful translation FAILED")
    return None
