# -*- coding: utf-8 -*-

import logging

import mock
import webtest_plus
import unittest
from nose.tools import *
from tests.base import DbTestCase, OsfTestCase

from flask import make_response
from pymongo.errors import CollectionInvalid, OperationFailure

from framework.flask import add_handlers
from framework.mongo import database
from framework.mongo import handlers as database_handlers
from framework.transactions import context, handlers, commands, messages, utils

from flask import Flask, abort
app = Flask('test_transactions_app')
@app.route('/')
def dummy_view():
    return 'dummy'


TEST_COLLECTION_NAME = 'transactions'

app.logger.setLevel(logging.CRITICAL)

SILENT_LOGGERS = ['framework.transactions.handlers', 'framework.transactions.context']

for each in SILENT_LOGGERS:
    logger = logging.getLogger(each)
    logger.setLevel(logging.CRITICAL)


class TestTransactionContext(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestTransactionContext, cls).setUpClass()
        try:
            database.create_collection('transaction')
        except CollectionInvalid:
            pass
        cls.collection = database[TEST_COLLECTION_NAME]

    def tearDown(self):
        super(TestTransactionContext, self).tearDown()
        self.collection.remove()

    def test_commit(self):
        with context.TokuTransaction(database) as txn:
            self.collection.insert({'hammer': 'to fall'})
            assert_true(txn.pending)
        assert_equal(self.collection.count(), 1)

    def test_exception_triggers_rollback(self):
        with assert_raises(Exception):
            with context.TokuTransaction(database):
                self.collection.insert({'hammer': 'to fall'})
                raise Exception
        assert_equal(self.collection.count(), 0)

    def test_nested_contexts(self):
        with context.TokuTransaction(database) as txn1:
            self.collection.insert({'stone': 'cold'})
            with context.TokuTransaction(database) as txn2:
                self.collection.insert({'crazy': 'yeah'})
                assert_true(txn1.pending)
                assert_false(txn2.pending)
        assert_equal(self.collection.count(), 2)

    def test_nested_exception_triggers_rollback(self):
        with assert_raises(Exception):
            with context.TokuTransaction(database):
                self.collection.insert({'stone': 'cold'})
                with context.TokuTransaction(database):
                    self.collection.insert({'crazy': 'yeah'})
                    raise Exception
        assert_equal(self.collection.count(), 0)



class TestTransactionHandlers(DbTestCase):

    def clear_transactions(self):
        try:
            commands.rollback()
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if messages.NO_TRANSACTION_ERROR not in message:
                raise

    def setUp(self):
        super(TestTransactionHandlers, self).setUp()
        self.clear_transactions()
        self.context = app.test_request_context('/')
        self.context.push()

    def tearDown(self):
        super(TestTransactionHandlers, self).tearDown()
        self.clear_transactions()
        self.context.pop()

    def test_before_request(self):
        handlers.transaction_before_request()
        transactions = database.command('showLiveTransactions')
        assert_equal(len(transactions['transactions']), 1)

    def test_before_request_transaction_active(self):
        commands.begin()
        transactions_before = database.command('showLiveTransactions')
        handlers.transaction_before_request()
        transactions = database.command('showLiveTransactions')
        assert_equal(len(transactions['transactions']), 1)
        assert_not_equal(
            transactions_before['transactions'][0]['txnid'],
            transactions['transactions'][0]['txnid'],
        )

    @mock.patch('framework.transactions.commands.rollback')
    def test_before_request_unexpected_error(self, mock_rollback):
        mock_rollback.side_effect = OperationFailure('daamn!')
        with assert_raises(OperationFailure):
            handlers.transaction_before_request()

    def test_after_request(self):
        commands.begin()
        key = 'test_after_request'
        database['txn'].insert({'_id': key})
        response = make_response('bob', 200)
        handlers.transaction_after_request(response)
        transactions = database.command('showLiveTransactions')
        assert_equal(len(transactions['transactions']), 0)
        assert_equal(
            database['txn'].find({'_id': key}).count(),
            1,
        )

    def test_after_request_uncaught_exception(self):
        commands.begin()
        key = 'test_after_request_uncaught_exception'
        database['txn'].insert({'_id': key})
        response = make_response('ack!', 500)
        handlers.transaction_after_request(response)
        transactions = database.command('showLiveTransactions')
        assert_equal(len(transactions['transactions']), 0)
        assert_equal(
            database['txn'].find({'_id': key}).count(),
            0,
        )

    def test_after_request_lock_error(self):
        commands.begin()
        key = 'test_after_request_lock_error'
        database['txn'].insert({'_id': key})
        with app.test_request_context(content_type='application/json'):
            response = make_response('bob', 200)
            with mock.patch('framework.transactions.commands.commit') as mock_commit:
                mock_commit.side_effect = OperationFailure(messages.LOCK_ERROR)
                handlers.transaction_after_request(response)
        transactions = database.command('showLiveTransactions')
        assert_equal(len(transactions['transactions']), 0)
        assert_equal(
            database['txn'].find({'_id': key}).count(),
            0,
        )


transaction_app = Flask('test_transactions_app')

add_handlers(transaction_app, database_handlers.handlers)
add_handlers(transaction_app, handlers.handlers)


@transaction_app.route('/transact/me/bro/', methods=['GET'])
def transaction_view():
    return make_response()


@handlers.no_auto_transaction
@transaction_app.route('/dont/transact/me/bro/', methods=['GET'])
def no_transaction_view():
    return make_response()


@transaction_app.route('/seriously/bro/', methods=['GET'])
@handlers.no_auto_transaction
def no_transaction_view_reverse_decorators():
    return make_response()


test_app = webtest_plus.TestApp(transaction_app)


class TestSkipTransactions(DbTestCase):

    @mock.patch('framework.transactions.commands.commit')
    @mock.patch('framework.transactions.commands.rollback')
    @mock.patch('framework.transactions.commands.begin')
    def test_no_skip(self, mock_begin, mock_rollback, mock_commit):
        test_app.get('/transact/me/bro/')
        assert_true(mock_begin.called)
        assert_true(mock_rollback.called)
        assert_true(mock_commit.called)

    @mock.patch('framework.transactions.commands.commit')
    @mock.patch('framework.transactions.commands.rollback')
    @mock.patch('framework.transactions.commands.begin')
    def test_skip_transaction(self, mock_begin, mock_rollback, mock_commit):
        test_app.get('/dont/transact/me/bro/')
        assert_false(mock_begin.called)
        assert_false(mock_rollback.called)
        assert_false(mock_commit.called)

    @mock.patch('framework.transactions.commands.commit')
    @mock.patch('framework.transactions.commands.rollback')
    @mock.patch('framework.transactions.commands.begin')
    def test_skip_transaction_reverse_decorators(self, mock_begin, mock_rollback, mock_commit):
        test_app.get('/seriously/bro/')
        assert_false(mock_begin.called)
        assert_false(mock_rollback.called)
        assert_false(mock_commit.called)


@transaction_app.route('/write/without/errors/', methods=['POST'])
def write_without_errors():
    database['txn'].insert({'_id': 'success'})
    return 'success'


@transaction_app.route('/write/with/error/500/', methods=['POST'])
def write_with_error_500():
    database['txn'].insert({'_id': 'error_500'})
    abort(500)


@transaction_app.route('/write/with/error/uncaught/', methods=['POST'])
def write_with_error_uncaught():
    database['txn'].insert({'_id': 'error_uncaught'})
    raise Exception


class TestTransactionIntegration(DbTestCase):

    def test_commit_if_no_error(self):
        test_app.post('/write/without/errors/')
        assert_equal(
            database['txn'].find({'_id': 'success'}).count(),
            1,
        )

    def test_rollback_if_error_500(self):
        test_app.post('/write/with/error/500/', expect_errors=True)
        assert_equal(
            database['txn'].find({'_id': 'error_500'}).count(),
            0,
        )

    def test_rollback_if_error_uncaught(self):
        test_app.post('/write/with/error/uncaught/', expect_errors=True)
        assert_equal(
            database['txn'].find({'_id': 'error_uncaught'}).count(),
            0,
        )


if __name__ == '__main__':
    unittest.run()

