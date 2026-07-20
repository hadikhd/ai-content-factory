# reviewer_agent.py (ULTRA PRO VERSION)
import json
import re
from typing import Any, Dict, List
from typing import cast
from app.state import ArticleState

from tools.ollama_client import call_ollama
from agents.reviewer_agent_core import run_reviewer



#######################################################################
# 1) ULTRA PRO REVIEWER CORE
#######################################################################

def _reviewer_core(text: str, model: str, temperature: float) -> Dict[str, Any]:
    """
    Core logic of the reviewer, unchanged from original behavior,
    except we pass model/temperature explicitly to call_ollama.
    """
    prompt = f"""
    You are an advanced professional article reviewer and editor.
    Your review must be thorough, technical, structured, and strictly JSON-only.

    Analyze the article across multiple dimensions:
    - Grammar accuracy
    - Clarity & readability
    - Structure & logical flow
    - Paragraph quality
    - Tone & style consistency
    - Redundancy / repetition
    - Completeness of content
    - SEO relevance (if applicable)

    Generate a JSON output with this structure EXACTLY:

    {{
        "needs_edit": true/false,
        "scores": {{
        "grammar_score": 0-100,
        "clarity_score": 0-100,
        "structure_score": 0-100,
        "coherence_score": 0-100,
        "readability_score": 0-100,
        "seo_score": 0-100
    }},
    "issues": [
    {{
        "issue": "Short description of the problem.",
        "severity": "minor/moderate/major/critical",
        "suggestion": "Actionable suggestion to fix the issue."
}}
    ],
        "review_summary": "One‑paragraph summary of what is wrong.",
        "final_recommendation": "edit_required / good_enough / major_rewrite"
}}

    Rules:
        - ALWAYS return a valid JSON object.
        - NEVER return markdown, explanations, or anything outside JSON.
        - If there are more than 15 issues, summarize to the most important ones.
        - Use realistic professional scoring (no random numbers).
        - needs_edit = false only if ALL scores >= 85 and no major issues exist.

    Article to review:
    {text}
    """

    raw = call_ollama(prompt=prompt, model=model, temperature=temperature)

    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        data = json.loads(cleaned)

# Ensure minimum structure & fill missing fields
        data.setdefault("needs_edit", True)
        data.setdefault("review_summary", "")
        data.setdefault("final_recommendation", "edit_required")

        if "scores" not in data:
            data["scores"] = {}
            scores = data["scores"]

# score defaults (bugfix: استفاده از نام فیلد واقعی)
            for field in [
                "grammar_score",
                "clarity_score",
                "structure_score",
                "coherence_score",
                "readability_score",
                "seo_score",
    ]:
                scores[field] = int(scores.get(field, 60))

# issues normalization
            issues = data.get("issues", [])
            normalized = []
            for item in issues:
                if not isinstance(item, dict):
                    continue
                normalized.append(
    {
                    "issue": str(item.get("issue", "")).strip(),
                    "severity": str(item.get("severity", "moderate")).strip(),
                    "suggestion": str(item.get("suggestion", "")).strip(),
}
)
            data["issues"] = normalized

        return data
    except Exception:

        return {
            "needs_edit": True,
            "scores": {
            "grammar_score": 50,
            "clarity_score": 50,
            "structure_score": 50,
            "coherence_score": 50,
            "readability_score": 50,
            "seo_score": 50,
},
    "issues": [
{
"issue": "Reviewer failed to parse output.",
"severity": "major",
"suggestion": "Please re-run the review or manually inspect the text.",
}
],
"review_summary": "Automatic review failed; default fallback used.",
"final_recommendation": "edit_required",
}


#######################################################################
# 2) STATEFUL WRAPPER
#######################################################################

def reviewer_agent(state: ArticleState) -> ArticleState:
    # Safe cast
    state = cast(ArticleState, state)

    # 1. انتخاب متن برای بررسی
    text = (
        state.get("edited_article")
        or state.get("article")
        or ""
    ).strip()

    model = state.get("reviewer_model") or state.get("model") or "gemma3:4b"
    temperature = float(state.get("reviewer_temperature") or state.get("temperature") or 0.2)

    # 2. اگر متنی نبود
    if not text:
        state["needs_edit"] = False

        reviewer_feedback = {
            "summary": "No text provided for review.",
            "scores": {},
            "issues": [],
            "needs_edit": False
        }
        state["reviewer_feedback"] = reviewer_feedback

        # Compatibility for older fields
        state["review_summary"] = reviewer_feedback["summary"]
        state["review_scores"] = reviewer_feedback["scores"]
        state["review_issues"] = reviewer_feedback["issues"]
        state["final_recommendation"] = "no_text"

        # شمارنده
        state["review_count"] = int(state.get("review_count") or 0) + 1
        return state

    # 3. فراخوانی منطق اصلی
    review_result = _reviewer_core(text, model, temperature) or {}

    # --- مهم‌ترین بخش: خروجی استاندارد برای UI ---
    reviewer_feedback = {
        "summary": review_result.get("review_summary", ""),
        "scores": review_result.get("scores", {}),
        "issues": review_result.get("issues", []),
        "needs_edit": bool(review_result.get("needs_edit", False))
    }
    state["reviewer_feedback"] = reviewer_feedback

    # --- سازگاری با فیلدهای قبلی ---
    state["review_summary"] = reviewer_feedback["summary"]
    state["review_scores"] = reviewer_feedback["scores"]
    state["review_issues"] = reviewer_feedback["issues"]
    state["needs_edit"] = reviewer_feedback["needs_edit"]
    state["final_recommendation"] = review_result.get("final_recommendation", "")

    # 4. Editor improvements (اگر وجود داشت)
    improvements = (
        review_result.get("editor_improvements")
        or review_result.get("improvements")
        or ""
    )
    state["editor_improvements"] = improvements

    # 5. شمارنده
    state["review_count"] = int(state.get("review_count") or 0) + 1

    return state

