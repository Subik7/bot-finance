import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from db.session import AsyncSessionLocal, init_db
from handlers import analytics, category, transaction
from middlewares.db import DBSessionMiddleware
from middlewares.services import ServiceMiddleware
from middlewares.user import UserMiddleware

from config import config

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(token=config.bot_token.get_secret_value())

    dp = Dispatcher(storage=MemoryStorage())

    # middlewares
    dp.update.middleware(DBSessionMiddleware(AsyncSessionLocal))
    dp.update.middleware(ServiceMiddleware())
    dp.update.middleware(UserMiddleware())

    # routers
    dp.include_router(analytics.router)
    dp.include_router(category.router)
    dp.include_router(transaction.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
