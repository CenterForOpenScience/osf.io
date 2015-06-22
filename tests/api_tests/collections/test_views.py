# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, FolderFactory, DashboardFactory, NodeFactory


class TestCollectionsList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.deleted = FolderFactory(is_deleted=True, creator=self.user)
        self.collection = FolderFactory(creator=self.user)
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

    def test_return_403_for_logged_out_user(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equals(res.status_code, 403)

    def tearDown(self):
        ApiTestCase.tearDown(self)
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
        self.collection_one = FolderFactory(title="Collection One", creator=self.user_one)
        self.collection_two = FolderFactory(title="Collection Two", creator=self.user_one)
        self.collection_three = FolderFactory(title="Three", creator=self.user_one)
        self.collection_four = FolderFactory(title="Collection User One", creator=self.user_one)
        self.collection_five = FolderFactory(title="Collection User Two", creator=self.user_two)
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
        assert_in(self.collection_four._id, ids)
        assert_not_in(self.collection_five._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_collection_with_exact_filter_logged_in(self):
        url = "/{}collections/?filter[title]=Collection%20One".format(API_BASE)

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_not_in(self.collection_four._id, ids)
        assert_not_in(self.collection_five._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_collections_with_substring_logged_in(self):
        url = "/{}collections/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_not_in(self.collection_four._id, ids)
        assert_not_in(self.collection_five._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_my_collections_with_filter_logged_in(self):
        url = "/{}collections/?filter[title]=Collection".format(API_BASE)

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)
        assert_in(self.collection_four._id, ids)
        assert_not_in(self.collection_five._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/{}collections/?filter[notafield]=bogus".format(API_BASE)

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [node['id'] for node in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_in(self.collection_three._id, ids)
        assert_in(self.collection_four._id, ids)
        assert_not_in(self.collection_five._id, ids)
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

        self.collection_one = {'title': self.title}
        self.collection_two = {'title': self.title}

    def test_not_creates_collection_logged_out(self):
        res = self.app.post_json(self.url, self.collection_one, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_collection_logged_in(self):
        res = self.app.post_json(self.url, self.collection_one, auth=self.basic_auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.collection_one['title'])

    def test_creates_collection_logged_in_two(self):
        res = self.app.post_json(self.url, self.collection_two, auth=self.basic_auth_two)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.collection_two['title'])

    def test_creates_collection_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'

        res = self.app.post_json(self.url, {
            'title': title,
        }, auth=self.basic_auth)
        collection_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/{}collections/{}/'.format(API_BASE, collection_id)
        res = self.app.get(url, auth=self.basic_auth)
        assert_equal(res.json['data']['title'], strip_html(title))


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

        self.collection_one = FolderFactory(title="Project One", creator=self.user)
        self.collection_two = FolderFactory(title="Project Two")
        self.url_one = '/{}collections/{}/'.format(API_BASE, self.collection_one._id)
        self.url_two = '/{}collections/{}/'.format(API_BASE, self.collection_two._id)

    def test_return_403_collection_details_logged_out(self):
        res = self.app.get(self.url_one, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_collection_details_logged_in(self):
        res = self.app.get(self.url_one, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.collection_one.title)


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

        self.collection_one = FolderFactory(title=self.title, creator=self.user)
        self.url_one = '/{}collections/{}/'.format(API_BASE, self.collection_one._id)

        self.collection_two = FolderFactory(title=self.title)
        self.url_two = '/{}collections/{}/'.format(API_BASE, self.collection_two._id, creator=self.user_two)

    def test_update_collection_logged_in(self):
        res = self.app.put_json(self.url_one, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

    def test_update_collection_logged_out(self):
        res = self.app.put_json(self.url_two, {
            'title': self.new_title,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_collection_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        collection = self.collection = FolderFactory(
            title=self.title, creator=self.user)

        url = '/{}collections/{}/'.format(API_BASE, collection._id)
        res = self.app.put_json(url, {
            'title': new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_partial_update_collection_updates_collection_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> collection'
        collection = self.collection = FolderFactory(
            title=self.title, creator=self.user)

        url = '/{}collections/{}/'.format(API_BASE, collection._id)
        res = self.app.patch_json(url, {
            'title': new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_partial_update_collection_logged_out(self):
        res = self.app.patch_json(self.url_two, {'title': self.new_title}, expect_errors=True, auth=self.user)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_partial_update_collection_logged_in(self):
        res = self.app.patch_json(self.url_two, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)


class TestCollectionChildrenList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)
        self.collection_one = FolderFactory()
        self.collection_one.add_contributor(self.user, permissions=['read', 'write'])
        self.collection_one.save()
        self.component = NodeFactory(parent=self.collection_one, creator=self.user)
        self.pointer = FolderFactory()
        self.collection_one.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.collection_one_url = '/{}collections/{}/children/'.format(API_BASE, self.collection_one._id)

        self.collection_two = FolderFactory(creator=self.user)
        self.collection_two.save()
        self.node_of_collection_two = NodeFactory(parent=self.collection_two, creator=self.user)
        self.collection_two_url = '/{}collections/{}/children/'.format(API_BASE, self.collection_two._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.dashboard_folder = DashboardFactory(creator=self.user)
        self.dashboard_children_url = '/{}collections/{}/children/'.format(API_BASE, self.dashboard_folder._id)
        self.dash_child = FolderFactory(parent=self.dashboard_folder, creator=self.user)
        self.dash_child2 = FolderFactory(parent=self.dashboard_folder, creator=self.user)

    def test_collection_children_list_does_not_include_pointers(self):
        res = self.app.get(self.collection_one_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)

    def test_not_return_collection_children_list_logged_out(self):
        res = self.app.get(self.collection_two_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_collection_children_list_logged_in(self):
        res = self.app.get(self.collection_two_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.node_of_collection_two._id)

    def test_return_collection_children_list_logged_out(self):
        res = self.app.get(self.collection_one_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_return_collection_children_list_logged_in_different_user(self):
        res = self.app.get(self.collection_one_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_smart_folders_in_dashboard_children(self):
        res = self.app.get(self.dashboard_children_url, auth=self.basic_auth)
        res_json = res.json['data']

        titles = [node['title'] for node in res_json]
        assert_equal(res.status_code, 200)
        assert_in('Smart Folder amr', titles)
        assert_in('Smart Folder amp', titles)

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()


class TestCollectionPointersList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')

        self.collection_one = FolderFactory(creator=self.user)
        self.collection_being_pointed_to = FolderFactory(creator=self.user)
        self.collection_one.add_pointer(self.collection_being_pointed_to, auth=Auth(self.user))
        self.collection_one_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_one._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()

        self.basic_auth_two = (self.user_two.username, 'password')
        self.collection_two = FolderFactory(creator=self.user_two)
        self.collection_being_pointed_to_two = FolderFactory(creator=self.user_two)
        self.collection_two.add_pointer(self.collection_being_pointed_to_two, auth=Auth(self.user_two))
        self.collection_two_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_two._id)

    def test_not_return_collection_pointers_logged_out(self):
        res = self.app.get(self.collection_two_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_collection_pointers_logged_in(self):
        res = self.app.get(self.collection_two_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['collection_id'], self.collection_being_pointed_to_two._id)

    def test_smart_folders_return_correctly(self):
        pass


class TestCreateCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')

        self.collection_one = FolderFactory(creator=self.user)
        self.collection_being_pointed_to = FolderFactory(creator=self.user)
        self.collection_one.add_pointer(self.collection_being_pointed_to, auth=Auth(self.user))
        self.collection_one_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_one._id)
        self.payload_one = {'collection_id': self.collection_one._id}

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.collection_two = FolderFactory(creator=self.user_two)
        self.collection_being_pointed_to_two = FolderFactory(creator=self.user_two)
        self.collection_two.add_pointer(self.collection_being_pointed_to_two, auth=Auth(self.user_two))
        self.collection_two_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_two._id)
        self.payload_two = {'collection_id': self.collection_two._id}

        self.smart_folder_amp = FolderFactory(_id="amp", creator=self.user)
        self.smart_folder_amr = FolderFactory(_id="amr", creator=self.user)
        self.smart_folder_amp_url = '/{}collections/amp/pointers/'.format(API_BASE)
        self.smart_folder_amr_url = '/{}collections/amr/pointers/'.format(API_BASE)

    def test_not_creates_collection_pointer_not_creator(self):
        res = self.app.post(self.collection_two_url, self.payload_two, expect_errors=True, auth=self.basic_auth)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_collection_pointer_logged_in(self):
        res = self.app.post(self.collection_two_url, self.payload_two, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 201)

        res = self.app.post(self.collection_one_url, self.payload_one, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['collection_id'], self.collection_one._id)

    def test_not_creates_collection_pointer_logged_out(self):
        res = self.app.post(self.collection_one_url, self.payload_one, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_return_smart_folder_info(self):
        res = self.app.get(self.smart_folder_amp_url, auth=self.basic_auth)
        res_json = res.json['data']

        assert_equal(res.status_code, 200)


class TestCollectionPointerDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.collection_one = FolderFactory(creator=self.user)
        self.collection_being_pointed_to = FolderFactory(creator=self.user)
        self.pointer_one = self.collection_one.add_pointer(self.collection_being_pointed_to, auth=Auth(self.user),
                                                           save=True)
        self.collection_one_url = '/{}collections/{}/pointers/{}/'.format(API_BASE, self.collection_one._id,
                                                                          self.pointer_one._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.collection_two = FolderFactory(creator=self.user_two)
        self.collection_being_pointed_to_two = FolderFactory(creator=self.user_two)
        self.pointer_two = self.collection_two.add_pointer(self.collection_being_pointed_to_two,
                                                           auth=Auth(self.user_two),
                                                           save=True)
        self.collection_two_url = '/{}collections/{}/pointers/{}/'.format(API_BASE, self.collection_two._id,
                                                                          self.pointer_two._id)

        self.collection_five = FolderFactory()

        self.non_folder_url = '/{}collections/{}/pointers/'.format(API_BASE, self.collection_one._id)

    def test_not_returns_collection_pointer_detail_logged_out(self):
        res = self.app.get(self.collection_two_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_collection_pointer_detail_logged_in(self):
        res = self.app.get(self.collection_two_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res_json['collection_id'], self.pointer_two._id)

    def test_not_returns_collection_pointer_detail_logged_out_two(self):
        res = self.app.get(self.collection_one_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_return_collection_pointers_from_non_folder(self):
        self.collection_five.add_pointer(self.collection_two, auth=Auth(self.user))
        res = self.app.get(self.non_folder_url, expect_errors=True)
        assert_equal(res.status_code, 403)
        # pointers = res.json
        # assert_equal(len(pointers), 0)


class TestDeleteCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')

        self.collection_one = FolderFactory(creator=self.user)
        self.collection_being_pointed_to = FolderFactory(creator=self.user)
        self.pointer_one = self.collection_one.add_pointer(self.collection_being_pointed_to, auth=Auth(self.user),
                                                           save=True)
        self.pointer_one_url = '/{}collections/{}/pointers/{}/'.format(API_BASE, self.collection_one._id,
                                                                       self.pointer_one._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.collection_two = FolderFactory(creator=self.user)
        self.collection_being_pointed_to_two = FolderFactory(creator=self.user)
        self.pointer_two = self.collection_two.add_pointer(self.collection_being_pointed_to_two, auth=Auth(self.user),
                                                           save=True)
        self.pointer_two_url = '/{}collections/{}/pointers/{}/'.format(API_BASE, self.collection_two._id,
                                                                       self.pointer_two._id)

    def test_not_deletes_collection_pointer_logged_out(self):
        res = self.app.delete(self.pointer_two_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_deletes_collection_pointer_logged_in(self):
        res = self.app.delete(self.pointer_two_url, auth=self.basic_auth_two, expect_errors=True)
        node_count_before = len(self.collection_two.nodes_pointer)
        assert_equal(res.status_code, 403)
        assert_equal(node_count_before, len(self.collection_two.nodes_pointer))

        res = self.app.delete(self.pointer_one_url, auth=self.basic_auth, expect_errors=True)
        node_count_before_two = len(self.collection_one.nodes_pointer)
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before_two, 0)
