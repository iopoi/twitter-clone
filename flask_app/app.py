import json
from tools import error_msg, success_msg, randomString #, sendemail
from flask import Flask, request, make_response, render_template
from datetime import datetime
import time, calendar
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
mc = MongoClient(mongo_server)


@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/adduser', methods = ["POST", "GET"])
def adduser():
    if request.method == 'GET':
        return render_template('register.html')

    request_json = request.json  # get json
    print('debug - adduser - json:', str(request_json))  # debug
    # connect to user collection
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    # check for existing verified user
    check = dict()
    check["$or"] = [{'username': request_json['username']},
                         {'email': request_json['email']}]
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) > 0:
        print('debug - adduser - error - check:', str(check), 'docs:', str(docs))
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
    # mc.close()
    print('debug - adduser - success')
    return success_msg({})

@app.route('/login', methods = ['POST', "GET"])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    request_json = request.json  # get json
    print('debug - login - json:', str(request_json))  # debug
    # connect to user and login collections
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    login_coll = mc.twitterclone.login
    # check for existing verified user
    check = dict()
    check['username'] = request_json['username']
    check['password'] = request_json['password']
    check['verified'] = True
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        print('debug - login - error - check:', str(check), 'docs:', str(docs))
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
    # mc.close()
    resp = make_response(success_msg({}))
    resp.set_cookie('cookie', login['session'])
    return resp
    

@app.route('/logout', methods = ['POST', 'GET'])
def logout():
    if request.method == 'GET':
        return render_template('logout.html')

    session = request.cookies.get('cookie')  # get session
    print('debug - logout - session:', str(session))  # debug
    # connect to user and login collections
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    login_coll = mc.twitterclone.login
    # check for logged in user
    check = dict()
    check['session'] = session
    docs = [doc for doc in login_coll.find(check)]
    print(str(len(docs)) + str(docs))
    if len(docs) != 1:
        print('debug - logout - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'not logged in'})
    # logs out user
    result = login_coll.delete_many(check)
    # optional - logout app cookies
    #global cookies
    #cookies.pop(cookie)
    # mc.close()
    print('debug - logout - success', str(result))
    return success_msg({})


@app.route('/verify', methods = ['POST', 'GET'])
def verify():
    if request.method == 'GET':
        return render_template('verify.html')

    request_json = request.json  # get json
    print('debug - verify - json:', str(request_json))  # debug
    # connect to user collection
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    # check for unverified email and matching key
    check = dict()
    check['email'] = request_json['email']
    check['verified'] = False
    if request_json['key'] != 'abracadabra':
        check['verify_key'] = request_json.get('key', 'abracadabra')
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        print('debug - verify - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'wrong key or email not found or user already verified'})
    # verifiy user
    Oid = docs[0]['_id']
    user = dict()
#    user['_id'] = docs[0]['_id']
    user['username'] = docs[0]['username']
    user['email'] = docs[0]['email']
    user['password'] = docs[0]['password']
    user['verified'] = True
    #print(user)
    result = user_coll.replace_one({'_id': Oid}, user)
    following_coll = mc.twitterclone.following
    followers_coll = mc.twitterclone.followers
    # insert new user
    following = dict()
    following['uid'] = Oid
    following['following'] = list()
    result = following_coll.insert_one(following)
    #print('added following row', str(result))
    followers = dict()
    followers['uid'] = Oid
    followers['followers'] = list()
    result = followers_coll.insert_one(followers)
    #print('added followers row', str(result))
    
    # mc.close()
    print('debug - verify - success')
    return success_msg({})


@app.route('/additem', methods = ['POST', 'GET'])
def additem():
    if request.method == 'GET':
        return render_template('addtweet.html')

    request_json = request.json  # get json
    print('debug - additme - json:', request_json)  # debug
    session = request.cookies.get('cookie')  # get session
    # connect to login and tweet collections
    # mc = MongoClient(mongo_server)
    global mc
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
        print('debug - additem - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'not logged in'})
    # insert tweet
    tweet = dict()
    tweet['uid'] = docs[0]['uid']
    tweet['content'] = request_json['content']
    tweet['timestamp'] = calendar.timegm(time.gmtime())
    result = tweet_coll.insert_one(tweet)
    #print('result')
    #print(result)
    #print(str(result))
    # mc.close()
    other_response_fields = dict()
    #other_response_fields['id'] = dumps(result.inserted_id)
    other_response_fields['id'] = str(result.inserted_id)
    print('debug - verify - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)


@app.route('/item/<tid>', methods = ['GET', 'DELETE'])
def item(tid):
    print('got to item')
    tid = '{"$oid": "' + tid + '"}'
    # mc = MongoClient(mongo_server)
    global mc
    if request.method == 'GET':
        print(tid)
        print(loads(tid))
        # connect to tweet and user collection

        tweet_coll = mc.twitterclone.tweet
        user_coll = mc.twitterclone.user
        # check for tweet with tid
        check = dict()
        check['_id'] = loads(tid)
        docs = [doc for doc in tweet_coll.find(check)]
        if len(docs) != 1:
            print('debug - item/get - error - check:', str(check), 'docs:', str(docs))  # debug
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
            print('debug - item/get - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': 'database issue'})
        # mc.close()
        item_details['username'] = docs[0]['username']
        other_response_fields = dict()
        other_response_fields['item'] = item_details
        print('debug - item/get - success - output:', str(other_response_fields))
        return success_msg(other_response_fields)

    elif request.method == 'DELETE':
        # connect to tweet collection
        tweet_coll = mc.twitterclone.tweet
        # check for tweet with tid
        check = dict()
        check['_id'] = loads(tid)
        docs = [doc for doc in tweet_coll.find(check)]
        if len(docs) != 1:
            print('debug - item/delete - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': 'incorrect tweet id'})
        # delete tweet
        result = tweet_coll.delete_many(check)
        # mc.close()
        other_response_fields = dict()
        print('debug - item/delete - success - output:', str(other_response_fields))
        return success_msg(other_response_fields)

    return 405


@app.route('/search', methods = ['GET','POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html')

    # connect
    # mc = MongoClient(mongo_server)
    global mc
    session = request.cookies.get('cookie')  # get session
    request_json = request.json
    print('debug - search - json:', request_json)  # debug
    tweet_coll = mc.twitterclone.tweet
    user_coll = mc.twitterclone.user
    login_coll = mc.twitterclone.login

    # get default values
    timestamp = int(request_json.get('timestamp', calendar.timegm(time.gmtime())))
    limit = int(request_json.get('limit', 25))
    if limit > 100:
        limit = 25
    print("limit - ", limit)
    q = request_json.get('q', None)
    username = request_json.get('username', None)
    following = bool(request_json.get('following', True))

    # form query M1
    check = dict()
    if timestamp is not None:
        check['timestamp'] = {"$lt": timestamp}
    sort = list()
    sort.append(("timestamp", pymongo.DESCENDING))
    
    # form query M2
    if following != False:
        # get list of follower ids
        check_session = dict()
        check_session['session'] = session
        docs = [doc for doc in login_coll.find(check_session)]
        if len(docs) != 1:
            print('debug - search - error - check:', str(check_session), 'docs:', str(docs))  # debug
            return error_msg({'error': 'not logged in'})
        s_uid = docs[0]['uid']
        check_following = dict()
        check_following['uid'] = s_uid
        docs = [doc for doc in following_coll.find(check_following)]
        if len(docs) != 1:
            print('debug - search - error - check:', str(check_following), 'docs:', str(docs))  # debug
            return error_msg({'error': 'user not found'})
        following = docs[0]['following']
        check['uid'] = {"$in": following}
   # if username is not None:
   #     # get username id
   #     # check for existing verified user
   #     check_user = dict()
   #     check_user['username'] = username
   #     docs = [doc for doc in user_coll.find(check_user)]
   #     if len(docs) != 1:
   #         print('debug - search - error - check:', str(check), 'docs:', str(docs))
   #         return error_msg({'error': 'incorrect password or user not verified or user does not exist'})
   #     check['uid'] = docs[0]['_id']
        

    # get tweets
    docs_t = [doc for doc in tweet_coll.find(check).sort(sort)][:limit]
    if len(docs_t) == 0:
        print('debug - search - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'no tweets found'})
    
    # get usernames for tweets
    check = dict()
    check['_id'] = {'$in': [doc['uid'] for doc in docs_t]}
    docs_u = [(doc['_id'], doc['username']) for doc in user_coll.find(check)]
    if len(docs_u) == 0:
        print('debug - search - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'no users found for tweets - server issue'})
    id_username = dict()
    for i in docs_u:
        id_username[i[0]] = i[1]
    def make_tweet_item(tid, uid, content, timestamp):
        # respond with tweet
        item_details = dict()
        item_details['id'] = str(tid)
        item_details['content'] = content
        item_details['timestamp'] = timestamp
        item_details['username'] = id_username[uid]
        print("make tweet item - return")
        return item_details
    tids = [make_tweet_item(doc['_id'], doc['uid'], doc['content'], doc['timestamp']) for doc in docs_t]

    # return 
    # mc.close()
    other_response_fields = dict()
    other_response_fields['items'] = tids
    print('debug - search - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)


@app.route('/user/<username>', methods = ['GET'])
def user(username):
    print('debug - user - GET - username:', str(username))  # debug
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    following_coll = mc.twitterclone.following
    followers_coll = mc.twitterclone.followers
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        return error_msg({'error': 'user not found'})
    uid = docs[0]['_id']
    email = docs[0]['email']
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in followers_coll.find(check)]
    if len(docs) != 1:
        print('debug - user - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    followers_num = len(docs[0]['followers'])
    # get following
    docs = [doc for doc in following_coll.find(check)]
    if len(docs) != 1:
        print('debug - user - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    following_num = len(docs[0]['following'])
    # return email followers and following
    # mc.close()
    user_parts = dict()
    user_parts['email'] = email
    user_parts['followers'] = followers_num
    user_parts['following'] = following_num
    other_response_fields = dict()
    other_response_fields['user'] = user_parts
    print('debug - user - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)

@app.route('/user/<username>/followers', methods = ['GET'])
def followers(username):
    print('debug - followers - GET - username:', str(username))  # debug
    request_json = request.json  # get json
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    followers_coll = mc.twitterclone.followers
    if request_json is None:
        limit = 50
    elif request_json['limit'] > 200:
        limit = 200
    elif request_json['limit'] < 1:
        limit = 50
    else:
        limit = request_json['limit']
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        print('debug - followers - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    uid = docs[0]['_id']
    #print('uid:', str(uid))
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in followers_coll.find(check)]
    if len(docs) != 1:
        print('debug - followers - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    followers = docs[0]['followers']
    followers = followers[:limit]

    # get usernames for followers
    check = dict()
    check['_id'] = {'$in': followers}
    usernames = [doc['username'] for doc in user_coll.find(check)]
    if len(usernames) == 0:
        print('debug - followers - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'no users found for tweets - server issue'})

    #print('followers:', str(usernames))
    # return the names of the followers
    # mc.close()
    other_response_fields = dict()
    other_response_fields['users'] = usernames
    print('debug - followers - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)

@app.route('/user/<username>/following', methods = ['GET'])
def following(username):
    print('debug - followers - GET - username:', str(username))  # debug
    request_json = request.json  # get json
    # mc = MongoClient(mongo_server)
    global mc
    user_coll = mc.twitterclone.user
    following_coll = mc.twitterclone.following
    if request_json is None:
        limit = 50
    elif request_json['limit'] > 200:
        limit = 200
    elif request_json['limit'] < 1:
        limit = 50
    else:
        limit = request_json['limit']
    # get uid from username
    check = dict()
    check['username'] = username
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        print('debug - following - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    uid = docs[0]['_id']
    
    # get following
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in following_coll.find(check)]
    if len(docs) != 1:
        print('debug - following - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    following = docs[0]['following']
    following = following[:limit]

    # get usernames for following
    check = dict()
    check['_id'] = {'$in': following}
    usernames = [doc['username'] for doc in user_coll.find(check)]
    if len(usernames) == 0:
        print('debug - following - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'no users found for tweets - server issue'})

    # return the names of the following
    # mc.close()
    other_response_fields = dict()
    other_response_fields['users'] = usernames
    print('debug - following - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)

@app.route('/follow', methods = ['GET', 'POST'])
def follow():
    if request.method == 'GET':
        return render_template('follow.html')
    request_json = request.json  # get json
    print('debug - follow - json:', request_json)  # debug
    session = request.cookies.get('cookie')  # get session
    # connect to login, user, following, and followers collections
    # mc = MongoClient(mongo_server)
    global mc
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
        print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'not logged in'})
    # get session uid
    uid = docs[0]['uid']
    # get follower id
    check = dict()
    check['username'] = request_json['username']
    docs = [doc for doc in user_coll.find(check)]
    if len(docs) != 1:
        print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': "follower doesn't exist"})
    fid = docs[0]['_id']

    # add or remove follower
    if request_json['follow'] == 'False':
        # remove follower
        #print(request_json['follow'])
        #print('unfollow')
        # you have a list of people you are following
        # to remove someone you follow
        #   you must remove yourself from their followers list
        check = dict()
        check['uid'] = fid
        docs = [doc for doc in followers_coll.find(check)]
        if len(docs) != 1:
            print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "follower doesn't exist"})
        followers = docs[0]['followers']  # TODO must check if followers is a list()
        if followers is None:
            followers = list()
        try:
            followers.remove(uid)
        except ValueError: 
            return error_msg({'error': "cannot unfollow someone you are not following"})
        result = followers_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"followers": followers}})
        #   you also must remove them from your following list 
        check['uid'] = uid
        docs = [doc for doc in following_coll.find(check)]
        if len(docs) != 1:
            print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "following doesn't exist"})
        following = docs[0]['following']  # TODO must check if followers is a list()
        #print('following - ', following)
        if following is None:
            following = list()
        try:
            following.remove(fid)
        except ValueError: 
            return error_msg({'error': "cannot unfollow someone you are not following"})
        #result = following_coll.update_one(check)
        result = following_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"following": following}})

    else:
        # add follower
        #print(request_json['follow'])
        #print('follow')
        # you have a list of people you are following
        # to add a follower
        #   you must add yourself to their followers list
        check = dict()
        check['uid'] = fid
        docs = [doc for doc in followers_coll.find(check)]
        print('followers doc - ', str(docs))
        if len(docs) != 1:
            print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "follower doesn't exist"})
        #followers = docs[0]['followers'].append(uid)  # TODO must check if followers is a list()
        followers = docs[0]['followers']  # TODO must check if followers is a list()
        #print('followers - ', followers)
        if followers is None:
            followers = list()
        followers.append(uid)
        #print('followers - ', followers)
        #result = followers_coll.update_one(check)
        result = followers_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"followers": followers}})
        #   you also must add them to your following list
        check['uid'] = uid
        docs = [doc for doc in following_coll.find(check)]
        #print('following doc - ', str(docs))
        if len(docs) != 1:
            print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "following doesn't exist"})
        following = docs[0]['following']  # TODO must check if followers is a list()
        #print('following - ', following)
        if following is None:
            following = list()
        following.append(fid)
        #print('following - ', following)
        #result = following_coll.update_one(check)
        result = following_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"following": following}})

    # mc.close()
    other_response_fields = dict()
    print('debug - follow - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)


if __name__ == '__main__':
    app.run(debug=True)

