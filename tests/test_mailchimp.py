# -*- coding: utf-8 -*-

import mock
from website import mailchimp_utils, settings
from tests.base import OsfTestCase
from nose.tools import *  # noqa; PEP8 asserts
from tests.factories import UserFactory
import mailchimp


class TestMailChimpHelpers(OsfTestCase):

    def setUp(self):
        super(TestMailChimpHelpers, self).setUp()
        self._enable_email_subscriptions_original = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True

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
        mailchimp_utils.subscribe_mailchimp(list_name, user)
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
        mailchimp_utils.subscribe_mailchimp(list_name, user)
        assert_false(user.mailing_lists[list_name])

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 2, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        mailchimp_utils.unsubscribe_mailchimp(list_name, user)
        mock_client.lists.unsubscribe.assert_called_with(id=list_id, email={'email': user.username})

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_subscriber_email(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        # subscribe user
        mailchimp_utils.subscribe_mailchimp(list_name, user)

        # update subscriber email
        old_username = user.username
        user.username = 'foo@fizzbuzz.com'
        user.save()
        mailchimp_utils.update_subscriber_email(user, old_username=old_username)
        mock_client.lists.update_member.assert_called_with(id=list_id, email={'email': old_username}, merge_vars={'email': user.username})

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_subscriber_email_for_user_unsubscribed_from_list(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}

        # user is subscribed in the db, but not on mailchimp
        user.mailing_lists[list_name] = True

        # update subscriber email
        old_username = user.username
        user.username = 'foobar@fizzbuzz.com'
        user.save()
        mock_client.lists.update_member.side_effect = mailchimp.ListNotSubscribedError
        mailchimp_utils.update_subscriber_email(user, old_username=old_username)
        assert_false(user.mailing_lists[list_name])

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_subscriber_email_not_found_in_list(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}

        # user is subscribed in the db, but not on mailchimp
        user.mailing_lists[list_name] = True

        # update subscriber email
        old_username = user.username
        user.username = 'foofoo@fizzbuzz.com'
        user.save()
        mock_client.lists.update_member.side_effect = mailchimp.EmailNotExistsError
        mailchimp_utils.update_subscriber_email(user, old_username=old_username)
        assert_false(user.mailing_lists[list_name])

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_subscriber_email_invalid_new_email(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}

        # subscribe user
        mailchimp_utils.subscribe_mailchimp(list_name, user)

        # update subscriber email
        old_username = user.username
        user.username = 'test+1@test.com'
        user.save()
        mock_client.lists.update_member.side_effect = mailchimp.ListMergeFieldRequiredError
        mailchimp_utils.update_subscriber_email(user, old_username=old_username)
        assert_false(user.mailing_lists[list_name])

    def tearDown(self):
        super(TestMailChimpHelpers, self).tearDown()
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = self._enable_email_subscriptions_original