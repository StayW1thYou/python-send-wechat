import os
import queue
import sys
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, request
from pyautogui import hotkey, moveTo
from pygetwindow import getWindowsWithTitle
from pyperclip import copy

app = Flask(__name__)
stop_until = datetime.now()
default_username = "工作-"
requests_queue = queue.Queue()


def send_actual(who, msg, again=False):
    one_more_time = False
    try:
        v7 = getWindowsWithTitle(who)[0]
    except Exception as e:
        return f"Error: windows not found -> {e}"
    try:
        v7.restore()
        try:
            v7.activate()
        except Exception as e:
            print(f"Warning: {e}")
            one_more_time = True
        moveTo(v7.left + 5, v7.top + v7.height - 5)
        if not one_more_time:
            paste(msg)
            time.sleep(0.5)
            hotkey('alt', 's')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(again, exc_type, filename, exc_tb.tb_lineno, e)
        if again:
            return f"Error: {e} while sending [{msg}] to [{who}]"
        else:
            one_more_time = True
    finally:
        v7.minimize()
        if one_more_time and not again:
            return send_actual(who, msg, True)

    return f"Success: Sent [{msg}] to [{who}]"


def paste(text):
    text = text.replace("\\n", "\n")
    copy(text)
    hotkey('ctrl', 'v')


def send_from_queue():
    while True:
        who, msg = requests_queue.get()
        try:
            info = send_actual(who, msg)
            print(info)
        except Exception as e:
            print(e)
        requests_queue.task_done()
        time.sleep(0.3)


def get_unsent_messages():
    unsent_messages = []
    count = 0
    with requests_queue.mutex:
        for index, (username, message) in enumerate(list(requests_queue.queue)):
            unsent_messages.append(f"{index + 1}: {username} -> {message}")
            count += 1
    return unsent_messages, count


@app.route('/init', methods=['GET'])
def init():
    username = request.args.get('username')
    if not username:
        username = default_username
    try:
        getWindowsWithTitle(username)[0].minimize()
    except Exception as e:
        return {"msg": f"can't minimize windows -> {e}", "status": 1}
    return {'msg': 'ok', 'status': 0}


@app.route('/reset', methods=['GET'])
def reset_queue():
    with requests_queue.mutex:
        requests_queue.queue.clear()
    return {"msg": "Queue has been reset", "status": 0}


@app.route('/unsent', methods=['GET'])
def unsent():
    unsent_messages, count = get_unsent_messages()
    return {"msg": unsent_messages, "status": count if count else 0}


@app.route('/stop', methods=['GET'])
def stop():
    global stop_until
    sec = request.args.get('sec', default=1, type=int)
    with requests_queue.mutex:
        requests_queue.queue.clear()
    stop_until = datetime.now() + timedelta(seconds=sec)
    return {"msg": "Queue has been reset and new sends are stopped", "status": 0}


@app.route('/send', methods=['GET', 'POST'])
def handle():
    global stop_until
    if datetime.now() < stop_until:
        return {'msg': 'temporarily unavailable due to stop request', 'status': 2}

    username = request.args.get('username')
    message = request.args.get('message')
    if not username:
        username = default_username
    if not message:
        return {'msg': 'message is required', 'status': 1}
    requests_queue.put((username, message))
    return {'msg': 'ok', 'status': 0}


if __name__ == '__main__':
    threading.Thread(target=send_from_queue, daemon=True).start()
    app.run(host="0.0.0.0", port=8989)
