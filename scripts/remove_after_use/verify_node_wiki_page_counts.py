# -*- coding: utf-8 -*-
import sys
import logging
from website.app import setup_django, init_app
from scripts import utils as script_utils
from django.db import transaction

setup_django()
from osf.models import AbstractNode
from addons.wiki.models import WikiPage, WikiVersion


logger = logging.getLogger(__name__)

def count_node_wiki_pages():
    """
    Assert that counts for created WikiPages and WikiVersions are correct.
    """
    nodes_with_wikis = AbstractNode.objects.exclude(wiki_pages_versions={}).exclude(type='osf.collection').exclude(type='osf.quickfilesnode')
    wiki_page_count = 0
    wiki_version_counts = 0
    for node in nodes_with_wikis:
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            wiki_page_count += 1
            wiki_version_counts += len(version_list)
    print "{} wiki pages expected".format(wiki_page_count)
    print "{} wiki versions expected".format(wiki_version_counts)
    assert wiki_page_count == WikiPage.objects.count()
    assert wiki_version_counts == WikiVersion.objects.count()

def main(dry=True):
    init_app(routes=False)
    count_node_wiki_pages()

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
