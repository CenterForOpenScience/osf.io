import pytest
from django.core.management import call_command
from django.utils import timezone

from osf.models import Preprint
from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from tests.utils import capture_notifications


@pytest.mark.django_db
class TestSetPreprintsMigrated:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider_preprints(self, provider):
        published = PreprintFactory(provider=provider)
        with capture_notifications():
            PreprintFactory.create_version(create_from=published, creator=published.creator, set_doi=False)
        PreprintFactory(provider=provider, is_published=False)
        withdrawn = PreprintFactory(provider=provider)
        withdrawn.date_withdrawn = timezone.now()
        withdrawn.save()
        deleted = PreprintFactory(provider=provider)
        deleted.deleted = timezone.now()
        deleted.save()
        return Preprint.objects.filter(provider=provider)

    @pytest.fixture()
    def other_preprint(self):
        return PreprintFactory()

    def test_set_and_unset(self, provider, provider_preprints, other_preprint):
        assert provider_preprints.count() == 5

        call_command('set_preprints_migrated', '--provider-id', provider._id)
        assert not provider_preprints.filter(is_migrated=False).exists()
        other_preprint.reload()
        assert not other_preprint.is_migrated

        call_command('set_preprints_migrated', '--provider-id', provider._id, '--unset')
        assert not provider_preprints.filter(is_migrated=True).exists()

    def test_unknown_provider(self):
        with pytest.raises(RuntimeError):
            call_command('set_preprints_migrated', '--provider-id', 'notaprovider')
