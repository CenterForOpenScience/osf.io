import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    CollectionProviderFactory,
)
from osf.utils import permissions
from tests.utils import capture_notifications


@pytest.fixture()
def url(provider):
    return f'/{API_BASE}providers/collections/{provider._id}/moderators/'


@pytest.fixture()
def provider():
    provider = CollectionProviderFactory()
    provider.update_group_permissions()
    return provider


@pytest.fixture()
def admin(provider):
    user = AuthUserFactory()
    provider.get_group(permissions.ADMIN).user_set.add(user)
    return user


@pytest.fixture()
def moderator(provider):
    user = AuthUserFactory()
    provider.get_group('moderator').user_set.add(user)
    return user


@pytest.fixture()
def nonmoderator():
    return AuthUserFactory()


def make_payload(permission_group, user_id=None, email=None, full_name=None):
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


@pytest.mark.django_db
class TestGETCollectionsModeratorList:

    def test_GET_unauthorized(self, app, url, provider):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_GET_forbidden(self, app, url, nonmoderator, provider):
        res = app.get(url, auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403

    def test_GET_moderator_formatting(self, app, url, nonmoderator, moderator, admin, provider):
        # admin/nonmoderator unused here, just len verification
        res = app.get(url, auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        for datum in res.json['data']:
            if datum['id'] == moderator._id:
                assert datum['attributes']['permission_group'] == 'moderator'

    def test_GET_admin_with_filter(self, app, url, nonmoderator, moderator, admin, provider):
        # mod/nonmoderator unused here, just len verification
        res = app.get(f'{url}?filter[permission_group]=admin&filter[id]={admin._id}', auth=admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == admin._id
        assert res.json['data'][0]['attributes']['permission_group'] == permissions.ADMIN


@pytest.mark.django_db
class TestPOSTCollectionsModeratorList:

    def test_POST_unauthorized(self, app, url, nonmoderator, moderator, provider):
        payload = make_payload(user_id=nonmoderator._id, permission_group='moderator')
        with capture_notifications() as notifications:
            res = app.post(url, payload, expect_errors=True)
        assert res.status_code == 401
        assert not notifications

    def test_POST_forbidden(self, app, url, nonmoderator, moderator, provider):
        payload = make_payload(user_id=nonmoderator._id, permission_group='moderator')

        with capture_notifications() as notifications:
            res = app.post(url, payload, auth=nonmoderator.auth, expect_errors=True)
            assert res.status_code == 403

            res = app.post(url, payload, auth=moderator.auth, expect_errors=True)
            assert res.status_code == 403

        assert not notifications

    def test_POST_admin_success_existing_user(self, app, url, nonmoderator, moderator, admin, provider):
        payload = make_payload(user_id=nonmoderator._id, permission_group='moderator')
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == nonmoderator._id
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        assert len(notifications) == 1

    def test_POST_admin_failure_existing_moderator(self, app, url, moderator, admin, provider):
        payload = make_payload(user_id=moderator._id, permission_group='moderator')
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400

        assert not notifications

    def test_POST_admin_failure_unreg_moderator(self, app, url, moderator, nonmoderator, admin, provider):
        unreg_user = {'full_name': 'Jalen Hurts', 'email': '1eagles@allbatman.org'}
        # test_user_with_no_moderator_admin_permissions
        payload = make_payload(permission_group='moderator', **unreg_user)
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403
        assert not notifications

    def test_user_with_moderator_admin_permissions(self, app, url, moderator, nonmoderator, admin, provider):
        unreg_user = {'full_name': 'Slay', 'email': 'bigplayslay@allbatman.org'}
        payload = make_payload(permission_group='moderator', **unreg_user)
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)

        assert res.status_code == 201
        assert len(notifications) == 1
        email = notifications[0]['kwargs']['user'].email
        assert email == unreg_user['email']

    def test_POST_admin_failure_invalid_group(self, app, url, nonmoderator, moderator, admin, provider):
        payload = make_payload(user_id=nonmoderator._id, permission_group='citizen')
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400

        assert not notifications

    def test_POST_admin_success_email(self, app, url, nonmoderator, moderator, admin, provider):
        payload = make_payload(email='somenewuser@gmail.com', full_name='Some User', permission_group='moderator')
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        assert len(res.json['data']['id']) == 5
        assert res.json['data']['attributes']['permission_group'] == 'moderator'
        assert 'email' not in res.json['data']['attributes']
        assert len(notifications) == 1

    def test_moderators_alphabetically(self, app, url, admin, moderator, provider):
        admin.fullname = 'Flecher Cox'
        moderator.fullname = 'Jason Kelce'
        new_mod = AuthUserFactory(fullname='Jordan Mailata')
        provider.get_group('moderator').user_set.add(new_mod)
        admin.save()
        moderator.save()
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 3
        assert res.json['data'][0]['id'] == admin._id
        assert res.json['data'][1]['id'] == moderator._id
        assert res.json['data'][2]['id'] == new_mod._id
