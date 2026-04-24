# Task Manager Bot

Telegram-бот для обліку особистих фінансів у вільній формі:
користувач пише повідомлення природною мовою, бот розпізнає намір через LLM (Groq), зберігає транзакції та показує аналітику.

## Можливості

- Додавання витрат і доходів звичайним текстом.
- Отримання поточного балансу, доходів і витрат.
- Видалення останньої транзакції.
- Перегляд списку категорій.
- Додавання власних категорій через команду `/add_category`.
- Аналітика:
- текстовий звіт;
- графік витрат по категоріях;
- графік витрат по днях;
- порівняння доходів і витрат.

## Технології

- Python 3.12+
- `aiogram` (Telegram Bot API)
- `SQLAlchemy` + `aiosqlite` (асинхронна робота з SQLite)
- `groq` (LLM + function/tool calling)
- `matplotlib` (побудова графіків)
- `pydantic-settings` (конфіг через змінні середовища)

## Структура проєкту

```text
app/
  bot.py                # точка входу
  config.py             # налаштування (.env)
  db/session.py         # engine, sessionmaker, init_db
  models/               # SQLAlchemy моделі: user/category/transaction
  repositories/         # CRUD + запити до БД + UnitOfWork
  services/             # бізнес-логіка
  middlewares/          # DI: session/services/user
  handlers/             # Telegram хендлери
  utils/seed_system_categories.py
```

## Як це працює

1. Telegram-апдейт приходить у `Dispatcher` (`app/bot.py`).
2. `DBSessionMiddleware` створює `AsyncSession`.
3. `ServiceMiddleware` створює `ServiceFactory`.
4. `UserMiddleware` знаходить/створює користувача та ініціалізує системні категорії.
5. `transaction_handler` передає текст у `TransactionService`.
6. `GroqService` класифікує повідомлення і повертає одну з дій:
- створити транзакцію;
- показати баланс;
- видалити останню транзакцію;
- показати категорії;
- віддати аналітику.
7. Відповідь повертається в Telegram у тексті або як зображення-графік.

## Вимоги перед запуском

- Створений Telegram-бот через `@BotFather`.
- Отриманий `BOT_TOKEN`.
- Ключ Groq API (`GROQ_API_KEY`).

## Налаштування середовища

Створіть файл `.env` в корені проєкту:

```env
BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
```

Назви змінних мають відповідати полям у `app/config.py`:

- `bot_token`
- `groq_api_key`

`pydantic-settings` автоматично читає `.env`.

## Локальний запуск

### Варіант 1: через `uv` (рекомендовано)

```bash
uv sync
uv run python app/bot.py
```

### Варіант 2: через `venv` + `pip`

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
# source .venv/bin/activate

pip install -U pip
pip install -e .
python app/bot.py
```

Після запуску бот працює в режимі long polling.

## База даних

- Використовується SQLite: `task_manager.db`.
- Таблиці створюються автоматично під час старту (`init_db()`).
- Основні таблиці:
- `users`
- `categories`
- `transactions`

## Приклади повідомлень користувача

- `кава 80`
- `таксі 220`
- `отримав зарплату 35000`
- `покажи баланс`
- `видали останню транзакцію`
- `які в мене категорії`
- `покажи аналітику за місяць`
- `статистика витрат по днях за тиждень`

## Команди бота

- `/add_category` — додати власну категорію.
- `/analytics` — покрокове меню аналітики (тип + період).

## Основні модулі

- `app/services/transaction.py`  
  Оркестрація всіх дій, пов'язаних з текстовими запитами користувача.

- `app/services/groq_service.py`  
  Опис tool-calling інструментів для LLM та парсинг результатів у typed-об'єкти.

- `app/services/analytics.py`  
  Агрегація даних і генерація графіків/текстових summary.

- `app/repositories/uow.py`  
  Патерн Unit of Work для транзакційної роботи із сесією.

- `app/middlewares/*.py`  
  DI-шар, який прокидає `session`, `services`, `user` у хендлери.

## Потенційні покращення

- Додати тести (unit + integration) на сервіси й репозиторії.
- Додати міграції (наприклад, Alembic) замість `create_all`.
- Покращити роботу з категоріями для edge-case сценаріїв.
- Додати Docker-конфіг для швидкого деплою.
- Розширити README секціями troubleshooting та roadmap.

## Ліцензія

За потреби додайте файл `LICENSE` і вкажіть тип ліцензії.
