# -*- coding: utf-8 -*-
import os
from types import NoneType
from xmlrpclib import DateTime
from flask import Flask
import mock
from nose.tools import *
from webtest_plus import TestApp

from tests.base import OsfTestCase
from tests.factories import (UserFactory, ProjectFactory, NodeFactory,
    AuthFactory, PointerFactory, DashboardFactory, FolderFactory, AuthUserFactory)

from framework.auth import Auth
from website.project import Node
from website.util import rubeus, api_url_for

import website.app
from website.views import get_all_projects_smart_folder

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

class TestRubeus(OsfTestCase):

    def setUp(self):

        super(TestRubeus, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.save()

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
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
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
                'upload': node.api_url + 's3/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
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
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_not_equals(rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=permissions), rv)

    def test_hgrid_dummy_overrides(self):
        node_settings = self.node_settings
        node_settings.config.urls = None
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
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
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket,
                permissions=permissions, urls={}
            ),
            rv
        )

    def test_hgrid_dummy_node_urls(self):
        node_settings = self.node_settings
        user = Auth(self.project.creator)

        node = self.project
        node_settings.config.urls = {
            'fetch': node.api_url + 's3/hgrid/',
            'upload': node.api_url + 's3/upload/'
        }

        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
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
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
        )

    def test_serialize_private_node(self):
        user = UserFactory()
        auth = Auth(user=user)
        public = ProjectFactory.build(is_public=True)
        public.add_contributor(user)
        public.save()
        private = ProjectFactory(project=public, is_public=False)
        NodeFactory(project=private)
        collector = rubeus.NodeFileCollector(node=public, auth=auth)

        private_dummy = collector._serialize_node(private)
        assert_false(private_dummy['permissions']['edit'])
        assert_false(private_dummy['permissions']['view'])
        assert_equal(private_dummy['name'], 'Private Component')
        assert_equal(len(private_dummy['children']), 0)

    def test_collect_components_deleted(self):
        node = NodeFactory(creator=self.project.creator, project=self.project)
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
        self.auth = AuthFactory()
        self.project = ProjectFactory(creator=self.auth.user)
        self.project.get_addons = mock.Mock()
        self.project.get_addons.return_value = [mock_addon]
        self.serializer = rubeus.NodeFileCollector(node=self.project, auth=self.auth)

    def test_collect_addons(self):
        ret = self.serializer._collect_addons(self.project)
        assert_equal(ret, [serialized])

    def test_serialize_node(self):
        ret = self.serializer._serialize_node(self.project)
        assert_equal(
            len(ret['children']),
            len(self.project.get_addons.return_value) + len(self.project.nodes)
        )
        assert_equal(ret['kind'], rubeus.FOLDER)
        assert_equal(ret['name'], 'Project: {0}'.format(self.project.title))
        assert_equal(ret['permissions'], {
            'view': True,
            'edit': True
        })
        assert_equal(
            ret['urls'],
            {
                'upload': os.path.join(self.project.api_url, 'osffiles') + '/',
                'fetch': None
            },
            'project root data has no upload or fetch urls'
        )

    def test_collect_js_recursive(self):
        self.project.get_addons.return_value[0].config.include_js = {'files': ['foo.js']}
        node = NodeFactory(project=self.project)
        mock_node_addon = mock.Mock()
        mock_node_addon.config.include_js = {'files': ['bar.js', 'baz.js']}
        node.get_addons = mock.Mock()
        node.get_addons.return_value = [mock_node_addon]
        assert_equal(
            rubeus.collect_addon_js(self.project),
            {'foo.js', 'bar.js', 'baz.js'}
        )

    def test_collect_js_unique(self):
        self.project.get_addons.return_value[0].config.include_js = {'files': ['foo.js']}
        node = NodeFactory(project=self.project)
        mock_node_addon = mock.Mock()
        mock_node_addon.config.include_js = {'files': ['foo.js', 'baz.js']}
        node.get_addons = mock.Mock()
        node.get_addons.return_value = [mock_node_addon]
        assert_equal(
            rubeus.collect_addon_js(self.project),
            {'foo.js', 'baz.js'}
        )

class TestSerializingEmptyDashboard(OsfTestCase):

    AMP = 'All my projects'
    AMP_ID = '-amp'
    AMR = 'All my registrations'
    AMR_ID = '-amr'

    def setUp(self):
        self.dash = DashboardFactory()
        self.auth = AuthFactory(user=self.dash.creator)
        self.dash_hgrid = rubeus.to_project_hgrid(self.dash, self.auth)


    def test_empty_dashboard_hgrid_is_list(self):
        assert_is_instance(self.dash_hgrid, list)


    def test_empty_dashboard_smart_folders_correct_number(self):
        assert_equal(len(self.dash_hgrid), 2)


    def test_empty_dashboard_smart_folders_correct_names_and_ids(self):
        for node_hgrid in self.dash_hgrid:
            assert_in(node_hgrid['name'], (self.AMP, self.AMR))
        for node_hgrid in self.dash_hgrid:
            if node_hgrid['name'] == self.AMP:
                assert_equal(node_hgrid['node_id'], self.AMP_ID)
            elif node_hgrid['name'] == self.AMR:
                assert_equal(node_hgrid['node_id'], self.AMR_ID)


    def test_empty_dashboard_smart_folders_empty(self):
        for node_hgrid in self.dash_hgrid:
            assert_equal(node_hgrid['children'], [])


    def test_empty_dashboard_valid_folders(self):
        for node in self.dash_hgrid:
            assert_valid_hgrid_folder(node)


    def test_empty_dashboard_valid_folders(self):
        for node in self.dash_hgrid:
            assert_valid_hgrid_smart_folder(node)

class testSerializingPopulatedDashboard(OsfTestCase):

    AMP_ID = '-amp'
    AMR_ID = '-amr'

    def setUp(self):
        self.dash = DashboardFactory()
        self.user = self.dash.creator
        self.auth = AuthFactory(user=self.user)

        self.init_dash_hgrid = rubeus.to_project_hgrid(self.dash, self.auth)

    def addFolder(self):
        self.folder = FolderFactory(creator=self.user)
        self.dash.add_pointer(self.folder, self.auth)

    def addProject(self):
        self.project = ProjectFactory(creator=self.user)


    def test_dashboard_1_folder_size(self):
        self.addFolder()
        dash_hgrid = rubeus.to_project_hgrid(self.dash, self.auth)
        assert_equal(len(dash_hgrid), len(self.init_dash_hgrid) + 1)


    def test_dashboard_1_folder_titles(self):
        self.addFolder()
        dash_hgrid = rubeus.to_project_hgrid(self.dash, self.auth)

        assert_true(
            {'All my projects', 'All my registrations', self.folder.title} <=
            {node_hgrid['name'] for node_hgrid in dash_hgrid}
        )


    def test_dashboard_1_folder_containing_project_size(self):
        self.addFolder()
        project = ProjectFactory(creator=self.user)
        self.folder.add_pointer(project,self.auth)

        dash_hgrid = rubeus.to_project_hgrid(self.dash, self.auth)
        len_with_folder = len(self.init_dash_hgrid) + 1
        assert_equal(len(dash_hgrid), len_with_folder)

class TestSmartFolderViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.dash = DashboardFactory()
        self.user = self.dash.creator
        self.auth = AuthFactory(user=self.user)

    # TODO: necessary? this should be existing functionality
    # def test_expanding_all_projects_then_adding_project(self):
    #     pass
    #
    # def test_adding_project_then_expanding_folder(self):
    #     pass

    # todo: parallel test for all registrations?
    @mock.patch('website.project.decorators.get_api_key')
    @mock.patch('website.project.decorators.Auth.from_kwargs')
    def test_adding_project_then_expanding_all_projects(self, mock_from_kwargs, mock_get_api_key):
        mock_get_api_key.return_value = 'api_keys_lol'
        mock_from_kwargs.return_value = Auth(user=self.user)

        with app.test_request_context():
            url = api_url_for('get_dashboard')

        #TODO: this fails if '-amp/' is appended. is that correct?
        res = self.app.get(url + '-amp')
        print res
        assert_equal(len(res), 0)

        project = ProjectFactory(creator=self.user)
        res = self.app.get(url + '-amp')
        print res
        assert_equal(len(res), 1)




    def test_expanding_all_projects_then_adding_project(self):
        assert False

    def test_serialize_folder_containing_folder(self):
        assert False




def assert_valid_hgrid_folder(node_hgrid):
    folder_types = {
        'name': str,
        'children': list,
        'contributors': list,
        'dateModified': (DateTime, NoneType),
        'node_id': str,
        'modifiedDelta': int,
        'modifiedBy': (dict, NoneType),
        'urls': dict,
        'isDashboard': bool,
        'expand': bool,
        'permissions': dict,
        'isSmartFolder': bool,
    }
    keys_types = {
        'urls': (str, NoneType),
        'permissions': bool,
    }
    folder_values = {
        'parentIsFolder': True,
        'isPointer': False,
        'isFolder': True,
        'kind': 'folder',
    }

    # TODO: test keys of permissions and urls?

    assert_is_instance(node_hgrid, dict)

    for key, correct_type in folder_types.items():
        assert_is_instance(node_hgrid[key], correct_type)

    for key, correct_type in keys_types.items():
        for inner_key, inner_value in node_hgrid[key].items():
            assert_is_instance(inner_value, correct_type)


def assert_valid_hgrid_smart_folder(node_hgrid):
    smart_folder_values = {
        'contributors': [],
        'isPointer': False,
        'dateModified': None,
        'modifiedDelta': 0,
        'modifiedBy': None,
        'isSmartFolder': True,
        'urls': {
            'upload': None,
            'fetch': None
        },
        'isDashboard': False,
        'permissions': {
            'edit': False,
            'acceptsDrops': False,
            'copyable': False,
            'movable': False,
            'view': True
        }
    }
    assert_valid_hgrid_folder(node_hgrid)
    for attr, correct_value in smart_folder_values.items():
        assert_equal(correct_value, node_hgrid[attr])


