# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

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
        self.project_one = ProjectFactory(title="Project One", is_public=True)
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True)
        self.private_project = ProjectFactory(title="Private Project", is_public=False)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

    def tearDown(self):
        OsfTestCase.tearDown(self)
        Node.remove()

    def test_get_all_projects_with_no_filter(self):
        url = "/api/v2/nodes/"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter(self):
        url = "/api/v2/nodes/?filter[title]=Project%20One"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring(self):
        url = "/api/v2/nodes/?filter[title]=Two"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_projects_with_filter(self):
        url = "/api/v2/nodes/?filter[title]=Project"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field(self):
        url = "/api/v2/nodes/?filter[description]=Three"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/api/v2/nodes/?filter[notafield]=bogus"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)