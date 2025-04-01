from unittest import mock
import pytest

from osf_tests.factories import (
    ApiOAuth2PersonalTokenFactory,
    ApiOAuth2ScopeFactory,
    AuthUserFactory,
)
from tests.base import assert_dict_contains_subset
from website.util import api_v2_url


@pytest.mark.django_db
class TestTokenDetailScopesAsAttributes:

    def post_attributes_payload(self, type_payload='tokens', scopes='osf.full_write', name='A shiny updated token'):
        return {
            'data': {
                'type': type_payload,
                'attributes': {
                    'name': name,
                    'scopes': scopes,
                }
            }
        }

    @pytest.fixture()
    def write_scope(self):
        return ApiOAuth2ScopeFactory(name='osf.full_write')

    @pytest.fixture()
    def read_scope(self):
        return ApiOAuth2ScopeFactory(name='osf.full_read')

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
    def token_full_write(self, user_one, write_scope):
        token = ApiOAuth2PersonalTokenFactory(
            owner=user_one,
        )
        token.scopes.add(write_scope)
        return token

    @pytest.fixture()
    def url_token_detail(self, user_one, token_user_one):
        path = f'tokens/{token_user_one._id}/'
        return api_v2_url(path, base_route='/')

    @pytest.fixture()
    def url_token_detail_full_write(self, user_one, token_full_write):
        path = f'tokens/{token_full_write._id}/'
        return api_v2_url(path, base_route='/')

    @pytest.fixture()
    def url_token_list(self):
        return api_v2_url('tokens/', base_route='/')

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
        assert res.json['data']['attributes']['scopes'] == token_user_one.scopes.first().name

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
            write_scope
    ):
        mock_revoke.return_value = True
        new_name = 'The token formerly known as Prince'
        res = app.patch_json_api(
            url_token_detail,
            {
                'data': {
                    'attributes': {
                        'name': new_name,
                        'scopes': 'osf.full_write'
                    },
                    'id': token_user_one._id,
                    'type': 'tokens'
                }
            },
            auth=user_one.auth
        )
        token_user_one.reload()
        assert res.status_code == 200
        assert_dict_contains_subset(
            {'owner': token_user_one.owner._id, 'name': new_name, 'scopes': f'{write_scope.name}'},
            res.json['data']['attributes']
        )
        assert res.json['data']['id'] == token_user_one._id

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_updating_an_instance_does_not_change_the_number_of_instances(
            self,
            mock_revoke,
            app,
            url_token_detail,
            url_token_list,
            token_user_one,
            user_one,
            write_scope
    ):
        mock_revoke.return_value = True
        res = app.patch_json_api(
            url_token_detail,
            {
                'data': {
                    'attributes': {
                        'name': 'The token formerly known as Prince',
                        'scopes': 'osf.full_write'
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
        assert res.json['data'][0]['attributes']['scopes'] == write_scope.name

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
            self, app, url_token_detail, user_one):
        res = app.get(url_token_detail, auth=user_one.auth)
        assert res.status_code == 200
        assert 'token_id' not in res.json['data']['attributes']
        assert 'scopes' in res.json['data']['attributes']

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_does_not_return_token_id(
            self,
            mock_revoke,
            app,
            url_token_detail,
            user_one,
            write_scope
    ):
        mock_revoke.return_value = True
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(scopes='osf.full_write'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 200
        assert 'token_id' not in res.json['data']['attributes']
        assert res.json['data']['attributes']['scopes'] == write_scope.name

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token(self, mock_revoke, app, user_one, url_token_detail, write_scope):
        mock_revoke.return_value = True
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(scopes='osf.full_write'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 200
        assert res.json['data']['attributes']['scopes'] == write_scope.name

    def test_owner_can_edit_scopes_via_pat(self, app, user_one, token_full_write, url_token_detail_full_write, write_scope):
        res = app.put_json_api(
            url_token_detail_full_write,
            {
                'data': {
                    'attributes': {
                        'scopes': write_scope.name
                    },
                    'id': token_full_write._id,
                    'type': 'tokens'
                }
            },
            headers={'Authorization': f'Bearer {token_full_write.token_id}'},
        )
        assert res.status_code == 200
        token_full_write.refresh_from_db()
        assert write_scope in token_full_write.scopes.all()

    def test_non_owner_cant_delete(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.delete(
            url_token_detail,
            auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_create_with_admin_scope_fails(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        admin_token = ApiOAuth2ScopeFactory(name='osf.admin')
        admin_token.is_public = False
        admin_token.save()

        injected_scope = self.post_attributes_payload(
            name='A shiny invalid token',
            scopes='osf.admin'
        )
        res = app.post_json_api(
            url_token_list,
            injected_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_create_with_fake_scope_fails(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        nonsense_scope = self.post_attributes_payload(
            name='A shiny invalid token',
            scopes='osf.nonsense'
        )
        res = app.post_json_api(
            url_token_list,
            nonsense_scope,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_update_with_admin_scope_fails(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(
                name='A shiny invalid token',
                scopes='osf.admin'
            ),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_update_with_fake_scope_fails(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(
                name='A shiny invalid token',
                scopes='osf.nonsense'
            ),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_update_token_incorrect_type(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(type_payload='Wrong type.'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_update_token_no_type(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(type_payload=''),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_update_token_no_attributes(
            self,
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

    def test_partial_update_token_incorrect_type(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.patch_json_api(
            url_token_detail,
            self.post_attributes_payload(type_payload='Wrong type.'),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_partial_update_token_no_type(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.patch_json_api(
            url_token_detail,
            self.post_attributes_payload(type_payload=''),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_token_too_long(
            self,
            app,
            url_token_list,
            url_token_detail,
            token_user_one,
            user_one,
            user_two
    ):
        res = app.put_json_api(
            url_token_detail,
            self.post_attributes_payload(name='A' * 101),
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404
