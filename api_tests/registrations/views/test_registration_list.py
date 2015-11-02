
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from website.models import Node
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory
)


class TestRegistrationList(ApiTestCase):

    def setUp(self):
        super(TestRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)
        self.url = '/{}registrations/'.format(API_BASE)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project)
        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestRegistrationList, self).tearDown()
        Node.remove()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_return_registrations_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.status_code, 200)

        registered_from_one = urlparse(res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path
        registered_from_two = urlparse(res.json['data'][1]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_items_equal([registered_from_one, registered_from_two],
                           ['/{}nodes/{}/'.format(API_BASE, self.public_project._id),
                            '/{}nodes/{}/'.format(API_BASE, self.project._id)])

    def test_return_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        registered_from = urlparse(res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_equal(registered_from, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_exclude_nodes_from_registrations_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_in(self.public_registration_project._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.project._id, ids)
