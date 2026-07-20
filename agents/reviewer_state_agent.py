from typing import Dict, Any, cast
from app.state import ArticleState
from agents.reviewer_agent import reviewer_agent
from agents.reviewer_agent_core import run_reviewer
   
# تابع اصلی غیر stateful

def reviewer_state_agent(state: ArticleState) -> ArticleState:
    # Safe copy
    new_state: ArticleState = cast(ArticleState, dict(state))

    # 1) Which text to review
    text = new_state.get("edited_article") or new_state.get("article") or ""

    # 2) Reviewer core agent
    review = run_reviewer(text=text) or {}

    # --- Normalize reviewer output for UI ---
    # Expected by UI: "reviewer_feedback"
    reviewer_feedback = {
        "summary": review.get("review_summary", ""),
        "scores": review.get("scores", {}),
        "issues": review.get("issues", []),
        "needs_edit": bool(review.get("needs_edit", False))
    }
    new_state["reviewer_feedback"] = reviewer_feedback

    # --- Store detailed items as before (no UI dependency) ---
    new_state["review_summary"] = review.get("review_summary", "")
    new_state["review_scores"] = reviewer_feedback["scores"]
    new_state["review_issues"] = reviewer_feedback["issues"]
    new_state["needs_edit"] = reviewer_feedback["needs_edit"]

    # Counter
    new_state["review_count"] = int(new_state.get("review_count") or 0) + 1

    # --- Editor Improvements (expected by UI) ---
    improvements = review.get("improvements") or review.get("editor_improvements") or ""
    new_state["editor_improvements"] = improvements

    return new_state
