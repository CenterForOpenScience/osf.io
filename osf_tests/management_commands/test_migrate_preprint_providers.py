# encoding: utf-8
import pytest

from osf_tests.factories import (
    PreprintFactory,
    PreprintProviderFactory
)

from osf.management.commands.migrate_preprint_providers import (
    migrate_preprint_providers
)

from osf.models import Preprint, PreprintProvider


@pytest.fixture()
def source_provider():
    return PreprintProviderFactory()

@pytest.fixture()
def destination_provider():
    return PreprintProviderFactory()

@pytest.fixture()
def empty_provider():
    return PreprintProviderFactory()

@pytest.fixture()
def preprint1(source_provider):
    return PreprintFactory(provider=source_provider)

@pytest.fixture()
def preprint2(source_provider):
    return PreprintFactory(provider=source_provider)

@pytest.fixture()
def preprint3(source_provider):
    return PreprintFactory(provider=source_provider)

@pytest.fixture()
def preprint4(destination_provider):
    return PreprintFactory(provider=destination_provider)

@pytest.fixture()
def preprint5(destination_provider):
    return PreprintFactory(provider=destination_provider)


@pytest.mark.django_db
class TestPreprintProviderMigration:

    def test_preprint_provider_migration(self, source_provider, destination_provider, empty_provider, preprint1, preprint2, preprint3, preprint4, preprint5):
        assert Preprint.objects.filter(provider=source_provider).count() == 3
        assert Preprint.objects.filter(provider=destination_provider).count() == 2

        migration_count = migrate_preprint_providers(source_provider._id, destination_provider._id)

        assert migration_count == 3
        assert Preprint.objects.filter(provider=source_provider).count() == 0
        assert Preprint.objects.filter(provider=destination_provider).count() == 5

        updated_preprint1 = Preprint.load(preprint1._id)
        updated_preprint5 = Preprint.load(preprint5._id)
        assert updated_preprint1.provider == destination_provider
        assert updated_preprint5.provider == destination_provider

        empty_migration_count = migrate_preprint_providers(empty_provider._id, destination_provider._id)
        assert empty_migration_count == 0
        assert Preprint.objects.filter(provider=destination_provider).count() == 5

    def test_preprint_provider_migration_deletion(self, source_provider, destination_provider, preprint1, preprint2):
        assert Preprint.objects.filter(provider=source_provider).count() == 2
        assert Preprint.objects.filter(provider=destination_provider).count() == 0
        assert PreprintProvider.objects.filter(_id=source_provider._id).count() == 1

        migrate_preprint_providers(source_provider._id, destination_provider._id, delete_source_provider=True)

        assert Preprint.objects.filter(provider=destination_provider).count() == 2
        assert PreprintProvider.objects.filter(_id=source_provider._id).count() == 0
