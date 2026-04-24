from models.transaction import TransactionModel
from repositories.uow import UnitOfWork
from services.analytics import AnalyticsService
from services.category import CategoryService
from services.groq_service import (
    GroqService,
    ParsedAnalyticsRequest,
    ParsedBalanceRequest,
    ParsedDeleteLast,
    ParsedListCategories,
    ParsedTextResponse,
    ParsedTransaction,
)


class TransactionService:
    def __init__(
        self,
        uow: UnitOfWork,
        category_service: CategoryService,
        groq_service: GroqService,
        analytics_service: AnalyticsService,
    ):
        self.uow = uow
        self.category_service = category_service
        self.groq_service = groq_service
        self.analytics_service = analytics_service

    async def handle_message(self, user_id: int, text: str):
        parsed = await self.groq_service.parse_message(text)

        if isinstance(parsed, ParsedTextResponse):
            return parsed

        if isinstance(parsed, ParsedBalanceRequest):
            return await self._get_balance(user_id)

        if isinstance(parsed, ParsedDeleteLast):
            return await self._delete_last(user_id)

        if isinstance(parsed, ParsedListCategories):
            return await self._list_categories(user_id)

        if isinstance(parsed, ParsedAnalyticsRequest):
            return await self._get_analytics(user_id, parsed)

        if isinstance(parsed, ParsedTransaction):
            return await self._create_transaction(user_id, parsed)

    async def _create_transaction(
        self, user_id: int, parsed: ParsedTransaction
    ) -> TransactionModel:
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
        return tx

    async def _get_balance(self, user_id: int) -> dict:
        async with self.uow:
            txs = await self.uow.transactions.get_by_user(user_id)

        income = sum(tx.amount for tx in txs if tx.amount > 0)
        expense = sum(tx.amount for tx in txs if tx.amount < 0)
        return {
            "type": "balance",
            "balance": income + expense,
            "income": income,
            "expense": expense,
        }

    async def _delete_last(self, user_id: int) -> dict:
        async with self.uow:
            tx = await self.uow.transactions.get_last(user_id)
            if not tx:
                return {"type": "delete_last", "success": False}
            desc = tx.description
            amount = tx.amount
            await self.uow.transactions.delete(tx)
        return {
            "type": "delete_last",
            "success": True,
            "description": desc,
            "amount": amount,
        }

    async def _list_categories(self, user_id: int) -> dict:
        cats = await self.category_service.get_all_for_user(user_id)
        return {"type": "categories", "names": [c.name for c in cats]}

    async def _get_analytics(self, user_id: int, parsed: ParsedAnalyticsRequest):
        method_map = {
            "category": self.analytics_service.chart_by_category,
            "days": self.analytics_service.chart_by_days,
            "income_expense": self.analytics_service.chart_income_expense,
            "text": None,
        }

        if parsed.analytics_type == "text":
            summary = await self.analytics_service.text_summary(user_id, parsed.period)
            summary["type"] = "analytics_text"
            summary["period"] = parsed.period
            return summary

        chart_fn = method_map[parsed.analytics_type]
        buf = await chart_fn(user_id, parsed.period)
        return {
            "type": "analytics_chart",
            "buf": buf,
            "period": parsed.period,
            "analytics_type": parsed.analytics_type,
        }
