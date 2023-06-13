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


class TestViews(BaseAddonTestCase, OsfTestCase):

    def test_no_file_metadata(self):
        url = self.project.api_url_for('{}_get_project'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json, {
            'data': {
                'attributes': {
                    'editable': True,
                    'files': [],
                },
                'id': self.node_settings.owner._id,
                'type': 'metadata-node-project',
            },
        })

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

    def test_invalid_filepath(self):
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='invalid')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equals(res.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_dir(self):
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='dir/osfstorage/dir1/')
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.status_code, http_status.HTTP_200_OK)
        assert_equals(res.json, {
            'data': {
                'id': self.project._id,
                'type': 'file-metadata-suggestion',
                'attributes': {
                    'filepath': 'dir/osfstorage/dir1/',
                    'suggestions': [
                        {
                            'format': 'data_format_number',
                            'value': 'files/dir/osfstorage/dir1/',
                        }
                    ]
                }
            }
        })

    def test_file(self):
        filepath = 'osfstorage/file.txt'
        filepath_guid = 'abcde'
        mock_node = mock.Mock()
        mock_node.get_guid.return_value = mock.Mock(_id=filepath_guid)
        mock_resolved_class = mock.Mock()
        mock_resolved_class.get_or_create.return_value = mock_node
        with mock.patch.object(BaseFileNode, 'resolve_class', return_value=mock_resolved_class):
            url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                           filepath=filepath)
            res = self.app.get(url, auth=self.user.auth)
            assert_equals(res.status_code, http_status.HTTP_200_OK)
            assert_equals(res.json, {
                'data': {
                    'id': self.project._id,
                    'type': 'file-metadata-suggestion',
                    'attributes': {
                        'filepath': filepath,
                        'suggestions': [
                            {
                                'format': 'data_format_number',
                                'value': filepath_guid,
                            }
                        ]
                    }
                }
            })

    def test_data_format_number(self):
        filepath = 'dir/osfstorage/dir1/'
        format = 'data_format_number'
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath=filepath)
        res = self.app.get(url, params={'format': format}, auth=self.user.auth)
        assert_equals(res.status_code, http_status.HTTP_200_OK)
        assert_equals(res.json, {
            'data': {
                'id': self.project._id,
                'type': 'file-metadata-suggestion',
                'attributes': {
                    'filepath': filepath,
                    'suggestions': [
                        {
                            'format': format,
                            'value': 'files/{}'.format(filepath),
                        }
                    ]
                }
            }
        })

    def test_invalid_format(self):
        url = self.project.api_url_for('{}_file_metadata_suggestions'.format(SHORT_NAME),
                                       filepath='dir/osfstorage/dir1/')
        res = self.app.get(url, params={'format': 'invalid'}, auth=self.user.auth, expect_errors=True)
        assert_equals(res.status_code, http_status.HTTP_400_BAD_REQUEST)
