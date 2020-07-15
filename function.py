import sqlite3
import json
import logging

def updateLp(c, qq, lp_name):
    '''
    功能：更新设置的lp
    参数：
        c       --- SQLite Connection Cursor
        qq      --- 要查询的QQ号
        lp_name --- 要增/改的名称
    返回：无
    '''
    cursor = c.execute('select * from lplist where qq="{userqq}"'.format(userqq=qq))

    if(not cursor.fetchall()):
        c.execute("INSERT INTO LPLIST (qq,lpname) VALUES ('{pqq}', '{plpname}' )".format(pqq=qq,plpname=lp_name))
        logging.info ("新增lp记录：用户{}设置lp为:{}".format(qq,lp_name))
    else:
        c.execute("UPDATE LPLIST SET lpname='{plp_name}' WHERE qq='{pqq}'".format(plp_name=lp_name,pqq=qq))
        logging.info ("修改lp记录：用户{}设置lp为:{}".format(qq,lp_name))


def fetchSetLp(c, qq):
    '''
    功能：获取设置的lp
    参数：
        c  --- SQLite Connection Cursor
        qq --- 要查询的QQ号
    返回：设置的lp名称
    '''
    cursor = c.execute('select lpname from lplist where qq="{userqq}"'.format(userqq=qq))
    for l in cursor.fetchall():
        if(l):
            return l[0]
