from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.zabbix_api import (
    get_hosts_by_group,
    get_all_groups,
    zabbix_login,
    get_host_ip,
)
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from app.mikrotik_api import (
    get_channel_status,
    channel_status_value,
    channel_status_value_special,
)
import threading
import time

cached_data = b""


from app.zabbix_api import get_icmp_metrics, get_host_id


registry = CollectorRegistry()
channel_gauge = Gauge(
    "mikrotik_channel_status",
    "1 for main, 0 for backup, -1 for unknown",
    ["host"],
    registry=registry,
)

loss_gauge = Gauge(
    "icmp_loss_avg_15m",
    "ICMP packet loss average over 15 minutes",
    ["host"],
    registry=registry,
)

resp_gauge = Gauge(
    "icmp_response_time_avg_1m",
    "ICMP response time average over 1 minute",
    ["host"],
    registry=registry,
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def metrics_updater():
    global cached_data
    while True:
        try:
            update_metrics()
            cached_data = generate_latest(registry)
        except Exception as e:
            print(f"[METRICS] Ошибка при обновлении метрик: {e}")
        time.sleep(30)  # обновлять раз в 30 секунд


def update_metrics():
    """Collect statistics for xfit and xfit_reserve hosts."""
    auth = zabbix_login()
    base_hosts = get_hosts_by_group("xfit", auth)
    reserve_hosts = get_hosts_by_group("xfit_reserv", auth)
    results = []

    for host in base_hosts:
        name = host.get("name")
        metrics = get_icmp_metrics(host["hostid"], auth)

        mikrotik_name = f"{name}.Gr3"
        if mikrotik_name in ("ALT OF.Gr3", "SEL.Gr3"):
            special_name = "ALT OF" if mikrotik_name == "ALT OF.Gr3" else "SEL"
            host_id = get_host_id(special_name, auth)
            status = "main" if metrics.get("ping", 0) == "1" else "unknown"
            print("--------------------------------")
            print(f"[MAIN] {name} {status} type {type(metrics.get('ping', 0))}")
            gauge_value = channel_status_value_special(status)
            ip = ""
        else:
            ip = get_host_ip(mikrotik_name, auth)
            status = get_channel_status(ip, 8728)
            gauge_value = channel_status_value(status)

        channel_gauge.labels(host=name).set(gauge_value)
        loss_gauge.labels(host=name).set(metrics.get("loss_15m", -1))
        resp_gauge.labels(host=name).set(metrics.get("resp_1m", -1))

        results.append(
            {
                "name": name,
                "ip": ip,
                "channel": status,
                **metrics,
            }
        )

    for host in reserve_hosts:
        name = host.get("name")
        ip = get_host_ip(name, auth)
        metrics = get_icmp_metrics(host["hostid"], auth)
        status = "main" if metrics.get("ping", 0) == "1" else "unknown"
        gauge_value = channel_status_value_special(status)
        channel_gauge.labels(host=name).set(gauge_value)
        loss_gauge.labels(host=name).set(metrics.get("loss_15m", -1))
        resp_gauge.labels(host=name).set(metrics.get("resp_1m", -1))

        results.append(
            {
                "name": name,
                "ip": ip,
                "channel": gauge_value,
                **metrics,
            }
        )

    return results


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        auth = zabbix_login()
        base_hosts = get_hosts_by_group("xfit", auth)
        hosts = []
        for h in base_hosts:
            name = h.get("name")
            metrics = get_icmp_metrics(h["hostid"], auth)

            mk_name = f"{name}.Gr3"
            ip = get_host_ip(mk_name, auth)
            channel = get_channel_status(ip, 8728)

            if mk_name in ("ALT OF.Gr3", "SEL.Gr3"):
                special_name = "ALT OF" if mk_name == "ALT OF.Gr3" else "SEL"
                host_id = get_host_id(special_name, auth)
                if host_id:
                    metrics = get_icmp_metrics(host_id, auth)
                channel = "main" if metrics.get("loss_15m", 100) < 100 else "unknown"
                value = channel_status_value_special(channel)
            else:
                value = channel_status_value(channel)
            hosts.append({
                "name": name,
                "ip": ip,
                "channel": value,
                "loss": str(metrics.get("loss_15m")) + "%  ",
                "resp": metrics.get("resp_1m"),
            })
    except Exception as e:
        print(f"[MAIN] Ошибка в index: {e}")
        return templates.TemplateResponse(
            "channel_status.html",
            {"request": request, "hosts": [], "error": str(e)},
            status_code=500
        )
    return templates.TemplateResponse(
        "channel_status.html",
        {"request": request, "hosts": hosts}
    )


@app.get("/groups", response_class=HTMLResponse)
async def groups(request: Request):
    try:
        auth = zabbix_login()
        groups = get_all_groups(auth)
    except Exception as e:
        print(f"[MAIN] Ошибка в groups: {e}")
        return templates.TemplateResponse(
            "groups.html",
            {"request": request, "groups": [], "error": str(e)},
            status_code=500
        )
    return templates.TemplateResponse(
        "groups.html",
        {"request": request, "groups": groups}
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(cached_data, media_type=CONTENT_TYPE_LATEST)



@app.get("/icmp_stats")
async def icmp_stats() -> JSONResponse:
    data = update_metrics()
    return JSONResponse(content=data)


threading.Thread(target=metrics_updater, daemon=True).start()