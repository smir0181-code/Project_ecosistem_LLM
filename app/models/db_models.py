from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Model(Base):
    __tablename__ = "models"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InferenceLog(Base):
    __tablename__ = "inference_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(nullable=False)
    response: Mapped[str] = mapped_column(nullable=True)
    temperature: Mapped[float] = mapped_column(nullable=True)
    tokens_used: Mapped[int] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
