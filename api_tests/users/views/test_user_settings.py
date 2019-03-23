# -*- coding: utf-8 -*-
import mock
import pytest

from api.base.settings.defaults import API_BASE
from api.base.utils import hashids
from osf_tests.factories import (
    AuthUserFactory,
    UserFactory,
)
from osf.models import Email, BlacklistedEmailDomain
from framework.auth.views import auth_email_logout

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.fixture()
def unconfirmed_address():
    return 'save@thewhales.test'


@pytest.mark.django_db
class TestUserRequestExport:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/export/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-export-form',
                'attributes': {}
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429


@pytest.mark.django_db
class TestUserChangePassword:

    @pytest.fixture()
    def user_one(self):
        user = UserFactory()
        user.set_password('password1')
        user.auth = (user.username, 'password1')
        user.save()
        return user

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/password/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'type': 'user_passwords',
                'id': user_one._id,
                'attributes': {
                    'existing_password': 'password1',
                    'new_password': 'password2',
                }
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    def test_post(self, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.check_password('password2')

    def test_post_invalid_type(self, app, user_one, url, payload):
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    def test_exceed_throttle_failed_attempts(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'wrong password'
        payload['data']['attributes']['new_password'] = 'password2'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Old password is invalid'

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Old password is invalid'

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Old password is invalid'

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429
        # Expected time is omitted to prevent probabilistic failures.
        assert 'Request was throttled. Expected available in ' in res.json['errors'][0]['detail']

    def test_multiple_errors(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'wrong password'
        payload['data']['attributes']['new_password'] = '!'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Old password is invalid'
        assert res.json['errors'][1]['detail'] == 'Password should be at least eight characters'


@pytest.mark.django_db
class TestUserEmailsList:

    @pytest.fixture(autouse=True)
    def user_with_emails(self, user_one, unconfirmed_address):
        new_addresses = ['new_one@test.test, new_two@test.test']
        for address in new_addresses:
            Email.objects.create(address=address, user=user_one)

        user_one.add_unconfirmed_email(unconfirmed_address)
        user_one.save()

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/emails/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'type': 'user_emails',
                'attributes': {}
            }
        }

    def test_get_emails_current_user(self, app, url, user_one):
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        confirmed_count = user_one.emails.count()
        unconfirmed_count = len(user_one.unconfirmed_emails)
        data = res.json['data']
        assert len(data) == confirmed_count + unconfirmed_count
        assert len([email for email in data if email['attributes']['confirmed']]) == confirmed_count
        assert len([email for email in data if email['attributes']['confirmed'] is False]) == unconfirmed_count

    def test_get_emails_not_current_user(self, app, url, user_one, user_two):
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

    def test_unconfirmed_email_included(self, app, url, payload, user_one, unconfirmed_address):
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert unconfirmed_address in [result['attributes']['email_address'] for result in res.json['data']]

    @mock.patch('api.users.serializers.send_confirm_email')
    def test_create_new_email_current_user(self, mock_send_confirm_mail, user_one, user_two, app, url, payload):
        new_email = 'hhh@wwe.test'
        payload['data']['attributes']['email_address'] = new_email

        # post from current user
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['email_address'] == new_email
        user_one.reload()
        assert new_email in user_one.unconfirmed_emails
        assert mock_send_confirm_mail.called

    @mock.patch('api.users.serializers.send_confirm_email')
    def test_create_new_email_not_current_user(self, mock_send_confirm_mail, app, url, payload, user_one, user_two):
        new_email = 'HHH@wwe.test'
        payload['data']['attributes']['email_address'] = new_email
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        user_one.reload()
        assert new_email not in user_one.unconfirmed_emails
        assert not mock_send_confirm_mail.called

    @mock.patch('api.users.serializers.send_confirm_email')
    def test_create_email_already_exists(self, mock_send_confirm_mail, app, url, payload, user_one):
        new_email = 'hello@email.test'
        Email.objects.create(address=new_email, user=user_one)
        payload['data']['attributes']['email_address'] = new_email
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        assert new_email in res.json['errors'][0]['detail']
        assert not mock_send_confirm_mail.called

        unconfirmed_email = 'hello@herewego.now'
        user_one.add_unconfirmed_email(unconfirmed_email)
        user_one.save()
        payload['data']['attributes']['email_address'] = unconfirmed_email
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        assert unconfirmed_email in res.json['errors'][0]['detail']
        assert not mock_send_confirm_mail.called

    def test_create_email_invalid_format(self, app, url, payload, user_one):
        new_email = 'this is not an email'
        payload['data']['attributes']['email_address'] = new_email
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Enter a valid email address.'

    def test_create_blacklisted_email(self, app, url, payload, user_one):
        BlacklistedEmailDomain.objects.get_or_create(domain='mailinator.com')
        new_email = 'freddie@mailinator.com'
        payload['data']['attributes']['email_address'] = new_email
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This email address domain is blacklisted.'

    def test_unconfirmed_email_with_expired_token_not_in_results(self, app, url, payload, user_one):
        unconfirmed = 'notyet@unconfirmed.test'
        old_token = user_one.add_unconfirmed_email(unconfirmed)
        user_one.save()
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert unconfirmed in [result['attributes']['email_address'] for result in res.json['data']]
        assert old_token in [result['id'] for result in res.json['data']]

        # add again, get a new token
        new_token = user_one.add_unconfirmed_email(unconfirmed)
        user_one.save()
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        returned_ids = [result['id'] for result in res.json['data']]
        assert new_token in returned_ids
        assert old_token not in returned_ids

    @mock.patch('api.base.throttling.BaseThrottle.allow_request')
    def test_filter_by_attributes(self, mock_throttle, app, url, user_one):
        confirmed_not_verified = 'notyet@unconfirmed.test'
        token = user_one.add_unconfirmed_email(confirmed_not_verified)
        user_one.email_verifications[token]['confirmed'] = True
        user_one.save()

        # test filter by confirmed
        confirmed_tokens = [key for key, value in user_one.email_verifications.iteritems() if value['confirmed']]
        confirmed_count = user_one.emails.count() + len(confirmed_tokens)
        filtered_url = '{}?filter[confirmed]=True'.format(url)
        res = app.get(filtered_url, auth=user_one.auth)
        assert confirmed_count > 0
        assert len(res.json['data']) == confirmed_count
        for result in res.json['data']:
            assert result['attributes']['confirmed'] is True

        filtered_url = '{}?filter[confirmed]=False'.format(url)
        res = app.get(filtered_url, auth=user_one.auth)
        assert len(res.json['data']) > 0
        for result in res.json['data']:
            assert result['attributes']['confirmed'] is False

        # test filter by verified
        verified_count = user_one.emails.count()
        filtered_url = '{}?filter[verified]=True'.format(url)
        res = app.get(filtered_url, auth=user_one.auth)
        assert verified_count > 0
        assert len(res.json['data']) == verified_count
        for result in res.json['data']:
            assert result['attributes']['verified'] is True

        filtered_url = '{}?filter[verified]=False'.format(url)
        res = app.get(filtered_url, auth=user_one.auth)
        assert len(res.json['data']) > 0
        for result in res.json['data']:
            assert result['attributes']['verified'] is False

        primary_filter_url = '{}?filter[primary]=True'.format(url)
        res = app.get(primary_filter_url, auth=user_one.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['primary'] is True
        not_primary_url = '{}?filter[primary]=False'.format(url)
        res = app.get(not_primary_url, auth=user_one.auth)
        assert len(res.json['data']) > 0
        for result in res.json['data']:
            assert result['attributes']['primary'] is False


@pytest.mark.django_db
class TestUserEmailDetail:

    def get_hashid(self, id_to_hash):
        return hashids.encode(id_to_hash)

    @pytest.fixture()
    def confirmed_email(self, user_one):
        return Email.objects.create(address='new@test.test', user=user_one)

    @pytest.fixture()
    def unconfirmed_token(self, unconfirmed_address, user_one):
        token = user_one.add_unconfirmed_email(unconfirmed_address)
        user_one.save()
        return token

    @pytest.fixture()
    def unconfirmed_url(self, user_one, unconfirmed_token):
        return '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, unconfirmed_token)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user_emails',
                'attributes': {}
            }
        }

    @pytest.fixture()
    def confirmed_url(self, user_one, confirmed_email):
        confirmed_email_hash = self.get_hashid(confirmed_email.id)
        return '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, confirmed_email_hash)

    def test_get_email_detail(self, app, confirmed_url, user_one, user_two, unconfirmed_url):
        # logged in and authorized and confirmed
        res = app.get(confirmed_url, auth=user_one.auth)
        assert res.status_code == 200
        assert 'resend_confirmation' not in res.json['data']['links'].keys()

        # not logged in
        res = app.get(confirmed_url, expect_errors=True)
        assert res.status_code == 401

        # logged in as different user
        res = app.get(confirmed_url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # unconfirmed email detail
        res_unconfirmed = app.get(unconfirmed_url, auth=user_one.auth)
        assert res_unconfirmed.status_code == 200
        assert res_unconfirmed.json['data']['attributes']['confirmed'] is False
        assert 'resend_confirmation' in res_unconfirmed.json['data']['links'].keys()
        assert '{}?resend_confirmation=true'.format(unconfirmed_url) in res_unconfirmed.json['data']['links']['resend_confirmation']

        # token for unconfirmed email different user
        res = app.get(unconfirmed_url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # id does not exist
        url = '/{}users/{}/settings/emails/thisisnotarealid/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

        # id is a real hashid but the database id does not exist
        potential_id = hashids.encode(10000000)
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, potential_id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

        # primary email detail
        primary_email = Email.objects.get(address=user_one.username)
        primary_hash = self.get_hashid(primary_email.id)
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, primary_hash)
        res_primary = app.get(url, auth=user_one.auth)
        assert res_primary.status_code == 200
        assert res_primary.json['data']['attributes']['primary'] is True

        # is_merge field
        token = user_one.add_unconfirmed_email(user_two.username)
        user_one.save()
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, token)
        res_merge = app.get(url, auth=user_one.auth)
        assert res_merge.json['data']['attributes']['is_merge'] is True
        assert res_unconfirmed.json['data']['attributes']['is_merge'] is False
        assert res_primary.json['data']['attributes']['is_merge'] is False

    def test_adding_new_token_for_unconfirmed_email(self, app, user_one, unconfirmed_address,
                                                    unconfirmed_token, unconfirmed_url):
        res = app.get(unconfirmed_url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == unconfirmed_token

        # add the same unconfirmed email again, refreshing the token
        second_token = user_one.add_unconfirmed_email(unconfirmed_address)
        user_one.save()
        assert unconfirmed_token != second_token
        second_token_url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, second_token)
        res = app.get(second_token_url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == second_token

        # make sure the old route no longer resolves
        res = app.get(unconfirmed_url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    def test_set_primary_email(self, app, confirmed_url, payload, confirmed_email, user_one, user_two, unconfirmed_url):
        payload['data']['attributes'] = {'primary': True}

        # test_set_email_primary_not_logged_in
        res = app.patch_json_api(confirmed_url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_set_primary_email_current_user
        res = app.patch_json_api(confirmed_url, payload, auth=user_one.auth)
        assert res.status_code == 200
        user_one.reload()
        assert user_one.username == confirmed_email.address

        # test set primary not current user
        res = app.patch_json_api(confirmed_url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test set primary not confirmed fails
        res = app.patch_json_api(unconfirmed_url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot set an unconfirmed email address as your primary email address.'

    def test_delete_email(self, app, payload, user_one, user_two, confirmed_email, confirmed_url, unconfirmed_url, unconfirmed_address):
        # test delete email logged in as another user fails
        res = app.delete_json_api(confirmed_url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test delete confirmed email
        res = app.delete_json_api(confirmed_url, payload, auth=user_one.auth)
        assert res.status_code == 204
        assert confirmed_email not in user_one.emails.all()

        # test delete primary email fails
        username_email = user_one.emails.get(address=user_one.username)
        username_hash = self.get_hashid(username_email.id)
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, username_hash)
        res = app.delete_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "Can't remove primary email"

        # test delete unconfirmed email
        res = app.delete_json_api(unconfirmed_url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert unconfirmed_address not in user_one.unconfirmed_emails

    @mock.patch('framework.auth.views.cas.get_logout_url')
    @mock.patch('framework.auth.views.web_url_for')
    def test_verified(self, mock_get_logout_url, mock_web_url_for, app, user_one, unconfirmed_token,
                        unconfirmed_url, unconfirmed_address):
        # clicking the link in the email to set confirm calls
        # auth_email_logout which does the correct attribute setting
        with mock.patch('framework.auth.views.redirect'):
            auth_email_logout(unconfirmed_token, user_one)
        user_one.reload()
        res = app.get(unconfirmed_url, auth=user_one.auth)
        assert res.json['data']['attributes']['confirmed'] is True
        assert res.json['data']['attributes']['verified'] is False

        # confirm email OSF side to set verified
        user_one.confirm_email(token=unconfirmed_token)
        user_one.reload()
        email = Email.objects.get(address=unconfirmed_address)
        email_hash = self.get_hashid(email.id)
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, email_hash)
        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['confirmed'] is True
        assert res.json['data']['attributes']['verified'] is True

    def test_update_confirmed_email_to_verified(self, app, user_one, unconfirmed_address,
                                                unconfirmed_url, payload, unconfirmed_token):
        payload['data']['attributes'] = {'verified': True}

        # setting verified on unconfirmed email fails
        res = app.patch_json_api(unconfirmed_url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot verify an email address that has not been confirmed by a user.'

        # manually set the email to confirmed
        user_one.email_verifications[unconfirmed_token]['confirmed'] = True
        user_one.save()

        # setting verified on confirmed email
        res = app.patch_json(unconfirmed_url, payload, auth=user_one.auth)
        assert res.json['data']['attributes']['confirmed'] is True
        assert res.json['data']['attributes']['verified'] is True
        new_email = Email.objects.get(address=unconfirmed_address)
        assert new_email in user_one.emails.all()
        assert res.json['data']['id'] == self.get_hashid(new_email.id)

        # old URL no longer resolves
        res_original = app.get(unconfirmed_url, auth=user_one.auth, expect_errors=True)
        assert res_original.status_code == 404

    @pytest.mark.enable_quickfiles_creation
    def test_updating_verified_for_merge(self, app, user_one, user_two, payload):
        payload['data']['attributes'] = {'verified': True}
        token = user_one.add_unconfirmed_email(user_two.username)
        user_one.save()
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, token)

        # test unconfirmed merge attempt fails
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot verify an email address that has not been confirmed by a user.'

        # test confirmed merge
        user_one.email_verifications[token]['confirmed'] = True
        user_one.save()
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['verified'] is True
        assert res.json['data']['attributes']['confirmed'] is True
        assert res.json['data']['attributes']['is_merge'] is False

    @mock.patch('api.users.views.send_confirm_email')
    def test_resend_confirmation_email(self, mock_send_confirm_email, app, user_one, unconfirmed_url, confirmed_url):
        url = '{}?resend_confirmation=True'.format(unconfirmed_url)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 202
        assert mock_send_confirm_email.called
        call_count = mock_send_confirm_email.call_count

        # make sure setting false does not send confirm email
        url = '{}?resend_confirmation=False'.format(unconfirmed_url)
        res = app.get(url, auth=user_one.auth)
        # should return 200 instead of 202 because nothing has been done
        assert res.status_code == 200
        assert mock_send_confirm_email.call_count

        # make sure normal GET request does not re-send confirmation email
        res = app.get(unconfirmed_url, auth=user_one.auth)
        assert mock_send_confirm_email.call_count == call_count
        assert res.status_code == 200

        # resend confirmation with confirmed email address does not send confirmation email
        url = '{}?resend_confirmation=True'.format(confirmed_url)
        res = app.get(url, auth=user_one.auth)
        assert mock_send_confirm_email.call_count == call_count
        assert res.status_code == 200
