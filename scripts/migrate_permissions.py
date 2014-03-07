#!/usr/bin/env
# -*- coding: utf-8 -*-
"""Grant full permissions to all current contributors.
"""

from website import app, models, settings

import logging
logger = logging.getLogger(__name__)

settings.USE_SOLR = False

def main():
    app.init_app()
    for node in models.Node.find():
        migrate_permissions(node)

def migrate_permissions(node):
    for contributor in node.contributors:
        node.set_permissions(
            contributor, ['read', 'write', 'admin'], save=False
        )
    node.save()
    logger.info('Finished migrating node {0}'.format(node._id))

if __name__ == '__main__':
    main()
