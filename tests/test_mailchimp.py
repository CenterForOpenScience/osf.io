# -*- coding: utf-8 -*-
import mock
from website import mailchimp_utils
from tests.base import OsfTestCase
from nose.tools import *  # noqa; PEP8 asserts
from tests.factories import UserFactory
import mailchimp

from framework.tasks import handlers

class TestMailChimpHelpers(OsfTestCase):

    def setUp(self, *args, **kwargs):
        super(TestMailChimpHelpers, self).setUp(*args, **kwargs)
        with self.context:
            handlers.celery_before_request()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_get_list_id_from_name(self, mock_get_mailchimp_api):
        list_name = 'foo'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        mock_client.lists.list.assert_called_with(filters={'list_name': list_name})
        assert_equal(list_id, 1)

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_get_list_name_from_id(self, mock_get_mailchimp_api):
        list_id = '12345'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': list_id, 'name': 'foo'}]}
        list_name = mailchimp_utils.get_list_name_from_id(list_id)
        mock_client.lists.list.assert_called_with(filters={'list_id': list_id})
        assert_equal(list_name, 'foo')

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        mailchimp_utils.subscribe_mailchimp(list_name, user._id)
        handlers.celery_teardown_request()
        mock_client.lists.subscribe.assert_called_with(
            id=list_id,
            email={'email': user.username},
            merge_vars={
                'fname': user.given_name,
                'lname': user.family_name,
            },
            double_optin=False,
            update_existing=True,
        )

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_fake_email_does_not_throw_validation_error(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory(username='fake@fake.com')
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        mock_client.lists.subscribe.side_effect = mailchimp.ValidationError
        mailchimp_utils.subscribe_mailchimp(list_name, user._id)
        handlers.celery_teardown_request()
        assert_false(user.mailchimp_mailing_lists[list_name])

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 2, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        mailchimp_utils.unsubscribe_mailchimp_async(list_name, user._id)
        handlers.celery_teardown_request()
        mock_client.lists.unsubscribe.assert_called_with(id=list_id, email={'email': user.username}, send_goodbye=True)

