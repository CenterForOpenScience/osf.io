import io
import os
import tempfile
import zipfile

from tests.utils import async, temp_files

from waterbutler.core import streams


class TestZipStreamReader:
    @async
    def test_single_file(self):
        file = ('filename.extension', streams.StringStream('[File Content]'))

        stream = streams.ZipStreamReader(file)

        data = yield from stream.read()

        zip = zipfile.ZipFile(io.BytesIO(data))

        # Verify CRCs
        assert zip.testzip() is None

        result = zip.open('filename.extension')

        # Check content of included file
        assert result.read() == b'[File Content]'

    @async
    def test_multiple_files(self):

        file1 = ('file1.txt', streams.StringStream('[File One]'))
        file2 = ('file2.txt', streams.StringStream('[File Two]'))
        file3 = ('file3.txt', streams.StringStream('[File Three]'))

        stream = streams.ZipStreamReader(file1, file2, file3)

        data = yield from stream.read()

        zip = zipfile.ZipFile(io.BytesIO(data))

        # Verify CRCs
        assert zip.testzip() is None

        # Check content of included files

        zipped1 = zip.open('file1.txt')
        assert zipped1.read() == b'[File One]'

        zipped2 = zip.open('file2.txt')
        assert zipped2.read() == b'[File Two]'

        zipped3 = zip.open('file3.txt')
        assert zipped3.read() == b'[File Three]'

    @async
    def test_single_large_file(self, temp_files):
        filename = 'foo.txt'
        path = temp_files.add_file(filename)
        random_data = os.urandom(2**18)
        with open(path, 'wb') as f:
            f.write(random_data)

        with open(path, 'rb') as f:

            stream = streams.ZipStreamReader(
                (filename, streams.FileStreamReader(f))
            )

            data = yield from stream.read()

        zip = zipfile.ZipFile(io.BytesIO(data))

        # Verify CRCs
        assert zip.testzip() is None

        result = zip.open('foo.txt')

        # Check content of included file
        assert result.read() == random_data

    @async
    def test_multiple_large_files(self, temp_files):
        files = []
        for index in range(5):
            filename = 'file{}.ext'.format(index)
            path = temp_files.add_file(filename)
            contents = os.urandom(2**18)

            with open(path, 'wb') as f:
                f.write(contents)

            files.append({
                'filename': filename,
                'path': path,
                'contents': contents
            })

        for file in files:
            file['handle'] = open(file['path'], 'rb')

        stream = streams.ZipStreamReader(
            *(
                (file['filename'], streams.FileStreamReader(file['handle']))
                for file in files
            )
        )

        data = yield from stream.read()

        for file in files:
            file['handle'].close()

        zip = zipfile.ZipFile(io.BytesIO(data))

        # Verify CRCs
        assert zip.testzip() is None

        for file in files:
            assert zip.open(file['filename']).read() == file['contents']