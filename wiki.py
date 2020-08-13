import json
import config
import time
import os
import redis

file_path = 'C:\\wwwroot\\mocabot.cn'
new_data = {'updateTime': str(time.strftime('%Y-%m-%d %H:%M',time.localtime(time.time())))}

names_list = os.listdir(config.mirai_path + '\\plugins\\MiraiAPIHTTP\\images\\pic\\')
file_count_list = []
for name in names_list:
    if os.path.isdir(config.mirai_path + "\\plugins\\MiraiAPIHTTP\\images\\pic\\" + name):
        files_list = os.listdir(config.mirai_path + '\\plugins\\MiraiAPIHTTP\\images\\pic\\' + name + '\\')
        files_count = len(files_list)
        file_count_list.append(files_count)
new_data['peopleCount'] = len(names_list)
new_data['picCount'] = sum(file_count_list)

pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)
count = 0
g_count = {}
data = r.hgetall("COUNT")
for d in data:
    dict_data = json.loads(data[d])
    g_count[str(d)] = 0
    for n in dict_data:
        g_count[str(d)] += dict_data[n]
        count += dict_data[n]

new_data['rCount'] = count

with open(file_path + '\\data.json', 'w', encoding='utf-8')as data_file:
    data_file.write(json.dumps(new_data, ensure_ascii=False))
with open(file_path + '\\data_history.json', 'a', encoding='utf-8')as data_file:
    data_file.write(json.dumps(new_data, ensure_ascii=False))
    data_file.write("\n")
