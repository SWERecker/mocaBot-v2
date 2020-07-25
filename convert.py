import sqlite3
import redis
import json


pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)


def import_lplist():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT QQ, LPNAME FROM LPLIST')
    for k, v in cursor:
        r.hset("LPLIST", k, v)
    conn.close()


def import_keyword():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT NAME, CONTENT FROM KEYWORDS')
    for k, v in cursor:
        r.hset("KEYWORDS", k, v)
    conn.close()


def import_config():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT NAME, CONTENT FROM CONFIG')
    for k, v in cursor:
        r.hset("CONFIG", k, v)
    conn.close()


def import_quotation():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT KEYS, CONTENT FROM QUOTATION')
    i = 0
    for k, v in cursor:
        r.hset("QUOTATION", str(i), v)
        i += 1
    conn.close()


def import_count():
    conn = sqlite3.connect('mocabot.sqlite3')
    conn_cursor = conn.cursor()
    cursor = conn_cursor.execute('SELECT NAME, CONTENT FROM COUNT')
    for k, v in cursor:
        r.hset("COUNT", k, v)
    conn.close()


def update_keaipa_chance():
    config = r.hgetall("CONFIG")
    for group in config:
        group_config = json.loads(config[group])
        group_config["keaiPaCD"] = 60
        r.hset("CONFIG", group, json.dumps(group_config, ensure_ascii=False))


# import_count()
# import_quotation()
# import_config()
# import_lplist()
# import_keyword()
update_keaipa_chance()