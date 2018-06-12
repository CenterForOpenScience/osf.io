# -*- coding: utf-8 -*-
import sys
import logging
from website.app import setup_django
from scripts import utils as script_utils

setup_django()
from django.db import connection
from osf.models import AbstractNode, Guid, Comment
from addons.wiki.models import NodeWikiPage, WikiPage, WikiVersion
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def determine_comments_that_should_be_repointed():
    """
    RUN PRE-MIGRATION
    """
    logger.debug('Counting Comment records that will be updated...')
    with connection.cursor() as cursor:
        cursor.execute('''
        -- Flatten all nodes' wiki_pages_versions
        CREATE OR REPLACE TEMPORARY VIEW wiki_page_version_guids AS (
            SELECT
                trim(nwp_guid::text, '"') as _id
            FROM osf_abstractnode as oan,
                jsonb_each(oan.wiki_pages_versions) as wiki_pages_versions,
                jsonb_array_elements(wiki_pages_versions->wiki_pages_versions.key) as nwp_guid
        );

        ''')

        cursor.execute('''
        -- Count comments whose root_target points to a GUID in wiki_pages_versions
        SELECT
        COUNT(*)
        FROM osf_comment
        INNER JOIN osf_guid ON (osf_comment.root_target_id = osf_guid.id)
        WHERE osf_guid._id IN (SELECT _id from wiki_page_version_guids);
        ''')
        comments_root_target_count = cursor.fetchone()[0]
        logger.info("Comments with root targets as NWP that should be repointed: {}".format(comments_root_target_count))

        cursor.execute('''
        -- Count comments whose root_target points to a GUID in wiki_pages_versions
        SELECT
        COUNT(*)
        FROM osf_comment
        INNER JOIN osf_guid ON (osf_comment.target_id = osf_guid.id)
        WHERE osf_guid._id IN (SELECT _id from wiki_page_version_guids);
        ''')
        comments_target_count = cursor.fetchone()[0]
        logger.info("Comments with NWP targets that should be repointed: {}".format(comments_target_count))

    return comments_root_target_count, comments_target_count


def count_node_wiki_pages():
    """
    RUN POST-MIGRATION.
    Assert that counts for WikiPages, WikiVersions, WikiPage guids are correct.
    Also check that NodeWikiPage guids with an _id of None is correct (should have been repointed to WikiPages)
    """
    logger.debug('Counting WikiPages, WikiVersions, and WikiPage GUIDS...')
    wiki_pages_versions = AbstractNode.objects.exclude(wiki_pages_versions={}).values_list('wiki_pages_versions', flat=True)
    wp_content_type_id = ContentType.objects.get_for_model(WikiPage).id
    wiki_key_count = 0
    expected_wiki_ids = []
    for wpv in wiki_pages_versions:
        for wiki_key, version_list in wpv.iteritems():
            # expected_wiki_ids.append(wiki_key)
            # Skip bad data: wiki pages that have no versions
            if version_list:
                expected_wiki_ids.extend(version_list)
                wiki_key_count += 1
    wiki_values_count = len(expected_wiki_ids)
    # There will be dupes for nodes that don't have the wiki addon (55 on production).
    # When nodes without the wiki addon are registered, their wiki_pages_versions
    # field gets copied as is.
    wiki_values_count_without_dupes = len(set(expected_wiki_ids))
    wiki_page_count = WikiPage.objects.count()
    assert wiki_key_count == wiki_page_count, (
        'WikiPage count mismatch: # keys in Node.wiki_pages_versions: {}, WikiPage.objects.count(): {}, Difference: {}'.format(
            wiki_key_count,
            wiki_page_count,
            wiki_key_count - wiki_page_count)
    )
    wiki_version_count = WikiVersion.objects.count()
    assert wiki_values_count == wiki_version_count, (
        'WikiVersion count mismatch: # items in Node.wiki_pages_versions.values(): {}, WikiVersion.objects.count(): {}, Difference: {}'.format(
            wiki_values_count,
            wiki_version_count,
            wiki_values_count - wiki_version_count)
    )
    guid_count = Guid.objects.filter(content_type_id=wp_content_type_id).count()
    expected_guid_count = wiki_key_count + wiki_values_count_without_dupes
    assert expected_guid_count == guid_count, (
        'Guid count mismatch: {}, {}, Difference: {}'.format(
            expected_guid_count, guid_count, expected_guid_count - guid_count
        )
    )
    # NodeWikiPages whose Guid was repointed to a WikiPage
    node_wiki_page_count = NodeWikiPage.objects.filter(guids___id=None, uids___id__isnull=False).count()
    assert wiki_values_count_without_dupes == node_wiki_page_count, (
        'NodeWikiPage count mismatch: # items in Node.wiki_pages_versions: {}, NodeWikiPage.objects.count(): {}, Difference: {}'.format(
            wiki_values_count_without_dupes,
            node_wiki_page_count,
            wiki_values_count_without_dupes - node_wiki_page_count
        )
    )
    logger.info('SUCCESS! WikiPage, WikiVersion, WikiPage GUI and NodeWikiPage counts matched!')

def verify_comments_were_repointed_to_wps():
    """
    RUN POST-MIGRATION
    """
    logger.debug('Counting comments...')
    wp_content_type_id = ContentType.objects.get_for_model(WikiPage).id
    logger.info("Comments with WikiPage root_targets: {}".format(Comment.objects.filter(root_target__content_type_id=wp_content_type_id).count()))
    logger.info("Comments with WikiPage targets: {}".format(Comment.objects.filter(target__content_type_id=wp_content_type_id).count()))
    logger.info('Check the above values against the pre-migration values.')

def main(dry=True):
    pre_migration = '--pre' in sys.argv
    if pre_migration:
        determine_comments_that_should_be_repointed()
    else:
        count_node_wiki_pages()
        verify_comments_were_repointed_to_wps()

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
