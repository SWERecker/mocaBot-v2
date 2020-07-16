import sqlite3
import os

conn = sqlite3.connect('mocabot.sqlite3')
print ("Opened database successfully")
group_list = []
group_files = os.listdir('config\\')
for files in group_files:
    group_list.append(files.split('.')[0])
print(group_list)

c = conn.cursor()
for group in group_list:
    c.execute('''CREATE TABLE config_{group_id}
       (ID             INTEGER PRIMARY KEY   AUTOINCREMENT,
       NAME            TEXT               NOT NULL,
       PARA            TEXT               NOT NULL);'''.format(group_id=group))
print ("Table created successfully")
conn.commit()
conn.close()
