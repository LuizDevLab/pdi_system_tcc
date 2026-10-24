from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargos.id"), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenure_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_participant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    cargo: Mapped["Cargo | None"] = relationship(back_populates="users")


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="cargo")
    references: Mapped[list["CargoReference"]] = relationship(back_populates="cargo")


class Competency(Base):
    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    references: Mapped[list["CargoReference"]] = relationship(back_populates="competency")
    catalog_actions: Mapped[list["ActionCatalog"]] = relationship(back_populates="competency")


class CargoReference(Base):
    __tablename__ = "cargo_reference"
    __table_args__ = (UniqueConstraint("cargo_id", "competency_id"),)

    cargo_id: Mapped[int] = mapped_column(ForeignKey("cargos.id"), primary_key=True)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), primary_key=True)
    expected_level: Mapped[int] = mapped_column(Integer, nullable=False)
    provisional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    cargo: Mapped[Cargo] = relationship(back_populates="references")
    competency: Mapped[Competency] = relationship(back_populates="references")


class EvaluationLink(Base):
    __tablename__ = "evaluation_links"
    __table_args__ = (UniqueConstraint("evaluator_id", "evaluated_id", "type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    evaluated_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    scores: Mapped[list["Score"]] = relationship(back_populates="link")
    development_input: Mapped["DevelopmentInput | None"] = relationship(back_populates="link")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("link_id", "competency_id"),)

    link_id: Mapped[int] = mapped_column(ForeignKey("evaluation_links.id"), primary_key=True)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    link: Mapped[EvaluationLink] = relationship(back_populates="scores")
    competency: Mapped[Competency] = relationship()


class DevelopmentInput(Base):
    __tablename__ = "development_inputs"

    link_id: Mapped[int] = mapped_column(ForeignKey("evaluation_links.id"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    link: Mapped[EvaluationLink] = relationship(back_populates="development_input")


class ActionCatalog(Base):
    __tablename__ = "action_catalog"
    __table_args__ = (UniqueConstraint("competency_id", "title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    competency: Mapped[Competency] = relationship(back_populates="catalog_actions")


class Pdi(Base):
    __tablename__ = "pdis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consolidated: Mapped[dict] = mapped_column(JSON, nullable=False)
    cosine: Mapped[float] = mapped_column(Float, nullable=False)
    jaccard: Mapped[float] = mapped_column(Float, nullable=False)
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    reference_provisional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    items: Mapped[list["PdiItem"]] = relationship(back_populates="pdi")
    user: Mapped[User] = relationship()


class PdiItem(Base):
    __tablename__ = "pdi_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pdi_id: Mapped[int] = mapped_column(ForeignKey("pdis.id"), nullable=False)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), nullable=False)
    gap: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    action_id: Mapped[int | None] = mapped_column(ForeignKey("action_catalog.id"), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    divergence: Mapped[float | None] = mapped_column(Float, nullable=True)

    pdi: Mapped[Pdi] = relationship(back_populates="items")
    competency: Mapped[Competency] = relationship()
    action: Mapped["ActionCatalog | None"] = relationship()
