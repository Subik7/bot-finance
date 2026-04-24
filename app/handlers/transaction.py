from aiogram import Router
from aiogram.types import Message, BufferedInputFile
from models.transaction import TransactionModel
from services.groq_service import ParsedTextResponse
from services.analytics import PERIOD_LABELS

router = Router()

ANALYTICS_TITLES = {
    "category": "Витрати по категоріях",
    "days": "Витрати по днях",
    "income_expense": "Дохід vs Витрати",
}


@router.message()
async def transaction_handler(message: Message, user, services):
    if not message.text:
        return

    try:
        result = await services.transaction_service().handle_message(
            user_id=user.id,
            text=message.text,
        )

        if isinstance(result, ParsedTextResponse):
            await message.answer(result.text)

        elif isinstance(result, dict) and result.get("type") == "balance":
            await message.answer(
                f"💰 Баланс: {result['balance']:.2f} грн\n"
                f"📈 Доходи: +{result['income']:.2f} грн\n"
                f"📉 Витрати: {result['expense']:.2f} грн"
            )

        elif isinstance(result, dict) and result.get("type") == "delete_last":
            if result["success"]:
                sign = "+" if result["amount"] > 0 else ""
                await message.answer(
                    f"Видалено ✅\n"
                    f"{sign}{result['amount']:.2f} грн — {result['description']}"
                )
            else:
                await message.answer("Немає транзакцій для видалення 🤷")

        elif isinstance(result, dict) and result.get("type") == "categories":
            names = "\n".join(f"• {n}" for n in result["names"])
            await message.answer(f"Твої категорії:\n{names}")

        elif isinstance(result, dict) and result.get("type") == "analytics_text":
            by_cat = "\n".join(
                f"  • {cat}: {amt:.2f} грн"
                for cat, amt in result["by_category"].items()
            ) or "  немає витрат"
            await message.answer(
                f"📊 Аналітика — {PERIOD_LABELS[result['period']]}\n\n"
                f"📈 Доходи: +{result['income']:.2f} грн\n"
                f"📉 Витрати: -{result['expense']:.2f} грн\n"
                f"💰 Баланс: {result['balance']:.2f} грн\n"
                f"📝 Транзакцій: {result['count']}\n\n"
                f"По категоріях:\n{by_cat}"
            )

        elif isinstance(result, dict) and result.get("type") == "analytics_chart":
            if result["buf"] is None:
                await message.answer("Немає даних за цей період 😕")
                return
            title = ANALYTICS_TITLES.get(result["analytics_type"], "Аналітика")
            photo = BufferedInputFile(result["buf"].read(), filename="analytics.png")
            await message.answer_photo(
                photo,
                caption=f"{title} — {PERIOD_LABELS[result['period']]}"
            )

        elif isinstance(result, TransactionModel):
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