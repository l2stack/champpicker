import base64
import json
import os
import threading
import time
from json import JSONDecoder

import psutil

import requests
import urllib3
from requests import JSONDecodeError
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ChampPicker by l2stack
artDecode = 'ICQkJCQkJFwgICQkXCAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgJCQkJCQkJFwgICQkXCAgICAgICAgICAgJCRcCiQkICBfXyQkXCAkJCB8ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICQkICBfXyQkXCBcX198ICAgICAgICAgICQkIHwKJCQgLyAgXF9ffCQkJCQkJCRcICAgJCQkJCQkXCAgJCQkJCQkXCQkJCRcICAgJCQkJCQkXCAgJCQgfCAgJCQgfCQkXCAgJCQkJCQkJFwgJCQgfCAgJCRcICAkJCQkJCRcICAgJCQkJCQkXAokJCB8ICAgICAgJCQgIF9fJCRcICBcX19fXyQkXCAkJCAgXyQkICBfJCRcICQkICBfXyQkXCAkJCQkJCQkICB8JCQgfCQkICBfX19fX3wkJCB8ICQkICB8JCQgIF9fJCRcICQkICBfXyQkXAokJCB8ICAgICAgJCQgfCAgJCQgfCAkJCQkJCQkIHwkJCAvICQkIC8gJCQgfCQkIC8gICQkIHwkJCAgX19fXy8gJCQgfCQkIC8gICAgICAkJCQkJCQgIC8gJCQkJCQkJCQgfCQkIHwgIFxfX3wKJCQgfCAgJCRcICQkIHwgICQkIHwkJCAgX18kJCB8JCQgfCAkJCB8ICQkIHwkJCB8ICAkJCB8JCQgfCAgICAgICQkIHwkJCB8ICAgICAgJCQgIF8kJDwgICQkICAgX19fX3wkJCB8ClwkJCQkJCQgIHwkJCB8ICAkJCB8XCQkJCQkJCQgfCQkIHwgJCQgfCAkJCB8JCQkJCQkJCAgfCQkIHwgICAgICAkJCB8XCQkJCQkJCRcICQkIHwgXCQkXCBcJCQkJCQkJFwgJCQgfAogXF9fX19fXy8gXF9ffCAgXF9ffCBcX19fX19fX3xcX198IFxfX3wgXF9ffCQkICBfX19fLyBcX198ICAgICAgXF9ffCBcX19fX19fX3xcX198ICBcX198IFxfX19fX19ffFxfX3wKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAkJCB8CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgJCQgfAkJYnk6IGwyc3RhY2sKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBcX198IApUb29sIHThu7EgxJHhu5luZyBjaOG6pXAgbmjhuq1uIHRy4bqtbiB2w6AgbG9jayB0xrDhu5tuZyBMZWFndWUgT2YgTGVnZW5kcyAoTG9jYWwgY2xpZW50KQpIw6N5IG5o4bqtcCB0w7l5IGNo4buNbjogKDEpIFBpY2sgdMaw4bubbmcgKDIpIFBpY2sgdsOgIGxvY2sgdMaw4bubbmc='
inThr = False
leagueClientExe = "LeagueClient.exe"

getChamps = '/lol-champions/v1/owned-champions-minimal'


def get_execute_dir(name):
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == name.lower():
                return proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


def process_json(json_data):
    result_dict = {}
    try:
        for item in json_data:
            result_dict[item['id']] = item['name']

    except Exception as e:
        print(f"Lỗi xảy ra: {e}")
    return result_dict


def make_request(method, url):
    try:
        response = requests.request(method, url, verify=False)
        response.raise_for_status()  # Kiểm tra lỗi trong response
        return response.json()  # Trả về JSON từ response
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def decode(encode):
    decoded_bytes = base64.b64decode(encode)
    decoded_string = decoded_bytes.decode("utf-8")
    return decoded_string


def similar(a, b):
    return sum(a[i] == b[i] for i in range(min(len(a), len(b))))


def find(name, data):
    best_match = None
    best_similarity = 0
    for id, value in data.items():
        similarity = similar(name.lower(), value.lower())
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = {id: value}
    return best_match


def request(url, account, password, http, port, method='GET', body=None):
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    response = requests.request(method, http + '://127.0.0.1:' + port + url, auth=HTTPBasicAuth(account, password),
                                verify=False, data=json.dumps(body), headers=headers)
    if response.ok:
        return response.json()
    else:
        return {}


def pick(id, champion_id, account, password, http, port):
    url = f'/lol-champ-select/v1/session/actions/{id}'
    body = {'championId': champion_id}
    response = request(url, account, password, http, port, 'PATCH', body)
    return not bool(response)


def _lock(id, account, password, http, port, ):
    url = f'/lol-champ-select/v1/session/actions/{id}/complete'
    request(url, account, password, http, port, 'POST')


def get_action_id(account, password, http, port):
    response = request('/lol-champ-select/v1/session', account, password, http, port)

    actions = response.get('actions')
    if not actions:
        return -1
    local_player_cell_id = response.get('localPlayerCellId')
    for action in actions[0]:
        if action.get('actorCellId') == local_player_cell_id:
            return action.get('id')
    return -1


def handler(inp):
    dir = get_execute_dir(leagueClientExe)
    if dir is None:
        print('League Of Legends hiện không hoạt động')
        return

    lock_file = os.path.join(os.path.dirname(dir), 'lockfile')
    if not os.path.exists(lock_file):
        print('Không tìm thấy lock file')
        return

    pick_lock = inp == '2'
    with open(lock_file, 'r') as f:
        content = f.read().split(":")
    req_url = f'{content[4]}://riot:{content[3]}@127.0.0.1:{content[2]}'
    champs = process_json(make_request('GET', req_url + getChamps))
    if champs is None:
        print('Không thể fetch dữ liệu! Hãy chắc rằng liên minh đã hoạt động.')
        return

    while True:
        champ = input('Nhập tên tướng: ')
        fc = find(champ, champs)
        print(f'Chọn: {fc}')
        if input('Bấm y để chọn enter để hủy: ') == 'y':
            break
    threading.Thread(target=league_thread, args=(fc, pick_lock, content[4], content[3], content[2])).start()


def league_thread(champ: dict, lock: bool, http: str, psw: str, port: str):
    champion = None
    champid = None

    global inThr
    if inThr:
        inThr = False
        time.sleep(1)

    for k in champ.keys():
        champion = champ[k]
        champid = k
    inThr = True
    print(f'Luồng đang chạy hãy tìm trận đi nào. Tướng: {champion} Lock: {lock}')

    while True:
        id = get_action_id('riot', psw, http, port)
        if id == -1:
            continue

        try:
            pick(id, champid, 'riot', psw, http, port)
        except JSONDecodeError:
            pass

        if lock:
            try:
                _lock(id, 'riot', psw, http, port)
            except JSONDecodeError:
                pass
        print()
        print('Hoàn tất! Bạn có thể tiếp tục chọn.')
        break


if __name__ == '__main__':
    print(decode(artDecode))

    while True:
        inp = input("> ")
        handler(inp)
