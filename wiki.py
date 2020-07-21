import sqlite3
import json
import config
import time
import os
file_path = 'C:\\wwwroot\\moca.swenetech.xyz'
new_data = {'updateTime': str(time.strftime('%Y-%m-%d %H:%M',time.localtime(time.time())))}

names_list = os.listdir(config.mirai_path + '\\plugins\\MiraiAPIHTTP\\images\\pic\\')
file_count_list = []
for names in names_list:
    files_list = os.listdir(config.mirai_path + '\\plugins\\MiraiAPIHTTP\\images\\pic\\' + names + '\\')
    files_count = len(files_list)
    file_count_list.append(files_count)
new_data['peopleCount'] = len(names_list)
new_data['picCount'] = sum(file_count_list)

conn = sqlite3.connect('mocabot.sqlite3')
conn_cursor = conn.cursor()
cursor = conn_cursor.execute('SELECT CONTENT FROM COUNT')
final_data = []
for g in list(cursor):
    for name in g:
        final_data.append(name)
# count_dict_list = json.loads(list(cursor)[0][0])
conn.close()
# return count_dict_list
count = 0
for group_data in range(len(final_data)):
    group_dict = json.loads(final_data[group_data])
    for people in group_dict:
        count += group_dict[people]

new_data['rCount'] = count

with open(file_path + '\\data.json','w',encoding='utf-8')as data_file:
    data_file.write(json.dumps(new_data, ensure_ascii=False))