import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth

from website.project.model import ensure_schemas
from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, RegistrationFactory, NodeFactory

class TestRegistrationList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)

        self.registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)

        self.project_two = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project_two = RegistrationFactory(creator=self.user, project=self.project_two)
        self.project_two.is_deleted = True
        self.registration_project_two.is_deleted = True
        self.project_two.save()
        self.registration_project_two.save()

        self.project_three = ProjectFactory(is_public=True, creator=self.user_two)
        self.registration_project_three = RegistrationFactory(creator=self.user_two, project=self.project_three)

        self.project_four = ProjectFactory(is_public=False, creator=self.user_two)
        self.registration_project_four = RegistrationFactory(creator=self.user_two, project=self.project_four)

        self.url = '/{}registrations/'.format(API_BASE)

    def test_list_all_registrations(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_not_in(self.registration_project_two._id, ids)
        assert_in(self.registration_project_three._id, ids)
        assert_not_in(self.registration_project_four._id, ids)
        assert_in(self.registration_draft._id, ids)


class TestRegistrationDetail(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

        self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
        self.public_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
        self.private_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.private_registration_draft._id)

    def test_return_registration_detail_node_is_not_registration(self):
        url = '/{}registrations/{}'.format(API_BASE, self.public_project)
        res = self.app.get(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_return_registration_details_node_does_not_exist(self):
        url = '/{}registrations/{}'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_return_public_registration_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)
        # TODO assert registration's source?

    def test_return_public_registration_draft_details_logged_out(self):
        res = self.app.get(self.public_reg_draft_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_draft._id)

    def test_return_public_registration_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)

        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)
        # TODO assert registration's source?

    def test_return_public_registration_draft_details_logged_in(self):
        res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_draft._id)

        res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_draft._id)

    def test_return_private_registration_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_details_logged_out(self):
        res = self.app.get(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_details_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration._id)
        assert_equal(res.json['data']['description'], self.private_registration.description)

    def test_return_private_registration_draft_details_logged_in_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration_draft._id)
        assert_equal(res.json['data']['description'], self.private_registration.description)

    def test_return_private_registration_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

#
# class TestRegistrationCreate(ApiTestCase):
#     def setUp(self):
#         ensure_schemas()
#         ApiTestCase.setUp(self)
#         self.user = UserFactory.build()
#         password = fake.password()
#         self.password = password
#         self.user.set_password(password)
#         self.user.save()
#         self.basic_auth = (self.user.username, password)
#
#         self.user_two = UserFactory.build()
#         self.user_two.set_password(password)
#         self.user_two.save()
#         self.basic_auth_two = (self.user_two.username, password)
#
#         self.public_project = ProjectFactory(creator=self.user, is_public=True)
#         self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
#         self.public_url = '/{}registrations/{}'.format(API_BASE, self.public_registration._id)
#
#         self.private_project = ProjectFactory(creator=self.user, is_private=True)
#         self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
#         self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)
#
#         self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
#         self.public_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.public_registration_draft._id)
#
#         self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
#         self.private_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.private_registration_draft._id)
#
#     def test_create_registration_from_registration_draft(self):
#         res = self.app.post(self.public_reg_draft_url, auth=self.basic_auth, expect_errors=True)
#         print res
#         assert_equal(res.status_code, 201)

    # def test_create_public_registration_logged_out(self):
    #     res = self.app.post(self.public_reg_draft_url, expect_errors=True)
    #     assert_equal(res.status_code, 403)
    #
    # def test_create_public_registration_logged_in(self):
    #     res = self.app.post(self.public_reg_draft_url, auth=self.basic_auth, expect_errors=True)
    #     print res.json['detail'][0]
    #     full_url = res.json["detail"]['data']['url']
    #     path = urlparse(full_url).path
    #     assert_equal(res.status_code, 202)
    #
    #     res = self.app.post(path, auth=self.basic_auth, expect_errors = True)
    #     assert_equal(res.status_code, 201)
    #     assert_equal(res.json["data"]["title"], self.public_registration_project.title)
    #
    #     def test_invalid_token_open_ended_registration(self):
    #     res = self.app.post(self.private_url, self.payload, auth=self.basic_auth, expect_errors=True)
    #     assert_equal(res.status_code, 400)
    #     full_url = self.private_url + "12345/"
    #
    #     res = self.app.post(full_url, self.payload, auth=self.basic_auth, expect_errors = True)
    #     assert_equal(res.status_code, 400)
    #     assert_equal(res.json["non_field_errors"][0], "Incorrect token.")
    #
    # def test_create_open_ended_public_registration_logged_out(self):
    #     res = self.app.post(self.public_url, self.payload, expect_errors=True)
    #     # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
    #     # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
    #     # a little better
    #     assert_equal(res.status_code, 403)
    #
    # def test_create_open_ended_public_registration_logged_in(self):
    #     res = self.app.post(self.public_url, self.payload, auth=self.basic_auth, expect_errors=True)
    #     full_url = res.json["non_field_errors"][1]
    #     path = urlparse(full_url).path
    #     assert_equal(res.status_code, 400)
    #
    #     res = self.app.post(path, self.payload, auth=self.basic_auth, expect_errors = True)
    #     assert_equal(res.status_code, 201)
    #     assert_equal(res.json["data"]["title"], self.public_project.title)
    #
    # def test_create_open_ended_private_registration_logged_out(self):
    #     res = self.app.post(self.private_url, self.payload, expect_errors=True)
    #     # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
    #     # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
    #     # a little better
    #     assert_equal(res.status_code, 403)
    #
    # def test_create_open_ended_private_registration_logged_in_contributor(self):
    #     res = self.app.post(self.private_url, self.payload, auth=self.basic_auth, expect_errors=True)
    #     full_url = res.json["non_field_errors"][1]
    #     path = urlparse(full_url).path
    #     assert_equal(res.status_code, 400)
    #
    #     res = self.app.post(path, self.payload, auth=self.basic_auth, expect_errors = True)
    #     print res
    #     assert_equal(res.status_code, 201)
    #     assert_equal(res.json["data"]["title"], self.private_project.title)
    #
    # def test_create_open_ended_private_registration_logged_in_non_contributor(self):
    #     res = self.app.post(self.private_url, self.payload, auth=self.basic_auth_two, expect_errors=True)
    #     assert_equal(res.status_code, 403)


class TestRegistrationUpdate(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

        self.new_title = "Updated registration title"
        self.new_description = "Updated registration description"
        self.new_category = 'project'

        self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
        self.public_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
        self.private_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.private_registration_draft._id)

    def test_update_node_that_is_not_registration_draft(self):
        url = '/{}registrations/{}'.format(API_BASE, self.private_project)
        res = self.app.put(url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_registration(self):
        res = self.app.put(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_node_that_does_not_exist(self):
        url = '/{}registrations/{}'.format(API_BASE, '12345')
        res = self.app.put(url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_update_public_registration_draft_logged_out(self):
        res = self.app.put(self.public_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_public_registration_draft_logged_in(self):
        res = self.app.put(self.public_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.put(self.public_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_out(self):
        res = self.app.put(self.private_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.put(self.private_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration_draft._id)

    def test_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.put(self.private_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.put(self.private_reg_draft_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationPartialUpdate(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

        self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
        self.public_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
        self.private_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.private_registration_draft._id)

        self.new_title = "Updated registration title"

    def test_partial_update_node_that_is_not_registration_draft(self):
        url = '/{}registrations/{}'.format(API_BASE, self.private_project)
        res = self.app.patch(url, {
            'title': self.new_title,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_registration(self):
        res = self.app.patch(self.private_url, {
            'title': self.new_title,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_node_that_does_not_exist(self):
        url = '/{}registrations/{}'.format(API_BASE, '12345')
        res = self.app.patch(url, {
            'title': self.new_title,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_partial_update_public_registration_draft_logged_out(self):
        res = self.app.patch(self.public_reg_draft_url, {
            'title': self.new_title,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_public_registration_draft_logged_in(self):
        res = self.app.patch(self.public_reg_draft_url, {
            'title': self.new_title,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_draft._id)

        res = self.app.patch(self.public_reg_draft_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_out(self):
        res = self.app.patch(self.private_reg_draft_url, {
            'title': self.new_title,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.patch(self.private_reg_draft_url, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration_draft._id)

    def test_partial_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.patch(self.private_reg_draft_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.patch(self.private_reg_draft_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationDelete(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

        self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
        self.public_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
        self.private_reg_draft_url = '/{}registrations/{}'.format(API_BASE, self.private_registration_draft._id)

    def test_delete_node_that_is_not_registration_draft(self):
        url = '/{}registrations/{}'.format(API_BASE, self.private_project)
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_delete_registration(self):
        res = self.app.delete(self.private_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_node_that_does_not_exist(self):
        url = '/{}registrations/{}'.format(API_BASE, '12345')
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_public_registration_draft_logged_out(self):
        res = self.app.delete(self.public_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_public_registration_draft_logged_in(self):
        res = self.app.patch(self.public_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_equal(self.public_registration_draft.is_deleted, False)
        res = self.app.delete(self.public_reg_draft_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 204)
        assert_equal(self.public_registration_draft.is_deleted, True)

    def test_delete_private_registration_draft_logged_out(self):
        res = self.app.delete(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_contributor(self):
        assert_equal(self.private_registration_draft.is_deleted, False)
        res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        assert_equal(self.private_registration_draft.is_deleted, True)

    def test_delete_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationContributorsList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(self.password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, self.password)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/contributors/'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/contributors/'.format(API_BASE, self.private_registration._id)

        self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
        self.public_reg_draft_url = '/{}registrations/{}/contributors/'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
        self.private_reg_draft_url = '/{}registrations/{}/contributors/'.format(API_BASE, self.private_registration_draft._id)


    def test_return_non_registration_contributor_list(self):
        url = '/{}registrations/{}/contributors/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_return_fake_node_contributor_list(self):
        url = '/{}/registrations/{}/contributors/'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_return_public_registration_contributor_list_logged_out(self):
        self.public_registration.add_contributor(self.user_two)
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_public_registration_draft_contributor_list_logged_out(self):
        self.public_registration_draft.add_contributor(self.user_two)
        res = self.app.get(self.public_reg_draft_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_public_registration_contributor_list_logged_in(self):
         res = self.app.get(self.public_url, auth=self.basic_auth_two)
         assert_equal(res.status_code, 200)
         assert_equal(len(res.json['data']), 1)
         assert_equal(res.json['data'][0]['id'], self.user._id)

    def test_return_public_registration_draft_contributor_list_logged_in(self):
         res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth_two)
         assert_equal(res.status_code, 200)
         assert_equal(len(res.json['data']), 1)
         assert_equal(res.json['data'][0]['id'], self.user._id)

    def test_return_private_registration_contributor_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_contributor_list_logged_out(self):
        res = self.app.get(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_contributor_list_logged_in_contributor(self):
        self.private_registration.add_contributor(self.user_two)
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_registration_draft_contributor_list_logged_in_contributor(self):
        self.private_registration_draft.add_contributor(self.user_two)
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_registration_contributor_list_logged_in_non_contributor(self):
         res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
         assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_contributor_list_logged_in_non_contributor(self):
         res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
         assert_equal(res.status_code, 403)


class TestRegistrationChildrenList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_component = NodeFactory(title='public child', parent=self.public_project, creator=self.user, is_public=True)
        self.public_project.save()
        self.public_project_url = '/{}registrations/{}/children/'.format(API_BASE, self.public_project._id)

        self.public_registration = RegistrationFactory(project=self.public_project, creator=self.user, is_public=True)
        self.public_registration_url = '/{}registrations/{}/children/'.format(API_BASE, self.public_registration._id)

        self.public_registration_draft = NodeFactory(is_registration_draft=True, creator=self.user, is_public=True)
        self.public_reg_draft_component = NodeFactory(parent=self.public_registration_draft, creator=self.user, is_public=True)
        self.public_registration_draft.save()
        self.public_reg_draft_url = '/{}registrations/{}/children/'.format(API_BASE, self.public_registration_draft._id)

        self.private_project = ProjectFactory(creator=self.user)
        self.private_component = NodeFactory(parent=self.private_project, creator=self.user)
        self.private_project.save()

        self.private_registration = RegistrationFactory(project=self.private_project, creator=self.user)
        self.private_registration_url = '/{}registrations/{}/children/'.format(API_BASE, self.private_registration._id)

        self.private_registration_draft = NodeFactory(is_registration_draft=True, creator=self.user)
        self.private_reg_draft_component = NodeFactory(parent=self.private_registration_draft, creator=self.user)
        self.private_reg_draft_url = '/{}registrations/{}/children/'.format(API_BASE, self.private_registration_draft._id)

    def test_return_non_registration_node_children(self):
        res = self.app.get(self.public_project_url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_return_public_registration_children_list_logged_out(self):
        res = self.app.get(self.public_registration_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['title'], self.public_component.title)

    def test_return_public_registration_draft_children_list_logged_out(self):
        res = self.app.get(self.public_reg_draft_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['title'], self.public_reg_draft_component.title)

    def test_return_public_registration_children_list_logged_in(self):
        res = self.app.get(self.public_registration_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['title'], self.public_component.title)

    def test_return_public_registration_draft_children_list_logged_in(self):
        res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['title'], self.public_reg_draft_component.title)

    def test_return_private_registration_children_list_logged_out(self):
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_children_list_logged_out(self):
        res = self.app.get(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_registration_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['category'], self.private_component.category)

    def test_return_private_registration_draft_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['category'], self.private_reg_draft_component.category)

    def test_return_private_registration_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_registration_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationPointersList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.public_registration._id)

        self.public_registration_draft = ProjectFactory(is_public=True, creator=self.user, is_registration_draft=True)
        self.public_registration_draft.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_reg_draft_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.public_registration_draft._id)

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_pointer(self.private_pointer_project, auth=Auth(self.user))
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.private_registration._id)

        self.private_registration_draft = NodeFactory(is_registration_draft=True, creator=self.user)
        self.private_registration_draft.add_pointer(self.private_pointer_project, auth=Auth(self.user))
        self.private_reg_draft_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.private_registration_draft._id)

    def test_return_non_registration_node_pointers(self):
        url = '/{}registrations/{}/pointers/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_return_public_registration_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_public_registration_draft_pointers_logged_out(self):
        res = self.app.get(self.public_reg_draft_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_public_registration_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_public_registration_draft_pointers_logged_in(self):
        res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_private_registration_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_draft_pointers_logged_out(self):
        res = self.app.get(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_pointers_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['node_id'], self.private_pointer_project._id)

    def test_return_private_registration_pointers_draft_logged_in_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['node_id'], self.private_pointer_project._id)

    def test_return_private_registration_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_pointers_draft_logged_in_non_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationFilesList(ApiTestCase):
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

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/files/'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/files/'.format(API_BASE, self.private_registration._id)

        self.public_registration_draft = ProjectFactory(is_public=True, creator=self.user, is_registration_draft=True)
        self.public_reg_draft_url = '/{}registrations/{}/files/'.format(API_BASE, self.public_registration_draft._id)

        self.private_registration_draft = NodeFactory(is_registration_draft=True, creator=self.user)
        self.private_reg_draft_url = '/{}registrations/{}/files/'.format(API_BASE, self.private_registration_draft._id)

    def test_returns_non_registration_files(self):
        url = '/{}registrations/{}/files/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_returns_registration_public_files_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_draft_public_files_logged_out(self):
        res = self.app.get(self.public_reg_draft_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_draft_public_files_logged_in(self):
        res = self.app.get(self.public_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_private_files_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_draft_private_files_logged_out(self):
        res = self.app.get(self.private_reg_draft_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_draft_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_draft_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

        self.private_registration.add_addon('github', auth=user_auth)
        self.private_registration.save()
        res = self.app.get(self.private_url, auth=self.basic_auth)
        data = res.json['data']
        providers = [item['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)

    def test_returns_registration_draft_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

        self.private_registration_draft.add_addon('github', auth=user_auth)
        self.private_registration_draft.save()
        res = self.app.get(self.private_reg_draft_url, auth=self.basic_auth)
        data = res.json['data']
        providers = [item['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)



