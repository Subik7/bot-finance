from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("balance"))
async def balance_handler(message: Message, user, services):
    analytics = services.analytics_service()
    total = await analytics.text_summary(user.id, "all")
    month = await analytics.text_summary(user.id, "month")

    await message.answer(
        f"💰 *Баланс*\n\n"
        f"*За цей місяць:*\n"
        f"📈 Доходи: +{month['income']:.2f} грн\n"
        f"📉 Витрати: -{month['expense']:.2f} грн\n"
        f"💵 Баланс: {month['balance']:.2f} грн\n\n"
        f"*За весь час:*\n"
        f"📈 Доходи: +{total['income']:.2f} грн\n"
        f"📉 Витрати: -{total['expense']:.2f} грн\n"
        f"💵 Баланс: {total['balance']:.2f} грн",
        parse_mode="Markdown",
    )
