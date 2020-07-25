from function import *
from mirai import *
import logging
import redis
import threading
import websocket
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S', filename='log.txt', filemode='a')

session_key = mirai_init_auth_key()
pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)
cache_pool = redis.ConnectionPool(host='localhost', port=6379, db=1, decode_responses=True)
rc = redis.Redis(connection_pool=cache_pool)


# noinspection PyBroadException
def mirai_message_handler(message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot,
                          message_chain):
    try:
        if message_type == 'GroupMessage':
            group_list = fetch_group_list()
            if str(group_id) in group_list:
                logging.debug("[GROUP] [{}] {},{} => {}".format(group_id, message_id, message_time, message_chain))
                rc.hset(group_id, 'handling', '1')
                rc.hset(group_id, 'at_moca', at_bot)  # 设置atMoca标志
                text = fetch_text(message_chain)
                if at_bot == '1':
                    upload_photo(group_id, session_key, text, message_chain)
                mirai_group_message_handler(group_id,
                                               session_key, text, sender_permission, sender_id)
                if not rc.hget(group_id, "do_not_repeat") == '1':
                    repeater(group_id, session_key, message_chain)

        if message_type == 'FriendMessage':
            logging.info("[FRIEND] [{}] {},{} => {}".format(sender_id, message_id, message_time, message_chain))
            # mirai_private_message_handler(0, session_key, sender_id, message_id, message_time, message_chain)
            mirai_reply_text(session_key, sender_id, "由于核心限制，目前暂不开放私聊功能。", friend=True)
        if message_type == 'TempMessage':
            logging.info(
                "[TEMP] [{}] [{}] {},{} => {}".format(group_id, sender_id, message_id, message_time, message_chain))
            # mirai_private_message_handler(group_id, session_key, sender_id, message_id, message_time, message_chain)
            mirai_reply_text(session_key, sender_id, "由于核心限制，目前暂不开放临时消息功能。", temp=True, temp_group_id=group_id)

    except:
        logging.error(str(traceback.format_exc()))
    finally:
        rc.hset(group_id, 'at_moca', '0')  # 复位atMoca标志
        rc.hset(group_id, 'handling', '0')
        rc.hset(group_id, "do_not_repeat", '0')
        if not rc.get('file_list_init') == '1':
            init_files_list()


def on_message(ws, message):  # 接受ws数据
    data = mirai_json_process(3270612406, message)
    if rc.hget(data[5], 'handling') == '0' or data[0]:
        tr = threading.Thread(target=mirai_message_handler, args=data)  # 创建子线程
        tr.start()  # 开始处理


def on_error(ws, error):
    logging.error(str(traceback.format_exc()))


def on_close(ws):
    rc.flushdb()
    logging.info("Websocket 连接关闭")  # 记录ws关闭连接
    user_input = input("Restart?[y/N]: \n")
    if user_input.lower() == "y":
        os.system('python main.py')


def on_open(ws):  # 打开ws时
    print('initialized websocket')


def event_process():
    os.system('python event.py')


load_group_list()
init_files_list()
init_keaipa_list()

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
