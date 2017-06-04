"""
Remove forward slashes from wiki page titles, since it is no longer an allowed character and
breaks validation.
"""
import logging
import sys

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.project.model import Node
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    wiki_pages = db.nodewikipage.find({'page_name': {'$regex': '/'}},
                                      {'_id': True, 'page_name': True, 'node': True})
    wiki_pages = wiki_pages.batch_size(200)
    fix_wiki_titles(wiki_pages)


def fix_wiki_titles(wiki_pages):
    for i, wiki in enumerate(wiki_pages):
        old_name = wiki['page_name']
        new_name = wiki['page_name'].replace('/', '')

        # update wiki page name
        db.nodewikipage.update({'_id': wiki['_id']}, {'$set': {'page_name': new_name}})
        logger.info('Updated wiki {} title to {}'.format(wiki['_id'], new_name))

        node = Node.load(wiki['node'])
        if not node:
            logger.info('Invalid node {} for wiki {}'.format(node, wiki['_id']))
            continue

        # update node wiki page records
        if old_name in node.wiki_pages_versions:
            node.wiki_pages_versions[new_name] = node.wiki_pages_versions[old_name]
            del node.wiki_pages_versions[old_name]

        if old_name in node.wiki_pages_current:
            node.wiki_pages_current[new_name] = node.wiki_pages_current[old_name]
            del node.wiki_pages_current[old_name]

        if old_name in node.wiki_private_uuids:
            node.wiki_private_uuids[new_name] = node.wiki_private_uuids[old_name]
            del node.wiki_private_uuids[old_name]
        node.save()


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
