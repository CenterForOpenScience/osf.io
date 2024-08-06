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
        super(TestSuggestion, self).tearDown()
        self.erad.delete()
        self.contributor.delete()

    @mock.patch('addons.metadata.suggestion.requests')
    def test_suggestion_ror(self, mock_requests):
        ror_data = {
            'items': [
                {
                    'id': 'https://ror.org/0123456789',
                    'name': 'Example University',
                    'labels': [{
                        'label': 'EXAMPLE UNIV.',
                        'iso639': 'ja',
                    }],
                },
            ],
        }
        mock_requests.get.return_value = mock.Mock(status_code=200, json=lambda: ror_data)
        r = suggestion_metadata('ror', 'searchkey', None, self.project)
        logger.info('ror suggestion: {}'.format(r))

        assert len(r) == 1
        assert r[0]['key'] == 'ror'
        assert r[0]['value']['id'] == 'https://ror.org/0123456789'
        assert r[0]['value']['name'] == 'Example University'
        assert r[0]['value']['name-ja'] == 'EXAMPLE UNIV.'
        assert len(r[0]['value']['labels']) == 1
        assert r[0]['value']['labels'][0]['label'] == 'EXAMPLE UNIV.'
        assert r[0]['value']['labels'][0]['iso639'] == 'ja'

        mock_requests.get.assert_called_once()
        assert mock_requests.get.call_args[1]['params']['query'] == 'searchkey'

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
        assert r[0]['value']['kenkyukikan_mei_ja'] == '研究機関名'
        assert r[0]['value']['kenkyukikan_mei_en'] == 'Research Institute Name'

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
