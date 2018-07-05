import sys

import progressbar
from django.core.paginator import Paginator

from website.app import setup_django
setup_django()

from website.search.search import update_file
from addons.osfstorage.models import OsfStorageFile

PAGE_SIZE = 100

def reindex_quickfiles(dry):
    qs = OsfStorageFile.objects.filter(node__type='osf.quickfilesnode').order_by('id')
    count = qs.count()
    paginator = Paginator(qs, PAGE_SIZE)

    progress_bar = progressbar.ProgressBar(maxval=count).start()
    n_processed = 0
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for quickfile in page.object_list:
            if not dry:
                update_file(quickfile)
        n_processed += len(page.object_list)
        progress_bar.update(n_processed)

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    reindex_quickfiles(dry=dry)
