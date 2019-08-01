import pytest
import pytz
from datetime import datetime

from osf_tests.factories import PreprintFactory, UserFactory, ProjectFactory, TagFactory
from osf.models import Tag
from scripts.normalize_user_tags import normalize_source_tags, add_claimed_tags, add_osf_provider_tags, add_prereg_campaign_tags, PROVIDER_SOURCE_TAGS, CAMPAIGN_SOURCE_TAGS, PROVIDER_CLAIMED_TAGS, CAMPAIGN_CLAIMED_TAGS
from website.util.metrics import OsfSourceTags, CampaignSourceTags, OsfClaimedTags, CampaignClaimedTags

pytestmark = pytest.mark.django_db


class TestUserSystemTagNormalization:

    @pytest.fixture()
    def legacy_system_tags(self):
        tags = []
        for item in [item[0] for item in PROVIDER_SOURCE_TAGS]:
            tag = Tag(name=item, system=True)
            tag.save()

        for item in [item[0] for item in CAMPAIGN_SOURCE_TAGS]:
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
        normalize_source_tags()
        add_claimed_tags()
        # Test that provider source tags are properly renamed
        for name in [item[1] for item in PROVIDER_SOURCE_TAGS]:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that provider claim tags are added
        for name in PROVIDER_CLAIMED_TAGS:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that campaign source tags are properly renamed
        for name in [item[1] for item in CAMPAIGN_SOURCE_TAGS]:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that campaign claim tags are added
        for name in CAMPAIGN_CLAIMED_TAGS:
            assert Tag.all_tags.filter(name=name, system=True).exists()

        # Test that osf provider tags are added
        add_osf_provider_tags()
        assert Tag.all_tags.filter(name=OsfSourceTags.Osf.value, system=True).exists()
        assert Tag.all_tags.filter(name=OsfClaimedTags.Osf.value, system=True).exists()

        # Test that prereg campaign source tag is created.
        # Also make sure users created after the cutoff date have
        # `source:campaign|prereg` instead of `source:campaign|prereg_challenge`
        prereg_challenge_source_tag = Tag.all_tags.get(name=CampaignSourceTags.PreregChallenge.value, system=True)
        prereg_challenge_user_created_before_cutoff.add_system_tag(prereg_challenge_source_tag)
        prereg_challenge_user_created_after_cutoff.add_system_tag(prereg_challenge_source_tag)
        add_prereg_campaign_tags()
        assert CampaignSourceTags.PreregChallenge.value in prereg_challenge_user_created_before_cutoff.system_tags
        assert CampaignSourceTags.Prereg.value not in prereg_challenge_user_created_before_cutoff.system_tags
        assert CampaignSourceTags.Prereg.value in prereg_challenge_user_created_after_cutoff.system_tags
        assert CampaignSourceTags.PreregChallenge.value not in prereg_challenge_user_created_after_cutoff.system_tags
