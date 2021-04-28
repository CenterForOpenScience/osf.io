import pytest

from osf.management.commands.backfill_egap_provider_metadata import main as backfill_egap_metadata
from osf.models import RegistrationSchema
from osf_tests.factories import RegistrationFactory
from tests.base import OsfTestCase

EGAP_ID_SCHEMA_KEY = 'q3'
REGISTRATION_DATE_SCHEMA_KEY = 'q4'
OLDER_EGAP_ID = 'ABC123'
OLDER_TIMESTAMP = '2020-10-04 08:30:00 -0400'
OLDEST_EGAP_ID = 'XYZ789'
OLDEST_TIMESTAMP = '03/01/2011 - 22:00'


class TestMigrateEgapRegistrationMetadata(OsfTestCase):

    @pytest.fixture
    def older_registration(self):
        schema = RegistrationSchema.objects.get(name='EGAP Registration', version=3)
        registration = RegistrationFactory(schema=schema)
        registration.registration_responses[EGAP_ID_SCHEMA_KEY] = OLDER_EGAP_ID
        registration.registration_responses[REGISTRATION_DATE_SCHEMA_KEY] = OLDER_TIMESTAMP
        registration.save()
        return registration

    @pytest.fixture
    def oldest_registration(self):
        schema = RegistrationSchema.objects.get(name='EGAP Registration', version=2)
        registration = RegistrationFactory(schema=schema)
        registration.registration_responses[EGAP_ID_SCHEMA_KEY] = OLDEST_EGAP_ID
        registration.registration_responses[REGISTRATION_DATE_SCHEMA_KEY] = OLDEST_TIMESTAMP
        registration.save()
        return registration

    @pytest.fixture
    def newer_registration(self):
        schema = RegistrationSchema.objects.get(name='EGAP Registration', version=4)
        registration = RegistrationFactory(schema=schema)
        return registration

    def test_backfill_egap_metadata(
            self, newer_registration, older_registration, oldest_registration):
        assert older_registration.additional_metadata is None
        assert older_registration.registered_date is None
        assert oldest_registration.additional_metadata is None
        assert oldest_registration.registered_date is None

        backfilled_registration_count = backfill_egap_metadata()
        assert backfilled_registration_count == 2

        older_registration.refresh_from_db()
        assert older_registration.additional_metadata['EGAP Registration ID'] == OLDER_EGAP_ID
        expected_older_date_string = '2020-10-04 08:30:00'
        assert older_registration.registered_date.strftime('%Y-%m-%d %H:%M:%S') == expected_older_date_string

        oldest_registration.refresh_from_db()
        assert oldest_registration.additional_metadata['EGAP Registration ID'] == OLDEST_EGAP_ID
        expected_oldest_date_string = '2011-03-01 22:00:00'
        assert oldest_registration.registered_date.strftime('%Y-%m-%d %H:%M:%S') == expected_oldest_date_string

        # Should have been excluded based on version
        assert newer_registration.additional_metadata is None

    def test_backfill_egap_metadata_dry_run(self, older_registration, oldest_registration):
        backfill_count = backfill_egap_metadata(dry_run=True)
        assert backfill_count == 2

        older_registration.refresh_from_db()
        oldest_registration.refresh_from_db()
        assert older_registration.additional_metadata is None
        assert older_registration.registered_date is None
        assert oldest_registration.additional_metadata is None
        assert oldest_registration.registered_date is None

    def test_backfill_egap_metadata_ignores_updated_registrations(
            self, older_registration, oldest_registration):
        older_registration.additional_metadata = {'EGAP Registration ID': OLDER_EGAP_ID}
        older_registration.save()

        backfill_count = backfill_egap_metadata()
        assert backfill_count == 1
        oldest_registration.refresh_from_db()
        assert oldest_registration.additional_metadata['EGAP Registration ID'] == OLDEST_EGAP_ID

        assert backfill_egap_metadata() == 0
