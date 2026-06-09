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

    async def _load(
        self,
        user_id: int,
        period: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ):
        if since is None:
            since = self._since(period)
        async with self.uow:
            txs = await self.uow.transactions.get_by_user_since(user_id, since, until)
            cats = await self.uow.categories.get_by_user(user_id)
        cat_map = {c.id: c.name for c in cats}
        return txs, cat_map

    async def chart_by_category(
        self, user_id: int, period: str,
        since: datetime | None = None, until: datetime | None = None,
    ) -> io.BytesIO | None:
        txs, cat_map = await self._load(user_id, period, since, until)

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

    async def chart_by_days(
        self, user_id: int, period: str,
        since: datetime | None = None, until: datetime | None = None,
    ) -> io.BytesIO | None:
        txs, _ = await self._load(user_id, period, since, until)

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
        self, user_id: int, period: str,
        since: datetime | None = None, until: datetime | None = None,
    ) -> io.BytesIO | None:
        txs, _ = await self._load(user_id, period, since, until)

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

    async def chart_category_detail(
        self, user_id: int, period: str, category_name: str,
        since: datetime | None = None, until: datetime | None = None,
    ) -> io.BytesIO | None:
        txs, cat_map = await self._load(user_id, period, since, until)

        daily = defaultdict(float)
        for tx in txs:
            if tx.amount < 0 and cat_map.get(tx.category_id) == category_name:
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

        ax.set_title(
            f"{category_name} — {PERIOD_LABELS[period]}", fontsize=14
        )
        ax.set_ylabel("Сума (грн)")
        ax.set_xlabel("День")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        buf.seek(0)
        plt.close()
        return buf

    async def text_summary(
        self, user_id: int, period: str,
        since: datetime | None = None, until: datetime | None = None,
    ) -> dict:
        txs, cat_map = await self._load(user_id, period, since, until)

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

    async def top_expenses(
        self,
        user_id: int,
        period: str,
        limit: int = 10,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict]:
        txs, cat_map = await self._load(user_id, period, since, until)
        expenses = [
            {
                "amount": abs(tx.amount),
                "description": tx.description,
                "category": cat_map.get(tx.category_id, "other"),
                "date": tx.created_at.strftime("%d.%m"),
            }
            for tx in txs if tx.amount < 0
        ]
        expenses.sort(key=lambda x: x["amount"], reverse=True)
        return expenses[:limit]

    async def compare_periods(self, user_id: int, period: str) -> dict | None:
        days = PERIOD_MAP.get(period)
        if not days:
            return None

        now = datetime.utcnow()
        cur_since = now - timedelta(days=days)
        prev_since = now - timedelta(days=days * 2)

        async with self.uow:
            cur_txs = await self.uow.transactions.get_by_user_since(user_id, cur_since)
            prev_txs = await self.uow.transactions.get_by_user_since(user_id, prev_since, cur_since)
            cats = await self.uow.categories.get_by_user(user_id)

        cat_map = {c.id: c.name for c in cats}

        def summarize(txs):
            income = sum(tx.amount for tx in txs if tx.amount > 0)
            expense = sum(abs(tx.amount) for tx in txs if tx.amount < 0)
            by_cat = defaultdict(float)
            for tx in txs:
                if tx.amount < 0:
                    by_cat[cat_map.get(tx.category_id, "other")] += abs(tx.amount)
            return {"income": income, "expense": expense, "balance": income - expense, "by_cat": dict(by_cat)}

        def pct(curr, prev):
            if prev == 0:
                return None
            return (curr - prev) / prev * 100

        cur = summarize(cur_txs)
        prev = summarize(prev_txs)
        return {
            "current": cur,
            "previous": prev,
            "expense_pct": pct(cur["expense"], prev["expense"]),
            "income_pct": pct(cur["income"], prev["income"]),
            "balance_pct": pct(cur["balance"], prev["balance"]),
        }

    async def chart_compare_periods(self, user_id: int, period: str) -> io.BytesIO | None:
        data = await self.compare_periods(user_id, period)
        if data is None:
            return None

        cur = data["current"]
        prev = data["previous"]

        if all(v == 0 for v in [cur["income"], cur["expense"], prev["income"], prev["expense"]]):
            return None

        categories = ["Доходи", "Витрати"]
        cur_vals = [cur["income"], cur["expense"]]
        prev_vals = [prev["income"], prev["expense"]]
        x = [0, 1]
        w = 0.35

        C_INC_CUR  = "#388E3C"
        C_INC_PREV = "#81C784"
        C_EXP_CUR  = "#C62828"
        C_EXP_PREV = "#EF9A9A"

        fig, ax = plt.subplots(figsize=(7, 5))
        bars_prev = ax.bar(
            [i - w / 2 for i in x], prev_vals, w,
            color=[C_INC_PREV, C_EXP_PREV], alpha=0.85,
        )
        bars_cur = ax.bar(
            [i + w / 2 for i in x], cur_vals, w,
            color=[C_INC_CUR, C_EXP_CUR],
        )

        max_val = max(max(cur_vals), max(prev_vals)) or 1
        for bar in [*bars_prev, *bars_cur]:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.015,
                f"{bar.get_height():.0f}",
                ha="center", va="bottom", fontsize=9,
            )

        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=C_INC_CUR,  label="Доходи поточні"),
            Patch(facecolor=C_INC_PREV, alpha=0.85, label="Доходи попередні"),
            Patch(facecolor=C_EXP_CUR,  label="Витрати поточні"),
            Patch(facecolor=C_EXP_PREV, alpha=0.85, label="Витрати попередні"),
        ]

        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.set_ylabel("Сума (грн)")
        ax.set_title(f"Порівняння периодів — {PERIOD_LABELS[period]}", fontsize=14)
        ax.legend(handles=legend_elements, fontsize=8)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        buf.seek(0)
        plt.close()
        return buf
