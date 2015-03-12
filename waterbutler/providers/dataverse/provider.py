import asyncio
import xmltodict

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings
from waterbutler.providers.dataverse.metadata import DataverseFileMetadata, DataverseDatasetMetadata


class DataversePath(utils.WaterButlerPath):

    def __init__(self, path, doi=None, prefix=True, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)

        self._path = path
        self._doi = doi

        @property
        def path(self):
            return self._path


class DataverseProvider(provider.BaseProvider):

    UP_BASE_URL = settings.UP_BASE_URL
    DOWN_BASE_URL = settings.DOWN_BASE_URL
    METADATA_BASE_URL = settings.METADATA_BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.doi = self.settings['doi']

    @asyncio.coroutine
    def download(self, path, **kwargs):
        resp = yield from self.make_request(
            'GET',
            provider.build_url(self.DOWN_BASE_URL, path),
            expects=(200, ),
            throws=exceptions.DownloadError,
            params={'key': self.token},
        )
        return streams.ResponseStreamReader(resp)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        #TODO deleteme
        _next = next
        def unwrap(f):
            result = yield from f
            return result

        path = DataversePath(self.doi, path)

        try:
            yield from self.metadata(str(path))
        except exceptions.MetadataError:
            created = True
        else:
            created = False

        dv_headers = {
            "Content-Disposition": "filename={0}".format(path),
            "Content-Type": "application/zip",
            "Packaging": "http://purl.org/net/sword/package/SimpleZip",
            "Content-Length": str(stream.size),
        }
        zip_stream = streams.ZipStreamReader(stream)
        import pdb; pdb.set_trace()
        resp = yield from self.make_request(
            'POST',
            provider.build_url(settings.UP_BASE_URL, self.doi),
            headers=dv_headers,
            auth=(self.token, ),
            data=zip_stream,
            expects=(200, ),
            throws=exceptions.UploadError
        )
        
        data = yield from resp.json()
        return DataverseFileMetadata(data, self.folder).serialized(), created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        path = DataversePath(path, self.doi)

        # A metadata call will verify the path specified is actually the
        # requested file or folder.
        yield from self.metadata(str(path))

        yield from self.make_request(
            'POST',
            self.build_url('fileops', 'delete'),
            data={'root': 'auto', 'path': path.path},
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        url = provider.build_url(settings.METADATA_BASE_URL, self.doi)
        resp = yield from self.make_request(
            'GET',
            url,
            auth=(self.token, ),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from resp.text()
        data = xmltodict.parse(data)

        return DataverseDatasetMetadata(data).serialized()
