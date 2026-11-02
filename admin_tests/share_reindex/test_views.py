from unittest import mock

import pytest
from django.test import RequestFactory

from admin.share_reindex import views
from admin_tests.utilities import setup_view
from osf.models import SpamStatus
from osf_tests.factories import AuthUserFactory, UserFactory
from website.settings import CeleryConfig

pytestmark = pytest.mark.django_db


@pytest.fixture()
def req():
    req = RequestFactory().get('/fake_path', {'type': 'users'})
    req.user = AuthUserFactory()
    return req


class TestFailedShareIndexedGuidList:

    def test_users_list_hides_opted_out_users(self, req):
        default_user = UserFactory()
        opted_in_user = UserFactory(allow_indexing=True)
        opted_out_user = UserFactory(allow_indexing=False)

        view = setup_view(views.FailedShareIndexedGuidList(), req)
        listed_guids = {item['first_guid'] for item in view.get_queryset()}
        assert {default_user._id, opted_in_user._id} <= listed_guids
        assert opted_out_user._id not in listed_guids

    def test_users_list_hides_spam_users(self, req):
        default_user = UserFactory()
        spam_user = UserFactory(spam_status=SpamStatus.SPAM)
        assert spam_user.is_active
        view = setup_view(views.FailedShareIndexedGuidList(), req)
        listed_guids = {item['first_guid'] for item in view.get_queryset()}
        assert {default_user._id} <= listed_guids
        assert spam_user._id not in listed_guids


@pytest.mark.urls('admin.base.urls')
class TestFailedShareIndexedGuidReindex:

    @mock.patch('admin.share_reindex.views.task__reindex_failed_or_not_indexed_resource_into_share')
    def test_reindex_all_users_runs_on_low_priority_queue(self, mock_reindex_task, req):
        view = setup_view(views.FailedShareIndexedGuidReindex(), req, resource_type='users')
        view.post(req)
        mock_reindex_task.apply_async.assert_called_once_with(args=('users',), queue=CeleryConfig.task_low_queue)
