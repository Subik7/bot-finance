from sqlalchemy import select

from models.category import CategoryModel, SYSTEM_CATEGORIES


async def seed_system_categories(session, user_id: int):

    result = await session.execute(
        select(CategoryModel.name).where(
            CategoryModel.user_id == user_id,
            CategoryModel.is_system == True,
        )
    )

    existing = set(result.scalars().all())

    new_categories = [
        CategoryModel(
            user_id=user_id,
            name=name,
            is_system=True,
        )
        for name in SYSTEM_CATEGORIES
        if name not in existing
    ]

    session.add_all(new_categories)
    await session.commit()