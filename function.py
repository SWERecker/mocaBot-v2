import json
import logging
import random
import redis
from mirai import *
from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont
import difflib
import os
import traceback

pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)
cache_pool = redis.ConnectionPool(host='localhost', port=6379, db=1, decode_responses=True)
rc = redis.Redis(connection_pool=cache_pool)
string = '/\:*<>|"'
url = 'http://120.79.166.168:8088/random_song'
dictionary = {
    'band': {
        'ro': 'Roselia',
        'ppp': 'Poppin‘Party',
        'pp': 'Pastel*Palettes',
        'ag': 'Afterglow',
        'hhw': 'Hello, Happy World',
        'ras': 'RAISE A SUILEN',
        'mo': 'Morfonica',
        'rimi': '牛込りみ',
        'saaya': '山吹沙綾',
        'arisa': '市ヶ谷有咲',
        'otae': 'GBP！スペシャルバンド',
        'ayaxmocaxlisaxkanonxtsugu': '彩×モカ×リサ×花音×つぐみ',
        'pppxykn': 'Poppin‘Party×友希那',
        'ksmxranxayaxyknxkkr': '香澄×蘭×彩×友希那×こころ',
        'hhwxranxaya': 'ハロハピ×蘭×彩',
        'roxran': 'Roselia×蘭',
        'agxkkr': 'Afterglow×こころ',
        'pppxgg': 'Poppin‘Party × Glitter*Green',
    },
    'type': {
        'ex': 'EXPERT',
        'sp': 'SPECIAL',
        'full': 'FULL'
    }
}


def update_lp(qq, lp_name):
    """
    功能：更新设置的lp
    参数：{
        qq      : 要查询的QQ号,
        lp_name : 要增/改的名称
    }
    返回：无
    """
    r.hset("LPLIST", qq, lp_name)
    logging.info("修改lp记录：用户{}设置lp为:{}".format(qq, lp_name))


def fetch_lp(qq):
    """
    功能：获取设置的lp
    参数：{
        qq : 要查询的QQ号
    }
    返回：设置的lp名称
    """
    return r.hget("LPLIST", qq)


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
        if data[n].get("type") == 'Plain':
            data[n]["text"].replace("'", "\'")
    data.append({'group_id': group_id})
    return data


def init_keyword_list(group_id):
    """
    功能：若不存在新建默认关键词列表
    参数：{
        group_id : QQ群号
    }
    返回：True,False(已存在)
    """
    if not r.hexists("KEYWORDS", group_id):
        r.hset("KEYWORDS", group_id, r.hget("KEYWORDS", "key_template"))
        logging.info("[{}] 初始化关键词列表".format(group_id))
        return True
    else:
        return False


def init_config(group_id):
    """
    功能：若不存在初始化参数
    参数：{
        group_id : QQ群号
    }
    返回：True,False(已存在)
    """
    if not r.hexists("CONFIG", group_id):
        r.hset("CONFIG", group_id, r.hget("CONFIG", "config_template"))
        return True
    else:
        return False


def load_group_list():
    """
    功能：从group.list文件加载群白名单到Redis数据库
    参数：{}
    返回：True
    """
    if os.path.isfile('group.list'):
        with open('group.list', 'r', encoding='utf-8')as group_list_file:
            for qq in group_list_file.readlines():
                rc.sadd("GROUPS", qq.strip('\n'))
    return True


def fetch_group_list():
    """
    功能：获取群列表
    参数：{}
    返回：群列表(集合)
    """
    return rc.smembers("GROUPS")


def init_files_list():
    """
    功能：读取文件列表缓存至Redis数据库
    参数：{}
    返回：True
    """
    names_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\")
    for name in names_list:
        file_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\" + name + "\\")
        rc.hset("FILES", name, json.dumps(file_list, ensure_ascii=False))
        logging.debug("saving {} to redis, data : {}".format(name, file_list))
    logging.info('重建图片索引完成')
    rc.set('file_list_init', '1', ex=600)
    return True


def fetch_config(group_id, arg):
    """
    功能：从Redis数据库中查询某参数
    参数：{
        group_id : QQ群号,
        arg      : 参数名称
    }
    返回：参数值
    """
    if not r.hexists("CONFIG", group_id):
        r.hset("CONFIG", group_id, r.hget("CONFIG", "config_template"))
        logging.info("[{}] 初始化参数".format(group_id))
    config_json = r.hget("CONFIG", group_id)
    config_data = json.loads(config_json)
    logging.debug("[{}] 获取CONFIG {} = {}".format(group_id, arg, config_data.get(arg)))
    return config_data.get(arg)


def update_config(group_id, arg, value):
    """
    功能：向Redis中更新某参数
    参数：{
        group_id : QQ群号,
        arg      : 参数名称,
        value    : 参数值
    }
    返回：新参数值
    """
    config_json = r.hget("CONFIG", group_id)
    config_data = json.loads(config_json)
    config_data[arg] = value
    r.hset("CONFIG", group_id, json.dumps(config_data, ensure_ascii=False))
    logging.debug("[{}] 设置CONFIG {} = {}".format(group_id, arg, value))
    return config_data.get(arg)


def append_keyword(group_id, key, value):
    """
    功能：添加关键词
    参数：{
        group_id : QQ群号,
        key      : 名称,
        value    : 关键词
    }
    返回：成功True，失败False，日志记录
    """
    group_keywords = json.loads(r.hget('KEYWORDS', group_id))
    if not group_keywords.get(key):
        logging.warning("[{}] 名称 {} 不存在".format(group_id, key))
        return False
    if value in group_keywords[key]:
        logging.warning("[{}] 向 {} 中添加重复关键词 {}".format(group_id, key, value))
        return False
    else:
        group_keywords[key].append(value)
        r.hset('KEYWORDS', group_id, json.dumps(group_keywords, ensure_ascii=False))
        logging.info("[{}] 向 {} 中添加关键词 {}".format(group_id, key, value))
        return True


def remove_keyword(group_id, key, value):
    """
    功能：删除关键词
    参数：{
        group_id : QQ群号,
        key      : 名称,
        value    : 关键词
    }
    返回：成功True，失败False，日志记录
    """
    group_keywords = json.loads(r.hget('KEYWORDS', group_id))
    if not group_keywords.get(key):
        logging.warning("[{}] 名称 {} 不存在".format(group_id, key))
        return False
    if value in group_keywords.get(key):
        group_keywords[key].remove(value)
        r.hset('KEYWORDS', group_id, json.dumps(group_keywords, ensure_ascii=False))
        logging.info("[{}] 删除 {} 中的关键词 {}".format(group_id, key, value))
        return True
    else:
        logging.warning("[{}] {} 中不存在关键词 {}".format(group_id, key, value))
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
    # null = None
    # 缓存消息 ===
    if not rc.hexists(group_id, "m_count"):
        rc.hset(group_id, "m_count", '0')
        rc.hset(group_id, "m_last_repeat", 'content')

    m_count = rc.hget(group_id, "m_count")
    processed_message_chain = fetch_processed_message_chain(group_id, message)
    json_processed_message_chain = json.dumps(processed_message_chain, ensure_ascii=False)
    if m_count == '0':
        rc.hset(group_id, "m_cache_0", json_processed_message_chain)
        rc.hset(group_id, "m_count", '1')  # 消息计数+1
    if m_count == '1':
        rc.hset(group_id, "m_cache_1", json_processed_message_chain)
        rc.hset(group_id, "m_count", '2')
    if m_count == '2':
        rc.hset(group_id, "m_cache_0", rc.hget(group_id, "m_cache_1"))
        rc.hset(group_id, "m_cache_1", json_processed_message_chain)
    # 缓存消息 ===

    m_cache_0 = rc.hget(group_id, "m_cache_0")
    m_cache_1 = rc.hget(group_id, "m_cache_1")

    if not rc.hget(group_id, "m_last_repeat") == json_processed_message_chain:
        if m_cache_0 == m_cache_1 and rc.hget(group_id, "do_not_repeat") == '0':
            if not is_in_cd(group_id, "repeatCD"):
                if random_do(fetch_config(group_id, "repeatChance")):
                    logging.debug("[{}] 命中复读条件且不在cd中且命中概率，开始复读".format(group_id))
                    del processed_message_chain[len(processed_message_chain) - 1]
                    mirai_reply_message_chain(group_id, session_key, processed_message_chain)
                    update_cd(group_id, "repeatCD")
                    rc.hset(group_id, "m_last_repeat", json_processed_message_chain)
                else:
                    logging.debug("[{}] 未命中复读概率".format(group_id))
            else:
                logging.debug("[{}] 复读cd冷却中".format(group_id))


def is_in_cd(group_id, cd_type):
    """
    功能：判断是否在cd中
    参数：{
        group_id    : QQ群号,
        cd_type     : 要查询的cd类型
    }
    返回：True/False
    """
    stat = rc.get('in_{}_cd_{}'.format(cd_type, group_id))
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
    返回：True
    """
    group_cd = fetch_config(group_id, cd_type)
    rc.set('in_{}_cd_{}'.format(cd_type, group_id), '1', ex=int(group_cd))
    return True


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
            logging.debug("pasted:y, {}".format(pos_y))
    if bg_x < img_x:
        pos_x = 0
        pos_y = 0
        while pos_y < img_y:
            while pos_x < img_x:
                im_new.paste(img, (pos_x, pos_y))
                pos_x += bg_x
                logging.debug("pasted:x,y {},{}".format(pos_x, pos_y))
            pos_x = 0
            pos_y += bg_y
    draw.multiline_text((space, space), tab_info, fill=(0, 0, 0), font=font)
    im_new.save(new_img_file, "png")
    del draw


def update_count(group_id, name):
    """
    功能：更新次数（+1）
    参数：{
        group_id : QQ群号,
        name     : 要+1的名称
    }
    返回：True
    """
    if not r.hexists("COUNT", group_id):
        r.hset("COUNT", group_id, "{}")
    count_list = json.loads(r.hget("COUNT", group_id))
    if not count_list.get(name):
        count_list[name] = 1
        logging.info("[{}] SET {} COUNT = 1".format(group_id, name))
    else:
        count_list[name] += 1
        logging.info("[{}] {} COUNT + 1".format(group_id, name))
    r.hset("COUNT", group_id, json.dumps(count_list, ensure_ascii=False))
    return True


def fetch_count_list(group_id):
    """
    功能：获取图片数量列表
    参数：{
        group_id : 群号
    }
    返回：图片文件名（名称不存在时返回False）
    """
    group_keyword = json.loads(r.hget("KEYWORDS", group_id))
    file_list = rc.hgetall("FILES")
    result_list = {}
    for name in group_keyword:
        if name in file_list:
            json_data = json.loads(file_list[name])
            result_list[name] = len(json_data)
    return result_list


def rand_pic(name):
    """
    功能：从图片库中随机抽取一张
    参数：{
        name : 名称
    }
    返回：图片文件名（名称不存在时返回False）
    """
    if not rc.hexists("FILES", name):
        return None
    file_list = json.loads(rc.hget("FILES", name))
    random.shuffle(file_list)
    random_file = random.choice(file_list)
    logging.info("Choose {}".format(random_file))
    return random_file


def init_keaipa_list():
    pass


def match_lp(lp_name, keyword_list):
    """
    功能：匹配最接近的lp
    参数：{
        lp_name      : 名称,
        keyword_list : 群的关键词
    }
    返回：图片文件名（名称不存在时返回False）
    """
    simi_dict = {}
    for keys in keyword_list:  # 在字典中遍历查找
        for e in range(len(keyword_list[keys])):  # 遍历名称
            seed = difflib.SequenceMatcher(None, str(lp_name), keyword_list[keys][e]).quick_ratio()
            if seed > 0.6:
                logging.debug("{} 最接近 : {} ,与 {} 最相似 ,相似度为 ：{}".format(lp_name, keys, keyword_list[keys][e], seed))
                simi_dict.update({keys: seed})
    if bool(simi_dict):
        return sorted(simi_dict, key=simi_dict.__getitem__, reverse=True)[0]
    else:
        return None


# noinspection PyBroadException
def upload_photo(group_id, session_key, text, message_chain):
    if text[0:4] == '提交图片':
        error_flag = False
        if len(text) > 4:
            logging.info("[{}] 提交图片".format(group_id))
            data_list = []
            category = text[4:len(text)]
            for n in category:
                if n in string:
                    mirai_reply_text(group_id, session_key, '名称中含有非法字符，请重试')
                    return
            for n in range(len(message_chain)):
                if message_chain[n].get("type") == "Image":
                    cache_data = {
                        "url": message_chain[n].get("url"),
                        "file_name": message_chain[n].get("imageId").split(".")[0].replace("{", "").replace("}", "")
                    }
                    logging.info("[{}] 收到：{}".format(group_id, cache_data))
                    data_list.append(cache_data)
            if not bool(data_list):
                mirai_reply_text(group_id, session_key, '没有图片')
                return

            # upload/{群号}/月/日/{imageId}
            month = time.strftime("%m")
            day = time.strftime("%d")
            if not os.path.exists("upload\\{}\\{}\\{}\\{}".format(group_id, month, day, category)):
                os.makedirs("upload\\{}\\{}\\{}\\{}".format(group_id, month, day, category))

            for file_index in range(len(data_list)):
                try:
                    res = requests.get(data_list[file_index]["url"])
                    content_type = res.headers.get("Content-Type")
                    file_type = content_type.split('/')[1]
                    logging.info("saving {}.{}".format(data_list[file_index]["file_name"], file_type))
                    logging.info("保存路径：upload\\{}\\{}\\{}\\{}\\{}.{}".format(
                                 group_id, month, day, category, data_list[file_index]["file_name"], file_type))

                    with open("upload\\{}\\{}\\{}\\{}\\{}.{}".format(
                            group_id, month, day, category, data_list[file_index]["file_name"], file_type
                            ), "wb") as image_file:
                        image_file.write(res.content)
                except:
                    logging.error(str(traceback.format_exc()))
                    error_flag = True

            if error_flag:
                mirai_reply_text(group_id, session_key, '提交失败')
            else:
                file_count = len(data_list)
                mirai_reply_text(group_id, session_key, '成功，收到{}张图片'.format(file_count))
        else:
            mirai_reply_text(group_id, session_key, '参数错误')

        rc.hset(group_id, "do_not_repeat", '1')


def rdm_song(text):
    l_text = text.lower().replace("；", ";").replace("，", ",").replace(" ", "")
    para = {}
    paras = l_text[4:].split(';')
    for t in paras:
        if t[:2] == '乐队':
            para["band"] = t[2:].split(',')
        if t[:2] == '难度':
            para["diff"] = t[2:].split(',')
        if t[:2] == '类型':
            para["type"] = t[2:].split(',')
        if t[:2] == '比赛':
            para["c_type"] = True
    print(para)
    r = requests.post(url, json=para)
    result = json.loads(r.text)
    result_name = result.get('name')
    result_band = dictionary['band'].get(result.get('band'))
    result_type = dictionary['type'].get(result.get('type'))
    result_diff = result.get('diff')
    if result.get("msg") == "error":
        if result.get("type") == "band":
            return "错误: 乐队条件错误\n支持: ppp, ro, ag, hhw, pp, other"
        elif result.get("type") == "type":
            return "错误: 歌曲类型条件错误\n支持：ex, sp, full"
        elif result.get("type") == "diff":
            return "错误: 难度条件错误\n支持：24~28"
        elif result.get("type") == "result":
            return "错误: 该条件下无歌曲可以选择"
        else:
            return "错误：{}".format(result.get("type"))
    return "选歌结果：\n{} — {}\n{} {}".format(result_name, result_band, result_type, result_diff)
    

# noinspection PyBroadException
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
    返回：
    """
    if rc.hget(group_id, 'at_moca'.format(group_id)) == '1':
        if '说明' in text or 'help' in text or '帮助' in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                mirai_reply_text(group_id, session_key, '使用说明：https://wiki.bang-dream.tech/')
                logging.info("[{}] 请求使用说明".format(group_id))
                rc.hset(group_id, "do_not_repeat", '1')
                update_cd(group_id, "replyHelpCD")
            return

        if '关键词' in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                logging.info("[{}] 请求关键词列表".format(group_id))
                json_data = json.loads(r.hget("KEYWORDS", group_id))
                create_dict_pic(json_data, str(group_id) + '_key', '关键词')
                mirai_reply_image(group_id, session_key, str(group_id) + '_key.png')
                update_cd(group_id, "replyHelpCD")
            else:
                logging.debug("[{}] 关键词列表cd冷却中".format(group_id))
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "统计次数" in text or "次数统计" in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                logging.info("[{}] 请求统计次数".format(group_id))
                json_data = json.loads(r.hget("COUNT", group_id))
                create_dict_pic(json_data, str(group_id) + '_count', '次数')  # 将json转换为图片
                mirai_reply_image(group_id, session_key, str(group_id) + "_count.png")  # 发送图片
                update_cd(group_id, "replyHelpCD")
            else:
                logging.debug("[{}] 统计次数cd冷却中".format(group_id))
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "图片数量" in text:
            if not is_in_cd(group_id, "replyHelpCD"):
                logging.info("[{}] 请求统计图片数量".format(group_id))
                json_data = fetch_count_list(group_id)
                create_dict_pic(json_data, str(group_id) + '_piccount', '图片数量')  # 将json转换为图片
                mirai_reply_image(group_id, session_key, str(group_id) + "_piccount.png")  # 发送图片
                update_cd(group_id, "replyHelpCD")
            else:
                logging.debug("[{}] 统计次数cd冷却中".format(group_id))
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "爬" in text or "爪巴" in text:
            if not is_in_cd(group_id, "keaiPaCD"):
                if random_do(fetch_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.hget("KEAIPA", "PA"))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                    update_cd(group_id, "keaiPaCD")
                else:
                    logging.debug("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.debug("[{}] moca爬，但是cd冷却中".format(group_id))
            update_count(group_id, '爬')
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "可爱" in text or "老婆" in text or "lp" in text or "mua" in text:
            if not is_in_cd(group_id, "keaiPaCD"):
                if random_do(fetch_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.hget("KEAIPA", "KEAI"))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                    update_cd(group_id, "keaiPaCD")
                else:
                    logging.debug("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.debug("[{}] moca可爱，但是cd冷却中".format(group_id))
            update_count(group_id, '可爱')
            rc.hset(group_id, "do_not_repeat", '1')
            return
    else:
        init_keyword_list(group_id)
        group_keywords = json.loads(r.hget("KEYWORDS", group_id))
        quo_data = r.hgetall('QUOTATION_LIST')
        for name in quo_data:
            quo_list = quo_data[name].split(',')
            quo_data[name] = []
            for key in quo_list:
                quo_data[name].append(key)

        if sender_permission == 'ADMINISTRATOR' or sender_permission == 'OWNER' or sender_id == config.superman:
            if text[0:6] == "设置图片cd":  # 设置图片cd
                try:
                    arg = str(text[6:len(text)])
                    to_set_cd = int(arg.rstrip("秒"))  # 获取参数
                    err_text = ''
                except:
                    logging.warning("[{}] 设置图片cd 参数错误".format(group_id))
                    to_set_cd = 10
                    err_text = '参数有误，请检查格式，当前已重置为10秒\n'
                if to_set_cd < 5:  # 最低5秒
                    mirai_reply_text(group_id, session_key, "不要无限火力不要无限火力，最低5秒cd")
                else:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前图片cd：{}秒".format(err_text,
                                                           update_config(group_id, "replyCD", to_set_cd)))  # 回复新参数
                    logging.info("[{}] 设置图片cd {}秒".format(group_id, to_set_cd))
                rc.hset(group_id, "do_not_repeat", '1')
                return

            if text[0:6] == "设置复读cd":  # 设置复读cd
                try:
                    arg = str(text[6:len(text)])
                    to_set_cd = int(arg.rstrip("秒"))  # 获取参数
                    err_text = ''
                except:
                    logging.warning("[{}] 设置复读cd 参数错误".format(group_id))
                    to_set_cd = 300
                    err_text = '参数有误，请检查格式，当前已重置为300秒\n'
                if to_set_cd < 120:  # 最低120秒
                    mirai_reply_text(group_id, session_key, "错误：最低120秒cd")
                else:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前复读cd：{}秒".format(err_text,
                                                           update_config(group_id, "repeatCD", to_set_cd)))  # 回复新参数
                    logging.info("[{}] 设置复读cd {}秒".format(group_id, to_set_cd))
                rc.hset(group_id, "do_not_repeat", '1')
                return

            if text[0:6] == "设置复读概率":  # 设置复读概率
                try:
                    arg = str(text[6:len(text)])
                    to_set_value = int(arg.rstrip("%"))  # 获取参数
                    err_text = ''
                except:
                    logging.warning("[{}] 设置复读概率 参数错误".format(group_id))
                    to_set_value = 50
                    err_text = '参数有误，请检查格式，当前已重置为50%\n'
                if 0 <= to_set_value <= 100:
                    mirai_reply_text(group_id, session_key,
                                     "{}当前复读概率：{}%".format(err_text, update_config(group_id, "repeatChance",
                                                                                   to_set_value)))  # 回复新参数
                    logging.info("[{}] 设置复读概率 {}%".format(group_id, to_set_value))
                else:
                    mirai_reply_text(group_id, session_key, "错误：概率为介于0~100之间的值")
                rc.hset(group_id, "do_not_repeat", '1')
                return

            if text == "查看当前参数":  # 查看当前参数
                logging.info("[{}] 查看参数".format(group_id))
                to_reply_text = ''  # 生成参数字符串
                to_reply_text += "当前复读概率：" + str(fetch_config(group_id, "repeatChance")) + "%\n"
                to_reply_text += "当前复读cd：" + str(fetch_config(group_id, "repeatCD")) + "秒\n"
                to_reply_text += "当前图片cd：" + str(fetch_config(group_id, "replyCD")) + "秒"
                mirai_reply_text(group_id, session_key, to_reply_text)  # 回复内容
                rc.hset(group_id, "do_not_repeat", '1')
                return

            if text[0:5] == "添加关键词" or text[0:5] == "增加关键词":
                arg = text[5:len(text)].replace("，", ",").split(',')
                if not len(arg) == 2:
                    logging.warning("[{}] 添加关键词 参数数量错误".format(group_id))
                else:
                    if not arg[0] in group_keywords:
                        mirai_reply_text(group_id, session_key, "未找到 {}，请检查名称是否正确".format(arg[0]))  # 回复内容
                    else:
                        if append_keyword(group_id, arg[0], arg[1]):
                            mirai_reply_text(group_id, session_key, "向 {} 中添加了关键词：{}".format(arg[0], arg[1]))  # 回复内容
                        else:
                            mirai_reply_text(group_id, session_key, "{} 中关键词：{} 已存在".format(arg[0], arg[1]))  # 回复内容
                rc.hset(group_id, "do_not_repeat", '1')
                return

            if text[0:5] == "删除关键词":
                arg = text[5:len(text)].replace("，", ",").split(',')
                if not len(arg) == 2:
                    logging.warning("[{}] 删除关键词 参数数量错误".format(group_id))
                else:
                    if not arg[0] in group_keywords:
                        mirai_reply_text(group_id, session_key, "未找到 {}，请检查名称是否正确".format(arg[0]))  # 回复内容
                    else:
                        if remove_keyword(group_id, arg[0], arg[1]):
                            mirai_reply_text(group_id, session_key, "删除了 {} 中的关键词：{}".format(arg[0], arg[1]))  # 回复内容
                        else:
                            mirai_reply_text(group_id, session_key, "{} 中未找到关键词：{}".format(arg[0], arg[1]))  # 回复内容
                rc.hset(group_id, "do_not_repeat", '1')
                return

        if "moca爬" in text or "moca爪巴" in text:
            if not is_in_cd(group_id, "keaiPaCD"):
                if random_do(fetch_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca爬了".format(group_id))
                    pa_list = json.loads(r.hget("KEAIPA", "KEAI"))
                    mirai_reply_image(group_id, session_key, image_id=pa_list[random.randint(0, len(pa_list) - 1)])
                    update_cd(group_id, "keaiPaCD")
                else:
                    logging.debug("[{}] moca爬，但是没有命中概率".format(group_id))
            else:
                logging.debug("[{}] moca爬，但是cd冷却中".format(group_id))
            update_count(group_id, '爬')
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "moca可爱" in text or "moca老婆" in text or "摩卡老婆" in text or "摩卡可爱" in text:
            if not is_in_cd(group_id, "keaiPaCD"):
                if random_do(fetch_config(group_id, "keaiPaChance")):
                    logging.info("[{}] moca可爱".format(group_id))
                    keai_list = json.loads(r.hget("KEAIPA", "KEAI"))
                    mirai_reply_image(group_id, session_key, image_id=keai_list[random.randint(0, len(keai_list) - 1)])
                    update_cd(group_id, "keaiPaCD")
                else:
                    logging.debug("[{}] moca可爱，但是没有命中概率".format(group_id))
            else:
                logging.debug("[{}] moca可爱，但是cd冷却中".format(group_id))
            update_count(group_id, '可爱')
            rc.hset(group_id, "do_not_repeat", '1')
            return

        if "来点wlp" in text or "来点lp" in text or "来点老婆" in text or "来点我老婆" in text:
            lp_name = fetch_lp(sender_id)
            if not is_in_cd(group_id, "replyCD") or sender_id == config.superman:
                if lp_name and lp_name in group_keywords:
                    pic_name = rand_pic(lp_name)
                    mirai_reply_image(group_id, session_key, path='pic\\' + lp_name + '\\' + pic_name)
                    update_count(group_id, lp_name)  # 更新统计次数
                else:
                    mirai_reply_text(group_id, session_key, 'az，似乎你还没有设置lp呢，用“wlp是xxx”来设置一个吧')
            rc.hset(group_id, "do_not_repeat", '1')
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
            rc.hset(group_id, "do_not_repeat", '1')
            return

        for keys in group_keywords:  # 在字典中遍历查找
            for e in range(len(group_keywords[keys])):  # 遍历名称
                if text == group_keywords[keys][e]:  # 若命中名称
                    if not is_in_cd(group_id, "replyCD") or sender_id == config.superman:  # 判断是否在回复图片的cd中
                        logging.info("[{}] 请求：{}".format(group_id, keys))
                        pic_name = rand_pic(keys)
                        mirai_reply_image(group_id, session_key, path='pic\\' + keys + '\\' + pic_name)
                        update_count(group_id, keys)  # 更新统计次数
                        update_cd(group_id, "replyCD")  # 更新cd
                    rc.hset(group_id, "do_not_repeat", '1')
                    return

        for keys in group_keywords:  # 在字典中遍历查找
            for e in range(len(group_keywords[keys])):  # 遍历名称
                if group_keywords[keys][e] in text:  # 若命中名称
                    if not is_in_cd(group_id, "replyCD") or sender_id == config.superman:  # 判断是否在回复图片的cd中
                        logging.info("[{}] 请求：{}".format(group_id, keys))
                        pic_name = rand_pic(keys)
                        mirai_reply_image(group_id, session_key, path='pic\\' + keys + '\\' + pic_name)
                        update_count(group_id, keys)  # 更新统计次数
                        update_cd(group_id, "replyCD")  # 更新cd
                    rc.hset(group_id, "do_not_repeat", '1')
                    return

        for name in quo_data:
            for key in quo_data[name]:
                if key in text:
                    if not is_in_cd(group_id, "replyCD") or sender_id == config.superman:
                        logging.info("[{}] 请求：{}".format(group_id, name))
                        quo_words = r.hget("QUOTATION", name).split(',')
                        random_num = random.randint(0, len(quo_words) - 1)
                        mirai_reply_text(group_id, session_key, quo_words[random_num].strip())
                        update_count(group_id, name)  # 更新统计次数

                    rc.hset(group_id, "do_not_repeat", '1')
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
