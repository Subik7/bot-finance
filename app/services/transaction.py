from models.transaction import TransactionModel
from repositories.uow import UnitOfWork
from services.category import CategoryService
from services.groq_service import GroqService, ParsedTransaction, ParsedUnknownRequest


class TransactionService:
    def __init__(self, uow: UnitOfWork, category_service: CategoryService, groq_service: GroqService):
        self.uow = uow
        self.category_service = category_service
        self.groq_service = groq_service

    async def handle_message(self, user_id: int, text: str) -> tuple[TransactionModel, str] | None:
        categories = await self.category_service.get_all_for_user(user_id)
        category_names = [c.name for c in categories]

        parsed = await self.groq_service.parse_message(text, category_names)

        if isinstance(parsed, ParsedUnknownRequest):
            return None

        if isinstance(parsed, ParsedTransaction):
            return await self._create_transaction(user_id, parsed)

    async def _create_transaction(self, user_id: int, parsed: ParsedTransaction) -> tuple[TransactionModel, str]:
        if parsed.amount <= 0:
            raise ValueError(f"Некоректна сума: {parsed.amount}")

        category = await self.category_service.resolve(user_id, parsed.category_hint)
        final_amount = parsed.amount if parsed.type == "income" else -abs(parsed.amount)

        async with self.uow:
            tx = TransactionModel(
                user_id=user_id,
                amount=final_amount,
                category_id=category.id,
                description=parsed.description,
            )
            await self.uow.transactions.add(tx)
        return tx, category.name
