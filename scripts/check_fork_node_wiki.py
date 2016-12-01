import logging
import sys

from modularodm import Q
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.project.model import Node
from website.addons.wiki.model import NodeWikiPage
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def get_fork_projects():
    return Node.find(
        Q('is_fork', 'exists', True) &
        Q('is_deleted', 'eq', False)
    )


def main():
    counts = 0
    for node in get_fork_projects():
        if node.wiki_pages_versions:
            for key in node.wiki_pages_versions:
                for wiki_id in node.wiki_pages_versions[key]:
                    wiki = NodeWikiPage.load(wiki_id)
                    if wiki.node._id != node._id:
                        logger.info(
                            'NodeWikiPage {} points to wrong node {} instead of correct node {}'.format(
                                wiki_id, wiki.node._id, node._id
                            ))
                        counts += 1
    if counts == 0:
        logger.info('All wiki of fork nodes point to the correct nodes')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')