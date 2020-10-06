import pytest

from website.settings import StorageLimits, STORAGE_WARNING_THRESHOLD, STORAGE_LIMIT_PUBLIC, STORAGE_LIMIT_PRIVATE, GBs
from osf_tests.factories import ProjectFactory
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestStorageUsageLimits:

    @pytest.fixture()
    def node(self):
        return ProjectFactory()

    def test_uncalculated_limit(self, node):
        assert node.storage_usage is None
        assert node.storage_limit_status is StorageLimits.NOT_CALCULATED

    def test_limit_default(self, node):
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, 0)

        assert node.storage_limit_status is StorageLimits.DEFAULT

    def test_storage_limits(self, node):
        assert node.storage_limit_status is StorageLimits.NOT_CALCULATED

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)
        storage_usage_cache.set(key, int(STORAGE_LIMIT_PUBLIC * STORAGE_WARNING_THRESHOLD * GBs))

        assert node.storage_limit_status is StorageLimits.APPROACHING_PUBLIC

        storage_usage_cache.set(key, int(STORAGE_LIMIT_PRIVATE * STORAGE_WARNING_THRESHOLD * GBs))

        assert node.storage_limit_status is StorageLimits.APPROACHING_PRIVATE

        storage_usage_cache.set(key, int(STORAGE_LIMIT_PUBLIC * GBs))

        assert node.storage_limit_status is StorageLimits.OVER_PUBLIC

    def test_limit_custom(self, node):
        node.custom_storage_usage_limit_private = 7
        node.save()

        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=node._id)

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private * GBs)

        assert node.storage_limit_status is StorageLimits.OVER_PRIVATE

        storage_usage_cache.set(key, node.custom_storage_usage_limit_private * GBs - 1)

        assert node.storage_limit_status is StorageLimits.APPROACHING_PRIVATE

        node.custom_storage_usage_limit_public = 142
        node.save()

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public * GBs)

        assert node.storage_limit_status is StorageLimits.OVER_PUBLIC

        storage_usage_cache.set(key, node.custom_storage_usage_limit_public * GBs - 1)

        assert node.storage_limit_status is StorageLimits.APPROACHING_PUBLIC
