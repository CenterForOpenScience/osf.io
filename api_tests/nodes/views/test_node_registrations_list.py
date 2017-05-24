import pytest
from urlparse import urlparse

from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)

node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)

@pytest.mark.django_db
class TestNodeRegistrationList:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project, is_public=True)
        self.project.save()
        self.private_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project, is_public=True)
        self.public_project.save()
        self.public_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_node_registration_list(self):

    #   test_return_public_registrations_logged_out
        res = self.app.get(self.public_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['attributes']['registration'] == True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(url).path == '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        assert res.json['data'][0]['type'] == 'registrations'

    #   test_return_public_registrations_logged_in
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['registration'] == True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(url).path == '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['type'] == 'registrations'

    #   test_return_private_registrations_logged_out
        res = self.app.get(self.private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_registrations_logged_in_contributor
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['registration'] == True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(url).path == '/{}nodes/{}/'.format(API_BASE, self.project._id)
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['type'] == 'registrations'
