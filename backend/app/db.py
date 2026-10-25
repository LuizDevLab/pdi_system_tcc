from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


def _sqlalchemy_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL está vazio. Preencha backend/.env e tente de novo.")
    return create_engine(_sqlalchemy_url(DATABASE_URL), pool_pre_ping=True)


def get_session_factory(engine=None):
    return sessionmaker(bind=engine or get_engine())


_session_factory = None


def get_db():
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory()
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
