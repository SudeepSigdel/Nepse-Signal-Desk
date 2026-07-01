"""
SQLAlchemy engine/session setup for user accounts, watchlist, and holdings.

Schema is created via Base.metadata.create_all() at startup (see app/main.py)
rather than Alembic migrations — the schema is new and not yet evolving, so
a migration tool would be premature; add Alembic when it starts changing
shape under real data.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True) if settings.database_url else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
