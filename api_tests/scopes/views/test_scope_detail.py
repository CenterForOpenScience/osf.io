import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.oauth_scopes import public_scopes


@pytest.mark.django_db
class TestScopeDetail:

    def test_scope_detail(self, app):
        count = 0
        expected_count = len(public_scopes)
        for key, value in public_scopes.items():
            id = key
            description = value.description
            is_public = value.is_public
            url_scope = '/{}scopes/{}/'.format(API_BASE, id)

            if is_public:
                res_scope = app.get(url_scope)
                data_scope = res_scope.json['data']
                # test_scope_detail_success
                assert res_scope.status_code == 200
                assert res_scope.content_type == 'application/vnd.api+json'

                # test_scope_top_level
                assert data_scope['type'] == 'scopes'
                assert data_scope['id'] == id

                # test_scope_attributes:
                assert data_scope['attributes']['description'] == description
                assert data_scope['attributes']['description'] != ''
                count += 1
            else:
                res_scope = app.get(url_scope, expect_errors=True)
                assert 'data' not in res_scope.json
                assert res_scope.status_code == 401
                count += 1
        assert count == expected_count
        assert count != 0
