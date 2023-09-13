import asyncio
import base64
import json
import msvcrt
import os
import signal
import threading
import time

import psutil

import requests
import urllib3
from requests import JSONDecodeError
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ChampPicker by l2stack
artDecode = 'IF9fX19fIF8gICAgICAgICAgICAgICAgICAgICAgICAgIF9fX19fXyBfICAgICAgXwovICBfXyBcIHwgICAgICAgICAgICAgICAgICAgICAgICAgfCBfX18gKF8pICAgIHwgfAp8IC8gIFwvIHxfXyAgIF9fIF8gXyBfXyBfX18gIF8gX18gfCB8Xy8gL18gIF9fX3wgfCBfX19fXyBfIF9fCnwgfCAgIHwgJ18gXCAvIF9gIHwgJ18gYCBfIFx8ICdfIFx8ICBfXy98IHwvIF9ffCB8LyAvIF8gXCAnX198CnwgXF9fL1wgfCB8IHwgKF98IHwgfCB8IHwgfCB8IHxfKSB8IHwgICB8IHwgKF9ffCAgIDwgIF9fLyB8CiBcX19fXy9ffCB8X3xcX18sX3xffCB8X3wgfF98IC5fXy9cX3wgICB8X3xcX19ffF98XF9cX19ffF98CiAgICAgICAgICAgICAgICAgICAgICAgICAgICB8IHwKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHxffCAgICAgICBieTogbDJzdGFjawpC4bqlbSBjw6FjIHBow61tIHPhu5EgYsOqbiBkxrDhu5tpIHTGsMahbmcg4bupbmcgY8OhYyB0w61uaCBuxINuZyDEkcaw4bujYyBsaeG7h3Qga8OqOgoJMTogQ2jhu4kgcGljayB0xrDhu5tuZwoJMjogUGljayB2w6AgbG9jayB0xrDhu5tuZwoJMzogTW9kc2tpbiAoxJBhbmcgcGjDoXQgdHJp4buDbikKCTQ6IFThu7EgxJHhu5luZyBjaOG6pXAgbmjhuq1uIHRy4bqtbiDEkeG6pXUKCTU6IMSQw7NuZyDhu6luZyBk4bulbmc='
pick_thread = False
accept_thread = False
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


def is_match_found(account, password, http, port):
    response = request('/lol-matchmaking/v1/ready-check', account, password, http, port)
    return response.get('state', '') == 'InProgress'


def accept_match(account, password, http, port):
    request('/lol-matchmaking/v1/ready-check/accept', account, password, http, port, 'POST')


def handler(inp):
    dir = get_execute_dir(leagueClientExe)
    if dir is None:
        print('League Of Legends hiện không hoạt động')
        return

    lock_file = os.path.join(os.path.dirname(dir), 'lockfile')
    if not os.path.exists(lock_file):
        print('Không tìm thấy lock file')
        return

    pick_lock = inp == b'2'
    with open(lock_file, 'r') as f:
        content = f.read().split(":")

    if inp == b'4' or inp == b'3':
        message = None
        if inp == b'3':
            message = input('Nhập tin nhắn cần gởi: ')
        threading.Thread(target=match_accept_thread, args=(content[4], content[3], content[2], message)).start()
        return

    req_url = f'{content[4]}://riot:{content[3]}@127.0.0.1:{content[2]}'
    champs = process_json(make_request('GET', req_url + getChamps))

    while True:
        champ = input('Nhập tên tướng cần tìm (Vd: na -> Nasus): ')
        fc = find(champ, champs)

        if fc is None:
            print('Không tìm thấy tướng hãy thử lại.')
            return

        print(f'Chọn tướng: {fc}')
        if input('Bấm (y và enter) để chọn bấm enter để hủy: ').lower() == 'y':
            break
    threading.Thread(target=pick_lock_thread, args=(fc, pick_lock, content[4], content[3], content[2])).start()


def match_accept_thread(http: str, psw: str, port: str, message: str):
    global accept_thread
    if accept_thread:
        accept_thread = False
        print('Đã tắt tính năng tự động chấp nhận trận.')
        return
    time.sleep(1)
    accept_thread = True
    print('Đã bật tính năng tự động chấp nhận trận đấu.')

    while accept_thread:
        time.sleep(0.2)
        if is_match_found('riot', psw, http, port):

            try:
                accept_match('riot', psw, http, port)
            except JSONDecodeError:
                pass
            print('Done! Hoàn tất tính năng sẽ được tắt.')
            accept_thread = False
            break


def pick_lock_thread(champ: dict, lock: bool, http: str, psw: str, port: str):
    champion = None
    champid = None

    global pick_thread
    if pick_thread:
        pick_thread = False
        time.sleep(1)

    for k in champ.keys():
        champion = champ[k]
        champid = k
    pick_thread = True
    print(f'Luồng đang chạy hãy tìm trận đi nào. Tướng: {champion} Lock: {lock}')

    while pick_thread:
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


def kill():
    current_pid = os.getpid()
    asyncio.run(os.kill(current_pid, signal.SIGTERM))


if __name__ == '__main__':
    print(decode(artDecode))

    # while True:
    #     inp = input("> ")
    #     time.sleep(1)
    #     handler(inp)
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key in [b'1', b'2', b'4', b'5']:
                if key == b'5':
                    kill()
                handler(key)
