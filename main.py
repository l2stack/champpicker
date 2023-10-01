import asyncio
import base64
import json
import os
import signal
import threading
import time

import psutil

import requests
import urllib3
import tkinter as tk
import win32api
from requests import JSONDecodeError
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ChampPicker by l2stack
# create window
root = tk.Tk()

# set title
root.title("ChampPicker")

# set background color
root.configure(bg="#1e1e1e")

# disable tool bar
root.overrideredirect(True)

# get screen size
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)

# calc pos to spawn window (center screen)
window_width = 612
window_height = 334
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2

# set window size and window pos
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# set default offset for move event
offset_x, offset_y = 0, 0


def get_pos(event):
    global offset_x, offset_y
    offset_x = event.x
    offset_y = event.y


def move_window(event):
    root.geometry(f"{window_width}x{window_height}+{event.x_root - offset_x}+{event.y_root - offset_y}")


def create_text_label(pos_x: int, pos_y: int, size: int, message: str):
    label = tk.Label(root, text=message, font=("monospace", size), fg="white", bg="#1e1e1e")
    label.place(x=pos_x, y=pos_y)  # Margin top 5% và margin left 5%
    label.config(anchor="w")  # anchor = lèft


def create_button_label(text: str, font_size: int, btn_width: int, btn_height: int, pos_x: int, pos_y: int, color: str, command):
    btn = tk.Button(root, text=text, command=command, font=("monospace", font_size), fg='white', bg=color,
                            width=btn_width, height=btn_height,
                            bd=5)
    btn.place(x=pos_x, y=pos_y)
    btn.config(cursor="hand2")


# bind event
root.bind("<Button-1>", get_pos)
root.bind("<B1-Motion>", move_window)

# app name label
create_text_label(30, 30, 12, "ChampPicker v1.0.5")
create_text_label(30, 60, 8, "author: l2stack")
create_text_label(30, 90, 12, "Các tính năng chính (Ấn các nút tương ứng):")
create_button_label("Chọn tướng", 12, 9, 0, 30, 120, 'green', None)


# #
# input_entry = tk.Entry(root, font=("monospace", 24), fg="#3cb371", justify="center", bd=0)
# input_entry.place(x=30, y=80)  # Margin top 5% và margin left 5%
# input_entry.config(width=21, insertbackground="white")  # Độ rộng, màu cursor và căn giữa văn bản

# # Tạo button


artDecode = 'ICAgX19fIF8gICAgICAgICAgICAgICAgICAgICAgICAgICAgIF9fXyBfICAgICAgXyAgICAgICAgICAgICAKICAvIF9fXCB8X18gICBfXyBfIF8gX18gX19fICBfIF9fICAgLyBfIChfKSBfX198IHwgX19fX18gXyBfXyAKIC8gLyAgfCAnXyBcIC8gX2AgfCAnXyBgIF8gXHwgJ18gXCAvIC9fKS8gfC8gX198IHwvIC8gXyBcICdfX3wKLyAvX19ffCB8IHwgfCAoX3wgfCB8IHwgfCB8IHwgfF8pIC8gX19fL3wgfCAoX198ICAgPCAgX18vIHwgICAKXF9fX18vfF98IHxffFxfXyxffF98IHxffCB8X3wgLl9fL1wvICAgIHxffFxfX198X3xcX1xfX198X3wgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHxffCAgICAgICBieTogbDJzc3RhY2sKTmjhuq1wIGPDoWMgcGjDrW0gdMawxqFuZyDhu6luZyDEkeG7gyBz4butIGThu6VuZyB0w61uaCBuxINuZwoxOiBDaOG7iSBwaWNrIHTGsOG7m25nCjI6IFBpY2sgdsOgIGxvY2sgdMaw4bubbmcKMzogQ2hhdCB24buLIHRyw60KNDogVOG7sSDEkeG7mW5nIGNo4bqlcCBuaOG6rW4gdHLhuq1uIMSR4bqldQo1OiDEkMOzbmcg4bupbmcgZOG7pW5n'
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


def chat(message, account, password, http, port):
    url = f'/lol-game-client-chat/v1/party-messages'
    body = {'message': message}
    request(url, account, password, http, port, 'POST', body)


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
    working_directory = get_execute_dir(leagueClientExe)
    if working_directory is None:
        print('League Of Legends hiện không hoạt động')
        return

    lock_file = os.path.join(os.path.dirname(working_directory), 'lockfile')
    if not os.path.exists(lock_file):
        print('Không tìm thấy lock file')
        return

    pick_lock = inp == '2'
    with open(lock_file, 'r') as f:
        content = f.read().split(":")

    if inp == '4' or inp == '3':
        message = None
        if inp == '3':
            message = input('Nhập tin nhắn cần gởi: ')
        threading.Thread(target=match_accept_thread, args=(content[4], content[3], content[2], message)).start()
        return

    req_url = f'{content[4]}://riot:{content[3]}@127.0.0.1:{content[2]}'
    champs = process_json(make_request('GET', req_url + getChamps))
    if champs is None:
        print('Error! Hãy thử lại (có vẻ client vẫn chưa khởi động xong)')
        return

    while True:
        champ = input('Nhập tên tướng cần tìm (Vd: na -> Nasus): ')
        fc = find(champ, champs)

        if fc is None:
            print('Không tìm thấy tướng hãy thử lại.')
            return

        print(f'Chọn tướng: {fc}')
        if input('Nhập y để chọn enter để hủy: ').lower() == 'y':
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
    print('Tự động chấp nhận trận đã bật.')

    while accept_thread:
        time.sleep(0.2)
        if is_match_found('riot', psw, http, port):

            try:
                accept_match('riot', psw, http, port)
            except JSONDecodeError:
                pass
            print('Hoàn tất! Tính năng sẽ được tắt.')
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
    print(f'Chọn tướng: {champion} Khóa tướng: {lock}')

    while pick_thread:
        action_id = get_action_id('riot', psw, http, port)
        if action_id == -1:
            continue

        try:
            pick(action_id, champid, 'riot', psw, http, port)
        except JSONDecodeError:
            pass

        if lock:
            try:
                _lock(action_id, 'riot', psw, http, port)
            except JSONDecodeError:
                pass
        print('Hoàn tất! Bạn có thể tiếp tục chọn.')
        pick_thread = False
        break


def kill():
    current_pid = os.getpid()
    asyncio.run(os.kill(current_pid, signal.SIGTERM))  # type: ignore


# Bắt sự kiện khi người dùng ấn các nút 1, 2, 3, 4, 5
def key_pressed(event):
    if event.char in ['1', '2', '3', '4', '5']:
        if event.char == '5':
            kill()
        handler(event.char)


root.bind("<Key>", key_pressed)

# Chạy ứng dụng
root.mainloop()
