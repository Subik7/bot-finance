from models.category import CategoryModel
from repositories.uow import UnitOfWork


class CategoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def resolve(self, user_id: int, hint: str | None):
        async with self.uow:
            if hint:
                category = await self.uow.categories.get_by_name(user_id, hint.lower())
                if category:
                    return category

                all_categories = await self.uow.categories.get_by_user(user_id)
                for cat in all_categories:
                    if cat.name in hint.lower() or hint.lower() in cat.name:
                        return cat

            return await self.uow.categories.get_default(user_id)

    async def create_for_user(self, user_id: int, name: str) -> CategoryModel:
        async with self.uow:
            exists = await self.uow.categories.exists_for_user(user_id, name)
            if exists:
                raise ValueError(f"Категорія «{name}» вже існує")

            cat = CategoryModel(
                user_id=user_id,
                name=name,
                is_system=False,
            )
            return await self.uow.categories.add(cat)

    async def get_all_for_user(self, user_id: int) -> list[CategoryModel]:
        async with self.uow:
            return await self.uow.categories.get_by_user(user_id)
