"""
Script to send updates to Datacite for projects that were updated
while the DISABLE_DATACITE_DOIS switch was active.

Start date:
    Dec 14, 2018 @ 10:09 PM EST = Dec 15, 2018 @ 03:09 UTC
End date:
    Dec 15, 2018 @ 12:34 PM EST = Dec 15, 2018 @ 17:34 UTC
"""
import datetime
import logging
import pytz
import waffle

from website.app import setup_django
setup_django()

from osf import features
from osf.models import Node

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


START_DATE = datetime.datetime(2018, 12, 15, 3, 9, tzinfo=pytz.UTC)
END_DATE = datetime.datetime(2018, 12, 15, 17, 34, tzinfo=pytz.UTC)


def main():
    assert not waffle.switch_is_active(features.DISABLE_DATACITE_DOIS)

    nodes = Node.objects.filter(
        identifiers__category='doi',
        identifiers__deleted__isnull=True,
        last_logged__gte=START_DATE,
        last_logged__lte=END_DATE
    )

    logger.info('Sending {} nodes to Datacite'.format(nodes.count()))

    for node in nodes:
        logger.info('Sending {} to Datacite for update.'.format(node._id))
        node.request_identifier_update(category='doi')

if __name__ == '__main__':
    main()
