# knowledge_graph_agent.py

import json
import re
from typing import Dict, Any

from tools.ollama_client import call_ollama


def knowledge_graph_agent(article: str):

    prompt = f"""
Extract a knowledge graph from the article.

Return JSON:

{{
 "nodes":[{{"id":"concept","type":"concept"}}],
 "edges":[{{"source":"A","target":"B","relation":"related"}}]
}}

Article:
{article}
"""

    raw = call_ollama(prompt)

    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except:
        return {"nodes": [], "edges": []}
