from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.zabbix_api import (
    get_hosts_by_group,
    get_hosts_by_groups,
    get_all_groups,
    zabbix_login,
)
from app.mikrotik_api import get_channel_status

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        auth = zabbix_login()
        raw_hosts = get_hosts_by_groups(["gr3", "Xfit"], auth, name_filter="gr3")
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
