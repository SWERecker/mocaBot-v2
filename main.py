import sqlite3
from function import *
from mirai import *
import logging
import json
import redis
import time
import threading
import websocket

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', filename='log.txt', filemode='a')

pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)

conn = sqlite3.connect('mocabot.sqlite3')
conn_cursor = conn.cursor()

session_key = mirai_init_auth_key()
group_id = [1141220711] 
r.set("do_not_repeat_{}".format(1141220711), '0')





def mirai_message_handler(data):
    if(data[0] == 'GroupMessage'):
        #fetched_message_chain = fetch_processed_message_chain(data[5], data[7])
        logging.info("[{}] => {}".format(data[5], data[7]))
        repeater(r, data[5], session_key, data[7])
        r.set('at_moca_{}'.format(str(data[5])) , '0')
        pass
    elif(data[0] == 'FriendMessage'):
        pass
    elif(data[0] == 'TempMessage'):
        pass
    else:
        pass



def on_message(ws, message):    #接受ws数据
    data = mirai_json_process(3270612406, message)
    if(data[6]):
        r.set('at_moca_{}'.format(str(data[5])) , '1')
    if(data[5] in group_id):
        mirai_message_handler(data)


def on_error(ws, error):
    logging.error(repr(error))    #记录ws错误数据

def on_close(ws):
    r.flushall()
    conn.commit()
    conn.close()
    logging.info("closed") #记录ws关闭连接


def on_open(ws):    #打开ws时
    for g_id in group_id:
        init_keyword_list(conn_cursor, r, g_id)
        init_config(conn_cursor, r, g_id)
        

#websocket.enableTrace(True)    #Websocket调试模式
ws = websocket.WebSocketApp(
    config.ws_addr + session_key,
    on_message = on_message,
    on_error = on_error,
    on_close = on_close
    )   #创建websocket连接
ws.on_open = on_open    #打开websocket
ws.run_forever(ping_interval=120,ping_timeout=5)    #每120秒发送心跳包，维持websocket长连接
