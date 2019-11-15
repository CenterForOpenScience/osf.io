# -*- coding: utf-8 -*-
"""Client tests for the IQB-RIMS addon."""
import json
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from addons.iqbrims.client import SpreadsheetClient, IQBRIMSFlowableClient
from addons.iqbrims.tests.utils import MockResponse

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestIQBRIMSSpreadsheetClient(OsfTestCase):

    def test_add_files(self):
        client = SpreadsheetClient('0001')
        with mock.patch.object(client, 'ensure_columns',
                               side_effect=lambda sid, cols, row: cols):
            with mock.patch.object(client, '_make_request',
                                   return_value=MockResponse('{"test": true}',
                                                             200)) as mkreq:
                client.add_files('sheet01', 1,
                                 ['file1.txt', 'file2.txt'])
                name, args, kwargs = mkreq.mock_calls[0]
                assert_equal(json.loads(kwargs['data']), {
                  'range': 'sheet01!A3:J3',
                  'values': [[u'\u251c\u2212\u2212', 'file1.txt', '', '', '', '.txt', '', '', ''],
                             [u'\u2514\u2212\u2212', 'file2.txt', '', '', '', '', '', '', '']],
                  'majorDimension': 'ROWS'
                })
            with mock.patch.object(client, '_make_request',
                                   return_value=MockResponse('{"test": true}',
                                                             200)) as mkreq:
                client.add_files('sheet01', 1,
                                 ['file1.txt', 'file2.txt', 'test/file3.txt'])
                name, args, kwargs = mkreq.mock_calls[0]
                print(kwargs['data'])
                assert_equal(json.loads(kwargs['data']), {
                  'range': 'sheet01!A3:K3',
                  'values': [[u'\u251c\u2212\u2212', 'test', '', '', '', '', '.txt', '', '', ''],
                             [u'\u2502', u'\u2514\u2212\u2212', 'file3.txt', '', '', '', '', '', '', ''],
                             [u'\u251c\u2212\u2212', 'file1.txt', '', '', '', '', '', '', '', ''],
                             [u'\u2514\u2212\u2212', 'file2.txt', '', '', '', '', '', '', '', '']],
                  'majorDimension': 'ROWS'
                })

class TestIQBRIMSFlowableClient(OsfTestCase):

    @mock.patch('requests.post')
    def test_start_workflow(self, mock_post):
        mock_post.return_value.content = ''
        mock_post.return_value.status_code = 200

        client = IQBRIMSFlowableClient('0001')
        status = {'state': 'deposit', 'labo_id': 'labox'}
        client.start_workflow('x1234', 'XPaper', status, 'key')

        name, args, kwargs = mock_post.mock_calls[0]
        vars = json.loads(kwargs['data'])['variables']
        assert_equal([v for v in vars if v['name'] == 'projectId'][0], {
          'name': 'projectId',
          'type': 'string',
          'value': 'x1234'
        })
        assert_equal([v for v in vars if v['name'] == 'paperFolderPattern'][0], {
          'name': 'paperFolderPattern',
          'type': 'string',
          'value': 'deposit/labox/%-x1234/'
        })
