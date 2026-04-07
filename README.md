# MAX Chat Frontend

Внутренняя web-панель для команды.

Что внутри:

- серверный frontend на `FastAPI + Jinja2`
- логин по cookie session
- страницы для пользователей, диалогов, сообщений, LLM-вызовов и ошибок
- чтение данных из backend internal API
- проксированный CSV-экспорт без раскрытия internal API key

## Проверки в CI

```bash
pip install ".[dev]"
ruff check src
python -m compileall src
```

## Документация

Общая документация и deploy-файлы ведутся в backend-репозитории как в основной точке входа проекта:

- `max_chat_backend/README.md`
- `max_chat_backend/docs/TZ.md`
- `max_chat_backend/docs/ARCHITECTURE.md`
- `max_chat_backend/docs/CONFIGURATION.md`
- `max_chat_backend/docs/DEPLOY.md`

Этот репозиторий содержит только frontend-код админки.
