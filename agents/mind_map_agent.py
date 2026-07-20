# agents/mind_map_agent.py

import json
import re
import logging
from typing import Any, Dict, List

from tools.ollama_client import call_ollama
from app.state import ArticleState

logger = logging.getLogger("mind_map_agent")
logger.setLevel(logging.INFO)


def ensure_text(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "\n".join(map(str, x))
    if isinstance(x, dict):
        return json.dumps(x, ensure_ascii=False)
    return str(x)


# ============================================================
# 1) STRUCTURE EXTRACTION
# ============================================================

_MINDMAP_PROMPT = """You are an expert knowledge engineer and information architect.

Your task: build a COMPLETE, DETAILED hierarchical mind map that captures
EVERY key concept, section, sub-section, example, and important detail
from the article below.

The mind map must be DEEP (3-4 levels) and FAITHFUL to the article.
Do NOT summarize away details — the mind map should let someone who
hasn't read the article understand its full structure and content.

Return ONLY valid JSON in EXACTLY this structure (no markdown, no
commentary, no code fences):

{{
  "title": "<the main topic / title of the article>",
  "summary": "<one-sentence summary of the whole article>",
  "branches": [
    {{
      "topic": "<major section heading>",
      "summary": "<one short sentence about this section>",
      "subtopics": [
        {{
          "label": "<key point or sub-heading>",
          "details": ["<specific fact / example / metric / definition>", "..."],
          "children": [
            {{
              "label": "<deeper sub-point>",
              "details": ["..."]
            }}
          ]
        }}
      ]
    }}
  ]
}}

RULES:
- Produce AT LEAST 4-6 main branches (one per major section of the article).
- Each branch should have 3-5 subtopics.
- Each subtopic may have a "children" array for deeper nesting (3rd/4th level).
- Use the ACTUAL headings and key terms from the article — do not invent.
- Include concrete details: numbers, names, definitions, examples.
- If the article has a conclusion, include it as a branch.
- Keep labels short (3-8 words). Put longer explanations in "details".
- Output ONLY the JSON object. No markdown fences. No prose.

ARTICLE (English):
{english}

ARTICLE (Persian — for cross-reference, prefer English structure):
{persian}
"""


def _clean_json(raw: str) -> str:
    """Strip code fences and extract the outermost JSON object."""
    if not raw:
        return ""
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    # Try to isolate the first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return cleaned


def _validate_structure(data: Any) -> Dict[str, Any]:
    """Ensure the parsed structure has the required keys and types."""
    if not isinstance(data, dict):
        return {"title": "Article", "summary": "", "branches": []}

    data.setdefault("title", "Article")
    data.setdefault("summary", "")
    data.setdefault("branches", [])

    if not isinstance(data["branches"], list):
        data["branches"] = []

    # Normalize each branch
    for branch in data["branches"]:
        if not isinstance(branch, dict):
            continue
        branch.setdefault("topic", "Untitled")
        branch.setdefault("summary", "")
        branch.setdefault("subtopics", [])
        if not isinstance(branch["subtopics"], list):
            branch["subtopics"] = []
        for sub in branch["subtopics"]:
            if not isinstance(sub, dict):
                continue
            sub.setdefault("label", str(sub))
            sub.setdefault("details", [])
            if not isinstance(sub["details"], list):
                sub["details"] = [str(sub["details"])]
            sub.setdefault("children", [])
            if not isinstance(sub["children"], list):
                sub["children"] = []

    return data


def mind_map_agent(english: str, persian: str) -> Dict[str, Any]:
    """Extract a deep hierarchical mind-map structure from the article.

    Uses a strong prompt that requests 3-4 levels of nesting and
    concrete details (numbers, definitions, examples) so the map
    captures the FULL article content rather than a shallow summary.
    """
    english = ensure_text(english)
    persian = ensure_text(persian)

    # Truncate to avoid exceeding context windows, but keep enough
    # to build a complete map (most models handle ~8k tokens).
    max_chars = 12000
    if len(english) > max_chars:
        english = english[:max_chars] + "\n…[truncated]"
    if len(persian) > 4000:
        persian = persian[:4000] + "\n…[truncated]"

    prompt = _MINDMAP_PROMPT.format(english=english, persian=persian)

    try:
        raw = call_ollama(prompt, model="gemma3:4b", temperature=0.2)
    except Exception as e:
        logger.error(f"[mind_map_agent] LLM call failed: {e}")
        return {"title": "Article", "summary": "", "branches": []}

    if isinstance(raw, dict):
        raw = raw.get("response") or raw.get("content") or str(raw)
    raw = str(raw)

    cleaned = _clean_json(raw)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        logger.error(f"[mind_map_agent] JSON parse failed: {e}\nRaw: {raw[:300]}")
        return {"title": "Article", "summary": "", "branches": []}

    return _validate_structure(data)


# ============================================================
# 2) HTML RENDERER — Interactive radial/tree mind map
# ============================================================

def build_mindmap(structure: Dict[str, Any]) -> str:
    """Render the mind-map structure as a self-contained, interactive
    HTML page using a collapsible tree layout with D3.js-style styling
    (pure CSS/JS, no external dependencies, works offline)."""

    data = json.dumps(structure, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mind Map</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f172a;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Tahoma, sans-serif;
    padding: 24px;
    min-height: 100vh;
  }}
  .mm-header {{
    text-align: center;
    margin-bottom: 24px;
  }}
  .mm-title {{
    font-size: 1.8rem;
    font-weight: 800;
    color: #818cf8;
    margin-bottom: 6px;
  }}
  .mm-summary {{
    color: #94a3b8;
    font-size: 0.95rem;
    max-width: 700px;
    margin: 0 auto;
    line-height: 1.5;
  }}
  .mm-controls {{
    text-align: center;
    margin: 16px 0;
  }}
  .mm-btn {{
    background: #6366f1;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    margin: 0 4px;
    transition: background 0.2s;
  }}
  .mm-btn:hover {{ background: #4f46e5; }}
  .mm-btn.secondary {{ background: #334155; }}
  .mm-btn.secondary:hover {{ background: #475569; }}

  /* Tree layout */
  .mm-tree {{
    display: flex;
    justify-content: center;
    margin-top: 20px;
  }}
  .mm-tree ul {{
    list-style: none;
    position: relative;
    padding-left: 28px;
    margin: 0;
  }}
  .mm-tree li {{
    position: relative;
    margin: 6px 0;
  }}
  .mm-tree li::before {{
    content: '';
    position: absolute;
    left: -14px;
    top: 14px;
    width: 14px;
    height: 1px;
    background: #334155;
  }}
  .mm-tree li::after {{
    content: '';
    position: absolute;
    left: -14px;
    top: 0;
    width: 1px;
    height: 14px;
    background: #334155;
  }}
  .mm-tree li:last-child::after {{
    height: 14px;
  }}
  .mm-tree > .mm-root > ul {{
    padding-left: 0;
  }}
  .mm-tree > .mm-root > ul > li::before,
  .mm-tree > .mm-root > ul > li::after {{
    display: none;
  }}

  /* Nodes */
  .mm-node {{
    display: inline-block;
    padding: 8px 14px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9rem;
    line-height: 1.4;
    max-width: 480px;
  }}
  .mm-node:hover {{ transform: translateX(3px); }}
  .mm-root-node {{
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 12px 20px;
    box-shadow: 0 4px 14px rgba(99,102,241,0.4);
  }}
  .mm-branch-node {{
    background: #1e293b;
    color: #c7d2fe;
    font-weight: 600;
    border: 1px solid #334155;
  }}
  .mm-branch-node:hover {{ background: #334155; }}
  .mm-sub-node {{
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #1e293b;
  }}
  .mm-sub-node:hover {{ background: #1e293b; }}
  .mm-child-node {{
    background: transparent;
    color: #94a3b8;
    border: 1px dashed #334155;
    font-size: 0.82rem;
  }}
  .mm-child-node:hover {{ background: #1e293b; color: #cbd5e1; }}

  .mm-branch-summary {{
    display: block;
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 400;
    margin-top: 2px;
  }}
  .mm-details {{
    margin: 4px 0 4px 16px;
    padding-left: 12px;
    border-left: 2px solid #334155;
  }}
  .mm-detail {{
    font-size: 0.8rem;
    color: #94a3b8;
    margin: 2px 0;
    line-height: 1.4;
  }}
  .mm-toggle {{
    margin-left: 6px;
    font-size: 0.7rem;
    color: #64748b;
  }}
  .mm-children.collapsed {{ display: none; }}
  .mm-empty {{
    text-align: center;
    color: #64748b;
    font-style: italic;
    padding: 40px;
  }}
</style>
</head>
<body>
<div id="mindmap-root"></div>

<script>
const data = {data};

function el(tag, cls, text) {{
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}}

function makeDetails(details) {{
  if (!Array.isArray(details) || details.length === 0) return null;
  const wrap = el('div', 'mm-details');
  details.forEach(d => wrap.appendChild(el('div', 'mm-detail', '• ' + String(d))));
  return wrap;
}}

function makeNode(text, cls) {{
  return el('div', 'mm-node ' + cls, text);
}}

function makeToggle() {{
  const t = el('span', 'mm-toggle', '[-]');
  return t;
}}

function buildSubtopic(sub) {{
  const li = el('li');
  const node = makeNode(sub.label || '', 'mm-sub-node');
  const toggle = makeToggle();
  node.appendChild(toggle);

  const details = makeDetails(sub.details);
  const childrenWrap = el('ul');

  if (Array.isArray(sub.children)) {{
    sub.children.forEach(ch => {{
      const chLi = el('li');
      const chNode = makeNode(ch.label || '', 'mm-child-node');
      const chDetails = makeDetails(ch.details);
      chLi.appendChild(chNode);
      if (chDetails) chLi.appendChild(chDetails);
      childrenWrap.appendChild(chLi);
    }});
  }}

  li.appendChild(node);
  if (details) li.appendChild(details);
  if (childrenWrap.children.length) li.appendChild(childrenWrap);

  // Toggle behavior
  let collapsed = false;
  node.addEventListener('click', () => {{
    collapsed = !collapsed;
    toggle.textContent = collapsed ? '[+]' : '[-]';
    if (details) details.style.display = collapsed ? 'none' : '';
    if (childrenWrap.children.length) childrenWrap.style.display = collapsed ? 'none' : '';
  }});

  return li;
}}

function buildBranch(branch) {{
  const li = el('li');
  const node = makeNode(branch.topic || 'Untitled', 'mm-branch-node');
  const toggle = makeToggle();
  node.appendChild(toggle);

  if (branch.summary) {{
    const sum = el('span', 'mm-branch-summary', branch.summary);
    node.appendChild(sum);
  }}

  const ul = el('ul');
  if (Array.isArray(branch.subtopics)) {{
    branch.subtopics.forEach(sub => ul.appendChild(buildSubtopic(sub)));
  }}

  li.appendChild(node);
  if (ul.children.length) li.appendChild(ul);

  // Toggle behavior
  let collapsed = false;
  node.addEventListener('click', () => {{
    collapsed = !collapsed;
    toggle.textContent = collapsed ? '[+]' : '[-]';
    if (ul.children.length) ul.style.display = collapsed ? 'none' : '';
  }});

  return li;
}}

function renderMindmap(data) {{
  const root = document.getElementById('mindmap-root');

  // Header
  const header = el('div', 'mm-header');
  header.appendChild(el('div', 'mm-title', data.title || 'Article'));
  if (data.summary) header.appendChild(el('div', 'mm-summary', data.summary));

  // Controls
  const controls = el('div', 'mm-controls');
  const expandAll = el('button', 'mm-btn', 'Expand All');
  const collapseAll = el('button', 'mm-btn secondary', 'Collapse All');
  controls.appendChild(expandAll);
  controls.appendChild(collapseAll);
  header.appendChild(controls);
  root.appendChild(header);

  if (!data.branches || data.branches.length === 0) {{
    root.appendChild(el('div', 'mm-empty', 'No branches extracted from the article.'));
    return;
  }}

  // Tree
  const tree = el('div', 'mm-tree');
  const rootWrap = el('div', 'mm-root');
  const rootNode = makeNode(data.title || 'Article', 'mm-root-node');
  rootWrap.appendChild(rootNode);
  const rootUl = el('ul');
  data.branches.forEach(b => rootUl.appendChild(buildBranch(b)));
  rootWrap.appendChild(rootUl);
  tree.appendChild(rootWrap);
  root.appendChild(tree);

  // Global controls
  expandAll.addEventListener('click', () => {{
    document.querySelectorAll('.mm-children, .mm-details, .mm-tree ul').forEach(e => {{
      e.style.display = '';
    }});
    document.querySelectorAll('.mm-toggle').forEach(t => t.textContent = '[-]');
  }});
  collapseAll.addEventListener('click', () => {{
    // Collapse everything except the root and first-level branches
    document.querySelectorAll('.mm-tree ul ul').forEach(e => {{
      e.style.display = 'none';
    }});
    document.querySelectorAll('.mm-details').forEach(e => {{
      e.style.display = 'none';
    }});
    document.querySelectorAll('.mm-sub-node .mm-toggle, .mm-child-node .mm-toggle').forEach(t => t.textContent = '[+]');
  }});
}}

renderMindmap(data);
</script>
</body>
</html>"""


def _esc(text: Any) -> str:
    """HTML-escape a value safely."""
    import html as _html
    return _html.escape(str(text)) if text is not None else ""


def _render_details_html(details: Any) -> str:
    """Render a details list as HTML."""
    if not details or not isinstance(details, list):
        return ""
    items = "".join(
        f"<div class='mm-detail'>• {_esc(d)}</div>" for d in details if d
    )
    return f"<div class='mm-details'>{items}</div>" if items else ""


def _render_children_html(children: Any) -> str:
    """Render the 4th-level children as a nested <ul>."""
    if not children or not isinstance(children, list):
        return ""
    items = []
    for ch in children:
        if not isinstance(ch, dict):
            items.append(f"<li><div class='mm-node mm-child-node'>{_esc(ch)}</div></li>")
            continue
        label = ch.get("label") or ""
        details_html = _render_details_html(ch.get("details"))
        items.append(
            f"<li><div class='mm-node mm-child-node'>{_esc(label)}</div>{details_html}</li>"
        )
    return f"<ul>{''.join(items)}</ul>" if items else ""


def _render_subtopic_html(sub: Any) -> str:
    """Render a single subtopic (3rd level) as an <li>."""
    if not isinstance(sub, dict):
        return f"<li><div class='mm-node mm-sub-node'>{_esc(sub)}</div></li>"

    label = sub.get("label") or str(sub)
    details_html = _render_details_html(sub.get("details"))
    children_html = _render_children_html(sub.get("children"))

    return (
        f"<li>"
        f"<div class='mm-node mm-sub-node'>{_esc(label)}</div>"
        f"{details_html}"
        f"{children_html}"
        f"</li>"
    )


def _render_branch_html(branch: Any) -> str:
    """Render a single branch (2nd level) as an <li> with its subtopics."""
    if not isinstance(branch, dict):
        return f"<li><div class='mm-node mm-branch-node'>{_esc(branch)}</div></li>"

    topic = branch.get("topic") or "Untitled"
    summary = branch.get("summary") or ""
    summary_html = (
        f"<span class='mm-branch-summary'>{_esc(summary)}</span>" if summary else ""
    )

    subtopics = branch.get("subtopics") or []
    sub_items = "".join(_render_subtopic_html(s) for s in subtopics if s)
    sub_ul = f"<ul>{sub_items}</ul>" if sub_items else ""

    return (
        f"<li>"
        f"<div class='mm-node mm-branch-node'>{_esc(topic)}{summary_html}</div>"
        f"{sub_ul}"
        f"</li>"
    )


def build_mindmap_embeddable(structure: Dict[str, Any]) -> str:
    """Return a PURE HTML (no JavaScript) rendering of the mind map
    suitable for embedding inside a Gradio gr.HTML component.

    Gradio strips <script> tags from gr.HTML values for security, so
    we generate the entire tree server-side in Python. The result is
    a static, fully-expanded tree with styled nodes and connector
    lines — no client-side JS required.
    """
    if not isinstance(structure, dict):
        structure = {"title": "Article", "branches": []}

    title = structure.get("title") or "Article"
    summary = structure.get("summary") or ""
    branches = structure.get("branches") or []

    summary_html = (
        f"<div class='mm-summary'>{_esc(summary)}</div>" if summary else ""
    )

    if not branches:
        branches_html = "<div class='mm-empty'>No branches extracted from the article.</div>"
    else:
        branch_items = "".join(_render_branch_html(b) for b in branches if b)
        branches_html = f"<ul>{branch_items}</ul>" if branch_items else ""

    return f"""<style>
  .mm-wrap * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  .mm-wrap {{
    background: #0f172a;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Tahoma, sans-serif;
    padding: 24px;
    border-radius: 12px;
    min-height: 200px;
    overflow-x: auto;
  }}
  .mm-wrap .mm-header {{ text-align: center; margin-bottom: 24px; }}
  .mm-wrap .mm-title {{ font-size: 1.8rem; font-weight: 800; color: #818cf8; margin-bottom: 6px; }}
  .mm-wrap .mm-summary {{ color: #94a3b8; font-size: 0.95rem; max-width: 700px; margin: 0 auto; line-height: 1.5; }}
  .mm-wrap .mm-tree {{ display: flex; justify-content: center; margin-top: 20px; }}
  .mm-wrap ul {{ list-style: none; position: relative; padding-left: 28px; margin: 0; }}
  .mm-wrap li {{ position: relative; margin: 6px 0; }}
  .mm-wrap li::before {{ content: ''; position: absolute; left: -14px; top: 14px; width: 14px; height: 1px; background: #334155; }}
  .mm-wrap li::after {{ content: ''; position: absolute; left: -14px; top: 0; width: 1px; height: 14px; background: #334155; }}
  .mm-wrap li:last-child::after {{ height: 14px; }}
  .mm-wrap > .mm-root > ul {{ padding-left: 0; }}
  .mm-wrap > .mm-root > ul > li::before,
  .mm-wrap > .mm-root > ul > li::after {{ display: none; }}
  .mm-wrap .mm-node {{ display: inline-block; padding: 8px 14px; border-radius: 10px; font-size: 0.9rem; line-height: 1.4; max-width: 480px; margin: 2px 0; }}
  .mm-wrap .mm-root-node {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; font-weight: 700; font-size: 1.1rem; padding: 12px 20px; box-shadow: 0 4px 14px rgba(99,102,241,0.4); }}
  .mm-wrap .mm-branch-node {{ background: #1e293b; color: #c7d2fe; font-weight: 600; border: 1px solid #334155; }}
  .mm-wrap .mm-sub-node {{ background: #0f172a; color: #e2e8f0; border: 1px solid #1e293b; }}
  .mm-wrap .mm-child-node {{ background: transparent; color: #94a3b8; border: 1px dashed #334155; font-size: 0.82rem; }}
  .mm-wrap .mm-branch-summary {{ display: block; font-size: 0.75rem; color: #64748b; font-weight: 400; margin-top: 2px; }}
  .mm-wrap .mm-details {{ margin: 4px 0 4px 16px; padding-left: 12px; border-left: 2px solid #334155; }}
  .mm-wrap .mm-detail {{ font-size: 0.8rem; color: #94a3b8; margin: 2px 0; line-height: 1.4; }}
  .mm-wrap .mm-empty {{ text-align: center; color: #64748b; font-style: italic; padding: 40px; }}
</style>
<div class="mm-wrap">
  <div class="mm-header">
    <div class="mm-title">{_esc(title)}</div>
    {summary_html}
  </div>
  <div class="mm-tree">
    <div class="mm-root">
      <div class="mm-node mm-root-node">{_esc(title)}</div>
      {branches_html}
    </div>
  </div>
</div>"""


# ============================================================
# 3) LANGGRAPH NODE
# ============================================================

def mind_map_node(state: ArticleState) -> ArticleState:
    """LangGraph node: extract the mind-map structure and render it
    both as a standalone HTML page (for download) and as embeddable
    HTML (for inline display in the Gradio UI)."""
    english = (
        state.get("seo_article")
        or state.get("edited_article")
        or state.get("article")
        or ""
    )
    persian = state.get("persian_article") or ""

    structure = mind_map_agent(english=english, persian=persian)

    state["mindmap_structure"] = structure

    # Full standalone HTML document (for download / file persistence)
    full_html = build_mindmap(structure)
    with open("mindmap.html", "w", encoding="utf-8") as f:
        f.write(full_html)

    # Embeddable HTML (inner content only) for inline Gradio display
    embed_html = build_mindmap_embeddable(structure)

    state["mindmap_html"] = embed_html
    state["mindmap_image"] = embed_html   # used by gr.HTML in the UI
    state["mindmap_path"] = "mindmap.html"

    return state
