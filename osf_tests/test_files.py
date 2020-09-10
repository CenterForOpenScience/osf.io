import pytest

from django.contrib.contenttypes.models import ContentType
from nose.tools import assert_raises

from addons.osfstorage.models import NodeSettings
from addons.osfstorage import settings as osfstorage_settings
from osf.models import BaseFileNode, Folder, File, FileVersion
from osf_tests.factories import (
    UserFactory,
    ProjectFactory,
    RegionFactory
)
from osf_tests.utils import create_mock_gcs_client

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)


@pytest.fixture()
def create_test_file(fake):
    # TODO: Copied from api_tests/utils.py. DRY this up.
    def _create_test_file(target, user=None, filename=None, create_guid=True):
        filename = filename or fake.file_name()
        user = user or target.creator
        osfstorage = target.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        test_file = root_node.append_file(filename)

        if create_guid:
            test_file.get_guid(create=True)

        test_file.create_version(user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
            'bucket': 'bucket'
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()
        return test_file
    return _create_test_file


def test_active_manager_does_not_return_trashed_file_nodes(project, create_test_file):
    create_test_file(target=project)
    deleted_file = create_test_file(target=project)
    deleted_file.delete(user=project.creator, save=True)
    content_type_for_query = ContentType.objects.get_for_model(project)
    # root folder + file + deleted_file = 3 BaseFileNodes
    assert BaseFileNode.objects.filter(target_object_id=project.id, target_content_type=content_type_for_query).count() == 3
    # root folder + file = 2 BaseFileNodes
    assert BaseFileNode.active.filter(target_object_id=project.id, target_content_type=content_type_for_query).count() == 2

def test_folder_update_calls_folder_update_method(project, create_test_file):
    file = create_test_file(target=project)
    parent_folder = file.parent
    # the folder update method should be the Folder.update method
    assert parent_folder.__class__.update == Folder.update
    # the folder update method should not be the File update method
    assert parent_folder.__class__.update != File.update
    # the file update method should be the File update method
    assert file.__class__.update == File.update


def test_file_update_respects_region(project, user, create_test_file):
    test_file = create_test_file(target=project)
    version = test_file.versions.first()
    original_region = project.osfstorage_region
    assert version.region == original_region

    # update the region on the project, ensure the new version has the new region
    node_settings = NodeSettings.objects.get(owner=project.id)
    new_region = RegionFactory()
    node_settings.region = new_region
    node_settings.save()
    test_file.save()

    new_version = test_file.create_version(
        user, {
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
            'object': '07d80a',
        }, {
            'sha256': 'existing',
        }
    )
    assert new_region != original_region
    assert new_version.region == new_region

def test_file_purged(project, create_test_file):
    test_file = create_test_file(target=project)
    version = test_file.versions.first()
    mock_client = create_mock_gcs_client()

    # Sanity
    assert test_file.purged is None
    assert version.purged is None

    # False attempt
    with assert_raises(AttributeError):
        freed = test_file._purge(client=mock_client)

    version.refresh_from_db()
    assert test_file.purged is None
    assert version.purged is None

    # Trash file
    test_file.delete()
    # Erroneous call
    freed = test_file._purge()

    version.refresh_from_db()
    assert freed == 0
    assert test_file.purged is None
    assert version.purged is None

    # Successful call
    freed = test_file._purge(client=mock_client)

    version.refresh_from_db()
    assert freed == version.size
    assert test_file.purged is not None
    assert version.purged is not None

def test_file_dupe_purged(project, create_test_file):
    test_file_0 = create_test_file(target=project)
    version_0 = test_file_0.versions.first()
    version_0.location['object'] = 'deadbeef'
    version_0.save()
    test_file_1 = create_test_file(target=project)
    version_1 = test_file_1.versions.first()
    version_1.location['object'] = 'deadbeef'
    version_1.save()
    mock_client = create_mock_gcs_client()

    # Sanity
    assert version_0.id != version_1.id
    assert version_0.location['object'] == version_1.location['object']
    assert FileVersion.objects.filter(location__object='deadbeef').count() == 2

    # Trash file_0
    test_file_0.delete()

    freed = test_file_0._purge(client=mock_client)

    version_0.refresh_from_db()
    assert freed == 0
    assert test_file_0.purged is not None
    assert version_0.purged is None

    # Trash file_1
    test_file_1.delete()

    freed = test_file_1._purge(client=mock_client)

    version_1.refresh_from_db()
    assert freed == version_1.size
    assert test_file_1.purged is not None
    assert version_1.purged is not None

def test_file_shared_purged(project, create_test_file):
    test_file_0 = create_test_file(target=project)
    version_0 = test_file_0.versions.first()
    version_0.location['object'] = 'deadbeef'
    version_0.save()
    test_file_1 = create_test_file(target=project)
    test_file_1.add_version(version_0)
    mock_client = create_mock_gcs_client()

    # Sanity
    assert test_file_1 in version_0.basefilenode_set.all()

    # Trash file_0
    test_file_0.delete()

    freed = test_file_0._purge(client=mock_client)

    version_0.refresh_from_db()
    assert freed == 0
    assert test_file_0.purged is not None
    assert version_0.purged is None

    # Trash file_1
    test_file_1.delete()

    freed = test_file_1._purge(client=mock_client)

    version_0.refresh_from_db()
    assert freed == sum(list(test_file_1.versions.values_list('size', flat=True)))
    assert test_file_1.purged is not None
    assert version_0.purged is not None
