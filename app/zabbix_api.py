import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
ZABBIX_URL = os.getenv("ZABBIX_URL")


def zabbix_login():
    url = os.getenv("ZABBIX_URL")
    username = os.getenv("ZABBIX_USER")
    password = os.getenv("ZABBIX_PASSWORD")
    print(f"[ZBX] Попытка логина: username={username}, url={url}")
    data = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": username,
            "password": password
        },
        "id": 1
    }
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data,
            verify=False,
        )
        print(f"[ZBX] Ответ на логин: {response.status_code}")
        print(f"[ZBX] Тело ответа: {response.text}")
        resp_json = response.json()
        if "result" in resp_json:
            print(f"[ZBX] Успешный логин, токен: {resp_json['result']}")
            return resp_json["result"]
        else:
            raise Exception(f"Ошибка логина: {resp_json}")
    except Exception as e:
        print(f"[ZBX] Ошибка при логине: {e}")
        raise


def zabbix_request(method, params, auth):
    url = os.getenv("ZABBIX_URL")
    data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": auth,
        "id": 1
    }
    print(f"[ZBX] Запрос: {json.dumps(data, ensure_ascii=False)}")
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data,
            verify=False,
        )
        print(f"[ZBX] Ответ: {response.status_code}")
        print(f"[ZBX] Тело ответа: {response.text}")
        resp_json = response.json()
        if "error" in resp_json:
            print(f"[ZBX] Ошибка в ответе: {resp_json['error']}")
            raise Exception(f"Zabbix API error: {resp_json['error']}")
        result = resp_json.get("result", None)
        if result is None:
            raise Exception(f"Zabbix вернул пустой result для метода {method}")
        return result
    except Exception as e:
        print(f"[ZBX] Ошибка при запросе {method}: {e}")
        raise


def get_hosts_by_group(group_name, auth, name_filter=None):
    """Return active hosts from a group.

    If ``name_filter`` is provided, only hosts whose names contain the given
    substring are returned.
    """
    group_id = get_group_id(group_name, auth)
    print(f"[ZBX] GROUP ID for {group_name}: {group_id}")

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": ["ip","port"],
        "groupids": group_id,
        "filter": {"status": "0"},  # Только активные хосты
    }
    if name_filter:
        # Zabbix performs a substring search on the provided value
        params["search"] = {"name": name_filter}

    result = zabbix_request("host.get", params, auth)
    print(f"[ZBX] HOSTS for group {group_name}: {result}")
    return result


def get_group_id(group_name, auth):
    print(f"[ZBX] Ищу группу: {group_name}")
    groups = zabbix_request("hostgroup.get", {
        "output": ["groupid", "name"],
        "filter": {"name": [group_name]}
    }, auth)

    print(f"[ZBX] GROUPS: {groups}")

    if not groups:
        raise Exception(f"Zabbix group '{group_name}' not found")
    return groups[0]["groupid"]


def get_group_ids(group_names, auth):
    print(f"[ZBX] Ищу группы: {group_names}")
    groups = zabbix_request("hostgroup.get", {
        "output": ["groupid", "name"],
        "filter": {"name": group_names}
    }, auth)
    print(f"[ZBX] GROUPS for {group_names}: {groups}")
    if not groups:
        raise Exception(f"Zabbix groups '{group_names}' not found")
    return [g["groupid"] for g in groups]


def get_hosts_by_groups(group_names, auth, name_filter=None):
    """Return hosts that belong to all groups and match the name filter."""
    print(
        "[ZBX] AND-режим: ищем хосты, которые входят во все группы: "
        f"{group_names}"
    )
    host_sets = []
    host_details = {}
    for group in group_names:
        hosts = get_hosts_by_group(group, auth, name_filter)
        ids = set()
        for h in hosts:
            ids.add(h["hostid"])
            host_details[h["hostid"]] = h
        print(f"[ZBX] HOSTIDS для группы {group}: {ids}")
        host_sets.append(ids)
    if not host_sets:
        print("[ZBX] Нет групп для поиска")
        return []
    common_ids = set.intersection(*host_sets)
    print(f"[ZBX] Общие HOSTIDS для всех групп: {common_ids}")
    result = [host_details[hid] for hid in common_ids]
    print(f"[ZBX] HOSTS для всех групп {group_names}: {result}")
    return result


def get_all_groups(auth):
    groups = zabbix_request("hostgroup.get", {
        "output": ["groupid", "name"]
    }, auth)
    print(f"[ZBX] ALL GROUPS: {groups}")
    return groups


def get_icmp_metrics(host_id, auth):
    """Return ICMP statistics for a host."""
    params = {
        "output": ["name", "lastvalue"],
        "hostids": host_id,
        "filter": {
            "name": [
                "ICMP loss avg 15 m",
                "ICMP response time avg 1m",
            ]
        },
    }
    items = zabbix_request("item.get", params, auth)
    metrics = {}
    for item in items:
        name = item.get("name")
        value = item.get("lastvalue")
        if name == "ICMP loss avg 15 m":
            metrics["loss_15m"] = round(float(value), 2)
        if name == "ICMP response time avg 1m":
            metrics["resp_1m"] = round(float(value)*1000,2)
    return metrics


def get_host_ip(host_name: str, auth: str) -> str:
    """Return the primary interface IP for a host by name."""

    params = {
        "output": ["hostid", "name"],
        "selectInterfaces": ["ip"],
        "filter": {"name": [host_name]},
        "limit": 1,
    }
    hosts = zabbix_request("host.get", params, auth)
    if not hosts:
        print(f"[ZBX] Host '{host_name}' not found")
        return ""
    return hosts[0].get("interfaces", [{}])[0].get("ip", "")


def get_host_id(host_name: str, auth: str) -> str:
    """Return Zabbix host ID for a given host name."""

    params = {
        "output": ["hostid"],
        "filter": {"name": [host_name]},
        "limit": 1,
    }
    hosts = zabbix_request("host.get", params, auth)
    if not hosts:
        print(f"[ZBX] Host '{host_name}' not found")
        return ""
    return hosts[0].get("hostid", "")
