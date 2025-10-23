# -*- coding: utf-8 -*-
import logging
import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory

from .utils import BaseAddonTestCase
from addons.metadata.suggestion import suggestion_metadata
from addons.metadata.models import ERadRecord


logger = logging.getLogger(__name__)


class TestSuggestion(BaseAddonTestCase, OsfTestCase):

    def setUp(self):
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        super(TestSuggestion, self).setUp()
        self.erad = ERadRecord.objects.create(
            kenkyusha_no='0123456',
            kenkyusha_shimei='姓|名|Last|First',
            kenkyukikan_mei='研究機関名|Research Institute Name',
        )
        self.erad.save()

        self.contributor = UserFactory()
        self.project.add_contributor(self.contributor)
        self.project.save()

    def tearDown(self):
        self.erad.delete()
        self.contributor.delete()
        super(TestSuggestion, self).tearDown()
        self.mock_fetch_metadata_asset_files.stop()

    @mock.patch('addons.metadata.suggestion.requests')
    def test_suggestion_ror_v2(self, mock_requests):
        ror_v2_data = {
            'items': [
                {
                    'id': 'https://ror.org/0123456789',
                    'names': [
                        {
                            'value': 'Example University',
                            'lang': 'en',
                            'types': ['ror_display', 'label']
                        },
                        {
                            'value': 'EXAMPLE UNIV.',
                            'lang': 'ja',
                            'types': ['label']
                        }
                    ],
                },
            ],
        }
        mock_requests.get.return_value = mock.Mock(status_code=200, json=lambda: ror_v2_data)
        r = suggestion_metadata('ror', 'searchkey', None, self.project)
        logger.info('ror suggestion: {}'.format(r))

        assert len(r) == 1
        assert r[0]['key'] == 'ror'
        assert r[0]['value']['id'] == 'https://ror.org/0123456789'
        assert r[0]['value']['name'] == 'Example University'
        assert r[0]['value']['name-ja'] == 'EXAMPLE UNIV.'

        mock_requests.get.assert_called_once()
        assert mock_requests.get.call_args[1]['params']['query'] == 'searchkey'

    @mock.patch('addons.metadata.suggestion.requests')
    def test_suggestion_ror_v2_no_japanese(self, mock_requests):
        ror_v2_data = {
            'items': [
                {
                    'id': 'https://ror.org/9876543210',
                    'names': [
                        {
                            'value': 'MIT',
                            'lang': 'en',
                            'types': ['ror_display', 'label']
                        }
                    ],
                },
            ],
        }
        mock_requests.get.return_value = mock.Mock(status_code=200, json=lambda: ror_v2_data)
        r = suggestion_metadata('ror', 'MIT', None, self.project)
        logger.info('ror suggestion without Japanese: {}'.format(r))

        assert len(r) == 1
        assert r[0]['key'] == 'ror'
        assert r[0]['value']['id'] == 'https://ror.org/9876543210'
        assert r[0]['value']['name'] == 'MIT'
        assert r[0]['value']['name-ja'] == 'MIT'

        mock_requests.get.assert_called_once()
        assert mock_requests.get.call_args[1]['params']['query'] == 'MIT'

    def test_suggestion_erad(self):
        r = suggestion_metadata('erad:kenkyusha_no', '0', None, self.project)
        logger.info('erad suggestion: {}'.format(r))
        assert len(r) == 0

        self.user.erad = '0123456'
        self.user.save()

        r = suggestion_metadata('erad:kenkyusha_no', '0', None, self.project)
        logger.info('erad suggestion: {}'.format(r))
        assert len(r) == 1
        assert r[0]['key'] == 'erad:kenkyusha_no'
        assert r[0]['value']['kenkyusha_no'] == '0123456'
        assert r[0]['value']['kenkyusha_shimei'] == '姓|名|Last|First'
        assert r[0]['value']['kenkyusha_shimei_ja'] == {
            'last': '姓',
            'middle': '',
            'first': '名',
        }
        assert r[0]['value']['kenkyusha_shimei_en'] == {
            'last': 'Last',
            'middle': '',
            'first': 'First',
        }
        assert r[0]['value']['kenkyusha_shimei_ja_msfullname'] == '姓名'
        assert r[0]['value']['kenkyusha_shimei_en_msfullname'] == 'First Last'
        assert r[0]['value']['display_fullname'] == '姓 名 (First Last)'
        assert 'display-fullname' not in r[0]['value']
        assert r[0]['value']['kenkyukikan_mei_ja'] == '研究機関名'
        assert r[0]['value']['kenkyukikan_mei_en'] == 'Research Institute Name'

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_suggestion_kaken(self, mock_es_service_class):
        """Test KAKEN suggestion with mocked Elasticsearch service"""
        # Test with no erad ID
        r = suggestion_metadata('kaken:kenkyusha_shimei', '山田', None, self.project)
        logger.info('kaken suggestion (no erad): {}'.format(r))
        assert len(r) == 0

        # Set erad ID for user
        self.user.erad = '12345678'
        self.user.save()

        # Setup mock Elasticsearch service
        mock_es = mock.MagicMock()
        mock_es_service_class.return_value = mock_es

        # Mock response data
        mock_es.get_researcher_by_erad.return_value = {
            'id:person:erad': ['12345678'],
            'name': {
                'humanReadableValue': [
                    {'text': '山田 太郎', 'lang': 'ja'},
                    {'text': 'YAMADA Taro', 'lang': 'en'}
                ],
                'name:familyName': [
                    {'text': '山田', 'lang': 'ja'},
                    {'text': 'YAMADA', 'lang': 'en'}
                ],
                'name:givenName': [
                    {'text': '太郎', 'lang': 'ja'},
                    {'text': 'Taro', 'lang': 'en'}
                ]
            },
            'affiliations:history': [{
                'sequence': 1,
                'affiliation:institution': {
                    'humanReadableValue': [
                        {'text': 'テスト大学', 'lang': 'ja'},
                        {'text': 'Test University', 'lang': 'en'}
                    ]
                }
            }],
            'work:project': [{
                'recordSource': {'id:project:kakenhi': ['KAKENHI-PROJECT-11111111']},
                'since': {'fiscal:year': {'commonEra:year': '2020'}}
            }]
        }
        mock_es.close.return_value = None

        # Test KAKEN suggestion
        r = suggestion_metadata('kaken:kenkyusha_shimei', '山田', None, self.project)
        logger.info('kaken suggestion: {}'.format(r))

        assert len(r) == 1
        assert r[0]['key'] == 'kaken:kenkyusha_shimei'
        assert r[0]['value']['erad'] == '12345678'
        assert r[0]['value']['kadai_id'] == '11111111'
        assert r[0]['value']['kenkyusha_shimei'] == '山田|太郎||YAMADA|Taro'
        assert r[0]['value']['kenkyusha_shimei_ja'] == '山田|太郎'
        assert r[0]['value']['kenkyusha_shimei_en'] == 'YAMADA|Taro'
        assert r[0]['value']['kenkyusha_shimei_ja_msfullname'] == '山田太郎'
        assert r[0]['value']['kenkyusha_shimei_en_msfullname'] == 'Taro YAMADA'
        assert r[0]['value']['display_fullname'] == '山田 太郎 (Taro YAMADA)'
        assert 'display-fullname' not in r[0]['value']
        assert 'テスト大学' in r[0]['value']['kenkyukikan_mei']
        assert r[0]['value']['japan_grant_number'] == 'JP11111111'
        assert r[0]['value']['nendo'] == '2020'

    def test_suggestion_contributors(self):
        self.user.erad = ''
        self.user.family_name = 'Family'
        self.user.middle_names = ''
        self.user.given_name = 'Given'
        self.user.family_name_ja = '姓'
        self.user.middle_names_ja = ''
        self.user.given_name_ja = '名'
        self.user.save()

        self.contributor.erad = '0123456'
        self.contributor.family_name = 'Family2'
        self.contributor.middle_names = 'Middle2'
        self.contributor.given_name = 'Given2'
        self.contributor.family_name_ja = '姓2'
        self.contributor.middle_names_ja = '中間2'
        self.contributor.given_name_ja = '名2'
        self.contributor.save()

        r = suggestion_metadata('contributor:erad', '0', None, self.project)
        logger.info('contributors suggestion: {}'.format(r))
        assert len(r) == 1
        assert r[0]['key'] == 'contributor:erad'
        assert r[0]['value']['erad'] == '0123456'
        assert r[0]['value']['name-ja-full'] == '姓2|中間2|名2'
        assert r[0]['value']['name-en-full'] == 'Family2|Middle2|Given2'
        assert r[0]['value']['name-ja'] == {
            'last': '姓2',
            'middle': '中間2',
            'first': '名2',
        }
        assert r[0]['value']['name-en'] == {
            'last': 'Family2',
            'middle': 'Middle2',
            'first': 'Given2',
        }
        assert r[0]['value']['name-ja-msfullname'] == '姓2中間2名2'
        assert r[0]['value']['name-en-msfullname'] == 'Given2 Middle2 Family2'
        assert r[0]['value']['display-fullname'] == '姓2 中間2 名2 (Given2 Middle2 Family2)'
        assert 'display_fullname' not in r[0]['value']

        r = suggestion_metadata('contributor:erad', '', None, self.project)
        logger.info('contributors suggestion: {}'.format(r))
        assert len(r) == 2
        assert r[0]['key'] == 'contributor:erad'
        assert r[0]['value']['erad'] == ''
        assert r[0]['value']['name-ja-full'] == '姓|名'
        assert r[0]['value']['name-en-full'] == 'Family|Given'
        assert r[0]['value']['name-ja'] == {
            'last': '姓',
            'middle': '',
            'first': '名',
        }
        assert r[0]['value']['name-en'] == {
            'last': 'Family',
            'middle': '',
            'first': 'Given',
        }
        assert r[0]['value']['name-ja-msfullname'] == '姓名'
        assert r[0]['value']['name-en-msfullname'] == 'Given Family'
        assert r[0]['value']['display-fullname'] == '姓 名 (Given Family)'
        assert 'display_fullname' not in r[0]['value']
        assert r[1]['key'] == 'contributor:erad'
        assert r[1]['value']['erad'] == '0123456'
        assert r[1]['value']['name-ja-full'] == '姓2|中間2|名2'
        assert r[1]['value']['name-en-full'] == 'Family2|Middle2|Given2'
        assert r[1]['value']['name-ja'] == {
            'last': '姓2',
            'middle': '中間2',
            'first': '名2',
        }
        assert r[1]['value']['name-en'] == {
            'last': 'Family2',
            'middle': 'Middle2',
            'first': 'Given2',
        }
        assert r[1]['value']['name-ja-msfullname'] == '姓2中間2名2'
        assert r[1]['value']['name-en-msfullname'] == 'Given2 Middle2 Family2'
        assert r[1]['value']['display-fullname'] == '姓2 中間2 名2 (Given2 Middle2 Family2)'
        assert 'display_fullname' not in r[1]['value']
