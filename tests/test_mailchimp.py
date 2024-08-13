from hashlib import md5
from unittest import mock
import pytest
from mailchimp3.mailchimpclient import MailChimpError

from framework.celery_tasks import handlers
from osf_tests.factories import UserFactory
from tests.base import OsfTestCase
from website import mailchimp_utils
from website.settings import MAILCHIMP_GENERAL_LIST, MAILCHIMP_LIST_MAP


@pytest.mark.enable_enqueue_task
class TestMailChimpHelpers(OsfTestCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        with self.context:
            handlers.celery_before_request()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_get_list_name_from_id(self, mock_get_mailchimp_api):
        list_id = '12345'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': 'foo'}
        list_name = mailchimp_utils.get_list_name_from_id(list_id)
        mock_client.lists.get.assert_called_with(list_id=list_id)
        assert list_name == 'foo'

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_called(self, mock_get_mailchimp_api):
        list_name = MAILCHIMP_GENERAL_LIST
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        mailchimp_utils.subscribe_mailchimp(list_name, user._id)
        handlers.celery_teardown_request()
        mock_client.lists.members.create_or_update.assert_called()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_fake_email_does_not_throw_validation_error(self, mock_get_mailchimp_api):
        list_name = MAILCHIMP_GENERAL_LIST
        user = UserFactory(username='fake@fake.com')
        assert list_name not in user.mailchimp_mailing_lists
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.members.create_or_update.side_effect = MailChimpError
        mailchimp_utils.subscribe_mailchimp(list_name, user._id)
        handlers.celery_teardown_request()
        user.reload()
        assert not user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = MAILCHIMP_GENERAL_LIST
        list_id = MAILCHIMP_LIST_MAP[MAILCHIMP_GENERAL_LIST]
        user = UserFactory()
        user_hash = md5(user.username.lower().encode()).hexdigest()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mailchimp_utils.unsubscribe_mailchimp_async(list_name, user._id)
        handlers.celery_teardown_request()
        mock_client.lists.members.delete.assert_called_with(list_id=list_id, subscriber_hash=user_hash)

