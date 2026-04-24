from sqlalchemy import select

from repositories.base import BaseRepository
from models.user import UserModel


class UserRepository(BaseRepository[UserModel]):
    model = UserModel

    async def get_by_tg_id(self, tg_id: int):
        stmt = select(self.model).where(self.model.tg_id == tg_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()