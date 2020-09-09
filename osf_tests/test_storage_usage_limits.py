import pytest

from website.settings import StorageLimits, STORAGE_WARNING_THRESHOLD
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

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, 0)

        assert node.storage_limit_status == StorageLimits.DEFAULT

    def test_storage_limits(self, node):
        GBs = 10 ** 9

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, int(StorageLimits.OVER_PUBLIC * STORAGE_WARNING_THRESHOLD * GBs))

        assert node.storage_limit_status == StorageLimits.APPROACHING_PUBLIC

        storage_usage_cache.set(key, int(StorageLimits.OVER_PRIVATE * STORAGE_WARNING_THRESHOLD * GBs))

        assert node.storage_limit_status == StorageLimits.APPROACHING_PRIVATE

        storage_usage_cache.set(key, int(StorageLimits.OVER_PUBLIC * GBs))

        assert node.storage_limit_status == StorageLimits.OVER_PUBLIC

    def test_limit_custom(self, node):
        node.custom_storage_usage_limit_private = 7
        node.custom_storage_usage_limit_public = 142
        node.save()
        GBs = 10 ** 9

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private * GBs)

        # Compare by name because values are custom and != to StorageLimits members
        assert node.storage_limit_status.name == StorageLimits.OVER_PRIVATE.name

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private * GBs - 1)

        assert node.storage_limit_status.name == StorageLimits.APPROACHING_PRIVATE.name

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public * GBs)

        assert node.storage_limit_status.name == StorageLimits.OVER_PUBLIC.name

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public * GBs - 1)

        assert node.storage_limit_status.name == StorageLimits.APPROACHING_PUBLIC.name
