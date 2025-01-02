from django.core.management.base import BaseCommand
from django.apps import apps
from tqdm import tqdm

class Command(BaseCommand):
    help = "Migrate preprints to the versioned style"

    def add_arguments(self, parser):
        parser.add_argument(
            '-batch_size',
            type=int,
            default=1,
            help='Batch size for processing preprints (default: 1)',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        ContentType = apps.get_model('contenttypes', 'ContentType')
        Preprint = apps.get_model('osf', 'Preprint')
        GuidVersionsThrough = apps.get_model('osf', 'GuidVersionsThrough')

        content_type_id = ContentType.objects.get_for_model(Preprint).id

        first_id = Preprint.objects.filter(versioned_guids__isnull=True).order_by('id').first().id
        last_id = Preprint.objects.filter(versioned_guids__isnull=True).order_by('id').last().id

        vq_list = []
        p_batch_ids = [[x, x + batch_size - 1] for x in range(first_id, last_id, batch_size)]

        for ids in tqdm(p_batch_ids, desc='Processing', unit='batch'):
            preprints_list = Preprint.objects.filter(id__range=ids)
            for preprint in preprints_list:
                guid = preprint.guids.first()
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
                GuidVersionsThrough.objects.bulk_create(vq_list, batch_size=len(vq_list))
            vq_list = []
        self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))
