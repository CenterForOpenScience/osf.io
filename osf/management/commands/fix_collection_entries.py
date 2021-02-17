import logging

from django.core.management.base import BaseCommand
from osf.models import AbstractNode, CollectionProvider

logger = logging.getLogger(__name__)

def remove_deleted_and_private(coll_id):
    collection_prov = CollectionProvider.load(coll_id)
    if not coll_id:
        raise RuntimeError('Collection Provider not found. Try again.')
    collection = collection_prov.primary_collection
    coll_submissions = collection.collectionsubmission_set.all()
    submissions_removed = 0
    for submission in coll_submissions:
        node = AbstractNode.load(submission.guid._id)
        if not node.is_public or node.deleted is not None:
            submission.remove_from_index()
    logger.info(f'{submissions_removed} submissions removed from collection')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('coll_id', type=str, nargs='+', help='Collection ID')

    def handle(self, *args, **options):
        coll_id = options.get('coll_id', [])[0]
        remove_deleted_and_private(coll_id)
