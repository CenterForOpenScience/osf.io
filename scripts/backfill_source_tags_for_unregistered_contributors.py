from datetime import timedelta
import logging
from django.apps import apps
from website.app import init_app
from scripts import utils as script_utils
import datetime
import progressbar
from django.core.paginator import Paginator

import sys

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def backfill_source_tags_for_osf4m_unregistered_contributors(dry_run):
    """ Backfill osf4m source tags to all osf4m unregistered contributors
    """
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    NodeLog = apps.get_model('osf', 'NodeLog')
    meeting_source_tag = Tag.all_tags.get(name='source:campaign|osf4m', system=True)
    meeting_nodes = meeting_source_tag.abstractnode_tagged.all()
    logging.info('Number of meeting nodes found: ' + str(len(meeting_nodes)))
    all_meeting_node_logs = NodeLog.objects.filter(action='contributor_added', node__in=meeting_nodes).only('created', 'params')
    ThroughModel = OSFUser.tags.through
    set_of_user_ids = set()
    pbar = progressbar.ProgressBar(maxval=len(all_meeting_node_logs) or 1).start()
    pbarcounter = 0
    for entry in all_meeting_node_logs:
        pbarcounter += 1
        entry_created_date = entry.created
        for contributor_id in entry.params['contributors']:
            contributor_added = OSFUser.objects.get(guids___id=contributor_id)
            if contributor_added.is_invited and contributor_added.date_confirmed and contributor_added.date_confirmed > entry_created_date:
                set_of_user_ids.add(contributor_added.pk)
                # If the user is merged to another user, add the same tag to that user as well
                if contributor_added.merged_by is not None:
                    set_of_user_ids.add(contributor_added.merged_by.pk)
        pbar.update(pbarcounter)
    logging.info('Number of meeting nodes unreg contrib found: ' + str(len(set_of_user_ids)))
    if not dry_run:
        list_of_user_ids_already_with_osf4m_source_tag = OSFUser.objects.filter(tags__id=meeting_source_tag.id).values_list('pk', flat=True)
        for id in list_of_user_ids_already_with_osf4m_source_tag:
            set_of_user_ids.discard(id)
        ThroughModel.objects.bulk_create([ThroughModel(tag_id=meeting_source_tag.pk, osfuser_id=user_id) for user_id in set_of_user_ids])


def backfill_source_tags_for_nodes_and_preprints_unregistered_contributors(dry_run):
    """ Backfill preprint provider source tags to all preprint unregistered contributors
    """
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    PreprintProvider = apps.get_model('osf', 'PreprintProvider')
    PreprintLog = apps.get_model('osf', 'PreprintLog')
    all_providers = PreprintProvider.objects.all()
    ThroughModel = OSFUser.tags.through
    # Add tags to unregistered contributors
    # Two cases: pre-NPD and post-NPD
    for provider in all_providers:
        provider_source_tag, created = Tag.all_tags.get_or_create(name='source:provider|preprint|{}'.format(provider._id), system=True)
        osf_provider_source_tag = Tag.all_tags.get(name='source:provider|osf', system=True)
        # For post-NPD preprints
        set_of_user_ids_post_npd = set()
        all_provider_preprints_post_npd = provider.preprints.filter(migrated__isnull=True)
        preprint_logs = PreprintLog.objects.filter(action='contributor_added', preprint__in=all_provider_preprints_post_npd)
        logging.info('Number of post-NPD preprints for {}: {}'.format(provider._id, str(len(all_provider_preprints_post_npd))))
        pbar = progressbar.ProgressBar(maxval=len(preprint_logs) or 1).start()
        pbarcounter = 0
        for entry in preprint_logs:
            pbarcounter += 1
            entry_created_date = entry.created
            for contributor_id in entry.params['contributors']:
                contributor_added = OSFUser.load(contributor_id)
                if contributor_added.is_invited and contributor_added.date_confirmed and contributor_added.date_confirmed > entry_created_date:
                    set_of_user_ids_post_npd.add(contributor_added.pk)
                    # If the user is merged to another user, add the same tag to that user as well
                    if contributor_added.merged_by is not None:
                        set_of_user_ids_post_npd.add(contributor_added.merged_by.pk)
            pbar.update(pbarcounter)
        logging.info('Number of post-NPD unreg contrib for {}: {}'.format(provider._id, str(len(set_of_user_ids_post_npd))))
        if not dry_run:
            list_of_user_ids_already_with_provider_source_tag = OSFUser.objects.filter(tags__id=provider_source_tag.id).values_list('pk', flat=True)
            for id in list_of_user_ids_already_with_provider_source_tag:
                set_of_user_ids_post_npd.discard(id)
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=provider_source_tag.pk, osfuser_id=user_id) for user_id in set_of_user_ids_post_npd])

        # For pre-NPD preprints
        set_of_user_ids_pre_npd_provider_tag= set()
        set_of_user_ids_pre_npd_osf_tag = set()
        all_provider_preprints_pre_npd = provider.preprints.filter(migrated__isnull=False, node__isnull=False).select_related('node').only('created', 'node')
        logging.info('Number of pre-NPD preprints with sup nodes for {}: {}'.format(provider._id, str(len(all_provider_preprints_pre_npd))))
        pbar = progressbar.ProgressBar(maxval=len(all_provider_preprints_pre_npd) or 1).start()
        pbarcounter = 0
        for preprint in all_provider_preprints_pre_npd:
            pbarcounter += 1
            if preprint.created < preprint.node.created:
                # Do nothing
                pass
            elif preprint.created - preprint.node.created < timedelta(minutes=10):
                node_logs = preprint.node.logs.filter(action='contributor_added').only('created', 'params')
                for entry in node_logs:
                    entry_created_date = entry.created
                    for contributor_id in entry.params['contributors']:
                        try:
                            contributor_added = OSFUser.load(contributor_id)
                        except:
                            logging.info('Legacy log entry found and ignored.')
                        if contributor_added.is_invited and contributor_added.date_confirmed and contributor_added.date_confirmed > entry_created_date:
                            set_of_user_ids_pre_npd_provider_tag.add(contributor_added.pk)
                            # If the user is merged to another user, add the same tag to that user as well
                            if contributor_added.merged_by is not None:
                                set_of_user_ids_pre_npd_provider_tag.add(contributor_added.merged_by.pk)
            elif preprint.created - preprint.node.created > timedelta(days=1):
                node_logs = preprint.node.logs.filter(action='contributor_added').only('created', 'params')
                for entry in node_logs:
                    entry_created_date = entry.created
                    for contributor_id in entry.params['contributors']:
                        try:
                            contributor_added = OSFUser.load(contributor_id)
                        except:
                            logging.info('Legacy log entry found and ignored.')
                        if contributor_added.is_invited and contributor_added.date_confirmed and contributor_added.date_confirmed > entry_created_date:
                            set_of_user_ids_pre_npd_osf_tag.add(contributor_added.pk)
                            # If the user is merged to another user, add the same tag to that user as well
                            if contributor_added.merged_by is not None:
                                set_of_user_ids_pre_npd_osf_tag.add(contributor_added.merged_by.pk)
            pbar.update(pbarcounter)
        logging.info('Number of pre-NPD unreg contrib for {}: {}'.format(provider._id, str(len(set_of_user_ids_pre_npd_provider_tag) + len(set_of_user_ids_pre_npd_osf_tag))))
        if not dry_run:
            list_of_user_ids_already_with_provider_source_tag = OSFUser.objects.filter(tags__id=provider_source_tag.id).values_list('pk', flat=True)
            list_of_user_ids_already_with_osf_source_tag = OSFUser.objects.filter(tags__id=osf_provider_source_tag.id).values_list('pk', flat=True)
            for id in list_of_user_ids_already_with_provider_source_tag:
                set_of_user_ids_pre_npd_provider_tag.discard(id)
            for id in list_of_user_ids_already_with_osf_source_tag:
                set_of_user_ids_pre_npd_osf_tag.discard(id)
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=provider_source_tag.pk, osfuser_id=user_id) for user_id in set_of_user_ids_pre_npd_provider_tag])
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=osf_provider_source_tag.pk, osfuser_id=user_id) for user_id in set_of_user_ids_pre_npd_osf_tag])


def backfill_osf_provider_tags_to_users_not_invited_but_have_no_source_tags(dry_run):
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    ThroughModel = OSFUser.tags.through
    osf_provider_source_tag = Tag.all_tags.get(name='source:provider|osf', system=True)
    source_tag_ids = Tag.all_tags.filter(name__icontains='source:', system=True).values_list('id', flat=True)
    # Find not invited users with no source tags
    users_with_no_source_tags = OSFUser.objects.exclude(is_invited=True).exclude(tags__id__in=source_tag_ids).only('tags').order_by('id')
    logging.info('Number of users with no source tag {}'.format(str(len(users_with_no_source_tags))))

    paginated_users = Paginator(users_with_no_source_tags, 1000)
    pbar = progressbar.ProgressBar(maxval=paginated_users.num_pages).start()
    pbarcounter = 0
    for page_num in paginated_users.page_range:
        pbarcounter += 1
        through_models_to_create = []
        for user in paginated_users.page(page_num).object_list:
            through_models_to_create.append(ThroughModel(tag_id=osf_provider_source_tag.pk, osfuser_id=user.pk))
        if not dry_run:
            ThroughModel.objects.bulk_create(through_models_to_create)
        pbar.update(pbarcounter)


def main():
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    script_start_time = datetime.datetime.now()
    logging.info('Script started time: ' + str(script_start_time))
    backfill_source_tags_for_osf4m_unregistered_contributors(dry_run)
    backfill_source_tags_for_nodes_and_preprints_unregistered_contributors(dry_run)
    backfill_osf_provider_tags_to_users_not_invited_but_have_no_source_tags(dry_run)
    script_finish_time = datetime.datetime.now()
    logging.info('Script finished time: ' + str(script_finish_time))
    logging.info('Run time ' + str(script_finish_time - script_start_time))


if __name__ == '__main__':
    main()