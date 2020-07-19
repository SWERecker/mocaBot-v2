import sqlite3
from function import *
from mirai import *
import logging
import redis
import threading
import websocket

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S', filename='log.txt', filemode='a')

session_key = mirai_init_auth_key()
pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)


def mirai_message_handler(message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot,
                          message_chain):
    try:
        if message_type == 'GroupMessage':
            if group_id in group_list:
                logging.info("[GROUP] [{}] {},{} => {}".format(group_id, message_id, message_time, message_chain))
                r.set('group_{}_handling'.format(group_id), '1')
                r.set('at_moca_{}'.format(group_id), at_bot)  # 设置atMoca标志
                mirai_group_message_handler(group_id, session_key, fetch_text(message_chain), sender_permission, sender_id)
                repeater(group_id, session_key, message_chain)
        if message_type == 'FriendMessage':
            logging.info("[FRIEND] [{}] {},{} => {}".format(sender_id, message_id, message_time, message_chain))
        if message_type == 'TempMessage':
            logging.info("[TEMP] [{}] {},{} => {}".format(sender_id, message_id, message_time, message_chain))
    except Exception as e:
        logging.error(repr(e))
    finally:
        r.set('at_moca_{}'.format(group_id), '0')  # 复位atMoca标志
        r.set('group_{}_handling'.format(group_id), '0')
        r.set("do_not_repeat_{}".format(group_id), '0')
        if not r.get('file_list_init') == '1':
            init_files_list()


def on_message(ws, message):  # 接受ws数据
    data = mirai_json_process(3270612406, message)
    if r.get('group_{}_handling'.format(data[5])) == '0':
        tr = threading.Thread(target=mirai_message_handler, args=data)  # 创建子线程
        tr.start()  # 开始处理


def on_error(ws, error):
    logging.error(repr(error))  # 记录ws错误数据


def on_close(ws):
    r.flushall()
    logging.info("CLOSING WEBSOCKET")  # 记录ws关闭连接
    user_input = input("Restart?[y/N]: \n")
    if user_input.lower() == "y":
        os.system('python main.py')


def on_open(ws):  # 打开ws时
    print('initialized websocket')


def event_process():
    os.system('python event.py')


group_list = load_group_list()
for g_id in group_list:
    init_keyword_list(g_id)
    r.set('group_{}_handling'.format(g_id), '0')
    r.set("do_not_repeat_{}".format(g_id), '0')
init_files_list()
init_keaipa_list()
init_quotation_list()

t = threading.Thread(target=event_process)
t.setDaemon(True)
t.start()

# websocket.enableTrace(True)    #Websocket调试模式
ws = websocket.WebSocketApp(
    config.ws_addr + session_key,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)  # 创建websocket连接
ws.on_open = on_open  # 打开websocket
ws.run_forever(ping_interval=120, ping_timeout=5)  # 每120秒发送心跳包，维持websocket长连接
