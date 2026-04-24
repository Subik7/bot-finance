from sqlalchemy.ext.asyncio import AsyncSession

from repositories.user import UserRepository
from repositories.category import CategoryRepository
from repositories.transaction import TransactionRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.categories = CategoryRepository(session)
        self.transactions = TransactionRepository(session)

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
    
    async def refresh(self, obj):
        await self.session.refresh(obj)