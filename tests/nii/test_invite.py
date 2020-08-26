from rest_framework import status as http_status

import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts

from framework.auth import Auth
from osf.models import OSFUser
from website import mails, settings
from website.project.views.contributor import (
    send_claim_email,
)
from api.institutions.authentication import NEW_USER_NO_NAME

from tests.base import (
    fake,
    OsfTestCase,
)
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
)


### refer to tests/test_views.py:TestClaimViews
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestInvite(OsfTestCase):

    def setUp(self):
        super(TestInvite, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.given_name = fake.name()
        self.given_email = fake_email()
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', False)
    def test_claim_user_not_login_by_eppn(self):
        url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token='faketoken',
        )
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_in('This URL does not support LOGIN_BY_EPPN=False', res.text)

    def _common_redirect_to_claim_user_login_by_eppn(self, user2):
        unclaimed_record = self.user.get_unclaimed_record(self.project._primary_key)
        token = unclaimed_record['token']
        # verify_url = '/user/eppn/{uid}/{pid}/claim/verify/{token}/'.format(
        #     uid=self.user._id,
        #     pid=self.project._id,
        #     token=token
        # )
        verify_url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token=token,
        )
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.status_code, 302)
        assert_in(verify_url, res.headers.get('Location'))
        res2 = res.follow(auth=user2.auth)
        assert_equal(res2.status_code, http.OK)
        if user2.have_email:  # existing user
            assert_in(user2.username, res2.text)
            assert_in(user2.fullname, res2.text)
            assert_in(self.user.username, res2.text)
            assert_not_in(self.user.fullname, res2.text)
        else:
            assert_in(self.user.username, res2.text)
            assert_in(self.user.fullname, res2.text)
            assert_not_in(user2.username, res2.text)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_redirect_by_existing_user_to_claim_user_login_by_eppn(self):
        user2 = AuthUserFactory()
        user2.eppn = fake_email()  # fake ePPN
        user2.have_email = True
        user2.save()
        self._common_redirect_to_claim_user_login_by_eppn(user2)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_redirect_by_new_user_to_claim_user_login_by_eppn(self):
        user2 = AuthUserFactory()
        user2.fullname = NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_redirect_to_claim_user_login_by_eppn(user2)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_claim_url_for_eppn_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=400)
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_in('The token in the URL is invalid or has expired.', res.text)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_cannot_claim_user_with_eppn_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth,
        ).follow(
            auth=contrib.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_in('The logged-in user is already a contributor to this ', res.text)

    def _common_posting_to_claim_user_login_by_eppn(self, user2, send_mail, existing_user):
        if existing_user:
            expected_username = user2.username
            expected_fullname = user2.fullname
        else:
            expected_username = self.user.username
            if user2.fullname == NEW_USER_NO_NAME:
                expected_fullname = self.user.fullname
            else:
                expected_fullname = user2.fullname
        unclaimed_record = self.user.get_unclaimed_record(self.project._primary_key)
        token = unclaimed_record['token']
        verify_url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token=token,
        )
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=user2.auth)
        assert_equal(res.status_code, 302)
        assert_in(verify_url, res.headers.get('Location'))

        with mock.patch('website.project.views.contributor.mapcore_sync_map_group') as mock1, \
             mock.patch('website.project.views.contributor.mapcore_sync_is_enabled') as mock2:
            mock2.return_value = True
            res2 = self.app.post(verify_url, auth=user2.auth)
        assert_equal(mock1.call_count, 1)
        assert_equal(res2.status_code, 302)
        assert_in(self.project.url, res2.headers.get('Location'))

        user2.reload()  # update have_email
        assert_true(user2.have_email)
        if existing_user:
            assert_equal(send_mail.call_count, 0)
        else:
            assert_equal(send_mail.call_count, 1)  # welcome

        user2_auth = Auth(OSFUser.objects.get(username=user2.username))
        res3 = res2.follow(auth=user2_auth)
        assert_equal(res3.status_code, http.OK)

        self.project.reload()
        self.user.reload()
        user2.reload()
        assert_equal(self.user.fullname, 'Deleted user')
        assert_false(self.user.is_active)
        assert_not_in(self.project._primary_key, self.user.unclaimed_records)
        assert_not_in(self.user, self.project.contributors)
        assert_equal(user2.username, expected_username)
        assert_equal(user2.fullname, expected_fullname)
        assert_in(user2, self.project.contributors)
        assert_true(user2.emails.filter(address=self.given_email).exists())

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_new_user_no_name_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.fullname = NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         False)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_new_user_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.fullname = 'not ' + NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         False)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_existing_user_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.eppn = fake_email()  # fake ePPN
        user2.have_email = True
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         True)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_given_email_for_eppn(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        claim_url = unreg_user.get_claim_url(project._primary_key, external=True)
        claimer_email = given_email.lower().strip()
        unclaimed_record = unreg_user.get_unclaimed_record(project._primary_key)
        referrer = OSFUser.load(unclaimed_record['referrer_id'])

        send_claim_email(email=given_email, unclaimed_user=unreg_user,
                         node=project)

        assert_true(send_mail.called)
        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=referrer,
            node=project,
            claim_url=claim_url,
            email=claimer_email,
            fullname=unclaimed_record['name'],
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            login_by_eppn=True,  # checking mainly
        )
