import re
from typing import Dict, Any

from tools.ollama_client import call_ollama

def generate_node_content(topic):

    prompt = f"""
Write a short paragraph explaining:

{topic}

Keep it concise and informative.
"""

    return call_ollama(prompt)
