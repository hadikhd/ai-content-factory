# agents/citation_agent.py

from typing import cast
import json
from tools.ollama_client import call_ollama
from app.state import ArticleState


def _extract_citations(article: str) -> dict:
    """
    Internal helper – فقط کار LLM
    """

    prompt = f"""
Extract academic citations for the following article.

Return ONLY pure JSON with keys:
- citations (array of objects)
- reference_section (string)

Article:
{article}
"""

    response = call_ollama(prompt)
    response = cast(str, response or "")

    try:
        parsed = json.loads(response)
        if not isinstance(parsed, dict):
            raise ValueError("LLM did not return a JSON object")
    except Exception:
        parsed = {
            "citations": [],
            "reference_section": response.strip(),
        }

    parsed.setdefault("citations", [])
    parsed.setdefault("reference_section", "")

    return parsed


def citation_agent(state: ArticleState) -> ArticleState:
    """
    LangGraph-compatible citation agent
    """

    article = (
        state.get("edited_article")
        or state.get("seo_article")
        or state.get("article")
        or ""
    )

    article = cast(str, article)

    # اگر مقاله نداریم → فقط state را سالم برمی‌گردانیم
    if not article.strip():
        state["citations"] = []
        state["reference_section"] = ""
        state["citation_error"] = "No article provided"
        return cast(ArticleState, state)

    result = _extract_citations(article)

    state["citations"] = result["citations"]
    state["reference_section"] = result["reference_section"]
    state["citation_error"] = ""

    return cast(ArticleState, state)
