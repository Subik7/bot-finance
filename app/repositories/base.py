from typing import TypeVar, Type, Generic
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = TypeVar("ModelType")



class BaseRepository(Generic[ModelType]):
    model: Type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, obj):
        self.session.add(obj)
        await self.session.flush()
        return obj
    
    async def delete(self, obj):
        await self.session.delete(obj)