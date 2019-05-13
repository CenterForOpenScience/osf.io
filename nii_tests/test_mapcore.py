# -*- coding: utf-8 -*-

import sys
import json

import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts

from framework.auth.core import Auth
from osf.models import AbstractNode, NodeLog
from api.base.settings.defaults import API_BASE
from tests.base import fake, OsfTestCase
from website.util import web_url_for
from website.profile.utils import add_contributor_json
from nii.mapcore import mapcore_is_enabled

from tests.utils import assert_latest_log
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import (fake_email,
                                 AuthUserFactory,
                                 UserFactory,
                                 ProjectFactory,
                                 BookmarkCollectionFactory,
                                 InstitutionFactory)

MOCK_STATE = None

ENABLE_DEBUG = True

def DEBUG(msg):
    if ENABLE_DEBUG:
        sys.stderr.write('DEBUG: {}\n'.format(msg))

@pytest.mark.django_db
class TestViewsWithMAPCore(OsfTestCase):
    def setUp(self):
        OsfTestCase.setUp(self)
        self.me = AuthUserFactory()
        BookmarkCollectionFactory(creator=self.me)
        self.project = ProjectFactory(
            creator=self.me,
            is_public=True,
            title=fake.bs()
        )
        self.project_url = self.project.web_url_for('view_project')
        self.user2 = AuthUserFactory()
        self.project.add_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', None)
    def test_disabled(self):
        #DEBUG('MAPCORE_CLIENTID={}'.format(settings.MAPCORE_CLIENTID))
        assert_equal(mapcore_is_enabled(), False)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_enabled')
    def test_enabled(self):
        #DEBUG('MAPCORE_CLIENTID={}'.format(settings.MAPCORE_CLIENTID))
        assert_equal(mapcore_is_enabled(), True)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_dashboard')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    @mock.patch('website.views.use_ember_app')
    def test_dashboard(self, mock_sync, mock_ember):
        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 1)
        assert_equal(mock_ember.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_my_projects')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    def test_my_projects(self, mock_sync):
        url = web_url_for('my_projects', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_view_project')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    #@mock.patch('framework.auth.decorators.mapcore_sync_rdm_project_or_map_group')  # not work
    def test_view_project(self, mock_sync):
        res = self.app.get(self.project_url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 2)
        # TODO mapcore_is_sync_time_expired, skip?

    ### from tests/test_views.py::test_edit_node_title
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_edit_node_title')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_edit_node_title(self, mock_sync1, mock_sync2):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        # The title is changed though posting form data
        self.app.post_json(url, {'name': 'title', 'value': 'Bacon'},
                           auth=self.me.auth).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        self.project.reload()
        # The title was changed
        assert_equal(self.project.title, 'Bacon')
        # A log event was saved
        assert_equal(self.project.logs.latest().action, 'edit_title')

    ### from tests/test_views.py::test_edit_description
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_edit_description')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_edit_description(self, mock_sync1, mock_sync2):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        self.app.post_json(url,
                           {'name': 'description', 'value': 'Deep-fried'},
                           auth=self.me.auth)
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        self.project.reload()
        assert_equal(self.project.description, 'Deep-fried')

    ### from tests/test_views.py::test_add_contributor_post
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_add_contributors')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_add_contributors(self, mock_sync1, mock_sync2):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.me, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = '/api/v1/project/{0}/contributors/'.format(project._id)

        dict2 = add_contributor_json(user2)
        dict3 = add_contributor_json(user3)
        dict2.update({
            'permission': 'admin',
            'visible': True,
        })
        dict3.update({
            'permission': 'write',
            'visible': False,
        })

        self.app.post_json(
            url,
            {
                'users': [dict2, dict3],
                'node_ids': [project._id],
            },
            content_type='application/json',
            auth=self.me.auth,
        ).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        project.reload()
        assert_in(user2, project.contributors)
        # A log event was added
        assert_equal(project.logs.latest().action, 'contributor_added')
        assert_equal(len(project.contributors), 3)

        assert_equal(project.get_permissions(user2), ['read', 'write', 'admin'])
        assert_equal(project.get_permissions(user3), ['read', 'write'])

    ### from tests/test_views.py::test_contributor_manage_reorder
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_contributor_manage_reorder')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_contributor_manage_reorder(self, mock_sync1, mock_sync2):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.me, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': [
                    'read', 'write', 'admin'], 'visible': False},
            ]
        )
        # Add a non-registered user
        unregistered_user = project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.me),
            save=True,
        )

        url = project.api_url + 'contributors/manage/'
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': reg_user2._id, 'permission': 'admin',
                        'registered': True, 'visible': False},
                    {'id': project.creator._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                    {'id': unregistered_user._id, 'permission': 'admin',
                        'registered': False, 'visible': True},
                    {'id': reg_user1._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                ]
            },
            auth=self.me.auth,
        )
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        project.reload()
        assert_equal(
            # Note: Cast ForeignList to list for comparison
            list(project.contributors),
            [reg_user2, project.creator, unregistered_user, reg_user1]
        )
        assert_equal(
            list(project.visible_contributors),
            [project.creator, unregistered_user, reg_user1]
        )

    ### from tests/test_views.py::test_project_remove_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_remove_contributor')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_remove_contributor(self, mock_sync1, mock_sync2):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id]}
        self.app.post(url, json.dumps(payload),
                      content_type='application/json',
                      auth=self.me.auth).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs.latest().action, 'contributor_removed')


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestAPIWithMAPCore:

    @pytest.fixture(autouse=True, scope='class')
    def app_init(self):
        #DEBUG('*** app_init')
        from website.app import init_app
        init_app(routes=False, set_backends=False)

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_one(self, institution_one):
        auth_user = AuthUserFactory()
        auth_user.affiliated_institutions.add(institution_one)
        return auth_user

    @pytest.fixture()
    def nodes_url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def title(self):
        return 'GRDM Project'

    @pytest.fixture()
    def title_new(self):
        return 'Super GRDM Project'

    @pytest.fixture()
    def description(self):
        return 'Pytest conversions are tedious'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def private_project(self, user_one, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user_one
        )

    @pytest.fixture()
    def private_project_json(self, title, description, category):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': False
                }
            }
        }

    ### from api_tests/nodes/views/test_node_list.py::
    ###      test_creates_private_project_logged_in_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_create_project')
    @mock.patch('nii.mapcore.mapcore_sync_map_new_group0')
    def test_create_project(
            self, mock_sync, app, user_one, private_project_json, nodes_url):
        res = app.post_json_api(nodes_url, private_project_json, auth=user_one.auth)
        assert_equal(mock_sync.call_count, 1)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == private_project_json['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == private_project_json['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == private_project_json['data']['attributes']['category']
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)
        assert project.logs.latest().action == NodeLog.PROJECT_CREATED

    ### from api_tests/nodes/views/test_node_detail.py::
    ###      test_partial_update_private_project_logged_in_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_update_project')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_update_project(
            self, mock_sync, app, user_one, title_new, description, category, private_project, private_url):
        with assert_latest_log(NodeLog.EDITED_TITLE, private_project):
            res = app.patch_json_api(private_url, {
                'data': {
                    'attributes': {
                        'title': title_new},
                    'id': private_project._id,
                    'type': 'nodes',
                }
            }, auth=user_one.auth)
            assert_equal(mock_sync.call_count, 1)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category
