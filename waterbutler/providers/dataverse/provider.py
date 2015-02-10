import os
import asyncio

import sys
import pdb
import traceback

import furl
import itertools
import xmltodict

# TODO deleteme
import requests as R

from zipstream import ZipFile

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.dataverse import settings
from waterbutler.providers.dataverse.metadata import DataverseFileMetadata, DataverseStudyMetadata

def build_dataverse_url(base, *segments, **query):
    url = furl.furl(base)
    segments = filter(
        lambda segment: segment,
        map(
            lambda segment: segment.strip('/'),
            itertools.chain(url.path.segments, segments)
        )
    )
    url.path = os.path.join(*segments)
    url.args = query
    return url.url


class DataversePath(utils.WaterButlerPath):

    def __init__(self, doi, path, prefix=True, suffix=False):
        super().__init__(path, prefix=prefix, suffix=suffix)

        self._doi = doi
        
        '''
        full_path = os.path.join(doi, path.lstrip('/'))
        self._full_path = self._format_path(full_path)

        @property
        def full_path(self):
            return self._full_path
        '''

class DataverseProvider(provider.BaseProvider):

    UP_BASE_URL = settings.UP_BASE_URL
    DOWN_BASE_URL = settings.DOWN_BASE_URL
    METADATA_BASE_URL = settings.METADATA_BASE_URL

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.api_key = self.credentials['api_key']
        self.doi = self.settings['study_doi']

    @asyncio.coroutine
    def intra_copy(self, dest_provider, source_options, dest_options):
        source_path = DataversePath(source_options['path'])
        dest_path = DataversePath(dest_options['path'])
        if self == dest_provider:
            resp = yield from self.make_request(
                'POST',
                self.build_url('fileops', 'copy'),
                data={
                    'folder': 'auto',
                    'from_path': source_path.full_path,
                    'to_path': dest_path.full_path,
                },
                expects=(200, 201),
                throws=exceptions.IntraCopyError,
            )
        else:
            from_ref_resp = yield from self.make_request(
                'GET',
                self.build_url('copy_ref', 'auto', source_path.full_path),
            )
            from_ref_data = yield from from_ref_resp.json()
            resp = yield from self.make_request(
                'POST',
                data={
                    'root': 'auto',
                    'from_copy_ref': from_ref_data['copy_ref'],
                    'to_path': dest_path,
                },
                headers=dest_provider.default_headers,
                expects=(200, 201),
                throws=exceptions.IntraCopyError,
            )
        data = yield from resp.json()
        return DataverseFileMetadata(data).serialized()

    @asyncio.coroutine
    def intra_move(self, dest_provider, source_options, dest_options):
        source_path = DataversePath(self.folder, source_options['path'])
        dest_path = DataversePath(self.folder, dest_options['path'])
        resp = yield from self.make_request(
            'POST',
            self.build_url('fileops', 'move'),
            data={
                'root': 'auto',
                'from_path': source_path.full_path,
                'to_path': dest_path.full_path,
            },
            expects=(200, ),
            throws=exceptions.IntraMoveError,
        )
        data = yield from resp.json()
        return DataverseFileMetadata(data).serialized()

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        path = DataversePath(path)
        resp = yield from self.make_request(
            'GET',
            self.build_url(path.full_path),
            expects=(200, ),
            throws=exceptions.DownloadError,
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

        dv_headers= {
            "Content-Disposition": "filename={0}".format(path),
            "Content-Type": "application/zip",
            "Packaging": "http://purl.org/net/sword/package/SimpleZip",
            "Content-Length": str(stream.size),
        }
        zip_stream = streams.ZipStreamReader(stream)
        import pdb; pdb.set_trace()
        resp = yield from self.make_request(
            'POST',
            build_dataverse_url(settings.UP_BASE_URL, self.doi),
            headers=dv_headers,
            auth=(self.api_key, ),
            data=zip_stream,
            expects=(200, ),
            throws=exceptions.UploadError
        )
        
        data = yield from resp.json()
        return DataverseFileMetadata(data, self.folder).serialized(), created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        path = DataversePath(self.folder, path)

        # A metadata call will verify the path specified is actually the
        # requested file or folder.
        yield from self.metadata(str(path))

        yield from self.make_request(
            'POST',
            self.build_url('fileops', 'delete'),
            data={'root': 'auto', 'path': path.full_path},
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        path = DataversePath(self.doi, path)

        url = build_dataverse_url(settings.METADATA_BASE_URL, self.doi)
        resp = yield from self.make_request(
            'GET',
            url,
            auth=(self.api_key, ),
            expects=(200, ),
            throws=exceptions.MetadataError
        )
        data = yield from resp.text()
        data = xmltodict.parse(data)
        
        return DataverseStudyMetadata(data).serialized()

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        path = DataversePath(self.folder, path)
        response = yield from self.make_request(
            'GET',
            self.build_url('revisions', 'auto', path.full_path),
            expects=(200, ),
            throws=exceptions.RevisionError
        )
        data = yield from response.json()

        return [
            DropboxRevision(item).serialized()
            for item in data
        ]

    def can_intra_copy(self, dest_provider):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider):
        return self.can_intra_copy(dest_provider)

    def _build_content_url(self, *segments, **query):
        return provider.build_url(settings.BASE_CONTENT_URL, *segments, **query)
