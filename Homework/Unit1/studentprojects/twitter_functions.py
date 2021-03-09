import requests
from requests_oauthlib import OAuth1
import os
import pandas as pd
from iteration_utilities import grouper

#read tokens/keys from local environment vars
auth = OAuth1(os.getenv("Twitter API Key"), os.getenv("Twitter API Secret Key"),
               os.getenv("Twitter Access Token"), os.getenv("Twitter Access Token Secret"))

#create API endpoints
search_endpoint =  'https://api.twitter.com/1.1/search/tweets.json'
followers_endpoint = 'https://api.twitter.com/1.1/followers/list.json'
user_endpoint = 'https://api.twitter.com/1.1/users/show.json'
friends_ids_endpoint = 'https://api.twitter.com/1.1/friends/ids.json'
users_endpoint = 'https://api.twitter.com/1.1/users/lookup.json'

#Function 1
def find_user(screen_name, keys=None):
    #remove "@" symbol from screen_name
    screen_name = screen_name.replace('@','')
    #query user api
    user = requests.get(user_endpoint, params={'screen_name':screen_name}, auth=auth).json()
    #if keys not sppecified, return entire user dict
    if not keys:
        return user
    #select specified keys from user dict
    else:
        return {key:user[key] for key in keys}  

#Function 2
def find_hashtag(hashtag, count=15, search_type='mixed'):
    #replace "#" with proper ecnoding (%23)
    if hashtag.startswith('#'):
        hashtag = hashtag.replace('#','%23')
    #add # encoding if missing from hashtag
    else:
        hashtag = '%23' + hashtag
    res = requests.get(search_endpoint, params={'q':hashtag, 'count':count, 'search_type':search_type}, auth=auth).json()
    return res['statuses']

#Function 3
def get_followers(screen_name, keys = ['name', 'followers_count', 'friends_count', 'screen_name'], to_df=False):
    #remove "@" symbol from screen_name
    screen_name = screen_name.replace('@', '')
    #query followers endpoint for given screen_name 
    res = requests.get(followers_endpoint, params={'screen_name':screen_name}, auth=auth).json()
    #filter to only selected keys for each user object
    followers = [{key:user[key] for key in keys} for user in res['users']]
    #convert to a DataFrame object if requested
    if to_df:
        return pd.DataFrame(followers)
    return followers

#Function 4
def friends_of_friends(names, keys=None, to_df=False):
    #remove "@" symbol from each screen_name
    names = [name.strip('@') for name in names]
    #get ids of friends for each user from the friends_ids_endpoint and convert to a set
    friends1 = set(requests.get(friends_ids_endpoint, params={'screen_name':names[0]}, auth=auth).json()['ids'])
    friends2 = set(requests.get(friends_ids_endpoint, params={'screen_name':names[1]}, auth=auth).json()['ids'])
    #use the sets' intersection to find the ids in common
    shared = friends1.intersection(friends2)
    #create the string of overlapping ids
    ids = ','.join(str(num) for num in shared)
    #query users endpoint with ids string
    users = requests.get(users_endpoint, params={'user_id':ids}, auth=auth).json()
    #select only certain keys for each user if specified
    if keys:
        users = [{key:user[key] for key in keys} for user in users]
    #optionally convert to DataFrame
    if to_df:
        return pd.DataFrame(users)
    return users

#Function 5
def friends_of_friends(names, keys=None, to_df=False, full_search=False):
    names = [name.strip('@') for name in names]
    friends = [set(),set()]
   
    if full_search:
        #loop over 2 screen names
        for i, name in enumerate(names):
            #use cursoring to loop over full results from friends queries (5,000 ids per page)
            cursor = -1
            while cursor != 0 :
                res = requests.get(friends_ids_endpoint, params={'screen_name':name, 'cursor':cursor}, auth=auth).json()
                #add ids from each page to respective set
                friends[i].update(set(res['ids']))
                #set next cursor
                cursor = res['next_cursor']
    #just grab first page of friends results for each user
    else:
        for i, name in enumerate(names):
            res = requests.get(friends_ids_endpoint, params={'screen_name':name}, auth=auth).json()
            friends[i].update(set(res['ids']))

    #get overlapping ids
    shared_ids = list(friends[0].intersection(friends[1]))

    #loop handles cases where there are > 100 ids in common (max users returned from users endpoint)
    shared_friends = []
    #use grouper function to loop over groups of 100 user ids
    for ids in grouper(shared_ids, 100):
        ids_str = ','.join(str(num) for num in ids)
        users = requests.get(users_endpoint, params={'user_id':ids_str}, auth=auth).json()
        #add user objects to shared_friends list
        shared_friends.extend(users)
        
    #select specific keys to return
    if keys:
        shared_friends = [{key:user[key] for key in keys} for user in shared_friends]
    
    #select return format
    if to_df:
        return pd.DataFrame(shared_friends)
    return shared_friends
