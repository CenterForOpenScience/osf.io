import os
import shutil
import pytest
from mock import call, Mock
import unittest
import responses
import json
HERE = os.path.dirname(os.path.abspath(__file__))
from nose.tools import assert_equal
from zipfile import ZipFile

from consume_files import consume_files



class TestIAFiles(unittest.TestCase):

    def tearDown(self):
        if os.path.isdir(os.path.join(HERE, 'sgg32')):
            shutil.rmtree(os.path.join(HERE, 'sgg32'))
        if os.path.isdir(os.path.join(HERE, 'jj81a')):
            shutil.rmtree(os.path.join(HERE, 'jj81a'))


    @responses.activate
    def test_file_dump(self):
        with open('tests/fixtures/sgg32.zip') as zipfile:
            responses.add(
                responses.Response(
                    responses.GET,
                    'https://files.osf.io/v1/resources/sgg32/providers/osfstorage/?zip=',
                    body = zipfile.read(), status=200,
                    stream=True
                )
            )


        consume_files('sgg32', 'asdfasdfasdgfasg', '.')

        assert os.path.isdir(os.path.join(HERE,'sgg32/files'))
        assert os.path.isfile(os.path.join(HERE, 'sgg32/files/test.txt'))


    @responses.activate
    def test_file_dump_multiple_levels(self):
        with open('tests/fixtures/jj81a.zip') as zipfile:
            responses.add(
                responses.Response(
                    responses.GET,
                    'https://files.osf.io/v1/resources/jj81a/providers/osfstorage/?zip=',
                    body = zipfile.read(), status=200,
                    stream=True
                )
            )


        consume_files('jj81a', None, '.')

        assert os.path.isdir(os.path.join(HERE,'jj81a/files/Folder 1'))
        assert os.path.isfile(os.path.join(HERE, 'jj81a/files/Folder 1/test.txt'))
        assert os.path.isfile(os.path.join(HERE, 'jj81a/files/Folder 1/Folder two/test3.txt'))

