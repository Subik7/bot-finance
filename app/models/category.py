from models.base import Base
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class CategoryModel(Base):
    __tablename__ = "categories"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(64))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("user_id", "name"),)


SYSTEM_CATEGORIES = [
    "food",
    "transport",
    "rent",
    "utilities",
    "entertainment",
    "shopping",
    "health",
    "other",
]
