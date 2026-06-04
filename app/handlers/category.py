from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class AddCategoryStates(StatesGroup):
    waiting_name = State()


class DeleteCategoryStates(StatesGroup):
    waiting_name = State()


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
async def delete_category_command(message: Message, state: FSMContext):
    await state.set_state(DeleteCategoryStates.waiting_name)
    await message.answer(
        "Введи назву кастомної категорії, яку треба видалити:\n"
        "Стандартні категорії видаляти не можна."
    )


@router.message(DeleteCategoryStates.waiting_name)
async def delete_category_name(message: Message, state: FSMContext, user, services):
    if not message.text:
        await message.answer("Надішли назву категорії текстом:")
        return

    name = message.text.strip().lower()

    if len(name) < 2:
        await message.answer("Занадто коротко. Спробуй ще раз:")
        return

    try:
        moved_count = await services.category_service().delete_for_user(user.id, name)
        await state.clear()
        await message.answer(
            f"Категорію «{name}» видалено\n"
            f"Транзакцій перенесено в other: {moved_count}"
        )
    except ValueError as e:
        await state.clear()
        await message.answer(str(e))
