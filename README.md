# Remote OpenCode Workplace — Telegram Bot

Telegram-бот для отправки задач в OpenCode через текстовые сообщения.

## Архитектура

```
Telegram (текст) → Python Bot → OpenCode API → Выполнение → Ответ в Telegram
```

- **bot/** — Python Telegram bot (python-telegram-bot + aiohttp)
- **opencode** — OpenCode в Docker-контейнере с Java 21 + Gradle 8.7 + Python 3.9
- **docker-compose.yml** — оркестрация обоих контейнеров
- **mount/** — глобальный AGENTS.md и скиллы для OpenCode

## Требования

- Docker Engine 24+
- Docker Compose v2
- Git Bash (на Windows) или bash (на Linux)
- Telegram Bot Token (от [BotFather](https://t.me/botfather))
- Ваш Telegram User ID

## Быстрый старт

1. **Клонировать репозиторий:**
   ```bash
   git clone <repo-url>
   cd remote-opencode-workplace
   ```

2. **Настроить конфиг:**
   ```bash
   mkdir -p ~/.rem-opencode
   ```

   Создайте `~/.rem-opencode/config.json`:
   ```json
   {
     "telegram_token": "738456...:AAH...",
     "allowed_user_id": 123456789
   }
   ```

3. **Запустить:**
   ```bash
   ./run.sh
   ```

4. **Написать боту в Telegram** — он передаст задачу в OpenCode и вернёт ответ.

## Команды

| Команда | Описание |
|---|---|
| `./run.sh` | Собрать и запустить все контейнеры |
| `./stop.sh` | Остановить все контейнеры |
| `docker compose logs -f bot` | Логи бота |
| `docker compose logs -f opencode` | Логи OpenCode |

## Разработка

### Зависимости Python

```bash
pip install -r requirements.txt
```

### Тесты

```bash
pytest bot/tests/ -v
```

### Структура проекта

```
.
├── AGENTS.md              # Инструкции для AI-сессий
├── project-goal.md        # Цель проекта
├── docker-compose.yml     # Оркестрация
├── Dockerfile             # OpenCode + Java 21 + Gradle 8.7 + Python 3.9
├── Dockerfile.bot         # Telegram bot
├── run.sh                 # Запуск стека
├── stop.sh                # Остановка стека
├── .gitignore
├── requirements.txt
├── bot/
│   ├── __init__.py
│   ├── main.py            # Entrypoint
│   ├── config.py          # Загрузка конфига
│   ├── handlers.py        # Обработчики Telegram
│   ├── opencode_client.py # HTTP-клиент для OpenCode API
│   └── tests/             # Тесты pytest
├── mount/
│   ├── AGENTS.md          # Глобальный агент для OpenCode
│   └── SKILLS/            # Наборы скиллов
└── docs/                  # Документация
```

## Безопасность

- Токен Telegram и User ID хранятся в `~/.rem-opencode/config.json`
- Этот файл НЕ КОММИТИТСЯ в репозиторий (в `.gitignore`)
- Бот отвечает только одному пользователю (фильтр по `allowed_user_id`)
