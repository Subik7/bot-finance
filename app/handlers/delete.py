from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

PAGE_SIZE = 10

router = Router()


class DeleteStates(StatesGroup):
    browsing = State()
    confirming = State()


def _format_tx(tx) -> str:
    sign = "+" if tx.amount > 0 else ""
    date = tx.created_at.strftime("%d.%m")
    return f"{date} {sign}{tx.amount:.0f} грн — {tx.description}"


async def _build_list_keyboard(user_id: int, offset: int, uow):
    async with uow:
        txs = await uow.transactions.get_page(user_id, offset, PAGE_SIZE)
        total = await uow.transactions.count(user_id)

    if not txs:
        return None, None, total

    kb = InlineKeyboardBuilder()
    for tx in txs:
        kb.button(text=_format_tx(tx), callback_data=f"del_pick:{tx.id}")
    kb.adjust(1)

    nav = []
    if offset > 0:
        nav.append(("⬅️ Назад", f"del_page:{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total:
        nav.append(("➡️ Далі", f"del_page:{offset + PAGE_SIZE}"))
    nav.append(("❌ Скасувати", "del_cancel"))

    for text, data in nav:
        kb.button(text=text, callback_data=data)
    kb.adjust(1)

    return kb.as_markup(), txs, total


@router.message(Command("delete"))
async def delete_start(message: Message, state: FSMContext, user, services):
    uow = services.transaction_service().uow
    keyboard, txs, total = await _build_list_keyboard(user.id, 0, uow)

    if not txs:
        await message.answer("Немає транзакцій для видалення 🤷")
        return

    await state.set_state(DeleteStates.browsing)
    await state.update_data(offset=0)
    await message.answer(
        f"Оберіть транзакцію для видалення (всього: {total}):",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("del_page:"), DeleteStates.browsing)
async def delete_page(callback: CallbackQuery, state: FSMContext, user, services):
    offset = int(callback.data.split(":")[1])
    uow = services.transaction_service().uow
    keyboard, txs, total = await _build_list_keyboard(user.id, offset, uow)

    await state.update_data(offset=offset)
    await callback.message.edit_text(
        f"Оберіть транзакцію для видалення (всього: {total}):",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_pick:"), DeleteStates.browsing)
async def delete_pick(callback: CallbackQuery, state: FSMContext, user, services):
    tx_id = int(callback.data.split(":")[1])
    uow = services.transaction_service().uow

    async with uow:
        tx = await uow.transactions.get_by_id(tx_id, user.id)

    if not tx:
        await callback.answer("Транзакцію не знайдено", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так, видалити", callback_data=f"del_confirm:{tx_id}")
    kb.button(text="❌ Скасувати", callback_data="del_cancel")
    kb.adjust(2)

    sign = "+" if tx.amount > 0 else ""
    await state.set_state(DeleteStates.confirming)
    await callback.message.edit_text(
        f"Видалити цю транзакцію?\n\n"
        f"{_format_tx(tx)}\n"
        f"{tx.created_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_confirm:"), DeleteStates.confirming)
async def delete_confirm(callback: CallbackQuery, state: FSMContext, user, services):
    tx_id = int(callback.data.split(":")[1])
    uow = services.transaction_service().uow

    async with uow:
        tx = await uow.transactions.get_by_id(tx_id, user.id)
        if not tx:
            await callback.answer("Транзакцію не знайдено", show_alert=True)
            await state.clear()
            return
        sign = "+" if tx.amount > 0 else ""
        desc = tx.description
        amount = tx.amount
        await uow.transactions.delete(tx)

    await state.clear()
    await callback.message.edit_text(
        f"Видалено ✅\n{sign}{amount:.2f} грн — {desc}"
    )
    await callback.answer()


@router.callback_query(F.data == "del_cancel")
async def delete_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано ❌")
    await callback.answer()
