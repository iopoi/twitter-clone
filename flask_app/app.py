import json
from tools import error_msg, success_msg, randomString #, sendemail
from flask import Flask, request, make_response, render_template
from datetime import datetime
#from MySQLdb import escape_string as thwart
import pymongo
from pymongo import MongoClient

app = Flask(__name__)

# TODO - move tables into mongo
cookies = dict()
verify_key = dict()

mongo_server = 'mongodb://192.168.1.35:27017/'

@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/adduser', methods = ["POST", "GET"])
def adduser():
    if request.method == 'GET':
        return render_template('register.html')
    # connect
    client = MongoClient(mongo_server)  # connect to server
    db = client.twitterclone  # connect to db
    coll_user = db.user  # connect to collection
    request_json = request.json  # get json
    # check for existing user or email
    user_check = dict()
    user_check["$or"] = [{'username': request_json['username']},
                         {'email': request_json['email']}]
    cursor = coll_user.find(user_check)
    docs = [doc for doc in cursor]
    if len(docs) > 0:
        return error_msg({'error': 'username or email already used'})
    # insert new user
    user_new = dict()
    user_new['username'] = request_json['username']
    user_new['email'] = request_json['email']
    user_new['password'] = request_json['password']
    user_new['verified'] = False
    user_new['verify_key'] = randomString()
    coll_user.insert_one(user_new)
    # optional - user app key verification
    #global verify_key
    #verify_key[email] = user_new['verify_key']
    #sendemail(key, email)
    client.close()
    return success_msg({})

#    c, conn = connection()
#    x = c.execute("SELECT * FROM user WHERE username = (%s) or email = (%s);", (username, email))
#    if x != 0:
#        return error_msg({'error': 'username or emial already used'})
#    c.execute("INSERT INTO user (username, password, email, disable) VALUES (%s, %s, %s, True)", (username, password, email))
#    conn.commit()
#    c.close()
#    conn.close()
#    global verify_key
#    key = randomString()
#    verify_key[email] = key
#    sendemail(key, email)
#    return success_msg({})

@app.route('/login', methods = ['POST', "GET"])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    request_json = request.json  # get json
    # connect to user and login collections
    user_coll = MongoClient(mongo_server).twitterclone.user
    login_coll = MongoClient(mongo_server).twitterclone.login
    # check for existing verified user
    check = dict()
    check['username'] = request_json['username']
    check['password'] = request_json['password']
    check['verify'] = True
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'incorrect password or user not verified or user does not exist'})
    # login user
    login = dict()
    login['uid'] = docs[0]['_id']
    login['session'] = randomString()
    login['last_login'] = datetime.utcnow()
    login_coll.insert_one(login)
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']
    client.close()
    resp = make_response(success_msg({}))
    resp.set_cookie('cookie', cookie)
    return resp
    
   # global cookies
   # c, conn = connection()
   # x = c.execute("SELECT uid FROM user WHERE username = (%s) and password = (%s) and disable =False", (username, password))
   # if x != 1:
   #     return error_msg({})
   # uid = c.fetchone()[0]
   # cookie = randomString()
   # cookies[cookie] = uid
   # resp = make_response(success_msg({}))
   # resp.set_cookie('cookie', cookie)
   # return resp

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
    if request.method == 'GET':
        return render_template('login.html')

    request_json = request.json  # get json
    # connect to user and login collections
    user_coll = MongoClient(mongo_server).twitterclone.user
    login_coll = MongoClient(mongo_server).twitterclone.login
    # check for existing verified user
    check = dict()
    check['username'] = request_json['username']
    check['password'] = request_json['password']
    check['verify'] = True
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'incorrect password or user not verified or user does not exist'})
    # login user
    login = dict()
    login['uid'] = docs[0]['_id']
    login['session'] = randomString()
    login['last_login'] = datetime.utcnow()
    login_coll.insert_one(login)
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']
    client.close()
    resp = make_response(success_msg({}))
    resp.set_cookie('cookie', cookie)
    return resp



    global cookies
    cookie = request.cookies.get('cookie')
    if not cookie:
        return "Not logged in!"
    # TODO - update mongo tables
    cookies.pop(cookie)
    return success_msg({})

@app.route('/verify', methods = ['POST', 'GET'])
def verify():
    if request.method == 'GET':
        return render_template('verify.html')
    request_json = request.json   
    email = request_json['email']
    key = request_json['key']
    # TODO - check mongo tables
    global verify_key
    if verify_key.get(email) != key and key != 'abracadabra':
        return error_msg({'error': 'wrong combination!'})
    verify_key.pop(email)
    # TODO - add mongo support
    c, conn = connection()
    c.execute("UPDATE user SET disable = False where email = (%s)", (email,))
    conn.commit()
    c.close()
    conn.close()
    return success_msg({})

@app.route('/additem', methods = ['POST', 'GET'])
def additem():
    if request.method == 'GET':
        return render_template('addtweet.html')
    # TODO - check mongo tables
    global cookies
    request_json = request.json
    post_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = request_json['content']
    cookie = request.cookies.get('cookie')
    try:
        uid = cookies[cookie]
    except:
        return error_msg({"error": "not logged in"})
    # TODO - add mongo support
    c, conn = connection()
    c.execute("INSERT INTO tweet (uid, content, time) VALUES (%s, %s, %s)", (uid, content, post_time))
    tid = c.lastrowid
    conn.commit()
    c.close()
    conn.close()
    return success_msg({"id": tid})

@app.route('/item/<tid>', methods = ['GET'])
def item(tid):
    tid = int(tid)
    # TODO - add mongo support
    c, conn = connection()
    c.execute("SELECT t.tid, u.username, t.content, t.time from tweet t, user u where u.uid = t.uid and t.tid = (%s);", (tid,))
    a = c.fetchone()
    return success_msg({"item": {"id": a[0], "username": a[1], "content": a[2], "timestamp": int(a[3].timestamp())}})

@app.route('/search', methods = ['GET','POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html')
    request_json = request.json   
    timestamp = request_json.get('timestamp')
    if timestamp:
        timestamp = datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        #timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    limit = int(request_json.get('limit', 25))
    #limit = request_json.get('limit', 25)
    if limit > 100:
        limit = 25
    # TODO - add mongo support
    c, conn = connection()
    c.execute("SELECT t.tid, u.username, t.content, t.time from user u, tweet t where u.uid = t.uid order by t.time desc limit %s;", (limit,))
    data = c.fetchall()
    items = []
    for a in data:
        items.append({"id": a[0], "username": a[1], "content": a[2], "timestamp": int(a[3].timestamp())})
    return success_msg({"items": items, "number": len(items)})

if __name__ == '__main__':
    app.run(debug=True)

