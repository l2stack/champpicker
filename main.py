import asyncio
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

# Tắt cảnh báo không an toàn về yêu cầu không an toàn
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ChampPicker by l2stack
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
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def similar(a, b):
    return sum(a[i] == b[i] for i in range(min(len(a), len(b))))


def request(url, account, password, http, port, method='GET', body=None):
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    response = requests.request(method, http + '://127.0.0.1:' + port + url, auth=HTTPBasicAuth(account, password),
                                verify=False, data=json.dumps(body), headers=headers)
    if response.ok:
        return response.json()
    else:
        return {}


def find(name, data):
    best_match = None
    best_similarity = 0
    for id, value in data.items():
        similarity = similar(name.lower(), value.lower())
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = {id: value}
    return best_match


def pick(id, champion_id, account, password, http, port):
    url = f'/lol-champ-select/v1/session/actions/{id}'
    body = {'championId': champion_id}
    response = request(url, account, password, http, port, 'PATCH', body)
    return not bool(response)


def chat(message, account, password, http, port):
    url = f'/lol-game-client-chat/v1/party-messages'
    body = {'message': message}
    request(url, account, password, http, port, 'POST', body)


def _lock(id, account, password, http, port):
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


def match_accept_thread(http, psw, port, message):
    accept_thread = False
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


class ChampPickerApp:
    def __init__(self):
        self.current_champ_select = None
        self.current_lock_file_content = None
        self.league_client_exe = "LeagueClient.exe"

        self.get_champs_url = '/lol-champions/v1/owned-champions-minimal'
        self.root = tk.Tk()
        self.initialize_gui()

    def initialize_gui(self):
        self.root.title("ChampPicker")
        self.root.configure(bg="#1e1e1e")
        self.root.overrideredirect(True)

        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        window_width = 612
        window_height = 180
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.offset_x, self.offset_y = 0, 0

        # Bind sự kiện di chuyển cửa sổ
        self.root.bind("<Button-1>", self.get_position)
        self.root.bind("<B1-Motion>", self.move_window)

        self.create_text_label(30, 30, 12, "ChampPicker v1.0.6")
        self.create_text_label(30, 60, 8, "author: l2stack")
        self.status_label = tk.Label(self.root, text="Nhập tên tướng vd: (na -> nasus):",
                                     font=("monospace", 12), fg="white", bg="#1e1e1e")
        self.status_label.place(x=30, y=90)
        self.status_label.config(anchor="w")

        self.create_button_label("Tìm tướng", 12, 9, 0, 200, 120, 'green', self.find_champ)
        self.create_button_label("Pick", 12, 9, 0, 300, 120, 'blue', self.pick_champ)
        self.create_button_label("Pick & Lock", 12, 9, 0, 400, 120, 'purple', self.pick_and_lock_champ)
        self.create_button_label("Đóng", 12, 9, 0, 500, 120, 'red', command=self.close)

        self.input_entry = tk.Entry(self.root, font=("monospace", 20), fg="black", bd=1)
        self.input_entry.place(x=30, y=120)
        self.input_entry.config(width=10, insertbackground="white")

    def create_text_label(self, pos_x, pos_y, size, message):
        label = tk.Label(self.root, text=message, font=("monospace", size), fg="white", bg="#1e1e1e")
        label.place(x=pos_x, y=pos_y)
        label.config(anchor="w")

    def create_button_label(self, text, font_size, btn_width, btn_height, pos_x, pos_y, color, command):
        btn = tk.Button(self.root, text=text, command=command, font=("monospace", font_size), fg='white', bg=color,
                        width=btn_width, height=btn_height, bd=5)
        btn.place(x=pos_x, y=pos_y)
        btn.config(cursor="hand2")

    def close(self):
        current_pid = os.getpid()
        asyncio.run(os.kill(current_pid, signal.SIGTERM))

    def get_position(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def move_window(self, event):
        self.root.geometry(f"{612}x{180}+{event.x_root - self.offset_x}+{event.y_root - self.offset_y}")

    def find_champ(self):
        working_directory = get_execute_dir(self.league_client_exe)
        if working_directory is None:
            self._print('League Of Legends hiện không hoạt động')
            return
        lock_file = os.path.join(os.path.dirname(working_directory), 'lockfile')
        if not os.path.exists(lock_file):
            self._print('Không tìm thấy lock file')
            return
        with open(lock_file, 'r') as f:
            content = f.read().split(":")
        req_url = f'{content[4]}://riot:{content[3]}@127.0.0.1:{content[2]}'
        champs = process_json(make_request('GET', req_url + self.get_champs_url))
        if champs is None:
            self._print('Error! Hãy thử lại (có vẻ client vẫn chưa khởi động xong)')
            return
        champ = self.input_entry.get()
        fc = find(champ, champs)
        if fc is None:
            self._print(f'Không tìm thấy tên khớp với: {champ}.')
            return
        else:
            self._print(f'Tìm thấy tướng: {fc} hãy chọn Pick hoặc Pick & Lock')
            self.current_champ_select = fc
            self.current_lock_file_content = content

    def pick_champ(self):
        if self.current_champ_select is None:
            self._print('Chưa tìm tướng cần pick hãy nhập tên và tìm trước')
        else:
            self._print('Luồng đang chạy! Hãy tìm trận')
            threading.Thread(target=self.pick_lock_thread, args=(
                self.current_champ_select, False, self.current_lock_file_content[4], self.current_lock_file_content[3],
                self.current_lock_file_content[2])).start()

    def pick_and_lock_champ(self):
        if self.current_champ_select is None:
            self._print('Chưa tìm tướng cần pick hãy nhập tên và tìm trước')
        else:
            self._print('Luồng đang chạy! Hãy tìm trận')
            threading.Thread(target=self.pick_lock_thread, args=(
                self.current_champ_select, True, self.current_lock_file_content[4], self.current_lock_file_content[3],
                self.current_lock_file_content[2])).start()

    def _print(self, msg):
        self.status_label.configure(text=msg)

    # def handler(self, inp):
    #     working_directory = get_execute_dir(self.league_client_exe)
    #     if working_directory is None:
    #         print('League Of Legends hiện không hoạt động')
    #         return
    #     lock_file = os.path.join(os.path.dirname(working_directory), 'lockfile')
    #     if not os.path.exists(lock_file):
    #         print('Không tìm thấy lock file')
    #         return
    #
    #     pick_lock = inp == '2'
    #     with open(lock_file, 'r') as f:
    #         content = f.read().split(":")
    #
    #     if inp == '4' or inp == '3':
    #         message = None
    #         if inp == '3':
    #             message = input('Nhập tin nhắn cần gởi: ')
    #         threading.Thread(target=self.match_accept_thread,
    #                          args=(content[4], content[3], content[2], message)).start()
    #         return
    #
    #     req_url = f'{content[4]}://riot:{content[3]}@127.0.0.1:{content[2]}'
    #     champs = process_json(make_request('GET', req_url + self.get_champs_url))
    #     if champs is None:
    #         print('Error! Hãy thử lại (có vẻ client vẫn chưa khởi động xong)')
    #         return
    #
    #     while True:
    #         champ = input('Nhập tên tướng cần tìm (Vd: na -> Nasus): ')
    #         fc = find(champ, champs)
    #
    #         if fc is None:
    #             print('Không tìm thấy tướng hãy thử lại.')
    #             return
    #
    #         print(f'Chọn tướng: {fc}')
    #         if input('Nhập y để chọn enter để hủy: ').lower() == 'y':
    #             break
    #     threading.Thread(target=self.pick_lock_thread, args=(fc, pick_lock, content[4], content[3], content[2])).start()

    def pick_lock_thread(self, champ, lock, http, psw, port):
        champion = None
        champ_id = None

        pick_thread = False
        if pick_thread:
            pick_thread = False
            time.sleep(1)

        for k in champ.keys():
            champion = champ[k]
            champ_id = k
        pick_thread = True
        self._print(f'Chọn tướng: {champion} Khóa tướng: {lock}')

        while pick_thread:
            action_id = get_action_id('riot', psw, http, port)
            if action_id == -1:
                continue

            try:
                pick(action_id, champ_id, 'riot', psw, http, port)
            except JSONDecodeError:
                pass

            if lock:
                try:
                    _lock(action_id, 'riot', psw, http, port)
                except JSONDecodeError:
                    pass
            self._print('Hoàn tất! Bạn có thể tiếp tục chọn.')
            pick_thread = False
            break

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ChampPickerApp()
    app.run()
