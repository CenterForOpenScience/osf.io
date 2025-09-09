import pytest
from flask import g

from http.cookies import SimpleCookie
from unittest import mock

from framework.auth import Auth, authenticate, cas
from framework.auth.utils import impute_names_model
from framework.exceptions import HTTPError
from framework.flask import redirect
from osf.models import (
    OSFUser,
    Tag, NotificationType,
)
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    PreprintFactory,
    ProjectFactory,
    UserFactory,
    UnregUserFactory,
)
from tests.base import (
    fake,
    OsfTestCase,
)
from tests.test_cas_authentication import generate_external_user_with_resp
from tests.utils import capture_notifications
from website import settings
from website.project.views.contributor import send_claim_registered_email
from website.util.metrics import (
    OsfSourceTags,
    OsfClaimedTags,
    provider_source_tag,
    provider_claimed_tag
)


@pytest.mark.enable_implicit_clean
class TestClaimViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.project_with_source_tag = ProjectFactory(creator=self.referrer, is_public=True)
        self.preprint_with_source_tag = PreprintFactory(creator=self.referrer, is_public=True)
        osf_source_tag, created = Tag.all_tags.get_or_create(name=OsfSourceTags.Osf.value, system=True)
        preprint_source_tag, created = Tag.all_tags.get_or_create(name=provider_source_tag(self.preprint_with_source_tag.provider._id, 'preprint'), system=True)
        self.project_with_source_tag.add_system_tag(osf_source_tag.name)
        self.preprint_with_source_tag.add_system_tag(preprint_source_tag.name)
        self.given_name = fake.name()
        self.given_email = fake_email()
        self.project_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        self.preprint_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        self.project.save()

    def test_claim_user_already_registered_redirects_to_claim_user_registered(self):
        name = fake.name()
        email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for(
            'claim_user_post',
            uid='undefined'
        )
        with capture_notifications() as notifications:
            self.app.post(
                invite_url,
                json={
                    'pk': unregistered_user._primary_key,
                    'value': email
                }
            )
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_PENDING_VERIFICATION
        assert notifications['emits'][1]['type'] == NotificationType.Type.USER_FORWARD_INVITE

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        UserFactory(username=email, fullname=name)

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    def test_claim_user_already_registered_secondary_email_redirects_to_claim_user_registered(self):
        name = fake.name()
        email = fake_email()
        secondary_email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for(
            'claim_user_post',
            uid='undefined'
        )
        with capture_notifications() as notifications:
            self.app.post(
                invite_url,
                json={
                    'pk': unregistered_user._primary_key,
                    'value': secondary_email
                }
            )
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_PENDING_VERIFICATION
        assert notifications['emits'][1]['type'] == NotificationType.Type.USER_FORWARD_INVITE

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': secondary_email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        registered_user = UserFactory(username=email, fullname=name)
        registered_user.emails.create(address=secondary_email)
        registered_user.save()

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    def test_claim_user_invited_with_no_email_posts_to_claim_form(self):
        given_name = fake.name()
        invited_user = self.project.add_unregistered_contributor(
            fullname=given_name,
            email=None,
            auth=Auth(user=self.referrer),
            notification_type=False
        )
        self.project.save()

        url = invited_user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        assert res.status_code == 400

    def test_claim_user_post_with_registered_user_id(self):
        # registered user who is attempting to claim the unclaimed contributor
        reg_user = UserFactory()
        with capture_notifications() as notifications:
            res = self.app.post(
                f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/',
                json={
                    # pk of unreg user record
                    'pk': self.user._primary_key,
                    'claimerId': reg_user._primary_key
                }
            )

        # mail was sent
        assert len(notifications['emits']) == 2
        # ... to the correct address
        assert notifications['emits'][0]['kwargs']['user'] == self.referrer
        assert notifications['emits'][1]['kwargs']['user'] == reg_user

        # view returns the correct JSON
        assert res.json == {
            'status': 'success',
            'email': reg_user.username,
            'fullname': self.given_name,
        }

    def test_send_claim_registered_email(self):
        reg_user = UserFactory()
        with capture_notifications() as notifications:
            send_claim_registered_email(
                claimer=reg_user,
                unclaimed_user=self.user,
                node=self.project
            )
        assert len(notifications['emits']) == 2
        # ... to the correct address
        assert notifications['emits'][0]['kwargs']['user'] == self.referrer
        assert notifications['emits'][1]['kwargs']['user'] == reg_user

    def test_send_claim_registered_email_before_throttle_expires(self):
        reg_user = UserFactory()
        with mock.patch('osf.email.send_email_with_send_grid', return_value=None):
            with capture_notifications(passthrough=True) as notifications:
                send_claim_registered_email(
                    claimer=reg_user,
                    unclaimed_user=self.user,
                    node=self.project,
                )
                assert len(notifications['emits']) == 2
                assert notifications['emits'][0]['type'] == NotificationType.Type.USER_FORWARD_INVITE_REGISTERED
                assert notifications['emits'][1]['type'] == NotificationType.Type.USER_PENDING_VERIFICATION_REGISTERED
        # second call raises error because it was called before throttle period
        with pytest.raises(HTTPError):
                send_claim_registered_email(
                    claimer=reg_user,
                    unclaimed_user=self.user,
                    node=self.project,
                )

    @mock.patch('website.project.views.contributor.send_claim_registered_email')
    def test_claim_user_post_with_email_already_registered_sends_correct_email(
            self, send_claim_registered_email):
        reg_user = UserFactory()
        payload = {
            'value': reg_user.username,
            'pk': self.user._primary_key
        }
        url = self.project.api_url_for('claim_user_post', uid=self.user._id)
        self.app.post(url, json=payload)
        assert send_claim_registered_email.called

    def test_user_with_removed_unclaimed_url_claiming(self):
        """ Tests that when an unclaimed user is removed from a project, the
        unregistered user object does not retain the token.
        """
        self.project.remove_contributor(self.user, Auth(user=self.referrer))

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_user_with_claim_url_cannot_claim_twice(self):
        """ Tests that when an unclaimed user is replaced on a project with a
        claimed user, the unregistered user object does not retain the token.
        """
        reg_user = AuthUserFactory()

        self.project.replace_contributor(self.user, reg_user)

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_claim_user_form_redirects_to_password_confirm_page_if_user_is_logged_in(self):
        reg_user = AuthUserFactory()
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=reg_user.auth)
        assert res.status_code == 302
        res = self.app.get(url, auth=reg_user.auth, follow_redirects=True)
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        expected = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token=token,
        )
        assert res.request.path == expected

    @mock.patch('framework.auth.cas.make_response_from_ticket')
    def test_claim_user_when_user_is_registered_with_orcid(self, mock_response_from_ticket):
        # TODO: check in qa url encoding
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        url = f'/user/{self.user._id}/{self.project._id}/claim/verify/{token}/'
        # logged out user gets redirected to cas login
        res1 = self.app.get(url)
        assert res1.status_code == 302
        res = self.app.resolve_redirect(self.app.get(url))
        service_url = f'http://localhost{url}'
        expected = cas.get_logout_url(service_url=cas.get_login_url(service_url=service_url))
        assert res1.location == expected

        # user logged in with orcid automatically becomes a contributor
        orcid_user, validated_credentials, cas_resp = generate_external_user_with_resp(url)
        mock_response_from_ticket.return_value = authenticate(
            orcid_user,
            redirect(url)
        )
        orcid_user.set_unusable_password()
        orcid_user.save()

        # The request to OSF with CAS service ticket must not have cookie and/or auth.
        service_ticket = fake.md5()
        url_with_service_ticket = f'{url}?ticket={service_ticket}'
        res = self.app.get(url_with_service_ticket)
        # The response of this request is expected to be a 302 with `Location`.
        # And the redirect URL must equal to the originial service URL
        assert res.status_code == 302
        redirect_url = res.headers['Location']
        assert redirect_url == url
        # The response of this request is expected have the `Set-Cookie` header with OSF cookie.
        # And the cookie must belong to the ORCiD user.
        raw_set_cookie = res.headers['Set-Cookie']
        assert raw_set_cookie
        simple_cookie = SimpleCookie()
        simple_cookie.load(raw_set_cookie)
        cookie_dict = {key: value.value for key, value in simple_cookie.items()}
        osf_cookie = cookie_dict.get(settings.COOKIE_NAME, None)
        assert osf_cookie is not None
        user = OSFUser.from_cookie(osf_cookie)
        assert user._id == orcid_user._id
        # The ORCiD user must be different from the unregistered user created when the contributor was added
        assert user._id != self.user._id

        # Must clear the Flask g context manual and set the OSF cookie to context
        g.current_session = None
        self.app.set_cookie(settings.COOKIE_NAME, osf_cookie)
        res = self.app.resolve_redirect(res)
        assert res.status_code == 302
        assert self.project.is_contributor(orcid_user)
        assert self.project.url in res.headers.get('Location')

    def test_get_valid_form(self):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200

    def test_invalid_claim_form_raise_400(self):
        uid = self.user._primary_key
        pid = self.project._primary_key
        url = f'/user/{uid}/{pid}/claim/?token=badtoken'
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 400

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_with_valid_data(self, mock_update_search_nodes):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location
        assert 'username' in location
        assert 'verification_key' in location
        assert self.project._primary_key in location

        self.user.reload()
        assert self.user.is_registered
        assert self.user.is_active
        assert self.project._primary_key not in self.user.unclaimed_records

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_removes_all_unclaimed_data(self, mock_update_search_nodes):
        # user has multiple unclaimed records
        p2 = ProjectFactory(creator=self.referrer)
        self.user.add_unclaimed_record(p2, referrer=self.referrer,
                                       given_name=fake.name())
        self.user.save()
        assert len(self.user.unclaimed_records.keys()) > 1  # sanity check
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.given_email,
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        self.user.reload()
        assert self.user.unclaimed_records == {}

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_sets_fullname_to_given_name(self, mock_update_search_nodes):
        # User is created with a full name
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)
        # User invited with a different name
        different_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=unreg.username,
            fullname=different_name,
            auth=Auth(self.project.creator),
        )
        self.project.save()
        # Goes to claim url
        claim_url = new_user.get_claim_url(self.project._id)
        self.app.post(claim_url, data={
            'username': unreg.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })
        unreg.reload()
        # Full name was set correctly
        assert unreg.fullname == different_name
        # CSL names were set correctly
        parsed_name = impute_names_model(different_name)
        assert unreg.given_name == parsed_name['given_name']
        assert unreg.family_name == parsed_name['family_name']

    def test_claim_user_post_returns_fullname(self):
        with capture_notifications() as notifications:
            res = self.app.post(
                f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/',
                auth=self.referrer.auth,
                json={
                    'value': self.given_email,
                    'pk': self.user._primary_key
                },
            )
        assert res.json['fullname'] == self.given_name
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_INVITE_DEFAULT

    def test_claim_user_post_if_email_is_different_from_given_email(self):
        email = fake_email()  # email that is different from the one the referrer gave
        with capture_notifications() as notifications:
            self.app.post(
                f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/',
                json={
                    'value': email,
                    'pk': self.user._primary_key
                }
            )
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_PENDING_VERIFICATION
        assert notifications['emits'][0]['kwargs']['user'].username == self.given_email
        assert notifications['emits'][1]['type'] == NotificationType.Type.USER_FORWARD_INVITE
        assert notifications['emits'][1]['kwargs']['destination_address'] == email

    def test_claim_url_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth)
        assert res.status_code == 400

    def test_cannot_claim_user_with_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth, follow_redirects=True)
        # Response is a 400
        assert res.status_code == 400

    def test_claim_user_with_project_id_adds_corresponding_claimed_tag_to_user(self):
        assert OsfClaimedTags.Osf.value not in self.user.system_tags
        url = self.user.get_claim_url(self.project_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert OsfClaimedTags.Osf.value in self.user.system_tags

    def test_claim_user_with_preprint_id_adds_corresponding_claimed_tag_to_user(self):
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') not in self.user.system_tags
        url = self.user.get_claim_url(self.preprint_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') in self.user.system_tags
