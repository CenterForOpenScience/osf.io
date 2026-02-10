#!/usr/bin/env python3
"""
Management command to migrate Crossref Funder IDs to ROR IDs.

This script reads a CSV mapping file and updates all GuidMetadataRecord entries
that have funding_info with Crossref Funder IDs, converting them to ROR IDs.

Usage:
    # Dry run (recommended first)
    python manage.py migrate_funder_ids_to_ror --csv-file /path/to/mapping.csv --dry-run

    # Actual migration
    python manage.py migrate_funder_ids_to_ror --csv-file /path/to/mapping.csv

CSV Format Expected (tab or comma separated):
    Funder Name, ror ID, ROR name, Crossref DOI, Funder ID
    Example:
    National Science Foundation, https://ror.org/021nxhr62, National Science Foundation, http://dx.doi.org/10.13039/100000001, 100000001
"""
import csv
import logging
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import GuidMetadataRecord


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate Crossref Funder IDs to ROR IDs in GuidMetadataRecord.funding_info'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            required=True,
            help='Path to the CSV file containing the Crossref to ROR mapping.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Run without making any changes to the database.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000).',
        )
        parser.add_argument(
            '--update-funder-name',
            action='store_true',
            dest='update_funder_name',
            help='Also update funder_name to the ROR name from the mapping.',
        )
        parser.add_argument(
            '--skip-reindex',
            action='store_true',
            dest='skip_reindex',
            help='Skip triggering SHARE/DataCite re-indexing after migration. '
                 'Use this if you plan to run recatalog_metadata separately.',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        update_funder_name = options['update_funder_name']
        reindex = not options['skip_reindex']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No changes will be made to the database.'))

        if not reindex:
            self.stdout.write(self.style.WARNING('Re-indexing is disabled. Run recatalog_metadata after migration.'))

        # Load the mapping
        mapping = self.load_mapping(csv_file)
        if not mapping:
            self.stdout.write(self.style.ERROR('No valid mappings found in CSV file.'))
            return

        self.stdout.write(f'Loaded {len(mapping)} Crossref to ROR mappings.')

        # Find and update records
        stats = self.migrate_records(mapping, dry_run, batch_size, update_funder_name, reindex)

        # Print summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Migration Summary:'))
        self.stdout.write(f"  Records scanned: {stats['scanned']}")
        self.stdout.write(f"  Records updated: {stats['updated']}")
        self.stdout.write(f"  Records re-indexed: {stats['reindexed']}")
        self.stdout.write(f"  Funders migrated: {stats['funders_migrated']}")
        self.stdout.write(f"  Funders not in mapping: {stats['not_in_mapping']}")
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"  Errors: {stats['errors']}"))

        if stats['unmapped_ids']:
            self.stdout.write('\nUnmapped Crossref Funder IDs (not in CSV):')
            for funder_id in sorted(stats['unmapped_ids'])[:50]:  # Show first 50
                self.stdout.write(f'  - {funder_id}')
            if len(stats['unmapped_ids']) > 50:
                self.stdout.write(f'  ... and {len(stats["unmapped_ids"]) - 50} more')

    def load_mapping(self, csv_file):
        """Load the Crossref to ROR mapping from CSV file.

        Returns a dict mapping various forms of Crossref ID to ROR info:
        {
            '100000001': {'ror_id': 'https://ror.org/021nxhr62', 'ror_name': 'National Science Foundation'},
            'http://dx.doi.org/10.13039/100000001': {...},
            'https://doi.org/10.13039/100000001': {...},
            ...
        }
        """
        mapping = {}

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                # Try to detect delimiter
                sample = f.read(2048)
                f.seek(0)
                if '\t' in sample:
                    delimiter = '\t'
                else:
                    delimiter = ','

                reader = csv.DictReader(f, delimiter=delimiter)

                # Normalize column names (handle various formats)
                for row in reader:
                    # Try to find the relevant columns
                    ror_id = None
                    ror_name = None
                    crossref_doi = None
                    funder_id = None

                    for key, value in row.items():
                        if not key:
                            continue
                        key_lower = key.lower().strip()

                        if 'ror' in key_lower and 'id' in key_lower and 'ror_name' not in key_lower:
                            ror_id = value.strip() if value else None
                        elif 'ror' in key_lower and 'name' in key_lower:
                            ror_name = value.strip() if value else None
                        elif 'crossref' in key_lower and 'doi' in key_lower:
                            crossref_doi = value.strip() if value else None
                        elif key_lower == 'funder id' or key_lower == 'funder_id':
                            funder_id = value.strip() if value else None

                    if not ror_id:
                        continue

                    ror_info = {
                        'ror_id': ror_id,
                        'ror_name': ror_name,
                    }

                    # Add mappings for various ID formats
                    if funder_id:
                        mapping[funder_id] = ror_info
                        # Also add with various DOI prefixes
                        mapping[f'http://dx.doi.org/10.13039/{funder_id}'] = ror_info
                        mapping[f'https://doi.org/10.13039/{funder_id}'] = ror_info
                        mapping[f'10.13039/{funder_id}'] = ror_info

                    if crossref_doi:
                        mapping[crossref_doi] = ror_info
                        # Normalize the DOI URL
                        if crossref_doi.startswith('http://'):
                            mapping[crossref_doi.replace('http://', 'https://')] = ror_info
                        elif crossref_doi.startswith('https://'):
                            mapping[crossref_doi.replace('https://', 'http://')] = ror_info

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_file}'))
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading CSV file: {e}'))
            return None

        return mapping

    def extract_funder_id(self, identifier):
        """Extract the numeric funder ID from various identifier formats."""
        if not identifier:
            return None

        # Already just a number
        if re.match(r'^\d+$', identifier):
            return identifier

        # Extract from DOI URL (e.g., http://dx.doi.org/10.13039/100000001)
        match = re.search(r'10\.13039/(\d+)', identifier)
        if match:
            return match.group(1)

        return identifier

    def migrate_records(self, mapping, dry_run, batch_size, update_funder_name, reindex):
        """Find and migrate all GuidMetadataRecord entries with Crossref Funder IDs."""
        stats = {
            'scanned': 0,
            'updated': 0,
            'reindexed': 0,
            'funders_migrated': 0,
            'not_in_mapping': 0,
            'errors': 0,
            'unmapped_ids': set(),
        }

        # Query records that have non-empty funding_info
        # We need to check if any funder has 'Crossref Funder ID' type
        queryset = GuidMetadataRecord.objects.exclude(funding_info=[]).exclude(funding_info__isnull=True)

        total_count = queryset.count()
        self.stdout.write(f'Found {total_count} records with funding_info to scan.')

        processed = 0
        for record in queryset.iterator(chunk_size=batch_size):
            stats['scanned'] += 1
            processed += 1

            if processed % 500 == 0:
                self.stdout.write(f'  Processed {processed}/{total_count} records...')

            try:
                updated, funder_stats = self.migrate_record(record, mapping, dry_run, update_funder_name)
                if updated:
                    stats['updated'] += 1
                    if reindex and not dry_run:
                        try:
                            self.reindex_record(record)
                            stats['reindexed'] += 1
                        except Exception as e:
                            logger.error(f'Error re-indexing record {record.guid._id}: {e}')
                stats['funders_migrated'] += funder_stats['migrated']
                stats['not_in_mapping'] += funder_stats['not_found']
                stats['unmapped_ids'].update(funder_stats['unmapped_ids'])
            except Exception as e:
                stats['errors'] += 1
                logger.error(f'Error migrating record {record.guid._id}: {e}')

        return stats

    def migrate_record(self, record, mapping, dry_run, update_funder_name):
        """Migrate a single GuidMetadataRecord's funding_info.

        Returns (was_updated, funder_stats)
        """
        funder_stats = {
            'migrated': 0,
            'not_found': 0,
            'unmapped_ids': set(),
        }

        if not record.funding_info:
            return False, funder_stats

        updated_funding_info = []
        record_modified = False

        for funder in record.funding_info:
            funder_type = funder.get('funder_identifier_type', '')
            funder_identifier = funder.get('funder_identifier', '')

            # Only migrate Crossref Funder IDs
            if funder_type != 'Crossref Funder ID':
                updated_funding_info.append(funder)
                continue

            # Try to find in mapping
            ror_info = None

            # Try exact match first
            if funder_identifier in mapping:
                ror_info = mapping[funder_identifier]
            else:
                # Try to extract numeric ID and look up
                numeric_id = self.extract_funder_id(funder_identifier)
                if numeric_id and numeric_id in mapping:
                    ror_info = mapping[numeric_id]

            if ror_info:
                # Create updated funder entry
                updated_funder = funder.copy()
                updated_funder['funder_identifier'] = ror_info['ror_id']
                updated_funder['funder_identifier_type'] = 'ROR'

                if update_funder_name and ror_info.get('ror_name'):
                    updated_funder['funder_name'] = ror_info['ror_name']

                updated_funding_info.append(updated_funder)
                record_modified = True
                funder_stats['migrated'] += 1

                logger.info(
                    f'{"[DRY RUN] " if dry_run else ""}'
                    f'Migrating funder in {record.guid._id}: '
                    f'{funder_identifier} -> {ror_info["ror_id"]}'
                )
            else:
                # No mapping found, keep original
                updated_funding_info.append(funder)
                funder_stats['not_found'] += 1
                funder_stats['unmapped_ids'].add(funder_identifier)

                logger.warning(
                    f'No ROR mapping found for Crossref Funder ID: {funder_identifier} '
                    f'in record {record.guid._id}'
                )

        # Warn about duplicate ROR IDs that would result from migration
        if record_modified:
            ror_identifiers = [
                f['funder_identifier']
                for f in updated_funding_info
                if f.get('funder_identifier_type') == 'ROR'
            ]
            seen = set()
            duplicates = {rid for rid in ror_identifiers if rid in seen or seen.add(rid)}
            if duplicates:
                logger.warning(
                    f'Record {record.guid._id} has duplicate ROR IDs after migration: {duplicates}'
                )

        if record_modified and not dry_run:
            with transaction.atomic():
                record.funding_info = updated_funding_info
                record.save(update_fields=['funding_info'])

        return record_modified, funder_stats

    def reindex_record(self, record):
        """Trigger SHARE/ElasticSearch and DataCite re-indexing for the record's referent."""
        referent = record.guid.referent
        if hasattr(referent, 'update_search'):
            referent.update_search()
        if hasattr(referent, 'request_identifier_update'):
            referent.request_identifier_update('doi')
