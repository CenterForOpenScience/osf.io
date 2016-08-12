# -*- coding: utf-8 -*-
# Tests ported from tests/test_models.py and tests/test_user.py
import datetime as dt
import urlparse

import mock
import itsdangerous
import pytest
import pytz

from framework.auth.exceptions import ExpiredTokenError, InvalidTokenError, ChangePasswordError
from framework.analytics import get_total_activity_count
from framework.exceptions import PermissionsError
from website import settings
from website import filters

from osf_models.models import OSFUser as User, Tag, Node, Contributor, Session
from osf_models.utils.auth import Auth
from osf_models.utils.names import impute_names_model
from osf_models.exceptions import ValidationError
from osf_models.modm_compat import Q

from .factories import (
    fake,
    NodeFactory,
    InstitutionFactory,
    UserFactory,
    UnregUserFactory,
    UnconfirmedUserFactory
)

@pytest.mark.django_db
def test_factory():
    user = UserFactory.build()
    user.save()

@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def auth(user):
    return Auth(user)

# Tests copied from tests/test_models.py
@pytest.mark.django_db
class TestOSFUser:

    def test_create(self):
        name, email = fake.name(), fake.email()
        user = User.create(
            username=email, password='foobar', fullname=name
        )
        # TODO: Remove me when auto_now_add is enabled (post-migration)
        user.date_registered = dt.datetime.utcnow()
        user.save()
        assert user.check_password('foobar') is True
        assert user._id
        assert user.given_name == impute_names_model(name)['given_name']

    def test_create_unconfirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_unconfirmed(
            username=email, password='foobar', fullname=name
        )
        # TODO: Remove me when auto_now_add is enabled (post-migration)
        user.date_registered = dt.datetime.utcnow()
        user.save()
        assert user.is_registered is False
        assert len(user.email_verifications.keys()) == 1
        assert len(user.emails) == 0, 'primary email has not been added to emails list'

    def test_create_unconfirmed_with_campaign(self):
        name, email = fake.name(), fake.email()
        user = User.create_unconfirmed(
            username=email, password='foobar', fullname=name,
            campaign='institution'
        )
        assert 'institution_campaign' in user.system_tags

    def test_update_guessed_names(self):
        name = fake.name()
        u = User(fullname=name)
        u.update_guessed_names()

        parsed = impute_names_model(name)
        assert u.fullname == name
        assert u.given_name == parsed['given_name']
        assert u.middle_names == parsed['middle_names']
        assert u.family_name == parsed['family_name']
        assert u.suffix == parsed['suffix']

    def test_create_unregistered(self):
        name, email = fake.name(), fake.email()
        u = User.create_unregistered(email=email,
                                     fullname=name)
        # TODO: Remove post-migration
        u.date_registered = dt.datetime.utcnow()
        u.save()
        assert u.username == email
        assert u.is_registered is False
        assert u.is_claimed is False
        assert u.is_invited is True
        assert email not in u.emails
        parsed = impute_names_model(name)
        assert u.given_name == parsed['given_name']

    @mock.patch('osf_models.models.user.OSFUser.update_search')
    def test_search_not_updated_for_unreg_users(self, update_search):
        u = User.create_unregistered(fullname=fake.name(), email=fake.email())
        # TODO: Remove post-migration
        u.date_registered = dt.datetime.utcnow()
        u.save()
        assert not update_search.called

    @mock.patch('osf_models.models.OSFUser.update_search')
    def test_search_updated_for_registered_users(self, update_search):
        UserFactory(is_registered=True)
        assert update_search.called

    def test_create_unregistered_raises_error_if_already_in_db(self):
        u = UnregUserFactory()
        dupe = User.create_unregistered(fullname=fake.name(), email=u.username)
        with pytest.raises(ValidationError):
            dupe.save()

    @pytest.mark.skip('User#merge_user not yet implemented')
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
        with pytest.raises(ValidationError):
            u.save()

    def test_date_registered_upon_saving(self):
        u = User(username=fake.email(), fullname='Foo bar')
        u.set_unusable_password()
        u.save()
        assert bool(u.date_registered) is True
        assert u.date_registered.tzinfo == pytz.utc

    def test_cant_create_user_without_full_name(self):
        u = User(username=fake.email())
        with pytest.raises(ValidationError):
            u.save()

    @mock.patch('osf_models.utils.security.random_string')
    def test_get_confirmation_token(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory.build()
        u.add_unconfirmed_email('foo@bar.com')
        u.save()
        assert u.get_confirmation_token('foo@bar.com') == '12345'
        assert u.get_confirmation_token('fOo@bar.com') == '12345'

    def test_get_confirmation_token_when_token_is_expired_raises_error(self):
        u = UserFactory()
        # Make sure token is already expired
        expiration = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

    @mock.patch('osf_models.utils.security.random_string')
    def test_get_confirmation_token_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        # sanity check
        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

        random_string.return_value = '54321'

        token = u.get_confirmation_token('foo@bar.com', force=True)
        assert token == '54321'

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

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token(email)

    @mock.patch('osf_models.utils.security.random_string')
    def test_get_confirmation_url(self, random_string):
        random_string.return_value = 'abcde'
        u = UserFactory()
        u.add_unconfirmed_email('foo@bar.com')
        assert(
            u.get_confirmation_url('foo@bar.com') ==
            '{0}confirm/{1}/{2}/'.format(settings.DOMAIN, u._id, 'abcde')
        )

    def test_get_confirmation_url_when_token_is_expired_raises_error(self):
        u = UserFactory()
        # Make sure token is already expired
        expiration = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_url('foo@bar.com')

    @mock.patch('osf_models.utils.security.random_string')
    def test_get_confirmation_url_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        # sanity check
        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

        random_string.return_value = '54321'

        url = u.get_confirmation_url('foo@bar.com', force=True)
        expected = '{0}confirm/{1}/{2}/'.format(settings.DOMAIN, u._id, '54321')
        assert url == expected

    def test_confirm_primary_email(self):
        u = UnconfirmedUserFactory()
        token = u.get_confirmation_token(u.username)
        confirmed = u.confirm_email(token)
        u.save()
        assert bool(confirmed) is True
        assert len(u.email_verifications.keys()) == 0
        assert u.username in u.emails
        assert bool(u.is_registered) is True
        assert bool(u.is_claimed) is True

    def test_confirm_email(self, user):
        token = user.add_unconfirmed_email('foo@bar.com')
        user.confirm_email(token)

        assert 'foo@bar.com' not in user.unconfirmed_emails
        assert 'foo@bar.com' in user.emails

    def test_confirm_email_comparison_is_case_insensitive(self):
        u = UnconfirmedUserFactory.build(
            username='letsgettacos@lgt.com'
        )
        u.add_unconfirmed_email('LetsGetTacos@LGT.com')
        u.save()
        assert bool(u.is_confirmed) is False  # sanity check

        token = u.get_confirmation_token('LetsGetTacos@LGT.com')

        confirmed = u.confirm_email(token)
        assert confirmed is True
        assert u.is_confirmed is True

    def test_verify_confirmation_token(self):
        u = UserFactory.build()
        u.add_unconfirmed_email('foo@bar.com')
        u.save()

        with pytest.raises(InvalidTokenError):
            u.get_unconfirmed_email_for_token('badtoken')

        valid_token = u.get_confirmation_token('foo@bar.com')
        assert bool(u.get_unconfirmed_email_for_token(valid_token)) is True
        manual_expiration = dt.datetime.utcnow() - dt.timedelta(0, 10)
        u._set_email_token_expiration(valid_token, expiration=manual_expiration)

        with pytest.raises(ExpiredTokenError):
            u.get_unconfirmed_email_for_token(valid_token)

    def test_verify_confirmation_token_when_token_has_no_expiration(self):
        # A user verification token may not have an expiration
        email = fake.email()
        u = UserFactory.build()
        u.add_unconfirmed_email(email)
        token = u.get_confirmation_token(email)
        # manually remove expiration to simulate legacy user
        del u.email_verifications[token]['expiration']
        u.save()

        assert bool(u.get_unconfirmed_email_for_token(token)) is True

    def test_format_surname(self):
        user = UserFactory(fullname='Duane Johnson')
        summary = user.get_summary(formatter='surname')
        assert(
            summary['user_display_name'] ==
            'Johnson'
        )

    def test_format_surname_one_name(self):
        user = UserFactory(fullname='Rock')
        summary = user.get_summary(formatter='surname')
        assert(
            summary['user_display_name'] ==
            'Rock'
        )

    def test_url(self, user):
        assert user.url == '/{0}/'.format(user._id)

    def test_absolute_url(self, user):
        assert(
            user.absolute_url ==
            urlparse.urljoin(settings.DOMAIN, '/{0}/'.format(user._id))
        )

    def test_profile_image_url(self, user):
        expected = filters.gravatar(
            user,
            use_ssl=True,
            size=settings.PROFILE_IMAGE_MEDIUM
        )
        assert user.profile_image_url(settings.PROFILE_IMAGE_MEDIUM) == expected

    def test_profile_image_url_has_no_default_size(self, user):
        expected = filters.gravatar(
            user,
            use_ssl=True,
        )
        assert user.profile_image_url() == expected
        size = urlparse.parse_qs(urlparse.urlparse(user.profile_image_url()).query).get('size')
        assert size is None

    @pytest.mark.skip('activity points not yet implemented')
    def test_activity_points(self, user):
        assert(
            user.get_activity_points(db=self.db) == get_total_activity_count(self.user._primary_key)
        )

    def test_contributed_property(self):
        user = UserFactory()
        node = NodeFactory()
        node2 = NodeFactory()
        # TODO: Use Node.add_contributor when it's implemented
        Contributor.objects.create(user=user, node=node)
        projects_contributed_to = Node.objects.filter(contributors=user)
        assert list(user.contributed) == list(projects_contributed_to)
        assert node2 not in user.contributed

    # copied from tests/test_views.py
    def test_clean_email_verifications(self, user):
        # Do not return bad token and removes it from user.email_verifications
        email = 'test@example.com'
        token = 'blahblahblah'
        user.email_verifications[token] = {'expiration': (dt.datetime.utcnow() + dt.timedelta(days=1)),
                                                'email': email,
                                                'confirmed': False }
        user.save()
        assert user.email_verifications[token]['email'] == email
        user.clean_email_verifications(given_token=token)
        unconfirmed_emails = user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert user.email_verifications == {}

    def test_display_full_name_registered(self):
        u = UserFactory()
        assert u.display_full_name() == u.fullname

    @pytest.mark.skip('add_unregistered_contributor not yet implemented')
    def test_display_full_name_unregistered(self):
        name = fake.name()
        u = UnregUserFactory()
        project = NodeFactory()
        project.add_unregistered_contributor(fullname=name, email=u.username,
            auth=Auth(project.creator))
        project.save()
        assert u.display_full_name(node=project) == name

    def test_username_is_automatically_lowercased(self):
        user = UserFactory(username='nEoNiCon@bet.com')
        assert user.username == 'neonicon@bet.com'

    def test_update_affiliated_institutions_by_email_domains(self):
        institution = InstitutionFactory()
        email_domain = institution.email_domains[0]

        user_email = '{}@{}'.format(fake.domain_word(), email_domain)
        user = UserFactory(username=user_email)
        user.update_affiliated_institutions_by_email_domain()

        assert user.is_affiliated_with(institution) is True

    def test_is_affiliated_with(self, user):
        institution1, institution2 = InstitutionFactory(), InstitutionFactory()

        user.affiliated_institutions.add(institution1)
        user.save()

        assert user.is_affiliated_with(institution1) is True
        assert user.is_affiliated_with(institution2) is False


@pytest.mark.django_db
class TestProjectsInCommon:

    def test_get_projects_in_common(self, user, auth):
        user2 = UserFactory()
        project = NodeFactory(creator=user)
        project.add_contributor(contributor=user2, auth=auth)
        project.save()

        project_keys = set([node._id for node in user.contributed])
        projects = set(user.contributed)
        user2_project_keys = set([node._id for node in user2.contributed])

        assert(user.get_projects_in_common(user2, primary_keys=True) ==
                     project_keys.intersection(user2_project_keys))
        assert(user.get_projects_in_common(user2, primary_keys=False) ==
                     projects.intersection(user2.contributed))

    def test_n_projects_in_common(self, user, auth):
        user2 = UserFactory()
        user3 = UserFactory()
        project = NodeFactory(creator=user)

        project.add_contributor(contributor=user2, auth=auth)
        project.save()

        assert user.n_projects_in_common(user2) == 1
        assert user.n_projects_in_common(user3) == 0


@pytest.mark.django_db
class TestCookieMethods:

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

        assert signer.unsign(user.get_or_create_cookie(super_secret_key)) == session._id

    def test_user_get_cookie_no_session(self):
        user = UserFactory()
        super_secret_key = 'children need maps'
        signer = itsdangerous.Signer(super_secret_key)
        assert(
            Session.find(Q('data.auth_user_id', 'eq', user._id)).count() == 0
        )

        cookie = user.get_or_create_cookie(super_secret_key)

        session = Session.find(Q('data.auth_user_id', 'eq', user._id))[0]

        assert session._id == signer.unsign(cookie)
        assert session.data['auth_user_id'] == user._id
        assert session.data['auth_user_username'] == user.username
        assert session.data['auth_user_fullname'] == user.fullname

    def test_get_user_by_cookie(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        assert user == User.from_cookie(cookie)

    def test_get_user_by_cookie_returns_none(self):
        assert User.from_cookie('') is None

    def test_get_user_by_cookie_bad_cookie(self):
        assert User.from_cookie('foobar') is None

    def test_get_user_by_cookie_no_user_id(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        session = Session.find_one(Q('data.auth_user_id', 'eq', user._id))
        del session.data['auth_user_id']
        session.save()
        assert User.from_cookie(cookie) is None

    def test_get_user_by_cookie_no_session(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        Session.objects.all().delete()
        assert User.from_cookie(cookie) is None


@pytest.mark.django_db
class TestChangePassword:

    def test_change_password(self, user):
        old_password = 'password'
        new_password = 'new password'
        confirm_password = new_password
        user.set_password(old_password)
        user.save()
        user.change_password(old_password, new_password, confirm_password)
        assert bool(user.check_password(new_password)) is True

    def test_change_password_invalid(self, old_password=None, new_password=None, confirm_password=None,
                                     error_message='Old password is invalid'):
        user = UserFactory()
        user.set_password('password')
        user.save()
        with pytest.raises(ChangePasswordError) as excinfo:
            user.change_password(old_password, new_password, confirm_password)
            user.save()
        assert error_message in excinfo.value.message
        assert bool(user.check_password(new_password)) is False

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


@pytest.mark.django_db
class TestIsActive:

    @pytest.fixture()
    def make_user(self):
        def func(**attrs):
            # By default, return an active user
            user = UserFactory.build(
                is_registered=True,
                merged_by=None,
                is_disabled=False,
                date_confirmed=dt.datetime.utcnow(),
            )
            user.set_password('secret')
            for attr, value in attrs.items():
                setattr(user, attr, value)
            return user
        return func

    def test_is_active_is_set_to_true_under_correct_conditions(self, make_user):
        user = make_user()
        user.save()
        assert user.is_active is True

    def test_is_active_is_false_if_not_registered(self, make_user):
        user = make_user(is_registered=False)
        user.save()
        assert user.is_active is False

    def test_is_active_is_false_if_not_confirmed(self, make_user):
        user = make_user(date_confirmed=None)
        user.save()
        assert user.is_active is False

    def test_is_active_is_false_if_password_unset(self, make_user):
        user = make_user()
        user.set_unusable_password()
        user.save()
        assert user.is_active is False

    def test_is_active_is_false_if_merged(self, make_user):
        merger = UserFactory()
        user = make_user(merged_by=merger)
        user.save()
        assert user.is_active is False

    def test_is_active_is_false_if_disabled(self, make_user):
        user = make_user(date_disabled=dt.datetime.utcnow())
        assert user.is_active is False


@pytest.mark.django_db
class TestAddUnconfirmedEmail:

    @mock.patch('osf_models.utils.security.random_string')
    def test_add_unconfirmed_email(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        assert len(u.email_verifications.keys()) == 0
        u.add_unconfirmed_email('foo@bar.com')
        assert len(u.email_verifications.keys()) == 1
        assert u.email_verifications[token]['email'] == 'foo@bar.com'

    @mock.patch('osf_models.utils.security.random_string')
    def test_add_unconfirmed_email_adds_expiration_date(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        u.add_unconfirmed_email('test@osf.io')
        assert isinstance(u.email_verifications[token]['expiration'], dt.datetime)

    def test_add_blank_unconfirmed_email(self):
        user = UserFactory()
        with pytest.raises(ValidationError) as exc_info:
            user.add_unconfirmed_email('')
        assert exc_info.value.message == 'Enter a valid email address.'

# Copied from tests/test_models.TestUnregisteredUser

@pytest.mark.django_db
class TestUnregisteredUser:

    @pytest.fixture()
    def referrer(self):
        return UserFactory()

    @pytest.fixture()
    def email(self):
        return fake.email()

    @pytest.fixture()
    def unreg_user(self, referrer, project, email):
        user = UnregUserFactory()
        given_name = 'Fredd Merkury'
        user.add_unclaimed_record(node=project,
            given_name=given_name, referrer=referrer,
            email=email)
        user.save()
        return user

    @pytest.fixture()
    def project(self, referrer):
        return NodeFactory(creator=referrer)

    def test_unregistered_factory(self):
        u1 = UnregUserFactory()
        assert bool(u1.is_registered) is False
        assert u1.has_usable_password() is False
        assert bool(u1.fullname) is True

    def test_unconfirmed_factory(self):
        u = UnconfirmedUserFactory()
        assert bool(u.is_registered) is False
        assert bool(u.username) is True
        assert bool(u.fullname) is True
        assert bool(u.password) is True
        assert len(u.email_verifications.keys()) == 1

    def test_add_unclaimed_record(self, unreg_user, email, referrer, project):
        data = unreg_user.unclaimed_records[project._primary_key]
        assert data['name'] == 'Fredd Merkury'
        assert data['referrer_id'] == referrer._id
        assert 'token' in data
        assert data['email'] == email
        assert data == unreg_user.get_unclaimed_record(project._primary_key)

    def test_get_claim_url(self, unreg_user, project):
        uid = unreg_user._primary_key
        pid = project._primary_key
        token = unreg_user.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert (
            unreg_user.get_claim_url(pid, external=True) ==
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals())
        )

    def test_get_claim_url_raises_value_error_if_not_valid_pid(self, unreg_user):
        with pytest.raises(ValueError):
            unreg_user.get_claim_url('invalidinput')

    def test_cant_add_unclaimed_record_if_referrer_isnt_contributor(self, referrer, unreg_user):
        project = NodeFactory()  # referrer isn't a contributor to this project
        with pytest.raises(PermissionsError):
            unreg_user.add_unclaimed_record(node=project,
                given_name='fred m', referrer=referrer)

    @mock.patch('osf_models.models.OSFUser.update_search_nodes')
    @mock.patch('osf_models.models.OSFUser.update_search')
    def test_register(self, mock_search, mock_search_nodes):
        user = UnregUserFactory()
        assert user.is_registered is False  # sanity check
        assert user.is_claimed is False
        email = fake.email()
        user.register(username=email, password='killerqueen')
        user.save()
        assert user.is_claimed is True
        assert user.is_registered is True
        assert user.check_password('killerqueen') is True
        assert user.username == email

    @mock.patch('osf_models.models.OSFUser.update_search_nodes')
    @mock.patch('osf_models.models.OSFUser.update_search')
    def test_registering_with_a_different_email_adds_to_emails_list(self, mock_search, mock_search_nodes):
        user = UnregUserFactory()
        assert user.has_usable_password() is False  # sanity check
        email = fake.email()
        user.register(username=email, password='killerqueen')
        assert email in user.emails

    def test_verify_claim_token(self, unreg_user, project):
        valid = unreg_user.get_unclaimed_record(project._primary_key)['token']
        assert bool(unreg_user.verify_claim_token(valid, project_id=project._primary_key)) is True
        assert bool(unreg_user.verify_claim_token('invalidtoken', project_id=project._primary_key)) is False

# Copied from tests/test_models.py
@pytest.mark.django_db
class TestRecentlyAdded:

    def test_recently_added(self, user, auth):
        # Project created
        project = NodeFactory()

        assert hasattr(user, 'recently_added') is True

        # Two users added as contributors
        user2 = UserFactory()
        user3 = UserFactory()
        project.add_contributor(contributor=user2, auth=auth)
        project.add_contributor(contributor=user3, auth=auth)
        recently_added = list(user.get_recently_added())
        assert user3 == recently_added[0]
        assert user2 == recently_added[1]
        assert len(list(recently_added)) == 2

    def test_recently_added_multi_project(self, user, auth):
        # Three users are created
        user2 = UserFactory()
        user3 = UserFactory()
        user4 = UserFactory()

        # 2 projects created
        project = NodeFactory()
        project2 = NodeFactory()

        # Users 2 and 3 are added to original project
        project.add_contributor(contributor=user2, auth=auth)
        project.add_contributor(contributor=user3, auth=auth)

        # Users 2 and 3 are added to another project
        project2.add_contributor(contributor=user2, auth=auth)
        project2.add_contributor(contributor=user4, auth=auth)

        recently_added = list(user.get_recently_added())
        assert user4 == recently_added[0]
        assert user2 == recently_added[1]
        assert user3 == recently_added[2]
        assert len(recently_added) == 3

    def test_recently_added_length(self, user, auth):
        # Project created
        project = NodeFactory()

        assert len(list(user.get_recently_added())) == 0
        # Add 17 users
        for _ in range(17):
            project.add_contributor(
                contributor=UserFactory(),
                auth=auth
            )

        assert len(list(user.get_recently_added())) == 15

# New tests
@pytest.mark.django_db
class TestTagging:
    def test_add_system_tag(self, user):
        tag_name = fake.word()
        user.add_system_tag(tag_name)
        user.save()

        assert len(user.system_tags) == 1

        tag = Tag.objects.get(name=tag_name, system=True)
        assert tag in user.tags.all()

    def test_tags_get_lowercased(self, user):
        tag_name = 'NeOn'
        user.add_system_tag(tag_name)
        user.save()

        tag = Tag.objects.get(name=tag_name.lower(), system=True)
        assert tag in user.tags.all()

    def test_system_tags_property(self, user):
        tag_name = fake.word()
        user.add_system_tag(tag_name)

        assert tag_name in user.system_tags
