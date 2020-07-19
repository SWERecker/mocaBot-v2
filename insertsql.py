import sqlite3
import json
import os

conn = sqlite3.connect('mocabot.sqlite3')
c = conn.cursor()


# group_files = os.listdir('count\\')
# for files in group_files:
#     group_id = files.split('.')[0]
#     print('updating ',group_id)
#     with open('count\\' + files,'r',encoding='utf-8')as group_file:
#         json_data = json.loads(group_file.read())
# 
#     json_str = json.dumps(json_data, ensure_ascii=False)
#     c.execute("UPDATE COUNT SET CONTENT='{key}' WHERE NAME={group};".format(group=str(group_id), key=json_str))


group_files = os.listdir('config\\')
for files in group_files:
    group_id = files.split('.')[0]
    print('updating ',group_id)
    with open('config\\' + files,'r',encoding='utf-8')as group_file:
        json_data = json.loads(group_file.read())

    json_str = json.dumps(json_data, ensure_ascii=False)
    c.execute("UPDATE CONFIG SET CONTENT='{key}' WHERE NAME={group};".format(group=str(group_id), key=json_str))
    
group_files = os.listdir('keywords\\')
for files in group_files:
    group_id = files.split('.')[0]
    print('updating ',group_id)
    with open('keywords\\' + files,'r',encoding='utf-8')as group_file:
        json_data = json.loads(group_file.read())

    json_str = json.dumps(json_data, ensure_ascii=False)
    c.execute("UPDATE KEYWORDS SET CONTENT='{key}' WHERE NAME={group};".format(group=str(group_id), key=json_str))
#

# with open('lpList.json','r',encoding='utf-8')as group_file:
#     json_data = json.loads(group_file.read())
# for p in json_data:
#     lpName = json_data[p]
#     c.execute("UPDATE LPLIST SET LPNAME='{key}' WHERE QQ={group};".format(group=str(p), key=lpName))
conn.commit()
conn.close()