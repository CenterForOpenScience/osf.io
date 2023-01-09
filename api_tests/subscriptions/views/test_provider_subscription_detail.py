import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import (
    CollectionProviderFactory,
    RegistrationProviderFactory,
    PreprintProviderFactory
)
from api_tests.utils import UserRoles

from osf.models import AbstractProvider


def configure_test_auth(user_role, provider):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        provider.add_to_group(user, 'moderator')
        provider.save()

    return user.auth


def get_provider_by_type(provider_type):
    return AbstractProvider.objects.get(_id='EAGLES', type=provider_type)


@pytest.mark.django_db
class TestGETPermissionsProviderSubscriptionDetail:
    """
    Autouse=True providers and ensure they have all identical `_id`s to test for bug where this causes errors.
    """

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture(autouse=True)
    def collections_provider(self):
        return CollectionProviderFactory(_id='EAGLES')

    @pytest.fixture(autouse=True)
    def registrations_provider(self):
        return RegistrationProviderFactory(_id='EAGLES')

    @pytest.fixture(autouse=True)
    def preprints_provider(self):
        return PreprintProviderFactory(_id='EAGLES')

    @pytest.fixture()
    def url(self, provider):
        provider = get_provider_by_type(provider)
        provider_type = provider.type.lstrip('osf.').rstrip('provider') + 's'
        return f'/{API_BASE}providers/{provider_type}/' \
               f'{provider._id}/subscriptions/{provider._id}_new_pending_submissions/'

    @pytest.mark.parametrize('user_role', [UserRoles.NONCONTRIB, UserRoles.UNAUTHENTICATED])
    @pytest.mark.parametrize('provider', ['osf.preprintprovider', 'osf.collectionprovider', 'osf.registrationprovider'])
    def test_status_code_no_auth_non_contrib(self, app, url, user_role, provider):
        provider = get_provider_by_type(provider)
        test_auth = configure_test_auth(user_role, provider)
        resp = app.get(
            url,
            auth=test_auth,
            expect_errors=True
        )
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR])
    @pytest.mark.parametrize('provider', ['osf.preprintprovider', 'osf.collectionprovider', 'osf.registrationprovider'])
    def test_status_code_moderator(self, app, url, provider, user_role):
        provider = get_provider_by_type(provider)
        test_auth = configure_test_auth(user_role, provider)
        resp = app.get(
            url,
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestPATCHPermissionsProviderSubscriptionDetail:
    """
    Autouse=True providers and ensure they have all identical `_id`s to test for bug where this causes errors.
    """

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture(autouse=True)
    def collections_provider(self):
        return CollectionProviderFactory(_id='EAGLES')

    @pytest.fixture(autouse=True)
    def registrations_provider(self):
        return RegistrationProviderFactory(_id='EAGLES')

    @pytest.fixture(autouse=True)
    def preprints_provider(self):
        return PreprintProviderFactory(_id='EAGLES')

    @pytest.fixture()
    def url(self, provider):
        provider = get_provider_by_type(provider)
        provider_type = provider.type.lstrip('osf.').rstrip('provider') + 's'
        return f'/{API_BASE}providers/{provider_type}/' \
               f'{provider._id}/subscriptions/{provider._id}_new_pending_submissions/'

    @pytest.fixture()
    def payload(self, frequecy):
        return {
            'data': {
                'type': 'user-provider-subscription',
                'attributes': {
                    'frequency': frequecy
                }
            }
        }

    @pytest.mark.parametrize('user_role', [UserRoles.NONCONTRIB, UserRoles.UNAUTHENTICATED])
    @pytest.mark.parametrize('provider', ['osf.preprintprovider', 'osf.collectionprovider', 'osf.registrationprovider'])
    def test_status_code_no_auth_non_contrib(self, app, url, user_role, provider):
        provider = get_provider_by_type(provider)
        test_auth = configure_test_auth(user_role, provider)
        resp = app.patch_json_api(
            url,
            auth=test_auth,
            expect_errors=True
        )
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR])
    @pytest.mark.parametrize('provider', ['osf.preprintprovider', 'osf.collectionprovider', 'osf.registrationprovider'])
    @pytest.mark.parametrize('frequecy', ['none', 'daily', 'instant'])
    def test_status_code_moderator(self, app, url, provider, user_role, payload, frequecy):
        provider = get_provider_by_type(provider)
        test_auth = configure_test_auth(user_role, provider)
        resp = app.patch_json_api(
            url,
            payload,
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['frequency'] == frequecy
