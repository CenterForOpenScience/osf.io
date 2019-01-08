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

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


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
class TestUserRequestDeactivate:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/deactivate/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-deactivate-form',
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
        assert user_one.requested_deactivation is False
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert user_one.requested_deactivation is True
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
                'type': 'user_password',
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
    def user_with_emails(self, user_one):
        new_addresses = ['new_one@test.test, new_two@test.test']
        for address in new_addresses:
            Email.objects.create(address=address, user=user_one)

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

    def test_get_emails_current_user_no_unconfirmed(self, app, url, user_one):
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == user_one.emails.count()

    def test_get_emails_not_current_user(self, app, url, user_one, user_two):
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

    def test_unconfirmed_email_included(self, app, url, payload, user_one):
        unconfirmed = 'notyet@unconfirmed.test'
        user_one.add_unconfirmed_email(unconfirmed)
        user_one.save()
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert unconfirmed in [result['attributes']['email_address'] for result in res.json['data']]

    @mock.patch('api.users.serializers.send_confirm_email')
    def test_create_new_email_current_user(self, mock_send_confirm_mail, user_one, app, url, payload):
        new_email = 'hhh@wwe.test'
        payload['data']['attributes']['email_address'] = new_email
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


@pytest.mark.django_db
class TestUserEmailDetail:

    def get_hashid(self, id_to_hash):
        return hashids.encode(id_to_hash)

    @pytest.fixture()
    def new_email(self, user_one):
        return Email.objects.create(address='new@test.test', user=user_one)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user_emails',
                'attributes': {}
            }
        }

    @pytest.fixture()
    def url(self, user_one, new_email):
        new_email_hash = self.get_hashid(new_email.id)
        return '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, new_email_hash)

    def test_get_email_detail(self, app, url, user_one, user_two):
        # logged in and authorized
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        # not logged in
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # logged in as different user
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # token for unconfirmed email
        token = user_one.add_unconfirmed_email('hello@fake.test')
        user_one.save()
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, token)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['confirmed'] is False

        # token for unconfirmed email different user
        res = app.get(url, auth=user_two.auth, expect_errors=True)
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
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['primary'] is True

    def test_adding_new_token_for_unconfirmed_email(self, app, user_one):
        new_email = 'save@thewhales.test'
        first_token = user_one.add_unconfirmed_email(new_email)
        user_one.save()
        first_token_url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, first_token)
        res = app.get(first_token_url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == first_token

        # add the same unconfirmed email again, refreshing the token
        second_token = user_one.add_unconfirmed_email(new_email)
        user_one.save()
        assert first_token != second_token
        second_token_url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, second_token)
        res = app.get(second_token_url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == second_token

        # make sure the old route no longer resolves
        res = app.get(first_token_url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    def test_set_primary_email(self, app, url, payload, new_email, user_one, user_two):
        payload['data']['attributes'] = {'primary': True}

        # test_set_email_primary_not_logged_in
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_set_primary_email_current_user
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200
        user_one.reload()
        assert user_one.username == new_email.address

        # test set primary not current user
        res = app.patch_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test set primary not confirmed fails
        unconfirmed_id = user_one.add_unconfirmed_email('unconfirmed@nope.test')
        user_one.save()
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, unconfirmed_id)
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot set an unconfirmed email address as your primary email address.'

    def test_delete_email(self, app, url, payload, user_one, user_two, new_email):
        # test delete email logged in as another user fails
        res = app.delete_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test delete confirmed email
        res = app.delete_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        assert new_email not in user_one.emails.all()

        # test delete primary email fails
        username_email = user_one.emails.get(address=user_one.username)
        username_hash = self.get_hashid(username_email.id)
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, username_hash)
        res = app.delete_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "Can't remove primary email"

        # test delete unconfirmed email
        unconfirmed_address = 'test@hello.nope'
        unconfirmed_token = user_one.add_unconfirmed_email(unconfirmed_address)
        user_one.save()
        url = '/{}users/{}/settings/emails/{}/'.format(API_BASE, user_one._id, unconfirmed_token)
        res = app.delete_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert unconfirmed_address not in user_one.unconfirmed_emails
