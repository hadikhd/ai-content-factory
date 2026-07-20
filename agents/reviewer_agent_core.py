# agents/reviewer_agent_core.py
import json
import re
from typing import Any, Dict
from tools.ollama_client import call_ollama

def _reviewer_core(text: str, model: str, temperature: float) -> Dict[str, Any]:
    """
    Core logic of the reviewer. Strictly JSON-only output.
    """
    prompt = f"""
    You are an advanced professional article reviewer and editor.
    Your review must be thorough, technical, structured, and strictly JSON-only.

    Analyze the article across multiple dimensions:
    - Grammar accuracy, Clarity, Structure, Coherence, Readability, SEO.

    Generate a JSON output with this structure EXACTLY:
    {{
        "needs_edit": true,
        "scores": {{
            "grammar_score": 80,
            "clarity_score": 85,
            "structure_score": 70,
            "coherence_score": 75,
            "readability_score": 80,
            "seo_score": 60
        }},
        "issues": [
            {{ "issue": "desc", "severity": "minor", "suggestion": "fix" }}
        ],
        "review_summary": "summary text",
        "final_recommendation": "edit_required"
    }}
    
    Article to review:
    {text}
    """

    try:
        raw = call_ollama(prompt=prompt, model=model, temperature=temperature)
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        data = json.loads(cleaned)

        # Default values and normalization
        data.setdefault("needs_edit", True)
        data.setdefault("review_summary", "")
        data.setdefault("final_recommendation", "edit_required")

        if "scores" not in data:
            data["scores"] = {
                "grammar_score": 60, "clarity_score": 60, "structure_score": 60,
                "coherence_score": 60, "readability_score": 60, "seo_score": 60
 }

        # Normalize issues
        issues = data.get("issues", [])
        normalized = []
        if isinstance(issues, list):
            for item in issues:
                if isinstance(item, dict):
                    normalized.append({
                        "issue": str(item.get("issue", "")),
                        "severity": str(item.get("severity", "moderate")),
                        "suggestion": str(item.get("suggestion", ""))
                    })
        data["issues"] = normalized
        return data

    except Exception as e:
        return {
            "needs_edit": True,
            "scores": {k: 50 for k in ["grammar_score", "clarity_score", "structure_score", "coherence_score", "readability_score", "seo_score"]},
            "issues": [{"issue": f"Parse error: {str(e)}", "severity": "major", "suggestion": "Retry"}],
            "review_summary": "Fallback due to error.",
            "final_recommendation": "edit_required"
        }
def run_reviewer(text: str, model="gemma3:4b", temperature=0.2):
    return _reviewer_core(text, model, temperature)
