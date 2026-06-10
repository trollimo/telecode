# AGENTS.MD — REMOTE OPENCODE WORKPLACE

## COMMUNICATION

- ПИШИ ВСЕ ОТВЕТЫ КАПСОМ (UPPERCASE). ЭТО ГЛАВНОЕ ПРАВИЛО.
- БУДЬ КРАТОК В ОТВЕТАХ.
- ПОЛЬЗОВАТЕЛЬ ПОНИМАЕТ РУССКИЙ ЯЗЫК.
- ВОПРОСЫ ПОЛЬЗОВАТЕЛЮ ЗАДАВАЙ В КЛИКАБЕЛЬНОМ ФОРМАТЕ (question tool С ОПЦИЯМИ).

## PROJECT GOAL

- ОСНОВНАЯ ЗАДАЧА: `./project-goal.md` — TELEGRAM-БОТ ДЛЯ OPENCODE С SPEECH-TO-TEXT.
- СХЕМА: TELEGRAM (ТЕКСТ/ГОЛОС) → PYTHON-БОТ (SPEECH-TO-ТЕКСТ) → OPENCODE (ВЫПОЛНЯЕТ) → ОТВЕТ В TELEGRAM.
- ВСЁ В DOCKER COMPOSE.

## INFRASTRUCTURE (GREENFIELD)

- **НЕТ GIT-РЕПОЗИТОРИЯ** — ПЕРВЫМ ДЕЛОМ `git init`.
- **НЕТ `.gitignore`** — СОЗДАТЬ С: `.idea/`, `.env`, `config.json`, `__pycache__/`, `*.pyc`.
- **НЕТ КОДА** — ВСЁ ПРЕДСТОИТ НАПИСАТЬ.
- **КОНТЕЙНЕР OPENCODE**: JAVA 21 + GRADLE 8.7 + PYTHON 3.9 (ДОБОРКА ОФИЦИАЛЬНОГО ОБРАЗА).
- **GRADLE CACHE** — ВО ВНЕШНИЙ VOLUME (ЧТОБЫ НЕ ПЕРЕСОБИРАТЬ).
- **MOUNT/**: `mount/AGENTS.md` (ГЛОБАЛЬНЫЙ АГЕНТ ДЛЯ OPENCODE В КОНТЕЙНЕРЕ) + `mount/SKILLS/` (СКИЛЛЫ).
- **SCRIPTS**: `run.sh` + `stop.sh` — РАБОТАЮТ НА LINUX И WINDOWS (GIT BASH).
- **БЕЗОПАСНОСТЬ**: КРЕДЫ В `%USERHOME%/.rem-opencode/config.json`. НЕ КОММИТИТЬ `.env`.
- **ТОКЕН TELEGRAMA**: ЛЕЖИТ В `%USERHOME%/.rem-opencode/config.json`.

## WORKFLOW

- TDD: СНАЧАЛА ТЕСТЫ, ПОТОМ КОД.
- ПОСЛЕ ДОРАБОТОК КОДА — ЗАПУСТИ ТЕСТЫ.
- ДОКУМЕНТАЦИЯ В MARKDOWN + MERMAID.
- ПРИ ИЗМЕНЕНИИ АРХИТЕКТУРЫ — АКТУАЛИЗИРУЙ `./docs/`.
- ПРИ ИЗМЕНЕНИИ ЛОГИКИ МЕТОДОВ — АКТУАЛИЗИРУЙ ДОКУМЕНТАЦИЮ В `./docs/`.
- ВЕДИ README: ЧТО ЗА СЕРВИС, КАК ЗАПУСТИТЬ, КАК СОБРАТЬ, КАК ТЕСТИРОВАТЬ.

## CODE STYLE

- PREFER STANDARD LIBRARY SOLUTIONS OVER EXTERNAL DEPENDENCIES.
- WRITE CLEAN, READABLE CODE WITH CONSISTENT FORMATTING.

## GIT STYLE

- `.idea/` В `.gitignore`.
- НЕ КОММИТИТЬ КРЕДЫ, ТОКЕНЫ, `.env`.
- НЕ ПУШИТЬ БЕЗ ЯВНОГО ЗАПРОСА.

## TESTING

- RUN EXISTING TESTS BEFORE AND AFTER MAKING CHANGES.
- ADD TESTS FOR NEW FUNCTIONALITY.
