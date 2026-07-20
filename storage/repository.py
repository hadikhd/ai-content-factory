from storage.sqlite_db import SessionLocal, Article
from storage.redis_cache import cache_article
from datetime import datetime


def save_article(data):

    db = SessionLocal()

    article = Article(
        topic=data["topic"],
        title=data["title"],
        article_en=data["article_en"],
        article_fa=data["article_fa"],
        created_at=datetime.utcnow()
    )

    db.add(article)
    db.commit()

    article_id = article.id

    cache_article(article_id, data)

    return article_id
