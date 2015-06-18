# -*- coding: utf-8 -*-
import copy

from nose.tools import *  # flake8: noqa

from website.models import Node, ApiOAuth2Application, User
from website.util import api_v2_url

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2ApplicationFactory, DashboardFactory, FolderFactory,  ProjectFactory, UserFactory

from api.base.settings.defaults import API_BASE


def _get_application_detail_route(app):
    path = "/users/{}/applications/{}/".format(app.owner._id, app.client_id)
    return api_v2_url(path, base_route='')


def _get_application_list_url(user):
    path = "/users/{}/applications/".format(user._id)
    return api_v2_url(path, base_route='')


class TestUsers(ApiTestCase):

    def setUp(self):
        super(TestUsers, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.save()
        self.user_two = UserFactory.build()
        self.user_two.save()

    def tearDown(self):
        super(TestUsers, self).tearDown()
        Node.remove()

    def test_returns_200(self):
        res = self.app.get('/{}users/'.format(API_BASE))
        assert_equal(res.status_code, 200)

    def test_find_user_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/{}users/?filter[fullname]=fred".format(API_BASE)

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/{}users/?filter[fullname]=my".format(API_BASE)
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/{}users/?filter[fullname]=NotMyMom".format(API_BASE)
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)


class TestUserDetail(ApiTestCase):

    def setUp(self):
        super(TestUserDetail, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        super(TestUserDetail, self).tearDown()
        Node.remove()

    def test_gets_200(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_correct_pk_user(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['social_accounts']['twitter'], 'howtopizza')

    def test_get_incorrect_pk_user_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)

    def test_get_incorrect_pk_user_not_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['fullname'], self.user_two.fullname)


class TestUserNodes(ApiTestCase):

    def setUp(self):
        super(TestUserNodes, self).setUp()
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.public_project_user_one = ProjectFactory(title="Public Project User One",
                                                      is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False, creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two",
                                                      is_public=True, creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False, creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One",
                                                      is_public=False, creator=self.user_one, is_deleted=True)
        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One",
                                            is_public=False, creator=self.user_one, is_deleted=True)
        self.dashboard = DashboardFactory()

    def tearDown(self):
        super(TestUserNodes, self).tearDown()
        Node.remove()

    def test_authorized_in_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_anonymous_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_projects_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

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

    def test_get_projects_logged_in_as_different_user(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_two._id, ids)
        assert_not_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)


class TestApplicationList(ApiTestCase):
    def setUp(self):
        super(TestApplicationList, self).setUp()

        fake_pwd = '112358'
        self.user1 = UserFactory.build()
        self.user1.set_password(fake_pwd)
        self.user1.save()
        self.basic_auth1 = (self.user1.username, fake_pwd)

        self.user2 = UserFactory.build()
        self.user2.set_password(fake_pwd)
        self.user2.save()
        self.basic_auth2 = (self.user2.username, fake_pwd)

        self.user1_apps = [ApiOAuth2ApplicationFactory(owner=self.user1) for i in xrange(3)]
        self.user2_apps = [ApiOAuth2ApplicationFactory(owner=self.user2) for i in xrange(2)]

        self.user1_list_url = _get_application_list_url(self.user1)
        self.user2_list_url = _get_application_list_url(self.user2)

        self.sample_data = {'client_id': 'Value discarded',
                            'client_secret': 'Value discarded',
                            'name': 'A shiny new application',
                            'description': "It's really quite shiny",
                            'home_url': 'http://osf.io',
                            'callback_url': 'https://cos.io'}

    def test_user1_should_see_only_their_applications(self):
        res = self.app.get(self.user1_list_url, auth=self.basic_auth1)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps))

    def test_user2_should_see_only_their_applications(self):
        res = self.app.get(self.user2_list_url, auth=self.basic_auth2)
        assert_equal(len(res.json['data']),
                     len(self.user2_apps))

    def test_deleting_application_should_hide_it_from_api_list(self):
        app = self.user1_apps[0]
        url = _get_application_detail_route(app)

        res = self.app.delete(url, auth=self.basic_auth1)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.user1_list_url, auth=self.basic_auth1)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps) - 1)

    def test_created_applications_are_tied_to_request_user_with_data_specified(self):
        res = self.app.post(self.user1_list_url, self.sample_data, auth=self.basic_auth1)

        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['owner'], self.user1._id)

        # Some fields aren't writable; make sure user can't set these
        assert_not_equal(res.json['data']['client_id'],
                         self.sample_data['client_id'])
        assert_not_equal(res.json['data']['client_secret'],
                         self.sample_data['client_secret'])

    def test_creating_application_fails_if_callbackurl_fails_validation(self):
        data = copy.copy(self.sample_data)
        data['callback_url'] = "itunes:///invalid_url_of_doom"
        res = self.app.post(self.user1_list_url, data,
                            auth=self.basic_auth1, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_created_applications_show_up_in_api_list(self):
        res = self.app.post(self.user1_list_url, self.sample_data, auth=self.basic_auth1)
        assert_equal(res.status_code, 201)

        res = self.app.get(self.user1_list_url, auth=self.basic_auth1)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps) + 1)

    def test_returns_403_when_not_logged_in(self):
        res = self.app.get(self.user1_list_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def tearDown(self):
        super(TestApplicationList, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()


class TestApplicationDetail(ApiTestCase):
    def setUp(self):
        super(TestApplicationDetail, self).setUp()

        fake_pwd = '112358'
        self.user1 = UserFactory.build()
        self.user1.set_password(fake_pwd)
        self.user1.save()
        self.basic_auth1 = (self.user1.username, fake_pwd)

        self.user2 = UserFactory.build()
        self.user2.set_password(fake_pwd)
        self.user2.save()
        self.basic_auth2 = (self.user2.username, fake_pwd)

        self.user1_app = ApiOAuth2ApplicationFactory(owner=self.user1)
        self.user1_app_url = _get_application_detail_route(self.user1_app)

    def test_owner_can_view(self):
        res = self.app.get(self.user1_app_url, auth=self.basic_auth1)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['client_id'], self.user1_app.client_id)

    def test_non_owner_cant_view(self):
        res = self.app.get(self.user1_app_url, auth=self.basic_auth2, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_403_when_not_logged_in(self):
        res = self.app.get(self.user1_app_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_owner_can_delete(self):
        res = self.app.delete(self.user1_app_url, auth=self.basic_auth1)
        assert_equal(res.status_code, 204)

    def test_non_owner_cant_delete(self):
        res = self.app.delete(self.user1_app_url,
                              auth=self.basic_auth2,
                              expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_deleting_application_makes_api_view_inaccessible(self):
        res = self.app.delete(self.user1_app_url, auth=self.basic_auth1)
        res = self.app.get(self.user1_app_url, auth=self.basic_auth1, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_updating_one_field_should_not_blank_others_on_patch_update(self):
        app = self.user1_app
        new_name = "The instance formerly known as Prince"
        res = self.app.patch(self.user1_app_url,
                             {"name": new_name},
                             auth=self.basic_auth1)

        assert_equal(res.status_code, 200)
        assert_dict_contains_subset({'client_id': app.client_id,
                                     'client_secret': app.client_secret,
                                     'owner': app.owner._id,
                                     'name': new_name,
                                     'description': app.description,
                                     'home_url': app.home_url,
                                     'callback_url': app.callback_url
                                     },
                                    res.json['data'])

    def test_updating_an_instance_does_not_change_the_number_of_instances(self):
        new_name = "The instance formerly known as Prince"
        res = self.app.patch(self.user1_app_url,
                             {"name": new_name},
                             auth=self.basic_auth1)
        assert_equal(res.status_code, 200)

        list_url = _get_application_list_url(self.user1)
        res = self.app.get(list_url, auth=self.basic_auth1)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     1)

    def test_deleting_application_flags_instance_inactive(self):
        res = self.app.delete(self.user1_app_url, auth=self.basic_auth1)
        # TODO: Will DB instance always be updated with newest result from API modification
        assert_false(self.user1_app.active)

    def tearDown(self):
        super(TestApplicationDetail, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()
