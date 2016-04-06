# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import mock
import unittest
from nose.tools import *  # noqa (PEP8 asserts)

import pytz
import datetime
import urlparse
import itsdangerous
import random
import string
from dateutil import parser

from modularodm import Q
from modularodm.exceptions import ValidationError, ValidationValueError, ValidationTypeError


from framework.analytics import get_total_activity_count
from framework.exceptions import PermissionsError
from framework.auth import User, Auth
from framework.auth import cas
from framework.sessions.model import Session
from framework.auth import exceptions as auth_exc
from framework.auth.exceptions import ChangePasswordError, ExpiredTokenError
from framework.auth.utils import impute_names_model
from framework.auth.signals import user_merged
from framework.celery_tasks import handlers
from framework.bcrypt import check_password_hash
from website import filters, language, settings, mailchimp_utils
from website.exceptions import NodeStateError
from website.profile.utils import serialize_user
from website.project.signals import contributor_added
from website.project.model import (
    Node, NodeLog, Pointer, ensure_schemas, has_anonymous_link,
    get_pointer_parent, Embargo, MetaSchema, DraftRegistration
)
from website.util.permissions import (
    CREATOR_PERMISSIONS,
    ADMIN,
    READ,
    WRITE,
    DEFAULT_CONTRIBUTOR_PERMISSIONS,
    expand_permissions,
)
from website.util import web_url_for, api_url_for
from website.addons.wiki.exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
    PageCannotRenameError,
    PageConflictError,
    PageNotFoundError,
)

from tests.base import OsfTestCase, Guid, fake, capture_signals, get_default_metaschema
from tests.factories import (
    UserFactory, ApiOAuth2ApplicationFactory, NodeFactory, PointerFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory,
    NodeWikiFactory, RegistrationFactory, UnregUserFactory,
    ProjectWithAddonFactory, UnconfirmedUserFactory, PrivateLinkFactory,
    AuthUserFactory, BookmarkCollectionFactory, CollectionFactory,
    NodeLicenseRecordFactory, InstitutionFactory
)
from tests.test_features import requires_piwik
from tests.utils import mock_archive

GUID_FACTORIES = UserFactory, NodeFactory, ProjectFactory


class TestUserValidation(OsfTestCase):

    def setUp(self):
        super(TestUserValidation, self).setUp()
        self.user = AuthUserFactory()

    def test_validate_fullname_none(self):
        self.user.fullname = None
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_fullname_empty(self):
        self.user.fullname = ''
        with assert_raises(ValidationValueError):
            self.user.save()

    def test_validate_social_profile_websites_empty(self):
        self.user.social = {'profileWebsites': []}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], [])

    def test_validate_social_valid_website_simple(self):
        self.user.social = {'profileWebsites': ['http://cos.io/']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://cos.io/'])

    def test_validate_social_valid_website_protocol(self):
        self.user.social = {'profileWebsites': ['https://definitelyawebsite.com']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['https://definitelyawebsite.com'])

    def test_validate_social_valid_website_ipv4(self):
        self.user.social = {'profileWebsites': ['http://127.0.0.1']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://127.0.0.1'])

    def test_validate_social_valid_website_path(self):
        self.user.social = {'profileWebsites': ['http://definitelyawebsite.com/definitelyapage/']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://definitelyawebsite.com/definitelyapage/'])

    def test_validate_social_valid_website_portandpath(self):
        self.user.social = {'profileWebsites': ['http://127.0.0.1:5000/hello/']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://127.0.0.1:5000/hello/'])

    def test_validate_social_valid_website_querystrings(self):
        self.user.social = {'profileWebsites': ['http://definitelyawebsite.com?real=yes&page=definitely']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://definitelyawebsite.com?real=yes&page=definitely'])

    def test_validate_multiple_profile_websites_valid(self):
        self.user.social = {'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com']}
        self.user.save()
        assert_equal(self.user.social['profileWebsites'], ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com'])

    def test_validate_social_profile_websites_invalid(self):
        self.user.social = {'profileWebsites': ['help computer']}
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_multiple_profile_social_profile_websites_invalid(self):
        self.user.social = {'profileWebsites': ['http://cos.io/', 'help computer', 'http://dinosaurs.com']}
        with assert_raises(ValidationError):
            self.user.save()

    def test_empty_social_links(self):
        assert_equal(self.user.social_links, {})
        assert_equal(len(self.user.social_links), 0)

    def test_profile_website_unchanged(self):
        self.user.social = {'profileWebsites': ['http://cos.io/']}
        self.user.save()
        assert_equal(self.user.social_links['profileWebsites'], ['http://cos.io/'])
        assert_equal(len(self.user.social_links), 1)

    def test_various_social_handles(self):
        self.user.social = {
            'profileWebsites': ['http://cos.io/'],
            'twitter': 'OSFramework',
            'github': 'CenterForOpenScience'
        }
        self.user.save()
        assert_equal(self.user.social_links, {
            'profileWebsites': ['http://cos.io/'],
            'twitter': 'http://twitter.com/OSFramework',
            'github': 'http://github.com/CenterForOpenScience'
        })

    def test_multiple_profile_websites(self):
        self.user.social = {
            'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com'],
            'twitter': 'OSFramework',
            'github': 'CenterForOpenScience'
        }
        self.user.save()
        assert_equal(self.user.social_links, {
            'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com'],
            'twitter': 'http://twitter.com/OSFramework',
            'github': 'http://github.com/CenterForOpenScience'
        })

    def test_nonsocial_ignored(self):
        self.user.social = {
            'foo': 'bar',
        }
        self.user.save()
        assert_equal(self.user.social_links, {})

    def test_validate_jobs_valid(self):
        self.user.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1980',
        }]
        self.user.save()

    def test_validate_jobs_institution_empty(self):
        self.user.jobs = [{'institution': ''}]
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_jobs_bad_end_date(self):
        # end year is < start year
        self.user.jobs = [{
            'institution': fake.company(),
            'department': fake.bs(),
            'position': fake.catch_phrase(),
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1960',
        }]
        with assert_raises(ValidationValueError):
            self.user.save()

    def test_validate_schools_bad_end_date(self):
        # end year is < start year
        self.user.schools = [{
            'degree': fake.catch_phrase(),
            'institution': fake.company(),
            'department': fake.bs(),
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1960',
        }]
        with assert_raises(ValidationValueError):
            self.user.save()

    def test_validate_jobs_bad_year(self):
        start_year = ['hi', '20507', '99', '67.34']
        for year in start_year:
            self.user.jobs = [{
                'institution': fake.company(),
                'department': fake.bs(),
                'position': fake.catch_phrase(),
                'startMonth': 1,
                'startYear': year,
                'endMonth': 1,
                'endYear': '1960',
            }]
            with assert_raises(ValidationValueError):
                self.user.save()

    def test_validate_schools_bad_year(self):
        start_year = ['hi', '20507', '99', '67.34']
        for year in start_year:
            self.user.schools = [{
                'degree': fake.catch_phrase(),
                'institution': fake.company(),
                'department': fake.bs(),
                'startMonth': 1,
                'startYear': year,
                'endMonth': 1,
                'endYear': '1960',
            }]
            with assert_raises(ValidationValueError):
                self.user.save()


class TestUser(OsfTestCase):

    def setUp(self):
        super(TestUser, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)

    def test_repr(self):
        assert_in(self.user.username, repr(self.user))
        assert_in(self.user._id, repr(self.user))

    def test_update_guessed_names(self):
        name = fake.name()
        u = User(fullname=name)
        u.update_guessed_names()
        u.save()

        parsed = impute_names_model(name)
        assert_equal(u.fullname, name)
        assert_equal(u.given_name, parsed['given_name'])
        assert_equal(u.middle_names, parsed['middle_names'])
        assert_equal(u.family_name, parsed['family_name'])
        assert_equal(u.suffix, parsed['suffix'])

    def test_non_registered_user_is_not_active(self):
        u = User(username=fake.email(),
                 fullname='Freddie Mercury',
                 is_registered=False)
        u.set_password('killerqueen')
        u.save()
        assert_false(u.is_active)

    def test_create_unregistered(self):
        name, email = fake.name(), fake.email()
        u = User.create_unregistered(email=email,
                                     fullname=name)
        u.save()
        assert_equal(u.username, email)
        assert_false(u.is_registered)
        assert_false(u.is_claimed)
        assert_true(u.is_invited)
        assert_false(email in u.emails)
        parsed = impute_names_model(name)
        assert_equal(u.given_name, parsed['given_name'])

    @mock.patch('framework.auth.core.User.update_search')
    def test_search_not_updated_for_unreg_users(self, update_search):
        u = User.create_unregistered(fullname=fake.name(), email=fake.email())
        u.save()
        assert not update_search.called

    @mock.patch('framework.auth.core.User.update_search')
    def test_search_updated_for_registered_users(self, update_search):
        UserFactory(is_registered=True)
        assert_true(update_search.called)

    def test_create_unregistered_raises_error_if_already_in_db(self):
        u = UnregUserFactory()
        dupe = User.create_unregistered(fullname=fake.name(), email=u.username)
        with assert_raises(ValidationValueError):
            dupe.save()

    def test_user_with_no_password_is_not_active(self):
        u = User(
            username=fake.email(),
            fullname='Freddie Mercury',
            is_registered=True,
        )
        u.save()
        assert_false(u.is_active)

    def test_merged_user_is_not_active(self):
        master = UserFactory()
        dupe = UserFactory(merged_by=master)
        assert_false(dupe.is_active)

    def test_merged_user_with_two_account_on_same_project_with_different_visibility_and_permissions(self):
        user2 = UserFactory.build()
        user2.save()

        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(user2, log=False)
        project.add_contributor(self.user, log=False)
        project.set_permissions(user=self.user, permissions=['read'])
        project.set_permissions(user=user2, permissions=['read', 'write', 'admin'])
        project.set_visible(user=self.user, visible=False)
        project.set_visible(user=user2, visible=True)
        project.save()
        self.user.merge_user(user2)
        self.user.save()
        project.reload()
        assert_true('admin' in project.permissions[self.user._id])
        assert_true(self.user._id in project.visible_contributor_ids)
        assert_false(project.is_contributor(user2))

    def test_cant_create_user_without_username(self):
        u = User()  # No username given
        with assert_raises(ValidationError):
            u.save()

    def test_date_registered_upon_saving(self):
        u = User(username=fake.email(), fullname='Foo bar')
        u.save()
        assert_true(u.date_registered)

    def test_create(self):
        name, email = fake.name(), fake.email()
        user = User.create(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_true(user.check_password('foobar'))
        assert_true(user._id)
        assert_equal(user.given_name, impute_names_model(name)['given_name'])

    def test_create_unconfirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_unconfirmed(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_false(user.is_registered)
        assert_equal(len(user.email_verifications.keys()), 1)
        assert_equal(
            len(user.emails),
            0,
            'primary email has not been added to emails list'
        )

    def test_create_confirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_confirmed(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_true(user.is_registered)
        assert_true(user.is_claimed)
        assert_equal(user.date_registered, user.date_confirmed)

    def test_cant_create_user_without_full_name(self):
        u = User(username=fake.email())
        with assert_raises(ValidationError):
            u.save()

    @mock.patch('website.security.random_string')
    def test_add_unconfirmed_email(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        assert_equal(len(u.email_verifications.keys()), 0)
        u.add_unconfirmed_email('foo@bar.com')
        assert_equal(len(u.email_verifications.keys()), 1)
        assert_equal(u.email_verifications[token]['email'], 'foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_add_unconfirmed_email_adds_expiration_date(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        u.add_unconfirmed_email("test@osf.io")
        assert_is_instance(u.email_verifications[token]['expiration'], datetime.datetime)

    def test_add_blank_unconfirmed_email(self):
        with assert_raises(ValidationError) as exc_info:
            self.user.add_unconfirmed_email('')
        assert_equal(exc_info.exception.message, "Invalid Email")

    @mock.patch('website.security.random_string')
    def test_get_confirmation_token(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        u.add_unconfirmed_email('foo@bar.com')
        assert_equal(u.get_confirmation_token('foo@bar.com'), '12345')
        assert_equal(u.get_confirmation_token('fOo@bar.com'), '12345')

    def test_get_confirmation_token_when_token_is_expired_raises_error(self):
        u = UserFactory()
        # Make sure token is already expired
        expiration = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with assert_raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_token_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        # sanity check
        with assert_raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

        random_string.return_value = '54321'

        token = u.get_confirmation_token('foo@bar.com', force=True)
        assert_equal(token, '54321')

    # Some old users will not have an 'expired' key in their email_verifications.
    # Assume the token in expired
    def test_get_confirmation_token_if_email_verification_doesnt_have_expiration(self):
        u = UserFactory()

        email = fake.email()
        u.add_unconfirmed_email(email)
        # manually remove 'expiration' key
        token = u.get_confirmation_token(email)
        del u.email_verifications[token]['expiration']
        u.save()

        with assert_raises(ExpiredTokenError):
            u.get_confirmation_token(email)

    @mock.patch('website.security.random_string')
    def test_get_confirmation_url(self, random_string):
        random_string.return_value = 'abcde'
        u = UserFactory()
        u.add_unconfirmed_email('foo@bar.com')
        assert_equal(u.get_confirmation_url('foo@bar.com'),
                '{0}confirm/{1}/{2}/'.format(settings.DOMAIN, u._primary_key, 'abcde'))

    def test_get_confirmation_url_when_token_is_expired_raises_error(self):
        u = UserFactory()
        # Make sure token is already expired
        expiration = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with assert_raises(ExpiredTokenError):
            u.get_confirmation_url('foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_url_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        # sanity check
        with assert_raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

        random_string.return_value = '54321'

        url = u.get_confirmation_url('foo@bar.com', force=True)
        expected = '{0}confirm/{1}/{2}/'.format(settings.DOMAIN, u._primary_key, '54321')
        assert_equal(url, expected)

    def test_confirm_primary_email(self):
        u = UnconfirmedUserFactory()
        token = u.get_confirmation_token(u.username)
        confirmed = u.confirm_email(token)
        u.save()
        assert_true(confirmed)
        assert_equal(len(u.email_verifications.keys()), 0)
        assert_in(u.username, u.emails)
        assert_true(u.is_registered)
        assert_true(u.is_claimed)

    def test_verify_confirmation_token(self):
        u = UserFactory.build()
        u.add_unconfirmed_email('foo@bar.com')
        u.save()

        with assert_raises(auth_exc.InvalidTokenError):
            u._get_unconfirmed_email_for_token('badtoken')

        valid_token = u.get_confirmation_token('foo@bar.com')
        assert_true(u._get_unconfirmed_email_for_token(valid_token))
        manual_expiration = datetime.datetime.utcnow() - datetime.timedelta(0, 10)
        u._set_email_token_expiration(valid_token, expiration=manual_expiration)

        with assert_raises(auth_exc.ExpiredTokenError):
            u._get_unconfirmed_email_for_token(valid_token)

    def test_verify_confirmation_token_when_token_has_no_expiration(self):
        # A user verification token may not have an expiration
        email = fake.email()
        u = UserFactory.build()
        u.add_unconfirmed_email(email)
        token = u.get_confirmation_token(email)
        # manually remove expiration to simulate legacy user
        del u.email_verifications[token]['expiration']
        u.save()

        assert_true(u._get_unconfirmed_email_for_token(token))

    def test_factory(self):
        # Clear users
        Node.remove()
        User.remove()
        user = UserFactory()
        assert_equal(User.find().count(), 1)
        assert_true(user.username)
        another_user = UserFactory(username='joe@example.com')
        assert_equal(another_user.username, 'joe@example.com')
        assert_equal(User.find().count(), 2)
        assert_true(user.date_registered)

    def test_format_surname(self):
        user = UserFactory(fullname='Duane Johnson')
        summary = user.get_summary(formatter='surname')
        assert_equal(
            summary['user_display_name'],
            'Johnson'
        )

    def test_format_surname_one_name(self):
        user = UserFactory(fullname='Rock')
        summary = user.get_summary(formatter='surname')
        assert_equal(
            summary['user_display_name'],
            'Rock'
        )

    def test_is_watching(self):
        # User watches a node
        watched_node = NodeFactory()
        unwatched_node = NodeFactory()
        config = WatchConfigFactory(node=watched_node)
        self.user.watched.append(config)
        self.user.save()
        assert_true(self.user.is_watching(watched_node))
        assert_false(self.user.is_watching(unwatched_node))

    def test_serialize(self):
        d = self.user.serialize()
        assert_equal(d['id'], str(self.user._primary_key))
        assert_equal(d['fullname'], self.user.fullname)
        assert_equal(d['registered'], self.user.is_registered)
        assert_equal(d['url'], self.user.url)

    def test_set_password(self):
        user = User(username=fake.email(), fullname='Nick Cage')
        user.set_password('ghostrider')
        user.save()
        assert_true(check_password_hash(user.password, 'ghostrider'))

    def test_check_password(self):
        user = User(username=fake.email(), fullname='Nick Cage')
        user.set_password('ghostrider')
        user.save()
        assert_true(user.check_password('ghostrider'))
        assert_false(user.check_password('ghostride'))

    def test_change_password(self):
        old_password = 'password'
        new_password = 'new password'
        confirm_password = new_password
        self.user.set_password(old_password)
        self.user.save()
        self.user.change_password(old_password, new_password, confirm_password)
        assert_true(self.user.check_password(new_password))

    def test_change_password_invalid(self, old_password=None, new_password=None, confirm_password=None,
                                     error_message='Old password is invalid'):
        self.user.set_password('password')
        self.user.save()
        with assert_raises(ChangePasswordError) as error:
            self.user.change_password(old_password, new_password, confirm_password)
            self.user.save()
        assert_in(error_message, error.exception.message)
        assert_false(self.user.check_password(new_password))

    def test_change_password_invalid_old_password(self):
        self.test_change_password_invalid(
            'invalid old password',
            'new password',
            'new password',
            'Old password is invalid',
        )

    def test_change_password_invalid_new_password_length(self):
        self.test_change_password_invalid(
            'password',
            '12345',
            '12345',
            'Password should be at least six characters',
        )

    def test_change_password_invalid_confirm_password(self):
        self.test_change_password_invalid(
            'password',
            'new password',
            'invalid confirm password',
            'Password does not match the confirmation',
        )

    def test_change_password_invalid_blank_password(self, old_password='', new_password='', confirm_password=''):
        self.test_change_password_invalid(
            old_password,
            new_password,
            confirm_password,
            'Passwords cannot be blank',
        )

    def test_change_password_invalid_blank_new_password(self):
        for password in (None, '', '      '):
            self.test_change_password_invalid_blank_password('password', password, 'new password')

    def test_change_password_invalid_blank_confirm_password(self):
        for password in (None, '', '      '):
            self.test_change_password_invalid_blank_password('password', 'new password', password)

    def test_url(self):
        assert_equal(
            self.user.url,
            '/{0}/'.format(self.user._primary_key)
        )

    def test_absolute_url(self):
        assert_equal(
            self.user.absolute_url,
            urlparse.urljoin(settings.DOMAIN, '/{0}/'.format(self.user._primary_key))
        )

    def test_profile_image_url(self):
        expected = filters.gravatar(
            self.user,
            use_ssl=True,
            size=settings.PROFILE_IMAGE_MEDIUM
        )
        assert_equal(self.user.profile_image_url(settings.PROFILE_IMAGE_MEDIUM), expected)

    def test_profile_image_url_has_no_default_size(self):
        expected = filters.gravatar(
            self.user,
            use_ssl=True,
        )
        assert_equal(self.user.profile_image_url(), expected)
        size = urlparse.parse_qs(urlparse.urlparse(self.user.profile_image_url()).query).get('size')
        assert_equal(size, None)

    def test_activity_points(self):
        assert_equal(self.user.get_activity_points(db=self.db),
                    get_total_activity_count(self.user._primary_key))

    def test_serialize_user(self):
        master = UserFactory()
        user = UserFactory.build()
        master.merge_user(user)
        d = serialize_user(user)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d.get('username', None), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
        assert_equal(d['active'], user.is_active)

    def test_serialize_user_full(self):
        master = UserFactory()
        user = UserFactory.build()
        master.merge_user(user)
        d = serialize_user(user, full=True)
        gravatar = filters.gravatar(
            user,
            use_ssl=True,
            size=settings.PROFILE_IMAGE_LARGE
        )
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d.get('username'), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['gravatar_url'], gravatar)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
        assert_equal(d['is_merged'], user.is_merged)
        assert_equal(d['merged_by']['url'], user.merged_by.url)
        assert_equal(d['merged_by']['absolute_url'], user.merged_by.absolute_url)
        projects = [
            node
            for node in user.contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = [p for p in projects if p.is_public]
        assert_equal(d['number_projects'], len(projects))
        assert_equal(d['number_public_projects'], len(public_projects))

    def test_recently_added(self):
        # Project created
        project = ProjectFactory()

        assert_true(hasattr(self.user, 'recently_added'))

        # Two users added as contributors
        user2 = UserFactory()
        user3 = UserFactory()
        project.add_contributor(contributor=user2, auth=self.auth)
        project.add_contributor(contributor=user3, auth=self.auth)
        assert_equal(user3, self.user.recently_added[0])
        assert_equal(user2, self.user.recently_added[1])
        assert_equal(len(self.user.recently_added), 2)

    def test_recently_added_multi_project(self):
        # Three users are created
        user2 = UserFactory()
        user3 = UserFactory()
        user4 = UserFactory()

        # 2 projects created
        project = ProjectFactory()
        project2 = ProjectFactory()

        # Users 2 and 3 are added to original project
        project.add_contributor(contributor=user2, auth=self.auth)
        project.add_contributor(contributor=user3, auth=self.auth)

        # Users 2 and 3 are added to original project
        project2.add_contributor(contributor=user2, auth=self.auth)
        project2.add_contributor(contributor=user4, auth=self.auth)

        assert_equal(user4, self.user.recently_added[0])
        assert_equal(user2, self.user.recently_added[1])
        assert_equal(user3, self.user.recently_added[2])
        assert_equal(len(self.user.recently_added), 3)

    def test_recently_added_length(self):
        # Project created
        project = ProjectFactory()

        assert_equal(len(self.user.recently_added), 0)
        # Add 17 users
        for _ in range(17):
            project.add_contributor(
                contributor=UserFactory(),
                auth=self.auth
            )

        assert_equal(len(self.user.recently_added), 15)

    def test_display_full_name_registered(self):
        u = UserFactory()
        assert_equal(u.display_full_name(), u.fullname)

    def test_display_full_name_unregistered(self):
        name = fake.name()
        u = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=name, email=u.username,
            auth=Auth(project.creator))
        project.save()
        assert_equal(u.display_full_name(node=project), name)

    def test_get_projects_in_common(self):
        user2 = UserFactory()
        project = ProjectFactory(creator=self.user)
        project.add_contributor(contributor=user2, auth=self.auth)
        project.save()

        project_keys = set([node._id for node in self.user.contributed])
        projects = set(self.user.contributed)
        user2_project_keys = set([node._id for node in user2.contributed])

        assert_equal(self.user.get_projects_in_common(user2, primary_keys=True),
                     project_keys.intersection(user2_project_keys))
        assert_equal(self.user.get_projects_in_common(user2, primary_keys=False),
                     projects.intersection(user2.contributed))

    def test_n_projects_in_common(self):
        user2 = UserFactory()
        user3 = UserFactory()
        project = ProjectFactory(creator=self.user)

        project.add_contributor(contributor=user2, auth=self.auth)
        project.save()

        assert_equal(self.user.n_projects_in_common(user2), 1)
        assert_equal(self.user.n_projects_in_common(user3), 0)

    def test_user_get_cookie(self):
        user = UserFactory()
        super_secret_key = 'children need maps'
        signer = itsdangerous.Signer(super_secret_key)
        session = Session(data={
            'auth_user_id': user._id,
            'auth_user_username': user.username,
            'auth_user_fullname': user.fullname,
        })
        session.save()

        assert_equal(signer.unsign(user.get_or_create_cookie(super_secret_key)), session._id)

    def test_user_get_cookie_no_session(self):
        user = UserFactory()
        super_secret_key = 'children need maps'
        signer = itsdangerous.Signer(super_secret_key)
        assert_equal(
            0,
            Session.find(Q('data.auth_user_id', 'eq', user._id)).count()
        )

        cookie = user.get_or_create_cookie(super_secret_key)

        session = Session.find(Q('data.auth_user_id', 'eq', user._id))[0]

        assert_equal(session._id, signer.unsign(cookie))
        assert_equal(session.data['auth_user_id'], user._id)
        assert_equal(session.data['auth_user_username'], user.username)
        assert_equal(session.data['auth_user_fullname'], user.fullname)

    def test_get_user_by_cookie(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        assert_equal(user, User.from_cookie(cookie))

    def test_get_user_by_cookie_returns_none(self):
        assert_equal(None, User.from_cookie(''))

    def test_get_user_by_cookie_bad_cookie(self):
        assert_equal(None, User.from_cookie('foobar'))

    def test_get_user_by_cookie_no_user_id(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        session = Session.find_one(Q('data.auth_user_id', 'eq', user._id))
        del session.data['auth_user_id']
        assert_in('data', session.save())

        assert_equal(None, User.from_cookie(cookie))

    def test_get_user_by_cookie_no_session(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        Session.remove()
        assert_equal(
            0,
            Session.find(Q('data.auth_user_id', 'eq', user._id)).count()
        )
        assert_equal(None, User.from_cookie(cookie))


class TestUserParse(unittest.TestCase):

    def test_parse_first_last(self):
        parsed = impute_names_model('John Darnielle')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'Darnielle')

    def test_parse_first_last_particles(self):
        parsed = impute_names_model('John van der Slice')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'van der Slice')


class TestDisablingUsers(OsfTestCase):
    def setUp(self):
        super(TestDisablingUsers, self).setUp()
        self.user = UserFactory()

    def test_user_enabled_by_default(self):
        assert_false(self.user.is_disabled)

    def test_disabled_user(self):
        """Ensure disabling a user sets date_disabled"""
        self.user.is_disabled = True
        self.user.save()

        assert_true(isinstance(self.user.date_disabled, datetime.datetime))
        assert_true(self.user.is_disabled)
        assert_false(self.user.is_active)

    def test_reenabled_user(self):
        """Ensure restoring a disabled user unsets date_disabled"""
        self.user.is_disabled = True
        self.user.save()

        self.user.is_disabled = False
        self.user.save()

        assert_is_none(self.user.date_disabled)
        assert_false(self.user.is_disabled)
        assert_true(self.user.is_active)

    def test_is_disabled_idempotency(self):
        self.user.is_disabled = True
        self.user.save()

        old_date_disabled = self.user.date_disabled

        self.user.is_disabled = True
        self.user.save()

        new_date_disabled = self.user.date_disabled

        assert_equal(new_date_disabled, old_date_disabled)

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_disable_account(self, mock_mail):
        self.user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST] = True
        self.user.save()
        self.user.disable_account()

        assert_true(self.user.is_disabled)
        assert_true(isinstance(self.user.date_disabled, datetime.datetime))
        assert_false(self.user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST])

    def test_disable_account_api(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True
        with assert_raises(mailchimp_utils.mailchimp.InvalidApiKeyError):
            self.user.disable_account()


class TestMergingUsers(OsfTestCase):

    def setUp(self):
        super(TestMergingUsers, self).setUp()
        with self.context:
            handlers.celery_before_request()

        self.master = UserFactory(
            fullname='Joe Shmo',
            is_registered=True,
            emails=['joe@example.com'],
        )
        self.dupe = UserFactory(
            fullname='Joseph Shmo',
            emails=['joseph123@hotmail.com']
        )

    def _merge_dupe(self):
        '''Do the actual merge.'''
        self.master.merge_user(self.dupe)
        self.master.save()

    def test_bookmark_collection_nodes_arent_merged(self):
        dashnode = ProjectFactory(creator=self.dupe, is_bookmark_collection=True)

        self._merge_dupe()

        assert_not_in(dashnode, self.master. contributed)

    def test_dupe_is_merged(self):
        self._merge_dupe()
        assert_true(self.dupe.is_merged)
        assert_equal(self.dupe.merged_by, self.master)

    def test_dupe_email_is_appended(self):
        self._merge_dupe()
        assert_in('joseph123@hotmail.com', self.master.emails)

    def test_send_user_merged_signal(self):
        self.dupe.mailchimp_mailing_lists['foo'] = True
        self.dupe.save()

        with capture_signals() as mock_signals:
            self._merge_dupe()
            assert_equal(mock_signals.signals_sent(), set([user_merged]))

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_merged_user_unsubscribed_from_mailing_lists(self, mock_get_mailchimp_api):
        list_name = 'foo'
        username = self.dupe.username
        self.dupe.mailchimp_mailing_lists[list_name] = True
        self.dupe.save()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 2, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)
        self._merge_dupe()
        handlers.celery_teardown_request()
        mock_client.lists.unsubscribe.assert_called_with(id=list_id, email={'email': username}, send_goodbye=False)
        assert_false(self.dupe.mailchimp_mailing_lists[list_name])

    def test_inherits_projects_contributed_by_dupe(self):
        project = ProjectFactory()
        project.add_contributor(self.dupe)
        project.save()
        self._merge_dupe()
        project.reload()
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))

    def test_inherits_projects_created_by_dupe(self):
        project = ProjectFactory(creator=self.dupe)
        self._merge_dupe()
        project.reload()
        assert_equal(project.creator, self.master)

    def test_adding_merged_user_as_contributor_adds_master(self):
        project = ProjectFactory(creator=UserFactory())
        self._merge_dupe()
        project.add_contributor(contributor=self.dupe)
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))

    def test_merging_dupe_who_is_contributor_on_same_projects(self):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=self.master)
        project.add_contributor(contributor=self.dupe)
        project.save()
        self._merge_dupe()  # perform the merge
        project.reload()
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))
        assert_equal(len(project.contributors), 2) # creator and master
                                                   # are the only contribs


class TestGUID(OsfTestCase):

    def setUp(self):
        super(TestGUID, self).setUp()
        self.records = {}
        for factory in GUID_FACTORIES:
            record = factory()
            self.records[record._name] = record

    def test_guid(self):

        for record in self.records.values():

            record_guid = Guid.load(record._primary_key)

            # GUID must exist
            assert_false(record_guid is None)

            # Primary keys of GUID and record must be the same
            assert_equal(
                record_guid._primary_key,
                record._primary_key
            )

            # GUID must refer to record
            assert_equal(
                record_guid.referent,
                record
            )


class TestApiOAuth2Application(OsfTestCase):
    def setUp(self):
        super(TestApiOAuth2Application, self).setUp()
        self.api_app = ApiOAuth2ApplicationFactory()

    def test_must_have_owner(self):
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(owner=None)
            api_app.save()

    def test_client_id_auto_populates(self):
        assert_greater(len(self.api_app.client_id), 0)

    def test_client_secret_auto_populates(self):
        assert_greater(len(self.api_app.client_secret), 0)

    def test_new_app_is_not_flagged_as_deleted(self):
        assert_true(self.api_app.is_active)

    def test_cant_edit_creation_date(self):
        with assert_raises(AttributeError):
            self.api_app.date_created = datetime.datetime.utcnow()

    def test_invalid_home_url_raises_exception(self):
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(home_url="Totally not a URL")
            api_app.save()

    def test_invalid_callback_url_raises_exception(self):
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(callback_url="itms://itunes.apple.com/us/app/apple-store/id375380948?mt=8")
            api_app.save()

    def test_name_cannot_be_blank(self):
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(name='')
            api_app.save()

    def test_long_name_raises_exception(self):
        long_name = ('JohnJacobJingelheimerSchmidtHisNameIsMyN' * 5) + 'a'
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(name=long_name)
            api_app.save()

    def test_long_description_raises_exception(self):
        long_desc = ('JohnJacobJingelheimerSchmidtHisNameIsMyN' * 25) + 'a'
        with assert_raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(description=long_desc)
            api_app.save()

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_active_set_to_false_upon_successful_deletion(self, mock_method):
        mock_method.return_value(True)
        self.api_app.deactivate(save=True)
        self.api_app.reload()
        assert_false(self.api_app.is_active)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_active_remains_true_when_cas_token_deletion_fails(self, mock_method):
        mock_method.side_effect = cas.CasHTTPError("CAS can't revoke tokens", 400, 'blank', 'blank')
        with assert_raises(cas.CasHTTPError):
            self.api_app.deactivate(save=True)
        self.api_app.reload()
        assert_true(self.api_app.is_active)


class TestNodeWikiPage(OsfTestCase):

    def setUp(self):
        super(TestNodeWikiPage, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.wiki = NodeWikiFactory(user=self.user, node=self.project)

    def test_factory(self):
        wiki = NodeWikiFactory()
        assert_equal(wiki.page_name, 'home')
        assert_equal(wiki.version, 1)
        assert_true(hasattr(wiki, 'is_current'))
        assert_equal(wiki.content, 'Some content')
        assert_true(wiki.user)
        assert_true(wiki.node)

    def test_url(self):
        assert_equal(self.wiki.url, '{project_url}wiki/home/'
                                    .format(project_url=self.project.url))


class TestUpdateNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestUpdateNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert_equal(project1.get_wiki_page('home'), None)

    def test_default_is_current(self):
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki('home', 'Hello world 2', self.auth)
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki('home', 'Hello world 3', self.auth)

    def test_wiki_content(self):
        # Wiki has correct content
        assert_equal(self.project.get_wiki_page('home').content, 'Hello world')
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # Both versions have the expected content
        assert_equal(self.project.get_wiki_page('home', 2).content, 'Hola mundo')
        assert_equal(self.project.get_wiki_page('home', 1).content, 'Hello world')

    def test_current(self):
        # Wiki is current
        assert_true(self.project.get_wiki_page('home', 1).is_current)
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # New version is current, old version is not
        assert_true(self.project.get_wiki_page('home', 2).is_current)
        assert_false(self.project.get_wiki_page('home', 1).is_current)

    def test_update_log(self):
        # Updates are logged
        assert_equal(self.project.logs[-1].action, 'wiki_updated')
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # There are two update logs
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)

    def test_update_log_specifics(self):
        page = self.project.get_wiki_page('home')
        log = self.project.logs[-1]
        assert_equal('wiki_updated', log.action)
        assert_equal(page._primary_key, log.params['page_id'])

    def test_wiki_versions(self):
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 1)
        # Update wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 2)
        # Versions are different
        assert_not_equal(self.versions['home'][0], self.versions['home'][1])

    def test_update_two_node_wikis(self):
        # user updates a second wiki for the same node
        self.project.update_node_wiki('second', 'Hola mundo', self.auth)
        # each wiki only has one version
        assert_equal(len(self.versions['home']), 1)
        assert_equal(len(self.versions['second']), 1)
        # There are 2 logs saved
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)
        # Each wiki has the expected content
        assert_equal(self.project.get_wiki_page('home').content, 'Hello world')
        assert_equal(self.project.get_wiki_page('second').content, 'Hola mundo')

    def test_update_name_invalid(self):
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        with assert_raises(NameInvalidError):
            self.project.update_node_wiki(invalid_name, 'more valid content', self.auth)


class TestRenameNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestRenameNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_rename_name_not_found(self):
        for invalid_name in [None, '', '   ', 'Unknown Name']:
            with assert_raises(PageNotFoundError):
                self.project.rename_node_wiki(invalid_name, None, auth=self.auth)

    def test_rename_new_name_invalid_none_or_blank(self):
        name = 'New Page'
        self.project.update_node_wiki(name, 'new content', self.auth)
        for invalid_name in [None, '', '   ']:
            with assert_raises(NameEmptyError):
                self.project.rename_node_wiki(name, invalid_name, auth=self.auth)

    def test_rename_new_name_invalid_special_characters(self):
        old_name = 'old name'
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        self.project.update_node_wiki(old_name, 'some content', self.auth)
        with assert_raises(NameInvalidError):
            self.project.rename_node_wiki(old_name, invalid_name, self.auth)

    def test_rename_name_maximum_length(self):
        old_name = 'short name'
        new_name = 'a' * 101
        self.project.update_node_wiki(old_name, 'some content', self.auth)
        with assert_raises(NameMaximumLengthError):
            self.project.rename_node_wiki(old_name, new_name, self.auth)

    def test_rename_cannot_rename(self):
        for args in [('home', 'New Home'), ('HOME', 'New Home')]:
            with assert_raises(PageCannotRenameError):
                self.project.rename_node_wiki(*args, auth=self.auth)

    def test_rename_page_not_found(self):
        for args in [('abc123', 'New Home'), (u'ˆ•¶£˙˙®¬™∆˙', 'New Home')]:
            with assert_raises(PageNotFoundError):
                self.project.rename_node_wiki(*args, auth=self.auth)

    def test_rename_page(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.project.update_node_wiki(old_name, 'new content', self.auth)
        self.project.rename_node_wiki(old_name, new_name, self.auth)
        page = self.project.get_wiki_page(new_name)
        assert_not_equal(old_name, page.page_name)
        assert_equal(new_name, page.page_name)
        assert_equal(self.project.logs[-1].action, NodeLog.WIKI_RENAMED)

    def test_rename_page_case_sensitive(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.project.update_node_wiki(old_name, 'new content', self.auth)
        self.project.rename_node_wiki(old_name, new_name, self.auth)
        new_page = self.project.get_wiki_page(new_name)
        assert_equal(new_name, new_page.page_name)
        assert_equal(self.project.logs[-1].action, NodeLog.WIKI_RENAMED)

    def test_rename_existing_deleted_page(self):
        old_name = 'old page'
        new_name = 'new page'
        old_content = 'old content'
        new_content = 'new content'
        # create the old page and delete it
        self.project.update_node_wiki(old_name, old_content, self.auth)
        assert_in(old_name, self.project.wiki_pages_current)
        self.project.delete_node_wiki(old_name, self.auth)
        assert_not_in(old_name, self.project.wiki_pages_current)
        # create the new page and rename it
        self.project.update_node_wiki(new_name, new_content, self.auth)
        self.project.rename_node_wiki(new_name, old_name, self.auth)
        new_page = self.project.get_wiki_page(old_name)
        old_page = self.project.get_wiki_page(old_name, version=1)
        # renaming over an existing deleted page replaces it.
        assert_equal(new_content, old_page.content)
        assert_equal(new_content, new_page.content)
        assert_equal(self.project.logs[-1].action, NodeLog.WIKI_RENAMED)

    def test_rename_page_conflict(self):
        existing_name = 'existing page'
        new_name = 'new page'
        self.project.update_node_wiki(existing_name, 'old content', self.auth)
        assert_in(existing_name, self.project.wiki_pages_current)
        self.project.update_node_wiki(new_name, 'new content', self.auth)
        assert_in(new_name, self.project.wiki_pages_current)
        with assert_raises(PageConflictError):
            self.project.rename_node_wiki(new_name, existing_name, self.auth)

    def test_rename_log(self):
        # Rename wiki
        self.project.update_node_wiki('wiki', 'content', self.auth)
        self.project.rename_node_wiki('wiki', 'renamed wiki', self.auth)
        # Rename is logged
        assert_equal(self.project.logs[-1].action, 'wiki_renamed')

    def test_rename_log_specifics(self):
        self.project.update_node_wiki('wiki', 'content', self.auth)
        self.project.rename_node_wiki('wiki', 'renamed wiki', self.auth)
        page = self.project.get_wiki_page('renamed wiki')
        log = self.project.logs[-1]
        assert_equal('wiki_renamed', log.action)
        assert_equal(page._primary_key, log.params['page_id'])


class TestDeleteNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestDeleteNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_delete_log(self):
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Deletion is logged
        assert_equal(self.project.logs[-1].action, 'wiki_deleted')

    def test_delete_log_specifics(self):
        page = self.project.get_wiki_page('home')
        self.project.delete_node_wiki('home', self.auth)
        log = self.project.logs[-1]
        assert_equal('wiki_deleted', log.action)
        assert_equal(page._primary_key, log.params['page_id'])

    def test_wiki_versions(self):
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 1)
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Number of versions is still correct
        assert_equal(len(self.versions['home']), 1)

    def test_wiki_delete(self):
        page = self.project.get_wiki_page('home')
        self.project.delete_node_wiki('home', self.auth)

        # page was deleted
        assert_false(self.project.get_wiki_page('home'))

        log = self.project.logs[-1]

        # deletion was logged
        assert_equal(
            NodeLog.WIKI_DELETED,
            log.action,
        )
        # log date is not set to the page's creation date
        assert_true(log.date > page.date)

    def test_deleted_versions(self):
        # Update wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        assert_equal(self.project.get_wiki_page('home', 2).content, 'Hola mundo')
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Check versions
        assert_equal(self.project.get_wiki_page('home',2).content, 'Hola mundo')
        assert_equal(self.project.get_wiki_page('home', 1).content, 'Hello world')


class TestNode(OsfTestCase):

    def setUp(self):
        super(TestNode, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.parent = ProjectFactory(creator=self.user)
        self.node = NodeFactory(creator=self.user, parent=self.parent)

    def test_set_privacy_checks_admin_permissions(self):
        non_contrib = UserFactory()
        project = ProjectFactory(creator=self.user, is_public=False)
        # Non-contrib can't make project public
        with assert_raises(PermissionsError):
            project.set_privacy('public', Auth(non_contrib))

        project.set_privacy('public', Auth(project.creator))
        project.save()

        # Non-contrib can't make project private
        with assert_raises(PermissionsError):
            project.set_privacy('private', Auth(non_contrib))

    def test_set_privacy_pending_embargo(self):
        project = ProjectFactory(creator=self.user, is_public=False)
        with mock_archive(project, embargo=True, autocomplete=True) as registration:
            assert_true(registration.embargo.is_pending_approval)
            assert_true(registration.is_pending_embargo)
            with assert_raises(NodeStateError):
                registration.set_privacy('public', Auth(project.creator))

    def test_set_privacy_pending_registration(self):
        project = ProjectFactory(creator=self.user, is_public=False)
        with mock_archive(project, embargo=False, autocomplete=True) as registration:
            assert_true(registration.registration_approval.is_pending_approval)
            assert_true(registration.is_pending_registration)
            with assert_raises(NodeStateError):
                registration.set_privacy('public', Auth(project.creator))

    def test_get_aggregate_logs_queryset_doesnt_return_hidden_logs(self):
        n_orig_logs = len(self.parent.get_aggregate_logs_queryset(Auth(self.user)))

        log = self.parent.logs[-1]
        log.should_hide = True
        log.save()

        n_new_logs = len(self.parent.get_aggregate_logs_queryset(Auth(self.user)))
        # Hidden log is not returned
        assert_equal(n_new_logs, n_orig_logs - 1)

    def test_validate_categories(self):
        with assert_raises(ValidationError):
            Node(category='invalid').save()  # an invalid category

    def test_web_url_for(self):
        result = self.parent.web_url_for('view_project')
        assert_equal(
            result,
            web_url_for(
                'view_project',
                pid=self.parent._id,
            )
        )

        result2 = self.node.web_url_for('view_project')
        assert_equal(
            result2,
            web_url_for(
                'view_project',
                pid=self.node._primary_key
            )
        )

    def test_web_url_for_absolute(self):
        result = self.parent.web_url_for('view_project', _absolute=True)
        assert_in(settings.DOMAIN, result)

    def test_category_display(self):
        node = NodeFactory(category='hypothesis')
        assert_equal(node.category_display, 'Hypothesis')
        node2 = NodeFactory(category='methods and measures')
        assert_equal(node2.category_display, 'Methods and Measures')

    def test_api_url_for(self):
        result = self.parent.api_url_for('view_project')
        assert_equal(
            result,
            api_url_for(
                'view_project',
                pid=self.parent._id
            )
        )

        result2 = self.node.api_url_for('view_project')
        assert_equal(
            result2,
            api_url_for(
                'view_project',
                pid=self.node._id,
            )
        )

    def test_api_url_for_absolute(self):
        result = self.parent.api_url_for('view_project', _absolute=True)
        assert_in(settings.DOMAIN, result)

    def test_get_absolute_url(self):
        assert_equal(self.node.get_absolute_url(),
                     '{}v2/nodes/{}/'
                     .format(settings.API_DOMAIN, self.node._id)
                     )

    def test_node_factory(self):
        node = NodeFactory()
        assert_equal(node.category, 'hypothesis')
        assert_true(node.node__parent)
        assert_equal(node.logs[0].action, 'project_created')
        assert_equal(
            set(node.get_addon_names()),
            set([
                addon_config.short_name
                for addon_config in settings.ADDONS_AVAILABLE
                if 'node' in addon_config.added_default
            ])
        )
        for addon_config in settings.ADDONS_AVAILABLE:
            if 'node' in addon_config.added_default:
                assert_in(
                    addon_config.short_name,
                    node.get_addon_names()
                )
                assert_true(
                    len([
                        addon
                        for addon in node.addons
                        if addon.config.short_name == addon_config.short_name
                    ]),
                    1
                )

    def test_add_addon(self):
        addon_count = len(self.node.get_addon_names())
        addon_record_count = len(self.node.addons)
        added = self.node.add_addon('github', self.auth)
        assert_true(added)
        self.node.reload()
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count + 1
        )
        assert_equal(
            len(self.node.addons),
            addon_record_count + 1
        )
        assert_equal(
            self.node.logs[-1].action,
            NodeLog.ADDON_ADDED
        )

    def test_add_existing_addon(self):
        addon_count = len(self.node.get_addon_names())
        addon_record_count = len(self.node.addons)
        added = self.node.add_addon('osffiles', self.auth)
        assert_false(added)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count
        )
        assert_equal(
            len(self.node.addons),
            addon_record_count
        )

    def test_delete_addon(self):
        addon_count = len(self.node.get_addon_names())
        deleted = self.node.delete_addon('wiki', self.auth)
        assert_true(deleted)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count - 1
        )
        assert_equal(
            self.node.logs[-1].action,
            NodeLog.ADDON_REMOVED
        )

    @mock.patch('website.addons.github.model.GitHubNodeSettings.config')
    def test_delete_mandatory_addon(self, mock_config):
        mock_config.added_mandatory = ['node']
        self.node.add_addon('github', self.auth)
        with assert_raises(ValueError):
            self.node.delete_addon('github', self.auth)

    def test_delete_nonexistent_addon(self):
        addon_count = len(self.node.get_addon_names())
        deleted = self.node.delete_addon('github', self.auth)
        assert_false(deleted)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count
        )

    def test_url(self):
        assert_equal(
            self.node.url,
            '/{0}/'.format(self.node._primary_key)
        )

    def test_watch_url(self):
        url = self.node.watch_url
        assert_equal(url, '/api/v1/project/{0}/watch/'
                                .format(self.node._primary_key))

    def test_parent_id(self):
        assert_equal(self.node.parent_id, self.parent._id)

    def test_parent(self):
        assert_equal(self.node.parent_node, self.parent)

    def test_in_parent_nodes(self):
        assert_in(self.node, self.parent.nodes)

    def test_log(self):
        latest_log = self.node.logs[-1]
        assert_equal(latest_log.action, 'project_created')
        assert_equal(latest_log.params, {
            'node': self.node._primary_key,
            'parent_node': self.parent._primary_key,
        })
        assert_equal(latest_log.user, self.user)

    def test_add_pointer(self):
        node2 = NodeFactory(creator=self.user)
        pointer = self.node.add_pointer(node2, auth=self.auth)
        assert_equal(pointer, self.node.nodes[0])
        assert_equal(len(self.node.nodes), 1)
        assert_false(self.node.nodes[0].primary)
        assert_equal(self.node.nodes[0].node, node2)
        assert_equal(len(node2.get_points()), 1)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_CREATED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'parent_node': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_add_pointer_fails_for_registrations(self):
        node = ProjectFactory()
        registration = RegistrationFactory(creator=self.user)

        with assert_raises(NodeStateError):
            registration.add_pointer(node, auth=self.auth)

    def test_get_points_exclude_folders(self):
        user = UserFactory()
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in a organizer collection
        folder = CollectionFactory(creator=pointed_project.creator)
        folder.add_pointer(pointed_project, Auth(pointed_project.creator), save=True)

        assert_in(pointer_project, pointed_project.get_points(folders=False))
        assert_not_in(folder, pointed_project.get_points(folders=False))
        assert_in(folder, pointed_project.get_points(folders=True))

    def test_get_points_exclude_deleted(self):
        user = UserFactory()
        pointer_project = ProjectFactory(is_public=True, is_deleted=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        assert_not_in(pointer_project, pointed_project.get_points(deleted=False))
        assert_in(pointer_project, pointed_project.get_points(deleted=True))

    def test_add_pointer_already_present(self):
        node2 = NodeFactory(creator=self.user)
        self.node.add_pointer(node2, auth=self.auth)
        with assert_raises(ValueError):
            self.node.add_pointer(node2, auth=self.auth)

    def test_rm_pointer(self):
        node2 = NodeFactory(creator=self.user)
        pointer = self.node.add_pointer(node2, auth=self.auth)
        self.node.rm_pointer(pointer, auth=self.auth)
        assert_is(Pointer.load(pointer._id), None)
        assert_equal(len(self.node.nodes), 0)
        assert_equal(len(node2.get_points()), 0)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_REMOVED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'parent_node': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_rm_pointer_not_present(self):
        node2 = NodeFactory(creator=self.user)
        pointer = Pointer(node=node2)
        with assert_raises(ValueError):
            self.node.rm_pointer(pointer, auth=self.auth)

    def test_fork_pointer_not_present(self):
        pointer = PointerFactory()
        with assert_raises(ValueError):
            self.node.fork_pointer(pointer, auth=self.auth)

    def test_cannot_fork_deleted_node(self):
        self.node.is_deleted = True
        self.node.save()
        fork = self.parent.fork_node(auth=self.auth)
        assert_false(fork.nodes)

    def _fork_pointer(self, content):
        pointer = self.node.add_pointer(content, auth=self.auth)
        forked = self.node.fork_pointer(pointer, auth=self.auth)
        assert_true(forked.is_fork)
        assert_equal(forked.forked_from, content)
        assert_true(self.node.nodes[-1].primary)
        assert_equal(self.node.nodes[-1], forked)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_FORKED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'parent_node': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_fork_pointer_project(self):
        project = ProjectFactory(creator=self.user)
        self._fork_pointer(project)

    def test_fork_pointer_component(self):
        component = NodeFactory(creator=self.user)
        self._fork_pointer(component)

    def test_add_file(self):
        #todo Add file series of tests
        pass

    def test_not_a_folder(self):
        assert_equal(self.node.is_collection, False)

    def test_not_a_bookmark_collection(self):
        assert_equal(self.node.is_bookmark_collection, False)

    def test_cannot_link_to_folder_more_than_once(self):
        folder = CollectionFactory(creator=self.user)
        node_two = ProjectFactory(creator=self.user)
        self.node.add_pointer(folder, auth=self.auth)
        with assert_raises(ValueError):
            node_two.add_pointer(folder, auth=self.auth)

    def test_cannot_register_deleted_node(self):
        self.node.is_deleted = True
        self.node.save()
        with assert_raises(NodeStateError) as err:
            self.node.register_node(
                schema=None,
                auth=self.auth,
                data=None
            )
        assert_equal(err.exception.message, 'Cannot register deleted node.')

    def test_set_visible_contributor_with_only_one_contributor(self):
        with assert_raises(ValueError) as e:
            self.node.set_visible(user=self.user, visible=False, auth=None)
            assert_equal(e.exception.message, 'Must have at least one visible contributor')

    def test_update_contributor(self):
        new_contrib = AuthUserFactory()
        self.node.add_contributor(new_contrib, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS, auth=self.auth)

        assert_equal(self.node.get_permissions(new_contrib), DEFAULT_CONTRIBUTOR_PERMISSIONS)
        assert_true(self.node.get_visible(new_contrib))

        self.node.update_contributor(
            new_contrib,
            READ,
            False,
            auth=self.auth
        )
        assert_equal(self.node.get_permissions(new_contrib), [READ])
        assert_false(self.node.get_visible(new_contrib))

    def test_update_contributor_non_admin_raises_error(self):
        non_admin = AuthUserFactory()
        self.node.add_contributor(
            non_admin,
            permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS,
            auth=self.auth
        )
        with assert_raises(PermissionsError):
            self.node.update_contributor(
                non_admin,
                None,
                False,
                auth=Auth(non_admin)
            )

    def test_update_contributor_only_admin_raises_error(self):
        with assert_raises(NodeStateError):
            self.node.update_contributor(
                self.user,
                WRITE,
                True,
                auth=self.auth
            )

    def test_update_contributor_non_contrib_raises_error(self):
        non_contrib = AuthUserFactory()
        with assert_raises(ValueError):
            self.node.update_contributor(
                non_contrib,
                ADMIN,
                True,
                auth=self.auth
            )

    def test_contributor_manage_visibility(self):

        reg_user1 = UserFactory()
        #This makes sure manage_contributors uses set_visible so visibility for contributors is added before visibility
        #for other contributors is removed ensuring there is always at least one visible contributor
        self.node.add_contributor(contributor=self.user, permissions=['read', 'write', 'admin'], auth=self.auth)
        self.node.add_contributor(contributor=reg_user1, permissions=['read', 'write', 'admin'], auth=self.auth)

        self.node.manage_contributors(
            user_dicts=[
                {'id': self.user._id, 'permission': 'admin', 'visible': True},
                {'id': reg_user1._id, 'permission': 'admin', 'visible': False},
            ],
            auth=self.auth,
            save=True
        )
        self.node.manage_contributors(
            user_dicts=[
                {'id': self.user._id, 'permission': 'admin', 'visible': False},
                {'id': reg_user1._id, 'permission': 'admin', 'visible': True},
            ],
            auth=self.auth,
            save=True
        )

        assert_equal(len(self.node.visible_contributor_ids), 1)

    def test_contributor_set_visibility_validation(self):
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        self.node.add_contributors(
            [
                {'user': reg_user1, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': [
                    'read', 'write', 'admin'], 'visible': False},
            ]
        )
        print(self.node.visible_contributor_ids)
        with assert_raises(ValueError) as e:
            self.node.set_visible(user=reg_user1, visible=False, auth=None)
            self.node.set_visible(user=self.user, visible=False, auth=None)
            assert_equal(e.exception.message, 'Must have at least one visible contributor')

    def test_active_child_nodes(self):
        self.node.is_deleted = True
        self.node.save()
        self.node.reload()
        assert_false(self.parent.nodes_active)

    def test_register_node_makes_private_registration(self):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.is_public = True
        node.save()
        registration = node.register_node(get_default_metaschema(), Auth(user), '', None)
        assert_false(registration.is_public)

    def test_register_node_makes_private_child_registrations(self):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.is_public = True
        node.save()
        child = NodeFactory(parent=node)
        child.is_public = True
        child.save()
        childchild = NodeFactory(parent=child)
        childchild.is_public = True
        childchild.save()
        registration = node.register_node(get_default_metaschema(), Auth(user), '', None)
        for node in registration.node_and_primary_descendants():
            assert_false(node.is_public)

    @mock.patch('website.project.signals.after_create_registration')
    def test_register_node_propagates_schema_and_data_to_children(self, mock_signal):
        root = ProjectFactory(creator=self.user)
        c1 = ProjectFactory(creator=self.user, parent=root)
        ProjectFactory(creator=self.user, parent=c1)

        ensure_schemas()
        meta_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended Registration') &
            Q('schema_version', 'eq', 1)
        )
        data = {'some': 'data'}
        reg = root.register_node(
            schema=meta_schema,
            auth=self.auth,
            data=data,
        )
        r1 = reg.nodes[0]
        r1a = r1.nodes[0]
        for r in [reg, r1, r1a]:
            assert_equal(r.registered_meta[meta_schema._id], data)
            assert_equal(r.registered_schema[0], meta_schema)


class TestNodeUpdate(OsfTestCase):

    def setUp(self):
        super(TestNodeUpdate, self).setUp()
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user, category='project', is_public=False)

    def test_update_title(self):
        # Creator (admin) can update
        new_title = fake.catch_phrase()
        self.node.update({'title': new_title}, auth=Auth(self.user), save=True)
        assert_equal(self.node.title, new_title)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, NodeLog.EDITED_TITLE)

        # Write contrib can update
        new_title2 = fake.catch_phrase()
        write_contrib = UserFactory()
        self.node.add_contributor(write_contrib, auth=Auth(self.user), permissions=(READ, WRITE))
        self.node.save()
        self.node.update({'title': new_title2}, auth=Auth(write_contrib))
        assert_equal(self.node.title, new_title2)

    def test_update_description(self):
        new_title = fake.bs()

        self.node.update({'title': new_title}, auth=Auth(self.user))
        assert_equal(self.node.title, new_title)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, NodeLog.EDITED_TITLE)

    def test_update_title_and_category(self):
        new_title = fake.bs()

        new_category = 'data'

        self.node.update({'title': new_title, 'category': new_category}, auth=Auth(self.user), save=True)
        assert_equal(self.node.title, new_title)
        assert_equal(self.node.category, 'data')

        penultimate_log, last_log = self.node.logs[-2], self.node.logs[-1]
        assert_equal(penultimate_log.action, NodeLog.EDITED_TITLE)
        assert_equal(last_log.action, NodeLog.UPDATED_FIELDS)

    def test_update_is_public(self):
        self.node.update({'is_public': True}, auth=Auth(self.user), save=True)
        assert_true(self.node.is_public)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, NodeLog.MADE_PUBLIC)

        self.node.update({'is_public': False}, auth=Auth(self.user), save=True)
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, NodeLog.MADE_PRIVATE)

    def test_update_can_make_registration_public(self):
        reg = RegistrationFactory(is_public=False)
        reg.update({'is_public': True})

        assert_true(reg.is_public)
        last_log = reg.logs[-1]
        assert_equal(last_log.action, NodeLog.MADE_PUBLIC)

    def test_updating_title_twice_with_same_title(self):
        original_n_logs = len(self.node.logs)
        new_title = fake.bs()
        self.node.update({'title': new_title}, auth=Auth(self.user), save=True)
        assert_equal(len(self.node.logs), original_n_logs + 1)  # sanity check

        # Call update with same title
        self.node.update({'title': new_title}, auth=Auth(self.user), save=True)
        # A new log is not created
        assert_equal(len(self.node.logs), original_n_logs + 1)

    def test_updating_description_twice_with_same_content(self):
        original_n_logs = len(self.node.logs)
        new_desc = fake.bs()
        self.node.update({'description': new_desc}, auth=Auth(self.user), save=True)
        assert_equal(len(self.node.logs), original_n_logs + 1)  # sanity check

        # Call update with same description
        self.node.update({'description': new_desc}, auth=Auth(self.user), save=True)
        # A new log is not created
        assert_equal(len(self.node.logs), original_n_logs + 1)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4664
    def test_updating_category_twice_with_same_content_generates_one_log(self):
        self.node.category = 'project'
        self.node.save()
        original_n_logs = len(self.node.logs)
        new_category = 'data'

        self.node.update({'category': new_category}, auth=Auth(self.user), save=True)
        assert_equal(len(self.node.logs), original_n_logs + 1)  # sanity check
        assert_equal(self.node.category, new_category)

        # Call update with same category
        self.node.update({'category': new_category}, auth=Auth(self.user), save=True)

        # Only one new log is created
        assert_equal(len(self.node.logs), original_n_logs + 1)
        assert_equal(self.node.category, new_category)

    # TODO: test permissions, non-writable fields


class TestNodeTraversals(OsfTestCase):

    def setUp(self):
        super(TestNodeTraversals, self).setUp()
        self.viewer = AuthUserFactory()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.root = ProjectFactory(creator=self.user)

    def test_next_descendants(self):
        comp1 = ProjectFactory(creator=self.user, parent=self.root)
        comp1a = ProjectFactory(creator=self.user, parent=comp1)
        comp1a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        ProjectFactory(creator=self.user, parent=comp1)
        comp2 = ProjectFactory(creator=self.user, parent=self.root)
        comp2.add_contributor(self.viewer, auth=self.auth, permissions='read')
        comp2a = ProjectFactory(creator=self.user, parent=comp2)
        comp2a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        ProjectFactory(creator=self.user, parent=comp2)

        descendants = self.root.next_descendants(
            Auth(self.viewer),
            condition=lambda auth, node: node.is_contributor(auth.user)
        )
        assert_equal(len(descendants), 2)  # two immediate children
        assert_equal(len(descendants[0][1]), 1)  # only one visible child of comp1
        assert_equal(len(descendants[1][1]), 0)  # don't auto-include comp2's children

    def test_delete_registration_tree(self):
        proj = NodeFactory()
        NodeFactory(parent=proj)
        comp2 = NodeFactory(parent=proj)
        NodeFactory(parent=comp2)
        reg = RegistrationFactory(project=proj)
        reg_ids = [reg._id] + [r._id for r in reg.get_descendants_recursive()]
        reg.delete_registration_tree(save=True)
        assert_false(Node.find(Q('_id', 'in', reg_ids) & Q('is_deleted', 'eq', False)).count())

    def test_delete_registration_tree_deletes_backrefs(self):
        proj = NodeFactory()
        NodeFactory(parent=proj)
        comp2 = NodeFactory(parent=proj)
        NodeFactory(parent=comp2)
        reg = RegistrationFactory(project=proj)
        reg.delete_registration_tree(save=True)
        assert_false(proj.registrations_all)

    def test_get_active_contributors_recursive_with_duplicate_users(self):
        parent = ProjectFactory(creator=self.user)

        child = ProjectFactory(creator=self.viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=self.auth,
                              permissions=expand_permissions(WRITE))
        grandchild = ProjectFactory(creator=self.user, parent=child)

        contributors = list(parent.get_active_contributors_recursive())
        assert_equal(len(contributors), 4)
        user_ids = [user._id for user, node in contributors]

        assert_in(self.user._id, user_ids)
        assert_in(self.viewer._id, user_ids)
        assert_in(child_non_admin._id, user_ids)

        node_ids = [node._id for user, node in contributors]
        assert_in(parent._id, node_ids)
        assert_in(grandchild._id, node_ids)

    def test_get_active_contributors_recursive_with_no_duplicate_users(self):
        parent = ProjectFactory(creator=self.user)

        child = ProjectFactory(creator=self.viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=self.auth,
                              permissions=expand_permissions(WRITE))
        grandchild = ProjectFactory(creator=self.user, parent=child)  # noqa

        contributors = list(parent.get_active_contributors_recursive(unique_users=True))
        assert_equal(len(contributors), 3)
        user_ids = [user._id for user, node in contributors]

        assert_in(self.user._id, user_ids)
        assert_in(self.viewer._id, user_ids)
        assert_in(child_non_admin._id, user_ids)

        node_ids = [node._id for user, node in contributors]
        assert_in(parent._id, node_ids)

    def test_get_admin_contributors_recursive_with_duplicate_users(self):
        parent = ProjectFactory(creator=self.user)

        child = ProjectFactory(creator=self.viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=self.auth,
                              permissions=expand_permissions(WRITE))
        child.save()

        grandchild = ProjectFactory(creator=self.user, parent=child)  # noqa

        admins = list(parent.get_admin_contributors_recursive())
        assert_equal(len(admins), 3)
        admin_ids = [user._id for user, node in admins]
        assert_in(self.user._id, admin_ids)
        assert_in(self.viewer._id, admin_ids)

        node_ids = [node._id for user, node in admins]
        assert_in(parent._id, node_ids)

    def test_get_admin_contributors_recursive_no_duplicates(self):
        parent = ProjectFactory(creator=self.user)

        child = ProjectFactory(creator=self.viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=self.auth,
                              permissions=expand_permissions(WRITE))
        child.save()

        grandchild = ProjectFactory(creator=self.user, parent=child)  # noqa

        admins = list(parent.get_admin_contributors_recursive(unique_users=True))
        assert_equal(len(admins), 2)
        admin_ids = [user._id for user, node in admins]
        assert_in(self.user._id, admin_ids)
        assert_in(self.viewer._id, admin_ids)

    def test_get_descendants_recursive(self):
        comp1 = ProjectFactory(creator=self.user, parent=self.root)
        comp1a = ProjectFactory(creator=self.user, parent=comp1)
        comp1a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        comp1b = ProjectFactory(creator=self.user, parent=comp1)
        comp2 = ProjectFactory(creator=self.user, parent=self.root)
        comp2.add_contributor(self.viewer, auth=self.auth, permissions='read')
        comp2a = ProjectFactory(creator=self.user, parent=comp2)
        comp2a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        comp2b = ProjectFactory(creator=self.user, parent=comp2)

        descendants = self.root.get_descendants_recursive()
        ids = {d._id for d in descendants}
        assert_false({node._id for node in [comp1, comp1a, comp1b, comp2, comp2a, comp2b]}.difference(ids))

    def test_get_descendants_recursive_filtered(self):
        comp1 = ProjectFactory(creator=self.user, parent=self.root)
        comp1a = ProjectFactory(creator=self.user, parent=comp1)
        comp1a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        ProjectFactory(creator=self.user, parent=comp1)
        comp2 = ProjectFactory(creator=self.user, parent=self.root)
        comp2.add_contributor(self.viewer, auth=self.auth, permissions='read')
        comp2a = ProjectFactory(creator=self.user, parent=comp2)
        comp2a.add_contributor(self.viewer, auth=self.auth, permissions='read')
        ProjectFactory(creator=self.user, parent=comp2)

        descendants = self.root.get_descendants_recursive(
            lambda n: n.is_contributor(self.viewer)
        )
        ids = {d._id for d in descendants}
        nids = {node._id for node in [comp1a, comp2, comp2a]}
        assert_false(ids.difference(nids))

    def test_get_descendants_recursive_cyclic(self):
        point1 = ProjectFactory(creator=self.user, parent=self.root)
        point2 = ProjectFactory(creator=self.user, parent=self.root)
        point1.add_pointer(point2, auth=self.auth)
        point2.add_pointer(point1, auth=self.auth)

        descendants = list(point1.get_descendants_recursive())
        assert_equal(len(descendants), 1)

class TestRemoveNode(OsfTestCase):

    def setUp(self):
        super(TestRemoveNode, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.parent_project = ProjectFactory(creator=self.user)
        self.project = ProjectFactory(creator=self.user,
                                      parent=self.parent_project)

    def test_remove_project_without_children(self):
        self.project.remove_node(auth=self.auth)

        assert_true(self.project.is_deleted)
        # parent node should have a log of the event
        assert_equal(
            self.parent_project.get_aggregate_logs_queryset(self.auth)[0].action,
            'node_removed'
        )

    def test_delete_project_log_present(self):
        self.project.remove_node(auth=self.auth)
        self.parent_project.remove_node(auth=self.auth)

        assert_true(self.parent_project.is_deleted)
        # parent node should have a log of the event
        assert_equal(self.parent_project.logs[-1].action, 'project_deleted')

    def test_remove_project_with_project_child_fails(self):
        with assert_raises(NodeStateError):
            self.parent_project.remove_node(self.auth)

    def test_remove_project_with_component_child_fails(self):
        NodeFactory(creator=self.user, parent=self.project)

        with assert_raises(NodeStateError):
            self.parent_project.remove_node(self.auth)

    def test_remove_project_with_pointer_child(self):
        target = ProjectFactory(creator=self.user)
        self.project.add_pointer(node=target, auth=self.auth)

        assert_equal(len(self.project.nodes), 1)

        self.project.remove_node(auth=self.auth)

        assert_true(self.project.is_deleted)
        # parent node should have a log of the event
        assert_equal(self.parent_project.logs[-1].action, 'node_removed')

        # target node shouldn't be deleted
        assert_false(target.is_deleted)


class TestBookmarkCollection(OsfTestCase):

    def setUp(self):
        super(TestBookmarkCollection, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = BookmarkCollectionFactory(creator=self.user)

    def test_bookmark_collection_is_bookmark_collection(self):
        assert_equal(self.project.is_bookmark_collection, True)

    def test_bookmark_collection_is_collection(self):
        assert_equal(self.project.is_collection, True)

    def test_cannot_remove_bookmark_collection(self):
        with assert_raises(NodeStateError):
            self.project.remove_node(self.auth)

    def test_cannot_have_two_bookmark_collection(self):
        with assert_raises(NodeStateError):
            BookmarkCollectionFactory(creator=self.user)

    def test_cannot_link_to_bookmark_collection(self):
        new_node = ProjectFactory(creator=self.user)
        with assert_raises(ValueError):
            new_node.add_pointer(self.project, auth=self.auth)

    def test_can_remove_empty_folder(self):
        new_folder = CollectionFactory(creator=self.user)
        assert_equal(new_folder.is_collection, True)
        new_folder.remove_node(auth=self.auth)
        assert_true(new_folder.is_deleted)

    def test_can_remove_folder_structure(self):
        outer_folder = CollectionFactory(creator=self.user)
        assert_equal(outer_folder.is_collection, True)
        inner_folder = CollectionFactory(creator=self.user)
        assert_equal(inner_folder.is_collection, True)
        outer_folder.add_pointer(inner_folder, self.auth)
        outer_folder.remove_node(auth=self.auth)
        assert_true(outer_folder.is_deleted)
        assert_true(inner_folder.is_deleted)


class TestAddonCallbacks(OsfTestCase):
    """Verify that callback functions are called at the right times, with the
    right arguments.
    """
    callbacks = {
        'after_remove_contributor': None,
        'after_set_privacy': None,
        'after_fork': (None, None),
        'after_register': (None, None),
    }

    def setUp(self):
        super(TestAddonCallbacks, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.parent = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.parent)

        # Mock addon callbacks
        for addon in self.node.addons:
            mock_settings = mock.create_autospec(addon.__class__)
            for callback, return_value in self.callbacks.iteritems():
                mock_callback = getattr(mock_settings, callback)
                mock_callback.return_value = return_value
                setattr(
                    addon,
                    callback,
                    getattr(mock_settings, callback)
                )

    def test_remove_contributor_callback(self):

        user2 = UserFactory()
        self.node.add_contributor(contributor=user2, auth=self.auth)
        self.node.remove_contributor(contributor=user2, auth=self.auth)
        for addon in self.node.addons:
            callback = addon.after_remove_contributor
            callback.assert_called_once_with(
                self.node, user2, self.auth
            )

    def test_set_privacy_callback(self):

        self.node.set_privacy('public', self.auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'public',
            )

        self.node.set_privacy('private', self.auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'private'
            )

    def test_fork_callback(self):
        fork = self.node.fork_node(auth=self.auth)
        for addon in self.node.addons:
            callback = addon.after_fork
            callback.assert_called_once_with(
                self.node, fork, self.user
            )

    def test_register_callback(self):
        with mock_archive(self.node) as registration:
            for addon in self.node.addons:
                callback = addon.after_register
                callback.assert_called_once_with(
                    self.node, registration, self.user
                )


class TestProject(OsfTestCase):

    def setUp(self):
        super(TestProject, self).setUp()
        # Create project
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user, description='foobar')

    def test_repr(self):
        assert_in(self.project.title, repr(self.project))
        assert_in(self.project._id, repr(self.project))

    def test_project_factory(self):
        node = ProjectFactory()
        assert_equal(node.category, 'project')
        assert_true(node._id)
        assert_almost_equal(
            node.date_created, datetime.datetime.utcnow(),
            delta=datetime.timedelta(seconds=5),
        )
        assert_false(node.is_public)
        assert_false(node.is_deleted)
        assert_true(hasattr(node, 'deleted_date'))
        assert_false(node.is_registration)
        assert_true(hasattr(node, 'registered_date'))
        assert_false(node.is_fork)
        assert_true(hasattr(node, 'forked_date'))
        assert_true(node.title)
        assert_true(hasattr(node, 'description'))
        assert_true(hasattr(node, 'registered_meta'))
        assert_true(hasattr(node, 'registered_user'))
        assert_true(hasattr(node, 'registered_schema'))
        assert_true(node.creator)
        assert_true(node.contributors)
        assert_equal(len(node.logs), 1)
        assert_true(hasattr(node, 'tags'))
        assert_true(hasattr(node, 'nodes'))
        assert_true(hasattr(node, 'forked_from'))
        assert_true(hasattr(node, 'registered_from'))
        assert_equal(node.logs[-1].action, 'project_created')

    def test_log(self):
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, 'project_created')
        assert_equal(latest_log.params['node'], self.project._primary_key)
        assert_equal(latest_log.user, self.user)

    def test_url(self):
        assert_equal(
            self.project.url,
            '/{0}/'.format(self.project._primary_key)
        )

    def test_api_url(self):
        api_url = self.project.api_url
        assert_equal(api_url, '/api/v1/project/{0}/'.format(self.project._primary_key))

    def test_watch_url(self):
        watch_url = self.project.watch_url
        assert_equal(
            watch_url,
            '/api/v1/project/{0}/watch/'.format(self.project._primary_key)
        )

    def test_parent_id(self):
        assert_false(self.project.parent_id)

    def test_watching(self):
        # A user watched a node
        user = UserFactory()
        config1 = WatchConfigFactory(node=self.project)
        user.watched.append(config1)
        user.save()
        assert_in(config1._id, [e._id for e in self.project.watches])

    def test_add_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, auth=self.auth)
        self.project.save()
        assert_in(user2, self.project.contributors)
        assert_equal(self.project.logs[-1].action, 'contributor_added')

    def test_add_contributor_sends_contributor_added_signal(self):
        user = UserFactory()
        contributors = [{
            'user': user,
            'visible': True,
            'permissions': ['read', 'write']
        }]
        with capture_signals() as mock_signals:
            self.project.add_contributors(contributors=contributors, auth=self.auth)
            self.project.save()
            assert_in(user, self.project.contributors)
            assert_equal(mock_signals.signals_sent(), set([contributor_added]))

    def test_add_unregistered_contributor(self):
        self.project.add_unregistered_contributor(
            email='foo@bar.com',
            fullname='Weezy F. Baby',
            auth=self.auth
        )
        self.project.save()
        latest_contributor = self.project.contributors[-1]
        assert_true(isinstance(latest_contributor, User))
        assert_equal(latest_contributor.username, 'foo@bar.com')
        assert_equal(latest_contributor.fullname, 'Weezy F. Baby')
        assert_false(latest_contributor.is_registered)

        # A log event was added
        assert_equal(self.project.logs[-1].action, 'contributor_added')
        assert_in(self.project._primary_key, latest_contributor.unclaimed_records,
            'unclaimed record was added')
        unclaimed_data = latest_contributor.get_unclaimed_record(self.project._primary_key)
        assert_equal(unclaimed_data['referrer_id'],
            self.auth.user._primary_key)
        assert_true(self.project.is_contributor(latest_contributor))
        assert_equal(unclaimed_data['email'], 'foo@bar.com')

    def test_add_unregistered_adds_new_unclaimed_record_if_user_already_in_db(self):
        user = UnregUserFactory()
        given_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=user.username,
            fullname=given_name,
            auth=self.auth
        )
        self.project.save()
        # new unclaimed record was added
        assert_in(self.project._primary_key, new_user.unclaimed_records)
        unclaimed_data = new_user.get_unclaimed_record(self.project._primary_key)
        assert_equal(unclaimed_data['name'], given_name)

    def test_add_unregistered_raises_error_if_user_is_registered(self):
        user = UserFactory(is_registered=True)  # A registered user
        with assert_raises(ValidationValueError):
            self.project.add_unregistered_contributor(
                email=user.username,
                fullname=user.fullname,
                auth=self.auth
            )

    def test_remove_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, auth=self.auth)
        self.project.save()
        # The user is removed
        self.project.remove_contributor(
            auth=self.auth,
            contributor=user2
        )

        self.project.reload()

        assert_not_in(user2, self.project.contributors)
        assert_not_in(user2._id, self.project.permissions)
        assert_equal(self.project.logs[-1].action, 'contributor_removed')
        assert_equal(self.project.logs[-1].params['contributors'], [user2._id])

    def test_manage_contributors_cannot_remove_last_admin_contributor(self):
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, permissions=['read', 'write'], auth=self.auth)
        self.project.save()
        with assert_raises(ValueError):
            self.project.manage_contributors(
                user_dicts=[{'id': user2._id,
                             'permission': 'write',
                             'visible': True}],
                auth=self.auth,
                save=True
            )

    def test_manage_contributors_logs_when_users_reorder(self):
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, permissions=['read', 'write'], auth=self.auth)
        self.project.save()
        self.project.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permission': 'write',
                    'visible': True,
                },
                {
                    'id': self.user._id,
                    'permission': 'admin',
                    'visible': True,
                },
            ],
            auth=self.auth,
            save=True
        )
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, NodeLog.CONTRIB_REORDERED)
        assert_equal(latest_log.user, self.user)
        assert_in(self.user._id, latest_log.params['contributors'])
        assert_in(user2._id, latest_log.params['contributors'])

    def test_add_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        assert_in(link._id, [e._id for e in self.project.private_links])

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_has_anonymous_link(self, mock_property):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = True

        link1 = PrivateLinkFactory(key="link1")
        link1.nodes.append(self.project)
        link1.save()

        user2 = UserFactory()
        auth2 = Auth(user=user2, private_key="link1")

        assert_true(has_anonymous_link(self.project, auth2))

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_has_no_anonymous_link(self, mock_property):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = False

        link2 = PrivateLinkFactory(key="link2")
        link2.nodes.append(self.project)
        link2.save()

        user3 = UserFactory()
        auth3 = Auth(user=user3, private_key="link2")

        assert_false(has_anonymous_link(self.project, auth3))

    def test_remove_unregistered_conributor_removes_unclaimed_record(self):
        new_user = self.project.add_unregistered_contributor(fullname=fake.name(),
            email=fake.email(), auth=Auth(self.project.creator))
        self.project.save()
        assert_true(self.project.is_contributor(new_user))  # sanity check
        assert_in(self.project._primary_key, new_user.unclaimed_records)
        self.project.remove_contributor(
            auth=self.auth,
            contributor=new_user
        )
        self.project.save()
        assert_not_in(self.project._primary_key, new_user.unclaimed_records)

    def test_manage_contributors_new_contributor(self):
        user = UserFactory()
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.auth, save=True
            )

    def test_manage_contributors_no_contributors(self):
        with assert_raises(ValueError):
            self.project.manage_contributors(
                [], auth=self.auth, save=True,
            )

    def test_manage_contributors_no_admins(self):
        user = UserFactory()
        self.project.add_contributor(
            user,
            permissions=['read', 'write', 'admin'],
            save=True
        )
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.auth, save=True,
            )

    def test_manage_contributors_no_registered_admins(self):
        unregistered = UnregUserFactory()
        self.project.add_contributor(
            unregistered,
            permissions=['read', 'write', 'admin'],
            save=True
        )
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': unregistered._id, 'permission': 'admin', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.auth, save=True,
            )

    def test_set_title_works_with_valid_title(self):
        proj = ProjectFactory(title='That Was Then', creator=self.user)
        proj.set_title('This is now', auth=self.auth)
        proj.save()
        # Title was changed
        assert_equal(proj.title, 'This is now')
        # A log event was saved
        latest_log = proj.logs[-1]
        assert_equal(latest_log.action, 'edit_title')
        assert_equal(latest_log.params['title_original'], 'That Was Then')

    def test_set_title_fails_if_empty_or_whitespace(self):
        proj = ProjectFactory(title='That Was Then', creator=self.user)
        with assert_raises(ValidationValueError):
            proj.set_title(' ', auth=self.auth)
        with assert_raises(ValidationValueError):
            proj.set_title('', auth=self.auth)
        #assert_equal(proj.title, 'That Was Then')

    def test_set_title_fails_if_too_long(self):
        proj = ProjectFactory(title='That Was Then', creator=self.user)
        long_title = ''.join(random.choice(string.ascii_letters + string.digits)
                             for _ in range(201))
        with assert_raises(ValidationValueError):
            proj.set_title(long_title, auth=self.auth)

    def test_title_cant_be_empty(self):
        with assert_raises(ValidationValueError):
            proj = ProjectFactory(title='', creator=self.user)
        with assert_raises(ValidationValueError):
            proj = ProjectFactory(title=' ', creator=self.user)

    def test_title_cant_be_too_long(self):
        long_title = ''.join(random.choice(string.ascii_letters + string.digits)
                             for _ in range(201))
        with assert_raises(ValidationValueError):
            proj = ProjectFactory(title=long_title, creator=self.user)

    def test_contributor_can_edit(self):
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.auth)
        self.project.save()
        assert_true(self.project.can_edit(contributor_auth))
        assert_false(self.project.can_edit(other_guy_auth))

    def test_can_edit_can_be_passed_a_user(self):
        assert_true(self.project.can_edit(user=self.user))

    def test_creator_can_edit(self):
        assert_true(self.project.can_edit(self.auth))

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        user1_auth = Auth(user=user1)
        # Change project to public
        self.project.set_privacy('public')
        self.project.save()
        # Noncontributor can't edit
        assert_false(self.project.can_edit(user1_auth))

    def test_can_view_private(self):
        # Create contributor and noncontributor
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.auth)
        self.project.save()
        # Only creator and contributor can view
        assert_true(self.project.can_view(self.auth))
        assert_true(self.project.can_view(contributor_auth))
        assert_false(self.project.can_view(other_guy_auth))
        other_guy_auth.private_key = link.key
        assert_true(self.project.can_view(other_guy_auth))

    def test_is_admin_parent_target_admin(self):
        assert_true(self.project.is_admin_parent(self.project.creator))

    def test_is_admin_parent_parent_admin(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        assert_true(node.is_admin_parent(self.project.creator))

    def test_is_admin_parent_grandparent_admin(self):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=self.project,
            category='project',
            creator=user
        )
        child_node = NodeFactory(parent=parent_node, creator=user)
        assert_true(child_node.is_admin_parent(self.project.creator))
        assert_true(parent_node.is_admin_parent(self.project.creator))

    def test_is_admin_parent_parent_write(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        self.project.set_permissions(self.project.creator, ['read', 'write'])
        assert_false(node.is_admin_parent(self.project.creator))

    def test_has_permission_read_parent_admin(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        assert_true(node.has_permission(self.project.creator, 'read'))
        assert_false(node.has_permission(self.project.creator, 'admin'))

    def test_has_permission_read_grandparent_admin(self):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=self.project,
            category='project',
            creator=user
        )
        child_node = NodeFactory(
            parent=parent_node,
            creator=user
        )
        assert_true(child_node.has_permission(self.project.creator, 'read'))
        assert_false(child_node.has_permission(self.project.creator, 'admin'))
        assert_true(parent_node.has_permission(self.project.creator, 'read'))
        assert_false(parent_node.has_permission(self.project.creator, 'admin'))

    def test_can_view_parent_admin(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        assert_true(node.can_view(Auth(user=self.project.creator)))
        assert_false(node.can_edit(Auth(user=self.project.creator)))

    def test_can_view_grandparent_admin(self):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=self.project,
            creator=user,
            category='project'
        )
        child_node = NodeFactory(
            parent=parent_node,
            creator=user
        )
        assert_true(parent_node.can_view(Auth(user=self.project.creator)))
        assert_false(parent_node.can_edit(Auth(user=self.project.creator)))
        assert_true(child_node.can_view(Auth(user=self.project.creator)))
        assert_false(child_node.can_edit(Auth(user=self.project.creator)))

    def test_can_view_parent_write(self):
        user = UserFactory()
        node = NodeFactory(parent=self.project, creator=user)
        self.project.set_permissions(self.project.creator, ['read', 'write'])
        assert_false(node.can_view(Auth(user=self.project.creator)))
        assert_false(node.can_edit(Auth(user=self.project.creator)))

    def test_creator_cannot_edit_project_if_they_are_removed(self):
        creator = UserFactory()
        project = ProjectFactory(creator=creator)
        contrib = UserFactory()
        project.add_contributor(contrib, permissions=['read', 'write', 'admin'], auth=Auth(user=creator))
        project.save()
        assert_in(creator, project.contributors)
        # Creator is removed from project
        project.remove_contributor(creator, auth=Auth(user=contrib))
        assert_false(project.can_view(Auth(user=creator)))
        assert_false(project.can_edit(Auth(user=creator)))
        assert_false(project.is_contributor(creator))

    def test_can_view_public(self):
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.auth)
        # Change project to public
        self.project.set_privacy('public')
        self.project.save()
        # Creator, contributor, and noncontributor can view
        assert_true(self.project.can_view(self.auth))
        assert_true(self.project.can_view(contributor_auth))
        assert_true(self.project.can_view(other_guy_auth))

    def test_parents(self):
        child1 = ProjectFactory(parent=self.project)
        child2 = ProjectFactory(parent=child1)
        assert_equal(self.project.parents, [])
        assert_equal(child1.parents, [self.project])
        assert_equal(child2.parents, [child1, self.project])

    def test_admin_contributor_ids(self):
        assert_equal(self.project.admin_contributor_ids, set())
        child1 = ProjectFactory(parent=self.project)
        child2 = ProjectFactory(parent=child1)
        assert_equal(child1.admin_contributor_ids, {self.project.creator._id})
        assert_equal(child2.admin_contributor_ids, {self.project.creator._id, child1.creator._id})
        self.project.set_permissions(self.project.creator, ['read', 'write'])
        self.project.save()
        assert_equal(child1.admin_contributor_ids, set())
        assert_equal(child2.admin_contributor_ids, {child1.creator._id})

    def test_admin_contributors(self):
        assert_equal(self.project.admin_contributors, [])
        child1 = ProjectFactory(parent=self.project)
        child2 = ProjectFactory(parent=child1)
        assert_equal(child1.admin_contributors, [self.project.creator])
        assert_equal(
            child2.admin_contributors,
            sorted([self.project.creator, child1.creator], key=lambda user: user.family_name)
        )
        self.project.set_permissions(self.project.creator, ['read', 'write'])
        self.project.save()
        assert_equal(child1.admin_contributors, [])
        assert_equal(child2.admin_contributors, [child1.creator])

    def test_is_contributor(self):
        contributor = UserFactory()
        other_guy = UserFactory()
        self.project.add_contributor(
            contributor=contributor, auth=self.auth)
        self.project.save()
        assert_true(self.project.is_contributor(contributor))
        assert_false(self.project.is_contributor(other_guy))
        assert_false(self.project.is_contributor(None))

    def test_is_fork_of(self):
        project = ProjectFactory()
        fork1 = project.fork_node(auth=Auth(user=project.creator))
        fork2 = fork1.fork_node(auth=Auth(user=project.creator))
        assert_true(fork1.is_fork_of(project))
        assert_true(fork2.is_fork_of(project))

    def test_is_fork_of_false(self):
        project = ProjectFactory()
        to_fork = ProjectFactory()
        fork = to_fork.fork_node(auth=Auth(user=to_fork.creator))
        assert_false(fork.is_fork_of(project))

    def test_is_fork_of_no_forked_from(self):
        project = ProjectFactory()
        assert_false(project.is_fork_of(self.project))

    def test_is_registration_of(self):
        project = ProjectFactory()
        with mock_archive(project) as reg1:
            with mock_archive(reg1) as reg2:
                assert_true(reg1.is_registration_of(project))
                assert_true(reg2.is_registration_of(project))

    def test_is_registration_of_false(self):
        project = ProjectFactory()
        to_reg = ProjectFactory()
        with mock_archive(to_reg) as reg:
            assert_false(reg.is_registration_of(project))

    def test_raises_permissions_error_if_not_a_contributor(self):
        project = ProjectFactory()
        user = UserFactory()
        with assert_raises(PermissionsError):
            project.register_node(None, Auth(user=user), '', None)

    def test_admin_can_register_private_children(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        project.set_permissions(user, ['admin', 'write', 'read'])
        child = NodeFactory(parent=project, is_public=False)
        assert_false(child.can_edit(auth=Auth(user=user)))  # sanity check
        with mock_archive(project, None, Auth(user=user), '', None) as registration:
            # child was registered
            child_registration = registration.nodes[0]
            assert_equal(child_registration.registered_from, child)

    def test_is_registration_of_no_registered_from(self):
        project = ProjectFactory()
        assert_false(project.is_registration_of(self.project))

    def test_registration_preserves_license(self):
        license = NodeLicenseRecordFactory()
        self.project.node_license = license
        self.project.save()
        with mock_archive(self.project, autocomplete=True) as registration:
            assert_equal(registration.node_license.id, license.id)

    def test_is_contributor_unregistered(self):
        unreg = UnregUserFactory()
        self.project.add_unregistered_contributor(
            fullname=fake.name(),
            email=unreg.username,
            auth=self.auth
        )
        self.project.save()
        assert_true(self.project.is_contributor(unreg))

    def test_creator_is_contributor(self):
        assert_true(self.project.is_contributor(self.user))
        assert_in(self.user, self.project.contributors)

    def test_cant_add_creator_as_contributor_twice(self):
        self.project.add_contributor(contributor=self.user)
        self.project.save()
        assert_equal(len(self.project.contributors), 1)

    def test_cant_add_same_contributor_twice(self):
        contrib = UserFactory()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        assert_equal(len(self.project.contributors), 2)

    def test_add_contributors(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.project.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write', 'admin'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': False}
            ],
            auth=self.auth
        )
        self.project.save()
        assert_equal(len(self.project.contributors), 3)
        assert_equal(
            self.project.logs[-1].params['contributors'],
            [user1._id, user2._id]
        )
        assert_in(user1._id, self.project.permissions)
        assert_in(user2._id, self.project.permissions)
        assert_in(user1._id, self.project.visible_contributor_ids)
        assert_not_in(user2._id, self.project.visible_contributor_ids)
        assert_equal(self.project.permissions[user1._id], ['read', 'write', 'admin'])
        assert_equal(self.project.permissions[user2._id], ['read', 'write'])
        assert_equal(
            self.project.logs[-1].params['contributors'],
            [user1._id, user2._id]
        )

    def test_set_privacy(self):
        self.project.set_privacy('public', auth=self.auth)
        self.project.save()
        assert_true(self.project.is_public)
        assert_equal(self.project.logs[-1].action, 'made_public')
        self.project.set_privacy('private', auth=self.auth)
        self.project.save()
        assert_false(self.project.is_public)
        assert_equal(self.project.logs[-1].action, NodeLog.MADE_PRIVATE)

    @mock.patch('website.project.model.mails.queue_mail')
    def test_set_privacy_sends_mail_default(self, mock_queue):
        self.project.set_privacy('private', auth=self.auth)
        self.project.set_privacy('public', auth=self.auth)
        assert_true(mock_queue.called_once())

    @mock.patch('website.project.model.mails.queue_mail')
    def test_set_privacy_sends_mail(self, mock_queue):
        self.project.set_privacy('private', auth=self.auth)
        self.project.set_privacy('public', auth=self.auth, meeting_creation=False)
        assert_true(mock_queue.called_once())

    @mock.patch('website.project.model.mails.queue_mail')
    def test_set_privacy_skips_mail(self, mock_queue):
        self.project.set_privacy('private', auth=self.auth)
        self.project.set_privacy('public', auth=self.auth, meeting_creation=True)
        assert_false(mock_queue.called)

    def test_set_privacy_can_not_cancel_pending_embargo_for_registration(self):
        registration = RegistrationFactory(project=self.project)
        registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        assert_true(registration.is_pending_embargo)

        with assert_raises(NodeStateError):
            registration.set_privacy('public', auth=self.auth)
        assert_false(registration.is_public)

    def test_set_privacy_can_not_cancel_active_embargo_for_registration(self):
        registration = RegistrationFactory(project=self.project)
        registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        registration.save()
        assert_true(registration.is_pending_embargo)

        approval_token = registration.embargo.approval_state[self.user._id]['approval_token']
        registration.embargo.approve_embargo(self.user, approval_token)
        assert_false(registration.is_pending_embargo)

        with assert_raises(NodeStateError):
            registration.set_privacy('public', auth=self.auth)

    def test_set_description(self):
        old_desc = self.project.description
        self.project.set_description(
            'new description', auth=self.auth)
        self.project.save()
        assert_equal(self.project.description, 'new description')
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, NodeLog.EDITED_DESCRIPTION)
        assert_equal(latest_log.params['description_original'], old_desc)
        assert_equal(latest_log.params['description_new'], 'new description')

    def test_set_description_on_node(self):
        node = NodeFactory(project=self.project)

        old_desc = node.description
        node.set_description(
            'new description', auth=self.auth)
        node.save()
        assert_equal(node.description, 'new description')
        latest_log = node.logs[-1]
        assert_equal(latest_log.action, NodeLog.EDITED_DESCRIPTION)
        assert_equal(latest_log.params['description_original'], old_desc)
        assert_equal(latest_log.params['description_new'], 'new description')

    def test_no_parent(self):
        assert_equal(self.project.parent_node, None)

    def test_get_recent_logs(self):
        # Add some logs
        for _ in range(5):
            self.project.add_log('file_added', params={'node': self.project._id}, auth=self.auth)

        # Expected logs appears
        assert_equal(
            self.project.get_recent_logs(3),
            list(reversed(self.project.logs))[:3]
        )

        assert_equal(
            self.project.get_recent_logs(),
            list(reversed(self.project.logs))
        )

    def test_date_modified(self):
        contrib = UserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()

        assert_equal(self.project.date_modified, self.project.logs[-1].date)
        assert_not_equal(self.project.date_modified, self.project.date_created)

    def test_date_modified_create_registration(self):
        registration = RegistrationFactory(project=self.project)
        self.project.save()

        assert_equal(self.project.date_modified, self.project.logs[-1].date)
        assert_not_equal(self.project.date_modified, self.project.date_created)

    def test_date_modified_create_component(self):
        self.component = NodeFactory(creator=self.user, parent=self.project)
        self.project.save()

        assert_equal(self.project.date_modified, self.project.date_created)

    def test_replace_contributor(self):
        contrib = UserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        assert_in(contrib, self.project.contributors)  # sanity check
        replacer = UserFactory()
        old_length = len(self.project.contributors)
        self.project.replace_contributor(contrib, replacer)
        self.project.save()
        new_length = len(self.project.contributors)
        assert_not_in(contrib, self.project.contributors)
        assert_in(replacer, self.project.contributors)
        assert_equal(old_length, new_length)

        # test unclaimed_records is removed
        assert_not_in(
            self.project._primary_key,
            contrib.unclaimed_records.keys()
        )

    def test_permission_override_on_readded_contributor(self):

        # A child node created
        self.child_node = NodeFactory(parent=self.project, creator=self.auth)

        # A user is added as with read permission
        user = UserFactory()
        self.child_node.add_contributor(user, permissions=['read'])

        # user is readded with permission admin
        self.child_node.add_contributor(user, permissions=['read','write','admin'])
        self.child_node.save()

        assert(self.child_node.has_permission(user, 'admin'))


class TestParentNode(OsfTestCase):
    def setUp(self):
        super(TestParentNode, self).setUp()
        # Create project
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user, description='The Dudleys strike again')
        self.child = NodeFactory(parent=self.project, creator=self.user, description="Devon.")

        self.registration = RegistrationFactory(project=self.project)
        self.template = self.project.use_as_template(auth=self.auth)

    def test_top_level_project_has_no_parent(self):
        assert_equal(self.project.parent_node, None)

    def test_child_project_has_correct_parent(self):
        assert_equal(self.child.parent_node._id, self.project._id)

    def test_grandchild_has_parent_of_child(self):
        grandchild = NodeFactory(parent=self.child, description="Spike")
        assert_equal(grandchild.parent_node._id, self.child._id)

    def test_registration_has_no_parent(self):
        assert_equal(self.registration.parent_node, None)

    def test_registration_child_has_correct_parent(self):
        registration_child = NodeFactory(parent=self.registration)
        assert_equal(self.registration._id, registration_child.parent_node._id)

    def test_registration_grandchild_has_correct_parent(self):
        registration_child = NodeFactory(parent=self.registration)
        registration_grandchild = NodeFactory(parent=registration_child)
        assert_equal(registration_grandchild.parent_node._id, registration_child._id)

    def test_fork_has_no_parent(self):
        fork = self.project.fork_node(auth=self.auth)
        assert_equal(fork.parent_node, None)

    def test_fork_child_has_parent(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        assert_equal(fork_child.parent_node._id, fork._id)

    def test_fork_grandchild_has_child_id(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        fork_grandchild = NodeFactory(parent=fork_child)
        assert_equal(fork_grandchild.parent_node._id, fork_child._id)

    def test_template_has_no_parent(self):
        new_project = self.project.use_as_template(auth=self.auth)
        assert_equal(new_project.parent_node, None)

    def test_teplate_project_child_has_correct_parent(self):
        template_child = NodeFactory(parent=self.template)
        assert_equal(template_child.parent_node._id, self.template._id)

    def test_template_project_grandchild_has_correct_root(self):
        template_child = NodeFactory(parent=self.template)
        new_project_grandchild = NodeFactory(parent=template_child)
        assert_equal(new_project_grandchild.parent_node._id, template_child._id)


class TestRoot(OsfTestCase):
    def setUp(self):
        super(TestRoot, self).setUp()
        # Create project
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user, description='foobar')

        self.registration = RegistrationFactory(project=self.project)

    def test_top_level_project_has_own_root(self):
        assert(self.project.root._id, self.project._id)

    def test_child_project_has_root_of_parent(self):
        child = NodeFactory(parent=self.project)
        assert_equal(child.root._id, self.project._id)
        assert_equal(child.root._id, self.project.root._id)

    def test_grandchild_root_relationships(self):
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        grandchild_from_one = NodeFactory(parent=child_node_one)
        grandchild_from_two = NodeFactory(parent=child_node_two)

        assert_equal(child_node_one.root._id, child_node_two.root._id)
        assert_equal(grandchild_from_one.root._id, grandchild_from_two.root._id)
        assert_equal(grandchild_from_two.root._id, self.project.root._id)

    def test_grandchild_has_root_of_immediate_parent(self):
        child_node = NodeFactory(parent=self.project)
        grandchild_node = NodeFactory(parent=child_node)
        assert_equal(child_node.root._id, grandchild_node.root._id)

    def test_registration_has_own_root(self):
        assert_equal(self.registration.root._id, self.registration._id)

    def test_registration_children_have_correct_root(self):
        registration_child = NodeFactory(parent=self.registration)
        assert_equal(registration_child.root._id, self.registration._id)

    def test_registration_grandchildren_have_correct_root(self):
        registration_child = NodeFactory(parent=self.registration)
        registration_grandchild = NodeFactory(parent=registration_child)

        assert_equal(registration_grandchild.root._id, self.registration._id)

    def test_fork_has_own_root(self):
        fork = self.project.fork_node(auth=self.auth)
        assert_equal(fork.root._id, fork._id)

    def test_fork_children_have_correct_root(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        assert_equal(fork_child.root._id, fork._id)

    def test_fork_grandchildren_have_correct_root(self):
        fork = self.project.fork_node(auth=self.auth)
        fork_child = NodeFactory(parent=fork)
        fork_grandchild = NodeFactory(parent=fork_child)
        assert_equal(fork_grandchild.root._id, fork._id)

    def test_template_project_has_own_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        assert_equal(new_project.root._id, new_project._id)

    def test_template_project_child_has_correct_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        new_project_child = NodeFactory(parent=new_project)
        assert_equal(new_project_child.root._id, new_project._id)

    def test_template_project_grandchild_has_correct_root(self):
        new_project = self.project.use_as_template(auth=self.auth)
        new_project_child = NodeFactory(parent=new_project)
        new_project_grandchild = NodeFactory(parent=new_project_child)
        assert_equal(new_project_grandchild.root._id, new_project._id)

    def test_node_find_returns_correct_nodes(self):
        # Build up a family of nodes
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)
        # Create a rogue node that's not related at all
        NodeFactory()

        family_ids = [self.project._id] + [r._id for r in self.project.get_descendants_recursive()]
        family_nodes = Node.find(Q('root', 'eq', self.project._id))
        number_of_nodes = family_nodes.count()

        assert_equal(number_of_nodes, 5)
        found_ids = []
        for node in family_nodes:
            assert_in(node._id, family_ids)
            found_ids.append(node._id)
        for node_id in family_ids:
            assert_in(node_id, found_ids)

    def test_get_descendants_recursive_returns_in_depth_order(self):
        """Test the get_descendants_recursive function to make sure its
        not returning any new nodes that we're not expecting
        """
        child_node_one = NodeFactory(parent=self.project)
        child_node_two = NodeFactory(parent=self.project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)

        parent_list = [self.project._id]
        # Verifies, for every node in the list, that parent, we've seen before, in order.
        for project in self.project.get_descendants_recursive():
            parent_list.append(project._id)
            if project.parent:
                assert_in(project.parent._id, parent_list)


class TestTemplateNode(OsfTestCase):

    def setUp(self):
        super(TestTemplateNode, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _verify_log(self, node):
        """Tests to see that the "created from" log event is present (alone).

        :param node: A node having been created from a template just prior
        """
        assert_equal(len(node.logs), 1)
        assert_equal(node.logs[0].action, NodeLog.CREATED_FROM)

    def test_simple_template(self):
        """Create a templated node, with no changes"""
        # created templated node
        new = self.project.use_as_template(
            auth=self.auth
        )

        assert_equal(new.title, self._default_title(self.project))
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def test_simple_template_title_changed(self):
        """Create a templated node, with the title changed"""
        changed_title = 'Made from template'

        # create templated node
        new = self.project.use_as_template(
            auth=self.auth,
            changes={
                self.project._primary_key: {
                    'title': changed_title,
                }
            }
        )

        assert_equal(new.title, changed_title)
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def test_use_as_template_preserves_license(self):
        license = NodeLicenseRecordFactory()
        self.project.node_license = license
        self.project.save()
        new = self.project.use_as_template(
            auth=self.auth
        )

        assert_equal(new.license.node_license._id, license.node_license._id)
        self._verify_log(new)

    def _create_complex(self):
        # create project connected via Pointer
        self.pointee = ProjectFactory(creator=self.user)
        self.project.add_pointer(self.pointee, auth=self.auth)

        # create direct children
        self.component = NodeFactory(creator=self.user, parent=self.project)
        self.subproject = ProjectFactory(creator=self.user, parent=self.project)

    @staticmethod
    def _default_title(x):
        if isinstance(x, Node):
            return str(language.TEMPLATED_FROM_PREFIX + x.title)
        return str(x.title)


    def test_complex_template(self):
        """Create a templated node from a node with children"""
        self._create_complex()

        # create templated node
        new = self.project.use_as_template(auth=self.auth)

        assert_equal(new.title, self._default_title(self.project))
        assert_equal(len(new.nodes), len(self.project.nodes))
        # check that all children were copied
        assert_equal(
            [x.title for x in new.nodes],
            [x.title for x in self.project.nodes],
        )
        # ensure all child nodes were actually copied, instead of moved
        assert {x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        )

    def test_complex_template_titles_changed(self):
        self._create_complex()

        # build changes dict to change each node's title
        changes = {
            x._primary_key: {
                'title': 'New Title ' + str(idx)
            } for idx, x in enumerate(self.project.nodes)
        }

        # create templated node
        new = self.project.use_as_template(
            auth=self.auth,
            changes=changes
        )

        for old_node, new_node in zip(self.project.nodes, new.nodes):
            if isinstance(old_node, Node):
                assert_equal(
                    changes[old_node._primary_key]['title'],
                    new_node.title,
                )
            else:
                assert_equal(
                    old_node.title,
                    new_node.title,
                )

    @requires_piwik
    def test_template_piwik_site_id_not_copied(self):
        new = self.project.use_as_template(
            auth=self.auth
        )
        assert_not_equal(new.piwik_site_id, self.project.piwik_site_id)
        assert_true(new.piwik_site_id is not None)

    def test_template_wiki_pages_not_copied(self):
        self.project.update_node_wiki(
            'template', 'lol',
            auth=self.auth
        )
        new = self.project.use_as_template(
            auth=self.auth
        )
        assert_in('template', self.project.wiki_pages_current)
        assert_in('template', self.project.wiki_pages_versions)
        assert_equal(new.wiki_pages_current, {})
        assert_equal(new.wiki_pages_versions, {})

    def test_user_who_makes_node_from_template_has_creator_permission(self):
        project = ProjectFactory(is_public=True)
        user = UserFactory()
        auth = Auth(user)

        templated = project.use_as_template(auth)

        assert_equal(templated.get_permissions(user), ['read', 'write', 'admin'])

    def test_template_security(self):
        """Create a templated node from a node with public and private children

        Children for which the user has no access should not be copied
        """
        other_user = UserFactory()
        other_user_auth = Auth(user=other_user)

        self._create_complex()

        # set two projects to public - leaving self.component as private
        self.project.is_public = True
        self.project.save()
        self.subproject.is_public = True
        self.subproject.save()

        # add new children, for which the user has each level of access
        self.read = NodeFactory(creator=self.user, parent=self.project)
        self.read.add_contributor(other_user, permissions=['read', ])
        self.read.save()

        self.write = NodeFactory(creator=self.user, parent=self.project)
        self.write.add_contributor(other_user, permissions=['read', 'write'])
        self.write.save()

        self.admin = NodeFactory(creator=self.user, parent=self.project)
        self.admin.add_contributor(other_user)
        self.admin.save()

        # filter down self.nodes to only include projects the user can see
        visible_nodes = filter(
            lambda x: x.can_view(other_user_auth),
            self.project.nodes
        )

        # create templated node
        new = self.project.use_as_template(auth=other_user_auth)

        assert_equal(new.title, self._default_title(self.project))

        # check that all children were copied
        assert_equal(
            set(x.template_node._id for x in new.nodes),
            set(x._id for x in visible_nodes),
        )
        # ensure all child nodes were actually copied, instead of moved
        assert_true({x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        ))

        # ensure that the creator is admin for each node copied
        for node in new.nodes:
            assert_equal(
                node.permissions.get(other_user._id),
                ['read', 'write', 'admin'],
            )


class TestForkNode(OsfTestCase):

    def setUp(self):
        super(TestForkNode, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _cmp_fork_original(self, fork_user, fork_date, fork, original,
                           title_prepend='Fork of '):
        """Compare forked node with original node. Verify copied fields,
        modified fields, and files; recursively compare child nodes.

        :param fork_user: User who forked the original nodes
        :param fork_date: Datetime (UTC) at which the original node was forked
        :param fork: Forked node
        :param original: Original node
        :param title_prepend: String prepended to fork title

        """
        # Test copied fields
        assert_equal(title_prepend + original.title, fork.title)
        assert_equal(original.category, fork.category)
        assert_equal(original.description, fork.description)
        assert_true(len(fork.logs) == len(original.logs) + 1)
        assert_not_equal(original.logs[-1].action, NodeLog.NODE_FORKED)
        assert_equal(fork.logs[-1].action, NodeLog.NODE_FORKED)
        assert_equal(original.tags, fork.tags)
        assert_equal(original.parent_node is None, fork.parent_node is None)

        # Test modified fields
        assert_true(fork.is_fork)
        assert_equal(len(fork.private_links), 0)
        assert_equal(fork.forked_from, original)
        assert_in(fork._id, [n._id for n in original.forks])
        # Note: Must cast ForeignList to list for comparison
        assert_equal(list(fork.contributors), [fork_user])
        assert_true((fork_date - fork.date_created) < datetime.timedelta(seconds=30))
        assert_not_equal(fork.forked_date, original.date_created)

        # Test that pointers were copied correctly
        assert_equal(
            [pointer.node for pointer in original.nodes_pointer],
            [pointer.node for pointer in fork.nodes_pointer],
        )

        # Test that add-ons were copied correctly
        assert_equal(
            original.get_addon_names(),
            fork.get_addon_names()
        )
        assert_equal(
            [addon.config.short_name for addon in original.get_addons()],
            [addon.config.short_name for addon in fork.get_addons()]
        )

        fork_user_auth = Auth(user=fork_user)
        # Recursively compare children
        for idx, child in enumerate(original.nodes):
            if child.can_view(fork_user_auth):
                self._cmp_fork_original(fork_user, fork_date, fork.nodes[idx],
                                        child, title_prepend='')

    @mock.patch('framework.status.push_status_message')
    def test_fork_recursion(self, mock_push_status_message):
        """Omnibus test for forking.
        """
        # Make some children
        self.component = NodeFactory(creator=self.user, parent=self.project)
        self.subproject = ProjectFactory(creator=self.user, parent=self.project)

        # Add pointers to test copying
        pointee = ProjectFactory()
        self.project.add_pointer(pointee, auth=self.auth)
        self.component.add_pointer(pointee, auth=self.auth)
        self.subproject.add_pointer(pointee, auth=self.auth)

        # Add add-on to test copying
        self.project.add_addon('github', self.auth)
        self.component.add_addon('github', self.auth)
        self.subproject.add_addon('github', self.auth)

        # Log time
        fork_date = datetime.datetime.utcnow()

        # Fork node
        with mock.patch.object(Node, 'bulk_update_search'):
            fork = self.project.fork_node(auth=self.auth)

        # Compare fork to original
        self._cmp_fork_original(self.user, fork_date, fork, self.project)

    def test_fork_private_children(self):
        """Tests that only public components are created

        """
        # Make project public
        self.project.set_privacy('public')
        # Make some children
        self.public_component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Forked',
            is_public=True,
        )
        self.public_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Forked',
            is_public=True,
        )
        self.private_component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Not Forked',
        )
        self.private_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Not Forked',
        )
        self.private_subproject_public_component = NodeFactory(
            creator=self.user,
            parent=self.private_subproject,
            title='Not Forked',
        )
        self.public_subproject_public_component = NodeFactory(
            creator=self.user,
            parent=self.private_subproject,
            title='Forked',
        )
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = None
        # New user forks the project
        fork = self.project.fork_node(user2_auth)

        # fork correct children
        assert_equal(len(fork.nodes), 2)
        assert_not_in('Not Forked', [node.title for node in fork.nodes])

    def test_fork_not_public(self):
        self.project.set_privacy('public')
        fork = self.project.fork_node(self.auth)
        assert_false(fork.is_public)

    def test_not_fork_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        fork = self.project.fork_node(self.auth)
        assert_not_in(link, fork.private_links)

    def test_cannot_fork_private_node(self):
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        with assert_raises(PermissionsError):
            self.project.fork_node(user2_auth)

    def test_can_fork_public_node(self):
        self.project.set_privacy('public')
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)

    def test_contributor_can_fork(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)
        # Forker has admin permissions
        assert_equal(len(fork.contributors), 1)
        assert_equal(fork.get_permissions(user2), ['read', 'write', 'admin'])

    def test_fork_preserves_license(self):
        license = NodeLicenseRecordFactory()
        self.project.node_license = license
        self.project.save()
        fork = self.project.fork_node(self.auth)
        assert_equal(fork.node_license.id, license.id)

    def test_fork_registration(self):
        self.registration = RegistrationFactory(project=self.project)
        fork = self.registration.fork_node(self.auth)

        # fork should not be a registration
        assert_false(fork.is_registration)

        # Compare fork to original
        self._cmp_fork_original(
            self.user,
            datetime.datetime.utcnow(),
            fork,
            self.registration,
        )


class TestRegisterNode(OsfTestCase):

    def setUp(self):
        super(TestRegisterNode, self).setUp()
        ensure_schemas()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()
        self.registration = RegistrationFactory(project=self.project)

    def test_factory(self):
        # Create a registration with kwargs
        registration1 = RegistrationFactory(
            title='t1', description='d1', creator=self.user,
        )
        assert_equal(registration1.title, 't1')
        assert_equal(registration1.description, 'd1')
        assert_equal(len(registration1.contributors), 1)
        assert_in(self.user, registration1.contributors)
        assert_equal(registration1.registered_user, self.user)
        assert_equal(len(registration1.private_links), 0)

        # Create a registration from a project
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration2 = RegistrationFactory(
            project=self.project,
            user=user2,
            data={'some': 'data'},
        )
        assert_equal(registration2.registered_from, self.project)
        assert_equal(registration2.registered_user, user2)
        assert_equal(
            registration2.registered_meta[get_default_metaschema()._id],
            {'some': 'data'}
        )

        # Test default user
        assert_equal(self.registration.registered_user, self.user)

    def test_title(self):
        assert_equal(self.registration.title, self.project.title)

    def test_description(self):
        assert_equal(self.registration.description, self.project.description)

    def test_category(self):
        assert_equal(self.registration.category, self.project.category)

    def test_permissions(self):
        assert_false(self.registration.is_public)
        self.project.set_privacy('public')
        registration = RegistrationFactory(project=self.project)
        assert_false(registration.is_public)

    def test_contributors(self):
        assert_equal(self.registration.contributors, self.project.contributors)

    def test_forked_from(self):
        # A a node that is not a fork
        assert_equal(self.registration.forked_from, None)
        # A node that is a fork
        fork = self.project.fork_node(self.auth)
        registration = RegistrationFactory(project=fork)
        assert_equal(registration.forked_from, self.project)

    def test_private_links(self):
        assert_not_equal(
            self.registration.private_links,
            self.project.private_links
        )

    def test_creator(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration = RegistrationFactory(project=self.project)
        assert_equal(registration.creator, self.user)

    def test_logs(self):
        # Registered node has all logs except for registration approval initiated
        assert_equal(len(self.project.logs) - 1, len(self.registration.logs))
        assert_equal(len(self.registration.logs), 1)
        assert_equal(self.registration.logs[0].action, 'project_created')
        assert_equal(len(self.project.logs), 2)
        assert_equal(self.project.logs[0].action, 'project_created')
        assert_equal(self.project.logs[1].action, 'registration_initiated')

    def test_tags(self):
        assert_equal(self.registration.tags, self.project.tags)

    def test_nodes(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Title1',
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Title2',
        )
        self.subproject_component = NodeFactory(
            creator=self.user,
            parent=self.subproject,
            title='Title3',
        )

        # Make a registration
        registration = RegistrationFactory(project=self.project)

        # Reload the registration; else test won't catch failures to save
        registration.reload()

        # Registration has the nodes
        assert_equal(len(registration.nodes), 2)
        assert_equal(
            [node.title for node in registration.nodes],
            [node.title for node in self.project.nodes],
        )
        # Nodes are copies and not the original versions
        for node in registration.nodes:
            assert_not_in(node, self.project.nodes)
            assert_true(node.is_registration)

    def test_private_contributor_registration(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            parent=self.project,
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
        )

        # Create some nodes to share
        self.shared_component = NodeFactory(
            creator=self.user,
            parent=self.project,
        )
        self.shared_subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
        )

        # Share the project and some nodes
        user2 = UserFactory()
        self.project.add_contributor(user2, permissions=('read', 'write', 'admin'))
        self.shared_component.add_contributor(user2, permissions=('read', 'write', 'admin'))
        self.shared_subproject.add_contributor(user2, permissions=('read', 'write', 'admin'))

        # Partial contributor registers the node
        registration = RegistrationFactory(project=self.project, user=user2)

        # The correct subprojects were registered
        assert_equal(len(registration.nodes), len(self.project.nodes))
        for idx in range(len(registration.nodes)):
            assert_true(registration.nodes[idx].is_registration_of(self.project.nodes[idx]))

    def test_is_registration(self):
        assert_true(self.registration.is_registration)

    def test_registered_date(self):
        assert_almost_equal(
            self.registration.registered_date,
            datetime.datetime.utcnow(),
            delta=datetime.timedelta(seconds=30),
        )

    def test_registered_addons(self):
        assert_equal(
            [addon.config.short_name for addon in self.registration.get_addons()],
            [addon.config.short_name for addon in self.registration.registered_from.get_addons()],
        )

    def test_registered_user(self):
        # Add a second contributor
        user2 = UserFactory()
        self.project.add_contributor(user2, permissions=('read', 'write', 'admin'))
        # Second contributor registers project
        registration = RegistrationFactory(parent=self.project, user=user2)
        assert_equal(registration.registered_user, user2)

    def test_registered_from(self):
        assert_equal(self.registration.registered_from, self.project)

    def test_registered_get_absolute_url(self):
        assert_equal(self.registration.get_absolute_url(),
                     '{}v2/registrations/{}/'
                        .format(settings.API_DOMAIN, self.registration._id)
        )

    def test_registration_list(self):
        assert_in(self.registration._id, [n._id for n in self.project.registrations_all])

    def test_registration_gets_institution_affiliation(self):
        node = NodeFactory()
        institution = InstitutionFactory()
        node.primary_institution = institution
        node.save()
        registration = RegistrationFactory(project=node)
        assert_equal(registration.primary_institution._id, node.primary_institution._id)
        assert_equal(set(registration.affiliated_institutions), set(node.affiliated_institutions))

class TestNodeLog(OsfTestCase):

    def setUp(self):
        super(TestNodeLog, self).setUp()
        self.log = NodeLogFactory()

    def test_repr(self):
        rep = repr(self.log)
        assert_in(self.log.action, rep)
        assert_in(self.log._id, rep)

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)

    def test_render_log_contributor_unregistered(self):
        node = NodeFactory()
        name, email = fake.name(), fake.email()
        unreg = node.add_unregistered_contributor(fullname=name, email=email,
            auth=Auth(node.creator))
        node.save()

        log = NodeLogFactory(params={'node': node._primary_key})
        ret = log._render_log_contributor(unreg._primary_key)

        assert_false(ret['registered'])
        record = unreg.get_unclaimed_record(node._primary_key)
        assert_equal(ret['fullname'], record['name'])

    def test_render_log_contributor_none(self):
        log = NodeLogFactory()
        assert_equal(log._render_log_contributor(None), None)

    def test_tz_date(self):
        assert_equal(self.log.tz_date.tzinfo, pytz.UTC)

    def test_formatted_date(self):
        iso_formatted = self.log.formatted_date  # The string version in iso format
        # Reparse the date
        parsed = parser.parse(iso_formatted)
        unparsed = self.log.tz_date
        assert_equal(parsed, unparsed)

    def test_can_view(self):
        project = ProjectFactory(is_public=False)

        non_contrib = UserFactory()

        created_log = project.logs[0]
        assert_false(created_log.can_view(project, Auth(user=non_contrib)))
        assert_true(created_log.can_view(project, Auth(user=project.creator)))

    def test_can_view_with_non_related_project_arg(self):
        project = ProjectFactory()
        unrelated = ProjectFactory()

        created_log = project.logs[0]
        assert_false(created_log.can_view(unrelated, Auth(user=project.creator)))


    def test_original_node_and_current_node_for_registration_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        registration = RegistrationFactory(project=project)

        log_project_created_original = project.logs[0]
        log_registration_initiated = project.logs[1]
        log_project_created_registration = registration.logs[0]

        assert_equal(project._id, log_project_created_original.original_node._id)
        assert_equal(project._id, log_project_created_original.node._id)
        assert_equal(registration._id, log_registration_initiated.original_node._id)
        assert_equal(project._id, log_registration_initiated.node._id)
        assert_equal(project._id, log_project_created_registration.original_node._id)
        assert_equal(registration._id, log_project_created_registration.node._id)

    def test_original_node_and_current_node_for_fork_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        fork = project.fork_node(auth=Auth(user))

        log_project_created_original = project.logs[0]
        log_project_created_fork = fork.logs[0]
        log_node_forked = fork.logs[1]

        assert_equal(project._id, log_project_created_original.original_node._id)
        assert_equal(project._id, log_project_created_original.node._id)
        assert_equal(project._id, log_project_created_fork.original_node._id)
        assert_equal(fork._id, log_project_created_fork.node._id)
        assert_equal(project._id, log_node_forked.original_node._id)
        assert_equal(fork._id, log_node_forked.node._id)


class TestPermissions(OsfTestCase):

    def setUp(self):
        super(TestPermissions, self).setUp()
        self.project = ProjectFactory()

    def test_default_creator_permissions(self):
        assert_equal(
            set(CREATOR_PERMISSIONS),
            set(self.project.permissions[self.project.creator._id])
        )

    def test_default_contributor_permissions(self):
        user = UserFactory()
        self.project.add_contributor(user, permissions=['read'], auth=Auth(user=self.project.creator))
        self.project.save()
        assert_equal(
            set(['read']),
            set(self.project.get_permissions(user))
        )

    def test_adjust_permissions(self):
        self.project.permissions[42] = ['dance']
        self.project.save()
        assert_not_in(42, self.project.permissions)

    def test_add_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_in(self.project.creator._id, self.project.permissions)
        assert_in('dance', self.project.permissions[self.project.creator._id])

    def test_add_permission_already_granted(self):
        self.project.add_permission(self.project.creator, 'dance')
        with assert_raises(ValueError):
            self.project.add_permission(self.project.creator, 'dance')

    def test_remove_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        self.project.remove_permission(self.project.creator, 'dance')
        assert_not_in('dance', self.project.permissions[self.project.creator._id])

    def test_remove_permission_not_granted(self):
        with assert_raises(ValueError):
            self.project.remove_permission(self.project.creator, 'dance')

    def test_has_permission_true(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_true(self.project.has_permission(self.project.creator, 'dance'))

    def test_has_permission_false(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_false(self.project.has_permission(self.project.creator, 'sing'))

    def test_has_permission_not_in_dict(self):
        assert_false(self.project.has_permission(self.project.creator, 'dance'))


class TestPointer(OsfTestCase):

    def setUp(self):
        super(TestPointer, self).setUp()
        self.pointer = PointerFactory()

    def test_title(self):
        assert_equal(
            self.pointer.title,
            self.pointer.node.title
        )

    def test_contributors(self):
        assert_equal(
            self.pointer.contributors,
            self.pointer.node.contributors
        )

    def _assert_clone(self, pointer, cloned):
        assert_not_equal(
            pointer._id,
            cloned._id
        )
        assert_equal(
            pointer.node,
            cloned.node
        )

    def test_get_pointer_parent(self):
        parent = ProjectFactory()
        pointed = ProjectFactory()
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()
        assert_equal(get_pointer_parent(parent.nodes[0]), parent)

    def test_clone(self):
        cloned = self.pointer._clone()
        self._assert_clone(self.pointer, cloned)

    def test_clone_no_node(self):
        pointer = Pointer()
        cloned = pointer._clone()
        assert_equal(cloned, None)

    def test_fork(self):
        forked = self.pointer.fork_node()
        self._assert_clone(self.pointer, forked)

    def test_register(self):
        registered = self.pointer.fork_node()
        self._assert_clone(self.pointer, registered)

    def test_register_with_pointer_to_registration(self):
        pointee = RegistrationFactory()
        project = ProjectFactory()
        auth = Auth(user=project.creator)
        project.add_pointer(pointee, auth=auth)
        with mock_archive(project) as registration:
            assert_equal(registration.nodes[0].node, pointee)

    def test_has_pointers_recursive_false(self):
        project = ProjectFactory()
        node = NodeFactory(project=project)
        assert_false(project.has_pointers_recursive)
        assert_false(node.has_pointers_recursive)

    def test_has_pointers_recursive_true(self):
        project = ProjectFactory()
        node = NodeFactory(parent=project)
        node.nodes.append(self.pointer)
        assert_true(node.has_pointers_recursive)
        assert_true(project.has_pointers_recursive)


class TestWatchConfig(OsfTestCase):

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)


class TestUnregisteredUser(OsfTestCase):

    def setUp(self):
        super(TestUnregisteredUser, self).setUp()
        self.referrer = UserFactory()
        self.project = ProjectFactory(creator=self.referrer)
        self.user = UnregUserFactory()

    def add_unclaimed_record(self):
        given_name = 'Fredd Merkury'
        email = fake.email()
        self.user.add_unclaimed_record(node=self.project,
            given_name=given_name, referrer=self.referrer,
            email=email)
        self.user.save()
        data = self.user.unclaimed_records[self.project._primary_key]
        return email, data

    def test_unregistered_factory(self):
        u1 = UnregUserFactory()
        assert_false(u1.is_registered)
        assert_true(u1.password is None)
        assert_true(u1.fullname)

    def test_unconfirmed_factory(self):
        u = UnconfirmedUserFactory()
        assert_false(u.is_registered)
        assert_true(u.username)
        assert_true(u.fullname)
        assert_true(u.password)
        assert_equal(len(u.email_verifications.keys()), 1)

    def test_add_unclaimed_record(self):
        email, data = self.add_unclaimed_record()
        assert_equal(data['name'], 'Fredd Merkury')
        assert_equal(data['referrer_id'], self.referrer._primary_key)
        assert_in('token', data)
        assert_equal(data['email'], email)
        assert_equal(data, self.user.get_unclaimed_record(self.project._primary_key))

    def test_get_claim_url(self):
        self.add_unclaimed_record()
        uid = self.user._primary_key
        pid = self.project._primary_key
        token = self.user.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert_equal(self.user.get_claim_url(pid, external=True),
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals()))

    def test_get_claim_url_raises_value_error_if_not_valid_pid(self):
        with assert_raises(ValueError):
            self.user.get_claim_url('invalidinput')

    def test_cant_add_unclaimed_record_if_referrer_isnt_contributor(self):
        project = ProjectFactory()  # referrer isn't a contributor to this project
        with assert_raises(PermissionsError):
            self.user.add_unclaimed_record(node=project,
                given_name='fred m', referrer=self.referrer)

    def test_register(self):
        assert_false(self.user.is_registered)  # sanity check
        assert_false(self.user.is_claimed)
        email = fake.email()
        self.user.register(username=email, password='killerqueen')
        self.user.save()
        assert_true(self.user.is_claimed)
        assert_true(self.user.is_registered)
        assert_true(self.user.check_password('killerqueen'))
        assert_equal(self.user.username, email)

    def test_registering_with_a_different_email_adds_to_emails_list(self):
        user = UnregUserFactory()
        assert_equal(user.password, None)  # sanity check
        user.register(username=fake.email(), password='killerqueen')

    def test_verify_claim_token(self):
        self.add_unclaimed_record()
        valid = self.user.get_unclaimed_record(self.project._primary_key)['token']
        assert_true(self.user.verify_claim_token(valid, project_id=self.project._primary_key))
        assert_false(self.user.verify_claim_token('invalidtoken', project_id=self.project._primary_key))

    def test_claim_contributor(self):
        self.add_unclaimed_record()
        # sanity cheque
        assert_false(self.user.is_registered)
        assert_true(self.project)


class TestTags(OsfTestCase):

    def setUp(self):
        super(TestTags, self).setUp()
        self.project = ProjectFactory()
        self.auth = Auth(self.project.creator)

    def test_add_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        assert_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.TAG_ADDED
        )

    def test_add_tag_too_long(self):
        with assert_raises(ValidationError):
            self.project.add_tag('q' * 129, auth=self.auth)

    def test_remove_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        self.project.remove_tag('scientific', auth=self.auth)
        assert_not_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.TAG_REMOVED
        )

    def test_remove_tag_not_present(self):
        self.project.remove_tag('scientific', auth=self.auth)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.PROJECT_CREATED
        )


class TestContributorVisibility(OsfTestCase):

    def setUp(self):
        super(TestContributorVisibility, self).setUp()
        self.project = ProjectFactory()
        self.user2 = UserFactory()
        self.project.add_contributor(self.user2)

    def test_get_visible_true(self):
        assert_true(self.project.get_visible(self.project.creator))

    def test_get_visible_false(self):
        self.project.set_visible(self.project.creator, False)
        assert_false(self.project.get_visible(self.project.creator))

    def test_make_invisible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.reload()
        assert_not_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_not_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.MADE_CONTRIBUTOR_INVISIBLE
        )

    def test_make_visible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.set_visible(self.project.creator, True, save=True)
        self.project.reload()
        assert_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.MADE_CONTRIBUTOR_VISIBLE
        )
        # Regression test: Ensure that hiding and showing the first contributor
        # does not change the visible contributor order
        assert_equal(
            self.project.visible_contributors,
            [self.project.creator, self.user2]
        )

    def test_set_visible_missing(self):
        with assert_raises(ValueError):
            self.project.set_visible(UserFactory(), True)


class TestProjectWithAddons(OsfTestCase):

    def test_factory(self):
        p = ProjectWithAddonFactory(addon='s3')
        assert_true(p.get_addon('s3'))
        assert_true(p.creator.get_addon('s3'))


class TestPrivateLink(OsfTestCase):

    def test_node_scale(self):
        link = PrivateLinkFactory()
        project = ProjectFactory()
        comp = NodeFactory(parent=project)
        link.nodes.append(project)
        link.save()
        assert_equal(link.node_scale(project), -40)
        assert_equal(link.node_scale(comp), -20)

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_to_json_nodes_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(project=project)
        link.nodes.extend([project, node])
        link.save()
        result = link.to_json()
        # result doesn't include deleted parent
        assert_equal(len(result['nodes']), 1)

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_node_scale_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(project=project)
        link.nodes.extend([project, node])
        link.save()
        assert_equal(link.node_scale(node), -40)


    def test_create_from_node(self):
        ensure_schemas()
        proj = ProjectFactory()
        user = proj.creator
        schema = MetaSchema.find()[0]
        data = {'some': 'data'}
        draft = DraftRegistration.create_from_node(
            proj,
            user=user,
            schema=schema,
            data=data,
        )
        assert_equal(user, draft.initiator)
        assert_equal(schema, draft.registration_schema)
        assert_equal(data, draft.registration_metadata)
        assert_equal(proj, draft.branched_from)


if __name__ == '__main__':
    unittest.main()