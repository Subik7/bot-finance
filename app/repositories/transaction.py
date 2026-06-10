from datetime import datetime
from sqlalchemy import select, update, func
from repositories.base import BaseRepository
from models.transaction import TransactionModel


class TransactionRepository(BaseRepository[TransactionModel]):
    model = TransactionModel

    async def get_page(self, user_id: int, offset: int, limit: int) -> list[TransactionModel]:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.user_id == user_id)
            .order_by(TransactionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).where(TransactionModel.user_id == user_id)
        )
        return result.scalar_one()

    async def get_by_id(self, tx_id: int, user_id: int) -> TransactionModel | None:
        result = await self.session.execute(
            select(TransactionModel).where(
                TransactionModel.id == tx_id,
                TransactionModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> list[TransactionModel]:
        result = await self.session.execute(
            select(TransactionModel).where(TransactionModel.user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_user_since(
        self, user_id: int, since: datetime, until: datetime | None = None
    ) -> list[TransactionModel]:
        q = select(TransactionModel).where(
            TransactionModel.user_id == user_id,
            TransactionModel.created_at >= since,
        )
        if until is not None:
            q = q.where(TransactionModel.created_at <= until)
        result = await self.session.execute(q.order_by(TransactionModel.created_at.asc()))
        return result.scalars().all()

    async def get_last(self, user_id: int) -> TransactionModel | None:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.user_id == user_id)
            .order_by(TransactionModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_all_by_user(self, user_id: int) -> int:
        from sqlalchemy import delete as sa_delete
        result = await self.session.execute(
            sa_delete(TransactionModel).where(TransactionModel.user_id == user_id)
        )
        return result.rowcount or 0

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

