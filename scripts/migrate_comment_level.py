#!/usr/bin/env
# -*- coding: utf-8 -*-
"""Set all projects to private commenting
"""

from website import app, models, settings

import logging
logger = logging.getLogger(__name__)

settings.SEARCH_ENGINE = None

def main():
    app.init_app()
    for node in models.Node.find():
        node.comment_level = 'private'
        node.save()
        logger.info('Finished migrating node {0}'.format(node._id))

if __name__ == '__main__':
    main()
