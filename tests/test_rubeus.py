#!/usr/bin/env python
# encoding: utf-8

import os
from types import NoneType
from xmlrpclib import DateTime

import mock
from nose.tools import *
from webtest_plus import TestApp

from tests.base import OsfTestCase
from tests.factories import (UserFactory, ProjectFactory, NodeFactory,
                             AuthFactory, PointerFactory, RegistrationFactory)
from framework.auth import Auth
from website.util import rubeus
from website.util.rubeus import sort_by_name

from website.util import sanitize

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
        user.system_tags.append('high_upload_limit')
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

    def test_serialize_private_node(self):
        user = UserFactory()
        auth = Auth(user=user)
        public = ProjectFactory.create(is_public=True)
        # Add contributor with write permissions to avoid admin permission cascade
        public.add_contributor(user, permissions=['read', 'write'])
        public.save()
        private = ProjectFactory(parent=public, is_public=False)
        NodeFactory(parent=private)
        collector = rubeus.NodeFileCollector(node=public, auth=auth)

        private_dummy = collector._serialize_node(private)
        assert_false(private_dummy['permissions']['edit'])
        assert_false(private_dummy['permissions']['view'])
        assert_equal(private_dummy['name'], 'Private Component')
        assert_equal(len(private_dummy['children']), 0)

    def test_get_node_name(self):
        user = UserFactory()
        auth = Auth(user=user)
        another_user = UserFactory()
        another_auth = Auth(user=another_user)

        # Public (Can View)
        public_project = ProjectFactory(is_public=True)
        collector = rubeus.NodeFileCollector(node=public_project, auth=another_auth)
        node_name =  sanitize.unescape_entities(public_project.title)
        assert_equal(collector._get_node_name(public_project), node_name)

        # Private  (Can't View)
        registration_private = RegistrationFactory(creator=user)
        registration_private.is_public = False
        registration_private.save()
        collector = rubeus.NodeFileCollector(node=registration_private, auth=another_auth)
        assert_equal(collector._get_node_name(registration_private), u'Private Registration')

        content = ProjectFactory(creator=user)
        node = ProjectFactory(creator=user)

        forked_private = node.fork_node(auth=auth)
        forked_private.is_public = False
        forked_private.save()
        collector = rubeus.NodeFileCollector(node=forked_private, auth=another_auth)
        assert_equal(collector._get_node_name(forked_private), u'Private Fork')

        pointer_private = node.add_pointer(content, auth=auth)
        pointer_private.is_public = False
        pointer_private.save()
        collector = rubeus.NodeFileCollector(node=pointer_private, auth=another_auth)
        assert_equal(collector._get_node_name(pointer_private), u'Private Link')

        private_project = ProjectFactory(is_public=False)
        collector = rubeus.NodeFileCollector(node=private_project, auth=another_auth)
        assert_equal(collector._get_node_name(private_project), u'Private Component')

        private_node = NodeFactory(is_public=False)
        collector = rubeus.NodeFileCollector(node=private_node, auth=another_auth)
        assert_equal(collector._get_node_name(private_node), u'Private Component')

    def test_collect_components_deleted(self):
        node = NodeFactory(creator=self.project.creator, parent=self.project)
        node.is_deleted = True
        collector = rubeus.NodeFileCollector(
            self.project, Auth(user=UserFactory())
        )
        nodes = collector._collect_components(self.project, visited=[])
        assert_equal(len(nodes), 0)

    def test_serialized_pointer_has_flag_indicating_its_a_pointer(self):
        pointer = PointerFactory()
        serializer = rubeus.NodeFileCollector(node=pointer, auth=self.consolidated_auth)
        ret = serializer._serialize_node(pointer)
        assert_true(ret['isPointer'])


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
        ret = self.serializer._serialize_node(self.project)
        assert_equal(
            len(ret['children']),
            len(self.project.get_addons.return_value) + len(self.project.nodes)
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
