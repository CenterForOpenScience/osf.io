"""
Create copies of wiki pages for existing forks and registrations instead of
using the same NodeWikiPage objects as the original node.
"""
import logging
import sys

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

from website.addons.wiki.model import NodeWikiPage
from website.models import Node
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

BACKUP_COLLECTION = 'unmigratedwikipages'


def main():
    nodes = db.node.find({}, {'_id': True})
    nodes = nodes.batch_size(200)
    update_wiki_pages(nodes)


def update_wiki_pages(nodes):
    for i, node in enumerate(nodes):
        if node.wiki_pages_versions:
            cloned_wiki_pages = {}
            for key, wiki_versions in node.wiki_pages_versions.items():
                cloned_wiki_pages[key] = []
                for wiki_id in wiki_versions:
                    node_wiki = NodeWikiPage.load(wiki_id)
                    if not node_wiki:
                        continue
                    if node_wiki.to_storage()['node'] != node._id:
                        clone = node_wiki.clone_wiki(node)
                        logger.info('Cloned wiki page {} from node {} to {}'.format(wiki_id, node_wiki.node, node))
                        cloned_wiki_pages[key].append(clone._id)

                        # update current wiki page
                        if node_wiki.is_current:
                            node.wiki_pages_current[key] = clone._id

                        if not node_wiki.node:
                            move_to_backup_collection(node_wiki._id)
                    else:
                        cloned_wiki_pages[key].append(wiki_id)
            node.wiki_pages_versions = cloned_wiki_pages
            node.save()

        # clear ODM cache
        if i % 1000 == 0:
            for key in ('node', 'user','fileversion', 'storedfilenode'):
                Node._cache.data.get(key, {}).clear()
                Node._object_cache.data.get(key, {}).clear()


# Wiki pages with nodes that no longer exist are removed from NodeWikiPage
# and put into a separate collection
def move_to_backup_collection(wiki_id):
    wiki = db.nodewikipage.find_one({'_id': wiki_id})
    assert wiki
    db[BACKUP_COLLECTION].insert(wiki)
    db.nodewikipage.remove({'_id': wiki_id}, just_one=True)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
