# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, BookmarkCollectionFactory, CollectionFactory, ProjectFactory, RegistrationFactory

from api.base.settings.defaults import API_BASE


class TestUserNodes(ApiTestCase):

    def setUp(self):
        super(TestUserNodes, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()

        self.user_two = AuthUserFactory()
        self.public_project_user_one = ProjectFactory(title="Public Project User One",
                                                      is_public=True,
                                                      creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two",
                                                      is_public=True,
                                                      creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)
        self.deleted_project_user_one = CollectionFactory(title="Deleted Project User One",
                                                          is_public=False,
                                                          creator=self.user_one,
                                                          is_deleted=True)
        self.folder = CollectionFactory()
        self.deleted_folder = CollectionFactory(title="Deleted Folder User One",
                                                is_public=False,
                                                creator=self.user_one,
                                                is_deleted=True)
        self.bookmark_collection = BookmarkCollectionFactory()

        self.registration = RegistrationFactory(project=self.public_project_user_one,
                                                      creator=self.user_one, is_public=True)

    def tearDown(self):
        super(TestUserNodes, self).tearDown()

    def test_authorized_in_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_anonymous_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_get_projects_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)
        assert_not_in(self.registration._id, ids)

    def test_get_projects_not_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)
        assert_not_in(self.registration._id, ids)

    def test_get_projects_logged_in_as_different_user(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_two._id, ids)
        assert_not_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)
        assert_not_in(self.registration._id, ids)

