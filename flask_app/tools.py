#import MySQLdb
import random
import json
import smtplib

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
