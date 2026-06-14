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
    summary = await services.analytics_service().text_summary(user.id, "all")
    by_cat = summary["by_category"]

    uow = services.transaction_service().uow
    async with uow:
        cat_counts = {
            c.id: await uow.transactions.count(user.id, category_id=c.id)
            for c in cats
        }

    system_cats = [c for c in cats if c.is_system]
    custom_cats  = [c for c in cats if not c.is_system]

    def fmt(cat):
        spent = by_cat.get(cat.name, 0)
        count = cat_counts.get(cat.id, 0)
        spent_str = f"  {spent:.0f} грн · {count} транз." if count else "  немає транзакцій"
        return f"• {cat.name}{spent_str}"

    lines = ["📂 *Твої категорії*\n"]

    lines.append("*Системні:*")
    lines.extend(fmt(c) for c in system_cats)

    if custom_cats:
        lines.append("\n*Кастомні:*")
        lines.extend(fmt(c) for c in custom_cats)

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("add_category"))
async def add_category_command(message: Message, state: FSMContext):
    await state.set_state(AddCategoryStates.waiting_name)
    await message.answer(
        "Введи назву нової категорії:\n"
        "(наприклад: спорт, навчання, подарунки)"
    )


@router.message(AddCategoryStates.waiting_name)
async def add_category_name(message: Message, state: FSMContext, user, services):
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("Створення категорії скасовано ❌\nВиконай команду ще раз.")
        return

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


async def _show_delete_category_list(target, state: FSMContext, user, services, edit: bool = False):
    cats = await services.category_service().get_custom_for_user(user.id)

    if not cats:
        text = "У тебе немає категорій для видалення."
        if edit:
            await target.edit_text(text)
        else:
            await target.answer(text)
        await state.clear()
        return

    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=cat.name, callback_data=f"delcat_pick:{cat.name}")
    kb.adjust(2)

    bottom = InlineKeyboardBuilder()
    bottom.button(text="❌ Скасувати", callback_data="delcat_cancel")
    bottom.adjust(1)
    kb.attach(bottom)

    await state.set_state(DeleteCategoryStates.confirming)
    text = "Оберіть категорію для видалення:"
    if edit:
        await target.edit_text(text, reply_markup=kb.as_markup())
    else:
        await target.answer(text, reply_markup=kb.as_markup())


@router.message(Command("delete_category"))
async def delete_category_command(message: Message, state: FSMContext, user, services):
    await _show_delete_category_list(message, state, user, services)


@router.callback_query(F.data.startswith("delcat_pick:"), DeleteCategoryStates.confirming)
async def delete_category_pick(callback: CallbackQuery, state: FSMContext, user, services):
    name = callback.data.split(":", 1)[1]

    uow = services.transaction_service().uow
    async with uow:
        cats = await uow.categories.get_by_user(user.id)
        cat = next((c for c in cats if c.name == name), None)
        tx_count = await uow.transactions.count(user.id, category_id=cat.id) if cat else 0

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так, видалити", callback_data=f"delcat_confirm:{name}")
    kb.button(text="⬅️ Назад", callback_data="delcat_back")
    kb.adjust(2)

    tx_info = f"Транзакцій у цій категорії: {tx_count}" if tx_count else "Транзакцій у цій категорії немає."
    await callback.message.edit_text(
        f"Видалити категорію «{name}»?\n"
        f"{tx_info}\n"
        f"Всі транзакції будуть перенесені в «other».",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delcat_confirm:"), DeleteCategoryStates.confirming)
async def delete_category_confirm(callback: CallbackQuery, state: FSMContext, user, services):
    name = callback.data.split(":", 1)[1]

    try:
        moved_count = await services.category_service().delete_for_user(user.id, name)
        info = f"Транзакцій перенесено в «other»: {moved_count}" if moved_count else "Транзакцій не було."
        await callback.message.edit_text(f"Категорію «{name}» видалено ✅\n{info}")
    except ValueError as e:
        await callback.message.edit_text(str(e))
        await state.clear()
        await callback.answer()
        return

    await callback.answer()
    await _show_delete_category_list(callback.message, state, user, services, edit=False)


@router.callback_query(F.data == "delcat_back", DeleteCategoryStates.confirming)
async def delete_category_back(callback: CallbackQuery, state: FSMContext, user, services):
    await _show_delete_category_list(callback.message, state, user, services, edit=True)
    await callback.answer()


@router.callback_query(F.data == "delcat_cancel", DeleteCategoryStates.confirming)
async def delete_category_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано ❌")
    await callback.answer()
