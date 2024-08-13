from django.core.paginator import Paginator
from website.search.search import update_file
from osf.models import Node, NodeLog
from addons.osfstorage.models import OsfStorageFileNode
from django.core.management.base import BaseCommand
from tqdm import tqdm

PAGE_SIZE = 100


def paginated_progressbar(queryset, page_size, function):
    paginator = Paginator(queryset, page_size)
    progress_bar = tqdm(total=queryset.count())
    n_processed = 0
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for item in page.object_list:
            function(item)
        n_processed += len(page.object_list)
        progress_bar.update(n_processed)
    progress_bar.close()


def reindex_quickfiles():
    nodes = Node.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    )

    file_ids = nodes.values_list('files__id', flat=True)

    files_to_reindex = OsfStorageFileNode.objects.filter(id__in=file_ids)
    paginated_progressbar(files_to_reindex, PAGE_SIZE, update_file)

    for node in nodes:
        node.update_search()


class Command(BaseCommand):
    """
    Reindex all Quickfiles files that were moved during migration. h/t to erinspace who's code old I'm cribbing here.
    """
    def handle(self, *args, **options):
        reindex_quickfiles()
