from sqlalchemy import select
from repositories.base import BaseRepository
from models.category import CategoryModel


class CategoryRepository(BaseRepository[CategoryModel]):
    model = CategoryModel

    async def get_by_user(self, user_id: int) -> list[CategoryModel]:
        result = await self.session.execute(
            select(CategoryModel).where(
                (CategoryModel.user_id == user_id) | (CategoryModel.is_system == True)
            )
        )
        return result.scalars().all()

    async def get_by_name(self, user_id: int, name: str) -> CategoryModel | None:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.user_id == user_id,
                CategoryModel.name == name,
            )
        )
        user_cat = result.scalar_one_or_none()
        if user_cat:
            return user_cat

        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.is_system == True,
                CategoryModel.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_default(self, user_id: int) -> CategoryModel | None:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.name == "other",
                (CategoryModel.user_id == user_id) | (CategoryModel.is_system == True)
            )
        )
        return result.scalar_one_or_none()

    async def exists_for_user(self, user_id: int, name: str) -> bool:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.name == name,
                CategoryModel.user_id == user_id
            )
        )
        return result.first() is not None