from tools.prompts import *
from config import *
from tools.ollama_client import ollama
from typing import Any, List
import re
import time
import logging
import json
#from tools.prompts import TITLE_PROMPT, TRANSLATOR_MEGA_PROMPT, TRANSLATOR_PROMPT_ACADEMIC,TRANSLATOR_PROMPT_ENGINEERING, TRANSLATOR_PROMPT_SIMPLE, TRANSLATOR_PROMPT_BLOG

logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------
# Internal helpers
# ---------------------------------------------------

def _extract_text(result: Any) -> str:
    """Extract text safely from different Ollama response formats."""

    if not result:
        return ""

    # string response
    if isinstance(result, str):
        return result

    # dict response
    if isinstance(result, dict):

        if "response" in result:
            return result["response"]

        if "message" in result:
            msg = result["message"]
            if isinstance(msg, dict):
                return msg.get("content", "") or msg.get("text", "")

    # object response (new ollama versions)
    if hasattr(result, "response"):
        return getattr(result, "response")

    if hasattr(result, "message"):
        msg = getattr(result, "message")
        if isinstance(msg, dict):
            return msg.get("content", "") or msg.get("text", "")

    return str(result)



def _clean_llm_output(text: str) -> str:
    """Remove markdown fences and wrapping quotes."""

    if not text:
        return ""

    text = text.strip()

    text = (
        text.replace("```json", "").replace("```text", "").replace("```markdown", "").replace("```", "")
    )

    text = text.strip()

    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1]

    return text.strip()


# ---------------------------------------------------
# Safe LLM call
# ---------------------------------------------------

def safe_call(
    model: str,
    prompt: str,
    temperature: float = 0.3,
    top_p: float = 0.95,
    top_k: int = 40,
    retries: int = 2,
) -> str:

    if not prompt:
        return ""

    for attempt in range(retries + 1):

        try:

            result = ollama.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": temperature,
                    "top_p": top_p,
                    "top_k": top_k,
                },
                stream=False,
            )

            text = _extract_text(result)

            text = _clean_llm_output(text)

            if text:
                return text

        except Exception as e:

            logging.warning(
                f"[safe_call] Attempt {attempt+1}/{retries+1} failed: {e}"
            )

            time.sleep(1)

    logging.error("LLM call failed after retries")

    return ""


# ---------------------------------------------------
# Title cleaning
# ---------------------------------------------------

def clean_title(line: str) -> str:

    if not line:
        return ""

    line = line.strip()

    line = re.sub(r"^[\*\-\d\.\)\s]+", "", line)
    line = re.sub(r"^#+\s*", "", line)
    line = re.sub(r"(?i)^title\s*:\s*", "", line)

    return line.strip()


# ---------------------------------------------------
# Title generation
# ---------------------------------------------------
def extract_titles(text: str) -> List[str]:

    if not text:
        return []

    # remove markdown blocks
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text).strip()

    # try JSON array
    match = re.search(r"\[[\s\S]*?\]", text)

    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [str(t).strip() for t in data if str(t).strip()]
        except Exception:
            pass

    titles = []

    for line in text.split("\n"):

        line = line.strip()

        if not line:
            continue

        # remove numbering / bullets
        line = re.sub(r"^[-•*\d\.]+\s*", "", line)

        cleaned = clean_title(line)

        if cleaned:
            titles.append(cleaned)

    return titles


def generate_titles(
    topic: str,
    article_type: str = "Educational",
    temperature: float = 0.5,
    model: str = TITLE_MODEL,
) -> List[str]:

    if not topic:
        return []

    prompt = TITLE_PROMPT.format(
        topic=topic,
        article_type=article_type,
    )

    raw = safe_call(
        model=model,
        prompt=prompt,
        temperature=temperature,
    )

    if not raw:
        return []

    titles = extract_titles(raw)

    # remove duplicates
    titles = list(dict.fromkeys(titles))

    return titles[:5]


# ---------------------------------------------------
# Writer
# ---------------------------------------------------

def write_article(
    title: str,
    topic: str = "",
    article_type: str = "Educational",
    temperature: float = 0.7,
    model: str = WRITER_MODEL,
) -> str:

    if not title:
        return "No title provided."

    prompt = generate_prompt(
        topic=topic,
        title=title,
        article_type=article_type,
    )

    article = safe_call(
        model=model,
        prompt=prompt,
        temperature=temperature,
    )

    if not article:
        return "No article generated."

    return article.strip()


# ---------------------------------------------------
# Editor
# ---------------------------------------------------
def edit_article(article: str, article_type: str, temperature: float = 0.4):
    """
    Calls the LLM and ensures the output is valid JSON.
    """

    prompt = EDITOR_PROMPT + f"\n\nARTICLE:\n{article}\n\n"

    raw = safe_call(
        model=EDITOR_MODEL,
        prompt=prompt,
        temperature=temperature,
    )

    if not raw:
        return {
            "feedback": "Editor model returned empty output.",
            "improvements": [],
            "final_article": article,
        }

    # try parse JSON (robust)
    try:
        data = json.loads(raw)
    except Exception:
        # fallback: try to extract {...}
        try:
            json_part = raw[raw.index("{"): raw.rindex("}")+1]
            data = json.loads(json_part)
        except Exception:
            # ultimate fallback
            return {
                "feedback": "Editor output invalid JSON; returning fallback.",
                "improvements": [],
                "final_article": raw,
            }

    return data


# ---------------------------------------------------
# Translator
# ---------------------------------------------------
def translate_article(
    source_text: str,
    target_lang: str = "fa",
    temperature: float = 0.3,
    model: str = TRANSLATE_MODEL,
) -> str:

    if not source_text:
        return "متنی برای ترجمه وجود ندارد."

    # Build full translation prompt
    prompt = (
        TRANSLATOR_MEGA_PROMPT
        + f"\n\nTARGET LANGUAGE: {target_lang}\n"
        + "\nTEXT TO TRANSLATE:\n"
        + source_text
        + "\n"
    )

    translated = safe_call(
        model=model,
        prompt=prompt,
        temperature=temperature,
    )

    if not translated:
        return "ترجمه‌ای تولید نشد."

    return translated.strip()


# =========================
# Prompt Factory
# =========================

def get_style_guideline(article_type: str) -> str:

    guidelines = {
        "Academic": "Formal, analytical, structured and research-oriented.",
        "Blog Post": "Casual, engaging and SEO-friendly.",
        "Comparative": "Objective comparison with pros and cons.",
        "Educational": "Clear explanation suitable for beginners.",
        "Technical Report": "Precise, data-driven and technical."
    }

    return guidelines.get(article_type, "Neutral informative tone.")


def get_article_structure(article_type: str) -> str:

    structures = {

        "Academic": """
Abstract
Introduction
Literature Review
Analysis
Discussion
Conclusion
""",

        "Blog Post": """
Hook
Background
Key Insights
Examples
Conclusion + Call to Action
""",

        "Educational": """
Concept Overview
Why It Matters
Step-by-step Explanation
Common Mistakes
Summary
""",

        "Comparative": """
Introduction
Comparison Table
Pros and Cons
Final Verdict
""",

        "Technical Report": """
Executive Summary
Background
Methodology
Results
Conclusion
"""
    }

    return structures.get(article_type, "Introduction, body, conclusion.")


def generate_prompt(topic: str, title: str, article_type: str) -> str:

    style = get_style_guideline(article_type)
    structure = get_article_structure(article_type)

    prompt = f"""
You are a professional AI writer specialized in {article_type} content.

Write a detailed article titled "{title}" about the topic "{topic}".

Structure:
{structure}

Style guideline:
{style}

Rules:
- Use Markdown formatting
- Use clear section headings (##)
- Content must match article type: {article_type}
"""

    return prompt.strip()

def translator_selector(article_type: str) -> str:
    """
    Select the optimal translator prompt based on article type.
    """

    t = article_type.lower().strip()

    if t in ["academic", "science", "research", "paper", "journal"]:
        return TRANSLATOR_PROMPT_ACADEMIC

    if t in ["engineering", "devops", "cloud", "network", "systems"]:
        return TRANSLATOR_PROMPT_ENGINEERING

    if t in ["simple", "general", "public", "easy"]:
        return TRANSLATOR_PROMPT_SIMPLE

    # Default (technical blog style)
    return TRANSLATOR_PROMPT_BLOG
