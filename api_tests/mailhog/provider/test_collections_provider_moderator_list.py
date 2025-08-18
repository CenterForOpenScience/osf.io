import pytest
from waffle.testutils import override_switch
from osf import features
from api.base.settings.defaults import API_BASE
from osf.models import NotificationType
from osf_tests.factories import (
    AuthUserFactory,
    CollectionProviderFactory,
)
from osf.utils import permissions
from tests.utils import get_mailhog_messages, delete_mailhog_messages, capture_notifications


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
class TestPOSTCollectionsModeratorList:

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_POST_admin_success_existing_user(self, app, url, nonmoderator, moderator, admin, provider):
        payload = make_payload(user_id=nonmoderator._id, permission_group='moderator')
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_MODERATOR_ADDED
        assert res.status_code == 201
        assert res.json['data']['id'] == nonmoderator._id
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_POST_admin_failure_unreg_moderator(self, app, url, moderator, nonmoderator, admin, provider):
        delete_mailhog_messages()
        unreg_user = {'full_name': 'Jalen Hurts', 'email': '1eagles@allbatman.org'}
        # test_user_with_no_moderator_admin_permissions
        payload = make_payload(permission_group='moderator', **unreg_user)
        with capture_notifications(passthrough=True) as notifications:
            res = app.post_json_api(url, payload, auth=nonmoderator.auth, expect_errors=True)
        assert notifications == {'emails': [], 'emits': []}
        assert res.status_code == 403
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()
        # test_user_with_moderator_admin_permissions
        payload = make_payload(permission_group='moderator', **unreg_user)
        with capture_notifications(passthrough=True) as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)

        assert res.status_code == 201
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_CONFIRM_EMAIL_MODERATION
        assert notifications['emits'][0]['kwargs']['user'].username == unreg_user['email']

        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_POST_admin_success_email(self, app, url, nonmoderator, moderator, admin, provider):
        delete_mailhog_messages()
        payload = make_payload(email='somenewuser@gmail.com', full_name='Some User', permission_group='moderator')
        with capture_notifications(passthrough=True) as notifications:
            res = app.post_json_api(url, payload, auth=admin.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_CONFIRM_EMAIL_MODERATION
        assert res.status_code == 201
        assert len(res.json['data']['id']) == 5
        assert res.json['data']['attributes']['permission_group'] == 'moderator'
        assert 'email' not in res.json['data']['attributes']

        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()
