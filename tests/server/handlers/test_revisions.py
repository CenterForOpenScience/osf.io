import json
from unittest import mock

from tornado import testing

from tests import utils


class TestRevisionHandler(utils.HandlerTestCase):

    @testing.gen_test
    def test_get_coro(self):
        expected = {
            'data': [
                {'name': 'version-one'},
                {'name': 'version-two'},
            ]
        }

        self.mock_provider.revisions = utils.MockCoroutine(return_value=expected['data'])

        resp = yield self.http_client.fetch(
            self.get_url('/revisions?provider=queenhub&path=/brian.tiff'),
        )

        assert expected == json.loads(resp.body.decode())

    @testing.gen_test
    def test_get_not_coro(self):
        expected = {
            'data': [
                {'name': 'version-one'},
                {'name': 'version-two'},
            ]
        }

        self.mock_provider.revisions = mock.Mock(return_value=expected['data'])

        resp = yield self.http_client.fetch(
            self.get_url('/revisions?provider=queenhub&path=/brian.tiff'),
        )

        assert expected == json.loads(resp.body.decode())
