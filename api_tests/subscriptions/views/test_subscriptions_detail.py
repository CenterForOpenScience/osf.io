import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory, NotificationSubscriptionFactory


@pytest.mark.django_db
class TestSubscriptionDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def global_user_notification(self, user):
        notification = NotificationSubscriptionFactory(_id='{}_global'.format(user._id), user=user, event_name='global')
        notification.add_user_to_subscription(user, 'email_transactional')
        return notification

    @pytest.fixture()
    def url(self, user, global_user_notification):
        return '/{}subscriptions/{}/'.format(API_BASE, global_user_notification._id)

    def test_retrieve_successful(self, app, user, global_user_notification, url):
        res = app.get(url, auth=user.auth)
        notification_id = res.json['data']['id']
        assert notification_id == '{}_global'.format(user._id)

    def test_unauthenticated(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_update_successful(self, app, user, global_user_notification, url):
        payload = {
            'data': {
                'type': 'user-provider-subscription',
                'attributes': {
                    'frequency': 'none'
                }
            }
        }
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.json['data']['attributes']['frequency'] == 'none'

    def test_update_with_invalid_frequency(self, app, user, global_user_notification, url):
        payload = {
            'data': {
                'type': 'user-provider-subscription',
                'attributes': {
                    'frequency': 'invalid-frequency'
                }
            }
        }
        res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
