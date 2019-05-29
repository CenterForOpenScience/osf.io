import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.oauth_scopes import public_scopes


@pytest.mark.django_db
class TestScopeList:

    def test_scope_list(self, app):
        url_scopes = '/{}scopes/'.format(API_BASE)
        res_scopes = app.get(url_scopes)

        # test_scope_list_success
        assert res_scopes.status_code == 200
        assert res_scopes.content_type == 'application/vnd.api+json'

        # test_license_list_count_correct
        total = res_scopes.json['links']['meta']['total']
        count = 0
        for key, value in public_scopes.items():
            if value.is_public:
                count += 1
        assert total == count
