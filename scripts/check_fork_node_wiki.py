import logging
import sys

from framework.transactions.context import TokuTransaction

from website.app import init_app
from framework.mongo import database
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def get_fork_projects():
    return database.node.find({'is_fork': True, 'is_deleted': False}, {'wiki_page_versions': True})


def main():
    counts = 0
    for node in get_fork_projects():
        logger.info('Going through the wikis of node {}'.format(node._id))
        for key in node.wiki_pages_versions:
            for wiki_id in node.wiki_pages_versions[key]:
                wiki = database.nodewikipage.find_one({'_id': wiki_id}, {'node': True})
                if wiki['node'] != node._id:
                    logger.error(
                        'NodeWikiPage {} points to wrong node {} instead of correct node {}'.format(
                            wiki_id, wiki.node._id, node._id
                        ))
                    counts += 1
    if counts != 0:
        logger.info('There are {} wikis points to the wrong node.'.format(counts))
    else:
        logger.info('All wiki of fork nodes point to the correct node.')



if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')