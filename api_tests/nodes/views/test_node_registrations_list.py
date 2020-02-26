import pytest
from future.moves.urllib.parse import urlparse

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    OSFGroupFactory,
    AuthUserFactory,
)
from osf.utils.permissions import READ


def node_url_for(n_id):
    return '/{}nodes/{}/'.format(API_BASE, n_id)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeRegistrationList:

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_registration(self, user, private_project):
        return RegistrationFactory(
            creator=user,
            project=private_project,
            is_public=True)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/registrations/'.format(
            API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            creator=user,
            project=public_project,
            is_public=True)

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/registrations/'.format(
            API_BASE, public_project._id)

    def test_node_registration_list(
            self, app, user, public_project, private_project, public_registration,
            private_registration, public_url, private_url):

        #   test_return_public_registrations_logged_out
        res = app.get(public_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['attributes']['registration'] is True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(
            url).path == '/{}nodes/{}/'.format(API_BASE, public_project._id)
        assert res.json['data'][0]['type'] == 'registrations'

    #   test_return_public_registrations_logged_in
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['registration'] is True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(
            url
        ).path == '/{}nodes/{}/'.format(API_BASE, public_project._id)
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['type'] == 'registrations'

    #   test_return_private_registrations_logged_out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_registration_group_mem_read
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, READ)
        res = app.get(private_url, expect_errors=True, auth=group_mem.auth)
        assert res.status_code == 200

    #   test_return_private_registrations_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['registration'] is True
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert urlparse(
            url
        ).path == '/{}nodes/{}/'.format(API_BASE, private_project._id)
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'][0]['type'] == 'registrations'
