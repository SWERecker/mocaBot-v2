import sqlite3
import json
import os

conn = sqlite3.connect('mocabot.sqlite3')
c = conn.cursor()


group_files = os.listdir('config\\')
for files in group_files:
    group_id = files.split('.')[0]
    print('inserting',group_id)
    with open('config\\' + files,'r',encoding='utf-8')as group_file:
        json_data = json.loads(group_file.read())
    for n in json_data:
        print('write ',n,',',json_data[n])
        c.execute('INSERT INTO config_{group} (NAME,PARA) VALUES ( "{name}", "{key_count}" );'.format(group=group_id,name=str(n),key_count=json_data[n]))

conn.commit()
conn.close()
