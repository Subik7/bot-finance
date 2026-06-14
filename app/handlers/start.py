from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from handlers.menu import main_reply_keyboard

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message):
    name = message.from_user.first_name or "друже"
    await message.answer(
        f"👋 Привіт, {name}!\n\n"
        "Я твій персональний фінансовий асистент. "
        "Просто пиши мені що витратив або отримав — я сам розберу і запишу.\n\n"
        "📝 *Як це працює:*\n"
        "Просто напиши у вільній формі:\n"
        "— `кава 80` → витрата 80 грн, категорія їжа\n"
        "— `таксі 200` → транспорт\n"
        "— `зарплата 30000` → дохід\n\n"
        "⚙️ *Команди:*\n"
        "/balance — поточний баланс\n"
        "/history — історія транзакцій\n"
        "/analytics — графіки та статистика\n"
        "/categories — список категорій\n"
        "/add\\_category — додати нову категорію\n"
        "/delete\\_category — видалити категорію\n"
        "/delete — видалити транзакцію",
        parse_mode="Markdown",
        reply_markup=main_reply_keyboard(),
    )
