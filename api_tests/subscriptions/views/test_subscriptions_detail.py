import pytest
from django.contrib.contenttypes.models import ContentType

from api.base.settings.defaults import API_BASE
from osf.models import NotificationType, OSFUser, AbstractNode
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    NotificationSubscriptionFactory,
)

@pytest.mark.django_db
class TestSubscriptionDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_without_permission(self):
        return NodeFactory()

    @pytest.fixture()
    def user_no_auth(self):
        return AuthUserFactory()

    @pytest.fixture()
    def notification(self, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.USER_FILE_UPDATED.instance,
            object_id=user.id,
            content_type_id=ContentType.objects.get_for_model(OSFUser).id,
            user=user,
            _is_digest=True,
            message_frequency='daily',
        )

    @pytest.fixture()
    def notification_user_global_reviews(self, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.instance,
            object_id=user.id,
            content_type_id=ContentType.objects.get_for_model(OSFUser).id,
            user=user,
            _is_digest=True,
            message_frequency='daily',
        )

    @pytest.fixture()
    def notification_node_file_updated(self, node, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance,
            object_id=node.id,
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id,
            user=user,
            _is_digest=True,
            message_frequency='daily',
        )

    @pytest.fixture()
    def url(self, user):
        return f'/{API_BASE}subscriptions/{user._id}_global_file_updated/'

    @pytest.fixture()
    def url_user_global_reviews(self, user):
        return f'/{API_BASE}subscriptions/{user._id}_global_reviews/'

    @pytest.fixture()
    def url_node_file_updated(self, node):
        return f'/{API_BASE}subscriptions/{node._id}_file_updated/'

    @pytest.fixture()
    def url_node_file_updated_not_found(self):
        return f'/{API_BASE}subscriptions/12345_file_updated/'

    @pytest.fixture()
    def url_node_file_updated_without_permission(self, node_without_permission):
        return f'/{API_BASE}subscriptions/{node_without_permission._id}_file_updated/'

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

    def test_node_file_updated_subscription_detail_success(self, app, user, node, notification_node_file_updated, url_node_file_updated):
        res = app.get(url_node_file_updated, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{node._id}_file_updated'

    def test_node_file_updated_subscription_detail_not_found(self, app, user, node, notification_node_file_updated, url_node_file_updated_not_found):
        res = app.get(url_node_file_updated_not_found, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_node_file_updated_subscription_detail_no_permission(self, app, user, node, notification_node_file_updated, url_node_file_updated_without_permission):
        res = app.get(url_node_file_updated_without_permission, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

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
            expect_errors=True,
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
