from datetime import datetime
import pytz
import logging
from django.apps import apps
from website.app import init_app
from scripts import utils as script_utils
import sys
from django.db import transaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


PROVIDER_SOURCE_TAGS = [
    ('africarxiv_preprints', 'source:provider|preprint|africarxiv'),
    ('agrixiv_preprints', 'source:provider|preprint|agrixiv'),
    ('arabixiv_preprints', 'source:provider|preprint|arabixiv'),
    ('bitss_preprints', 'source:provider|preprint|metaarxiv'),
    ('eartharxiv_preprints', 'source:provider|preprint|eartharxiv'),
    ('ecoevorxiv_preprints', 'source:provider|preprint|ecoevorxiv'),
    ('ecsarxiv_preprints', 'source:provider|preprint|ecsarxiv'),
    ('engrxiv_preprints', 'source:provider|preprint|engrxiv'),
    ('focusarchive_preprints', 'source:provider|preprint|focusarchive'),
    ('frenxiv_preprints', 'source:provider|preprint|frenxiv'),
    ('inarxiv_preprints', 'source:provider|preprint|inarxiv'),
    ('lawarxiv_preprints', 'source:provider|preprint|lawarxiv'),
    ('lissa_preprints', 'source:provider|preprint|lissa'),
    ('marxiv_preprints', 'source:provider|preprint|marxiv'),
    ('mediarxiv_preprints', 'source:provider|preprint|mediarxiv'),
    ('mindrxiv_preprints', 'source:provider|preprint|mindrxiv'),
    ('nutrixiv_preprints', 'source:provider|preprint|nutrixiv'),
    ('osf_preprints', 'source:provider|preprint|osf'),
    ('paleorxiv_preprints', 'source:provider|preprint|paleorxiv'),
    ('psyarxiv_preprints', 'source:provider|preprint|psyarxiv'),
    ('socarxiv_preprints', 'source:provider|preprint|socarxiv'),
    ('sportrxiv_preprints', 'source:provider|preprint|sportrxiv'),
    ('thesiscommons_preprints', 'source:provider|preprint|thesiscommons'),
    ('bodoarxiv_preprints', 'source:provider|preprint|bodoarxiv'),
    ('osf_registries', 'source:provider|registry|osf'),
]

CAMPAIGN_SOURCE_TAGS = [
    ('erp_challenge_campaign', 'source:campaign|erp'),
    ('prereg_challenge_campaign', 'source:campaign|prereg_challenge'),
    ('osf_registered_reports', 'source:campaign|osf_registered_reports'),
    ('osf4m', 'source:campaign|osf4m'),
]

PROVIDER_CLAIMED_TAGS = [
    'claimed:provider|preprint|africarxiv',
    'claimed:provider|preprint|agrixiv',
    'claimed:provider|preprint|arabixiv',
    'claimed:provider|preprint|metaarxiv',
    'claimed:provider|preprint|eartharxiv',
    'claimed:provider|preprint|ecoevorxiv',
    'claimed:provider|preprint|ecsarxiv',
    'claimed:provider|preprint|engrxiv',
    'claimed:provider|preprint|focusarchive',
    'claimed:provider|preprint|frenxiv',
    'claimed:provider|preprint|inarxiv',
    'claimed:provider|preprint|lawarxiv',
    'claimed:provider|preprint|lissa',
    'claimed:provider|preprint|marxiv',
    'claimed:provider|preprint|mediarxiv',
    'claimed:provider|preprint|mindrxiv',
    'claimed:provider|preprint|nutrixiv',
    'claimed:provider|preprint|osf',
    'claimed:provider|preprint|paleorxiv',
    'claimed:provider|preprint|psyarxiv',
    'claimed:provider|preprint|socarxiv',
    'claimed:provider|preprint|sportrxiv',
    'claimed:provider|preprint|thesiscommons',
    'claimed:provider|preprint|bodoarxiv',
    'claimed:provider|registry|osf',
]

CAMPAIGN_CLAIMED_TAGS = [
    'claimed:campaign|erp',
    'claimed:campaign|prereg_challenge',
    'claimed:campaign|prereg',
    'claimed:campaign|osf_registered_reports',
    'claimed:campaign|osf4m',
]


def normalize_provider_source_tags():
    """ Normailize provider source tags
    """
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in PROVIDER_SOURCE_TAGS:
        try:
            tag = Tag.all_tags.get(name=tag_name[0], system=True)
            tag.name = tag_name[1]
            tag.save()
            logging.info(tag_name[0] + ' migrated to ' + tag_name[1])
        except Tag.DoesNotExist:
            pass


def add_provider_claimed_tags():
    """ Add provider claimed tag instances
    """
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in PROVIDER_CLAIMED_TAGS:
        tag = Tag.all_tags.create(name=tag_name, system=True)
        tag.save()
        logging.info('Added tag ' + tag.name)


def normalize_campaign_source_tags():
    """ Normalize campaign source tags
    """
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in CAMPAIGN_SOURCE_TAGS:
        try:
            tag = Tag.all_tags.get(name=tag_name[0], system=True)
            tag.name = tag_name[1]
            tag.save()
            logging.info(tag_name[0] + ' migrated to ' + tag_name[1])
        except Tag.DoesNotExist:
            pass


def add_campaign_claimed_tags():
    """ Add campaign claimed tag instances
    """
    Tag = apps.get_model('osf', 'Tag')
    for tag_name in CAMPAIGN_CLAIMED_TAGS:
        tag = Tag.all_tags.create(name=tag_name, system=True)
        tag.save()
        logging.info('Added tag ' + tag.name)


def add_osf_provider_tags():
    """ Add 'source:provider|osf' tag instance.
        Add 'claimed:provider|osf' tag instance.
    """
    Tag = apps.get_model('osf', 'Tag')
    Tag.all_tags.create(name='source:provider|osf', system=True)
    Tag.all_tags.create(name='claimed:provider|osf', system=True)
    logging.info('Added tag ' + 'source:provider|osf')
    logging.info('Added tag ' + 'claimed:provider|osf')


def add_prereg_campaign_tags():
    """ Add 'source:campaign|prereg' tag instance.
        Add 'claimed:campaign|prereg' tag instance.
        Migrate all users created after prereg challenge end date to the new source tag.
    """
    Tag = apps.get_model('osf', 'Tag')
    OSFUser = apps.get_model('osf', 'OSFuser')
    prereg_challenge_source_tag = Tag.all_tags.get(name='source:campaign|prereg_challenge', system=True)
    logging.info('Added tag ' + prereg_challenge_source_tag.name)
    prereg_source_tag = Tag.all_tags.create(name='source:campaign|prereg', system=True)
    logging.info('Added tag ' + prereg_source_tag.name)
    prereg_challenge_cutoff_date = pytz.utc.localize(datetime(2019, 01, 01, 05, 59))
    prereg_users_registered_after_january_first = OSFUser.objects.filter(tags__id=prereg_challenge_source_tag.id, date_registered__gt=prereg_challenge_cutoff_date)
    logging.info('Number of OSFUsers created on/after 2019-01-01: ' + str(len(prereg_users_registered_after_january_first)))
    for user in prereg_users_registered_after_january_first:
        user.tags.through.objects.filter(tag=prereg_challenge_source_tag).delete()
        user.add_system_tag(prereg_source_tag)
        # Check  whether the user is merged to another user
        # If so, add the same tag to that user as well
        if user.merged_by is not None:
            user.merged_by.add_system_tag(prereg_source_tag)
    logging.info('Migrated users from ' + prereg_challenge_source_tag.name + ' to ' + prereg_source_tag.name)


def main():
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    with transaction.atomic():
        normalize_provider_source_tags()
        add_provider_claimed_tags()
        normalize_campaign_source_tags()
        add_campaign_claimed_tags()
        add_osf_provider_tags()
        add_prereg_campaign_tags()
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back')


if __name__ == '__main__':
    main()