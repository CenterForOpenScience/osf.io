from datetime import datetime
import pytz
import logging
from django.apps import apps
from website.app import init_app
from scripts import utils as script_utils
import sys
from django.db import transaction, IntegrityError
from website.util.metrics import OsfSourceTags, OsfClaimedTags, CampaignSourceTags, CampaignClaimedTags, provider_source_tag, provider_claimed_tag

logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

PROVIDER_SOURCE_TAGS = [
    ('africarxiv_preprints', provider_source_tag('africarxiv', 'preprint')),
    ('agrixiv_preprints', provider_source_tag('agrixiv', 'preprint')),
    ('arabixiv_preprints', provider_source_tag('arabixiv', 'preprint')),
    ('bitss_preprints', provider_source_tag('bitss', 'preprint')),
    ('eartharxiv_preprints', provider_source_tag('eartharxiv', 'preprint')),
    ('ecoevorxiv_preprints', provider_source_tag('ecoevorxiv', 'preprint')),
    ('ecsarxiv_preprints', provider_source_tag('ecsarxiv', 'preprint')),
    ('engrxiv_preprints', provider_source_tag('engrxiv', 'preprint')),
    ('focusarchive_preprints', provider_source_tag('focusarchive', 'preprint')),
    ('frenxiv_preprints', provider_source_tag('frenxiv', 'preprint')),
    ('inarxiv_preprints', provider_source_tag('inarxiv', 'preprint')),
    ('lawarxiv_preprints', provider_source_tag('lawarxiv', 'preprint')),
    ('lissa_preprints', provider_source_tag('lissa', 'preprint')),
    ('marxiv_preprints', provider_source_tag('marxiv', 'preprint')),
    ('mediarxiv_preprints', provider_source_tag('mediarxiv', 'preprint')),
    ('mindrxiv_preprints', provider_source_tag('mindrxiv', 'preprint')),
    ('nutrixiv_preprints', provider_source_tag('nutrixiv', 'preprint')),
    ('osf_preprints', provider_source_tag('osf', 'preprint')),
    ('paleorxiv_preprints', provider_source_tag('paleorxiv', 'preprint')),
    ('psyarxiv_preprints', provider_source_tag('psyarxiv', 'preprint')),
    ('socarxiv_preprints', provider_source_tag('socarxiv', 'preprint')),
    ('sportrxiv_preprints', provider_source_tag('sportrxiv', 'preprint')),
    ('thesiscommons_preprints', provider_source_tag('thesiscommons', 'preprint')),
    ('bodoarxiv_preprints', provider_source_tag('bodoarxiv', 'preprint')),
    ('indiarxiv_preprints', provider_source_tag('indiarxiv', 'preprint')),
    ('osf_registries', provider_source_tag('osf', 'registry')),
]

CAMPAIGN_SOURCE_TAGS = [
    ('erp_challenge_campaign', CampaignSourceTags.ErpChallenge.value),
    ('prereg_challenge_campaign', CampaignSourceTags.PreregChallenge.value),
    ('osf_registered_reports', CampaignSourceTags.OsfRegisteredReports.value),
    ('osf4m', CampaignSourceTags.Osf4m.value),
]

PROVIDER_CLAIMED_TAGS = [
    provider_claimed_tag('africarxiv', 'preprint'),
    provider_claimed_tag('agrixiv', 'preprint'),
    provider_claimed_tag('arabixiv', 'preprint'),
    provider_claimed_tag('bitss', 'preprint'),
    provider_claimed_tag('eartharxiv', 'preprint'),
    provider_claimed_tag('ecoevorxiv', 'preprint'),
    provider_claimed_tag('ecsarxiv', 'preprint'),
    provider_claimed_tag('engrxiv', 'preprint'),
    provider_claimed_tag('focusarchive', 'preprint'),
    provider_claimed_tag('frenxiv', 'preprint'),
    provider_claimed_tag('inarxiv', 'preprint'),
    provider_claimed_tag('lawarxiv', 'preprint'),
    provider_claimed_tag('lissa', 'preprint'),
    provider_claimed_tag('marxiv', 'preprint'),
    provider_claimed_tag('mediarxiv', 'preprint'),
    provider_claimed_tag('mindrxiv', 'preprint'),
    provider_claimed_tag('nutrixiv', 'preprint'),
    provider_claimed_tag('osf', 'preprint'),
    provider_claimed_tag('paleorxiv', 'preprint'),
    provider_claimed_tag('psyarxiv', 'preprint'),
    provider_claimed_tag('socarxiv', 'preprint'),
    provider_claimed_tag('sportrxiv', 'preprint'),
    provider_claimed_tag('thesiscommons', 'preprint'),
    provider_claimed_tag('bodoarxiv', 'preprint'),
    provider_claimed_tag('indiarxiv', 'preprint'),
    provider_claimed_tag('osf', 'registry'),
]

CAMPAIGN_CLAIMED_TAGS = [
    CampaignClaimedTags.ErpChallenge.value,
    CampaignClaimedTags.PreregChallenge.value,
    CampaignClaimedTags.Prereg.value,
    CampaignClaimedTags.OsfRegisteredReports.value,
    CampaignClaimedTags.Osf4m.value,
]


def migrate_source_tags(tags):
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in tags:
        tag, created = Tag.all_tags.get_or_create(name=tag_name[0], system=True)
        if created:
            logger.info('Tag with name {} created'.format(tag_name[0]))
        tag.name = tag_name[1]
        try:
            with transaction.atomic():
                tag.save()
                logger.info(tag_name[0] + ' migrated to ' + tag_name[1])
        except IntegrityError:
            # If there is an IntegrityError, a tag with the new name already exists
            # Delete the old tag if it was created in this method
            if created:
                tag.delete()
            pass


def add_tags(tags):
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in tags:
        tag, created = Tag.all_tags.get_or_create(name=tag_name, system=True)
        if not created:
            logger.info('System tag {} already exists, skipping.'.format(tag_name))
        else:
            tag.save()
            logger.info('Added tag ' + tag.name)


def normalize_source_tags():
    """ Normailize source tags
    """
    migrate_source_tags(PROVIDER_SOURCE_TAGS)
    migrate_source_tags(CAMPAIGN_SOURCE_TAGS)


def add_claimed_tags():
    """ Add claimed tags
    """
    add_tags(PROVIDER_CLAIMED_TAGS)
    add_tags(CAMPAIGN_CLAIMED_TAGS)


def add_osf_provider_tags():
    """ Add 'source:provider|osf' tag instance.
        Add 'claimed:provider|osf' tag instance.
    """
    Tag = apps.get_model('osf', 'Tag')
    Tag.all_tags.get_or_create(name=OsfSourceTags.Osf.value, system=True)
    Tag.all_tags.get_or_create(name=OsfClaimedTags.Osf.value, system=True)
    logger.info('Added tag ' + OsfSourceTags.Osf.value)
    logger.info('Added tag ' + OsfClaimedTags.Osf.value)


def add_prereg_campaign_tags():
    """ Add 'source:campaign|prereg' tag instance.
        Add 'claimed:campaign|prereg' tag instance.
        Migrate all users created after prereg challenge end date to the new source tag.
    """
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFuser')

    try:
        # Try to get prereg challenge source tag
        prereg_challenge_source_tag = Tag.all_tags.get(name=CampaignSourceTags.PreregChallenge.value, system=True)
    except Tag.DoesNotExist:
        # If prereg challenge source tag doesn't exist, create the prereg source tag and we are done.
        prereg_source_tag, created = Tag.all_tags.get_or_create(name=CampaignSourceTags.Prereg.value, system=True)
        logger.info('Added tag ' + prereg_source_tag.name)
    else:
        # Otherwise, we create the prereg source tag, and then migrate the users.
        prereg_source_tag, created = Tag.all_tags.get_or_create(name=CampaignSourceTags.Prereg.value, system=True)
        logger.info('Added tag ' + prereg_source_tag.name)
        prereg_challenge_cutoff_date = pytz.utc.localize(datetime(2019, 1, 1, 5, 59))
        prereg_users_registered_after_january_first = OSFUser.objects.filter(tags__id=prereg_challenge_source_tag.id,
                                                                             date_registered__gt=prereg_challenge_cutoff_date)
        logger.info(
            'Number of OSFUsers created on/after 2019-01-01: ' + str(len(prereg_users_registered_after_january_first)))
        for user in prereg_users_registered_after_january_first:
            user.tags.through.objects.filter(tag=prereg_challenge_source_tag, osfuser=user).delete()
            user.add_system_tag(prereg_source_tag)
            # Check  whether the user is merged to another user
            # If so, add the same tag to that user as well
            if user.merged_by is not None:
                user.merged_by.add_system_tag(prereg_source_tag)
        logger.info('Migrated users from ' + prereg_challenge_source_tag.name + ' to ' + prereg_source_tag.name)


def main():
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    with transaction.atomic():
        normalize_source_tags()
        add_claimed_tags()
        add_osf_provider_tags()
        add_prereg_campaign_tags()
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back')


if __name__ == '__main__':
    main()
