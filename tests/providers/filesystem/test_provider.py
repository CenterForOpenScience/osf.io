import pytest

from tests.utils import async

import io
import os
import shutil

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.filesystem import FileSystemProvider
from waterbutler.providers.filesystem.provider import FileSystemPath
from waterbutler.providers.filesystem.metadata import FileSystemFileMetadata


@pytest.fixture
def auth():
    return {}


@pytest.fixture
def credentials():
    return {}


@pytest.fixture
def settings(tmpdir):
    return {'folder': str(tmpdir)}


@pytest.fixture
def provider(auth, credentials, settings):
    return FileSystemProvider(auth, credentials, settings)


@pytest.fixture(scope="function", autouse=True)
def setup_filesystem(provider):
    shutil.rmtree(provider.folder)
    os.makedirs(provider.folder, exist_ok=True)

    with open(os.path.join(provider.folder, 'flower.jpg'), 'wb') as fp:
        fp.write(b'I am a file')

    os.mkdir(os.path.join(provider.folder, 'subfolder'))

    with open(os.path.join(provider.folder, 'subfolder', 'nested.txt'), 'wb') as fp:
        fp.write(b'Here is my content')


class TestCRUD:

    @async
    def test_download(self, provider):
        path = FileSystemPath(provider.folder, '/flower.jpg')

        result = yield from provider.download(str(path))
        content = yield from result.read()

        assert content == b'I am a file'

    @async
    def test_download_not_found(self, provider):
        path = FileSystemPath(provider.folder, '/missing.txt')

        with pytest.raises(exceptions.DownloadError):
            yield from provider.download(str(path))

    @async
    def test_upload_create(self, provider):
        file_name = 'upload.txt'
        file_folder = '/'
        file_path = os.path.join(file_folder, file_name)
        file_content = b'Test Upload Content'
        file_stream = streams.FileStreamReader(io.BytesIO(file_content))

        path = FileSystemPath(provider.folder, file_path)
        metadata, created = yield from provider.upload(file_stream, str(path))

        assert metadata['name'] == file_name
        assert metadata['path'] == file_path
        assert metadata['size'] == len(file_content)
        assert created == True

    @async
    def test_upload_update(self, provider):
        file_name = 'flower.jpg'
        file_folder = '/'
        file_path = os.path.join(file_folder, file_name)
        file_content = b'Short and stout'
        file_stream = streams.FileStreamReader(io.BytesIO(file_content))

        path = FileSystemPath(provider.folder, file_path)
        metadata, created = yield from provider.upload(file_stream, str(path))

        assert metadata['name'] == file_name
        assert metadata['path'] == file_path
        assert metadata['size'] == len(file_content)
        assert created == False

    @async
    def test_delete_file(self, provider):
        path = FileSystemPath(provider.folder, '/flower.jpg')

        yield from provider.delete(str(path))

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(str(path))


class TestMetadata:

    @async
    def test_metadata(self, provider):
        path = FileSystemPath(provider.folder, '/')
        result = yield from provider.metadata(str(path))

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['kind'] == 'file'
        assert result[0]['name'] == 'flower.jpg'
        assert result[0]['path'] == '/flower.jpg'
        assert result[1]['kind'] == 'folder'
        assert result[1]['name'] == 'subfolder'
        assert result[1]['path'] == '/subfolder/'

    @async
    def test_metadata_root_file(self, provider):
        path = FileSystemPath(provider.folder, '/flower.jpg')
        result = yield from provider.metadata(str(path))

        assert isinstance(result, dict)
        assert result['kind'] == 'file'
        assert result['name'] == 'flower.jpg'
        assert result['path'] == '/flower.jpg'

    @async
    def test_metadata_missing(self, provider):
        path = FileSystemPath(provider.folder, '/missing.txt')

        with pytest.raises(exceptions.MetadataError):
            yield from provider.metadata(str(path))


class TestOperations:

    def test_can_intra_copy(self, provider):
        assert provider.can_intra_copy(provider)

    def test_can_intra_move(self, provider):
        assert provider.can_intra_move(provider)
