import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import ApiOAuth2ScopeFactory


@pytest.mark.django_db
class TestScopeList:

    def test_scope_list(self, app):
        scope = ApiOAuth2ScopeFactory()
        second_scope = ApiOAuth2ScopeFactory()

        url_scopes = '/{}scopes/'.format(API_BASE)
        res_scopes = app.get(url_scopes)

        # test_scope_list_success
        assert res_scopes.status_code == 200
        assert res_scopes.content_type == 'application/vnd.api+json'

        # test_scope_list_count_correct
        total = res_scopes.json['links']['meta']['total']
        assert total == 2

        # test_private_scope_excluded
        second_scope.is_public = False
        second_scope.save()

        res_scopes = app.get(url_scopes)
        assert res_scopes.status_code == 200
        total = res_scopes.json['links']['meta']['total']
        assert total == 1
        assert second_scope.name != res_scopes.json['data'][0]['id']
        assert scope.name == res_scopes.json['data'][0]['id']
