"""Due to an unknown bug, wiki pages were saved without dates between
September 4 and 6. This script identifies wiki pages without dates and
imputes dates using ObjectIds.

Dry run: python -m scripts/consistency/impute_wiki_date
Real: python -m scripts/consistency/impute_wiki_date false

"""

from bson import ObjectId

from website.app import init_app
from website import models
from framework import Q

app = init_app()

def impute_wiki_date(dry_run=True):
    no_date = models.NodeWikiPage.find(
        Q('date', 'eq', None)
    )
    for wiki in no_date:
        oid = ObjectId(wiki._primary_key)
        imputed_date = oid.generation_time
        print u'Imputing date {} for wiki ID {}'.format(
            imputed_date.strftime('%c'),
            wiki._primary_key,
        )
        if not dry_run:
            wiki._fields['date'].__set__(wiki, imputed_date, safe=True)
            wiki.save()

if __name__ == '__main__':
    import sys
    dry_run = len(sys.argv) == 1 or sys.argv[1].lower() not in ['f', 'false']
    impute_wiki_date(dry_run=dry_run)
