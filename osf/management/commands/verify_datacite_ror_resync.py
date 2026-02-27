#!/usr/bin/env python3
"""
Management command to verify and profile DataCite metadata resync after ROR migration.

Finds GuidMetadataRecords with ROR funder identifiers, builds DataCite metadata for each,
validates the output, and reports timing/performance metrics.

Usage:
    # Verify metadata builds correctly (no DataCite API calls)
    python manage.py verify_datacite_ror_resync

    # Verify with a sample of N records
    python manage.py verify_datacite_ror_resync --sample 50

    # Actually resync with DataCite (triggers API calls)
    python manage.py verify_datacite_ror_resync --resync

    # Profile metadata build times only
    python manage.py verify_datacite_ror_resync --profile-only
"""
import logging
import time

import lxml.etree
from django.core.management.base import BaseCommand
from osf.models import GuidMetadataRecord

logger = logging.getLogger(__name__)

DATACITE_NS = 'http://datacite.org/schema/kernel-4'


class Command(BaseCommand):
    help = 'Verify and profile DataCite metadata resync for records with ROR funder identifiers.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample',
            type=int,
            default=0,
            help='Limit to N records (0 = all, default: 0).',
        )
        parser.add_argument(
            '--resync',
            action='store_true',
            help='Actually trigger DataCite resync (API calls). Without this flag, only builds and validates metadata.',
        )
        parser.add_argument(
            '--profile-only',
            action='store_true',
            dest='profile_only',
            help='Only report timing metrics, skip detailed validation output.',
        )
        parser.add_argument(
            '--skip-reindex',
            action='store_true',
            dest='skip_reindex',
            help='When --resync is used, skip SHARE/ElasticSearch reindexing (only resync DataCite).',
        )

    def handle(self, *args, **options):
        sample = options['sample']
        resync = options['resync']
        profile_only = options['profile_only']
        skip_reindex = options['skip_reindex']

        if resync:
            self.stdout.write(self.style.WARNING(
                'RESYNC MODE: Will trigger DataCite API calls for records with DOIs.'
            ))

        # Find records with non-empty funding_info that contain ROR funders
        # (filter in Python since JSONField contains with dicts has adapter issues)
        queryset = (
            GuidMetadataRecord.objects
            .exclude(funding_info=[])
            .exclude(funding_info__isnull=True)
            .select_related('guid')
        )

        # Pre-filter to only records with at least one ROR funder
        ror_record_ids = []
        for record in queryset.iterator(chunk_size=500):
            if any(
                f.get('funder_identifier_type') == 'ROR'
                for f in record.funding_info
            ):
                ror_record_ids.append(record.pk)

        total = len(ror_record_ids)
        self.stdout.write(f'Found {total} records with ROR funder identifiers.')

        if sample:
            ror_record_ids = ror_record_ids[:sample]
            self.stdout.write(f'Sampling {sample} records.')

        queryset = GuidMetadataRecord.objects.filter(
            pk__in=ror_record_ids,
        ).select_related('guid')

        stats = {
            'total': 0,
            'build_success': 0,
            'build_errors': 0,
            'validation_errors': 0,
            'has_doi': 0,
            'resynced': 0,
            'resync_errors': 0,
            'reindexed': 0,
            'build_times': [],
            'resync_times': [],
            'error_guids': [],
        }

        for record in queryset.iterator(chunk_size=100):
            stats['total'] += 1

            if stats['total'] % 100 == 0:
                self.stdout.write(f'  Processing {stats["total"]}/{total}...')

            guid_id = record.guid._id
            referent = record.guid.referent

            # Build metadata
            build_start = time.monotonic()
            try:
                metadata_xml = self._build_metadata(referent)
                build_elapsed = time.monotonic() - build_start
                stats['build_times'].append(build_elapsed)
                stats['build_success'] += 1
            except Exception as e:
                build_elapsed = time.monotonic() - build_start
                stats['build_times'].append(build_elapsed)
                stats['build_errors'] += 1
                stats['error_guids'].append((guid_id, f'build: {e}'))
                if not profile_only:
                    self.stdout.write(self.style.ERROR(
                        f'  [{guid_id}] Build error: {e}'
                    ))
                continue

            # Validate ROR funders in output
            if metadata_xml and not profile_only:
                validation_issues = self._validate_ror_funders(metadata_xml, record, guid_id)
                if validation_issues:
                    stats['validation_errors'] += 1
                    for issue in validation_issues:
                        self.stdout.write(self.style.WARNING(f'  [{guid_id}] {issue}'))

            # Check DOI
            has_doi = bool(
                hasattr(referent, 'get_identifier_value')
                and referent.get_identifier_value('doi')
            )
            if has_doi:
                stats['has_doi'] += 1

            # Resync if requested
            if resync and has_doi:
                resync_start = time.monotonic()
                try:
                    referent.request_identifier_update('doi')
                    resync_elapsed = time.monotonic() - resync_start
                    stats['resync_times'].append(resync_elapsed)
                    stats['resynced'] += 1

                    if not skip_reindex and hasattr(referent, 'update_search'):
                        referent.update_search()
                        stats['reindexed'] += 1
                except Exception as e:
                    resync_elapsed = time.monotonic() - resync_start
                    stats['resync_times'].append(resync_elapsed)
                    stats['resync_errors'] += 1
                    stats['error_guids'].append((guid_id, f'resync: {e}'))
                    if not profile_only:
                        self.stdout.write(self.style.ERROR(
                            f'  [{guid_id}] Resync error: {e}'
                        ))

        self._print_summary(stats, resync)

    def _build_metadata(self, referent):
        """Build DataCite XML metadata for a referent, returns bytes or None."""
        client = getattr(referent, 'get_doi_client', lambda: None)()
        if not client:
            return None
        return client.build_metadata(referent)

    def _validate_ror_funders(self, metadata_xml, record, guid_id):
        """Validate that ROR funders from funding_info appear correctly in DataCite XML."""
        issues = []

        try:
            parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            root = lxml.etree.fromstring(metadata_xml, parser=parser)
        except Exception as e:
            return [f'XML parse error: {e}']

        ns = DATACITE_NS
        funding_refs_el = root.find(f'{{{ns}}}fundingReferences')
        xml_funders = []
        if funding_refs_el is not None:
            for ref_el in funding_refs_el.findall(f'{{{ns}}}fundingReference'):
                funder_id_el = ref_el.find(f'{{{ns}}}funderIdentifier')
                if funder_id_el is not None:
                    xml_funders.append({
                        'identifier': funder_id_el.text or '',
                        'type': funder_id_el.attrib.get('funderIdentifierType', ''),
                        'schemeURI': funder_id_el.attrib.get('schemeURI', ''),
                    })

        # Check each ROR funder in funding_info appears in XML
        for funder in record.funding_info:
            if funder.get('funder_identifier_type') != 'ROR':
                continue
            ror_id = funder.get('funder_identifier', '')
            matching = [f for f in xml_funders if f['identifier'] == ror_id]
            if not matching:
                issues.append(f'ROR funder {ror_id} not found in DataCite XML')
            else:
                m = matching[0]
                if m['type'] != 'ROR':
                    issues.append(
                        f'ROR funder {ror_id} has wrong type: {m["type"]}'
                    )
                if m['schemeURI'] != 'https://ror.org/':
                    issues.append(
                        f'ROR funder {ror_id} missing/wrong schemeURI: {m["schemeURI"]}'
                    )

        return issues

    def _print_summary(self, stats, resync):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('DataCite ROR Resync Verification Summary:'))
        self.stdout.write(f"  Records processed: {stats['total']}")
        self.stdout.write(f"  Metadata build success: {stats['build_success']}")
        self.stdout.write(f"  Metadata build errors: {stats['build_errors']}")
        self.stdout.write(f"  Validation issues: {stats['validation_errors']}")
        self.stdout.write(f"  Records with DOI: {stats['has_doi']}")

        if resync:
            self.stdout.write(f"  Records resynced: {stats['resynced']}")
            self.stdout.write(f"  Records reindexed: {stats['reindexed']}")
            self.stdout.write(f"  Resync errors: {stats['resync_errors']}")

        # Timing stats
        if stats['build_times']:
            build_times = stats['build_times']
            self.stdout.write('\n  Build Performance:')
            self.stdout.write(f"    Total: {sum(build_times):.2f}s")
            self.stdout.write(f"    Mean:  {sum(build_times) / len(build_times):.3f}s")
            self.stdout.write(f"    Min:   {min(build_times):.3f}s")
            self.stdout.write(f"    Max:   {max(build_times):.3f}s")
            sorted_times = sorted(build_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            self.stdout.write(f"    P50:   {p50:.3f}s")
            self.stdout.write(f"    P95:   {p95:.3f}s")
            self.stdout.write(f"    P99:   {p99:.3f}s")

        if stats['resync_times']:
            resync_times = stats['resync_times']
            self.stdout.write('\n  Resync Performance (DataCite API):')
            self.stdout.write(f"    Total: {sum(resync_times):.2f}s")
            self.stdout.write(f"    Mean:  {sum(resync_times) / len(resync_times):.3f}s")
            self.stdout.write(f"    Min:   {min(resync_times):.3f}s")
            self.stdout.write(f"    Max:   {max(resync_times):.3f}s")
            sorted_times = sorted(resync_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            self.stdout.write(f"    P50:   {p50:.3f}s")
            self.stdout.write(f"    P95:   {p95:.3f}s")

        if stats['error_guids']:
            self.stdout.write(f"\n  Errors ({len(stats['error_guids'])}):")
            for guid_id, error in stats['error_guids'][:20]:
                self.stdout.write(f'    {guid_id}: {error}')
            if len(stats['error_guids']) > 20:
                self.stdout.write(f'    ... and {len(stats["error_guids"]) - 20} more')
