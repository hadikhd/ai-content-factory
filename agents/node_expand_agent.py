import re
from typing import Dict, Any

from tools.ollama_client import call_ollama
import json

def expand_node(topic):

    prompt = f"""
Expand the mind map node.

Topic: {topic}

Return JSON:

{{
 "children":[
   {{"title":"subtopic"}}
 ]
}}
"""

    raw = call_ollama(prompt)

    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except:
        return {"children":[]}
