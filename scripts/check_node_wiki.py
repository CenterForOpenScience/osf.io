import logging
import sys

from framework.transactions.context import TokuTransaction

from website.app import init_app
from framework.mongo import database
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def get_projects():
    return database.node.find({'is_deleted': False}, {'wiki_pages_versions': True})


def log_ref(ref):
    logger.error(
        'NodeWikiPage {} points to wrong node {} instead of correct node {}'.format(
            ref['wiki'], ref['actual'], ref['correct']
        )
    )


def main():
    incorrect_refs = []
    nodes = get_projects()
    target_count = nodes.count()
    count = 0
    for node in nodes:
        count += 1
        if not count % 50 or count == target_count:
            logger.info('({}/{}) Checking {}'.format(count, target_count, node['_id']))
        for key in node['wiki_pages_versions']:
            for wiki_id in node['wiki_pages_versions'][key]:
                wiki = database.nodewikipage.find_one({'_id': wiki_id}, {'node': True})
                if wiki['node'] != node['_id']:
                    incorrect_refs.append({'wiki': wiki_id, 'actual': wiki['node'], 'correct': node['_id']})

    if len(incorrect_refs):
        for ref in incorrect_refs:
            log_ref(ref)
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