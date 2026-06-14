from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

MENU_BUTTON_TEXT = "🏠 Меню"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=MENU_BUTTON_TEXT)]],
        resize_keyboard=True,
        input_field_placeholder="Напиши транзакцію або натисни Меню...",
    )


def menu_inline_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс",       callback_data="menu:balance")
    kb.button(text="📋 Історія",      callback_data="menu:history")
    kb.button(text="📊 Аналітика",    callback_data="menu:analytics")
    kb.button(text="🗑 Видалити",     callback_data="menu:delete")
    kb.button(text="📂 Категорії",    callback_data="menu:categories")
    kb.button(text="➕ Нова категорія", callback_data="menu:add_category")
    kb.adjust(2)
    return kb.as_markup()


async def show_menu(target: Message):
    await target.answer("Оберіть дію:", reply_markup=menu_inline_keyboard())


@router.message(Command("menu"))
async def menu_command(message: Message):
    await show_menu(message)


@router.message(F.text == MENU_BUTTON_TEXT)
async def menu_button_handler(message: Message):
    await show_menu(message)


@router.callback_query(F.data.startswith("menu:"))
async def menu_callback(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    commands = {
        "balance":      "/balance",
        "history":      "/history",
        "analytics":    "/analytics",
        "delete":       "/delete",
        "categories":   "/categories",
        "add_category": "/add_category",
    }
    await callback.message.delete()
    await callback.message.answer(commands[action])
    await callback.answer()
