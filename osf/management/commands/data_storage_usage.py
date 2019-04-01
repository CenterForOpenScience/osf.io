# -*- coding: utf-8 -*-
import csv
import os.path
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import BooleanField, Case, CharField, Count, OuterRef, Subquery, Sum, Value, When

from osf.models import AbstractNode, Preprint, TrashedFile
from addons.osfstorage.models import NodeSettings, Region


class Command(BaseCommand):
    """Get raw and summary data of storage usage for Product and Metascience"""

    def __init__(self):
        super(Command, self).__init__()
        today = date.today().isoformat()
        self.summary_data = ['2019-03-27']
        self.summary_headers = ['Date']
        self.total = 0

    # Detail gatherers
    @staticmethod
    def gather_node_usage():
        region = Region.objects.filter(id=OuterRef('region_id'))
        node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('name')[:1])).filter(owner_id=OuterRef('pk'))
        return AbstractNode.objects.filter(
                files__type='osf.osfstoragefile',
            ).exclude(
                spam_status=2,  # SPAM
            ).annotate(
                Count('files__versions'),
                Sum('files__versions__size'),
                roots_id=Case(
                    When(root__isnull=False, then='root__guids___id'),
                    default=Value(None),
                    output_field=CharField(),
                ),
            region=Subquery(node_settings.values('region_abbrev')[:1])
        ).filter(
                files__versions__count__gte=1,
            ).order_by(
                '-files__versions__size__sum',
            ).values_list(
                'guids___id',
                'type',
                'roots_id',
                'title',
                'is_fork',
                'is_public',
                'is_deleted',
                'region',
                'files__versions__count',
                'files__versions__size__sum',
            )

    def gather_preprint_usage(self):
        preprint_files = Preprint.objects.exclude(
            spam_status=2,  # SPAM
        ).annotate(
            Count('files__versions'),
            Sum('files__versions__size'),
            type=Value('osf.preprint', CharField()),
            rootz_id=Value('', CharField()),
            is_fork=Value(False, BooleanField()),
            is_deleted=Case(
                When(date_withdrawn__isnull=True, then=False),
                default=Value(True),
                output_field=BooleanField(),
            ),
        ).filter(
            files__versions__count__gte=1,
        )

        preprint_total = preprint_files.all()\
            .aggregate(preprint_total=Sum('files__versions__size__sum'))['preprint_total']
        self.total += int(preprint_total)
        self.summary_data.append(preprint_total)
        self.summary_headers.append('total_preprints')

        return preprint_files.order_by(
            '-files__versions__size__sum',
        ).values_list(
            'guids___id',
            'type',
            'guids___id',
            'title',
            'is_fork',
            'is_public',
            'is_deleted',
            'region__name',
            'files__versions__count',
            'files__versions__size__sum',
        )

    # Summary Gatherers
    def total_deleted_summary(self):
        total = TrashedFile.objects.all().aggregate(total_deleted=Sum('versions__size'))['total_deleted']
        self.update_summary(
            summary=total,
            header='total_deleted',
        )
        self.total += total

    # Summary helpers
    def update_summary(self, summary, header):
        self.summary_data.append(summary)
        self.summary_headers.append(header)

    def gather_summary_data(self):
        self.total_deleted_summary()

        self.summary_data.append(str(self.total))
        self.summary_headers.append('total')

    # Data writers
    @staticmethod
    def write_raw_data(data, filename):
        with open(filename, 'wb') as fp:
            # for row in data:
                # print([s.encode('utf-8') if isinstance(s, (str, unicode)) else s for s in row])
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
            ])
            for row in data:
                writer.writerow([s.encode('utf-8') if isinstance(s, (str, unicode)) else s for s in row])

    def write_summary_data(self, filename):
        if os.path.isfile(filename):
            with open(filename) as old_file:
                reader = csv.reader(old_file, delimiter=',', lineterminator='\n')
                summary_rows = [row for row in reader]
        else:
            summary_rows = [self.summary_headers]
        with open(filename, 'w') as fp:
            writer = csv.writer(fp, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
            for row in summary_rows:
                writer.writerow(row)
            writer.writerow(self.summary_data)

    # Management command handler
    def handle(self, *args, **options):
        node_usage = self.gather_node_usage()
        preprint_usage = self.gather_preprint_usage()
        data = list(node_usage)+list(preprint_usage)
        today = date.today().isoformat()
        self.write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(today))

        self.gather_summary_data()
        self.write_summary_data(filename='./osf_storage_metrics.csv')
