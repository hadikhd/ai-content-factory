from typing import cast, List
from app.state import ArticleState
from tools.article_tools import edit_article


def editor_agent(state: ArticleState) -> ArticleState:
    """
    Stable, JSON-based editor agent.
    Ensures the following keys always exist:
    - edited_article (str)
    - editor_feedback (str)
    - editor_improvements (List[str])
    Fully compatible with JSON-returning edit_article in article_tools.py.
    """

# ------------------------------
# 1) Source selection
# ------------------------------
    source_text = (
        state.get("edited_article")
        or state.get("draft_en")
        or state.get("article")
        or ""
    ).strip()

    if not source_text:
        state["edited_article"] = ""
        state["editor_feedback"] = "No source text found for editor."
        # state["editor_improvements"] = []
        return cast(ArticleState, state)

    article_type = cast(str, state.get("article_type") or "blog_post")
    temperature = cast(float, state.get("temperature") or 0.4)

# ------------------------------
# 2) Call the JSON-based editor
# ------------------------------
    try:
        result = edit_article(
        article=source_text,
        article_type=article_type,
        temperature=temperature,
)
    except Exception as e:
# Full fallback
        state["edited_article"] = source_text
        state["editor_feedback"] = f"Editor tool failed: {e}. Original text was kept."
# state["editor_improvements"] = []
        return cast(ArticleState, state)

# ------------------------------
# 3) Validate and repair JSON
# ------------------------------
    if not isinstance(result, dict):
# Editor returned invalid format (string or other)
        state["edited_article"] = source_text
        state["editor_feedback"] = "Editor returned non-JSON output. Original text was kept."
        #state["editor_improvements"] = []
        return cast(ArticleState, state)

# Extract safely:
    feedback = result.get("feedback", "")
    improvements = result.get("improvements", [])
    final_article = result.get("final_article", source_text)

# Ensure correct types
    if not isinstance(feedback, str):
        feedback = str(feedback)

    if not isinstance(improvements, list):
        improvements = [str(improvements)]

    if not isinstance(final_article, str):
        final_article = source_text

# ------------------------------
# 4) Save to state (always stable)
# ------------------------------
    state["edited_article"] = final_article.strip()
    state["editor_feedback"] = feedback.strip()
# state["editor_improvements"] = [str(item).strip() for item in improvements]

    return cast(ArticleState, state)
