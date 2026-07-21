"""SQLite metadata store: datasource registry and audit log."""

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from eiye_db.config import settings


class Base(DeclarativeBase):
    pass


class DataSourceRow(Base):
    __tablename__ = "datasources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    pii_risk_level: Mapped[str] = mapped_column(String(10), default="unknown")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    last_connected: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    action: Mapped[str] = mapped_column(String(50))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(255))
    api_key_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    datasource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, default=True)


_engine = None


def configure(url: str | None = None):
    """Create (or replace) the engine and ensure tables exist."""
    global _engine
    if url is None:
        url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(_engine)
    return _engine


def get_engine():
    if _engine is None:
        configure()
    return _engine


@contextmanager
def session():
    with Session(get_engine()) as s:
        yield s
