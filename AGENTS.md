# Repository Guidelines

This project is a small FastAPI service that displays host and group information
from a Zabbix instance. The API logic is in `app/zabbix_api.py` and the web
pages are rendered with Jinja2 templates under `templates/`.

## Development
- Use **Python 3** with [PEP 8](https://peps.python.org/pep-0008/) style.
- Keep imports at the top of files and remove unused imports.
- Write functions with clear names and add comments or docstrings when needed.
- All environment values (e.g. `ZABBIX_URL`, `ZABBIX_USER`, `ZABBIX_PASSWORD`)
  are loaded with `python-dotenv`. Do not hard‑code secrets.
- Functions in `app/zabbix_api.py` accept an optional `name_filter` argument to
  filter hosts by **substring** in addition to group membership.
- Use `uvicorn main:app --reload` to run the application during development.
- There are no automated tests. Do **not** attempt to run tests.

## Commit Messages
Describe the intent of the change briefly, e.g. "Add error handling to
zabbix_request".

## Pull Request Notes
Include a short summary of the change and mention any manual steps required.

## Logging
Use print statements or a simple logging setup for debugging. Log files may be stored as `log.txt` when running the server with `nohup`.
