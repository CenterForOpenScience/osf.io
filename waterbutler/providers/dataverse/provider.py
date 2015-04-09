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

    BASE_URL = 'https://{0}'.format(settings.HOSTNAME)
    EDIT_MEDIA_BASE_URL = settings.EDIT_MEDIA_BASE_URL
    DOWN_BASE_URL = settings.DOWN_BASE_URL
    METADATA_BASE_URL = settings.METADATA_BASE_URL
    JSON_BASE_URL = settings.JSON_BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.doi = self.settings['doi']
        self.id = self.settings['id']
        self.name = self.settings['name']

    @asyncio.coroutine
    def download(self, path, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.build_url(self.DOWN_BASE_URL, path, key=self.token),
            expects=(200, ),
            throws=exceptions.DownloadError,
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
            self.build_url(self.EDIT_MEDIA_BASE_URL, 'study', self.doi),
            headers=dv_headers,
            auth=(self.token, ),
            data=stream,
            expects=(201, ),
            throws=exceptions.UploadError
        )

        # Find appropriate version of file from metadata url
        data = yield from self.metadata(state='draft')
        filename, version = dataverse_utils.unpack_filename(filename)
        highest_compatible = None

        # Reduce to files of the same base name of the same/higher version
        filtered_data = sorted([
            data_file for data_file in data
            if data_file['extra']['original'] == filename and
            data_file['extra']['version'] >= version
        ], key=lambda x: x['extra']['version'])

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
            self.build_url(self.EDIT_MEDIA_BASE_URL, 'file', path),
            auth=(self.token, ),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path='/', state=None, **kwargs):

        # Get appropriate metadata
        if state == 'draft':
            dataset_metadata = yield from self.get_draft_data()
        elif state == 'published':
            dataset_metadata = yield from self.get_published_data()
        else:
            dataset_metadata = yield from self.get_all_data()

        if path == '/':
            return dataset_metadata

        try:
            return next(
                item for item in dataset_metadata if item['path'] == path
            )
        except StopIteration:
            raise exceptions.MetadataError(
                "Could not retrieve file '{}'".format(path),
                code=http.client.NOT_FOUND,
            )

    @asyncio.coroutine
    def get_draft_data(self):
        url = self.build_url(self.METADATA_BASE_URL, self.doi)
        resp = yield from self.make_request(
            'GET',
            url,
            auth=(self.token, ),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from resp.text()
        data = xmltodict.parse(data)

        return DataverseDatasetMetadata(
            data, self.name, self.doi, native=False
        ).serialized()

    @asyncio.coroutine
    def get_published_data(self):
        url = self.build_url(self.JSON_BASE_URL.format(self.id), key=self.token)
        resp = yield from self.make_request(
            'GET',
            url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()
        data = data['data']

        return DataverseDatasetMetadata(
            data, self.name, self.doi, native=True
        ).serialized()

    @asyncio.coroutine
    def get_all_data(self):
        # Unspecified (file view page), check both sets for metadata
        published_data = yield from self.get_published_data()
        published_files = published_data if isinstance(published_data, list) else []
        draft_data = yield from self.get_draft_data()
        draft_files = draft_data if isinstance(draft_data, list) else []
        return published_files + draft_files