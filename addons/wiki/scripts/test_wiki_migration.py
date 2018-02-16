# -*- coding: utf-8 -*-
"""

Test script to run before node wiki migration addons/wiki/migrations/0007_auto_20180124_1152.py
DELETE BEFORE MERGE DELETE BEFORE MERGE
To test:
docker-compose run --rm web python -m addons/wiki/scripts/test_wiki_migration
"""
from __future__ import print_function, absolute_import

import sys

from website.app import init_app
from osf.models import AbstractNode, Comment
from addons.wiki.models import NodeWikiPage
from addons.wiki.utils import to_mongo_key

import django
django.setup()

def nodes_with_wikis():
    # Returns all nodes with wikis
    return AbstractNode.objects.exclude(wiki_pages_versions={})

def count_nodes_with_wikis():
    print ('Nodes with wikis to be looped through: {}'.format(len(nodes_with_wikis())))

def comments_to_be_repointed():
    """
    Returns comments whose root_target and/or target will have to be repointed from a NodeWikiPage to a WikiPage
    """
    wikis_with_comments = []
    for node_wiki_page in wiki_versions_to_be_created():
        if Comment.objects.filter(root_target=node_wiki_page.guids.all()[0]).exists():
            wikis_with_comments.append(node_wiki_page)
    print([wiki._id for wiki in wikis_with_comments])
    return wikis_with_comments

def count_comments_to_be_repointed():
    print ('{} Comments should be repointed'.format(len(comments_to_be_repointed())))

def count_expected_wiki_pages():
    """
    One WikiPage will be created for every key in wiki_pages_versions on all nodes with wikis.
    This function returns the number of WikiPage instances you should expect post-migration
    """
    print ('Expect {} WikiPages to be created during the migration'.format(len(wiki_pages_to_be_created())))

def count_expected_wiki_versions():
    """
    WikiVersions will be created for all guids on each key in the wiki_pages_versions dict.
    This function returns the number of WikiVersion instances you should expect post-migration.

    Note, this count will differ from counting NodeWikiPage where is_deleted=False, which is not a good way to decide which
    wikis to copy. The is_deleted property on the NodeWikiPage picks up if the wiki has been deleted, but also renamed.
    """
    print ('Expect {} WikiVersions to be created during the migration'.format(len(wiki_versions_to_be_created())))

def wiki_pages_to_be_created():
    """
    Returns a list of NodeWikiPages that need to have a WikiPage created from them.
    """
    wiki_pages = []
    for node in nodes_with_wikis():
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            wiki_pages.append(NodeWikiPage.load(version_list[0]))
    return wiki_pages

def wiki_versions_to_be_created():
    """
    Returns a list of NodeWikiPages that need to have a WikiVersion created from them
    """
    wv = []
    for node in nodes_with_wikis():
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            for version in version_list:
                wv.append(NodeWikiPage.load(version))
    return wv

def check_contributors(node, wiki_guid):
    """
    Check contributors who have the wiki_guid present in their comments_viewed_timestamp dictionary
    """
    for contrib in node.contributors:
        if contrib.comments_viewed_timestamp.get(wiki_guid, None):
            return True

def check_that_last_wiki_version_is_also_current():
    """
    Check that the latest wiki_version guid matches the wiki_pages_current guid.
    (Spoiler: this doesn't hold up on staging, there are discrepancies in some registrations and forks.
    )
    """
    discrepancies = []
    reg_fork_count = 0
    problem_discrepancies = []
    for node in nodes_with_wikis():
        for key, value in node.wiki_pages_current.iteritems():
            if node.wiki_pages_versions[key][-1] != value:
                discrepancies.append(node)
                if node.is_registration or node.is_fork:
                    reg_fork_count += 1
                # Guid will not be transformed into a WikiVersion
                current = NodeWikiPage.load(value)
                # Guid will be transformed into a WikiVersion
                former = NodeWikiPage.load(node.wiki_pages_versions[key][-1])
                if Comment.objects.filter(root_target=current.guids.all()[0]).exists() or current.page_name != former.page_name or current.version != former.version or check_contributors(node, current._id):
                        problem_discrepancies.append(node)
    print('{} nodes whose last guid on wiki_pages_versions does not match the guid on wiki_pages_current'.format(len(discrepancies)))
    print('{}/{} nodes flagged as problematic'.format(len(problem_discrepancies), len(discrepancies)))
    print('{}/{} nodes are registrations or forks'.format(reg_fork_count, len(discrepancies)))
    print(problem_discrepancies)

def node_with_wikis_that_are_registrations_or_forks():
    reg_or_fork = []
    for node in AbstractNode.objects.exclude(wiki_pages_versions={}):
        if node.is_registration or node.is_fork:
            reg_or_fork.append(node)
    return reg_or_fork

def check_which_node_wiki_pages_have_name_discrepancies():
    # This would just be an issue when trying to restore NodeWikiPages post-migration, which no longer have guids.
    # For every new WikiPage, try fetch to NodeWikiPages with same page_name and node.  If NodeWikiPage was prior to rename, is difficult to rematch
    discrepancies = []
    for node in nodes_with_wikis():
        for key, versions in node.wiki_pages_versions.iteritems():
            for version in versions:
                nwp = NodeWikiPage.load(version)
                if to_mongo_key(nwp.page_name) != key:
                    discrepancies.append(node)
    print(len(discrepancies))
    print(discrepancies)

def check_wiki_pages_versions_equals_page_name():
    """
    Checks to see if the latest version in wiki_pages_version matches the page_name.
    """

    discrepancies = []
    for node in nodes_with_wikis():
        for key, versions in node.wiki_pages_versions.iteritems():
            nwp = NodeWikiPage.load(versions[-1])
            if to_mongo_key(nwp.page_name) != key:
                discrepancies.append(node)
    print(len(discrepancies))
    print(discrepancies)

def check_wiki_pages_current_equals_page_name():
    """
    Checks to see if the latest version in wiki_pages_version matches the page_name.
    """

    discrepancies = []
    for node in nodes_with_wikis():
        for key, version in node.wiki_pages_current.iteritems():
            nwp = NodeWikiPage.load(version)
            if to_mongo_key(nwp.page_name) != key:
                discrepancies.append(node)
    print(len(discrepancies))
    print(discrepancies)

def main():
    count_expected_wiki_pages()
    count_expected_wiki_versions()
    count_nodes_with_wikis()
    count_comments_to_be_repointed()
    check_that_last_wiki_version_is_also_current()
    check_that_last_wiki_version_is_also_current()
    check_which_node_wiki_pages_have_name_discrepancies()
    check_wiki_pages_versions_equals_page_name()
    check_wiki_pages_current_equals_page_name()
    sys.exit(0)

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
