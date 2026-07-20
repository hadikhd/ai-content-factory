# agents/image_agent.py

from typing import cast, List
from tools.ollama_client import call_ollama
from app.state import ArticleState


def image_agent(state: ArticleState) -> ArticleState:
    """
    Generate image prompts for the article
    """

    article = (
        state.get("seo_article")
        or state.get("edited_article")
        or state.get("article")
        or ""
    )

    article = cast(str, article)

    if not article.strip():
        state["images"] = []
        return cast(ArticleState, state)

    prompt = f"""
Create 3 detailed image prompts suitable for Stable Diffusion.

Return them as a simple list, one prompt per line.

Article:
{article}
"""

    response = call_ollama(prompt)
    raw = cast(str, response or "")

    # تبدیل ساده به لیست
    lines: List[str] = [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]

    state["images"] = lines
    return cast(ArticleState, state)
