from aiogram import Router
from aiogram.types import Message


router = Router()


@router.message()
async def start_handler(message: Message, user, services):
    await message.answer(f"Hello {user.first_name}")
