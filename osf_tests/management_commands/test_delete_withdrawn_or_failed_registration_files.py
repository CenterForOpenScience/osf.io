import pytest
from osf_tests.factories import WithdrawnRegistrationFactory

from osf.management.commands.delete_withdrawn_or_failed_registration_files import (
    mark_withdrawn_files_as_deleted,
    mark_failed_registration_files_as_deleted,
)
from website.settings import STUCK_FILES_DELETE_TIMEOUT
from addons.osfstorage import settings as addon_settings
from osf_tests.factories import RegistrationFactory
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestPurgedFiles:

    @pytest.fixture()
    def withdrawn_registration(self):
        retraction = WithdrawnRegistrationFactory()
        registration = retraction.target_registration
        return registration

    @pytest.fixture()
    def stuck_registration(self):
        registration = RegistrationFactory(archive=True)
        # Make the registration "stuck"
        archive_job = registration.archive_job
        archive_job.datetime_initiated = (timezone.now() - STUCK_FILES_DELETE_TIMEOUT - timedelta(hours=1))
        archive_job.save()
        return registration

    @pytest.fixture
    def stuck_file(self, stuck_registration):
        file = stuck_registration.get_addon('osfstorage').root_node.append_file('Hurts')
        file.create_version(
            stuck_registration.creator,
            {
                'service': 'Fulgham',
                addon_settings.WATERBUTLER_RESOURCE: 'osf',
                'object': 'Sanders',
                'bucket': 'Hurts',
            }, {
                'size': 1234,
                'contentType': 'text/plain'
            })
        file.save()
        return file

    @pytest.fixture
    def withdrawn_file(self, withdrawn_registration):
        file = withdrawn_registration.get_addon('osfstorage').root_node.append_file('Hurts')
        file.create_version(
            withdrawn_registration.creator,
            {
                'service': 'Fulgham',
                addon_settings.WATERBUTLER_RESOURCE: 'osf',
                'object': 'Sanders',
                'bucket': 'Hurts',
            }, {
                'size': 1234,
                'contentType': 'text/plain'
            })
        file.save()
        return file

    def test_withdrawn_registration_files(self, withdrawn_registration, withdrawn_file):
        # Marks files as deleted
        assert withdrawn_registration.files.filter(deleted__isnull=True).count() == 1
        mark_withdrawn_files_as_deleted(dry_run=False, batch_size=1)
        assert withdrawn_registration.files.filter(deleted__isnull=True).count() == 0

    def test_failed_registration_files(self, stuck_registration, stuck_file):
        # Marks files as deleted
        assert stuck_registration.files.filter(deleted__isnull=True).count() == 1
        mark_failed_registration_files_as_deleted(dry_run=False, batch_size=1)
        assert stuck_registration.files.filter(deleted__isnull=True).count() == 0
