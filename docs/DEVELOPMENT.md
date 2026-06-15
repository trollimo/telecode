# Development

## Prerequisites

- Python 3.11+
- Docker Engine 24+ & Docker Compose v2
- Git Bash (Windows) or bash (Linux/macOS)

## Local Development

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Run tests

```bash
# All tests
pytest bot/tests/ -v

# Specific file
pytest bot/tests/test_opencode_client.py -v

# With coverage
pytest bot/tests/ --cov=bot --cov-report=term-missing
```

### Manual ad-hoc tests

```bash
# Run from project root
python tests/manual/test_simple.py
python tests/manual/debug_client.py
```

### Code style

- Standard library preferred over external dependencies
- Type hints required for all public methods
- Async/await for all I/O-bound operations
- TDD: add tests before or alongside code changes

## Project conventions

- **AGENTS.md** at root level contains instructions for AI coding sessions
- **docker/opencode/AGENTS.md** is the global agent config mounted into the OpenCode container
- Update `docs/` when architecture or method contracts change
- Keep `README.md` in sync with setup procedures

## Docker development

### Quick rebuild of a single service

```bash
# Rebuild bot image and restart
docker compose -f docker/compose.yml --project-directory . build bot
docker compose -f docker/compose.yml --project-directory . up -d bot
```

### Follow logs

```bash
docker compose -f docker/compose.yml --project-directory . logs -f bot
docker compose -f docker/compose.yml --project-directory . logs -f opencode
```

### Shell access

```bash
docker compose -f docker/compose.yml --project-directory . exec bot /bin/bash
docker compose -f docker/compose.yml --project-directory . exec opencode /bin/bash
```

## Testing the bot locally

1. Start the stack (see [DEPLOYMENT.md](DEPLOYMENT.md))
2. Send a message to your bot in Telegram
3. Check bot logs: `docker compose -f docker/compose.yml --project-directory . logs -f bot`
4. Check OpenCode API directly: `curl http://localhost:4096/global/health`
