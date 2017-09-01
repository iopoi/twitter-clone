import json
from tools import error_msg, success_msg, randomString#, mem_login, mem_logout, mem_check_login #, sendemail
from flask import Flask, request, make_response, render_template,send_file
from datetime import datetime
import time, calendar
import pymongo
from pymongo import MongoClient, IndexModel
import bson
from bson.objectid import ObjectId
from bson.json_util import dumps
from bson.json_util import loads
import string
import random
import os
import traceback
#import memcache

from cassandra.cluster import Cluster

app = Flask(__name__)

#cookies = dict()
#memcached_server = '192.168.1.37:11211'
#mem = memcache.Client([memcached_server], debug=0)

#mongo_server = 'mongodb://192.168.1.35:27017/'
#mongo_server = 'mongodb://192.168.1.45:27017/'
mongo_server = 'mongodb://192.168.1.49:27017/'
mc = MongoClient(mongo_server)
#mc.twitterclone.tweet.create_index(("content", pymongo.TEXT))
mc.twitterclone.user.create_index([("email", 'hashed')])
mc.twitterclone.user.create_index([("username", 'hashed')])
mc.twitterclone.tweet.create_index([("uid", 'hashed')])
mc.twitterclone.tweet.create_index([("timestamp", 1)])
mc.twitterclone.tweet.create_index([("content", 'text')])
mc.twitterclone.login.create_index([("uid", 'hashed')])
mc.twitterclone.login.create_index([("session", 'hashed')])
mc.twitterclone.followers.create_index([("uid", 'hashed')])
mc.twitterclone.following.create_index([("uid", 'hashed')])
mc.twitterclone.like.create_index([("tid", 'hashed')])
mc.twitterclone.parent.create_index([("tid", 'hashed')])

#cluster = Cluster(['192.168.1.52'])
cluster = Cluster()
cass = cluster.connect()
keyspace = 'tweet_images'
cass.execute("""
    CREATE KEYSPACE IF NOT EXISTS %s
    WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '2' }
    """ % keyspace)
cass.set_keyspace(keyspace)
cass.execute("""
    CREATE TABLE IF NOT EXISTS images (
        key text,
        image blob,
        PRIMARY KEY (key)
    )
    """)

media_path = '/home/ubuntu/media'
app.config['UPLOAD_FOLDER'] = media_path
app.config['MAX_CONTENT_LENGTH'] = 16000000  # to limit large images

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
#    mem_login(mem, login['session'], login['uid'])  # TODO test
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
#    mem_logout(mem, session)
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
    print('debug - additem - json:', request_json)  # debug
    session = request.cookies.get('cookie')  # get session
    parent = request_json.get('parent', None)
    media = request_json.get('media', list())

    # connect to login and tweet collections
    # mc = MongoClient(mongo_server)
    global mc
    login_coll = mc.twitterclone.login
    tweet_coll = mc.twitterclone.tweet
    parent_coll = mc.twitterclone.parent
    like_coll = mc.twitterclone.like
    # check for session
    # optional - login app cookies
    #global cookies
    #cookies[login['session']] = login['uid']

    check = dict()
#    is_mem_login = mem_check_login(mem, session)
    is_mem_login = (None, None)
    print('debug - additem - info - is_mem_login:', is_mem_login)
    if is_mem_login[0] == True:
        docs = [{'uid': is_mem_login[1]}]
    elif is_mem_login[0] == False:
        return error_msg({'error': 'not logged in'})
    elif is_mem_login[0] is None:
        check['session'] = session
        docs = [doc for doc in login_coll.find(check)]
        if len(docs) != 1:
            print('debug - additem - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': 'not logged in'})
    else:
        return error_msg({'error': 'additem server error'})

    # insert tweet
    tweet = dict()
    tweet['uid'] = docs[0]['uid']
    tweet['content'] = request_json['content']
    tweet['timestamp'] = calendar.timegm(time.gmtime())
    tweet['parent'] = parent  # maybe put entry into an if statement
    tweet['media'] = media
    tweet['intrest'] = 0
    result = tweet_coll.insert_one(tweet)

    # TOD if there are media files, insert the media id's into the media table sorted by tid.
        # or store the mid's in the tweet object

    # TOD if there is a parent, let the parent know there is a reply in the parent table
        # when a tweet becomes a parent it gets a list of tid replies in the parent table

    # if tweet is a child then inform the parent
#    if parent is not None:
  #      print('debug - additem - parent format', parent)
#        # update collection
#        parent['tid'] = loads('{"$oid": "' + parent + '"}')  # changed the formating of parent
#        child['$addToSet'] = {'children_tid': tid}
#        if like_coll.update(tweet, like)['nModified'] == 0:
#            return error_msg({'error': 'server issue - parent child insert error'})
#        #return success_msg({})  # didn't think this was necessary

    # if tweet is a child then inform the parent
    if parent is not None:
        print('debug - additem - parent format', parent)
        # update collection
       # parent = dict()
        parent_d = dict()
        parent_d['tid'] = loads('{"$oid": "' + parent + '"}')  # changed the formating of parent
        tid = result.inserted_id
        child = dict()
        child['$addToSet'] = {'children_tid': tid}
        print('debug - additem - parent info', parent_d)
        print('debug - additem - child info', child) 
        if parent_coll.update(parent_d, child)['nModified'] == 0:
            return error_msg({'error': 'server issue - parent child insert error'})
        #return success_msg({})  # didn't think this was necessary


    # initialize parent entry in parent table
    parent = dict()
    print("result:", result)
    parent['tid'] = result.inserted_id
#    parent['tid'] = result
    parent['children_count'] = 0
    parent['children_tid'] = list()
    result_parent = parent_coll.insert_one(parent)


    # initialize like entry
    like = dict()
    like['tid'] = result.inserted_id
    like['like_count'] = 0
    like['uids'] = list()
    result_like = like_coll.insert_one(like)
    # TODO might have to do retweet stuff as well



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
        # TODO might want to if statement just in case
        item_details['parent'] = docs[0]['parent']
        item_details['media'] = docs[0]['media']

        # TOD add parent id - optional
        # TOD add media id's - optional

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

        # TOD delete media files related to tweet
        print("docs['media'] =", str(docs))
        for file_name in docs[0]['media']:
#        print()  # debug
#        for file_name in docs['media']
            # file system remove
            #print('debug - item/delete file - ', str(os.path.join(media_path, file_name)))
            #os.remove(os.path.join(media_path, file_name))

            # Cassandra remove
            query = "DELETE FROM images WHERE key=%s"
            rows = cass.execute(query, [file_name])
            print "deleted image from cass"
            print rows


        # delete tweet
        result = tweet_coll.delete_many(check)
        # mc.close()
        other_response_fields = dict()
        print('debug - item/delete - success - output:', str(other_response_fields))
        return success_msg(other_response_fields)

    return 405


@app.route('/item/<tid>/like', methods = ['GET', 'POST'])
def like(tid):
    if request.method == 'GET':
        return render_template('like.html')
    print('debug - like - info - tid='+str(tid))
    # to like a tweet
    # the logged in users id should be added to like_tweet collection

    # get the uid of the session
    # get the tid of the tweet

    # use tid to update uid in the like_tweet collection


    global mc
    tweet_coll = mc.twitterclone.tweet
    like_coll = mc.twitterclone.like
    login_coll = mc.twitterclone.login

    session = request.cookies.get('cookie')  # get session
    request_json = request.json

    # get session uid
    check = dict()
    check['session'] = session
    docs = [doc for doc in login_coll.find(check)]
    if len(docs) != 1:
        print('debug - follow - error - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'not logged in'})
    uid = docs[0]['uid']

    # get tweet tid
    tid = loads('{"$oid": "' + tid + '"}')

    # TODO if this works migrate it to follow
    # like or unlike
    like_bool = bool(request_json.get('like', True))
    if like_bool != False:
        action = "$addToSet"  # like
        increment = 1
    else:
        action = "$pull"  # unlike
        increment = -1

    # update collection
    tweet = dict()  # added this idk - check this TODO
    tweet['tid'] = tid
    like = dict()
    like[action] = {'uids': uid}
    like['$inc'] = {'like_count': increment}
    print('debug - like - info - tweet', tweet)
    print('debug - like - info - like', like)
    if like_coll.update(tweet, like)['nModified'] == 0:
        return error_msg({'error': 'cannot like or unlike twice'})
    else:
        # increment intrest rating in tweet object
        tweet = dict()
        tweet['_id'] = tid
        like = dict()
        like['$inc'] = {'intrest': increment}
        if tweet_coll.update(tweet, like)['nModified'] == 0:
            return error_msg({'error': 'cannot update tweet intrest'})
    return success_msg({})

    # like = bool(request_json.get('like', True))
    # if like != False:
    #     # true



    #     # # check if person already liked tweet
    #     # check = dict()
    #     # check['uids'] = uid
    #     # if len([doc for doc in like_coll.find(check)]) > 0:
    #     #     # if so throw error
    #     #     return error_msg({'error': 'cannot like an already liked tweet'})

    #     # # add uid to like


    #     like = dict()
    #     like['tid'] = tid
    #     # like['email'] = request_json['email']
    #     # like['password'] = request_json['password']
    #     # like['verified'] = False
    #     # like['verify_key'] = randomString()
    #     result = like_coll.insert_one(like)

    # else:
    #     # flase

    #     # check if person already did not like tweet
    #     check = dict()
    #     check['uids'] = uid
    #     if len([doc for doc in like_coll.find(check)]) == 0:
    #         # if so throw error
    #         return error_msg({'error': 'cannot unlike a tweet that was never liked'})


    # # print(id)
    # # print(loads(id))
    # # # connect to tweet and user collection

    # # tweet_coll = mc.twitterclone.tweet
    # # user_coll = mc.twitterclone.user
    # # # check for tweet with tid
    # # check = dict()
    # # check['_id'] = loads(id)
    # # docs = [doc for doc in tweet_coll.find(check)]
    # # if len(docs) != 1:
    # #     print('debug - item/get - error - check:', str(check), 'docs:', str(docs))  # debug
    # #     return error_msg({'error': 'incorrect tweet id'})

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
    following_coll = mc.twitterclone.following

    # get default values
    timestamp = int(request_json.get('timestamp', calendar.timegm(time.gmtime())))
    limit = int(request_json.get('limit', 25))
    if limit > 100:
        limit = 25
    print("limit - ", limit)
    q = request_json.get('q', None)
    username = request_json.get('username', None)
    following = bool(request_json.get('following', True))
    rank = request_json.get('rank', 'intrest')
    parent = request_json.get('parent', None)
    replies = bool(request_json.get('replies', True))
    hasMedia = bool(request_json.get('hasMedia', False))

    # form query M1
    check = dict()
    if timestamp is not None:
        check['timestamp'] = {"$lt": timestamp}
    sort = list()
    if rank == 'intrest':  # from M3 query
        sort.append(('intrest', pymongo.DESCENDING))
      #  sort.append(("timestamp", pymongo.DESCENDING))  # maybe
    else:  # from M2 query
        sort.append(("timestamp", pymongo.DESCENDING))
    
    # form query M2
    if following != False:
        # get list of following ids
        check_session = dict()
        check_session['session'] = session
        docs = [doc for doc in login_coll.find(check_session)]
        if len(docs) != 1:
            print('debug - search - error - check:', str(check_session), 'docs:', str(docs))  # debug
            return error_msg({'error': 'not logged in'})
        s_uid = docs[0]['uid']
        print("session", str(session), "session_uid", str(s_uid))
        check_following = dict()
        check_following['uid'] = s_uid
        docs = [doc for doc in following_coll.find(check_following)]
        if len(docs) != 1:
            print('debug - search - error - check:', str(check_following), 'docs:', str(docs))  # debug
            return error_msg({'error': 'user not found'})
        following = docs[0]['following']
        check['uid'] = {"$in": following}
        if username is not None:
            # get username id
            # check for existing verified user
            check_user = dict()
            check_user['username'] = username
            docs = [doc for doc in user_coll.find(check_user)]
            if len(docs) != 1:
                print('debug - search - error - check:', str(check_user), 'docs:', str(docs))
                return error_msg({'error': 'uid username error'})
            if docs[0]['_id'] not in following:
                return success_msg({'items': []})
    else:
        if username is not None:
            # get username id
            # check for existing verified user
            check_user = dict()
            check_user['username'] = username
            docs = [doc for doc in user_coll.find(check_user)]
            if len(docs) != 1:
                print('debug - search - error - check:', str(check_user), 'docs:', str(docs))
                return error_msg({'error': 'uid username error'})
            check['uid'] = docs[0]['_id']

    if q is not None:
        check['$text'] = {'$search': q}
        print('debug - search - error - check - q:', str(check))

    # form query M3 - TOD
    # sort by interest - TOD
    # filter on whether a tweet is a child of parent id - TOD
    # filter on whether a tweet had a parent or not - TOD

    if parent is not None:
        check['parent'] = parent

    if not replies:
        check['parent'] = {'$exists': False}

    if hasMedia:
        check['media'] = {'media': {'$not': {'$size': 0}}}

    # get tweets
    #docs_t = [doc for doc in tweet_coll.find(check).sort(sort)][:limit]
    docs_t = [doc for doc in tweet_coll.find(check).sort(sort).limit(limit)]
    print('debug - search - doc - q:', str(docs_t))
    if len(docs_t) == 0:
#        print('debug - search - error - check:', str(check), 'docs:', str(docs_t))  # debug
 #       return error_msg({'error': 'no tweets found'})
        return success_msg({"items": []})    
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
        #print("make tweet item - return")  #debug
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
        print('debug - followers - error - uid - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    uid = docs[0]['_id']
    #print('uid:', str(uid))app.config['UPLOAD_FOLDER']
    # get followers
    check = dict()
    check['uid'] = uid
    docs = [doc for doc in followers_coll.find(check)]
    if len(docs) != 1:
        print('debug - followers - error - fid - check:', str(check), 'docs:', str(docs))  # debug
        return error_msg({'error': 'user not found'})
    followers = docs[0]['followers']
    followers = followers[:limit]

    # get usernames for followers
    check = dict()
    check['_id'] = {'$in': followers}
    usernames = [doc['username'] for doc in user_coll.find(check)]
    if len(usernames) < 0:
        print('debug - followers - error - check:', str(check), 'docs:', str(docs))  # debug
        print('usernames:', str(usernames))  # debug
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
    if len(usernames) < 0:
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
    print('debug - follow - request: ', str(request))
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
    if request_json['follow'] in ['False', 'false', False]:
        print('unfollowtest!@#$%')
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
            print('debug - unfollow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "follower doesn't exist"})
        followers = docs[0]['followers']
        if followers is None:
            followers = list()
        try:
            followers = list(set(followers))
            if uid not in followers:
                return error_msg({'error': "cannot unfollow - username knows you don't follow them"})
            followers.remove(uid)
        except ValueError: 
            return error_msg({'error': "cannot unfollow someone you are not following"})
        result = followers_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"followers": followers}})
        #   you also must remove them from your following list 
        check['uid'] = uid
        docs = [doc for doc in following_coll.find(check)]
        if len(docs) != 1:
            print('debug - unfollow - error - check:', str(check), 'docs:', str(docs))  # debug
            return error_msg({'error': "following doesn't exist"})
        following = docs[0]['following']
        #print('following - ', following)
        if following is None:
            following = list()
        try:
            following = list(set(following))
            if fid not in following:
                return error_msg({'error': "cannot unfollow - you don't follow username"})
            following.remove(fid)
        except ValueError: 
            return error_msg({'error': "cannot unfollow someone you are not following"})
        #result = following_coll.update_one(check)
        result = following_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"following": following}})

    else:
        print('followtest!@#$%')
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
        #followers = docs[0]['followers'].append(uid)
        followers = docs[0]['followers']
        #print('followers - ', followers)
        if followers is None:
            followers = list()
        followers = list(set(followers))
        if uid in followers:
            return error_msg({'error': "cannot follow - username already knows you follow them"})
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
        following = docs[0]['following']
        #print('following - ', following)
        if following is None:
            following = list()
        following = list(set(following))
        if fid in following:
            return error_msg({'error': "cannot follow - you are already following username"})
        following.append(fid)
        #print('following - ', following)
        #result = following_coll.update_one(check)
        result = following_coll.update_one({'_id': docs[0]['_id']}, {'$set': {"following": following}})

    # mc.close()
    other_response_fields = dict()
    print('debug - follow - success - output:', str(other_response_fields))
    return success_msg(other_response_fields)


@app.route('/addmedia', methods = ['GET', 'POST'])
def addmedia():
    if request.method == 'GET':
        return render_template('addmedia.html')

    print("/addmedia")
    # generate id
    l = 32
    s = string.ascii_letters+string.digits
    file_id = ''.join(random.sample(s, l))

    
    print('request data:', request.files)

    ## Request object analysis 
    ## log data to console and stdout

    print type(request.files["content"])
    print dir(request.files["content"])
    print request.files["content"].save.__doc__
    #print request.files["content"].save.__doc_ 

    ##
    ## This chunk tests whether we can save fileobjects
    ## to the local filesystem. Exceptions are | to stdout
    ##
    
    try:
        ## Retrieve FileObject from request
        fo = request.files["content"]


        # Cassandra insert
        query = "INSERT INTO images (key,image) VALUES (?,?)"
        prep = cass.prepare(query)
        cass.execute(prep,[file_id, fo.read()])


        # Mongo insert
#        global mc
#        image_coll = mc.twitterclone.image
#        image = dict()
#        image['data'] = fo
#       # result = image_coll.insert_one(image)
#       # result = image_coll.insert_one(request)
#        result = {0 : image_coll.insert_one(request)}
#        print('debug - addmedia - inserted image - result', result)
#        file_id = result.inserted_id

#        # file system insert
#        print('debug - addmedia - content_length')
#        print(str(fo.content_length))
#
#        ## Save fileobjext to desired filepath
#        filepath = app.config['UPLOAD_FOLDER']
#        savename = file_id
#        fo.save(os.path.join(filepath, savename), buffer_size=10000)
    except Exception, e:
     #   print('exception - addmedia - inserted image - result', result)
        print e
        traceback.print_exc()
    
   # print("file data:", request.files['file'])
   #if 'file' not in request.files:
   #     print('request: ', request)
   #     return error_msg({'error': 'no file attached'})
   # print('file exists')
   # f = request.files['file']
   # print('file contents', str(f))
   # f.save(os.path.join(app.config['UPLOAD_FOLDER'], file_id))
   # print("file_id =", file_id)
    #file_attachment = request.files['file'].save(media_path+file_id)
    #print("file from request -", file_attachment)
    ## save file
    #if (False):  # TODO check for save success or file retrival
    #    return error_msg({'error': "file error"})

    # return id
    other_response_fields = dict()
    other_response_fields['id'] = file_id
    msg = success_msg(other_response_fields)
    print('debug - /addmedia - return message', msg)  # debug
    return msg 
    



@app.route('/media/<mid>', methods = ['GET'])
def media(mid):
    # returns file
    filepath = app.config['UPLOAD_FOLDER']
    #fo.save(os.path.join(filepath, mid), buffer_size=10000)
    #return send_from_directory(media_path, mid)
    #res = make_response(open(os.path.abspath(os.path.join(filepath, mid))).read())
    # TOD - fill method


    # Cassandra return
    query = "SELECT image FROM images WHERE key=%s"
    rows = cass.execute(query, [mid])  
#    print "image data mid="+mid
#    print rows
    return send_file(rows[0], mimetype="image/gif")

    # mongo return
#    global mc
#    image_coll = mc.twitterclone.image
#    check = dict()
#    check['_id'] = mid
#    docs = [doc for doc in image_coll.find(check)]
#    if len(docs) != 1:
#        print('debug - media - error - check:', str(check), 'docs:', str(docs))  # debug
#        return error_msg({'error': 'image not found'})
#    # get session uid
#    image_file = docs[0]['data'] 
#  #  return image_file
#  #  return image_file.files["content"]
#    return image_file.files["content"][0]


    # filesystem return
#    return send_file(os.path.abspath(os.path.join(filepath, mid)), mimetype="image/gif")

    




if __name__ == '__main__':
    #app.run(debug=True)
    app.run(debug=False)
