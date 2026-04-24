from models.user import UserModel
from repositories.uow import UnitOfWork
from repositories.user import UserRepository
from utils.seed_system_categories import seed_system_categories


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_or_create(self, tg_user):
        async with self.uow:
            user = await self.uow.users.get_by_tg_id(tg_user.id)
            if user:
                return user

            new_user = UserModel(
                tg_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code,
            )

            user = await self.uow.users.add(new_user)
            await self.uow.session.flush()
            await seed_system_categories(self.uow.session, user.id)
            return user
