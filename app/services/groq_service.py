import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from groq import AsyncGroq, BadRequestError

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "transaction.md"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


@dataclass
class ParsedTransaction:
    amount: float
    type: str
    category_hint: str
    description: str


@dataclass
class ParsedUnknownRequest:
    pass


ParseResult = ParsedTransaction | ParsedUnknownRequest


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_transaction",
            "description": "Record a financial transaction — income or expense. Call only when message contains an explicit number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount, always a positive number",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["income", "expense"],
                        "description": "income = дохід, expense = витрата",
                    },
                    "category_hint": {
                        "type": "string",
                        "description": (
                            "Transaction category. You MUST copy the value EXACTLY as it appears in the "
                            "available categories list — same script (Cyrillic vs Latin), same case, "
                            "character by character. Do NOT transliterate, do NOT mix scripts. "
                            "Default: food, transport, health, shopping, entertainment, utilities, rent, other. "
                            "Custom user categories take priority. Use 'other' only when nothing fits."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description of the transaction",
                    },
                },
                "required": ["amount", "type", "category_hint", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unknown_request",
            "description": "Call when message has no number or is not a financial transaction (greetings, questions, random text).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class GroqService:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def parse_message(self, text: str, categories: list[str]) -> ParseResult:
        category_list = ", ".join(categories)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    f"Available categories for this user: [{category_list}]. "
                    "CRITICAL: for category_hint you MUST return the value as a verbatim copy from this list. "
                    "Copy the exact characters — do NOT change the script (Cyrillic stays Cyrillic, Latin stays Latin), "
                    "do NOT transliterate, do NOT mix Cyrillic and Latin letters within one word. "
                    "Use your world knowledge to match the item to the most fitting category by meaning. "
                    "Custom categories (those not in the default list) were created by the user "
                    "and likely represent specific spending habits — apply them broadly. "
                    "For example: if a category named after a drink type exists, use it for any drinks; "
                    "if a category named after a person exists, use it for spending related to that person; "
                    "if a category named after an animal/pet exists, use it for pet-related spending. "
                    "Use 'other' ONLY when no category fits even by broad semantic reasoning."
                ),
            },
            {"role": "user", "content": text},
        ]
        logger.info("Groq prompt: %s", json.dumps(messages, ensure_ascii=False))

        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=TOOLS,
                tool_choice="required",
            )
        except BadRequestError as e:
            return self._parse_failed_generation(e)

        tool_call = response.choices[0].message.tool_calls[0]
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
        logger.info("Tool called: %s | args: %s", name, args)

        if name == "create_transaction":
            return ParsedTransaction(
                amount=args["amount"],
                type=args["type"],
                category_hint=args["category_hint"],
                description=args["description"],
            )

        return ParsedUnknownRequest()

    def _parse_failed_generation(self, error: BadRequestError) -> ParseResult:
        try:
            body = error.body or {}
            failed = body.get("error", {}).get("failed_generation", "")
            match = re.search(r"<function=\w+=({.*?})</function>", failed, re.DOTALL)
            if not match:
                return ParsedUnknownRequest()
            args = json.loads(match.group(1))
            if "amount" not in args:
                return ParsedUnknownRequest()
            logger.info("Recovered from failed_generation: %s", args)
            return ParsedTransaction(
                amount=args["amount"],
                type=args.get("type", "expense"),
                category_hint=args.get("category_hint", "other"),
                description=args.get("description", ""),
            )
        except Exception:
            logger.warning("Could not recover from failed_generation", exc_info=True)
            return ParsedUnknownRequest()
