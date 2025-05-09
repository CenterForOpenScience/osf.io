import unittest
from unittest import mock
import pytest
from rest_framework import status as http_status
from framework.celery_tasks import handlers
from osf_tests.factories import (
    AuthUserFactory,
    UserFactory,
)
from tests.base import (
    OsfTestCase,
)
from website import mailchimp_utils, settings
from website.settings import MAILCHIMP_GENERAL_LIST
from website.util import api_url_for

@pytest.mark.enable_enqueue_task
class TestConfigureMailingListViews(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._original_enable_email_subscriptions = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True

    def test_user_unsubscribe_and_subscribe_help_mailing_list(self):
        user = AuthUserFactory()
        url = api_url_for('user_choose_mailing_lists')
        payload = {settings.OSF_HELP_LIST: False}
        res = self.app.post(url, json=payload, auth=user.auth)
        user.reload()

        assert not user.osf_mailing_lists[settings.OSF_HELP_LIST]

        payload = {settings.OSF_HELP_LIST: True}
        res = self.app.post(url, json=payload, auth=user.auth)
        user.reload()

        assert user.osf_mailing_lists[settings.OSF_HELP_LIST]

    def test_get_notifications(self):
        user = AuthUserFactory()
        mailing_lists = dict(list(user.osf_mailing_lists.items()) + list(user.mailchimp_mailing_lists.items()))
        url = api_url_for('user_notifications')
        res = self.app.get(url, auth=user.auth)
        assert mailing_lists == res.json['mailing_lists']

    @unittest.skipIf(settings.USE_CELERY, 'Subscription must happen synchronously for this test')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_user_choose_mailing_lists_updates_user_dict(self, mock_get_mailchimp_api):
        user = AuthUserFactory()
        list_name = MAILCHIMP_GENERAL_LIST
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        payload = {settings.MAILCHIMP_GENERAL_LIST: True}
        url = api_url_for('user_choose_mailing_lists')
        res = self.app.post(url, json=payload, auth=user.auth)
        # the test app doesn't have celery handlers attached, so we need to call this manually.
        handlers.celery_teardown_request()
        user.reload()

        # check user.mailing_lists is updated
        assert user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST]
        assert user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST] == payload[settings.MAILCHIMP_GENERAL_LIST]

        # check that user is subscribed
        mock_client.lists.members.create_or_update.assert_called()

    def test_get_mailchimp_get_endpoint_returns_200(self):
        url = api_url_for('mailchimp_get_endpoint')
        res = self.app.get(url)
        assert res.status_code == 200

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_mailchimp_webhook_subscribe_action_does_not_change_user(self, mock_get_mailchimp_api):
        """ Test that 'subscribe' actions sent to the OSF via mailchimp
            webhooks update the OSF database.
        """
        list_id = '12345'
        list_name = MAILCHIMP_GENERAL_LIST
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': list_name}

        # user is not subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {MAILCHIMP_GENERAL_LIST: False}
        user.save()

        # user subscribes and webhook sends request to OSF
        data = {
            'type': 'subscribe',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_mailchimp_webhook_profile_action_does_not_change_user(self, mock_get_mailchimp_api):
        """ Test that 'profile' actions sent to the OSF via mailchimp
            webhooks do not cause any database changes.
        """
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': list_id, 'name': list_name}]}

        # user is subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {'OSF General': True}
        user.save()

        # user hits subscribe again, which will update the user's existing info on mailchimp
        # webhook sends request (when configured to update on changes made through the API)
        data = {
            'type': 'profile',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field does not change
        user.reload()
        assert user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_sync_data_from_mailchimp_unsubscribes_user(self, mock_get_mailchimp_api):
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': list_name}

        # user is subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {'OSF General': True}
        user.save()

        # user unsubscribes through mailchimp and webhook sends request
        data = {
            'type': 'unsubscribe',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert not user.mailchimp_mailing_lists[list_name]

    def test_sync_data_from_mailchimp_fails_without_secret_key(self):
        user = AuthUserFactory()
        payload = {'values': {'type': 'unsubscribe',
                              'data': {'list_id': '12345',
                                       'email': 'freddie@cos.io'}}}
        url = api_url_for('sync_data_from_mailchimp')
        res = self.app.post(url, json=payload, auth=user.auth)
        assert res.status_code == http_status.HTTP_401_UNAUTHORIZED

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = cls._original_enable_email_subscriptions
