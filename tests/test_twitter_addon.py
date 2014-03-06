from __future__ import absolute_import
import json
import unittest
import datetime as dt

from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp

import website.app
from website.models import Node, NodeLog
from website.project.model import ensure_schemas
import tweepy
from tests.base import DbTestCase
from tests.factories import (UserFactory, ApiKeyFactory, ProjectFactory,
                            WatchConfigFactory, NodeFactory, NodeLogFactory)

class Test_Twitter_Addon(DbTestCase):


def test_auth_dance(self):
#Create OAuthHandler object
    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
    auth= tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    oauth_key =  '325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy'
    oauth_secret = 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb'
    auth.set_access_token(oauth_key, oauth_secret)

    api = tweepy.API(auth)
    assert_equal(api.me().username, 'Phresh_Phish')
    assert_equal(api.verify_credentials()._api, api)


def test_status(self):
#oauth dance
    consumer_key = 'rohTTQSPWzgIXWw0g5dw'
    consumer_secret = '7pmpjEtvoGjnSNCN2GlULrV104uVQQhg60Da7MEEy0'
    auth= tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    oauth_key =  '325216328-OrWD6qHU01Ovc3HLg1cyXno0kbjRLuFpE2byvXqy'
    oauth_secret = 'dJTzVdKSa37sV1X82YXJjV2KPgPoQjuZDH2MDRNnDLixb'
    auth.set_access_token(oauth_key, oauth_secret)
    api = tweepy.API(auth)
#send a tweet and test if tweet count increments
    message = 'testing this message'
    previous_count = api.me().statuses_count
    api.update_status(message)
    assert_equal(previous_count+1, api.me().statuses_count)




    #       test changing displayed tweets
    #       test updating action (add and delete)
    #       test updating custom message()
    #       test tweets that are too long
    #