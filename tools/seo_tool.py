# agents/seo_tool.py
import json
import re
from tools.ollama_client import call_ollama


def _clean_json_response(raw: str) -> str:
    """Strip code fences and isolate the outermost JSON object."""
    if not raw:
        return ""
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return cleaned


def optimize_article(content: str, article_type: str = "") -> dict:
    """
    Optimize an article for SEO using the LLM.

    Args:
        content: the article text to optimize.
        article_type: the chosen article style (e.g. "Educational",
            "Academic", "Technical Report", "Blog Post"). Used to tune
            the SEO guidance.

    Returns:
        dict with keys: seo_article, keywords, seo_score.
    """

    if not content or not isinstance(content, str):
        return {
            "seo_article": "",
            "keywords": [],
            "seo_score": 0,
            "error": "No content provided"
        }

    # Truncate very long articles to avoid exceeding the model context
    # window, which would truncate the JSON output and cause parse
    # failures (resulting in score=0 and no keywords).
    max_chars = 10000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n…[truncated]"

    style_hint = ""
    if article_type:
        style_hint = (
            f"\nThe article is written in a '{article_type}' style. "
            f"Tailor the keywords and SEO recommendations to that style."
        )

    prompt = f"""
You are an expert SEO specialist and content optimizer.

Analyze the following article and produce an SEO-optimized version with
a thorough keyword strategy and an honest, well-justified SEO score.

Return ONLY a valid JSON object with EXACTLY these keys (no markdown,
no code fences, no commentary):

{{
  "seo_article": "<the article with SEO improvements applied — keep the
                   full structure, add a meta-description-style intro
                   paragraph, optimize headings and keyword density>",
  "keywords": ["<primary keyword>", "<secondary keyword>", "..."],
  "seo_score": <integer 0-100>,
  "score_breakdown": {{
    "keyword_optimization": <0-100>,
    "heading_structure": <0-100>,
    "readability": <0-100>,
    "meta_description": <0-100>,
    "internal_linking_suggestions": <0-100>
  }},
  "recommendations": ["<actionable SEO tip 1>", "<tip 2>", "..."]
}}

Rules:
- "keywords" MUST contain at least 5 and up to 12 relevant, high-traffic
  keywords and key phrases extracted from the article.
- "seo_score" must be a realistic integer between 0 and 100 reflecting
  the article's current SEO strength. Do NOT default to 0.
- "seo_article" should be the improved version of the input article.
- Output ONLY the JSON object. No markdown fences. No prose.{style_hint}

ARTICLE:
{content}
"""

    # Use a capable model with low temperature for deterministic,
    # well-structured JSON output.
    response = call_ollama(
        prompt,
        model="gemma3:12b",
        temperature=0.2,
        max_tokens=4096,
    )

    cleaned = _clean_json_response(response)
    try:
        parsed_response = json.loads(cleaned)
    except Exception:
        # Fallback: try to salvage whatever the model returned
        parsed_response = {
            "seo_article": response.strip(),
            "keywords": [],
            "seo_score": 0
        }

    # Normalize / enforce required keys
    parsed_response.setdefault("seo_article", "")
    parsed_response.setdefault("keywords", [])
    parsed_response.setdefault("seo_score", 0)

    # Ensure keywords is a list of strings
    kw = parsed_response.get("keywords")
    if not isinstance(kw, list):
        if isinstance(kw, str):
            parsed_response["keywords"] = [
                k.strip() for k in kw.split(",") if k.strip()
            ]
        else:
            parsed_response["keywords"] = []
    else:
        parsed_response["keywords"] = [str(k) for k in kw if k]

    # Ensure score is an int
    try:
        parsed_response["seo_score"] = int(parsed_response["seo_score"])
    except Exception:
        parsed_response["seo_score"] = 0

    return parsed_response
