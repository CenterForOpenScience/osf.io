from unittest import mock
import pytest

from api.scopes.serializers import SCOPES_RELATIONSHIP_VERSION
from osf_tests.factories import (
    ApiOAuth2PersonalTokenFactory,
    ApiOAuth2ScopeFactory,
    AuthUserFactory,
)
from tests.base import assert_dict_contains_subset
from website.util import api_v2_url

@pytest.mark.django_db
class TestTokenDetailScopesAsRelationships:

    def post_payload(self, type_payload='tokens', scopes=None, name='A shiny updated token'):
        if not scopes:
            scopes = ApiOAuth2ScopeFactory().name

        return {
            'data': {
                'type': type_payload,
                'attributes': {
                    'name': name,
                },
                'relationships': {
                    'scopes': {
                        'data': [
                            {
                                'type': 'scopes',
                                'id': scopes
                            }
                        ]
                    }
                }
            }
        }

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def token_user_one(self, user_one):
        return ApiOAuth2PersonalTokenFactory(owner=user_one)

    @pytest.fixture()
    def url_token_detail(self, user_one, token_user_one):
        path = f'tokens/{token_user_one._id}/?version={SCOPES_RELATIONSHIP_VERSION}'
        return api_v2_url(path, base_route='/')

    @pytest.fixture()
    def url_token_list(self):
        return api_v2_url(f'tokens/?version={SCOPES_RELATIONSHIP_VERSION}', base_route='/')

    @pytest.fixture()
    def read_scope(self):
        return ApiOAuth2ScopeFactory(name='osf.full_read')

    @pytest.fixture()
    def private_scope(self):
        return ApiOAuth2ScopeFactory(is_public=False)

    def test_owner_can_view(
            self,
            app,
            url_token_detail,
            user_one,
            user_two,
            token_user_one
    ):
        res = app.get(url_token_detail, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == token_user_one._id

    def test_non_owner_cant_view(
            self,
            app,
            url_token_detail,
            user_one,
            user_two,
            token_user_one
    ):
        res = app.get(url_token_detail, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

    def test_returns_401_when_not_logged_in(
            self,
            app,
            url_token_detail,
            user_one,
            user_two,
            token_user_one
    ):
        res = app.get(url_token_detail, expect_errors=True)
        assert res.status_code == 401

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_owner_can_delete(
            self,
            mock_method,
            app,
            user_one,
            url_token_detail
    ):
        mock_method.return_value(True)
        res = app.delete(url_token_detail, auth=user_one.auth)
        assert res.status_code == 204

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_tokens_makes_api_view_inaccessible(
            self,
            mock_method,
            app,
            url_token_detail,
            user_one
    ):
        mock_method.return_value(True)
        app.delete(url_token_detail, auth=user_one.auth)
        res = app.get(url_token_detail, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_updating_one_field_should_not_blank_others_on_patch_update(
            self,
            mock_revoke,
            app,
            token_user_one,
            url_token_detail,
            user_one,
            read_scope
    ):
        mock_revoke.return_value = True
        user_one_token = token_user_one
        new_name = 'The token formerly known as Prince'
        res = app.patch_json_api(
            url_token_detail,
            {
                'data': {
                    'attributes': {
                        'name': new_name,
                    },
                    'id': token_user_one._id,
                    'type': 'tokens',
                    'relationships': {
                        'scopes': {
                            'data': [
                                {
                                    'type': 'scopes',
                                    'id': read_scope.name
                                }
                            ]

                        }
                    }
                }
            },
            auth=user_one.auth
        )
        user_one_token.reload()
        assert res.status_code == 200

        assert_dict_contains_subset(
            {'name': new_name},
            res.json['data']['attributes']
        )
        assert res.json['data']['id'] == user_one_token._id
        assert res.json['data']['relationships']['owner']['data']['id'] == user_one_token.owner._id
        assert len(res.json['data']['embeds']['scopes']['data']) == 1
        assert res.json['data']['embeds']['scopes']['data'][0]['id'] == read_scope.name

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_updating_an_instance_does_not_change_the_number_of_instances(
            self,
            mock_revoke,
            app,
            url_token_detail,
            url_token_list,
            token_user_one,
            user_one,
            read_scope
    ):
        mock_revoke.return_value = True
        res = app.patch_json_api(
            url_token_detail,
            {
                'data': {
                    'attributes': {
                        'name': 'The token formerly known as Prince',
                    },
                    'relationships': {
                        'scopes': {
                            'data': [
                                {
                                    'type': 'scopes',
                                    'id': read_scope.name
                                }
                            ]
                        }
                    },
                    'id': token_user_one._id,
                    'type': 'tokens'
                }
            },
            auth=user_one.auth
        )
        assert res.status_code == 200

        res = app.get(url_token_list, auth=user_one.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == 1)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_flags_instance_inactive(
            self,
            mock_method,
            app,
            url_token_detail,
            user_one,
            token_user_one
    ):
        mock_method.return_value(True)
        app.delete(url_token_detail, auth=user_one.auth)
        token_user_one.reload()
        assert not token_user_one.is_active

    def test_read_does_not_return_token_id(
            self,
            app,
            url_token_detail,
            user_one
    ):
        res = app.get(url_token_detail, auth=user_one.auth)
        assert res.status_code == 200
        assert 'token_id' not in res.json['data']['attributes']

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_does_not_return_token_id(self, mock_revoke, app, url_token_detail, user_one):
        mock_revoke.return_value = True
        res = app.put_json_api(
            url_token_detail,
            self.post_payload(),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 200
        assert 'token_id' not in res.json['data']['attributes']
        assert 'token_id' not in res.json['data']['attributes']

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token(self, mock_revoke, app, user_one, url_token_detail):
        mock_revoke.return_value = True
        res = app.put_json_api(
            url_token_detail,
            self.post_payload(),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 200

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_add_scope(self, mock_revoke, app, user_one, token_user_one, url_token_detail):
        mock_revoke.return_value = True
        original_scope = token_user_one.scopes.first()
        scope = ApiOAuth2ScopeFactory()
        res = app.put_json_api(
            url_token_detail,
            self.post_payload(scopes=scope.name),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 200
        scopes_data = res.json['data']['embeds']['scopes']['data']
        assert len(scopes_data) == 1
        assert scopes_data[0]['id'] == scope.name
        assert scope.name != original_scope.name

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_non_owner_cant_delete(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        mock_revoke.return_value = True
        res = app.delete(
            url_token_detail,
            auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_create_with_nonexistant_scope_fails(
            self,
            mock_revoke,
            url_token_list,
            user_one,
            app,
    ):
        mock_revoke.return_value = True

        injected_scope = self.post_payload(
            name='A shiny invalid token',
            scopes='osf.admin'
        )
        res = app.post_json_api(
            url_token_list,
            injected_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_create_with_private_scope_fails(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two,
            private_scope
    ):
        assert not private_scope.is_public
        nonsense_scope = self.post_payload(
            scopes=private_scope.name
        )
        res = app.post_json_api(
            url_token_list,
            nonsense_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_with_nonexistant_scope_fails(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        injected_scope = self.post_payload(
            name='A shiny invalid token',
            scopes='osf.admin'
        )
        res = app.put_json_api(
            url_token_detail,
            injected_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_with_private_scope_fails(
            self,
            mock_revoke,
            url_token_detail,
            user_one,
            app,
            private_scope
    ):
        private_scope = self.post_payload(
            name='A shiny invalid token',
            scopes=private_scope.name
        )
        res = app.put_json_api(
            url_token_detail,
            private_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_incorrect_type(
            self,
            mock_revoke,
            app,
            url_token_detail,
            user_one,
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_payload(type_payload='Wrong type.'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_no_type(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_payload(type_payload=''),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_no_attributes(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            {
                'id': token_user_one._id,
                'type': 'tokens',
                'name': 'The token formerly known as Prince'
            },
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_partial_update_token_incorrect_type(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.patch_json_api(
            url_token_detail,
            self.post_payload(type_payload='Wrong type.'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    @pytest.mark.enable_implicit_clean
    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_partial_update_token_no_type(
            self,
            mock_revoke,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.patch_json_api(
            url_token_detail,
            self.post_payload(type_payload=''),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
