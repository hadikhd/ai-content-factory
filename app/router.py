from app.state import ArticleState

def review_router(state: ArticleState) -> str:
    needs_edit = state.get("needs_edit", False)
    review_count = int(state.get("review_count") or 0)


    if needs_edit and review_count < 3:
        return "editor"
    else:
        return "seo"
