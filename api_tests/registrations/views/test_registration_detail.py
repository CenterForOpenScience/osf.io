from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    RetractedRegistrationFactory
)


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

    def test_retractions_display_limited_fields(self):
        registration = RegistrationFactory(creator=self.user, project=self.public_project, public=True)
        url = '/{}registrations/{}/'.format(API_BASE, registration._id)
        retraction = RetractedRegistrationFactory(registration=registration, user=registration.creator)
        retraction.justification = 'We made a major error.'
        retraction.save()
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        assert_items_equal(res.json['data']['attributes'], {
            'title': registration.title,
            'description': registration.description,
            'date_created': registration.date_created,
            'date_registered': registration.registered_date,
            'retraction_justification': registration.retraction.justification,
            'public': None,
            'category': None,
            'date_modified': None,
            "registration": True,
            'fork': None,
            'collection': None,
            'dashboard': None,
            'tags': None,
            'retracted': True,
            'pending_retraction': None,
            'pending_registration_approval': None,
            'pending_embargo_approval': None,
            "embargo_end_date": None,
            "registered_meta": None,
            'current_user_permissions': None,
            "registration_supplement": registration.registered_meta.keys()[0]
        })

        contributors = urlparse(res.json['data']['relationships']['contributors']['links']['related']['href']).path
        assert_equal(contributors, '/{}registrations/{}/contributors/'.format(API_BASE, registration._id))

        assert_not_in('children', res.json['data']['relationships'])
        assert_not_in('comments', res.json['data']['relationships'])
        assert_not_in('node_links', res.json['data']['relationships'])
        assert_not_in('registrations', res.json['data']['relationships'])
        assert_not_in('parent', res.json['data']['relationships'])
        assert_not_in('forked_from', res.json['data']['relationships'])
        assert_not_in('files', res.json['data']['relationships'])
        assert_not_in('logs', res.json['data']['relationships'])
