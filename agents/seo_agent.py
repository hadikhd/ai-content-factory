# agents/seo_agent.py

import json
import re
from typing import cast, Dict, Any
from tools.seo_tool import optimize_article
from app.state import ArticleState


def clean_json_output(raw: str) -> Dict[str, Any]:
# پاک‌سازی```json و سایر backtick ها
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()

# اگر واقعا JSON بود، parse می‌کنیم
    try:
        return json.loads(cleaned)
    except:
        return {"seo_article": raw, "seo_score": 0}


def seo_agent(state: ArticleState) -> ArticleState:
    content = state.get("edited_article") or state.get("article") or ""
    article_type = state.get("article_type") or ""

    if not content:
            state["seo_article"] = ""
            state["seo_score"] = 0
            state["seo_json"] = {}
            state["seo_report"] = ""
            return cast(ArticleState, state)

# خروجی خام LLM
    raw_output = optimize_article(content, article_type=article_type)

# اگر dict نیست → string است → باید clean شود
    if isinstance(raw_output, str):
        result = clean_json_output(raw_output)
    else:
        result = raw_output

# استخراج
    seo_article = result.get("seo_article") or result.get("article") or content
    seo_score = result.get("seo_score", 0)
    seo_json = result

# این کلید برای UI ضروری است
    seo_report = json.dumps(seo_json, indent=2, ensure_ascii=False)

# ذخیره state
    state["seo_article"] = seo_article
    state["seo_score"] = seo_score
    state["seo_json"] = seo_json
    state["seo_report"] = seo_report  # ← کلید اصلی UI

    return cast(ArticleState, state)