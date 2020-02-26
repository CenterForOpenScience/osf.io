import mock
import pytest

from addons.osfstorage.models import OsfStorageFile
from osf.exceptions import DraftRegistrationStateError, MaxRetriesError, NodeStateError, MaxRetriesError
from api_tests.utils import create_test_quickfile, create_test_file, create_test_folder
from tests.utils import assert_equals
from tests.base import get_default_metaschema

from django.contrib.contenttypes.models import ContentType

from osf.exceptions import UserStateError
from osf_tests.factories import AuthUserFactory, ProjectFactory


def bad_content_type():
    return ContentType.objects.get_for_model(OsfStorageFile)


def bad_file_node():
    node = ProjectFactory()
    return create_test_file(node, node.creator)


def bad_node():
    return ProjectFactory()


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestQuickFolder:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user2(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user3(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def file_node(self, user, project):
        return create_test_file(project, user, 'test file')

    @pytest.fixture()
    def folder_node(self, user, project):
        return create_test_folder(project, 'test folder')

    def test_quickfiles_cannot_be_registered(self, quickfiles, auth):
        with pytest.raises(DraftRegistrationStateError):
            quickfiles.register_node(get_default_metaschema(), auth, factories.DraftRegistrationFactory(branched_from=quickfiles), None)

    def test_new_user_has_quickfolder(self, user):
        assert getattr(user, 'quickfolder', False)
        assert user.quickfolder.is_root
        assert user.quickfiles.count() == 0

        # No QuickFolders in nodes
        assert user.nodes.filter(type='osf.quickfolder').count() == 0

        # No old QuickFilesNode in nodes
        assert user.nodes.filter(type='osf.quickfilesnode').count() == 0

    def test_quickfiles_title_has_users_fullname(self):
        plain_user = AuthUserFactory(fullname='Kenny Omega')
        s_user = AuthUserFactory(fullname='Cody Runnels')

        assert plain_user.quickfolder.title == "Kenny Omega's Quick Files"
        assert s_user.quickfolder.title == "Cody Runnels' Quick Files"

    def test_quickfiles_add_file(self, user, file_node):
        file = user.quickfolder.append_file('test')
        assert user.quickfolder.children.count() == 1
        assert user.quickfolder.children.get(name='test') == file

        with pytest.raises(NotImplementedError):
            user.quickfolder.append_folder('test')

    def test_quickfiles_title_updates_when_fullname_updated(self, user):
        new_name = 'Hiroshi Tanahashi'
        user.fullname = new_name
        user.save()

        assert new_name in user.quickfolder.title

    def test_quickfiles_moves_files_on_merge(self, user, user2):
        create_test_quickfile(user, filename='Guerrillas_of_Destiny.pdf')
        create_test_quickfile(user2, filename='Young_Bucks.pdf')

        user.merge_user(user2)
        user.save()

        stored_files = OsfStorageFile.objects.all()
        assert stored_files.count() == 2
        for stored_file in stored_files:
            assert stored_file.target == user
            assert stored_file.parent == user.quickfolder

    def test_quickfiles_moves_files_on_triple_merge_with_name_conflict(self, user, user2, user3):
        name = 'Woo.pdf'

        create_test_quickfile(user, filename=name)
        create_test_quickfile(user2, filename=name)
        create_test_quickfile(user3, filename=name)

        user.merge_user(user2)
        user.save()

        user.merge_user(user3)
        user.save()

        actual_filenames = set(OsfStorageFile.objects.all().values_list('name', flat=True))
        expected_filenames = {'Woo.pdf', 'Woo (1).pdf', 'Woo (2).pdf'}
        assert actual_filenames == expected_filenames

    def test_quickfiles_moves_files_on_triple_merge_with_name_conflict_with_digit(self, user, user2, user3):
        name = 'Woo (1).pdf'

        create_test_quickfile(user, filename=name)
        create_test_quickfile(user2, filename=name)
        create_test_quickfile(user3, filename=name)

        user.merge_user(user2)
        user.save()

        user.merge_user(user3)
        user.save()

        actual_filenames = set(OsfStorageFile.objects.all().values_list('name', flat=True))
        expected_filenames = {'Woo (1).pdf', 'Woo (2).pdf', 'Woo (3).pdf'}
        assert actual_filenames == expected_filenames

    def test_quickfiles_moves_destination_quickfiles_has_weird_numbers(self, user, user2, user3):

        create_test_quickfile(user, filename='Woo (1).pdf')
        create_test_quickfile(user, filename='Woo (3).pdf')

        create_test_quickfile(user2, filename='Woo.pdf')
        create_test_quickfile(user3, filename='Woo.pdf')

        user.merge_user(user2)
        user.save()

        user.merge_user(user3)
        user.save()

        actual_filenames = set(user.quickfiles.all().values_list('name', flat=True))
        expected_filenames = {'Woo.pdf', 'Woo (1).pdf', 'Woo (2).pdf', 'Woo (3).pdf'}

        assert actual_filenames == expected_filenames

    @mock.patch('osf.models.user.MAX_QUICKFILES_MERGE_RENAME_ATTEMPTS', 1)
    def test_quickfiles_moves_errors_after_max_renames(self, user, user2):
        create_test_quickfile(user, filename='Woo (1).pdf')
        create_test_quickfile(user, filename='Woo (2).pdf')

        create_test_quickfile(user2, filename='Woo (1).pdf')

        with pytest.raises(MaxRetriesError):
            user.merge_user(user2)

    def test_quickfiles_cannot_be_deleted(self, user):
        with pytest.raises(UserStateError):
            user.quickfolder.delete()
        assert not user.quickfolder.is_deleted
