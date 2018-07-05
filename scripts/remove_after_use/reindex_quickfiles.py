import sys

import progressbar
from django.core.paginator import Paginator

from website.app import setup_django
setup_django()

from website.search.search import update_file
from osf.models import QuickFilesNode

PAGE_SIZE = 50

def reindex_quickfiles(dry):
    qs = QuickFilesNode.objects.all().order_by('id')
    count = qs.count()
    paginator = Paginator(qs, PAGE_SIZE)

    progress_bar = progressbar.ProgressBar(maxval=count).start()
    n_processed = 0
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for quickfiles in page.object_list:
            for file_ in quickfiles.files.all():
                if not dry:
                    update_file(file_)
        n_processed += len(page.object_list)
        progress_bar.update(n_processed)

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    reindex_quickfiles(dry=dry)
