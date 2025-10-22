# -*- coding: utf-8 -*-
"""
Tests for KAKEN suggestion module
"""
import mock
import requests
from nose.tools import *  # noqa
from elasticsearch.exceptions import ConnectionError as ESConnectionError, ConnectionTimeout

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, ProjectFactory

from addons.metadata.suggestions.kaken import kaken_candidates
from addons.metadata.suggestions.kaken.elasticsearch import (
    KakenElasticsearchService,
    KakenBulkError,
    KakenTransportError,
)
from addons.metadata.suggestions.kaken.suggest import _kaken_candidates_for_node
from addons.metadata.suggestions.kaken.client import ResourceSyncClient
from scripts.update_kaken import _should_apply_change
import xml.etree.ElementTree as ET
from dateutil.parser import parse as parse_datetime


class TestKakenSuggestion(OsfTestCase):
    """Test KAKEN suggestion functionality"""

    def setUp(self):
        super(TestKakenSuggestion, self).setUp()
        self.user = UserFactory()
        self.user.erad = '12345678'
        self.user.save()

        self.project = ProjectFactory(creator=self.user)
        self.project.save()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        super(TestKakenSuggestion, self).tearDown()

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', None)
    def test_suggest_kaken_disabled_when_uri_is_none(self):
        """Test that suggest_kaken returns empty list when KAKEN_ELASTIC_URI is None"""
        from addons.metadata.suggestions.kaken.suggest import suggest_kaken

        result = suggest_kaken('kaken:kenkyusha_shimei', 'test', self.project)
        assert_equal(result, [])

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', None)
    def test_kaken_candidates_disabled_when_uri_is_none(self):
        """Test that kaken_candidates returns empty list when KAKEN_ELASTIC_URI is None"""
        result = kaken_candidates('12345678')
        assert_equal(result, [])

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_kaken_candidates_when_index_does_not_exist(self, mock_es_service):
        """Test that kaken_candidates returns empty list when index doesn't exist"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = None
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('12345678')
        assert_equal(result, [])

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_elasticsearch_unavailable(self, mock_es_service):
        """Test behavior when Elasticsearch service is unavailable"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.side_effect = ESConnectionError('Connection refused')
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        # Service unavailability should be visible to caller
        assert_raises(ESConnectionError, kaken_candidates, '12345678')

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_elasticsearch_timeout(self, mock_es_service):
        """Test behavior when Elasticsearch request times out"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.side_effect = ConnectionTimeout('Request timed out')
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        assert_raises(ConnectionTimeout, kaken_candidates, '12345678')

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_retrieves_researcher_data(self, mock_es_service):
        """Test successful retrieval of researcher data"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = {
            'work:project': [{
                'recordSource': {'id:project:kakenhi': '12345678'},
                'title': [{'humanReadableValue': [{'text': 'Test Project', 'lang': 'ja'}]}]
            }]
        }
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('12345678')

        assert_equal(len(result), 1)
        assert_equal(result[0]['kadai_id'], '12345678')

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_kaken_candidates_include_project_members(self, mock_es_service):
        mock_es = mock.MagicMock()
        mock_es_service.return_value = mock_es
        mock_es.close.return_value = None

        mock_es.get_researcher_by_erad.return_value = {
            'id:person:erad': ['99999999'],
            'name': {
                'humanReadableValue': [{'text': '代表 太郎', 'lang': 'ja'}],
                'name:familyName': [{'text': '代表', 'lang': 'ja'}],
                'name:givenName': [{'text': '太郎', 'lang': 'ja'}],
            },
            'affiliations:history': [
                {
                    'sequence': 1,
                    'affiliation:institution': {
                        'humanReadableValue': [{'text': '代表大学', 'lang': 'ja'}]
                    }
                }
            ],
            'work:project': [
                {
                    'recordSource': {'id:project:kakenhi': ['KAKENHI-PROJECT-22223333']},
                    'projectStatus': {'fiscal:year': {'commonEra:year': '2024'}},
                    'title': [{
                        'humanReadableValue': [{'text': 'テスト共同研究', 'lang': 'ja'}]
                    }],
                    'member': [
                        {
                            'sequence': 1,
                            'role': [{'code:roleInProject:kakenhi': 'principal_investigator'}],
                            'id:person:erad': '99999999',
                            'person:name': [{'text': '代表 太郎', 'lang': 'ja'}],
                            'institution:name': [{'text': '代表大学', 'lang': 'ja'}],
                        },
                        {
                            'sequence': 2,
                            'role': [{'code:roleInProject:kakenhi': 'co_investigator_buntan'}],
                            'id:person:erad': '11110000',
                            'person:name': [
                                {'text': '協力 花子', 'lang': 'ja'},
                                {'text': 'Hanako KYOURYOKU', 'lang': 'en'}
                            ],
                            'institution:name': [{'text': '協力大学', 'lang': 'ja'}],
                        },
                        {
                            'sequence': 3,
                            'role': [{'code:roleInProject:kakenhi': 'co_investigator_buntan'}],
                            'person:name': [{'text': '名前不明', 'lang': 'ja'}],
                        },
                    ]
                }
            ]
        }

        candidates = kaken_candidates('99999999')

        assert_equal(len(candidates), 3)
        primary = candidates[0]
        collab_with_id = candidates[1]
        collab_without_id = candidates[2]

        assert_equal(primary['erad'], '99999999')
        assert_equal(collab_with_id['erad'], '11110000')
        assert_true(collab_with_id.get('kaken_collaborator'))
        assert_equal(collab_with_id.get('kaken_role'), 'co_investigator_buntan')
        assert_equal(collab_with_id.get('source_erad'), '99999999')
        assert_equal(collab_with_id.get('kenkyukikan_mei_ja'), '協力大学')
        assert_equal(collab_with_id.get('kenkyusha_shimei_ja_msfullname'), '協力花子')
        assert_equal(collab_with_id.get('kenkyusha_shimei_en_msfullname'), 'Hanako KYOURYOKU')
        assert_true('display-fullname' not in collab_with_id)
        assert_equal(collab_with_id.get('display_fullname'), '協力 花子 (Hanako KYOURYOKU)')

        assert_equal(collab_without_id['erad'], '')
        assert_true(collab_without_id.get('kaken_collaborator'))
        assert_equal(collab_without_id.get('kenkyusha_shimei_ja_msfullname'), '名前不明')
        assert_true('display-fullname' not in collab_without_id)
        assert_equal(collab_without_id.get('display_fullname'), '名前不明')

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_collaborator_name_enriched_from_elasticsearch(self, mock_es_service):
        mock_es = mock.MagicMock()
        mock_es_service.return_value = mock_es
        mock_es.close.return_value = None

        primary_erad = '99999999'
        collaborator_erad = '11110000'

        primary_response = {
            'id:person:erad': [primary_erad],
            'name': {
                'name:familyName': [{'text': '代表', 'lang': 'ja'}],
                'name:givenName': [{'text': '太郎', 'lang': 'ja'}],
            },
            'work:project': [
                {
                    'recordSource': {'id:project:kakenhi': ['KAKENHI-PROJECT-22223333']},
                    'projectStatus': {'fiscal:year': {'commonEra:year': '2024'}},
                    'member': [
                        {
                            'role': [{'code:roleInProject:kakenhi': 'principal_investigator'}],
                            'id:person:erad': primary_erad,
                            'person:name': [{'text': '代表 太郎', 'lang': 'ja'}],
                        },
                        {
                            'role': [{'code:roleInProject:kakenhi': 'co_investigator_buntan'}],
                            'id:person:erad': collaborator_erad,
                            'person:name': [{'text': '協力 花子', 'lang': 'ja'}],
                        },
                    ],
                }
            ],
        }

        collaborator_response = {
            'name': {
                'name:familyName': [{'text': 'DOE', 'lang': 'en'}],
                'name:givenName': [{'text': 'John', 'lang': 'en'}],
            },
        }

        mock_es.get_researcher_by_erad.side_effect = [primary_response, collaborator_response]

        candidates = kaken_candidates(primary_erad)
        collaborator = next(c for c in candidates if c.get('erad') == collaborator_erad)

        assert_equal(collaborator.get('kenkyusha_shimei_en'), 'DOE|John')
        assert_equal(collaborator.get('kenkyusha_shimei_en_msfullname'), 'John DOE')
        assert_equal(collaborator.get('display_fullname'), '協力 花子 (John DOE)')
        assert_equal(mock_es.get_researcher_by_erad.call_count, 2)

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_collaborator_with_english_name_and_no_erad_skips_enrichment(self, mock_es_service):
        mock_es = mock.MagicMock()
        mock_es_service.return_value = mock_es
        mock_es.close.return_value = None

        primary_erad = '99999999'

        primary_response = {
            'id:person:erad': [primary_erad],
            'name': {
                'name:familyName': [{'text': '代表', 'lang': 'ja'}],
                'name:givenName': [{'text': '太郎', 'lang': 'ja'}],
            },
            'work:project': [
                {
                    'recordSource': {'id:project:kakenhi': ['KAKENHI-PROJECT-33334444']},
                    'projectStatus': {'fiscal:year': {'commonEra:year': '2024'}},
                    'member': [
                        {
                            'role': [{'code:roleInProject:kakenhi': 'principal_investigator'}],
                            'id:person:erad': primary_erad,
                            'person:name': [{'text': '代表 太郎', 'lang': 'ja'}],
                        },
                        {
                            'role': [{'code:roleInProject:kakenhi': 'co_investigator_buntan'}],
                            'person:name': [
                                {'text': '協力 花子', 'lang': 'ja'},
                                {'text': 'Hanako KYOURYOKU', 'lang': 'en'},
                            ],
                        },
                    ],
                }
            ],
        }

        mock_es.get_researcher_by_erad.return_value = primary_response

        candidates = kaken_candidates(primary_erad)
        collaborator = next(c for c in candidates if c.get('erad') == '')

        assert_equal(collaborator.get('kenkyusha_shimei_en_msfullname'), 'Hanako KYOURYOKU')
        assert_equal(mock_es.get_researcher_by_erad.call_count, 1)

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_no_matching_researchers(self, mock_es_service):
        """Test when no researchers match the ERAD ID"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = None
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('99999999')

        assert_equal(result, [])

    @mock.patch('addons.metadata.suggestions.kaken.suggest.kaken_candidates')
    def test_node_level_service_failure(self, mock_kaken_candidates):
        """Test that service failures affect node-level searches"""
        mock_kaken_candidates.side_effect = ESConnectionError('Service unavailable')

        # Service failure should affect the whole operation
        assert_raises(ESConnectionError, _kaken_candidates_for_node, self.project)

    def test_order_candidates_by_contributors_helper(self):
        """Order preserves contributor order and dedupes by kadai_id keeping first occurrence."""
        from addons.metadata.suggestions.utils import order_candidates_by_contributors

        me = '12345678'
        other = '87654321'
        contributors_order = [me, other]
        candidates = [
            {'erad': other, 'kadai_id': 'B', 'nendo': '2023'},
            {'erad': me,    'kadai_id': 'A', 'nendo': '2020'},
            {'erad': other, 'kadai_id': 'A', 'nendo': '2024'},  # duplicate id, should be dropped
        ]

        ordered = order_candidates_by_contributors(candidates, contributor_erads_order=contributors_order)
        # Expect contributor grouping order: me first, then other; and dedupe keeps first A (from me)
        assert_equal([c['erad'] for c in ordered], [me, other])
        assert_equal([c['kadai_id'] for c in ordered], ['A', 'B'])

    def test_deduplicate_suggestions_person_merges_ids(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei']
        suggestions = [
            {'key': 'erad:kenkyusha_no', 'value': {'kenkyusha_no': '1111', 'nendo': '2020'}},
            {'key': 'kaken:kenkyusha_shimei', 'value': {'erad': '1111', 'nendo': '2019'}},
            {'key': 'erad:kenkyusha_no', 'value': {'kenkyusha_no': '2222', 'nendo': '2021'}},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='person', key_order=key_order)
        # Expect 2 persons: '1111' (keep erad due to key priority with same-ish person), and '2222'
        assert_equal(len(deduped), 2)
        kept_keys = sorted([s['key'] for s in deduped])
        assert_equal(kept_keys, ['erad:kenkyusha_no', 'erad:kenkyusha_no'])

    def test_deduplicate_suggestions_person_respects_name_variants(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei']
        suggestions = [
            {'key': 'erad:kenkyusha_no', 'value': {
                'kenkyusha_no': '1111', 'nendo': '2020', 'kenkyusha_shimei_ja_msfullname': '山田太郎'
            }},
            {'key': 'kaken:kenkyusha_shimei', 'value': {
                'erad': '1111', 'nendo': '2021', 'kenkyusha_shimei_ja_msfullname': '山田 太郎'
            }},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='person', key_order=key_order)
        # Same ID but different normalized names -> treated as distinct, both kept
        assert_equal(len(deduped), 2)

    def test_deduplicate_suggestions_person_respects_institution_ja_variants(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei']
        suggestions = [
            {'key': 'erad:kenkyusha_no', 'value': {
                'kenkyusha_no': '2222', 'nendo': '2020',
                'kenkyusha_shimei_ja_msfullname': '山田太郎', 'kenkyukikan_mei_ja': '東京大学'
            }},
            {'key': 'kaken:kenkyusha_shimei', 'value': {
                'erad': '2222', 'nendo': '2021',
                'kenkyusha_shimei_ja_msfullname': '山田太郎', 'kenkyukikan_mei_ja': '京都大学'
            }},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='person', key_order=key_order)
        # Same ID+name but different institution ja -> distinct. Unified ordering applies (owner → year desc → key).
        assert_equal(len(deduped), 2)
        assert_equal([s['key'] for s in deduped], ['kaken:kenkyusha_shimei', 'erad:kenkyusha_no'])
        # Validate each element to catch subtle regressions
        first, second = deduped
        assert_equal(first['value'].get('erad'), '2222')
        assert_equal(first['value'].get('kenkyukikan_mei_ja'), '京都大学')
        assert_equal(first['value'].get('kenkyusha_shimei_ja_msfullname'), '山田太郎')
        assert_equal(second['value'].get('kenkyusha_no'), '2222')
        assert_equal(second['value'].get('kenkyukikan_mei_ja'), '東京大学')
        assert_equal(second['value'].get('kenkyusha_shimei_ja_msfullname'), '山田太郎')

    def test_deduplicate_suggestions_project_key_priority_then_year(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['kaken:kadai_id', 'erad:kadai_id']
        suggestions = [
            {'key': 'kaken:kadai_id', 'value': {'kadai_id': 'P1', 'nendo': '2020'}},
            {'key': 'erad:kadai_id', 'value': {'kadai_id': 'P1', 'nendo': '2021'}},
            {'key': 'kaken:kadai_id', 'value': {'kadai_id': 'P2', 'nendo': '2019'}},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='project', key_order=key_order)
        # Unified ordering then first-wins dedup: newer year appears first, then key priority.
        by_id = {s['value']['kadai_id']: s for s in deduped}
        assert_equal(by_id['P1']['key'], 'erad:kadai_id')
        assert_equal(set(by_id.keys()), {'P1', 'P2'})

    def test_deduplicate_suggestions_person_newest_year_tiebreak_same_key(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei']
        suggestions = [
            {'key': 'erad:kenkyusha_no', 'value': {
                'kenkyusha_no': '3333', 'nendo': '2019',
                'kenkyusha_shimei_ja_msfullname': '佐藤次郎', 'kenkyukikan_mei_ja': '大阪大学'
            }},
            {'key': 'erad:kenkyusha_no', 'value': {
                'kenkyusha_no': '3333', 'nendo': '2021',
                'kenkyusha_shimei_ja_msfullname': '佐藤次郎', 'kenkyukikan_mei_ja': '大阪大学'
            }},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='person', key_order=key_order)
        # Only the newest year remains; validate full content of the survivor
        assert_equal(len(deduped), 1)
        only = deduped[0]
        assert_equal(only['key'], 'erad:kenkyusha_no')
        assert_equal(only['value'].get('kenkyusha_no'), '3333')
        assert_equal(only['value'].get('kenkyukikan_mei_ja'), '大阪大学')
        assert_equal(only['value'].get('kenkyusha_shimei_ja_msfullname'), '佐藤次郎')
        assert_equal(only['value'].get('nendo'), '2021')

    def test_deduplicate_suggestions_project_newest_year_tiebreak_same_key(self):
        from addons.metadata.suggestions.utils import deduplicate_suggestions

        key_order = ['kaken:kadai_id']
        suggestions = [
            {'key': 'kaken:kadai_id', 'value': {'kadai_id': 'PX', 'nendo': '2018'}},
            {'key': 'kaken:kadai_id', 'value': {'kadai_id': 'PX', 'nendo': '2022'}},
        ]
        deduped = deduplicate_suggestions(suggestions, mode='project', key_order=key_order)
        assert_equal(len(deduped), 1)
        assert_equal(deduped[0]['value']['nendo'], '2022')
        assert_equal(deduped[0]['key'], 'kaken:kadai_id')

    def test_order_suggestions_by_contributors_key_priority_tiebreak(self):
        from addons.metadata.suggestions.utils import order_suggestions_by_contributors

        me, other = '11', '22'
        key_list = ['kaken:kenkyusha_shimei', 'erad:kenkyusha_no']
        # same owner and year, key order should decide
        sugs = [
            {'key': 'erad:kenkyusha_no', 'value': {'kenkyusha_no': me, 'nendo': '2020'}},
            {'key': 'kaken:kenkyusha_shimei', 'value': {'erad': me, 'nendo': '2020'}},
            {'key': 'erad:kenkyusha_no', 'value': {'kenkyusha_no': other, 'nendo': '2020'}},
            {'key': 'kaken:kenkyusha_shimei', 'value': {'erad': other, 'nendo': '2020'}},
        ]
        ordered = order_suggestions_by_contributors(sugs, [me, other], key_list)
        ordered_keys = [s['key'] for s in ordered[:2]]
        assert_equal(ordered_keys, ['kaken:kenkyusha_shimei', 'erad:kenkyusha_no'])

    def test_order_suggestions_respects_key_list_for_contributor_keys(self):
        from addons.metadata.suggestions.utils import order_suggestions_by_contributors

        me, other = '11', '22'
        key_list = ['contributor:name', 'contributor:erad', 'kaken:kenkyusha_shimei', 'erad:kenkyusha_no']
        sugs = [
            {'key': 'kaken:kenkyusha_shimei', 'value': {'erad': me, 'nendo': '2020'}},
            {'key': 'contributor:name', 'value': {'erad': me}},
            {'key': 'erad:kenkyusha_no', 'value': {'kenkyusha_no': other, 'nendo': '2021'}},
            {'key': 'contributor:erad', 'value': {'erad': other}},
        ]
        ordered = order_suggestions_by_contributors(sugs, [me, other], key_list)
        # Unified ordering: within each owner, higher year wins before key priority when years differ
        first_owner = [s for s in ordered if (s['value'].get('erad') or s['value'].get('kenkyusha_no')) == me]
        second_owner = [s for s in ordered if (s['value'].get('erad') or s['value'].get('kenkyusha_no')) == other]
        assert_equal(first_owner[0]['key'], 'kaken:kenkyusha_shimei')
        assert_equal(second_owner[0]['key'], 'erad:kenkyusha_no')

    def test_classify_mode_for_contributor_keys(self):
        from addons.metadata.suggestions.utils import classify_mode_for_keys
        assert_equal(classify_mode_for_keys(['contributor:name']), 'person')
        assert_equal(classify_mode_for_keys(['contributor:erad', 'kaken:kenkyusha_shimei']), 'person')
        # ERAD project key should be classified as project
        assert_equal(classify_mode_for_keys(['erad:kadai_id']), 'project')

    def test_process_change_list_parses_all_actions(self):
        # Sample NRID-like changelist XML (truncated)
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            '        xmlns:rs="http://www.openarchives.org/rs/terms/">\n'
            '  <rs:md capability="changelist" from="2025-08-09T05:00:03+09:00" '
            '        until="2025-08-30T05:00:02+09:00" />\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000000961393.json</loc>'
            '      <lastmod>2025-08-30T03:30:03+09:00</lastmod><rs:md change="created"/></url>\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000000992182.json</loc>'
            '      <lastmod>2025-08-30T03:30:04+09:00</lastmod><rs:md change="updated"/></url>\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000001021823.json</loc>'
            '      <lastmod>2025-08-30T03:30:05+09:00</lastmod><rs:md change="deleted"/></url>\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000001029504.json</loc>'
            '      <lastmod>2025-08-30T03:30:06+09:00</lastmod><rs:md change="updated"/></url>\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000001029505.json</loc>'
            '      <lastmod>2025-08-30T03:30:00+09:00</lastmod><rs:md change="updated"/></url>\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000001029506.json</loc>'
            '      <lastmod>2025-08-30T03:29:59+09:00</lastmod><rs:md change="updated"/></url>\n'
            '</urlset>'
        )

        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        # Patch the XML fetcher to return our sample
        client._fetch_xml = lambda url: ET.fromstring(xml.encode('utf-8'))

        changes = list(client.process_change_list('https://nrid.nii.ac.jp/sitemaps/changelist00169.xml'))

        # All entries are returned in order; downstream watermark decides applicability
        assert_equal(len(changes), 6)
        actions = [a for (a, _, _) in changes]
        assert_equal(actions, ['created', 'updated', 'deleted', 'updated', 'updated', 'updated'])

    def test_should_apply_change_enforces_strictly_newer_lastmod(self):
        existing = {'_last_updated': '2025-08-30T03:30:05+09:00'}
        newer = parse_datetime('2025-08-29T18:30:06+00:00')  # 1 second after existing in UTC
        same = parse_datetime('2025-08-29T18:30:05+00:00')   # equal instant
        older = parse_datetime('2025-08-29T18:30:04+00:00')

        assert_true(_should_apply_change(newer, existing, 'https://example.org/doc.json'))
        assert_false(_should_apply_change(same, existing, 'https://example.org/doc.json'))
        assert_false(_should_apply_change(older, existing, 'https://example.org/doc.json'))

    def test_should_apply_change_handles_missing_or_invalid_state(self):
        # Missing existing -> apply
        ts = parse_datetime('2025-08-29T18:30:06+00:00')
        assert_true(_should_apply_change(ts, None, 'https://example.org/doc.json'))

        # Missing stored lastmod -> apply
        assert_true(_should_apply_change(ts, {}, 'https://example.org/doc.json'))

        # Invalid stored lastmod -> apply but should not raise
        assert_true(_should_apply_change(ts, {'_last_updated': 'not-a-date'}, 'https://example.org/doc.json'))

        # Missing new lastmod -> raises
        assert_raises(ValueError, _should_apply_change, None, {}, 'https://example.org/doc.json')

    def test_process_change_list_requires_change_metadata(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:rs="http://www.openarchives.org/rs/terms/">\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000002000000.json</loc>'
            '      <lastmod>2025-08-30T03:30:03+09:00</lastmod></url>\n'
            '</urlset>'
        )

        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        client._fetch_xml = lambda url: ET.fromstring(xml.encode('utf-8'))

        assert_raises(ValueError, list, client.process_change_list('https://nrid.nii.ac.jp/sitemaps/changelist00170.xml'))

    def test_process_change_list_requires_lastmod(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:rs="http://www.openarchives.org/rs/terms/">\n'
            '  <url><loc>https://nrid.nii.ac.jp/nrid/1000002000001.json</loc>'
            '      <rs:md change="created"/></url>\n'
            '</urlset>'
        )

        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        client._fetch_xml = lambda url: ET.fromstring(xml.encode('utf-8'))

        assert_raises(ValueError, list, client.process_change_list('https://nrid.nii.ac.jp/sitemaps/changelist00171.xml'))

    def test_fetch_researcher_data_raises_http_error_on_server_failure(self):
        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        response = mock.MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError('500 error', response=response)
        client.session = mock.MagicMock()
        client.session.get.return_value = response

        assert_raises(requests.HTTPError, client.fetch_researcher_data, 'https://nrid.nii.ac.jp/nrid/123.json')
        assert_false(response.json.called)

    def test_fetch_researcher_data_handles_empty_body(self):
        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        response = mock.MagicMock()
        response.status_code = 200
        response.content = b''
        response.raise_for_status.return_value = None
        client.session = mock.MagicMock()
        client.session.get.return_value = response

        result = client.fetch_researcher_data('https://nrid.nii.ac.jp/nrid/789.json')
        assert_false(response.json.called)
        assert_equal(result, {'_source_url': 'https://nrid.nii.ac.jp/nrid/789.json'})

    def test_fetch_researcher_data_propagates_value_error_for_ok_response(self):
        client = ResourceSyncClient('https://nrid.nii.ac.jp/.well-known/resourcesync')
        response = mock.MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError('Expecting value')
        client.session = mock.MagicMock()
        client.session.get.return_value = response

        assert_raises(ValueError, client.fetch_researcher_data, 'https://nrid.nii.ac.jp/nrid/456.json')
        response.json.assert_called_once()


# Sample real KAKEN researcher data with dummy personal information
SAMPLE_KAKEN_RESEARCHER = {
    'accn': 'id:person:kakenhi**12345',
    'id:person:erad': ['12345678'],
    'recordSource': {
        'id:person:kakenhi': ['12345', '67890']
    },
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
    'affiliations:history': [
        {
            'sequence': 1,
            'since': {'commonEra:year': 1999, 'month': 4, 'day': 1},
            'until': {'commonEra:year': 2001, 'month': 4, 'day': 1},
            'affiliation:institution': {
                'humanReadableValue': [
                    {'text': 'テスト大学', 'lang': 'ja'},
                    {'text': 'Test University', 'lang': 'en'}
                ]
            },
            'affiliation:department': {
                'humanReadableValue': [
                    {'text': '研究所', 'lang': 'ja'}
                ]
            },
            'affiliation:jobTitle': {
                'humanReadableValue': [
                    {'text': '教授', 'lang': 'ja'}
                ]
            }
        }
    ],
    'work:project': [
        {
            'recordSource': {
                'id:project:kakenhi': ['KAKENHI-PROJECT-11111111']
            },
            'review_section': [
                {
                    'humanReadableValue': [
                        {'text': '小区分38010: テスト分野', 'lang': 'ja'},
                        {'text': 'Basic Section 38010: Test field', 'lang': 'en'}
                    ]
                }
            ],
            'title': [
                {
                    'humanReadableValue': [
                        {'text': 'テスト研究プロジェクト１', 'lang': 'ja'},
                        {'text': 'Test Research Project 1', 'lang': 'en'}
                    ]
                }
            ],
            'since': {'fiscal:year': {'commonEra:year': '1989'}},
            'until': {'fiscal:year': {'commonEra:year': '1989'}},
            'category': [
                {
                    'humanReadableValue': [
                        {'text': '一般研究(C)', 'lang': 'ja'},
                        {'text': 'Grant-in-Aid for General Scientific Research (C)', 'lang': 'en'}
                    ]
                }
            ],
            'institution': [
                {
                    'humanReadableValue': [
                        {'text': 'テスト大学', 'lang': 'ja'},
                        {'text': 'Test University', 'lang': 'en'}
                    ]
                }
            ]
        },
        {
            'recordSource': {
                'id:project:kakenhi': ['KAKENHI-PROJECT-22222222']
            },
            'title': [
                {
                    'humanReadableValue': [
                        {'text': 'テスト研究プロジェクト２', 'lang': 'ja'}
                    ]
                }
            ],
            'since': {'fiscal:year': {'commonEra:year': '1990'}},
            'until': {'fiscal:year': {'commonEra:year': '1990'}}
        }
    ],
    '_source_url': 'https://nrid.nii.ac.jp/nrid/1000012345678.json'
}


class TestKakenWithSampleData(OsfTestCase):
    """Tests for processing KAKEN data with sample data structures"""

    def setUp(self):
        super(TestKakenWithSampleData, self).setUp()
        from addons.metadata.suggestions.kaken.transformer import KakenToElasticsearchTransformer
        self.transformer = KakenToElasticsearchTransformer()
        self.user = UserFactory()
        self.user.erad = '12345678'
        self.user.save()
        self.project = ProjectFactory(creator=self.user)
        self.project.save()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        super(TestKakenWithSampleData, self).tearDown()

    def test_transform_sample_researcher_data(self):
        """Test transforming sample KAKEN researcher data structure"""
        # Transform the data
        es_doc = self.transformer.transform_researcher(SAMPLE_KAKEN_RESEARCHER)

        # Verify basic structure is preserved
        assert_equal(es_doc['accn'], 'id:person:kakenhi**12345')
        assert_equal(es_doc['id:person:erad'], ['12345678'])
        assert_in('_source_url', es_doc)

        # Verify search_text is generated
        assert_in('search_text', es_doc)
        assert_in('山田 太郎', es_doc['search_text'])
        assert_in('YAMADA Taro', es_doc['search_text'])
        assert_in('テスト大学', es_doc['search_text'])
        assert_in('テスト研究プロジェクト１', es_doc['search_text'])

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_index_and_retrieve_researcher(self, mock_req):
        """Test indexing and retrieving researcher data with requests-based client"""
        from addons.metadata.suggestions.kaken.elasticsearch import KakenElasticsearchService

        # Mock responses for index (201) and search (200)
        class DummyResp:
            def __init__(self, status_code=200, text='', body=None):
                self.status_code = status_code
                self.text = text
                self._body = body or {}

            def json(self):
                return self._body

        def side_effect(method, path, **kwargs):
            if method == 'PUT' and path.startswith('/test_kaken/_doc/'):
                return DummyResp(status_code=201, text='created')
            if method == 'POST' and path == '/test_kaken/_search':
                return DummyResp(status_code=200, body={
                    'hits': {
                        'total': 1,
                        'hits': [{'_source': SAMPLE_KAKEN_RESEARCHER}]
                    }
                })
            return DummyResp(status_code=200)

        mock_req.side_effect = side_effect

        # Initialize service
        es_service = KakenElasticsearchService(
            hosts=['http://test:9200'],
            index_name='test_kaken'
        )

        # Index the document
        transformed = self.transformer.transform_researcher(SAMPLE_KAKEN_RESEARCHER)
        ok = es_service.index_researcher(transformed)
        assert_true(ok)

        # Verify index endpoint
        called_methods = [c[0][0] for c in mock_req.call_args_list]
        called_paths = [c[0][1] for c in mock_req.call_args_list]
        assert_in('PUT', called_methods)
        assert_true(any(p.startswith('/test_kaken/_doc/') for p in called_paths))

        # Retrieve by ERAD ID
        result = es_service.get_researcher_by_erad('12345678')

        # Verify result
        assert_is_not_none(result)
        assert_equal(result['id:person:erad'], ['12345678'])

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_kaken_candidates_generation_with_sample_structure(self, mock_service_class):
        """Test generating candidates from sample researcher data structure"""
        # Setup mock service
        mock_service = mock.MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_researcher_by_erad.return_value = SAMPLE_KAKEN_RESEARCHER
        mock_service.close.return_value = None

        # Get candidates
        candidates = kaken_candidates('12345678')

        # Should have one candidate per project
        assert_equal(len(candidates), 2)

        # Verify first candidate
        candidate1 = candidates[0]
        assert_equal(candidate1['erad'], '12345678')
        assert_equal(candidate1['kadai_id'], '11111111')
        assert_equal(candidate1['kenkyusha_shimei_ja'], '山田|太郎')
        assert_equal(candidate1['kenkyusha_shimei_en'], 'YAMADA|Taro')
        assert_in('テスト大学', candidate1['kenkyukikan_mei'])
        assert_equal(candidate1['nendo'], '1989')
        assert_equal(candidate1['japan_grant_number'], 'JP11111111')
        # bunya_cd uses Large Section code mapped from small -> 'A189' -> '189'
        assert_equal(candidate1['bunya_cd'], '189')
        # bunya_mei is large section name (not the small field name from review_section)
        assert_true(candidate1['bunya_mei'])
        assert_not_equal(candidate1['bunya_mei'], 'テスト分野')
        # English name resolved via e‑Rad schema mapping for code '189'
        assert_equal(candidate1.get('bunya_mei_en'), 'Life Science')

        # Verify second candidate
        candidate2 = candidates[1]
        assert_equal(candidate2['kadai_id'], '22222222')
        assert_equal(candidate2['nendo'], '1990')

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_filtering_candidates_by_field(self, mock_service_class):
        """Test filtering candidates by various fields with sample data structure"""
        # Setup mock service
        mock_service = mock.MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_researcher_by_erad.return_value = SAMPLE_KAKEN_RESEARCHER
        mock_service.close.return_value = None

        # Test filtering by institution name
        candidates = kaken_candidates('12345678', kenkyukikan_mei='テスト')
        assert_equal(len(candidates), 2)  # Both projects should match

        # Test filtering by project title
        candidates = kaken_candidates('12345678', kadai_mei='プロジェクト２')
        assert_equal(len(candidates), 1)
        assert_equal(candidates[0]['kadai_id'], '22222222')

        # Test filtering by non-existent text
        candidates = kaken_candidates('12345678', kenkyusha_shimei='鈴木')
        assert_equal(len(candidates), 0)

    def test_transform_researcher_without_projects(self):
        """Test transforming researcher with no projects"""
        researcher_no_projects = dict(SAMPLE_KAKEN_RESEARCHER)
        researcher_no_projects['work:project'] = []

        # Transform the data
        es_doc = self.transformer.transform_researcher(researcher_no_projects)

        # Should still have basic data
        assert_equal(es_doc['accn'], 'id:person:kakenhi**12345')
        assert_in('search_text', es_doc)
        assert_in('山田 太郎', es_doc['search_text'])

    def test_transform_researcher_with_malformed_data(self):
        """Test transformer handles malformed data gracefully"""
        malformed_researcher = {
            'accn': 'test123',
            'id:person:erad': '99999999',  # String instead of list
            'name': {
                'humanReadableValue': 'Test Name'  # String instead of list
            },
            'work:project': None  # None instead of list
        }

        # Should not raise exception
        es_doc = self.transformer.transform_researcher(malformed_researcher)
        assert_equal(es_doc['accn'], 'test123')
        assert_in('search_text', es_doc)


class _DummyResp:
    def __init__(self, status_code=200, text='', body=None):
        self.status_code = status_code
        self.text = text
        self._body = body or {}

    def json(self):
        return self._body


class TestKakenEsClientIntegrated(object):
    def setup(self):
        self.es = KakenElasticsearchService(
            hosts=['http://localhost:9200'],
            index_name='test_kaken'
        )

    def teardown(self):
        self.es.close()

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_index_exists_true_false(self, mock_req):
        mock_req.return_value = _DummyResp(status_code=200)
        assert_true(self.es.index_exists())

        mock_req.return_value = _DummyResp(status_code=404)
        assert_false(self.es.index_exists())

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_create_index_typeless_mapping(self, mock_req):
        # exists() -> 404, then PUT mapping -> 200
        mock_req.side_effect = [
            _DummyResp(status_code=404),
            _DummyResp(status_code=200, text='ack')
        ]
        self.es.create_index()

        # Second call is the PUT /{index} with mapping in json_body
        _, kwargs = mock_req.call_args
        body = kwargs.get('json_body')
        assert_is_not_none(body)
        assert_in('mappings', body)
        assert_in('properties', body['mappings'])
        assert_not_in('doc', body['mappings'])

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_index_puts_to_doc_endpoint(self, mock_req):
        import hashlib
        mock_req.return_value = _DummyResp(status_code=201)
        url = 'https://nrid.nii.ac.jp/nrid/1000012345678.json'
        ok = self.es.index_researcher({'_source_url': url, 'accn': 'abc', 'search_text': 'x'})
        assert_true(ok)
        args, kwargs = mock_req.call_args
        assert_equal(args[0], 'PUT')
        expected_id = hashlib.sha256(url.encode('utf-8')).hexdigest()
        assert_equal(args[1], f'/test_kaken/_doc/{expected_id}')

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_bulk_ndjson_typeless_and_raises_on_item_errors(self, mock_req):
        # First call: POST /_bulk returns one item with error
        mock_req.return_value = _DummyResp(status_code=200, body={
            'took': 1,
            'errors': True,
            'items': [
                {'index': {'_index': 'test_kaken', '_id': 'ok', 'status': 201}},
                {'index': {'_index': 'test_kaken', '_id': 'ng', 'status': 400, 'error': {'reason': 'bad'}}},
            ]
        })

        with assert_raises(KakenBulkError):
            self.es.bulk_index([
                {'_source_url': 'https://nrid.nii.ac.jp/nrid/ok.json', 'accn': 'ok', 'search_text': ''},
                {'_source_url': 'https://nrid.nii.ac.jp/nrid/ng.json', 'accn': 'ng', 'search_text': ''},
            ], batch_size=100)

        # Verify NDJSON payload structure (no _type)
        _, kwargs = mock_req.call_args
        payload = kwargs.get('data')
        assert_is_not_none(payload)
        assert_in('"_index": "test_kaken"', payload)
        import hashlib
        ok_id = hashlib.sha256('https://nrid.nii.ac.jp/nrid/ok.json'.encode('utf-8')).hexdigest()
        assert_in(f'"_id": "{ok_id}"', payload)
        assert_not_in('"_type"', payload)

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_search_wraps_size_and_from(self, mock_req):
        mock_req.return_value = _DummyResp(status_code=200, body={'hits': {'total': 0, 'hits': []}})
        q = {'query': {'match_all': {}}}
        res = self.es.search_researchers(q, size=5, from_=10)
        assert_equal(res['hits']['total'], 0)
        args, kwargs = mock_req.call_args
        sent = kwargs.get('json_body')
        assert_equal(sent.get('size'), 5)
        assert_equal(sent.get('from'), 10)

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_get_404_returns_none(self, mock_req):
        mock_req.return_value = _DummyResp(status_code=404)
        assert_is_none(self.es.get_researcher_by_id('none'))

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.KakenElasticsearchService._req')
    def test_delete_404_treated_success(self, mock_req):
        mock_req.return_value = _DummyResp(status_code=404)
        assert_true(self.es.delete_researcher('none'))

    @mock.patch('requests.Session.request')
    def test_transport_error_on_connection_issue(self, mock_request):
        from requests import ConnectionError
        mock_request.side_effect = ConnectionError('boom')
        with assert_raises(KakenTransportError):
            # call a simple HEAD
            self.es._req('HEAD', '/x')


def test_review_map_lookup_small_with_hierarchical_json():
    """Verify review_map.lookup_small works with hierarchical JSON and no small_name_en."""
    import json, os
    from addons.metadata.suggestions.kaken import review_map

    # Reset cache and load actual review_sections.json in repo
    review_map._CACHE = None
    data_path = os.path.join('addons', 'metadata', 'suggestions', 'kaken', 'data', 'review_sections.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Pick the first small section from the hierarchical data
    lg = next(iter(data))
    child = next(iter(lg.get('children') or []))
    sc = child['small_code']
    code5 = sc[-5:] if isinstance(sc, str) and len(sc) >= 5 else sc

    rec = review_map.lookup_small(code5)
    assert_is_not_none(rec)
    assert_equal(rec.get('small_name_ja'), child.get('small_name_ja'))
    assert_equal(rec.get('large_code'), lg.get('large_code'))
    assert_equal(rec.get('large_name_ja'), lg.get('large_name_ja'))
    # small_name_en is optional and currently absent; loader should return empty string
    assert_equal(rec.get('small_name_en', ''), '')

    # Negative case
    assert_is_none(review_map.lookup_small('00000'))
