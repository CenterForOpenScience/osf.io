from datetime import datetime
import pytz
import logging
from django.apps import apps
from website.app import init_app
from scripts import utils as script_utils
import sys
from django.db import transaction
from website.util.metrics import ProviderSourceTags, ProviderClaimedTags, CampaignSourceTags, CampaignClaimedTags

logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

PROVIDER_SOURCE_TAGS = [
    ('africarxiv_preprints', ProviderSourceTags.AfricarxivPreprints.value),
    ('agrixiv_preprints', ProviderSourceTags.AgrixivPreprints.value),
    ('arabixiv_preprints', ProviderSourceTags.ArabixivPreprints.value),
    ('bitss_preprints', ProviderSourceTags.MetaarxivPreprints.value),
    ('eartharxiv_preprints', ProviderSourceTags.EartharxivPreprints.value),
    ('ecoevorxiv_preprints', ProviderSourceTags.EcoevorxivPreprints.value),
    ('ecsarxiv_preprints', ProviderSourceTags.EcsarxivPreprints.value),
    ('engrxiv_preprints', ProviderSourceTags.EngrxivPreprints.value),
    ('focusarchive_preprints', ProviderSourceTags.FocusarchivePreprints.value),
    ('frenxiv_preprints', ProviderSourceTags.FrenxivPreprints.value),
    ('inarxiv_preprints', ProviderSourceTags.InarxivPreprints.value),
    ('lawarxiv_preprints', ProviderSourceTags.LawarxivPreprints.value),
    ('lissa_preprints', ProviderSourceTags.LissaPreprints.value),
    ('marxiv_preprints', ProviderSourceTags.MarxivPreprints.value),
    ('mediarxiv_preprints', ProviderSourceTags.MediarxivPreprints.value),
    ('mindrxiv_preprints', ProviderSourceTags.MindrxivPreprints.value),
    ('nutrixiv_preprints', ProviderSourceTags.NutrixivPreprints.value),
    ('osf_preprints', ProviderSourceTags.OsfPreprints.value),
    ('paleorxiv_preprints', ProviderSourceTags.PaleorxivPreprints.value),
    ('psyarxiv_preprints', ProviderSourceTags.PsyarxivPreprints.value),
    ('socarxiv_preprints', ProviderSourceTags.SocarxivPreprints.value),
    ('sportrxiv_preprints', ProviderSourceTags.SportrxivPreprints.value),
    ('thesiscommons_preprints', ProviderSourceTags.ThesiscommonsPreprints.value),
    ('bodoarxiv_preprints', ProviderSourceTags.BodoarxivPreprints.value),
    ('osf_registries', ProviderSourceTags.OsfRegistries.value),
]

CAMPAIGN_SOURCE_TAGS = [
    ('erp_challenge_campaign', CampaignSourceTags.ErpChallenge.value),
    ('prereg_challenge_campaign', CampaignSourceTags.PreregChallenge.value),
    ('osf_registered_reports', CampaignSourceTags.OsfRegisteredReports.value),
    ('osf4m', CampaignSourceTags.Osf4m.value),
]

PROVIDER_CLAIMED_TAGS = [
    ProviderClaimedTags.AfricarxivPreprints.value,
    ProviderClaimedTags.AgrixivPreprints.value,
    ProviderClaimedTags.ArabixivPreprints.value,
    ProviderClaimedTags.MetaarxivPreprints.value,
    ProviderClaimedTags.EartharxivPreprints.value,
    ProviderClaimedTags.EcoevorxivPreprints.value,
    ProviderClaimedTags.EcsarxivPreprints.value,
    ProviderClaimedTags.EngrxivPreprints.value,
    ProviderClaimedTags.FocusarchivePreprints.value,
    ProviderClaimedTags.FrenxivPreprints.value,
    ProviderClaimedTags.InarxivPreprints.value,
    ProviderClaimedTags.LawarxivPreprints.value,
    ProviderClaimedTags.LissaPreprints.value,
    ProviderClaimedTags.MarxivPreprints.value,
    ProviderClaimedTags.MediarxivPreprints.value,
    ProviderClaimedTags.MindrxivPreprints.value,
    ProviderClaimedTags.NutrixivPreprints.value,
    ProviderClaimedTags.OsfPreprints.value,
    ProviderClaimedTags.PaleorxivPreprints.value,
    ProviderClaimedTags.PsyarxivPreprints.value,
    ProviderClaimedTags.SocarxivPreprints.value,
    ProviderClaimedTags.SportrxivPreprints.value,
    ProviderClaimedTags.ThesiscommonsPreprints.value,
    ProviderClaimedTags.BodoarxivPreprints.value,
    ProviderClaimedTags.OsfRegistries.value,
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
        tag.save()
        logger.info(tag_name[0] + ' migrated to ' + tag_name[1])


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
    Tag.all_tags.get_or_create(name=ProviderSourceTags.Osf.value, system=True)
    Tag.all_tags.get_or_create(name=ProviderClaimedTags.Osf.value, system=True)
    logger.info('Added tag ' + ProviderSourceTags.Osf.value)
    logger.info('Added tag ' + ProviderClaimedTags.Osf.value)


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
        prereg_challenge_cutoff_date = pytz.utc.localize(datetime(2019, 01, 01, 05, 59))
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
