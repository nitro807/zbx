from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.zabbix_api import (
    get_hosts_by_group,
    get_hosts_by_groups,
    get_all_groups,
    zabbix_login,
)
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from app.mikrotik_api import get_channel_status, channel_status_value
from app.zabbix_api import get_icmp_metrics


registry = CollectorRegistry()
channel_gauge = Gauge(
    "mikrotik_channel_status",
    "1 for main, 0 for backup, -1 for unknown",
    ["host"],
    registry=registry,
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def update_metrics():
    """Collect MikroTik and Zabbix statistics."""
    auth = zabbix_login()
    raw_hosts = get_hosts_by_group("Xfit", auth)
    icmp_results = []
    for host in raw_hosts:
        ip = host.get("interfaces", [{}])[0].get("ip")
        port = 8728
        name = host.get("name")

        status = get_channel_status(ip, port)
        channel_gauge.labels(host=f"{name}.Gr3").set(channel_status_value(status))

        metrics = get_icmp_metrics(host["hostid"], auth)
        icmp_results.append({
            "host": name,
            **metrics,
        })
    return icmp_results


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        auth = zabbix_login()
        raw_hosts = get_hosts_by_groups(["Gr3", "Xfit"], auth, name_filter="gr3")
        hosts = []
        for h in raw_hosts:
            ip = h.get("interfaces", [{}])[0].get("ip")
            port = 8728
            # port = h.get("interfaces", [{}])[0].get("port")
            channel = get_channel_status(ip, port)
            hosts.append({
                "name": h.get("name"),
                "ip": ip,
                "channel": channel,
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
    update_metrics()
    data = generate_latest(registry)
    return Response(data, media_type=CONTENT_TYPE_LATEST)


@app.get("/icmp_stats")
async def icmp_stats() -> JSONResponse:
    data = update_metrics()
    return JSONResponse(content=data)
