import pytest
from unittest import mock

from addons.osfstorage import settings as osfstorage_settings
from osf.management.commands.repair_recovered_preprint_regions import repair_preprint_regions
from osf.models import FileVersion
from osf_tests.factories import PreprintFactory, RegionFactory


def make_region(bucket):
    return RegionFactory(waterbutler_settings={'storage': {'provider': 'googlecloud', 'bucket': bucket}})


@pytest.mark.django_db
class TestRepairRecoveredPreprintRegions:

    @pytest.fixture()
    def us(self):
        return make_region('osf-us-1')

    @pytest.fixture()
    def de(self):
        return make_region('osf-de-1')

    @pytest.fixture()
    def preprint(self, de):
        # blob uploaded to the US bucket but the version and preprint were relabeled to de-1 by recovery
        return PreprintFactory()

    def _break(self, preprint, blob_bucket, wrong_region):
        version = preprint.primary_file.versions.order_by('-created').first()
        # shape of a prod location: written by Waterbutler with `bucket` and no `folder`, so it fails
        # `validate_location` and can't go through FileVersion.save()
        location = {
            'host': 'wb-pod', 'bucket': blob_bucket, 'object': 'a' * 64, 'address': None,
            'service': 'googlecloud', 'version': '0.0.1', 'provider': 'googlecloud',
        }
        assert osfstorage_settings.WATERBUTLER_RESOURCE not in location
        FileVersion.objects.filter(pk=version.pk).update(location=location, region=wrong_region)
        type(preprint).objects.filter(id=preprint.id).update(region=wrong_region)
        version.refresh_from_db()
        preprint.reload()
        return version

    def test_relabels_version_and_preprint_to_region_holding_blob(self, preprint, us, de):
        version = self._break(preprint, 'osf-us-1', de)

        stats = repair_preprint_regions([preprint])

        version.refresh_from_db()
        preprint.reload()
        assert version.region_id == us.id
        assert preprint.region_id == us.id
        assert stats['versions_fixed'] == 1
        assert stats['preprints_fixed'] == 1

    def test_dry_run_changes_nothing(self, preprint, us, de):
        version = self._break(preprint, 'osf-us-1', de)

        stats = repair_preprint_regions([preprint], dry_run=True)

        version.refresh_from_db()
        preprint.reload()
        assert version.region_id == de.id
        assert preprint.region_id == de.id
        assert stats['versions_fixed'] == 1

    def test_is_idempotent(self, preprint, us, de):
        self._break(preprint, 'osf-us-1', de)
        repair_preprint_regions([preprint])

        stats = repair_preprint_regions([preprint])

        assert stats['versions_fixed'] == 0
        assert stats['preprints_fixed'] == 0

    def test_purged_version_is_left_alone(self, preprint, us, de):
        version = self._break(preprint, 'osf-us-1', de)
        version.purged = preprint.created
        version.save()

        stats = repair_preprint_regions([preprint])

        version.refresh_from_db()
        assert version.region_id == de.id
        assert stats['unresolved'] == 1

    def test_unknown_bucket_without_probe_is_unresolved(self, preprint, us, de):
        version = self._break(preprint, 'some-other-bucket', de)

        stats = repair_preprint_regions([preprint])

        version.refresh_from_db()
        assert version.region_id == de.id
        assert stats['unresolved'] == 1

    def test_probe_finds_region_bucket_holding_blob(self, preprint, us, de):
        version = self._break(preprint, 'unknown', de)
        client = mock.Mock()
        client.bucket.side_effect = lambda name: mock.Mock(
            blob=lambda obj: mock.Mock(exists=lambda: name == 'osf-us-1')
        )

        repair_preprint_regions([preprint], client=client)

        version.refresh_from_db()
        assert version.region_id == us.id
