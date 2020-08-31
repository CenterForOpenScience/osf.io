import pytest

from website.settings import StorageLimits
from osf_tests.factories import ProjectFactory
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestStorageUsageLimits:

    @pytest.fixture()
    def node(self):
        return ProjectFactory()

    def test_limit_default(self, node):
        assert node.storage_usage is None

        with pytest.raises(NotImplementedError) as e:
            node.storage_limit_status

        assert str(e.value) == 'Storage usage not calculated'

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, 0)

        assert node.storage_limit_status == StorageLimits.DEFAULT

    def test_limit_private_public(self, node):
        assert node.is_public is False

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, StorageLimits.APPROACHING_PUBLIC)

        assert node.storage_limit_status == StorageLimits.OVER_PRIVATE

        node.is_public = True
        node.save()

        assert node.storage_limit_status == StorageLimits.APPROACHING_PUBLIC

    def test_limit_custom(self, node):
        node.custom_storage_usage_limit_private = 20
        node.custom_storage_usage_limit_public = 21
        node.save()

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, 0)

        assert node.storage_limit_status == StorageLimits.DEFAULT

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private)

        assert node.storage_limit_status == StorageLimits.OVER_CUSTOM

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private - 1)

        assert node.storage_limit_status == StorageLimits.DEFAULT

        node.is_public = True
        node.save()

        assert node.storage_limit_status == StorageLimits.DEFAULT

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public)

        assert node.storage_limit_status == StorageLimits.OVER_CUSTOM

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public - 1)

        assert node.storage_limit_status == StorageLimits.DEFAULT
