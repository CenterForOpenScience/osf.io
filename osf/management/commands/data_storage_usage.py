# -*- coding: utf-8 -*-
import csv
from collections import OrderedDict
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import BooleanField, Case, CharField, Count, F, OuterRef, QuerySet, Subquery, Sum, Value, When

from osf.models import AbstractNode, Node, Preprint, Registration, TrashedFile
from addons.osfstorage.models import NodeSettings, Region
import os

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


# Detail gatherers
def gather_node_usage():
    region = Region.objects.filter(id=OuterRef('region_id'))
    node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(
        owner_id=OuterRef('pk'))
    node_set = Node.objects.exclude(
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
    )
    return node_set


def gather_registration_usage():
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
    )

    return registration_set


def gather_preprint_usage():
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
    )

    return preprints


def gather_quickfile_usage():
    # TODO: Make this like preprint usage when quickfiles are no longer in nodes
    # (this is why it's not part of gather_node_usage(), for easy replacement)

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
    )

    return quickfiles


def gather_summary_data():
    deleted = TrashedFile.objects.all().aggregate(total_deleted=Sum('versions__size'))['total_deleted']

    registrations = Registration.objects.all().annotate(
            Count('files__versions'),
            Sum('files__versions__size'),
    ).filter(
            files__versions__count__gte=1,
    ).aggregate(
        registrations=Sum('files__versions__size__sum')
    )['registrations']

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
    public = nodes.filter(is_public=True).aggregate(public=Sum('files__versions__size__sum'))['public']
    if not public:
        public = 0
    private = nodes.filter(is_public=False).annotate(Sum('files__versions__size'))
    under = private.filter(
            files__versions__size__sum__lt=PRIVATE_SIZE_THRESHOLD,
        ).aggregate(under=Sum('files__versions__size__sum'))['under']
    if not under:
        under = 0
    over = private.filter(
            files__versions__size__sum__gte=PRIVATE_SIZE_THRESHOLD,
        ).aggregate(over=Sum('files__versions__size__sum'))['over']
    if not over:
        over = 0

    return deleted, registrations, public, under, over


def convert_regional_data(regional_data):
    return {item['region_name']: item['files__versions__size__sum'] for item in regional_data}


def combine_regional_data(*args):
    regional_totals = {}
    for region_data_item in args:
        if isinstance(region_data_item, QuerySet):
            region_data_set = convert_regional_data(region_data_item)
        else:
            region_data_set = region_data_item
        for key in region_data_set.keys():
            regional_totals[key] = regional_totals.get(key, 0) + region_data_set.get(key, 0)
    return regional_totals


def paginate_data(data, index=0):
    start = 0
    end = PAGE_SIZE + 1
    for lines in range(0, data.count(), PAGE_SIZE):
        index += 1
        yield data[start:end], index
        end += PAGE_SIZE
        start += PAGE_SIZE


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
        pages = paginate_data(usage_details[key], index=index)
        for data_page, index in pages:
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
                )['supplemental_node_total']

            if write_detail:
                data = data_page.values_list(*VALUES)
                write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(index))

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
    """Get raw and summary data of storage usage for Product and Metascience"""

    # Management command handler
    def handle(self, *args, **options):
        process_usages()
