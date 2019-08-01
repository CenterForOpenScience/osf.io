import logging
import sys

from datetime import timedelta
from django.apps import apps
from website.app import init_app
from website.util.metrics import CampaignSourceTags, provider_source_tag, OsfSourceTags
from scripts import utils as script_utils
import datetime
from django.core.paginator import Paginator
from django.db.models import F
from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def _get_set_of_user_ids_from_logs(node_logs):
    OSFUser = apps.get_model('osf', 'OSFUser')
    set_of_user_ids = set()
    with tqdm(total=node_logs.count()) as pbar:
        for entry in node_logs:
            entry_created_date = entry.created
            for contributor_id in entry.params['contributors']:
                try:
                    contributor_added = OSFUser.objects.filter(guids___id=contributor_id).only('is_invited', 'date_confirmed', 'merged_by')[0]
                except:
                    logger.info('Legacy log entry found and ignored.')
                if contributor_added.is_invited and contributor_added.date_confirmed and contributor_added.date_confirmed > entry_created_date:
                    set_of_user_ids.add(contributor_added.pk)
                    # If the user is merged to another user, add the same tag to that user as well
                    if contributor_added.merged_by is not None:
                        set_of_user_ids.add(contributor_added.merged_by.pk)
            pbar.update()
    return set_of_user_ids


def backfill_source_tags_for_osf4m_unregistered_contributors(dry_run):
    """ Backfill osf4m source tags to all osf4m unregistered contributors
    """
    # Define the models
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    NodeLog = apps.get_model('osf', 'NodeLog')
    ThroughModel = OSFUser.tags.through

    # Get the appropriate tag instance for backfilling
    meeting_source_tag = Tag.all_tags.get(name=CampaignSourceTags.Osf4m.value, system=True)

    # Find ids of all meeting nodes
    meeting_nodes_id = meeting_source_tag.abstractnode_tagged.all().values_list('id', flat=True)
    logger.info('Number of meeting nodes found: {}'.format(meeting_nodes_id.count()))

    # Find id of all log entries of these meeting nodes
    all_meeting_node_logs = NodeLog.objects.filter(action='contributor_added', node__id__in=meeting_nodes_id).only('created', 'params')

    # Find id of all contributors that meets requirements
    logger.info('Finding all OSF4M unreg contributors')
    logger.debug(datetime.datetime.now())
    set_of_user_ids = _get_set_of_user_ids_from_logs(all_meeting_node_logs)
    logger.info('Number of meeting nodes unreg contrib found: ' + str(len(set_of_user_ids)))

    if not dry_run:
        set_of_user_ids_already_with_osf4m_source_tag = set(OSFUser.objects.filter(tags__id=meeting_source_tag.id).values_list('pk', flat=True))
        set_bulk_create = set_of_user_ids.difference(set_of_user_ids_already_with_osf4m_source_tag)
        ThroughModel.objects.bulk_create([ThroughModel(tag_id=meeting_source_tag.pk, osfuser_id=user_id) for user_id in set_bulk_create])
        for id in set_bulk_create:
            logger.info('User with id {} gets osf4m source tags'.format(id))


def backfill_source_tags_for_nodes_and_preprints_unregistered_contributors(dry_run):
    """ Backfill preprint provider source tags to all preprint unregistered contributors
    """
    # Define the models
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    PreprintProvider = apps.get_model('osf', 'PreprintProvider')
    PreprintLog = apps.get_model('osf', 'PreprintLog')
    NodeLog = apps.get_model('osf', 'NodeLog')
    ThroughModel = OSFUser.tags.through

    # Add tags to unregistered contributors
    # Two cases: pre-NPD and post-NPD
    all_providers = PreprintProvider.objects.all()
    for provider in all_providers:
        source_tag, created = Tag.all_tags.get_or_create(name=provider_source_tag(provider._id, 'preprint'), system=True)
        osf_provider_source_tag = Tag.all_tags.get(name=provider_source_tag('osf'), system=True)

        # For post-NPD preprints
        logger.info('Finding post-NPD preprints for {}'.format(provider._id))
        all_provider_preprints_post_npd_id = provider.preprints.filter(migrated__isnull=True).values_list('id')
        logger.info('Number of post-NPD preprints for {}: {}'.format(provider._id, all_provider_preprints_post_npd_id.count()))
        preprint_logs = PreprintLog.objects.filter(action='contributor_added', preprint__id__in=all_provider_preprints_post_npd_id).only('created', 'params')
        logger.info('Finding post-NPD unreg contrib for {}'.format(provider._id))
        set_of_user_ids_post_npd = _get_set_of_user_ids_from_logs(preprint_logs)
        logger.info('Number of post-NPD unreg contrib for {}: {}'.format(provider._id, str(len(set_of_user_ids_post_npd))))
        if not dry_run:
            set_of_user_ids_already_with_provider_source_tag = set(OSFUser.objects.filter(tags__id=source_tag.id).values_list('pk', flat=True))
            set_bulk_create = set_of_user_ids_post_npd.difference(set_of_user_ids_already_with_provider_source_tag)
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=source_tag.pk, osfuser_id=user_id) for user_id in set_bulk_create])

        # For pre-NPD preprints
        logger.info('Finding pre-NPD preprints within then minutes for {}'.format(provider._id))
        node_ids_created_within_ten_minutes = provider.preprints.filter(migrated__isnull=False, node__isnull=False, created__lte=F('node__created')+timedelta(minutes=10)).values_list('node__id', flat=True)
        logger.info('Finding pre-NPD logs within then minutes for {}'.format(provider._id))
        node_logs_within_ten_minutes = NodeLog.objects.filter(action='contributor_added', node__id__in=node_ids_created_within_ten_minutes).only('created', 'params')

        logger.info('Finding pre-NPD preprints more than a day for {}'.format(provider._id))
        node_ids_created_more_than_a_day = provider.preprints.filter(migrated__isnull=False, node__isnull=False, created__gte=F('node__created')+timedelta(days=1)).values_list('node__id', flat=True)
        logger.info('Finding pre-NPD logs more than a day for {}'.format(provider._id))
        node_logs_more_than_a_day = NodeLog.objects.filter(action='contributor_added', node__id__in=node_ids_created_more_than_a_day).only('created', 'params')

        logger.info('Finding pre-NPD unreg contrib for {}'.format(provider._id))
        set_of_user_ids_pre_npd_provider_tag = _get_set_of_user_ids_from_logs(node_logs_within_ten_minutes)
        set_of_user_ids_pre_npd_osf_tag = _get_set_of_user_ids_from_logs(node_logs_more_than_a_day)
        logger.info('Number of pre-NPD unreg contrib for {}: {}'.format(provider._id, str(len(set_of_user_ids_pre_npd_provider_tag) + len(set_of_user_ids_pre_npd_osf_tag))))

        if not dry_run:
            set_of_user_ids_already_with_provider_source_tag = set(OSFUser.objects.filter(tags__id=source_tag.id).values_list('pk', flat=True))
            set_of_user_ids_already_with_osf_source_tag = set(OSFUser.objects.filter(tags__id=osf_provider_source_tag.id).values_list('pk', flat=True))
            set_bulk_create_provider_tag = set_of_user_ids_pre_npd_provider_tag.difference(set_of_user_ids_already_with_provider_source_tag)
            set_bulk_create_osf_tag = set_of_user_ids_pre_npd_osf_tag.difference(set_of_user_ids_already_with_osf_source_tag)
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=source_tag.pk, osfuser_id=user_id) for user_id in set_bulk_create_provider_tag])
            ThroughModel.objects.bulk_create([ThroughModel(tag_id=osf_provider_source_tag.pk, osfuser_id=user_id) for user_id in set_bulk_create_osf_tag])


def backfill_osf_provider_tags_to_users_not_invited_but_have_no_source_tags(dry_run):
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFUser')
    ThroughModel = OSFUser.tags.through
    osf_provider_source_tag = Tag.all_tags.get(name=OsfSourceTags.Osf.value, system=True)
    source_tag_ids = Tag.all_tags.filter(name__icontains='source:', system=True).values_list('id', flat=True)

    # Find not invited users with no source tags
    id_users_with_no_source_tags = OSFUser.objects.exclude(is_invited=True).exclude(tags__id__in=source_tag_ids).values_list('pk', flat=True).order_by('pk')
    logger.info('Number of users with no source tag {}'.format(id_users_with_no_source_tags.count()))

    # Backfill OSF source tags to these users
    logger.info('Backfilling OSF Source tags to uninvited users with no source tags')
    paginated_users = Paginator(id_users_with_no_source_tags, 1000)
    with tqdm(total=paginated_users.num_pages) as pbar:
        for page_num in paginated_users.page_range:
            through_models_to_create = []
            for id in paginated_users.page(page_num).object_list:
                through_models_to_create.append(ThroughModel(tag_id=osf_provider_source_tag.pk, osfuser_id=id))
            if not dry_run:
                ThroughModel.objects.bulk_create(through_models_to_create)
            pbar.update()


def main():
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    script_start_time = datetime.datetime.now()
    logger.info('Script started time: ' + str(script_start_time))
    backfill_source_tags_for_osf4m_unregistered_contributors(dry_run)
    backfill_source_tags_for_nodes_and_preprints_unregistered_contributors(dry_run)
    backfill_osf_provider_tags_to_users_not_invited_but_have_no_source_tags(dry_run)
    script_finish_time = datetime.datetime.now()
    logger.info('Script finished time: ' + str(script_finish_time))
    logger.info('Run time ' + str(script_finish_time - script_start_time))


if __name__ == '__main__':
    main()
