from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory
)


class TestRegistrationDetail(ApiTestCase):
    def setUp(self):
        super(TestRegistrationDetail, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_registration = RegistrationFactory(project=self.public_project, creator=self.user)
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
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "This is not a registration.")
