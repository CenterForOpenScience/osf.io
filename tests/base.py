# -*- coding: utf-8 -*-
'''Base TextCase class for OSF unittests. Uses a temporary MongoDB database.'''
import os
import unittest

from pymongo import MongoClient

from framework import storage, set_up_storage
from framework.auth.model import User
from framework.sessions.model import Session
from framework.search.model import Keyword
from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)

from new_style import app

# All Models
MODELS = (User, ApiKey, Keyword, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session)


class DbTestCase(unittest.TestCase):
    '''Base TestCase for tests that require a temporary MongoDB database.
    '''
    # DB settings
    db_name = os.environ.get('MONGO_DATABASE', 'osf_test')
    db_host = os.environ.get('MONGO_HOST', 'localhost')
    db_port = int(os.environ.get('MONGO_PORT', '20771'))

    @classmethod
    def setUpClass(klass):
        '''Before running this TestCase, set up a temporary MongoDB database'''
        klass._client = MongoClient(host=klass.db_host, port=klass.db_port)
        klass.db = klass._client[klass.db_name]
        # Set storage backend to MongoDb
        set_up_storage(MODELS, storage.MongoStorage, db=klass.db)

    @classmethod
    def tearDownClass(klass):
        '''Drop the database when all tests finish.'''
        klass._client.drop_database(klass.db)


class AppTestCase(unittest.TestCase):
    '''Base TestCase for OSF tests that require the WSGI app (but no database).
    '''

    def setUp(self):
        self.app = app
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
