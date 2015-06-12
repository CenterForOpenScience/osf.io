# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, FolderFactory, DashboardFactory, NodeFactory, ProjectFactory


class TestCollectionsList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.deleted = FolderFactory(is_deleted=True, creator=self.user)
        self.collection = FolderFactory(creator=self.user, is_public=True, )
        self.url = "/{}collections/".format(API_BASE)

    def test_only_returns_non_deleted_collections(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_not_in(self.deleted._id, ids)
        assert_in(self.collection._id, ids)

    def test_return_collection_list_logged_in_user(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        ids = [node['id'] for node in res.json['data']]
        assert_in(self.collection._id, ids)

    def test_return_collection_list_logged_out_user(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        ids = [node['id'] for node in res.json['data']]
        assert_in(self.collection._id, ids)

        Node.remove()


class TestCollectionFiltering(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.save()
        self.basic_auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')
        self.collection_one = FolderFactory(title="Project One", is_public=True, creator=self.user_one)
        self.collection_two = FolderFactory(title="Project Two", is_public=True, creator=self.user_one)
        self.collection_three = FolderFactory(title="Three", is_public=True, creator=self.user_one)
        self.private_collection_user_one = FolderFactory(title="Private Project User One", is_public=False,
                                                         creator=self.user_one)
        self.private_collection_user_two = FolderFactory(title="Private Project User Two", is_public=False,
                                                         creator=self.user_two)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

        self.url = "/{}collections/".format(API_BASE)

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_get_all_collections_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_in(self.collection_three._id, ids)
        assert_in(self.private_collection_user_one._id, ids)
        assert_not_in(self.private_collection_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_collection_with_exact_filter_logged_in(self):
        url = "/v2/collections/?filter[title]=Project%20One"

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_not_in(self.private_collection_user_one._id, ids)
        assert_not_in(self.private_collection_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_collections_with_substring_logged_in(self):
        url = "/v2/collections/?filter[title]=Two"

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_not_in(self.private_collection_user_one._id, ids)
        assert_not_in(self.private_collection_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_or_my_collections_with_filter_logged_in(self):
        url = "/v2/collections/?filter[title]=Project"

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_in(self.private_collection_user_one._id, ids)
        assert_not_in(self.private_collection_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/v2/collections/?filter[notafield]=bogus"

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_in(self.collection_three._id, ids)
        assert_in(self.private_collection_user_one._id, ids)
        assert_not_in(self.private_collection_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)


class TestCollectionCreate(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.url = "/{}collections/".format(API_BASE)

        self.title = 'Cool Project'
        self.category = 'data'

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_folder = {'title': self.title, 'public': True, 'is_folder': True}
        self.private_folder = {'title': self.title, 'is_folder': True, 'public': False}

    def test_creates_public_collection_logged_out(self):
        res = self.app.post_json(self.url, self.public_folder, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_public_collection_logged_in(self):
        res = self.app.post_json(self.url, self.public_folder, auth=self.basic_auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.public_folder['title'])

    def test_creates_private_collection_logged_out(self):
        res = self.app.post_json(self.url, self.private_folder, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_private_collection_logged_in_contributor(self):
        res = self.app.post_json(self.url, self.private_folder, auth=self.basic_auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.private_folder['title'])

    def test_creates_collection_creates_collection_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'

        res = self.app.post_json(self.url, {
            'title': title,
            'public': True,
            'is_folder': True,
        }, auth=self.basic_auth)
        collection_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/{}collections/{}/'.format(API_BASE, collection_id)
        res = self.app.get(url, auth=self.basic_auth)
        assert_equal(res.json['data']['title'], strip_html(title))
        # on


class TestCollectionDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_folder = FolderFactory(title="Project One", is_public=True, creator=self.user)
        self.nonuser_folder = FolderFactory(title="Project Two", is_public=False)
        self.public_url = '/{}collections/{}/'.format(API_BASE, self.public_folder._id)
        self.private_url = '/{}collections/{}/'.format(API_BASE, self.nonuser_folder._id)
        self.smart_folder_url = '/{}collections/{}/'.format(API_BASE, '~amr')

        self.smart_folder = FolderFactory(_id='~amr')

    def test_return_403_collection_details_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_public_collection_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.public_folder.title)

    def test_return_smart_folder(self):
        res = self.app.get(self.smart_folder_url, auth=self.basic_auth)
        node_json = res.json['data']

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['smart_folder'], True)


class TestDashboardDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_folder = FolderFactory(title="Project One", is_public=True, creator=self.user)
        self.nonuser_folder = FolderFactory(title="Project Two", is_public=False)
        self.public_url = '/{}collections/{}/'.format(API_BASE, self.public_folder._id)
        self.private_url = '/{}collections/{}/'.format(API_BASE, self.nonuser_folder._id)
        self.dash_url = "/{}collections/dashboard/".format(API_BASE)
        self.dashboard_folder = DashboardFactory()

    def test_return_403_dash_details_logged_out(self):
        res = self.app.get(self.dash_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_dash_details_logged_in(self):
        res = self.app.get(self.dash_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)

        ids = [node['id'] for node in res.json['data']]
        assert_in(self.dashboard_folder._id, ids)


class TestCollectionUpdate(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_collection = FolderFactory(title=self.title, is_public=False, creator=self.user)
        self.public_url = '/{}collections/{}/'.format(API_BASE, self.public_collection._id)

        self.private_collection = FolderFactory(title=self.title, is_public=False)
        self.private_url = '/{}collections/{}/'.format(API_BASE, self.private_collection._id, creator=self.user_two)

    def test_update_public_collection_logged_in(self):
        # Public collection, logged in, contrib
        res = self.app.put_json(self.public_url, {
            'title': self.new_title,
            'public': True,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

    def test_update_private_collection_logged_out(self):
        res = self.app.put_json(self.private_url, {
            'title': self.new_title,
            'public': False,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_collection_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        collection = self.collection = FolderFactory(
            title=self.title, is_public=True, creator=self.user)

        url = '/{}collections/{}/'.format(API_BASE, collection._id)
        res = self.app.put_json(url, {
            'title': new_title,
            'public': True,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_partial_update_collection_updates_collection_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> collection'
        collection = self.collection = FolderFactory(
            title=self.title, is_public=True, creator=self.user)

        url = '/v2/collections/{}/'.format(collection._id)
        res = self.app.patch_json(url, {
            'title': new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_partial_update_collection_logged_out(self):
        res = self.app.patch_json(self.private_url, {'title': self.new_title}, expect_errors=True, auth=self.user)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_partial_update_collection_logged_in(self):
        res = self.app.patch_json(self.private_url, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

    def test_partial_update_private_collection_logged_out(self):
        res = self.app.patch_json(self.private_url, {'title': self.new_title}, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)


class TestCollectionChildrenList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)
        self.collection = FolderFactory()
        self.collection.add_contributor(self.user, permissions=['read', 'write'])
        self.collection.save()
        self.component = NodeFactory(parent=self.collection, creator=self.user)
        self.pointer = FolderFactory()
        self.collection.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_collection_url = '/v2/collections/{}/children/'.format(self.collection._id)

        self.public_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_collection.save()
        self.public_component = NodeFactory(parent=self.public_collection, creator=self.user,
                                            is_public=True)
        self.public_collection_url = '/v2/collections/{}/children/'.format(self.public_collection._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

    def test_collection_children_list_does_not_include_pointers(self):
        res = self.app.get(self.private_collection_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)

    def test_return_public_collection_children_list_logged_out(self):
        res = self.app.get(self.public_collection_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_public_collection_children_list_logged_in(self):
        res = self.app.get(self.public_collection_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_private_collection_children_list_logged_out(self):
        res = self.app.get(self.private_collection_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_return_private_collection_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_collection_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.component._id)

        Node.remove()


class TestCollectionPointersList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.collection = FolderFactory(is_public=False, creator=self.user)
        self.pointer_collection = FolderFactory(is_public=False, creator=self.user)
        self.collection.add_pointer(self.pointer_collection, auth=Auth(self.user))
        self.private_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection._id)

        self.public_folder = FolderFactory(is_public=True, creator=self.user)
        self.public_pointer_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_folder.add_pointer(self.public_pointer_collection, auth=Auth(self.user))
        self.public_url = '/{}collections/{}/pointers/'.format(API_BASE, self.public_folder._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

    def test_return_public_collection_pointers_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_public_collection_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_collection._id)

    def test_return_private_collection_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)


class TestCreateCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.collection = FolderFactory(is_public=False, creator=self.user)
        self.pointer_collection = FolderFactory(is_public=False, creator=self.user)
        self.collection.add_pointer(self.pointer_collection, auth=Auth(self.user))
        self.private_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection._id)
        self.private_payload = {'node_id': self.collection._id}

        self.public_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_pointer_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_collection.add_pointer(self.public_pointer_collection, auth=Auth(self.user))
        self.public_url = '/{}collections/{}/pointers/'.format(API_BASE, self.public_collection._id)
        self.public_payload = {'node_id': self.public_collection._id}

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')



    def test_creates_public_collection_pointer_logged_out(self):
        res = self.app.post(self.public_url, self.public_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_public_collection_pointer_logged_in(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.post(self.public_url, self.public_payload, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['node_id'], self.public_collection._id)

    def test_creates_private_collection_pointer_logged_out(self):
        res = self.app.post(self.private_url, self.private_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)


class TestCollectionPointerDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.private_collection = FolderFactory(creator=self.user, is_public=False)
        self.pointer_collection = FolderFactory(creator=self.user, is_public=False)
        self.pointer = self.private_collection.add_pointer(self.pointer_collection, auth=Auth(self.user), save=True)
        self.private_url = '/v2/collections/{}/pointers/{}'.format(self.private_collection._id, self.pointer._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.public_collection = FolderFactory(is_public=True)
        self.public_pointer_collection = FolderFactory(is_public=True)
        self.public_pointer = self.public_collection.add_pointer(self.public_pointer_collection, auth=Auth(self.user),
                                                                 save=True)
        self.public_url = '/v2/collections/{}/pointers/{}'.format(self.public_collection._id, self.public_pointer._id)

        self.collection_one = FolderFactory(creator=self.user)
        self.collection_two = FolderFactory(creator=self.user)

    def test_returns_public_collection_pointer_detail_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_public_collection_pointer_detail_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res_json['node_id'], self.public_pointer_collection._id)

    def test_returns_private_collection_pointer_detail_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_api_get_folder_pointers_from_non_folder(self):

        url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_one._id)
        self.collection_one.add_pointer(self.collection_two, auth=self.basic_auth)
        res = self.app.get(url, auth=self.basic_auth)
        pointers = res.json
        assert_equal(len(pointers), 0)


class TestDeleteCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.collection = FolderFactory(creator=self.user, is_public=False)
        self.pointer_collection = FolderFactory(creator=self.user, is_public=True)
        self.pointer = self.collection.add_pointer(self.pointer_collection, auth=Auth(self.user), save=True)
        self.private_url = '/{}collections/{}/pointers/{}'.format(API_BASE, self.collection._id, self.pointer._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.public_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_pointer_collection = FolderFactory(is_public=True, creator=self.user)
        self.public_pointer = self.public_collection.add_pointer(self.public_pointer_collection, auth=Auth(self.user),
                                                                 save=True)
        self.public_url = '/{}collections/{}/pointers/{}'.format(API_BASE, self.public_collection._id,
                                                                 self.public_pointer._id)

    def test_deletes_public_collection_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_deletes_public_collection_pointer_logged_in(self):
        res = self.app.delete(self.public_url, auth=self.basic_auth_two, expect_errors=True)
        node_count_before = len(self.public_collection.nodes_pointer)
        assert_equal(res.status_code, 403)
        assert_equal(node_count_before, len(self.public_collection.nodes_pointer))

        res = self.app.delete(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_collection.nodes_pointer))

    def test_deletes_private_collection_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
