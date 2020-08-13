import logging
import threading
import traceback
import redis
import websocket

from logging import handlers
from function import *
from mirai import *

##################
loghandler = handlers.TimedRotatingFileHandler(os.path.join('log', 'mocaBot.log'), when='midnight', encoding='utf-8')
loghandler.setLevel(logging.DEBUG)
loghandler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s]: %(message)s'))
logger = logging.getLogger('botlogger')
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)
logger.info("日志初始化成功")
##################

session_key = mirai_init_auth_key()
pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)
cache_pool = redis.ConnectionPool(host='localhost', port=6379, db=1, decode_responses=True)
rc = redis.Redis(connection_pool=cache_pool)

handling_flag = {}


# noinspection PyBroadException
def mirai_message_handler(message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot,
                          message_chain):
    global handling_flag
    try:
        if message_type == 'GroupMessage':
            logger.debug("[GROUP] [{}] {},{} => {}".format(group_id, message_id, message_time, message_chain))
            mirai_group_message_handler(group_id, session_key, sender_permission, sender_id, message_chain, at_bot)

        if message_type == 'FriendMessage':
            logger.debug("[FRIEND] [{}] {},{} => {}".format(sender_id, message_id, message_time, message_chain))
            mirai_private_message_handler(group_id, session_key, sender_id, message_id, message_time, message_chain)

        if message_type == 'TempMessage':
            logger.debug("[TEMP] [{}] [{}] {},{} => {}".format(group_id, sender_id, message_id, message_time, message_chain))
            mirai_private_message_handler(group_id, session_key, sender_id, message_id, message_time, message_chain)

    except:
        logger.error(str(traceback.format_exc()))
    finally:
        handling_flag[str(group_id)] = False
        if not rc.get('file_list_init') == '1':
            init_files_list()


def on_message(ws, message):  # 接受ws数据
    data = mirai_json_process(3270612406, message)
    if not handling_flag.get(str(data[5])) or data[0] == 'FriendMessage' or data[0] == 'TempMessage':
        handling_flag[str(data[5])] = True
        tr = threading.Thread(target=mirai_message_handler, args=data)  # 创建子线程
        tr.start()  # 开始处理


def on_error(ws, error):
    logger.error(str(traceback.format_exc()))


def on_close(ws):
    rc.flushdb()
    logger.warning("Websocket 连接关闭")  # 记录ws关闭连接
    user_input = input("Restart?[y/N]: \n")
    if user_input.lower() == "y":
        os.system('python main.py')


def on_open(ws):  # 打开ws时
    print('initialized websocket')


def event_process():
    # os.system('python event.py')
    pass


load_group_list()
init_files_list()
init_keaipa_list()

# t = threading.Thread(target=event_process)
# t.setDaemon(True)
# t.start()

for g_id in fetch_group_list():
    init_keyword_list(int(g_id))
    init_config(int(g_id))

# websocket.enableTrace(True)    #Websocket调试模式
ws = websocket.WebSocketApp(
    "{}{}".format(config.ws_addr, session_key),
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)  # 创建websocket连接
ws.on_open = on_open  # 打开websocket
ws.run_forever(ping_interval=120, ping_timeout=5)  # 每120秒发送心跳包，维持websocket长连接
