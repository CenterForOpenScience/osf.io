import pytest
from django.db import connection

from osf.models.files import BaseFileNode
from osf_tests.factories import ProjectFactory, UserFactory
from api_tests.utils import create_test_file
from addons.osfstorage import settings as osfstorage_settings
from osf.management.commands.handle_duplicate_files import (
    inspect_duplicates,
    remove_duplicates,
    FETCH_DUPLICATES_BY_FILETYPE)

"""
Temporary tests - after partial file uniqueness constraint is added, these tests
will cause IntegrityErrors
"""

OSF_STORAGE_FILE = 'osf.osfstoragefile'
TRASHED = 'osf.trashedfile'
TRASHED_FOLDER = 'osf.trashedfolder'
OSF_STORAGE_FOLDER = 'osf.osfstoragefolder'

def create_version(file, user):
    file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        'bucket': 'us-bucket',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337,
        'contentType': 'img/png'
    }).save()
    return file

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def file_dupe_one(project, user):
    return create_test_file(project, user)

@pytest.fixture()
def file_dupe_two(project, user, file_dupe_one):
    # Creating a test file and then renaming it to have the
    # same name as the first file to artificially create
    # the duplicate file scencario
    file = create_test_file(project, user, 'temp_name')
    file.name = file_dupe_one.name
    file.save()
    return file

@pytest.fixture()
def file_dupe_three(project, user, file_dupe_one):
    file = create_test_file(project, user, 'temp_name')
    file.name = file_dupe_one.name
    file.save()
    return file

@pytest.fixture()
def folder_one(project, user):
    folder = project.get_addon(
        'osfstorage').get_root().append_folder('NewFolder')
    folder.save()
    test_file = folder.append_file('dupe_file')
    create_version(test_file, user)
    return folder

@pytest.fixture()
def folder_two(project, user):
    folder = project.get_addon(
        'osfstorage').get_root().append_folder('temp_name')
    folder.name = 'NewFolder'
    folder.save()
    test_file = folder.append_file('dupe_file')
    create_version(test_file, user)
    return folder


@pytest.mark.django_db
class TestHandleDuplicates:

    def test_does_not_remove_non_duplicates(self, app, project, user, file_dupe_one):
        create_test_file(project, user, 'non dupe')
        assert project.files.count() == 2

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FILE])
            duplicate_files = cursor.fetchall()
        assert duplicate_files == []
        remove_data = inspect_duplicates(duplicate_files)
        assert remove_data == []

        remove_duplicates(remove_data, OSF_STORAGE_FILE)
        assert project.files.count() == 2

    def test_remove_duplicate_files(self, app, project, user, file_dupe_one, file_dupe_two, file_dupe_three):
        assert project.files.count() == 3
        guid_two = file_dupe_two.get_guid()
        guid_three = file_dupe_three.get_guid()

        assert guid_two.referent == file_dupe_two
        assert guid_three.referent == file_dupe_three

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FILE])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 2
        assert remove_data[0]['to_remove'] == file_dupe_two._id
        assert remove_data[0]['preserving'] == file_dupe_one._id
        assert remove_data[0]['guid_to_repoint'] == guid_two._id

        assert remove_data[1]['to_remove'] == file_dupe_three._id
        assert remove_data[1]['preserving'] == file_dupe_one._id
        assert remove_data[1]['guid_to_repoint'] == guid_three._id

        remove_duplicates(remove_data, OSF_STORAGE_FILE)

        assert project.files.count() == 1

        # reloading trashedfiles
        file_dupe_two = BaseFileNode.objects.get(_id=file_dupe_two._id)
        file_dupe_three = BaseFileNode.objects.get(_id=file_dupe_three._id)

        # asserting all but one dupe has been marked as trashed
        assert file_dupe_one.type == OSF_STORAGE_FILE
        assert file_dupe_two.type == TRASHED
        assert file_dupe_three.type == TRASHED

        guid_two.reload()
        guid_three.reload()

        # Assert deleted duplicates' guids were repointed to the remaining file
        assert guid_two.referent == file_dupe_one
        assert guid_three.referent == file_dupe_one

    def test_remove_duplicate_files_with_different_history(self, app, project, user):
        folder = project.get_addon('osfstorage').get_root()

        file_one = folder.append_file('test_file')
        file_two = folder.append_file('temp_name')
        file_two.name = 'test_file'
        file_two.save()
        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FILE])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        # No version or history information, so marked as needing manual deletion
        assert len(remove_data) == 0

        file_one._history = {'commits': '12334'}
        file_one.save()

        remove_data = inspect_duplicates(duplicate_files)
        # _history differs
        assert len(remove_data) == 0

        file_two._history = {'commits': '12334'}
        file_two.save()
        remove_data = inspect_duplicates(duplicate_files)
        # _history same
        assert len(remove_data) == 1

    def test_remove_duplicate_folders(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        file_one = folder_one.children.first()
        file_two = folder_two.children.first()

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 1
        assert remove_data[0]['to_remove'] == folder_two._id
        assert remove_data[0]['preserving'] == folder_one._id
        assert remove_data[0]['guid_to_repoint'] is None

        remove_duplicates(remove_data, OSF_STORAGE_FILE)
        assert project.files.count() == 1

        # reloading trashedfiles
        file_two = BaseFileNode.objects.get(_id=file_two._id)
        folder_two = BaseFileNode.objects.get(_id=folder_two._id)

        # asserting all but one dupe has been marked as trashed
        assert file_one.type == OSF_STORAGE_FILE
        assert file_two.type == TRASHED
        assert folder_one.type == OSF_STORAGE_FOLDER
        assert folder_two.type == TRASHED_FOLDER

    def test_does_not_remove_duplicate_folders_with_extra_files(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        # Add an extra file to the second folder so their contents differ
        folder_two.append_file('another file')

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

    def test_does_not_remove_duplicate_folders_where_first_has_extra_files(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        # Add an extra file to the first folder so their contents differ
        folder_one.append_file('another file')

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

    def test_does_not_remove_duplicate_folders_with_different_contents(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        # Add different files to each folder
        folder_one.append_file('another file')
        folder_two.append_file('hello')

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

    def test_does_not_remove_duplicate_folders_with_different_fileversions_count(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        folder_one.append_file('another file')
        file = folder_two.append_file('another file')
        # Add an extra version to the second file
        create_version(file, user)

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()
        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

    def test_does_not_remove_duplicate_folders_with_different_fileversions_content(self, app, project, user, folder_one, folder_two):
        # The single file in folder one and folder two are being counted here
        assert project.files.count() == 2
        file_one = folder_one.append_file('another file')
        file_two = folder_two.append_file('another file')
        # Add an extra version to the second file
        create_version(file_one, user)
        create_version(file_two, user)
        version_two = file_two.versions.first()
        version_two.location['bucket'] = 'canada-bucket'
        version_two.save()

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()
        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

        version_two.location['bucket'] = 'us-bucket'
        version_two.location['object'] = 'abcdefg'
        version_two.save()

        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 0

    def test_removes_duplicate_folders_with_deeply_nested_duplicate_contents(self, app, project, user, folder_one, folder_two):
        sub_folder_one = folder_one.append_folder('Test folder')
        sub_folder_two = folder_two.append_folder('Test folder')
        sub_file_one = sub_folder_one.append_file('sub file')
        sub_file_two = sub_folder_two.append_file('sub file')
        create_version(sub_file_one, user)
        create_version(sub_file_two, user)

        assert project.files.count() == 4

        with connection.cursor() as cursor:
            cursor.execute(FETCH_DUPLICATES_BY_FILETYPE, [OSF_STORAGE_FOLDER])
            duplicate_files = cursor.fetchall()
        remove_data = inspect_duplicates(duplicate_files)
        assert len(remove_data) == 1
        assert remove_data[0]['to_remove'] == folder_two._id
        assert remove_data[0]['preserving'] == folder_one._id
        assert remove_data[0]['guid_to_repoint'] is None

        remove_duplicates(remove_data, OSF_STORAGE_FOLDER)
        assert project.files.count() == 2

        # reloading files/folders
        folder_one = BaseFileNode.objects.get(_id=folder_one._id)
        folder_two = BaseFileNode.objects.get(_id=folder_two._id)
        sub_folder_one = BaseFileNode.objects.get(_id=sub_folder_one._id)
        sub_folder_two = BaseFileNode.objects.get(_id=sub_folder_two._id)
        sub_file_one = BaseFileNode.objects.get(_id=sub_file_one._id)
        sub_file_two = BaseFileNode.objects.get(_id=sub_file_two._id)

        # asserting folder two contents have been trashed
        assert folder_one.type == OSF_STORAGE_FOLDER
        assert folder_two.type == TRASHED_FOLDER
        assert sub_folder_one.type == OSF_STORAGE_FOLDER
        assert sub_folder_two.type == TRASHED_FOLDER
        assert sub_file_one.type == OSF_STORAGE_FILE
        assert sub_file_two.type == TRASHED
