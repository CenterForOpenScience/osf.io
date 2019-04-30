# -*- coding: utf-8 -*-
import csv
from collections import OrderedDict
from datetime import date
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from django.db.models import BooleanField, Case, CharField, Count, F, OuterRef, QuerySet, Subquery, Sum, Value, When

from osf.models import AbstractNode, Node, Preprint, Registration, TrashedFile
from addons.osfstorage.models import NodeSettings, Region
import os
import logging

PRIVATE_SIZE_THRESHOLD = 5368709120
PAGE_SIZE = 10000
VALUES = (
        'guids___id',
        'type',
        'roots_id',
        'title',
        'is_fork',
        'is_public',
        'is_deleted',
        'region_name',
        'files__versions__count',
        'files__versions__size__sum',
        'is_spam',
    )


logger = logging.getLogger(__name__)


# Detail gatherers
def gather_node_usage():
    queries = []
    logger.info('Gathering node usage')
    region = Region.objects.filter(id=OuterRef('region_id'))
    node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(
        owner_id=OuterRef('pk'))
    node_limit = Node.objects.exclude(
        spam_status=2,  # SPAM
    ).only(
        'id',
    )
    page_start = 0
    page_end = page_start + PAGE_SIZE
    data_page = node_limit[page_start:page_end]
    # logger.info(data_page.explain())
    while data_page.exists():
        # logger.info(data_page.query)
        logger.info('Node data {} to {}'.format(page_start, page_end))
        node_set = Node.objects.filter(id__in=Subquery(data_page.values('id'))).only(
            'guids',
            'type',
            'title',
            'root',
            'is_fork',
            'is_public',
            'is_deleted',
            'files',
            'spam_status',
            'created',
        ).annotate(
            Count('files__versions'),
            Sum('files__versions__size'),
            roots_id=Case(
                When(root__isnull=False, then='root__guids___id'),
                default=Value(None),
                output_field=CharField(),
            ),
            is_spam=Case(
                When(spam_status=2, then=True),
                default=Value(False),
                output_field=BooleanField()
            ),
            region_name=Subquery(node_settings.values('region_abbrev')[:1])
        ).order_by('created')
        queries.append(node_set)
        page_start = page_end
        page_end = page_start + PAGE_SIZE
        data_page = node_limit[page_start:page_end]
    return queries


def gather_registration_usage():
    logger.info('Gathering registration usage')
    region = Region.objects.filter(id=OuterRef('region_id'))
    node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(
        owner_id=OuterRef('pk'))
    registration_set = Registration.objects.exclude(
        spam_status=2,  # SPAM
    ).annotate(
        Count('files__versions'),
        Sum('files__versions__size'),
        roots_id=Case(
            When(root__isnull=False, then='root__guids___id'),
            default=Value(None),
            output_field=CharField(),
        ),
        is_spam=Case(
            When(spam_status=2, then=True),
            default=Value(False),
            output_field=BooleanField()
        ),
        region_name=Subquery(node_settings.values('region_abbrev')[:1])
    ).order_by('guids___id')

    return registration_set


def gather_preprint_usage():
    logger.info('Gathering preprint usage')
    preprints = Preprint.objects.exclude(
        spam_status=2,  # SPAM
    ).annotate(
        Count('files__versions'),
        Sum('files__versions__size'),
        type=Value('osf.preprint', CharField()),
        roots_id=Value('', CharField()),
        is_fork=Value(False, BooleanField()),
        is_deleted=Case(
            When(date_withdrawn__isnull=True, then=False),
            default=Value(True),
            output_field=BooleanField(),
        ),
        is_spam=Case(
            When(spam_status=2, then=True),
            default=Value(False),
            output_field=BooleanField()
        ),
        region_name=F('region__name')
    ).order_by('guids___id')

    return preprints


def gather_quickfile_usage():
    # TODO: Make this like preprint usage when quickfiles are no longer in nodes
    # (this is why it's not part of gather_node_usage(), for easy replacement)
    logger.info('Gathering quickfile usage')

    quickfiles = AbstractNode.objects.filter(
        files__type='osf.osfstoragefile',
        type='osf.quickfilesnode'
    ).annotate(
        Count('files__versions'),
        Sum('files__versions__size'),
        is_spam=Value(False, BooleanField()),
        roots_id=F('guids___id'),
        region_name=Value('United States', CharField())
    ).filter(
        files__versions__count__gte=1,
    ).order_by('guids___id')

    return quickfiles


def gather_summary_data():
    logger.info('Gathering summary data')
    logger.info('Deleted')

    deleted = TrashedFile.objects.all().aggregate(total_deleted=Sum('versions__size'))['total_deleted']
    logger.info('Registrations')

    registrations = Registration.objects.all().annotate(
            Count('files__versions'),
            Sum('files__versions__size'),
    ).filter(
            files__versions__count__gte=1,
    ).aggregate(
        registrations=Sum('files__versions__size__sum')
    )['registrations']
    logger.info('Nodes')

    nodes = Node.objects.all().filter(
            files__type='osf.osfstoragefile',
        ).exclude(
            spam_status=2,  # SPAM
            type='osf.registration',
        ).annotate(
            Count('files__versions'),
            Sum('files__versions__size'),
        ).filter(
            files__versions__count__gte=1,
        )
    logger.info('Public nodes')

    public = nodes.filter(is_public=True).aggregate(public=Sum('files__versions__size__sum'))['public']
    if not public:
        public = 0
    private = nodes.filter(is_public=False).annotate(Sum('files__versions__size'))
    logger.info('Under 5')
    under = private.filter(
            files__versions__size__sum__lt=PRIVATE_SIZE_THRESHOLD,
        ).aggregate(under=Sum('files__versions__size__sum'))['under']
    if not under:
        under = 0
    logger.info('Over 5')
    over = private.filter(
            files__versions__size__sum__gte=PRIVATE_SIZE_THRESHOLD,
        ).aggregate(over=Sum('files__versions__size__sum'))['over']
    if not over:
        over = 0

    return deleted, registrations, public, under, over


def convert_regional_data(regional_data):
    logger.info('Convert regional data: {}'.format(regional_data))
    return {
        item['region_name']:
            item['files__versions__size__sum'] if item['files__versions__size__sum'] is not None else 0
        for item in regional_data
    }


def combine_regional_data(*args):
    regional_totals = {}
    for region_data_item in args:
        # logger.info('Combine regional item: {}'.format(region_data_item))
        if isinstance(region_data_item, QuerySet):
            region_data_set = convert_regional_data(region_data_item)
        else:
            region_data_set = region_data_item
        for key in region_data_set.keys():
            regional_totals[key] = regional_totals.get(key, 0) + region_data_set.get(key, 0)
    return regional_totals


def write_summary_data(filename, summary_data):
    header_row = []
    summary_row = []
    for key in summary_data:
        header_row += [key]
        summary_row += [summary_data[key]]

    if os.path.isfile(filename):
        with open(filename) as old_file:
            reader = csv.reader(old_file, delimiter=',', lineterminator='\n')
            header_skipped = False
            with open('{}-temp'.format(filename), 'w') as new_file:
                writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
                writer.writerow(header_row)
                for row in reader:
                    if header_skipped:
                        writer.writerow(row)
                    header_skipped = True
                writer.writerow(summary_row)
        os.remove(filename)
        os.rename('{}-temp'.format(filename), filename)

    else:
        with open(filename, 'w') as new_file:
            writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
            writer.writerow(header_row)
            writer.writerow(summary_row)


def write_raw_data(data, filename):
    with open(filename, 'wb') as fp:
        writer = csv.writer(fp, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
        writer.writerow([
            'guid',
            'type',
            'root_guid',
            'title',
            'is_fork',
            'is_public',
            'is_deleted',
            'region',
            'files_count',
            'files_size_bytes',
            'is_spam',
        ])
        for row in data:
            row_to_write = []
            for s in row:
                item = s.encode('utf-8') if isinstance(s, (str, unicode)) else s
                row_to_write.append(s)
            writer.writerow(row_to_write)


def process_usages(write_detail=True, write_summary=True):
    # We can't re-order these columns after they are released, only add columns to the end
    # This is why we can't just append whatever storage regions we add to the system automatically,
    # because then they'd likely be out of order when they were added.
    import logging
    logger = logging.getLogger(__name__)

    summary_data = OrderedDict([
        ('date', date.today().isoformat()),
        ('total', 0),
        ('deleted', 0),
        ('registrations', 0),
        ('nd_quick_files', 0),
        ('nd_public_nodes', 0),
        ('nd_private_nodes_under5', 0),
        ('nd_private_nodes_over5', 0),
        ('nd_preprints', 0),
        ('nd_supp_nodes', 0),
        ('canada_montreal', 0),
        ('australia_syndey', 0),
        ('germany_frankfurt', 0),
        ('united_states', 0),
    ])
    logger.info('Collecting usage details')

    usage_details = {
        'node': gather_node_usage(),
        'registration': gather_registration_usage(),
        'preprint': gather_preprint_usage(),
        'quickfile': gather_quickfile_usage(),
    }

    regional_totals = {}
    quickfiles = 0
    preprints = 0
    supplemental_node_total = 0
    index = 0

    for key in usage_details.keys():
        query_set = usage_details[key]
        logger.info('Processing {}'.format(key))
        if key == 'node':
            for item in usage_details[key]:
                index += 1
                logger.info('Index: {}'.format(index))
                logger.info('regional_totals')
                regional_totals = combine_regional_data(
                    regional_totals,
                    item.values('region_name').annotate(Sum('files__versions__size'))
                )
                if write_detail:
                    logger.info('Writing ./data-usage-raw-{}.csv'.format(index))

                    data = item.values_list(*VALUES)
                    write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(index))
        else:
            page_start = 0
            page_end = page_start + PAGE_SIZE
            data_page = query_set[page_start:page_end]
            logger.info(data_page.query)
            # logger.info(data_page.explain())
            while data_page.exists():
                page_end = page_start + PAGE_SIZE
                index += 1
                logger.info('Index: {}'.format(index))
                if key == 'quickfile':
                    quickfiles_total = data_page.aggregate(
                        quickfiles_total=Sum('files__versions__size__sum'),
                    )['quickfiles_total']
                    quickfiles += quickfiles_total
                    regional_totals = combine_regional_data(
                        regional_totals,
                        {'United States': quickfiles_total},
                    )
                else:
                    logger.info('regional_totals')
                    regional_totals = combine_regional_data(
                        regional_totals,
                        data_page.values('region_name').annotate(Sum('files__versions__size'))
                    )
                if key == 'preprint':
                    preprints += data_page.aggregate(
                        preprints_total=Sum('files__versions__size__sum'),
                    )['preprints_total']

                    supplemental_node_usage = Node.objects.filter(
                        id__in=Subquery(data_page.values('node')),
                        files__type='osf.osfstoragefile',
                        is_deleted=False,
                    ).exclude(
                        spam_status=2,  # SPAM
                    ).annotate(
                        Count('files__versions'),
                        Sum('files__versions__size'),
                    ).filter(
                        files__versions__count__gte=1,
                    )

                    supplemental_node_total += supplemental_node_usage.aggregate(
                        supplemental_node_total=Sum('files__versions__size__sum'),
                    ).get(supplemental_node_total, 0)

                if write_detail:
                    logger.info('Writing ./data-usage-raw-{}.csv'.format(index))

                    data = data_page.values_list(*VALUES)
                    write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(index))
                page_start = page_end
                page_end = page_start + PAGE_SIZE
                data_page = query_set[page_start:page_end]

    deleted, registrations, public, under, over = gather_summary_data()
    summary_data['total'] = deleted + registrations + quickfiles + public + under + over + preprints
    summary_data['deleted'] = deleted
    summary_data['registrations'] = registrations
    summary_data['nd_quick_files'] = quickfiles
    summary_data['nd_public_nodes'] = public
    summary_data['nd_private_nodes_under5'] = under
    summary_data['nd_private_nodes_over5'] = over
    summary_data['nd_preprints'] = preprints
    summary_data['nd_supp_nodes'] = supplemental_node_total
    summary_data['canada_montreal'] = regional_totals.get(u'Canada - Montréal', 0)
    summary_data['australia_syndey'] = regional_totals.get('Australia - Sydney', 0)
    summary_data['germany_frankfurt'] = regional_totals.get('Germany - Frankfurt', 0)
    summary_data['united_states'] = regional_totals.get('United States', 0)
    if write_summary:
        write_summary_data(filename='./osf_storage_metrics.csv', summary_data=summary_data)

    return summary_data


class Command(BaseCommand):
    help = 'Get raw and summary data of storage usage for Product and Metascience'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Delete poll instead of closing it',
        )

    # Management command handler
    def handle(self, *args, **options):
        process_usages(write_summary=not options['dry_run'], write_detail=not options['dry_run'])
