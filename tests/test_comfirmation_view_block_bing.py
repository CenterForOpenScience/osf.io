import pytest
from framework.auth import Auth, core

from osf.models import OSFUser
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import fake,  OsfTestCase
from website.util import web_url_for

@pytest.mark.django_db
class TestConfirmationViewBlockBingPreview(OsfTestCase):

    def setUp(self):

        super().setUp()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b'

    # reset password link should fail with BingPreview
    def test_reset_password_get_returns_403(self):

        user = UserFactory()
        osf_key_v2 = core.generate_verification_key(verification_type='password')
        user.verification_key_v2 = osf_key_v2
        user.verification_key = None
        user.save()

        reset_password_get_url = web_url_for(
            'reset_password_get',
            uid=user._id,
            token=osf_key_v2['token']
        )
        res = self.app.get(
            reset_password_get_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # new user confirm account should fail with BingPreview
    def test_confirm_email_get_new_user_returns_403(self):

        user = OSFUser.create_unconfirmed('unconfirmed@cos.io', 'abCD12#$', 'Unconfirmed User')
        user.save()
        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False)
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for adding new email should fail with BingPreview
    def test_confirm_email_add_email_returns_403(self):

        user = UserFactory()
        user.add_unconfirmed_email('unconfirmed@cos.io')
        user.save()

        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for merging accounts should fail with BingPreview
    def test_confirm_email_merge_account_returns_403(self):

        user = UserFactory()
        user_to_be_merged = UserFactory()
        user.add_unconfirmed_email(user_to_be_merged.username)
        user.save()

        confirm_url = user.get_confirmation_url(user_to_be_merged.username, external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for new user claiming contributor should fail with BingPreview
    def test_claim_user_form_new_user(self):

        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        project.save()

        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for existing user claiming contributor should fail with BingPreview
    def test_claim_user_form_existing_user(self):

        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        auth_user = AuthUserFactory()
        pending_user = project.add_unregistered_contributor(
            fullname=auth_user.fullname,
            email=None,
            auth=Auth(user=referrer)
        )
        project.save()
        claim_url = pending_user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            auth = auth_user.auth,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # account creation confirmation for ORCiD login should fail with BingPreview
    def test_external_login_confirm_email_get_create_user(self):
        name, email = fake.name(), fake_email()
        provider_id = fake.ean()
        external_identity = {
            'service': {
                provider_id: 'CREATE'
            }
        }
        user = OSFUser.create_unconfirmed(
            username=email,
            password=str(fake.password()),
            fullname=name,
            external_identity=external_identity,
        )
        user.save()
        create_url = user.get_confirmation_url(
            user.username,
            external_id_provider='service',
            destination='dashboard'
        )

        res = self.app.get(
            create_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # account linking confirmation for ORCiD login should fail with BingPreview
    def test_external_login_confirm_email_get_link_user(self):

        user = UserFactory()
        provider_id = fake.ean()
        user.external_identity = {
            'service': {
                provider_id: 'LINK'
            }
        }
        user.add_unconfirmed_email(user.username, external_identity='service')
        user.save()

        link_url = user.get_confirmation_url(
            user.username,
            external_id_provider='service',
            destination='dashboard'
        )

        res = self.app.get(
            link_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403
