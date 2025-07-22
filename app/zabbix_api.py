from dotenv import load_dotenv
load_dotenv()

import os
import requests
import json


ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

def zabbix_login():
    url = os.getenv("ZABBIX_URL")
    user = os.getenv("ZABBIX_USER")
    password = os.getenv("ZABBIX_PASSWORD")
    print(f"[ZBX] Попытка логина: user={user}, url={url}")
    data = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": user,
            "password": password
        },
        "id": 1
    }
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=data, verify=False)
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
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=data, verify=False)
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





def get_hosts_by_group(group_name, auth):
    group_id = get_group_id(group_name, auth)
    print(f"[ZBX] GROUP ID for {group_name}: {group_id}")

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": ["ip"],
        "groupids": group_id,
        "filter": {
            "status": "0"  # Только активные хосты
        }
    }

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


def get_hosts_by_groups(group_names, auth):
    print(f"[ZBX] AND-режим: ищем хосты, которые входят во все группы: {group_names}")
    host_sets = []
    host_details = {}
    for group in group_names:
        hosts = get_hosts_by_group(group, auth)
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
