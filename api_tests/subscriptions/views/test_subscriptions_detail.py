import pytest
from django.contrib.contenttypes.models import ContentType

from api.base.settings.defaults import API_BASE
from osf.models import NotificationType
from osf_tests.factories import (
    AuthUserFactory,
    NotificationSubscriptionFactory
)

@pytest.mark.django_db
class TestSubscriptionDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_no_auth(self):
        return AuthUserFactory()

    @pytest.fixture()
    def notification(self, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.USER_FILE_UPDATED.instance,
            object_id=user.id,
            content_type_id=ContentType.objects.get_for_model(user).id,
            user=user
        )

    @pytest.fixture()
    def url(self, notification):
        return f'/{API_BASE}subscriptions/{notification._id}/'

    @pytest.fixture()
    def url_invalid(self):
        return f'/{API_BASE}subscriptions/invalid-notification-id/'

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

    def test_subscription_detail_invalid_user(self, app, user, user_no_auth, notification, url, payload):
        res = app.get(
            url,
            auth=user_no_auth.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_subscription_detail_no_user(
            self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.get(
            url,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_subscription_detail_valid_user(
            self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):

        res = app.get(url, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{user._id}_global_file_updated'

    def test_subscription_detail_invalid_notification_id_no_user(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.get(url_invalid, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_invalid_notification_id_existing_user(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.get(
            url_invalid,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_subscription_detail_invalid_payload_403(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url, payload_invalid, auth=user_no_auth.auth, expect_errors=True)
        assert res.status_code == 403

    def test_subscription_detail_invalid_payload_401(
            self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url, payload_invalid, expect_errors=True)
        assert res.status_code == 401

    def test_subscription_detail_invalid_payload_400(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(
            url,
            payload_invalid,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == ('"invalid-frequency" is not a valid choice.')

    def test_subscription_detail_patch_invalid_notification_id_no_user(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_invalid, payload, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_patch_invalid_notification_id_existing_user(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_invalid, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_patch_invalid_user(
            self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url, payload, auth=user_no_auth.auth, expect_errors=True)
        assert res.status_code == 403

    def test_subscription_detail_patch_no_user(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

    def test_subscription_detail_patch(
        self, app, user, user_no_auth, notification, url, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['frequency'] == 'none'
