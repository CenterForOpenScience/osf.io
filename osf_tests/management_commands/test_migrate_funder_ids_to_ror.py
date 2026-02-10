import os
import pytest
import tempfile
from unittest import mock

from django.core.management import call_command

from osf.models import GuidMetadataRecord
from osf.management.commands.migrate_funder_ids_to_ror import Command
from osf_tests import factories


@pytest.mark.django_db
class TestMigrateFunderIdsToRor:

    @pytest.fixture
    def user(self):
        return factories.UserFactory()

    @pytest.fixture
    def project(self, user):
        return factories.ProjectFactory(creator=user)

    @pytest.fixture
    def csv_mapping_file(self):
        """Create a temporary CSV file with test mapping data."""
        content = """Funder Name\tror ID\tROR name\tCrossref DOI\tFunder ID
National Institutes of Health\thttps://ror.org/01cwqze88\tNational Institutes of Health\thttp://dx.doi.org/10.13039/100000002\t100000002
National Science Foundation\thttps://ror.org/021nxhr62\tNational Science Foundation\thttp://dx.doi.org/10.13039/100000001\t100000001
European Research Council\thttps://ror.org/0472cxd90\tEuropean Research Council\thttp://dx.doi.org/10.13039/501100000781\t501100000781
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    @pytest.fixture
    def mock_reindex(self):
        """Mock update_search and request_identifier_update to avoid actual re-indexing in tests."""
        with mock.patch('osf.models.node.AbstractNode.update_search') as mock_search, \
             mock.patch('osf.models.node.AbstractNode.request_identifier_update') as mock_doi:
            yield mock_search, mock_doi

    @pytest.fixture
    def record_with_crossref_funder(self, project):
        """Create a GuidMetadataRecord with Crossref Funder ID."""
        record = GuidMetadataRecord.objects.for_guid(project._id)
        record.funding_info = [{
            'funder_name': 'National Institutes of Health',
            'funder_identifier': 'http://dx.doi.org/10.13039/100000002',
            'funder_identifier_type': 'Crossref Funder ID',
            'award_number': 'R01-GM-123456',
            'award_title': 'Test Grant',
        }]
        record.save()
        return record

    @pytest.fixture
    def record_with_multiple_funders(self, user):
        """Create a GuidMetadataRecord with multiple funders (mix of Crossref and ROR)."""
        project = factories.ProjectFactory(creator=user)
        record = GuidMetadataRecord.objects.for_guid(project._id)
        record.funding_info = [
            {
                'funder_name': 'NIH',
                'funder_identifier': 'https://doi.org/10.13039/100000002',
                'funder_identifier_type': 'Crossref Funder ID',
                'award_number': 'R01-123',
            },
            {
                'funder_name': 'Already ROR',
                'funder_identifier': 'https://ror.org/existing123',
                'funder_identifier_type': 'ROR',
            },
            {
                'funder_name': 'NSF',
                'funder_identifier': '100000001',
                'funder_identifier_type': 'Crossref Funder ID',
            },
        ]
        record.save()
        return record

    @pytest.fixture
    def record_with_unmapped_funder(self, user):
        """Create a GuidMetadataRecord with a funder not in the mapping."""
        project = factories.ProjectFactory(creator=user)
        record = GuidMetadataRecord.objects.for_guid(project._id)
        record.funding_info = [{
            'funder_name': 'Unknown Funder',
            'funder_identifier': 'http://dx.doi.org/10.13039/999999999',
            'funder_identifier_type': 'Crossref Funder ID',
        }]
        record.save()
        return record

    def test_migrate_single_crossref_funder(self, record_with_crossref_funder, csv_mapping_file):
        """Test migrating a single Crossref Funder ID to ROR."""
        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        # Run migration (not dry run)
        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record_with_crossref_funder,
            mapping,
            dry_run=False,
            update_funder_name=False
        )

        assert updated is True
        assert stats['migrated'] == 1
        assert stats['not_found'] == 0

        record_with_crossref_funder.refresh_from_db()
        funder = record_with_crossref_funder.funding_info[0]

        assert funder['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funder['funder_identifier_type'] == 'ROR'
        # Original name preserved (update_funder_name=False)
        assert funder['funder_name'] == 'National Institutes of Health'
        # Other fields preserved
        assert funder['award_number'] == 'R01-GM-123456'
        assert funder['award_title'] == 'Test Grant'

    def test_migrate_with_funder_name_update(self, record_with_crossref_funder, csv_mapping_file):
        """Test migrating with funder name update enabled."""
        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        command.migrate_record(
            record_with_crossref_funder,
            mapping,
            dry_run=False,
            update_funder_name=True
        )

        record_with_crossref_funder.refresh_from_db()
        funder = record_with_crossref_funder.funding_info[0]

        assert funder['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funder['funder_identifier_type'] == 'ROR'
        assert funder['funder_name'] == 'National Institutes of Health'

    def test_dry_run_does_not_modify(self, record_with_crossref_funder, csv_mapping_file):
        """Test that dry run does not modify the database."""
        original_funding_info = record_with_crossref_funder.funding_info.copy()

        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record_with_crossref_funder,
            mapping,
            dry_run=True,
            update_funder_name=False
        )

        assert updated is True  # Would have updated
        assert stats['migrated'] == 1

        record_with_crossref_funder.refresh_from_db()
        # Data should be unchanged
        assert record_with_crossref_funder.funding_info == original_funding_info

    def test_migrate_multiple_funders(self, record_with_multiple_funders, csv_mapping_file):
        """Test migrating record with multiple funders."""
        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record_with_multiple_funders,
            mapping,
            dry_run=False,
            update_funder_name=False
        )

        assert updated is True
        assert stats['migrated'] == 2  # NIH and NSF
        assert stats['not_found'] == 0

        record_with_multiple_funders.refresh_from_db()
        funders = record_with_multiple_funders.funding_info

        # NIH should be migrated
        assert funders[0]['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funders[0]['funder_identifier_type'] == 'ROR'

        # Already ROR should be unchanged
        assert funders[1]['funder_identifier'] == 'https://ror.org/existing123'
        assert funders[1]['funder_identifier_type'] == 'ROR'

        # NSF should be migrated
        assert funders[2]['funder_identifier'] == 'https://ror.org/021nxhr62'
        assert funders[2]['funder_identifier_type'] == 'ROR'

    def test_unmapped_funder_preserved(self, record_with_unmapped_funder, csv_mapping_file):
        """Test that funders not in mapping are preserved unchanged."""
        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record_with_unmapped_funder,
            mapping,
            dry_run=False,
            update_funder_name=False
        )

        assert updated is False
        assert stats['migrated'] == 0
        assert stats['not_found'] == 1
        assert 'http://dx.doi.org/10.13039/999999999' in stats['unmapped_ids']

        record_with_unmapped_funder.refresh_from_db()
        funder = record_with_unmapped_funder.funding_info[0]

        # Should be unchanged
        assert funder['funder_identifier'] == 'http://dx.doi.org/10.13039/999999999'
        assert funder['funder_identifier_type'] == 'Crossref Funder ID'

    def test_load_mapping_various_id_formats(self, csv_mapping_file):
        """Test that mapping handles various ID formats."""
        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)

        # All these formats should map to the same ROR ID
        assert mapping['100000002']['ror_id'] == 'https://ror.org/01cwqze88'
        assert mapping['http://dx.doi.org/10.13039/100000002']['ror_id'] == 'https://ror.org/01cwqze88'
        assert mapping['https://doi.org/10.13039/100000002']['ror_id'] == 'https://ror.org/01cwqze88'
        assert mapping['10.13039/100000002']['ror_id'] == 'https://ror.org/01cwqze88'

    def test_extract_funder_id(self):
        """Test extraction of numeric funder ID from various formats."""
        command = Command()

        assert command.extract_funder_id('100000002') == '100000002'
        assert command.extract_funder_id('http://dx.doi.org/10.13039/100000002') == '100000002'
        assert command.extract_funder_id('https://doi.org/10.13039/100000002') == '100000002'
        assert command.extract_funder_id('10.13039/100000002') == '100000002'

    def test_empty_funding_info_skipped(self, project, csv_mapping_file):
        """Test that records with empty funding_info are skipped."""
        record = GuidMetadataRecord.objects.for_guid(project._id)
        record.funding_info = []
        record.save()

        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record,
            mapping,
            dry_run=False,
            update_funder_name=False
        )

        assert updated is False
        assert stats['migrated'] == 0

    def test_ror_funder_not_modified(self, user, csv_mapping_file):
        """Test that funders already using ROR are not modified."""
        project = factories.ProjectFactory(creator=user)
        record = GuidMetadataRecord.objects.for_guid(project._id)
        record.funding_info = [{
            'funder_name': 'Already ROR',
            'funder_identifier': 'https://ror.org/01cwqze88',
            'funder_identifier_type': 'ROR',
        }]
        record.save()

        command = Command()
        command.stdout = type('MockStdout', (), {'write': lambda self, x: None})()

        mapping = command.load_mapping(csv_mapping_file)
        updated, stats = command.migrate_record(
            record,
            mapping,
            dry_run=False,
            update_funder_name=False
        )

        assert updated is False
        assert stats['migrated'] == 0

        record.refresh_from_db()
        assert record.funding_info[0]['funder_identifier'] == 'https://ror.org/01cwqze88'

    def test_reindex_triggered_after_migration(self, record_with_crossref_funder, csv_mapping_file, mock_reindex):
        """Test that SHARE/DataCite re-indexing is triggered for migrated records."""
        mock_update_search, mock_request_identifier_update = mock_reindex

        call_command(
            'migrate_funder_ids_to_ror',
            '--csv-file', csv_mapping_file,
        )

        # Verify re-indexing was triggered
        mock_update_search.assert_called()
        mock_request_identifier_update.assert_called_with('doi')

        # Verify data was actually migrated
        record_with_crossref_funder.refresh_from_db()
        funder = record_with_crossref_funder.funding_info[0]
        assert funder['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funder['funder_identifier_type'] == 'ROR'

    def test_reindex_not_triggered_on_dry_run(self, record_with_crossref_funder, csv_mapping_file, mock_reindex):
        """Test that re-indexing is NOT triggered during dry run."""
        mock_update_search, mock_request_identifier_update = mock_reindex

        call_command(
            'migrate_funder_ids_to_ror',
            '--csv-file', csv_mapping_file,
            '--dry-run',
        )

        mock_update_search.assert_not_called()
        mock_request_identifier_update.assert_not_called()

    def test_reindex_not_triggered_with_skip_flag(self, record_with_crossref_funder, csv_mapping_file, mock_reindex):
        """Test that re-indexing is NOT triggered when --skip-reindex is used."""
        mock_update_search, mock_request_identifier_update = mock_reindex

        call_command(
            'migrate_funder_ids_to_ror',
            '--csv-file', csv_mapping_file,
            '--skip-reindex',
        )

        mock_update_search.assert_not_called()
        mock_request_identifier_update.assert_not_called()

        # But data should still be migrated
        record_with_crossref_funder.refresh_from_db()
        funder = record_with_crossref_funder.funding_info[0]
        assert funder['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funder['funder_identifier_type'] == 'ROR'

    def test_reindex_not_triggered_for_unmapped_records(self, record_with_unmapped_funder, csv_mapping_file, mock_reindex):
        """Test that re-indexing is NOT triggered for records that weren't updated."""
        mock_update_search, mock_request_identifier_update = mock_reindex

        call_command(
            'migrate_funder_ids_to_ror',
            '--csv-file', csv_mapping_file,
        )

        mock_update_search.assert_not_called()
        mock_request_identifier_update.assert_not_called()

    def test_end_to_end_call_command(self, record_with_crossref_funder, record_with_multiple_funders, csv_mapping_file, mock_reindex):
        """Test the full management command end-to-end via call_command."""
        mock_update_search, mock_request_identifier_update = mock_reindex

        call_command(
            'migrate_funder_ids_to_ror',
            '--csv-file', csv_mapping_file,
        )

        # Record with single crossref funder should be migrated
        record_with_crossref_funder.refresh_from_db()
        funder = record_with_crossref_funder.funding_info[0]
        assert funder['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funder['funder_identifier_type'] == 'ROR'
        assert funder['award_number'] == 'R01-GM-123456'

        # Record with multiple funders should have Crossref ones migrated
        record_with_multiple_funders.refresh_from_db()
        funders = record_with_multiple_funders.funding_info
        assert funders[0]['funder_identifier'] == 'https://ror.org/01cwqze88'
        assert funders[0]['funder_identifier_type'] == 'ROR'
        assert funders[1]['funder_identifier'] == 'https://ror.org/existing123'
        assert funders[1]['funder_identifier_type'] == 'ROR'
        assert funders[2]['funder_identifier'] == 'https://ror.org/021nxhr62'
        assert funders[2]['funder_identifier_type'] == 'ROR'

        # Re-indexing should have been triggered for both updated records
        assert mock_update_search.call_count == 2
        assert mock_request_identifier_update.call_count == 2
