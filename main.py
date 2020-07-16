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

#r.set('cd',1,ex=10)

def repeater(group_id, message):
    if(r.get("m_count_{}".format(group_id)) == None):
        r.set("m_count_{}".format(group_id), 0)
    
    if(r.get("m_count_{}".format()) < 2):
        r.set("configMessageCache" + str(r.get("config" + str(groupID) + "messageCount")), )   #拼接字符串（群号+内容）

        r.set("config" + str(groupID) + "messageCount",r.get("config" + str(groupID) + "messageCount") + 1)            #消息计数+1
    else:                                                                                                                                            #收到了大于两条的消息后
        r.set("config" + str(groupID) + "messageCache0", r.get("config" + str(groupID) + "messageCache1"))                     #将后缓存的内容替换掉前面缓存的内容
        r.set("config" + str(groupID) + "messageCache1",str(function.fetchGroupID(pList)) + str(function.fetchMessageChain(pList)))

    if(r.get("config" + str(groupID) + "messageCache0") == r.get("config" + str(groupID) + "messageCache1") and r.get("config" + str(groupID) + "doNotRepeat") == 0):

        if(not function.isInRepeatCD(groupID) and function.randomDo(repeatChance)):
            function.consoleLog("==命中复读条件且不在cd中且命中概率，开始复读==")
            function.consoleLog(function.replyMessageChain(str(function.fetchGroupID(pList)), sessionKey, function.fetchMessageChain(pList)))
            function.updateRepeatCD(repeatCD, groupID)
        else:
            function.consoleLog("====命中复读条件但cd冷却中或没有命中概率====")



def mirai_message_handler(data):
    if(data[0] == 'GroupMessage'):
        fetched_message_chain = fetch_processed_message_chain(data[7])

        mirai_reply_message_chain(data[5], session_key, fetched_message_chain)
        r.set('at_moca_{}'.format(str(data[5])) , '0')
        pass
    elif(data[0] == 'FriendMessage'):
        pass
    elif(data[0] == 'TempMessage'):
        pass
    else:
        pass




#
# print(session_key)
# r_msg = mirai_reply_text(565379987, session_key, '23333', True)
# if(r_msg[0] == 0):
#     logging.info("success code:" + str(r_msg[0]) + "，id=" + str(r_msg[1]))
# else:
#     logging.info("error code:" + str(r_msg[0]) + "，id=" + str(r_msg[1]))

#mirai_reply_image(565379987, session_key, '116.jpg','',True)


def on_message(ws, message):    #接受ws数据
    data = mirai_json_process(3270612406, message)
    #if(data[0] == 'GroupMessage'):
        #logging.info('[{m_id}], [{group}] - [{qq}] : {m}'.format(m_id=data[1],group=data[5],qq=data[3],m=data[7]))
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
        load_keyword_list(conn_cursor, r, g_id)
    pass

#websocket.enableTrace(True)    #Websocket调试模式
ws = websocket.WebSocketApp(
    config.ws_addr + session_key,
    on_message = on_message,
    on_error = on_error,
    on_close = on_close
    )   #创建websocket连接
ws.on_open = on_open    #打开websocket
ws.run_forever(ping_interval=120,ping_timeout=5)    #每120秒发送心跳包，维持websocket长连接
