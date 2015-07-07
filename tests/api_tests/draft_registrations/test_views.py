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


class TestRegistrationUpdate(ApiTestCase):

    def setUp(self):
        super(TestRegistrationUpdate, self).setUp()
        ensure_schemas()
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
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)

        self.registration_form = 'OSF-Standard Pre-Data Collection Registration'
        self.registration_metadata = "{'Have you looked at the data?': 'No'}"
        self.schema_version = 1

    # TODO, figure out how to not need eval!
    def test_update_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.put(url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_update_node_that_does_not_exist(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, '12345')
        res = self.app.put(url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_update_public_registration_draft_logged_out(self):
        res = self.app.put(self.public_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_public_registration_draft_logged_in(self):
        res = self.app.put(self.public_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        source = eval(res.json['data']['branched_from'])
        metadata = res.json['data']['registration_metadata']
        registration_schema =eval(res.json['data']['registration_schema'])
        assert_equal(source['title'], self.public_project.title)
        assert_equal(metadata, self.registration_metadata)
        assert_not_equal(registration_schema, None)
        assert_equal(registration_schema['name'], self.registration_form)

        res = self.app.put(self.public_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_out(self):
        res = self.app.put(self.private_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.put(self.private_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        source = eval(res.json['data']['branched_from'])
        metadata = res.json['data']['registration_metadata']
        registration_schema = eval(res.json['data']['registration_schema'])
        assert_equal(source['title'], self.private_project.title)
        assert_equal(metadata, self.registration_metadata)
        assert_not_equal(registration_schema, None)
        assert_equal(registration_schema['name'], self.registration_form)

    def test_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.put(self.private_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.put(self.private_url, {
            'registration_form': self.registration_form,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestDraftRegistrationPartialUpdate(ApiTestCase):

    def setUp(self):
        super(TestDraftRegistrationPartialUpdate, self).setUp()
        ensure_schemas()
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
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)

        self.registration_form = 'OSF-Standard Pre-Data Collection Registration'
        self.registration_metadata = "{'Have you looked at the data?': 'No'}"
        self.schema_version = 1

    def test_partial_update_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.patch(url, {
            'self.registration_form': self.registration_form,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_partial_update_node_that_does_not_exist(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, '12345')
        res = self.app.patch(url, {
            'self.registration_form': self.registration_form,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_partial_update_registration_schema_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, {
            'registration_form': self.registration_form,
        }, auth=self.basic_auth, expect_errors=True)
        registration_schema = eval(res.json['data']['registration_schema'])
        assert_equal(registration_schema['name'], 'Open-Ended Registration')
        assert_equal(res.status_code, 200)

        res = self.app.patch(self.public_url, {
            'registration_form': self.registration_form,
            'schema_version': self.schema_version
        }, auth=self.basic_auth, expect_errors=True)
        registration_schema = eval(res.json['data']['registration_schema'])
        assert_equal(registration_schema['name'], self.registration_form)
        assert_equal(res.status_code, 200)

    def test_partial_update_public_draft_registration_logged_out(self):
        res = self.app.patch(self.public_url, {
            'registration_form': self.registration_form,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth, expect_errors=True)
        registration_metadata = res.json['data']['registration_metadata']
        assert_equal(registration_metadata, self.registration_metadata)
        assert_equal(res.status_code, 200)

        res = self.app.patch(self.public_url, {
             'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_out(self):
        res = self.app.patch(self.private_url, {
             'registration_metadata': self.registration_metadata,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.patch(self.private_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth)
        registration_metadata = res.json['data']['registration_metadata']
        assert_equal(registration_metadata, self.registration_metadata)
        assert_equal(res.status_code, 200)

    def test_partial_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.patch(self.private_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.patch(self.private_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestDeleteDraftRegistration(ApiTestCase):

    def setUp(self):
        super(TestDeleteDraftRegistration, self).setUp()
        ensure_schemas()
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
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)


    def test_delete_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_node_that_does_not_exist(self):
        url = '/{}draft_ registrations/{}/'.format(API_BASE, '12345')
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_public_draft_registration_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_equal(self.public_draft.is_deleted, False)
        res = self.app.delete(self.public_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 204)
        assert_equal(self.public_draft.is_deleted, True)

    def test_delete_private_registration_draft_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_contributor(self):
        assert_equal(self.private_draft.is_deleted, False)
        res = self.app.delete(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        assert_equal(self.private_draft.is_deleted, True)

    def test_delete_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_draft.add_contributor(self.user_two, permissions=['read'])
        res = self.app.delete(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)






