import os
import shutil
import asyncio
import datetime
import mimetypes

from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions
from waterbutler.core.path import WaterButlerPath

from waterbutler.providers.filesystem import settings
from waterbutler.providers.filesystem.metadata import FileSystemFileMetadata
from waterbutler.providers.filesystem.metadata import FileSystemFolderMetadata


class FileSystemProvider(provider.BaseProvider):
    NAME = 'filesystem'

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.folder = self.settings['folder']
        os.makedirs(self.folder, exist_ok=True)

    @asyncio.coroutine
    def validate_path(self, path, **kwargs):
        return WaterButlerPath(path, prepend=self.folder)

    @asyncio.coroutine
    def intra_copy(self, dest_provider, src_path, dest_path):
        exists = yield from self.exists(dest_path)
        shutil.copy(src_path.full_path, dest_path.full_path)
        return (yield from dest_provider.metadata(dest_path)), not exists

    @asyncio.coroutine
    def intra_move(self, dest_provider, src_path, dest_path):
        exists = yield from self.exists(dest_path)
        shutil.move(src_path.full_path, dest_path.full_path)
        return (yield from dest_provider.metadata(dest_path)), not exists

    @asyncio.coroutine
    def download(self, path, revision=None, **kwargs):
        if not os.path.exists(path.full_path):
            raise exceptions.DownloadError(
                'Could not retrieve file \'{0}\''.format(path),
                code=404,
            )

        file_pointer = open(path.full_path, 'rb')
        return streams.FileStreamReader(file_pointer)

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        created = not (yield from self.exists(path))

        os.makedirs(os.path.split(path.full_path)[0], exist_ok=True)

        with open(path.full_path, 'wb') as file_pointer:
            chunk = yield from stream.read(settings.CHUNK_SIZE)
            while chunk:
                file_pointer.write(chunk)
                chunk = yield from stream.read(settings.CHUNK_SIZE)

        metadata = yield from self.metadata(path)
        return metadata, created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        if path.is_file:
            os.remove(path.full_path)
        else:
            shutil.rmtree(path.full_path)
            if path.is_root:
                os.makedirs(self.folder, exist_ok=True)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        if path.is_dir:
            if not os.path.exists(path.full_path) or not os.path.isdir(path.full_path):
                raise exceptions.MetadataError(
                    'Could not retrieve folder \'{0}\''.format(path),
                    code=404,
                )

            ret = []
            for item in os.listdir(path.full_path):
                if os.path.isdir(os.path.join(path.full_path, item)):
                    metadata = self._metadata_folder(path, item)
                    ret.append(FileSystemFolderMetadata(metadata, self.folder).serialized())
                else:
                    metadata = self._metadata_file(path, item)
                    ret.append(FileSystemFileMetadata(metadata, self.folder).serialized())
            return ret
        else:
            if not os.path.exists(path.full_path) or os.path.isdir(path.full_path):
                raise exceptions.MetadataError(
                    'Could not retrieve file \'{0}\''.format(path),
                    code=404,
                )

            metadata = self._metadata_file(path)
            return FileSystemFileMetadata(metadata, self.folder).serialized()

    def _metadata_file(self, path, file_name=''):
        full_path = path.full_path if file_name == '' else os.path.join(path.full_path, file_name)
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
        return {
            'path': full_path,
            'size': os.path.getsize(full_path),
            'modified': modified.strftime('%a, %d %b %Y %H:%M:%S %z'),
            'mime_type': mimetypes.guess_type(full_path)[0],
        }

    def _metadata_folder(self, path, folder_name):
        return {
            'path': os.path.join(path.path, folder_name),
        }

    def can_intra_copy(self, dest_provider, path=None):
        return type(self) == type(dest_provider)

    def can_intra_move(self, dest_provider, path=None):
        return self.can_intra_copy(dest_provider)
