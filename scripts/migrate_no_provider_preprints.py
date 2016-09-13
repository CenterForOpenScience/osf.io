import sys
import logging
from modularodm import Q

from website.app import init_app
from website.models import PreprintProvider, Node


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run):
    if dry_run:
        logger.warn('Running in DRY mode')
    osf = PreprintProvider.load('osf')
    nodes = Node.find(Q('preprint_file', 'ne', None))
    for node in nodes:
        if node.is_preprint and node.preprint_providers == []:
            node.preprint_providers.append(osf)
            logger.info('OSF provider added to {}'.format(node.title))
            if not dry_run:
                node.save()


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    main(dry_run=dry_run)


