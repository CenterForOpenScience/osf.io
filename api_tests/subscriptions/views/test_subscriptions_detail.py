import pytest

from django.contrib.contenttypes.models import ContentType

from api.base.settings.defaults import API_BASE
from osf.models import (
    AbstractNode,
    NotificationSubscription,
    NotificationType,
    OSFUser
)
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
    def user_missing_subscriptions(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_no_permission(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_missing_subscriptions(self, user_missing_subscriptions):
        node = NodeFactory(creator=user_missing_subscriptions)
        subscription = NotificationSubscription.objects.get(
            user=user_missing_subscriptions,
            notification_type__name=NotificationType.Type.NODE_FILE_UPDATED.value,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(AbstractNode)
        )
        subscription.delete()
        return node

    @pytest.fixture()
    def notification_user_global_file_updated(self, user):
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
            notification_type=NotificationType.Type.REVIEWS_SUBMISSION_STATUS.instance,
            object_id=user.id,
            content_type_id=ContentType.objects.get_for_model(OSFUser).id,
            user=user,
            _is_digest=True,
            message_frequency='daily',
        )

    @pytest.fixture()
    def url_user_global_file_updated(self, user):
        return f'/{API_BASE}subscriptions/{user._id}_global_file_updated/'

    @pytest.fixture()
    def url_user_global_reviews(self, user):
        return f'/{API_BASE}subscriptions/{user._id}_global_reviews/'

    @pytest.fixture()
    def url_user_global_file_updated_missing(self, user_missing_subscriptions):
        return f'/{API_BASE}subscriptions/{user_missing_subscriptions._id}_global_file_updated/'

    @pytest.fixture()
    def url_user_global_reviews_missing(self, user_missing_subscriptions):
        return f'/{API_BASE}subscriptions/{user_missing_subscriptions._id}_global_reviews/'

    @pytest.fixture()
    def url_node_file_updated(self, node):
        return f'/{API_BASE}subscriptions/{node._id}_files_updated/'

    @pytest.fixture()
    def url_node_file_updated_not_found(self):
        return f'/{API_BASE}subscriptions/12345_files_updated/'

    @pytest.fixture()
    def url_node_file_updated_without_permission(self, node_without_permission):
        return f'/{API_BASE}subscriptions/{node_without_permission._id}_files_updated/'

    @pytest.fixture()
    def url_node_file_updated_missing(self, node_missing_subscriptions):
        return f'/{API_BASE}subscriptions/{node_missing_subscriptions._id}_files_updated/'

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

    def test_user_global_subscription_detail_permission_denied(
            self,
            app,
            user,
            user_no_permission,
            notification_user_global_file_updated,
            notification_user_global_reviews,
            url_user_global_file_updated,
            url_user_global_reviews
    ):
        res = app.get(url_user_global_file_updated, auth=user_no_permission.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.get(url_user_global_reviews, auth=user_no_permission.auth, expect_errors=True)
        assert res.status_code == 403

    def test_user_global_subscription_detail_forbidden(
            self,
            app,
            user,
            user_no_permission,
            notification_user_global_file_updated,
            notification_user_global_reviews,
            url_user_global_file_updated,
            url_user_global_reviews
    ):
        res = app.get(url_user_global_file_updated, expect_errors=True)
        assert res.status_code == 401
        res = app.get(url_user_global_reviews, expect_errors=True)
        assert res.status_code == 401

    def test_user_global_subscription_detail_success(
            self,
            app,
            user,
            user_no_permission,
            notification_user_global_file_updated,
            notification_user_global_reviews,
            url_user_global_file_updated,
            url_user_global_reviews
    ):
        res = app.get(url_user_global_file_updated, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{user._id}_global_file_updated'
        res = app.get(url_user_global_reviews, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{user._id}_global_reviews'

    def test_user_global_file_updated_subscription_detail_missing_and_created(
            self,
            app,
            user_missing_subscriptions,
            url_user_global_file_updated_missing,
    ):
        assert not NotificationSubscription.objects.filter(
            user=user_missing_subscriptions,
            notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
            object_id=user_missing_subscriptions.id,
            content_type=ContentType.objects.get_for_model(OSFUser)
        ).exists()
        res = app.get(url_user_global_file_updated_missing, auth=user_missing_subscriptions.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{user_missing_subscriptions._id}_global_file_updated'

    def test_user_global_reviews_subscription_detail_missing_and_created(
            self,
            app,
            user_missing_subscriptions,
            url_user_global_reviews_missing,
    ):
        assert not NotificationSubscription.objects.filter(
            user=user_missing_subscriptions,
            notification_type__name=NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
            object_id=user_missing_subscriptions.id,
            content_type=ContentType.objects.get_for_model(OSFUser)
        ).exists()
        res = app.get(url_user_global_reviews_missing, auth=user_missing_subscriptions.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{user_missing_subscriptions._id}_global_reviews'

    def test_node_file_updated_subscription_detail_success(
            self,
            app,
            user,
            node,
            url_node_file_updated
    ):
        res = app.get(url_node_file_updated, auth=user.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{node._id}_files_updated'

    def test_node_file_updated_subscription_detail_missing_and_created(
            self,
            app,
            user_missing_subscriptions,
            node_missing_subscriptions,
            url_node_file_updated_missing,
    ):
        assert not NotificationSubscription.objects.filter(
            user=user_missing_subscriptions,
            notification_type__name=NotificationType.Type.NODE_FILE_UPDATED.value,
            object_id=node_missing_subscriptions.id,
            content_type=ContentType.objects.get_for_model(AbstractNode)
        ).exists()
        res = app.get(url_node_file_updated_missing, auth=user_missing_subscriptions.auth)
        notification_id = res.json['data']['id']
        assert res.status_code == 200
        assert notification_id == f'{node_missing_subscriptions._id}_files_updated'

    def test_node_file_updated_subscription_detail_not_found(
            self,
            app,
            user,
            node,
            url_node_file_updated_not_found
    ):
        res = app.get(url_node_file_updated_not_found, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_node_file_updated_subscription_detail_permission_denied(
            self,
            app,
            user,
            user_no_permission,
            node,
            url_node_file_updated
    ):
        res = app.get(url_node_file_updated, auth=user_no_permission.auth, expect_errors=True)
        assert res.status_code == 403

    def test_node_file_updated_subscription_detail_forbidden(
            self,
            app,
            user,
            node,
            url_node_file_updated
    ):
        res = app.get(url_node_file_updated, expect_errors=True)
        assert res.status_code == 401

    def test_subscription_detail_invalid_notification_id_no_user(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.get(url_invalid, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_invalid_notification_id_existing_user(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.get(
            url_invalid,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_subscription_detail_invalid_payload_403(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_user_global_file_updated, payload_invalid, auth=user_no_permission.auth, expect_errors=True)
        assert res.status_code == 403

    def test_subscription_detail_invalid_payload_401(
            self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_user_global_file_updated, payload_invalid, expect_errors=True)
        assert res.status_code == 401

    def test_subscription_detail_invalid_payload_400(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(
            url_user_global_file_updated,
            payload_invalid,
            auth=user.auth,
            expect_errors=True,
        )

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == ('"invalid-frequency" is not a valid choice.')

    def test_subscription_detail_patch_invalid_notification_id_no_user(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_invalid, payload, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_patch_invalid_notification_id_existing_user(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_invalid, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_subscription_detail_patch_invalid_user(
            self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_user_global_file_updated, payload, auth=user_no_permission.auth, expect_errors=True)
        assert res.status_code == 403

    def test_subscription_detail_patch_no_user(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):
        res = app.patch_json_api(url_user_global_file_updated, payload, expect_errors=True)
        assert res.status_code == 401

    def test_subscription_detail_patch(
        self, app, user, user_no_permission, notification_user_global_file_updated, url_user_global_file_updated, url_invalid, payload, payload_invalid
    ):

        res = app.patch_json_api(url_user_global_file_updated, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['frequency'] == 'none'
