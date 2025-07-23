import os
from librouteros import connect
from dotenv import load_dotenv

load_dotenv()
MIKROTIK_USER = os.getenv("MIKROTIK_USER")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD")


def get_channel_status(host_ip: str) -> str:
    """Return channel status for a MikroTik host.

    Parameters
    ----------
    host_ip : str
        Device IP address.

    Returns
    -------
    str
        "main" for primary channel, "backup" for reserve, or "unknown".
    """
    if not host_ip:
        return "unknown"
    if not MIKROTIK_USER or not MIKROTIK_PASSWORD:
        raise RuntimeError("MikroTik credentials are not configured")
    try:
        api = connect(host=host_ip, username=MIKROTIK_USER, password=MIKROTIK_PASSWORD)
        routes = api(
            "/ip/route/print",
            detail="",
            **{"dst-address": "0.0.0.0/0"}
        )
        for route in routes:
            status = str(route.get("gateway-status", ""))
            if any(tag in status for tag in ("CCR11", "CCR22")):
                api.close()
                return "main"
            if any(tag in status for tag in ("CCR12", "CCR21")):
                api.close()
                return "backup"
        api.close()
    except Exception as exc:
        print(f"[MT] Error for {host_ip}: {exc}")
    return "unknown"
