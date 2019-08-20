import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import ApiOAuth2ScopeFactory, AuthUserFactory


@pytest.mark.django_db
class TestScopeDetail:

    def test_scope_detail(self, app):
        scope = ApiOAuth2ScopeFactory()
        url_scope = '/{}scopes/{}/'.format(API_BASE, scope.name)
        res_scope = app.get(url_scope)
        data_scope = res_scope.json['data']

        # test_scope_detail_success
        assert res_scope.status_code == 200
        assert res_scope.content_type == 'application/vnd.api+json'

        # test_scope_top_level
        assert data_scope['type'] == 'scopes'
        assert data_scope['id'] == scope.name

        # test_scope_attributes:
        assert data_scope['attributes']['description'] == scope.description
        assert data_scope['attributes']['description'] != ''

    def test_scope_detail_errors(self, app):
        scope = ApiOAuth2ScopeFactory()
        user = AuthUserFactory()

        # Scope Not Found
        url_scope = '/{}scopes/{}/'.format(API_BASE, 'not_found_scope')
        res = app.get(url_scope, expect_errors=True)
        assert res.status_code == 404

        scope.is_public = False
        scope.save()
        # Private scope, Unauthenticated
        url_scope = '/{}scopes/{}/'.format(API_BASE, scope.name)
        res = app.get(url_scope, expect_errors=True)
        assert res.status_code == 401

        # Private scope, authenticated
        res = app.get(url_scope, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
