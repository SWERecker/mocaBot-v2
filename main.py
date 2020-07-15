import sqlite3
from function import *
from mirai import *
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='log.txt',
                    filemode='a')
#
#conn = sqlite3.connect('mocabot.sqlite3')
#conn_cursor = conn.cursor()
#
#
#updateLp(conn_cursor, 565379987, "伊藤彩沙")
#print(fetchSetLp(conn_cursor, 565379987))
#
#conn.close()

session_key = mirai_init_auth_key()

print(session_key)
r_msg = mirai_reply_text(565379987, session_key, '23333', True)
if(r_msg[0] == 0):
    logging.info("success code:" + str(r_msg[0]) + "id=" + str(r_msg[1]))
else:
    logging.info("error code:" + str(r_msg[0]) + "id=" + str(r_msg[1]))

#mirai_reply_image(565379987, session_key, '116.jpg','',True)