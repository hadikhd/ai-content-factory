from __future__ import annotations
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import cast, List

from app.state import ArticleState
from tools.prompts import (
    TRANSLATOR_PROMPT_ACADEMIC,
    TRANSLATOR_PROMPT_ENGINEERING,
    TRANSLATOR_PROMPT_SIMPLE,
    TRANSLATOR_PROMPT_BLOG,
    LANGUAGE_STYLE_ANALYZER_PROMPT,
)
from tools.ollama_client import call_ollama

logger = logging.getLogger("translator_agent")
logger.setLevel(logging.INFO)


# ============================================================
# 1) --- STYLE DETECTION LLM ---
# ============================================================

def detect_text_style(text: str, temperature: float = 0.0, article_type: str = "") -> str:
    """
    Detect writing style using a raw LLM call.
    Output must be one of:
       academic | research | engineering | blog | simple

    If the user has already chosen an article_type (e.g. "Educational",
    "Academic", "Technical Report", "Blog Post"), we PREFER that choice
    and map it to the translator's style vocabulary. The LLM detection
    is only used as a fallback when no article_type was selected.
    """

    # ---- 1) Prefer the user's chosen article_type ----
    # Map UI article_type labels → translator style vocabulary.
    type_to_style = {
        "academic": "academic",
        "educational": "simple",       # educational → clear, beginner-friendly
        "education": "simple",
        "technical report": "engineering",
        "technical_report": "engineering",
        "technical": "engineering",
        "report": "engineering",
        "blog post": "blog",
        "blog_post": "blog",
        "blog": "blog",
        "comparative": "academic",
    }
    if article_type:
        key = article_type.strip().lower()
        mapped = type_to_style.get(key)
        if mapped:
            logger.info(
                f"[translator_agent] Using user-selected article_type "
                f"'{article_type}' → style '{mapped}'"
            )
            return mapped

    # ---- 2) Fallback: LLM-based detection ----
    if not text:
        return "blog"

    prompt = (
        LANGUAGE_STYLE_ANALYZER_PROMPT
        + "\n\nTEXT:\n"
        + text[:4000]
    )

    try:
        result = call_ollama(prompt, temperature=temperature).strip().lower()
        logger.info(f"[translator_agent] Detected style (LLM): {result}")
    except Exception as e:
        logger.error(f"[translator_agent] Style detection failed: {e}")
        return "blog"

    valid = ["academic", "research", "engineering", "blog", "simple"]

    return result if result in valid else "blog"


# ============================================================
# 2) ROUTER → MAP STYLE TO PROMPT
# ============================================================

def router_prompt_by_style(style: str) -> str:
    style = style.lower().strip()

    if style in ["academic", "research"]:
        return TRANSLATOR_PROMPT_ACADEMIC

    if style == "engineering":
        return TRANSLATOR_PROMPT_ENGINEERING

    if style == "simple":
        return TRANSLATOR_PROMPT_SIMPLE

    return TRANSLATOR_PROMPT_BLOG



# ============================================================
# 3) SMART SPLITTER (Sentence + Paragraph Aware)
# ============================================================

def smart_chunk_split(text: str, max_len: int = 1200) -> List[str]:
    """
    Splits text on paragraph and sentence boundaries to keep chunks clean.
    Much better than textwrap.wrap.
    """

    if not text:
        return []

    # Normalize line breaks
    text = text.replace("\r\n", "\n").strip()

    # Split into paragraphs
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    def flush():
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?]) +", para)

        for s in sentences:
            if len(current) + len(s) <= max_len:
                current += s + " "
            else:
                flush()
                current = s + " "

        flush()

    return chunks



# ============================================================
# 4) TRANSLATE CHUNK
# ============================================================

def translate_chunk(chunk: str, temperature: float, prompt_base: str, detected_style: str) -> str:
    final_prompt = (
        prompt_base
        + "\n\nDETECTED STYLE: " + detected_style
        + "\n\nTEXT TO TRANSLATE:\n"
        + chunk
    )

    try:
        # استفاده مستقیم از رپر امن call_ollama
        result = call_ollama(
            prompt=final_prompt,
            temperature=temperature,
            # اگر خواستی می‌توانی مدل را هم override کنی:
            model="translategemma:4b"
        )
        return result.strip()
    except Exception as e:
        logger.error(f"[translator_agent] Chunk translation failed: {e}")
        return ""


# ============================================================
# 5) MAIN TRANSLATOR AGENT NODE
# ============================================================

def translator_agent(state: ArticleState) -> ArticleState:
    """
    AI Translator (Production‑Ready)
    Uses:
       - Smart style detection (single call)
       - Smart chunking
       - Parallel LLM calls
       - Thread‑safe progress
    """

    # Determine final English text to translate
    article = (
        state.get("edited_article")
        or state.get("writer_output")
        or state.get("article")
        or ""
    )

    if not article.strip():
        state["persian_article"] = "متنی برای ترجمه یافت نشد."
        return state

    temperature = float(state.get("temperature") or 0.3)

    # --------------------------------------------------------
    # Step 1 — detect global style ONCE
    # --------------------------------------------------------
    # Prefer the user's chosen article_type; only fall back to LLM
    # detection when no article_type was selected.
    article_type = state.get("article_type") or ""
    detected_style = detect_text_style(article, article_type=article_type)
    state["detected_style"] = detected_style

    # Pick correct translator prompt
    prompt_base = router_prompt_by_style(detected_style)

    # --------------------------------------------------------
    # Step 2 — split into clean chunks
    # --------------------------------------------------------
    chunks = smart_chunk_split(article)
    total = len(chunks)
    state["translation_total"] = total
    state["translation_progress"] = 0

    if total == 0:
        state["persian_article"] = ""
        return state

    translated = [""] * total

    # --------------------------------------------------------
    # Step 3 — parallel translation
    # --------------------------------------------------------
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_index = {
            executor.submit(
                translate_chunk,
                chunk,
                temperature,
                prompt_base,
                detected_style
            ): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(future_to_index):
            idx = future_to_index[future]

            try:
                translated[idx] = future.result()
            except Exception as e:
                logger.error(f"[translator_agent] Error in chunk {idx}: {e}")
                translated[idx] = ""

            # Update progress safely
            state["translation_progress"] = int(state["translation_progress"]) + 1

    # --------------------------------------------------------
    # Step 4 — merge final text
    # --------------------------------------------------------
    state["persian_article"] = "\n\n".join(translated)
    logger.info("[translator_agent] Translation completed successfully.")

    return cast(ArticleState, state)

