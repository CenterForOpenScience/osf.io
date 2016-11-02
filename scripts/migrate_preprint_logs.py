import sys
import logging
from datetime import datetime

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from website.app import init_app
from website.models import NodeLog, PreprintService

logger = logging.getLogger(__name__)


def main(dry):
    if dry:
        logging.warn('DRY mode running')
    now = datetime.utcnow()
    initiated_logs = NodeLog.find(Q('action', 'eq', NodeLog.PREPRINT_INITIATED) & Q('date', 'lt', now))
    for log in initiated_logs:
        try:
            preprint = PreprintService.find_one(Q('node', 'eq', log.node))
            log.params.update({
                'preprint': {
                    'id': preprint._id
                },
                'service': {
                    'name': preprint.provider.name
                }
            })
            logging.info('Updating log {} from node {}, with preprint id: {}'.format(log._id, log.node.title, preprint._id))
            if not dry:
                log.save()
        except NoResultsFound:
            pass

    updated_logs = NodeLog.find(Q('action', 'eq', NodeLog.PREPRINT_FILE_UPDATED) & Q('date', 'lt', now))
    for log in updated_logs:
        try:
            preprint = PreprintService.find_one(Q('node', 'eq', log.node))
            log.params.update({
                'preprint': {
                    'id': preprint._id
                }
            })
            logging.info('Updating log {} from node {}, with preprint id: {}'.format(log._id, log.node.title, preprint._id))
            if not dry:
                log.save()
        except NoResultsFound:
            pass

if __name__ == '__main__':
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    main(dry)
