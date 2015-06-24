import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth

from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, RegistrationFactory, DashboardFactory, NodeFactory

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
        # TODO include registration drafts!  List all registrations should include drafts as well as reg

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

        # TODO test getting registration details for registration DRAFTS

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

    def test_return_public_registration_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)

        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)
        # TODO assert registration's source?

    def test_return_private_registration_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_details_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration._id)
        assert_equal(res.json['data']['description'], self.private_registration.description)

    def test_return_private_registration_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


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

        #TODO ADD registration drafts to test.  User should only be able to update registration DRAFT, never registration.

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

        self.new_title = "Updated registration title"
        self.new_description = "Updated registration description"
        self.new_category = 'project'

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
        res = self.app.put(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_public_registration_draft_logged_in(self):
        #TODO test updating public registration DRAFT, not registration
        res = self.app.put(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.put(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_out(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.put(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_in_contributor(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.put(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)

    def test_update_private_registration_draft_logged_in_non_contributor(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.put(self.public_url, {
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

        #TODO ADD registration drafts to test.  User should only be able to update registration DRAFT, never registration.

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}'.format(API_BASE, self.private_registration._id)

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
        #TODO test updating public registration DRAFT, not registration
        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_public_registration_draft_logged_in(self):
        #TODO test updating public registration DRAFT, not registration
        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_out(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_contributor(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration._id)

    def test_partial_update_private_registration_draft_logged_in_non_contributor(self):
        #TODO test updating private registration DRAFT, not registration
        res = self.app.patch(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationContributorsList(ApiTestCase):
    #TODO add tests return registration DRAFT contributors
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

    def test_return_public_registration_contributor_list_logged_in(self):
         res = self.app.get(self.public_url, auth=self.basic_auth_two)
         assert_equal(res.status_code, 200)
         assert_equal(len(res.json['data']), 1)
         assert_equal(res.json['data'][0]['id'], self.user._id)

    def test_return_private_registration_contributor_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_contributor_list_logged_in_contributor(self):
        self.private_registration.add_contributor(self.user_two)
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_registration_contributor_list_logged_in_non_contributor(self):
         res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
         assert_equal(res.status_code, 403)


class TestRegistrationChildrenList(ApiTestCase):
    # TODO add tests for registration DRAFTS
    # TODO child id not returning for registration. why?
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
        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_project.save()
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/children/'.format(API_BASE, self.public_registration._id)

        self.private_project = ProjectFactory(creator=self.user, is_public=True)
        self.private_component = NodeFactory(parent=self.private_project, creator=self.user, is_public=False)
        self.private_project.save()
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/children/'.format(API_BASE, self.private_registration._id)

    def test_return_node_children_inside_registration_url(self):
        url = '/{}registrations/{}/children/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_return_public_registration_children_list_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_public_registration_children_list_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_private_registration_children_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.private_component._id)

    def test_return_private_registration_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_registration_children_list_does_not_include_unauthorized_projects(self):
        private_component = NodeFactory(parent=self.private_project)
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)


class TestRegistrationPointersList(ApiTestCase):
    # TODO add tests for registration DRAFTS
    # TODO 500 error being thrown for 1,2,4.
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_pointer(self.private_pointer_project, auth=Auth(self.user))
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.private_registration._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/pointers/'.format(API_BASE, self.public_registration._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

    def test_return_public_registration_pointers_logged_out(self):
        res = self.app.get(self.public_url)
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

    def test_return_private_registration_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_registration_pointers_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['node_id'], self.private_pointer_project._id)

    def test_return_private_registration_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestRegistrationFilesList(ApiTestCase):
    # TODO add tests for registration DRAFTS
    # TODO 500 error being thrown for 1,2,4,6

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

        self.private_project = ProjectFactory(creator=self.user)
        self.private_registration = RegistrationFactory(creator=self.user, project=self.private_project)
        self.private_url = '/{}registrations/{}/files/'.format(API_BASE, self.private_registration._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_url = '/{}registrations/{}/files/'.format(API_BASE, self.public_registration._id)

    def test_returns_registration_public_files_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_private_files_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

    def test_returns_registration_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_registration_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['provider'], 'osfstorage')

        self.private_project.add_addon('github', auth=user_auth)
        self.private_project.save()
        res = self.app.get(self.private_url, auth=self.basic_auth)
        data = res.json['data']
        providers = [item['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)


