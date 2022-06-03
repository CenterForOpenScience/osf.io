# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
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
