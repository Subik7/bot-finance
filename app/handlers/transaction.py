from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message()
async def transaction_handler(message: Message, user, services):
    if not message.text:
        return

    try:
        result = await services.transaction_service().handle_message(
            user_id=user.id,
            text=message.text,
        )

        if result is None:
            await message.answer(
                "Я фінансовий бот 💰\n"
                "Просто напиши суму, наприклад: кава 80 або зарплата 30000\n\n"
                "Команди:\n"
                "/balance — баланс\n"
                "/analytics — аналітика\n"
                "/categories — категорії\n"
                "/delete — видалити транзакцію"
            )
            return

        tx, category_name = result
        sign = "+" if tx.amount > 0 else ""
        await message.answer(
            f"Записав ✅\n"
            f"{sign}{tx.amount:.2f} грн\n"
            f"🏷 {category_name}\n"
            f"📝 {tx.description}"
        )

    except ValueError as e:
        await message.answer(f"Помилка: {e}")
    except Exception as e:
        await message.answer("Щось пішло не так 😕")
        raise e
