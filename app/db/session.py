from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from models.base import Base


_DB_PATH = Path(__file__).parent.parent / "finance_bot.db"
DATABASE_URL = f"sqlite+aiosqlite:///{_DB_PATH}"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


