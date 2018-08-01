#!/usr/bin/env python
# encoding: utf-8

import os
from types import NoneType
from xmlrpc.client import DateTime

import mock
from nose.tools import *  # flake8: noqa

from tests.base import OsfTestCase
from osf_tests.factories import (UserFactory, ProjectFactory, NodeFactory,
                             AuthFactory, RegistrationFactory,
                             PrivateLinkFactory)
from framework.auth import Auth
from website.util import rubeus
from website.util.rubeus import sort_by_name

from osf.utils import sanitize

class TestRubeus(OsfTestCase):

    def setUp(self):

        super(TestRubeus, self).setUp()

        self.project = ProjectFactory.create()
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.save()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.add_addon('s3', self.consolidated_auth)
        self.project.creator.add_addon('s3', self.consolidated_auth)
        self.node_settings = self.project.get_addon('s3')
        self.user_settings = self.project.creator.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    def test_hgrid_dummy(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        # FIXME: These tests are very brittle.
        expected = {
            'isPointer': False,
            'provider': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon S3: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
            'nodeId': node._id,
            'nodeUrl': node.url,
            'nodeApiUrl': node.api_url,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }

        expected['permissions'] = permissions

        actual = rubeus.build_addon_root(node_settings, node_settings.bucket, permissions=permissions)

        assert actual['urls']['fetch']
        assert actual['urls']['upload']

        del actual['urls']

        assert_equals(actual, expected)

    def test_build_addon_root_has_correct_upload_limits(self):
        self.node_settings.config.max_file_size = 10
        self.node_settings.config.high_max_file_size = 20

        node = self.project
        user = self.project.creator
        auth = Auth(user)
        permissions = {
            'view': node.can_view(auth),
            'edit': node.can_edit(auth) and not node.is_registration,
        }

        result = rubeus.build_addon_root(
            self.node_settings,
            self.node_settings.bucket,
            permissions=permissions,
            user=user
        )

        assert_equal(result['accept']['maxSize'], self.node_settings.config.max_file_size)

        # user now has elevated upload limit
        user.add_system_tag('high_upload_limit')
        user.save()

        result = rubeus.build_addon_root(
            self.node_settings,
            self.node_settings.bucket,
            permissions=permissions,
            user=user
        )
        assert_equal(
            result['accept']['maxSize'],
            self.node_settings.config.high_max_file_size
        )

    def test_build_addon_root_for_anonymous_vols_hides_path(self):
        private_anonymous_link = PrivateLinkFactory(anonymous=True)
        private_anonymous_link.nodes.add(self.project)
        private_anonymous_link.save()
        project_viewer = UserFactory()

        result = rubeus.build_addon_root(
            self.node_settings,
            self.node_settings.bucket,
            user=project_viewer,
            private_key=private_anonymous_link.key
        )

        assert result['name'] == 'Amazon S3'

    def test_build_addon_root_for_anonymous_vols_shows_path(self):
        private_link = PrivateLinkFactory()
        private_link.nodes.add(self.project)
        private_link.save()
        project_viewer = UserFactory()

        result = rubeus.build_addon_root(
            self.node_settings,
            self.node_settings.bucket,
            user=project_viewer,
            private_key=private_link.key
        )

        assert result['name'] == 'Amazon S3: {0}'.format(
            self.node_settings.bucket
        )

    def test_hgrid_dummy_fail(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon S3: {0}'.format(
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
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'nodeId': node._id,
            'nodeUrl': node.url,
            'nodeApiUrl': node.api_url,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_not_equals(rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=permissions), rv)

    def test_hgrid_dummy_overrides(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        expected = {
            'isPointer': False,
            'provider': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon S3: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {},
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
            'nodeId': node._id,
            'nodeUrl': node.url,
            'nodeApiUrl': node.api_url,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equal(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket,
                permissions=permissions, urls={}
            ),
            expected
        )

    def test_get_nodes_deleted_component(self):
        node = NodeFactory(creator=self.project.creator, parent=self.project)
        node.is_deleted = True
        collector = rubeus.NodeFileCollector(
            self.project, Auth(user=UserFactory())
        )
        nodes = collector._get_nodes(self.project)
        assert_equal(len(nodes['children']), 0)

    def test_serialized_pointer_has_flag_indicating_its_a_pointer(self):
        project = ProjectFactory(creator=self.consolidated_auth.user)
        pointed_project = ProjectFactory(is_public=True)
        project.add_pointer(pointed_project, auth=self.consolidated_auth)
        serializer = rubeus.NodeFileCollector(node=project, auth=self.consolidated_auth)
        ret = serializer._get_nodes(project)
        child = ret['children'][1]  # first child is OSFStorage, second child is pointer
        assert_true(child['isPointer'])

    def test_private_components_not_shown(self):
        user = UserFactory()
        public_project = ProjectFactory(creator=user, is_public=True)
        private_child = NodeFactory(parent=public_project, creator=user, is_public=False)
        public_grandchild = NodeFactory(parent=private_child, creator=user, is_public=True)
        private_greatgrandchild = NodeFactory(parent=public_grandchild, creator=user, is_public=False)
        public_greatgreatgranchild = NodeFactory(parent=private_greatgrandchild, creator=user, is_public=True)

        serializer = rubeus.NodeFileCollector(node=public_project, auth=Auth(user=UserFactory()))
        ret = serializer.to_hgrid()

        children = ret[0]['children']

        assert 'osfstorage' == children[0]['provider']

        assert public_grandchild._id == children[1]['nodeID']
        assert public_grandchild.title == children[1]['name']
        assert False == children[1]['permissions']['edit']

        assert public_greatgreatgranchild._id == children[1]['children'][1]['nodeID']
        assert public_greatgreatgranchild.title == children[1]['children'][1]['name']
        assert False == children[1]['children'][1]['permissions']['edit']

        assert 'Private Component' not in ret

    def test_private_components_shown(self):
        user = UserFactory()
        public_project = ProjectFactory(creator=user, is_public=True)
        private_child = NodeFactory(parent=public_project, creator=user, is_public=False)
        public_grandchild = NodeFactory(parent=private_child, creator=user, is_public=True)

        serializer = rubeus.NodeFileCollector(node=public_project, auth=Auth(user))
        ret = serializer.to_hgrid()

        children = ret[0]['children']

        assert 'osfstorage' == children[0]['provider']

        assert private_child._id == children[1]['nodeID']
        assert private_child.title == children[1]['name']
        assert True == children[1]['permissions']['edit']

        assert public_grandchild._id == children[1]['children'][1]['nodeID']
        assert public_grandchild.title == children[1]['children'][1]['name']
        assert True == children[1]['children'][1]['permissions']['edit']

        assert 'Private Component' not in ret


# TODO: Make this more reusable across test modules
mock_addon = mock.Mock()
serialized = {
    'addon': 'mockaddon',
    'name': 'Mock Addon',
    'isAddonRoot': True,
    'extra': '',
    'permissions': {'view': True, 'edit': True},
    'urls': {
        'fetch': '/fetch',
        'delete': '/delete'
    }
}
mock_addon.config.get_hgrid_data.return_value = [serialized]


class TestSerializingNodeWithAddon(OsfTestCase):

    def setUp(self):
        super(TestSerializingNodeWithAddon, self).setUp()
        self.auth = AuthFactory()
        self.project = ProjectFactory(creator=self.auth.user)
        self.project.get_addons = mock.Mock()
        self.project.get_addons.return_value = [mock_addon]
        self.serializer = rubeus.NodeFileCollector(node=self.project, auth=self.auth)

    def test_collect_addons(self):
        ret = self.serializer._collect_addons(self.project)
        assert_equal(ret, [serialized])

    def test_sort_by_name(self):
        files = [
            {'name': 'F.png'},
            {'name': 'd.png'},
            {'name': 'B.png'},
            {'name': 'a.png'},
            {'name': 'c.png'},
            {'name': 'e.png'},
            {'name': 'g.png'},
        ]
        sorted_files = [
            {'name': 'a.png'},
            {'name': 'B.png'},
            {'name': 'c.png'},
            {'name': 'd.png'},
            {'name': 'e.png'},
            {'name': 'F.png'},
            {'name': 'g.png'},
        ]
        ret = sort_by_name(files)
        for index, value in enumerate(ret):
            assert_equal(value['name'], sorted_files[index]['name'])

    def test_sort_by_name_none(self):
        files = None
        sorted_files = None
        ret = sort_by_name(files)
        assert_equal(ret, sorted_files)

    def test_serialize_node(self):
        ret = self.serializer._get_nodes(self.project)
        assert_equal(
            len(ret['children']),
            len(self.project.get_addons.return_value) + len(list(self.project.nodes))
        )
        assert_equal(ret['kind'], rubeus.FOLDER)
        assert_equal(ret['name'], self.project.title)
        assert_equal(
            ret['permissions'],
            {
                'view': True,
                'edit': True,
            }
        )
        assert_equal(
            ret['urls'],
            {
                'upload': None,
                'fetch': None,
            },
        )
