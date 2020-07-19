import sqlite3
import json
import os

conn = sqlite3.connect('mocabot.sqlite3')
c = conn.cursor()
#
#
# # group_files = os.listdir('count\\')
# # for files in group_files:
# #     group_id = files.split('.')[0]
# #     print('inserting ',group_id)
# #     with open('count\\' + files,'r',encoding='utf-8')as group_file:
# #         json_data = json.loads(group_file.read())
# #
# #     json_str = json.dumps(json_data, ensure_ascii=False)
# #     print(json_str)
# #
#
#


with open('yulu.json','r',encoding='utf-8')as group_file:
    json_data = json.loads(group_file.read())
for p in json_data:
    keys = json_data[p]["keys"]
    quotations = json_data[p]["words"]
    c.execute('INSERT INTO QUOTATION (KEYS,CONTENT) VALUES ( "{group}", "{key}" );'.format(group=str(keys), key=str(quotations)))
conn.commit()
conn.close()