import pytest
from django.contrib.contenttypes.models import ContentType

from api.base.settings.defaults import API_BASE
from osf.models.notification_type import NotificationType
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
    ProjectFactory,
    NotificationSubscriptionFactory
)


@pytest.mark.django_db
class TestSubscriptionList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider(self, user):
        provider = PreprintProviderFactory()
        provider.add_to_group(user, 'moderator')
        return provider

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def global_user_notification(self, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.USER_FILE_UPDATED.instance,
            object_id=user.id,
            content_type_id=ContentType.objects.get_for_model(user).id,
            user=user,
        )

    @pytest.fixture()
    def file_updated_notification(self, node, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance,
            object_id=node.id,
            content_type_id=ContentType.objects.get_for_model(node).id,
            user=user,
        )

    @pytest.fixture()
    def provider_notification(self, provider, user):
        return NotificationSubscriptionFactory(
            notification_type=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.instance,
            object_id=provider.id,
            content_type_id=ContentType.objects.get_for_model(provider).id,
            subscribed_object=provider,
            user=user,
        )

    @pytest.fixture()
    def url(self, user, node):
        return f'/{API_BASE}subscriptions/'

    def test_list_complete(
            self,
            app,
            user,
            provider,
            node,
            url
    ):
        res = app.get(url, auth=user.auth)
        notification_ids = [item['id'] for item in res.json['data']]
        # There should only be 3 notifications: users' global, node's file updates and provider's preprint added.
        assert len(notification_ids) == 3
        assert f'{user._id}_global_file_updated' in notification_ids
        assert f'{provider._id}_new_pending_submissions' in notification_ids
        assert f'{node._id}_file_updated' in notification_ids

    def test_unauthenticated(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_cannot_post_patch_put_or_delete(self, app, url, user):
        post_res = app.post(url, expect_errors=True, auth=user.auth)
        patch_res = app.patch(url, expect_errors=True, auth=user.auth)
        put_res = app.put(url, expect_errors=True, auth=user.auth)
        delete_res = app.delete(url, expect_errors=True, auth=user.auth)
        assert post_res.status_code == 405
        assert patch_res.status_code == 405
        assert put_res.status_code == 405
        assert delete_res.status_code == 405

    def test_multiple_values_filter(self, app, url, user):
        res = app.get(url + '?filter[event_name]=comments,file_updated', auth=user.auth)
        assert len(res.json['data']) == 2
        for subscription in res.json['data']:
            subscription['attributes']['event_name'] in ['global', 'comments']

    def test_value_filter_id(
        self,
        app,
        url,
        user,
        node,
    ):
        # Request all subscriptions first, to confirm all are visible
        res = app.get(url, auth=user.auth)
        all_ids = [sub['id'] for sub in res.json['data']]
        assert len(all_ids) == 2
        assert f'{node._id}_file_updated' in all_ids
        assert f'{user._id}_global_file_updated' in all_ids

        # Now filter by a specific annotated legacy_id (the node file_updated one)
        target_id = f'{node._id}_file_updated'
        filtered_res = app.get(f'{url}?filter[id]={target_id}', auth=user.auth)

        # Response should contain exactly one record matching that legacy_id
        assert filtered_res.status_code == 200
        data = filtered_res.json['data']
        assert len(data) == 1
        assert data[0]['id'] == target_id

        # Confirm it’s the expected subscription object
        attributes = data[0]['attributes']
        assert attributes['event_name'] is None  # event names are legacy
        assert attributes['frequency'] in ['instantly', 'daily', 'none']
