import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

from framework.auth.decorators import Auth
from website.util import rubeus
from deep_eq import deep_eq


class TestRubeus(DbTestCase):

    def setUp(self):

        super(TestRubeus, self).setUp()

        self.project = ProjectFactory.build()
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )
        self.project.save()

        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')
        self.node_settings = self.project.get_addon('s3')
        self.user_settings = self.project.creator.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    def test_hgrid_dummy_correct(self):
        node_settings = self. node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'extensions': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        deep_eq(rubeus.build_dummy_folder(node_settings, node_settings.bucket, permissions=permissions), rv, _assert=True)

    def test_hgrid_dummy_fail(self):
        node_settings = self. node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'extensions': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_false(deep_eq(rubeus.build_dummy_folder(node_settings, node_settings.bucket, permissions=permissions), rv))

    def test_hgrid_dummy_overrides(self):
        node_settings = self. node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {

            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'extensions': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        deep_eq(rubeus.build_dummy_folder(node_settings, node_settings.bucket, permissions=permissions, urls={}), rv, _assert=True)

    def test_hgrid_dummy_node_urls(self):
        node_settings = self.node_settings
        node_settings.config.urls = {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'extensions': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        deep_eq(rubeus.build_dummy_folder(node_settings, node_settings.bucket, permissions=permissions), rv, _assert=True)










