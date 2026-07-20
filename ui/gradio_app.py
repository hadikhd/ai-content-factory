import gradio as gr
from gradio import themes
import json
import re
import html
from typing import Any, Dict, List, cast, MutableMapping
from app.graph import graph
from app.state import ArticleState
from typing import Generator
# Import agents
from agents.title_agent import title_agent
from agents.writer_agent import writer_agent
#from agents.reviewer_agent import reviewer_agent
#from agents.editor_agent import editor_agent
#from agents.seo_agent import seo_agent
#from agents.citation_agent import citation_agent
#from agents.image_agent import image_agent
#from agents.translator_agent import translator_agent
#from agents.mind_map_agent import mind_map_agent
#from ui.timeline import render_timeline
# Import timeline rendering
#from .gradio_app import render_timeline # Assuming gradio_app.py is in the same directory


# ========================
# Report Error
# ========================
import traceback
print(traceback.format_exc())


# ========================
#   Persian RTL DIR CSS
# ========================
css = """
/* ============================================================
   LOCAL FONTS — Inter (English) & Vazirmatn (Persian)
   Served from the /fonts route registered in app() below.
   ============================================================ */
@font-face {
    font-family: 'Inter';
    src: url('/fonts/Inter-Regular.ttf') format('truetype');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Vazirmatn';
    src: url('/fonts/Vazirmatn-Regular.ttf') format('truetype');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Vazirmatn';
    src: url('/fonts/Vazirmatn-Medium.ttf') format('truetype');
    font-weight: 500;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Vazirmatn';
    src: url('/fonts/Vazirmatn-SemiBold.ttf') format('truetype');
    font-weight: 600;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Vazirmatn';
    src: url('/fonts/Vazirmatn-Bold.ttf') format('truetype');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Vazirmatn';
    src: url('/fonts/Vazirmatn-ExtraBold.ttf') format('truetype');
    font-weight: 800;
    font-style: normal;
    font-display: swap;
}

/* Only elements explicitly marked with .rtl */
.rtl {
    direction: rtl;
    text-align: right;
    font-family: 'Vazirmatn', 'Tahoma', sans-serif;
}

/* markdown content inside rtl container */
.rtl .markdown-body,
.rtl .prose,
.rtl p,
.rtl h1,
.rtl h2,
.rtl h3,
.rtl h4,
.rtl h5,
.rtl h6,
.rtl li {
    direction: rtl;
    text-align: right;
    font-family: 'Vazirmatn', 'Tahoma', sans-serif;
}

/* bullet alignment */
.rtl ul,
.rtl ol {
    padding-right: 20px;
    padding-left: 0;
}
.timeline-box {
    background: #0f172a;
    padding: 16px;
    border-radius: 10px;
    font-family: sans-serif;
}

.timeline-step {
    display: flex;
    align-items: center;
    margin: 6px 0;
    font-size: 14px;
}

.timeline-icon {
    width: 22px;
    margin-right: 8px;
}

.timeline-done {
    color: #22c55e;
}

.timeline-running {
    color: #f59e0b;
}

.timeline-wait {
    color: #64748b;
}

.progress-bar {
    height: 6px;
    background: #1e293b;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 12px;
}

.progress-fill {
    height: 6px;
    background: #22c55e;
}
 # =============== sidebar ============
#sidebar {
    background: rgba(128, 128, 128, 0.05);
    padding: 20px;
    border-right: 1px solid rgba(128, 128, 128, 0.2);
    height: 100vh;
}
.rtl { direction: rtl; font-family: 'Vazirmatn', 'Tahoma', sans-serif; text-align: right; }
.word-count-box { font-weight: bold; color: #555; margin-bottom: 10px; }

/* Auto Dark/Light Mode */
@media (prefers-color-scheme: dark) {
    #sidebar { background: #1a1a1a; }
}
# ============= Main Title Style ============

.main-title-wrap {
    text-align: center;
    padding: 30px 20px;
}

.main-title {
    font-size: 48px;
    font-weight: 800;
    color: FFFFFF;
    margin: 0 0 14px 0;
    opacity: 0;
    transform: translateY(12px);
    animation: fadeSlideIn 0.8s ease-out forwards;
}

.main-caption {
    font-size: 20px;
    color: #F59E0B;
    margin: 10px 0 0 0;
    opacity: 0;
    animation: fadeInCaption 1s ease-out forwards;
    animation-delay: 0.45s;
}

@keyframes fadeSlideIn {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInCaption {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}
"""



def rtl_wrap(text: str) -> str:
    if not text:
        return ""
    return f"<div dir='rtl' class='rtl'>{text}</div>"



# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def ensure_json(value: Any):
    """Ensure JSON-safe output."""
    if value is None:
        return []
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", value).strip()
            return json.loads(cleaned)
        except Exception:
            return [{"value": value}]
    return [{"value": str(value)}]


def parse_llm_list(raw_data: Any) -> List[str]:
    if not raw_data:
        return []
    if isinstance(raw_data, list):
        return [item.get("title", str(item)) if isinstance(item, dict) else str(item)
                for item in raw_data]
    if isinstance(raw_data, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", raw_data).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [item.get("title", str(item)) if isinstance(item, dict) else str(item)
                        for item in parsed]
        except Exception:
            pass
        return [line.strip("- ").strip() for line in raw_data.split("\n") if line.strip()]
    return [str(raw_data)]
# ======= pretty json ===============

def prettify_json(data):
    import json
    try:
        if isinstance(data, str):
            obj = json.loads(data)
        else:
            obj = data
        return "```json\n" + json.dumps(obj, indent=4, ensure_ascii=False) + "\n```"
    except:
        return str(data)
def normalize_translation(text: str) -> str:
    """
    Clean and normalize Persian translation output.
    Removes JSON wrappers, brackets, and enforces RTL.
    """
    if not text:
        return ""

    # Remove code fences
    if text.startswith("```"):
        text = text.strip("`").strip()

# Remove bracket artifacts
        text = text.replace("{", "").replace("}", "")
        text = text.replace("[", "").replace("]", "")

# Fix double newlines
        text = text.replace("\n\n", "\n")

    return rtl_wrap(text.strip())    
# --------- Mark down to html -------------
def md_to_html(md: str) -> str:
    """Simple markdown to HTML for streaming (headings, bold, italic, quotes, code, lists)."""

    # Code blocks

    md = re.sub(r"```(.*?)```", r"<pre><code>\1</code></pre>", md, flags=re.S)

    # Headings
    md = re.sub(r"^### (.*)", r"<h3>\1</h3>", md, flags=re.M)
    md = re.sub(r"^## (.*)", r"<h2>\1</h2>", md, flags=re.M)
    md = re.sub(r"^# (.*)", r"<h1>\1</h1>", md, flags=re.M)

    # Blockquotes
    md = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", md, flags=re.M)

    # Lists (* item)
    md = re.sub(r"^\* (.*)", r"<li>\1</li>", md, flags=re.M)
    md = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>", md, flags=re.S)

    # Bold / italic
    md = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", md)
    md = re.sub(r"\*(.*?)\*", r"<em>\1</em>", md)

    # Paragraphs line by line
    lines = md.split("\n")
    html_lines = []
    for line in lines:
        if not line.strip():
            continue
        if line.lstrip().startswith("<"):
            # already HTML (heading, list, blockquote, pre, etc.)
            html_lines.append(line)
        else:
            html_lines.append(f"<p>{line}</p>")

    return "\n".join(html_lines)


def chunk_markdown_stream(markdown_text: str):
    """Split markdown into logical chunks (by blank line) and convert to HTML."""
    for chunk in markdown_text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        yield md_to_html(chunk)
# ---------------------------------------------------------
# Step 1 – Generate Titles
# ---------------------------------------------------------
def extract_titles(text: str) -> list[str]:

    lines = text.split("\n")
    titles: list[str] = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # remove numbering like 1. 1) 1-
        line = re.sub(r"^\d+[\.\-\)]\s*", "", line)

        # ignore short lines
        if len(line.split()) < 3:
            continue

        titles.append(line)

    return titles


def step_titles(topic, article_type, temperature, state):

    state = cast(ArticleState, state or {})

    state["topic"] = topic
    state["article_type"] = article_type
    state["temperature"] = temperature

    new_state = title_agent(state)

    titles = new_state.get("titles") or []

    if not isinstance(titles, list):
        titles = [titles]

    # remove None and ensure str
    titles = [str(t) for t in titles if t]

    # remove duplicates but keep order
    titles = list(dict.fromkeys(titles))

    new_state["titles"] = titles

    status = f"Generated {len(titles)} titles for type: {article_type}"

    return (
        gr.update(
            choices=titles,
            value=titles[0] if titles else None
        ),
        new_state,
        status
    )

# ---------------------------------------------------------
# Step 2 – Writer with Streaming
# ---------------------------------------------------------

def step_writer(selected_title, article_type, temperature, state):

    # Ensure correct type
    state = cast(ArticleState, state or {})

    # Update state fields
    state["selected_title"] = selected_title
    state["article_type"] = article_type
    state["temperature"] = temperature

    # Call the writer agent (returns ArticleState)
    new_state = writer_agent(state)

    # Extract article text safely
    article = new_state.get("article") or ""

    # Render with the article-type-specific style class so the draft
    # follows the typography conventions of the chosen style.
    rendered = render_article_html(article, article_type) if article else ""

    status = f"Draft generated ({article_type})"

    return rendered, new_state, status
# ==========================================
#     Timeline Render Function
# ==========================================
def render_timeline(completed_steps, pipeline_order, step_details=None):
    """
    Render animated timeline with gradient progress, smart icons and collapsible sections.
    step_details: dict[str, str] -> optional human-readable info per step
    """

    if not pipeline_order:
        return "<div class='timeline-box'>No pipeline defined.</div>"

    done = min(len(completed_steps), len(pipeline_order))
    total = len(pipeline_order)
    percent = max(0, min(100, int((done / total) * 100)))
    running_step = pipeline_order[done] if done < total else None

    rows = []
    for step in pipeline_order:
        safe_step = html.escape(str(step))
        detail = html.escape(step_details.get(step, "")) if step_details else ""

        if step in completed_steps:
            icon = "✅"
            cls = "timeline-step timeline-done"
        elif step == running_step:
            icon = "⚙️"
            cls = "timeline-step timeline-running"
        else:
            icon = "🕓"
            cls = "timeline-step timeline-wait"

        collapse_html = (
            f"<div class='timeline-detail'>{detail}</div>" if detail else ""
        )

        rows.append(f"""
            <div class="{cls}">
                <span class="timeline-icon">{icon}</span>
                <span class="timeline-label" onclick="this.nextElementSibling.classList.toggle('open')">
                    {safe_step}
                </span>
                {collapse_html}
            </div>
        """)

    steps_html = "\n".join(rows)

    return f"""
    <style>
    .timeline-box {{
        background: #161616;
        padding: 15px 20px;
        border-radius: 12px;
        font-family: Inter, sans-serif;
        color: #ddd;
        overflow-x: auto;
    }}
    .timeline-container {{
        display: flex;
        flex-direction: column;
        gap: 8px;
    }}
    .progress-bar {{
        background: rgba(255,255,255,0.08);
        border-radius: 6px;
        height: 10px;
        margin-bottom: 8px;
        overflow: hidden;
    }}
    .progress-fill {{
        height: 100%;
        width: 0;
        background: linear-gradient(90deg,#09c6f9,#045de9);
        border-radius: 6px;
        animation: fillAnim 1.4s forwards;
    }}
    @keyframes fillAnim {{
        from {{ width: 0; }}
        to {{ width: {percent}%; }}
    }}
    .timeline-step {{
        padding: 6px 10px;
        border-radius: 8px;
        background: rgba(255,255,255,0.05);
        cursor: pointer;
        transition: background 0.3s ease;
    }}
    .timeline-step:hover {{
        background: rgba(255,255,255,0.12);
    }}
    .timeline-done .timeline-icon {{ color: #4CAF50; }}
    .timeline-running .timeline-icon {{ color: #FFD700; animation: spin 2s infinite linear; }}
    .timeline-wait .timeline-icon {{ color: #777; }}
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    .timeline-label {{
        margin-left: 6px;
        font-weight: 500;
    }}
    .timeline-detail {{
        display: none;
        padding: 8px 12px;
        margin-top: 4px;
        background: rgba(255,255,255,0.06);
        border-radius: 6px;
        font-size: 13px;
        line-height: 1.4em;
        animation: fadeIn 0.4s ease;
    }}
    .timeline-detail.open {{
        display: block;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(-5px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>

    <div class="timeline-box">
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        <div style="font-size:13px;margin-bottom:10px;">
            Progress: {percent}%
        </div>
        <div class="timeline-container">
            {steps_html}
        </div>
    </div>
    """


# ---------------------------------------------------------
# Step 3 – Full Pipeline Streaming
# ---------------------------------------------------------

def step_full_pipeline_stream(
    topic: str,
    article_type: str,
    temperature: float,
    selected_title: str,
    state: ArticleState | None,
):
    import json

    # -----------------------------------------------------
    # Utilities for streaming HTML
    # -----------------------------------------------------
    def md_to_html(md: str) -> str:
        """Very simplified markdown → HTML for real-time streaming."""
        import re

        # Code blocks
        md = re.sub(r"```(.*?)```", r"<pre><code>\1</code></pre>", md, flags=re.S)

        # Headings
        md = re.sub(r"^### (.*)", r"<h3>\1</h3>", md, flags=re.M)
        md = re.sub(r"^## (.*)", r"<h2>\1</h2>", md, flags=re.M)
        md = re.sub(r"^# (.*)", r"<h1>\1</h1>", md, flags=re.M)

        # Blockquotes
        md = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", md, flags=re.M)

        # Lists
        md = re.sub(r"^\* (.*)", r"<li>\1</li>", md, flags=re.M)
        md = re.sub(r"(<li>.*?</li>)", r"<ul>\1</ul>", md, flags=re.S)

        # Bold / italic
        md = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", md)
        md = re.sub(r"\*(.*?)\*", r"<em>\1</em>", md)

        # paragraphs
        lines = md.split("\n")
        html = []
        for ln in lines:
            if not ln.strip():
                continue
            if ln.strip().startswith("<"):
                html.append(ln)
            else:
                html.append(f"<p>{ln}</p>")

        return "\n".join(html)

    def chunk_markdown_stream(text: str):
        """split markdown into chunks for streaming."""
        for chunk in text.split("\n\n"):
            c = chunk.strip()
            if not c:
                continue
            yield md_to_html(c)

    # -----------------------------------------------------
    # Normalize initial state
    # -----------------------------------------------------
    state = cast(ArticleState, state or {})
    state["topic"] = topic
    state["article_type"] = article_type
    state["temperature"] = temperature

    # Preserve the user-selected title from the dropdown so the
    # pipeline reuses it instead of regenerating a new one.
    if selected_title:
        state["selected_title"] = selected_title
        state["title"] = selected_title

    state.setdefault("article", "")
    state.setdefault("edited_article", "")
    state.setdefault("reviewer_feedback", {})
    state.setdefault("editor_improvements", "")
    state.setdefault("seo_report", "")
    state.setdefault("persian_article", "")
    state.setdefault("images", [])
    state.setdefault("citations", [])
    state.setdefault("reference_section", state.get("references", "") or "")
    state.setdefault("mindmap_image", None)
    state.setdefault("completed_steps", [])

    # -----------------------------------------------------
    # TITLE AGENT
    # -----------------------------------------------------
    # Only regenerate titles if the user has NOT already selected one
    # via the "Generate Titles" button. This prevents the full pipeline
    # from overwriting the user's chosen title.
    if not state.get("selected_title"):
        try:
            state = title_agent(state)
        except Exception as ex:
            state["titles"] = [f"Untitled Article ({topic})"]
            state["title_error"] = str(ex)
    else:
        # Make sure `titles` list contains the selected title so the
        # writer agent and downstream nodes can rely on it.
        titles = list(state.get("titles") or [])
        sel = str(state.get("selected_title") or "")
        if sel and sel not in titles:
            titles = [sel] + titles
        state["titles"] = titles
        state["title"] = sel

    # -----------------------------------------------------
    # Buffers
    # -----------------------------------------------------
    # Buffers
    # -----------------------------------------------------
    # CSS class suffix for the article-type-specific typography.
    style_cls = f"style-{style_to_class(article_type)}"

    english_buf = []
    persian_buf = []

    # Helper: render raw markdown text into styled article HTML so the
    # final (non-streaming) yields display as a formatted article instead
    # of raw text. Uses the article-type-specific style class.
    def render_en_html(md_text: str) -> str:
        if not md_text:
            return ""
        return f"<div class='article-container {style_cls}'>{md_to_html(md_text)}</div>"

    def render_fa_html(md_text: str) -> str:
        if not md_text:
            return ""
        return (
            f"<div dir='rtl' class='rtl article-container {style_cls}'>"
            f"{md_to_html(md_text)}</div>"
        )

    english_out = render_en_html(state.get("article") or "")
    edited_article = render_en_html(state.get("edited_article") or "")
    editor_review = render_review_html(state.get("reviewer_feedback") or {})
    editor_improvements = render_improvements_html(state.get("editor_improvements", ""))
    seo_out = render_seo_html(state.get("seo_report") or state.get("seo_json") or {})
    images_out = render_images_html(state.get("images") or [])
    citations_out = render_citations_html(state.get("citations") or [])
    references_out = render_references_html(
        state.get("reference_section") or state.get("references") or ""
    )
    persian_out = render_fa_html(
        normalize_translation(
            state.get("translated_article") or state.get("persian_article") or "")
    )
    mindmap_image = state.get("mindmap_image") or ""

    # timeline
    pipeline_order = [
        "writer",
        "editor_review",
        "editor_improvements",
        "editor",
        "seo",
        "citation",
        "image",
        "translator",
        "mind_map",
    ]
    completed_steps = state.get("completed_steps") or []
    step_details = {}

    # JS snippet that clears the EN stream container AND applies the
    # style class so the rendered article follows the conventions of
    # the selected article type (academic / educational / ...).
    en_init_js = (
        "ProStreamEn.clear();"
        f"const enEl=document.getElementById('pro-article-en');"
        f"if(enEl){{enEl.className='article-container {style_cls}';}}"
    )
    fa_init_js = (
        "ProStreamFa.clear();"
        "const faEl=document.getElementById('pro-article-fa');"
        "if(faEl){faEl.className='rtl article-container " + style_cls + "';faEl.setAttribute('dir','rtl');}"
    )

    # -----------------------------------------------------
    # FIRST YIELD: Initialize UI + Clear EN/FA Containers
    # -----------------------------------------------------
    yield (
        gr.update(_js=en_init_js),                              # 1 EN
        safe_str(editor_review),                               # 2
        safe_str(editor_improvements),                         # 3
        safe_str(edited_article),                              # 4
        safe_str(seo_out),                                     # 5
        safe_str(images_out),                                  # 6
        safe_str(citations_out),                               # 7
        safe_str(references_out),                              # 8
        gr.update(value=None, _js=fa_init_js),                 # 9 FA
        mindmap_image,                                         # 10
        render_timeline(completed_steps, pipeline_order, step_details),  # 11
        state,                                                 # 12
        "Pipeline started...",                                 # 13
    )

    # -----------------------------------------------------
    # STREAM LOOP
    # -----------------------------------------------------
    try:
        for event in graph.stream(state):
            node = list(event.keys())[0]
            data = event[node] or {}

            # Timeline
            if node not in completed_steps:
                completed_steps.append(node)
                step_details[node] = f"Completed: {node}"
                state["completed_steps"] = completed_steps

            # ---------------------- Writer ----------------------
            if node == "writer" and "article" in data:
                text = data["article"]
                state["article"] = text
                english_buf.append(text)
                full_eng = "\n".join(english_buf)

                # Stream chunks into JS
                for html_chunk in chunk_markdown_stream(text):
                    yield (
                        gr.update(_js=f"ProStreamEn.append({json.dumps(html_chunk)})"),
                        safe_str(editor_review),
                        safe_str(editor_improvements),
                        safe_str(edited_article),
                        safe_str(seo_out),
                        safe_str(images_out),
                        safe_str(citations_out),
                        safe_str(references_out),
                        safe_str(persian_out),
                        mindmap_image,
                        render_timeline(completed_steps, pipeline_order, step_details),
                        state,
                        f"Streaming writer…",
                    )

                english_out = render_en_html(full_eng)

            # ---------------------- Editor Review ----------------------
            if node == "editor_review":
                for key in ["reviewer_feedback","review_summary","final_recommendation",
                            "review_scores","review_issues"]:
                    if key in data:
                        state[key] = data[key]

                editor_review = render_review_html(state.get("reviewer_feedback") or {})

            # ---------------------- Editor Improvements ----------------------
            if node == "editor_improvements" and "editor_improvements" in data:
                state["editor_improvements"] = data["editor_improvements"]
                editor_improvements = render_improvements_html(state.get("editor_improvements", ""))

            # ---------------------- Editor ----------------------
            if node == "editor":
                if "edited_article" in data:
                    state["edited_article"] = data["edited_article"]
                edited_article = render_en_html(state.get("edited_article") or "")

            # ---------------------- SEO ----------------------
            if node == "seo":
                for key in ("seo_article","seo_json","seo_report","seo_score"):
                    if key in data:
                        state[key] = data[key]

                seo_out = render_seo_html(
                    state.get("seo_report") or state.get("seo_json") or {}
                )

            # ---------------------- Translator (RTL Stream) ----------------------
            if node == "translator":
                # store
                if "persian_article" in data:
                    text = data["persian_article"]
                elif "translated_article" in data:
                    text = data["translated_article"]
                else:
                    text = ""

                state["persian_article"] = text
                # Capture the style detected by the translator so the
                # post-pipeline .then() callbacks can display it.
                if "detected_style" in data:
                    state["detected_style"] = data["detected_style"]
                persian_buf.append(text)
                full_fa = "\n".join(persian_buf)

                # stream chunks to FA renderer
                for html_chunk in chunk_markdown_stream(text):
                    yield (
                        safe_str(english_out),
                        safe_str(editor_review),
                        safe_str(editor_improvements),
                        safe_str(edited_article),
                        safe_str(seo_out),
                        safe_str(images_out),
                        safe_str(citations_out),
                        safe_str(references_out),
                        gr.update(value=None, _js=f"ProStreamFa.append({json.dumps(html_chunk)})"),
                        mindmap_image,
                        render_timeline(completed_steps, pipeline_order, step_details),
                        state,
                        f"Streaming Persian…",
                    )

                persian_out = render_fa_html(full_fa)

            # ---------------------- Mind Map ----------------------
            if node == "mind_map":
                for key in ("mindmap_image","mindmap_html","mindmap_structure","mindmap_path"):
                    if key in data:
                        state[key] = data[key]
                mindmap_image = state.get("mindmap_image") or ""

            # ---------------------- Assets ----------------------
            for key in ("images", "citations", "reference_section", "references",
                        "detected_style"):
                if key in data:
                    state[key] = data[key]
            # Re-render the pretty cards whenever the underlying data
            # changes so the user sees updated HTML instead of raw JSON.
            if "images" in data:
                images_out = render_images_html(state.get("images") or [])
            if "citations" in data:
                citations_out = render_citations_html(state.get("citations") or [])
            if "reference_section" in data or "references" in data:
                references_out = render_references_html(
                    state.get("reference_section") or state.get("references") or ""
                )

            # ---------------------- Standard periodic yield ----------------------
            yield (
                safe_str(english_out),
                safe_str(editor_review),
                safe_str(editor_improvements),
                safe_str(edited_article),
                safe_str(seo_out),
                safe_str(images_out),
                safe_str(citations_out),
                safe_str(references_out),
                safe_str(persian_out),
                mindmap_image,
                render_timeline(completed_steps, pipeline_order, step_details),
                state,
                f"Streaming: {node}",
            )

        # -----------------------------------------------------
        # FINAL YIELD
        # -----------------------------------------------------
        final_fa = render_fa_html("\n".join(persian_buf)) if persian_buf else render_fa_html(
            normalize_translation(state.get("persian_article") or "")
        )

        # Final re-render of the pretty cards from the final state.
        final_images = render_images_html(state.get("images") or [])
        final_citations = render_citations_html(state.get("citations") or [])
        final_seo = render_seo_html(state.get("seo_report") or state.get("seo_json") or {})
        final_review = render_review_html(state.get("reviewer_feedback") or {})
        final_improvements = render_improvements_html(state.get("editor_improvements", ""))
        final_references = render_references_html(
            state.get("reference_section") or state.get("references") or ""
        )

        yield (
            safe_str(english_out),
            safe_str(final_review),
            safe_str(final_improvements),
            safe_str(edited_article),
            safe_str(final_seo),
            safe_str(final_images),
            safe_str(final_citations),
            safe_str(final_references),
            safe_str(final_fa),
            mindmap_image,
            render_timeline(completed_steps, pipeline_order, step_details),
            state,
            f"Pipeline finished ({article_type}, temp={temperature})",
        )

    except Exception as e:
        yield (
            "", "", "", "", "",
            render_images_html([]),
            render_citations_html([]),
            render_references_html(""),
            "",
            None,
            render_timeline(completed_steps, pipeline_order, step_details),
            state,
            f"❌ Pipeline error: {e}",
        )

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------


def animated_title(article_type):
    captions = {
        "Educational": "Write a clear educational article with explanations and examples.",
        "Academic": "Write a formal academic article with structured sections and neutral tone.",
        "Technical Report":"Write a step-by-step technical guide with practical implementation details.",
        "Blog Post": "Write an engaging Medium-style blog post with a friendly tone.",
    }

    titles = {
        "Educational": "📘 Educational Article",
        "Academic": "🎓 Academic Article",
        "Technical Report": "⚙️ Technical Report",
        "Blog Post": "✍️ Blog Post",
    }

    title = html.escape(titles.get(article_type, "AI Article Generator"))
    caption = html.escape(captions.get(article_type, ""))

    return f"""
    <div class="main-title-wrap">
        <h1 class="main-title">{title}</h1>
        <p class="main-caption">{caption}</p>
    </div>
    """



def style_to_class(article_type: str) -> str:
    """Convert an article_type label into a CSS class suffix used by
    .article-container.style-<suffix> rules. Falls back to blog_post."""
    if not article_type:
        return "blog_post"
    s = article_type.strip().lower().replace(" ", "_")
    aliases = {
        "blog": "blog_post",
        "blogpost": "blog_post",
        "tech": "technical_report",
        "technical": "technical_report",
        "report": "technical_report",
        "edu": "educational",
    }
    return aliases.get(s, s)


def render_article_html(text: str, article_type: str = ""):
    style_cls = f"style-{style_to_class(article_type)}"
    try:
        import markdown
        body = markdown.markdown(
            text,
            extensions=["extra", "tables", "fenced_code"]
        )
    except ImportError:
        # Fallback to the regex-based renderer if the `markdown`
        # package is not installed.
        body = md_to_html(text)
    return f"<div class='article-container {style_cls}'>{body}</div>"


# ============================================================
#  Pretty renderers for SEO / Citations / Image prompts
#  These convert raw JSON / list data into human-friendly HTML
#  cards so the user sees a polished report instead of raw JSON.
# ============================================================

def _esc(text: Any) -> str:
    """HTML-escape a value safely."""
    return html.escape(str(text)) if text is not None else ""


def render_seo_html(seo_data: Any) -> str:
    """Render the SEO report as a styled HTML card.

    Accepts either:
      - a JSON string
      - a dict with keys: seo_article, keywords, seo_score
    """
    if not seo_data:
        return "<div class='seo-card empty'>No SEO report available.</div>"

    # Parse JSON string if needed
    if isinstance(seo_data, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", seo_data).strip()
            seo_data = json.loads(cleaned)
        except Exception:
            return f"<div class='seo-card'>{_esc(seo_data)}</div>"

    if not isinstance(seo_data, dict):
        return f"<div class='seo-card'>{_esc(seo_data)}</div>"

    score = seo_data.get("seo_score", 0)
    try:
        score = int(score)
    except Exception:
        score = 0

    # Color based on score
    if score >= 80:
        score_color, score_label = "#22c55e", "Excellent"
    elif score >= 60:
        score_color, score_label = "#f59e0b", "Good"
    elif score >= 40:
        score_color, score_label = "#f97316", "Needs Work"
    else:
        score_color, score_label = "#ef4444", "Poor"

    keywords = seo_data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    if not isinstance(keywords, list):
        keywords = [str(keywords)]

    keyword_chips = "".join(
        f"<span class='seo-keyword'>{_esc(k)}</span>" for k in keywords if k
    ) or "<span class='seo-empty'>No keywords extracted</span>"

    article = seo_data.get("seo_article") or seo_data.get("article") or ""

    return f"""
    <div class="seo-card">
        <div class="seo-header">
            <h3>🔍 SEO Report</h3>
            <div class="seo-score-wrap">
                <div class="seo-score" style="color:{score_color}; border-color:{score_color};">
                    {score}
                </div>
                <span class="seo-score-label" style="color:{score_color};">{score_label}</span>
            </div>
        </div>
        <div class="seo-section">
            <h4>Keywords</h4>
            <div class="seo-keywords">{keyword_chips}</div>
        </div>
        {f'<div class="seo-section"><h4>Optimized Article Preview</h4><div class="seo-article-preview">{_esc(article[:500])}{"…" if len(article) > 500 else ""}</div></div>' if article else ''}
    </div>
    """


def render_citations_html(citations: Any) -> str:
    """Render citations as a styled numbered list instead of raw JSON.

    Accepts:
      - a list of strings
      - a list of dicts (with keys like title, author, year, url)
      - a JSON string
    """
    if not citations:
        return "<div class='citations-card empty'>No citations extracted.</div>"

    # Parse JSON string if needed
    if isinstance(citations, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", citations).strip()
            citations = json.loads(cleaned)
        except Exception:
            citations = [citations]

    if isinstance(citations, dict):
        # If the LLM returned {"citations": [...], "reference_section": "..."}
        citations = citations.get("citations") or [citations]

    if not isinstance(citations, list):
        citations = [citations]

    items = []
    for i, cit in enumerate(citations, 1):
        if isinstance(cit, dict):
            title = cit.get("title") or cit.get("name") or ""
            author = cit.get("author") or cit.get("authors") or ""
            year = cit.get("year") or cit.get("date") or ""
            url = cit.get("url") or cit.get("link") or ""
            source = cit.get("source") or cit.get("publisher") or ""

            parts = []
            if author:
                parts.append(f"<span class='cit-author'>{_esc(author)}</span>")
            if year:
                parts.append(f"<span class='cit-year'>({_esc(year)})</span>")
            if title:
                parts.append(f"<span class='cit-title'>{_esc(title)}</span>")
            if source:
                parts.append(f"<span class='cit-source'>{_esc(source)}</span>")
            if url:
                parts.append(
                    f"<a class='cit-url' href='{_esc(url)}' target='_blank'>{_esc(url)}</a>"
                )

            body = " ".join(parts) if parts else _esc(str(cit))
        else:
            body = _esc(str(cit))

        items.append(f"<li class='citation-item'>{body}</li>")

    return f"""
    <div class="citations-card">
        <h3>📚 Citations</h3>
        <ol class="citations-list">
            {"".join(items)}
        </ol>
    </div>
    """


def render_images_html(images: Any) -> str:
    """Render image prompts as styled cards instead of raw JSON.

    Accepts:
      - a list of strings (prompts)
      - a list of dicts
      - a JSON string
    """
    if not images:
        return "<div class='images-card empty'>No image prompts generated.</div>"

    # Parse JSON string if needed
    if isinstance(images, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", images).strip()
            images = json.loads(cleaned)
        except Exception:
            images = [images]

    if not isinstance(images, list):
        images = [images]

    cards = []
    for i, img in enumerate(images, 1):
        if isinstance(img, dict):
            prompt = img.get("prompt") or img.get("description") or ""
            style = img.get("style") or ""
            extra = ""
            if style:
                extra = f"<span class='img-style'>{_esc(style)}</span>"
        else:
            prompt = str(img)
            extra = ""

        cards.append(f"""
            <div class="image-prompt-card">
                <div class="img-prompt-num">{i}</div>
                <div class="img-prompt-body">
                    <p class="img-prompt-text">{_esc(prompt)}</p>
                    {extra}
                </div>
            </div>
        """)

    return f"""
    <div class="images-card">
        <h3>🖼️ Image Prompts</h3>
        <div class="image-prompts-grid">
            {"".join(cards)}
        </div>
    </div>
    """


def render_review_html(review_data: Any) -> str:
    """Render the reviewer feedback as a styled HTML card.

    Accepts:
      - a dict with keys: summary, scores, issues, needs_edit
      - a JSON string
    """
    if not review_data:
        return "<div class='review-card empty'>No review available.</div>"

    if isinstance(review_data, str):
        try:
            cleaned = re.sub(r"```(?:json)?\s*|```", "", review_data).strip()
            review_data = json.loads(cleaned)
        except Exception:
            return f"<div class='review-card'>{_esc(review_data)}</div>"

    if not isinstance(review_data, dict):
        return f"<div class='review-card'>{_esc(review_data)}</div>"

    summary = review_data.get("summary") or review_data.get("review_summary") or ""
    scores = review_data.get("scores") or review_data.get("review_scores") or {}
    issues = review_data.get("issues") or review_data.get("review_issues") or []
    needs_edit = bool(review_data.get("needs_edit", False))

    # Score badges
    score_items = []
    if isinstance(scores, dict):
        for label, value in scores.items():
            try:
                v = int(value)
            except Exception:
                v = 0
            if v >= 80:
                color = "#22c55e"
            elif v >= 60:
                color = "#f59e0b"
            elif v >= 40:
                color = "#f97316"
            else:
                color = "#ef4444"
            pretty_label = label.replace("_", " ").title().replace(" Score", "")
            score_items.append(
                f"<div class='review-score-item'>"
                f"<span class='review-score-label'>{_esc(pretty_label)}</span>"
                f"<span class='review-score-value' style='color:{color};'>{v}</span>"
                f"</div>"
            )

    scores_html = (
        f"<div class='review-scores'>{''.join(score_items)}</div>"
        if score_items else ""
    )

    # Issues list
    issues_html = ""
    if issues:
        if isinstance(issues, str):
            issues = [issues]
        if isinstance(issues, list):
            issue_items = []
            for iss in issues:
                if isinstance(iss, dict):
                    issue = iss.get("issue") or iss.get("description") or ""
                    severity = iss.get("severity") or "moderate"
                    suggestion = iss.get("suggestion") or ""

                    sev_color = {
                        "minor": "#f59e0b",
                        "moderate": "#f97316",
                        "major": "#ef4444",
                        "critical": "#dc2626",
                    }.get(str(severity).lower(), "#f97316")

                    issue_items.append(f"""
                        <div class='review-issue'>
                            <span class='review-issue-sev' style='background:{sev_color};'>{_esc(severity)}</span>
                            <span class='review-issue-text'>{_esc(issue)}</span>
                            {f"<span class='review-issue-fix'>💡 {_esc(suggestion)}</span>" if suggestion else ""}
                        </div>
                    """)
                else:
                    issue_items.append(
                        f"<div class='review-issue'><span class='review-issue-text'>{_esc(iss)}</span></div>"
                    )
            issues_html = f"<div class='review-issues'>{''.join(issue_items)}</div>"

    status_badge = (
        "<span class='review-status needs-edit'>⚠️ Needs Editing</span>"
        if needs_edit else
        "<span class='review-status good'>✅ Good to Go</span>"
    )

    return f"""
    <div class="review-card">
        <div class="review-header">
            <h3>📋 Editor Review</h3>
            {status_badge}
        </div>
        {f"<p class='review-summary'>{_esc(summary)}</p>" if summary else ""}
        {scores_html}
        {issues_html}
    </div>
    """


def render_improvements_html(improvements: Any) -> str:
    """Render editor improvements as a styled HTML list.

    Accepts:
      - a string (possibly newline or bullet separated)
      - a list of strings
      - a JSON string
    """
    if not improvements:
        return "<div class='improvements-card empty'>No suggested improvements.</div>"

    # Parse JSON string if needed
    if isinstance(improvements, str):
        cleaned = improvements.strip()
        if cleaned.startswith("[") or cleaned.startswith("{"):
            try:
                cleaned2 = re.sub(r"```(?:json)?\s*|```", "", cleaned).strip()
                improvements = json.loads(cleaned2)
            except Exception:
                pass
        if isinstance(improvements, str):
            # Split by newlines or bullets
            parts = [p.strip().lstrip("-*• ").strip() for p in improvements.split("\n") if p.strip()]
            improvements = parts if parts else [improvements]

    if isinstance(improvements, dict):
        # Could be {"improvements": [...]} or {"feedback": "..."}
        if "improvements" in improvements:
            improvements = improvements["improvements"]
        elif "feedback" in improvements:
            improvements = [improvements["feedback"]]
        else:
            improvements = [str(improvements)]

    if not isinstance(improvements, list):
        improvements = [str(improvements)]

    items = "".join(
        f"<li class='improvement-item'>{_esc(str(item))}</li>"
        for item in improvements if item
    )

    return f"""
    <div class="improvements-card">
        <h3>💡 Suggested Improvements</h3>
        <ul class="improvements-list">
            {items}
        </ul>
    </div>
    """


def render_references_html(reference_data: Any) -> str:
    """Render the reference section as styled HTML instead of raw JSON.

    Accepts:
      - a plain-text reference string (rendered as-is, line by line)
      - a JSON string (parsed and rendered as a numbered list)
      - a list of strings / dicts
    """
    if not reference_data:
        return "<div class='references-card empty'>No references available.</div>"

    # If it's already a clean plain-text string (not JSON), render it
    # line by line so the user sees formatted references.
    if isinstance(reference_data, str):
        text = reference_data.strip()
        if not text:
            return "<div class='references-card empty'>No references available.</div>"

        # Try to parse as JSON — if it succeeds, it's structured data
        if text.startswith("{") or text.startswith("["):
            try:
                cleaned = re.sub(r"```(?:json)?\s*|```", "", text).strip()
                parsed = json.loads(cleaned)
                reference_data = parsed
            except Exception:
                # Not valid JSON — treat as plain text
                pass

        if isinstance(reference_data, str):
            # Plain text: split into lines and render each as a reference entry
            lines = [ln.strip() for ln in reference_data.split("\n") if ln.strip()]
            # Strip common numbering prefixes (1. , [1], etc.)
            cleaned_lines = []
            for ln in lines:
                ln = re.sub(r"^\[?\d+\]?\.?\s*", "", ln)
                if ln:
                    cleaned_lines.append(ln)
            items = "".join(
                f"<li class='ref-item'>{_esc(ln)}</li>" for ln in cleaned_lines
            )
            return f"""
            <div class="references-card">
                <h3>📚 References</h3>
                <ol class="references-list">
                    {items}
                </ol>
            </div>
            """

    # Structured data (list or dict)
    if isinstance(reference_data, dict):
        # Could be {"reference_section": "...", "citations": [...]}
        if "reference_section" in reference_data and isinstance(reference_data["reference_section"], str):
            return render_references_html(reference_data["reference_section"])
        if "citations" in reference_data:
            return render_citations_html(reference_data["citations"])
        # Fallback: render the dict values
        reference_data = list(reference_data.values())

    if not isinstance(reference_data, list):
        reference_data = [reference_data]

    items = []
    for ref in reference_data:
        if isinstance(ref, dict):
            parts = []
            for k in ("author", "authors", "title", "year", "date", "url", "link", "source", "publisher"):
                if k in ref and ref[k]:
                    parts.append(f"<span class='ref-{k}'>{_esc(ref[k])}</span>")
            items.append(f"<li class='ref-item'>{' '.join(parts) or _esc(str(ref))}</li>")
        else:
            items.append(f"<li class='ref-item'>{_esc(str(ref))}</li>")

    return f"""
    <div class="references-card">
        <h3>📚 References</h3>
        <ol class="references-list">
            {"".join(items)}
        </ol>
    </div>
    """


def render_style_color(style):
    style = (style or "").lower().strip()
    # Map the translator's detected style labels to colors.
    # The translator returns: academic | research | engineering | blog | simple
    colors = {
        "academic": "#2958a5",
        "research": "#7c3aed",
        "engineering": "#ff8c00",
        "blog": "#8a2be2",
        "simple": "#3aa75f",
        # Backward-compatible aliases for UI article_type labels
        "technical report": "#ff8c00",
        "blog post": "#8a2be2",
        "educational": "#3aa75f",
    }
    color = colors.get(style, "#666")
    # Pretty label
    pretty = {
        "academic": "Academic",
        "research": "Research",
        "engineering": "Engineering",
        "blog": "Blog",
        "simple": "Simple",
        "technical report": "Technical Report",
        "blog post": "Blog Post",
        "educational": "Educational",
    }.get(style, style.title() or "Unknown")
    return f"""
    <div style='padding:10px;border-radius:8px;font-size:16px;
                font-weight:bold;color:white;background:{color};'>
        Detected Style: {pretty}
    </div>
    """

def make_seo_style_card(style):
    style = (style or "").lower().strip()
    pretty = {
        "academic": "Academic",
        "research": "Research",
        "engineering": "Engineering",
        "blog": "Blog",
        "simple": "Simple",
    }.get(style, style.title() or "Unknown")
    return f"""
    <div style="
        border:1px solid #ddd;
        border-radius:12px;
        padding:15px;
        background:white;
        box-shadow:0 2px 6px rgba(0,0,0,0.1);
        font-family:Arial;
        margin-bottom:20px;
    ">
        <h3 style="margin-top:0;color:#444;">Detected Writing Style</h3>
        <p style="font-size:18px;font-weight:bold;color:#111;">{pretty}</p>
        <p style="color:#666;">
            این سبک توسط LLM تشخیص داده شده و برای انتخاب بهترین پرامپت ترجمه استفاده شده است.
        </p>
    </div>
    """
# ================= UI ==================================
def app():
    with gr.Blocks(theme=themes.Citrus(),css=css) as demo:
        global_article_style = gr.HTML(
        """
            <style>

            :root {
            --font-body: 'Inter', 'Vazirmatn', sans-serif;
            --font-serif: 'Inter', 'Georgia', serif;
            --font-mono: 'JetBrains Mono', 'Consolas', monospace;
            --font-fa: 'Vazirmatn', 'Tahoma', sans-serif;

            --color-bg: #ffffff;
            --color-text: #222222;
            --color-soft: #555555;
            --color-accent: #2b6cb0;
            --color-border: #e5e7eb;

            --max-width: 780px;
            }

            @media (prefers-color-scheme: dark) {
            :root {
            --color-bg: #1a1a1a;
            --color-text: #dddddd;
            --color-soft: #b3b3b3;
            --color-accent: #63b3ed;
            --color-border: #2a2a2a;
            }
            }

            /* ARTICLE MAIN CONTAINER */

            #pro-article-en.article-container {
            max-width: var(--max-width);
            margin: 40px auto;
            background: var(--color-bg);
            color: var(--color-text);
            padding: 35px 40px;
            font-family: var(--font-body);
            font-size: 19px;
            line-height: 1.85;
            letter-spacing: -0.01em;
            }

            /* HEADERS */

            .article-container h1 {
            font-size: 2.4rem;
            font-weight: 800;
            margin-bottom: 20px;
            font-family: var(--font-serif);
            }

            .article-container h2 {
            font-size: 1.9rem;
            font-weight: 700;
            margin-top: 50px;
            margin-bottom: 18px;
            }

            .article-container h3 {
            font-size: 1.55rem;
            font-weight: 600;
            margin-top: 38px;
            margin-bottom: 14px;
            }

            /* PARAGRAPH */

            .article-container p {
            margin: 18px 0;
            color: var(--color-text);
            }

            /* BLOCKQUOTE — Medium Style */

            .article-container blockquote {
            border-left: 4px solid var(--color-accent);
            margin: 25px 0;
            padding-left: 18px;
            font-style: italic;
            color: var(--color-soft);
            }

            /* CODE BLOCK — Notion Style */

            .article-container pre {
            background: #f7f7f7;
            color: #111;
            padding: 14px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 0.95rem;
            border: 1px solid #e5e5e5;
            }

            @media (prefers-color-scheme: dark) {
            .article-container pre {
            background: #2b2b2b;
            color: #eee;
            border-color: #3a3a3a;
            }
            }

            /* INLINE CODE */
            .article-container code {
            background: #eee;
            padding: 3px 5px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 0.92rem;
            }
            @media (prefers-color-scheme: dark) {
            .article-container code {
            background: #333;
            }
            }

            /* LINKS — Substack Style */

            .article-container a {
            color: var(--color-accent);
            text-decoration: none;
            }
            .article-container a:hover {
            text-decoration: underline;
            }

            /* LISTS */

            .article-container ul,
            .article-container ol {
            margin-top: 16px;
            margin-bottom: 18px;
            padding-left: 28px;
            }

            .article-container li {
            margin-bottom: 8px;
            }

            /* IMAGES */

            .article-container img {
            max-width: 100%;
            border-radius: 10px;
            margin: 25px 0;
            }

            /* IMAGE CAPTION — Medium Style */
            .article-container figure {
            text-align: center;
            margin: 30px auto;
            }
            .article-container figcaption {
            font-size: 0.9rem;
            color: var(--color-soft);
            margin-top: 8px;
            }

            /* TABLES */

            .article-container table {
            width: 100%;
            border-collapse: collapse;
            margin: 28px 0;
            }

            .article-container th,
            .article-container td {
            padding: 10px 14px;
            border: 1px solid var(--color-border);
            }

            .article-container th {
            background: #f6f6f6;
            font-weight: 600;
            }

            @media (prefers-color-scheme: dark) {
            .article-container th {
            background: #2a2a2a;
            }

            /* ============================================================
               ARTICLE STYLE VARIANTS
               Each variant adapts typography & layout to match the
               conventions of its article type so the output looks
               expert and publication-ready.
               ============================================================ */

            /* ---- ACADEMIC ---- */
            .article-container.style-academic {
            font-family: 'Inter', 'Georgia', serif;
            font-size: 17px;
            line-height: 1.7;
            text-align: justify;
            hyphens: auto;
            }
            .article-container.style-academic h1 {
            font-family: 'Inter', 'Georgia', serif;
            font-weight: 700;
            font-size: 2rem;
            text-align: left;
            }
            .article-container.style-academic h2,
            .article-container.style-academic h3 {
            font-family: 'Inter', 'Georgia', serif;
            font-weight: 700;
            }
            .article-container.style-academic p {
            text-indent: 1.5em;
            margin: 12px 0;
            }
            .article-container.style-academic blockquote {
            font-style: normal;
            border-left: 3px solid #888;
            color: #444;
            }

            /* ---- EDUCATIONAL ---- */
            .article-container.style-educational {
            font-family: 'Inter', sans-serif;
            font-size: 18px;
            line-height: 1.8;
            }
            .article-container.style-educational h2 {
            border-bottom: 2px solid var(--color-accent);
            padding-bottom: 6px;
            }
            .article-container.style-educational h3 {
            color: var(--color-accent);
            }
            .article-container.style-educational blockquote {
            background: rgba(43, 108, 176, 0.06);
            border-left: 4px solid var(--color-accent);
            padding: 10px 14px;
            border-radius: 6px;
            }
            .article-container.style-educational code {
            font-size: 0.95rem;
            }

            /* ---- TECHNICAL REPORT ---- */
            .article-container.style-technical_report {
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            line-height: 1.65;
            }
            .article-container.style-technical_report h1 {
            font-size: 2.1rem;
            border-bottom: 3px solid #ff8c00;
            padding-bottom: 8px;
            }
            .article-container.style-technical_report h2 {
            color: #ff8c00;
            font-weight: 700;
            }
            .article-container.style-technical_report pre {
            border-left: 3px solid #ff8c00;
            }
            .article-container.style-technical_report table {
            font-size: 0.95rem;
            }

            /* ---- BLOG POST ---- */
            .article-container.style-blog_post {
            font-family: 'Inter', sans-serif;
            font-size: 19px;
            line-height: 1.85;
            }
            .article-container.style-blog_post h1 {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            }
            .article-container.style-blog_post h2 {
            font-size: 1.9rem;
            margin-top: 40px;
            }
            .article-container.style-blog_post blockquote {
            font-size: 1.15rem;
            border-left: 4px solid #8a2be2;
            color: #555;
            }
            .article-container.style-blog_post p:first-of-type {
            font-size: 1.15rem;
            color: var(--color-soft);
            }

            /* ============================================================
               SEO / CITATIONS / IMAGE PROMPTS — Pretty Cards
               ============================================================ */
            .seo-card, .citations-card, .images-card {
            font-family: 'Inter', sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .seo-card.empty, .citations-card.empty, .images-card.empty {
            color: var(--color-soft);
            font-style: italic;
            text-align: center;
            }
            .seo-card h3, .citations-card h3, .images-card h3 {
            margin-top: 0;
            font-size: 1.3rem;
            font-weight: 700;
            }
            .seo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            }
            .seo-score-wrap {
            display: flex;
            flex-direction: column;
            align-items: center;
            }
            .seo-score {
            font-size: 2rem;
            font-weight: 800;
            border: 3px solid;
            border-radius: 50%;
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            }
            .seo-score-label {
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            }
            .seo-section { margin: 14px 0; }
            .seo-section h4 {
            font-size: 1rem;
            font-weight: 600;
            margin: 0 0 8px 0;
            color: var(--color-soft);
            }
            .seo-keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            }
            .seo-keyword {
            background: rgba(43, 108, 176, 0.1);
            color: var(--color-accent);
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.9rem;
            font-weight: 500;
            }
            .seo-empty { color: var(--color-soft); font-style: italic; }
            .seo-article-preview {
            background: rgba(0,0,0,0.03);
            padding: 12px;
            border-radius: 8px;
            font-size: 0.9rem;
            line-height: 1.6;
            max-height: 200px;
            overflow-y: auto;
            }

            /* Citations */
            .citations-list {
            margin: 0;
            padding-left: 24px;
            }
            .citation-item {
            margin-bottom: 12px;
            line-height: 1.6;
            }
            .cit-author { font-weight: 600; }
            .cit-year { color: var(--color-soft); margin: 0 4px; }
            .cit-title { font-style: italic; }
            .cit-source { color: var(--color-soft); }
            .cit-url {
            display: block;
            color: var(--color-accent);
            text-decoration: none;
            font-size: 0.85rem;
            word-break: break-all;
            }
            .cit-url:hover { text-decoration: underline; }

            /* Image prompts */
            .image-prompts-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
            }
            .image-prompt-card {
            display: flex;
            gap: 12px;
            background: rgba(0,0,0,0.03);
            border-radius: 10px;
            padding: 14px;
            border-left: 4px solid #8a2be2;
            }
            .img-prompt-num {
            flex-shrink: 0;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #8a2be2;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            }
            .img-prompt-body { flex: 1; }
            .img-prompt-text {
            margin: 0;
            line-height: 1.6;
            }
            .img-style {
            display: inline-block;
            margin-top: 6px;
            background: rgba(138, 43, 226, 0.1);
            color: #8a2be2;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
            }

            /* Review card */
            .review-card {
            font-family: 'Inter', sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .review-card.empty { color: var(--color-soft); font-style: italic; text-align: center; }
            .review-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            }
            .review-header h3 { margin: 0; font-size: 1.3rem; font-weight: 700; }
            .review-status {
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            }
            .review-status.needs-edit { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
            .review-status.good { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
            .review-summary {
            margin: 0 0 14px 0;
            line-height: 1.6;
            color: var(--color-text);
            }
            .review-scores {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 14px;
            }
            .review-score-item {
            background: rgba(0,0,0,0.03);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            }
            .review-score-label {
            display: block;
            font-size: 0.75rem;
            color: var(--color-soft);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
            }
            .review-score-value {
            display: block;
            font-size: 1.5rem;
            font-weight: 800;
            }
            .review-issues {
            display: flex;
            flex-direction: column;
            gap: 8px;
            }
            .review-issue {
            background: rgba(0,0,0,0.03);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            }
            .review-issue-sev {
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            }
            .review-issue-text { flex: 1; line-height: 1.5; }
            .review-issue-fix {
            display: block;
            width: 100%;
            color: var(--color-soft);
            font-size: 0.85rem;
            margin-top: 4px;
            }

            /* Improvements card */
            .improvements-card {
            font-family: 'Inter', sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .improvements-card.empty { color: var(--color-soft); font-style: italic; text-align: center; }
            .improvements-card h3 { margin-top: 0; font-size: 1.2rem; font-weight: 700; }
            .improvements-list { margin: 0; padding-left: 20px; }
            .improvement-item {
            margin-bottom: 8px;
            line-height: 1.6;
            }

            /* References card */
            .references-card {
            font-family: 'Inter', sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            .references-card.empty { color: var(--color-soft); font-style: italic; text-align: center; }
            .references-card h3 { margin-top: 0; font-size: 1.2rem; font-weight: 700; }
            .references-list {
            margin: 0;
            padding-left: 24px;
            }
            .ref-item {
            margin-bottom: 10px;
            line-height: 1.6;
            }
            .ref-author { font-weight: 600; }
            .ref-title { font-style: italic; }
            .ref-year, .ref-source { color: var(--color-soft); }
            .ref-url, .ref-link {
            color: var(--color-accent);
            text-decoration: none;
            word-break: break-all;
            }

            .stream-chunk {
            opacity: 0;
            transform: translateY(8px);
            animation: fadeInUp 0.35s ease forwards;
            }

            @keyframes fadeInUp {
            to {
            opacity: 1;
            transform: translateY(0);
        }
            }

            </style>

        """,
    visible=True
    )
        state_output = gr.State()
        state = gr.State({})

        with gr.Row():
            # ================= SIDEBAR (Scale 1) =================
            with gr.Column(scale=1, elem_id="sidebar"):
                gr.Markdown("## ⚙️ Settings")
                
                topic_input = gr.Textbox(
                    label="Main Topic",
                    placeholder="e.g. Future of AI",
                    lines=2
                )
                
                article_type = gr.Dropdown(
                    label="Article Type",
                    choices=["Blog Post", "Educational", "Academic", "Technical Report"],
                    value="Educational"
                )
                
                
                temperature = gr.Slider(
                    label="Creativity",
                    minimum=0.2, maximum=1.0, value=0.7, step=0.05
                )
                
                gr.Markdown("---")
                
                title_btn = gr.Button("🔍 1. Generate Titles", variant="secondary")
                writer_btn = gr.Button("✍️ 2. Generate Draft", variant="secondary")
                
                gr.Markdown("---")
                full_btn = gr.Button("🚀 RUN FULL PIPELINE", variant="primary")
                
                status_msg = gr.Markdown("### Status: *Ready*")

            # ================= MAIN CONTENT (Scale 3) =================
            with gr.Column(scale=3):

                main_title = gr.HTML(animated_title("Educational"))
                article_type.change(fn=animated_title, inputs=article_type, outputs=main_title)


                # Progress Timeline
                timeline_out = gr.HTML(label="Pipeline Progress")

                # Step 1 Output: Title Selection
                titles_dropdown = gr.Dropdown(
                    label="Step 1: Select Your Preferred Title",
                    choices=[],
                    value=None,
                    interactive=True
                )

                # Output Tabs
                with gr.Tabs():
                    with gr.Tab("📝 Article Draft"):
                        # Live Word Count Display
                        word_count = gr.Markdown("Words: 0", elem_classes="word-count-box")
                        with gr.Tab("Article Draft"):
                            english_out = gr.HTML(
                                value="""
                                <div id="pro-article-en" class="article-container"></div>

                                <script>
                                window.ProStreamEn = {
                                    clear() {
                                    const el = document.getElementById("pro-article-en");
                                    if (!el) return;
                                    el.innerHTML = "";
                                    },
                                    append(html) {
                                    const el = document.getElementById("pro-article-en");
                                    if (!el) return;
                                    const wrapper = document.createElement("div");
                                    wrapper.className = "stream-chunk";
                                    wrapper.innerHTML = html;
                                    el.appendChild(wrapper);
                                    if (window.autoScrollEnabled !== false) {
                                        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
                                    }
                                    }
                                };
                                </script>
                                """,
                                elem_id="article_draft_html",
                                label="Article Draft"
                            )

                        # JS Logic for Live Word Count
                        english_out.change(
                            None, 
                            inputs=english_out, 
                            outputs=word_count,
                            js="""(text) => {
                                if(!text) return "Words: 0";
                                let words = text.trim().split(/\\s+/).length;
                                return "🔢 Words: " + words;
                            }"""
                        )

                    with gr.Tab("🔍 SEO & Editor"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### Editor Review")
                                review = gr.HTML()
                            with gr.Column():
                                gr.Markdown("### SEO Final")
                                seo_out = gr.HTML()
                                seo_style_card = gr.HTML()


                        gr.Markdown("---")
                        gr.Markdown("### Edited Article")
                        edited_article = gr.HTML()
                        editor_improvements = gr.HTML()

                    with gr.Tab("Persian Translation"):
                        detected_style_out = gr.Textbox(label="Detected Style (LLM-based)", interactive=False)
                        style_color_box = gr.HTML()
                        persian_out = gr.HTML(
                            value="""
                            <div id="pro-article-fa" class="rtl article-container" dir="rtl"></div>

                            <script>
                            window.ProStreamFa = {
                                clear() {
                                    const el = document.getElementById("pro-article-fa");
                                    if (!el) return;
                                    el.innerHTML = "";
                                },
                                append(html) {
                                    const el = document.getElementById("pro-article-fa");
                                    if (!el) return;
                                    const wrapper = document.createElement("div");
                                    wrapper.className = "stream-chunk";
                                    wrapper.innerHTML = html;
                                    el.appendChild(wrapper);
                                    if (window.autoScrollEnabled !== false) {
                                        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
                                    }
                                }
                            };
                            </script>
                            """,
                            elem_classes="rtl"
                        )

                    with gr.Tab("🗺️ Mind Map"):
                        mindmap_image = gr.HTML(label="Visualization")

                    with gr.Tab("📦 Assets & Refs"):
                        with gr.Row():
                            images_out = gr.HTML(label="Generated Images")
                            citations_out = gr.HTML(label="Citations")
                            reference_out = gr.HTML(label="Full References")
        # ---------------- EVENTS ----------------
        # 1) Generate Titles
        title_btn.click(
            fn=step_titles,
            inputs=[
                topic_input,
                article_type,
                temperature,
                state
            ],
            outputs=[
                titles_dropdown,   # پیشنهاد عنوان‌ها
                state,             # به‌روزرسانی state
                status_msg         # پیام وضعیت
            ]
        )

        # 2) Generate Draft (English Article)
        writer_btn.click(
            fn=step_writer,
            inputs=[
                titles_dropdown,
                article_type,
                temperature,
                state
            ],
            outputs=[
                english_out,       # خروجی پیش‌نویس انگلیسی
                state,
                status_msg
            ]
        )

        # 3) FULL PIPELINE (Writer → Reviewer → Editor → SEO → Translator → Mindmap)
        full_btn.click(
            fn=step_full_pipeline_stream,
            inputs=[
                topic_input,
                article_type,
                temperature,
                titles_dropdown,
                state
            ],
            outputs=[
                english_out,              # مقاله اولیه
                review,                   # نظر Reviewer
                editor_improvements,  # پیشنهادات Editor
                edited_article,       # نسخه ویرایش‌شده
                seo_out,                  # ساختار SEO Final
                images_out,               # تصاویر
                citations_out,            # منابع استخراج‌شده
                reference_out,            # متن کامل منابع
                persian_out,              # ترجمه فارسی
                mindmap_image,            # مایندمپ
                timeline_out,             # پیشرفت Pipeline
                state_output,             # state نهایی
                status_msg                # پیام وضعیت
            ]
        ).then(
        fn=lambda st: st.get("detected_style", "Not detected"),
        inputs=state_output,
        outputs=detected_style_out
    ).then(
        fn=lambda st: render_style_color(st.get("detected_style", "")),
        inputs=state_output,
        outputs=style_color_box
    ).then(
        fn=lambda st: make_seo_style_card(st.get("detected_style", "")),
        inputs=state_output,
        outputs=seo_style_card
    )




    return demo

if __name__ == "__main__":
    import os
    from gradio.routes import App  # type: ignore

    demo = app()

    # Serve the local fonts folder at /fonts so @font-face can load them.
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

    try:
        from fastapi.staticfiles import StaticFiles
        if os.path.isdir(fonts_dir):
            demo.app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")
    except Exception as _e:
        print(f"[fonts] Could not mount /fonts static route: {_e}")

    demo.launch(allowed_paths=[fonts_dir])

