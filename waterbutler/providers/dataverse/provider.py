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
    """Provider for Dataverse"""

    def __init__(self, auth, credentials, settings):
        """
        :param dict auth: Not used
        :param dict credentials: Contains `token`
        :param dict settings: Contains `host`, `doi`, `id`, and `name` of a dataset. Hosts:

            - 'apitest.dataverse.org': Api Test Server
            - 'dataverse-demo.iq.harvard.edu': Harvard Demo Server
            - 'dataverse.harvard.edu': Dataverse Production Server **(NO TEST DATA)**
            - Other
        """
        super().__init__(auth, credentials, settings)
        self.BASE_URL = 'https://{0}'.format(self.settings['host'])

        self.token = self.credentials['token']
        self.doi = self.settings['doi']
        self._id = self.settings['id']
        self.name = self.settings['name']

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        raises FileNotFoundError if the status from Dataverse is not 200

        :param str path: Path to the file you want to download
        :param str revision: Used to verify if file is in selected dataset

            - 'latest' to check draft files
            - 'latest-published' to check published files
            - None to check all data
        :param dict \*\*kwargs: Additional arguments that are ignored
        :rtype: :class:`waterbutler.core.streams.ResponseStreamReader`
        :raises: :class:`waterbutler.core.exceptions.DownloadError`
        """
        metadata = yield from self._get_data(revision)
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
        """Zips the given stream then uploads to Dataverse.
        This will delete existing draft files with the same name.

        :param waterbutler.core.streams.RequestWrapper stream: The stream to put to Dataverse
        :param str path: The filename prepended with '/'

        :rtype: dict, bool
        """

        filename = path.strip('/')

        stream = streams.ZipStreamReader((filename, stream))

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
        """Deletes the key at the specified path

        :param str path: The path of the key to delete
        """

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
    def metadata(self, path, version=None, **kwargs):
        """
        :param str version:

            - 'latest' for draft files
            - 'latest-published' for published files
            - None for all data
        """

        # Get appropriate metadata
        dataset_metadata = yield from self._get_data(version)

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
        """Get past versions of the request file. Orders versions based on
        `_get_all_data()`

        :param str path: The path to a key
        :rtype list:
        """

        metadata = yield from self._get_data()
        return [
            DataverseRevision(item['extra']['datasetVersion']).serialized()
            for item in metadata if item['path'] == path
        ]

    @asyncio.coroutine
    def _get_data(self, version=None):
        """Get list of file metadata for a given dataset version

        :param str version:

            - 'latest' for draft files
            - 'latest-published' for published files
            - None for all data
        """

        if not version:
            return (yield from self._get_all_data())

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

        dataset_metadata = DataverseDatasetMetadata(
            data, self.name, self.doi, version,
        )

        return [item.serialized() for item in dataset_metadata.contents]

    @asyncio.coroutine
    def _get_all_data(self):
        """Get list of file metadata for all dataset versions"""
        try:
            published_data = yield from self._get_data('latest-published')
        except exceptions.MetadataError as e:
            if e.code != 404:
                raise
            published_data = []
        draft_data = yield from self._get_data('latest')

        # Prefer published to guarantee users get published version by default
        return published_data + draft_data

    def _validate_path(self, path, metadata):
        """Ensure path is in configured dataset

        :param str path: The path to a file
        :param list metadata: List of file metadata from _get_data
        """
        # Ensure file is in specified dataset
        if path.lstrip('/') not in [item['path'].lstrip('/') for item in metadata]:
            raise exceptions.MetadataError(
                "Could not retrieve file '{}'".format(path),
                code=http.client.NOT_FOUND,
            )
