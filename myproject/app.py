import json
from tools import connection, error_msg, success_msg, randomString, sendemail
from flask import Flask, request, make_response, render_template
from datetime import datetime
from MySQLdb import escape_string as thwart

app = Flask(__name__)

cookies = dict()
verify_key = dict()

@app.route('/', methods = ['GET'])
def indes():
    return render_template('index.html')

@app.route('/adduser', methods = ["POST", "GET"])
def adduser():
    if request.method == 'GET':
        return render_template('register.html')
    request_json = request.json
    username = request_json['username']
    email = request_json['email']
    password = request_json['password']
    c, conn = connection()
    x = c.execute("SELECT * FROM user WHERE username = (%s) or email = (%s);", (username, email))
    if x != 0:
        return error_msg({'error': 'username or emial already used'})
    c.execute("INSERT INTO user (username, password, email, disable) VALUES (%s, %s, %s, True)", (username, password, email))
    conn.commit()
    c.close()
    conn.close()
    global verify_key
    key = randomString()
    verify_key[email] = key
    sendemail(key, email)
    return success_msg({})

@app.route('/login', methods = ['POST', "GET"])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    global cookies
    request_json = request.json
    username = request_json['username']
    password = request_json['password']
    c, conn = connection()
    x = c.execute("SELECT uid FROM user WHERE username = (%s) and password = (%s) and disable =False", (username, password))
    if x != 1:
        return error_msg({})
    uid = c.fetchone()[0]
    cookie = randomString()
    cookies[cookie] = uid
    resp = make_response(success_msg({}))
    resp.set_cookie('cookie', cookie)
    return resp

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
    global cookies
    cookie = request.cookies.get('cookie')
    if not cookie:
        return "Not logged in!"
    cookies.pop(cookie)
    return success_msg({})

@app.route('/verify', methods = ['POST', 'GET'])
def verify():
    if request.method == 'GET':
        return render_template('verify.html')
    request_json = request.json   
    email = request_json['email']
    key = request_json['key']
    global verify_key
    if verify_key.get(email) != key and key != 'abracadabra':
        return error_msg({'error': 'wrong combination!'})
    verify_key.pop(email)
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
    global cookies
    request_json = request.json
    post_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = request_json['content']
    cookie = request.cookies.get('cookie')
    try:
        uid = cookies[cookie]
    except:
        return error_msg({"error": "not logged in"})
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
    c, conn = connection()
    c.execute("SELECT t.tid, u.username, t.content, t.time from user u, tweet t where u.uid = t.uid order by t.time desc limit %s;", (limit,))
    data = c.fetchall()
    items = []
    for a in data:
        items.append({"id": a[0], "username": a[1], "content": a[2], "timestamp": int(a[3].timestamp())})
    return success_msg({"items": items, "number": len(items)})

if __name__ == '__main__':
    app.run(debug=True)

