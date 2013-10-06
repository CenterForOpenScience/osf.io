# -*- coding: utf-8 -*-
'''Base TextCase class for OSF unittests. Uses a temporary MongoDB database.'''
import os
from base64 import b64encode
import unittest

import webtest
from pymongo import MongoClient

from framework import storage, set_up_storage
from framework.auth.model import User
from framework.sessions.model import Session
from framework.search.model import Keyword
from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)

# All Models
MODELS = (User, ApiKey, Keyword, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session)


class OsfTestCase(unittest.TestCase):

    '''Base TestCase for OSF unittests. Creates a test database and destroys it
    after the tests are finished.
    '''

    db_name = os.environ.get('MONGO_DATABASE', 'osf_test')
    db_host = os.environ.get('MONGO_HOST', 'localhost')
    db_port = int(os.environ.get('MONGO_PORT', '20771'))

    @classmethod
    def setUpClass(klass):
        klass._client = MongoClient(host=klass.db_host, port=klass.db_port)
        klass.db = klass._client[klass.db_name]
        # Set storage backend to MongoDb
        set_up_storage(MODELS, storage.MongoStorage, db=klass.db)

    @classmethod
    def tearDownClass(klass):
        klass._client.drop_database(klass.db)

##### WebTest ####

def _basic_auth_str(username, password):
    """Returns a Basic Auth string."""
    return 'Basic ' + b64encode(('%s:%s' % (username, password)).encode('latin1')).strip().decode('latin1')


def _add_auth(auth, headers):
    '''Adds authentication key to headers.'''
    headers = headers or {}
    if isinstance(auth, (tuple, list)) and len(auth) == 2:
        headers["Authorization"] = str(_basic_auth_str(*auth))
    return headers


class TestApp(webtest.TestApp):
    '''A modified webtest.TestApp with useful features such as
    requests-style authentication and auto_follow.
    '''

    # TODO(sloria): Add ability to pass in a User object (like django-webtest)?
    def get(self, url, params=None, headers=None, extra_environ=None,
            status=None, expect_errors=False, auth=None, auto_follow=False,
            content_type=None):
        if auth:
            headers = _add_auth(auth, headers)
        response = super(TestApp, self).get(
                        url, params, headers, extra_environ, status, expect_errors)
        is_redirect = lambda r: r.status_int >= 300 and r.status_int < 400
        while auto_follow and is_redirect(response):
            response = response.follow()
        return response

    def post(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False,
             content_type=None, auth=None):
        if auth:
            headers = _add_auth(auth, headers)
        return super(TestApp, self).post(
                    url, params, headers, extra_environ, status,
                    upload_files, expect_errors, content_type)

    def put(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False,
             content_type=None, auth=None):
        if auth:
            headers = _add_auth(auth, headers)
        return super(TestApp, self).put(
                    url, params, headers, extra_environ, status,
                    upload_files, expect_errors, content_type)

    def patch(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False,
             content_type=None, auth=None):
        if auth:
            headers = _add_auth(auth, headers)
        return super(TestApp, self).patch(
                    url, params, headers, extra_environ, status,
                    upload_files, expect_errors, content_type)

    def options(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False,
             content_type=None, auth=None):
        if auth:
            headers = _add_auth(auth, headers)
        return super(TestApp, self).options(
                    url, params, headers, extra_environ, status)

    def delete(self, url, params='', headers=None, extra_environ=None,
             status=None, expect_errors=False,
             content_type=None, auth=None):
        if auth:
            headers = _add_auth(auth, headers)
        return super(TestApp, self).delete(
                        url, params, headers, extra_environ, status,
                        expect_errors, content_type)
