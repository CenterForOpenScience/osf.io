# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory

from framework.auth import Auth
from ..models import NodeSettings, FileMetadata
from .factories import NodeSettingsFactory


pytestmark = pytest.mark.django_db

class TestNodeSettings(unittest.TestCase):
    _NodeSettingsFactory = NodeSettingsFactory

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.node_settings = self._NodeSettingsFactory(owner=self.node)
        self.node_settings.save()

    def tearDown(self):
        super(TestNodeSettings, self).tearDown()
        self.node.delete()
        self.user.delete()

    def test_set_invalid_file_metadata(self):
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {})
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
            })
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'items': [],
            })
        with pytest.raises(ValueError):
            self.node_settings.set_file_metadata('osfstorage/', {
                'path': 'osfstorage/',
                'folder': True,
                'items': [
                    {}
                ],
            })
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

    @mock.patch.object(FileMetadata, 'resolve_urlpath')
    def test_delete_file_metadata(self, mock_resolve_urlpath):
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
