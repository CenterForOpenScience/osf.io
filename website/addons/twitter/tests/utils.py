import mock
import tweepy
from framework.status import push_status_message

from tweepy import Cursor
import httplib as http
import os
import json
import ctypes
from framework import request, redirect
from framework.sessions import session#, get_session, set_session, create_session
from framework.exceptions import HTTPError
from website import models
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public
from framework.status import push_status_message
from framework.auth import get_current_user
from website import settings
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import AddonError
from framework.status import push_status_message
#
#
#def create_mock_twitter(username = 'Phresh_phish'):
#    twitter_mock = mock.create_mock_twitter(username = 'Phresh_phish')
#    twitter_mock.auth.return_value =
#    {
#        'OAUTH_HOST': 'api.twitter.com',
#        'OAUTH_ROOT': '/oauth/',
#        '_consumer': {'key':'rohTTQSPWzgIXWw0g5dw',
#                    'secret': '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
#        },
#        'access_token': {'callback': None,
#                         'callback_confirmed': None,
#                         'key':'',
#                         'secret':'',
#                         'verifier':''
#        },
#        'callback': '',
#        'request_token':{ 'callback': None,
#                         'callback_confirmed': None,
#                         'key':'',
#                         'secret':'',
#                         'verifier':''
#    },
#        'secure': True,
#        'username': "".format()
#
#
#
#    }




def send_tweet(twitter_node_settings, message):
    auth = tweepy.OAuthHandler(twitter_node_settings.CONSUMER_KEY, twitter_node_settings.CONSUMER_SECRET, secure=True)
    auth.set_access_token(twitter_node_settings.oauth_key, twitter_node_settings.oauth_secret)
    api = tweepy.API(auth)
    api.update_status(message)


