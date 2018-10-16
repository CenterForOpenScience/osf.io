import sys
import csv
import logging
import datetime

from website.app import setup_django
setup_django()

from osf.models import Node, SpamStatus
from django.db.models import Count
from scripts import utils as script_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    nodes_excluding_spam = Node.objects.filter(is_deleted=False,  created__gte=datetime.datetime(2018, 3, 14)).exclude(spam_status__in=[SpamStatus.SPAM, SpamStatus.FLAGGED])

    # The extra statement here is to round down the datetimes so we can count by dates only
    data = nodes_excluding_spam.extra({'date_created': 'date(created)'}).values('date_created').annotate(count=Count('id')).order_by('date_created')

    with open('spamless_node_count_through_2018_3_14.csv', mode='w') as csv_file:
        fieldnames = ['date_created', 'count']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not dry_run:
            writer.writeheader()
            for data_point in data:
                writer.writerow(data_point)

    logger.info('Writing csv data for {} dates'.format(data.count()))


if __name__ == '__main__':
    main()
