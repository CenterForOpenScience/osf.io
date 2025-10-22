# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from osf.models import BaseFileNode
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory

from .. import SHORT_NAME
from .. import settings
from .utils import BaseAddonTestCase
from website.util import api_url_for
from addons.metadata.models import NodeSettings
from osf_tests import factories



class TestViews(BaseAddonTestCase, OsfTestCase):

    def setUp(self):
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.mock_fetch_metadata_asset_files.stop()

    def test_no_file_metadata(self):
        url = self.project.api_url_for('{}_get_project'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_true('data' in res.json)
        assert_equals(res.json['data']['type'], 'metadata-node-project')
        assert_equals(res.json['data']['id'], self.node_settings.owner._id)
        assert_true('attributes' in res.json['data'])
        assert_equals(res.json['data']['attributes']['editable'], True)
        assert_true('features' in res.json['data']['attributes'])
        assert_true('dataset_importing' in res.json['data']['attributes']['features'])
        assert_true('exporting' in res.json['data']['attributes']['features'])
        assert_equals(res.json['data']['attributes']['files'], [])
        assert_equals(res.json['data']['attributes']['repositories'], [])

    def test_single_file_metadata(self):
        self.node_settings.set_file_metadata('osfstorage/', {
            'path': 'osfstorage/',
            'folder': True,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': 'xxxx',
                    'data': {
                        'test': True,
                    },
                },
            ],
        })
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_project'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['attributes']['files'], [
            {
                'path': 'osfstorage/',
                'generated': False,
                'hash': '1234567890',
                'urlpath': '/{}/files/dir/osfstorage/'.format(self.node_settings.owner._id),
                'folder': True,
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            }
        ])


class TestSuggestionsViews(BaseAddonTestCase, OsfTestCase):

    fake_metadata_asset_pool = [
        {'title': 'apple'},
        {'title': 'pine'},
        {'title': 'pineapple'},
    ]

    def setUp(self):
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.mock_fetch_metadata_asset_files.stop()

    def test_no_key(self):
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='fake')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equals(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', 'http://localhost:9200')
    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_erad_and_kaken_person_mode_order_and_dedup(self, mock_es_service):
        # Setup ERAD records for self and collaborator
        from addons.metadata.models import ERadRecord
        self.user.erad = '11111111'
        self.user.save()
        collab = factories.AuthUserFactory()
        collab.erad = '22222222'
        collab.save()
        self.project.add_contributor(collab, save=True)

        ERadRecord.objects.create(
            kenkyusha_no=self.user.erad,
            kenkyusha_shimei='姓|名|LAST|FIRST',
            kenkyukikan_mei='研究機関名|Research Institute',
            nendo=2020,
        )
        ERadRecord.objects.create(
            kenkyusha_no=collab.erad,
            kenkyusha_shimei='姓2|名2|LAST2|FIRST2',
            kenkyukikan_mei='研究機関名2|Research Institute 2',
            nendo=2019,
        )

        # Mock KAKEN ES to return one project per user
        def get_researcher_by_erad_side_effect(erad):
            if erad == self.user.erad:
                return {
                    'id:person:erad': [erad],
                    'name': {
                        'humanReadableValue': [{'text': '山田 太郎', 'lang': 'ja'}],
                        'name:familyName': [{'text': '山田', 'lang': 'ja'}],
                        'name:givenName': [{'text': '太郎', 'lang': 'ja'}],
                    },
                    'affiliations:history': [],
                    'work:project': [{
                        'recordSource': {'id:project:kakenhi': 'KAKENHI-PROJECT-SELF1'},
                        'since': {'fiscal:year': {'commonEra:year': '2020'}},
                        'title': [{'humanReadableValue': [{'text': 'Self1', 'lang': 'ja'}]}],
                    }],
                }
            if erad == collab.erad:
                return {
                    'id:person:erad': [erad],
                    'name': {
                        'humanReadableValue': [{'text': '佐藤 次郎', 'lang': 'ja'}],
                        'name:familyName': [{'text': '佐藤', 'lang': 'ja'}],
                        'name:givenName': [{'text': '次郎', 'lang': 'ja'}],
                    },
                    'affiliations:history': [],
                    'work:project': [{
                        'recordSource': {'id:project:kakenhi': 'KAKENHI-PROJECT-COLL1'},
                        'since': {'fiscal:year': {'commonEra:year': '2021'}},
                        'title': [{'humanReadableValue': [{'text': 'Collab1', 'lang': 'ja'}]}],
                    }],
                }
            return None

        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.side_effect = get_researcher_by_erad_side_effect
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        # Call combined suggestions endpoint (no keyword filter)
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME), filepath='dir/osfstorage/dir1/')
        res = self.app.get(url, auth=self.user.auth, params={'key[]': ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei'], 'keyword': ''})
        assert_equals(res.status_code, http_status.HTTP_200_OK)

        suggestions = res.json['data']['attributes']['suggestions']
        keys = [s['key'] for s in suggestions]
        owners = [s['value'].get('erad', s['value'].get('kenkyusha_no')) for s in suggestions]

        # Policy: person keys with institution/name variants are distinct.
        # Order by contributor (self first), then year desc, then key order for ties.
        # Self has ERAD(2020, inst_ja present) and KAKEN(2020, inst_ja empty) -> both kept, ERAD first by key order.
        # Collaborator has ERAD(2019) and KAKEN(2021) -> both kept, KAKEN first by year.
        assert_equal(len(suggestions), 4)
        assert_equal(owners[:2], [self.user.erad, self.user.erad])
        assert_equal(keys[:2], ['erad:kenkyusha_no', 'kaken:kenkyusha_shimei'])
        assert_equal(owners[2:], [collab.erad, collab.erad])
        assert_equal(keys[2:], ['kaken:kenkyusha_shimei', 'erad:kenkyusha_no'])

    @mock.patch.object(NodeSettings, 'get_metadata_assets')
    def test_dir_with_multiple_keys(self, mock_get_metadata_assets):
        mock_get_metadata_assets.return_value = self.fake_metadata_asset_pool
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='dir/osfstorage/dir1/')
        res = self.app.get(url, auth=self.user.auth, params={'key[]': ['file-data-number', 'asset:title']})
        assert_equals(res.status_code, http_status.HTTP_200_OK)
        assert_equals(res.json, {
            'data': {
                'id': self.project._id,
                'type': 'file-metadata-suggestion',
                'attributes': {
                    'filepath': 'dir/osfstorage/dir1/',
                    'suggestions': [
                        {
                            'key': 'file-data-number',
                            'value': 'files/dir/osfstorage/dir1/',
                        },
                        {
                            'key': 'asset:title',
                            'value': {
                                'title': 'apple'
                            }
                        },
                        {
                            'key': 'asset:title',
                            'value': {
                                'title': 'pine'
                            }
                        },
                        {
                            'key': 'asset:title',
                            'value': {
                                'title': 'pineapple'
                            }
                        },
                    ]
                }
            }
        })

    @mock.patch.object(NodeSettings, 'get_metadata_assets')
    def test_file_with_multiple_keys(self, mock_get_metadata_assets):
        mock_get_metadata_assets.return_value = self.fake_metadata_asset_pool
        filepath = 'osfstorage/file.txt'
        filepath_guid = 'abcde'
        mock_node = mock.Mock()
        mock_node.get_guid.return_value = mock.Mock(_id=filepath_guid)
        mock_resolved_class = mock.Mock()
        mock_resolved_class.get_or_create.return_value = mock_node
        with mock.patch.object(BaseFileNode, 'resolve_class', return_value=mock_resolved_class):
            url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                           filepath=filepath)
            res = self.app.get(url, auth=self.user.auth, params={'key[]': ['file-data-number', 'asset:title']})
            assert_equals(res.status_code, http_status.HTTP_200_OK)
            assert_equals(res.json, {
                'data': {
                    'id': self.project._id,
                    'type': 'file-metadata-suggestion',
                    'attributes': {
                        'filepath': filepath,
                        'suggestions': [
                            {
                                'key': 'file-data-number',
                                'value': filepath_guid,
                            },
                            {
                                'key': 'asset:title',
                                'value': {
                                    'title': 'apple'
                                }
                            },
                            {
                                'key': 'asset:title',
                                'value': {
                                    'title': 'pine'
                                }
                            },
                            {
                                'key': 'asset:title',
                                'value': {
                                    'title': 'pineapple'
                                }
                            },
                        ]
                    }
                }
            })

    @mock.patch.object(NodeSettings, 'get_metadata_assets')
    def test_asset_title_with_keyword(self, mock_get_metadata_assets):
        mock_get_metadata_assets.return_value = self.fake_metadata_asset_pool
        filepath = 'dir/osfstorage/dir1/'
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath=filepath)
        res = self.app.get(url, params={'key': 'asset:title', 'keyword': 'app'}, auth=self.user.auth)
        assert_equals(res.status_code, http_status.HTTP_200_OK)
        assert_equals(res.json, {
            'data': {
                'id': self.project._id,
                'type': 'file-metadata-suggestion',
                'attributes': {
                    'filepath': filepath,
                    'suggestions': [
                        {
                            'key': 'asset:title',
                            'value': {
                                'title': 'apple'
                            }
                        },
                        {
                            'key': 'asset:title',
                            'value': {
                                'title': 'pineapple'
                            }
                        },
                    ]
                }
            }
        })

    def test_invalid_key(self):
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='dir/osfstorage/dir1/')
        res = self.app.get(url, params={'key': 'invalid'}, auth=self.user.auth, expect_errors=True)
        assert_equals(res.status_code, http_status.HTTP_400_BAD_REQUEST)


class TestEradCandidatesOrderingView(BaseAddonTestCase, OsfTestCase):
    def setUp(self):
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.mock_fetch_metadata_asset_files.stop()

    @mock.patch('addons.metadata.views.kaken_candidates')
    @mock.patch('addons.metadata.views.erad_candidates')
    def test_self_first_then_collaborators_over_http(self, mock_erad_candidates, mock_kaken_candidates):
        # Prepare ERAD IDs
        self.user.erad = '12345678'
        self.user.save()
        collaborator = factories.AuthUserFactory()
        collaborator.erad = '87654321'
        collaborator.save()
        self.project.add_contributor(collaborator, save=True)

        # ERAD DB returns none (focus on KAKEN path)
        mock_erad_candidates.return_value = []

        # KAKEN: self has older year, collaborator has newer year
        def kc_side_effect(erad_value, **kwargs):
            if erad_value == self.user.erad:
                return [{
                    'erad': self.user.erad,
                    'kadai_id': 'KSELF',
                    'nendo': '2020',
                }]
            if erad_value == collaborator.erad:
                return [{
                    'erad': collaborator.erad,
                    'kadai_id': 'KCOLL',
                    'nendo': '2023',
                }]
            return []

        mock_kaken_candidates.side_effect = kc_side_effect

        # Call HTTP endpoint
        url = self.project.api_url_for('{}_get_erad_candidates'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)

        assert_equals(res.status_code, http_status.HTTP_200_OK)
        records = res.json['data']['attributes']['records']
        # Self-first ordering expected, regardless of year
        assert_equal(len(records), 2)
        assert_equal(records[0]['erad'], self.user.erad)
        assert_equal(records[1]['erad'], collaborator.erad)

    @mock.patch('addons.metadata.views.kaken_candidates')
    @mock.patch('addons.metadata.views.erad_candidates')
    def test_dedup_by_kadai_id_prefers_self(self, mock_erad_candidates, mock_kaken_candidates):
        # Prepare ERAD IDs
        self.user.erad = '12345678'
        self.user.save()
        collaborator = factories.AuthUserFactory()
        collaborator.erad = '87654321'
        collaborator.save()
        self.project.add_contributor(collaborator, save=True)

        mock_erad_candidates.return_value = []

        # Both return the same kadai_id; collaborator has newer year
        def kc_side_effect(erad_value, **kwargs):
            if erad_value == self.user.erad:
                return [{
                    'erad': self.user.erad,
                    'kadai_id': 'KDUP',
                    'nendo': '2020',
                }]
            if erad_value == collaborator.erad:
                return [{
                    'erad': collaborator.erad,
                    'kadai_id': 'KDUP',
                    'nendo': '2023',
                }]
            return []

        mock_kaken_candidates.side_effect = kc_side_effect

        # Call HTTP endpoint
        url = self.project.api_url_for('{}_get_erad_candidates'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)

        assert_equals(res.status_code, http_status.HTTP_200_OK)
        records = res.json['data']['attributes']['records']
        # Expect dedupe to keep the self record (first after sorting)
        assert_equal(len(records), 1)
        assert_equal(records[0]['erad'], self.user.erad)
        assert_equal(records[0]['kadai_id'], 'KDUP')

    @mock.patch('addons.metadata.views.kaken_candidates')
    @mock.patch('addons.metadata.views.erad_candidates')
    def test_contributor_order_preserved(self, mock_erad_candidates, mock_kaken_candidates):
        # creator (self) + two collaborators; expect order: self, collab1, collab2
        self.user.erad = '11111111'
        self.user.save()
        collab1 = factories.AuthUserFactory()
        collab1.erad = '22222222'
        collab1.save()
        self.project.add_contributor(collab1, save=True)
        collab2 = factories.AuthUserFactory()
        collab2.erad = '33333333'
        collab2.save()
        self.project.add_contributor(collab2, save=True)

        mock_erad_candidates.return_value = []

        def kc_side_effect(erad_value, **kwargs):
            return [{
                'erad': erad_value,
                'kadai_id': f'K-{erad_value[-2:]}',
                'nendo': '2020',
            }]

        mock_kaken_candidates.side_effect = kc_side_effect

        url = self.project.api_url_for('{}_get_erad_candidates'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.status_code, http_status.HTTP_200_OK)
        records = res.json['data']['attributes']['records']
        assert_equal([r['erad'] for r in records], [self.user.erad, collab1.erad, collab2.erad])
