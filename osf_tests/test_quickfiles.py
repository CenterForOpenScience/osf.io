import mock
import pytest

from framework.auth.core import Auth
from osf.models import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile
from osf.exceptions import MaxRetriesError, NodeStateError
from api_tests.utils import create_test_file
from tests.utils import assert_items_equal
from tests.base import get_default_metaschema

from . import factories

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    return factories.UserFactory()


@pytest.fixture()
def project(user, auth, fake):
    ret = factories.ProjectFactory(creator=user)
    ret.add_tag(fake.word(), auth=auth)
    return ret


@pytest.fixture()
def auth(user):
    return Auth(user)


@pytest.mark.enable_quickfiles_creation
class TestQuickFilesNode:

    @pytest.fixture()
    def quickfiles(self, user):
        return QuickFilesNode.objects.get(creator=user)

    def test_new_user_has_quickfiles(self):
        user = factories.UserFactory()
        quickfiles_node = QuickFilesNode.objects.filter(creator=user)
        assert quickfiles_node.exists()

    def test_quickfiles_is_public(self, quickfiles):
        assert quickfiles.is_public

    def test_quickfiles_has_creator_as_contributor(self, quickfiles, user):
        assert quickfiles.creator == user
        assert quickfiles.is_contributor(user)

    def test_quickfiles_cannot_have_other_contributors(self, quickfiles, auth):
        another_user = factories.UserFactory()
        with pytest.raises(NodeStateError):
            quickfiles.add_contributor(contributor=another_user, auth=auth)

    def test_quickfiles_cannot_be_private(self, quickfiles):
        with pytest.raises(NodeStateError):
            quickfiles.set_privacy('private')
        assert quickfiles.is_public

    def test_quickfiles_cannot_be_deleted(self, quickfiles, auth):
        with pytest.raises(NodeStateError):
            quickfiles.remove_node(auth=auth)
        assert not quickfiles.is_deleted

    def test_quickfiles_cannot_be_registered(self, quickfiles, auth):
        with pytest.raises(NodeStateError):
            quickfiles.register_node(get_default_metaschema(), auth, '', None)

    def test_quickfiles_cannot_be_forked(self, quickfiles, auth):
        with pytest.raises(NodeStateError):
            quickfiles.fork_node(auth=auth)

    def test_quickfiles_cannot_be_used_as_template(self, quickfiles, auth):
        with pytest.raises(NodeStateError):
            quickfiles.use_as_template(auth=auth)

    def test_quickfiles_cannot_have_other_addons(self, quickfiles, auth):
        with pytest.raises(NodeStateError):
            quickfiles.add_addon('github', auth=auth)

    def test_quickfiles_title_has_users_fullname(self, quickfiles, user):
        plain_user = factories.UserFactory(fullname='Kenny Omega')
        s_user = factories.UserFactory(fullname='Cody Runnels')

        plain_user_quickfiles = QuickFilesNode.objects.get(creator=plain_user)
        s_user_quickfiles = QuickFilesNode.objects.get(creator=s_user)

        assert plain_user_quickfiles.title == "Kenny Omega's Quick Files"
        assert s_user_quickfiles.title == "Cody Runnels' Quick Files"

    def test_quickfiles_title_updates_when_fullname_updated(self, quickfiles, user):
        assert user.fullname in quickfiles.title

        new_name = 'Hiroshi Tanahashi'
        user.fullname = new_name
        user.save()

        quickfiles.refresh_from_db()
        assert new_name in quickfiles.title

    def test_quickfiles_moves_files_on_merge(self, user, quickfiles):
        create_test_file(quickfiles, user, filename='Guerrillas_of_Destiny.pdf')
        other_user = factories.UserFactory()
        other_quickfiles = QuickFilesNode.objects.get(creator=other_user)
        create_test_file(other_quickfiles, user, filename='Young_Bucks.pdf')

        user.merge_user(other_user)
        user.save()

        stored_files = OsfStorageFile.objects.all()
        assert stored_files.count() == 2
        for stored_file in stored_files:
            assert stored_file.target == quickfiles
            assert stored_file.parent.target == quickfiles

    def test_quickfiles_moves_files_on_triple_merge_with_name_conflict(self, user, quickfiles):
        name = 'Woo.pdf'
        other_user = factories.UserFactory()
        third_user = factories.UserFactory()

        create_test_file(quickfiles, user, filename=name)
        create_test_file(QuickFilesNode.objects.get(creator=other_user), other_user, filename=name)
        create_test_file(QuickFilesNode.objects.get(creator=third_user), third_user, filename=name)

        user.merge_user(other_user)
        user.save()

        user.merge_user(third_user)
        user.save()

        actual_filenames = list(OsfStorageFile.objects.all().values_list('name', flat=True))
        expected_filenames = ['Woo.pdf', 'Woo (1).pdf', 'Woo (2).pdf']

        assert_items_equal(actual_filenames, expected_filenames)

    def test_quickfiles_moves_files_on_triple_merge_with_name_conflict_with_digit(self, user, quickfiles):
        name = 'Woo (1).pdf'
        other_user = factories.UserFactory()
        third_user = factories.UserFactory()

        create_test_file(quickfiles, user, filename=name)
        create_test_file(QuickFilesNode.objects.get(creator=other_user), other_user, filename=name)
        create_test_file(QuickFilesNode.objects.get(creator=third_user), third_user, filename=name)

        user.merge_user(other_user)
        user.save()

        user.merge_user(third_user)
        user.save()

        actual_filenames = list(OsfStorageFile.objects.all().values_list('name', flat=True))
        expected_filenames = ['Woo (1).pdf', 'Woo (2).pdf', 'Woo (3).pdf']
        assert_items_equal(actual_filenames, expected_filenames)

    def test_quickfiles_moves_destination_quickfiles_has_weird_numbers(self, user, quickfiles):
        other_user = factories.UserFactory()
        third_user = factories.UserFactory()

        create_test_file(quickfiles, user, filename='Woo (1).pdf')
        create_test_file(quickfiles, user, filename='Woo (3).pdf')

        create_test_file(QuickFilesNode.objects.get(creator=other_user), other_user, filename='Woo.pdf')
        create_test_file(QuickFilesNode.objects.get(creator=third_user), other_user, filename='Woo.pdf')

        user.merge_user(other_user)
        user.save()

        user.merge_user(third_user)
        user.save()

        actual_filenames = list(quickfiles.files.all().values_list('name', flat=True))
        expected_filenames = ['Woo.pdf', 'Woo (1).pdf', 'Woo (2).pdf', 'Woo (3).pdf']

        assert_items_equal(actual_filenames, expected_filenames)

    @mock.patch('osf.models.user.MAX_QUICKFILES_MERGE_RENAME_ATTEMPTS', 1)
    def test_quickfiles_moves_errors_after_max_renames(self, user, quickfiles):
        create_test_file(quickfiles, user, filename='Woo (1).pdf')
        create_test_file(quickfiles, user, filename='Woo (2).pdf')

        other_user = factories.UserFactory()
        create_test_file(QuickFilesNode.objects.get(creator=other_user), other_user, filename='Woo (1).pdf')

        with pytest.raises(MaxRetriesError):
            user.merge_user(other_user)
