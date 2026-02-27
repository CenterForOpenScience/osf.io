import pytest
from io import StringIO
from unittest import mock

from django.core.management import call_command

from osf.models import GuidMetadataRecord
from osf_tests import factories


@pytest.mark.django_db
class TestVerifyDataciteRorResync:

    @pytest.fixture
    def user(self):
        return factories.UserFactory()

    @pytest.fixture
    def registration_with_ror_funder(self, user):
        registration = factories.RegistrationFactory(creator=user, is_public=True)
        record = GuidMetadataRecord.objects.for_guid(registration._id)
        record.funding_info = [{
            'funder_name': 'National Science Foundation',
            'funder_identifier': 'https://ror.org/021nxhr62',
            'funder_identifier_type': 'ROR',
        }]
        record.save()
        return registration

    @pytest.fixture
    def registration_with_crossref_funder(self, user):
        registration = factories.RegistrationFactory(creator=user, is_public=True)
        record = GuidMetadataRecord.objects.for_guid(registration._id)
        record.funding_info = [{
            'funder_name': 'Some Funder',
            'funder_identifier': 'https://doi.org/10.13039/100000001',
            'funder_identifier_type': 'Crossref Funder ID',
        }]
        record.save()
        return registration

    @pytest.fixture
    def mock_reindex(self):
        with mock.patch('osf.models.node.AbstractNode.update_search') as mock_search, \
             mock.patch('osf.models.node.AbstractNode.request_identifier_update') as mock_doi:
            yield mock_search, mock_doi

    @pytest.fixture
    def mock_datacite(self, registration_with_ror_funder):
        from website import settings as website_settings
        with mock.patch.object(website_settings, 'DATACITE_ENABLED', True), \
             mock.patch.object(website_settings, 'DATACITE_USERNAME', 'test'), \
             mock.patch.object(website_settings, 'DATACITE_PASSWORD', 'test'):
            yield

    def test_finds_ror_records(self, registration_with_ror_funder, mock_gravy_valet_get_verified_links):
        """Verify the command finds records with ROR funder identifiers."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', stdout=out)
        output = out.getvalue()
        assert 'Found 1 records with ROR funder identifiers' in output
        assert 'Metadata build success: 1' in output
        assert 'Metadata build errors: 0' in output

    def test_ignores_non_ror_records(self, registration_with_crossref_funder, mock_gravy_valet_get_verified_links):
        """Verify the command ignores records without ROR funder identifiers."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', stdout=out)
        output = out.getvalue()
        assert 'Found 0 records with ROR funder identifiers' in output

    def test_validates_ror_in_xml(self, registration_with_ror_funder, mock_gravy_valet_get_verified_links):
        """Verify the command validates ROR funder appears correctly in DataCite XML."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', stdout=out)
        output = out.getvalue()
        assert 'Validation issues: 0' in output

    def test_sample_limits_records(self, registration_with_ror_funder, mock_gravy_valet_get_verified_links):
        """Verify --sample limits the number of records processed."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', '--sample', '1', stdout=out)
        output = out.getvalue()
        assert 'Sampling 1 records' in output
        assert 'Records processed: 1' in output

    def test_profile_only_suppresses_detail(self, registration_with_ror_funder, mock_gravy_valet_get_verified_links):
        """Verify --profile-only shows timing but no per-record detail."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', '--profile-only', stdout=out)
        output = out.getvalue()
        assert 'Build Performance:' in output
        assert 'Metadata build success: 1' in output

    def test_resync_triggers_doi_update(self, registration_with_ror_funder, mock_reindex, mock_gravy_valet_get_verified_links):
        """Verify --resync triggers request_identifier_update for records with DOIs."""
        mock_search, mock_doi = mock_reindex

        # Give the registration a DOI
        registration_with_ror_funder.set_identifier_value('doi', '10.70102/test')

        out = StringIO()
        call_command('verify_datacite_ror_resync', '--resync', stdout=out)
        output = out.getvalue()

        mock_doi.assert_called_with('doi')
        mock_search.assert_called()
        assert 'Records resynced: 1' in output

    def test_resync_skip_reindex(self, registration_with_ror_funder, mock_reindex, mock_gravy_valet_get_verified_links):
        """Verify --skip-reindex skips SHARE/ES reindexing during resync."""
        mock_search, mock_doi = mock_reindex

        registration_with_ror_funder.set_identifier_value('doi', '10.70102/test')

        out = StringIO()
        call_command('verify_datacite_ror_resync', '--resync', '--skip-reindex', stdout=out)
        output = out.getvalue()

        mock_doi.assert_called_with('doi')
        mock_search.assert_not_called()
        assert 'Records resynced: 1' in output
        assert 'Records reindexed: 0' in output

    def test_no_resync_without_flag(self, registration_with_ror_funder, mock_reindex, mock_gravy_valet_get_verified_links):
        """Verify no DataCite API calls without --resync flag."""
        mock_search, mock_doi = mock_reindex

        registration_with_ror_funder.set_identifier_value('doi', '10.70102/test')

        out = StringIO()
        call_command('verify_datacite_ror_resync', stdout=out)

        mock_doi.assert_not_called()
        mock_search.assert_not_called()

    def test_reports_build_timing(self, registration_with_ror_funder, mock_gravy_valet_get_verified_links):
        """Verify build timing stats are reported."""
        out = StringIO()
        call_command('verify_datacite_ror_resync', stdout=out)
        output = out.getvalue()
        assert 'Build Performance:' in output
        assert 'Total:' in output
        assert 'Mean:' in output
        assert 'P50:' in output
        assert 'P95:' in output
