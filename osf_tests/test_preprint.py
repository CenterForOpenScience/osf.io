import mock
import urlparse
import datetime
from django.utils import timezone
import pytest
import pytz

from framework.exceptions import PermissionsError
from website import settings
from framework.auth.core import Auth
from osf.models import Tag, Preprint, PreprintLog, PreprintContributor
from osf.exceptions import PreprintStateError, ValidationError, ValidationValueError
from osf.utils.permissions import READ, WRITE, ADMIN
from .utils import assert_datetime_equal

from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    UserFactory,
    PreprintFactory,
    NodeFactory,
    TagFactory,
    SubjectFactory,
    UnregUserFactory,
    PreprintProviderFactory
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
        assert preprint.node is not None
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

    def test_preprint_doi(self, preprint):
        assert preprint.preprint_doi == '{}osf.io/{}'.format(settings.DOI_NAMESPACE.replace('doi:', ''), preprint._id)

    def test_is_preprint_orphan(self, preprint):
        assert preprint.is_preprint_orphan is False
        preprint.primary_file.is_deleted = True
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

    def test_admin_contributor_ids(self, preprint, user):
        user2 = UserFactory()
        assert len(preprint.admin_contributor_ids) == 1
        assert user._id in preprint.admin_contributor_ids

        preprint.add_permission(user2, ADMIN, save=True)

        assert len(preprint.admin_contributor_ids) == 2
        assert user2._id in preprint.admin_contributor_ids

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
        preprint.add_contributor(write_contrib, auth=Auth(preprint.creator), permission='write')
        preprint.save()
        return write_contrib

    def test_get_subjects(self, preprint):
        subject = preprint.subject_hierarchy[0][0]
        assert preprint.get_subjects()[0][0]['text'] == subject.text
        assert preprint.get_subjects()[0][0]['id'] == subject._id

    def test_set_subjects(self, preprint, auth):
        subject = SubjectFactory()
        subjects = [[subject._id]]
        preprint.set_subjects(subjects, auth)

        assert preprint.get_subjects()[0][0]['text'] == subject.text
        assert preprint.get_subjects()[0][0]['id'] == subject._id

    def test_nonadmin_cannot_set_subjects(self, preprint, subject, write_contrib):
        initial_subjects = list(preprint.subjects.all())
        with pytest.raises(PermissionsError):
            preprint.set_subjects([[subject._id]], auth=Auth(write_contrib))

        preprint.reload()
        assert initial_subjects == list(preprint.subjects.all())

    def test_admin_can_set_subjects(self, preprint, subject):
        initial_subjects = list(preprint.subjects.all())
        preprint.set_subjects([[subject._id]], auth=Auth(preprint.creator))

        preprint.reload()
        assert initial_subjects != list(preprint.subjects.all())


class TestLogging:

    def test_add_preprint_log(self, preprint, auth):
        preprint.add_preprint_log(PreprintLog.CREATED, params={'preprint': preprint._id}, auth=auth)
        preprint.add_preprint_log(PreprintLog.FILE_UPDATED, params={'preprint': preprint._id}, auth=auth)
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

    def test_created_log_is_added(self, fake):
        user = UserFactory()
        preprint = Preprint(
            title=fake.bs(),
            creator=user,
            provider=PreprintProviderFactory()
        )
        preprint.save()
        # Preprint Log
        assert preprint.logs.count() == 1
        first_log = preprint.logs.first()
        assert first_log.action == PreprintLog.CREATED
        params = first_log.params
        assert params['preprint'] == preprint._id
        assert_datetime_equal(first_log.created, preprint.created)


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
                {'user': user1, 'permission': ADMIN, 'visible': True},
                {'user': user2, 'permission': WRITE, 'visible': False}
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
        assert set(preprint.get_permissions(user1)) == set(['admin_preprint', 'write_preprint', 'read_preprint'])
        assert set(preprint.get_permissions(user2)) == set(['read_preprint', 'write_preprint'])
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
                {'user': user1, 'permission': WRITE, 'visible': True},
                {'user': user2, 'permission': WRITE, 'visible': True}
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
            preprint.add_contributor(user, permission=WRITE)

    def test_update_contributor(self, preprint, auth):
        new_contrib = AuthUserFactory()
        preprint.add_contributor(new_contrib, permission=WRITE, auth=auth)

        assert set(preprint.get_permissions(new_contrib)) == set(['read_preprint', 'write_preprint'])
        assert preprint.get_visible(new_contrib) is True

        preprint.update_contributor(
            new_contrib,
            READ,
            False,
            auth=auth
        )
        assert set(preprint.get_permissions(new_contrib)) == set(['read_preprint'])
        assert preprint.get_visible(new_contrib) is False

    def test_update_contributor_non_admin_raises_error(self, preprint, auth):
        non_admin = AuthUserFactory()
        preprint.add_contributor(
            non_admin,
            permission=WRITE,
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

    def test_has_permission_passed_non_contributor_returns_false(self, preprint):
        noncontrib = UserFactory()
        assert preprint.has_permission(noncontrib, READ) is False

    def test_get_permissions(self, preprint):
        user = UserFactory()
        contributor = PreprintContributor.objects.create(
            preprint=preprint, user=user,
        )
        preprint.add_permission(user, READ)
        assert preprint.get_permissions(user) == ['read_preprint']

        preprint.add_permission(user, WRITE)
        assert set(preprint.get_permissions(user)) == set(['read_preprint', 'write_preprint'])
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
        preprint.add_contributor(contrib, permission=WRITE, auth=auth)
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
            preprint.set_permissions(preprint.creator, permission=WRITE)
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
        preprint.add_contributor(contrib, permission='admin', auth=Auth(user=creator))
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
    def test_preprint_on_spammy_preprint(self, preprint):
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
                user.add_system_tag('ham_confirmed')
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

    @mock.patch('osf.models.node.mails.send_mail')
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

    @mock.patch('osf.models.node.mails.send_mail')
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
        assert preprint.is_spammy
        assert preprint.is_public is False

    def test_flag_spam_do_not_make_preprint_private(self, preprint):
        assert preprint.is_public
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', False):
            preprint.flag_spam()
        assert preprint.is_spammy
        assert preprint.is_public

    def test_confirm_spam_makes_preprint_private(self, preprint):
        assert preprint.is_public
        preprint.confirm_spam()
        assert preprint.is_spammy
        assert preprint.is_public is False


# copied from tests/test_models.py
class TestManageContributors:

    def test_contributor_manage_visibility(self, preprint, user, auth):
        reg_user1 = UserFactory()
        #This makes sure manage_contributors uses set_visible so visibility for contributors is added before visibility
        #for other contributors is removed ensuring there is always at least one visible contributor
        preprint.add_contributor(contributor=user, permission=ADMIN, auth=auth)
        preprint.add_contributor(contributor=reg_user1, permission=ADMIN, auth=auth)

        preprint.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': ADMIN, 'visible': True},
                {'id': reg_user1._id, 'permission': ADMIN, 'visible': False},
            ],
            auth=auth,
            save=True
        )
        preprint.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': ADMIN, 'visible': False},
                {'id': reg_user1._id, 'permission': ADMIN, 'visible': True},
            ],
            auth=auth,
            save=True
        )

        assert len(preprint.visible_contributor_ids) == 1

    def test_contributor_set_visibility_validation(self, preprint, user, auth):
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        preprint.add_contributors(
            [
                {'user': reg_user1, 'permission': ADMIN, 'visible': True},
                {'user': reg_user2, 'permission': ADMIN, 'visible': False},
            ]
        )
        print(preprint.visible_contributor_ids)
        with pytest.raises(ValueError) as e:
            preprint.set_visible(user=reg_user1, visible=False, auth=None)
            preprint.set_visible(user=user, visible=False, auth=None)
            assert e.value.message == 'Must have at least one visible contributor'

    def test_manage_contributors_cannot_remove_last_admin_contributor(self, auth, preprint):
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, permission=WRITE, auth=auth)
        preprint.save()
        with pytest.raises(PreprintStateError) as excinfo:
            preprint.manage_contributors(
                user_dicts=[{'id': user2._id,
                             'permission': WRITE,
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
                    'permission': WRITE,
                    'visible': True,
                },
                {
                    'id': user3._id,
                    'permission': WRITE,
                    'visible': True,
                },
                {
                    'id': user._id,
                    'permission': ADMIN,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        assert list(preprint.contributors.all()) == [user2, user3, user]

    def test_manage_contributors_logs_when_users_reorder(self, preprint, user, auth):
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, permission=WRITE, auth=auth)
        preprint.save()
        preprint.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permission': WRITE,
                    'visible': True,
                },
                {
                    'id': user._id,
                    'permission': ADMIN,
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
        preprint.add_contributor(contributor=user2, permission=WRITE, auth=auth)
        preprint.save()
        preprint.manage_contributors(
            user_dicts=[
                {
                    'id': user._id,
                    'permission': ADMIN,
                    'visible': True,
                },
                {
                    'id': user2._id,
                    'permission': READ,
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
            {'id': user._id, 'permission': READ, 'visible': True},
            {'id': preprint.creator._id, 'permission': [READ, WRITE, ADMIN], 'visible': True},
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
            permission=ADMIN,
            save=True
        )
        users = [
            {'id': preprint.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with pytest.raises(PreprintStateError):
            preprint.manage_contributors(
                users, auth=auth, save=True,
            )

    def test_manage_contributors_no_registered_admins(self, preprint, auth):
        unregistered = UnregUserFactory()
        preprint.add_contributor(
            unregistered,
            permission=ADMIN,
            save=True
        )
        users = [
            {'id': preprint.creator._id, 'permission': READ, 'visible': True},
            {'id': unregistered._id, 'permission': ADMIN, 'visible': True},
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
        preprint.add_contributor(read, auth=auth, permission=READ)
        preprint.add_contributor(write, auth=auth, permission=WRITE)
        preprint.add_contributor(admin, auth=auth, permission=ADMIN)
        preprint.add_contributor(nonactive_admin, auth=auth, permission=ADMIN)
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
                {'user': user1, 'permission': WRITE, 'visible': True},
                {'user': user2, 'permission': WRITE, 'visible': True}
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


class TestDOIValidation:

    def test_validate_bad_doi(self):
        with pytest.raises(ValidationError):
            Preprint(article_doi='nope').save()
        with pytest.raises(ValidationError):
            Preprint(article_doi='https://dx.doi.org/10.123.456').save()  # should save the bare DOI, not a URL
        with pytest.raises(ValidationError):
            Preprint(article_doi='doi:10.10.1038/nwooo1170').save()  # should save without doi: prefix

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
        long_title = ''.join('a' for _ in range(201))
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
