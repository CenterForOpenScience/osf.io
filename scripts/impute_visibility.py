"""
Set all contributors to visible.
"""

import logging

from website.app import init_app
from website import models


app = init_app('website.settings', set_backends=True, routes=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def impute_visibility():
    for node in models.Node.find():
        logger.info('Migrating node {0}'.format(node._id))
        node.visible_contributor_ids = node.contributors._to_primary_keys()
        # Saving may fail for unrelated reasons; catch and log exceptions
        try:
            node.save()
            logger.info('Migration successful')
        except Exception as error:
            logger.error('Error migrating visibility on node {0}'.format(node._id))
            logger.exception(error)

if __name__ == '__main__':
    impute_visibility()
