import sqlite3
import json
import os

conn = sqlite3.connect('mocabot.sqlite3')
c = conn.cursor()


group_files = os.listdir('count\\')
for files in group_files:
    group_id = files.split('.')[0]
    print('inserting ',group_id)
    with open('count\\' + files,'r',encoding='utf-8')as group_file:
        json_data = json.loads(group_file.read())

    json_str = json.dumps(json_data, ensure_ascii=False)
    print(json_str)
    c.execute("INSERT INTO COUNT (NAME,CONTENT) VALUES ( '{group}', '{key}' );".format(group=group_id,key=str(json_str)))

conn.commit()
conn.close()
