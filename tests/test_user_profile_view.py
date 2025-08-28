#!/usr/bin/env python3
"""Views tests for the OSF."""
from hashlib import md5
from unittest import mock

import pytest
from rest_framework import status as http_status

from addons.github.tests.factories import GitHubAccountFactory
from framework.celery_tasks import handlers
from osf.external.spam import tasks as spam_tasks
from osf.models import NotableDomain, NotificationType
from osf_tests.factories import (
    fake_email,
    ApiOAuth2ApplicationFactory,
    ApiOAuth2PersonalTokenFactory,
    AuthUserFactory,
    RegionFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from tests.utils import capture_notifications
from website import mailchimp_utils
from website.settings import MAILCHIMP_GENERAL_LIST
from website.util import api_url_for, web_url_for


@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
class TestUserProfile(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

    def test_unserialize_social(self):
        url = api_url_for('unserialize_social')
        payload = {
            'profileWebsites': ['http://frozen.pizza.com/reviews'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        with mock.patch.object(spam_tasks.requests, 'head'):
            resp = self.app.put(
                url,
                json=payload,
                auth=self.user.auth,
            )

        self.user.reload()
        for key, value in payload.items():
            assert self.user.social[key] == value
        assert self.user.social['researcherId'] is None

        assert NotableDomain.objects.all()
        assert NotableDomain.objects.get(domain='frozen.pizza.com')

    # Regression test for help-desk ticket
    def test_making_email_primary_is_not_case_sensitive(self):
        user = AuthUserFactory(username='fred@queen.test')
        # make confirmed email have different casing
        email = user.emails.first()
        email.address = email.address.capitalize()
        email.save()
        url = api_url_for('update_user')
        res = self.app.put(
            url,
            json={'id': user._id, 'emails': [{'address': 'fred@queen.test', 'primary': True, 'confirmed': True}]},
            auth=user.auth
        )
        assert res.status_code == 200

    def test_unserialize_social_validation_failure(self):
        url = api_url_for('unserialize_social')
        # profileWebsites URL is invalid
        payload = {
            'profileWebsites': ['http://goodurl.com', 'http://invalidurl'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        res = self.app.put(
            url,
            json=payload,
            auth=self.user.auth,

        )
        assert res.status_code == 400
        assert res.json['message_long'] == 'Invalid personal URL.'

    def test_serialize_social_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        with mock.patch.object(spam_tasks.requests, 'head'):
            self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert res.json.get('twitter') == 'howtopizza'
        assert res.json.get('profileWebsites') == ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        assert res.json.get('github') is None
        assert res.json['editable']

    def test_serialize_social_not_editable(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        with mock.patch.object(spam_tasks.requests, 'head'):
            self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        with mock.patch.object(spam_tasks.requests, 'head'):
            res = self.app.get(
                url,
                auth=user2.auth,
            )
        assert res.json.get('twitter') == 'howtopizza'
        assert res.json.get('profileWebsites') == ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        assert res.json.get('github') is None
        assert not res.json['editable']

    def test_serialize_social_addons_editable(self):
        self.user.add_addon('github')
        github_account = GitHubAccountFactory()
        github_account.save()
        self.user.external_accounts.add(github_account)
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert res.json['addons']['github'] == 'abc'

    def test_serialize_social_addons_not_editable(self):
        user2 = AuthUserFactory()
        self.user.add_addon('github')
        github_account = GitHubAccountFactory()
        github_account.save()
        self.user.external_accounts.add(github_account)
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert 'addons' not in res.json

    def test_unserialize_and_serialize_jobs(self):
        jobs = [{
            'institution': 'an institution',
            'department': 'a department',
            'title': 'a title',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'department': None,
            'title': None,
            'startMonth': 'May',
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert len(self.user.jobs) == 2
        url = api_url_for('serialize_jobs')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(jobs):
            assert job == res.json['contents'][i]

    def test_unserialize_and_serialize_schools(self):
        schools = [{
            'institution': 'an institution',
            'department': 'a department',
            'degree': 'a degree',
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'department': None,
            'degree': None,
            'startMonth': 5,
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': schools}
        url = api_url_for('unserialize_schools')
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert len(self.user.schools) == 2
        url = api_url_for('serialize_schools')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(schools):
            assert job == res.json['contents'][i]

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_jobs(self, mock_check_spam):
        jobs = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'title': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # jobs field is updated
        assert self.user.jobs == jobs
        assert mock_check_spam.called

    def test_unserialize_names(self):
        fake_fullname_w_spaces = f'    {fake.name()}    '
        names = {
            'full': fake_fullname_w_spaces,
            'given': 'Tea',
            'middle': 'Gray',
            'family': 'Pot',
            'suffix': 'Ms.',
        }
        url = api_url_for('unserialize_names')
        res = self.app.put(url, json=names, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # user is updated
        assert self.user.fullname == fake_fullname_w_spaces.strip()
        assert self.user.given_name == names['given']
        assert self.user.middle_names == names['middle']
        assert self.user.family_name == names['family']
        assert self.user.suffix == names['suffix']

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_schools(self, mock_check_spam):
        schools = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'degree': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': schools}
        url = api_url_for('unserialize_schools')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # schools field is updated
        assert self.user.schools == schools
        assert mock_check_spam.called

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_jobs_valid(self, mock_check_spam):
        jobs = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'title': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        assert mock_check_spam.called

    def test_update_user_timezone(self):
        assert self.user.timezone == 'Etc/UTC'
        payload = {'timezone': 'America/New_York', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.timezone == 'America/New_York'

    def test_update_user_locale(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': 'de_DE', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'de_DE'

    def test_update_user_locale_none(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': None, 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'en_US'

    def test_update_user_locale_empty_string(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': '', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'en_US'

    def test_cannot_update_user_without_user_id(self):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        header = {'emails': [{'address': user1.username}]}
        res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == '"id" is required'

    def test_add_emails_return_emails(self):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'emails': [{'address': user1.username, 'primary': True, 'confirmed': True},
                             {'address': email, 'primary': False, 'confirmed': False}
                  ]}
        with capture_notifications():
            res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 200
        assert 'emails' in res.json['profile']
        assert len(res.json['profile']['emails']) == 2

    def test_resend_confirmation_return_emails(self):
        user1 = AuthUserFactory()
        url = api_url_for('resend_confirmation')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'email': {'address': email, 'primary': False, 'confirmed': False}
                  }
        with capture_notifications():
            res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 200
        assert 'emails' in res.json['profile']
        assert len(res.json['profile']['emails']) == 2

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_user_mailing_lists(self, mock_get_mailchimp_api):
        email = fake_email()
        email_hash = md5(email.lower().encode()).hexdigest()
        self.user.emails.create(address=email)
        list_name = MAILCHIMP_GENERAL_LIST
        self.user.mailchimp_mailing_lists[list_name] = True
        self.user.save()
        user_hash = md5(self.user.username.lower().encode()).hexdigest()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put(url, json=payload, auth=self.user.auth)
        # the test app doesn't have celery handlers attached, so we need to call this manually.
        handlers.celery_teardown_request()

        assert mock_client.lists.members.delete.called
        mock_client.lists.members.delete.assert_called_with(
            list_id=list_id,
            subscriber_hash=user_hash
        )
        mock_client.lists.members.create_or_update.assert_called_with(
            list_id=list_id,
            subscriber_hash=email_hash,
            data={
                'status': 'subscribed',
                'status_if_new': 'subscribed',
                'email_address': email,
                'merge_fields': {
                    'FNAME': self.user.given_name,
                    'LNAME': self.user.family_name
                }
            }
        )
        handlers.celery_teardown_request()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_mailchimp_not_called_if_user_not_subscribed(self, mock_get_mailchimp_api):
        email = fake_email()
        self.user.emails.create(address=email)
        list_name = MAILCHIMP_GENERAL_LIST
        self.user.mailchimp_mailing_lists[list_name] = False
        self.user.save()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put(url, json=payload, auth=self.user.auth)

        assert mock_client.lists.members.delete.call_count == 0
        assert mock_client.lists.members.create_or_update.call_count == 0
        handlers.celery_teardown_request()

    def test_user_update_region(self):
        user_settings = self.user.get_addon('osfstorage')
        assert user_settings.default_region_id == 1

        url = '/api/v1/profile/region/'
        auth = self.user.auth
        region = RegionFactory(name='Frankfort', _id='eu-central-1')
        payload = {'region_id': 'eu-central-1'}

        res = self.app.put(url, json=payload, auth=auth)
        user_settings.reload()
        assert user_settings.default_region_id == region.id

    def test_user_update_region_missing_region_id_key(self):
        url = '/api/v1/profile/region/'
        auth = self.user.auth
        region = RegionFactory(name='Frankfort', _id='eu-central-1')
        payload = {'bad_key': 'eu-central-1'}

        res = self.app.put(url, json=payload, auth=auth)
        assert res.status_code == 400

    def test_user_update_region_missing_bad_region(self):
        url = '/api/v1/profile/region/'
        auth = self.user.auth
        payload = {'region_id': 'bad-region-1'}

        res = self.app.put(url, json=payload, auth=auth)
        assert res.status_code == 404

class TestUserProfileApplicationsPage(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.platform_app = ApiOAuth2ApplicationFactory(owner=self.user)
        self.detail_url = web_url_for('oauth_application_detail', client_id=self.platform_app.client_id)

    def test_non_owner_cant_access_detail_page(self):
        res = self.app.get(self.detail_url, auth=self.user2.auth)
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_owner_cant_access_deleted_application(self):
        self.platform_app.is_active = False
        self.platform_app.save()
        res = self.app.get(self.detail_url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_410_GONE

    def test_owner_cant_access_nonexistent_application(self):
        url = web_url_for('oauth_application_detail', client_id='nonexistent')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_404_NOT_FOUND

    def test_url_has_not_broken(self):
        assert self.platform_app.url == self.detail_url


class TestUserProfileTokensPage(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.token = ApiOAuth2PersonalTokenFactory()
        self.detail_url = web_url_for('personal_access_token_detail', _id=self.token._id)

    def test_url_has_not_broken(self):
        assert self.token.url == self.detail_url


class TestUserAccount(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        with capture_notifications():
            self.user.set_password('password')
        self.user.auth = (self.user.username, 'password')
        self.user.save()

    def test_password_change_valid(self,
                                   old_password='password',
                                   new_password='Pa$$w0rd',
                                   confirm_password='Pa$$w0rd'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, data=post_data, auth=(self.user.username, old_password))
        assert res.status_code == 302
        res = self.app.post(url, data=post_data, auth=(self.user.username, new_password), follow_redirects=True)
        assert res.status_code == 200
        self.user.reload()
        assert self.user.check_password(new_password)

    @mock.patch('website.profile.views.push_status_message')
    def test_user_account_password_reset_query_params(self, mock_push_status_message):
        url = web_url_for('user_account') + '?password_reset=True'
        res = self.app.get(url, auth=self.user.auth)
        assert mock_push_status_message.called
        assert 'Password updated successfully' in mock_push_status_message.mock_calls[0][1][0]

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_invalid(self, mock_push_status_message, old_password='', new_password='',
                                     confirm_password='', error_message='Old password is invalid'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert res.status_code == 302
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200
        self.user.reload()
        assert not self.user.check_password(new_password)
        assert mock_push_status_message.called
        error_strings = [e[1][0] for e in mock_push_status_message.mock_calls]
        assert error_message in error_strings

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_rate_limiting(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'invalid old password',
            'new_password': 'this is a new password',
            'confirm_password': 'this is a new password',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 1
        assert res.status_code == 200
        # Make a second request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert len( mock_push_status_message.mock_calls) == 2
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[1][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 2

        # Make a third request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert len(mock_push_status_message.mock_calls) == 3
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[2][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 3

        # Make a fourth request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert mock_push_status_message.called
        error_strings = mock_push_status_message.mock_calls[3][2]
        assert 'Too many failed attempts' in error_strings['message']
        self.user.reload()
        # Too many failed requests within a short window.  Throttled.
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 3

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_rate_limiting_not_imposed_if_old_password_correct(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'password',
            'new_password': 'short',
            'confirm_password': 'short',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        assert res.status_code == 200
        # Make a second request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 2
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[1][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

        # Make a third request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 3
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[2][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

        # Make a fourth request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert mock_push_status_message.called
        assert len(mock_push_status_message.mock_calls) == 4
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[3][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

    @mock.patch('website.profile.views.push_status_message')
    def test_old_password_invalid_attempts_reset_if_password_successfully_reset(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'invalid old password',
            'new_password': 'this is a new password',
            'confirm_password': 'this is a new password',
        }
        correct_post_data = {
            'old_password': 'password',
            'new_password': 'thisisanewpassword',
            'confirm_password': 'thisisanewpassword',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 1
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[0][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 1
        assert res.status_code == 200

        # Make a second request that successfully changes password
        res = self.app.post(url, data=correct_post_data, auth=self.user.auth)
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 0

    def test_password_change_invalid_old_password(self):
        self.test_password_change_invalid(
            old_password='invalid old password',
            new_password='new password',
            confirm_password='new password',
            error_message='Old password is invalid',
        )

    def test_password_change_invalid_confirm_password(self):
        self.test_password_change_invalid(
            old_password='password',
            new_password='new password',
            confirm_password='invalid confirm password',
            error_message='Password does not match the confirmation',
        )

    def test_password_change_invalid_new_password_length(self):
        self.test_password_change_invalid(
            old_password='password',
            new_password='1234567',
            confirm_password='1234567',
            error_message='Password should be at least eight characters',
        )

    def test_password_change_valid_new_password_length(self):
        self.test_password_change_valid(
            old_password='password',
            new_password='12345678',
            confirm_password='12345678',
        )

    def test_password_change_invalid_blank_password(self, old_password='', new_password='', confirm_password=''):
        self.test_password_change_invalid(
            old_password=old_password,
            new_password=new_password,
            confirm_password=confirm_password,
            error_message='Passwords cannot be blank',
        )

    def test_password_change_invalid_empty_string_new_password(self):
        self.test_password_change_invalid_blank_password('password', '', 'new password')

    def test_password_change_invalid_blank_new_password(self):
        self.test_password_change_invalid_blank_password('password', '      ', 'new password')

    def test_password_change_invalid_empty_string_confirm_password(self):
        self.test_password_change_invalid_blank_password('password', 'new password', '')

    def test_password_change_invalid_blank_confirm_password(self):
        self.test_password_change_invalid_blank_password('password', 'new password', '      ')

    def test_user_cannot_request_account_export_before_throttle_expires(self):
        url = api_url_for('request_export')
        with capture_notifications() as notifications:
            self.app.post(url, auth=self.user.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.DESK_REQUEST_EXPORT

        with capture_notifications() as notifications:
            res = self.app.post(url, auth=self.user.auth)
        assert res.status_code == 400
        assert len(notifications) == 0

    def test_get_unconfirmed_emails_exclude_external_identity(self):
        external_identity = {
            'service': {
                'AFI': 'LINK'
            }
        }
        self.user.add_unconfirmed_email('james@steward.com')
        self.user.add_unconfirmed_email('steward@james.com', external_identity=external_identity)
        self.user.save()
        unconfirmed_emails = self.user.get_unconfirmed_emails_exclude_external_identity()
        assert 'james@steward.com' in unconfirmed_emails
        assert 'steward@james.com'not in unconfirmed_emails
