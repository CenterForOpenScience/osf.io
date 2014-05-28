import httplib as http
import os
import json

import tweepy

from framework import request, redirect
from framework.exceptions import HTTPError
from website import models
from website.project.decorators import must_have_addon,must_have_permission
from website.project.decorators import must_be_contributor_or_public, must_be_valid_project
from framework.status import push_status_message
from website.addons.twitter.utils import check_tweet
from website.addons.twitter.settings import CONSUMER_KEY, CONSUMER_SECRET


@must_be_valid_project
@must_have_addon('twitter', 'node')
def twitter_oauth_start(*args, **kwargs):
    """Gets request token from twitter to create OAuthHandler instance

        :param None

        :return: redirects user to twitter's authentication page
        """

    #Build OAuthHandler and set redirect url
    node = models.Node.load(kwargs['pid'])
    callback_url = node.api_url_for('twitter_oauth_callback', _absolute=True)
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, callback_url, secure=True)
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError as e:
        print 'Error! Failed to get request token.'
    node = models.Node.load(kwargs['pid'])
    twitter = node.get_addon('twitter')
    twitter.request_token_key = auth.request_token.key
    twitter.request_token_secret = auth.request_token.secret
    twitter.save()

    return redirect(redirect_url)

def twitter_oauth_callback(*args, **kwargs):

    """Exchange request token for access token

        :param message: None

        :return: Redirects user to add-on settings page
    """

    #Rebuild OAuthHandler
    node = models.Node.load(kwargs['pid'])
    twitter = node.get_addon('twitter')
    callback_url = node.api_url_for('twitter_oauth_callback', _absolute=True)
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, callback_url, secure=True)
    #Use request token and verifier to get access token
    auth.set_request_token(twitter.request_token_key, twitter.request_token_secret)
    verifier = request.args.get('oauth_verifier')
    try:
      auth.get_access_token(verifier = verifier)
    except tweepy.TweepError as e:
            raise HTTPError(
                400,
                data={
                    'message_long':'Please try again.',
                    'message_short':'Twitter Error!',
                }
            )
    auth.set_access_token(auth.access_token.key, auth.access_token.secret)
    api = tweepy.API(auth)
    twitter.oauth_key = auth.access_token.key
    twitter.oauth_secret = auth.access_token.secret
    twitter.user_name = api.me().screen_name
    twitter.save()
    return redirect(os.path.join(node.url, 'settings'))
    return redirect('/settings/')

@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_widget(*args, **kwargs):
    """Passes twitter user data to twitter_widget.mako

        :param message: None

        :return: None
    """
    #Build OAuthHandler
    node = kwargs.get('node') or kwargs.get('project')
    twitter = kwargs.get('node_addon')
    config = node.get_addon('twitter')


    if config.oauth_key:
        callback_url = node.api_url_for('twitter_oauth_callback', _absolute=True)
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, callback_url, secure=True)
        #Rebuild access token and tweepy object
        auth.set_access_token(config.oauth_key, config.oauth_secret)
        try:
            api = tweepy.API(auth)
            screen_name = api.me().screen_name
        #if user is not authorized, clear out node settings
        #TODO: decide which node settings will persist
        except tweepy.TweepError as e:
            #raise HTTPError(400,
            #                data={
            #                'message_long':'Your authentication token has expired.  '
            #                        'Visit the settings page to re-authenticate.',
            #                'message_short':'Twitter Error'
            #                }
            #)
            screen_name = None
            twitter.log_messages = {}
            twitter.log_actions =[]
            twitter.oauth_key = None
            twitter.oauth_secret = None
            twitter.user_name = None
            twitter.save()
    else:
        screen_name = None
    if twitter:
        if (config.displayed_tweets == None):
            config.displayed_tweets = 0
        rv = {
            'complete': True,
            'user_name': screen_name,
            'displayed_tweets': config.displayed_tweets,
            'tweet_queue': config.tweet_queue,
        }
        rv.update(twitter.config.to_json())
        return rv
    raise HTTPError(http.NOT_FOUND)

@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_oauth_delete_node(*args, **kwargs):
     """Removes OAuth info from twitter add-on node

        :param None

        :return: None
     """

     twitter = kwargs['node_addon']
     twitter.oauth_key = None
     twitter.oauth_secret = None
     twitter.user_name = None
     twitter.log_messages = {}
     twitter.log_actions = []
     twitter.tweet_queue = []

     twitter.save()
     return {}

@must_have_permission('write')
@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_set_config(*args, **kwargs):
    """Called when settings get updated and saves input data to relevant fields
       in twitter node add-on object


        :param None

        :return: None
    """

    #retrieve node add-on object
    twitter = kwargs['node_addon']
    #building list of logs that the user wants to tweet a message for, and the messages the user has built
    twitter_logs = [k for k,v in request.json.iteritems() if v == 'on']
    twitter_log_messages = {}
    for k,v in request.json.iteritems():
        if 'message' in k:
            if len(v) <= 140:
              twitter_log_messages[k]=v
            else:
              action_name = k
              twitter_log_messages[action_name] = twitter.log_messages.get(action_name)
              action_name = action_name.replace("_message", "")
              action_name = action_name.replace("_", " ")
              action_name = action_name.title()
              push_status_message(
                    'The custom message for event {action} is {nchar} characters over the '
                    '140 character limit, and could not be saved.  Please use a message '
                    'within the 140 character limit.'.format(
                    action=action_name,
                    nchar=len(v) - 140,
                    ),
                     kind='warning'
              )
    #Update twitter object
    twitter.displayed_tweets  = request.json.get('displayed_tweets', '')
    twitter.log_messages= twitter_log_messages
    twitter.log_actions = twitter_logs
    twitter.save()
    return twitter.config.to_json()

@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_update_status(*args, **kwargs):
    """Called when user manually updates status
    through twitter widget

        :param None

        :return: Redirects user to settings page
    """
    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    status = json.loads(request.data).get('status')
    check_tweet(config, status)



@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_remove_queued_tweet(*args, **kwargs):
    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    index = json.loads(request.data).get('index')
    config.tweet_queue.pop(index)


@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_send_queued_tweet(*args, **kwargs):
    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    status = json.loads(request.data).get('status')
    if isinstance(status, unicode):
        status = status.encode("utf-8")
    index = int(json.loads(request.data).get('index'))
    config.tweet_queue.pop(index)
    check_tweet(config, status)


@must_be_contributor_or_public
@must_have_addon('twitter', 'node')
def twitter_tweet_queue(*args, **kwargs):
    node = kwargs.get('node') or kwargs.get('project')
    config = node.get_addon('twitter')
    return {'key': config.tweet_queue}
