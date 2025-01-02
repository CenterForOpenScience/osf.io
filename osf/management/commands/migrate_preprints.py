from django.core.management.base import BaseCommand
from django.apps import apps
from tqdm import tqdm


class Command(BaseCommand):
    """Migrate non-versioned preprints to versioned using guid versions.
    For each preprint, it creates an entry in the GuidVersionsThrough table as version 1.
    """

    help = 'Migrate non-versioned preprints to versioned using guid versions.'

    def add_arguments(self, parser):

        parser.add_argument(
            '--dry_run',
            action='store_true',
            dest='dry_run',
            help='Run the command without making changes to the database (default: True).',
        )

        parser.add_argument(
            '--batch_size',
            type=int,
            default=100,
            help='Batch size for processing preprints (default: 100).',
        )

    def handle(self, *args, **options):

        dry_run = options['dry_run']
        batch_size = options['batch_size']
        if dry_run:
            self.stdout.write(self.style.WARNING('This is a DRY_RUN pass!'))

        ContentType = apps.get_model('contenttypes', 'ContentType')
        GuidVersionsThrough = apps.get_model('osf', 'GuidVersionsThrough')
        Preprint = apps.get_model('osf', 'Preprint')

        content_type_id = ContentType.objects.get_for_model(Preprint).id
        first_id = Preprint.objects.filter(versioned_guids__isnull=True).order_by('id').first().id
        last_id = Preprint.objects.filter(versioned_guids__isnull=True).order_by('id').last().id

        vq_list = []
        p_batch_ids = [[x, x + batch_size - 1] for x in range(first_id, last_id, batch_size)]

        for ids in tqdm(p_batch_ids, desc='Processing', unit='batch'):
            preprints_list = Preprint.objects.filter(id__range=ids)
            for preprint in preprints_list:
                guid = preprint.guids.first()
                if not guid:
                    self.stdout.write(self.style.ERROR(f'Preprint object [pk={preprint.pk}] skipped, missing guid.'))
                else:
                    if not guid.versions.exists():
                        vq_list.append(
                            GuidVersionsThrough(
                                object_id=preprint.id,
                                version=1,
                                content_type_id=content_type_id,
                                guid_id=guid.id
                            )
                        )
            if vq_list:
                if dry_run:
                    self.stdout.write(self.style.WARNING(f'DRY_RUN: GuidVersionsThrough.objects.bulk_create() with {len(vq_list)} items ...'))
                else:
                    GuidVersionsThrough.objects.bulk_create(vq_list, batch_size=len(vq_list))
                    self.stdout.write(self.style.SUCCESS( f'{len(vq_list)} Preprints migrated ...'))
            vq_list = []
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY_RUN: Migration has completed successfully!}'))
        else:
            self.stdout.write(self.style.SUCCESS('Migration completed successfully!}'))
