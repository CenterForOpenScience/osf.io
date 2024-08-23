# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa
import pytest
import unittest

from django.db import IntegrityError
from osf.models import NodeLog
from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory, OsfStorageFileFactory

from framework.auth import Auth
from ..models import NodeSettings, FileMetadata
from .factories import NodeSettingsFactory


pytestmark = pytest.mark.django_db

class TestNodeSettings(unittest.TestCase):
    _NodeSettingsFactory = NodeSettingsFactory

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.node_settings = self._NodeSettingsFactory(owner=self.node)
        self.node_settings.save()

        self.node_without_metadata = ProjectFactory()
        self.node_with_metadata = ProjectFactory()
        self.node_with_metadata_settings = NodeSettingsFactory(owner=self.node_with_metadata)
        self.node_with_metadata_settings.save()

    def tearDown(self):
        super(TestNodeSettings, self).tearDown()
        self.node.delete()
        self.user.delete()
        self.node_with_metadata.delete()
        self.node_without_metadata.delete()
        self.mock_fetch_metadata_asset_files.stop()

    @mock.patch('website.search.search.update_file_metadata')
    def test_set_invalid_file_metadata(self, mock_update_file_metadata):
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {})
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
            })
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'items': [],
            })
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'folder': True,
                'items': [
                    {}
                ],
            })
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'folder': True,
                'items': [
                    {
                        'active': True,
                    }
                ],
            })
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'folder': True,
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                    }
                ],
            })
        assert_false(mock_update_file_metadata.called)
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'folder': True,
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    }
                ],
            })
        assert_false(mock_update_file_metadata.called)
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
                    }
            ],
        })
        assert_true(mock_update_file_metadata.called)

    def test_set_valid_folder_file_metadata(self):
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
        }, auth=Auth(self.user))
        self.node_settings.save()
        node_id = self.node_settings.owner._id
        metadata = {
            'generated': False,
            'path': 'osfstorage/',
            'folder': True,
            'hash': '1234567890',
            'urlpath': '/{}/files/dir/osfstorage/'.format(node_id),
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
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/'),
            metadata
        )
        assert_equal(self.node_settings.get_file_metadatas(), [metadata])
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_added')

    @mock.patch.object(FileMetadata, 'resolve_urlpath')
    def test_set_valid_file_metadata(self, mock_resolve_urlpath):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.set_file_metadata('osfstorage/', {
            'path': 'osfstorage/',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_settings.save()
        metadatas = self.node_settings.get_file_metadatas()
        metadata = {
            'generated': False,
            'path': 'osfstorage/',
            'folder': False,
            'hash': '1234567890',
            'urlpath': '/testFileGUID/',
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
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/'),
            metadata
        )
        assert_equal(metadatas, [metadata])
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_added')

    @mock.patch.object(FileMetadata, 'resolve_urlpath')
    def test_update_file_metadata(self, mock_resolve_urlpath):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.set_file_metadata('osfstorage/', {
            'path': 'osfstorage/',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_settings.save()
        self.node_settings.set_file_metadata('osfstorage/', {
            'path': 'osfstorage/',
            'folder': False,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': 'yyyy',
                    'data': {
                        'test': True,
                    },
                },
            ],
        }, auth=Auth(self.user))
        self.node_settings.save()
        metadatas = self.node_settings.get_file_metadatas()
        metadata = {
            'generated': False,
            'path': 'osfstorage/',
            'folder': False,
            'hash': '1234567890',
            'urlpath': '/testFileGUID/',
            'items': [
                {
                    'active': True,
                    'schema': 'yyyy',
                    'data': {
                        'test': True,
                    },
                },
            ],
        }
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/'),
            metadata
        )
        assert_equal(metadatas, [metadata])
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_updated')

    @mock.patch('website.search.search.update_file_metadata')
    def test_delete_file_metadata(self, mock_update_file_metadata):
        self.node_settings.set_file_metadata('osfstorage/', {
            'path': 'osfstorage/',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_settings.save()
        self.node_settings.delete_file_metadata(
            'osfstorage/',
            auth=Auth(self.user)
        )
        self.node_settings.save()
        metadatas = self.node_settings.get_file_metadatas()
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/'),
            None
        )
        assert_equal(metadatas, [])
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_deleted')
        assert_true(mock_update_file_metadata.called)

    @mock.patch('website.search.search.update_file_metadata')
    @mock.patch('addons.metadata.models.FileMetadata.resolve_urlpath')
    def test_update_file_metadata_for_renamed(
        self,
        mock_resolve_urlpath,
        mock_update_file_metadata
    ):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.set_file_metadata('osfstorage/testfile', {
            'path': 'osfstorage/testfile',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_settings.save()

        self.node_settings.update_file_metadata_for(
            NodeLog.FILE_RENAMED,
            {
                'source': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
                'destination': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile2',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/testfile'),
            None,
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/testfile2'),
            {
                'generated': False,
                'path': 'osfstorage/testfile2',
                'folder': False,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_deleted')

    @mock.patch('website.search.search.update_file_metadata')
    @mock.patch('addons.metadata.models.FileMetadata.resolve_urlpath')
    def test_update_file_metadata_for_moved_from_node_without_metadata(
        self,
        mock_resolve_urlpath,
        mock_update_file_metadata
    ):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.save()

        self.node_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node_without_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
                'destination': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/testfile'),
            None,
        )
        assert_equal(
            self.node_without_metadata.logs.latest().action,
            'project_created'
        )
        assert_equal(
            self.node.logs.latest().action,
            'project_created'
        )

    @mock.patch('website.search.search.update_file_metadata')
    @mock.patch('addons.metadata.models.FileMetadata.resolve_urlpath')
    def test_update_file_metadata_for_file_moved_from_node_with_metadata(
        self,
        mock_resolve_urlpath,
        mock_update_file_metadata
    ):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_with_metadata_settings.set_file_metadata('osfstorage/testfile', {
            'path': 'osfstorage/testfile',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_with_metadata_settings.save()

        self.node_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
                'destination': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/testfile'),
            None,
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/testfile'),
            {
                'generated': False,
                'path': 'osfstorage/testfile',
                'folder': False,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_added')
        last_log = self.node_with_metadata.logs.latest()
        assert_equal(last_log.action, 'metadata_file_deleted')

        self.node_with_metadata_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'testfile',
                },
                'destination': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/testfile',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/testfile'),
            None,
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/test/testfile'),
            {
                'generated': False,
                'path': 'osfstorage/test/testfile',
                'folder': False,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, 'metadata_file_deleted')
        last_log = self.node_with_metadata.logs.latest()
        assert_equal(last_log.action, 'metadata_file_added')

    @mock.patch('website.search.search.update_file_metadata')
    @mock.patch('addons.metadata.models.FileMetadata.resolve_urlpath')
    def test_update_file_metadata_for_folder_moved_from_node_with_metadata(
        self,
        mock_resolve_urlpath,
        mock_update_file_metadata
    ):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.set_file_metadata('osfstorage/test/testfile', {
            'path': 'osfstorage/test/testfile',
            'folder': False,
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
        }, auth=Auth(self.user))
        self.node_settings.save()

        self.node_with_metadata_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
                'destination': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/test/testfile'),
            None,
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/test/testfile'),
            {
                'generated': False,
                'path': 'osfstorage/test/testfile',
                'folder': False,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        assert_equal(
            self.node_with_metadata.logs.latest().action,
            'metadata_file_added'
        )
        assert_equal(
            self.node.logs.latest().action,
            'metadata_file_deleted'
        )

        self.node_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
                'destination': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'test1/test/',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/test/testfile'),
            None,
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/test1/test/testfile'),
            {
                'generated': False,
                'path': 'osfstorage/test1/test/testfile',
                'folder': False,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        assert_equal(
            self.node_with_metadata.logs.latest().action,
            'metadata_file_deleted'
        )
        assert_equal(
            self.node.logs.latest().action,
            'metadata_file_added'
        )

    @mock.patch('website.search.search.update_file_metadata')
    @mock.patch('addons.metadata.models.FileMetadata.resolve_urlpath')
    def test_update_file_metadata_for_folder_metadata_moved_from_node_with_metadata(
        self,
        mock_resolve_urlpath,
        mock_update_file_metadata
    ):
        mock_resolve_urlpath.return_value = '/testFileGUID/'
        self.node_settings.set_file_metadata('osfstorage/test/', {
            'path': 'osfstorage/test/',
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
        }, auth=Auth(self.user))
        self.node_settings.save()

        self.node_with_metadata_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
                'destination': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/test/'),
            None,
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/test/'),
            {
                'generated': False,
                'path': 'osfstorage/test/',
                'folder': True,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        assert_equal(
            self.node_with_metadata.logs.latest().action,
            'metadata_file_added'
        )
        assert_equal(
            self.node.logs.latest().action,
            'metadata_file_deleted'
        )

        self.node_settings.update_file_metadata_for(
            NodeLog.FILE_MOVED,
            {
                'source': {
                    'nid': self.node_with_metadata._id,
                    'provider': 'osfstorage',
                    'materialized': 'test/',
                },
                'destination': {
                    'nid': self.node._id,
                    'provider': 'osfstorage',
                    'materialized': 'test1/test/',
                },
            },
            auth=Auth(self.user)
        )
        assert_equal(
            self.node_with_metadata_settings.get_file_metadata_for_path('osfstorage/test/'),
            None,
        )
        assert_equal(
            self.node_settings.get_file_metadata_for_path('osfstorage/test1/test/'),
            {
                'generated': False,
                'path': 'osfstorage/test1/test/',
                'folder': True,
                'hash': '1234567890',
                'urlpath': '/testFileGUID/',
                'items': [
                    {
                        'active': True,
                        'schema': 'xxxx',
                        'data': {
                            'test': True,
                        },
                    },
                ],
            },
        )
        assert_equal(
            self.node_with_metadata.logs.latest().action,
            'metadata_file_deleted'
        )
        assert_equal(
            self.node.logs.latest().action,
            'metadata_file_added'
        )

class TestFileMetadata(unittest.TestCase):

    def setUp(self):
        self.mock_fetch_metadata_asset_files = mock.patch('addons.metadata.models.fetch_metadata_asset_files')
        self.mock_fetch_metadata_asset_files.start()
        self.node = ProjectFactory()
        self.node_settings = NodeSettingsFactory(owner=self.node)

    def tearDown(self):
        self.mock_fetch_metadata_asset_files.stop()

    def test_duplicated_file_metadata(self):
        FileMetadata.objects.create(
            path='osfstorage/',
            folder=False,
            project=self.node_settings,
        )
        with assert_raises(IntegrityError):
            # Force to create duplicated metadata
            FileMetadata.objects.create(
                path='osfstorage/',
                folder=False,
                project=self.node_settings,
            )
