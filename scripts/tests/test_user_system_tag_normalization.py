import pytest
import pytz
from datetime import datetime

from osf_tests.factories import PreprintFactory, UserFactory, ProjectFactory, TagFactory
from osf.models import Tag
from scripts.normalize_user_tags import normalize_provider_source_tags, normalize_campaign_source_tags, add_provider_claimed_tags, add_campaign_claimed_tags, add_osf_provider_tags, add_prereg_campaign_tags, PROVIDER_SOURCE_TAGS

pytestmark = pytest.mark.django_db

LEGACY_PROVIDER_SOURCE_TAG_NAMES = [
    'africarxiv_preprints',
    'agrixiv_preprints',
    'arabixiv_preprints',
    'bitss_preprints',
    'eartharxiv_preprints',
    'ecoevorxiv_preprints',
    'ecsarxiv_preprints',
    'engrxiv_preprints',
    'focusarchive_preprints',
    'frenxiv_preprints',
    'inarxiv_preprints',
    'lawarxiv_preprints',
    'lissa_preprints',
    'marxiv_preprints',
    'mediarxiv_preprints',
    'mindrxiv_preprints',
    'nutrixiv_preprints',
    'osf_preprints',
    'paleorxiv_preprints',
    'psyarxiv_preprints',
    'socarxiv_preprints',
    'sportrxiv_preprints',
    'thesiscommons_preprints',
    'bodoarxiv_preprints',
    'osf_registries',
]

NORMALIZED_PROVIDER_SOURCE_TAG_NAMES = [
    'source:provider|preprint|africarxiv',
    'source:provider|preprint|agrixiv',
    'source:provider|preprint|arabixiv',
    'source:provider|preprint|metaarxiv',
    'source:provider|preprint|eartharxiv',
    'source:provider|preprint|ecoevorxiv',
    'source:provider|preprint|ecsarxiv',
    'source:provider|preprint|engrxiv',
    'source:provider|preprint|focusarchive',
    'source:provider|preprint|frenxiv',
    'source:provider|preprint|inarxiv',
    'source:provider|preprint|lawarxiv',
    'source:provider|preprint|lissa',
    'source:provider|preprint|marxiv',
    'source:provider|preprint|mediarxiv',
    'source:provider|preprint|mindrxiv',
    'source:provider|preprint|nutrixiv',
    'source:provider|preprint|osf',
    'source:provider|preprint|paleorxiv',
    'source:provider|preprint|psyarxiv',
    'source:provider|preprint|socarxiv',
    'source:provider|preprint|sportrxiv',
    'source:provider|preprint|thesiscommons',
    'source:provider|preprint|bodoarxiv',
    'source:provider|registry|osf',
]

PROVIDER_CLAIMED_TAG_NAMES = [
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

LEGACY_CAMPAIGN_SOURCE_TAG_NAMES = [
    'erp_challenge_campaign',
    'prereg_challenge_campaign',
    'osf_registered_reports',
    'osf4m',
]

NORMALIZED_CAMPAIGN_SOURCE_TAG_NAMES = [
    'source:campaign|erp',
    'source:campaign|prereg_challenge',
    'source:campaign|osf_registered_reports',
    'source:campaign|osf4m',
]

CAMPAIGN_CLAIMED_TAG_NAMES = [
    'claimed:campaign|erp',
    'claimed:campaign|prereg_challenge',
    'claimed:campaign|prereg',
    'claimed:campaign|osf_registered_reports',
    'claimed:campaign|osf4m',
]

class TestUserSystemTagNormalization:

    @pytest.fixture()
    def legacy_system_tags(self):
        tags = []
        for item in LEGACY_PROVIDER_SOURCE_TAG_NAMES:
            tag = Tag(name=item, system=True)
            tag.save()

        for item in LEGACY_CAMPAIGN_SOURCE_TAG_NAMES:
            tag = Tag(name=item, system=True)
            tag.save()

    @pytest.fixture()
    def prereg_challenge_user_created_before_cutoff(self):
        user = UserFactory()
        user.date_registered = pytz.utc.localize(datetime(1998, 12, 01, 04, 48))
        user.save()
        return user

    @pytest.fixture()
    def prereg_challenge_user_created_after_cutoff(self):
        user = UserFactory()
        user.date_registered = pytz.utc.localize(datetime(2019, 12, 01, 04, 48))
        user.save()
        return user

    def test_user_system_tags_normalization(self, legacy_system_tags, prereg_challenge_user_created_before_cutoff,
                                            prereg_challenge_user_created_after_cutoff):
        # Test that provider source tags are properly renamed
        normalize_provider_source_tags()
        for name in NORMALIZED_PROVIDER_SOURCE_TAG_NAMES:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that provider claim tags are added
        add_provider_claimed_tags()
        for name in PROVIDER_CLAIMED_TAG_NAMES:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that campaign source tags are properly renamed
        normalize_campaign_source_tags()
        for name in NORMALIZED_CAMPAIGN_SOURCE_TAG_NAMES:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that campaign claim tags are added
        add_campaign_claimed_tags()
        for name in CAMPAIGN_CLAIMED_TAG_NAMES:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that osf provider tags are added
        add_osf_provider_tags()
        assert Tag.all_tags.filter(name='source:provider|osf', system=True).exists()
        assert Tag.all_tags.filter(name='claimed:provider|osf', system=True).exists()

        # Test that prereg campaign source tag is created.
        # Also make sure users created after the cutoff date have
        # `source:campaign|prereg` instead of `source:campaign|prereg_challenge`
        prereg_challenge_source_tag = Tag.all_tags.get(name='source:campaign|prereg_challenge', system=True)
        prereg_challenge_user_created_before_cutoff.add_system_tag(prereg_challenge_source_tag)
        prereg_challenge_user_created_after_cutoff.add_system_tag(prereg_challenge_source_tag)
        add_prereg_campaign_tags()
        assert 'source:campaign|prereg_challenge' in prereg_challenge_user_created_before_cutoff.system_tags
        assert 'source:campaign|prereg' not in prereg_challenge_user_created_before_cutoff.system_tags
        assert 'source:campaign|prereg' in prereg_challenge_user_created_after_cutoff.system_tags
        assert 'source:campaign|prereg_challenge' not in prereg_challenge_user_created_after_cutoff.system_tags
