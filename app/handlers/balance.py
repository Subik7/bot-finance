from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("balance"))
async def balance_handler(message: Message, user, services):
    summary = await services.analytics_service().text_summary(user.id, "all")
    await message.answer(
        f"💰 Баланс: {summary['balance']:.2f} грн\n"
        f"📈 Доходи: +{summary['income']:.2f} грн\n"
        f"📉 Витрати: {summary['expense']:.2f} грн"
    )
