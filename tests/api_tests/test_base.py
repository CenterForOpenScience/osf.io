# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from website.models import Node
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory

class TestApiBaseViews(OsfTestCase):

    def test_root_returns_200(self):
        res = self.app.get('/api/v2/')
        assert_equal(res.status_code, 200)


class TestFiltering(OsfTestCase):

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