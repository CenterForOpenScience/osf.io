# -*- coding: utf-8 -*-
from nose.tools import *  # noqa: F403
import jwe
import jwt
import mock
import furl
import time
import urlparse
import datetime
from django.utils import timezone
import pytest
import pytz
import itsdangerous

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from addons.osfstorage.models import OsfStorageFile
from api_tests import utils as api_test_utils
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.postcommit_tasks.handlers import enqueue_postcommit_task, get_task_from_postcommit_queue
from framework.exceptions import PermissionsError
from website import settings, mails
from website.preprints.tasks import format_preprint, update_preprint_share, on_preprint_updated, update_or_create_preprint_identifiers, update_or_enqueue_on_preprint_updated
from website.project.views.contributor import find_preprint_provider
from website.identifiers.clients import CrossRefClient, ECSArXivCrossRefClient, crossref
from website.identifiers.utils import request_identifiers
from website.util.share import format_user
from framework.auth import Auth, cas, signing
from framework.celery_tasks import handlers
from framework.postcommit_tasks.handlers import enqueue_postcommit_task, get_task_from_postcommit_queue, postcommit_celery_queue
from framework.exceptions import PermissionsError, HTTPError
from framework.auth.core import Auth
from addons.osfstorage.models import OsfStorageFile
from addons.base import views
from osf.models import Tag, Preprint, PreprintLog, PreprintContributor, Subject, Session
from osf.exceptions import PreprintStateError, ValidationError, ValidationValueError, PreprintProviderError

from osf.utils.permissions import READ, WRITE, ADMIN
from osf.utils.workflows import DefaultStates, RequestTypes
from osf_tests.utils import MockShareResponse
from tests.base import assert_datetime_equal, OsfTestCase
from tests.utils import assert_preprint_logs

from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    UserFactory,
    PreprintFactory,
    NodeFactory,
    TagFactory,
    SubjectFactory,
    UserFactory,
    UnregUserFactory,
    PreprintProviderFactory,
    PreprintRequestFactory,
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def preprint(user):
    return PreprintFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)

@pytest.fixture()
def subject():
    return SubjectFactory()


class TestPreprint:
    def test_preprint_factory(self, preprint):
        assert preprint.title is not None
        assert preprint.description is not None
        assert preprint.provider is not None
        assert preprint.is_published is True
        assert preprint.is_public is True
        assert preprint.creator is not None
        assert preprint.files.first() == preprint.primary_file
        assert preprint.deleted is None
        assert preprint.root_folder is not None


class TestPreprintProperties:
    def test_contributors(self, preprint):
        assert len(preprint.contributors) == 1
        assert preprint.contributors[0] == preprint.creator

    def test_verified_publishable(self, preprint):
        preprint.is_published = False
        assert preprint.verified_publishable is False

        preprint.is_published = True
        preprint.deleted = datetime.datetime.now()
        assert preprint.verified_publishable is False

        preprint.deleted = None
        assert preprint.verified_publishable is True

    def test_is_deleted(self, preprint):
        assert preprint.deleted is None
        assert preprint.is_deleted is False

        preprint.deleted = timezone.now()
        preprint.save()

        assert preprint.deleted is not None
        assert preprint.is_deleted is True

    def test_is_preprint_orphan(self, preprint):
        assert preprint.is_preprint_orphan is False
        preprint.primary_file = None
        preprint.save()
        assert preprint.is_preprint_orphan is True

    def test_has_submitted_preprint(self, preprint):
        preprint.machine_state = 'initial'
        preprint.save()
        assert preprint.has_submitted_preprint is False

        preprint.machine_state = 'pending'
        preprint.save()
        assert preprint.has_submitted_preprint is True

    def test_deep_url(self, preprint):
        assert preprint.deep_url == '/preprints/{}/'.format(preprint._id)

    def test_url_(self, preprint):
        assert preprint.url == '/preprints/{}/{}/'.format(preprint.provider._id, preprint._id)

    def test_absolute_url(self, preprint):
        assert preprint.absolute_url == urlparse.urljoin(
            preprint.provider.domain if preprint.provider.domain_redirect_enabled else settings.DOMAIN,
            preprint.url
        )

    def test_absolute_api_v2_url(self, preprint):
        assert '/preprints/{}/'.format(preprint._id) in preprint.absolute_api_v2_url

    def test_admin_contributor_or_group_member_ids(self, preprint, user):
        user2 = UserFactory()
        assert len(preprint.admin_contributor_or_group_member_ids) == 1
        assert user._id in preprint.admin_contributor_or_group_member_ids

        preprint.add_permission(user2, ADMIN, save=True)

        assert len(preprint.admin_contributor_or_group_member_ids) == 2
        assert user2._id in preprint.admin_contributor_or_group_member_ids

    def test_visible_contributor_ids(self, preprint):
        assert preprint.visible_contributor_ids[0] == preprint.creator._id

    def test_all_tags(self, preprint, auth):
        preprint.add_tags(['test_tag_1'], auth)
        preprint.save()

        assert len(preprint.all_tags) == 1
        assert preprint.all_tags[0].name == 'test_tag_1'

    def test_system_tags(self, preprint):
        assert preprint.system_tags.exists() is False


class TestPreprintSubjects:

    @pytest.fixture()
    def write_contrib(self, preprint):
        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, auth=Auth(preprint.creator), permissions=WRITE)
        preprint.save()
        return write_contrib

    def test_set_subjects(self, preprint, auth):
        subject = SubjectFactory()
        subjects = [[subject._id]]
        preprint.set_subjects(subjects, auth)

        assert preprint.subjects.count() == 1
        assert subject in preprint.subjects.all()

    def test_admin_can_set_subjects(self, preprint, subject):
        initial_subjects = list(preprint.subjects.all())
        preprint.set_subjects([[subject._id]], auth=Auth(preprint.creator))

        preprint.reload()
        assert initial_subjects != list(preprint.subjects.all())

    def test_write_can_set_subjects(self, preprint, subject, write_contrib):
        initial_subjects = list(preprint.subjects.all())
        preprint.set_subjects([[subject._id]], auth=Auth(write_contrib))

        preprint.reload()
        assert initial_subjects != list(preprint.subjects.all())


class TestLogging:

    def test_add_log(self, preprint, auth):
        preprint.add_log(PreprintLog.FILE_UPDATED, params={'preprint': preprint._id}, auth=auth)
        preprint.save()

        last_log = preprint.logs.latest()
        assert last_log.action == PreprintLog.FILE_UPDATED
        # date is tzaware
        assert last_log.created.tzinfo == pytz.utc

        # updates preprint.modified
        assert_datetime_equal(preprint.modified, last_log.created)


class TestTagging:

    def test_add_tag(self, preprint, auth):
        preprint.add_tag('FoO', auth=auth)
        preprint.save()

        tag = Tag.objects.get(name='FoO')
        assert preprint.tags.count() == 1
        assert tag in preprint.tags.all()

        last_log = preprint.logs.all().order_by('-created')[0]
        assert last_log.action == PreprintLog.TAG_ADDED
        assert last_log.params['tag'] == 'FoO'
        assert last_log.params['preprint'] == preprint._id

    def test_add_system_tag(self, preprint):
        original_log_count = preprint.logs.count()
        preprint.add_system_tag('FoO')
        preprint.save()

        tag = Tag.all_tags.get(name='FoO', system=True)
        assert preprint.all_tags.count() == 1
        assert tag in preprint.all_tags.all()

        assert tag.system is True

        # No log added
        new_log_count = preprint.logs.count()
        assert original_log_count == new_log_count

    def test_add_system_tag_instance(self, preprint):
        tag = TagFactory(system=True)
        preprint.add_system_tag(tag)

        assert tag in preprint.all_tags.all()

    def test_add_system_tag_non_system_instance(self, preprint):
        tag = TagFactory(system=False)
        with pytest.raises(ValueError):
            preprint.add_system_tag(tag)

        assert tag not in preprint.all_tags.all()

    def test_system_tags_property(self, preprint, auth):
        other_preprint = ProjectFactory()
        other_preprint.add_system_tag('bAr')

        preprint.add_system_tag('FoO')
        preprint.add_tag('bAr', auth=auth)

        assert 'FoO' in preprint.system_tags
        assert 'bAr' not in preprint.system_tags


class TestSearch:

    @mock.patch('website.search.search.update_preprint')
    def test_update_search(self, mock_update_preprint, preprint):
        preprint.update_search()
        assert mock_update_preprint.called


class TestPreprintCreation:

    def test_creator_is_added_as_contributor(self, fake):
        user = UserFactory()
        preprint = Preprint(
            title=fake.bs(),
            creator=user,
            provider=PreprintProviderFactory()
        )
        preprint.save()
        assert preprint.is_contributor(user) is True
        contributor = PreprintContributor.objects.get(user=user, preprint=preprint)
        assert contributor.visible is True
        assert preprint.has_permission(user, ADMIN) is True
        assert preprint.has_permission(user, WRITE) is True
        assert preprint.has_permission(user, READ) is True

    def test_default_region_set_to_user_settings_osfstorage_default(self, fake):
        user = UserFactory()
        preprint = Preprint(
            title=fake.bs,
            creator=user,
            provider=PreprintProviderFactory()
        )
        preprint.save()

        assert preprint.region.id == user.get_addon('osfstorage').default_region_id

    def test_root_folder_created_automatically(self, fake):
        user = UserFactory()
        preprint = Preprint(
            title=fake.bs,
            creator=user,
            provider=PreprintProviderFactory()
        )
        preprint.save()
        assert preprint.root_folder is not None
        assert preprint.root_folder.is_root is True


# Copied from osf_tests/test_node.py
class TestContributorMethods:
    def test_add_contributor(self, preprint, user, auth):
        # A user is added as a contributor
        user = UserFactory()
        preprint.add_contributor(contributor=user, auth=auth)
        preprint.save()
        assert preprint.is_contributor(user) is True
        assert preprint.has_permission(user, ADMIN) is False
        assert preprint.has_permission(user, WRITE) is True
        assert preprint.has_permission(user, READ) is True

        last_log = preprint.logs.all().order_by('-created')[0]
        assert last_log.action == 'contributor_added'
        assert last_log.params['contributors'] == [user._id]

    def test_add_contributors(self, preprint, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        preprint.add_contributors(
            [
                {'user': user1, 'permissions': ADMIN, 'visible': True},
                {'user': user2, 'permissions': WRITE, 'visible': False}
            ],
            auth=auth
        )
        last_log = preprint.logs.all().order_by('-created')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )
        assert preprint.is_contributor(user1)
        assert preprint.is_contributor(user2)
        assert user1._id in preprint.visible_contributor_ids
        assert user2._id not in preprint.visible_contributor_ids
        assert preprint.get_permissions(user1) == [READ, WRITE, ADMIN]
        assert preprint.get_permissions(user2) == [READ, WRITE]
        last_log = preprint.logs.all().order_by('-created')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )

    def test_cant_add_creator_as_contributor_twice(self, preprint, user):
        preprint.add_contributor(contributor=user)
        preprint.save()
        assert len(preprint.contributors) == 1

    def test_cant_add_same_contributor_twice(self, preprint):
        contrib = UserFactory()
        preprint.add_contributor(contributor=contrib)
        preprint.save()
        preprint.add_contributor(contributor=contrib)
        preprint.save()
        assert len(preprint.contributors) == 2

    def test_remove_unregistered_conributor_removes_unclaimed_record(self, preprint, auth):
        new_user = preprint.add_unregistered_contributor(fullname='David Davidson',
            email='david@davidson.com', auth=auth)
        preprint.save()
        assert preprint.is_contributor(new_user)  # sanity check
        assert preprint._primary_key in new_user.unclaimed_records
        preprint.remove_contributor(
            auth=auth,
            contributor=new_user
        )
        preprint.save()
        new_user.refresh_from_db()
        assert preprint.is_contributor(new_user) is False
        assert preprint._primary_key not in new_user.unclaimed_records

    def test_is_contributor(self, preprint):
        contrib, noncontrib = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint)

        assert preprint.is_contributor(contrib) is True
        assert preprint.is_contributor(noncontrib) is False
        assert preprint.is_contributor(None) is False

    def test_visible_contributor_ids(self, preprint, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        PreprintContributor.objects.create(user=visible_contrib, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible_contrib, preprint=preprint, visible=False)
        assert visible_contrib._id in preprint.visible_contributor_ids
        assert invisible_contrib._id not in preprint.visible_contributor_ids

    def test_visible_contributors(self, preprint, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        PreprintContributor.objects.create(user=visible_contrib, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible_contrib, preprint=preprint, visible=False)
        assert visible_contrib in preprint.visible_contributors
        assert invisible_contrib not in preprint.visible_contributors

    def test_set_visible_false(self, preprint, auth):
        contrib = UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint, visible=True)
        preprint.set_visible(contrib, visible=False, auth=auth)
        preprint.save()
        assert PreprintContributor.objects.filter(user=contrib, preprint=preprint, visible=False).exists() is True

        last_log = preprint.logs.all().order_by('-created')[0]
        assert last_log.user == auth.user
        assert last_log.action == PreprintLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_set_visible_true(self, preprint, auth):
        contrib = UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint, visible=False)
        preprint.set_visible(contrib, visible=True, auth=auth)
        preprint.save()
        assert PreprintContributor.objects.filter(user=contrib, preprint=preprint, visible=True).exists() is True

        last_log = preprint.logs.all().order_by('-created')[0]
        assert last_log.user == auth.user
        assert last_log.action == PreprintLog.MADE_CONTRIBUTOR_VISIBLE

    def test_set_visible_is_noop_if_visibility_is_unchanged(self, preprint, auth):
        visible, invisible = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=visible, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible, preprint=preprint, visible=False)
        original_log_count = preprint.logs.count()
        preprint.set_visible(invisible, visible=False, auth=auth)
        preprint.set_visible(visible, visible=True, auth=auth)
        preprint.save()
        assert preprint.logs.count() == original_log_count

    def test_set_visible_contributor_with_only_one_contributor(self, preprint, user):
        with pytest.raises(ValueError) as excinfo:
            preprint.set_visible(user=user, visible=False, auth=None)
        assert excinfo.value.message == 'Must have at least one visible contributor'

    def test_set_visible_missing(self, preprint):
        with pytest.raises(ValueError):
            preprint.set_visible(UserFactory(), True)

    def test_remove_contributor(self, preprint, auth):
        # A user is added as a contributor
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, auth=auth, save=True)
        assert user2 in preprint.contributors
        assert preprint.has_permission(user2, WRITE)
        # The user is removed
        preprint.remove_contributor(auth=auth, contributor=user2)
        preprint.reload()

        assert user2 not in preprint.contributors
        assert preprint.get_permissions(user2) == []
        assert preprint.logs.latest().action == 'contributor_removed'
        assert preprint.logs.latest().params['contributors'] == [user2._id]

    def test_remove_contributors(self, preprint, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        preprint.add_contributors(
            [
                {'user': user1, 'permissions': WRITE, 'visible': True},
                {'user': user2, 'permissions': WRITE, 'visible': True}
            ],
            auth=auth
        )
        assert user1 in preprint.contributors
        assert user2 in preprint.contributors
        assert preprint.has_permission(user1, WRITE)
        assert preprint.has_permission(user2, WRITE)

        preprint.remove_contributors(auth=auth, contributors=[user1, user2], save=True)
        preprint.reload()

        assert user1 not in preprint.contributors
        assert user2 not in preprint.contributors
        assert preprint.get_permissions(user1) == []
        assert preprint.get_permissions(user2) == []
        assert preprint.logs.latest().action == 'contributor_removed'

    def test_replace_contributor(self, preprint):
        contrib = UserFactory()
        preprint.add_contributor(contrib, auth=Auth(preprint.creator))
        preprint.save()
        assert contrib in preprint.contributors.all()  # sanity check
        replacer = UserFactory()
        old_length = preprint.contributors.count()
        preprint.replace_contributor(contrib, replacer)
        preprint.save()
        new_length = preprint.contributors.count()
        assert contrib not in preprint.contributors.all()
        assert replacer in preprint.contributors.all()
        assert old_length == new_length

        # test unclaimed_records is removed
        assert (
            preprint._id not in
            contrib.unclaimed_records.keys()
        )

    def test_permission_override_fails_if_no_admins(self, preprint, user):
        # User has admin permissions because they are the creator
        # Cannot lower permissions
        with pytest.raises(PreprintStateError):
            preprint.add_contributor(user, permissions=WRITE)

    def test_update_contributor(self, preprint, auth):
        new_contrib = AuthUserFactory()
        preprint.add_contributor(new_contrib, permissions=WRITE, auth=auth)

        assert preprint.get_permissions(new_contrib) == [READ, WRITE]
        assert preprint.get_visible(new_contrib) is True

        preprint.update_contributor(
            new_contrib,
            READ,
            False,
            auth=auth
        )
        assert preprint.get_permissions(new_contrib) == [READ]
        assert preprint.get_visible(new_contrib) is False

    def test_update_contributor_non_admin_raises_error(self, preprint, auth):
        non_admin = AuthUserFactory()
        preprint.add_contributor(
            non_admin,
            permissions=WRITE,
            auth=auth
        )
        with pytest.raises(PermissionsError):
            preprint.update_contributor(
                non_admin,
                None,
                False,
                auth=Auth(non_admin)
            )

    def test_update_contributor_only_admin_raises_error(self, preprint, auth):
        with pytest.raises(PreprintStateError):
            preprint.update_contributor(
                auth.user,
                WRITE,
                True,
                auth=auth
            )

    def test_update_contributor_non_contrib_raises_error(self, preprint, auth):
        non_contrib = AuthUserFactory()
        with pytest.raises(ValueError):
            preprint.update_contributor(
                non_contrib,
                ADMIN,
                True,
                auth=auth
            )


# Copied from tests/test_models.py
class TestPreprintAddContributorRegisteredOrNot:

    def test_add_contributor_user_id(self, user, preprint):
        registered_user = UserFactory()
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), user_id=registered_user._id, save=True)
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is True

    def test_add_contributor_user_id_already_contributor(self, user, preprint):
        with pytest.raises(ValidationError) as excinfo:
            preprint.add_contributor_registered_or_not(auth=Auth(user), user_id=user._id, save=True)
        assert 'is already a contributor' in excinfo.value.message

    def test_add_contributor_invalid_user_id(self, user, preprint):
        with pytest.raises(ValueError) as excinfo:
            preprint.add_contributor_registered_or_not(auth=Auth(user), user_id='abcde', save=True)
        assert 'was not found' in excinfo.value.message

    def test_add_contributor_fullname_email(self, user, preprint):
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe', email='jane@doe.com')
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname(self, user, preprint):
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe')
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname_email_already_exists(self, user, preprint):
        registered_user = UserFactory()
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='F Mercury', email=registered_user.username)
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is True


class TestContributorVisibility:

    @pytest.fixture()
    def user2(self):
        return UserFactory()

    @pytest.fixture()
    def preprint2(self, user2, user, auth):
        preprint = PreprintFactory(creator=user)
        preprint.add_contributor(contributor=user2, auth=auth)
        return preprint

    def test_get_visible_true(self, preprint2):
        assert preprint2.get_visible(preprint2.creator) is True

    def test_get_visible_false(self, preprint2, user2, auth):
        preprint2.set_visible(preprint2.creator, False)
        assert preprint2.get_visible(preprint2.creator) is False

    def test_make_invisible(self, preprint2):
        preprint2.set_visible(preprint2.creator, False, save=True)
        preprint2.reload()
        assert preprint2.creator._id not in preprint2.visible_contributor_ids
        assert preprint2.creator not in preprint2.visible_contributors
        assert preprint2.logs.latest().action == PreprintLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_make_visible(self, preprint2, user2):
        preprint2.set_visible(preprint2.creator, False, save=True)
        preprint2.set_visible(preprint2.creator, True, save=True)
        preprint2.reload()
        assert preprint2.creator._id in preprint2.visible_contributor_ids
        assert preprint2.creator in preprint2.visible_contributors
        assert preprint2.logs.latest().action == PreprintLog.MADE_CONTRIBUTOR_VISIBLE
        # Regression project test: Ensure that hiding and showing the first contributor
        # does not change the visible contributor order
        assert list(preprint2.visible_contributors) == [preprint2.creator, user2]

    def test_set_visible_missing(self, preprint2):
        with pytest.raises(ValueError):
            preprint2.set_visible(UserFactory(), True)


class TestPermissionMethods:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    def test_has_permission(self, preprint):
        user = UserFactory()
        contributor = PreprintContributor.objects.create(
            preprint=preprint, user=user,
        )
        preprint.add_permission(user, READ)

        assert preprint.has_permission(user, READ) is True
        assert preprint.has_permission(user, WRITE) is False
        assert preprint.has_permission(user, ADMIN) is False

        preprint.add_permission(user, WRITE)
        assert contributor.user in preprint.contributors
        assert preprint.has_permission(user, WRITE) is True

        user.is_superuser = True
        user.save()

        assert preprint.has_permission(user, ADMIN) is False

    def test_has_permission_passed_non_contributor_returns_false(self, preprint):
        noncontrib = UserFactory()
        assert preprint.has_permission(noncontrib, READ) is False

    def test_get_permissions(self, preprint):
        user = UserFactory()
        contributor = PreprintContributor.objects.create(
            preprint=preprint, user=user,
        )
        preprint.add_permission(user, READ)
        assert preprint.get_permissions(user) == [READ]

        preprint.add_permission(user, WRITE)
        assert preprint.get_permissions(user) == [READ, WRITE]
        assert contributor.user in preprint.contributors

    def test_add_permission(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user,
        )
        preprint.add_permission(user, WRITE)
        preprint.save()
        assert preprint.has_permission(user, WRITE) is True

    def test_remove_permission(self, preprint):
        assert preprint.has_permission(preprint.creator, ADMIN) is True
        assert preprint.has_permission(preprint.creator, WRITE) is True
        assert preprint.has_permission(preprint.creator, WRITE) is True
        preprint.remove_permission(preprint.creator, ADMIN)
        assert preprint.has_permission(preprint.creator, ADMIN) is False
        assert preprint.has_permission(preprint.creator, WRITE) is False
        assert preprint.has_permission(preprint.creator, WRITE) is False

    def test_remove_permission_not_granted(self, preprint, auth):
        contrib = UserFactory()
        preprint.add_contributor(contrib, permissions=WRITE, auth=auth)
        with pytest.raises(ValueError):
            preprint.remove_permission(contrib, ADMIN)

    def test_set_permissions(self, preprint):
        user = UserFactory()

        preprint.set_permissions(user, WRITE, save=True)
        assert preprint.has_permission(user, ADMIN) is False
        assert preprint.has_permission(user, WRITE) is True
        assert preprint.has_permission(user, READ) is True

        preprint.set_permissions(user, READ, save=True)
        assert preprint.has_permission(user, ADMIN) is False
        assert preprint.has_permission(user, WRITE) is False
        assert preprint.has_permission(user, READ) is True

        preprint.set_permissions(user, ADMIN, save=True)
        assert preprint.has_permission(user, ADMIN) is True
        assert preprint.has_permission(user, WRITE) is True
        assert preprint.has_permission(user, READ) is True

    def test_set_permissions_raises_error_if_only_admins_permissions_are_reduced(self, preprint):
        # creator is the only admin
        with pytest.raises(PreprintStateError) as excinfo:
            preprint.set_permissions(preprint.creator, permissions=WRITE)
        assert excinfo.value.args[0] == 'Must have at least one registered admin contributor'

    def test_add_permission_with_admin_also_grants_read_and_write(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user,
        )
        preprint.add_permission(user, ADMIN)
        preprint.save()
        assert preprint.has_permission(user, ADMIN)
        assert preprint.has_permission(user, WRITE)

    def test_add_permission_already_granted(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user
        )
        preprint.add_permission(user, ADMIN)
        with pytest.raises(ValueError):
            preprint.add_permission(user, ADMIN)

    def test_contributor_can_edit(self, preprint, auth):
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        preprint.add_contributor(
            contributor=contributor, auth=auth)
        preprint.save()
        # write contribs can now edit preprints
        assert bool(preprint.can_edit(contributor_auth)) is True
        assert bool(preprint.can_edit(other_guy_auth)) is False

    def test_can_edit_can_be_passed_a_user(self, user, preprint):
        assert bool(preprint.can_edit(user=user)) is True

    def test_creator_can_edit(self, auth, preprint):
        assert bool(preprint.can_edit(auth)) is True

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        user1_auth = Auth(user=user1)
        preprint = PreprintFactory(is_public=True)
        # Noncontributor can't edit
        assert bool(preprint.can_edit(user1_auth)) is False

    def test_can_view_private(self, preprint, auth):
        preprint.is_public = False
        preprint.save()
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        preprint.add_contributor(
            contributor=contributor, auth=auth)
        preprint.save()
        # Only creator and contributor can view
        assert preprint.can_view(auth)
        assert preprint.can_view(contributor_auth)
        assert preprint.can_view(other_guy_auth) is False

    def test_creator_cannot_edit_project_if_they_are_removed(self):
        creator = UserFactory()
        preprint = PreprintFactory(creator=creator)
        contrib = UserFactory()
        preprint.add_contributor(contrib, permissions=ADMIN, auth=Auth(user=creator))
        preprint.save()
        assert creator in preprint.contributors.all()
        # Creator is removed from project
        preprint.remove_contributor(creator, auth=Auth(user=contrib))
        assert preprint.can_view(Auth(user=creator)) is True
        assert preprint.can_edit(Auth(user=creator)) is False
        assert preprint.is_contributor(creator) is False

    def test_can_view_public(self, preprint, auth):
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        preprint.add_contributor(
            contributor=contributor, auth=auth)
        # Change preprint to public
        preprint.is_public = True
        preprint.save()
        # Creator, contributor, and noncontributor can view
        assert preprint.can_view(auth)
        assert preprint.can_view(contributor_auth)
        assert preprint.can_view(other_guy_auth)

    def test_can_view_unpublished(self, preprint, auth):
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        preprint.add_contributor(
            contributor=contributor, auth=auth)

        # Change preprint to unpublished
        preprint.is_published = False
        preprint.save()
        # Creator, contributor, and noncontributor can view
        assert preprint.can_view(auth)
        assert preprint.can_view(contributor_auth)
        assert preprint.can_view(other_guy_auth) is False


# Copied from tests/test_models.py
@pytest.mark.enable_implicit_clean
class TestAddUnregisteredContributor:

    def test_add_unregistered_contributor(self, preprint, user, auth):
        preprint.add_unregistered_contributor(
            email='foo@bar.com',
            fullname='Weezy F. Baby',
            auth=auth
        )
        preprint.save()
        latest_contributor = PreprintContributor.objects.get(preprint=preprint, user__username='foo@bar.com').user
        assert latest_contributor.username == 'foo@bar.com'
        assert latest_contributor.fullname == 'Weezy F. Baby'
        assert bool(latest_contributor.is_registered) is False

        # A log event was added
        assert preprint.logs.first().action == 'contributor_added'
        assert preprint._id in latest_contributor.unclaimed_records, 'unclaimed record was added'
        unclaimed_data = latest_contributor.get_unclaimed_record(preprint._primary_key)
        assert unclaimed_data['referrer_id'] == user._primary_key
        assert bool(preprint.is_contributor(latest_contributor)) is True
        assert unclaimed_data['email'] == 'foo@bar.com'

    def test_add_unregistered_adds_new_unclaimed_record_if_user_already_in_db(self, fake, preprint, auth):
        user = UnregUserFactory()
        given_name = fake.name()
        new_user = preprint.add_unregistered_contributor(
            email=user.username,
            fullname=given_name,
            auth=auth
        )
        preprint.save()
        # new unclaimed record was added
        assert preprint._primary_key in new_user.unclaimed_records
        unclaimed_data = new_user.get_unclaimed_record(preprint._primary_key)
        assert unclaimed_data['name'] == given_name

    def test_add_unregistered_raises_error_if_user_is_registered(self, preprint, auth):
        user = UserFactory(is_registered=True)  # A registered user
        with pytest.raises(ValidationError):
            preprint.add_unregistered_contributor(
                email=user.username,
                fullname=user.fullname,
                auth=auth
            )


class TestPreprintSpam:
    @mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', True)
    def test_set_privacy_on_spammy_preprint(self, preprint):
        preprint.is_public = False
        preprint.save()
        with mock.patch.object(Preprint, 'is_spammy', mock.PropertyMock(return_value=True)):
            with pytest.raises(PreprintStateError):
                preprint.set_privacy('public')

    def test_check_spam_disabled_by_default(self, preprint, user):
        # SPAM_CHECK_ENABLED is False by default
        with mock.patch('osf.models.preprint.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.preprint.Preprint.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                preprint.set_privacy('public')
                assert preprint.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_check_spam_only_public_preprint_by_default(self, preprint, user):
        # SPAM_CHECK_PUBLIC_ONLY is True by default
        with mock.patch('osf.models.preprint.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.preprint.Preprint.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                preprint.set_privacy('private')
                assert preprint.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_check_spam_skips_ham_user(self, preprint, user):
        with mock.patch('osf.models.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.Preprint.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                user.confirm_ham()
                preprint.set_privacy('public')
                assert preprint.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_CHECK_PUBLIC_ONLY', False)
    def test_check_spam_on_private_preprint(self, preprint, user):
        preprint.is_public = False
        preprint.save()
        with mock.patch('osf.models.preprint.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.preprint.Preprint.do_check_spam', mock.Mock(return_value=True)):
                preprint.set_privacy('private')
                assert preprint.check_spam(user, None, None) is True

    @mock.patch('website.mailchimp_utils.unsubscribe_mailchimp')
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_ACCOUNT_SUSPENSION_ENABLED', True)
    def test_check_spam_on_private_preprint_bans_new_spam_user(self, mock_send_mail, preprint, user):
        preprint.is_public = False
        preprint.save()
        with mock.patch('osf.models.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.Preprint.do_check_spam', mock.Mock(return_value=True)):
                user.date_confirmed = timezone.now()
                preprint.set_privacy('public')
                user2 = UserFactory()
                # preprint w/ one contributor
                preprint2 = PreprintFactory(creator=user, description='foobar2', is_public=True)
                preprint2.save()
                # preprint with more than one contributor
                preprint3 = PreprintFactory(creator=user, description='foobar3', is_public=True)
                preprint3.add_contributor(user2)
                preprint3.save()

                assert preprint.check_spam(user, None, None) is True

                assert user.is_disabled is True
                assert preprint.is_public is False
                preprint2.reload()
                assert preprint2.is_public is False
                preprint3.reload()
                assert preprint3.is_public is True

    @mock.patch('website.mailchimp_utils.unsubscribe_mailchimp')
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_ACCOUNT_SUSPENSION_ENABLED', True)
    def test_check_spam_on_private_preprint_does_not_ban_existing_user(self, mock_send_mail, preprint, user):
        preprint.is_public = False
        preprint.save()
        with mock.patch('osf.models.Preprint._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.Preprint.do_check_spam', mock.Mock(return_value=True)):
                preprint.creator.date_confirmed = timezone.now() - datetime.timedelta(days=9001)
                preprint.set_privacy('public')
                assert preprint.check_spam(user, None, None) is True
                assert preprint.is_public is True

    def test_flag_spam_make_preprint_private(self, preprint):
        assert preprint.is_public
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', True):
            preprint.flag_spam()
            preprint.save()
        assert preprint.is_spammy
        assert preprint.is_public is False

    def test_flag_spam_do_not_make_preprint_private(self,  preprint):
        assert preprint.is_public
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', False):
            preprint.flag_spam()
            preprint.save()
        assert preprint.is_spammy
        assert preprint.is_public

    def test_confirm_spam_makes_preprint_private(self, preprint):
        assert preprint.is_public
        preprint.confirm_spam()
        preprint.save()
        assert preprint.is_spammy
        assert preprint.is_public is False


# copied from tests/test_models.py
class TestManageContributors:

    def test_contributor_manage_visibility(self, preprint, user, auth):
        reg_user1 = UserFactory()
        #This makes sure manage_contributors uses set_visible so visibility for contributors is added before visibility
        #for other contributors is removed ensuring there is always at least one visible contributor
        preprint.add_contributor(contributor=user, permissions=ADMIN, auth=auth)
        preprint.add_contributor(contributor=reg_user1, permissions=ADMIN, auth=auth)

        preprint.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permissions': ADMIN, 'visible': True},
                {'id': reg_user1._id, 'permissions': ADMIN, 'visible': False},
            ],
            auth=auth,
            save=True
        )
        preprint.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permissions': ADMIN, 'visible': False},
                {'id': reg_user1._id, 'permissions': ADMIN, 'visible': True},
            ],
            auth=auth,
            save=True
        )

        assert len(preprint.visible_contributor_ids) == 1

    def test_contributor_set_visibility_validation(self, preprint, user, auth):
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        preprint.add_contributors(
            [
                {'user': reg_user1, 'permissions': ADMIN, 'visible': True},
                {'user': reg_user2, 'permissions': ADMIN, 'visible': False},
            ]
        )
        print(preprint.visible_contributor_ids)
        with pytest.raises(ValueError) as e:
            preprint.set_visible(user=reg_user1, visible=False, auth=None)
            preprint.set_visible(user=user, visible=False, auth=None)
            assert e.value.message == 'Must have at least one visible contributor'

    def test_manage_contributors_cannot_remove_last_admin_contributor(self, auth, preprint):
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, permissions=WRITE, auth=auth)
        preprint.save()
        with pytest.raises(PreprintStateError) as excinfo:
            preprint.manage_contributors(
                user_dicts=[{'id': user2._id,
                             'permissions': WRITE,
                             'visible': True}],
                auth=auth,
                save=True
            )
        assert excinfo.value.args[0] == 'Must have at least one registered admin contributor'

    def test_manage_contributors_reordering(self, preprint, user, auth):
        user2, user3 = UserFactory(), UserFactory()
        preprint.add_contributor(contributor=user2, auth=auth)
        preprint.add_contributor(contributor=user3, auth=auth)
        preprint.save()
        assert list(preprint.contributors.all()) == [user, user2, user3]
        preprint.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permissions': WRITE,
                    'visible': True,
                },
                {
                    'id': user3._id,
                    'permissions': WRITE,
                    'visible': True,
                },
                {
                    'id': user._id,
                    'permissions': ADMIN,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        assert list(preprint.contributors.all()) == [user2, user3, user]

    def test_manage_contributors_logs_when_users_reorder(self, preprint, user, auth):
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, permissions=WRITE, auth=auth)
        preprint.save()
        preprint.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permissions': WRITE,
                    'visible': True,
                },
                {
                    'id': user._id,
                    'permissions': ADMIN,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        latest_log = preprint.logs.latest()
        assert latest_log.action == PreprintLog.CONTRIB_REORDERED
        assert latest_log.user == user
        assert user._id in latest_log.params['contributors']
        assert user2._id in latest_log.params['contributors']

    def test_manage_contributors_logs_when_permissions_change(self, preprint, user, auth):
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, permissions=WRITE, auth=auth)
        preprint.save()
        preprint.manage_contributors(
            user_dicts=[
                {
                    'id': user._id,
                    'permissions': ADMIN,
                    'visible': True,
                },
                {
                    'id': user2._id,
                    'permissions': READ,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        latest_log = preprint.logs.latest()
        assert latest_log.action == PreprintLog.PERMISSIONS_UPDATED
        assert latest_log.user == user
        assert user2._id in latest_log.params['contributors']
        assert user._id not in latest_log.params['contributors']

    def test_manage_contributors_new_contributor(self, preprint, user, auth):
        user = UserFactory()
        users = [
            {'id': user._id, 'permissions': READ, 'visible': True},
            {'id': preprint.creator._id, 'permissions': [READ, WRITE, ADMIN], 'visible': True},
        ]
        with pytest.raises(ValueError) as excinfo:
            preprint.manage_contributors(
                users, auth=auth, save=True
            )
        assert excinfo.value.args[0] == 'User {0} not in contributors'.format(user.fullname)

    def test_manage_contributors_no_contributors(self, preprint, auth):
        with pytest.raises(PreprintStateError):
            preprint.manage_contributors(
                [], auth=auth, save=True,
            )

    def test_manage_contributors_no_admins(self, preprint, auth):
        user = UserFactory()
        preprint.add_contributor(
            user,
            permissions=ADMIN,
            save=True
        )
        users = [
            {'id': preprint.creator._id, 'permissions': READ, 'visible': True},
            {'id': user._id, 'permissions': READ, 'visible': True},
        ]
        with pytest.raises(PreprintStateError):
            preprint.manage_contributors(
                users, auth=auth, save=True,
            )

    def test_manage_contributors_no_registered_admins(self, preprint, auth):
        unregistered = UnregUserFactory()
        preprint.add_unregistered_contributor(
            unregistered.fullname,
            unregistered.email,
            auth=Auth(preprint.creator),
            permissions=ADMIN,
            existing_user=unregistered
        )
        users = [
            {'id': preprint.creator._id, 'permissions': READ, 'visible': True},
            {'id': unregistered._id, 'permissions': ADMIN, 'visible': True},
        ]
        with pytest.raises(PreprintStateError):
            preprint.manage_contributors(
                users, auth=auth, save=True,
            )

    def test_get_admin_contributors(self, user, auth, preprint):
        read, write, admin = UserFactory(), UserFactory(), UserFactory()
        nonactive_admin = UserFactory()
        noncontrib = UserFactory()
        preprint = PreprintFactory(creator=user)
        preprint.add_contributor(read, auth=auth, permissions=READ)
        preprint.add_contributor(write, auth=auth, permissions=WRITE)
        preprint.add_contributor(admin, auth=auth, permissions=ADMIN)
        preprint.add_contributor(nonactive_admin, auth=auth, permissions=ADMIN)
        preprint.save()

        nonactive_admin.is_disabled = True
        nonactive_admin.save()

        result = list(preprint.get_admin_contributors([
            read, write, admin, noncontrib, nonactive_admin
        ]))

        assert admin in result
        assert read not in result
        assert write not in result
        assert noncontrib not in result
        assert nonactive_admin not in result


class TestContributorOrdering:

    def test_can_get_contributor_order(self, preprint):
        user1, user2 = UserFactory(), UserFactory()
        contrib1 = PreprintContributor.objects.create(user=user1, preprint=preprint)
        contrib2 = PreprintContributor.objects.create(user=user2, preprint=preprint)
        creator_contrib = PreprintContributor.objects.get(user=preprint.creator, preprint=preprint)
        assert list(preprint.get_preprintcontributor_order()) == [creator_contrib.id, contrib1.id, contrib2.id]
        assert list(preprint.contributors.all()) == [preprint.creator, user1, user2]

    def test_can_set_contributor_order(self, preprint):
        user1, user2 = UserFactory(), UserFactory()
        contrib1 = PreprintContributor.objects.create(user=user1, preprint=preprint)
        contrib2 = PreprintContributor.objects.create(user=user2, preprint=preprint)
        creator_contrib = PreprintContributor.objects.get(user=preprint.creator, preprint=preprint)
        preprint.set_preprintcontributor_order([contrib1.id, contrib2.id, creator_contrib.id])
        assert list(preprint.get_preprintcontributor_order()) == [contrib1.id, contrib2.id, creator_contrib.id]
        assert list(preprint.contributors.all()) == [user1, user2, preprint.creator]

    def test_move_contributor(self, user, preprint, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        preprint.add_contributors(
            [
                {'user': user1, 'permissions': WRITE, 'visible': True},
                {'user': user2, 'permissions': WRITE, 'visible': True}
            ],
            auth=auth
        )

        user_contrib_id = preprint.preprintcontributor_set.get(user=user).id
        user1_contrib_id = preprint.preprintcontributor_set.get(user=user1).id
        user2_contrib_id = preprint.preprintcontributor_set.get(user=user2).id

        old_order = [user_contrib_id, user1_contrib_id, user2_contrib_id]
        assert list(preprint.get_preprintcontributor_order()) == old_order

        preprint.move_contributor(user2, auth=auth, index=0, save=True)

        new_order = [user2_contrib_id, user_contrib_id, user1_contrib_id]
        assert list(preprint.get_preprintcontributor_order()) == new_order


@pytest.mark.enable_implicit_clean
class TestDOIValidation:

    def test_validate_bad_doi(self, preprint):
        with pytest.raises(ValidationError):
            preprint.article_doi = 'nope'
            preprint.save()
        with pytest.raises(ValidationError):
            preprint.article_doi = 'https://dx.doi.org/10.123.456'
            preprint.save()  # should save the bare DOI, not a URL
        with pytest.raises(ValidationError):
            preprint.article_doi = 'doi:10.10.1038/nwooo1170'
            preprint.save() # should save without doi: prefix

    def test_validate_good_doi(self, preprint):
        doi = '10.11038/nwooo1170'
        preprint.article_doi = doi
        preprint.save()
        assert preprint.article_doi == doi


# copied from tests/test_models.py
class TestPreprintUpdate:
    def test_set_title_works_with_valid_title(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        proj.set_title('This is now', auth=auth)
        proj.save()
        # Title was changed
        assert proj.title == 'This is now'
        # A log event was saved
        latest_log = proj.logs.latest()
        assert latest_log.action == 'edit_title'
        assert latest_log.params['title_original'] == 'That Was Then'

    def test_set_title_fails_if_empty_or_whitespace(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        with pytest.raises(ValidationValueError):
            proj.set_title(' ', auth=auth)
        with pytest.raises(ValidationValueError):
            proj.set_title('', auth=auth)
        assert proj.title == 'That Was Then'

    def test_set_title_fails_if_too_long(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        long_title = ''.join('a' for _ in range(513))
        with pytest.raises(ValidationValueError):
            proj.set_title(long_title, auth=auth)

    def test_set_description(self, preprint, auth):
        old_desc = preprint.description
        preprint.set_description(
            'new description', auth=auth)
        preprint.save()
        assert preprint.description, 'new description'
        latest_log = preprint.logs.latest()
        assert latest_log.action, PreprintLog.EDITED_DESCRIPTION
        assert latest_log.params['description_original'], old_desc
        assert latest_log.params['description_new'], 'new description'

    def test_updating_title_twice_with_same_title(self, fake, auth, preprint):
        original_n_logs = preprint.logs.count()
        new_title = fake.bs()
        preprint.set_title(new_title, auth=auth, save=True)
        assert preprint.logs.count() == original_n_logs + 1  # sanity check

        # Call update with same title
        preprint.set_title(new_title, auth=auth, save=True)
        # A new log is not created
        assert preprint.logs.count() == original_n_logs + 1

    def test_updating_description_twice_with_same_content(self, fake, auth, preprint):
        original_n_logs = preprint.logs.count()
        new_desc = fake.bs()
        preprint.set_description(new_desc, auth=auth, save=True)
        assert preprint.logs.count() == original_n_logs + 1  # sanity check

        # Call update with same description
        preprint.set_description(new_desc, auth=auth, save=True)
        # A new log is not created
        assert preprint.logs.count() == original_n_logs + 1


class TestSetPreprintFile(OsfTestCase):

    def setUp(self):
        super(TestSetPreprintFile, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.read_write_user = AuthUserFactory()
        self.read_write_user_auth = Auth(user=self.read_write_user)

        self.project = ProjectFactory(creator=self.user)
        self.preprint = PreprintFactory(project=self.project, creator=self.user, finish=False)
        self.file = OsfStorageFile.create(
            target=self.preprint,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

        self.file_two = OsfStorageFile.create(
            target=self.preprint,
            path='/pandapanda.txt',
            name='pandapanda.txt',
            materialized_path='/pandapanda.txt')
        self.file_two.save()

        self.preprint.add_contributor(self.read_write_user, permissions=WRITE)
        self.project.save()

    @assert_preprint_logs(PreprintLog.PUBLISHED, 'preprint')
    def test_is_preprint_property_new_file_to_published(self):
        assert_false(self.preprint.is_published)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        self.preprint.reload()
        assert_false(self.preprint.is_published)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.reload()
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth)
        self.preprint.reload()
        assert_false(self.preprint.is_published)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.reload()
        assert_true(self.preprint.is_published)

    @assert_preprint_logs(PreprintLog.SUPPLEMENTAL_NODE_ADDED, 'preprint')
    def test_set_supplemental_node(self):
        assert_false(self.preprint.is_published)
        project = ProjectFactory(creator=self.preprint.creator)
        self.preprint.set_supplemental_node(project, auth=self.auth, save=True)
        self.preprint.reload()
        assert self.preprint.node == project

    def test_set_supplemental_node_deleted(self):
        project = ProjectFactory(creator=self.preprint.creator)
        with assert_raises(ValueError):
            project.is_deleted= True
            project.save()
            self.preprint.set_supplemental_node(project, auth=self.auth, save=True)

    def test_set_supplemental_node_already_has_a_preprint(self):
        project_two = ProjectFactory(creator=self.preprint.creator)
        preprint = PreprintFactory(project=project_two, provider=self.preprint.provider)
        self.preprint.set_supplemental_node(project_two, auth=self.auth, save=True)
        assert project_two.preprints.count() == 2

    def test_preprint_made_public(self):
        # Testing for migrated preprints, that may have had is_public = False
        self.preprint.is_public = False
        self.preprint.save()
        assert_false(self.preprint.is_public)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_false(self.preprint.is_public)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.reload()
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth)
        self.preprint.reload()
        assert_false(self.preprint.is_public)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.preprint.is_public)

    def test_add_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.preprint.primary_file, self.file)
        assert_equal(type(self.preprint.primary_file), type(self.file))

    @assert_preprint_logs(PreprintLog.FILE_UPDATED, 'preprint')
    def test_change_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.preprint.primary_file, self.file)

        self.preprint.set_primary_file(self.file_two, auth=self.auth, save=True)
        assert_equal(self.preprint.primary_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(AttributeError):
            self.preprint.set_primary_file('inatlanta', auth=self.auth, save=True)

    def test_removing_primary_file_creates_orphan(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_false(self.preprint.is_preprint_orphan)
        self.preprint.primary_file = None
        self.preprint.save()
        assert_true(self.preprint.is_preprint_orphan)

    def test_preprint_created_date(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.preprint.primary_file._id, self.file._id)

        assert(self.preprint.created)
        assert_not_equal(self.project.created, self.preprint.created)


class TestPreprintPermissions(OsfTestCase):
    def setUp(self):
        super(TestPreprintPermissions, self).setUp()
        self.user = AuthUserFactory()
        self.noncontrib = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.read_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.preprint = PreprintFactory(project=self.project, is_published=False, creator=self.user)
        self.preprint.add_contributor(self.write_contrib, permissions=WRITE)
        self.preprint.add_contributor(self.read_contrib, permissions=READ)

        self.file = OsfStorageFile.create(
            target=self.preprint,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

    def test_noncontrib_cannot_set_subjects(self):
        initial_subjects = list(self.preprint.subjects.all())
        with assert_raises(PermissionsError):
            self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.noncontrib))
        self.preprint.reload()
        assert_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_read_cannot_set_subjects(self):
        initial_subjects = list(self.preprint.subjects.all())
        with assert_raises(PermissionsError):
            self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.read_contrib))

        self.preprint.reload()
        assert_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_write_can_set_subjects(self):
        initial_subjects = list(self.preprint.subjects.all())
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.write_contrib))
        self.preprint.reload()
        assert_not_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_admin_can_set_subjects(self):
        initial_subjects = list(self.preprint.subjects.all())
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.user))

        self.preprint.reload()
        assert_not_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_noncontrib_cannot_set_file(self):
        initial_file = self.preprint.primary_file
        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(self.file, auth=Auth(self.noncontrib), save=True)
        self.preprint.reload()
        assert_equal(initial_file._id, self.preprint.primary_file._id)

    def test_read_contrib_cannot_set_file(self):
        initial_file = self.preprint.primary_file
        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(self.file, auth=Auth(self.read_contrib), save=True)
        self.preprint.reload()
        assert_equal(initial_file._id, self.preprint.primary_file._id)

    def test_write_contrib_can_set_file(self):
        initial_file = self.preprint.primary_file
        self.preprint.set_primary_file(self.file, auth=Auth(self.write_contrib), save=True)
        self.preprint.reload()
        assert_equal(self.file._id, self.preprint.primary_file._id)

    def test_admin_can_set_file(self):
        initial_file = self.preprint.primary_file
        self.preprint.set_primary_file(self.file, auth=Auth(self.user), save=True)
        self.preprint.reload()
        assert_equal(self.file._id, self.preprint.primary_file._id)

    def test_primary_file_must_target_preprint(self):
        file = OsfStorageFile.create(
            target=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        file.save()

        with assert_raises(ValueError):
            self.preprint.set_primary_file(file, auth=Auth(self.user), save=True)

    def test_non_admin_cannot_publish(self):
        assert_false(self.preprint.is_published)

        with assert_raises(PermissionsError):
            self.preprint.set_published(True, auth=Auth(self.noncontrib), save=True)

        assert_false(self.preprint.is_published)

    def test_read_cannot_publish(self):
        assert_false(self.preprint.is_published)

        with assert_raises(PermissionsError):
            self.preprint.set_published(True, auth=Auth(self.read_contrib), save=True)

        assert_false(self.preprint.is_published)

    def test_write_cannot_publish(self):
        assert_false(self.preprint.is_published)

        with assert_raises(PermissionsError):
            self.preprint.set_published(True, auth=Auth(self.write_contrib), save=True)

        assert_false(self.preprint.is_published)

    def test_admin_can_publish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

    def test_admin_cannot_unpublish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

        with assert_raises(ValueError) as e:
            self.preprint.set_published(False, auth=Auth(self.user), save=True)

        assert_in('Cannot unpublish', e.exception.message)

    def test_set_title_permissions(self):
        original_title = self.preprint.title
        new_title = 'My new preprint title'

        # noncontrib
        with assert_raises(PermissionsError):
            self.preprint.set_title(new_title, auth=Auth(self.noncontrib), save=True)
        assert_equal(self.preprint.title, original_title)

        # read
        with assert_raises(PermissionsError):
            self.preprint.set_title(new_title, auth=Auth(self.read_contrib), save=True)
        assert_equal(self.preprint.title, original_title)

        # write
        self.preprint.set_title(new_title, auth=Auth(self.write_contrib), save=True)
        assert_equal(self.preprint.title, new_title)

        # admin
        self.preprint.title = original_title
        self.preprint.save()
        self.preprint.set_title(new_title, auth=Auth(self.user), save=True)
        assert_equal(self.preprint.title, new_title)

    def test_set_abstract_permissions(self):
        original_abstract = self.preprint.description
        new_abstract = 'This is my preprint abstract'

        # noncontrib
        with assert_raises(PermissionsError):
            self.preprint.set_description(new_abstract, auth=Auth(self.noncontrib), save=True)
        assert_equal(self.preprint.description, original_abstract)

        # read
        with assert_raises(PermissionsError):
            self.preprint.set_description(new_abstract, auth=Auth(self.read_contrib), save=True)
        assert_equal(self.preprint.description, original_abstract)

        # write
        self.preprint.set_description(new_abstract, auth=Auth(self.write_contrib), save=True)
        assert_equal(self.preprint.description, new_abstract)

        # admin
        self.preprint.description = original_abstract
        self.preprint.save()
        self.preprint.set_description(new_abstract, auth=Auth(self.user), save=True)
        assert_equal(self.preprint.description, new_abstract)

    def test_set_privacy(self):
        # Not currently exposed, but adding is_public field for legacy preprints and spam
        self.preprint.is_public = False
        self.preprint.save()

        # noncontrib
        with assert_raises(PermissionsError):
            self.preprint.set_privacy('public', auth=Auth(self.noncontrib), save=True)
        assert_false(self.preprint.is_public)

        # read
        with assert_raises(PermissionsError):
            self.preprint.set_privacy('public', auth=Auth(self.read_contrib), save=True)
        assert_false(self.preprint.is_public)

        # write
        self.preprint.set_privacy('public', auth=Auth(self.write_contrib), save=True)
        assert_true(self.preprint.is_public)

        # admin
        self.preprint.is_public = False
        self.preprint.save()
        self.preprint.set_privacy('public', auth=Auth(self.user), save=True)
        assert_true(self.preprint.is_public)

    def test_set_supplemental_node_project_permissions(self):
        # contributors have proper permissions on preprint, but not supplementary_node
        self.preprint.node = None
        self.preprint.save()

        project = ProjectFactory(creator=self.preprint.creator)
        project.add_contributor(self.read_contrib, READ, save=True)
        project.add_contributor(self.write_contrib, WRITE, save=True)

        self.preprint.add_contributor(self.read_contrib, ADMIN, save=True)
        self.preprint.add_contributor(self.write_contrib, ADMIN, save=True)
        self.preprint.add_contributor(self.noncontrib, ADMIN, save=True)

        # noncontrib
        with assert_raises(PermissionsError):
            self.preprint.set_supplemental_node(project, auth=Auth(self.noncontrib), save=True)
        assert self.preprint.node is None

        # read
        with assert_raises(PermissionsError):
            self.preprint.set_supplemental_node(project, auth=Auth(self.read_contrib), save=True)
        assert self.preprint.node is None

        # write
        self.preprint.set_supplemental_node(project, auth=Auth(self.write_contrib), save=True)
        assert self.preprint.node == project

        # admin
        self.preprint.node = None
        self.preprint.save()
        self.preprint.set_supplemental_node(project, auth=Auth(self.user), save=True)
        assert self.preprint.node == project

    def test_set_supplemental_node_preprint_permissions(self):
        # contributors have proper permissions on the supplementary node, but not the preprint
        self.preprint.node = None
        self.preprint.save()

        project = ProjectFactory(creator=self.preprint.creator)
        project.add_contributor(self.read_contrib, ADMIN, save=True)
        project.add_contributor(self.write_contrib, ADMIN, save=True)
        project.add_contributor(self.noncontrib, ADMIN, save=True)

        # noncontrib
        with assert_raises(PermissionsError):
            self.preprint.set_supplemental_node(project, auth=Auth(self.noncontrib), save=True)
        assert self.preprint.node is None

        # read
        with assert_raises(PermissionsError):
            self.preprint.set_supplemental_node(project, auth=Auth(self.read_contrib), save=True)
        assert self.preprint.node is None

        # write
        self.preprint.set_supplemental_node(project, auth=Auth(self.write_contrib), save=True)
        assert self.preprint.node == project

        # admin
        self.preprint.node = None
        self.preprint.save()
        self.preprint.set_supplemental_node(project, auth=Auth(self.user), save=True)
        assert self.preprint.node == project


class TestPreprintProvider(OsfTestCase):
    def setUp(self):
        super(TestPreprintProvider, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.provider_osf = PreprintProviderFactory(_id='osf')
        self.preprint = PreprintFactory(provider=None, is_published=False)
        self.provider = PreprintProviderFactory(name='WWEArxiv')
        self.provider_one = PreprintProviderFactory(name='DoughnutArxiv')
        self.provider_two = PreprintProviderFactory(name='IceCreamArxiv')
        self.subject_one = SubjectFactory(provider=self.provider_one)
        self.subject_osf = SubjectFactory(provider=self.provider_osf)


    def test_add_provider(self):
        assert_not_equal(self.preprint.provider, self.provider)

        self.preprint.provider = self.provider
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, self.provider)

    def test_remove_provider(self):
        self.preprint.provider = None
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, None)

    def test_find_provider(self):
        self.preprint.provider = self.provider
        self.preprint.save()
        self.preprint.reload()

        assert ('branded', self.provider) == find_preprint_provider(self.preprint)

    def test_top_level_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        some_other_provider = PreprintProviderFactory(name='asdfArxiv')
        subj_asdf = SubjectFactory(provider=some_other_provider)

        assert set(self.provider.top_level_subjects) == set([subj_a, subj_b])

    def test_all_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        some_other_provider = PreprintProviderFactory(name='asdfArxiv')
        subj_asdf = SubjectFactory(provider=some_other_provider)

        assert set(self.provider.all_subjects) == set([subj_a, subj_b, subj_aa, subj_ab, subj_ba, subj_bb, subj_aaa])

    def test_highlighted_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        assert self.provider.has_highlighted_subjects is False
        assert set(self.provider.highlighted_subjects) == set([subj_a, subj_b])
        subj_aaa.highlighted = True
        subj_aaa.save()
        assert self.provider.has_highlighted_subjects is True
        assert set(self.provider.highlighted_subjects) == set([subj_aaa])

    def test_change_preprint_provider_custom_taxonomies(self):
        subject_two = SubjectFactory(provider=self.provider_two,
            bepress_subject=self.subject_one.bepress_subject)
        preprint = PreprintFactory(subjects=[[self.subject_one._id]], provider=self.provider_one, creator=self.user)
        subject_problems = preprint.map_subjects_between_providers(self.provider_one, self.provider_two, self.auth)
        preprint.refresh_from_db()
        assert subject_problems == []
        assert subject_two in preprint.subjects.all()

    def test_change_preprint_provider_from_osf(self):
        subject_two = SubjectFactory(provider=self.provider_one,
            bepress_subject=self.subject_osf)
        preprint = PreprintFactory(subjects=[[self.subject_osf._id]], provider=self.provider_osf, creator=self.user)
        subject_problems = preprint.map_subjects_between_providers(self.provider_osf, self.provider_one, self.auth)
        preprint.refresh_from_db()
        assert subject_problems == []
        assert subject_two in preprint.subjects.all()

    def test_change_preprint_provider_to_osf(self):
        subject_two = SubjectFactory(provider=self.provider_one,
            bepress_subject=self.subject_osf)
        preprint = PreprintFactory(subjects=[[subject_two._id]], provider=self.provider_one, creator=self.user)
        subject_problems = preprint.map_subjects_between_providers(self.provider_one, self.provider_osf, self.auth)
        preprint.refresh_from_db()
        assert subject_problems == []
        assert self.subject_osf in preprint.subjects.all()

    def test_change_preprint_provider_problem_subject(self):
        subject_two = SubjectFactory(provider=self.provider_one,
            bepress_subject=self.subject_osf)
        preprint = PreprintFactory(subjects=[[subject_two._id]], provider=self.provider_one, creator=self.user)
        subject_problems = preprint.map_subjects_between_providers(self.provider_one, self.provider_two, self.auth)
        preprint.refresh_from_db()
        assert subject_problems == [subject_two.text]
        assert subject_two in preprint.subjects.all()

class TestPreprintIdentifiers(OsfTestCase):
    def setUp(self):
        super(TestPreprintIdentifiers, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)

    def test_update_or_create_preprint_identifiers_called(self):
        published_preprint = PreprintFactory(is_published=True, creator=self.user)
        with mock.patch.object(published_preprint, 'request_identifier_update') as mock_update_doi:
            update_or_create_preprint_identifiers(published_preprint)
        assert mock_update_doi.called
        assert mock_update_doi.call_count == 1

    @mock.patch('website.settings.CROSSREF_URL', 'http://test.osf.crossref.test')
    def test_correct_doi_client_called(self):
        osf_preprint = PreprintFactory(is_published=True, creator=self.user, provider=PreprintProviderFactory())
        assert isinstance(osf_preprint.get_doi_client(), CrossRefClient)
        ecsarxiv_preprint = PreprintFactory(is_published=True, creator=self.user, provider=PreprintProviderFactory(_id='ecsarxiv'))
        assert isinstance(ecsarxiv_preprint.get_doi_client(), ECSArXivCrossRefClient)

    def test_qatest_doesnt_make_dois(self):
        preprint = PreprintFactory(is_published=True, creator=self.user, provider=PreprintProviderFactory())
        preprint.add_tag('qatest', self.auth)
        assert not request_identifiers(preprint)


@pytest.mark.enable_implicit_clean
class TestOnPreprintUpdatedTask(OsfTestCase):
    def setUp(self):
        super(TestOnPreprintUpdatedTask, self).setUp()
        self.user = AuthUserFactory()
        if len(self.user.fullname.split(' ')) > 2:
            # Prevent unexpected keys ('suffix', 'additional_name')
            self.user.fullname = 'David Davidson'
            self.user.middle_names = ''
            self.user.suffix = ''
            self.user.save()

        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory()
        thesis_provider = PreprintProviderFactory(share_publish_type='Thesis')
        self.thesis = PreprintFactory(provider=thesis_provider)

        for pp in [self.preprint, self.thesis]:

            pp.add_tag('preprint', self.auth, save=False)
            pp.add_tag('spoderman', self.auth, save=False)
            pp.add_unregistered_contributor('BoJack Horseman', 'horse@man.org', Auth(pp.creator))
            pp.add_contributor(self.user, visible=False)
            pp.save()

            pp.creator.given_name = u'ZZYZ'
            if len(pp.creator.fullname.split(' ')) > 2:
                # Prevent unexpected keys ('suffix', 'additional_name')
                pp.creator.fullname = 'David Davidson'
                pp.creator.middle_names = ''
                pp.creator.suffix = ''
            pp.creator.save()

            pp.set_subjects([[SubjectFactory()._id]], auth=Auth(pp.creator))

    def tearDown(self):
        handlers.celery_before_request()
        super(TestOnPreprintUpdatedTask, self).tearDown()

    def test_update_or_enqueue_on_preprint_updated(self):
        # enqueue_postcommit_task automatically calls task in testing now.
        # This test modified to stick something in the postcommit_queue manually so
        # we can test that the queue is modified properly.
        first_subjects = [15]
        args = ()
        kwargs = {'preprint_id': self.preprint._id, 'old_subjects': first_subjects, 'update_share': False, 'share_type': None, 'saved_fields': ['contributors']}
        postcommit_celery_queue().update({'asdfasd': on_preprint_updated.si(*args, **kwargs)})

        second_subjects = [16, 17]
        update_or_enqueue_on_preprint_updated(
            self.preprint._id,
            old_subjects=second_subjects,
            saved_fields={'title': 'Hello'}
        )

        updated_task = get_task_from_postcommit_queue(
            'website.preprints.tasks.on_preprint_updated',
            predicate=lambda task: task.kwargs['preprint_id'] == self.preprint._id
        )
        assert 'title' in updated_task.kwargs['saved_fields']
        assert 'contributors' in  updated_task.kwargs['saved_fields']
        assert set(first_subjects + second_subjects).issubset(updated_task.kwargs['old_subjects'])

    def test_format_preprint(self):
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'throughsubjects', 'subject', 'throughtags', 'tag', 'workidentifier', 'agentidentifier', 'person', 'preprint', 'workrelation', 'creativework'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.title
        assert preprint['description'] == self.preprint.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.is_public or self.preprint.is_preprint_orphan)
        assert preprint['date_updated'] == self.preprint.modified.isoformat()
        assert preprint['date_published'] == self.preprint.date_published.isoformat()

        tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'tag']
        through_tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughtags']
        assert sorted(tag['@id'] for tag in tags) == sorted(tt['tag']['@id'] for tt in through_tags)
        assert sorted(tag['name'] for tag in tags) == ['preprint', 'spoderman']

        subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'subject']
        through_subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughsubjects']
        s_ids = [s['@id'] for s in subjects]
        ts_ids = [ts['subject']['@id'] for ts in through_subjects]
        cs_ids = [i for i in set(s.get('central_synonym', {}).get('@id') for s in subjects) if i]
        for ts in ts_ids:
            assert ts in s_ids
            assert ts not in cs_ids  # Only aliased subjects are connected to self.preprint
        for s in subjects:
            subject = Subject.objects.get(text=s['name'])
            assert s['uri'].endswith('v2/taxonomies/{}/'.format(subject._id))  # This cannot change
        assert set(subject['name'] for subject in subjects) == set([s.text for s in self.preprint.subjects.all()] + [s.bepress_subject.text for s in self.preprint.subjects.filter(bepress_subject__isnull=False)])

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        expected_people = sorted([{
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@type': 'person',
            'given_name': self.preprint.creator.given_name,
            'family_name': self.preprint.creator.family_name,
        }], key=lambda x: x['given_name'])
        for i, p in enumerate(expected_people):
            expected_people[i]['@id'] = people[i]['@id']

        assert people == expected_people

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': u'{}'.format(self.preprint.creator.fullname),
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.preprint.creator.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': u'BoJack Horseman',
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == u'BoJack'][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': u'{}'.format(self.user.fullname),
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.user.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.creator.username,
            self.user.profile_image_url(),
            self.preprint.creator.profile_image_url(),
        ]) | set(user.absolute_url for user in self.preprint.contributors)

        related_work = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creativework')
        assert set(related_work.keys()) == {'@id', '@type'}  # Empty except @id and @type

        osf_doi = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'workidentifier' and 'doi' in v['uri'] and 'osf.io' in v['uri'])
        assert osf_doi['creative_work'] == {'@id': preprint['@id'], '@type': preprint['@type']}

        related_doi = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'workidentifier' and 'doi' in v['uri'])
        assert related_doi['creative_work'] == related_work

        workidentifiers = [nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier']
        assert workidentifiers == [urlparse.urljoin(settings.DOMAIN, self.preprint._id + '/')]

        relation = nodes.pop(nodes.keys()[0])
        assert relation == {'@id': relation['@id'], '@type': 'workrelation', 'related': {'@id': related_work['@id'], '@type': related_work['@type']}, 'subject': {'@id': preprint['@id'], '@type': preprint['@type']}}

        assert nodes == {}

    def test_format_thesis(self):
        res = format_preprint(self.thesis, self.thesis.provider.share_publish_type)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'throughsubjects', 'subject', 'throughtags', 'tag', 'workidentifier', 'agentidentifier', 'person', 'thesis', 'workrelation', 'creativework'}

        nodes = dict(enumerate(res))
        thesis = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'thesis'))
        assert thesis['title'] == self.thesis.title
        assert thesis['description'] == self.thesis.description

    def test_format_preprint_date_modified_node_updated(self):
        self.preprint.save()
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['date_updated'] == self.preprint.modified.isoformat()

    def test_format_preprint_nones(self):
        self.preprint.tags = []
        self.preprint.date_published = None
        self.preprint.article_doi = None
        self.preprint.set_subjects([], auth=Auth(self.preprint.creator))

        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

        assert self.preprint.provider != 'osf'
        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'workidentifier', 'agentidentifier', 'person', 'preprint'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.title
        assert preprint['description'] == self.preprint.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.is_public or self.preprint.is_preprint_orphan or (self.preprint.deleted or False))
        assert preprint['date_updated'] == self.preprint.modified.isoformat()
        assert preprint.get('date_published') is None

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        expected_people = sorted([{
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@type': 'person',
            'given_name': self.preprint.creator.given_name,
            'family_name': self.preprint.creator.family_name,
        }], key=lambda x: x['given_name'])
        for i, p in enumerate(expected_people):
            expected_people[i]['@id'] = people[i]['@id']

        assert people == expected_people

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': self.preprint.creator.fullname,
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.preprint.creator.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': u'BoJack Horseman',
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == u'BoJack'][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': self.user.fullname,
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.user.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.creator.username,
            self.user.profile_image_url(),
            self.preprint.creator.profile_image_url(),
        ]) | set(user.absolute_url for user in self.preprint.contributors)

        workidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier'}
        # URLs should *always* be osf.io/guid/
        assert workidentifiers == set([urlparse.urljoin(settings.DOMAIN, self.preprint._id) + '/', 'https://doi.org/{}'.format(self.preprint.get_identifier('doi').value)])

        assert nodes == {}

    def test_format_preprint_is_deleted(self):
        self.file = OsfStorageFile.create(
            target=self.preprint,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

        CASES = {
            'is_published': (True, False),
            'is_published': (False, True),
            'is_public': (True, False),
            'is_public': (False, True),
            'primary_file': (self.file, False),
            'primary_file': (None, True),
            'deleted': (True, True),
            'deleted': (False, False),
        }
        for key, (value, is_deleted) in CASES.items():
            target = self.preprint
            for k in key.split('.')[:-1]:
                if k:
                    target = getattr(target, k)
            orig_val = getattr(target, key.split('.')[-1])
            setattr(target, key.split('.')[-1], value)

            res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

            preprint = next(v for v in res if v['@type'] == 'preprint')
            assert preprint['is_deleted'] is is_deleted

            setattr(target, key.split('.')[-1], orig_val)

    def test_format_preprint_is_deleted_true_if_qatest_tag_is_added(self):
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        preprint = next(v for v in res if v['@type'] == 'preprint')
        assert preprint['is_deleted'] is False

        self.preprint.add_tag('qatest', auth=self.auth, save=True)

        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        preprint = next(v for v in res if v['@type'] == 'preprint')
        assert preprint['is_deleted'] is True

    def test_unregistered_users_guids(self):
        user = UserFactory.build(is_registered=False)
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {user.absolute_url}

    def test_verified_orcid(self):
        user = UserFactory.build(is_registered=True)
        user.external_identity = {'ORCID': {'fake-orcid': 'VERIFIED'}}
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {'fake-orcid', user.absolute_url, user.profile_image_url()}

    def test_unverified_orcid(self):
        user = UserFactory.build(is_registered=True)
        user.external_identity = {'ORCID': {'fake-orcid': 'SOMETHINGELSE'}}
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {user.absolute_url, user.profile_image_url()}


class TestPreprintSaveShareHook(OsfTestCase):
    def setUp(self):
        super(TestPreprintSaveShareHook, self).setUp()
        self.admin = AuthUserFactory()
        self.auth = Auth(user=self.admin)
        self.provider = PreprintProviderFactory(name='Lars Larson Snowmobiling Experience')
        self.project = ProjectFactory(creator=self.admin, is_public=True)
        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()
        self.file = api_test_utils.create_test_file(self.project, self.admin, 'second_place.pdf')
        self.preprint = PreprintFactory(creator=self.admin, filename='second_place.pdf', provider=self.provider, subjects=[[self.subject._id]], project=self.project, is_published=False)

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_unpublished_not_called(self, mock_on_preprint_updated):
        self.preprint.save()
        assert not mock_on_preprint_updated.called

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_published_called(self, mock_on_preprint_updated):
        self.preprint.set_published(True, auth=self.auth, save=True)
        assert mock_on_preprint_updated.called

    # This covers an edge case where a preprint is forced back to unpublished
    # that it sends the information back to share
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_unpublished_called_forced(self, mock_on_preprint_updated):
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.is_published = False
        self.preprint.save(**{'force_update': True})
        assert_equal(mock_on_preprint_updated.call_count, 2)

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_published_subject_change_called(self, mock_on_preprint_updated):
        self.preprint.is_published = True
        self.preprint.set_subjects([[self.subject_two._id]], auth=self.auth)
        assert mock_on_preprint_updated.called
        call_args, call_kwargs = mock_on_preprint_updated.call_args
        assert 'old_subjects' in mock_on_preprint_updated.call_args[1]
        assert call_kwargs.get('old_subjects') == [self.subject.id]
        assert [self.subject.id] in mock_on_preprint_updated.call_args[1].values()

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_unpublished_subject_change_not_called(self, mock_on_preprint_updated):
        self.preprint.set_subjects([[self.subject_two._id]], auth=self.auth)
        assert not mock_on_preprint_updated.called

    @mock.patch('website.preprints.tasks.requests')
    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'ima_real_website')
    def test_send_to_share_is_true(self, mock_requests):
        self.preprint.provider.access_token = 'Snowmobiling'
        self.preprint.provider.save()
        on_preprint_updated(self.preprint._id)

        assert mock_requests.post.called

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_preprint_contributor_changes_updates_preprints_share(self, mock_on_preprint_updated):
        preprint = PreprintFactory(is_published=True, creator=self.admin)
        assert mock_on_preprint_updated.call_count == 2

        user = AuthUserFactory()
        preprint.primary_file = self.file

        preprint.add_contributor(contributor=user, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 5

        preprint.move_contributor(contributor=user, index=0, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 7

        data = [{'id': self.admin._id, 'permissions': ADMIN, 'visible': True},
                {'id': user._id, 'permissions': WRITE, 'visible': False}]

        preprint.manage_contributors(data, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 9

        preprint.update_contributor(user, READ, True, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 11

        preprint.remove_contributor(contributor=user, auth=self.auth)
        assert mock_on_preprint_updated.call_count == 13

    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.preprints.tasks._async_update_preprint_share.delay')
    @mock.patch('website.preprints.tasks.requests')
    def test_call_async_update_on_500_failure(self, requests, mock_async):
        self.preprint.provider.access_token = 'Snowmobiling'
        requests.post.return_value = MockShareResponse(501)
        update_preprint_share(self.preprint)
        assert mock_async.called

    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.preprints.tasks.send_desk_share_preprint_error')
    @mock.patch('website.preprints.tasks._async_update_preprint_share.delay')
    @mock.patch('website.preprints.tasks.requests')
    def test_no_call_async_update_on_400_failure(self, requests, mock_async, mock_mail):
        self.preprint.provider.access_token = 'Snowmobiling'
        requests.post.return_value = MockShareResponse(400)
        update_preprint_share(self.preprint)
        assert not mock_async.called
        assert mock_mail.called


class TestPreprintConfirmationEmails(OsfTestCase):
    def setUp(self):
        super(TestPreprintConfirmationEmails, self).setUp()
        self.user = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.preprint = PreprintFactory(creator=self.user, project=self.project, provider=PreprintProviderFactory(_id='osf'), is_published=False)
        self.preprint.add_contributor(self.write_contrib, permissions=WRITE)
        self.preprint_branded = PreprintFactory(creator=self.user, is_published=False)

    @mock.patch('website.mails.send_mail')
    def test_creator_gets_email(self, send_mail):
        self.preprint.set_published(True, auth=Auth(self.user), save=True)
        domain = self.preprint.provider.domain or settings.DOMAIN
        send_mail.assert_called_with(
            self.user.email,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            user=self.user,
            mimetype='html',
            provider_url='{}preprints/{}'.format(domain, self.preprint.provider._id),
            domain=domain,
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            workflow=None,
            reviewable=self.preprint,
            is_creator=True,
            provider_name=self.preprint.provider.name,
            no_future_emails=[],
            logo=settings.OSF_PREPRINTS_LOGO,
        )
        assert_equals(send_mail.call_count, 1)

        self.preprint_branded.set_published(True, auth=Auth(self.user), save=True)
        assert_equals(send_mail.call_count, 2)


class TestPreprintOsfStorage(OsfTestCase):
    def setUp(self):
        super(TestPreprintOsfStorage, self).setUp()
        self.user = UserFactory()
        self.session = Session(data={'auth_user_id': self.user._id})
        self.session.save()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session._id)
        self.preprint = PreprintFactory(creator=self.user)
        self.JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))

    def test_create_log(self):
        action = 'file_added'
        path = 'pizza.nii'
        nlog = self.preprint.logs.count()
        self.preprint.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            payload={'metadata': {'path': path, 'materialized': path, 'kind': 'file'}},
        )
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlog + 1)
        assert_equal(
            self.preprint.logs.latest().action,
            '{0}_{1}'.format('osf_storage', action),
        )
        assert_equal(
            self.preprint.logs.latest().params['path'],
            path
        )

    def build_url(self, **kwargs):
        options = {'payload': jwe.encrypt(jwt.encode({'data': dict(dict(
            action='download',
            nid=self.preprint._id,
            provider='osfstorage'), **kwargs),
            'exp': timezone.now() + datetime.timedelta(seconds=500),
        }, settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM), self.JWE_KEY)}
        return self.preprint.api_url_for('get_auth', **options)

    def test_auth_download(self):
        url = self.build_url(cookie=self.cookie)
        res = self.app.get(url, auth=Auth(user=self.user))
        data = jwt.decode(jwe.decrypt(res.json['payload'].encode('utf-8'), self.JWE_KEY), settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM)['data']
        assert_equal(data['credentials'], self.preprint.serialize_waterbutler_credentials())
        assert_equal(data['settings'], self.preprint.serialize_waterbutler_settings())
        expected_url = furl.furl(self.preprint.api_url_for('create_waterbutler_log', _absolute=True, _internal=True))
        observed_url = furl.furl(data['callback_url'])
        observed_url.port = expected_url.port
        assert_equal(expected_url, observed_url)


class TestCheckPreprintAuth(OsfTestCase):

    def setUp(self):
        super(TestCheckPreprintAuth, self).setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)

    def test_has_permission(self):
        res = views.check_access(self.preprint, Auth(user=self.user), 'upload', None)
        assert_true(res)

    def test_not_has_permission_read_published(self):
        res = views.check_access(self.preprint, Auth(), 'download', None)
        assert_true(res)

    def test_not_has_permission_logged_in(self):
        user2 = AuthUserFactory()
        self.preprint.is_published = False
        self.preprint.save()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(user=user2), 'download', None)
        assert_equal(exc_info.exception.code, 403)

    def test_not_has_permission_not_logged_in(self):
        self.preprint.is_published = False
        self.preprint.save()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(), 'download', None)
        assert_equal(exc_info.exception.code, 401)

    def test_check_access_withdrawn_preprint_file(self):
        self.preprint.date_withdrawn = timezone.now()
        self.preprint.save()
        # Unauthenticated
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(), 'download', None)
        assert_equal(exc_info.exception.code, 401)

        # Noncontributor
        user2 = AuthUserFactory()
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(user2), 'download', None)
        assert_equal(exc_info.exception.code, 403)

        # Read contributor
        self.preprint.add_contributor(user2, READ, save=True)
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(user2), 'download', None)
        assert_equal(exc_info.exception.code, 403)

        # Admin contributor
        with assert_raises(HTTPError) as exc_info:
            views.check_access(self.preprint, Auth(self.user), 'download', None)
        assert_equal(exc_info.exception.code, 403)



class TestPreprintOsfStorageLogs(OsfTestCase):

    def setUp(self):
        super(TestPreprintOsfStorageLogs, self).setUp()
        self.user = AuthUserFactory()
        self.user_non_contrib = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user)
        self.file = OsfStorageFile.create(
            target=self.preprint,
            path='/testfile',
            _id='testfile',
            name='testfile',
            materialized_path='/testfile'
        )
        self.file.save()
        self.session = Session(data={'auth_user_id': self.user._id})
        self.session.save()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session._id)

    def build_payload(self, metadata, **kwargs):
        options = dict(
            auth={'id': self.user._id},
            action='create',
            provider='osfstorage',
            metadata=metadata,
            time=time.time() + 1000,
        )
        options.update(kwargs)
        options = {
            key: value
            for key, value in options.iteritems()
            if value is not None
        }
        message, signature = signing.default_signer.sign_payload(options)
        return {
            'payload': message,
            'signature': signature,
        }

    def test_add_log(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path})
        nlogs = self.preprint.logs.count()
        self.app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs + 1)

    def test_add_log_missing_args(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path}, auth=None)
        nlogs = self.preprint.logs.count()
        res = self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs)

    def test_add_log_no_user(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path}, auth={'id': None})
        nlogs = self.preprint.logs.count()
        res = self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs)

    def test_add_log_bad_action(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path}, action='dance')
        nlogs = self.preprint.logs.count()
        res = self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'},
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs)

    def test_action_file_rename(self):
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(
            action='rename',
            metadata={
                'path': 'foo',
                'nid': self.preprint._id,
                'materialized': 'foo',
                'kind': 'file'
            },
            source={
                'materialized': 'foo',
                'provider': 'osfstorage',
                'node': {'_id': self.preprint._id},
                'name': 'new.txt',
                'kind': 'file',
            },
            destination={
                'path': 'foo',
                'materialized': 'foo',
                'provider': 'osfstorage',
                'node': {'_id': self.preprint._id},
                'name': 'old.txt',
                'kind': 'file',
            },
        )
        self.app.put_json(
            url,
            payload,
            headers={'Content-Type': 'application/json'}
        )
        self.preprint.reload()

        assert_equal(
            self.preprint.logs.latest().action,
            'osf_storage_addon_file_renamed',
        )

    def test_action_downloads_contrib(self):
        url = self.preprint.api_url_for('create_waterbutler_log')
        download_actions=('download_file', 'download_zip')
        wb_url = settings.WATERBUTLER_URL + '?version=1'
        for action in download_actions:
            payload = self.build_payload(metadata={'path': '/testfile',
                                                   'nid': self.preprint._id},
                                         action_meta={'is_mfr_render': False},
                                         request_meta={'url': wb_url},
                                         action=action)
            nlogs = self.preprint.logs.count()
            res = self.app.put_json(
                url,
                payload,
                headers={'Content-Type': 'application/json'},
                expect_errors=False,
            )
            assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs)

    def test_add_file_osfstorage_log(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'file', 'path': path})
        nlogs = self.preprint.logs.count()
        self.app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs + 1)
        assert('urls' in self.preprint.logs.filter(action='osf_storage_file_added')[0].params)

    def test_add_folder_osfstorage_log(self):
        path = 'pizza'
        url = self.preprint.api_url_for('create_waterbutler_log')
        payload = self.build_payload(metadata={'materialized': path, 'kind': 'folder', 'path': path})
        nlogs = self.preprint.logs.count()
        self.app.put_json(url, payload, headers={'Content-Type': 'application/json'})
        self.preprint.reload()
        assert_equal(self.preprint.logs.count(), nlogs + 1)
        assert('urls' not in self.preprint.logs.filter(action='osf_storage_file_added')[0].params)


@pytest.mark.django_db
class TestWithdrawnPreprint:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def unpublished_preprint_pre_mod(self):
        return PreprintFactory(provider__reviews_workflow='pre-moderation', is_published=False)

    @pytest.fixture()
    def preprint_pre_mod(self):
        return PreprintFactory(provider__reviews_workflow='pre-moderation')

    @pytest.fixture()
    def unpublished_preprint_post_mod(self):
        return PreprintFactory(provider__reviews_workflow='post-moderation', is_published=False)

    @pytest.fixture()
    def preprint_post_mod(self):
        return PreprintFactory(provider__reviews_workflow='post-moderation')

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def admin(self):
        admin = AuthUserFactory()
        osf_admin = Group.objects.get(name='osf_admin')
        admin.groups.add(osf_admin)
        return admin

    @pytest.fixture()
    def moderator(self, preprint_pre_mod, preprint_post_mod):
        moderator = AuthUserFactory()
        preprint_pre_mod.provider.add_to_group(moderator, 'moderator')
        preprint_pre_mod.provider.save()

        preprint_post_mod.provider.add_to_group(moderator, 'moderator')
        preprint_post_mod.provider.save()

        return moderator

    @pytest.fixture()
    def make_withdrawal_request(self, user):
        def withdrawal_request(target):
            request = PreprintRequestFactory(
                        creator=user,
                        target=target,
                        request_type=RequestTypes.WITHDRAWAL.value,
                        machine_state=DefaultStates.INITIAL.value)
            request.run_submit(user)
            return request
        return withdrawal_request

    @pytest.fixture()
    def crossref_client(self):
        return crossref.CrossRefClient(base_url='http://test.osf.crossref.test')


    def test_withdrawn_preprint(self, user, preprint, unpublished_preprint_pre_mod, unpublished_preprint_post_mod):
        # test_ever_public

        # non-moderated
        assert preprint.ever_public

        # pre-mod
        unpublished_preprint_pre_mod.run_submit(user)

        assert not unpublished_preprint_pre_mod.ever_public
        unpublished_preprint_pre_mod.run_reject(user, 'it')
        unpublished_preprint_pre_mod.reload()
        assert not unpublished_preprint_pre_mod.ever_public
        unpublished_preprint_pre_mod.run_accept(user, 'it')
        unpublished_preprint_pre_mod.reload()
        assert unpublished_preprint_pre_mod.ever_public

        # post-mod
        unpublished_preprint_post_mod.run_submit(user)
        assert unpublished_preprint_post_mod.ever_public

        # test_cannot_set_ever_public_to_False
        unpublished_preprint_pre_mod.ever_public = False
        unpublished_preprint_post_mod.ever_public = False
        preprint.ever_public = False
        with pytest.raises(ValidationError):
            preprint.save()
        with pytest.raises(ValidationError):
            unpublished_preprint_pre_mod.save()
        with pytest.raises(ValidationError):
            unpublished_preprint_post_mod.save()

    def test_crossref_status_is_updated(self, make_withdrawal_request, preprint, preprint_post_mod, preprint_pre_mod, moderator, admin, crossref_client):
        # test_non_moderated_preprint
        assert preprint.verified_publishable
        assert crossref_client.get_status(preprint) == 'public'

        withdrawal_request = make_withdrawal_request(preprint)
        withdrawal_request.run_accept(admin, withdrawal_request.comment)

        assert preprint.is_retracted
        assert preprint.verified_publishable
        assert crossref_client.get_status(preprint) == 'unavailable'

        # test_post_moderated_preprint
        assert preprint_post_mod.verified_publishable
        assert crossref_client.get_status(preprint_post_mod) == 'public'

        withdrawal_request = make_withdrawal_request(preprint_post_mod)
        withdrawal_request.run_accept(moderator, withdrawal_request.comment)

        assert preprint_post_mod.is_retracted
        assert preprint_post_mod.verified_publishable
        assert crossref_client.get_status(preprint_post_mod) == 'unavailable'

        # test_pre_moderated_preprint
        assert preprint_pre_mod.verified_publishable
        assert crossref_client.get_status(preprint_pre_mod) == 'public'

        withdrawal_request = make_withdrawal_request(preprint_pre_mod)
        withdrawal_request.run_accept(moderator, withdrawal_request.comment)

        assert preprint_pre_mod.is_retracted
        assert preprint_pre_mod.verified_publishable
        assert crossref_client.get_status(preprint_pre_mod) == 'unavailable'
