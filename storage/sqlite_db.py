from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime


DATABASE_URL = "sqlite:///data/articles.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Article(Base):

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)

    topic = Column(Text)

    title = Column(Text)

    article_en = Column(Text)

    article_fa = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():

    Base.metadata.create_all(engine)
