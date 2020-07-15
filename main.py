import sqlite3
from function import *
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='log.txt',
                    filemode='w')

conn = sqlite3.connect('mocabot.sqlite3')
conn_cursor = conn.cursor()


updateLp(conn_cursor, 565379987, "伊藤彩沙")
print(fetchSetLp(conn_cursor, 565379987))

conn.close()
