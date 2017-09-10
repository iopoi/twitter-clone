#import MySQLdb
import random
import json
import smtplib

import pymongo
from pymongo import MongoClient, IndexModel
import bson
from bson.objectid import ObjectId
from bson.json_util import dumps
from bson.json_util import loads

import logging as log

fromaddr = ''
username = ''
password = ''
server = smtplib.SMTP('smtp.gmail.com:587')


def connection():
    conn = MySQLdb.connect(host="localhost",
                           user = "root",
                           passwd = "mysqlpassword",
                           db = "mydb", charset='utf8')
    c = conn.cursor()

    return c, conn

def error_msg(msg):
    msg['status'] = 'error'
    return json.dumps(msg)


def success_msg(msg):
    msg['status'] = 'OK'
    return json.dumps(msg)

def randomString():
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.sample(possible, 16))

def sendemail(key, toaddrs):
    fromaddr = 'zhaoyu9610@gmail.com'
    username = 'zhaoyu9610@gmail.com'
    password = 'zhaoyu1009ZY@'
    msg = 'Key is: ' + key
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()


# Memcached methods

# TODO must to testing and error catching
def mem_login(mem, session, uid):
    mem.set(session, (True, uid))

def mem_logout(mem, session):
    mem.set(session, (False, None))

def mem_check_login(mem, session):
    is_login = mem.get(session)
    if is_login is None:
        return (None, None)
    return is_login

def check_login(login_coll, mem, session):
    check = dict()
    is_mem_login = mem_check_login(mem, session)
    log.debug('debug - tools - check login - info - is_mem_login:', is_mem_login)
    if is_mem_login[0] == True:
        docs = [{'uid': is_mem_login[1]}]
    elif is_mem_login[0] == False:
        return error_msg({'error': 'not logged in'})
    elif is_mem_login[0] is None:
        check['session'] = session
        docs = [doc for doc in login_coll.find(check)]
        if len(docs) != 1:
            log.debug('debug - additem - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': 'not logged in'})
    else:
        return error_msg({'error': 'additem server error'})
    
    return docs
    
    

