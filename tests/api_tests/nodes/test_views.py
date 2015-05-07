# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from website.util import api_v2_url_for
from tests.base import OsfTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory


class TestNodeList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.auth = (self.user.username, 'justapoorboy')

    def test_returns_200(self):
        res = self.app.get('/api/v2/nodes/')
        assert_equal(res.status_code, 200)

    def test_only_returns_non_deleted_public_projects(self):
        deleted = ProjectFactory(is_deleted=True)
        private = ProjectFactory(is_public=False)
        public = ProjectFactory(is_public=True)

        res = self.app.get('/api/v2/nodes/')
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert_in(public._id, ids)
        assert_not_in(deleted._id, ids)
        assert_not_in(private._id, ids)

        Node.remove()


class TestNodeContributorList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()

        password = fake.password()
        self.password = password

        self.user.set_password(password)
        self.user.save()
        self.auth = (self.user.username, password)

        self.project = ProjectFactory(is_public=False)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_must_be_contributor(self):

        non_contrib = UserFactory.build()
        pw = fake.password()
        non_contrib.set_password(pw)
        non_contrib.save()

        url = api_v2_url_for('nodes:node-contributors', kwargs=dict(pk=self.project._id))
        # non-authenticated
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # non-contrib
        res = self.app.get(url, auth=(non_contrib.username, pw), expect_errors=True)
        assert_equal(res.status_code, 403)

        # contrib
        res = self.app.get(url, auth=(self.user.username, self.password))
        assert_equal(res.status_code, 200)
        Node.remove()


class TestNodeFiltering(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.project_one = ProjectFactory(title="Project One", is_public=True)
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False, creator=self.user_two)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

    def tearDown(self):
        OsfTestCase.tearDown(self)
        Node.remove()

    def test_get_all_projects_with_no_filter_logged_in(self):
        url = "/api/v2/nodes/"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_all_projects_with_no_filter_not_logged_in(self):
        url = "/api/v2/nodes/"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Project%20One"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_not_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Project%20One"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Two"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_not_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Two"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_or_my_projects_with_filter_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Project"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_projects_with_filter_not_logged_in(self):
        url = "/api/v2/nodes/?filter[title]=Project"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_logged_in(self):
        url = "/api/v2/nodes/?filter[description]=Three"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_not_logged_in(self):
        url = "/api/v2/nodes/?filter[description]=Three"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/api/v2/nodes/?filter[notafield]=bogus"

        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/api/v2/nodes/?filter[notafield]=bogus"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)


class TestNodePointersList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.auth = (self.user.username, 'password')
        self.project = ProjectFactory()
        self.pointer_project = ProjectFactory()
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))

    def test_returns_200(self):
        url = api_v2_url_for('nodes:node-pointers', kwargs=dict(pk=self.project._id))
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 200)

    def test_returns_node_pointers(self):
        url = api_v2_url_for('nodes:node-pointers', kwargs=dict(pk=self.project._id))
        res = self.app.get(url, auth=self.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['node_id'], self.pointer_project._id)

    def test_creates_node_pointer(self):
        project = ProjectFactory()
        url = api_v2_url_for('nodes:node-pointers', kwargs=dict(pk=self.project._id))
        payload = {'node_id': project._id}
        res = self.app.post(url, payload, auth=self.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['node_id'], project._id)


class TestNodeContributorFiltering(OsfTestCase):

    def test_filtering_node_with_only_bibliographic_contributors(self):
        project = ProjectFactory()
        password = fake.password()
        project.creator.set_password(password)
        project.creator.save()
        auth = (project.creator.username, password)

        base_url = api_v2_url_for('nodes:node-contributors', kwargs=dict(pk=project._id))

        # no filter
        res = self.app.get(base_url, auth=auth)
        assert_equal(len(res.json['data']), 1)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_node_with_non_bibliographic_contributor(self):
        project = ProjectFactory()
        password = fake.password()
        project.creator.set_password(password)
        project.creator.save()
        auth = (project.creator.username, password)
        non_bibliographic_contrib = UserFactory()
        project.add_contributor(non_bibliographic_contrib, visible=False)
        project.save()

        base_url = api_v2_url_for('nodes:node-contributors', kwargs=dict(pk=project._id))

        # no filter
        res = self.app.get(base_url, auth=auth)
        assert_equal(len(res.json['data']), 2)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0].get('bibliographic', None))


class TestNodePointerDetail(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.auth = (self.user.username, 'password')
        self.project = ProjectFactory()
        self.pointer_project = ProjectFactory()
        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)

    def test_returns_200(self):
        url = api_v2_url_for('nodes:node-pointer-detail', kwargs=dict(pk=self.project._id, pointer_id=self.pointer._id))
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 200)

    def test_returns_node_pointer(self):
        url = api_v2_url_for('nodes:node-pointer-detail', kwargs=dict(pk=self.project._id, pointer_id=self.pointer._id))
        res = self.app.get(url, auth=self.auth)
        res_json = res.json['data']
        assert_equal(res_json['node_id'], self.pointer_project._id)

    def test_deletes_node_pointer(self):
        url = api_v2_url_for('nodes:node-pointer-detail', kwargs=dict(pk=self.project._id, pointer_id=self.pointer._id))
        res = self.app.delete(url, auth=self.auth)
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)