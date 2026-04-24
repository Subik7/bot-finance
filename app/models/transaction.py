from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)  
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
