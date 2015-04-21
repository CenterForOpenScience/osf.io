import asyncio
import http
import tempfile

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings
from waterbutler.providers.dataverse.metadata import DataverseRevision
from waterbutler.providers.dataverse.metadata import DataverseDatasetMetadata


class DataverseProvider(provider.BaseProvider):

    BASE_URL = 'https://{0}'.format(settings.HOSTNAME)

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.token = self.credentials['token']
        self.doi = self.settings['doi']
        self._id = self.settings['id']
        self.name = self.settings['name']

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        # Can download draft or published files
        if revision:
            metadata = yield from self._get_data(revision)
        else:
            metadata = yield from self._get_all_data()
        self._validate_path(path, metadata)

        resp = yield from self.make_request(
            'GET',
            self.build_url(settings.DOWN_BASE_URL, path, key=self.token),
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

        # Delete old file if it exists
        metadata = yield from self._get_data('latest')
        files = metadata if isinstance(metadata, list) else []

        try:
            old_file = next(file for file in files if file['name'] == filename)
        except StopIteration:
            old_file = None

        if old_file:
            yield from self.delete(old_file['path'])

        yield from self.make_request(
            'POST',
            self.build_url(settings.EDIT_MEDIA_BASE_URL, 'study', self.doi),
            headers=dv_headers,
            auth=(self.token, ),
            data=stream,
            expects=(201, ),
            throws=exceptions.UploadError
        )

        # Find appropriate version of file
        metadata = yield from self._get_data('latest')
        files = metadata if isinstance(metadata, list) else []
        file_metadata = next(file for file in files if file['name'] == filename)

        return file_metadata, old_file is None

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        # Can only delete files in draft
        metadata = yield from self._get_data('latest')
        self._validate_path(path, metadata)

        yield from self.make_request(
            'DELETE',
            self.build_url(settings.EDIT_MEDIA_BASE_URL, 'file', path),
            auth=(self.token, ),
            expects=(204, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, state=None, **kwargs):

        # Get appropriate metadata
        if state == 'draft':
            dataset_metadata = yield from self._get_data('latest')
        elif state == 'published':
            dataset_metadata = yield from self._get_data('latest-published')
        else:
            dataset_metadata = yield from self._get_all_data()

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
    def revisions(self, path, **kwargs):
        versions = ['latest', 'latest-published']
        revisions = []
        for version in versions:
            metadata = yield from self._get_data(version)
            revision = next(
                (item for item in metadata if item['path'] == path), None
            )
            if revision:
                revisions.append(DataverseRevision(version).serialized())

        return revisions

    @asyncio.coroutine
    def _get_data(self, version):
        """
        :param str version:
            'latest' for draft files
            'latest-published' for published files
        """

        url = self.build_url(
            settings.JSON_BASE_URL.format(self._id, version),
            key=self.token,
        )
        resp = yield from self.make_request(
            'GET',
            url,
            expects=(200, ),
            throws=exceptions.MetadataError
        )

        data = yield from resp.json()
        data = data['data']

        return DataverseDatasetMetadata(
            data, self.name, self.doi, version,
        ).serialized()

    @asyncio.coroutine
    def _get_all_data(self):
        # Unspecified (file view page), check both sets for metadata
        try:
            published_data = yield from self._get_data('latest-published')
        except exceptions.MetadataError:
            published_data = []
        published_files = published_data if isinstance(published_data, list) else []
        draft_data = yield from self._get_data('latest')
        draft_files = draft_data if isinstance(draft_data, list) else []
        return draft_files + published_files

    def _validate_path(self, path, metadata):
        if path.lstrip('/') not in [item['path'].lstrip('/') for item in metadata]:
            raise exceptions.MetadataError(
                "Could not retrieve file '{}'".format(path),
                code=http.client.NOT_FOUND,
            )
