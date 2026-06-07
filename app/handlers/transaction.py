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
            return

        sign = "+" if result.amount > 0 else ""
        await message.answer(
            f"Записав ✅\n"
            f"{sign}{result.amount:.2f} грн\n"
            f"📝 {result.description}"
        )

    except ValueError as e:
        await message.answer(f"Помилка: {e}")
    except Exception as e:
        await message.answer("Щось пішло не так 😕")
        raise e
