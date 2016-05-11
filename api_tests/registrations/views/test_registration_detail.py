from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from website.util import permissions

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)

from api.registrations.serializers import RegistrationSerializer, RegistrationDetailSerializer

class TestRegistrationDetail(ApiTestCase):

    def setUp(self):
        self.maxDiff = None
        super(TestRegistrationDetail, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_registration = RegistrationFactory(project=self.public_project, creator=self.user, is_public=True)
        self.private_registration = RegistrationFactory(project=self.private_project, creator=self.user)
        self.public_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration._id)
        self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)

    def test_return_public_registration_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        registered_from = urlparse(data['relationships']['registered_from']['links']['related']['href']).path
        assert_equal(data['attributes']['registration'], True)
        assert_equal(registered_from, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_return_public_registration_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        data = res.json['data']
        registered_from = urlparse(data['relationships']['registered_from']['links']['related']['href']).path
        assert_equal(data['attributes']['registration'], True)
        assert_equal(registered_from, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_return_private_registration_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_private_project_registrations_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        data = res.json['data']
        registered_from = urlparse(data['relationships']['registered_from']['links']['related']['href']).path
        assert_equal(data['attributes']['registration'], True)
        assert_equal(registered_from, '/{}nodes/{}/'.format(API_BASE, self.private_project._id))

    def test_return_private_registration_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_do_not_return_node_detail(self):
        url = '/{}registrations/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], "Not found.")

    def test_do_not_return_node_detail_in_sub_view(self):
        url = '/{}registrations/{}/contributors/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], "Not found.")

    def test_do_not_return_registration_in_node_detail(self):
        url = '/{}nodes/{}/'.format(API_BASE, self.public_registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], "Not found.")

    def test_registration_shows_specific_related_counts(self):
        url = '/{}registrations/{}/?related_counts=children'.format(API_BASE, self.private_registration._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['relationships']['children']['links']['related']['meta']['count'], 0)
        assert_equal(res.json['data']['relationships']['contributors']['links']['related']['meta'], {})

    def test_hide_if_registration(self):
        # Registrations are a HideIfRegistration field
        node_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        res = self.app.get(node_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in('registrations', res.json['data']['relationships'])

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_not_in('registrations', res.json['data']['relationships'])

class TestRegistrationUpdate(ApiTestCase):

    def setUp(self):
        self.maxDiff = None
        super(TestRegistrationUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_registration = RegistrationFactory(project=self.public_project, creator=self.user, is_public=True)
        self.private_registration = RegistrationFactory(project=self.private_project, creator=self.user)
        self.public_url = '/{}registrations/{}/'.format(API_BASE, self.public_registration._id)
        self.private_url = '/{}registrations/{}/'.format(API_BASE, self.private_registration._id)

        self.private_registration.add_contributor(self.user_two, permissions=[permissions.READ])
        self.private_registration.add_contributor(self.user_three, permissions=[permissions.WRITE])
        self.private_registration.save()

        self.payload = {
            "data": {
                "id": self.private_registration._id,
                "type": "registrations",
                "attributes": {
                    "public": True,
                }
            }
        }

    def test_update_private_registration_logged_out(self):
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_update_private_registration_logged_in_admin(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['public'], True)

    def test_update_private_registration_logged_in_read_only_contributor(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_logged_in_read_write_contributor(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_public_registration_to_private(self):
        payload = {
            "data": {
                "id": self.public_registration._id,
                "type": "registrations",
                "attributes": {
                    "public": False,
                }
            }
        }
        res = self.app.put_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Registrations can only be turned from private to public.')

    def test_public_field_has_invalid_value(self):
        payload = {
            "data": {
                "id": self.public_registration._id,
                "type": "registrations",
                "attributes": {
                    "public": "Yes"
                }
            }
        }
        res = self.app.put_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '"Yes" is not a valid boolean.')

    def test_fields_other_than_public_are_ignored(self):
        payload = {
            "data": {
                "id": self.private_registration._id,
                "type": "registrations",
                "attributes": {
                    "public": True,
                    "category": "instrumentation",
                    "title": "New title",
                    "description": "New description"
                }
            }
        }
        res = self.app.put_json_api(self.private_url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['public'], True)
        assert_equal(res.json['data']['attributes']['category'], 'project')
        assert_equal(res.json['data']['attributes']['description'], self.private_registration.description)
        assert_equal(res.json['data']['attributes']['title'], self.private_registration.title)

    def test_type_field_must_match(self):
        payload = {
            "data": {
                "id": self.private_registration._id,
                "type": "nodes",
                "attributes": {
                    "public": True,
                    "category": "instrumentation",
                    "title": "New title",
                    "description": "New description"
                }
            }
        }
        res = self.app.put_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_id_field_must_match(self):
        payload = {
            "data": {
                "id": '12345',
                "type": "registrations",
                "attributes": {
                    "public": True,
                    "category": "instrumentation",
                    "title": "New title",
                    "description": "New description"
                }
            }
        }
        res = self.app.put_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_turning_private_registrations_public(self):
        node1 = ProjectFactory(creator=self.user, is_public=False)
        node2 = ProjectFactory(creator=self.user, is_public=False)

        node1.is_registration = True
        node1.registered_from = node2
        node1.registered_date = node1.date_modified
        node1.save()

        payload = {
            "data": {
                "id": node1._id,
                "type": "registrations",
                "attributes": {
                    "public": True,
                }
            }
        }

        url = '/{}registrations/{}/'.format(API_BASE, node1._id)
        res = self.app.put_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['public'], True)

    def test_registration_fields_are_read_only(self):
        writeable_fields = ['type', 'public', 'draft_registration', 'registration_choice', 'lift_embargo' ]
        for field in RegistrationSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert_equal(getattr(reg_field, 'read_only', False), True)

    def test_registration_detail_fields_are_read_only(self):
        writeable_fields = ['type', 'public', 'draft_registration', 'registration_choice', 'lift_embargo' ]

        for field in RegistrationDetailSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert_equal(getattr(reg_field, 'read_only', False), True)

    def test_user_cannot_delete_registration(self):
        res = self.app.delete_json_api(self.private_url, expect_errors=True, auth=self.user.auth)
        assert_equal(res.status_code, 405)



