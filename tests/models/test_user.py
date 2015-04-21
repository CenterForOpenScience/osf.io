from nose.tools import *

from framework import auth
from framework.auth import exceptions
from framework.exceptions import PermissionsError
from website import models
from tests import base
from tests.base import fake
from tests import factories


class UserTestCase(base.OsfTestCase):
    def setUp(self):
        super(UserTestCase, self).setUp()
        self.user = factories.AuthUserFactory()
        self.unregistered = factories.UnregUserFactory()
        self.unconfirmed = factories.UnconfirmedUserFactory()
        self.USERS = (self.user, self.unregistered, self.unconfirmed)

        factories.ProjectFactory(creator=self.user)
        self.project_with_unreg_contrib = factories.ProjectFactory()
        self.project_with_unreg_contrib.add_unregistered_contributor(
            fullname='Unreg',
            email=self.unregistered.username,
            auth=auth.Auth(self.project_with_unreg_contrib.creator)
        )
        self.project_with_unreg_contrib.save()

        self.user.system_tags = ['shared', 'user']
        self.unconfirmed.system_tags = ['shared', 'unconfirmed']

        self.user.aka = ['shared', 'user']
        self.unconfirmed.aka = ['shared', 'unconfirmed']

    def tearDown(self):
        models.Node.remove()
        models.User.remove()
        super(UserTestCase, self).tearDown()

    def test_can_be_merged(self):
        # No addons present
        assert_true(self.user.can_be_merged)
        assert_true(self.unregistered.can_be_merged)
        assert_true(self.unconfirmed.can_be_merged)

        # Add an addon
        addon = self.user.get_or_add_addon('mendeley')
        addon.save()

        assert_false(self.user.can_be_merged)

    def test_merge_unconfirmed(self):
        self.user.merge_user(self.unconfirmed)

        assert_true(self.unconfirmed.is_merged)
        assert_equal(self.unconfirmed.merged_by, self.user)

        assert_true(self.user.is_claimed)
        assert_false(self.user.is_invited)

        # TODO: test profile fields - jobs, schools, social
        # TODO: test security_messages
        # TODO: test mailing_lists

        assert_equal(self.user.system_tags, ['shared', 'user', 'unconfirmed'])
        assert_equal(self.user.aka, ['shared', 'user', 'unconfirmed'])

        # TODO: test emails
        # TODO: test watched
        # TODO: test external_accounts

        # TODO: test api_keys
        assert_equal(self.unconfirmed.email_verifications, {})
        assert_is_none(self.unconfirmed.username)
        assert_is_none(self.unconfirmed.password)
        assert_is_none(self.unconfirmed.verification_key)

    def test_merge_unregistered(self):
        # test only those behaviors that are not tested with unconfirmed users
        self.user.merge_user(self.unregistered)

        assert_true(self.user.is_invited)

        assert_in(self.user, self.project_with_unreg_contrib.contributors)

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2454
    def test_add_unconfirmed_email_when_email_verifications_is_None(self):

        self.user.email_verifications = None
        self.user.save()
        email = fake.email()
        self.user.add_unconfirmed_email(email)
        self.user.save()
        assert_in(email, self.user.unconfirmed_emails)

    def test_unconfirmed_emails(self):
        assert_equal(
            self.user.unconfirmed_emails,
            []
        )
        self.user.add_unconfirmed_email('foo@bar.com')
        assert_equal(
            self.user.unconfirmed_emails,
            ['foo@bar.com']
        )

        assert_equal(
            self.unregistered.unconfirmed_emails,
            []
        )

        assert_equal(
            self.unconfirmed.unconfirmed_emails,
            [self.unconfirmed.username]
        )

        # email_verifications field may be None
        self.user.email_verifications = None
        self.user.save()
        assert_equal(self.user.unconfirmed_emails, [])

    def test_remove_unconfirmed_email(self):
        self.user.add_unconfirmed_email('foo@bar.com')
        self.user.save()

        assert_in('foo@bar.com', self.user.unconfirmed_emails) # sanity check

        self.user.remove_unconfirmed_email('foo@bar.com')
        self.user.save()

        assert_not_in('foo@bar.com', self.user.unconfirmed_emails)

    def test_confirm_email(self):
        token = self.user.add_unconfirmed_email('foo@bar.com')
        self.user.confirm_email(token)

        assert_not_in('foo@bar.com', self.user.unconfirmed_emails)
        assert_in('foo@bar.com', self.user.emails)

    def test_confirm_duplicate_email(self):
        second_user = factories.UserFactory()
        second_user.emails.append('foo@bar.com')
        second_user.save()

        token = self.user.add_unconfirmed_email('foo@bar.com')

        with assert_raises(exceptions.DuplicateEmailError):
            self.user.confirm_email(token)

    def test_confirm_email_comparison_is_case_insensitive(self):
        u = factories.UnconfirmedUserFactory.build(
            username='letsgettacos@lgt.com'
        )
        u.add_unconfirmed_email('LetsGetTacos@LGT.com')
        u.save()
        assert_false(u.is_confirmed)  # sanity check

        token = u.get_confirmation_token('LetsGetTacos@LGT.com')

        confirmed = u.confirm_email(token)
        assert_true(confirmed)
        assert_true(u.is_confirmed)

    def test_cannot_remove_primary_email_from_email_list(self):
        with assert_raises(PermissionsError) as e:
            self.user.remove_email(self.user.username)
        assert_equal(e.exception.message, "Can't remove primary email")

    def test_cannot_remove_primary_email_from_unconfirmed_list(self):
        with assert_raises(PermissionsError) as e:
            self.user.remove_unconfirmed_email(self.user.username)
        assert_equal(e.exception.message, "Can't remove primary email")