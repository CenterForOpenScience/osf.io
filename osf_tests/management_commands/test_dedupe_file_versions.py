import pytest
from django.core.management import call_command

from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.tests.factories import FileVersionFactory
from osf.models import BaseFileVersionsThrough, FileVersion
from osf_tests.factories import ProjectFactory


def make_location(obj):
    return {
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        'object': obj,
    }


@pytest.mark.django_db
class TestDedupeFileVersions:

    @pytest.fixture()
    def file_node(self):
        project = ProjectFactory()
        return project.get_addon('osfstorage').get_root().append_file('dupes.txt')

    @pytest.fixture()
    def add_duplicate_version(self, file_node):
        def _add_duplicate_version(identifier, location):
            version = FileVersionFactory(identifier=identifier, location=location)
            file_node.add_version(version)
            return version
        return _add_duplicate_version

    def test_dry_run_leaves_duplicates_untouched(self, file_node, add_duplicate_version):
        add_duplicate_version('2', make_location('object-a'))
        add_duplicate_version('2', make_location('object-b'))

        call_command('dedupe_file_versions')

        assert file_node.versions.filter(identifier='2').count() == 2

    def test_apply_unlinks_duplicate_keeping_earliest(self, file_node, add_duplicate_version):
        version_to_keep = add_duplicate_version('2', make_location('object-a'))
        extra = add_duplicate_version('2', make_location('object-b'))

        call_command('dedupe_file_versions', dry_run=False)

        remaining = list(file_node.versions.filter(identifier='2'))
        assert remaining == [version_to_keep]
        assert FileVersion.objects.filter(id=extra.id).exists()
        assert not BaseFileVersionsThrough.objects.filter(basefilenode=file_node, fileversion=extra).exists()

    def test_leaves_non_duplicate_versions_alone(self, file_node, add_duplicate_version):
        add_duplicate_version('1', make_location('object-1'))
        add_duplicate_version('2', make_location('object-2'))

        call_command('dedupe_file_versions', dry_run=False)

        assert file_node.versions.count() == 2

    def test_apply_deletes_every_duplicate_but_the_keeper(self, file_node, add_duplicate_version):
        version_to_keep = add_duplicate_version('2', make_location('object-a'))
        extra_1 = add_duplicate_version('2', make_location('object-b'))
        extra_2 = add_duplicate_version('2', make_location('object-c'))

        assert BaseFileVersionsThrough.objects.filter(basefilenode=file_node).count() == 3

        call_command('dedupe_file_versions', dry_run=False)

        assert BaseFileVersionsThrough.objects.filter(basefilenode=file_node).count() == 1
        assert list(file_node.versions.all()) == [version_to_keep]
        for extra in (extra_1, extra_2):
            assert not BaseFileVersionsThrough.objects.filter(basefilenode=file_node, fileversion=extra).exists()
