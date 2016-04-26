# -*- coding: utf-8 -*-
"""Ensure that all nodes will pass title validation (i.e. have <=200 characters.)"""
from __future__ import unicode_literals
import logging
import sys

from framework.mongo import database as db
from website.app import init_app
from framework.transactions.context import TokuTransaction

from scripts import utils as script_utils

logger = logging.getLogger(__name__)
MAX_TITLE_LENGTH = 200

def main():
    count = 0
    for node in db.node.find({'$where': 'this.title.length > 200'}):
        logger.info('Updating node {}'.format(node['_id']))
        logger.info('Old title: {}'.format(node['title']))
        new_title = node['title'][:MAX_TITLE_LENGTH]
        logger.info('New title: {}'.format(new_title))
        db.node.update({'_id': node['_id']}, {
            'title': new_title
        })
        count += 1
    logger.info('Updated {} nodes'.format(count))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
