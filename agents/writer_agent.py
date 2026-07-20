from tools.ollama_client import call_ollama
from tools.prompts import WRITER_PROMPT
from app.state import ArticleState
from typing import cast


def writer_agent(state: ArticleState) -> ArticleState:
    topic = state.get("topic", "").strip()
    selected_title = state.get("selected_title") or state.get("title")
    article_type = state.get("article_type", "blog_post")
    temperature = float(state.get("temperature", 0.7) or 0.7)


    model = state.get("writer_model") or state.get("model") or "gemma3:12b"

    if not topic or not selected_title:
        state["article"] = ""
        state["writer_error"] = "Topic or selected title is missing."
        return cast(ArticleState, state)

    prompt = WRITER_PROMPT + f"\n\nARTICLE TYPE: {article_type}\n\nTITLE: {selected_title}\n"

    article = call_ollama(
    model=model,
    prompt=prompt,
    temperature=temperature,
    )

# Ensure string output
    if not isinstance(article, str):
        article = str(article)

    state["article"] = article.strip()
    return cast(ArticleState, state)
