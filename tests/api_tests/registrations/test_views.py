import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from website.project.model import ensure_schemas
from tests.factories import UserFactory, ProjectFactory, RegistrationFactory, NodeFactory, DraftRegistrationFactory

class TestRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestRegistrationList, self).setUp()
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
        assert_not_in(self.project_two._id, ids)


class TestRegistrationCreate(ApiTestCase):
    def setUp(self):
        ensure_schemas()
        super(TestRegistrationCreate, self).setUp()
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
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}registrations/{}/'.format(API_BASE, self.public_draft._id)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.registration = RegistrationFactory(project=self.public_project)

    def test_create_registration_from_node(self):
        url = '/{}registrations/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_registration_from_fake_node(self):
        url = '/{}registrations/{}/'.format(API_BASE, '12345')
        res = self.app.post(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_registration_from_registration(self):
        url = '/{}registrations/{}/'.format(API_BASE, self.registration._id)
        res = self.app.post(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_public_registration_logged_out(self):
        res = self.app.post(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_public_registration_logged_in(self):
        res = self.app.post(self.public_url, auth=self.basic_auth, expect_errors=True)
        token_url = res.json['data']['links']['confirm_register']
        assert_equal(res.status_code, 202)

        res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.public_draft.title)
        assert_equal(res.json['data']['properties']['registration'], True)

    def test_invalid_token_create_registration(self):
        res = self.app.post(self.private_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 202)
        token_url = self.private_url + "freeze/12345/"

        res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json["non_field_errors"][0], "Incorrect token.")

    def test_create_private_registration_logged_out(self):
        res = self.app.post(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_private_registration_logged_in_contributor(self):
        res = self.app.post(self.private_url, auth=self.basic_auth, expect_errors=True)
        token_url = res.json['data']['links']['confirm_register']
        assert_equal(res.status_code, 202)

        assert_equal(self.private_draft.is_registration, False)
        res = self.app.post(token_url, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.private_draft.title)
        assert_equal(res.json['data']['properties']['registration'], True)

    def test_create_private_registration_logged_in_non_contributor(self):
        res = self.app.post(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_private_registration_logged_in_read_only_contributor(self):
        self.private_draft.add_contributor(self.user_two, permissions = ['read'])
        res = self.app.post(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)



