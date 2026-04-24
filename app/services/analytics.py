import io
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from repositories.uow import UnitOfWork

PERIOD_MAP = {
    "week": 7,
    "month": 30,
    "3months": 90,
    "all": None,
}

PERIOD_LABELS = {
    "week": "7 днів",
    "month": "місяць",
    "3months": "3 місяці",
    "all": "весь час",
}


class AnalyticsService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def _since(self, period: str) -> datetime:
        days = PERIOD_MAP.get(period)
        if days is None:
            return datetime(2000, 1, 1)
        return datetime.utcnow() - timedelta(days=days)

    async def _load(self, user_id: int, period: str):
        since = self._since(period)
        async with self.uow:
            txs = await self.uow.transactions.get_by_user_since(user_id, since)
            cats = await self.uow.categories.get_by_user(user_id)
        cat_map = {c.id: c.name for c in cats}
        return txs, cat_map

    async def chart_by_category(self, user_id: int, period: str) -> io.BytesIO | None:
        txs, cat_map = await self._load(user_id, period)

        expenses = defaultdict(float)
        for tx in txs:
            if tx.amount < 0:
                expenses[cat_map.get(tx.category_id, "other")] += abs(tx.amount)

        if not expenses:
            return None

        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(expenses.keys())
        values = list(expenses.values())

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.85,
        )
        ax.set_title(
            f"Витрати по категоріях — {PERIOD_LABELS[period]}", fontsize=14, pad=20
        )

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        plt.close()
        return buf

    async def chart_by_days(self, user_id: int, period: str) -> io.BytesIO | None:
        txs, _ = await self._load(user_id, period)

        daily = defaultdict(float)
        for tx in txs:
            if tx.amount < 0:
                day = tx.created_at.strftime("%d.%m")
                daily[day] += abs(tx.amount)

        if not daily:
            return None

        days = list(daily.keys())
        values = list(daily.values())

        fig, ax = plt.subplots(figsize=(max(8, len(days) * 0.6), 5))
        bars = ax.bar(days, values, color="#5DCAA5", edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.01,
                f"{val:.0f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        ax.set_title(f"Витрати по днях — {PERIOD_LABELS[period]}", fontsize=14)
        ax.set_ylabel("Сума (грн)")
        ax.set_xlabel("День")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        buf.seek(0)
        plt.close()
        return buf

    async def chart_income_expense(
        self, user_id: int, period: str
    ) -> io.BytesIO | None:
        txs, _ = await self._load(user_id, period)

        income = sum(tx.amount for tx in txs if tx.amount > 0)
        expense = sum(abs(tx.amount) for tx in txs if tx.amount < 0)

        if income == 0 and expense == 0:
            return None

        fig, ax = plt.subplots(figsize=(6, 5))
        bars = ax.bar(
            ["Доходи", "Витрати"],
            [income, expense],
            color=["#639922", "#E24B4A"],
            width=0.5,
            edgecolor="white",
        )

        max_val = max(income, expense)
        for bar, val in zip(bars, [income, expense]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.02,
                f"{val:.2f} грн",
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
            )

        ax.set_title(f"Дохід vs Витрати — {PERIOD_LABELS[period]}", fontsize=14)
        ax.set_ylabel("Сума (грн)")
        ax.set_ylim(0, max_val * 1.2)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        buf.seek(0)
        plt.close()
        return buf

    async def text_summary(self, user_id: int, period: str) -> dict:
        txs, cat_map = await self._load(user_id, period)

        income = sum(tx.amount for tx in txs if tx.amount > 0)
        expense = sum(abs(tx.amount) for tx in txs if tx.amount < 0)

        by_cat = defaultdict(float)
        for tx in txs:
            if tx.amount < 0:
                by_cat[cat_map.get(tx.category_id, "other")] += abs(tx.amount)

        return {
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "count": len(txs),
            "by_category": dict(
                sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
            ),
        }
