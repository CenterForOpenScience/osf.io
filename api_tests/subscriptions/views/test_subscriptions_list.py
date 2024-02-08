import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory, PreprintProviderFactory, ProjectFactory, NotificationSubscriptionFactory


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
        notification = NotificationSubscriptionFactory(_id=f'{user._id}_global', user=user, event_name='global')
        notification.add_user_to_subscription(user, 'email_transactional')
        return notification

    @pytest.fixture()
    def url(self, user, node):
        return f'/{API_BASE}subscriptions/'

    def test_list_complete(self, app, user, provider, node, global_user_notification, url):
        res = app.get(url, auth=user.auth)
        notification_ids = [item['id'] for item in res.json['data']]
        # There should only be 4 notifications: users' global, node's comments, node's file updates and provider's preprint added.
        assert len(notification_ids) == 4
        assert f'{user._id}_global' in notification_ids
        assert f'{provider._id}_new_pending_submissions' in notification_ids
        assert f'{node._id}_comments' in notification_ids
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
