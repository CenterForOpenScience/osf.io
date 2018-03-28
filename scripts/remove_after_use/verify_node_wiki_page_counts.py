# -*- coding: utf-8 -*-
import sys
import logging
from website.app import setup_django, init_app
from scripts import utils as script_utils
from django.db import transaction

setup_django()
from django.db.models import Q
from osf.models import AbstractNode, Guid, Comment
from addons.wiki.models import NodeWikiPage, WikiPage, WikiVersion
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# Replace with output of determine_comments_viewed_timestamps_that_should_change
expected_values = []

def determine_comments_that_should_be_repointed():
    """
    RUN PRE-MIGRATION
    """
    comments_count_root_target = 0
    comments_count_target = 0
    for node in AbstractNode.objects.exclude(wiki_pages_versions={}):
        for key, version_list in node.wiki_pages_versions.iteritems():
            nwp_guid  = Guid.load(version_list[-1])
            comments_count_root_target += Comment.objects.filter(Q(root_target=nwp_guid)).count()
            comments_count_target += Comment.objects.filter(Q(target=nwp_guid)).count()
    print "Comments with root targets as NWP that should be repointed: {}".format(comments_count_root_target)
    print "Comments with NWP targets that should be repointed".format(comments_count_target)
    return comments_count_root_target, comments_count_target

def determine_comments_viewed_timestamps_that_should_change():
    """
    RUN AFTER CREATING WIKI PAGES AND WIKI VERSIONS BUT BEFORE MODIFYING comments_viewed_timestamps, if using
    Save results under expected_values.
    """
    pending_changes = []
    for node in AbstractNode.objects.exclude(wiki_pages_versions={}):
        for key, version_list in node.wiki_pages_versions.iteritems():
            nwp_guid  = version_list[-1]
            nwp_page_name = NodeWikiPage.objects.get(former_guid=nwp_guid).page_name
            wp_guid = node.wikis.get(page_name=nwp_page_name)._id
            for user in node.contributors.all():
                if nwp_guid in user.comments_viewed_timestamp:
                    pending_changes.append({"user_id": user.id, "nwp_guid": str(nwp_guid), "wp_guid": str(wp_guid), "timestamp": str(user.comments_viewed_timestamp.get(nwp_guid)), "cvt_length": len(user.comments_viewed_timestamp.keys())})
    print pending_changes
    return pending_changes

def count_node_wiki_pages():
    """
    RUN POST-MIGRATION.
    Assert that counts for WikiPages, WikiVersions, WikiPage guids are correct.
    Also check that NodeWikiPage guids with an _id of None is correct (should have been repointed to WikiPages)
    """
    nodes_with_wikis = AbstractNode.objects.exclude(wiki_pages_versions={}).exclude(type='osf.collection').exclude(type='osf.quickfilesnode')
    wp_content_type_id = ContentType.objects.get_for_model(WikiPage).id
    wiki_page_count = 0
    wiki_version_counts = 0
    for node in nodes_with_wikis:
        for wiki_key, version_list in node.wiki_pages_versions.iteritems():
            wiki_page_count += 1
            wiki_version_counts += len(version_list)
    assert wiki_page_count == WikiPage.objects.count()
    assert wiki_version_counts == WikiVersion.objects.count()
    assert wiki_page_count + wiki_version_counts == Guid.objects.filter(content_type_id=wp_content_type_id).count()
    assert wiki_version_counts == NodeWikiPage.objects.filter(guids___id=None).count()

def verify_comments_viewed_timestamp():
    """
    RUN POST MIGRATION.
    determine_comments_viewed_timestamps_that_should_change should have been run previously.
    """
    for user_dict in expected_values:
        u = OSFUser.objects.get(id=user_dict['user_id'])
        assert user_dict['nwp_guid'] not in u.comments_viewed_timestamp.keys()
        assert user_dict['wp_guid'] in u.comments_viewed_timestamp.keys()
        assert user_dict['timestamp'] == str(u.comments_viewed_timestamp[user_dict['wp_guid']])
        assert user_dict['cvt_length'] == len(u.comments_viewed_timestamp.keys())

def verify_comments_were_repointed_to_wps():
    """
    RUN POST-MIGRATION
    """
    wp_content_type_id = ContentType.objects.get_for_model(WikiPage).id
    print "Comments with WikiPage root_targets: {}".format(Comment.objects.filter(root_target__content_type_id=wp_content_type_id).count())
    print "Comments with WikiPage targets: {}".format(Comment.objects.filter(target__content_type_id=wp_content_type_id).count())

def main(dry=True):
    init_app(routes=False)
    count_node_wiki_pages()

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
