import mock
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from website.project.model import ensure_schemas
from tests.factories import UserFactory, ProjectFactory, RegistrationFactory, NodeFactory, DraftRegistrationFactory

class TestDraftRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestDraftRegistrationList, self).setUp()
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
        self.public_draft = DraftRegistrationFactory(branched_from=self.public_project, initiator=self.user)

        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.private_draft = DraftRegistrationFactory(branched_from=self.private_project, initiator=self.user)

        self.url = '/{}draft_registrations/'.format(API_BASE)

    def test_return_draft_registration_list_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_draft_registration_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

    def test_return_draft_registration_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.basic_auth_two)
        assert_equal(len(res.json['data']), 0)
        assert_equal(res.status_code, 200)


# class TestRegistrationCreate(ApiTestCase):
#     def setUp(self):
#         ensure_schemas()
#         super(TestRegistrationCreate, self).setUp()
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
#         self.public_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration._id)
#
#         self.private_project = ProjectFactory(creator=self.user, is_private=True)
#         self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
#         self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)
#
#         self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
#         self.public_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration_draft._id)
#
#         self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
#         self.private_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration_draft._id)
#
#     def test_create_registration_from_registration(self):
#         res = self.app.post(self.public_url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_create_registration_from_node(self):
#         url = '/{}registrations/{}/'.format(API_BASE, self.public_project._id)
#         res = self.app.post(url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 400)
#
#     def test_create_registration_from_fake_node(self):
#         url = '/{}registrations/{}/'.format(API_BASE, '12345')
#         res = self.app.post(url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 404)
#
#     def test_create_public_registration_logged_out(self):
#         res = self.app.post(self.public_reg_draft_url, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_create_public_registration_logged_in(self):
#         res = self.app.post(self.public_reg_draft_url, auth=self.basic_auth, expect_errors=True)
#         token_url = res.json['data']['links']['confirm_delete']
#         assert_equal(res.status_code, 202)
#
#         assert_equal(self.public_registration_draft.is_registration, False)
#         res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
#         assert_equal(res.status_code, 201)
#         assert_equal(res.json['data']['title'], self.public_registration_draft.title)
#         assert_equal(res.json['data']['properties']['registration'], True)
#
#     def test_invalid_token_create_registration(self):
#         res = self.app.post(self.private_reg_draft_url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 202)
#         token_url = self.private_reg_draft_url + "freeze/12345/"
#
#         res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
#         assert_equal(res.status_code, 400)
#         assert_equal(res.json["non_field_errors"][0], "Incorrect token.")
#
#     def test_create_private_registration_logged_out(self):
#         res = self.app.post(self.private_reg_draft_url, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_create_private_registration_logged_in_contributor(self):
#         res = self.app.post(self.private_reg_draft_url, auth=self.basic_auth, expect_errors=True)
#         token_url = res.json['data']['links']['confirm_delete']
#         assert_equal(res.status_code, 202)
#
#         assert_equal(self.private_registration_draft.is_registration, False)
#         res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
#         assert_equal(res.status_code, 201)
#         assert_equal(res.json['data']['title'], self.private_registration_draft.title)
#         assert_equal(res.json['data']['properties']['registration'], True)
#
#     def test_create_private_registration_logged_in_non_contributor(self):
#         res = self.app.post(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_create_private_registration_logged_in_read_only_contributor(self):
#         self.private_registration_draft.add_contributor(self.user_two, permissions = ['read'])
#         res = self.app.post(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#
# class TestRegistrationUpdate(ApiTestCase):
#
#     def setUp(self):
#         super(TestRegistrationUpdate, self).setUp()
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
#         self.private_project = ProjectFactory(creator=self.user, is_private=True)
#         self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
#         self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)
#
#         self.new_title = "Updated registration title"
#         self.new_description = "Updated registration description"
#         self.new_category = 'project'
#
#         self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
#         self.public_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration_draft._id)
#
#         self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
#         self.private_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration_draft._id)
#
#     def test_update_node_that_is_not_registration_draft(self):
#         url = '/{}registrations/{}/'.format(API_BASE, self.private_project)
#         res = self.app.put(url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 400)
#
#     def test_update_registration(self):
#         res = self.app.put(self.private_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_update_node_that_does_not_exist(self):
#         url = '/{}registrations/{}/'.format(API_BASE, '12345')
#         res = self.app.put(url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 404)
#
#     def test_update_public_registration_draft_logged_out(self):
#         res = self.app.put(self.public_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_update_public_registration_draft_logged_in(self):
#         res = self.app.put(self.public_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 200)
#
#         res = self.app.put(self.public_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_update_private_registration_draft_logged_out(self):
#         res = self.app.put(self.private_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_update_private_registration_draft_logged_in_contributor(self):
#         res = self.app.put(self.private_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth)
#         assert_equal(res.status_code, 200)
#         assert_equal(res.json['data']['id'], self.private_registration_draft._id)
#
#     def test_update_private_registration_draft_logged_in_non_contributor(self):
#         res = self.app.put(self.private_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
#         self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
#         res = self.app.put(self.private_reg_draft_url, {
#             'title': self.new_title,
#             'description': self.new_description,
#             'category': self.new_category,
#             'public': False,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#
# class TestRegistrationPartialUpdate(ApiTestCase):
#
#     def setUp(self):
#         super(TestRegistrationPartialUpdate, self).setUp()
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
#         self.private_project = ProjectFactory(creator=self.user, is_private=True)
#         self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
#         self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)
#
#         self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
#         self.public_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration_draft._id)
#
#         self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
#         self.private_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration_draft._id)
#
#         self.new_title = "Updated registration title"
#
#     def test_partial_update_node_that_is_not_registration_draft(self):
#         url = '/{}registrations/{}/'.format(API_BASE, self.private_project)
#         res = self.app.patch(url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 400)
#
#     def test_partial_update_registration(self):
#         res = self.app.patch(self.private_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_node_that_does_not_exist(self):
#         url = '/{}registrations/{}/'.format(API_BASE, '12345')
#         res = self.app.patch(url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 404)
#
#     def test_partial_update_public_registration_draft_logged_out(self):
#         res = self.app.patch(self.public_reg_draft_url, {
#             'title': self.new_title,
#         }, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_public_registration_draft_logged_in(self):
#         res = self.app.patch(self.public_reg_draft_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 200)
#         assert_equal(res.json['data']['id'], self.public_registration_draft._id)
#
#         res = self.app.patch(self.public_reg_draft_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_private_registration_draft_logged_out(self):
#         res = self.app.patch(self.private_reg_draft_url, {
#             'title': self.new_title,
#         }, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_private_registration_draft_logged_in_contributor(self):
#         res = self.app.patch(self.private_reg_draft_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth)
#         assert_equal(res.status_code, 200)
#         assert_equal(res.json['data']['id'], self.private_registration_draft._id)
#
#     def test_partial_update_private_registration_draft_logged_in_non_contributor(self):
#         res = self.app.patch(self.private_reg_draft_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
#         self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
#         res = self.app.patch(self.private_reg_draft_url, {
#             'title': self.new_title,
#         }, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#
# class TestRegistrationDelete(ApiTestCase):
#
#     def setUp(self):
#         super(TestRegistrationDelete, self).setUp()
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
#         self.private_project = ProjectFactory(creator=self.user, is_private=True)
#         self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
#         self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)
#
#         self.public_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True, is_public=True)
#         self.public_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration_draft._id)
#
#         self.private_registration_draft = NodeFactory(creator=self.user, is_registration_draft=True)
#         self.private_reg_draft_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration_draft._id)
#
#     def test_delete_node_that_is_not_registration_draft(self):
#         url = '/{}registrations/{}/'.format(API_BASE, self.private_project)
#         res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 400)
#
#     def test_delete_registration(self):
#         res = self.app.delete(self.private_url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_delete_node_that_does_not_exist(self):
#         url = '/{}registrations/{}/'.format(API_BASE, '12345')
#         res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 404)
#
#     def test_delete_public_registration_draft_logged_out(self):
#         res = self.app.delete(self.public_reg_draft_url, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_delete_public_registration_draft_logged_in(self):
#         res = self.app.patch(self.public_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#         assert_equal(self.public_registration_draft.is_deleted, False)
#         res = self.app.delete(self.public_reg_draft_url, auth=self.basic_auth, expect_errors=True)
#         assert_equal(res.status_code, 204)
#         assert_equal(self.public_registration_draft.is_deleted, True)
#
#     def test_delete_private_registration_draft_logged_out(self):
#         res = self.app.delete(self.private_reg_draft_url, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_delete_private_registration_draft_logged_in_contributor(self):
#         assert_equal(self.private_registration_draft.is_deleted, False)
#         res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth)
#         assert_equal(res.status_code, 204)
#         assert_equal(self.private_registration_draft.is_deleted, True)
#
#     def test_delete_private_registration_draft_logged_in_non_contributor(self):
#         res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#     def test_delete_private_registration_draft_logged_in_read_only_contributor(self):
#         self.private_registration_draft.add_contributor(self.user_two, permissions=['read'])
#         res = self.app.delete(self.private_reg_draft_url, auth=self.basic_auth_two, expect_errors=True)
#         assert_equal(res.status_code, 403)
#
#
#



