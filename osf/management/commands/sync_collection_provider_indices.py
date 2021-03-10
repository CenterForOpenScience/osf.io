import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework.celery_tasks import app
from osf.models import CollectionProvider

logger = logging.getLogger(__name__)

@app.task(name='osf.management.commands.sync_collection_provider_indices')
def sync_collection_provider_indices(cp_ids=None, only_remove=False):
    if cp_ids:
        qs = CollectionProvider.objects.filter(_id__in=cp_ids)
    else:
        qs = CollectionProvider.objects.all()
    for prov in qs.all():
        collection = prov.primary_collection
        coll_submissions = collection.collectionsubmission_set.all()
        remove_ct = 0
        add_ct = 0
        for submission in coll_submissions:
            target = submission.guid.referent
            if not target.is_public or target.deleted:
                submission.remove_from_index()
                remove_ct += 1
            elif not only_remove:
                submission.update_index()
                add_ct += 1
        logger.info(f'{remove_ct} submissions removed from {prov._id}')
        logger.info(f'{add_ct} submissions synced to {prov._id}')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--collection_provider_ids',
            type=str,
            nargs='*',
            help='List of CollectionProvider._id to sync'
        )
        parser.add_argument(
            '--only_remove',
            type=bool,
            default=False,
            help='Flag to only remove deleted or private objects from collection.'
        )

    def handle(self, *args, **options):
        script_start_time = timezone.now()
        logger.info('script started time: {}'.format(script_start_time))
        logger.debug(options)

        cp_ids = options.get('collection_provider_ids', None)
        sync_collection_provider_indices(cp_ids)

        script_finish_time = timezone.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
