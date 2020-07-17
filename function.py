import json
import logging
import sqlite3
import random
from mirai import *
from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont


def update_lp(c, qq, lp_name):
    """
    功能：更新设置的lp
    参数：{
        c       : SQLite Connection Cursor,
        qq      : 要查询的QQ号,
        lp_name : 要增/改的名称
    }
    返回：无
    """
    cursor = c.execute('select * from lplist where qq="{userqq}"'.format(userqq=qq))

    if not cursor.fetchall():
        c.execute("INSERT INTO LPLIST (qq,lpname) VALUES ('{pqq}', '{plpname}' )".format(pqq=qq, plpname=lp_name))
        logging.info("新增lp记录：用户{}设置lp为:{}".format(qq, lp_name))
    else:
        c.execute("UPDATE LPLIST SET lpname='{plp_name}' WHERE qq='{pqq}'".format(plp_name=lp_name, pqq=qq))
        logging.info("修改lp记录：用户{}设置lp为:{}".format(qq, lp_name))


def fetch_lp(c, qq):
    """
    功能：获取设置的lp
    参数：{
        c  : SQLite Connection Cursor,
        qq : 要查询的QQ号
    }
    返回：设置的lp名称
    """
    cursor = c.execute('select lpname from lplist where qq="{userqq}"'.format(userqq=qq))
    for l in cursor.fetchall():
        if l:
            return l[0]
        else:
            return None


def mirai_json_process(bot_id, data):
    """
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
    """
    group_id = ''
    at_bot = '0'
    message_id = 0
    message_time = 0
    r_json_dict = json.loads(data)
    message_type = r_json_dict.get('type')
    message_chain = r_json_dict.get('messageChain')
    if message_chain:
        message_id = message_chain[0].get('id')
        message_time = message_chain[0].get('time')
        del message_chain[0]
        for n in range(len(message_chain)):
            if message_chain[n].get('type') == 'At' and message_chain[n].get('target') == bot_id:
                at_bot = '1'
                break
            else:
                at_bot = '0'
    sender_id = r_json_dict["sender"].get('id')
    sender_permission = r_json_dict["sender"].get('permission')
    if r_json_dict["sender"].get('group'):
        group_id = r_json_dict["sender"]["group"].get('id')

    return message_type, message_id, message_time, sender_id, sender_permission, group_id, at_bot, message_chain


def random_do(chance):
    """
    功能：随机事件 {chance}% 发生
    参数：{
        chance : 0~100,
    }
    返回：发生(True)，不发生(False)
    """
    seed = random.random()
    true_chance = int(chance) / 100
    if seed < true_chance:
        return True
    else:
        return False


def fetch_text(data):
    """
    功能：获取去空格的文字内容
    参数：{
        data : messageChain (List)
    }
    返回：去空格的文字内容
    """
    texts = ""
    for n in range(len(data)):
        if data[n].get('type') == 'Plain':
            texts += data[n].get('text')
            texts = texts.replace(" ", "")
    return texts.lower()


def fetch_processed_message_chain(group_id, data):
    """
    功能：返回的messageChain，将图片URL和path去除，方便判断是否复读消息
    参数：{
        group_id : 群号,
        data     : messageChain (List)
    }
    返回：去空格的文字内容
    """
    for n in range(len(data)):
        if data[n].get('type') == 'Image':
            del data[n]["url"]
            del data[n]["path"]
    data.append({'group_id': group_id})
    return data


def init_keyword_list(r, group_id):
    """
    功能：从SQLite中加载关键词列表到Redis内存数据库中，在Redis中存储至key_{群号},格式为json字符串
    参数：{
        r        : Redis对象,
        group_id : QQ群号
    }
    返回：1
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    c = conn.cursor()
    cursor = c.execute('select NAME,KEYWORD from "key_{}"'.format(group_id))
    keyword_list = {}
    for row in cursor:
        keyword_list[row[0]] = row[1]
    json_data = json.dumps(keyword_list, ensure_ascii=False)
    r.set('key_{}'.format(group_id), json_data)
    conn.close()

    return 1


# def init_config(c, r, group_id):
#     """
#     功能：从SQLite中加载参数到Redis内存数据库中，在Redis中存储至config_{群号},格式为json字符串
#     参数：{
#         c        : SQLite Connection Cursor,
#         r        : Redis对象,
#         group_id : QQ群号
#     }
#     返回：1
#     """
#     cursor = c.execute('select NAME,PARA from "config_{}"'.format(group_id))
#     config_list = {}
#     for row in cursor:
#         config_list[row[0]] = row[1]
#     json_data = json.dumps(config_list, ensure_ascii=False)
#     r.set('config_{}'.format(group_id), json_data)
#     return 1


def get_config(group_id, arg):
    """
    功能：从SQLite数据库中查询某参数
    参数：{
        group_id : QQ群号,
        arg      : 参数名称
    }
    返回：参数值
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('select PARA from config_{} WHERE NAME="{}"'.format(group_id, arg))

    for l in cursor.fetchall():
        if l:
            logging.debug("{} : {}".format(arg, l[0]))
            return l[0]
        else:
            return None


def repeater(r, group_id, session_key, message):
    """
    功能：复读机
    参数：{
        r           : Redis对象,
        group_id    : QQ群号,
        session_key : sessionKey,
        message     : 消息的MessageChain
    }
    返回：无
    """
    # 缓存消息 ===
    m_cache_0 = ''
    m_cache_1 = ''
    if not r.exists("m_count_{}".format(group_id)):
        r.set("m_count_{}".format(group_id), '0')

    m_count = int(r.get("m_count_{}".format(group_id)))
    processed_message_chain = fetch_processed_message_chain(group_id, message)
    if m_count < 2:
        r.set("m_cache_{}_{}".format(group_id, m_count), str(processed_message_chain))  # 拼接字符串（群号+内容）
        r.set("m_count_{}".format(group_id), str(m_count + 1))  # 消息计数+1
    else:  # 收到了大于两条的消息后
        r.set("m_cache_{}_0".format(group_id), r.get("m_cache_{}_1".format(group_id)))  # 将后缓存的内容替换掉前面缓存的内容
        r.set("m_cache_{}_1".format(group_id), str(processed_message_chain))
    # 缓存消息 ===

    if r.exists("m_cache_{}_0".format(group_id)):
        m_cache_0 = json.loads(r.get("m_cache_{}_0".format(group_id)).replace("'", '"'))
    if r.exists("m_cache_{}_1".format(group_id)):
        m_cache_1 = json.loads(r.get("m_cache_{}_1".format(group_id)).replace("'", '"'))

    if m_cache_0 == m_cache_1 and r.get("do_not_repeat_{}".format(group_id)) == '0':
        if not is_in_cd(r, group_id, "repeatCD"):
            if random_do(get_config(group_id, "repeatChance")):
                logging.info("[{}] 命中复读条件且不在cd中且命中概率，开始复读".format(group_id))
                del processed_message_chain[len(processed_message_chain) - 1]
                mirai_reply_message_chain(group_id, session_key, processed_message_chain)
                update_cd(r, group_id, "repeatCD")
            else:
                logging.info("[{}] 未命中复读概率".format(group_id))
        else:
            logging.info("[{}] 复读cd冷却中".format(group_id))


def is_in_cd(r, group_id, cd_type):
    """
    功能：判断是否在复读cd中
    参数：{
        r           : Redis对象,
        group_id    : QQ群号,
        cd_type     : 要查询的cd类型
    }
    返回：True/False
    """
    stat = r.get('in_{}_cd_{}'.format(cd_type, group_id))
    if stat == '1':
        return True
    else:
        return False


def update_cd(r, group_id, cd_type):
    """
    功能：更新cd（通过设置Redis key的过期时间实现）
    参数：{
        r           : Redis对象,
        group_id    : QQ群号,
        cd_type     : 要设置的cd类型
    }
    返回：True/False
    """
    group_cd = get_config(group_id, cd_type)
    r.set('in_{}_cd_{}'.format(cd_type, group_id), '1', ex=int(group_cd))


def create_dict_pic(data, group_id, content):
    """
    功能：将json转换为图片文件
    参数：{
        data        : 列表,
        group_id    : 群号,
        content     : 表格第二列的标题
    }
    返回：无
    创建对象：写入{mirai_path}\plugins\MiraiAPIHTTP\images\{名称}.png
    """
    tab = PrettyTable(border=False, header=True, header_style='title')
    font_file = os.path.dirname(os.path.abspath(__file__)) + "\\font\\PingFang.ttf"
    bg_file = os.path.dirname(os.path.abspath(__file__)) + "\\template\\bg.png"
    new_img_file = config.mirai_path + '\\plugins\\MiraiAPIHTTP\\images\\' + str(group_id) + '.png'
    # 设置表头
    tab.field_names = ["名称", content]
    tab.align["名称"] = "l"
    # 表格内容插入
    tab.add_row(["", ""])
    for name in data:
        tab.add_row([name, data[name]])
    tab_info = str(tab).replace("[", "").replace("]", "").replace(",", ", ").replace("'", " ")
    space = 50
    # PIL模块中，确定写入到图片中的文本字体
    font = ImageFont.truetype(font_file, 20, encoding='utf-8')
    # Image模块创建一个图片对象
    im = Image.new('RGB', (10, 10), (255, 255, 255, 0))
    # ImageDraw向图片中进行操作，写入文字或者插入线条都可以
    draw = ImageDraw.Draw(im, "RGB")
    # 根据插入图片中的文字内容和字体信息，来确定图片的最终大小
    img_size = draw.multiline_textsize(tab_info, font=font)
    # 图片初始化的大小为10-10，现在根据图片内容要重新设置图片的大小
    im_new = im.resize((img_size[0] + int(space * 2), img_size[1] + int(space * 2)))
    del draw
    del im
    draw = ImageDraw.Draw(im_new, 'RGB')
    img = Image.open(bg_file)
    im_new.paste(img, (0, 0))
    img_x, img_y = im_new.size
    bg_x, bg_y = img.size
    if bg_y < img_y:
        pos_y = 0
        while pos_y < img_y:
            im_new.paste(img, (0, pos_y))
            pos_y += bg_y
            logging.debug("pasted:y,", pos_y)
    if bg_x < img_x:
        pos_x = 0
        pos_y = 0
        while pos_y < img_y:
            while pos_x < img_x:
                im_new.paste(img, (pos_x, pos_y))
                pos_x += bg_x
                logging.debug("pasted:x,y ,", pos_x, ",", pos_y)
            pos_x = 0
            pos_y += bg_y
    draw.multiline_text((space, space), tab_info, fill=(0, 0, 0), font=font)
    im_new.save(new_img_file, "png")
    del draw


def update_count(group_id, name):
    return 1


def get_count_dict(group_id):
    """
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('select NAME,COUNT from "count_{}"'.format(group_id))
    count_list = {}
    for row in cursor:
        count_list[row[0]] = row[1]
    return count_list


def mirai_group_message_handler(r, group_id, session_key, text, sender_permission):
    """
    功能：群聊消息处理器
    参数：{
        r                 : Redis对象,
        group_id          : QQ群号,
        session_key       : sessionKey,
        text              : 消息的文本内容,
        sender_permission : 发消息的人的权限
    }
    返回：True/False
    """

    if r.get('at_moca_{}'.format(group_id)) == '1':
        if '说明' in text or 'help' in text or '帮助' in text:
            mirai_reply_text(group_id, session_key, '使用说明：https://wiki.bang-dream.tech/')
            logging.info("[{}] 请求使用说明".format(group_id))
            return True

        if '关键词' in text:
            if not is_in_cd(r, group_id, "replyHelpCD"):
                logging.info("[{}] 请求关键词列表".format(group_id))
                json_data = json.loads(r.get('key_{}'.format(group_id)))
                create_dict_pic(json_data, str(group_id) + '_key', '关键词')
                mirai_reply_image(group_id, session_key, str(group_id) + '_key.png')
                update_cd(r, group_id, "replyHelpCD")
            else:
                logging.info("[{}] 关键词列表cd冷却中".format(group_id))
            return True

        if "统计次数" in text:
            if not is_in_cd(r, group_id, "replyHelpCD"):
                logging.info("[{}] 请求统计次数".format(group_id))
                json_data = get_count_dict(group_id)
                create_dict_pic(json_data, str(group_id) + '_count', '次数')  # 将json转换为图片
                mirai_reply_image(group_id, session_key, str(group_id) + "_count.png")  # 发送图片
                update_cd(r, group_id, "replyHelpCD")
            else:
                logging.info("[{}] 统计次数cd冷却中".format(group_id))
            return True

        if "爬" in text or "爪巴" in text:
            if not is_in_cd(r, group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.get('pa_list'))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                else:
                    logging.info("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca爬，但是cd冷却中".format(group_id))
            return True

        if "可爱" in text or "老婆" in text or "lp" in text or "mua" in text:
            if not is_in_cd(r, group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.get('keai_list'))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                else:
                    logging.info("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca可爱，但是cd冷却中".format(group_id))
            return True
    else:
        if "moca爬" in text or "moca爪巴" in text:
            if not is_in_cd(r, group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.get('pa_list'))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                else:
                    logging.info("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca爬，但是cd冷却中".format(group_id))
            return True

        if "moca可爱" in text or "moca老婆" in text:
            if not is_in_cd(r, group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.get('keai_list'))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                else:
                    logging.info("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca可爱，但是cd冷却中".format(group_id))
            return True

        if sender_permission == 'ADMINISTRATOR' or sender_permission == 'OWNER':
            pass

    return False

