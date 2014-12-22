import pytest

import json
import asyncio
from unittest import mock

from tornado import testing
from tornado import httpclient

from waterbutler.core import streams
from waterbutler.core import exceptions

from tests import utils


class TestCrudHandler(utils.HandlerTestCase):

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

    @mock.patch('waterbutler.server.handlers.core.make_provider')
    @testing.gen_test
    def test_download_redirect(self, mock_make_provider):
        redirect_url = 'http://queen.com/freddie.png'
        mock_provider = utils.mock_provider_method(mock_make_provider, 'download', redirect_url)
        with pytest.raises(httpclient.HTTPError) as exc:
            resp = yield self.http_client.fetch(
                self.get_url('/file?provider=queenhub&path=freddie.png'),
                follow_redirects=False,
            )
        assert exc.value.code == 302
        assert exc.value.response.headers.get('Location') == redirect_url
        calls = mock_provider.download.call_args_list
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert kwargs.get('action') == 'download'

    @mock.patch('waterbutler.server.handlers.core.make_provider')
    @testing.gen_test
    def test_download_stream(self, mock_make_provider):
        stream = asyncio.StreamReader()
        data = b'freddie brian john roger'
        stream.feed_data(data)
        stream.feed_eof()
        stream.size = len(data)
        stream.content_type = 'application/octet-stream'
        mock_provider = utils.mock_provider_method(mock_make_provider, 'download', stream)
        resp = yield self.http_client.fetch(
            self.get_url('/file?provider=queenhub&path=freddie.png'),
        )
        assert resp.body == data
        calls = mock_provider.download.call_args_list
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert kwargs.get('action') == 'download'

    @mock.patch('waterbutler.server.handlers.core.make_provider')
    @testing.gen_test
    def test_download_not_found(self, mock_make_provider):
        utils.mock_provider_method(mock_make_provider, 'download', side_effect=exceptions.DownloadError('missing'))
        with pytest.raises(httpclient.HTTPError) as exc:
            resp = yield self.http_client.fetch(
                self.get_url('/file?provider=queenhub&path=freddie.png'),
            )

    @mock.patch('waterbutler.server.handlers.core.make_provider')
    @testing.gen_test
    def test_upload(self, mock_make_provider):
        data = b'stone cold crazy'
        expected = {'path': 'roger.png'}
        mock_provider = utils.mock_provider_method(mock_make_provider, 'upload', expected)
        resp = yield self.http_client.fetch(
            self.get_url('/file?provider=queenhub&path=roger.png'),
            method='PUT',
            body=data,
        )
        calls = mock_provider.upload.call_args_list
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert isinstance(args[0], streams.RequestStreamReader)
        streamed = asyncio.new_event_loop().run_until_complete(args[0].read())
        assert streamed == data
        assert kwargs.get('action') == 'upload'
        assert kwargs.get('path') == 'roger.png'
        assert expected == json.loads(resp.body.decode())

    @mock.patch('waterbutler.server.handlers.core.make_provider')
    @testing.gen_test
    def test_delete(self, mock_make_provider):
        mock_provider = utils.mock_provider_method(mock_make_provider, 'delete', '')
        resp = yield self.http_client.fetch(
            self.get_url('/file?provider=queenhub&path=john.png'),
            method='DELETE',
        )
        calls = mock_provider.delete.call_args_list
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert kwargs.get('action') == 'delete'
        assert resp.code == 204
