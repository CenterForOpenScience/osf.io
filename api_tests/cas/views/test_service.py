import pytest

from rest_framework import status

from api.base.settings.defaults import API_BASE
from api_tests.cas import util as cas_test_util

from osf_tests.factories import (ApiOAuth2ApplicationFactory, ApiOAuth2PersonalTokenFactory,
                                 ApiOAuth2ScopeFactory, InstitutionFactory)

from osf.models.oauth import generate_token_id


@pytest.mark.django_db
class TestServiceInstitutions(object):

    @pytest.fixture()
    def institution_no_auth(self):
        institution = InstitutionFactory()
        institution.login_url = None
        institution.logout_url = None
        institution.delegation_protocol = ''
        institution.save()
        return institution

    @pytest.fixture()
    def institution_saml(self):
        institution = InstitutionFactory()
        institution.delegation_protocol = 'saml-shib'
        institution.save()
        return institution

    @pytest.fixture()
    def institution_cas(self):
        institution = InstitutionFactory()
        institution.login_url = ''
        institution.delegation_protocol = 'cas-pac4j'
        institution.save()
        return institution

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/service/institutions/'.format(API_BASE)

    def test_load_institutions(self, app, endpoint_url, institution_no_auth, institution_saml, institution_cas):

        payload = cas_test_util.make_payload_service_institutions()
        res = app.post(endpoint_url, payload)
        assert res.status_code == status.HTTP_200_OK
        assert res.json.get(institution_no_auth._id, None) is None
        assert res.json.get(institution_saml._id, None) is not None
        assert res.json.get(institution_cas._id, None) is not None


@pytest.mark.django_db
class TestServiceOauthApps(object):

    @pytest.fixture()
    def oauth_app_1(self):
        return ApiOAuth2ApplicationFactory()

    @pytest.fixture()
    def expected_response_entry(self, oauth_app_1):
        return {
            'name': oauth_app_1.name,
            'description': oauth_app_1.description,
            'callbackUrl': oauth_app_1.callback_url,
            'clientId': oauth_app_1.client_id,
            'clientSecret': oauth_app_1.client_secret,
        }

    @pytest.fixture()
    def oauth_app_2(self):
        return ApiOAuth2ApplicationFactory()

    @pytest.fixture()
    def oauth_app_3(self):
        return ApiOAuth2ApplicationFactory()

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/service/oauth/apps/'.format(API_BASE)

    def test_load_oauth_apps(self, app, endpoint_url, oauth_app_1, expected_response_entry, oauth_app_2, oauth_app_3):

        payload = cas_test_util.make_payload_service_oauth_apps()
        res = app.post(endpoint_url, payload)
        assert res.status_code == status.HTTP_200_OK

        assert res.json.get(oauth_app_1._id, {}) == expected_response_entry
        assert res.json.get(oauth_app_2._id, {}) is not None
        assert res.json.get(oauth_app_3._id, {}) is not None


@pytest.mark.django_db
class TestServiceOauthToken(object):

    @pytest.fixture()
    def oauth_token(self):
        return ApiOAuth2PersonalTokenFactory()

    @pytest.fixture()
    def expected_response(self, oauth_token):
        return {
            'tokenId': oauth_token.token_id,
            'ownerId': oauth_token.owner._id,
            'tokenScopes': oauth_token.scopes,
        }

    @pytest.fixture()
    def invalid_token_id(self):
        return generate_token_id()

    @pytest.fixture()
    def expected_error_response(self):
        return {
            'code': 40003,
            'source': {},
            'meta': {},
            'detail': 'The personal access token requested is not found or invalid.'
        }

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/service/oauth/token/'.format(API_BASE)

    def test_personal_access_token_exists(self, app, endpoint_url, oauth_token, expected_response):

        payload = cas_test_util.make_payload_service_oauth_token(oauth_token.token_id)
        res = app.post(endpoint_url, payload)
        assert res.status_code == status.HTTP_200_OK
        assert res.json == expected_response

    def test_personal_access_token_not_found(self, app, endpoint_url, invalid_token_id, expected_error_response):

        payload = cas_test_util.make_payload_service_oauth_token(invalid_token_id)
        res = app.post(endpoint_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.json.get('errors')[0] == expected_error_response


@pytest.mark.django_db
class TestServiceOauthScope(object):

    @pytest.fixture()
    def oauth_scope(self):
        return ApiOAuth2ScopeFactory()

    @pytest.fixture()
    def expected_response(self, oauth_scope):
        return {
            'scopeDescription': oauth_scope.description,
        }

    @pytest.fixture()
    def invalid_scope_name(self):
        return 'invalid.scope'

    @pytest.fixture()
    def expected_error_response(self):
        return {
            'code': 40002,
            'source': {},
            'meta': {},
            'detail': 'The scope requested is not found or inactive.'
        }

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/service/oauth/scope/'.format(API_BASE)

    def test_oauth_scope_registred(self, app, endpoint_url, oauth_scope, expected_response):

        payload = cas_test_util.make_payload_service_oauth_scope(oauth_scope.name)
        res = app.post(endpoint_url, payload)
        assert res.status_code == status.HTTP_200_OK
        assert res.json == expected_response

    def test_oauth_scope_not_registered(self, app, endpoint_url, invalid_scope_name, expected_error_response):
        payload = cas_test_util.make_payload_service_oauth_scope(invalid_scope_name)
        res = app.post(endpoint_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.json.get('errors')[0] == expected_error_response
