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

    async def delete_for_user(self, user_id: int, name: str) -> int:
        async with self.uow:
            category = await self.uow.categories.get_owned_by_name(user_id, name)
            if not category:
                raise ValueError("\u0422\u0430\u043a\u043e\u0457 \u0442\u0432\u043e\u0454\u0457 \u043a\u0430\u0441\u0442\u043e\u043c\u043d\u043e\u0457 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0456\u0457 \u043d\u0435\u043c\u0430\u0454")

            if category.is_system:
                raise ValueError("\u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0456 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0456\u0457 \u0432\u0438\u0434\u0430\u043b\u044f\u0442\u0438 \u043d\u0435 \u043c\u043e\u0436\u043d\u0430")

            default_category = await self.uow.categories.get_owned_by_name(user_id, "other")
            if not default_category:
                raise ValueError("\u041d\u0435 \u0437\u043d\u0430\u0439\u0448\u043e\u0432 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u0443 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0456\u044e other")

            moved_count = await self.uow.transactions.move_category(
                user_id=user_id,
                from_category_id=category.id,
                to_category_id=default_category.id,
            )
            await self.uow.categories.delete(category)
            return moved_count

