import asyncio
import io
import zipfile
from unittest import mock

from tornado import testing

from waterbutler.core import streams

from tests import utils


class TestZipHandler(utils.HandlerTestCase):

    @testing.gen_test
    def test_download_stream(self):
        data = b'freddie brian john roger'
        stream = streams.StringStream(data)
        stream.content_type = 'application/octet-stream'

        zipstream = streams.ZipStreamReader(('file.txt', stream))

        self.mock_provider.zip = utils.MockCoroutine(return_value=zipstream)

        resp = yield self.http_client.fetch(
            self.get_url('/zip?provider=queenhub&path=/freddie.png'),
        )

        zip = zipfile.ZipFile(io.BytesIO(resp.body))

        assert zip.testzip() is None

        assert zip.open('file.txt').read() == data
