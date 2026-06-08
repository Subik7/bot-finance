from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


class AddCategoryStates(StatesGroup):
    waiting_name = State()


class DeleteCategoryStates(StatesGroup):
    confirming = State()


@router.message(Command("categories"))
async def list_categories_command(message: Message, user, services):
    cats = await services.category_service().get_all_for_user(user.id)
    names = "\n".join(f"• {c.name}" for c in cats)
    await message.answer(f"Твої категорії:\n{names}")


@router.message(Command("add_category"))
async def add_category_command(message: Message, state: FSMContext):
    await state.set_state(AddCategoryStates.waiting_name)
    await message.answer(
        "Введи назву нової категорії:\n"
        "(наприклад: спорт, навчання, подарунки)"
    )


@router.message(AddCategoryStates.waiting_name)
async def add_category_name(message: Message, state: FSMContext, user, services):
    name = message.text.strip().lower()

    if len(name) < 2:
        await message.answer("Занадто коротко. Спробуй ще раз:")
        return

    if len(name) > 64:
        await message.answer("Занадто довго. Спробуй коротше:")
        return

    try:
        await services.category_service().create_for_user(user.id, name)
        await state.clear()
        await message.answer(f"Категорію «{name}» створено ✅")
    except ValueError as e:
        await state.clear()
        await message.answer(str(e))


@router.message(Command("delete_category"))
async def delete_category_command(message: Message, state: FSMContext, user, services):
    cats = await services.category_service().get_custom_for_user(user.id)

    if not cats:
        await message.answer("У тебе немає кастомних категорій для видалення.")
        return

    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=cat.name, callback_data=f"delcat_pick:{cat.name}")
    kb.button(text="❌ Скасувати", callback_data="delcat_cancel")
    kb.adjust(2)

    await state.set_state(DeleteCategoryStates.confirming)
    await message.answer("Оберіть категорію для видалення:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("delcat_pick:"), DeleteCategoryStates.confirming)
async def delete_category_pick(callback: CallbackQuery, state: FSMContext):
    name = callback.data.split(":", 1)[1]

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так, видалити", callback_data=f"delcat_confirm:{name}")
    kb.button(text="❌ Скасувати", callback_data="delcat_cancel")
    kb.adjust(2)

    await callback.message.edit_text(
        f"Видалити категорію «{name}»?\n"
        f"Всі транзакції будуть перенесені в «other».",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delcat_confirm:"), DeleteCategoryStates.confirming)
async def delete_category_confirm(callback: CallbackQuery, state: FSMContext, user, services):
    name = callback.data.split(":", 1)[1]

    try:
        moved_count = await services.category_service().delete_for_user(user.id, name)
        await state.clear()
        await callback.message.edit_text(
            f"Категорію «{name}» видалено ✅\n"
            f"Транзакцій перенесено в «other»: {moved_count}"
        )
    except ValueError as e:
        await state.clear()
        await callback.message.edit_text(str(e))

    await callback.answer()


@router.callback_query(F.data == "delcat_cancel")
async def delete_category_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано ❌")
    await callback.answer()
