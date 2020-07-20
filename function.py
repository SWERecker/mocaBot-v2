import json
import logging
import sqlite3
import random
import redis
from mirai import *
from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont
import difflib

pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)


def update_lp(qq, lp_name):
    """
    功能：更新设置的lp
    参数：{
        qq      : 要查询的QQ号,
        lp_name : 要增/改的名称
    }
    返回：无
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()

    cursor = conn_cursor.execute('SELECT * FROM LPLIST WHERE QQ="{userqq}"'.format(userqq=qq))

    if len(list(cursor)) > 0:
        conn_cursor.execute("UPDATE LPLIST SET LPNAME='{plp_name}' WHERE QQ='{pqq}'".format(plp_name=lp_name, pqq=qq))
        logging.info("修改lp记录：用户{}设置lp为:{}".format(qq, lp_name))
    else:
        conn_cursor.execute(
            "INSERT INTO LPLIST (QQ,LPNAME) VALUES ('{pqq}', '{plpname}' )".format(pqq=qq, plpname=lp_name))
        logging.info("新增lp记录：用户{}设置lp为:{}".format(qq, lp_name))
    conn.commit()
    conn.close()


def fetch_lp(qq):
    """
    功能：获取设置的lp
    参数：{
        qq : 要查询的QQ号
    }
    返回：设置的lp名称
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT LPNAME FROM LPLIST WHERE QQ="{userqq}"'.format(userqq=qq))
    fetched_list = list(cursor)
    conn.close()
    if len(fetched_list) > 0:
        return fetched_list[0][0]
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


def init_keyword_list(group_id):
    """
    功能：从SQLite中加载关键词列表到Redis内存数据库中，在Redis中存储至key_{群号},格式为json字符串
    参数：{
        group_id : QQ群号
    }
    返回：1
    """
    global r
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute("SELECT CONTENT FROM KEYWORDS WHERE NAME='{}'".format(group_id))
    data_list = list(cursor)
    if len(data_list) > 0:
        r.set('key_{}'.format(group_id), data_list[0][0])
        logging.info('[{}] 初始化关键词列表成功'.format(group_id))
    else:
        logging.info('[{}] 未找到关键词列表，新建默认'.format(group_id))
        cursor = conn_cursor.execute("SELECT CONTENT FROM KEYWORDS WHERE NAME='key_template'")
        template_list = list(cursor)
        temp_data = template_list[0][0]
        update_database('KEYWORDS', group_id, temp_data)
        r.set('key_{}'.format(group_id), data_list[0][0])
    conn.close()
    return 1


def load_group_list():
    """

    """
    file_group_list = []
    if os.path.isfile('group.list'):
        with open('group.list', 'r', encoding='utf-8')as group_list_file:
            for qq in group_list_file.readlines():
                file_group_list.append(int(qq.strip('\n')))  # 遍历添加
    return file_group_list


def init_files_list():
    """
    功能：读取文件列表缓存至Redis数据库
    参数：{}
    返回：1
    """
    global r
    names_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\")
    for name in names_list:
        file_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\" + name + "\\")
        r.set(name, json.dumps(file_list, ensure_ascii=False))
        logging.debug("saving {} to redis, data : {}".format(name, file_list))
    logging.info('已重建图片索引')
    r.set('file_list_init', '1', ex=600)


def init_quotation_list():
    """

    """
    global r
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute("SELECT KEYS, CONTENT FROM QUOTATION")
    temp_data = {}
    i = 0
    for row in cursor:
        keys = row[0].replace(' ', '').split(',')
        data = row[1].replace(' ', '').split(',')
        temp_data[str(i)] = {"key": keys, "quo": data}
        i += 1
    conn.close()
    r.set('quotation_dict', json.dumps(temp_data, ensure_ascii=False))


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
    cursor = conn_cursor.execute('SELECT CONTENT FROM CONFIG WHERE NAME="{}"'.format(group_id))
    data_list = list(cursor)
    if len(data_list) > 0:
        config_data = json.loads(data_list[0][0])
        logging.info('[{}] GET CONFIG {} = {}'.format(group_id, arg, config_data.get(arg)))
        conn.close()
    else:
        logging.info('[{}] CONFIG 不存在，新建默认'.format(group_id))
        cursor = conn_cursor.execute('SELECT CONTENT FROM CONFIG WHERE NAME="config_template"')
        temp_data = list(cursor)
        update_database('CONFIG', group_id, temp_data[0][0])
        conn.commit()
        cursor = conn_cursor.execute('SELECT CONTENT FROM CONFIG WHERE NAME="{}"'.format(group_id))
        data_list = list(cursor)
        config_data = json.loads(data_list[0][0])
        conn.close()
    return config_data.get(arg)


def update_config(group_id, arg, value):
    """
    功能：向SQLite中更新某参数
    参数：{
        group_id : QQ群号,
        arg      : 参数名称,
        value    : 参数值
    }
    返回：新参数值
    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT CONTENT FROM CONFIG WHERE NAME="{}"'.format(group_id))
    data_list = list(cursor)
    if len(data_list) > 0:
        config_data = json.loads(data_list[0][0])
        if config_data.get(arg):
            config_data[arg] = value
            logging.info('[{}] UPDATE CONFIG {} = {}'.format(group_id, arg, value))
            update_database("CONFIG", group_id, json.dumps(config_data, ensure_ascii=False))
            conn.commit()
        else:
            logging.info("[{}] 无此参数: {}".format(group_id, arg))
    cursor = conn_cursor.execute('SELECT CONTENT FROM CONFIG WHERE NAME="{}"'.format(group_id))
    data_list = list(cursor)
    config_data = json.loads(data_list[0][0])
    conn.close()
    return config_data.get(arg)


def append_keyword(group_id, key, value):
    """

    """
    global r
    group_keywords = json.loads(r.get('key_{}'.format(group_id)))
    if value in group_keywords[key]:
        logging.error("[{}] 向 {} 中添加重复关键词 {}")
        return False
    else:
        group_keywords[key].append(value)
        new_keywords_json = json.dumps(group_keywords, ensure_ascii=False)
        r.set('key_{}'.format(group_id), new_keywords_json)
        update_database("KEYWORDS", group_id, new_keywords_json)
        logging.info("[{}] 向 {} 中添加关键词 {}".format(group_id, key, value))
        return True


def remove_keyword(group_id, key, value):
    """

    """
    global r
    group_keywords = json.loads(r.get('key_{}'.format(group_id)))
    if value in group_keywords[key]:
        group_keywords[key].remove(value)
        new_keywords_json = json.dumps(group_keywords, ensure_ascii=False)
        r.set('key_{}'.format(group_id), new_keywords_json)
        update_database("KEYWORDS", group_id, new_keywords_json)
        logging.info("[{}] 删除 {} 中的关键词 {}".format(group_id, key, value))
        return True
    else:
        logging.error("[{}] 删除 {} 的关键词 {} 不存在")
        return False


def repeater(group_id, session_key, message):
    """
    功能：复读机
    参数：{
        group_id    : QQ群号,
        session_key : sessionKey,
        message     : 消息的MessageChain
    }
    返回：无
    """
    global r
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
        if not is_in_cd(group_id, "repeatCD"):
            if random_do(get_config(group_id, "repeatChance")):
                logging.info("[{}] 命中复读条件且不在cd中且命中概率，开始复读".format(group_id))
                del processed_message_chain[len(processed_message_chain) - 1]
                mirai_reply_message_chain(group_id, session_key, processed_message_chain)
                update_cd(group_id, "repeatCD")
            else:
                logging.info("[{}] 未命中复读概率".format(group_id))
        else:
            logging.info("[{}] 复读cd冷却中".format(group_id))


def is_in_cd(group_id, cd_type):
    """
    功能：判断是否在复读cd中
    参数：{
        group_id    : QQ群号,
        cd_type     : 要查询的cd类型
    }
    返回：True/False
    """
    global r
    stat = r.get('in_{}_cd_{}'.format(cd_type, group_id))
    if stat == '1':
        return True
    else:
        return False


def update_cd(group_id, cd_type):
    """
    功能：更新cd（通过设置Redis key的过期时间实现）
    参数：{
        group_id    : QQ群号,
        cd_type     : 要设置的cd类型
    }
    返回：True/False
    """
    global r
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
    for item in sorted(data.items(), key=lambda d: d[1], reverse=True):
        tab.add_row([item[0], item[1]])
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


def update_database(table, g_name, value):
    """


    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute("SELECT CONTENT FROM {} WHERE NAME='{}'".format(table, g_name))
    if len(list(cursor)) > 0:
        conn_cursor.execute("UPDATE {t} SET CONTENT='{v}' WHERE NAME='{pqq}'".format(v=value, pqq=g_name, t=table))
        logging.debug("表 {} 中的 {} 被替换为: {}".format(table, g_name, value))
    else:
        conn_cursor.execute(
            "INSERT INTO '{t}' (NAME, CONTENT) VALUES ('{g_id}', '{g_val}')".format(t=table, g_id=g_name, g_val=value))
        logging.debug("表 {} 中的 {} 新增 : {}".format(table, g_name, value))
    conn.commit()
    conn.close()


def update_count(group_id, name):
    """


    """
    logging.info("[{}] {} COUNT + 1".format(group_id, name))
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute("SELECT CONTENT FROM COUNT WHERE NAME='{}'".format(group_id))
    data_list = list(cursor)
    if len(data_list) > 0:
        count_data = json.loads(data_list[0][0])
        this_count = count_data.get(name)
        if this_count:
            this_count += 1
        else:
            this_count = 1
        count_data[name] = this_count
        logging.info("[{}] {} COUNT : {}".format(group_id, name, this_count))
        update_database("COUNT", group_id, json.dumps(count_data, ensure_ascii=False))
    else:
        logging.info("[{}] COUNT 记录不存在，新建记录".format(group_id))
        count_data = {name: 1}
        update_database("COUNT", group_id, json.dumps(count_data, ensure_ascii=False))
    conn.commit()
    conn.close()


def rand_pic(key):
    """

    """
    global r
    if r.get(key):
        file_list = json.loads(r.get(key))
    else:
        file_list = []
    random.shuffle(file_list)
    # logging.info("{} => {}".format(key, file_list))
    random_file = random.choice(file_list)
    logging.info("Choose {}".format(random_file))
    return random_file


def get_count_dict(group_id):
    """

    """
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT CONTENT FROM COUNT WHERE NAME="{}"'.format(group_id))
    count_list = json.loads(list(cursor)[0][0])
    conn.close()
    return count_list


def init_keaipa_list():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT "CONTENT" FROM "KEAIPA" WHERE "NAME"="KEAI"')
    keai_list = json.loads(list(cursor)[0][0])
    r.set('keai_list', json.dumps(keai_list, ensure_ascii=False))
    cursor = conn_cursor.execute('SELECT "CONTENT" FROM "KEAIPA" WHERE "NAME"="PA"')
    pa_list = json.loads(list(cursor)[0][0])
    r.set('pa_list', json.dumps(pa_list, ensure_ascii=False))
    conn.close()


def string_similar(s1, s2):
    """

    """
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()


def match_lp(lp_name, keyword_list):
    """

    """
    simi_dict = {}
    for keys in keyword_list:  # 在字典中遍历查找
        for e in range(len(keyword_list[keys])):  # 遍历名称
            seed = string_similar(str(lp_name), keyword_list[keys][e])
            if seed > 0.6:
                logging.info("{} 最接近 : {} ,与 {} 最相似 ,相似度为 ：{}".format(lp_name, keys, keyword_list[keys][e], seed))
                simi_dict.update({keys: seed})

    if bool(simi_dict):
        return sorted(simi_dict, key=simi_dict.__getitem__, reverse=True)[0]
    else:
        return None


def mirai_group_message_handler(group_id, session_key, text, sender_permission, sender_id):
    """
    功能：群聊消息处理器
    参数：{
        group_id          : QQ群号,
        session_key       : sessionKey,
        text              : 消息的文本内容,
        sender_permission : 发消息的人的权限,
        sender_id         : 发消息的人的QQ号
    }
    返回：True/False
    """
    global r
    if r.get('at_moca_{}'.format(group_id)) == '1':
        if '说明' in text or 'help' in text or '帮助' in text:
            mirai_reply_text(group_id, session_key, '使用说明：https://wiki.bang-dream.tech/')
            logging.info("[{}] 请求使用说明".format(group_id))
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if '关键词' in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                logging.info("[{}] 请求关键词列表".format(group_id))
                json_data = json.loads(r.get('key_{}'.format(group_id)))
                create_dict_pic(json_data, str(group_id) + '_key', '关键词')
                mirai_reply_image(group_id, session_key, str(group_id) + '_key.png')
                update_cd(group_id, "replyHelpCD")
            else:
                logging.info("[{}] 关键词列表cd冷却中".format(group_id))
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if "统计次数" in text or "次数统计" in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                logging.info("[{}] 请求统计次数".format(group_id))
                json_data = get_count_dict(group_id)
                create_dict_pic(json_data, str(group_id) + '_count', '次数')  # 将json转换为图片
                mirai_reply_image(group_id, session_key, str(group_id) + "_count.png")  # 发送图片
                update_cd(group_id, "replyHelpCD")
            else:
                logging.info("[{}] 统计次数cd冷却中".format(group_id))
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if "爬" in text or "爪巴" in text:
            if not is_in_cd(group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.get('pa_list'))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                else:
                    logging.info("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca爬，但是cd冷却中".format(group_id))
            update_count(group_id, '爬')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if "可爱" in text or "老婆" in text or "lp" in text or "mua" in text:
            if not is_in_cd(group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.get('keai_list'))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                else:
                    logging.info("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca可爱，但是cd冷却中".format(group_id))
            update_count(group_id, '可爱')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

    else:
        group_keywords = json.loads(r.get('key_{}'.format(group_id)))
        quo_keywords = json.loads(r.get('quotation_dict'))
        if sender_permission == 'ADMINISTRATOR' or sender_permission == 'OWNER' or sender_id == 565379987:
            if text[0:6] == "设置图片cd":  # 设置图片cd
                try:
                    arg = str(text[6:len(text)])
                    to_set_cd = int(arg.rstrip("秒"))  # 获取参数
                    err_text = ''
                except:
                    logging.error("[{}] 设置图片cd 参数错误".format(group_id))
                    to_set_cd = 10
                    err_text = '参数有误，请检查格式，当前已重置为10秒\n'
                if to_set_cd < 5:  # 最低5秒
                    mirai_reply_text(group_id, session_key, "不要无限火力不要无限火力，最低5秒cd")
                else:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前图片cd：{}秒".format(err_text,
                                                           update_config(group_id, "replyCD", to_set_cd)))  # 回复新参数
                    logging.info("[{}] 设置图片cd {}秒".format(group_id, to_set_cd))
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

            if text[0:6] == "设置复读cd":  # 设置复读cd
                try:
                    arg = str(text[6:len(text)])
                    to_set_cd = int(arg.rstrip("秒"))  # 获取参数
                    err_text = ''
                except:
                    logging.error("[{}] 设置复读cd 参数错误".format(group_id))
                    to_set_cd = 300
                    err_text = '参数有误，请检查格式，当前已重置为300秒\n'
                if to_set_cd < 120:  # 最低120秒
                    mirai_reply_text(group_id, session_key, "错误：最低120秒cd")
                else:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前复读cd：{}秒".format(err_text,
                                                           update_config(group_id, "repeatCD", to_set_cd)))  # 回复新参数
                    logging.info("[{}] 设置复读cd {}秒".format(group_id, to_set_cd))
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

            if text[0:6] == "设置复读概率":  # 设置复读概率
                try:
                    arg = str(text[6:len(text)])
                    to_set_value = int(arg.rstrip("%"))  # 获取参数
                    err_text = ''
                except:
                    logging.error("[{}] 设置复读概率 参数错误".format(group_id))
                    to_set_value = 50
                    err_text = '参数有误，请检查格式，当前已重置为50%\n'
                if 0 <= to_set_value <= 100:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前复读概率：{}%".format(err_text, update_config(group_id, "repeatChance",
                                                                                   to_set_value)))  # 回复新参数
                    logging.info("[{}] 设置复读概率 {}%".format(group_id, to_set_value))
                else:
                    mirai_reply_text(group_id, session_key, "错误：概率为介于0~100之间的值")
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

            if text == "查看当前参数":  # 查看当前参数
                to_reply_text = ''  # 生成参数字符串
                to_reply_text += "当前复读概率：" + str(get_config(group_id, "repeatChance")) + "%\n"
                to_reply_text += "当前复读cd：" + str(get_config(group_id, "repeatCD")) + "秒\n"
                to_reply_text += "当前图片cd：" + str(get_config(group_id, "replyCD")) + "秒"
                mirai_reply_text(group_id, session_key, to_reply_text)  # 回复内容
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

            if text[0:5] == "添加关键词" or text[0:5] == "增加关键词":
                arg = text[5:len(text)].replace("，", ",").split(',')
                if not len(arg) == 2:
                    logging.error("[{}] 添加关键词 参数数量错误".format(group_id))
                else:
                    if not arg[0] in group_keywords:
                        mirai_reply_text(group_id, session_key, "未找到 {}，请检查名称是否正确".format(arg[0]))  # 回复内容
                    else:
                        if append_keyword(group_id, arg[0], arg[1]):
                            mirai_reply_text(group_id, session_key, "向 {} 中添加了关键词：{}".format(arg[0], arg[1]))  # 回复内容
                        else:
                            mirai_reply_text(group_id, session_key, "{} 中关键词：{} 已存在".format(arg[0], arg[1]))  # 回复内容
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

            if text[0:5] == "删除关键词":
                arg = text[5:len(text)].replace("，", ",").split(',')
                if not len(arg) == 2:
                    logging.error("[{}] 删除关键词 参数数量错误".format(group_id))
                else:
                    if not arg[0] in group_keywords:
                        mirai_reply_text(group_id, session_key, "未找到 {}，请检查名称是否正确".format(arg[0]))  # 回复内容
                    else:
                        if remove_keyword(group_id, arg[0], arg[1]):
                            mirai_reply_text(group_id, session_key, "删除了 {} 中的关键词：{}".format(arg[0], arg[1]))  # 回复内容
                        else:
                            mirai_reply_text(group_id, session_key, "{} 中未找到关键词：{}".format(arg[0], arg[1]))  # 回复内容
                r.set("do_not_repeat_{}".format(group_id), '1')
                return

        if "moca爬" in text or "moca爪巴" in text:
            if not is_in_cd(group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.get('pa_list'))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                else:
                    logging.info("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca爬，但是cd冷却中".format(group_id))
            update_count(group_id, '爬')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if "moca可爱" in text or "moca老婆" in text or "摩卡老婆" in text or "摩卡可爱" in text:
            if not is_in_cd(group_id, "replyCD"):
                if random_do(get_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.get('keai_list'))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                else:
                    logging.info("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.info("[{}] moca可爱，但是cd冷却中".format(group_id))
            update_count(group_id, '可爱')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if "来点wlp" in text or "来点lp" in text or "来点老婆" in text or "来点我老婆" in text:
            lp_name = fetch_lp(sender_id)
            if not is_in_cd(group_id, "replyCD") or sender_id == 565379987:
                if lp_name and lp_name in group_keywords:
                    pic_name = rand_pic(lp_name)
                    mirai_reply_image(group_id, session_key, path='pic\\' + lp_name + '\\' + pic_name)
                    update_count(group_id, lp_name)  # 更新统计次数
                else:
                    mirai_reply_text(group_id, session_key, 'az，似乎你还没有设置lp呢，用“wlp是xxx”来设置一个吧')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        if text[0:4] == "wlp是" or text[0:4] == "我老婆是" or text[0:4] == "我lp是":
            lp_name = text[4:len(text)].replace("？", "?")
            if lp_name == '?' or lp_name == '谁' or lp_name == '谁?':
                lp_name = fetch_lp(sender_id)
                if lp_name:
                    mirai_reply_text(group_id, session_key, '你设置的lp为: {}'.format(lp_name))
                else:
                    mirai_reply_text(group_id, session_key, 'az，没有找到nlp呢...')
            else:
                true_lp_name = match_lp(lp_name, group_keywords)
                if true_lp_name:
                    update_lp(sender_id, true_lp_name)
                    mirai_reply_text(group_id, session_key, '用户{}设置lp为: {}'.format(sender_id, true_lp_name))
                else:
                    mirai_reply_text(group_id, session_key, 'az，没有找到nlp呢...')
            r.set("do_not_repeat_{}".format(group_id), '1')
            return

        for keys in group_keywords:  # 在字典中遍历查找
            for e in range(len(group_keywords[keys])):  # 遍历名称
                if text == group_keywords[keys][e]:  # 若命中名称
                    if not is_in_cd(group_id, "replyCD") or sender_id == 565379987:  # 判断是否在回复图片的cd中
                        logging.info("[{}] 请求：{}".format(group_id, keys))
                        pic_name = rand_pic(keys)
                        mirai_reply_image(group_id, session_key, path='pic\\' + keys + '\\' + pic_name)
                        update_count(group_id, keys)  # 更新统计次数
                        update_cd(group_id, "replyCD")  # 更新cd
                    r.set("do_not_repeat_{}".format(group_id), '1')
                    return

        for keys in group_keywords:  # 在字典中遍历查找
            for e in range(len(group_keywords[keys])):  # 遍历名称
                if group_keywords[keys][e] in text:  # 若命中名称
                    if not is_in_cd(group_id, "replyCD") or sender_id == 565379987:  # 判断是否在回复图片的cd中
                        logging.info("[{}] 请求：{}".format(group_id, keys))
                        pic_name = rand_pic(keys)
                        mirai_reply_image(group_id, session_key, path='pic\\' + keys + '\\' + pic_name)
                        update_count(group_id, keys)  # 更新统计次数
                        update_cd(group_id, "replyCD")  # 更新cd
                    r.set("do_not_repeat_{}".format(group_id), '1')
                    return

        for index in quo_keywords:  # 在字典中遍历查找
            for keys in quo_keywords[index]["key"]:
                if keys in text:  # 若命中名称
                    if not is_in_cd(group_id, "replyCD") or sender_id == 565379987:  # 判断是否在回复图片的cd中
                        logging.info("[{}] 请求：{}".format(group_id, keys))
                        random_num = random.randint(0, len(quo_keywords[index]["quo"]) - 1)
                        mirai_reply_text(group_id, session_key, quo_keywords[index]["quo"][random_num])
                        # update_count(group_id, keys)  # 更新统计次数
                        update_cd(group_id, "replyCD")  # 更新cd
                    r.set("do_not_repeat_{}".format(group_id), '1')
                    return


def mirai_private_message_handler(group_id, session_key, sender_id, message_id, message_time, message_chain):
    texts = ""
    for n in range(len(message_chain)):
        if message_chain[n]["type"] == "Plain":
            texts += message_chain[n]["text"]
    if group_id == 0:  # 好友消息
        if texts[0:4] == '提交图片':
            # config_data = text[4:len(texts)]
            # if not config_data == '':
            #     mirai_reply_text(sender_id, session_key, "请求提交图片：{}".format(config_data), friend=True)
            # else:
            #     mirai_reply_text(sender_id, session_key, "参数错误", friend=True)
            pass
        else:
            group_keywords = json.loads(r.get('key_0'))
            for keys in group_keywords:  # 在字典中遍历查找
                for e in range(len(group_keywords[keys])):  # 遍历名称
                    if texts == group_keywords[keys][e]:  # 若命中名称
                        logging.info("[{}] [FRIEND] 请求：{}".format(group_id, keys))
                        pic_name = rand_pic(keys)
                        mirai_reply_image(sender_id, session_key, path='pic\\' + keys + '\\' + pic_name, friend=True)
                        update_count(0, keys)  # 更新统计次数
                        return
    else:  # 临时消息
        group_keywords = json.loads(r.get('key_{}'.format(group_id)))
        for keys in group_keywords:  # 在字典中遍历查找
            for e in range(len(group_keywords[keys])):  # 遍历名称
                if texts == group_keywords[keys][e]:  # 若命中名称
                    logging.info("[{}] [{}] [TEMP] 请求：{}".format(group_id, sender_id, keys))
                    pic_name = rand_pic(keys)
                    mirai_reply_image(sender_id, session_key, path='pic\\' + keys + '\\' + pic_name, temp=True,
                                      temp_group_id=group_id)
                    update_count(group_id, keys)  # 更新统计次数
                    return
