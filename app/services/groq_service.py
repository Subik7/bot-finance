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

SYSTEM_PROMPT = """Ти асистент для обліку особистих фінансів.

Інструменти:
- create_transaction — якщо є сума грошей
- get_balance — якщо питають про баланс
- delete_last_transaction — якщо просять відмінити/видалити останню операцію
- list_categories — якщо питають які є категорії
- get_analytics — якщо просять аналітику, статистику, графік

Правила для create_transaction:
- Без явного доходу (отримав/зарплата/продав/заробив) → expense
- Категорії:
  * food → їжа, кафе, кав'ярня, ресторан, продукти, доставка
  * transport → таксі, метро, бензин, автобус, СТО, сто, автосервіс, мийка
  * health → аптека, лікар, клініка, ліки
  * shopping → магазин, одяг, взуття, техніка
  * entertainment → кіно, концерт, гра, підписка, Netflix, Spotify
  * utilities → комуналка, інтернет, телефон, світло, вода, газ
  * rent → оренда, квартира
  * other → все інше

Правила для get_analytics:
- "за тиждень/тиждні" → week
- "за місяць" → month
- "за 3 місяці" → 3months
- без уточнення → month
- "по категоріях/розбивку" → category
- "по днях/динаміку" → days
- "дохід і витрати/порівняй" → income_expense
- без уточнення типу → text

Якщо не про фінанси → не викликай нічого, відповідай як асистент."""


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
                    "If the message clearly matches a default category, for example ATB or groceries, "
                    "use the default category food. "
                    "If an exact or obvious custom user category fits, use it. "
                    "If nothing fits, use other."
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
            return ParsedTextResponse(text=message.content)

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
