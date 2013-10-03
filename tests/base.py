# -*- coding: utf-8 -*-
'''Base TextCase class for OSF unittests. Uses a temporary MongoDB database.'''
import os
import unittest

from pymongo import MongoClient
from framework import storage, set_up_storage
from framework.auth.model import User
from framework.search.model import Keyword
from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)

MODELS = (User, ApiKey, Keyword, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig)


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
