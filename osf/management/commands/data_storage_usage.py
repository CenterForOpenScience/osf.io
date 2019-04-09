# -*- coding: utf-8 -*-
import csv
from collections import OrderedDict
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import BooleanField, Case, CharField, Count, OuterRef, Subquery, Sum, Value, When

from osf.models import AbstractNode, Node, Preprint, Registration, TrashedFile
from addons.osfstorage.models import NodeSettings, Region
import os

over_under = 1478542654  # 5368709120

class Command(BaseCommand):
    """Get raw and summary data of storage usage for Product and Metascience"""

    def __init__(self):
        super(Command, self).__init__()
        today = date.today().isoformat()
        self.summary_data = OrderedDict([
            ('date', today),
            ('total', 0),
            ('deleted', 0),
            ('registrations', 0),
            ('nd_quick_files', 0),
            ('nd_public_nodes', 0),
            ('nd_private_nodes_under5', 0),
            ('nd_private_nodes_over5', 0),
            ('nd_preprints', 0),
            ('nd_supp_nodes', 0),
            ('canada', 0),
            ('australia', 0),
            ('germany', 0),
        ])


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
                is_spam=Case(
                    When(spam_status=2, then=True),
                    default=Value(False),
                    output_field=BooleanField()
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
                'is_spam',
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
            is_spam=Case(
                When(spam_status=2, then=True),
                default=Value(False),
                output_field=BooleanField()
            ),
        ).filter(
            files__versions__count__gte=1,
        )

        preprint_total = preprint_files.all()\
            .aggregate(preprint_total=Sum('files__versions__size__sum'))['preprint_total']
        self.summary_data['nd_preprints'] = preprint_total
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
            'is_spam',
        )

    def gather_quickfile_usage(self):
        # Make this like preprint usage when quickfiles are no longer in nodes
        pass

    def gather_summary_data(self):
        deleted = TrashedFile.objects.all().aggregate(total_deleted=Sum('versions__size'))['total_deleted']
        self.summary_data['deleted'] = deleted

        registrations = Registration.objects.all().annotate(
                Count('files__versions'),
                Sum('files__versions__size'),
        ).filter(
                files__versions__count__gte=1,
        ).aggregate(
            registrations=Sum('files__versions__size')
        )['registrations']
        self.summary_data['registrations'] = registrations

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
        public = nodes.filter(is_public=True).aggregate(public=Sum('files__versions__size'))['public']
        if not public:
            public = 0
        self.summary_data['nd_public_nodes'] = public
        private = nodes.filter(is_public=False).annotate(Sum('files__versions__size'))
        under = private.filter(
                files__versions__size__lt=over_under,
            ).aggregate(under=Sum('files__versions__size'))['under']
        if not under:
            under = 0
        self.summary_data['nd_private_nodes_under5'] = under
        over = private.filter(
                files__versions__size__gte=over_under,
            ).aggregate(over=Sum('files__versions__size'))['over']
        if not over:
            over = 0
        self.summary_data['nd_private_nodes_over5'] = over

        preprints = self.summary_data['nd_preprints']
        quickfiles = self.summary_data['nd_quick_files']
        print('Del {} Reg {} QF {} Pub {} Und {} Ove {} Prep {}'.format(deleted, registrations, quickfiles, public, under, over, preprints))
        self.summary_data['total'] = deleted + registrations + quickfiles + public + under + over + preprints

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
                'is_spam',
            ])
            for row in data:
                writer.writerow([s.encode('utf-8') if isinstance(s, (str, unicode)) else s for s in row])

    def write_summary_data(self, filename):
        header_row = []
        summary_row = []
        for key in self.summary_data:
            header_row += [key]
            summary_row += [self.summary_data[key]]

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

    # Management command handler
    def handle(self, *args, **options):
        node_usage = self.gather_node_usage()
        preprint_usage = self.gather_preprint_usage()
        # quickfile_usage = self.gather_quickfile_usage()
        data = list(node_usage)+list(preprint_usage)
        today = date.today().isoformat()
        self.write_raw_data(data=data, filename='./data-usage-raw-{}.csv'.format(today))

        self.gather_summary_data()
        self.write_summary_data(filename='./osf_storage_metrics.csv')
