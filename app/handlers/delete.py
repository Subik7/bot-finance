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
    confirming_all = State()
    confirming_all_final = State()


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

    nav = InlineKeyboardBuilder()
    if offset > 0:
        nav.button(text="⬅️ Назад", callback_data=f"del_page:{offset - PAGE_SIZE}")
    if offset + PAGE_SIZE < total:
        nav.button(text="➡️ Далі", callback_data=f"del_page:{offset + PAGE_SIZE}")
    if offset > 0 or offset + PAGE_SIZE < total:
        nav.adjust(2)
        kb.attach(nav)

    bottom = InlineKeyboardBuilder()
    bottom.button(text="🗑 Видалити всі", callback_data="del_all")
    bottom.button(text="❌ Скасувати", callback_data="del_cancel")
    bottom.adjust(2)
    kb.attach(bottom)

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


# ── Видалення всіх: крок 1 ───────────────────────────────────────────────

@router.callback_query(F.data == "del_all", DeleteStates.browsing)
async def delete_all_step1(callback: CallbackQuery, state: FSMContext, user, services):
    uow = services.transaction_service().uow
    async with uow:
        total = await uow.transactions.count(user.id)

    kb = InlineKeyboardBuilder()
    kb.button(text="⚠️ Так, видалити всі", callback_data="del_all_confirm")
    kb.button(text="❌ Скасувати", callback_data="del_cancel")
    kb.adjust(2)

    await state.set_state(DeleteStates.confirming_all)
    await callback.message.edit_text(
        f"⚠️ Ви збираєтесь видалити всі {total} транзакцій.\n\n"
        f"Це незворотня дія. Ви впевнені?",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# ── Видалення всіх: крок 2 (фінальне підтвердження) ─────────────────────

@router.callback_query(F.data == "del_all_confirm", DeleteStates.confirming_all)
async def delete_all_step2(callback: CallbackQuery, state: FSMContext, user, services):
    uow = services.transaction_service().uow
    async with uow:
        total = await uow.transactions.count(user.id)

    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Підтверджую, видалити все", callback_data="del_all_final")
    kb.button(text="❌ Скасувати", callback_data="del_cancel")
    kb.adjust(1)

    await state.set_state(DeleteStates.confirming_all_final)
    await callback.message.edit_text(
        f"🚨 Остаточне підтвердження!\n\n"
        f"Всі {total} транзакцій будуть видалені безповоротно.\n\n"
        f"Натисніть «Підтверджую» для продовження.",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# ── Видалення всіх: виконання ────────────────────────────────────────────

@router.callback_query(F.data == "del_all_final", DeleteStates.confirming_all_final)
async def delete_all_final(callback: CallbackQuery, state: FSMContext, user, services):
    uow = services.transaction_service().uow
    async with uow:
        deleted = await uow.transactions.delete_all_by_user(user.id)

    await state.clear()
    await callback.message.edit_text(
        f"Видалено ✅\nВсі {deleted} транзакцій видалено."
    )
    await callback.answer()


# ── Скасування (будь-який стан Delete) ──────────────────────────────────

@router.callback_query(F.data == "del_cancel", DeleteStates())
async def delete_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано ❌")
    await callback.answer()
