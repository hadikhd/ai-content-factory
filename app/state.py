from typing import List, Optional, TypedDict, Dict, Any


class ArticleState(TypedDict, total=False):
    # ورودی اصلی
    topic: str
    temperature: float
    article_type: str

    # Title agent
    title: Optional[str]
    titles: Optional[List[str]]
    generated_titles: Optional[List[str]]
    selected_title: Optional[str]
    title_error: Optional[str]

    # Writer agent
    article: Optional[str]              # raw english
    writer_error: Optional[str]
    # for article style 
    english_article: Optional[str]


    # Editor agent
    edited_article: Optional[str]       # edited english version
    editor_feedback: Optional[str]
    editor_improvements: Optional[str]
    editor_notes: Optional[str]

    # Reviewer agent
    review_summary: Optional[str]
    final_recommendation: Optional[str]
    review_scores: Optional[Dict[str, int]]
    review_issues: Optional[List[Dict[str, str]]]
    reviewer_feedback: Optional[Dict[str, Any]]
    reviewed: Optional[str]

    # SEO agent
    seo_article: Optional[str]
    seo_score: Optional[int]
    seo_json: Optional[Dict[str, Any]]
    seo_report: Optional[str]

    # Translation agent
    translated_article: Optional[str]    # persian
    persian_article: Optional[str]
    translation_progress: Optional[int]
    translation_total: Optional[int]
    detected_style: Optional[str]


    # Citations
    citations: Optional[List[str]]
    reference_section: Optional[str]
    references: Optional[str]
    citation_error: Optional[str]

    # Images
    images: Optional[List[str]]

    # Mindmap
    mindmap_html: Optional[str]
    mindmap_structure: Optional[Dict[str, Any]]
    mindmap_image: Optional[str]
    mindmap_path: Optional[str]

    # Metadata / pipeline
    needs_edit: Optional[bool]
    review_count: Optional[int]
    article_id: Optional[int]

    draft: Optional[str]
    completed_steps: Optional[List[str]]
