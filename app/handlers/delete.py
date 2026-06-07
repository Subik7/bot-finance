from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from repositories.uow import UnitOfWork

router = Router()


@router.message(Command("delete"))
async def delete_handler(message: Message, user, services):
    uow: UnitOfWork = services.transaction_service().uow

    async with uow:
        tx = await uow.transactions.get_last(user.id)
        if not tx:
            await message.answer("Немає транзакцій для видалення 🤷")
            return
        desc = tx.description
        amount = tx.amount
        await uow.transactions.delete(tx)

    sign = "+" if amount > 0 else ""
    await message.answer(
        f"Видалено ✅\n"
        f"{sign}{amount:.2f} грн — {desc}"
    )
