# -*- coding: utf-8 -*-
"""Client tests for the IQB-RIMS addon."""
import json
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest

from addons.iqbrims.client import SpreadsheetClient, IQBRIMSFlowableClient
from addons.iqbrims.tests.utils import MockResponse
from addons.iqbrims import settings

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
                name, args, kwargs = mkreq.mock_calls[1]
                assert_equal(json.loads(kwargs['data']), {
                  'requests': [{
                    'setDataValidation': {
                      'range': {
                        'endRowIndex': 2,
                        'endColumnIndex': 1,
                        'sheetId': 1,
                        'startColumnIndex': 0,
                        'startRowIndex': 1
                      },
                      'rule': {'condition': {'type': 'BOOLEAN'}}
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 1,
                          'endColumnIndex': 1,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 0
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 3,
                          'endColumnIndex': 9,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 2
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 5,
                          'endColumnIndex': 2,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 5,
                          'endColumnIndex': 6,
                          'sheetId': 1,
                          'startColumnIndex': 5,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }]})
            with mock.patch.object(client, '_make_request',
                                   return_value=MockResponse('{"test": true}',
                                                             200)) as mkreq:
                client.add_files('sheet01', 1,
                                 ['file1.txt', 'file2.txt', 'test/file3.txt'])
                name, args, kwargs = mkreq.mock_calls[0]
                assert_equal(json.loads(kwargs['data']), {
                  'range': 'sheet01!A3:K3',
                  'values': [[u'\u251c\u2212\u2212', 'test', '', '', '', '', '.txt', '', '', ''],
                             [u'\u2502', u'\u2514\u2212\u2212', 'file3.txt', '', '', '', '', '', '', ''],
                             [u'\u251c\u2212\u2212', 'file1.txt', '', '', '', '', '', '', '', ''],
                             [u'\u2514\u2212\u2212', 'file2.txt', '', '', '', '', '', '', '', '']],
                  'majorDimension': 'ROWS'
                })
                name, args, kwargs = mkreq.mock_calls[1]
                assert_equal(json.loads(kwargs['data']), {
                  'requests': [{
                    'setDataValidation': {
                      'range': {
                        'endRowIndex': 2,
                        'endColumnIndex': 1,
                        'sheetId': 1,
                        'startColumnIndex': 0,
                        'startRowIndex': 1
                      },
                      'rule': {'condition': {'type': 'BOOLEAN'}}
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 1,
                          'endColumnIndex': 1,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 0
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 3,
                          'endColumnIndex': 10,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 2
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 7,
                          'endColumnIndex': 3,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 7,
                          'endColumnIndex': 7,
                          'sheetId': 1,
                          'startColumnIndex': 6,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }]})
            with mock.patch.object(client, '_make_request',
                                   return_value=MockResponse('{"test": true}',
                                                             200)) as mkreq:
                client.add_files('sheet01', 1,
                                 [u'ファイル1.txt', u'ファイル2.txt',
                                  u'テスト/ファイル3.txt'])
                name, args, kwargs = mkreq.mock_calls[0]
                assert_equal(json.loads(kwargs['data']), {
                  'range': 'sheet01!A3:K3',
                  'values': [[u'\u251c\u2212\u2212', u'テスト', '', '', '', '', '.txt', '', '', ''],
                             [u'\u2502', u'\u2514\u2212\u2212', u'ファイル3.txt', '', '', '', '', '', '', ''],
                             [u'\u251c\u2212\u2212', u'ファイル1.txt', '', '', '', '', '', '', '', ''],
                             [u'\u2514\u2212\u2212', u'ファイル2.txt', '', '', '', '', '', '', '', '']],
                  'majorDimension': 'ROWS'
                })
                name, args, kwargs = mkreq.mock_calls[1]
                assert_equal(json.loads(kwargs['data']), {
                  'requests': [{
                    'setDataValidation': {
                      'range': {
                        'endRowIndex': 2,
                        'endColumnIndex': 1,
                        'sheetId': 1,
                        'startColumnIndex': 0,
                        'startRowIndex': 1
                      },
                      'rule': {'condition': {'type': 'BOOLEAN'}}
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 1,
                          'endColumnIndex': 1,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 0
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 3,
                          'endColumnIndex': 10,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 2
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 7,
                          'endColumnIndex': 3,
                          'sheetId': 1,
                          'startColumnIndex': 0,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }, {
                    'addProtectedRange': {
                      'protectedRange': {
                        'range': {
                          'endRowIndex': 7,
                          'endColumnIndex': 7,
                          'sheetId': 1,
                          'startColumnIndex': 6,
                          'startRowIndex': 3
                        },
                        'warningOnly': True
                      }
                    }
                  }]})

class TestIQBRIMSFlowableClient(OsfTestCase):

    def test_start_workflow(self):
        client = IQBRIMSFlowableClient('0001')
        with mock.patch.object(client, '_make_request',
                               return_value=MockResponse('{"test": true}',
                                                         200)) as mkreq:
            status = {'state': 'deposit', 'labo_id': 'labox'}
            client.start_workflow('x1234', 'XPaper', status, 'key')

            name, args, kwargs = mkreq.mock_calls[0]
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

    def test_start_check_workflow(self):
        client = IQBRIMSFlowableClient('test_app')
        with mock.patch.object(client, '_make_request',
                               return_value=MockResponse('{"test": true}',
                                                         200)) as mkreq:
            status = {'state': 'check',
                      'labo_id': 'rna'}
            client.start_workflow('abc01', 'Sample Test', status, 'hash123')
            name, args, kwargs = mkreq.mock_calls[0]
            #
            print(json.loads(kwargs['data']))
            assert_equal(json.loads(kwargs['data']), {
              u'variables': [{u'type': u'string',
                              u'name': u'projectId',
                              u'value': u'abc01'},
                             {u'type': u'string',
                              u'name': u'paperTitle',
                              u'value': u'Sample Test'},
                             {u'type': u'string',
                              u'name': u'paperFolderPattern',
                              u'value': u'check/rna/%-abc01/'},
                             {u'type': u'string',
                              u'name': u'laboName',
                              u'value': u'RNA分野'},
                             {u'type': u'boolean',
                              u'name': u'isDirectlySubmitData',
                              u'value': False},
                             {u'type': u'string',
                              u'name': u'acceptedDate',
                              u'value': u''},
                             {u'type': u'string',
                              u'name': u'acceptedDateTime',
                              u'value': u''},
                             {u'type': u'string',
                              u'name': u'flowableWorkflowUrl',
                              u'value': u'http://localhost:9999/flowable-task/'},
                             {u'type': u'string',
                              u'name': u'secret',
                              u'value': u'hash123'}],
              u'processDefinitionId': u'test_app'
            })
            assert_equal(client._auth,
                         (settings.FLOWABLE_USER, settings.FLOWABLE_PASSWORD))

    def test_start_deposit_workflow(self):
        client = IQBRIMSFlowableClient('test_app')
        with mock.patch.object(client, '_make_request',
                               return_value=MockResponse('{"test": true}',
                                                         200)) as mkreq:
            status = {'state': 'deposit',
                      'labo_id': 'rna',
                      'accepted_date': '2019-08-29T15:00:00.000Z',
                      'is_directly_submit_data': True}
            client.start_workflow('abc01', 'Sample Paper', status, 'hash123')
            name, args, kwargs = mkreq.mock_calls[0]
            print(json.loads(kwargs['data']))
            assert_equal(json.loads(kwargs['data']), {
              'variables': [{'type': 'string',
                             'name': 'projectId',
                             'value': 'abc01'},
                            {'type': 'string',
                             'name': 'paperTitle',
                             'value': 'Sample Paper'},
                            {u'type': u'string',
                             u'name': u'paperFolderPattern',
                             u'value': u'deposit/rna/%-abc01/'},
                            {'type': 'string',
                             'name': 'laboName',
                             'value': u'RNA分野'},
                            {'type': 'boolean',
                             'name': 'isDirectlySubmitData',
                             'value': True},
                            {'type': 'string',
                             'name': 'acceptedDate',
                             'value': '2019-08-29'},
                            {'type': 'string',
                             'name': 'acceptedDateTime',
                             'value': '2019-08-29T15:00:00.000Z'},
                            {'type': 'string',
                             'name': 'flowableWorkflowUrl',
                             'value': u'http://localhost:9999/flowable-task/'},
                            {'type': 'string',
                             'name': 'secret',
                             'value': 'hash123'}],
              'processDefinitionId': 'test_app'
            })
