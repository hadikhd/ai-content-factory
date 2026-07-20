from tools.ollama_client import call_ollama
from tools.prompts import TITLE_PROMPT
from app.state import ArticleState
from typing import cast


def clean_titles_output(text: str):
    """
    Cleans LLM output and extracts titles reliably.
    Removes code fences, numbering, bullets, quotes, JSON artifacts, etc.
    """
    if not text:
        return []

    # Remove code fences and markdown blocks
    for marker in ["```", "'''", "json", "yaml"]:
        text = text.replace(marker, "")

    cleaned = []

    # Split and process lines
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

    # Remove bullets / numbering
        for prefix in ["- ", "* ", "• ", "1. ", "2. ", "3. ", "4. ", "5. "]:
            if line.startswith(prefix):
                line = line[len(prefix):]

    # Remove surrounding quotes
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]

    # Must be reasonably long to be considered a title
        if len(line) > 5:
         cleaned.append(line)

    return cleaned


def title_agent(state: ArticleState) -> ArticleState:
    topic = state.get("topic", "").strip()
    article_type = state.get("article_type", "blog_post")
    temperature = float(state.get("temperature", 0.7) or 0.7)

    # MAIN FIX: use the model from state or a safe fallback model
    model = state.get("title_model") or state.get("model") or "gemma3:4b"

    # If the user has already selected a title (e.g. via the "Generate
    # Titles" button in the UI), keep it and skip regeneration so the
    # full pipeline reuses the chosen title instead of overwriting it.
    selected_title = (state.get("selected_title") or "").strip()
    if selected_title:
        state["title"] = selected_title
        titles = state.get("titles") or []
        if selected_title not in titles:
            titles = [selected_title] + titles
        state["titles"] = titles
        state["title_error"] = ""
        return cast(ArticleState, state)

    if not topic:
    # در حالت خطا، روی state می‌نویسیم
        state["title"] = ""
        state["titles"] = []
        state["title_error"] = "Topic is empty!"
        return cast(ArticleState, state)

    # Build full prompt
    prompt = f"""
    {TITLE_PROMPT}

    ARTICLE TYPE: {article_type}

    Generate 5 high‑quality, engaging, human‑like article titles.
    Focus on clarity, SEO strength, structure, and relevance.

    TOPIC:
    {topic}
    """

    # Call Ollama safely
    response = call_ollama(
    model=model,
    prompt=prompt,
    temperature=temperature,
    )

    # If LLM failed → fallback to topic
    if not response or not isinstance(response, str):
        state["titles"] = [topic]
        state["title"] = topic
        state["title_error"] = "LLM returned empty or invalid response."
        return cast(ArticleState, state)

    # Clean & extract titles
    titles = clean_titles_output(response)

    # Always ensure at least one title
    if not titles:
        titles = [topic]

    # Always pick the first title
    best_title = titles[0]

    # نتایج روی state
    state["titles"] = titles
    state["title"] = best_title
    state["title_error"] = ""

    return cast(ArticleState, state)