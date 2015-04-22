import datetime

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

    def tearDown(self):
        models.Node.remove()
        models.User.remove()
        super(UserTestCase, self).tearDown()

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

        # email_verifications field may be None
        self.user.email_verifications = None
        self.user.save()
        assert_equal(self.user.unconfirmed_emails, [])

    def test_unconfirmed_emails_unregistered_user(self):

        assert_equal(
            factories.UnregUserFactory().unconfirmed_emails,
            []
        )

    def test_unconfirmed_emails_unconfirmed_user(self):
        user = factories.UnconfirmedUserFactory()

        assert_equal(
            user.unconfirmed_emails,
            [user.username]
        )

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


class UserMergingTestCase(base.OsfTestCase):
    ADDONS_UNDER_TEST = {
        'unmergeable': {
            'user_settings': factories.MockAddonUserSettings,
            'node_settings': factories.MockAddonNodeSettings,
        },
        'mergeable': {
            'user_settings': factories.MockAddonUserSettingsMergeable,
            'node_settings': factories.MockAddonNodeSettings,
        }
    }

    def setUp(self):
        super(UserMergingTestCase, self).setUp()
        self.user = factories.UserFactory()

    def _add_unconfirmed_user(self):

        self.unconfirmed = factories.UnconfirmedUserFactory()

        self.user.system_tags = ['shared', 'user']
        self.unconfirmed.system_tags = ['shared', 'unconfirmed']

        self.user.aka = ['shared', 'user']
        self.unconfirmed.aka = ['shared', 'unconfirmed']

    def _add_unregistered_user(self):
        self.unregistered = factories.UnregUserFactory()

        self.project_with_unreg_contrib = factories.ProjectFactory()
        self.project_with_unreg_contrib.add_unregistered_contributor(
            fullname='Unreg',
            email=self.unregistered.username,
            auth=auth.Auth(self.project_with_unreg_contrib.creator)
        )
        self.project_with_unreg_contrib.save()

    def test_can_be_merged_no_addons(self):
        # No addons present
        assert_true(self.user.can_be_merged)

    def test_can_be_merged_unmergable_addon(self):
        self.user.add_addon('unmergeable')

        assert_false(self.user.can_be_merged)

    def test_can_be_merged_mergable_addon(self):
        self.user.add_addon('mergeable')

        assert_true(self.user.can_be_merged)

    def test_can_be_merged_both_addons(self):
        self.user.add_addon('mergeable')
        self.user.add_addon('unmergeable')

        assert_false(self.user.can_be_merged)

    def test_merge(self):
        other_user = factories.UserFactory()
        other_user.save()

        # define values for users' fields
        today = datetime.datetime.now()
        yesterday = today - datetime.timedelta(days=1)

        self.user.aka = ['foo']
        other_user.aka = ['bar']

        self.user.api_keys = [factories.ApiKeyFactory()]
        other_user.api_keys = [factories.ApiKeyFactory()]

        self.user.comments_viewed_timestamp['shared_gt'] = today
        other_user.comments_viewed_timestamp['shared_gt'] = yesterday
        self.user.comments_viewed_timestamp['shared_lt'] = yesterday
        other_user.comments_viewed_timestamp['shared_lt'] = today
        self.user.comments_viewed_timestamp['user'] = yesterday
        other_user.comments_viewed_timestamp['other'] = yesterday

        self.user.email_verifications = {'user': {'email': 'a'}}
        other_user.email_verifications = {'other': {'email': 'b'}}

        self.user.external_accounts = [factories.ExternalAccountFactory()]
        other_user.external_accounts = [factories.ExternalAccountFactory()]

        self.user.mailing_lists = {
            'user': True,
            'shared_gt': True,
            'shared_lt': False,
        }
        other_user.mailing_lists = {
            'other': True,
            'shared_gt': False,
            'shared_lt': True,
        }

        self.user.piwik_token = 'abc'
        other_user.piwik_token = 'def'

        self.user.security_messages = {
            'user': today,
            'shared': today,
        }
        other_user.security_messages = {
            'other': today,
            'shared': today,
        }

        self.user.system_tags = ['user', 'shared']
        other_user.system_tags = ['other', 'shared']

        self.user.watched = [factories.WatchConfigFactory()]
        other_user.watched = [factories.WatchConfigFactory()]

        self.user.save()
        other_user.save()

        # define expected behavior for ALL FIELDS of the User object
        default_to_master_user_fields = [
            '_id',
            'date_confirmed',
            'date_disabled',
            'date_last_login',
            'date_registered',
            'family_name',
            'fullname',
            'given_name',
            'is_claimed',
            'is_invited',
            'is_registered',
            'jobs',
            'locale',
            'merged_by',
            'middle_names',
            'password',
            'piwik_token',
            'recently_added',
            'schools',
            'social',
            'suffix',
            'timezone',
            'username',
            'verification_key',
        ]

        calculated_fields = {
            'aka': ['foo', 'bar'],
            'api_keys': [
                self.user.api_keys[0]._id,
                other_user.api_keys[0]._id,
            ],
            'comments_viewed_timestamp': {
                'user': yesterday,
                'other': yesterday,
                'shared_gt': today,
                'shared_lt': today,
            },
            'email_verifications': {
                'user': {'email': 'a'},
                'other': {'email': 'b'},
            },
            'emails': [
                self.user.username,
                other_user.username,
            ],
            'external_accounts': [
                self.user.external_accounts[0]._id,
                other_user.external_accounts[0]._id,
            ],
            'mailing_lists': {
                'user': True,
                'other': True,
                'shared_gt': True,
                'shared_lt': True,
            },
            'security_messages': {
                'user': today,
                'other': today,
                'shared': today,
            },
            'system_tags': ['user', 'shared', 'other'],
            'unclaimed_records': {},
            'watched': [
                self.user.watched[0]._id,
                other_user.watched[0]._id,
            ],
        }

        # from the explicit rules above, compile expected field/value pairs
        expected = {}
        expected.update(calculated_fields)
        for key in default_to_master_user_fields:
            expected[key] = getattr(self.user, key)

        # ensure all fields of the user object have an explicit expectation
        assert_equal(
            set(expected.keys()),
            set(self.user._fields),
        )

        # perform the merge
        self.user.merge_user(other_user)
        self.user.save()

        # check each field/value pair
        for k, v in expected.iteritems():
            assert_equal(
                getattr(self.user, k),
                v,
                # "{} doesn't match expectation".format(k)
            )

        # check fields set on merged user
        assert_equal(other_user.merged_by, self.user)

    def test_merge_unconfirmed(self):
        self._add_unconfirmed_user()
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
        self._add_unregistered_user()

        self.user.merge_user(self.unregistered)

        assert_true(self.user.is_invited)

        assert_in(self.user, self.project_with_unreg_contrib.contributors)