import tweepy
from tweepy import Cursor
import httplib as http
import os
import json
from framework import request, redirect
from framework.sessions import session# get_session, set_session
from framework.exceptions import HTTPError
from website import models
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from framework.auth import get_current_user

def oauth_start(*args, **kwargs):



    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
    # callback_key = 'http://localhost:5000/'
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError as e:
        print 'Error! Failed to get request token.'

    #session = get_session()
    session.data['request_token_key'] = auth.request_token.key
    session.data['request_token_secret'] = auth.request_token.secret

    session.save()
    #set_session(session)
    return redirect(redirect_url)




def username(*args, **kwargs):
    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)

    auth.set_request_token(session.data.get('request_token_key'), session.data.get('request_token_secret'))

    verifier = request.args.get('oauth_verifier')
    print verifier
    session.data['verifier'] = request.args.get('oauth_verifier')
    x =  auth.get_access_token(verifier)

    auth.set_access_token(auth.access_token.key, auth.access_token.secret)
    session.data['access_token_key'] = auth.access_token.key
    session.data['access_token_secret'] = auth.access_token.secret

    session.save()
    api = tweepy.API(auth)

    node = models.Node.load(kwargs['pid'])
    twitter = node.get_addon('twitter')
    twitter.oauth_key = auth.access_token.key
    twitter.oauth_secret = auth.access_token.secret
    twitter.user_name = api.me().screen_name
    twitter.save()
    #return {'foo': api.me().name, 'token': request.args.get('oauth_verifier','token not found'), 'verifier':'b'}
    return redirect(os.path.join(node.url, 'settings'))
    return redirect('/settings/')

def twitter_oauth():
    return {'foo':'bar'}


@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_widget(*args, **kwargs):


    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    auth.set_access_token(config.oauth_key, config.oauth_secret)

    api = tweepy.API(auth)


    twitter = kwargs['node_addon']

    if twitter:
        rv = {
            'complete': True,
            'user_name': api.me().screen_name,
            'displayed_tweets': config.displayed_tweets,

        }
        print twitter
        rv.update(twitter.config.to_json())




        return rv
    raise HTTPError(http.NOT_FOUND)


@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_oauth_delete_node(*args, **kwargs):
#
#    node = models.Node.load(kwargs['pid'])
     twitter = kwargs['node_addon']

     twitter.oauth_key = None
     twitter.oauth_secret = None
     twitter.user_name = None
     twitter.save()
#
#    #twitter_node.delete_hook()
#
     return {}


@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_set_config(*args, **kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    #node = kwargs.get('node') or kwargs.get('project')
    #config = node.get_addon('twitter')
    twitter = kwargs['node_addon']
    displayed_tweets  = request.json.get('displayed_tweets', '')


#list comprehension
    default_message = 'Enter message here'

    twitter_logs = [k for k,v in request.json.iteritems() if v == 'on']
    twitter_log_messages = {k:v for k,v in request.json.iteritems() if 'message' in k and v != 'None' and v != default_message}




   # twitter_logs = request.json.get('twitter_logs', '')



    #rv = {
    #    'displayed_tweets': displayed_tweets,
    #    'log_actions': twitter_logs
    #}
    #

    twitter.log_messages= twitter_log_messages
    twitter.displayed_tweets = displayed_tweets
    twitter.log_actions = twitter_logs
    twitter.save()
    print repr(twitter.to_json(get_current_user()))
    return twitter.config.to_json()



@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_update_status(*args, **kwargs):

    print repr(request.data)
    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    auth.set_access_token(config.oauth_key, config.oauth_secret)
    api = tweepy.API(auth)

    status = json.loads(request.data).get('status')
    #if (len(status) > 140):


        #error error error

    api.update_status(status)

    return redirect(os.path.join(node.url, 'settings'))
    return redirect('/settings/')


