import sqlite3
from function import *
from mirai import *
import logging
import redis
import threading
import websocket

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S', filename='log.txt', filemode='a')


def load_group_list():
    group_list = [1141220711]
    return group_list


def mirai_message_handler(message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot,
                          message_chain):
    global session_key, r, conn, conn_cursor
    try:
        group_list = load_group_list()
        if message_type == 'GroupMessage':
            if group_id in group_list:
                logging.info("[{}] => {}".format(group_id, message_chain))
                r.set('group_{}_handling'.format(group_id), '1')
                r.set('at_moca_{}'.format(group_id), at_bot)  # 设置atMoca标志
                do_not_repeat_flag = mirai_group_message_handler(r, group_id, session_key, fetch_text(message_chain), sender_permission)
                if not do_not_repeat_flag:
                    repeater(r, group_id, session_key, message_chain)
        if message_type == 'FriendMessage':
            pass
        if message_type == 'TempMessage':
            pass
    except Exception as e:
        logging.error(repr(e))
    finally:
        r.set('at_moca_{}'.format(group_id), '0')  # 复位atMoca标志
        r.set('group_{}_handling'.format(group_id), '0')


def on_message(ws, message):  # 接受ws数据
    data = mirai_json_process(3270612406, message)
    if r.get('group_{}_handling'.format(data[5])) == '0':
        tr = threading.Thread(target=mirai_message_handler, args=data)  # 创建子线程
        tr.start()  # 开始处理


def on_error(ws, error):
    logging.error(repr(error))  # 记录ws错误数据


def on_close(ws):
    global session_key, r, conn, conn_cursor
    r.flushall()
    conn.commit()
    conn.close()
    logging.info("CLOSING WEBSOCKET")  # 记录ws关闭连接
    user_input = input("Restart?[y/n]: \n")
    if user_input.lower() == "y":
        session_key, r, conn, conn_cursor = init_main()
        ws_open()


def on_open(ws):  # 打开ws时
    group_list = load_group_list()
    for g_id in group_list:
        init_keyword_list(r, g_id)
        # init_config(conn_cursor, r, g_id)
        r.set('group_{}_handling'.format(g_id), '0')
        r.set("do_not_repeat_{}".format(g_id), '0')

    print('initialized websocket')


def ws_open():
    # websocket.enableTrace(True)    #Websocket调试模式
    ws = websocket.WebSocketApp(
        config.ws_addr + session_key,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )  # 创建websocket连接
    ws.on_open = on_open  # 打开websocket
    ws.run_forever(ping_interval=120, ping_timeout=5)  # 每120秒发送心跳包，维持websocket长连接


def init_main():
    global session_key, conn, conn_cursor
    session_key = mirai_init_auth_key()
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    r = redis.Redis(connection_pool=pool)

    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    return session_key, r, conn, conn_cursor


pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)
conn = sqlite3.connect('mocabot.sqlite3')
conn_cursor = conn.cursor()
cursor = conn_cursor.execute('select "CONTENT" from "KEAIPA" WHERE "NAME"="KEAI"')
for row in cursor:
    keai_list = json.loads(row[0])
cursor = conn_cursor.execute('select "CONTENT" from "KEAIPA" WHERE "NAME"="PA"')
for row in cursor:
    pa_list = json.loads(row[0])
r.set('keai_list', json.dumps(keai_list, ensure_ascii=False))
r.set('pa_list', json.dumps(pa_list, ensure_ascii=False))

session_key, r, conn, conn_cursor = init_main()
ws_open()
