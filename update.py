import json
import os
from mirai import *
from function import load_group_list
import time
import sqlite3
import config

session_key = mirai_init_auth_key()


def compare_change(group_id):
    latest_file_count = {}
    latest_group_count = {}
    result_text = str(time.strftime('%Y-%m-%d %H:%M',time.localtime(time.time()))) + " 图片数量变化\n"
    names_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\")
    for name in names_list:
        file_list = os.listdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\" + name + "\\")
        latest_file_count[name] = len(file_list)
    result_json = {}
    cursor = conn_cursor.execute("SELECT CONTENT FROM KEYWORDS WHERE NAME='{}'".format(group_id))
    data_list = list(cursor)
    group_keyword = json.loads(data_list[0][0])
    if not os.path.exists("cache"):
        os.makedirs("cache")
    if os.path.isfile("cache\\{}.cache".format(group_id)):
        with open("cache\\{}.cache".format(group_id), 'r', encoding='utf-8')as cache_file:
            cache_dict = json.load(cache_file)
        for name in group_keyword:
            latest_count = cache_dict.get(name)
            latest_group_count[name] = latest_file_count[name]

            if not latest_count:
                result_json[name] = "{}({})*新增\n".format(name, latest_file_count[name])
            else:
                delta = latest_file_count[name] - cache_dict[name]
                if not delta == 0:
                    if delta > 0:
                        result_json[name] = "{}(+{})\n".format(name, delta)
                    else:
                        result_json[name] = "{}({})\n".format(name, delta)

        if bool(result_json):
            for name, result in result_json.items():
                result_text += result
            print(result_json)

            mirai_reply_text(group_id, session_key, result_text)
        else:
            print("[{}] 统计没有变化".format(group_id))

        with open("cache\\{}.cache".format(group_id), 'w', encoding='utf-8')as cache_file:
            cache_file.write(json.dumps(latest_group_count, ensure_ascii=False))
    else:
        print("[{}] 缓存文件不存在，直接存储本次读取结果".format(group_id))
        for name in group_keyword:
            latest_group_count[name] = latest_file_count[name]
        with open("cache\\{}.cache".format(group_id), 'w', encoding='utf-8')as cache_file:
            cache_file.write(json.dumps(latest_group_count, ensure_ascii=False))


conn = sqlite3.connect('mocabot.sqlite3')
conn_cursor = conn.cursor()
g_list = load_group_list()
for g_id in g_list:
    compare_change(g_id)
conn.close()
