import asyncio
import http
import tempfile
import xmltodict

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings
from waterbutler.providers.dataverse.metadata import DataverseDatasetMetadata
from waterbutler.providers.dataverse import utils as dataverse_utils


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

        filename = path.strip('/')

        stream = streams.ZipStreamReader(
            filename=filename,
            file_stream=stream,
        )

        # Write stream to disk (Necessary to find zip file size)
        f = tempfile.TemporaryFile()
        chunk = yield from stream.read()
        while chunk:
            f.write(chunk)
            chunk = yield from stream.read()
        stream = streams.FileStreamReader(f)

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
        filename, version = dataverse_utils.unpack_filename(filename)
        highest_compatible = None

        # Reduce to files of the same base name of the same/higher version
        filtered_data = sorted([
            f for f in data
            if f['extra']['original'] == filename
            and f['extra']['version'] >= version
        ], key=lambda f: f['extra']['version'])

        # Find highest version from original without a gap in between
        for item in filtered_data:
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
    def metadata(self, path='/', state='draft', **kwargs):
        url = provider.build_url(self.METADATA_BASE_URL, self.doi)
        resp = yield from self.make_request(
            'GET',
            url,
            auth=(self.token, ),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from resp.text()
        data = xmltodict.parse(data)

        dataset_metadata = DataverseDatasetMetadata(data, state).serialized()

        # Dataset metadata
        if path == '/':
            return dataset_metadata

        # File metadata
        else:
            try:
                return next(
                    item for item in dataset_metadata if item['path'] == path
                )
            except StopIteration:
                raise exceptions.MetadataError(
                    "Could not retrieve file '{}'".format(path),
                    code=http.client.NOT_FOUND,
                )
