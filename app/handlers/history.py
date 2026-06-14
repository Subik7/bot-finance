from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

PAGE_SIZE = 10

router = Router()

FILTER_LABELS = {
    "all":     "Всі",
    "expense": "Витрати",
    "income":  "Доходи",
}


class HistoryStates(StatesGroup):
    browsing = State()
    choosing_category = State()


def _filter_keyboard(active: str, offset: int, total: int, cat_name: str | None = None):
    kb = InlineKeyboardBuilder()

    for key, label in FILTER_LABELS.items():
        text = f"• {label}" if key == active else label
        kb.button(text=text, callback_data=f"hist_filter:{key}")
    kb.adjust(3)

    cat_row = InlineKeyboardBuilder()
    cat_label = f"• Категорія: {cat_name}" if cat_name else "По категорії"
    cat_row.button(text=cat_label, callback_data="hist_pick_cat")
    if cat_name:
        cat_row.button(text="Скинути", callback_data="hist_filter:all")
    cat_row.adjust(2 if cat_name else 1)
    kb.attach(cat_row)

    nav = InlineKeyboardBuilder()
    if offset > 0:
        nav.button(text="⬅️ Назад", callback_data=f"hist_page:{offset - PAGE_SIZE}")
    if offset + PAGE_SIZE < total:
        nav.button(text="➡️ Далі", callback_data=f"hist_page:{offset + PAGE_SIZE}")
    if offset > 0 or offset + PAGE_SIZE < total:
        nav.adjust(2)
        kb.attach(nav)

    bottom = InlineKeyboardBuilder()
    bottom.button(text="❌ Закрити", callback_data="hist_close")
    bottom.adjust(1)
    kb.attach(bottom)

    return kb.as_markup()


async def _show_page(
    target,
    state: FSMContext,
    user_id: int,
    offset: int,
    services,
    tx_type: str = "all",
    category_id: int | None = None,
    cat_name: str | None = None,
    edit: bool = False,
):
    uow = services.transaction_service().uow
    async with uow:
        txs = await uow.transactions.get_page(user_id, offset, PAGE_SIZE, tx_type, category_id)
        total = await uow.transactions.count(user_id, tx_type, category_id)
        cats = await uow.categories.get_by_user(user_id)

    cat_map = {c.id: c.name for c in cats}

    filter_label = FILTER_LABELS[tx_type]
    title = f"📋 *Історія — {filter_label}*"
    if cat_name:
        title += f" / {cat_name}"

    kb = _filter_keyboard(tx_type, offset, total, cat_name)

    if not txs:
        text = f"{title}\n\nТранзакцій не знайдено 🤷"
        if edit:
            await target.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        else:
            await target.answer(text, reply_markup=kb, parse_mode="Markdown")
        await state.set_state(HistoryStates.browsing)
        await state.update_data(offset=0, tx_type=tx_type, category_id=category_id, cat_name=cat_name)
        return

    lines = [f"{title} (всього: {total})\n"]

    current_date = None
    for tx in txs:
        date = tx.created_at.strftime("%d.%m.%Y")
        if date != current_date:
            current_date = date
            lines.append(f"\n📅 {date}")
        sign = "+" if tx.amount > 0 else ""
        category = cat_map.get(tx.category_id, "other")
        lines.append(f"{sign}{tx.amount:.0f} грн  |  {tx.description}  |  категорія: {category}")

    page_info = f"Сторінка {offset // PAGE_SIZE + 1}/{(total - 1) // PAGE_SIZE + 1}"
    text = "\n".join(lines) + f"\n\n_{page_info}_"

    await state.set_state(HistoryStates.browsing)
    await state.update_data(offset=offset, tx_type=tx_type, category_id=category_id, cat_name=cat_name)

    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="Markdown")


# ── старт ────────────────────────────────────────────────────────────────

@router.message(Command("history"))
async def history_start(message: Message, state: FSMContext, user, services):
    await _show_page(message, state, user.id, offset=0, services=services)


# ── пагінація ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("hist_page:"), HistoryStates.browsing)
async def history_page(callback: CallbackQuery, state: FSMContext, user, services):
    offset = int(callback.data.split(":")[1])
    data = await state.get_data()
    await _show_page(
        callback.message, state, user.id, offset=offset, services=services,
        tx_type=data.get("tx_type", "all"),
        category_id=data.get("category_id"),
        cat_name=data.get("cat_name"),
        edit=True,
    )
    await callback.answer()


# ── фільтр по типу ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("hist_filter:"), HistoryStates.browsing)
async def history_filter(callback: CallbackQuery, state: FSMContext, user, services):
    tx_type = callback.data.split(":")[1]
    # скидаємо фільтр категорії при "Всі"
    cat_id = None if tx_type == "all" else (await state.get_data()).get("category_id")
    cat_name = None if tx_type == "all" else (await state.get_data()).get("cat_name")
    await _show_page(
        callback.message, state, user.id, offset=0, services=services,
        tx_type=tx_type, category_id=cat_id, cat_name=cat_name, edit=True,
    )
    await callback.answer()


# ── вибір категорії ──────────────────────────────────────────────────────

@router.callback_query(F.data == "hist_pick_cat", HistoryStates.browsing)
async def history_pick_cat(callback: CallbackQuery, state: FSMContext, user, services):
    uow = services.transaction_service().uow
    async with uow:
        cats = await uow.categories.get_by_user(user.id)

    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=cat.name, callback_data=f"hist_cat:{cat.id}:{cat.name}")
    kb.adjust(2)

    back = InlineKeyboardBuilder()
    back.button(text="⬅️ Назад", callback_data="hist_cat_back")
    back.adjust(1)
    kb.attach(back)

    await state.set_state(HistoryStates.choosing_category)
    await callback.message.edit_text("Оберіть категорію:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("hist_cat:"), HistoryStates.choosing_category)
async def history_cat_chosen(callback: CallbackQuery, state: FSMContext, user, services):
    _, cat_id, cat_name = callback.data.split(":", 2)
    data = await state.get_data()
    await _show_page(
        callback.message, state, user.id, offset=0, services=services,
        tx_type=data.get("tx_type", "all"),
        category_id=int(cat_id),
        cat_name=cat_name,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data == "hist_cat_back", HistoryStates.choosing_category)
async def history_cat_back(callback: CallbackQuery, state: FSMContext, user, services):
    data = await state.get_data()
    await _show_page(
        callback.message, state, user.id,
        offset=data.get("offset", 0), services=services,
        tx_type=data.get("tx_type", "all"),
        category_id=data.get("category_id"),
        cat_name=data.get("cat_name"),
        edit=True,
    )
    await callback.answer()


# ── закрити ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "hist_close", HistoryStates())
async def history_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()
