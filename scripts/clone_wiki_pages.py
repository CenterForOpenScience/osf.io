"""
Create copies of wiki pages for existing forks and registrations instead of
using the same NodeWikiPage objects as the original node.
"""
import logging
import sys

from framework.transactions.context import TokuTransaction

from website.addons.wiki.model import NodeWikiPage
from website.models import Node
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    nodes = Node.find()
    clone_wiki_pages(nodes)


def clone_wiki_pages(nodes):
    for i, node in enumerate(nodes):
        if node.wiki_pages_versions:
            cloned_wiki_pages = {}
            for key in node.wiki_pages_versions:
                cloned_wiki_pages[key] = []
                for wiki_id in node.wiki_pages_versions[key]:
                    node_wiki = NodeWikiPage.load(wiki_id)
                    if node_wiki.node._id != node._id:
                        clone = node_wiki.clone()
                        clone.node = node
                        clone.save()
                        logger.info('Cloned wiki page {} from node {} to {}'.format(wiki_id, node_wiki.node._id, node._id))
                        cloned_wiki_pages[key].append(clone._id)

                        # update current wiki page
                        if node_wiki.is_current:
                            node.wiki_pages_current[key] = clone._id
                    else:
                        cloned_wiki_pages[key].append(wiki_id)
            node.wiki_pages_versions = cloned_wiki_pages
            node.save()

        # clear ODM cache
        if i % 1000 == 0:
            for key in ('node', 'user','fileversion', 'storedfilenode'):
                Node._cache.data.get(key, {}).clear()
                Node._object_cache.data.get(key, {}).clear()


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
