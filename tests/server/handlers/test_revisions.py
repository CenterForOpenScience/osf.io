import json
import asyncio
from unittest import mock

from tornado import testing

from tests import utils


class TestRevisionHandler(utils.HandlerTestCase):

    def setUp(self):
        super().setUp()
        identity_future = asyncio.Future()
        identity_future.set_result({
            'auth': {},
            'credentials': {},
            'settings': {},
        })
        self.mock_identity = mock.Mock()
        self.mock_identity.return_value = identity_future
        self.identity_patcher = mock.patch('waterbutler.server.handlers.core.get_identity', self.mock_identity)
        self.identity_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.identity_patcher.stop()

    @mock.patch('waterbutler.core.utils.make_provider')
    @testing.gen_test
    def test_get_coro(self, mock_make_provider):
        expected = {
            'data': [
                {'name': 'version-one'},
                {'name': 'version-two'},
            ]
        }
        mock_provider = utils.mock_provider_method(mock_make_provider, 'revisions', expected['data'])
        resp = yield self.http_client.fetch(
            self.get_url('/revisions?provider=queenhub&path=brian.tiff'),
        )
        assert expected == json.loads(resp.body.decode())

    @mock.patch('waterbutler.core.utils.make_provider')
    @testing.gen_test
    def test_get_not_coro(self, mock_make_provider):
        expected = {
            'data': [
                {'name': 'version-one'},
                {'name': 'version-two'},
            ]
        }
        mock_provider = utils.mock_provider_method(mock_make_provider, 'revisions', expected['data'], as_coro=False)
        resp = yield self.http_client.fetch(
            self.get_url('/revisions?provider=queenhub&path=brian.tiff'),
        )
        assert expected == json.loads(resp.body.decode())
