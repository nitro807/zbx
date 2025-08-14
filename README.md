## Zabbix → MikroTik мониторинг и Prometheus экспортёр

FastAPI‑сервис, который:

- собирает ICMP-метрики хостов из Zabbix (loss/RTT/ping),
- определяет активный/резервный WAN‑канал на MikroTik через RouterOS API,
- показывает сводную HTML‑страницу и отдаёт метрики в Prometheus,
- поставляется с docker-compose, Prometheus и Grafana.

### Стек
- **FastAPI** (uvicorn), **Jinja2** (UI)
- **prometheus_client** (экспортёр), **Prometheus**, **Grafana**
- **requests** (Zabbix JSON-RPC API), **librouteros** (RouterOS API)
- **python-dotenv** (конфигурация через `.env`)

### Структура проекта
```
main.py                      # FastAPI-приложение и экспортёр метрик
app/
  zabbix_api.py              # Запросы к Zabbix API
  mikrotik_api.py            # Запросы к MikroTik (RouterOS API)
templates/
  channel_status.html        # Статус каналов
  groups.html                # Список групп Zabbix
static/                      # Статика для UI
requirements.txt
Dockerfile
docker-compose.yml
prometheus.yml               # Скрейп /metrics сервиса
```

### Переменные окружения (.env)
Создайте файл `.env` рядом с `docker-compose.yml`:
```
ZABBIX_URL=https://zabbix.example.com/api_jsonrpc.php
ZABBIX_USER=zabbix_user
ZABBIX_PASSWORD=zabbix_password

MIKROTIK_USER=router_user
MIKROTIK_PASSWORD=router_password
```

Примечания:
- `ZABBIX_URL` должен указывать на JSON-RPC эндпоинт Zabbix (`/api_jsonrpc.php`).
- Подключение к MikroTik выполняется на порт 8728 (API). Убедитесь, что доступ разрешён.

### Быстрый старт (Docker)
Требуется Docker и Docker Compose.

1) Собрать и запустить:
```
docker compose up -d --build
```
2) Открыть:
- UI: `http://localhost:8000/`
- Группы: `http://localhost:8000/groups`
- Метрики: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3030` (логин: admin / пароль: admin)

### Локальный запуск (без Docker)
1) Python 3.11+, создать окружение и установить зависимости:
```
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
2) Экспортировать переменные окружения (или использовать `.env`):
```
export ZABBIX_URL=https://zabbix.example.com/api_jsonrpc.php
export ZABBIX_USER=...
export ZABBIX_PASSWORD=...
export MIKROTIK_USER=...
export MIKROTIK_PASSWORD=...
```
3) Запустить API:
```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Эндпоинты
- `GET /` — HTML‑сводка по хостам (канал, loss 15m, RTT 1m)
- `GET /groups` — HTML‑список групп Zabbix
- `GET /metrics` — Prometheus метрики (кэшируются и обновляются каждые 30 секунд)
- `GET /icmp_stats` — те же данные, что используются для метрик, в JSON

### Метрики Prometheus
- `mikrotik_channel_status{host}` — Gauge: 1 (main), 0 (backup), -1 (unknown)
- `icmp_loss_avg_15m{host}` — Gauge: средний ICMP loss за 15 минут, %
- `icmp_response_time_avg_1m{host}` — Gauge: средний ICMP RTT за 1 минуту, миллисекунды

Обновление метрик выполняется фоновым потоком раз в 30 секунд, результат кешируется и отдаётся из `/metrics`.

### Prometheus и Grafana
- В `prometheus.yml` уже настроен скрейп `api:8000/metrics` для compose-сети.
- При локальном запуске без Docker измените цель на `localhost:8000`.
- В `docker-compose.yml` Grafana опубликована на порт `3030` и ставит плагин `grafana-polystat-panel`.

Пример PromQL:
```
avg by(host) (icmp_response_time_avg_1m)
```
```
avg by(host) (icmp_loss_avg_15m)
```

### Настройка под ваш Zabbix
По умолчанию в `main.py` используются группы `xfit` и `xfit_reserv`:
```python
# main.py → update_metrics()
base_hosts = get_hosts_by_group("xfit", auth)
reserve_hosts = get_hosts_by_group("xfit_reserv", auth)
```
Замените их на ваши названия групп. Специфические исключения для `ALT OF` и `SEL` также заданы в коде и могут быть изменены при необходимости.

### Диагностика
- Проверьте переменные окружения (`.env`/экспорт).
- Убедитесь, что Zabbix API и MikroTik API доступны по сети.
- Логи содержат подробные ответы Zabbix JSON‑RPC (включая коды статуса).
- Для HTTPS к Zabbix используется `verify=False`. При необходимости добавьте проверку сертификата или корпоративное CA.

### Лицензия
Отсутствует. Добавьте информацию о лицензии при необходимости.


