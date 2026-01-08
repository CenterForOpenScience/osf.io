from rest_framework import status
import unittest

import pytest
from framework.auth import exceptions
from framework.auth.core import Auth
from tests.base import OsfTestCase
from tests.base import fake
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    PreprintFactory,
    ProjectFactory,
    UserFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
)
from tests.test_webtests import assert_in_html
from website import language
from website.util import api_url_for

@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_implicit_clean
class TestClaiming(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)

    def test_correct_name_shows_in_contributor_list(self):
        name1, email = fake.name(), fake_email()
        UnregUserFactory(fullname=name1, email=email)
        name2, email = fake.name(), fake_email()
        # Added with different name
        self.project.add_unregistered_contributor(fullname=name2,
            email=email, auth=Auth(self.referrer))
        self.project.save()

        res = self.app.get(self.project.url, auth=self.referrer.auth)
        # Correct name is shown
        assert_in_html(name2, res.text)
        assert name1 not in res.text

    def test_user_can_set_password_on_claim_page(self):
        name, email = fake.name(), fake_email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        self.project.reload()
        assert 'Set Password' in res.text
        form = res.get_form('setPasswordForm')
        #form['username'] = new_user.username #Removed as long as E-mail can't be updated.
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        self.app.resolve_redirect(form.submit(self.app))
        new_user.reload()
        assert new_user.check_password('killerqueen')

    def test_sees_is_redirected_if_user_already_logged_in(self):
        name, email = fake.name(), fake_email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        existing = AuthUserFactory()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        # a user is already logged in
        res = self.app.get(claim_url, auth=existing.auth)
        assert res.status_code == 302

    def test_unregistered_users_names_are_project_specific(self):
        name1, name2, email = fake.name(), fake.name(), fake_email()
        project2 = ProjectFactory(creator=self.referrer)
        # different projects use different names for the same unreg contributor
        self.project.add_unregistered_contributor(
            email=email,
            fullname=name1,
            auth=Auth(self.referrer)
        )
        self.project.save()
        project2.add_unregistered_contributor(
            email=email,
            fullname=name2,
            auth=Auth(self.referrer)
        )
        project2.save()
        # Each project displays a different name in the contributor list
        res = self.app.get(self.project.url, auth=self.referrer.auth)
        assert_in_html(name1, res.text)

        res2 = self.app.get(project2.url, auth=self.referrer.auth)
        assert_in_html(name2, res2.text)

    @unittest.skip('as long as E-mails cannot be changed')
    def test_cannot_set_email_to_a_user_that_already_exists(self):
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        # Goes to claim url and successfully claims account
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        self.project.reload()
        assert 'Set Password' in res
        form = res.get_form('setPasswordForm')
        # Fills out an email that is the username of another user
        form['username'] = reg_user.username
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        res = form.submit(follow_redirects=True)
        assert language.ALREADY_REGISTERED.format(email=reg_user.username) in res.text

    def test_correct_display_name_is_shown_at_claim_page(self):
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)

        different_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=unreg.username,
            fullname=different_name,
            auth=Auth(self.referrer),
        )
        self.project.save()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        # Correct name (different_name) should be on page
        assert_in_html(different_name, res.text)


class TestConfirmingEmail(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UnconfirmedUserFactory()
        self.confirmation_url = self.user.get_confirmation_url(
            self.user.username,
            external=False,
        )
        self.confirmation_token = self.user.get_confirmation_token(
            self.user.username
        )

    def test_cannot_remove_another_user_email(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        url = api_url_for('update_user')
        header = {'id': user1.username, 'emails': [{'address': user1.username}]}
        res = self.app.put(url, json=header, auth=user2.auth)
        assert res.status_code == 403

    def test_cannnot_make_primary_email_for_another_user(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        email = 'test@cos.io'
        user1.emails.create(address=email)
        user1.save()
        url = api_url_for('update_user')
        header = {'id': user1.username,
                  'emails': [{'address': user1.username, 'primary': False, 'confirmed': True},
                            {'address': email, 'primary': True, 'confirmed': True}
                  ]}
        res = self.app.put(url, json=header, auth=user2.auth)
        assert res.status_code == 403

    def test_cannnot_add_email_for_another_user(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        email = 'test@cos.io'
        url = api_url_for('update_user')
        header = {'id': user1.username,
                  'emails': [{'address': user1.username, 'primary': True, 'confirmed': True},
                            {'address': email, 'primary': False, 'confirmed': False}
                  ]}
        res = self.app.put(url, json=header, auth=user2.auth)
        assert res.status_code == 403

    def test_error_page_if_confirm_link_is_used(self):
        self.user.confirm_email(self.confirmation_token)
        self.user.save()
        res = self.app.get(self.confirmation_url)

        assert exceptions.InvalidTokenError.message_short in res.text
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
class TestClaimingAsARegisteredUser(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        name, email = fake.name(), fake_email()
        self.user = self.project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    def test_claim_user_registered_with_correct_password(self):
        reg_user = AuthUserFactory()  # NOTE: AuthUserFactory sets password as 'queenfan86'
        url = self.user.get_claim_url(self.project._primary_key)
        # Follow to password re-enter page
        res = self.app.get(url, auth=reg_user.auth, follow_redirects=True)

        # verify that the "Claim Account" form is returned
        assert 'Claim Contributor' in res.text

        form = res.get_form('claimContributorForm')
        form['password'] = 'queenfan86'
        res = form.submit(self.app, auth=reg_user.auth)
        self.app.resolve_redirect(res)
        self.project.reload()
        self.user.reload()
        # user is now a contributor to the project
        assert reg_user in self.project.contributors

        # the unregistered user (self.user) is removed as a contributor, and their
        assert self.user not in self.project.contributors

        # unclaimed record for the project has been deleted
        assert self.project not in self.user.unclaimed_records

    def test_claim_user_registered_preprint_with_correct_password(self):
        preprint = PreprintFactory(creator=self.referrer)
        name, email = fake.name(), fake_email()
        unreg_user = preprint.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=self.referrer)
        )
        reg_user = AuthUserFactory()  # NOTE: AuthUserFactory sets password as 'queenfan86'
        url = unreg_user.get_claim_url(preprint._id)
        # Follow to password re-enter page
        res = self.app.get(url, auth=reg_user.auth, follow_redirects=True)

        # verify that the "Claim Account" form is returned
        assert 'Claim Contributor' in res.text

        form = res.get_form('claimContributorForm')
        form['password'] = 'queenfan86'
        res = form.submit(self.app, auth=reg_user.auth)

        preprint.reload()
        unreg_user.reload()
        # user is now a contributor to the project
        assert reg_user in preprint.contributors

        # the unregistered user (unreg_user) is removed as a contributor, and their
        assert unreg_user not in preprint.contributors

        # unclaimed record for the project has been deleted
        assert preprint not in unreg_user.unclaimed_records
