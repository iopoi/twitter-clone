import json
from tools import error_msg, success_msg, randomString #, sendemail
from flask import Flask, request, make_response, render_template
from datetime import datetime
import time, calendar
#from MySQLdb import escape_string as thwart
import pymongo
from pymongo import MongoClient
import bson
from bson.objectid import ObjectId
from bson.json_util import dumps
from bson.json_util import loads


app = Flask(__name__)

# TODO - move tables into mongo
#cookies = dict()

mongo_server = 'mongodb://192.168.1.35:27017/'

@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/adduser', methods = ["POST", "GET"])
def adduser():
    if request.method == 'GET':
        return render_template('register.html')

    request_json = request.json  # get json
    # connect to user collection
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    # check for existing verified user
    check = dict()
    check["$or"] = [{'username': request_json['username']},
                         {'email': request_json['email']}]
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) > 0:
        return error_msg({'error': 'username or email already used'})
    # insert new user
    user = dict()
    user['username'] = request_json['username']
    user['email'] = request_json['email']
    user['password'] = request_json['password']
    user['verified'] = False
    user['verify_key'] = randomString()
    result = user_coll.insert_one(user)
    #sendemail(key, email)
    mc.close()
    return success_msg({})

    # # connect
    # client = MongoClient(mongo_server)  # connect to server
    # db = client.twitterclone  # connect to db
    # coll_user = db.user  # connect to collection
    # request_json = request.json  # get json
    # # check for existing user or email
    # user_check = dict()
    # user_check["$or"] = [{'username': request_json['username']},
    #                      {'email': request_json['email']}]
    # cursor = coll_user.find(user_check)
    # docs = [doc for doc in cursor]
    # if len(docs) > 0:
    #     return error_msg({'error': 'username or email already used'})
    # # insert new user
    # user_new = dict()
    # user_new['username'] = request_json['username']
    # user_new['email'] = request_json['email']
    # user_new['password'] = request_json['password']
    # user_new['verified'] = False
    # user_new['verify_key'] = randomString()
    # coll_user.insert_one(user_new)
    # # optional - user app key verification
    # #global verify_key
    # #verify_key[email] = user_new['verify_key']
    # #sendemail(key, email)
    # client.close()
    # return success_msg({})

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
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    login_coll = mc.twitterclone.login
    # check for existing verified user
    check = dict()
    check['username'] = request_json['username']
    check['password'] = request_json['password']
    check['verified'] = True
    docs = [doc for doc in user_coll.find(check)]
    print('login - docs')  # debug
    print(docs)  #debug
    if len(docs) != 1:
        return error_msg({'error': 'incorrect password or user not verified or user does not exist'})
    # login user
    login = dict()
    login['uid'] = docs[0]['_id']
    login['session'] = randomString()
    login['last_login'] = calendar.timegm(time.gmtime())
    result = login_coll.insert_one(login)
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']
    mc.close()
    resp = make_response(success_msg({}))
    resp.set_cookie('cookie', login['session'])
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
        return render_template('logout.html')

    session = request.cookies.get('cookie')  # get session
    print(session)
    # connect to user and login collections
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    login_coll = mc.twitterclone.login
    # check for logged in user
    check = dict()
    check['session'] = session
    docs = [doc for doc in login_coll.find(check)]
    print(str(len(docs)) + str(docs))
    if len(docs) != 1:
        return error_msg({'error': 'not logged in'})
    # logs out user
    result = login_coll.delete_many(check)
    print('logout - ' + str(result))
    # optional - logout app cookies
    #global cookies
    #cookies.pop(cookie)
    mc.close()
    return success_msg({})

    # global cookies
    # cookie = request.cookies.get('cookie')
    # if not cookie:
    #     return "Not logged in!"
    # # TODO - update mongo tables
    # cookies.pop(cookie)
    # return success_msg({})

@app.route('/verify', methods = ['POST', 'GET'])
def verify():
    if request.method == 'GET':
        return render_template('verify.html')

    request_json = request.json  # get json
    # connect to user collection
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    # check for unverified email and matching key
    check = dict()
    check['email'] = request_json['email']
    check['verified'] = False
    if request_json['key'] != 'abracadabra':
        check['verify_key'] = request_json.get('key', 'abracadabra')
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'wrong key or email not found or user already verified'})
    # verifiy user
    Oid = docs[0]['_id']
    user = dict()
#    user['_id'] = docs[0]['_id']
    user['username'] = docs[0]['username']
    user['email'] = docs[0]['email']
    user['password'] = docs[0]['password']
    user['verified'] = True
    print(user)
    result = user_coll.replace_one({'_id': Oid}, user)
    mc.close()
    return success_msg({})

    # request_json = request.json   
    # email = request_json['email']
    # key = request_json['key']
    # # TODO - check mongo tables
    # global verify_key
    # if verify_key.get(email) != key and key != 'abracadabra':
    #     return error_msg({'error': 'wrong combination!'})
    # verify_key.pop(email)
    # # TODO - add mongo support
    # c, conn = connection()
    # c.execute("UPDATE user SET disable = False where email = (%s)", (email,))
    # conn.commit()
    # c.close()
    # conn.close()
    # return success_msg({})

@app.route('/additem', methods = ['POST', 'GET'])
def additem():
    if request.method == 'GET':
        return render_template('addtweet.html')

    request_json = request.json  # get json
    session = request.cookies.get('cookie')  # get session
    # connect to login and tweet collections
    mc = MongoClient(mongo_server)
    login_coll = mc.twitterclone.login
    tweet_coll = mc.twitterclone.tweet
    # check for session
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']
    check = dict()
    check['session'] = session
    docs = [doc for doc in login_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'not logged in'})
    # insert tweet
    tweet = dict()
    tweet['uid'] = docs[0]['uid']
    tweet['content'] = request_json['content']
    tweet['timestamp'] = calendar.timegm(time.gmtime())
    result = tweet_coll.insert_one(tweet)
    print('result')
    print(result)
    print(str(result))
    mc.close()
    other_response_fields = dict()
    #other_response_fields['id'] = dumps(result.inserted_id)
    other_response_fields['id'] = str(result.inserted_id)
    return success_msg(other_response_fields)

    # # TODO - check mongo tables
    # global cookies
    # request_json = request.json
    # post_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # content = request_json['content']
    # cookie = request.cookies.get('cookie')
    # try:
    #     uid = cookies[cookie]
    # except:
    #     return error_msg({"error": "not logged in"})
    # # TODO - add mongo support
    # c, conn = connection()
    # c.execute("INSERT INTO tweet (uid, content, time) VALUES (%s, %s, %s)", (uid, content, post_time))
    # tid = c.lastrowid
    # conn.commit()
    # c.close()
    # conn.close()
    # return success_msg({"id": tid})

@app.route('/item/<tid>', methods = ['GET', 'DELETE'])
def item(tid):
    print('got to item')
    tid = '{"$oid": "' + tid + '"}'
    if request.method == 'GET':
        print(tid)
        print(loads(tid))
        # connect to tweet and user collection
        mc = MongoClient(mongo_server)
        tweet_coll = mc.twitterclone.tweet
        user_coll = mc.twitterclone.user
        # check for tweet with tid
        check = dict()
        check['_id'] = loads(tid)
        docs = [doc for doc in tweet_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': 'incorrect tweet id'})
        # respond with tweet
        item_details = dict()
        item_details['id'] = str(docs[0]['_id'])
        item_details['content'] = docs[0]['content']
        item_details['timestamp'] = docs[0]['timestamp']
        # check for user of tweet
        check = dict()
        check['_id'] = docs[0]['uid']
        docs = [doc for doc in user_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': 'database issue'})
        mc.close()
        item_details['username'] = docs[0]['username']
        other_response_fields = dict()
        other_response_fields['item'] = item_details
        return success_msg(other_response_fields)

    elif request.method == 'DELETE':
        # connect to tweet collection
        mc = MongoClient(mongo_server)
        tweet_coll = mc.twitterclone.tweet
        # check for tweet with tid
        check = dict()
        check['_id'] = loads(tid)
        docs = [doc for doc in tweet_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': 'incorrect tweet id'})
        # delete tweet
        result = tweet_coll.delete_many(check)
        mc.close()
        other_response_fields = dict()
        return success_msg(other_response_fields)

    return 405

    # tid = int(tid)
    # # TODO - add mongo support
    # c, conn = connection()
    # c.execute("SELECT t.tid, u.username, t.content, t.time from tweet t, user u where u.uid = t.uid and t.tid = (%s);", (tid,))
    # a = c.fetchone()
    # return success_msg({"item": {"id": a[0], "username": a[1], "content": a[2], "timestamp": int(a[3].timestamp())}})

@app.route('/search', methods = ['GET','POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html')

    mc = MongoClient(mongo_server)
    request_json = request.json
    tweet_coll = mc.twitterclone.tweet
    user_coll = mc.twitterclone.user
    # timestamp = request_json.get('timestamp')
    # if timestamp:
    #     timestamp = datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    #     #timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    # else:
    #     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # get default values
    timestamp = int(request_json.get('timestamp', calendar.timegm(time.gmtime())))
    limit = int(request_json.get('limit', 25))
    if limit > 100:
        limit = 25
    print("limit - ", limit)
    q = request_json.get('q', None)
    username = request_json.get('username', None)
    following = request_json.get('following', None)

    # form query M1
    check = dict()
    if timestamp is not None:
        check['timestamp'] = {"$lt": timestamp}
    sort = list()
    sort.append(("timestamp", pymongo.DESCENDING))

    docs = [doc for doc in tweet_coll.find(check).sort(sort)][limit:]
    print(check)
    print(str(len(docs)) + str(docs))
    if len(docs) == 0:
        return error_msg({'error': 'user not found'})
    #tids = [str(doc['_id']) for doc in docs]
    def make_tweet_item(tid, uid, content, timestamp):
        # respond with tweet
        item_details = dict()
        item_details['id'] = str(tid)
        item_details['content'] = content
        item_details['timestamp'] = timestamp
        # check for user of tweet
        check = dict()
        check['_id'] = uid
        docs = [doc for doc in user_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': 'database issue'})
        mc.close()
        item_details['username'] = docs[0]['username']
        return item_details
    tids = [make_tweet_item(doc['_id'], doc['uid'], doc['content'], doc['timestamp']) for doc in docs]

    # return 
    mc.close()
    other_response_fields = dict()
    other_response_fields['items'] = tids
    return success_msg(other_response_fields)


    # # TODO - add mongo support
    # c, conn = connection()
    # c.execute("SELECT t.tid, u.username, t.content, t.time from user u, tweet t where u.uid = t.uid order by t.time desc limit %s;", (limit,))
    # data = c.fetchall()
    # items = []
    # for a in data:
    #     items.append({"id": a[0], "username": a[1], "content": a[2], "timestamp": int(a[3].timestamp())})
    # return success_msg({"items": items, "number": len(items)})


@app.route('/user/<username>', methods = ['GET'])
def user():
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    following_coll = mc.twitterclone.following
    followers_coll = mc.twitterclone.followers
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    uid = docs[0]['uid']
    email = docs[0]['email']
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in followers_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    followers_num = len(docs[0]['followers'])
    # get following
    docs = [doc for doc in following_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    following_num = len(docs[0]['following'])
    # return email followers and following
    mc.close()
    user_parts = dict()
    user_parts['email'] = email
    user_parts['followers'] = followers_num
    user_parts['following'] = following_num
    other_response_fields = dict()
    other_response_fields['user'] = user_parts
    return success_msg(other_response_fields)

@app.route('/user/<username>/followers', methods = ['GET'])
def followers():
    request_json = request.json  # get json
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    followers_coll = mc.twitterclone.followers
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    uid = docs[0]['uid']
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in followers_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    followers = docs[0]['followers']
    # return email followers and following
    limit = int(request_json.get('limit', 50))
    if limit > 200:
        limit = 200
    mc.close()
    other_response_fields = dict()
    other_response_fields['users'] = followers[limit:]
    return success_msg(other_response_fields)

@app.route('/user/<username>/following', methods = ['GET'])
def following():
    request_json = request.json  # get json
    mc = MongoClient(mongo_server)
    user_coll = mc.twitterclone.user
    following_coll = mc.twitterclone.followers
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    uid = docs[0]['uid']
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in following_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    following = docs[0]['followers']
    # return email followers and following
    limit = int(request_json.get('limit', 50))
    if limit > 200:
        limit = 200
    mc.close()
    other_response_fields = dict()
    other_response_fields['users'] = following[limit:]
    return success_msg(other_response_fields)

@app.route('/follow', methods = ['POST'])
def follow():
    request_json = request.json  # get json
    session = request.cookies.get('cookie')  # get session
    # connect to login, user, following, and followers collections
    mc = MongoClient(mongo_server)
    login_coll = mc.twitterclone.login
    user_coll = mc.twitterclone.user
    following_coll = mc.twitterclone.following
    followers_coll = mc.twitterclone.followers
    # check for session
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']
    check = dict()
    check['session'] = session
    docs = [doc for doc in login_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'not logged in'})
    # get session uid
    uid = docs[0]['uid']
    # get follower id
    check = dict()
    check['username'] = request_json['username']
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': "follower doesn't exist"})
    fid = docs[0]['uid']

    # add or remove follower
    if request_json['follow'] == False:
        # remove follower

        # you have a list of people you are following
        # to remove someone you follow
        #   you must remove yourself from their followers list
        check = dict()
        check['uid'] = fid
        docs = [doc for doc in followers_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': "follower doesn't exist"})
        followers = docs[0]['followers'].remove(uid)  # TODO must check if followers is a list()
        check['$set'] = {'followers': followers}
        result = followers_coll.update_one(check)
        #   you also must remove them from your following list 
        check['uid'] = uid
        docs = [doc for doc in following_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': "following doesn't exist"})
        following = docs[0]['following'].remove(fid)  # TODO must check if following is a list()
        check['$set'] = {'following': following}
        result = following_coll.update_one(check)

    else:
        # add follower

        # you have a list of people you are following
        # to add a follower
        #   you must add yourself to their followers list
        check = dict()
        check['uid'] = fid
        docs = [doc for doc in followers_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': "follower doesn't exist"})
        followers = docs[0]['followers'].append(uid)  # TODO must check if followers is a list()
        check['$set'] = {'followers': followers}
        result = followers_coll.update_one(check)
        #   you also must add them to your following list
        check['uid'] = uid
        docs = [doc for doc in following_coll.find(check)]
        if len(docs) != 1:
            return error_msg({'error': "following doesn't exist"})
        following = docs[0]['following'].append(fid)  # TODO must check if following is a list()
        check['$set'] = {'following': following}
        result = following_coll.update_one(check)

    mc.close()
    other_response_fields = dict()
    return success_msg(other_response_fields)


if __name__ == '__main__':
    app.run(debug=True)

