import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
)
from osf.utils import permissions


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationContributorsList:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user):
        return ProjectFactory(
            title='Public Project',
            description='A public project',
            category='data',
            is_public=True,
            creator=user,
        )

    @pytest.fixture()
    def registration_public(self, project_public, user):
        return RegistrationFactory(project=project_public, creator=user, is_public=True)

    @pytest.fixture()
    def url_public(self, registration_public):
        return f'/{API_BASE}registrations/{registration_public._id}/contributors/?send_email=false'

    @pytest.fixture()
    def payload_one(self, user_two):
        return {
            'type': 'contributors',
            'attributes': {'bibliographic': True, 'permission': permissions.ADMIN},
            'relationships': {'users': {'data': {'id': user_two._id, 'type': 'users'}}},
        }

    @pytest.fixture()
    def payload_two(self, user_three):
        return {
            'type': 'contributors',
            'attributes': {'bibliographic': False, 'permission': permissions.READ},
            'relationships': {
                'users': {'data': {'id': user_three._id, 'type': 'users'}}
            },
        }

    @pytest.fixture()
    def make_contrib_id(self):
        def contrib_id(registration_id, user_id):
            return f'{registration_id}-{user_id}'
        return contrib_id

    @pytest.fixture()
    def registration_with_contributors(self, project_public, user, user_two, user_three):
        registration = RegistrationFactory(project=project_public, creator=user, is_public=True)

        registration.add_contributor(
            user_two, permissions=permissions.READ, visible=True, save=True
        )
        registration.add_contributor(
            user_three, permissions=permissions.READ, visible=True, save=True
        )
        return registration

    @pytest.fixture()
    def url_with_contributors(self, registration_with_contributors):
        return f'/{API_BASE}registrations/{registration_with_contributors._id}/contributors/'

    @pytest.fixture()
    def update_payload_one(self, user_two, registration_with_contributors, make_contrib_id):
        return {
            'id': make_contrib_id(registration_with_contributors._id, user_two._id),
            'type': 'contributors',
            'attributes': {'bibliographic': True, 'permission': permissions.ADMIN},
        }

    @pytest.fixture()
    def update_payload_two(self, user_three, registration_with_contributors, make_contrib_id):
        return {
            'id': make_contrib_id(registration_with_contributors._id, user_three._id),
            'type': 'contributors',
            'attributes': {'bibliographic': False, 'permission': permissions.WRITE},
        }

    def test_bulk_post_new_contributors(
        self, app, user, registration_public, payload_one, payload_two, url_public
    ):
        res = app.post_json_api(
            url_public,
            {'data': [payload_one, payload_two]},
            auth=user.auth,
            bulk=True,
        )
        assert res.status_code == 201
        assert len(res.json['data']) == 2
        assert [
            res.json['data'][0]['attributes']['bibliographic'],
            res.json['data'][1]['attributes']['bibliographic'],
        ] == [True, False]
        assert [
            res.json['data'][0]['attributes']['permission'],
            res.json['data'][1]['attributes']['permission'],
        ] == [permissions.ADMIN, permissions.READ]
        assert res.content_type == 'application/vnd.api+json'

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

    def test_bulk_patch_existing_contributors(
        self, app, user, registration_with_contributors, update_payload_one, update_payload_two, url_with_contributors
    ):
        res = app.patch_json_api(
            url_with_contributors,
            {'data': [update_payload_one, update_payload_two]},
            auth=user.auth,
            bulk=True,
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert [
            res.json['data'][0]['attributes']['bibliographic'],
            res.json['data'][1]['attributes']['bibliographic'],
        ] == [True, False]
        assert [
            res.json['data'][0]['attributes']['permission'],
            res.json['data'][1]['attributes']['permission'],
        ] == [permissions.ADMIN, permissions.WRITE]

        res = app.get(url_with_contributors, auth=user.auth)
        data = res.json['data']
        contrib_dict = {contrib['id']: contrib for contrib in data}
        assert contrib_dict[update_payload_one['id']]['attributes']['permission'] == permissions.ADMIN
        assert contrib_dict[update_payload_two['id']]['attributes']['permission'] == permissions.WRITE
