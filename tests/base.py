# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import unittest

from pymongo import MongoClient

from framework import storage, set_up_storage
from framework.auth.model import User
from framework.sessions.model import Session
from framework.guid.model import Guid
from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig, MetaData)
from website import settings


# All Models
MODELS = (User, ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session, MetaData, Guid)

import website.models
from website.app import init_app

# Just a simple app without routing set up or backends
test_app = init_app(settings_module="website.settings", routes=False, set_backends=False)

class DbTestCase(unittest.TestCase):
    '''Base TestCase for tests that require a temporary MongoDB database.
    '''
    # DB settings
    db_name = getattr(settings, 'TEST_DB_NAME', 'osf_test')
    db_host = getattr(settings, 'MONGO_HOST', 'localhost')
    db_port = int(getattr(settings, 'DB_PORT', '20771'))

    @classmethod
    def setUpClass(klass):
        '''Before running this TestCase, set up a temporary MongoDB database'''
        klass._client = MongoClient(host=klass.db_host, port=klass.db_port)
        klass.db = klass._client[klass.db_name]
        # Set storage backend to MongoDb
        set_up_storage(
            website.models.MODELS, storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE, db=klass.db,
        )

    @classmethod
    def tearDownClass(klass):
        '''Drop the database when all tests finish.'''
        klass._client.drop_database(klass.db)


class AppTestCase(unittest.TestCase):
    '''Base TestCase for OSF tests that require the WSGI app (but no database).
    '''

    def setUp(self):
        self.app = test_app
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
