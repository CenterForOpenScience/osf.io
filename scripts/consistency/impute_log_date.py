"""Due to an unknown bug, a handful of logs were saved without dates. This
script identifies logs without dates and imputes dates using ObjectIds.

Dry run: python -m scripts/consistency/impute_log_date
Real: python -m scripts/consistency/impute_log_date false

"""

from bson import ObjectId

from website.app import init_app
from website import models
from framework import Q

app = init_app()

def impute_log_date(dry_run=True):
    no_date = models.NodeLog.find(
        Q('date', 'eq', None)
    )
    for log in no_date:
        oid = ObjectId(log._primary_key)
        imputed_date = oid.generation_time
        print u'Imputing date {} for log ID {}'.format(
            imputed_date.strftime('%c'),
            log._primary_key,
        )
        if not dry_run:
            log._fields['date'].__set__(log, imputed_date, safe=True)
            log.save()

if __name__ == '__main__':
    import sys
    dry_run = len(sys.argv) == 1 or sys.argv[1].lower() not in ['f', 'false']
    impute_log_date(dry_run=dry_run)
