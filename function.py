import sqlite3
import json
import logging
import random
from mirai import *
def update_lp(c, qq, lp_name):
    '''
    功能：更新设置的lp
    参数：{
        c       : SQLite Connection Cursor,
        qq      : 要查询的QQ号,
        lp_name : 要增/改的名称
    }
    返回：无
    '''
    cursor = c.execute('select * from lplist where qq="{userqq}"'.format(userqq=qq))

    if(not cursor.fetchall()):
        c.execute("INSERT INTO LPLIST (qq,lpname) VALUES ('{pqq}', '{plpname}' )".format(pqq=qq,plpname=lp_name))
        logging.info ("新增lp记录：用户{}设置lp为:{}".format(qq,lp_name))
    else:
        c.execute("UPDATE LPLIST SET lpname='{plp_name}' WHERE qq='{pqq}'".format(plp_name=lp_name,pqq=qq))
        logging.info ("修改lp记录：用户{}设置lp为:{}".format(qq,lp_name))

def fetch_lp(c, qq):
    '''
    功能：获取设置的lp
    参数：{
        c  : SQLite Connection Cursor,
        qq : 要查询的QQ号
    }
    返回：设置的lp名称
    '''
    cursor = c.execute('select lpname from lplist where qq="{userqq}"'.format(userqq=qq))
    for l in cursor.fetchall():
        if(l):
            return l[0]


def mirai_json_process(bot_id, data):
    '''
    功能：处理json数据
    参数：{
        bot_id : bot的QQ号
        data   : 从mirai-http-api接收到的数据
    }
    返回：{
        消息类型,
        消息ID,
        消息时间（时间戳）,
        发送者QQ,
        发送者权限（若非群聊消息则为None）,
        群号（若非群聊消息则为None）,
        消息列表，不包含id，时间
    }
    '''
    sender_permission = None
    group_id = None
    at_bot = False
    r_json_dict = json.loads(data)
    message_type = r_json_dict.get('type')
    message_chain = r_json_dict.get('messageChain')
    if(message_chain):
        message_id = message_chain[0].get('id')
        message_time = message_chain[0].get('time')
        del message_chain[0]
        for n in range(len(message_chain)):
            if(message_chain[n].get('type') == 'At' and message_chain[n].get('target') == bot_id):
                at_bot = True
    sender_id = r_json_dict["sender"].get('id')
    sender_permission = r_json_dict["sender"].get('permission')
    if(r_json_dict["sender"].get('group')):
        group_id = r_json_dict["sender"]["group"].get('id')
    return message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot, message_chain


def random_do(chance):
    '''
    功能：随机事件 {chance}% 发生
    参数：{
        chance : 0~100,
    }
    返回：发生(True)，不发生(False)
    '''
    seed = random.random()
    true_chance = int(chance) / 100
    if(seed < true_chance):
        return True
    else:
        return False


def fetch_text(data):
    '''
    功能：获取去空格的文字内容
    参数：{
        data : messageChain (List)
    }
    返回：去空格的文字内容
    '''
    texts = ""
    for n in range(len(data)):
        if(data[n].get('type') == 'Plain'):
            texts += data[n].get('text')
            texts = texts.replace(" ","")
    return texts.lower()


def fetch_processed_message_chain(group_id, data):
    '''
    功能：返回的messageChain，将图片URL和path去除，方便判断是否复读消息
    参数：{
        group_id : 群号,
        data     : messageChain (List)
    }
    返回：去空格的文字内容
    '''
    for n in range(len(data)):
        if(data[n].get('type') == 'Image'):
            del data[n]["url"]
            del data[n]["path"]
    data.append({'group_id':group_id})
    return data


def init_keyword_list(c, r, group_id):
    '''
    功能：从SQLite中加载关键词列表到Redis内存数据库中，在Redis中存储至key_{群号},格式为json字符串
    参数：{
        c        : SQLite Connection Cursor,
        r        : Redis对象,
        group_id : QQ群号
    }
    返回：1
    '''
    cursor = c.execute('select NAME,KEYWORD from "key_{}"'.format(group_id))
    keyword_list = {}
    for row in cursor:
        keyword_list[row[0]] = row[1]
    json_data = json.dumps(keyword_list,ensure_ascii=False)
    r.set('key_{}'.format(group_id), json_data)
    return 1


def init_config(c, r, group_id):
    cursor = c.execute('select NAME,PARA from "config_{}"'.format(group_id))
    config_list = {}
    for row in cursor:
        config_list[row[0]] = row[1]
    json_data = json.dumps(config_list,ensure_ascii=False)
    r.set('config_{}'.format(group_id), json_data)
    return 1


def get_config(r, group_id, arg):
    if(r.exists('config_{}'.format(group_id))):
        json_dict = json.loads(r.get('config_{}'.format(group_id)))
    return json_dict.get(arg)


def repeater(r, group_id, session_key, message):
    #缓存消息 ===
    m_cache_0 = ''
    m_cache_1 = ''
    if(r.get("m_count_{}".format(group_id)) == None):
        r.set("m_count_{}".format(group_id), '0')
    m_count = int(r.get("m_count_{}".format(group_id)))
    processed_message_chain = fetch_processed_message_chain(group_id, message)
    if(m_count < 2):
        r.set("m_cache_{}_{}".format(group_id,m_count), str(processed_message_chain))    #拼接字符串（群号+内容）
        r.set("m_count_{}".format(group_id), str(m_count + 1))   #消息计数+1
    else:   #收到了大于两条的消息后
        r.set("m_cache_{}_0".format(group_id), r.get("m_cache_{}_1".format(group_id)))  #将后缓存的内容替换掉前面缓存的内容
        r.set("m_cache_{}_1".format(group_id) , str(processed_message_chain))
    #缓存消息 ===
    
    if(r.exists("m_cache_{}_0".format(group_id))):
        m_cache_0 = json.loads(r.get("m_cache_{}_0".format(group_id)).replace("'", '"'))
    if(r.exists("m_cache_{}_1".format(group_id))):
        m_cache_1 = json.loads(r.get("m_cache_{}_1".format(group_id)).replace("'", '"'))
    
    if(m_cache_0 == m_cache_1 and r.get("do_not_repeat_{}".format(group_id)) == '0'):
        if( not is_in_repeat_cd(r, group_id) ):
            if(random_do(get_config(r, group_id, "repeatChance")) ):
                logging.info ("[{}] 命中复读条件且不在cd中且命中概率，开始复读".format(group_id))
                del processed_message_chain[len(processed_message_chain) - 1]
                mirai_reply_message_chain(group_id, session_key, processed_message_chain)
                update_repeat_cd(r, group_id)
            else:
                logging.info ("[{}] 未命中复读概率".format(group_id))  
        else:
            logging.info ("[{}] 复读cd冷却中".format(group_id))      
            

def is_in_repeat_cd(r, group_id):
    stat = r.get('in_repeat_cd_{}'.format(group_id))
    if(stat == '1'):
        return True
    else:
        return False
        
        
def update_repeat_cd(r, group_id):
    group_cd = get_config(r, group_id, "repeatCD")
    r.set('in_repeat_cd_{}'.format(group_id), '1', ex=int(group_cd))