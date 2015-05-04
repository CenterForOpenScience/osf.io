import io
import zipfile

from tests.utils import async

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

    # @async
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