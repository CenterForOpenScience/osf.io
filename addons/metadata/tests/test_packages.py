# -*- coding: utf-8 -*-
"""Export and import tests of the metadata addon."""
import io
import json
import logging
import os
import re
import shutil
import tempfile
from zipfile import ZipFile

import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
from tests.base import OsfTestCase

from framework.auth import Auth
from osf.models import Guid
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import ProjectFactory, CommentFactory
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory

from .utils import remove_fields
from ..packages import ROCrateFactory, ROCrateExtractor


logger = logging.getLogger(__name__)


def _find_entity_by_id(json_entities, id):
    for e in json_entities['@graph']:
        if e['@id'] == id:
            return e
    raise ValueError(f'Entity is not found: {id}')

def _create_waterbutler_object(provider, file):
    def _download_to(f):
        f.write(file['content'])

    def _get_files():
        assert file['kind'] == 'folder'
        return [
            _create_waterbutler_object(provider, file)
            for file in file['children']
        ]

    obj = mock.MagicMock()
    obj.attributes = file
    obj.provider = provider
    obj.kind = file['kind']
    obj.name = file['name']
    obj.path = file['path']
    obj.materialized = file['materialized']
    if file['kind'] == 'file':
        obj.contentType = file.get('contentType', None)
        obj.size = len(file['content'])
        obj.modified_utc= None
        obj.created_utc= None

    obj.download_to = mock.MagicMock(side_effect=_download_to)
    obj.get_files = mock.MagicMock(side_effect=_get_files)
    return obj

def _create_waterbutler_node_client(new_node, files):
    def _get_root_files(name):
        logger.info(f'_get_root_files: {name}')
        if name not in files:
            return []
        return [
            _create_waterbutler_object(name, file)
            for file in files[name]
        ]
    mock_upload_file = mock.MagicMock()
    def _get_file_by_materialized_path(path, create=False):
        def _upload_file(data_path, dest_name):
            buf = io.BytesIO()
            with open(data_path, 'rb') as f:
                shutil.copyfileobj(f, buf)
            mock_upload_file(path, dest_name, buf.getvalue())
            r = mock.MagicMock()
            provider = path.split('/')[0]
            root_file = new_node.get_addon(provider).get_root().append_file(dest_name)
            r.provider = provider
            r.path = root_file.path
            return r
        obj = mock.MagicMock()
        obj.upload_file = mock.MagicMock(side_effect=_upload_file)
        return obj
    wb = mock.MagicMock()
    wb.get_root_files = mock.MagicMock(side_effect=_get_root_files)
    wb.get_file_by_materialized_path = mock.MagicMock(side_effect=_get_file_by_materialized_path)
    return wb, mock_upload_file

def _create_waterbutler_client_for_single_node(new_node, files):
    node_wb, node_wb_upload_file = _create_waterbutler_node_client(new_node, files)
    wb = mock.MagicMock()
    wb.get_client_for_node = mock.MagicMock(return_value=node_wb)
    return wb, node_wb, node_wb_upload_file

def _get_ro_crate_from(zip_path):
    with ZipFile(zip_path, 'r') as zf:
        return json.load(zf.open('ro-crate-metadata.json'))

def _assert_dict_matches(value, expected_with_patterns):
    for k, v in expected_with_patterns.items():
        assert_true(k in value, f'Key not found: {k} in {value}')
        if isinstance(v, dict):
            _assert_dict_matches(value[k], v)
        elif isinstance(v, list):
            assert_equals(len(value[k]), len(v), f'Length mismatch: {len(value[k])} != {len(v)} (expected {v})')
            for i, e in enumerate(v):
                _assert_dict_matches(value[k][i], e)
        elif hasattr(v, 'match'):
            # v is a regular expression
            assert_true(v.match(value[k]), f'Unexpected value: {value[k]} (expected {v})')
        else:
            assert_equals(value[k], v, f'Unexpected value: {value[k]} (expected {v})')

class TestExportAndImport(OsfTestCase):

    def setUp(self):
        super(TestExportAndImport, self).setUp()
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        self.work_dir = tempfile.mkdtemp()
        self.node = ProjectFactory()
        self.node.add_addon('metadata', auth=Auth(self.node.creator))
        self.node.description = 'TEST_DESCRIPTION'
        self.node.add_tags(['Test Node'], auth=Auth(user=self.node.creator), log=False)
        self.node.save()
        self.node_comment_1 = CommentFactory(node=self.node, user=self.node.creator)
        self.node_comment_1.content = 'Comment for the node'
        self.node_comment_1.save()
        self.node_comment_2 = CommentFactory(
            node=self.node,
            user=self.node.creator,
            target=Guid.load(self.node_comment_1._id),
        )
        self.node_comment_2.content = 'Reply comment'
        self.node_comment_2.save()
        root_file = self.node.get_addon('osfstorage').get_root().append_file('file_in_root')
        root_file_comment = CommentFactory(
            node=self.node,
            user=self.node.creator,
            target=root_file.get_guid(create=True),
        )
        root_file_comment.content = 'Comment for the file file_in_root'
        root_file_comment.save()
        file = self.node.get_addon('osfstorage').get_root().append_file('file_in_folder')
        file.add_tags(['Test File'], auth=Auth(user=self.node.creator), log=False)
        file.save()
        sub_file = self.node.get_addon('osfstorage').get_root().append_file('file_in_sub_folder')

        _, node_wb, _ = _create_waterbutler_client_for_single_node(self.node, {
            'osfstorage': [
                {
                    'provider': 'osfstorage',
                    'kind': 'folder',
                    'name': 'sample',
                    'path': '/SAMPLE/',
                    'materialized': '/sample/',
                    'children': [
                        {
                            'provider': 'osfstorage',
                            'kind': 'file',
                            'name': 'file_in_folder',
                            'path': file.path,
                            'materialized': '/sample/file_in_folder',
                            'content': b'FOLDER_DATA',
                        },
                        {
                            'provider': 'osfstorage',
                            'kind': 'folder',
                            'name': 'sub_folder',
                            'path': '/SUB_FOLDER/',
                            'materialized': '/sample/sub_folder/',
                            'children': [
                                {
                                    'provider': 'osfstorage',
                                    'kind': 'file',
                                    'name': 'file_in_sub_folder',
                                    'path': sub_file.path,
                                    'materialized': '/sample/sub_folder/file_in_sub_folder',
                                    'content': b'SUB_FOLDER_DATA',
                                }
                            ],
                        },
                        {
                            'provider': 'osfstorage',
                            'kind': 'folder',
                            'name': 'empty',
                            'path': '/EMPTY/',
                            'materialized': '/sample/empty/',
                            'children': [],
                        }
                    ],
                },
                {
                    'provider': 'osfstorage',
                    'kind': 'file',
                    'name': 'file_in_root',
                    'path': root_file.path,
                    'materialized': '/file_in_root',
                    'content': b'ROOT_DATA',
                },
            ]
        })
        schema = RegistrationSchema.objects \
            .filter(name='公的資金による研究データのメタデータ登録') \
            .order_by('-schema_version') \
            .first()
        self.node.get_addon('metadata').set_file_metadata('osfstorage/file_in_root', {
            'path': 'osfstorage/file_in_root',
            'folder': False,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': schema._id,
                    'data': {
                        'test': True,
                    },
                },
            ],
        }, auth=Auth(self.node.creator))
        self.node.get_addon('metadata').set_file_metadata('osfstorage/sample/sub_folder/', {
            'path': 'osfstorage/sample/sub_folder/',
            'folder': True,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': schema._id,
                    'data': {
                        'test': True,
                        'this_is_folder': True,
                    },
                },
            ],
        }, auth=Auth(self.node.creator))
        wiki_page = WikiFactory(node=self.node, page_name='test')
        wiki = WikiVersionFactory(wiki_page=wiki_page)
        wiki.content = 'Test Wiki Page'
        wiki.save()

        self.composite_node = ProjectFactory()
        self.composite_node.add_addon('metadata', auth=Auth(self.node.creator))
        self.composite_node.description = 'TEST_COMPOSITE_DESCRIPTION'
        self.composite_node.add_tags(['Composite Node'], auth=Auth(user=self.node.creator), log=False)
        self.composite_node.save()
        root_file = self.composite_node.get_addon('osfstorage').get_root().append_file('file_in_composite_root')
        root_file_comment = CommentFactory(
            node=self.composite_node,
            user=self.composite_node.creator,
            target=root_file.get_guid(create=True),
        )
        root_file_comment.content = 'Comment for the file file_in_composite_root'
        root_file_comment.save()

        self.composite_node.get_addon('metadata').set_file_metadata('osfstorage/file_in_composite_root', {
            'path': 'osfstorage/file_in_composite_root',
            'folder': False,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': schema._id,
                    'data': {
                        'test': True,
                    },
                },
            ],
        }, auth=Auth(self.node.creator))
        _, composite_node_wb, _ = _create_waterbutler_client_for_single_node(self.composite_node, {
            'osfstorage': [
                {
                    'provider': 'osfstorage',
                    'kind': 'file',
                    'name': 'file_in_composite_root',
                    'path': root_file.path,
                    'materialized': '/file_in_composite_root',
                    'content': b'COMPOSITE_DATA',
                },
            ]
        })

        self.sub_node = ProjectFactory(parent=self.composite_node, creator=self.composite_node.creator)
        self.sub_node.description = 'TEST_SUB_DESCRIPTION'
        self.sub_node.add_tags(['Sub Node'], auth=Auth(user=self.node.creator), log=False)
        self.sub_node.save()
        root_file = self.sub_node.get_addon('osfstorage').get_root().append_file('file_in_sub_root')
        root_file_comment = CommentFactory(
            node=self.sub_node,
            user=self.sub_node.creator,
            target=root_file.get_guid(create=True),
        )
        root_file_comment.content = 'Comment for the file file_in_sub_root'
        root_file_comment.save()
        _, sub_node_wb, _ = _create_waterbutler_client_for_single_node(self.sub_node, {
            'osfstorage': [
                {
                    'provider': 'osfstorage',
                    'kind': 'file',
                    'name': 'file_in_sub_root',
                    'path': root_file.path,
                    'materialized': '/file_in_sub_root',
                    'content': b'SUB_DATA',
                },
            ]
        })
        self.wb = mock.MagicMock()
        def get_wb_client_for_node(node):
            if node == self.node:
                return node_wb
            if node == self.composite_node:
                return composite_node_wb
            if node == self.sub_node:
                return sub_node_wb
            raise ValueError(f'Unexpected node: {node}')
        self.node_wb = node_wb
        self.composite_node_wb = composite_node_wb
        self.sub_node_wb = sub_node_wb

        self.wb.get_client_for_node = mock.MagicMock(side_effect=get_wb_client_for_node)

        wiki_page = WikiFactory(node=self.sub_node, page_name='test')
        wiki = WikiVersionFactory(wiki_page=wiki_page)
        wiki.content = 'Sub Wiki Page'
        wiki.save()

    def tearDown(self):
        shutil.rmtree(self.work_dir)
        self.mock_fetch_metadata_asset_files.stop()
        super(TestExportAndImport, self).tearDown()

    # TC-A-2023-7-001
    def test_files_only(self):
        config = {
            'comment': {
                'enable': False,
            },
            'log': {
                'enable': False,
            },
            'wiki': {
                'enable': False,
            },
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(json_entities['@context'], [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ])
        assert_equals(
            [e['@id'] for e in json_entities['@graph']],
            [
                './',
                'ro-crate-metadata.json',
                'root/osfstorage/sample/file_in_folder',
                'root/osfstorage/sample/sub_folder/file_in_sub_folder',
                './root/osfstorage/sample/sub_folder/',
                '#./root/osfstorage/sample/sub_folder/#0',
                '#metadata-schema-公的資金による研究データのメタデータ登録-2',
                './root/osfstorage/sample/empty/',
                './root/osfstorage/sample/',
                'root/osfstorage/file_in_root',
                '#root/osfstorage/file_in_root#0',
                '#root-osfstorage',
                '#root-metadata',
                '#root',
                '#creator0'
            ],
        )
        assert_equals(remove_fields(_find_entity_by_id(json_entities, './'), fields=['datePublished']), {
            '@id': './',
            '@type': 'Dataset',
            'hasPart': [
                {'@id': 'root/osfstorage/sample/file_in_folder'},
                {'@id': 'root/osfstorage/sample/sub_folder/file_in_sub_folder'},
                {'@id': './root/osfstorage/sample/sub_folder/'},
                {'@id': './root/osfstorage/sample/empty/'},
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ]
        })
        assert_true('datePublished' in _find_entity_by_id(json_entities, './'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'),
            fields=['rdmURL'],
        ), {
            '@id': 'root/osfstorage/file_in_root',
            '@type': 'File',
            'contentSize': '9',
            'dateCreated': None,
            'dateModified': None,
            'encodingFormat': None,
            'keywords': [],
            'name': 'file_in_root'
        })
        assert_true('rdmURL' in _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root/osfstorage/file_in_root#0'),
            fields=['dateCreated', 'dateModified'],
        ), {
            '@id': '#root/osfstorage/file_in_root#0',
            '@type': 'RDMFileMetadata',
            'about': {
                '@id': 'root/osfstorage/file_in_root'
            },
            'encodingFormat': 'application/json',
            'rdmSchema': {
                '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'
            },
            'text': "{\"test\": true}",
            'version': 'active'
        })
        assert_equals(_find_entity_by_id(json_entities, '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'), {
            '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2',
            '@type': 'RDMMetadataSchema',
            'name': '\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332',
            'version': 2
        })
        assert_equals(_find_entity_by_id(json_entities, 'ro-crate-metadata.json'), {
            '@id': 'ro-crate-metadata.json',
            '@type': 'CreativeWork',
            'about': {
                '@id': './'
            },
            'conformsTo': {
                '@id': 'https://w3id.org/ro/crate/1.1'
            }
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-osfstorage'), {
            '@id': '#root-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'NII Storage',
            'hasPart': [
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ],
            'name': 'osfstorage'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-metadata'), {
            '@id': '#root-metadata',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Metadata',
            'name': 'metadata'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#root',
            '@type': 'RDMProject',
            'about': {
                '@id': './'
            },
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_DESCRIPTION',
            'hasPart': [],
            'keywords': [
                'Test Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root'))
        assert_true('name' in _find_entity_by_id(json_entities, '#root'))
        creator = self.node.creator
        assert_equals(_find_entity_by_id(json_entities, '#creator0'), {
            '@id': '#creator0',
            '@type': 'Person',
            'familyName': [
                {
                    '@language': 'en',
                    '@value': creator.family_name
                }
            ],
            'givenName': [
                {
                    '@language': 'en',
                    '@value': creator.given_name
                }
            ],
            'identifier': [],
            'name': creator.given_name + ' ' + creator.family_name
        })

    # TC-A-2023-7-002
    def test_comments_and_files_only(self):
        config = {
            'comment': {
                'enable': True,
            },
            'log': {
                'enable': False,
            },
            'wiki': {
                'enable': False,
            },
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(json_entities['@context'], [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ])
        assert_equals(
            [e['@id'] for e in json_entities['@graph']],
            [
                './',
                'ro-crate-metadata.json',
                'root/osfstorage/sample/file_in_folder',
                'root/osfstorage/sample/sub_folder/file_in_sub_folder',
                './root/osfstorage/sample/sub_folder/',
                '#./root/osfstorage/sample/sub_folder/#0',
                '#metadata-schema-公的資金による研究データのメタデータ登録-2',
                './root/osfstorage/sample/empty/',
                './root/osfstorage/sample/',
                'root/osfstorage/file_in_root',
                '#root/osfstorage/file_in_root#0',
                '#root-osfstorage',
                '#root-metadata',
                '#root',
                '#comment#0',
                '#comment#1',
                '#comment#2',
                '#creator0'
            ],
        )
        assert_equals(remove_fields(_find_entity_by_id(json_entities, './'), fields=['datePublished']), {
            '@id': './',
            '@type': 'Dataset',
            'hasPart': [
                {'@id': 'root/osfstorage/sample/file_in_folder'},
                {'@id': 'root/osfstorage/sample/sub_folder/file_in_sub_folder'},
                {'@id': './root/osfstorage/sample/sub_folder/'},
                {'@id': './root/osfstorage/sample/empty/'},
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ]
        })
        assert_true('datePublished' in _find_entity_by_id(json_entities, './'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'),
            fields=['rdmURL'],
        ), {
            '@id': 'root/osfstorage/file_in_root',
            '@type': 'File',
            'contentSize': '9',
            'dateCreated': None,
            'dateModified': None,
            'encodingFormat': None,
            'keywords': [],
            'name': 'file_in_root'
        })
        assert_true('rdmURL' in _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root/osfstorage/file_in_root#0'),
            fields=['dateCreated', 'dateModified'],
         ), {
            '@id': '#root/osfstorage/file_in_root#0',
            '@type': 'RDMFileMetadata',
            'about': {
                '@id': 'root/osfstorage/file_in_root'
            },
            'encodingFormat': 'application/json',
            'rdmSchema': {
                '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'
            },
            'text': "{\"test\": true}",
            'version': 'active'
        })
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root/osfstorage/file_in_root#0'))
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root/osfstorage/file_in_root#0'))
        assert_equals(_find_entity_by_id(json_entities, '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'), {
            '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2',
            '@type': 'RDMMetadataSchema',
            'name': '\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332',
            'version': 2
        })
        assert_equals(_find_entity_by_id(json_entities, 'ro-crate-metadata.json'), {
            '@id': 'ro-crate-metadata.json',
            '@type': 'CreativeWork',
            'about': {
                '@id': './'
            },
            'conformsTo': {
                '@id': 'https://w3id.org/ro/crate/1.1'
            }
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-osfstorage'), {
            '@id': '#root-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'NII Storage',
            'hasPart': [
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ],
            'name': 'osfstorage'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-metadata'), {
            '@id': '#root-metadata',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Metadata',
            'name': 'metadata'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#root',
            '@type': 'RDMProject',
            'about': {
                '@id': './'
            },
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_DESCRIPTION',
            'hasPart': [],
            'keywords': [
                'Test Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root'))
        assert_true('name' in _find_entity_by_id(json_entities, '#root'))
        _assert_dict_matches(_find_entity_by_id(json_entities, '#creator0'), {
            '@id': '#creator0',
            '@type': 'Person',
            'familyName': [
                {
                    '@language': 'en',
                    '@value': re.compile(r'Mercury[0-9]+')
                }
            ],
            'givenName': [
                {
                    '@language': 'en',
                    '@value': 'Freddie'
                }
            ],
            'identifier': [],
            'name': re.compile(r'Freddie Mercury[0-9]+')
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#comment#0'),
            fields=['dateCreated', 'dateModified'],
        ), {
            '@id': '#comment#0',
            '@type': 'Comment',
            'about': {
                '@id': '#root'
            },
            'author': {
                '@id': '#creator0'
            },
            'text': 'Reply comment'
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#comment#0'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#comment#0'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#comment#1'),
            fields=['dateCreated', 'dateModified'],
        ), {
            '@id': '#comment#1',
            '@type': 'Comment',
            'about': {
                '@id': '#root'
            },
            'author': {
                '@id': '#creator0'
            },
            'text': 'Comment for the node'
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#comment#1'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#comment#1'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#comment#2'),
            fields=['dateCreated', 'dateModified'],
        ), {
            '@id': '#comment#2',
            '@type': 'Comment',
            'about': {
                '@id': './root/osfstorage/file_in_root'
            },
            'author': {
                '@id': '#creator0'
            },
            'text': 'Comment for the file file_in_root'
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#comment#2'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#comment#2'))

    # TC-A-2023-7-003
    def test_logs_and_files_only(self):
        config = {
            'comment': {
                'enable': False,
            },
            'log': {
                'enable': True,
            },
            'wiki': {
                'enable': False,
            },
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(json_entities['@context'], [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ])
        assert_equals(
            [e['@id'] for e in json_entities['@graph']],
            [
                './',
                'ro-crate-metadata.json',
                'root/osfstorage/sample/file_in_folder',
                'root/osfstorage/sample/sub_folder/file_in_sub_folder',
                './root/osfstorage/sample/sub_folder/',
                '#./root/osfstorage/sample/sub_folder/#0',
                '#metadata-schema-公的資金による研究データのメタデータ登録-2',
                './root/osfstorage/sample/empty/',
                './root/osfstorage/sample/',
                'root/osfstorage/file_in_root',
                '#root/osfstorage/file_in_root#0',
                '#root-osfstorage',
                '#root-metadata',
                '#root',
                '#action#0',
                '#action#1',
                '#action#2',
                '#action#3',
                '#creator0'
            ],
        )
        assert_equals(remove_fields(_find_entity_by_id(json_entities, './'), fields=['datePublished']), {
            '@id': './',
            '@type': 'Dataset',
            'hasPart': [
                {'@id': 'root/osfstorage/sample/file_in_folder'},
                {'@id': 'root/osfstorage/sample/sub_folder/file_in_sub_folder'},
                {'@id': './root/osfstorage/sample/sub_folder/'},
                {'@id': './root/osfstorage/sample/empty/'},
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ]
        })
        assert_true('datePublished' in _find_entity_by_id(json_entities, './'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'),
            fields=['rdmURL'],
        ), {
            '@id': 'root/osfstorage/file_in_root',
            '@type': 'File',
            'contentSize': '9',
            'dateCreated': None,
            'dateModified': None,
            'encodingFormat': None,
            'keywords': [],
            'name': 'file_in_root'
        })
        assert_true('rdmURL' in _find_entity_by_id(json_entities, 'root/osfstorage/file_in_root'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root/osfstorage/file_in_root#0'),
            fields=['dateCreated', 'dateModified'],
         ), {
            '@id': '#root/osfstorage/file_in_root#0',
            '@type': 'RDMFileMetadata',
            'about': {
                '@id': 'root/osfstorage/file_in_root'
            },
            'encodingFormat': 'application/json',
            'rdmSchema': {
                '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'
            },
            'text': "{\"test\": true}",
            'version': 'active'
        })
        assert_equals(_find_entity_by_id(json_entities, '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2'), {
            '@id': '#metadata-schema-\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332-2',
            '@type': 'RDMMetadataSchema',
            'name': '\u516c\u7684\u8cc7\u91d1\u306b\u3088\u308b\u7814\u7a76\u30c7\u30fc\u30bf\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u767b\u9332',
            'version': 2
        })
        assert_equals(_find_entity_by_id(json_entities, 'ro-crate-metadata.json'), {
            '@id': 'ro-crate-metadata.json',
            '@type': 'CreativeWork',
            'about': {
                '@id': './'
            },
            'conformsTo': {
                '@id': 'https://w3id.org/ro/crate/1.1'
            }
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-osfstorage'), {
            '@id': '#root-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'NII Storage',
            'hasPart': [
                {'@id': './root/osfstorage/sample/'},
                {'@id': 'root/osfstorage/file_in_root'},
            ],
            'name': 'osfstorage'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-metadata'), {
            '@id': '#root-metadata',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Metadata',
            'name': 'metadata'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#root',
            '@type': 'RDMProject',
            'about': {
                '@id': './'
            },
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_DESCRIPTION',
            'hasPart': [],
            'keywords': [
                'Test Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root'))
        assert_true('name' in _find_entity_by_id(json_entities, '#root'))
        _assert_dict_matches(_find_entity_by_id(json_entities, '#creator0'), {
            '@id': '#creator0',
            '@type': 'Person',
            'familyName': [
                {
                    '@language': 'en',
                    '@value': re.compile(r'Mercury[0-9]+')
                }
            ],
            'givenName': [
                {
                    '@language': 'en',
                    '@value': 'Freddie'
                }
            ],
            'identifier': [],
            'name': re.compile(r'Freddie Mercury[0-9]+')
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#action#0'),
            fields=['startTime'],
        ), {
            '@id': '#action#0',
            '@type': 'Action',
            'agent': {
                '@id': '#creator0'
            },
            'name': 'metadata_file_added',
        })
        assert_true('startTime' in _find_entity_by_id(json_entities, '#action#0'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#action#1'),
            fields=['startTime'],
        ), {
            '@id': '#action#1',
            '@type': 'Action',
            'agent': {
                '@id': '#creator0'
            },
            'name': 'metadata_file_added',
        })
        assert_true('startTime' in _find_entity_by_id(json_entities, '#action#1'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#action#2'),
            fields=['startTime'],
        ), {
            '@id': '#action#2',
            '@type': 'Action',
            'agent': {
                '@id': '#creator0'
            },
            'name': 'addon_added',
        })
        assert_true('startTime' in _find_entity_by_id(json_entities, '#action#2'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#action#3'),
            fields=['startTime'],
        ), {
            '@id': '#action#3',
            '@type': 'Action',
            'agent': {
                '@id': '#creator0'
            },
            'name': 'project_created',
        })
        assert_true('startTime' in _find_entity_by_id(json_entities, '#action#3'))

    # TC-A-2023-7-004
    def test_wiki_only(self):
        config = {
            'comment': {
                'enable': False,
            },
            'log': {
                'enable': False,
            },
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(json_entities['@context'], [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ])
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 0)
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Action']), 0)
        assert_equals(
            [e['@id'] for e in json_entities['@graph']],
            ['./', 'ro-crate-metadata.json', '#root-osfstorage', '#root-metadata', 'root/wiki/test', '#root-wiki', '#root', '#creator0'],
        )
        assert_equals(remove_fields(_find_entity_by_id(json_entities, './'), fields=['datePublished']), {
            '@id': './',
            '@type': 'Dataset',
            'hasPart': [
                {
                '@id': 'root/wiki/test'
                }
            ]
        })
        assert_true('datePublished' in _find_entity_by_id(json_entities, './'))
        assert_equals(_find_entity_by_id(json_entities, 'ro-crate-metadata.json'), {
            '@id': 'ro-crate-metadata.json',
            '@type': 'CreativeWork',
            'about': {
                '@id': './'
            },
            'conformsTo': {
                '@id': 'https://w3id.org/ro/crate/1.1'
            }
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-osfstorage'), {
            '@id': '#root-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'NII Storage',
            'hasPart': [],
            'name': 'osfstorage'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-metadata'), {
            '@id': '#root-metadata',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Metadata',
            'name': 'metadata'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, 'root/wiki/test'),
            fields=['dateCreated', 'dateModified'],
        ), {
            '@id': 'root/wiki/test',
            '@type': 'File',
            'contentSize': '14',
            'encodingFormat': 'text/markdown',
            'name': 'test',
            'version': 1
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, 'root/wiki/test'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, 'root/wiki/test'))
        assert_equals(_find_entity_by_id(json_entities, '#root-wiki'), {
            '@id': '#root-wiki',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Wiki',
            'hasPart': [
                {
                '@id': 'root/wiki/test'
                }
            ],
            'name': 'wiki'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#root',
            '@type': 'RDMProject',
            'about': {
                '@id': './'
            },
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_DESCRIPTION',
            'hasPart': [],
            'keywords': [
                'Test Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root'))
        assert_true('name' in _find_entity_by_id(json_entities, '#root'))
        creator = self.node.creator
        assert_equals(_find_entity_by_id(json_entities, '#creator0'), {
            '@id': '#creator0',
            '@type': 'Person',
            'familyName': [
                {
                    '@language': 'en',
                    '@value': creator.family_name
                }
            ],
            'givenName': [
                {
                    '@language': 'en',
                    '@value': creator.given_name
                }
            ],
            'identifier': [],
            'name': creator.given_name + ' ' + creator.family_name
        })

    # TC-A-2023-7-005
    def test_child_nodes(self):
        config = {
            'comment': {
                'enable': False,
            },
            'log': {
                'enable': False,
            },
        }
        rocrate = ROCrateFactory(self.composite_node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(json_entities['@context'], [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ])
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 0)
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Action']), 0)
        assert_equals(
            [e['@id'] for e in json_entities['@graph']],
            [
                './', 'ro-crate-metadata.json',
                '#node1-osfstorage', 'node1/wiki/test', '#node1-wiki',
                '#root-osfstorage', '#root-metadata', '#root-wiki', '#root',
                '#node1', '#creator0',
            ],
        )
        assert_equals(remove_fields(_find_entity_by_id(json_entities, './'), fields=['datePublished']), {
            '@id': './',
            '@type': 'Dataset',
            'hasPart': [{'@id': 'node1/wiki/test'}],
        })
        assert_true('datePublished' in _find_entity_by_id(json_entities, './'))
        assert_equals(_find_entity_by_id(json_entities, 'ro-crate-metadata.json'), {
            '@id': 'ro-crate-metadata.json',
            '@type': 'CreativeWork',
            'about': {
                '@id': './'
            },
            'conformsTo': {
                '@id': 'https://w3id.org/ro/crate/1.1'
            }
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-osfstorage'), {
            '@id': '#root-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'NII Storage',
            'hasPart': [],
            'name': 'osfstorage'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-metadata'), {
            '@id': '#root-metadata',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Metadata',
            'name': 'metadata'
        })
        assert_equals(_find_entity_by_id(json_entities, '#root-wiki'), {
            '@id': '#root-wiki',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#root'
            },
            'description': 'Wiki',
            'hasPart': [],
            'name': 'wiki'
        })
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#root'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#root',
            '@type': 'RDMProject',
            'about': {
                '@id': './'
            },
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_COMPOSITE_DESCRIPTION',
            'hasPart': [{
                '@id': '#node1',
            }],
            'keywords': [
                'Composite Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#root'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#root'))
        assert_true('name' in _find_entity_by_id(json_entities, '#root'))
        assert_equals(remove_fields(
            _find_entity_by_id(json_entities, '#node1'),
            fields=['dateCreated', 'dateModified', 'name'],
        ), {
            '@id': '#node1',
            '@type': 'RDMProject',
            'category': 'project',
            'contributor': [
                {
                    '@id': '#creator0'
                }
            ],
            'creator': {
                '@id': '#creator0'
            },
            'description': 'TEST_SUB_DESCRIPTION',
            'hasPart': [],
            'keywords': [
                'Sub Node'
            ],
        })
        assert_true('dateCreated' in _find_entity_by_id(json_entities, '#node1'))
        assert_true('dateModified' in _find_entity_by_id(json_entities, '#node1'))
        assert_true('name' in _find_entity_by_id(json_entities, '#node1'))
        assert_equals(_find_entity_by_id(json_entities, '#node1-osfstorage'), {
            '@id': '#node1-osfstorage',
            '@type': 'RDMAddon',
            'about': {
                '@id': '#node1'
            },
            'description': 'NII Storage',
            'hasPart': [],
            'name': 'osfstorage'
        })
        _assert_dict_matches(_find_entity_by_id(json_entities, '#creator0'), {
            '@id': '#creator0',
            '@type': 'Person',
            'familyName': [
                {
                    '@language': 'en',
                    '@value': re.compile(r'Mercury[0-9]+')
                }
            ],
            'givenName': [
                {
                    '@language': 'en',
                    '@value': 'Freddie'
                }
            ],
            'identifier': [],
            'name': re.compile(r'Freddie Mercury[0-9]+')
        })

    # TC-A-2023-7-006
    def test_simple_extraction(self):
        config = {
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        logger.info(f'ro-crate: {json.dumps(json_entities, indent=2)}')
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 3)
        assert_equals(
            [e['name'] for e in json_entities['@graph'] if e['@type'] == 'Action'],
            ['metadata_file_added', 'metadata_file_added', 'addon_added', 'project_created'],
        )

        zip_buf = io.BytesIO()
        with open(zip_path, 'rb') as f:
            shutil.copyfileobj(f, zip_buf)

        with mock.patch.object(ROCrateExtractor, '_download') as mock_request:
            def to_file(f):
                zip_buf.seek(0)
                shutil.copyfileobj(zip_buf, f)
            mock_request.side_effect = to_file

            new_node = ProjectFactory()
            new_node.add_addon('metadata', auth=Auth(user=new_node.creator))
            extractor = ROCrateExtractor(
                new_node.creator,
                'http://test.rdm.nii.ac.jp/test-data.zip',
                self.work_dir,
            )
            new_wb, new_node_wb, new_wb_upload_file = _create_waterbutler_client_for_single_node(new_node, {})
            extractor.ensure_node(new_node)
            extractor.ensure_folders(new_wb)
            for file_extractor in extractor.file_extractors:
                file_extractor.extract(new_wb)

            assert_equals(new_node.description, 'TEST_DESCRIPTION')
            assert_equals([t.name for t in new_node.tags.all()], ['Test Node'])

            assert_equals(
                [
                    t.name
                    for t in new_node.get_addon('osfstorage').get_root().find_child_by_name('file_in_folder').tags.all()
                ],
                ['Test File'],
            )
            schema = RegistrationSchema.objects \
                .filter(name='公的資金による研究データのメタデータ登録') \
                .order_by('-schema_version') \
                .first()
            assert_equals(
                new_node.get_addon('metadata').get_file_metadata_for_path('osfstorage/file_in_root')['items'],
                [
                    {
                        'active': True,
                        'schema': schema._id,
                        'data': {
                            'test': True,
                        },
                    },
                ],
            )
            assert_equals(
                new_node.get_addon('metadata').get_file_metadata_for_path('osfstorage/sample/sub_folder/')['items'],
                [
                    {
                        'active': True,
                        'schema': schema._id,
                        'data': {
                            'test': True,
                            'this_is_folder': True,
                        },
                    },
                ],
            )
            new_node_wb.assert_has_calls([
                mock.call.get_file_by_materialized_path('osfstorage/sample/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/sub_folder/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/empty/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/'),
                mock.call.get_file_by_materialized_path('osfstorage/sample/sub_folder/'),
                mock.call.get_file_by_materialized_path('osfstorage/'),
            ])
            new_wb_upload_file.assert_has_calls([
                mock.call('osfstorage/sample/', 'file_in_folder', b'FOLDER_DATA'),
                mock.call('osfstorage/sample/sub_folder/', 'file_in_sub_folder', b'SUB_FOLDER_DATA'),
                mock.call('osfstorage/', 'file_in_root', b'ROOT_DATA'),
            ])
            assert_equals(
                new_node.wikis.get(page_name='test').get_version().content,
                'Test Wiki Page',
            )

    # TC-A-2023-7-007
    def test_composite_extraction(self):
        config = {
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.composite_node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        logger.info(f'ro-crate: {json.dumps(json_entities, indent=2)}')
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 1)
        assert_equals(
            [e['name'] for e in json_entities['@graph'] if e['@type'] == 'Action'],
            ['metadata_file_added', 'addon_added', 'project_created', 'project_created'],
        )
        assert_equals(
            sorted([e['description'] for e in json_entities['@graph'] if e['@type'] == 'RDMProject']),
            ['TEST_COMPOSITE_DESCRIPTION', 'TEST_SUB_DESCRIPTION'],
        )

        zip_buf = io.BytesIO()
        with open(zip_path, 'rb') as f:
            shutil.copyfileobj(f, zip_buf)

        with mock.patch.object(ROCrateExtractor, '_download') as mock_request:
            def to_file(f):
                zip_buf.seek(0)
                shutil.copyfileobj(zip_buf, f)
            mock_request.side_effect = to_file

            new_node = ProjectFactory()
            new_node.add_addon('metadata', auth=Auth(user=new_node.creator))
            extractor = ROCrateExtractor(
                new_node.creator,
                'http://test.rdm.nii.ac.jp/test-data.zip',
                self.work_dir,
            )
            extractor.ensure_node(new_node)
            children = list(new_node.nodes)
            assert_equals(len(children), 1)
            new_child = children[0]
            _, new_node_wb, new_wb_upload_file = _create_waterbutler_client_for_single_node(new_node, {})
            _, new_child_node_wb, new_child_wb_upload_file = _create_waterbutler_client_for_single_node(new_child, {})
            new_wb = mock.MagicMock()
            new_wb.get_client_for_node = mock.MagicMock(side_effect=lambda n: new_node_wb if n == new_node else new_child_node_wb)
            extractor.ensure_folders(new_wb)
            for file_extractor in extractor.file_extractors:
                file_extractor.extract(new_wb)

            assert_equals(new_node.description, 'TEST_COMPOSITE_DESCRIPTION')
            assert_equals(new_child.description, 'TEST_SUB_DESCRIPTION')
            assert_equals([t.name for t in new_node.tags.all()], ['Composite Node'])
            assert_equals([t.name for t in new_child.tags.all()], ['Sub Node'])

            schema = RegistrationSchema.objects \
                .filter(name='公的資金による研究データのメタデータ登録') \
                .order_by('-schema_version') \
                .first()
            assert_equals(
                new_node.get_addon('metadata').get_file_metadata_for_path('osfstorage/file_in_composite_root')['items'],
                [
                    {
                        'active': True,
                        'schema': schema._id,
                        'data': {
                            'test': True,
                        },
                    },
                ],
            )
            new_wb_upload_file.assert_has_calls([
                mock.call('osfstorage/', 'file_in_composite_root', b'COMPOSITE_DATA'),
            ])
            new_child_wb_upload_file.assert_has_calls([
                mock.call('osfstorage/', 'file_in_sub_root', b'SUB_DATA'),
            ])
            assert_equals(
                new_child.wikis.get(page_name='test').get_version().content,
                'Sub Wiki Page',
            )

    # TC-A-2023-7-008
    def test_simple_export_on_error(self):
        config = {
            'addons': {
                'osfstorage': {},
            }
        }

        old_side_effect = self.node_wb.get_root_files.side_effect
        try:
            self.node_wb.get_root_files.side_effect = Exception('test')
            rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
            zip_path = os.path.join(self.work_dir, 'package.zip')
            with assert_raises(Exception):
                rocrate.download_to(zip_path)
        finally:
            self.node_wb.get_root_files.side_effect = old_side_effect

    # TC-A-2023-7-009
    def test_simple_extraction_on_error(self):
        config = {
            'addons': {
                'osfstorage': {},
            }
        }

        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        logger.info(f'ro-crate: {json.dumps(json_entities, indent=2)}')
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 3)
        assert_equals(
            [e['name'] for e in json_entities['@graph'] if e['@type'] == 'Action'],
            ['metadata_file_added', 'metadata_file_added', 'addon_added', 'project_created'],
        )

        zip_buf = io.BytesIO()
        with open(zip_path, 'rb') as f:
            shutil.copyfileobj(f, zip_buf)

        with mock.patch.object(ROCrateExtractor, '_download') as mock_request:
            mock_request.side_effect = Exception('test')

            new_node = ProjectFactory()
            new_node.add_addon('metadata', auth=Auth(user=new_node.creator))
            extractor = ROCrateExtractor(
                new_node.creator,
                'http://test.rdm.nii.ac.jp/test-data.zip',
                self.work_dir,
            )
            new_wb, new_node_wb, new_wb_upload_file = _create_waterbutler_client_for_single_node(new_node, {})
            with assert_raises(Exception):
                extractor.ensure_node(new_node)
