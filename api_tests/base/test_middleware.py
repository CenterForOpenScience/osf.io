# -*- coding: utf-8 -*-

from tests.base import ApiTestCase, fake

import mock
from nose.tools import *  # flake8: noqa

from api.base.middleware import TokuTransactionMiddleware
from tests.base import ApiTestCase

class TestMiddlewareRollback(ApiTestCase):
    def setUp(self):
        super(TestMiddlewareRollback, self).setUp()
        self.middleware = TokuTransactionMiddleware()
        self.mock_response = mock.Mock()
    
    @mock.patch('framework.transactions.handlers.commands')
    def test_400_error_causes_rollback(self, mock_commands):

        self.mock_response.status_code = 400
        self.middleware.process_response(mock.Mock(), self.mock_response)

        assert_true(mock_commands.rollback.called)

    @mock.patch('framework.transactions.handlers.commands')
    def test_200_OK_causes_commit(self, mock_commands):

        self.mock_response.status_code = 200
        self.middleware.process_response(mock.Mock(), self.mock_response)

        assert_true(mock_commands.commit.called)
