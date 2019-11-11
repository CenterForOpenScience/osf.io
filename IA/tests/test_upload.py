import os
import unittest
import responses
from IA_upload import upload

HERE = os.path.dirname(os.path.abspath(__file__))

class TestWikiDumper(unittest.TestCase):

    @responses.activate
    def test_IA_upload(self):
        responses.add(
            responses.Response(
                responses.PUT,
                'http://s3.us.archive.org/bucketname/file_name',
            )
        )
        upload('bucketname', 'file_name', b'content')
