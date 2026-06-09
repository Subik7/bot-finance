from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram_calendar.simple_calendar import SimpleCalAct

from services.analytics import PERIOD_LABELS

router = Router()

CAT_PAGE_SIZE = 8


class AnalyticsStates(StatesGroup):
    choosing_type = State()
    choosing_category = State()
    choosing_period = State()
    entering_start_date = State()
    entering_end_date = State()


def type_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 По категоріях",    callback_data="atype:category")
    kb.button(text="📅 По днях",           callback_data="atype:days")
    kb.button(text="💰 Дохід vs Витрати", callback_data="atype:income_expense")
    kb.button(text="📝 Текстовий звіт",   callback_data="atype:text")
    kb.button(text="📈 Порівняння",        callback_data="atype:compare")
    kb.button(text="🏆 Топ витрат",        callback_data="atype:top")
    kb.adjust(2)
    kb.button(text="❌ Скасувати", callback_data="a_cancel")
    kb.adjust(2)
    return kb.as_markup()


def category_keyboard(cats_page: list, offset: int, total: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Всі категорії", callback_data="acat:__all__")
    for cat in cats_page:
        kb.button(text=cat.name, callback_data=f"acat:{cat.name}")
    kb.adjust(2)

    if offset > 0 or offset + CAT_PAGE_SIZE < total:
        nav = InlineKeyboardBuilder()
        if offset > 0:
            nav.button(text="⬅️ Попередні", callback_data=f"acat_page:{offset - CAT_PAGE_SIZE}")
        if offset + CAT_PAGE_SIZE < total:
            nav.button(text="➡️ Наступні", callback_data=f"acat_page:{offset + CAT_PAGE_SIZE}")
        nav.adjust(2)
        kb.attach(nav)

    bottom = InlineKeyboardBuilder()
    bottom.button(text="⬅️ Назад",    callback_data="a_back_to_type")
    bottom.button(text="❌ Скасувати", callback_data="a_cancel")
    bottom.adjust(2)
    kb.attach(bottom)

    return kb.as_markup()


def period_keyboard(back_to: str, show_all: bool = True, show_custom: bool = True):
    kb = InlineKeyboardBuilder()
    kb.button(text="7 днів",   callback_data="period:week")
    kb.button(text="Місяць",   callback_data="period:month")
    kb.button(text="3 місяці", callback_data="period:3months")
    if show_all:
        kb.button(text="Весь час", callback_data="period:all")
    kb.adjust(2)

    if show_custom:
        custom = InlineKeyboardBuilder()
        custom.button(text="📅 Свій діапазон", callback_data="period:custom")
        custom.adjust(1)
        kb.attach(custom)

    bottom = InlineKeyboardBuilder()
    bottom.button(text="⬅️ Назад",    callback_data=f"a_back_to:{back_to}")
    bottom.button(text="❌ Скасувати", callback_data="a_cancel")
    bottom.adjust(2)
    kb.attach(bottom)

    return kb.as_markup()


async def _show_category_page(target, state: FSMContext, user, services, offset: int):
    all_cats = await services.category_service().get_all_for_user(user.id)
    total = len(all_cats)
    cats_page = all_cats[offset: offset + CAT_PAGE_SIZE]
    await state.update_data(cat_offset=offset)
    await state.set_state(AnalyticsStates.choosing_category)
    await target.edit_text("Оберіть категорію:", reply_markup=category_keyboard(cats_page, offset, total))


def _fmt_pct(pct: float | None) -> str:
    if pct is None:
        return "нові дані"
    arrow = "📈" if pct > 0 else ("📉" if pct < 0 else "➡️")
    return f"{arrow} {pct:+.1f}%"


async def _generate_result(
    callback: CallbackQuery,
    user,
    services,
    atype: str,
    category: str | None,
    period_label: str,
    period: str = "all",
    since: datetime | None = None,
    until: datetime | None = None,
):
    analytics = services.analytics_service()
    kwargs = dict(since=since, until=until)

    if atype == "top":
        top = await analytics.top_expenses(user.id, period, **kwargs)
        if not top:
            await callback.message.edit_text("Немає витрат за цей період 😕")
            return
        lines = [f"🏆 Топ витрат — {period_label}\n"]
        for i, tx in enumerate(top, 1):
            lines.append(f"{i}. {tx['amount']:.0f} грн — {tx['description']} ({tx['category']}) {tx['date']}")
        await callback.message.edit_text("\n".join(lines))
        return

    if atype == "compare":
        buf = await analytics.chart_compare_periods(user.id, period)
        data = await analytics.compare_periods(user.id, period)
        if buf is None or data is None:
            await callback.message.edit_text("Недостатньо даних для порівняння 😕")
            return
        cur = data["current"]
        prev = data["previous"]
        caption = (
            f"📈 Порівняння — {period_label}\n\n"
            f"Витрати:  {cur['expense']:.0f} грн  (було: {prev['expense']:.0f})  {_fmt_pct(data['expense_pct'])}\n"
            f"Доходи:   {cur['income']:.0f} грн  (було: {prev['income']:.0f})  {_fmt_pct(data['income_pct'])}\n"
            f"Баланс:   {cur['balance']:.0f} грн  (було: {prev['balance']:.0f})  {_fmt_pct(data['balance_pct'])}"
        )
        photo = BufferedInputFile(buf.read(), filename="analytics.png")
        await callback.message.answer_photo(photo, caption=caption)
        await callback.message.delete()
        return

    if atype == "text":
        summary = await analytics.text_summary(user.id, period, **kwargs)
        by_cat = "\n".join(
            f"  • {cat}: {amt:.2f} грн"
            for cat, amt in summary["by_category"].items()
        ) or "  немає витрат"
        await callback.message.edit_text(
            f"📊 Аналітика — {period_label}\n\n"
            f"📈 Доходи: +{summary['income']:.2f} грн\n"
            f"📉 Витрати: -{summary['expense']:.2f} грн\n"
            f"💰 Баланс: {summary['balance']:.2f} грн\n"
            f"📝 Транзакцій: {summary['count']}\n\n"
            f"По категоріях:\n{by_cat}"
        )
        return

    if atype == "category" and category and category != "__all__":
        buf = await analytics.chart_category_detail(user.id, period, category, **kwargs)
        title = f"📊 {category}"
    else:
        method_map = {
            "category":       analytics.chart_by_category,
            "days":           analytics.chart_by_days,
            "income_expense": analytics.chart_income_expense,
        }
        titles = {
            "category":       "Витрати по категоріях",
            "days":           "Витрати по днях",
            "income_expense": "Дохід vs Витрати",
        }
        buf = await method_map[atype](user.id, period, **kwargs)
        title = titles[atype]

    if buf is None:
        await callback.message.edit_text("Немає даних за цей період 😕")
        return

    photo = BufferedInputFile(buf.read(), filename="analytics.png")
    await callback.message.answer_photo(photo, caption=f"{title} — {period_label}")
    await callback.message.delete()


# ── старт ────────────────────────────────────────────────────

@router.message(Command("analytics"))
async def analytics_start(message: Message, state: FSMContext):
    await state.set_state(AnalyticsStates.choosing_type)
    await message.answer("Оберіть тип аналітики:", reply_markup=type_keyboard())


# ── вибір типу ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("atype:"), AnalyticsStates.choosing_type)
async def analytics_type_chosen(callback: CallbackQuery, state: FSMContext, user, services):
    atype = callback.data.split(":")[1]
    await state.update_data(atype=atype)

    if atype == "category":
        await _show_category_page(callback.message, state, user, services, offset=0)
    else:
        await state.set_state(AnalyticsStates.choosing_period)
        is_compare = atype == "compare"
        await callback.message.edit_text(
            "За який період?",
            reply_markup=period_keyboard(back_to="type", show_all=not is_compare, show_custom=not is_compare),
        )

    await callback.answer()


# ── вибір категорії ──────────────────────────────────────────

@router.callback_query(F.data.startswith("acat_page:"), AnalyticsStates.choosing_category)
async def analytics_category_page(callback: CallbackQuery, state: FSMContext, user, services):
    offset = int(callback.data.split(":")[1])
    await _show_category_page(callback.message, state, user, services, offset)
    await callback.answer()


@router.callback_query(F.data.startswith("acat:"), AnalyticsStates.choosing_category)
async def analytics_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AnalyticsStates.choosing_period)
    await callback.message.edit_text("За який період?", reply_markup=period_keyboard(back_to="category"))
    await callback.answer()


# ── вибір периоду ────────────────────────────────────────────

@router.callback_query(F.data.startswith("period:"), AnalyticsStates.choosing_period)
async def period_chosen(callback: CallbackQuery, state: FSMContext, user, services):
    period = callback.data.split(":")[1]

    if period == "custom":
        await state.set_state(AnalyticsStates.entering_start_date)
        await callback.message.edit_text(
            "Оберіть дату початку:",
            reply_markup=await SimpleCalendar().start_calendar(),
        )
        await callback.answer()
        return

    data = await state.get_data()
    atype = data["atype"]
    category = data.get("category")
    await state.clear()

    await callback.message.edit_text("Генерую... ⏳")
    await callback.answer()

    await _generate_result(
        callback, user, services,
        atype=atype, category=category,
        period=period, period_label=PERIOD_LABELS[period],
    )


# ── календар: вибір дати початку ─────────────────────────────

@router.callback_query(SimpleCalendarCallback.filter(), AnalyticsStates.entering_start_date)
async def start_date_handler(
    callback: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
):
    if callback_data.act == SimpleCalAct.cancel:
        await state.clear()
        await callback.message.edit_text("Скасовано ❌")
        await callback.answer()
        return

    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(custom_start=date.date().isoformat())
        await state.set_state(AnalyticsStates.entering_end_date)
        await callback.message.edit_text(
            f"Початок: {date.strftime('%d.%m.%Y')}\n\nОберіть дату кінця:",
            reply_markup=await SimpleCalendar().start_calendar(date.year, date.month),
        )


# ── календар: вибір дати кінця ───────────────────────────────

@router.callback_query(SimpleCalendarCallback.filter(), AnalyticsStates.entering_end_date)
async def end_date_handler(
    callback: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
    user,
    services,
):
    if callback_data.act == SimpleCalAct.cancel:
        await state.clear()
        await callback.message.edit_text("Скасовано ❌")
        await callback.answer()
        return

    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if not selected:
        return

    data = await state.get_data()
    atype = data["atype"]
    category = data.get("category")
    start = datetime.fromisoformat(data["custom_start"])
    end = datetime(date.year, date.month, date.day, 23, 59, 59)

    if end < start:
        start, end = end, datetime(start.year, start.month, start.day, 23, 59, 59)

    await state.clear()
    period_label = f"{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}"

    await callback.message.edit_text("Генерую... ⏳")
    await callback.answer()

    await _generate_result(
        callback, user, services,
        atype=atype, category=category,
        period_label=period_label,
        since=start, until=end,
    )


# ── навігація назад ──────────────────────────────────────────

@router.callback_query(F.data == "a_back_to_type", AnalyticsStates.choosing_category)
async def back_to_type(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AnalyticsStates.choosing_type)
    await callback.message.edit_text("Оберіть тип аналітики:", reply_markup=type_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("a_back_to:"), AnalyticsStates.choosing_period)
async def back_to(callback: CallbackQuery, state: FSMContext, user, services):
    target = callback.data.split(":")[1]

    if target == "type":
        await state.set_state(AnalyticsStates.choosing_type)
        await callback.message.edit_text("Оберіть тип аналітики:", reply_markup=type_keyboard())
    elif target == "category":
        data = await state.get_data()
        offset = data.get("cat_offset", 0)
        await _show_category_page(callback.message, state, user, services, offset)

    await callback.answer()


@router.callback_query(F.data == "a_cancel", AnalyticsStates())
async def analytics_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано ❌")
    await callback.answer()
