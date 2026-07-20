from langgraph.graph import StateGraph, END

from app.state import ArticleState

from agents.title_agent import title_agent
from agents.writer_agent import writer_agent
from agents.reviewer_state_agent import reviewer_state_agent
from agents.editor_agent import editor_agent
from agents.seo_agent import seo_agent
from agents.citation_agent import citation_agent
from agents.image_agent import image_agent
from agents.translator_agent import translator_agent
from agents.mind_map_agent import mind_map_node

from app.router import review_router


def build_graph():
    builder = StateGraph(ArticleState)

    # nodes
    builder.add_node("title", title_agent)              # type: ignore[arg-type]
    builder.add_node("writer", writer_agent)            # type: ignore[arg-type]
    builder.add_node("editor_review", reviewer_state_agent) 
    builder.add_node("editor", editor_agent)            # type: ignore[arg-type]
    builder.add_node("seo", seo_agent)                  # type: ignore[arg-type]
    builder.add_node("citation", citation_agent)        # type: ignore[arg-type]
    builder.add_node("image", image_agent)              # type: ignore[arg-type]
    builder.add_node("translator", translator_agent)    # type: ignore[arg-type]
    builder.add_node("mind_map", mind_map_node)         # type: ignore[arg-type]

    # edges
    builder.set_entry_point("title")

    builder.add_edge("title", "writer")
    builder.add_edge("writer", "editor_review")

    # فقط conditional از editor_review به editor/seo
    builder.add_conditional_edges(
        "editor_review",
        review_router,
        {
            "editor": "editor",  # go to editor
            "seo": "seo",        # skip editing
        },
    )

    # بعد از editor دوباره برای re-review
    builder.add_edge("editor", "editor_review")

    # از اینجا دیگه مسیر قطعی به جلو
    builder.add_edge("seo", "citation")
    builder.add_edge("citation", "image")
    builder.add_edge("image", "translator")
    builder.add_edge("translator", "mind_map")
    builder.add_edge("mind_map", END)

    return builder.compile()


graph = build_graph()
