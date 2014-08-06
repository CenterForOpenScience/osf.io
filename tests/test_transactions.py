# -*- coding: utf-8 -*-

import unittest
from nose.tools import *
from tests.base import OsfTestCase

from pymongo.errors import CollectionInvalid

from framework.mongo import client
from framework.transactions import context


TEST_COLLECTION_NAME = 'transactions'


class TestTransactionContext(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestTransactionContext, cls).setUpClass()
        cls.database = client[cls.db_name]
        try:
            cls.database.create_collection('transaction')
        except CollectionInvalid:
            pass
        cls.collection = cls.database[TEST_COLLECTION_NAME]

    def tearDown(self):
        super(TestTransactionContext, self).tearDown()
        self.collection.remove()

    def test_commit(self):
        with context.TokuTransaction(self.database) as txn:
            self.collection.insert({'hammer': 'to fall'})
            assert_true(txn.pending)
        assert_equal(self.collection.count(), 1)

    def test_exception_triggers_rollback(self):
        with assert_raises(Exception):
            with context.TokuTransaction(self.database):
                self.collection.insert({'hammer': 'to fall'})
                raise Exception
        assert_equal(self.collection.count(), 0)

    def test_nested_contexts(self):
        with context.TokuTransaction(self.database) as txn1:
            self.collection.insert({'stone': 'cold'})
            with context.TokuTransaction(self.database) as txn2:
                self.collection.insert({'crazy': 'yeah'})
                assert_true(txn1.pending)
                assert_false(txn2.pending)
        assert_equal(self.collection.count(), 2)

    def test_nested_exception_triggers_rollback(self):
        with assert_raises(Exception):
            with context.TokuTransaction(self.database):
                self.collection.insert({'stone': 'cold'})
                with context.TokuTransaction(self.database):
                    self.collection.insert({'crazy': 'yeah'})
                    raise Exception
        assert_equal(self.collection.count(), 0)


if __name__ == '__main__':
    unittest.run()
