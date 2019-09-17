# -*- coding: utf-8 -*-
# Tests ported from tests/test_models.py and tests/test_user.py
import os
import json
import datetime as dt
from future.moves.urllib.parse import urlparse, urljoin, parse_qs

from django.db import connection, transaction
from django.contrib.auth.models import Group
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
import mock
import itsdangerous
import pytest
import pytz

from framework.auth.exceptions import ExpiredTokenError, InvalidTokenError, ChangePasswordError
from framework.auth.signals import user_merged
from framework.analytics import get_total_activity_count
from framework.exceptions import PermissionsError
from framework.celery_tasks import handlers
from website import settings
from website import filters
from website import mailchimp_utils
from website.project.signals import contributor_added
from website.project.views.contributor import notify_added_contributor
from website.views import find_bookmark_collection

from osf.models import AbstractNode, OSFUser, OSFGroup, Tag, Contributor, Session, BlacklistedEmailDomain, QuickFilesNode, PreprintContributor
from addons.github.tests.factories import GitHubAccountFactory
from addons.osfstorage.models import Region
from addons.osfstorage.settings import DEFAULT_REGION_ID
from framework.auth.core import Auth
from osf.utils.names import impute_names_model
from osf.utils import permissions
from osf.exceptions import ValidationError, BlacklistedEmailError, UserStateError

from .utils import capture_signals
from .factories import (
    fake,
    fake_email,
    AuthUserFactory,
    CollectionFactory,
    ExternalAccountFactory,
    InstitutionFactory,
    NodeFactory,
    OSFGroupFactory,
    PreprintProviderFactory,
    ProjectFactory,
    SessionFactory,
    TagFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
    UserFactory,
    RegistrationFactory,
    PreprintFactory
)
from tests.base import OsfTestCase
from tests.utils import run_celery_tasks


pytestmark = pytest.mark.django_db

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
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestOSFUser:

    def test_create(self):
        name, email = fake.name(), fake_email()
        user = OSFUser.create(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert user.check_password('foobar') is True
        assert user._id
        assert user.given_name == impute_names_model(name)['given_name']

    def test_create_unconfirmed(self):
        name, email = fake.name(), fake_email()
        user = OSFUser.create_unconfirmed(
            username=email, password='foobar', fullname=name
        )
        assert user.is_registered is False
        assert len(user.email_verifications.keys()) == 1
        assert user.emails.count() == 0, 'primary email has not been added to emails list'

    def test_create_unconfirmed_with_campaign(self):
        name, email = fake.name(), fake_email()
        user = OSFUser.create_unconfirmed(
            username=email, password='foobar', fullname=name,
            campaign='institution'
        )
        assert 'institution_campaign' in user.system_tags

    def test_create_unconfirmed_from_external_service(self):
        name, email = fake.name(), fake_email()
        external_identity = {
            'ORCID': {
                fake.ean(): 'CREATE'
            }
        }
        user = OSFUser.create_unconfirmed(
            username=email,
            password=str(fake.password()),
            fullname=name,
            external_identity=external_identity,
        )
        user.save()
        assert user.is_registered is False
        assert len(user.email_verifications.keys()) == 1
        assert user.email_verifications.popitem()[1]['external_identity'] == external_identity
        assert user.emails.count() == 0, 'primary email has not been added to emails list'

    def test_create_confirmed(self):
        name, email = fake.name(), fake_email()
        user = OSFUser.create_confirmed(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert user.is_registered is True
        assert user.date_registered == user.date_confirmed

    def test_update_guessed_names(self):
        name = fake.name()
        u = OSFUser(fullname=name)
        u.update_guessed_names()

        parsed = impute_names_model(name)
        assert u.fullname == name
        assert u.given_name == parsed['given_name']
        assert u.middle_names == parsed['middle_names']
        assert u.family_name == parsed['family_name']
        assert u.suffix == parsed['suffix']

    def test_create_unregistered(self):
        name, email = fake.name(), fake_email()
        u = OSFUser.create_unregistered(email=email,
                                     fullname=name)
        # TODO: Remove post-migration
        u.date_registered = timezone.now()
        u.save()
        assert u.username == email
        assert u.is_registered is False
        assert u.is_invited is True
        assert not u.emails.filter(address=email).exists()
        parsed = impute_names_model(name)
        assert u.given_name == parsed['given_name']

    @mock.patch('osf.models.user.OSFUser.update_search')
    def test_search_not_updated_for_unreg_users(self, update_search):
        u = OSFUser.create_unregistered(fullname=fake.name(), email=fake_email())
        # TODO: Remove post-migration
        u.date_registered = timezone.now()
        u.save()
        assert not update_search.called

    @mock.patch('osf.models.OSFUser.update_search')
    def test_search_updated_for_registered_users(self, update_search):
        UserFactory(is_registered=True)
        assert update_search.called

    def test_create_unregistered_raises_error_if_already_in_db(self):
        u = UnregUserFactory()
        dupe = OSFUser.create_unregistered(fullname=fake.name(), email=u.username)
        with pytest.raises(ValidationError):
            dupe.save()

    def test_merged_user_is_not_active(self):
        master = UserFactory()
        dupe = UserFactory(merged_by=master)
        assert dupe.is_active is False

    def test_non_registered_user_is_not_active(self):
        u = OSFUser(username=fake_email(),
                 fullname='Freddie Mercury',
                 is_registered=False)
        u.set_password('killerqueen')
        u.save()
        assert u.is_active is False

    def test_user_with_no_password_is_invalid(self):
        u = OSFUser(
            username=fake_email(),
            fullname='Freddie Mercury',
            is_registered=True,
        )
        with pytest.raises(ValidationError):
            u.save()

    def test_merged_user_with_two_account_on_same_project_with_different_visibility_and_permissions(self, user):
        user2 = UserFactory.build()
        user2.save()

        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(user2, log=False)
        project.add_contributor(user, log=False)
        project.set_permissions(user=user, permissions=permissions.READ)
        project.set_permissions(user=user2, permissions=permissions.ADMIN)
        project.set_visible(user=user, visible=False)
        project.set_visible(user=user2, visible=True)
        project.save()
        user.merge_user(user2)
        user.save()
        project.reload()

        assert project.has_permission(user, permissions.ADMIN) is True
        assert project.get_visible(user) is True
        assert project.is_contributor(user2) is False

    def test_merged_user_group_member_permissions_are_ignored(self, user):
        user2 = UserFactory.build()
        user2.save()
        group = OSFGroupFactory(creator=user2)

        project = ProjectFactory(is_public=True)
        project.add_osf_group(group, permissions.ADMIN)
        assert project.has_permission(user2, permissions.ADMIN)
        # Both the master and dupe are contributors
        project.add_contributor(user2, log=False)
        project.add_contributor(user, log=False)
        project.set_permissions(user=user, permissions=permissions.READ)
        project.set_permissions(user=user2, permissions=permissions.WRITE)
        project.save()
        user.merge_user(user2)
        user.save()
        project.reload()

        assert project.has_permission(user, permissions.ADMIN) is True
        assert project.is_admin_contributor(user) is False
        assert project.is_contributor(user2) is False
        assert group.is_member(user) is True
        assert group.is_member(user2) is False

    def test_merge_projects(self):
        user = AuthUserFactory()
        user2 = AuthUserFactory()

        project_one = ProjectFactory(creator=user, title='project_one')

        project_two = ProjectFactory(title='project_two')
        project_two.add_contributor(user2)

        project_three = ProjectFactory(title='project_three', creator=user2)
        project_three.add_contributor(user, visible=False)

        project_four = ProjectFactory(title='project_four')
        project_four.add_contributor(user2, permissions=permissions.READ, visible=False)

        project_five = ProjectFactory(title='project_five')
        project_five.add_contributor(user2, permissions=permissions.READ, visible=False)
        project_five.add_contributor(user, permissions=permissions.WRITE, visible=True)

        # two projects shared b/t user and user2
        assert user.nodes.filter(type='osf.node').count() == 3
        assert user2.nodes.filter(type='osf.node').count() == 4

        user.merge_user(user2)
        project_one.reload()
        project_two.reload()
        project_three.reload()
        project_four.reload()
        project_five.reload()

        assert user.nodes.filter(type='osf.node').count() == 5
        # one group for each node
        assert user.groups.count() == 6  # (including quickfiles node)
        assert user2.nodes.filter(type='osf.node').count() == 0
        assert user2.groups.count() == 1  # (quickfilesnode)

        contrib_obj = Contributor.objects.get(user=user, node=project_one)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.ADMIN
        assert project_one.creator == user
        assert not project_one.has_permission(user2, permissions.READ)
        assert not project_one.is_contributor(user2)

        contrib_obj = Contributor.objects.get(user=user, node=project_two)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.WRITE
        assert project_two.creator != user
        assert not project_two.has_permission(user2, permissions.READ)
        assert not project_two.is_contributor(user2)

        contrib_obj = Contributor.objects.get(user=user, node=project_three)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.ADMIN  # of the two users the highest perm wins out.
        assert project_three.creator == user
        assert not project_three.has_permission(user2, permissions.READ)
        assert not project_three.is_contributor(user2)

        contrib_obj = Contributor.objects.get(user=user, node=project_four)
        assert contrib_obj.visible is False
        assert contrib_obj.permission == permissions.READ
        assert project_four.creator != user
        assert not project_four.has_permission(user2, permissions.READ)
        assert not project_four.is_contributor(user2)

        contrib_obj = Contributor.objects.get(user=user, node=project_five)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.WRITE
        assert project_five.creator != user
        assert not project_five.has_permission(user2, permissions.READ)
        assert not project_five.is_contributor(user2)

    def test_merge_preprints(self, user):
        user2 = AuthUserFactory()

        preprint_one = PreprintFactory(creator=user, title='preprint_one')

        preprint_two = PreprintFactory(title='preprint_two')
        preprint_two.add_contributor(user2)

        preprint_three = PreprintFactory(title='preprint_three', creator=user2)
        preprint_three.add_contributor(user, visible=False)

        preprint_four = PreprintFactory(title='preprint_four')
        preprint_four.add_contributor(user2, permissions=permissions.READ, visible=False)

        preprint_five = PreprintFactory(title='preprint_five')
        preprint_five.add_contributor(user2, permissions=permissions.READ, visible=False)
        preprint_five.add_contributor(user, permissions=permissions.WRITE, visible=True)

        # two preprints shared b/t user and user2
        assert user.preprints.count() == 3
        assert user2.preprints.count() == 4

        user.merge_user(user2)
        preprint_one.reload()
        preprint_two.reload()
        preprint_three.reload()
        preprint_four.reload()
        preprint_five.reload()

        assert user.preprints.count() == 5
        # one group for each preprint
        assert user.groups.filter(name__icontains='preprint').count() == 5
        assert user2.preprints.count() == 0
        assert not user2.groups.filter(name__icontains='preprint').all()

        contrib_obj = PreprintContributor.objects.get(user=user, preprint=preprint_one)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.ADMIN
        assert preprint_one.creator == user
        assert not preprint_one.has_permission(user2, permissions.READ)
        assert not preprint_one.is_contributor(user2)

        contrib_obj = PreprintContributor.objects.get(user=user, preprint=preprint_two)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.WRITE
        assert preprint_two.creator != user
        assert not preprint_two.has_permission(user2, permissions.READ)
        assert not preprint_two.is_contributor(user2)

        contrib_obj = PreprintContributor.objects.get(user=user, preprint=preprint_three)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.ADMIN  # of the two users the highest perm wins out.
        assert preprint_three.creator == user
        assert not preprint_three.has_permission(user2, permissions.READ)
        assert not preprint_three.is_contributor(user2)

        contrib_obj = PreprintContributor.objects.get(user=user, preprint=preprint_four)
        assert contrib_obj.visible is False
        assert contrib_obj.permission == permissions.READ
        assert preprint_four.creator != user
        assert not preprint_four.has_permission(user2, permissions.READ)
        assert not preprint_four.is_contributor(user2)

        contrib_obj = PreprintContributor.objects.get(user=user, preprint=preprint_five)
        assert contrib_obj.visible is True
        assert contrib_obj.permission == permissions.WRITE
        assert preprint_five.creator != user
        assert not preprint_five.has_permission(user2, permissions.READ)
        assert not preprint_five.is_contributor(user2)

    def test_cant_create_user_without_username(self):
        u = OSFUser()  # No username given
        with pytest.raises(ValidationError):
            u.save()

    def test_date_registered_upon_saving(self):
        u = OSFUser(username=fake_email(), fullname='Foo bar')
        u.set_unusable_password()
        u.save()
        assert bool(u.date_registered) is True
        assert u.date_registered.tzinfo == pytz.utc

    def test_cant_create_user_without_full_name(self):
        u = OSFUser(username=fake_email())
        with pytest.raises(ValidationError):
            u.save()

    def test_add_blacklisted_domain_unconfirmed_email(self, user):
        BlacklistedEmailDomain.objects.get_or_create(domain='mailinator.com')
        with pytest.raises(BlacklistedEmailError) as e:
            user.add_unconfirmed_email('kanye@mailinator.com')
        assert str(e.value) == 'Invalid Email'

    @mock.patch('website.security.random_string')
    def test_get_confirmation_url_for_external_service(self, random_string):
        random_string.return_value = 'abcde'
        u = UnconfirmedUserFactory()
        assert (u.get_confirmation_url(u.username, external_id_provider='service', destination='dashboard') ==
                '{0}confirm/external/{1}/{2}/?destination={3}'.format(settings.DOMAIN, u._id, 'abcde', 'dashboard'))

    @mock.patch('website.security.random_string')
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
        expiration = timezone.now() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token('foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_token_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = timezone.now() - dt.timedelta(seconds=1)
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

        email = fake_email()
        u.add_unconfirmed_email(email)
        # manually remove 'expiration' key
        token = u.get_confirmation_token(email)
        del u.email_verifications[token]['expiration']
        u.save()

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_token(email)

    @mock.patch('website.security.random_string')
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
        expiration = timezone.now() - dt.timedelta(seconds=1)
        u.add_unconfirmed_email('foo@bar.com', expiration=expiration)

        with pytest.raises(ExpiredTokenError):
            u.get_confirmation_url('foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_url_when_token_is_expired_force(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        # Make sure token is already expired
        expiration = timezone.now() - dt.timedelta(seconds=1)
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
        assert u.emails.filter(address=u.username).exists()
        assert bool(u.is_registered) is True

    def test_confirm_email(self, user):
        token = user.add_unconfirmed_email('foo@bar.com')
        user.confirm_email(token)

        assert 'foo@bar.com' not in user.unconfirmed_emails
        assert user.emails.filter(address='foo@bar.com').exists()

    def test_confirm_email_merge_select_for_update(self, user):
        mergee = UserFactory(username='foo@bar.com')
        token = user.add_unconfirmed_email('foo@bar.com')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user

        for_update_sql = connection.ops.for_update_sql()
        assert any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    @mock.patch('osf.utils.requests.settings.SELECT_FOR_UPDATE_ENABLED', False)
    def test_confirm_email_merge_select_for_update_disabled(self, user):
        mergee = UserFactory(username='foo@bar.com')
        token = user.add_unconfirmed_email('foo@bar.com')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user

        for_update_sql = connection.ops.for_update_sql()
        assert not any(for_update_sql in query['sql'] for query in ctx.captured_queries)

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
        manual_expiration = timezone.now() - dt.timedelta(0, 10)
        u.email_verifications[valid_token]['expiration'] = manual_expiration

        with pytest.raises(ExpiredTokenError):
            u.get_unconfirmed_email_for_token(valid_token)

    def test_verify_confirmation_token_when_token_has_no_expiration(self):
        # A user verification token may not have an expiration
        email = fake_email()
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
            urljoin(settings.DOMAIN, '/{0}/'.format(user._id))
        )

    def test_profile_image_url(self, user):
        expected = filters.profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                         user,
                                         use_ssl=True,
                                         size=settings.PROFILE_IMAGE_MEDIUM)
        assert user.profile_image_url(settings.PROFILE_IMAGE_MEDIUM) == expected

    def test_set_unusable_username_for_unsaved_user(self):
        user = UserFactory.build()
        user.set_unusable_username()
        assert user.username is not None
        user.save()
        assert user.has_usable_username() is False

    def test_set_unusable_username_for_saved_user(self):
        user = UserFactory()
        user.set_unusable_username()
        assert user.username == user._id

    def test_has_usable_username(self):
        user = UserFactory()
        assert user.has_usable_username() is True
        user.username = user._id
        assert user.has_usable_username() is False

    def test_profile_image_url_has_no_default_size(self, user):
        expected = filters.profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                         user,
                                         use_ssl=True)
        assert user.profile_image_url() == expected
        size = parse_qs(urlparse(user.profile_image_url()).query).get('size')
        assert size is None

    def test_activity_points(self, user):
        assert(
            user.get_activity_points() == get_total_activity_count(user._primary_key)
        )

    def test_contributed_property(self):
        user = UserFactory()
        node = NodeFactory()
        node2 = NodeFactory()
        # TODO: Use Node.add_contributor when it's implemented
        Contributor.objects.create(user=user, node=node)
        projects_contributed_to = AbstractNode.objects.filter(_contributors=user)
        assert list(user.contributed) == list(projects_contributed_to)
        assert node2 not in user.contributed

    # copied from tests/test_views.py
    def test_clean_email_verifications(self, user):
        # Do not return bad token and removes it from user.email_verifications
        email = 'test@example.com'
        token = 'blahblahblah'
        user.email_verifications[token] = {'expiration': (timezone.now() + dt.timedelta(days=1)),
                                                'email': email,
                                                'confirmed': False}
        user.save()
        assert user.email_verifications[token]['email'] == email
        user.clean_email_verifications(given_token=token)
        unconfirmed_emails = user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert user.email_verifications == {}

    def test_display_full_name_registered(self):
        u = UserFactory()
        assert u.display_full_name() == u.fullname

    def test_display_full_name_unregistered(self):
        name = fake.name()
        u = UnregUserFactory()
        project = NodeFactory()
        project.add_unregistered_contributor(
            fullname=name, email=u.username,
            auth=Auth(project.creator)
        )
        project.save()
        u.reload()
        assert u.display_full_name(node=project) == name

    def test_repeat_add_same_unreg_user_with_diff_name(self):
        unreg_user = UnregUserFactory()
        project = NodeFactory()
        old_name = unreg_user.fullname
        project.add_unregistered_contributor(
            fullname=old_name, email=unreg_user.username,
            auth=Auth(project.creator)
        )
        project.save()
        unreg_user.reload()
        name_list = [contrib.fullname for contrib in project.contributors]
        assert unreg_user.fullname in name_list
        project.remove_contributor(contributor=unreg_user, auth=Auth(project.creator))
        project.save()
        project.reload()
        assert unreg_user not in project.contributors
        new_name = fake.name()
        project.add_unregistered_contributor(
            fullname=new_name, email=unreg_user.username,
            auth=Auth(project.creator)
        )
        project.save()
        unreg_user.reload()
        project.reload()
        unregistered_name = unreg_user.unclaimed_records[project._id].get('name', None)
        assert new_name == unregistered_name

    def test_username_is_automatically_lowercased(self):
        user = UserFactory(username='nEoNiCon@bet.com')
        assert user.username == 'neonicon@bet.com'

    def test_update_affiliated_institutions_by_email_domains(self):
        institution = InstitutionFactory()
        email_domain = institution.email_domains[0]

        user_email = '{}@{}'.format(fake.domain_word(), email_domain)
        user = UserFactory(username=user_email)
        user.update_affiliated_institutions_by_email_domain()

        assert user.affiliated_institutions.count() == 1
        assert user.is_affiliated_with_institution(institution) is True

        user.update_affiliated_institutions_by_email_domain()

        assert user.affiliated_institutions.count() == 1

    def test_is_affiliated_with_institution(self, user):
        institution1, institution2 = InstitutionFactory(), InstitutionFactory()

        user.affiliated_institutions.add(institution1)
        user.save()

        assert user.is_affiliated_with_institution(institution1) is True
        assert user.is_affiliated_with_institution(institution2) is False

    def test_has_osfstorage_usersettings(self, user):
        addon = user.get_addon('osfstorage')
        default_region = Region.objects.get(_id=DEFAULT_REGION_ID)

        assert addon
        assert addon.default_region == default_region

class TestProjectsInCommon:

    def test_get_projects_in_common(self, user, auth):
        user2 = UserFactory()
        project = NodeFactory(creator=user)
        project.add_contributor(contributor=user2, auth=auth)
        project.save()

        group = OSFGroupFactory(creator=user, name='Platform')
        group.make_member(user2)
        group_project = ProjectFactory()
        group_project.add_osf_group(group)
        group_project.save()

        project_keys = set([node._id for node in user.all_nodes])
        projects = set(user.all_nodes)
        user2_project_keys = set([node._id for node in user2.all_nodes])

        assert set(n._id for n in user.get_projects_in_common(user2)) == project_keys.intersection(user2_project_keys)
        assert user.get_projects_in_common(user2) == projects.intersection(user2.all_nodes)

    def test_n_projects_in_common(self, user, auth):
        user2 = UserFactory()
        user3 = UserFactory()
        project = NodeFactory(creator=user)

        project.add_contributor(contributor=user2, auth=auth)
        project.save()

        group = OSFGroupFactory(name='Platform', creator=user)
        group.make_member(user3)
        project.add_osf_group(group)
        project.save()

        assert user.n_projects_in_common(user2) == 1
        assert user.n_projects_in_common(user3) == 1


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
            Session.objects.filter(data__auth_user_id=user._id).count() == 0
        )

        cookie = user.get_or_create_cookie(super_secret_key)

        session = Session.objects.filter(data__auth_user_id=user._id).first()

        assert session._id == signer.unsign(cookie)
        assert session.data['auth_user_id'] == user._id
        assert session.data['auth_user_username'] == user.username
        assert session.data['auth_user_fullname'] == user.fullname

    def test_get_user_by_cookie(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        assert user == OSFUser.from_cookie(cookie)

    def test_get_user_by_cookie_returns_none(self):
        assert OSFUser.from_cookie('') is None

    def test_get_user_by_cookie_bad_cookie(self):
        assert OSFUser.from_cookie('foobar') is None

    def test_get_user_by_cookie_no_user_id(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        session = Session.objects.get(data__auth_user_id=user._id)
        del session.data['auth_user_id']
        session.save()
        assert OSFUser.from_cookie(cookie) is None

    def test_get_user_by_cookie_no_session(self):
        user = UserFactory()
        cookie = user.get_or_create_cookie()
        Session.objects.all().delete()
        assert OSFUser.from_cookie(cookie) is None


class TestChangePassword:

    def test_change_password(self, user):
        old_password = 'password'
        new_password = 'new password'
        confirm_password = new_password
        user.set_password(old_password)
        user.save()
        user.change_password(old_password, new_password, confirm_password)
        assert bool(user.check_password(new_password)) is True

    @mock.patch('website.mails.send_mail')
    def test_set_password_notify_default(self, mock_send_mail, user):
        old_password = 'password'
        user.set_password(old_password)
        user.save()
        assert mock_send_mail.called is True

    @mock.patch('website.mails.send_mail')
    def test_set_password_no_notify(self, mock_send_mail, user):
        old_password = 'password'
        user.set_password(old_password, notify=False)
        user.save()
        assert mock_send_mail.called is False

    @mock.patch('website.mails.send_mail')
    def test_check_password_upgrade_hasher_no_notify(self, mock_send_mail, user, settings):
        # NOTE: settings fixture comes from pytest-django.
        # changes get reverted after tests run
        settings.PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.MD5PasswordHasher',
            'django.contrib.auth.hashers.SHA1PasswordHasher',
        )
        raw_password = 'password'
        user.password = 'sha1$lNb72DKWDv6P$e6ae16dada9303ae0084e14fc96659da4332bb05'
        user.check_password(raw_password)
        assert user.password.startswith('md5$')
        assert mock_send_mail.called is False

    def test_change_password_invalid(self, old_password=None, new_password=None, confirm_password=None,
                                     error_message='Old password is invalid'):
        user = UserFactory()
        user.set_password('password')
        user.save()
        with pytest.raises(ChangePasswordError) as excinfo:
            user.change_password(old_password, new_password, confirm_password)
            user.save()
        assert error_message in str(excinfo)
        assert bool(user.check_password(new_password)) is False

    def test_change_password_invalid_old_password(self):
        self.test_change_password_invalid(
            'invalid old password',
            'new password',
            'new password',
            'Old password is invalid',
        )

    def test_change_password_invalid_too_short(self):
        self.test_change_password_invalid(
            'password',
            '12345',
            '12345',
            'Password should be at least eight characters',
        )

    def test_change_password_invalid_too_long(self):
        too_long = 'X' * 257
        self.test_change_password_invalid(
            'password',
            too_long,
            too_long,
            'Password should not be longer than 256 characters',
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


class TestIsActive:

    @pytest.fixture()
    def make_user(self):
        def func(**attrs):
            # By default, return an active user
            user = UserFactory.build(
                is_registered=True,
                merged_by=None,
                is_disabled=False,
                date_confirmed=timezone.now(),
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

    def test_user_with_unusable_password_but_verified_orcid_is_active(self, make_user):
        user = make_user()
        user.set_unusable_password()
        user.save()
        assert user.is_active is False
        user.external_identity = {'ORCID': {'fake-orcid': 'VERIFIED'}}
        user.save()
        assert user.is_active is True

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
        user = make_user(date_disabled=timezone.now())
        user.save()
        assert user.is_active is False


class TestAddUnconfirmedEmail:

    @mock.patch('website.security.random_string')
    def test_add_unconfirmed_email(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        assert len(u.email_verifications.keys()) == 0
        u.add_unconfirmed_email('foo@bar.com')
        assert len(u.email_verifications.keys()) == 1
        assert u.email_verifications[token]['email'] == 'foo@bar.com'

    @mock.patch('website.security.random_string')
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

class TestUnregisteredUser:

    @pytest.fixture()
    def referrer(self):
        return UserFactory()

    @pytest.fixture()
    def email(self):
        return fake_email()

    @pytest.fixture()
    def unreg_user(self, referrer, project, email):
        user = UnregUserFactory()
        given_name = 'Fredd Merkury'
        user.add_unclaimed_record(project,
            given_name=given_name, referrer=referrer,
            email=email)
        user.save()
        return user

    @pytest.fixture()
    def provider(self, referrer):
        provider = PreprintProviderFactory()
        provider.add_to_group(referrer, 'moderator')
        provider.save()
        return provider

    @pytest.fixture()
    def unreg_moderator(self, referrer, provider, email):
        user = UnregUserFactory()
        given_name = 'Freddie Merkkury'
        user.add_unclaimed_record(provider,
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

    def test_add_unclaimed_record(self, unreg_user, unreg_moderator, email, referrer, provider, project):
        # test_unreg_contrib
        data = unreg_user.unclaimed_records[project._primary_key]
        assert data['name'] == 'Fredd Merkury'
        assert data['referrer_id'] == referrer._id
        assert 'token' in data
        assert data['email'] == email
        assert data == unreg_user.get_unclaimed_record(project._primary_key)

        # test_unreg_moderator
        data = unreg_moderator.unclaimed_records[provider._id]
        assert data['name'] == 'Freddie Merkkury'
        assert data['referrer_id'] == referrer._id
        assert 'token' in data
        assert data['email'] == email
        assert data == unreg_moderator.get_unclaimed_record(provider._id)

    def test_get_claim_url(self, unreg_user, unreg_moderator, project, provider):
        # test_unreg_contrib
        uid = unreg_user._primary_key
        pid = project._primary_key
        token = unreg_user.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert (
            unreg_user.get_claim_url(pid, external=True) ==
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals())
        )

        # test_unreg_moderator
        uid = unreg_moderator._id
        pid = provider._id
        token = unreg_moderator.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert (
            unreg_moderator.get_claim_url(pid, external=True) ==
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals())
        )

    def test_get_claim_url_raises_value_error_if_not_valid_pid(self, unreg_user, unreg_moderator):
        with pytest.raises(ValueError):
            unreg_user.get_claim_url('invalidinput')
            unreg_moderator.get_claim_url('invalidinput')

    def test_cant_add_unclaimed_record_if_referrer_has_no_permissions(self, referrer, unreg_moderator, unreg_user, provider):
        # test_referrer_is_not_contrib
        project = NodeFactory()
        with pytest.raises(PermissionsError) as e:
            unreg_user.add_unclaimed_record(project,
                given_name='fred m', referrer=referrer)
            unreg_user.save()
        assert str(e.value) == 'Referrer does not have permission to add a contributor to {}'.format(project._primary_key)

        # test_referrer_is_not_admin_or_moderator
        referrer = UserFactory()
        with pytest.raises(PermissionsError) as e:
            unreg_moderator.add_unclaimed_record(provider,
                given_name='hodor', referrer=referrer)
            unreg_user.save()
        assert str(e.value) == 'Referrer does not have permission to add a moderator to provider {}'.format(provider._id)

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    @mock.patch('osf.models.OSFUser.update_search')
    def test_register(self, mock_search, mock_search_nodes):
        user = UnregUserFactory()
        assert user.is_registered is False  # sanity check
        email = fake_email()
        user.register(username=email, password='killerqueen')
        user.save()
        assert user.is_registered is True
        assert user.check_password('killerqueen') is True
        assert user.username == email

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    @mock.patch('osf.models.OSFUser.update_search')
    def test_registering_with_a_different_email_adds_to_emails_list(self, mock_search, mock_search_nodes):
        user = UnregUserFactory()
        assert user.has_usable_password() is False  # sanity check
        email = fake_email()
        user.register(username=email, password='killerqueen')
        assert user.emails.filter(address=email).exists()

    def test_verify_claim_token(self, unreg_user, unreg_moderator, project, provider):
        # test_unreg_contrib
        valid = unreg_user.get_unclaimed_record(project._primary_key)['token']
        assert bool(unreg_user.verify_claim_token(valid, project_id=project._primary_key)) is True
        assert bool(unreg_user.verify_claim_token('invalidtoken', project_id=project._primary_key)) is False

        # test_unreg_moderator
        valid = unreg_moderator.get_unclaimed_record(provider._id)['token']
        assert bool(unreg_moderator.verify_claim_token(valid, project_id=provider._id)) is True
        assert bool(unreg_moderator.verify_claim_token('invalidtoken', project_id=provider._id)) is False

    def test_verify_claim_token_with_no_expiration_date(self, unreg_user, project):
        # Legacy records may not have an 'expires' key
        #self.add_unclaimed_record()
        record = unreg_user.get_unclaimed_record(project._primary_key)
        del record['expires']
        unreg_user.save()
        token = record['token']
        assert unreg_user.verify_claim_token(token, project_id=project._primary_key) is True


# Copied from tests/test_models.py
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
class TestTagging:
    def test_add_system_tag(self, user):
        tag_name = fake.word()
        user.add_system_tag(tag_name)
        user.save()

        assert len(user.system_tags) == 1

        tag = Tag.all_tags.get(name=tag_name, system=True)
        assert tag in user.all_tags.all()

    def test_add_system_tag_instance(self, user):
        tag = TagFactory(system=True)
        user.add_system_tag(tag)
        assert tag in user.all_tags.all()

    def test_add_system_tag_with_non_system_instance(self, user):
        tag = TagFactory(system=False)
        with pytest.raises(ValueError):
            user.add_system_tag(tag)
        assert tag not in user.all_tags.all()

    def test_tags_get_lowercased(self, user):
        tag_name = 'NeOn'
        user.add_system_tag(tag_name)
        user.save()

        tag = Tag.all_tags.get(name=tag_name.lower(), system=True)
        assert tag in user.all_tags.all()

    def test_system_tags_property(self, user):
        tag_name = fake.word()
        user.add_system_tag(tag_name)

        assert tag_name.lower() in user.system_tags

class TestCitationProperties:

    @pytest.fixture()
    def referrer(self):
        return UserFactory()

    @pytest.fixture()
    def email(self):
        return fake_email()

    @pytest.fixture()
    def unreg_user(self, referrer, project, email):
        user = UnregUserFactory()
        user.add_unclaimed_record(project,
            given_name=user.fullname, referrer=referrer,
            email=email)
        user.save()
        return user

    @pytest.fixture()
    def project(self, referrer):
        return NodeFactory(creator=referrer)

    def test_registered_user_csl(self, user):
        # Tests the csl name for a registered user
        if user.is_registered:
            assert bool(
                user.csl_name() ==
                {
                    'given': user.csl_given_name,
                    'family': user.family_name,
                }
            )

    def test_unregistered_user_csl(self, unreg_user, project):
        # Tests the csl name for an unregistered user
        name = unreg_user.unclaimed_records[project._primary_key]['name'].split(' ')
        family_name = name[-1]
        given_name = ' '.join(name[:-1])
        assert bool(
            unreg_user.csl_name(project._id) ==
            {
                'given': given_name,
                'family': family_name,
            }
        )

# copied from tests/test_models.py
@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestMergingUsers:

    @pytest.yield_fixture()
    def email_subscriptions_enabled(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True
        yield
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False

    @pytest.fixture()
    def master(self):
        return UserFactory(
            fullname='Joe Shmo',
            is_registered=True,
            emails=['joe@mail.com'],
        )

    @pytest.fixture()
    def dupe(self):
        return UserFactory(
            fullname='Joseph Shmo',
            emails=['joseph123@hotmail.com']
        )

    @pytest.fixture()
    def merge_dupe(self, master, dupe):
        def f():
            """Do the actual merge."""
            master.merge_user(dupe)
            master.save()
        return f

    def test_bookmark_collection_nodes_arent_merged(self, dupe, master, merge_dupe):
        dashnode = find_bookmark_collection(dupe)
        assert dupe.collection_set.filter(id=dashnode.id).exists()
        merge_dupe()
        assert not master.collection_set.filter(id=dashnode.id).exists()

    # Note the files are merged, but the actual node stays with the dupe user
    def test_quickfiles_node_arent_merged(self, dupe, master, merge_dupe):
        assert master.nodes.filter(type='osf.quickfilesnode').count() == 1
        assert dupe.nodes.filter(type='osf.quickfilesnode').count() == 1

        merge_dupe()
        master.refresh_from_db()
        dupe.refresh_from_db()
        assert master.nodes.filter(type='osf.quickfilesnode').count() == 1
        assert dupe.nodes.filter(type='osf.quickfilesnode').count() == 1

    def test_dupe_is_merged(self, dupe, master, merge_dupe):
        merge_dupe()
        assert dupe.is_merged
        assert dupe.merged_by == master

    def test_dupe_email_is_appended(self, master, merge_dupe):
        merge_dupe()
        assert master.emails.filter(address='joseph123@hotmail.com').exists()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_send_user_merged_signal(self, mock_get_mailchimp_api, dupe, merge_dupe):
        dupe.mailchimp_mailing_lists['foo'] = True
        dupe.save()

        with capture_signals() as mock_signals:
            merge_dupe()
            assert mock_signals.signals_sent() == set([user_merged])

    @pytest.mark.enable_enqueue_task
    @mock.patch('website.mailchimp_utils.unsubscribe_mailchimp_async')
    def test_merged_user_unsubscribed_from_mailing_lists(self, mock_unsubscribe, dupe, merge_dupe, email_subscriptions_enabled):
        list_name = 'foo'
        dupe.mailchimp_mailing_lists[list_name] = True
        dupe.save()
        merge_dupe()
        assert mock_unsubscribe.called

    def test_inherits_projects_contributed_by_dupe(self, dupe, master, merge_dupe):
        project = ProjectFactory()
        project.add_contributor(dupe)
        project.save()
        merge_dupe()
        project.reload()
        assert project.is_contributor(master) is True
        assert project.is_contributor(dupe) is False

    def test_inherits_projects_created_by_dupe(self, dupe, master, merge_dupe):
        project = ProjectFactory(creator=dupe)
        merge_dupe()
        project.reload()
        assert project.creator == master

    def test_adding_merged_user_as_contributor_adds_master(self, dupe, master, merge_dupe):
        project = ProjectFactory(creator=UserFactory())
        merge_dupe()
        project.add_contributor(contributor=dupe)
        assert project.is_contributor(master) is True
        assert project.is_contributor(dupe) is False

    def test_merging_dupe_who_is_contributor_on_same_projects(self, master, dupe, merge_dupe):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=master, visible=True)
        project.add_contributor(contributor=dupe, visible=True)
        project.save()
        merge_dupe()  # perform the merge
        project.reload()
        assert project.is_contributor(master)
        assert project.is_contributor(dupe) is False
        assert len(project.contributors) == 2   # creator and master are the only contribs
        assert project.contributor_set.get(user=master).visible is True

    def test_merging_dupe_who_has_different_visibility_from_master(self, master, dupe, merge_dupe):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=master, visible=False)
        project.add_contributor(contributor=dupe, visible=True)

        project.save()
        merge_dupe()  # perform the merge
        project.reload()

        assert project.contributor_set.get(user=master).visible is True

    def test_merging_dupe_who_is_a_non_bib_contrib_and_so_is_the_master(self, master, dupe, merge_dupe):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=master, visible=False)
        project.add_contributor(contributor=dupe, visible=False)

        project.save()
        merge_dupe()  # perform the merge
        project.reload()

        assert project.contributor_set.get(user=master).visible is False

    def test_merge_user_with_higher_permissions_on_project(self, master, dupe, merge_dupe):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=master, permissions=permissions.WRITE)
        project.add_contributor(contributor=dupe, permissions=permissions.ADMIN)

        project.save()
        merge_dupe()  # perform the merge

        assert project.get_permissions(master) == [permissions.READ, permissions.WRITE, permissions.ADMIN]

    def test_merge_user_with_lower_permissions_on_project(self, master, dupe, merge_dupe):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=master, permissions=permissions.ADMIN)
        project.add_contributor(contributor=dupe, permissions=permissions.WRITE)

        project.save()
        merge_dupe()  # perform the merge

        assert project.get_permissions(master) == [permissions.READ, permissions.WRITE, permissions.ADMIN]

    def test_merge_user_into_self_fails(self, master):
        with pytest.raises(ValueError):
            master.merge_user(master)


class TestDisablingUsers(OsfTestCase):
    def setUp(self):
        super(TestDisablingUsers, self).setUp()
        self.user = UserFactory()

    def test_user_enabled_by_default(self):
        assert self.user.is_disabled is False

    def test_disabled_user(self):
        """Ensure disabling a user sets date_disabled"""
        self.user.is_disabled = True
        self.user.save()

        assert isinstance(self.user.date_disabled, dt.datetime)
        assert self.user.is_disabled is True
        assert self.user.is_active is False

    def test_reenabled_user(self):
        """Ensure restoring a disabled user unsets date_disabled"""
        self.user.is_disabled = True
        self.user.save()

        self.user.is_disabled = False
        self.user.save()

        assert self.user.date_disabled is None
        assert self.user.is_disabled is False
        assert self.user.is_active is True

    def test_is_disabled_idempotency(self):
        self.user.is_disabled = True
        self.user.save()

        old_date_disabled = self.user.date_disabled

        self.user.is_disabled = True
        self.user.save()

        new_date_disabled = self.user.date_disabled

        assert new_date_disabled == old_date_disabled

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_disable_account_and_remove_sessions(self, mock_mail):
        session1 = SessionFactory(user=self.user, created=(timezone.now() - dt.timedelta(seconds=settings.OSF_SESSION_TIMEOUT)))
        session2 = SessionFactory(user=self.user, created=(timezone.now() - dt.timedelta(seconds=settings.OSF_SESSION_TIMEOUT)))

        self.user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST] = True
        self.user.save()
        self.user.disable_account()

        assert self.user.is_disabled is True
        assert isinstance(self.user.date_disabled, dt.datetime)
        assert self.user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST] is False

        assert not Session.load(session1._id)
        assert not Session.load(session2._id)

    def test_disable_account_api(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True
        with pytest.raises(mailchimp_utils.mailchimp.InvalidApiKeyError):
            self.user.disable_account()

# Copied from tests/modes/test_user.py
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_bookmark_creation
class TestUser(OsfTestCase):
    def setUp(self):
        super(TestUser, self).setUp()
        self.user = AuthUserFactory()

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2454
    def test_add_unconfirmed_email_when_email_verifications_is_empty(self):
        self.user.email_verifications = []
        self.user.save()
        email = fake_email()
        self.user.add_unconfirmed_email(email)
        self.user.save()
        assert email in self.user.unconfirmed_emails

    def test_unconfirmed_emails(self):
        assert self.user.unconfirmed_emails == []
        self.user.add_unconfirmed_email('foo@bar.com')
        assert self.user.unconfirmed_emails == ['foo@bar.com']

        # email_verifications field may NOT be None
        self.user.email_verifications = []
        self.user.save()
        assert self.user.unconfirmed_emails == []

    def test_unconfirmed_emails_unregistered_user(self):
        assert UnregUserFactory().unconfirmed_emails == []

    def test_unconfirmed_emails_unconfirmed_user(self):
        user = UnconfirmedUserFactory()

        assert user.unconfirmed_emails == [user.username]

    # regression test for https://sentry.cos.io/sentry/osf/issues/6510/
    def test_unconfirmed_email_info_when_email_verifications_is_empty(self):
        user = UserFactory()
        user.email_verifications = []
        assert user.unconfirmed_email_info == []

    def test_remove_unconfirmed_email(self):
        self.user.add_unconfirmed_email('foo@bar.com')
        self.user.save()

        assert 'foo@bar.com' in self.user.unconfirmed_emails  # sanity check

        self.user.remove_unconfirmed_email('foo@bar.com')
        self.user.save()

        assert 'foo@bar.com' not in self.user.unconfirmed_emails

    def test_confirm_email(self):
        token = self.user.add_unconfirmed_email('foo@bar.com')
        self.user.confirm_email(token)

        assert 'foo@bar.com' not in self.user.unconfirmed_emails
        assert self.user.emails.filter(address='foo@bar.com').exists()

    def test_confirm_email_comparison_is_case_insensitive(self):
        u = UnconfirmedUserFactory.build(
            username='letsgettacos@lgt.com'
        )
        u.add_unconfirmed_email('LetsGetTacos@LGT.com')
        u.save()
        assert u.is_confirmed is False  # sanity check

        token = u.get_confirmation_token('LetsGetTacos@LGT.com')

        confirmed = u.confirm_email(token)
        assert confirmed is True
        assert u.is_confirmed is True

    def test_cannot_remove_primary_email_from_email_list(self):
        with pytest.raises(PermissionsError) as e:
            self.user.remove_email(self.user.username)
        assert str(e.value) == 'Can\'t remove primary email'

    def test_add_same_unconfirmed_email_twice(self):
        email = 'test@mail.com'
        token1 = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert token1 == self.user.get_confirmation_token(email)
        assert email == self.user.get_unconfirmed_email_for_token(token1)

        token2 = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert token1 != self.user.get_confirmation_token(email)
        assert token2 == self.user.get_confirmation_token(email)
        assert email == self.user.get_unconfirmed_email_for_token(token2)
        with pytest.raises(InvalidTokenError):
            self.user.get_unconfirmed_email_for_token(token1)

    def test_contributed_property(self):
        projects_contributed_to = self.user.nodes.all()
        assert list(self.user.contributed.all()) == list(projects_contributed_to)

    def test_contributor_to_property(self):
        normal_node = ProjectFactory(creator=self.user)
        normal_contributed_node = ProjectFactory()
        normal_contributed_node.add_contributor(self.user)
        normal_contributed_node.save()
        deleted_node = ProjectFactory(creator=self.user, is_deleted=True)
        bookmark_collection_node = find_bookmark_collection(self.user)
        collection_node = CollectionFactory(creator=self.user)
        project_to_be_invisible_on = ProjectFactory()
        project_to_be_invisible_on.add_contributor(self.user, visible=False)
        project_to_be_invisible_on.save()
        group = OSFGroupFactory(creator=self.user, name='Platform')
        group_project = ProjectFactory()
        group_project.add_osf_group(group, permissions.READ)

        contributor_to_nodes = [node._id for node in self.user.contributor_to]

        assert normal_node._id in contributor_to_nodes
        assert normal_contributed_node._id in contributor_to_nodes
        assert project_to_be_invisible_on._id in contributor_to_nodes
        assert deleted_node._id not in contributor_to_nodes
        assert bookmark_collection_node._id not in contributor_to_nodes
        assert collection_node._id not in contributor_to_nodes
        assert group_project._id not in contributor_to_nodes

    def test_contributor_or_group_member_to_property(self):
        normal_node = ProjectFactory(creator=self.user)
        normal_contributed_node = ProjectFactory()
        normal_contributed_node.add_contributor(self.user)
        normal_contributed_node.save()
        deleted_node = ProjectFactory(creator=self.user, is_deleted=True)
        bookmark_collection_node = find_bookmark_collection(self.user)
        collection_node = CollectionFactory(creator=self.user)
        project_to_be_invisible_on = ProjectFactory()
        project_to_be_invisible_on.add_contributor(self.user, visible=False)
        project_to_be_invisible_on.save()
        group = OSFGroupFactory(creator=self.user, name='Platform')
        group_project = ProjectFactory()
        group_project.add_osf_group(group, permissions.READ)
        registration = RegistrationFactory(creator=self.user)

        contributor_to_or_group_member_nodes = [node._id for node in self.user.contributor_or_group_member_to]

        assert normal_node._id in contributor_to_or_group_member_nodes
        assert normal_contributed_node._id in contributor_to_or_group_member_nodes
        assert project_to_be_invisible_on._id in contributor_to_or_group_member_nodes
        assert deleted_node._id not in contributor_to_or_group_member_nodes
        assert bookmark_collection_node._id not in contributor_to_or_group_member_nodes
        assert collection_node._id not in contributor_to_or_group_member_nodes
        assert group_project._id in contributor_to_or_group_member_nodes
        assert registration._id in contributor_to_or_group_member_nodes

    def test_all_nodes_property(self):
        project = ProjectFactory(creator=self.user)
        project_two = ProjectFactory()

        group = OSFGroupFactory(creator=self.user)
        project_two.add_osf_group(group)
        project_two.save()

        project_three = ProjectFactory()
        project_three.save()

        user_nodes = self.user.all_nodes
        assert user_nodes.count() == 3
        assert project in user_nodes
        assert project_two in user_nodes
        assert project_three not in user_nodes
        assert QuickFilesNode.objects.get(creator=self.user) in user_nodes

    def test_visible_contributor_to_property(self):
        invisible_contributor = UserFactory()
        normal_node = ProjectFactory(creator=invisible_contributor)
        deleted_node = ProjectFactory(creator=invisible_contributor, is_deleted=True)
        bookmark_collection_node = find_bookmark_collection(invisible_contributor)
        collection_node = CollectionFactory(creator=invisible_contributor)
        project_to_be_invisible_on = ProjectFactory()
        project_to_be_invisible_on.add_contributor(invisible_contributor, visible=False)
        project_to_be_invisible_on.save()
        visible_contributor_to_nodes = [node._id for node in invisible_contributor.visible_contributor_to]

        assert normal_node._id in visible_contributor_to_nodes
        assert deleted_node._id not in visible_contributor_to_nodes
        assert bookmark_collection_node._id not in visible_contributor_to_nodes
        assert collection_node._id not in visible_contributor_to_nodes
        assert project_to_be_invisible_on._id not in visible_contributor_to_nodes

    def test_created_property(self):
        # make sure there's at least one project
        ProjectFactory(creator=self.user)
        projects_created_by_user = AbstractNode.objects.filter(creator=self.user)
        assert list(self.user.nodes_created.all()) == list(projects_created_by_user)


# Copied from tests/models/test_user.py
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_quickfiles_creation
class TestUserMerging(OsfTestCase):
    def setUp(self):
        super(TestUserMerging, self).setUp()
        self.user = UserFactory()
        with self.context:
            handlers.celery_before_request()

    def _add_unconfirmed_user(self):
        self.unconfirmed = UnconfirmedUserFactory()

        self.user.add_system_tag('user')
        self.user.add_system_tag('shared')
        self.unconfirmed.add_system_tag('unconfirmed')
        self.unconfirmed.add_system_tag('shared')

    def _add_unregistered_user(self):
        self.unregistered = UnregUserFactory()

        self.project_with_unreg_contrib = ProjectFactory()
        self.project_with_unreg_contrib.add_unregistered_contributor(
            fullname='Unreg',
            email=self.unregistered.username,
            auth=Auth(self.project_with_unreg_contrib.creator)
        )
        self.project_with_unreg_contrib.save()

    @pytest.mark.enable_enqueue_task
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_merge(self, mock_get_mailchimp_api):
        def is_mrm_field(value):
            return 'RelatedManager' in str(value.__class__)

        other_user = UserFactory()
        other_user.save()

        # define values for users' fields
        today = timezone.now()
        yesterday = today - dt.timedelta(days=1)

        self.user.comments_viewed_timestamp['shared_gt'] = today
        other_user.comments_viewed_timestamp['shared_gt'] = yesterday
        self.user.comments_viewed_timestamp['shared_lt'] = yesterday
        other_user.comments_viewed_timestamp['shared_lt'] = today
        self.user.comments_viewed_timestamp['user'] = yesterday
        other_user.comments_viewed_timestamp['other'] = yesterday

        self.user.email_verifications = {'user': {'email': 'a'}}
        other_user.email_verifications = {'other': {'email': 'b'}}

        self.user.notifications_configured = {'abc12': True}
        other_user.notifications_configured = {'123ab': True}

        self.user.external_accounts = [ExternalAccountFactory()]
        other_user.external_accounts = [ExternalAccountFactory()]

        self.user.mailchimp_mailing_lists = {
            'user': True,
            'shared_gt': True,
            'shared_lt': False,
        }
        other_user.mailchimp_mailing_lists = {
            'other': True,
            'shared_gt': False,
            'shared_lt': True,
        }

        self.user.security_messages = {
            'user': today,
            'shared': today,
        }
        other_user.security_messages = {
            'other': today,
            'shared': today,
        }

        self.user.add_system_tag('user')
        self.user.add_system_tag('shared')
        other_user.add_system_tag('other')
        other_user.add_system_tag('shared')

        self.user.save()
        other_user.save()

        # define expected behavior for ALL FIELDS of the User object
        default_to_master_user_fields = [
            'id',
            'date_confirmed',
            'date_disabled',
            'date_last_login',
            'date_registered',
            'email_last_sent',
            'external_identity',
            'family_name',
            'fullname',
            'given_name',
            'is_invited',
            'is_registered',
            'jobs',
            'locale',
            'merged_by',
            'middle_names',
            'password',
            'schools',
            'social',
            'suffix',
            'timezone',
            'username',
            'verification_key',
            'verification_key_v2',
            'affiliated_institutions',
            'contributor_added_email_records',
            'requested_deactivation',
        ]

        calculated_fields = {
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
            'notifications_configured': {
                '123ab': True, 'abc12': True,
            },
            'emails': set([
                other_user.emails.first().id,
                self.user.emails.first().id,
            ]),
            'external_accounts': set([
                self.user.external_accounts.first().id,
                other_user.external_accounts.first().id,
            ]),
            'recently_added': set(),
            'mailchimp_mailing_lists': {
                'user': True,
                'other': True,
                'shared_gt': True,
                'shared_lt': True,
            },
            'osf_mailing_lists': {
                'Open Science Framework Help': True
            },
            'security_messages': {
                'user': today,
                'other': today,
                'shared': today,
            },
            'unclaimed_records': {},
        }

        # from the explicit rules above, compile expected field/value pairs
        expected = {}
        expected.update(calculated_fields)
        for key in default_to_master_user_fields:
            if is_mrm_field(getattr(self.user, key)):
                expected[key] = set(list(getattr(self.user, key).all().values_list('id', flat=True)))
            else:
                expected[key] = getattr(self.user, key)

        # ensure all fields of the user object have an explicit expectation
        all_field_names = {each.name for each in self.user._meta.get_fields()}
        assert set(expected.keys()).issubset(all_field_names)

        # mock mailchimp
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': x, 'list_name': list_name} for x, list_name in enumerate(self.user.mailchimp_mailing_lists)]}

        with run_celery_tasks():
            # perform the merge
            self.user.merge_user(other_user)
            self.user.save()

        self.user.reload()

        # check each field/value pair
        for k, v in expected.items():
            if is_mrm_field(getattr(self.user, k)):
                assert set(list(getattr(self.user, k).all().values_list('id', flat=True))) == v, '{} doesn\'t match expectations'.format(k)
            else:
                assert getattr(self.user, k) == v, '{} doesn\'t match expectation'.format(k)

        assert sorted(self.user.system_tags) == ['other', 'shared', 'user']

        # check fields set on merged user
        assert other_user.merged_by == self.user

        assert not Session.objects.filter(data__auth_user_id=other_user._id).exists()

    def test_merge_unconfirmed(self):
        self._add_unconfirmed_user()
        unconfirmed_username = self.unconfirmed.username
        self.user.merge_user(self.unconfirmed)

        assert self.unconfirmed.is_merged is True
        assert self.unconfirmed.merged_by == self.user

        assert self.user.is_registered is True
        assert self.user.is_invited is False

        # TODO: test profile fields - jobs, schools, social
        # TODO: test security_messages
        # TODO: test mailing_lists

        assert sorted(self.user.system_tags) == sorted(['shared', 'user', 'unconfirmed'])

        # TODO: test emails
        # TODO: test external_accounts

        assert self.unconfirmed.email_verifications == {}
        assert self.unconfirmed.password[0] == '!'
        assert self.unconfirmed.verification_key is None
        # The mergee's email no longer needs to be confirmed by merger
        unconfirmed_emails = [record['email'] for record in self.user.email_verifications.values()]
        assert unconfirmed_username not in unconfirmed_emails

    def test_merge_preserves_external_identity(self):
        verified_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}})
        linking_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'LINK'}})
        creating_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'CREATE'}})
        different_id_user = UserFactory(external_identity={'ORCID': {'4321-4321-4321-4321': 'VERIFIED'}})
        no_id_user = UserFactory(external_identity={'ORCID': {}})
        no_provider_user = UserFactory(external_identity={})

        linking_user.merge_user(creating_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'LINK'}}
        linking_user.merge_user(verified_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        linking_user.merge_user(no_id_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        linking_user.merge_user(no_provider_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        linking_user.merge_user(different_id_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED', '4321-4321-4321-4321': 'VERIFIED'}}

        assert creating_user.external_identity == {}
        assert verified_user.external_identity == {}
        assert no_id_user.external_identity == {}
        assert no_provider_user.external_identity == {}

        no_provider_user.merge_user(linking_user)
        assert linking_user.external_identity == {}
        assert no_provider_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED', '4321-4321-4321-4321': 'VERIFIED'}}

    def test_merge_unregistered(self):
        # test only those behaviors that are not tested with unconfirmed users
        self._add_unregistered_user()

        self.user.merge_user(self.unregistered)

        self.project_with_unreg_contrib.reload()
        assert self.user.is_invited is True
        assert self.user in self.project_with_unreg_contrib.contributors

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_merge_doesnt_send_signal(self, mock_notify):
        #Explictly reconnect signal as it is disconnected by default for test
        contributor_added.connect(notify_added_contributor)
        other_user = UserFactory()
        self.user.merge_user(other_user)
        assert other_user.merged_by._id == self.user._id
        assert mock_notify.called is False


@pytest.mark.enable_implicit_clean
class TestUserValidation(OsfTestCase):

    def setUp(self):
        super(TestUserValidation, self).setUp()
        self.user = AuthUserFactory()

    def test_validate_fullname_none(self):
        self.user.fullname = None
        with pytest.raises(ValidationError):
            self.user.save()

    def test_validate_fullname_empty(self):
        self.user.fullname = ''
        with pytest.raises(ValidationError):
            self.user.save()

    def test_validate_social_profile_websites_empty(self):
        self.user.social = {'profileWebsites': []}
        self.user.save()
        assert self.user.social['profileWebsites'] == []

    def test_validate_social_profile_website_many_different(self):
        basepath = os.path.dirname(__file__)
        url_data_path = os.path.join(basepath, '../website/static/urlValidatorTest.json')
        with open(url_data_path) as url_test_data:
            data = json.load(url_test_data)

        fails_at_end = False
        for should_pass in data['testsPositive']:
            try:
                self.user.social = {'profileWebsites': [should_pass]}
                self.user.save()
                assert self.user.social['profileWebsites'] == [should_pass]
            except ValidationError:
                fails_at_end = True
                print('\"' + should_pass + '\" failed but should have passed while testing that the validator ' + data['testsPositive'][should_pass])

        for should_fail in data['testsNegative']:
            self.user.social = {'profileWebsites': [should_fail]}
            try:
                with pytest.raises(ValidationError):
                    self.user.save()
            except AssertionError:
                fails_at_end = True
                print('\"' + should_fail + '\" passed but should have failed while testing that the validator ' + data['testsNegative'][should_fail])
        if fails_at_end:
            raise

    def test_validate_multiple_profile_websites_valid(self):
        self.user.social = {'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com']}
        self.user.save()
        assert self.user.social['profileWebsites'] == ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com']

    def test_validate_social_profile_websites_invalid(self):
        self.user.social = {'profileWebsites': ['help computer']}
        with pytest.raises(ValidationError):
            self.user.save()

    def test_validate_multiple_profile_social_profile_websites_invalid(self):
        self.user.social = {'profileWebsites': ['http://cos.io/', 'help computer', 'http://dinosaurs.com']}
        with pytest.raises(ValidationError):
            self.user.save()

    def test_empty_social_links(self):
        assert self.user.social_links == {}
        assert len(self.user.social_links) == 0

    def test_profile_website_unchanged(self):
        self.user.social = {'profileWebsites': ['http://cos.io/']}
        self.user.save()
        assert self.user.social_links['profileWebsites'] == ['http://cos.io/']
        assert len(self.user.social_links) == 1

    def test_various_social_handles(self):
        self.user.social = {
            'profileWebsites': ['http://cos.io/'],
            'twitter': ['OSFramework'],
            'github': ['CenterForOpenScience'],
            'scholar': 'ztt_j28AAAAJ'
        }
        self.user.save()
        assert self.user.social_links == {
            'profileWebsites': ['http://cos.io/'],
            'twitter': 'http://twitter.com/OSFramework',
            'github': 'http://github.com/CenterForOpenScience',
            'scholar': 'http://scholar.google.com/citations?user=ztt_j28AAAAJ'
        }

    def test_multiple_profile_websites(self):
        self.user.social = {
            'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com'],
            'twitter': ['OSFramework'],
            'github': ['CenterForOpenScience']
        }
        self.user.save()
        assert self.user.social_links == {
            'profileWebsites': ['http://cos.io/', 'http://thebuckstopshere.com', 'http://dinosaurs.com'],
            'twitter': 'http://twitter.com/OSFramework',
            'github': 'http://github.com/CenterForOpenScience'
        }

    def test_nonsocial_ignored(self):
        self.user.social = {
            'foo': 'bar',
        }
        with pytest.raises(ValidationError) as exc_info:
            self.user.save()
        assert isinstance(exc_info.value.args[0], dict)
        assert self.user.social_links == {}

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
        with pytest.raises(ValidationError):
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
        with pytest.raises(ValidationError):
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
        with pytest.raises(ValidationError):
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
            with pytest.raises(ValidationError):
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
            with pytest.raises(ValidationError):
                self.user.save()


@pytest.mark.enable_quickfiles_creation
class TestUserGdprDelete:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_with_two_admins(self, user):
        second_admin_contrib = UserFactory()
        project = ProjectFactory(creator=user)
        project.add_contributor(second_admin_contrib)
        project.set_permissions(user=second_admin_contrib, permissions=permissions.ADMIN)
        project.save()
        return project

    @pytest.fixture()
    def project_with_two_admins_and_addon_credentials(self, user):
        second_admin_contrib = UserFactory()
        project = ProjectFactory(creator=user)
        project.add_contributor(second_admin_contrib)
        project.set_permissions(user=second_admin_contrib, permissions=permissions.ADMIN)
        user = project.creator

        node_settings = project.add_addon('github', auth=None)
        user_settings = user.add_addon('github')
        node_settings.user_settings = user_settings
        github_account = GitHubAccountFactory()
        github_account.save()
        node_settings.external_account = github_account
        node_settings.save()
        user.save()
        project.save()
        return project

    @pytest.fixture()
    def registration(self, user):
        registration = RegistrationFactory(creator=user)
        registration.save()
        return registration

    @pytest.fixture()
    def project(self, user):
        project = ProjectFactory(creator=user)
        project.save()
        return project

    @pytest.fixture()
    def preprint(self, user):
        preprint = PreprintFactory(creator=user)
        preprint.save()
        return preprint

    @pytest.fixture()
    def project_user_is_only_admin(self, user):
        non_admin_contrib = UserFactory()
        project = ProjectFactory(creator=user)
        project.add_contributor(non_admin_contrib)
        project.add_unregistered_contributor('lisa', 'lisafrank@cos.io', permissions=permissions.ADMIN, auth=Auth(user))
        project.save()
        return project

    def test_can_gdpr_delete(self, user):
        user.social = ['fake social']
        user.schools = ['fake schools']
        user.jobs = ['fake jobs']
        user.external_identity = ['fake external identity']
        user.external_accounts.add(ExternalAccountFactory())

        user.gdpr_delete()

        assert user.fullname == 'Deleted user'
        assert user.suffix == ''
        assert user.social == []
        assert user.schools == []
        assert user.jobs == []
        assert user.external_identity == {}
        assert not user.emails.exists()
        assert not user.external_accounts.exists()
        assert user.is_disabled
        assert user.deleted is not None

    def test_can_gdpr_delete_personal_nodes(self, user):

        user.gdpr_delete()

        # user still has nodes because we did a soft delete
        assert user.nodes.all().count()
        # but they're all deleted
        assert user.nodes.exclude(is_deleted=True).count() == 0

    def test_can_gdpr_delete_shared_nodes_with_multiple_admins(self, user, project_with_two_admins):

        user.gdpr_delete()

        # The deleted user is still associated with the node, though their name still appears as 'Deleted User'
        assert user.nodes.all().count() == 1

    def test_cant_gdpr_delete_registrations(self, user, registration):

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()

        assert exc_info.value.args[0] == 'You cannot delete this user because they have one or more registrations.'

    def test_cant_gdpr_delete_preprints(self, user, preprint):

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()

        assert exc_info.value.args[0] == 'You cannot delete this user because they have one or more preprints.'

    def test_cant_gdpr_delete_shared_node_if_only_admin(self, user, project_user_is_only_admin):

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()

        assert exc_info.value.args[0] == 'You cannot delete node {} because it would' \
                                         ' be a node with contributors, but with no admin.'.format(project_user_is_only_admin._id)

    def test_cant_gdpr_delete_osf_group_if_only_manager(self, user):
        group = OSFGroupFactory(name='My Group', creator=user)
        osf_group_name = group.name
        manager_group_name = group.manager_group.name
        member_group_name = group.member_group.name
        member = AuthUserFactory()
        group.make_member(member)

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()

        assert exc_info.value.args[0] == 'You cannot delete this user because ' \
                                        'they are the only registered manager of OSFGroup ' \
                                        '{} that contains other members.'.format(group._id)

        unregistered = group.add_unregistered_member('fake_user', 'fake_email@cos.io', Auth(user), 'manager')
        assert len(group.managers) == 2

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()

        assert exc_info.value.args[0] == 'You cannot delete this user because ' \
                                        'they are the only registered manager of OSFGroup ' \
                                        '{} that contains other members.'.format(group._id)

        group.remove_member(member)
        member.gdpr_delete()
        # User is not the last member in the group, so they are just removed
        assert OSFGroup.objects.filter(name=osf_group_name).exists()
        assert Group.objects.filter(name=manager_group_name).exists()
        assert Group.objects.filter(name=member_group_name).exists()
        assert group.is_member(member) is False
        assert group.is_manager(member) is False

        group.remove_member(unregistered)
        user.gdpr_delete()
        # Group was deleted because user was the only member
        assert not OSFGroup.objects.filter(name=osf_group_name).exists()
        assert not Group.objects.filter(name=manager_group_name).exists()
        assert not Group.objects.filter(name=member_group_name).exists()

    def test_cant_gdpr_delete_with_addon_credentials(self, user, project_with_two_admins_and_addon_credentials):

        with pytest.raises(UserStateError) as exc_info:
            user.gdpr_delete()
        assert exc_info.value.args[0] == 'You cannot delete this user because they have an external account for' \
                                         ' github attached to Node {}, which has other contributors.'.format(project_with_two_admins_and_addon_credentials._id)


class TestUserSpam:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    def test_get_spam_content(self, user):
        schools_list = []
        expected_content = ''

        for _ in range(2):
            institution = fake.company()
            degree = fake.catch_phrase()
            schools_list.append({
                'degree': degree,
                'institution': institution
            })
            expected_content += '{} {} '.format(institution, degree)
        saved_fields = {'schools': schools_list}

        spam_content = user._get_spam_content(saved_fields)
        assert spam_content == expected_content.strip()

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch('osf.models.spam._get_client')
    def test_do_check_spam(self, mock_get_client, user):
        new_mock = mock.MagicMock()
        new_mock.check_comment = mock.MagicMock(return_value=(True, None))
        mock_get_client.return_value = new_mock

        suspicious_content = 'spam eggs sausage and spam'
        with mock.patch('osf.models.user.OSFUser._get_spam_content', mock.Mock(return_value=suspicious_content)):
            user.do_check_spam(
                author=user.fullname,
                author_email=user.username,
                content=suspicious_content,
                request_headers={'Referrer': 'Woo', 'User-Agent': 'yay', 'Remote-Addr': 'ok'}
            )
        user.save()
        assert user.spam_data['content'] == suspicious_content
        assert user.spam_data['author'] == user.fullname
        assert user.spam_data['author_email'] == user.username

        # test do_check_spam for ham user
        user.confirm_ham()
        assert user.do_check_spam(None, None, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch('osf.models.OSFUser.do_check_spam')
    def test_check_spam(self, mock_do_check_spam, user):

        # test check_spam for other saved fields
        with mock.patch('osf.models.OSFUser._get_spam_content', mock.Mock(return_value='some content!')):
            assert user.check_spam(saved_fields={'fullname': 'Dusty Rhodes'}, request_headers=None) is False
            assert mock_do_check_spam.call_count == 0

        # test check spam for correct saved_fields
        with mock.patch('osf.models.OSFUser._get_spam_content', mock.Mock(return_value='some content!')):
            user.check_spam(saved_fields={'schools': ['one']}, request_headers=None)
            assert mock_do_check_spam.call_count == 1
