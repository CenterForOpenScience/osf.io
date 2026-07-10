#!/usr/bin/env python3
"""
Management command to migrate ROR funders to use ROR funder names.

This script reads a CSV mapping file and updates all GuidMetadataRecord entries
that have funding_info with ROR funder IDs, converting them to ROR IDs.

This has similar functionality to migrate_funder_ids_to_ror.py but is useful if
someone that definitely doesn't have the github id felliott forgot to include
name migrations when running the prior script. It's also useful for generally
updating a bunch of ROR funder names.

Usage:
    # Dry run (recommended first)
    python manage.py migrate_funder_names_to_ror --csv-file /path/to/mapping.csv --dry-run

    # Actual migration
    python manage.py migrate_funder_names_to_ror --csv-file /path/to/mapping.csv

CSV Format Expected (tab or comma separated):
    Funder Name, ror ID, ROR name, Crossref DOI, Funder ID
    Example:
    National Science Foundation, https://ror.org/021nxhr62, National Science Foundation, http://dx.doi.org/10.13039/100000001, 100000001

Only the "ror id" and "ror name" columns are used. The others may be omitted.

"""
import csv
import logging

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
            required=False,
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
        reindex = not options['skip_reindex']

        if dry_run:
            logger.warning('[DRY RUN] No changes will be made to the database.')

        if not reindex:
            logger.warning('Re-indexing is disabled. Run recatalog_metadata after migration.')

        migrate_funder_names_to_ror(csv_file=csv_file, dry_run=dry_run, batch_size=batch_size,
                                    reindex=reindex, stdout=self.stdout)

def migrate_funder_names_to_ror(csv_file=None, dry_run=False, batch_size=1000, reindex=True,
                                stdout=None):

    if csv_file is None:
        csv_file = 'osf/management/commands/funder_mapping.csv'

    # Load the mapping
    mapping = load_mapping(csv_file)
    if not mapping:
        stdout.write('No valid mappings found in CSV file.')
        return

    stdout.write(f'Loaded {len(mapping)} ROR id to name mappings.')

    # Find and update records
    stats = migrate_records(mapping, dry_run, batch_size, reindex, stdout=stdout)

    # Print summary
    stdout.write('\n' + '=' * 60)
    stdout.write('Migration Summary:')
    stdout.write(f"  Records scanned: {stats['scanned']}")
    stdout.write(f"  Records updated: {stats['updated']}")
    stdout.write(f"  Records re-indexed: {stats['reindexed']}")
    stdout.write(f"  Funder names updated: {stats['funders_migrated']}")
    stdout.write(f"  Unmapped funders removed: {stats['not_in_mapping']}")
    stdout.write(f"  Unique funders not in mapping: {len(stats['unmapped_ids'])}")
    if stats['errors']:
        stdout.write(f"  Errors: {stats['errors']}")

    if stats['unmapped_ids']:
        stdout.write('Unmapped ROR Funder IDs (not in CSV):')
        for funder_id in sorted(stats['unmapped_ids'])[:50]:  # Show first 50
            stdout.write(f'  - {funder_id}')
        if len(stats['unmapped_ids']) > 50:
            stdout.write(f'  ... and {len(stats["unmapped_ids"]) - 50} more')

def load_mapping(csv_file):
    """Load the ROR ID to ROR info mapping from CSV file.

    Returns a dict mapping ROR IDs to ROR info:
    {
        'https://ror.org/021nxhr62': {
            'ror_id': 'https://ror.org/021nxhr62',
            'ror_name': 'National Science Foundation'
        },
        ...
    }
    """
    funder_map = {}

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
            sample = f.read(2048)
            delimiter = '\t' if '\t' in sample else ','

            # reset fp and read
            f.seek(0)
            reader = csv.reader(f, delimiter=delimiter, quotechar='"')

            for row in reader:
                funder_map[row[0]] = {
                    'ror_id': row[0],
                    'ror_name': row[1],
                }

    except FileNotFoundError:
        logger.error(f'CSV file not found: {csv_file}')
        return None
    except Exception as e:
        logger.error(f'Error reading CSV file: {type(e)}')
        return None

    return funder_map

def migrate_records(mapping, dry_run, batch_size, reindex, stdout=None):
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
    stdout.write(f'Found {total_count} records with funding_info to scan.')

    processed = 0
    for record in queryset.iterator(chunk_size=batch_size):
        stats['scanned'] += 1
        processed += 1

        if processed % 500 == 0:
            stdout.write(f'  Processed {processed}/{total_count} records...')

        try:
            updated, funder_stats = migrate_record(record, mapping, dry_run, stdout)
            if updated:
                stats['updated'] += 1
                if reindex and not dry_run:
                    try:
                        reindex_record(record)
                        stats['reindexed'] += 1
                    except Exception as e:
                        stdout.write(f'Error re-indexing record {record.guid._id}: {e}')
            stats['funders_migrated'] += funder_stats['migrated']
            stats['not_in_mapping'] += funder_stats['not_found']
            stats['unmapped_ids'].update(funder_stats['unmapped_ids'])
        except Exception as e:
            stats['errors'] += 1
            stdout.write(f'Error migrating record {record.guid._id}: {e}')

    return stats

def migrate_record(record, mapping, dry_run, stdout=None):
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

        # Only update ROR funder records
        if funder_type != 'ROR':
            updated_funding_info.append(funder)
            continue

        # Try to find in mapping
        ror_info = mapping.get(funder_identifier, None)
        if ror_info is None:
            stdout.write(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Unrecognized ror id for {record.guid._id}: '
                f'{funder_identifier}'
            )
            updated_funding_info.append(funder)
            continue

        # Has name changed?
        if funder.get('funder_name') == ror_info['ror_name']:
            logger.debug(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'ROR name unchanged for {record.guid._id}: '
                f'{funder_identifier} -> {funder.get("funder_name")}'
            )
            updated_funding_info.append(funder)
            continue

        # Create updated funder entry
        stdout.write(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Updating name for {record.guid._id}: '
            f'id {funder_identifier} from {funder["funder_name"]} to {ror_info["ror_name"]}'
        )
        updated_funder = funder.copy()
        updated_funder['funder_name'] = ror_info['ror_name']
        updated_funding_info.append(updated_funder)
        record_modified = True
        funder_stats['migrated'] += 1

    # Warn about duplicate ROR IDs that would result from migration
    # THIS SHOULDN'T HAPPEN
    if record_modified:
        ror_identifiers = [
            f['funder_identifier']
            for f in updated_funding_info
            if f.get('funder_identifier_type') == 'ROR'
        ]
        seen = set()
        duplicates = {rid for rid in ror_identifiers if rid in seen or seen.add(rid)}
        if duplicates:
            logger.debug(
                f'Record {record.guid._id} has multiple ROR IDs after migration: {duplicates}'
            )

    if record_modified and not dry_run:
        with transaction.atomic():
            record.funding_info = updated_funding_info
            record.save(update_fields=['funding_info'])

    return record_modified, funder_stats

def reindex_record(record):
    """Trigger SHARE/ElasticSearch and DataCite re-indexing for the record's referent."""
    referent = record.guid.referent
    if hasattr(referent, 'update_search'):
        referent.update_search()
    if hasattr(referent, 'request_identifier_update'):
        referent.request_identifier_update('doi')
