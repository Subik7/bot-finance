from datetime import datetime
from sqlalchemy import select, update
from repositories.base import BaseRepository
from models.transaction import TransactionModel


class TransactionRepository(BaseRepository[TransactionModel]):
    model = TransactionModel

    async def get_by_user(self, user_id: int) -> list[TransactionModel]:
        result = await self.session.execute(
            select(TransactionModel).where(TransactionModel.user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_user_since(self, user_id: int, since: datetime) -> list[TransactionModel]:
        result = await self.session.execute(
            select(TransactionModel).where(
                TransactionModel.user_id == user_id,
                TransactionModel.created_at >= since
            ).order_by(TransactionModel.created_at.asc())
        )
        return result.scalars().all()

    async def get_last(self, user_id: int) -> TransactionModel | None:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.user_id == user_id)
            .order_by(TransactionModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def move_category(
        self,
        user_id: int,
        from_category_id: int,
        to_category_id: int,
    ) -> int:
        result = await self.session.execute(
            update(TransactionModel)
            .where(
                TransactionModel.user_id == user_id,
                TransactionModel.category_id == from_category_id,
            )
            .values(category_id=to_category_id)
        )
        return result.rowcount or 0

