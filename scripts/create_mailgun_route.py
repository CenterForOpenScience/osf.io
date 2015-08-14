# -*- coding: utf-8 -*-

"""Create mailing lists for all top-level projects
"""

import sys
import logging
import requests

logger = logging.getLogger(__name__)

def migrate_node(node, dry=False):

    for user in node.contributors:
        if not user.is_active:
            logger.info('Unsubscribing user {} on node {} since it is not active'.format(user, node))
            node.mailing_unsubs.append(user)

    if not node.parent_node:
        logger.info('Creating mailing list for node {}'.format(node))
        node.mailing_enabled = True
        if not dry:
            create_list(title=node.title, **node.mailing_params)

    if not dry:
        node.save()


def main():
    init_app(routes=False)
    dry = 'dry' in sys.argv
    for node in Node.find():
        migrate_node(node, dry)
        logger.info('Finished migrating node {0}'.format(node._id))

if __name__ == '__main__':
    main()

