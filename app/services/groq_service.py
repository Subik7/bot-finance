import json
import logging
from dataclasses import dataclass

from groq import AsyncGroq

logger = logging.getLogger(__name__)


@dataclass
class ParsedTransaction:
    amount: float
    type: str
    category_hint: str
    description: str


@dataclass
class ParsedBalanceRequest:
    pass


@dataclass
class ParsedTextResponse:
    text: str


@dataclass
class ParsedDeleteLast:
    pass


@dataclass
class ParsedListCategories:
    pass


@dataclass
class ParsedAnalyticsRequest:
    period: str
    analytics_type: str


ParseResult = (
    ParsedTransaction
    | ParsedBalanceRequest
    | ParsedTextResponse
    | ParsedDeleteLast
    | ParsedListCategories
    | ParsedAnalyticsRequest
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_transaction",
            "description": "Записує фінансову операцію — дохід або витрату",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Сума операції, завжди позитивне число",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["income", "expense"],
                        "description": "income = дохід, expense = витрата",
                    },
                    "category_hint": {
                        "type": "string",
                        "description": (
                            "Transaction category. Use one of the available user categories. "
                            "Default categories: food, transport, health, shopping, entertainment, utilities, rent, other. "
                            "If a custom user category clearly fits, use it. "
                            "If nothing fits, use other."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "Короткий опис операції",
                    },
                },
                "required": ["amount", "type", "category_hint", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "Показує поточний баланс користувача",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_last_transaction",
            "description": "Видаляє або відміняє останню записану транзакцію",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "Показує список доступних категорій витрат користувача",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_analytics",
            "description": "Показує аналітику, статистику або графік витрат за певний період",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["week", "month", "3months", "all"],
                        "description": "week=7 днів, month=30 днів, 3months=90 днів, all=весь час",
                    },
                    "analytics_type": {
                        "type": "string",
                        "enum": ["category", "days", "income_expense", "text"],
                        "description": "category=по категоріях, days=по днях, income_expense=доходи vs витрати, text=текстовий звіт",
                    },
                },
                "required": ["period", "analytics_type"],
            },
        },
    },
]

SYSTEM_PROMPT = """Ти розумний Telegram-асистент з двома режимами роботи.

━━━ РЕЖИМ 1 — ФІНАНСИ (викликай інструменти) ━━━

create_transaction — ТІЛЬКИ якщо в повідомленні є ЯВНА ЧИСЛОВА СУМА (цифри).
  ⚠️ ЗАБОРОНЕНО викликати create_transaction якщо в тексті немає жодного числа!
  ⚠️ Питання, привітання, запити пояснення — НЕ є транзакціями.
  Правила:
  - Без явного доходу (отримав/зарплата/продав/заробив) → expense
  - Категорії:
    * food → їжа, кафе, кав'ярня, ресторан, продукти, доставка
    * transport → таксі, метро, бензин, автобус, СТО, автосервіс, мийка
    * health → аптека, лікар, клініка, ліки
    * shopping → магазин, одяг, взуття, техніка
    * entertainment → кіно, концерт, гра, підписка, Netflix, Spotify
    * utilities → комуналка, інтернет, телефон, світло, вода, газ
    * rent → оренда, квартира
    * other → все інше

get_balance — якщо питають про баланс або залишок

delete_last_transaction — якщо просять відмінити/видалити останню операцію

list_categories — якщо питають які є категорії

get_analytics — якщо просять аналітику, статистику, графік
  - "за тиждень" → week, "за місяць" → month, "за 3 місяці" → 3months, без уточнення → month
  - "по категоріях" → category, "по днях" → days, "дохід і витрати" → income_expense, без уточнення → text

━━━ РЕЖИМ 2 — ЗВИЧАЙНИЙ АСИСТЕНТ (НЕ викликай інструменти) ━━━

Якщо повідомлення НЕ є фінансовою операцією з числом — відповідай як корисний AI-асистент.
ВАЖЛИВО: Відповідай ВИКЛЮЧНО українською мовою. Не використовуй слова з інших мов.
Будь дружнім, коротким і корисним."""


class GroqService:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def parse_message(self, text: str, categories: list[str]) -> ParseResult:
        category_list = ", ".join(categories)
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    "Available user categories: "
                    f"{category_list}. "
                    "For create_transaction, choose category_hint only from this list. "
                    "Default categories are useful, but custom user categories have priority over other. "
                    "Choose a custom category when the item, service, merchant, or context semantically belongs to it, "
                    "even if the category name is not written exactly in the user message. "
                    "For example: if the user has category \u0430\u043b\u043a\u043e\u0433\u043e\u043b\u044c, then \u043f\u0438\u0432\u043e, \u0432\u0438\u043d\u043e, \u0442\u0435\u043a\u0456\u043b\u0430, \u0433\u043e\u0440\u0456\u043b\u043a\u0430 should use \u0430\u043b\u043a\u043e\u0433\u043e\u043b\u044c; "
                    "if the user has category \u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438, then MacBook, Lenovo laptop, laptop repair, laptop charger should use \u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438; "
                    "if the user has category \u0441\u043f\u043e\u0440\u0442, then gym, \u0442\u0440\u0435\u043d\u0443\u0432\u0430\u043d\u043d\u044f, \u0430\u0431\u043e\u043d\u0435\u043c\u0435\u043d\u0442 should use \u0441\u043f\u043e\u0440\u0442. "
                    "If the message clearly matches a default category, for example ATB or groceries, use food. "
                    "Use other only when no default or custom category fits."
                ),
            },
            {"role": "user", "content": text},
        ]
        logger.info(
            "Groq prompt messages: %s",
            json.dumps(prompt_messages, ensure_ascii=False),
        )

        response = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=prompt_messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            content = message.content or "Вибач, не зміг відповісти. Спробуй ще раз."
            return ParsedTextResponse(text=content)

        tool_call = message.tool_calls[0]
        name = tool_call.function.name
        args = (
            json.loads(tool_call.function.arguments)
            if tool_call.function.arguments
            else {}
        )

        match name:
            case "create_transaction":
                return ParsedTransaction(
                    amount=args["amount"],
                    type=args["type"],
                    category_hint=args["category_hint"],
                    description=args["description"],
                )
            case "get_balance":
                return ParsedBalanceRequest()
            case "delete_last_transaction":
                return ParsedDeleteLast()
            case "list_categories":
                return ParsedListCategories()
            case "get_analytics":
                return ParsedAnalyticsRequest(
                    period=args.get("period", "month"),
                    analytics_type=args.get("analytics_type", "text"),
                )
            case _:
                return ParsedTextResponse(text="Не зрозумів запит")
