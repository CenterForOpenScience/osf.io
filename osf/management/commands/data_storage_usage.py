# -*- coding: utf-8 -*-
import csv
import datetime
import logging
import os

from collections import OrderedDict
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import BooleanField, Case, CharField, Count, F, OuterRef, QuerySet, Subquery, Sum, Value, When

from osf.models import AbstractNode, Node, Preprint, Registration, TrashedFile
from addons.osfstorage.models import NodeSettings, Region

PRIVATE_SIZE_THRESHOLD = 5368709120
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
def gather_node_usage(page_size):
    logger.info('Gathering node usage at {}'.format(datetime.datetime.now()))
    region = Region.objects.filter(id=OuterRef('region_id'))
    node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(
        owner_id=OuterRef('pk'))
    node_limit = Node.objects.only(
        'id',
    ).order_by('created')
    queries = []
    page_start = 0
    page_end = page_start + page_size
    data_page = node_limit[page_start:page_end]
    while data_page.exists():
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
        )
        queries.append(node_set)
        page_start = page_end
        page_end = page_start + page_size
        data_page = node_limit[page_start:page_end]
    return queries


def gather_registration_usage(page_size):
    logger.info('Gathering registration usage at {}'.format(datetime.datetime.now()))
    region = Region.objects.filter(id=OuterRef('region_id'))
    node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(
        owner_id=OuterRef('pk'))
    registration_limit = Registration.objects.only(
        'id',
    ).order_by('created')

    queries = []
    page_start = 0
    page_end = page_start + page_size
    data_page = registration_limit[page_start:page_end]
    while data_page.exists():
        registration_set = Registration.objects.filter(id__in=Subquery(data_page.values('id'))).only(
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
        )
        queries.append(registration_set)
        page_start = page_end
        page_end = page_start + page_size
        data_page = registration_limit[page_start:page_end]
    return queries


def gather_preprint_usage(page_size):
    logger.info('Gathering preprint usage at {}'.format(datetime.datetime.now()))
    preprint_limit = Preprint.objects.only(
        'id',
    ).order_by('created')

    queries = []
    page_start = 0
    page_end = page_start + page_size
    data_page = preprint_limit[page_start:page_end]
    while data_page.exists():
        preprints_set = Preprint.objects.filter(id__in=Subquery(data_page.values('id'))).only(
            'guids',
            'type',
            'title',
            'is_public',
            'files',
            'spam_status',
            'created',
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
        )
        queries.append(preprints_set)
        page_start = page_end
        page_end = page_start + page_size
        data_page = preprint_limit[page_start:page_end]
    return queries


def gather_quickfile_usage(page_size):
    # TODO: Make this like preprint usage when quickfiles are no longer in nodes
    # (this is why it's not part of gather_node_usage(), for easy replacement)
    logger.info('Gathering quickfile usage at {}'.format(datetime.datetime.now()))

    quickfile_limit = AbstractNode.objects.filter(
        files__type='osf.osfstoragefile',
        type='osf.quickfilesnode',
    ).only(
        'id',
    ).order_by('created')
    queries = []
    page_start = 0
    page_end = page_start + page_size
    data_page = quickfile_limit[page_start:page_end]
    while data_page.exists():
        quickfiles_set = AbstractNode.objects.filter(id__in=Subquery(data_page.values('id'))).only(
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
            is_spam=Value(False, BooleanField()),
            roots_id=F('guids___id'),
            region_name=Value('United States', CharField())
        ).filter(
            files__versions__count__gte=1,
        )
        queries.append(quickfiles_set)
        page_start = page_end
        page_end = page_start + page_size
        data_page = quickfile_limit[page_start:page_end]
    return queries


def gather_summary_data(size_threshold):
    logger.info('Gathering summary data at {}'.format(datetime.datetime.now()))
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
        files__versions__size__sum__lt=size_threshold,
    ).aggregate(under=Sum('files__versions__size__sum'))['under']
    if not under:
        under = 0
    logger.info('Over 5')
    over = private.filter(
        files__versions__size__sum__gte=size_threshold,
    ).aggregate(over=Sum('files__versions__size__sum'))['over']
    if not over:
        over = 0

    return deleted, registrations, public, under, over


def convert_regional_data(regional_data):
    # logger.info('Convert regional data: {}'.format(regional_data))
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
                row_to_write.append(item)
            writer.writerow(row_to_write)


def process_usages(write_detail=True, write_summary=True, page_size=1000, size_threshold=PRIVATE_SIZE_THRESHOLD):
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
        'node': gather_node_usage(page_size=page_size),
        'registration': gather_registration_usage(page_size=page_size),
        'preprint': gather_preprint_usage(page_size=page_size),
        'quickfile': gather_quickfile_usage(page_size=page_size),
    }

    regional_totals = {}
    quickfiles = 0
    preprints = 0
    supplemental_node_total = 0
    index = 0

    for key in usage_details.keys():
        logger.info('Processing {}'.format(key))
        for item in usage_details[key]:
            index += 1
            logger.info('Index: {}'.format(index))

            if key == 'quickfile':
                logger.info('Quickfile totals at {}'.format(datetime.datetime.now()))
                quickfiles_total = item.aggregate(
                    quickfiles_total=Sum('files__versions__size__sum'),
                ).get('quickfiles_total', 0)
                quickfiles += quickfiles_total
                logger.info('Quickfile regional_totals: {}'.format(quickfiles_total))
                regional_totals = combine_regional_data(
                    regional_totals,
                    {'United States': quickfiles_total},
                )
            else:
                logger.info('Other regional_totals at {}'.format(datetime.datetime.now()))
                regional_totals = combine_regional_data(
                    regional_totals,
                    item.values('region_name').annotate(Sum('files__versions__size'))
                )
            if key == 'preprint':
                logger.info('Preprint totals at {}'.format(datetime.datetime.now()))
                preprints += item.aggregate(
                    preprints_total=Sum('files__versions__size__sum'),
                )['preprints_total']
                supplemental_node_usage = Node.objects.filter(
                    id__in=Subquery(item.values('node')),
                    files__type='osf.osfstoragefile',
                    is_deleted=False,
                ).annotate(
                    Count('files__versions'),
                    Sum('files__versions__size'),
                ).filter(
                    files__versions__count__gte=1,
                )

                supplemental_node_total += supplemental_node_usage.aggregate(
                    supplemental_node_total=Sum('files__versions__size__sum'),
                ).get('supplemental_node_total', 0)

            if write_detail:
                logger.info('Writing ./data-usage-raw-{}.csv'.format(index))

                data = item.values_list(*VALUES)
                write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(index))

    deleted, registrations, public, under, over = gather_summary_data(size_threshold=size_threshold)
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
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--page_size',
            type=int,
            default=1000,
            help='How many items at a time to include for each query',
        )
        parser.add_argument(
            '--size_threshold',
            type=int,
            default=PRIVATE_SIZE_THRESHOLD,
            help='How big should a node storage be to be considered big',
        )

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logging.info('Script started time: {}'.format(script_start_time))
        process_usages(
            write_summary=not options['dry_run'],
            write_detail=not options['dry_run'],
            page_size=options['page_size'],
            size_threshold=options['size_threshold']
        )

        script_finish_time = datetime.datetime.now()
        logging.info('Script finished time: {}'.format(script_finish_time))
        logging.info('Run time {}'.format(script_finish_time - script_start_time))
