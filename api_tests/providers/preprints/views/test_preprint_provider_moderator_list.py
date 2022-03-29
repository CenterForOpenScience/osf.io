import mock
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
)
from osf.utils import permissions


class ProviderModeratorListTestClass:

    @pytest.fixture()
    def admin(self, provider):
        user = AuthUserFactory()
        provider.get_group(permissions.ADMIN).user_set.add(user)
        return user

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        provider.get_group('moderator').user_set.add(user)
        return user

    @pytest.fixture()
    def nonmoderator(self):
        return AuthUserFactory()

    def create_payload(self, permission_group, user_id=None, email=None, full_name=None):
        data = {
            'data': {
                'attributes': {
                    'permission_group': permission_group,
                },
                'type': 'moderators',
            }
        }
        if full_name:
            data['data']['attributes']['full_name'] = full_name
        if user_id:
            data['data']['id'] = user_id
        if email:
            data['data']['attributes']['email'] = email
        return data

    def test_list_get_not_authorized(self, app, url, nonmoderator, admin, provider):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url, auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403

    def test_list_get_moderator(self, app, url, nonmoderator, moderator, admin, provider):
        # admin/nonmoderator unused here, just len verification
        res = app.get(url, auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        for datum in res.json['data']:
            if datum['id'] == moderator._id:
                assert datum['attributes']['permission_group'] == 'moderator'

    def test_list_get_admin_with_filter(self, app, url, nonmoderator, moderator, admin, provider):
        # mod/nonmoderator unused here, just len verification
        res = app.get('{}?filter[permission_group]=admin&filter[id]={}'.format(url, admin._id), auth=admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == admin._id
        assert res.json['data'][0]['attributes']['permission_group'] == permissions.ADMIN

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_unauthorized(self, mock_mail, app, url, nonmoderator, moderator, provider):
        payload = self.create_payload(user_id=nonmoderator._id, permission_group='moderator')
        res = app.post(url, payload, expect_errors=True)
        assert res.status_code == 401

        res = app.post(url, payload, auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.post(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403

        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_admin_success_existing_user(self, mock_mail, app, url, nonmoderator, moderator, admin, provider):
        payload = self.create_payload(user_id=nonmoderator._id, permission_group='moderator')

        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == nonmoderator._id
        assert res.json['data']['attributes']['permission_group'] == 'moderator'
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_admin_failure_existing_moderator(self, mock_mail, app, url, moderator, admin, provider):
        payload = self.create_payload(user_id=moderator._id, permission_group='moderator')
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_admin_failure_unreg_moderator(self, mock_mail, app, url, moderator, nonmoderator, admin, provider):
        unreg_user = {'full_name': 'Son Goku', 'email': 'goku@dragonball.org'}
        # test_user_with_no_moderator_admin_permissions
        payload = self.create_payload(permission_group='moderator', **unreg_user)
        res = app.post_json_api(url, payload, auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403
        assert mock_mail.call_count == 0

        # test_user_with_moderator_admin_permissions
        payload = self.create_payload(permission_group='moderator', **unreg_user)
        res = app.post_json_api(url, payload, auth=admin.auth)

        assert res.status_code == 201
        assert mock_mail.call_count == 1
        assert mock_mail.call_args[0][0] == unreg_user['email']

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_admin_failure_invalid_group(self, mock_mail, app, url, nonmoderator, moderator, admin, provider):
        payload = self.create_payload(user_id=nonmoderator._id, permission_group='citizen')
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_list_post_admin_success_email(self, mock_mail, app, url, nonmoderator, moderator, admin, provider):
        payload = self.create_payload(email='somenewuser@gmail.com', full_name='Some User', permission_group='moderator')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        assert len(res.json['data']['id']) == 5
        assert res.json['data']['attributes']['permission_group'] == 'moderator'
        assert 'email' not in res.json['data']['attributes']
        assert mock_mail.call_count == 1

    def test_list_moderators_alphabetically(self, app, url, admin, moderator, provider):
        admin.fullname = 'Alice Alisdottir'
        moderator.fullname = 'Bob Bobsson'
        new_mod = AuthUserFactory(fullname='Cheryl Cherylsdottir')
        provider.get_group('moderator').user_set.add(new_mod)
        admin.save()
        moderator.save()
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 3
        assert res.json['data'][0]['id'] == admin._id
        assert res.json['data'][1]['id'] == moderator._id
        assert res.json['data'][2]['id'] == new_mod._id


@pytest.mark.django_db
class TestPreprintProviderModeratorList(ProviderModeratorListTestClass):

    @pytest.fixture()
    def provider(self):
        pp = PreprintProviderFactory(name='ModArxiv')
        pp.update_group_permissions()
        return pp

    @pytest.fixture(params=['/{}preprint_providers/{}/moderators/', '/{}providers/preprints/{}/moderators/'])
    def url(self, provider, request):
        url = request.param
        return url.format(API_BASE, provider._id)
