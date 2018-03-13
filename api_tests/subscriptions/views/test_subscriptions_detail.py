import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory, NotificationSubscriptionFactory


@pytest.mark.django_db
class TestSubscriptionDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_no_auth(self):
        return AuthUserFactory()

    @pytest.fixture()
    def global_user_notification(self, user):
        notification = NotificationSubscriptionFactory(_id='{}_global'.format(user._id), user=user, event_name='global')
        notification.add_user_to_subscription(user, 'email_transactional')
        return notification

    @pytest.fixture()
    def url(self, global_user_notification):
        return '/{}subscriptions/{}/'.format(API_BASE, global_user_notification._id)

    @pytest.fixture()
    def url_invalid(self):
        return '/{}subscriptions/{}/'.format(API_BASE, 'invalid-notification-id')

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-provider-subscription',
                'attributes': {
                    'frequency': 'none'
                }
            }
        }

    @pytest.fixture()
    def payload_invalid(self):
        return {
            'data': {
                'type': 'user-provider-subscription',
                'attributes': {
                    'frequency': 'invalid-frequency'
                }
            }
        }

    def test_subscription_detail(self, app, user, user_no_auth, global_user_notification, url, url_invalid, payload, payload_invalid):
        # GET with valid notification_id
        # Invalid user
        res = app.get(url, auth=user_no_auth.auth, expect_errors=True)
        assert res.status_code == 403
        # No user
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        # Valid user
        res = app.get(url, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == '{}_global'.format(user._id)

        # GET with invalid notification_id
        # No user
        res = app.get(url_invalid, expect_errors=True)
        assert res.status_code == 404
        # Existing user
        res = app.get(url_invalid, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # PATCH with valid notification_id and invalid data
        # Invalid user
        res = app.patch_json_api(url, payload_invalid, auth=user_no_auth.auth, expect_errors=True)
        assert res.status_code == 403
        # No user
        res = app.patch_json_api(url, payload_invalid, expect_errors=True)
        assert res.status_code == 401
        # Valid user
        res = app.patch_json_api(url, payload_invalid, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid frequency "invalid-frequency"'

        # PATCH with invalid notification_id
        # No user
        res = app.patch_json_api(url_invalid, payload, expect_errors=True)
        assert res.status_code == 404
        # Existing user
        res = app.patch_json_api(url_invalid, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # PATCH with valid notification_id and valid data
        # Invalid user
        res = app.patch_json_api(url, payload, auth=user_no_auth.auth, expect_errors=True)
        assert res.status_code == 403
        # No user
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401
        # Valid user
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['frequency'] == 'none'
