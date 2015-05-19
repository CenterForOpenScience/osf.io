import asyncio
import io
import zipfile
from unittest import mock

from tornado import testing

from waterbutler.core import streams

from tests import utils


class TestZipHandler(utils.HandlerTestCase):

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
    def test_download_stream(self, mock_make_provider):
        stream = asyncio.StreamReader()
        data = b'freddie brian john roger'
        stream.feed_data(data)
        stream.feed_eof()
        stream.size = len(data)
        stream.content_type = 'application/octet-stream'

        zipstream = streams.ZipStreamReader(('file.txt', stream))

        mock_provider = utils.mock_provider_method(mock_make_provider,
                                                   'zip',
                                                   zipstream)
        resp = yield self.http_client.fetch(
            self.get_url('/zip?provider=queenhub&path=freddie.png'),
        )

        zip = zipfile.ZipFile(io.BytesIO(resp.body))

        assert zip.testzip() is None

        assert zip.open('file.txt').read() == data