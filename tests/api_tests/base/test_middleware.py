# -*- coding: utf-8 -*-

from tests.base import ApiTestCase, fake

import mock
from nose.tools import *  # flake8: noqa

from api.base.middleware import TokuTransactionsMiddleware
from tests.base import ApiTestCase

class TestMiddlewareRollback(ApiTestCase):
    
    @mock.patch('api.base.middleware.commands')
    def test_400_error_causes_rollback(self, mock_commands):

        middleware = TokuTransactionsMiddleware()
        mock_response = mock.Mock()
        mock_response.status_code = 400
        middleware.process_response(mock.Mock(), mock_response)

        assert_is(mock_commands.rollback.assert_called_once_with(), None)

