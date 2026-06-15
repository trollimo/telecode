# Remote OpenCode Workplace — Telegram Bot

[![CI](https://github.com/YOUR_USER/remote-opencode-workplace/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USER/remote-opencode-workplace/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker)](https://docs.docker.com/compose/)

Telegram-бот для отправки задач в [OpenCode](https://opencode.ai) через текстовые сообщения. Поддерживает multi-turn диалоги: бот запоминает контекст разговора.

```
Telegram (текст) → Python Bot → OpenCode API → Выполнение → Ответ в Telegram
```

---

## 📋 Требования

- **Docker Engine** 24+ и **Docker Compose** v2
- **Git Bash** (Windows) или **bash** (Linux/macOS)
- Telegram Bot Token (от [@BotFather](https://t.me/botfather))
- Ваш Telegram User ID

---

## 🚀 Быстрый старт

### 1. Получить токен Telegram бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/botfather)
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте полученный токен (формат: `738456...:AAH...`)

### 2. Узнать свой Telegram User ID

Напишите [@userinfobot](https://t.me/userinfobot) — он ответит вашим числовым ID.

### 3. Создать файл конфигурации

Создайте `~/.rem-opencode/config.json`:

```bash
mkdir -p ~/.rem-opencode
```

```json
{
  "telegram_token": "738456...:AAH...",
  "allowed_user_id": 123456789,
  "opencode_url": "http://opencode:4096"
}
```

| Поле | Описание |
|---|---|
| `telegram_token` | Токен от BotFather |
| `allowed_user_id` | Ваш числовой Telegram ID |
| `opencode_url` | Внутренний Docker hostname (не менять) |

> ⚠️ **Файл содержит секреты.** Он добавлен в `.gitignore` и **никогда не должен попасть в git**.

### 4. Запустить стек

```bash
# Первый запуск (сборка образов)
./scripts/run.sh

# Или без пересборки (если образы уже есть)
docker compose -f docker/compose.yml --project-directory . up -d
```

### 5. Написать боту

Найдите своего бота в Telegram и отправьте любое текстовое сообщение. Бот передаст задачу в OpenCode и вернёт ответ.

---

## 📖 Команды

| Команда | Описание |
|---|---|
| `./scripts/run.sh` | Первый запуск — создаёт конфиг, собирает образы, стартует |
| `./scripts/stop.sh` | Остановить все контейнеры |
| `./scripts/restart.sh` | Перезапустить все сервисы |
| `./scripts/restart.sh bot` | Перезапустить только Telegram бота |
| `docker compose -f docker/compose.yml --project-directory . logs -f bot` | Логи бота |
| `docker compose -f docker/compose.yml --project-directory . logs -f opencode` | Логи OpenCode |

---

## 🛠 Как избежать регулярной пересборки

Образы собираются **только** при первом запуске или явном указании `--build`.

- ✅ `./scripts/restart.sh` — **без пересборки**
- ✅ `docker compose restart` — **без пересборки**
- ✅ `docker compose up -d` — **без пересборки**
- ❌ `docker compose up -d --build` — принудительная пересборка
- ❌ `docker compose build` — ручная пересборка

Код бота подключен как Docker volume (`./bot:/app/bot`), поэтому изменения в Python-файлах применяются после перезапуска контейнера без пересборки образа.

```bash
# Пример: изменили код → перезапустили бота
./scripts/restart.sh bot
```

---

## 🧪 Разработка

### Зависимости

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
├── .github/workflows/        # GitHub Actions CI
├── bot/                      # Telegram bot
│   ├── main.py               # Entrypoint
│   ├── config.py             # Загрузка конфига
│   ├── handlers.py           # Обработчики Telegram
│   ├── opencode_client.py    # HTTP-клиент для OpenCode API
│   └── tests/                # Тесты pytest
├── docker/                   # Docker-инфраструктура
│   ├── compose.yml           # Docker Compose
│   ├── opencode/             # OpenCode контейнер
│   │   ├── Dockerfile
│   │   ├── opencode.json
│   │   ├── AGENTS.md         # Глобальный агент для OpenCode
│   │   └── SKILLS/           # Скиллы для OpenCode
│   └── bot/
│       └── Dockerfile.bot
├── docs/                     # Документация
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── DEPLOYMENT.md
│   └── API.md
├── scripts/                  # Скрипты управления
│   ├── run.sh
│   ├── stop.sh
│   ├── restart.sh
│   └── restart.ps1
├── tests/manual/             # Ручные/отладочные тесты
├── AGENTS.md                 # Инструкции для AI-сессий
├── project-goal.md           # Цель проекта
└── requirements.txt
```

---

## 🔒 Безопасность

- Токен Telegram и User ID хранятся в `~/.rem-opencode/config.json`
- Файл конфигурации **не коммитится** (в `.gitignore`)
- Бот отвечает только одному пользователю (фильтр по `allowed_user_id`)
- API-ключи LLM передаются через переменные окружения (`.env`)

---

## 📚 Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Разработка](docs/DEVELOPMENT.md)
- [Деплой](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)
