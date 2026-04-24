from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.analytics import PERIOD_LABELS

router = Router()


class AnalyticsStates(StatesGroup):
    choosing_type = State()
    choosing_period = State()


def type_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 По категоріях",      callback_data="atype:category")
    kb.button(text="📅 По днях",             callback_data="atype:days")
    kb.button(text="💰 Дохід vs Витрати",   callback_data="atype:income_expense")
    kb.button(text="📝 Текстовий звіт",     callback_data="atype:text")
    kb.adjust(2)
    return kb.as_markup()


def period_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="7 днів",    callback_data="period:week")
    kb.button(text="Місяць",    callback_data="period:month")
    kb.button(text="3 місяці",  callback_data="period:3months")
    kb.button(text="Весь час",  callback_data="period:all")
    kb.adjust(2)
    return kb.as_markup()


@router.message(Command("analytics"))
async def analytics_start(message: Message, state: FSMContext):
    await state.set_state(AnalyticsStates.choosing_type)
    await message.answer("Оберіть тип аналітики:", reply_markup=type_keyboard())


@router.callback_query(F.data.startswith("atype:"), AnalyticsStates.choosing_type)
async def analytics_type_chosen(callback: CallbackQuery, state: FSMContext):
    atype = callback.data.split(":")[1]
    await state.update_data(atype=atype)
    await state.set_state(AnalyticsStates.choosing_period)
    await callback.message.edit_text("За який період?", reply_markup=period_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("period:"), AnalyticsStates.choosing_period)
async def period_chosen(callback: CallbackQuery, state: FSMContext, user, services):
    period = callback.data.split(":")[1]
    data = await state.get_data()
    atype = data["atype"]
    await state.clear()

    await callback.message.edit_text("Генерую... ⏳")
    await callback.answer()

    analytics = services.analytics_service()
    period_label = PERIOD_LABELS[period]

    if atype == "text":
        summary = await analytics.text_summary(user.id, period)
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

    buf = await method_map[atype](user.id, period)

    if buf is None:
        await callback.message.edit_text("Немає даних за цей період 😕")
        return

    photo = BufferedInputFile(buf.read(), filename="analytics.png")
    await callback.message.answer_photo(
        photo,
        caption=f"{titles[atype]} — {period_label}"
    )
    await callback.message.delete()