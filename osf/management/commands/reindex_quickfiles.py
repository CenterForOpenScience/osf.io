from django.core.paginator import Paginator
from website.search.search import update_file
from osf.models import Node, NodeLog
from addons.osfstorage.models import OsfStorageFileNode
from django.core.management.base import BaseCommand

PAGE_SIZE = 100
from tqdm import tqdm

def reindex_quickfiles(dry_run):
    file_ids = Node.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    ).values_list('files__id', flat=True)

    files_to_reindex = OsfStorageFileNode.objects.filter(id__in=file_ids)
    paginator = Paginator(files_to_reindex, PAGE_SIZE)

    progress_bar = tqdm(total=files_to_reindex.count())
    n_processed = 0
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for quickfile in page.object_list:
            if not dry_run:
                update_file(quickfile)
        n_processed += len(page.object_list)
        progress_bar.update(n_processed)
    progress_bar.close()


class Command(BaseCommand):
    """
    Reindex all Quickfiles files that were moved during migration. h/t to erinspace who's code old I'm cribbing here.
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
            required=False,
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', None)
        reindex_quickfiles(dry_run)
