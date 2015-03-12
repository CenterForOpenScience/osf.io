import asyncio
import xmltodict

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings
from waterbutler.providers.dataverse.metadata import DataverseFileMetadata, DataverseDatasetMetadata
from waterbutler.providers.dataverse import utils as dataverse_utils


class DataversePath(utils.WaterButlerPath):

    def __init__(self, path, doi=None, prefix=True, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)

        self._path = path
        self._doi = doi

        @property
        def path(self):
            return self._path


class DataverseProvider(provider.BaseProvider):

    EDIT_MEDIA_BASE_URL = settings.EDIT_MEDIA_BASE_URL
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

        # zip_stream = streams.ZipStreamReader(stream)
        stream.__class__ = streams.ZipStreamReader
        stream.initialize()
        # import ipdb; ipdb.set_trace()
        dv_headers = {
            "Content-Disposition": "filename=temp.zip",
            "Content-Type": "application/zip",
            "Packaging": "http://purl.org/net/sword/package/SimpleZip",
            "Content-Length": str(stream.size),
        }
        yield from self.make_request(
            'POST',
            provider.build_url(self.EDIT_MEDIA_BASE_URL, 'study', self.doi),
            headers=dv_headers,
            auth=(self.token, ),
            data=stream,
            expects=(201, ),
            throws=exceptions.UploadError
        )

        # Find appropriate version of file from metadata url
        data = yield from self.metadata()
        filename, version = dataverse_utils.unpack_filename(path.strip('/'))

        # Reduce to files of the same base name of the same/higher version
        data = sorted([
            f for f in data
            if f['extra']['original'] == filename
            and f['extra']['version'] >= version
        ], key=lambda f: f['extra']['version'])

        # Find highest version from original without a gap in between
        for item in data:
            if item['extra']['version'] == version:
                highest_compatible = item
                version += 1
            else:
                break

        return highest_compatible, True


    @asyncio.coroutine
    def delete(self, path, **kwargs):
        yield from self.make_request(
            'DELETE',
            provider.build_url(self.EDIT_MEDIA_BASE_URL, 'file', path),
            auth=(self.token, ),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, **kwargs):
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
